from fastapi import Body, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from stt_hf import pipeline_status, transcribe
from parser import parse_atc
from parser_ai_enhanced import parse_atc_enhanced  # AI-enhanced parser
from fastapi.responses import FileResponse
from tts import describe_capabilities, synthesize
from phonetics import replace_callsign_at_start, expand_callsign_inline

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def _format_flight_level(value: int | float | None) -> str:
    if value is None:
        return "flight level"

    level = int(round(value))
    return f"flight level {level:03d}"


def _normalize_heading(value: int | float | None) -> int | None:
    if value is None:
        return None

    return int(round(value)) % 360


def _build_controller_response(parsed: dict) -> str:
    cs = parsed.get("callsign") or "Aircraft"
    fl = parsed.get("flight_level") or 0
    hdg = parsed.get("heading") or 0
    cmd = parsed.get("command")
    speaker = parsed.get("speaker")
    event = parsed.get("event")

    if event == "traffic_alert":
        intruder = parsed.get("traffic_callsign") or "opposing traffic"
        current_heading = _normalize_heading(parsed.get("heading"))
        divergence_heading = None
        if current_heading is not None:
            divergence_heading = (current_heading - 30) % 360

        descent_target = None
        if isinstance(parsed.get("flight_level"), (int, float)):
            level_value = int(round(parsed.get("flight_level")))
            if level_value >= 20:
                descent_target = max(0, level_value - 20)

        fragments: list[str] = [f"{cs}, roger. Traffic alert on {intruder} acknowledged."]
        if divergence_heading is not None:
            fragments.append(f"Turn left heading {divergence_heading:03d} immediately.")
        if descent_target is not None:
            fragments.append(
                f"Descend to {_format_flight_level(descent_target)} for separation."
            )
        else:
            fragments.append("Descend immediately to increase vertical spacing.")
        if intruder != "opposing traffic":
            fragments.append(f"We'll ensure {intruder} maintains clearance.")
        fragments.append("Report clear of conflict.")
        return " ".join(fragments)

    if speaker == "pilot":
        if cmd == "descend":
            return f"{cs}, roger. Descend to flight level {fl} approved."
        if cmd == "climb":
            return f"{cs}, roger. Climb and maintain flight level {fl} approved."
        if cmd == "turn":
            return f"{cs}, roger. Turn heading {hdg} approved."
        if cmd == "maintain":
            return f"{cs}, roger. Maintain current flight level {fl}."
        return f"{cs}, say again."

    if speaker == "controller":
        if cmd == "descend":
            return f"{cs}, wilco. Descending to flight level {fl}."
        if cmd == "climb":
            return f"{cs}, wilco. Climbing to flight level {fl}."
        if cmd == "turn":
            return f"{cs}, wilco. Turning heading {hdg}."
        if cmd == "maintain":
            return f"{cs}, wilco. Maintaining flight level {fl}."
        return f"{cs}, wilco."

    return f"{cs}, say again — transmission unclear."


def _process_transcript(transcript: str, use_ai_parser: bool = True):
    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty")

    # Use AI-enhanced parser for better quality, fallback to original if specified
    if use_ai_parser:
        parsed = parse_atc_enhanced(transcript)
    else:
        parsed = parse_atc(transcript)

    normalized = replace_callsign_at_start(transcript, parsed.get("callsign"))
    response_text = _build_controller_response(parsed)
    response_tts = expand_callsign_inline(response_text, parsed.get("callsign"))

    return {
        "transcript": normalized,
        "parsed": parsed,
        "response": response_text,
        "response_tts": response_tts,
    }


@app.post("/stt")
async def stt(file: UploadFile, use_ai_parser: bool = True):
    """
    Speech-to-text endpoint with AI-enhanced parsing.

    Args:
        file: Audio file upload
        use_ai_parser: Use AI-enhanced parser (default: True) for better quality
    """
    transcript = await transcribe(file)
    return _process_transcript(transcript, use_ai_parser=use_ai_parser)


@app.post("/interpret")
async def interpret(payload: dict = Body(...)):
    """
    Interpret text transcript with AI-enhanced parsing.

    Args:
        payload: {"transcript": str, "use_ai_parser": bool (optional, default: True)}
    """
    transcript = payload.get("transcript", "") if isinstance(payload, dict) else ""
    use_ai_parser = payload.get("use_ai_parser", True) if isinstance(payload, dict) else True
    return _process_transcript(transcript, use_ai_parser=use_ai_parser)


@app.post("/tts")
async def tts_endpoint(data: dict):
    text = data.get("text", "")
    speaker = data.get("speaker", "controller")
    if not text:
        return {"error": "Missing text"}
    path = synthesize(text, speaker=speaker)
    return FileResponse(path, media_type="audio/wav")


@app.get("/health")
async def health_check():
    """Expose backend readiness for monitoring dashboards."""

    return {
        "status": "ok",
        "speech_to_text": pipeline_status(),
        "text_to_speech": describe_capabilities(),
        "parser": {
            "type": "AI-enhanced",
            "version": "1.0",
        },
    }

