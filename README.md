# Six Strings 🎸

**HackMerced XI submission.** Sheet music in, guitar tab out.

Six Strings reads printed sheet music with an open-source deep-learning model (**oemer**),
works out the easiest way to finger every note on the fretboard, rates how hard the song is
on an explainable 1–10 scale, renders tab + notation with playback (**alphaTab**), and coaches
you through it with a local open-source LLM (**Qwen 2.5 3B via Ollama**).
Everything runs offline on a laptop.

## Features
- **Upload sheet music**: a photo/scan (PNG/JPG) goes through oemer; MusicXML files are read directly
- **Automatic fingering**: every note gets a string and fret, chosen to minimize hand movement
- **Standard / Beginner modes**: Beginner keeps you near the first frets and open strings
- **Explainable difficulty score**: 1–10 with the reasons and the trickiest measures
- **Playback**: tab + standard notation, moving cursor, speed slider, metronome, loop any measure
- **AI practice coach**: practice plans, measure-by-measure tips and chat, streamed from a local LLM
- **Song library**: 14 public-domain melodies sorted from Beginner to Advanced

## Requirements
- Windows 10/11
- [Python 3.11](https://www.python.org/downloads/) (`py -3.11 --version` should work).
  Newer versions such as 3.14 are not supported by oemer's dependencies yet.
- [Ollama](https://ollama.com/download)
- Internet for the first run only (packages, alphaTab files, oemer model weights)

## Run it

**One-time setup**
```
ollama pull qwen2.5:3b
```
(If `ollama` isn't recognized, restart VS Code/your terminal, or use
`& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:3b`.)

**Every time** — use two terminals:

1. **Start the AI model:** double-click `start-ollama.bat` (or run `.\start-ollama.bat`).
   Leave that window open.
2. **Start the app:** double-click `run.bat` (or run `.\run.bat`).
   The first run creates `.venv` and installs packages, which takes a few minutes.
   Your browser opens **http://localhost:8000**; refresh if it loads before the server is ready.

Stop the app with **Ctrl+C** in its terminal.

**Manual setup** (instead of `run.bat`):
```
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --port 8000
```

## Demo tips
- To get a clean test image for the upload, open any library song, switch the view to
  **Notation**, and take a screenshot.
- Run one image upload before presenting: oemer downloads its model weights the first time.
- `samples/` has MusicXML files that upload instantly.

## Troubleshooting
| Problem | Fix |
|---|---|
| Coach says *"Offline coach: start Ollama"* | Make sure `start-ollama.bat` is running. The top-right pill should be green. |
| Ollama error `CUDA error: device kernel image is invalid` | The NVIDIA driver is older than Ollama's CUDA build. `start-ollama.bat` disables CUDA (Ollama still uses the GPU via Vulkan). Updating the NVIDIA driver also fixes it. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. |
| Tab doesn't render | The first page load downloads alphaTab into `vendor/`; check you're online and refresh. A plain-text tab is shown as a fallback. |
| Use a different model | `set OLLAMA_MODEL=llama3.2:3b` before `run.bat` (pull it first). |

## How it works
| Stage | File | What |
|---|---|---|
| Optical music recognition | `app.py` → `oemer` | photo/scan → MusicXML |
| Parsing | `engine.parse_musicxml` | MusicXML → notes (top melody line, ties, rests) |
| Range fitting | `engine.fit_to_guitar` | octave-shift into guitar range (E2–G5) |
| Fingering | `engine.assign_frets` | Viterbi search over (string, fret) choices, minimizing hand shifts, string skips and high positions |
| Difficulty | `engine.score_difficulty` | weighted features: sustained speed, note density, position shifts, stretches, neck position, string skips, chords, length |
| Rendering | `static/app.js` | alphaTex → alphaTab (tab + notation, playback, cursor, loop, speed) |
| Coach | `/api/coach` | structured song analysis → local LLM, streamed. The LLM explains; it never computes the tab or the score. |

## Tech
Python · FastAPI · oemer (ONNX Runtime) · Ollama + Qwen 2.5 3B · alphaTab · vanilla HTML/CSS/JS
