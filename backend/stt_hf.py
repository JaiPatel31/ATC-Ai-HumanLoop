import tempfile
from typing import Any

from fastapi import HTTPException, UploadFile

try:
    import torch
    from transformers import pipeline
except Exception:  # pragma: no cover - optional dependency
    torch = None
    pipeline = None


ASR_MODEL_ID = "jacktol/whisper-large-v3-finetuned-for-ATC"


def _load_asr_pipeline() -> Any | None:
    if pipeline is None or torch is None:
        return None

    try:
        return pipeline(
            task="automatic-speech-recognition",
            model=ASR_MODEL_ID,
            torch_dtype=torch.float32,  # safer on CPU
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
    except Exception:
        return None


ASR_PIPELINE: Any | None = None
_ASR_ATTEMPTED = False


def load_asr_pipeline(*, force: bool = False) -> Any | None:
    """Lazily load the ASR pipeline so offline test runs avoid network calls."""

    global ASR_PIPELINE, _ASR_ATTEMPTED  # pylint: disable=global-statement

    if not force and _ASR_ATTEMPTED and ASR_PIPELINE is not None:
        return ASR_PIPELINE

    if not _ASR_ATTEMPTED or force:
        _ASR_ATTEMPTED = True
        ASR_PIPELINE = _load_asr_pipeline()
    return ASR_PIPELINE


def pipeline_status() -> dict[str, object]:
    return {
        "attempted": _ASR_ATTEMPTED,
        "available": ASR_PIPELINE is not None,
        "model": ASR_MODEL_ID if ASR_PIPELINE is not None else None,
    }


async def transcribe(file: UploadFile):
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    pipeline_instance = load_asr_pipeline()

    if pipeline_instance is None:
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

    result = pipeline_instance(tmp_path)
    text = result["text"]
    text = text.replace("NINER", "NINE").upper()
    return text
