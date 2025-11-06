from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from stt_hf import transcribe
from parser import parse_atc

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

    # Build controller reply
    cs = parsed["callsign"] or "Aircraft"
    fl = parsed["flight_level"] or 0
    hdg = parsed["heading"] or 0
    cmd = parsed["command"]
    speaker = parsed["speaker"]

    # --- Dynamic, phrase-aware response generator ---
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
        # Acknowledge receipt of a controller instruction (as a pilot would)
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

    return {
        "transcript": transcript,
        "parsed": parsed,
        "response": response_text
    }

