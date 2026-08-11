import wave

from .audio import SAMPLE_RATE
from .config import MEMORY_DIR

MODEL_SIZE = "small"
LAST_COMMAND_WAV = MEMORY_DIR / "last_command.wav"

_model = None


def _disable_hf_symlinks() -> None:
    """huggingface_hub tries to symlink into its cache when downloading model
    files, which needs Windows Developer Mode or admin rights. Pre-mark the
    cache dir as symlink-unsupported so it falls back to copying instead of
    raising OSError [WinError 1314] on machines without that privilege."""
    try:
        from pathlib import Path

        from huggingface_hub import constants as hf_constants
        from huggingface_hub import file_download as hf_file_download

        cache_dir = str(Path(hf_constants.HF_HUB_CACHE).expanduser().resolve())
        hf_file_download._are_symlinks_supported_in_dir[cache_dir] = False
    except Exception:
        pass  # best effort — internals changed, let the normal path run


def _get_model():
    global _model
    if _model is None:
        _disable_hf_symlinks()
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio) -> str:
    """Transcribe mono int16 audio (numpy array at SAMPLE_RATE) to French text."""
    if audio.size == 0:
        return ""

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(LAST_COMMAND_WAV), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio.tobytes())

    model = _get_model()
    segments, _ = model.transcribe(str(LAST_COMMAND_WAV), language="fr")
    return " ".join(segment.text.strip() for segment in segments).strip()
