from datetime import datetime

from .config import MEMORY_DIR, MEMORY_FILE


def load_memory() -> str:
    if not MEMORY_FILE.exists():
        return ""
    return MEMORY_FILE.read_text(encoding="utf-8")


def append_memory(entry: str) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n## {timestamp}\n{entry}\n")
