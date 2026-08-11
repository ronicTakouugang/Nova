import os
from pathlib import Path

from .config import MEMORY_DIR, VOICE_ENABLED

os.environ.setdefault("COQUI_TOS_AGREED", "1")

XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
LANGUAGE = "fr"
VOICE_SAMPLE = os.getenv("NOVA_VOICE_SAMPLE")  # optional wav to clone a specific voice
OUTPUT_WAV = MEMORY_DIR / "last_reply.wav"

_tts = None


def _get_tts():
    global _tts
    if _tts is None:
        from TTS.api import TTS

        _tts = TTS(XTTS_MODEL)
    return _tts


def speak(text: str) -> None:
    """Synthesize `text` with XTTS-v2 and play it. Fails silently (with a
    printed notice) so a broken audio pipeline never breaks the chat loop."""
    text = text.strip()
    if not text or not VOICE_ENABLED:
        return
    try:
        tts = _get_tts()
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        kwargs = {"text": text, "language": LANGUAGE, "file_path": str(OUTPUT_WAV)}
        if VOICE_SAMPLE:
            kwargs["speaker_wav"] = VOICE_SAMPLE
        elif tts.speakers:
            kwargs["speaker"] = tts.speakers[0]
        tts.tts_to_file(**kwargs)
        _play(OUTPUT_WAV)
    except Exception as exc:
        print(f"[voix indisponible : {exc}]")


def _play(path: Path) -> None:
    # winsound is stdlib and Windows-only — this project targets Windows for now.
    # Revisit with a cross-platform backend (e.g. sounddevice) if Nova ever runs elsewhere.
    import winsound

    winsound.PlaySound(str(path), winsound.SND_FILENAME)
