import torch
from transformers import pipeline
import tempfile
from fastapi import UploadFile

# load once at startup (Large-v3 fine-tuned for ATC)
asr = pipeline(
    task="automatic-speech-recognition",
    model="jacktol/whisper-large-v3-finetuned-for-ATC",
    torch_dtype=torch.float32,   # safer on CPU
    device="cuda" if torch.cuda.is_available() else "cpu",
)

async def transcribe(file: UploadFile):
    # save uploaded audio to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # run inference
    result = asr(tmp_path)
    text = result["text"]

    # optional cleanup for ICAO-style normalization
    text = text.replace("NINER", "NINE").upper()
    return text
