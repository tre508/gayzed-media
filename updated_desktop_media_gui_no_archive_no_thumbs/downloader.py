from __future__ import annotations

import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

import yt_dlp
from PySide6.QtCore import QObject, QRunnable, Signal


class GuiLogger:
    def __init__(self, emit_func):
        self.emit = emit_func

    def debug(self, msg):
        self.emit(str(msg))

    def info(self, msg):
        self.emit(str(msg))

    def warning(self, msg):
        self.emit(f"[warning] {msg}")

    def error(self, msg):
        self.emit(f"[error] {msg}")

    def critical(self, msg):
        self.emit(f"[critical] {msg}")


class DownloadSignals(QObject):
    status = Signal(str, str)
    meta = Signal(str, dict)
    progress = Signal(str, dict)
    finished = Signal(str, dict)
    failed = Signal(str, str)
    log = Signal(str)


class DownloadWorker(QRunnable):
    def __init__(
        self,
        item_id: str,
        url: str,
        output_dir: str,
        format_selector: str,
        write_subtitles: bool,
        rate_limit: Optional[str],
        retries: int,
        retry_backoff_seconds: int,
        cookie_browser: str,
        custom_headers: Dict[str, str],
        cancel_check,
    ) -> None:
        super().__init__()
        self.item_id = item_id
        self.url = url
        self.output_dir = output_dir
        self.format_selector = format_selector
        self.write_subtitles = write_subtitles
        self.rate_limit = rate_limit
        self.retries = retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.cookie_browser = cookie_browser
        self.custom_headers = custom_headers
        self.cancel_check = cancel_check
        self.signals = DownloadSignals()
        self.setAutoDelete(True)

    def _progress_hook(self, data: Dict[str, Any]) -> None:
        if self.cancel_check(self.item_id):
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user")

        info_dict = data.get("info_dict")
        if info_dict:
            self.signals.meta.emit(self.item_id, info_dict)

        self.signals.progress.emit(self.item_id, data)

    def _resolve_final_filepath(self, info: Dict[str, Any]) -> str:
        requested = info.get("requested_downloads") or []
        if isinstance(requested, list):
            for entry in requested:
                fp = entry.get("filepath")
                if fp and Path(fp).exists():
                    return str(fp)

        fp = info.get("_filename")
        if fp and Path(fp).exists():
            return str(fp)

        video_id = str(info.get("id") or "").strip()
        if not video_id:
            return ""

        candidates = []
        out_dir = Path(self.output_dir)
        for path in out_dir.iterdir():
            if not path.is_file():
                continue
            if path.name.endswith(".part"):
                continue
            if path.stem == video_id:
                candidates.append(path)

        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return str(candidates[0])

        return ""

    def run(self) -> None:
        attempts = 0

        while attempts <= self.retries:
            if self.cancel_check(self.item_id):
                self.signals.failed.emit(self.item_id, "Cancelled")
                return

            try:
                self.signals.status.emit(
                    self.item_id,
                    f"Starting ({attempts + 1}/{self.retries + 1})",
                )

                Path(self.output_dir).mkdir(parents=True, exist_ok=True)

                # Short safe internal filename to prevent "file name too long" failures.
                outtmpl = str(Path(self.output_dir) / "%(id)s.%(ext)s")

                opts: Dict[str, Any] = {
                    "outtmpl": outtmpl,
                    "format": self.format_selector,
                    "continuedl": True,
                    "noprogress": True,
                    "progress_hooks": [self._progress_hook],
                    "writesubtitles": self.write_subtitles,
                    "writeautomaticsub": False,
                    "retries": 2,
                    "fragment_retries": 2,
                    "extractor_retries": 1,
                    "verbose": True,
                    "logger": GuiLogger(self.signals.log.emit),
                }

                if self.custom_headers:
                    opts["http_headers"] = self.custom_headers

                if self.cookie_browser and self.cookie_browser != "none":
                    opts["cookiesfrombrowser"] = (
                        self.cookie_browser,
                        None,
                        None,
                        None,
                    )

                if self.rate_limit:
                    opts["ratelimit"] = self._parse_rate_limit(self.rate_limit)

                with yt_dlp.YoutubeDL(opts) as ydl:
                    self.signals.status.emit(self.item_id, "Downloading")
                    info = ydl.extract_info(self.url, download=True) or {}

                final_path = self._resolve_final_filepath(info)
                info["__final_filepath"] = final_path

                self.signals.finished.emit(self.item_id, info)
                return

            except Exception as exc:
                self.signals.log.emit(traceback.format_exc())

                attempts += 1
                if attempts > self.retries:
                    self.signals.failed.emit(self.item_id, str(exc))
                    return

                wait_s = self.retry_backoff_seconds * attempts
                self.signals.status.emit(self.item_id, f"Retrying in {wait_s}s")
                time.sleep(wait_s)

    @staticmethod
    def _parse_rate_limit(value: str):
        import re

        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*([KMG]?)(?:B)?(?:/s)?\s*",
            value,
            re.I,
        )
        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2).upper()
        mult = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[unit]
        return int(number * mult)
