import tempfile
from fastapi import HTTPException, UploadFile

try:
    import torch
    from transformers import pipeline
except Exception:  # pragma: no cover - optional dependency
    torch = None
    pipeline = None


def _load_asr_pipeline():
    if pipeline is None or torch is None:
        return None

    try:
        return pipeline(
            task="automatic-speech-recognition",
            model="jacktol/whisper-large-v3-finetuned-for-ATC",
            torch_dtype=torch.float32,  # safer on CPU
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
    except Exception:
        return None


ASR_PIPELINE = _load_asr_pipeline()


async def transcribe(file: UploadFile):
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if ASR_PIPELINE is None:
        try:
            return data.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=500,
                detail="Speech-to-text model is unavailable and the provided file could not be decoded as text.",
            ) from exc

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    result = ASR_PIPELINE(tmp_path)
    text = result["text"]
    text = text.replace("NINER", "NINE").upper()
    return text
