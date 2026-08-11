import sounddevice as sd

from .audio import FRAME_SAMPLES, SAMPLE_RATE, apply_gain

WAKE_WORD = "hey_jarvis"
# 0.5 (the common default) was too strict on a real voice through a built-in mic —
# a clearly-enunciated "Hey Jarvis" during testing scored 0.469, but normal
# conversational volume scored lower still (required near-shouting at 0.3).
# Digital gain didn't help — a clean signal scaled to 12% amplitude still scored
# 0.999, so amplitude alone isn't the bottleneck; more likely background noise or
# natural speech being less crisp than deliberate test speech. Lowered further as
# the one lever with direct supporting data. speexdsp noise suppression (the more
# principled fix) has no Windows wheel and doesn't support Python 3.14 — not
# usable here.
THRESHOLD = 0.2

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
            frame = apply_gain(frame[:, 0])
            prediction = model.predict(frame)
            if prediction.get(WAKE_WORD, 0.0) > THRESHOLD:
                model.reset()
                return
