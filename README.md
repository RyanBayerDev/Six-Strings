# Six Strings 🎸

Sheet music in, guitar tab out. Six Strings reads printed notation with an open-source
deep-learning OMR model (**oemer**), assigns every note to a string and fret with a
dynamic-programming fingering optimizer, rates the song 1–10 with an explainable
difficulty score, renders tab + notation with playback (**alphaTab**), and coaches you
with a local open-source LLM (**Qwen 2.5 3B via Ollama**). Everything runs offline on a laptop.

## Run (Windows)
1. Install Ollama and pull the model: `ollama pull qwen2.5:3b`
2. Double-click `run.bat` (first run creates `.venv` and installs packages), or:
   ```
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m uvicorn app:app --port 8000
   ```
3. Open http://localhost:8000

The first page load downloads alphaTab (renderer, music font, soundfont) and caches it in
`vendor/`, so later runs work offline. oemer downloads its model checkpoints on its first run.

Change the model with `set OLLAMA_MODEL=llama3.2:3b` before starting.

## How it works
| Stage | File | What |
|---|---|---|
| Optical music recognition | `app.py` → `oemer` | photo/scan → MusicXML |
| Parsing | `engine.parse_musicxml` | MusicXML → note events (melody line, ties, rests) |
| Range fitting | `engine.fit_to_guitar` | octave-shift into E2–G5 |
| Fingering | `engine.assign_frets` | Viterbi search over (string, fret) choices minimizing hand movement, string skips and high-fret positions; Beginner mode caps at fret 12 and strongly prefers first position |
| Difficulty | `engine.score_difficulty` | weighted features: sustained speed, note density, position shifts, stretches, neck position, string skips, chords, length |
| Rendering | `static/app.js` | alphaTex → alphaTab (tab + notation, playback, cursor, loop, speed) |
| Coach | `/api/coach` | structured song analysis → local LLM, streamed. The LLM explains; it never computes the tab or the score. |

## Library
14 public-domain melodies in `songs.py`, from Mary Had a Little Lamb (1.3) to Flight of
the Bumblebee (9.1). `samples/` has MusicXML files for testing the upload path.
