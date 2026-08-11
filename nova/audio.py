import math

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80ms at 16kHz — the chunk size openWakeWord expects

_FRAME_MS = FRAME_SAMPLES / SAMPLE_RATE * 1000
ENERGY_THRESHOLD = 300.0  # empirical RMS threshold for int16 mic audio
SILENCE_MS = 1200
MIN_SPEECH_MS = 300
MAX_RECORD_SECONDS = 12

_input_device = None
_input_device_is_wasapi = False


def get_input_device():
    """Prefer the WASAPI variant of the default input device. sounddevice's
    global default on this machine resolved to the MME variant, which bypasses
    driver-level mic processing (array beamforming, automatic gain control) that
    WASAPI-based apps (browsers, etc.) get — this made normal speaking volume
    far too quiet to work with. Falls back to the system default if no WASAPI
    input device is found (e.g. non-Windows)."""
    global _input_device, _input_device_is_wasapi
    if _input_device is not None:
        return _input_device

    hostapis = sd.query_hostapis()
    wasapi_index = next(
        (i for i, api in enumerate(hostapis) if api["name"] == "Windows WASAPI"), None
    )
    if wasapi_index is None:
        _input_device = sd.default.device[0]
        return _input_device

    devices = sd.query_devices()
    default_name = devices[sd.default.device[0]]["name"]

    # Same physical mic, WASAPI variant, if it exists
    for i, d in enumerate(devices):
        if d["hostapi"] == wasapi_index and d["max_input_channels"] > 0 and d["name"] == default_name:
            _input_device = i
            _input_device_is_wasapi = True
            return _input_device

    # Otherwise any WASAPI input device
    for i, d in enumerate(devices):
        if d["hostapi"] == wasapi_index and d["max_input_channels"] > 0:
            _input_device = i
            _input_device_is_wasapi = True
            return _input_device

    _input_device = sd.default.device[0]
    return _input_device


def get_stream_kwargs() -> dict:
    """Extra kwargs for sd.InputStream(): pins the chosen device and, for WASAPI,
    enables auto_convert. Without it, WASAPI shared-mode streams reject any
    samplerate that doesn't match the device's own mix format (e.g. 48kHz) —
    opening at our SAMPLE_RATE (16kHz) raises `PortAudioError: Invalid sample
    rate` otherwise."""
    get_input_device()  # populate _input_device / _input_device_is_wasapi
    kwargs = {"device": _input_device}
    if _input_device_is_wasapi:
        kwargs["extra_settings"] = sd.WasapiSettings(auto_convert=True)
    return kwargs


def record_until_silence() -> np.ndarray:
    """Record mono int16 audio at SAMPLE_RATE from the microphone until
    SILENCE_MS of low-energy audio follows some detected speech, or
    MAX_RECORD_SECONDS elapses. Returns an empty array if nothing was captured."""
    silence_frames_needed = int(SILENCE_MS / _FRAME_MS)
    min_speech_frames = math.ceil(MIN_SPEECH_MS / _FRAME_MS)
    max_frames = int(MAX_RECORD_SECONDS * 1000 / _FRAME_MS)

    frames = []
    speech_frames = 0
    silence_run = 0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME_SAMPLES,
        **get_stream_kwargs(),
    ) as stream:
        for _ in range(max_frames):
            frame, _ = stream.read(FRAME_SAMPLES)
            frame = frame[:, 0]
            frames.append(frame)

            rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
            if rms > ENERGY_THRESHOLD:
                speech_frames += 1
                silence_run = 0
            else:
                silence_run += 1

            if speech_frames >= min_speech_frames and silence_run >= silence_frames_needed:
                break

    if speech_frames < min_speech_frames:
        return np.empty(0, dtype=np.int16)

    return np.concatenate(frames)
