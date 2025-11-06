from fastapi import FastAPI, UploadFile
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

@app.post("/stt")
async def stt(file: UploadFile):
    transcript = await transcribe(file)
    parsed = parse_atc(transcript)
    transcript = replace_callsign_at_start(transcript, parsed.get("callsign"))

    cs = parsed.get("callsign") or "Aircraft"
    fl = parsed.get("flight_level") or 0
    hdg = parsed.get("heading") or 0
    cmd = parsed.get("command")
    speaker = parsed.get("speaker")

    # --- your existing response generation ---
    if speaker == "pilot":
        if cmd == "descend":
            response_text = f"{cs}, roger. Descend to flight level {fl} approved."
        elif cmd == "climb":
            response_text = f"{cs}, roger. Climb and maintain flight level {fl} approved."
        elif cmd == "turn":
            response_text = f"{cs}, roger. Turn heading {hdg} approved."
        elif cmd == "maintain":
            response_text = f"{cs}, roger. Maintain current flight level {fl}."
        else:
            response_text = f"{cs}, say again."
    elif speaker == "controller":
        if cmd == "descend":
            response_text = f"{cs}, wilco. Descending to flight level {fl}."
        elif cmd == "climb":
            response_text = f"{cs}, wilco. Climbing to flight level {fl}."
        elif cmd == "turn":
            response_text = f"{cs}, wilco. Turning heading {hdg}."
        elif cmd == "maintain":
            response_text = f"{cs}, wilco. Maintaining flight level {fl}."
        else:
            response_text = f"{cs}, wilco."
    else:
        response_text = f"{cs}, say again — transmission unclear."

    # 🔡 expand callsign for TTS output
    response_tts = expand_callsign_inline(response_text, parsed.get("callsign"))

    return {
        "transcript": transcript,
        "parsed": parsed,
        "response": response_text,      # for on-screen display
        "response_tts": response_tts    # use this for /tts playback
    }
@app.post("/tts")
async def tts_endpoint(data: dict):
    text = data.get("text", "")
    speaker = data.get("speaker", "controller")
    if not text:
        return {"error": "Missing text"}
    path = synthesize(text, speaker=speaker)
    return FileResponse(path, media_type="audio/wav")

