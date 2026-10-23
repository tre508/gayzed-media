#!/usr/bin/env python3
"""
Desktop Media GUI
--------------
A Pop!_OS-friendly personal desktop downloader with:
- Full GUI (PySide6 / Qt Widgets)
- Paste links directly or import from file
- Bulk queueing
- Parallel downloads via QThreadPool
- Per-item progress, speed, ETA, and status
- Output folder picker
- Simple settings persisted in ~/.config/desktop-media-gui/settings.json

What this starter intentionally does NOT do:
- DRM bypass
- Anti-bot / Cloudflare circumvention
- Browser-extension style page instrumentation

Use it for media URLs or site URLs that yt-dlp already supports.

Install:
    sudo apt update
    sudo apt install -y ffmpeg python3-pip
    python3 -m pip install --user -U PySide6 "yt-dlp[default,curl-cffi]"

Run:
    python3 desktop_media_gui.py

Optional packaging:
    python3 -m pip install --user pyinstaller
    python3 -m PyInstaller --name DesktopMediaGUI --onefile --windowed desktop_media_gui.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    import yt_dlp
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "yt-dlp is not installed. Run: python3 -m pip install --user -U yt-dlp"
    ) from exc

APP_NAME = "Desktop Media GUI"
CONFIG_DIR = Path.home() / ".config" / "desktop-media-gui"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
DEFAULT_OUTPUT = str(Path.home() / "Videos" / "latest")

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


@dataclass
class QueueItem:
    id: str
    url: str
    status: str = "Queued"
    title: str = ""
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    error: str = ""
    row: int = -1


class DownloadSignals(QObject):
    status = Signal(str, str)
    meta = Signal(str, dict)
    progress = Signal(str, dict)
    finished = Signal(str)
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
        limit_rate: Optional[str],
        extra_args: Optional[List[str]] = None,
    ) -> None:
        super().__init__()
        self.item_id = item_id
        self.url = url
        self.output_dir = output_dir
        self.format_selector = format_selector
        self.write_subtitles = write_subtitles
        self.limit_rate = limit_rate
        self.extra_args = extra_args or []
        self.signals = DownloadSignals()
        self.setAutoDelete(True)

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        self.signals.progress.emit(self.item_id, d)

    @Slot()
    def run(self) -> None:
        try:
            self.signals.status.emit(self.item_id, "Starting")

            outtmpl = os.path.join(self.output_dir, "%(title).180B [%(id)s].%(ext)s")
            opts: Dict[str, Any] = {
                "outtmpl": outtmpl,
                "extractor_args": {"generic": {"impersonate": [""]}},
                "paths": {"home": self.output_dir},
                "format": self.format_selector,
                "ignoreerrors": False,
                "continuedl": True,
                "noprogress": True,
                "progress_hooks": [self._progress_hook],
                "writesubtitles": self.write_subtitles,
                "writeautomaticsub": False,
                "restrictfilenames": False,
                "nopart": False,
                "quiet": True,
                "no_warnings": True,
                "consoletitle": False,
                "retries": 3,
            }

            if self.limit_rate:
                opts["ratelimit"] = self._parse_rate_limit(self.limit_rate)

            # Conservative, safe defaults: do not attempt anti-bot bypass here.
            # Users can add benign yt-dlp args below if needed for ordinary supported sites.
            if self.extra_args:
                opts["compat_opts"] = []

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if info:
                    self.signals.meta.emit(self.item_id, info)
                self.signals.status.emit(self.item_id, "Downloading")
                ydl.download([self.url])

            self.signals.status.emit(self.item_id, "Completed")
            self.signals.finished.emit(self.item_id)
        except Exception as exc:
            self.signals.failed.emit(self.item_id, str(exc))
            self.signals.log.emit(traceback.format_exc())

    @staticmethod
    def _parse_rate_limit(value: str) -> Optional[int]:
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMG]?)(?:B)?(?:/s)?\s*", value, re.I)
        if not match:
            return None
        number = float(match.group(1))
        unit = match.group(2).upper()
        mult = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[unit]
        return int(number * mult)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1300, 800)

        self.items: Dict[str, QueueItem] = {}
        self.thread_pool = QThreadPool.globalInstance()
        self.settings = self.load_settings()

        self._build_ui()
        self._apply_settings()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)

        splitter = QSplitter(Qt.Orientation.Vertical)
        root_layout.addWidget(splitter)

        top = QWidget()
        top_layout = QGridLayout(top)
        splitter.addWidget(top)

        # Input area
        input_box = QGroupBox("Add links")
        input_layout = QVBoxLayout(input_box)

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "Paste one URL per line here, or paste mixed text and I will extract links from it."
        )
        self.url_input.setMinimumHeight(140)
        input_layout.addWidget(self.url_input)

        input_btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add to queue")
        self.import_btn = QPushButton("Import file")
        self.clear_input_btn = QPushButton("Clear input")
        input_btn_row.addWidget(self.add_btn)
        input_btn_row.addWidget(self.import_btn)
        input_btn_row.addWidget(self.clear_input_btn)
        input_btn_row.addStretch(1)
        input_layout.addLayout(input_btn_row)

        top_layout.addWidget(input_box, 0, 0, 1, 2)

        # Settings area
        settings_box = QGroupBox("Download settings")
        settings_form = QFormLayout(settings_box)

        out_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_browse_btn = QPushButton("Browse")
        out_row.addWidget(self.output_dir_edit)
        out_row.addWidget(self.output_browse_btn)
        settings_form.addRow("Output folder", out_row)

        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 16)
        self.parallel_spin.setValue(3)
        settings_form.addRow("Parallel downloads", self.parallel_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItems(
            [
                "bv*+ba/b",
                "bestvideo+bestaudio/best",
                "best",
                "worst",
                "ba/bestaudio",
            ]
        )
        settings_form.addRow("Format selector", self.format_combo)

        self.rate_limit_edit = QLineEdit()
        self.rate_limit_edit.setPlaceholderText("Optional, e.g. 5M or 750K")
        settings_form.addRow("Rate limit", self.rate_limit_edit)

        self.subs_check = QCheckBox("Write subtitles when available")
        settings_form.addRow("Extras", self.subs_check)

        top_layout.addWidget(settings_box, 0, 2)

        controls_box = QGroupBox("Queue controls")
        controls_layout = QVBoxLayout(controls_box)
        self.start_btn = QPushButton("Start queue")
        self.remove_selected_btn = QPushButton("Remove selected")
        self.clear_finished_btn = QPushButton("Clear completed/failed")
        self.stop_tip = QLabel("Tip: items already running are not cancelled in this starter. Remove queued items before starting if needed.")
        self.stop_tip.setWordWrap(True)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.remove_selected_btn)
        controls_layout.addWidget(self.clear_finished_btn)
        controls_layout.addWidget(self.stop_tip)
        controls_layout.addStretch(1)
        top_layout.addWidget(controls_box, 0, 3)

        # Queue table
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        splitter.addWidget(bottom)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Status", "Progress", "Title", "URL", "Speed", "ETA", "File", "Error"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

        bottom_layout.addWidget(self.table)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Event log")
        self.log_output.setMinimumHeight(150)
        bottom_layout.addWidget(self.log_output)

        splitter.setSizes([280, 520])

        self.add_btn.clicked.connect(self.add_urls_from_input)
        self.import_btn.clicked.connect(self.import_urls_from_file)
        self.clear_input_btn.clicked.connect(self.url_input.clear)
        self.output_browse_btn.clicked.connect(self.choose_output_dir)
        self.start_btn.clicked.connect(self.start_queue)
        self.remove_selected_btn.clicked.connect(self.remove_selected_rows)
        self.clear_finished_btn.clicked.connect(self.clear_finished_rows)

    def _apply_settings(self) -> None:
        self.output_dir_edit.setText(self.settings.get("output_dir", DEFAULT_OUTPUT))
        self.parallel_spin.setValue(int(self.settings.get("parallel", 3)))
        self.format_combo.setCurrentText(self.settings.get("format", "bv*+ba/b"))
        self.rate_limit_edit.setText(self.settings.get("rate_limit", ""))
        self.subs_check.setChecked(bool(self.settings.get("write_subtitles", False)))
        self.thread_pool.setMaxThreadCount(self.parallel_spin.value())
        self.parallel_spin.valueChanged.connect(self.thread_pool.setMaxThreadCount)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.save_settings()
        super().closeEvent(event)

    def load_settings(self) -> Dict[str, Any]:
        try:
            if SETTINGS_FILE.exists():
                return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "output_dir": DEFAULT_OUTPUT,
            "parallel": 3,
            "format": "bv*+ba/b",
            "rate_limit": "",
            "write_subtitles": False,
        }

    def save_settings(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "output_dir": self.output_dir_edit.text().strip() or DEFAULT_OUTPUT,
            "parallel": self.parallel_spin.value(),
            "format": self.format_combo.currentText(),
            "rate_limit": self.rate_limit_edit.text().strip(),
            "write_subtitles": self.subs_check.isChecked(),
        }
        SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @Slot()
    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_dir_edit.text() or DEFAULT_OUTPUT)
        if path:
            self.output_dir_edit.setText(path)

    def extract_urls(self, text: str) -> List[str]:
        matches = URL_RE.findall(text)
        seen = set()
        result = []
        for url in matches:
            if url not in seen:
                seen.add(url)
                result.append(url)
        return result

    @Slot()
    def add_urls_from_input(self) -> None:
        raw = self.url_input.toPlainText().strip()
        if not raw:
            QMessageBox.information(self, APP_NAME, "Paste at least one URL first.")
            return
        urls = self.extract_urls(raw)
        if not urls:
            QMessageBox.warning(self, APP_NAME, "I could not find any valid http/https URLs in the input.")
            return
        self.add_urls_to_queue(urls)
        self.url_input.clear()
        self.log(f"Added {len(urls)} item(s) to queue.")

    @Slot()
    def import_urls_from_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import URLs",
            str(Path.home()),
            "Text files (*.txt *.csv *.md);;All files (*)",
        )
        if not file_path:
            return
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            urls = self.extract_urls(content)
            if not urls:
                QMessageBox.warning(self, APP_NAME, "No valid URLs found in the selected file.")
                return
            self.add_urls_to_queue(urls)
            self.log(f"Imported {len(urls)} URL(s) from {file_path}.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Failed to import file:\n{exc}")

    def add_urls_to_queue(self, urls: List[str]) -> None:
        existing_urls = {item.url for item in self.items.values()}
        for url in urls:
            if url in existing_urls:
                continue
            item = QueueItem(id=str(uuid4()), url=url)
            row = self.table.rowCount()
            self.table.insertRow(row)
            item.row = row
            self.items[item.id] = item

            status_item = QTableWidgetItem(item.status)
            self.table.setItem(row, 0, status_item)

            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            self.table.setCellWidget(row, 1, progress_bar)

            self.table.setItem(row, 2, QTableWidgetItem(item.title))
            self.table.setItem(row, 3, QTableWidgetItem(item.url))
            self.table.setItem(row, 4, QTableWidgetItem(item.speed))
            self.table.setItem(row, 5, QTableWidgetItem(item.eta))
            self.table.setItem(row, 6, QTableWidgetItem(item.filename))
            self.table.setItem(row, 7, QTableWidgetItem(item.error))

    @Slot()
    def start_queue(self) -> None:
        output_dir = self.output_dir_edit.text().strip() or DEFAULT_OUTPUT
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self.thread_pool.setMaxThreadCount(self.parallel_spin.value())
        queued = [item for item in self.items.values() if item.status == "Queued"]
        if not queued:
            QMessageBox.information(self, APP_NAME, "There are no queued items to start.")
            return

        for item in queued:
            worker = DownloadWorker(
                item_id=item.id,
                url=item.url,
                output_dir=output_dir,
                format_selector=self.format_combo.currentText(),
                write_subtitles=self.subs_check.isChecked(),
                limit_rate=self.rate_limit_edit.text().strip() or None,
            )
            worker.signals.status.connect(self.on_worker_status)
            worker.signals.meta.connect(self.on_worker_meta)
            worker.signals.progress.connect(self.on_worker_progress)
            worker.signals.finished.connect(self.on_worker_finished)
            worker.signals.failed.connect(self.on_worker_failed)
            worker.signals.log.connect(self.log)
            self.thread_pool.start(worker)

        self.log(f"Started {len(queued)} queued download(s) with parallelism={self.parallel_spin.value()}.")

    @Slot(str, str)
    def on_worker_status(self, item_id: str, status: str) -> None:
        item = self.items.get(item_id)
        if not item:
            return
        item.status = status
        self._set_text(item.row, 0, status)

    @Slot(str, dict)
    def on_worker_meta(self, item_id: str, info: Dict[str, Any]) -> None:
        item = self.items.get(item_id)
        if not item:
            return
        title = info.get("title") or item.url
        item.title = str(title)
        self._set_text(item.row, 2, item.title)
        filename = info.get("_filename") or ""
        if filename:
            item.filename = str(filename)
            self._set_text(item.row, 6, item.filename)

    @Slot(str, dict)
    def on_worker_progress(self, item_id: str, data: Dict[str, Any]) -> None:
        item = self.items.get(item_id)
        if not item:
            return

        status = data.get("status", "")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            progress = int((downloaded / total) * 100) if total else 0
            speed = self._format_bytes_per_sec(data.get("speed"))
            eta = self._format_eta(data.get("eta"))
            filename = str(data.get("filename") or "")

            item.progress = progress
            item.speed = speed
            item.eta = eta
            if filename:
                item.filename = filename

            self._set_progress(item.row, progress)
            self._set_text(item.row, 4, speed)
            self._set_text(item.row, 5, eta)
            self._set_text(item.row, 6, item.filename)
            self._set_text(item.row, 0, "Downloading")
        elif status == "finished":
            self._set_progress(item.row, 100)
            self._set_text(item.row, 0, "Processing")

    @Slot(str)
    def on_worker_finished(self, item_id: str) -> None:
        item = self.items.get(item_id)
        if not item:
            return
        item.status = "Completed"
        item.progress = 100.0
        self._set_text(item.row, 0, "Completed")
        self._set_progress(item.row, 100)
        self.log(f"Completed: {item.url}")

    @Slot(str, str)
    def on_worker_failed(self, item_id: str, error: str) -> None:
        item = self.items.get(item_id)
        if not item:
            return
        item.status = "Failed"
        item.error = error
        self._set_text(item.row, 0, "Failed")
        self._set_text(item.row, 7, error)
        self.log(f"Failed: {item.url}\n{error}")

    @Slot()
    def remove_selected_rows(self) -> None:
        selected_rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}, reverse=True)
        if not selected_rows:
            return
        for row in selected_rows:
            item_id = self._find_item_id_by_row(row)
            if item_id:
                del self.items[item_id]
            self.table.removeRow(row)
        self._reindex_rows()
        self.log(f"Removed {len(selected_rows)} selected row(s).")

    @Slot()
    def clear_finished_rows(self) -> None:
        removable_rows = []
        for item in self.items.values():
            if item.status in {"Completed", "Failed"}:
                removable_rows.append(item.row)
        for row in sorted(removable_rows, reverse=True):
            item_id = self._find_item_id_by_row(row)
            if item_id:
                del self.items[item_id]
            self.table.removeRow(row)
        self._reindex_rows()
        self.log(f"Cleared {len(removable_rows)} completed/failed row(s).")

    def _find_item_id_by_row(self, row: int) -> Optional[str]:
        for item_id, item in self.items.items():
            if item.row == row:
                return item_id
        return None

    def _reindex_rows(self) -> None:
        for row in range(self.table.rowCount()):
            item_id = self._find_item_id_by_row(row)
            if item_id:
                self.items[item_id].row = row

    def _set_text(self, row: int, col: int, value: str) -> None:
        cell = self.table.item(row, col)
        if cell is None:
            cell = QTableWidgetItem()
            self.table.setItem(row, col, cell)
        cell.setText(value)
        cell.setToolTip(value)

    def _set_progress(self, row: int, value: int) -> None:
        widget = self.table.cellWidget(row, 1)
        if isinstance(widget, QProgressBar):
            widget.setValue(max(0, min(100, value)))

    def _format_bytes_per_sec(self, value: Any) -> str:
        if not value:
            return ""
        return f"{self._format_bytes(float(value))}/s"

    def _format_bytes(self, value: float) -> str:
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024
            idx += 1
        return f"{value:.1f} {units[idx]}"

    def _format_eta(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return ""
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours:d}:{mins:02d}:{secs:02d}"
        return f"{mins:d}:{secs:02d}"

    def log(self, message: str) -> None:
        self.log_output.append(message)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
