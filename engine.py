"""Six Strings engine: parse music -> assign frets -> score difficulty -> export tab.

Pure Python (no music21 needed). Works on MusicXML (.musicxml/.xml/.mxl, e.g. from oemer)
and on the compact text format used by the built-in song library (songs.py).
"""
from __future__ import annotations

import io
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from itertools import product

# ---------------------------------------------------------------- basics
TUNING = [64, 59, 55, 50, 45, 40]          # string 1 (high e) .. string 6 (low E)
STRING_NAMES = ["high e", "B", "G", "D", "A", "low E"]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
STEP_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
FIFTHS_TO_KEY = {-7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F", 0: "C",
                 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#"}
LOW, HIGH = TUNING[-1], TUNING[0] + 15      # playable range E2..G5 (15 frets)


def midi_name(m: int) -> str:
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


def name_to_midi(s: str) -> int:
    m = re.fullmatch(r"([A-Ga-g])([#b]*)(-?\d)", s.strip())
    if not m:
        raise ValueError(f"bad pitch {s!r}")
    pc = STEP_TO_PC[m.group(1).upper()] + m.group(2).count("#") - m.group(2).count("b")
    return pc + 12 * (int(m.group(3)) + 1)


@dataclass
class Event:
    pitches: list[int]            # empty = rest
    dur: float                    # quarter lengths
    measure: int                  # 1-based
    tie_stop: bool = False        # continues the previous note (don't re-pick)
    pos: list[tuple[int, int]] = field(default_factory=list)  # (string, fret) per pitch


@dataclass
class Song:
    title: str
    tempo: int
    ts: tuple[int, int]
    key_fifths: int
    events: list[Event]
    composer: str = ""

    @property
    def bar_len(self) -> float:
        return self.ts[0] * 4 / self.ts[1]


# ---------------------------------------------------------------- durations
# alphaTex duration codes for each representable quarter-length
_DUR_TABLE = [(6, "1", True), (4, "1", False), (3, "2", True), (2, "2", False), (1.5, "4", True),
              (1, "4", False), (0.75, "8", True), (0.5, "8", False), (0.375, "16", True),
              (0.25, "16", False), (0.125, "32", False)]


def quantize(ql: float) -> float:
    q = round(ql * 8) / 8
    return q if q > 0 else 0.125


def split_duration(ql: float) -> list[tuple[float, str, bool]]:
    """Break a duration into representable pieces (tied together when written)."""
    out, rest = [], quantize(ql)
    while rest > 1e-6:
        for v, code, dot in _DUR_TABLE:
            if v <= rest + 1e-6:
                out.append((v, code, dot))
                rest -= v
                break
        else:
            break
    return out


# ---------------------------------------------------------------- library text format
def parse_text(title: str, text: str, tempo: int, ts=(4, 4), key_fifths=0, composer="") -> Song:
    """Compact format: tokens 'E4', 'E4:2', 'r:1', 'C#5:0.5', '[C4,E4,G4]:1', bars split by '|'.
    Default duration is 1 quarter. Raises if a bar (except the first = pickup) doesn't add up."""
    bar_len = ts[0] * 4 / ts[1]
    events: list[Event] = []
    bars = [b.split() for b in text.replace("\n", " ").split("|") if b.strip()]
    for i, toks in enumerate(bars, 1):
        total = 0.0
        for tok in toks:
            p, _, d = tok.partition(":")
            dur = float(d) if d else 1.0
            if p.lower() == "r":
                pitches = []
            elif p.startswith("["):
                pitches = [name_to_midi(x) for x in p.strip("[]").split(",")]
            else:
                pitches = [name_to_midi(p)]
            events.append(Event(pitches, dur, i))
            total += dur
        if i > 1 and i < len(bars) and abs(total - bar_len) > 1e-6:
            raise ValueError(f"{title}: bar {i} has {total} beats, expected {bar_len}")
        if total > bar_len + 1e-6:
            raise ValueError(f"{title}: bar {i} overfull ({total})")
    return Song(title, tempo, ts, key_fifths, events, composer)


# ---------------------------------------------------------------- MusicXML
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _findall(el, name):
    return [c for c in el if _local(c.tag) == name]


def read_musicxml_bytes(data: bytes) -> bytes:
    if data[:2] == b"PK":   # compressed .mxl
        z = zipfile.ZipFile(io.BytesIO(data))
        path = None
        if "META-INF/container.xml" in z.namelist():
            c = ET.fromstring(z.read("META-INF/container.xml"))
            for el in c.iter():
                if _local(el.tag) == "rootfile":
                    path = el.get("full-path")
                    break
        if not path:
            path = next(n for n in z.namelist() if n.endswith((".xml", ".musicxml")) and not n.startswith("META"))
        return z.read(path)
    return data


def parse_musicxml(data: bytes, fallback_title="Uploaded song", melody_only=True) -> Song:
    root = ET.fromstring(read_musicxml_bytes(data))
    title = fallback_title
    for el in root.iter():
        if _local(el.tag) in ("work-title", "movement-title") and (el.text or "").strip():
            title = el.text.strip()
            break
    composer = ""
    for el in root.iter():
        if _local(el.tag) == "creator" and el.get("type") == "composer" and el.text:
            composer = el.text.strip()
    part = next((c for c in root if _local(c.tag) == "part"), None)
    if part is None:
        raise ValueError("No <part> found in MusicXML")

    divisions, ts, fifths, tempo = 1, (4, 4), 0, None
    events: list[Event] = []
    first_voice = None
    for mi, meas in enumerate(_findall(part, "measure"), 1):
        mevents: list[Event] = []
        for el in meas:
            tag = _local(el.tag)
            if tag == "attributes":
                d = _find(el, "divisions")
                if d is not None and d.text:
                    divisions = float(d.text)
                t = _find(el, "time")
                if t is not None and _find(t, "beats") is not None:
                    try:
                        ts = (int(_find(t, "beats").text.split("+")[0]), int(_find(t, "beat-type").text))
                    except Exception:
                        pass
                k = _find(el, "key")
                if k is not None and _find(k, "fifths") is not None:
                    try:
                        fifths = int(_find(k, "fifths").text)
                    except Exception:
                        pass
            elif tag in ("direction", "sound"):
                for s in el.iter():
                    if _local(s.tag) == "sound" and s.get("tempo") and tempo is None:
                        try:
                            tempo = int(round(float(s.get("tempo"))))
                        except Exception:
                            pass
            elif tag == "note":
                if _find(el, "grace") is not None or _find(el, "cue") is not None:
                    continue
                staff = _find(el, "staff")
                if staff is not None and staff.text and staff.text.strip() != "1":
                    continue
                voice_el = _find(el, "voice")
                voice = voice_el.text.strip() if voice_el is not None and voice_el.text else "1"
                if first_voice is None:
                    first_voice = voice
                if voice != first_voice:
                    continue
                dur_el = _find(el, "duration")
                ql = float(dur_el.text) / divisions if dur_el is not None and dur_el.text else 1.0
                is_chord = _find(el, "chord") is not None
                pitch_el = _find(el, "pitch")
                midi = None
                if pitch_el is not None and _find(el, "rest") is None:
                    step = _find(pitch_el, "step").text.strip()
                    alter = _find(pitch_el, "alter")
                    octv = int(_find(pitch_el, "octave").text)
                    midi = STEP_TO_PC[step] + (int(round(float(alter.text))) if alter is not None and alter.text else 0) + 12 * (octv + 1)
                ties = [t.get("type") for t in _findall(el, "tie")]
                if is_chord and mevents and midi is not None:
                    mevents[-1].pitches.append(midi)
                    continue
                mevents.append(Event([midi] if midi is not None else [], quantize(ql), mi,
                                     tie_stop="stop" in ties))
        # keep bars consistent: trim overfull bars
        bar_len = ts[0] * 4 / ts[1]
        total, kept = 0.0, []
        for e in mevents:
            if total + e.dur > bar_len + 1e-6:
                e.dur = quantize(bar_len - total)
                if total + e.dur > bar_len + 1e-6 or e.dur <= 0:
                    break
            kept.append(e)
            total += e.dur
        if mi > 1 and total < bar_len - 1e-6 and kept:
            kept.append(Event([], quantize(bar_len - total), mi))
        if not kept:
            kept = [Event([], bar_len, mi)]
        events.extend(kept)
    # melody mode: keep the top note of each chord
    for e in events:
        if melody_only and len(e.pitches) > 1:
            e.pitches = [max(e.pitches)]
        e.pitches = sorted(set(e.pitches), reverse=True)[:4]
    # drop trailing all-rest bars
    while events and not events[-1].pitches:
        last_m = events[-1].measure
        if any(e.pitches for e in events if e.measure == last_m):
            break
        events = [e for e in events if e.measure != last_m]
    if not any(e.pitches for e in events):
        raise ValueError("No notes found in the score")
    return Song(title, tempo or 100, ts, fifths, events, composer)


# ---------------------------------------------------------------- range fitting
def fit_to_guitar(song: Song) -> int:
    """Shift the whole piece by octaves into guitar range, then fold stragglers. Returns shift."""
    notes = [p for e in song.events for p in e.pitches]
    if not notes:
        return 0
    med = sorted(notes)[len(notes) // 2]
    best = None
    for k in range(-4, 5):
        out = sum(1 for p in notes if not (LOW <= p + 12 * k <= HIGH))
        score = out * 10 + abs(med + 12 * k - 62) / 12
        if best is None or score < best[0]:
            best = (score, k)
    k = best[1]
    for e in song.events:
        new = []
        for p in e.pitches:
            p += 12 * k
            while p < LOW:
                p += 12
            while p > HIGH:
                p -= 12
            new.append(p)
        e.pitches = sorted(set(new), reverse=True)
    return 12 * k


# ---------------------------------------------------------------- fret assignment
def positions(p: int, max_fret: int):
    return [(s + 1, p - o) for s, o in enumerate(TUNING) if 0 <= p - o <= max_fret]


def _shapes(pitches, max_fret):
    opts = [positions(p, max_fret) or positions(p, 24) for p in pitches]
    shapes = []
    for combo in product(*opts):
        strings = [c[0] for c in combo]
        if len(set(strings)) != len(strings):
            continue
        fretted = [c[1] for c in combo if c[1] > 0]
        if fretted and max(fretted) - min(fretted) > 4:
            continue
        shapes.append(list(combo))
    return shapes[:60] or [list(c) for c in zip(*[o[:1] for o in opts])]


def _hand(shape):
    f = [x[1] for x in shape if x[1] > 0]
    return sum(f) / len(f) if f else None


def _static_cost(shape, beginner):
    c = 0.0
    for s, f in shape:
        c += 0.08 * f
        if beginner and f > 4:
            c += 0.35 * (f - 4)
        if not beginner and f > 7:
            c += 0.2 * (f - 7)
    f = [x[1] for x in shape if x[1] > 0]
    if len(f) > 1:
        c += 0.3 * (max(f) - min(f))
    return c


def _move_cost(a, b):
    ha, hb = _hand(a), _hand(b)
    sa = sum(x[0] for x in a) / len(a)
    sb = sum(x[0] for x in b) / len(b)
    c = 0.15 * abs(sa - sb) + (0.4 if abs(sa - sb) >= 2 else 0)
    if ha is None or hb is None:
        return c + 0.2
    d = abs(ha - hb)
    return c + (d * 0.5 if d <= 3 else 1.5 + (d - 3) * 1.2)


def assign_frets(song: Song, mode: str = "standard") -> None:
    beginner = mode == "beginner"
    max_fret = 12 if beginner else 15
    idx = [i for i, e in enumerate(song.events) if e.pitches]
    if not idx:
        return
    layers = []
    for i in idx:
        e = song.events[i]
        prev = layers[-1] if layers else None
        if e.tie_stop and prev is not None and song.events[prev[0]].pitches == e.pitches:
            layers.append((i, [None]))   # copy previous choice
        else:
            layers.append((i, _shapes(e.pitches, max_fret)))
    # Viterbi
    INF = float("inf")
    costs = [[_static_cost(s, beginner) for s in layers[0][1]]] if layers[0][1][0] is not None else [[0.0]]
    back = [[None] * len(layers[0][1])]
    resolved = [layers[0][1]]
    for li in range(1, len(layers)):
        shapes = layers[li][1]
        prev_shapes = resolved[-1]
        if shapes == [None]:
            resolved.append(prev_shapes)
            costs.append(costs[-1][:])
            back.append(list(range(len(prev_shapes))))
            continue
        row, brow = [], []
        for s in shapes:
            sc = _static_cost(s, beginner)
            best, bj = INF, 0
            for j, ps in enumerate(prev_shapes):
                v = costs[-1][j] + _move_cost(ps, s)
                if v < best:
                    best, bj = v, j
            row.append(best + sc)
            brow.append(bj)
        costs.append(row)
        back.append(brow)
        resolved.append(shapes)
    j = min(range(len(costs[-1])), key=lambda k: costs[-1][k])
    for li in range(len(layers) - 1, -1, -1):
        e = song.events[layers[li][0]]
        shape = resolved[li][j]
        pm = {}
        for (s, f) in shape:
            pm.setdefault(TUNING[s - 1] + f, (s, f))
        e.pos = [pm.get(p, shape[0]) for p in e.pitches]
        j = back[li][j] if back[li][j] is not None else 0


# ---------------------------------------------------------------- difficulty
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _dur_word(ql):
    return {4: "whole notes", 3: "dotted halves", 2: "half notes", 1.5: "dotted quarters", 1: "quarter notes",
            0.75: "dotted 8ths", 0.5: "8th notes", 0.25: "16th notes", 0.125: "32nd notes"}.get(ql, f"{ql}-beat notes")


def _ranges(ms):
    ms = sorted(set(ms))
    out, start = [], None
    for i, m in enumerate(ms):
        if start is None:
            start = m
        if i == len(ms) - 1 or ms[i + 1] != m + 1:
            out.append(f"{start}" if start == m else f"{start}-{m}")
            start = None
    return ", ".join(out[:4]) + ("…" if len(out) > 4 else "")


def score_difficulty(song: Song) -> dict:
    notes = [e for e in song.events if e.pitches and not e.tie_stop]
    played = [e for e in song.events if e.pitches]
    sec_per_q = 60 / song.tempo
    total_sec = sum(e.dur for e in song.events) * sec_per_q or 1
    n = max(1, len(notes))
    nps = len(notes) / total_sec
    # sustained speed: fastest run of 6 consecutive notes (ignores lone pickups / grace-like notes)
    onsets, t = [], 0.0
    for e in song.events:
        if e.pitches and not e.tie_stop:
            onsets.append((t, e))
        t += e.dur * sec_per_q
    fastest, run_ms = 0.0, []
    W = min(5, len(onsets) - 1)
    for i in range(len(onsets) - W):
        dt = onsets[i + W][0] - onsets[i][0]
        if dt > 0:
            r = W / dt
            if r > fastest + 1e-6:
                fastest = r
    if W <= 0:
        fastest = nps
    for i in range(len(onsets) - W):
        dt = onsets[i + W][0] - onsets[i][0]
        if dt > 0 and W / dt >= fastest * 0.95:
            run_ms += [o[1].measure for o in onsets[i:i + W + 1]]
    min_dur = min((e.dur for e in notes), default=1)
    fast_measures = run_ms

    shifts, big_shifts, skips, shift_ms, skip_ms = 0, 0, 0, [], []
    prev = None
    max_span, span_m = 0, None
    window = []
    for e in played:
        hand = _hand(e.pos)
        s_avg = sum(s for s, _ in e.pos) / len(e.pos)
        if prev is not None:
            ph, ps = prev
            if hand is not None and ph is not None and abs(hand - ph) >= 3:
                shifts += 1
                shift_ms.append(e.measure)
                if abs(hand - ph) >= 5:
                    big_shifts += 1
            if abs(s_avg - ps) >= 2:
                skips += 1
                skip_ms.append(e.measure)
        if hand is not None:
            prev = (hand, s_avg)
        else:
            prev = (prev[0] if prev else None, s_avg)
        for _, f in e.pos:
            if f > 0:
                window.append((f, e.measure))
        window = window[-3:]
        if len(window) >= 2:
            span = max(f for f, _ in window) - min(f for f, _ in window)
            if span <= 5 and span > max_span:
                max_span, span_m = span, e.measure
    max_fret = max((f for e in played for _, f in e.pos), default=0)
    chord_frac = sum(1 for e in notes if len(e.pitches) > 1) / n
    fs = [f for e in played for _, f in e.pos]
    avg_fret = sum(fs) / len(fs) if fs else 0

    feats = {
        "speed": (clamp((fastest - 1.5) / 6), 0.32),
        "density": (clamp((nps - 1.0) / 5), 0.18),
        "shifts": (clamp(shifts / n * 10 / 2.5 + big_shifts * 0.05), 0.16),
        "stretch": (clamp((max_span - 2) / 4), 0.10),
        "position": (clamp((avg_fret - 2) / 7), 0.10),
        "crossing": (clamp(skips / n * 2.5), 0.08),
        "chords": (clamp(chord_frac * 2), 0.05),
        "length": (clamp((len(notes) - 20) / 120), 0.03),
    }
    raw = sum(v * w for v, w in feats.values())
    score = round(1 + 9 * clamp(raw / 0.68), 1)
    level = "Beginner" if score < 4 else ("Intermediate" if score < 6.8 else "Advanced")

    reasons = []
    reasons.append({"key": "speed", "weight": feats["speed"][0],
                    "text": f"Fastest runs hit {fastest:.1f} notes/sec ({_dur_word(min_dur)} at {song.tempo} BPM)"
                            + (f", in measures {_ranges(fast_measures)}" if feats["speed"][0] > 0.3 else "")})
    reasons.append({"key": "density", "weight": feats["density"][0],
                    "text": f"{len(notes)} notes over {total_sec:.0f} seconds ({nps:.1f} notes/sec on average)"})
    if shifts:
        reasons.append({"key": "shifts", "weight": feats["shifts"][0],
                        "text": f"{shifts} position shift{'s' if shifts > 1 else ''}"
                                + (f" ({big_shifts} large)" if big_shifts else "") + f", in measures {_ranges(shift_ms)}"})
    else:
        reasons.append({"key": "shifts", "weight": 0, "text": "Stays in one hand position, no shifts needed"})
    reasons.append({"key": "stretch", "weight": feats["stretch"][0],
                    "text": f"Widest stretch is {max_span} fret{'s' if max_span != 1 else ''}" + (f" (measure {span_m})" if span_m else "")})
    reasons.append({"key": "position", "weight": feats["position"][0],
                    "text": "Mostly open strings and the first few frets" if avg_fret < 3.5
                    else f"Played higher up the neck (average fret {avg_fret:.1f}, up to fret {max_fret})"})
    if skips:
        reasons.append({"key": "crossing", "weight": feats["crossing"][0],
                        "text": f"{skips} string skip{'s' if skips > 1 else ''} (jumping over a string), in measures {_ranges(skip_ms)}"})
    if chord_frac:
        reasons.append({"key": "chords", "weight": feats["chords"][0], "text": f"{chord_frac:.0%} of beats are chords"})
    reasons.sort(key=lambda r: -r["weight"])

    # per-measure hotspots
    per = {}
    prev = None
    for e in played:
        d = per.setdefault(e.measure, {"notes": 0, "shifts": 0, "skips": 0, "frets": [], "fast": 0})
        if not e.tie_stop:
            d["notes"] += 1
        if e.dur <= 0.25 + 1e-6:
            d["fast"] += 1
        d["frets"] += [f for _, f in e.pos if f > 0]
        hand = _hand(e.pos)
        s_avg = sum(s for s, _ in e.pos) / len(e.pos)
        if prev:
            if hand is not None and prev[0] is not None and abs(hand - prev[0]) >= 3:
                d["shifts"] += 1
            if abs(s_avg - prev[1]) >= 2:
                d["skips"] += 1
        prev = (hand if hand is not None else (prev[0] if prev else None), s_avg)
    hot = []
    for m, d in per.items():
        span = (max(d["frets"]) - min(d["frets"])) if len(d["frets"]) > 1 else 0
        val = d["notes"] * 0.4 + d["fast"] * 0.5 + d["shifts"] * 2 + d["skips"] * 1 + max(0, span - 3) * 1.2
        why = []
        if d["fast"]:
            why.append(f"{d['fast']} fast notes")
        if d["shifts"]:
            why.append(f"{d['shifts']} position shift{'s' if d['shifts'] > 1 else ''}")
        if d["skips"]:
            why.append(f"{d['skips']} string skip{'s' if d['skips'] > 1 else ''}")
        if span >= 4:
            why.append(f"{span}-fret stretch")
        if not why:
            why.append(f"{d['notes']} notes")
        hot.append({"measure": m, "value": round(val, 2), "why": ", ".join(why)})
    hot.sort(key=lambda h: -h["value"])
    return {
        "score": score, "level": level, "reasons": reasons, "hardest_measures": hot[:3],
        "stats": {"notes": len(notes), "seconds": round(total_sec), "notes_per_sec": round(nps, 2),
                  "fastest_nps": round(fastest, 2), "shifts": shifts, "string_skips": skips,
                  "max_stretch": max_span, "max_fret": max_fret, "avg_fret": round(avg_fret, 1)},
    }


# ---------------------------------------------------------------- exports
def to_alphatex(song: Song, staff: str = "score tabs", plain: bool = False) -> str:
    def esc(s):
        return s.replace('"', "'")
    lines = [f'\\title "{esc(song.title)}"']
    if song.composer:
        lines.append(f'\\artist "{esc(song.composer)}"')
    lines.append(f"\\tempo {song.tempo}")
    lines.append(".")
    if not plain:
        lines.append('\\track "Guitar"')
        lines.append(f"\\staff {{{staff}}}")
    bars, cur, cur_m = [], [], None
    prev_pos = None
    for e in song.events:
        if cur_m is not None and e.measure != cur_m:
            bars.append(cur)
            cur = []
        cur_m = e.measure
        pieces = split_duration(e.dur)
        for k, (_, code, dot) in enumerate(pieces):
            suffix = f".{code}" + ("{d}" if dot else "")
            if not e.pitches:
                cur.append("r" + suffix)
                continue
            tied = e.tie_stop or k > 0
            pos = e.pos if e.pos else prev_pos
            notes = [("-" if tied else str(f)) + f".{s}" for s, f in pos]
            if len(notes) == 1:
                cur.append(notes[0] + suffix)
            else:
                cur.append("(" + " ".join(notes) + ")" + suffix)
            prev_pos = pos
    if cur:
        bars.append(cur)
    head = f"\\ts {song.ts[0]} {song.ts[1]} "
    if not plain:
        head += f"\\ks {FIFTHS_TO_KEY.get(song.key_fifths, 'C')} "
    body = []
    for i, b in enumerate(bars):
        body.append((head if i == 0 else "") + " ".join(b))
    return "\n".join(lines) + "\n" + " |\n".join(body) + " |"


def to_ascii(song: Song, bars_per_line: int = 4) -> str:
    """Plain-text tab (fallback view + LLM context)."""
    by_m: dict[int, list[Event]] = {}
    for e in song.events:
        by_m.setdefault(e.measure, []).append(e)
    ms = sorted(by_m)
    out = []
    for i in range(0, len(ms), bars_per_line):
        rows = [f"{n:<2}|" for n in ["e", "B", "G", "D", "A", "E"]]
        header = "   "
        for m in ms[i:i + bars_per_line]:
            seg = ["" for _ in range(6)]
            for e in by_m[m]:
                width = max(3, int(e.dur * 4) + 1)
                cells = ["-" * width for _ in range(6)]
                for (s, f) in e.pos if e.pitches else []:
                    t = "~" if e.tie_stop else str(f)
                    cells[s - 1] = t + "-" * (width - len(t))
                for r in range(6):
                    seg[r] += cells[r]
            header += f"m{m}".ljust(len(seg[0]) + 1)
            for r in range(6):
                rows[r] += seg[r] + "|"
        out.append(header + "\n" + "\n".join(rows))
    return "\n\n".join(out)


def measure_text(song: Song, measure: int) -> str:
    parts = []
    for e in song.events:
        if e.measure != measure:
            continue
        if not e.pitches:
            parts.append(f"rest ({e.dur} beats)")
            continue
        parts.append(" + ".join(f"{midi_name(p)} on {STRING_NAMES[s-1]} string fret {f}"
                                for p, (s, f) in zip(e.pitches, e.pos)) + f" ({e.dur} beats)")
    return "; ".join(parts)


def process(song: Song, mode: str = "standard") -> dict:
    fit_to_guitar(song)
    assign_frets(song, mode)
    diff = score_difficulty(song)
    for h in diff["hardest_measures"]:
        h["notes"] = measure_text(song, h["measure"])
    return {
        "title": song.title, "composer": song.composer, "tempo": song.tempo,
        "time_signature": f"{song.ts[0]}/{song.ts[1]}", "key": FIFTHS_TO_KEY.get(song.key_fifths, "C"),
        "measures": max(e.measure for e in song.events), "mode": mode,
        "difficulty": diff,
        "alphatex": to_alphatex(song), "alphatex_plain": to_alphatex(song, plain=True),
        "alphatex_score": to_alphatex(song, staff="score"),
        "ascii": to_ascii(song),
    }
