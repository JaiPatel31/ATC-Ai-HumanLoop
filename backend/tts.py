from TTS.api import TTS
from pydub import AudioSegment, effects
import random, os


# Load two voices (you can experiment later)
TTS_MODELS = {
    "controller": "tts_models/en/ljspeech/tacotron2-DDC",  # clear tower-style voice
    "pilot": "tts_models/en/vctk/vits",                    # male pilot-like voice
}

tts_cache = {}

def add_radio_effect(wav_path: str) -> str:
    """
    Apply a simple ATC-style radio filter to a WAV file.
    - Band-limit to ~300–3400 Hz
    - Slight compression
    - Optional static noise layer
    """
    audio = AudioSegment.from_wav(wav_path)

    # Band-pass filter like VHF radio
    audio = audio.high_pass_filter(300).low_pass_filter(3400)

    # Light compression and volume tweak
    audio = effects.compress_dynamic_range(audio)
    audio = audio + random.randint(-1, 2)  # small volume variation

    # Add a bit of static noise
    noise = AudioSegment(
        (os.urandom(len(audio.raw_data))),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels,
    ).apply_gain(-45)
    audio = audio.overlay(noise)

    # Export new file
    out_path = wav_path.replace(".wav", "_radio.wav")
    audio.export(out_path, format="wav")
    return out_path

def get_tts(speaker: str):
    if speaker not in tts_cache:
        model = TTS_MODELS.get(speaker, TTS_MODELS["controller"])
        print(f"Loading TTS model for {speaker}: {model}")
        tts_cache[speaker] = TTS(model)
    return tts_cache[speaker]

def synthesize(text: str, speaker: str = "controller", path: str = "response.wav"):
    tts = get_tts(speaker)
    os.makedirs("generated_audio", exist_ok=True)
    full_path = os.path.join("generated_audio", path)

    tts.tts_to_file(text=text, file_path=full_path)

    # 🔊 Apply radio effect
    radio_path = add_radio_effect(full_path)
    return radio_path

