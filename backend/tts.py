import math
import os
import random
import wave
from contextlib import closing
from typing import Any

try:  # pragma: no cover - optional dependency
    from TTS.api import TTS  # type: ignore
    from pydub import AudioSegment, effects
except Exception:  # pragma: no cover
    TTS = None
    AudioSegment = None
    effects = None


TTS_MODELS = {
    "controller": "tts_models/en/ljspeech/tacotron2-DDC",
    "pilot": "tts_models/en/vctk/vits",
}

tts_cache: dict[str, Any] = {}


def _ensure_output_dir() -> str:
    os.makedirs("generated_audio", exist_ok=True)
    return "generated_audio"


def add_radio_effect(wav_path: str) -> str:
    if AudioSegment is None or effects is None:
        return wav_path

    audio = AudioSegment.from_wav(wav_path)
    audio = audio.high_pass_filter(300).low_pass_filter(3400)
    audio = effects.compress_dynamic_range(audio)
    audio = audio + random.randint(-1, 2)

    noise = AudioSegment(
        os.urandom(len(audio.raw_data)),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels,
    ).apply_gain(-45)
    audio = audio.overlay(noise)

    out_path = wav_path.replace(".wav", "_radio.wav")
    audio.export(out_path, format="wav")
    return out_path


def get_tts(speaker: str):
    if TTS is None:
        return None

    if speaker not in tts_cache:
        model = TTS_MODELS.get(speaker, TTS_MODELS["controller"])
        print(f"Loading TTS model for {speaker}: {model}")
        tts_cache[speaker] = TTS(model)
    return tts_cache[speaker]


def _sine_wave_speech_stub(text: str, output_path: str):
    duration_per_char = 0.12
    min_duration = 0.8
    sample_rate = 22050
    amplitude = 16000

    duration = max(min_duration, len(text) * duration_per_char)
    total_frames = int(duration * sample_rate)
    base_freq = 550.0

    with closing(wave.open(output_path, "w")) as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(total_frames):
            freq_variation = 25 * math.sin(2 * math.pi * i / (sample_rate * 0.6))
            sample = int(
                amplitude
                * math.sin(2 * math.pi * (base_freq + freq_variation) * i / sample_rate)
            )
            wav_file.writeframes(sample.to_bytes(2, byteorder="little", signed=True))

    return output_path


def synthesize(text: str, speaker: str = "controller", path: str = "response.wav"):
    directory = _ensure_output_dir()
    full_path = os.path.join(directory, path)

    tts = get_tts(speaker)
    if tts is None:
        return _sine_wave_speech_stub(text or "", full_path)

    # For multi-speaker models like VCTK, we need to specify a speaker
    # Use different speaker IDs for different roles
    if speaker == "pilot":
        # VCTK model - use a specific speaker (p225 is a female voice)
        tts.tts_to_file(text=text, speaker="p225", file_path=full_path)
    else:
        # Single-speaker model (LJSpeech)
        tts.tts_to_file(text=text, file_path=full_path)

    return add_radio_effect(full_path)


def describe_capabilities() -> dict[str, Any]:
    """Expose availability and cache state for health checks."""

    return {
        "available": TTS is not None,
        "loaded_voices": sorted(tts_cache.keys()),
        "supported_voices": sorted(TTS_MODELS.keys()),
    }

