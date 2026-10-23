from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueueItem:
    id: str
    url: str
    status: str = "Queued"
    title: str = ""
    progress: int = 0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    error: str = ""
    retries: int = 0
    row: int = -1
    cancelled: bool = False


@dataclass
class DownloadResult:
    item_id: str
    success: bool
    final_path: str = ""
    error: str = ""
    title: str = ""