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

# Some mics/devices (e.g. a laptop's built-in array at default Windows input level)
# capture normal speech far quieter than what the wake word model and silence
# detector were tuned against — requiring the user to nearly shout. Boost quiet
# frames toward a target peak instead of chasing this with an ever-lower threshold.
GAIN_TARGET_PEAK = 12000.0
GAIN_MAX = 6.0
GAIN_NOISE_FLOOR = 50  # skip near-silence — don't amplify mic hiss into false energy


def apply_gain(frame: np.ndarray) -> np.ndarray:
    """Boost a mono int16 frame toward GAIN_TARGET_PEAK if it's quieter than that,
    capped at GAIN_MAX to avoid amplifying silence/noise into false triggers."""
    peak = float(np.abs(frame).max())
    if peak < GAIN_NOISE_FLOOR:
        return frame
    gain = min(GAIN_MAX, GAIN_TARGET_PEAK / peak)
    if gain <= 1.0:
        return frame
    amplified = frame.astype(np.float32) * gain
    return np.clip(amplified, -32768, 32767).astype(np.int16)


def record_until_silence() -> np.ndarray:
    """Record mono int16 audio at SAMPLE_RATE from the default microphone until
    SILENCE_MS of low-energy audio follows some detected speech, or
    MAX_RECORD_SECONDS elapses. Returns an empty array if nothing was captured."""
    silence_frames_needed = int(SILENCE_MS / _FRAME_MS)
    min_speech_frames = math.ceil(MIN_SPEECH_MS / _FRAME_MS)
    max_frames = int(MAX_RECORD_SECONDS * 1000 / _FRAME_MS)

    frames = []
    speech_frames = 0
    silence_run = 0

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES
    ) as stream:
        for _ in range(max_frames):
            frame, _ = stream.read(FRAME_SAMPLES)
            frame = apply_gain(frame[:, 0])
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
