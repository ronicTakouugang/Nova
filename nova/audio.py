import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80ms at 16kHz — the chunk size openWakeWord expects

_FRAME_MS = FRAME_SAMPLES / SAMPLE_RATE * 1000
ENERGY_THRESHOLD = 300.0  # empirical RMS threshold for int16 mic audio
SILENCE_MS = 1200
MIN_SPEECH_MS = 300
MAX_RECORD_SECONDS = 12


def record_until_silence() -> np.ndarray:
    """Record mono int16 audio at SAMPLE_RATE from the default microphone until
    SILENCE_MS of low-energy audio follows some detected speech, or
    MAX_RECORD_SECONDS elapses. Returns an empty array if nothing was captured."""
    silence_frames_needed = int(SILENCE_MS / _FRAME_MS)
    min_speech_frames = int(MIN_SPEECH_MS / _FRAME_MS)
    max_frames = int(MAX_RECORD_SECONDS * 1000 / _FRAME_MS)

    frames = []
    speech_frames = 0
    silence_run = 0

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES
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

    return np.concatenate(frames) if frames else np.empty(0, dtype=np.int16)
