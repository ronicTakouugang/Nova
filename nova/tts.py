import os
from pathlib import Path

from .config import BASE_DIR, MEMORY_DIR, VOICE_ENABLED

# "piper" (default): fast, local, CPU-friendly — ~6s load + ~6s for a 40-word
# reply, no GPU needed. "xtts": much higher voice quality (cloning-capable) but
# ~70s load + ~1.5s/word on CPU — unusably slow for back-and-forth conversation
# without a GPU. Measured on this machine; see README.
TTS_BACKEND = os.getenv("NOVA_TTS_BACKEND", "piper")
LANGUAGE = "fr"
OUTPUT_WAV = MEMORY_DIR / "last_reply.wav"

# --- Piper ---
PIPER_VOICE_NAME = "fr_FR-siwis-medium"
PIPER_VOICES_DIR = BASE_DIR / ".piper_voices"

_piper_voice = None


def _get_piper_voice():
    global _piper_voice
    if _piper_voice is None:
        from piper.download_voices import download_voice
        from piper.voice import PiperVoice

        PIPER_VOICES_DIR.mkdir(parents=True, exist_ok=True)
        model_path = PIPER_VOICES_DIR / f"{PIPER_VOICE_NAME}.onnx"
        if not model_path.exists():
            download_voice(PIPER_VOICE_NAME, PIPER_VOICES_DIR)
        _piper_voice = PiperVoice.load(str(model_path))
    return _piper_voice


def _speak_piper(text: str) -> None:
    import wave

    voice = _get_piper_voice()
    with wave.open(str(OUTPUT_WAV), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    _play(OUTPUT_WAV)


# --- XTTS-v2 (optional, NOVA_TTS_BACKEND=xtts) ---
os.environ.setdefault("COQUI_TOS_AGREED", "1")

XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
XTTS_VOICE_SAMPLE = os.getenv("NOVA_VOICE_SAMPLE")  # optional wav to clone a specific voice

_xtts = None


def _get_xtts():
    global _xtts
    if _xtts is None:
        from TTS.api import TTS

        _xtts = TTS(XTTS_MODEL)
    return _xtts


def _speak_xtts(text: str) -> None:
    tts = _get_xtts()
    kwargs = {"text": text, "language": LANGUAGE, "file_path": str(OUTPUT_WAV)}
    if XTTS_VOICE_SAMPLE:
        kwargs["speaker_wav"] = XTTS_VOICE_SAMPLE
    elif tts.speakers:
        kwargs["speaker"] = tts.speakers[0]
    tts.tts_to_file(**kwargs)
    _play(OUTPUT_WAV)


def _play(path: Path) -> None:
    # winsound is stdlib and Windows-only — this project targets Windows for now.
    import winsound

    winsound.PlaySound(str(path), winsound.SND_FILENAME)


def speak(text: str) -> None:
    """Synthesize `text` and play it. Fails silently (with a printed notice) so
    a broken audio pipeline never breaks the chat loop."""
    text = text.strip()
    if not text or not VOICE_ENABLED:
        return
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        if TTS_BACKEND == "xtts":
            _speak_xtts(text)
        else:
            _speak_piper(text)
    except Exception as exc:
        print(f"[voix indisponible : {exc}]")
