import json
from pathlib import Path

MEMORY_DIR = Path("memory")
MEMORY_FILE = MEMORY_DIR / "memory.json"


def save_destination(destination):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    data = {"previous_destination": destination}
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_destination():
    if not MEMORY_FILE.exists():
        return None
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("previous_destination")
    except Exception:
        return None
