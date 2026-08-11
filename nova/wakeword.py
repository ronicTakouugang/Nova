import sounddevice as sd

from .audio import FRAME_SAMPLES, SAMPLE_RATE, get_stream_kwargs

WAKE_WORD = "hey_jarvis"
# Real root cause of needing to shout: sounddevice's global default input device
# resolved to the MME variant of the mic, which skips WASAPI-level driver
# processing (array beamforming, AGC) — see get_input_device() in audio.py.
# Threshold stays lowered from the 0.5 default pending a retest on WASAPI, which
# should score real speech much closer to the ~0.99 seen on synthetic TTS audio.
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
    """Block until the wake word is heard on the microphone."""
    model = _get_model()
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME_SAMPLES,
        **get_stream_kwargs(),
    ) as stream:
        while True:
            frame, _ = stream.read(FRAME_SAMPLES)
            prediction = model.predict(frame[:, 0])
            if prediction.get(WAKE_WORD, 0.0) > THRESHOLD:
                model.reset()
                return
