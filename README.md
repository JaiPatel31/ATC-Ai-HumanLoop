# ATC Voice Loop

ATC Voice Loop is a prototype assistant for air-traffic controllers that pairs live
transcription and intent parsing with a conflict-resolution workspace. The system
listens to pilot/controller audio, turns it into structured data, synthesises a
suggested readback, and surfaces potential conflicts between aircraft so that the
controller can respond quickly.

## Project layout

```
ATC-Ai-HumanLoop/
├── backend/            # FastAPI service for STT, intent parsing, and TTS
├── frontend/           # Vite + React dashboard for the controller workstation
├── requirements.txt    # Python dependencies for the backend service
└── README.md           # Project overview (this file)
```

### Backend service (`backend/`)

* **Framework** – [FastAPI](https://fastapi.tiangolo.com/) with CORS enabled for
  the local frontend.
* **Speech-to-text** – Attempts to load the
  [`jacktol/whisper-large-v3-finetuned-for-ATC`](https://huggingface.co/jacktol/whisper-large-v3-finetuned-for-ATC)
  pipeline. When the model (or GPU) is unavailable the endpoint falls back to
  interpreting uploaded files as plain text so you can still demo the flow.
* **Intent parsing** – `parser.parse_atc` normalises transcripts into structured
  fields (callsign, command, heading, flight level, speaker) using simple
  heuristics tailored for ICAO phraseology.
* **Callsign phonetics** – Utilities in `phonetics.py` expand callsigns into the
  ICAO alphabet both for display and for feeding into TTS.
* **Text-to-speech** – Uses Coqui TTS when available, with a sine-wave stub as a
  lightweight fallback. Generated audio is written to `generated_audio/`.
* **API endpoints** –
  * `POST /stt` – Accepts an audio file upload and returns the parsed
    transmission plus suggested response.
  * `POST /interpret` – Same response shape, but accepts a JSON payload with a
    `transcript` string for manual entry/testing.
  * `POST /tts` – Synthesises audio for a supplied controller/pilot response and
    streams the WAV file back to the caller.

### Frontend application (`frontend/`)

* Built with React 19, TypeScript, and Vite.
* Uploads recordings or manual transcripts, displays the transcript and parsed
  intent, and plays the synthesised readback audio.
* Maintains a rolling history (10 entries) of transmissions for context.
* Aggregates aircraft state from recent transmissions and highlights potential
  conflicts (e.g. vertical separation under 1,000 ft, small heading divergence)
  with suggested controller actions in the `ConflictResolutionPanel`.

## Getting started

### Backend

1. Create and activate a Python environment (Python 3.10+ recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   > **Tip:** The speech synthesis/transcription stacks pull in heavy
   > dependencies (PyTorch, Coqui TTS). For a quicker demo you can install a
   > lighter subset such as `fastapi`, `uvicorn[standard]`, and
   > `transformers`/`torch` only when you need full STT/TTS support.
3. Run the API with auto-reload:
   ```bash
   uvicorn backend.main:app --reload
   ```
4. The service listens on `http://127.0.0.1:8000`. Visit `http://127.0.0.1:8000/docs`
   for automatically generated OpenAPI documentation.

### Frontend

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite dev server:
   ```bash
   npm run dev
   ```
3. Open the printed local URL (usually `http://127.0.0.1:5173`) in your browser.

The frontend expects the FastAPI server to be running on `http://127.0.0.1:8000`.
If you host it elsewhere, update the base URLs in `frontend/src/api.ts`.

## Development notes

* Back-end fallbacks mean you can exercise the UI even without GPU access or the
  optional Coqui/Torch dependencies. Calls to `/stt` will echo the uploaded text
  and `/tts` will produce a synthetic sine-wave response.
* Generated audio files accumulate in `generated_audio/`. Clean this directory if
  you need to reset the workspace.
* The repository uses the default Vite/TypeScript ESLint configuration for the
  frontend. Run `npm run lint` inside `frontend/` to check React code style.

## License

This project is provided as-is for experimentation and human-in-the-loop
workflows. No explicit license has been specified.
