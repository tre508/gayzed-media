from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
    matches = URL_RE.findall(text)
    seen = set()
    urls = []
    for url in matches:
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def format_bytes(value: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.1f} {units[idx]}"


def format_bps(value) -> str:
    if not value:
        return ""
    return f"{format_bytes(float(value))}/s"


def format_eta(value) -> str:
    if value in (None, ""):
        return ""
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return ""
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def save_url_list(path: str, urls: Iterable[str]) -> None:
    Path(path).write_text("\n".join(urls) + "\n", encoding="utf-8")


def load_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default