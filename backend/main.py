from fastapi import Body, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from stt_hf import transcribe
from parser import parse_atc
from fastapi.responses import FileResponse
from tts import synthesize
from phonetics import replace_callsign_at_start, expand_callsign_inline

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def _build_controller_response(parsed: dict) -> str:
    cs = parsed.get("callsign") or "Aircraft"
    fl = parsed.get("flight_level") or 0
    hdg = parsed.get("heading") or 0
    cmd = parsed.get("command")
    speaker = parsed.get("speaker")

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


def _process_transcript(transcript: str):
    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty")

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
async def stt(file: UploadFile):
    transcript = await transcribe(file)
    return _process_transcript(transcript)


@app.post("/interpret")
async def interpret(payload: dict = Body(...)):
    transcript = payload.get("transcript", "") if isinstance(payload, dict) else ""
    return _process_transcript(transcript)


@app.post("/tts")
async def tts_endpoint(data: dict):
    text = data.get("text", "")
    speaker = data.get("speaker", "controller")
    if not text:
        return {"error": "Missing text"}
    path = synthesize(text, speaker=speaker)
    return FileResponse(path, media_type="audio/wav")

