import sounddevice as sd

from .audio import FRAME_SAMPLES, SAMPLE_RATE

WAKE_WORD = "hey_jarvis"
# 0.5 (the common default) was too strict on a real voice through a built-in mic —
# a genuine "Hey Jarvis" from the user only scored 0.469. Lowered after measuring
# real utterances; revisit if false triggers become a problem.
THRESHOLD = 0.3

_model = None


def _get_model():
    global _model
    if _model is None:
        from openwakeword.model import Model
        from openwakeword.utils import download_models

        download_models([f"{WAKE_WORD}_v0.1"])
        _model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
    return _model


def wait_for_wake_word() -> None:
    """Block until the wake word is heard on the default microphone."""
    model = _get_model()
    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES
    ) as stream:
        while True:
            frame, _ = stream.read(FRAME_SAMPLES)
            prediction = model.predict(frame[:, 0])
            if prediction.get(WAKE_WORD, 0.0) > THRESHOLD:
                model.reset()
                return
