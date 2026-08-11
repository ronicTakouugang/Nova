import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Benign on machines without Windows Developer Mode / admin rights — nova/stt.py
# already routes around the underlying limitation, this just quiets the warning.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = BASE_DIR / "memory"
MEMORY_FILE = MEMORY_DIR / "notes.md"

MODEL = "claude-opus-5"

# Set NOVA_VOICE=off to run text-only (no synthesis, no playback).
VOICE_ENABLED = os.getenv("NOVA_VOICE", "on").lower() not in ("off", "0", "false")
