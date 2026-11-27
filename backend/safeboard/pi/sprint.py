"""Sprint settings. The file lives in SAFEBOARD_DATA_DIR, outside the repository."""
import datetime as dt
import json

from safeboard import config

DEFAULT = {"name": "Sprint 1", "start": "2026-11-23", "end": "2026-12-06", "source": "varsayılan"}


def sprint_file():
    return config.DATA_DIR / "sprint.json"


def sprint_conf():
    try:
        with open(sprint_file(), encoding="utf-8") as f:
            c = json.load(f)
        dt.date.fromisoformat(c["start"]); dt.date.fromisoformat(c["end"])
        return c
    except Exception:
        return dict(DEFAULT)


def parse(body):
    """Validate a PUT body. Raises on bad input."""
    start = dt.date.fromisoformat(body["start"]); end = dt.date.fromisoformat(body["end"])
    if end < start:
        raise ValueError("Bitiş tarihi başlangıçtan önce olamaz.")
    return {"name": str(body.get("name") or "Sprint")[:60], "start": start.isoformat(), "end": end.isoformat(), "source": "pano"}


def save(conf):
    path = sprint_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(conf, f, ensure_ascii=False, indent=1)
