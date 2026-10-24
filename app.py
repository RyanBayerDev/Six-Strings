"""Six Strings backend: python -m uvicorn app:app --reload  ->  http://localhost:8000"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import engine
from songs import SONGS

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
VENDOR = ROOT / "vendor"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
UPLOADS_FILE = DATA / "uploads.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
ALPHATAB_CDN = ["https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.5/dist/",
                "https://cdn.jsdelivr.net/npm/@coderline/alphatab@1/dist/"]

app = FastAPI(title="Six Strings")

# ------------------------------------------------------------------ library
_cache: dict[tuple[str, str], dict] = {}
_sources: dict[str, dict] = {}     # id -> {"kind": "text"|"xml", ...}

for s in SONGS:
    _sources[s["id"]] = {"kind": "text", **s}

if UPLOADS_FILE.exists():
    try:
        for u in json.loads(UPLOADS_FILE.read_text(encoding="utf-8")):
            _sources[u["id"]] = u
    except Exception:
        pass


def _save_uploads():
    ups = [v for v in _sources.values() if v["kind"] == "xml"]
    UPLOADS_FILE.write_text(json.dumps(ups), encoding="utf-8")


def build(song_id: str, mode: str = "standard") -> dict:
    key = (song_id, mode)
    if key in _cache:
        return _cache[key]
    src = _sources.get(song_id)
    if not src:
        raise HTTPException(404, "Song not found")
    if src["kind"] == "text":
        song = engine.parse_text(src["title"], src["text"], src["tempo"], tuple(src["ts"]), src["key"], src["composer"])
    else:
        song = engine.parse_musicxml(Path(src["path"]).read_bytes(), src["title"])
        if src.get("title"):
            song.title = src["title"]
    out = engine.process(song, mode)
    out["id"] = song_id
    out["source"] = "library" if src["kind"] == "text" else src.get("origin", "upload")
    _cache[key] = out
    return out


def summary(d: dict) -> dict:
    return {k: d[k] for k in ("id", "title", "composer", "tempo", "time_signature", "key", "measures", "source")} | {
        "score": d["difficulty"]["score"], "level": d["difficulty"]["level"],
        "top_reasons": [r["text"] for r in d["difficulty"]["reasons"][:2]]}


@app.get("/api/songs")
def list_songs():
    out = []
    for sid in _sources:
        try:
            out.append(summary(build(sid)))
        except Exception as e:  # a broken upload shouldn't break the library
            print("skip", sid, e)
    out.sort(key=lambda x: x["score"])
    return out


@app.get("/api/songs/{song_id}")
def get_song(song_id: str, mode: str = "standard"):
    return build(song_id, "beginner" if mode == "beginner" else "standard")


# ------------------------------------------------------------------ upload (MusicXML or image -> oemer)
def _find_oemer() -> list[str] | None:
    exe = shutil.which("oemer")
    if exe:
        return [exe]
    for cand in (Path(sys.executable).parent / "oemer.exe", Path(sys.executable).parent / "Scripts" / "oemer.exe",
                 Path(sys.executable).parent / "oemer"):
        if cand.exists():
            return [str(cand)]
    return None


def run_oemer(img: Path, outdir: Path) -> Path:
    cmd = _find_oemer()
    if not cmd:
        raise HTTPException(500, "oemer isn't installed in this Python environment (pip install oemer)")
    proc = subprocess.run(cmd + [str(img), "-o", str(outdir)], capture_output=True, text=True, timeout=900)
    found = sorted(outdir.glob("*.musicxml")) + sorted(outdir.glob("*.xml"))
    if not found:
        tail = (proc.stderr or proc.stdout or "")[-800:]
        raise HTTPException(500, f"oemer didn't produce MusicXML. {tail}")
    return found[0]


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    name = file.filename or "upload"
    ext = Path(name).suffix.lower()
    data = await file.read()
    sid = "up-" + uuid.uuid4().hex[:8]
    dest_dir = DATA / sid
    dest_dir.mkdir(parents=True, exist_ok=True)
    origin = "musicxml"
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        img = dest_dir / f"page{ext if ext != '.webp' else '.png'}"
        img.write_bytes(data)
        xml_path = run_oemer(img, dest_dir)
        origin = "photo (oemer)"
    elif ext in (".musicxml", ".xml", ".mxl"):
        xml_path = dest_dir / f"score{ext}"
        xml_path.write_bytes(data)
    else:
        raise HTTPException(400, "Upload a sheet-music image (PNG/JPG) or a MusicXML file (.musicxml/.xml/.mxl). "
                                 "For a PDF, take a screenshot of the page.")
    title = Path(name).stem.replace("_", " ").replace("-", " ").title()
    try:
        song = engine.parse_musicxml(xml_path.read_bytes(), title)
    except Exception as e:
        raise HTTPException(422, f"Couldn't read the music: {e}")
    if song.title in ("Uploaded song", "", None) or song.title.lower().startswith("page"):
        song.title = title
    _sources[sid] = {"kind": "xml", "id": sid, "title": song.title, "path": str(xml_path), "origin": origin}
    _save_uploads()
    return build(sid)


@app.delete("/api/songs/{song_id}")
def delete_song(song_id: str):
    if song_id in _sources and _sources[song_id]["kind"] == "xml":
        _sources.pop(song_id)
        for k in list(_cache):
            if k[0] == song_id:
                _cache.pop(k)
        _save_uploads()
        return {"ok": True}
    raise HTTPException(400, "Only uploaded songs can be removed")


# ------------------------------------------------------------------ AI coach (Ollama)
SYSTEM = """You are the Six Strings practice coach: a friendly, encouraging guitar teacher for beginners.
You are given analysis data for one song (tab positions, tempo, a difficulty score and the hardest measures).
Rules:
- Base every claim on the provided data. Never invent fret numbers, measures or notes that aren't in it.
- Use plain English and explain any music term you use in a few words.
- Be concise: short paragraphs or short bullet lists, no more than about 180 words unless asked for more.
- Give concrete practice advice: target BPMs (start around 60% of the song tempo), what to isolate, how many reps.
- String names: "high e" is the thinnest string, "low E" is the thickest."""


def song_context(d: dict) -> str:
    diff = d["difficulty"]
    lines = [f"Song: {d['title']}" + (f" by {d['composer']}" if d.get("composer") else ""),
             f"Tempo: {d['tempo']} BPM, time signature {d['time_signature']}, key {d['key']}, {d['measures']} measures",
             f"Difficulty: {diff['score']}/10 ({diff['level']})",
             "Why: " + "; ".join(r["text"] for r in diff["reasons"][:5]),
             "Stats: " + json.dumps(diff["stats"]),
             "Hardest measures:"]
    for h in diff["hardest_measures"]:
        lines.append(f"- Measure {h['measure']} ({h['why']}): {h['notes']}")
    ascii_tab = d["ascii"]
    if len(ascii_tab) > 3500:
        ascii_tab = ascii_tab[:3500] + "\n…(truncated)"
    lines.append("Tab (e = high e string, numbers = frets, m = measure):\n" + ascii_tab)
    return "\n".join(lines)


def fallback_plan(d: dict) -> str:
    diff = d["difficulty"]
    slow = max(40, int(d["tempo"] * 0.6))
    hard = diff["hardest_measures"]
    txt = [f"(Offline coach: start Ollama for full AI answers.)\n",
           f"**{d['title']}** is rated **{diff['score']}/10 ({diff['level']})**. Main reasons: "
           + "; ".join(r["text"] for r in diff["reasons"][:2]) + ".\n",
           "**Practice plan**",
           f"1. Play through slowly at {slow} BPM using the speed slider. Accuracy first.",
           ]
    for i, h in enumerate(hard, 2):
        txt.append(f"{i}. Loop measure {h['measure']} ({h['why']}). Play it 5 times cleanly before moving on.")
    txt.append(f"{len(hard) + 2}. Raise the tempo by 5–10 BPM each time you get 3 clean run-throughs, up to {d['tempo']} BPM.")
    return "\n".join(txt)


@app.get("/api/coach/status")
def coach_status():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        return {"online": True, "model": OLLAMA_MODEL, "installed": OLLAMA_MODEL in models or any(m.startswith(OLLAMA_MODEL) for m in models), "models": models}
    except Exception:
        return {"online": False, "model": OLLAMA_MODEL}


@app.post("/api/coach")
async def coach(req: Request):
    body = await req.json()
    d = build(body["song_id"], body.get("mode", "standard"))
    kind = body.get("kind", "chat")
    question = (body.get("question") or "").strip()
    history = body.get("history", [])[-8:]
    if kind == "plan":
        question = ("Give me a step-by-step practice plan for this song. Start with a one-sentence plain-English "
                    "summary of what makes it hard, then numbered steps that reference the hardest measures.")
    elif kind == "measure":
        question = f"Explain how to practice measure {body.get('measure')} of this song: which fingers, what's tricky, and a drill."
    msgs = [{"role": "system", "content": SYSTEM + "\n\nSONG DATA:\n" + song_context(d)}]
    for h in history:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": question or "How should I practice this song?"})

    def gen():
        try:
            with requests.post(f"{OLLAMA_URL}/api/chat", json={"model": OLLAMA_MODEL, "messages": msgs, "stream": True,
                                                                "options": {"temperature": 0.4, "num_ctx": 4096}},
                               stream=True, timeout=(3, 300)) as r:
                if r.status_code != 200:
                    raise RuntimeError(r.text[:300])
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    piece = chunk.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if chunk.get("done"):
                        break
        except Exception as e:
            print("Ollama error:", e)
            yield fallback_plan(d) if kind != "chat" else (
                "The AI coach is offline. Start Ollama (run `ollama serve`, or open the Ollama app) and make sure "
                f"`{OLLAMA_MODEL}` is pulled.\n\n" + fallback_plan(d))
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


# ------------------------------------------------------------------ alphaTab assets (cached locally)
def _fetch_vendor(path: str) -> Path | None:
    dest = (VENDOR / path).resolve()
    if not str(dest).startswith(str(VENDOR.resolve())):
        return None
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    for base in ALPHATAB_CDN:
        try:
            r = requests.get(base + path, timeout=30)
            if r.status_code == 200 and r.content:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                return dest
        except Exception as e:
            print("vendor fetch failed", path, e)
    return None


@app.get("/vendor/{path:path}")
def vendor(path: str):
    p = _fetch_vendor(path)
    if not p:
        raise HTTPException(404, f"Could not load {path} (are you online for the first run?)")
    media = {".js": "application/javascript", ".mjs": "application/javascript", ".woff2": "font/woff2",
             ".woff": "font/woff", ".otf": "font/otf", ".sf2": "application/octet-stream", ".sf3": "application/octet-stream"}.get(p.suffix)
    return FileResponse(p, media_type=media)


def _prefetch():
    for f in ["alphaTab.js", "font/Bravura.woff2", "font/Bravura.woff", "font/Bravura.otf", "soundfont/sonivox.sf2"]:
        _fetch_vendor(f)


@app.on_event("startup")
def startup():
    threading.Thread(target=_prefetch, daemon=True).start()
    threading.Thread(target=list_songs, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
