#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import urllib.request
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, QTimer, Qt, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from downloader import DownloadWorker
from models import QueueItem
from storage import SETTINGS_PATH, HistoryStore
from theme import get_stylesheet
from utils import (
    extract_urls,
    format_bps,
    format_eta,
    load_json,
    load_text_file,
    save_json,
    save_url_list,
)

APP_NAME = "Gayzed Media"
DEFAULT_OUTPUT = str(Path.home() / "Videos" / "latest")
ICON_NAME = "gayzed-media"
ICON_PATH = str(
    Path(__file__).resolve().parent.parent
    / "assets"
    / "icons"
    / "hicolor"
    / "128x128"
    / "apps"
    / f"{ICON_NAME}.png"
)
UBUNTU_THUMBNAIL_HELPER = Path(__file__).parent / "ubuntu_native_thumbnail_helper.py"


def _debug_report(hypothesis_id: str, location: str, msg: str, data: dict) -> None:
    _p = ".dbg/thumbnail-preview-bug.env"
    _u = "http://127.0.0.1:7777/event"
    _s = "thumbnail-preview-bug"
    _r = os.environ.get("GM_DEBUG_RUN_ID", "pre-fix")
    try:
        with open(_p, "r", encoding="utf-8") as f:
            for line in f.read().splitlines():
                if line.startswith("DEBUG_SERVER_URL="):
                    _u = line.split("=", 1)[1]
                elif line.startswith("DEBUG_SESSION_ID="):
                    _s = line.split("=", 1)[1]
                elif line.startswith("DEBUG_RUN_ID="):
                    _r = line.split("=", 1)[1]
        urllib.request.urlopen(
            urllib.request.Request(
                _u,
                data=json.dumps(
                    {
                        "sessionId": _s,
                        "runId": _r,
                        "hypothesisId": hypothesis_id,
                        "location": location,
                        "msg": msg,
                        "data": data,
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=0.3,
        ).read()
    except Exception:
        pass


class ThumbnailTaskSignals(QObject):
    ready = Signal(str, int, QImage)


class ThumbnailLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.file_path = ""
        self.open_callback = None

    def mousePressEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.open_callback is not None
            and self.file_path
            and self.pixmap() is not None
            and not self.pixmap().isNull()
        ):
            self.open_callback(self.file_path)
            event.accept()
            return
        super().mousePressEvent(event)


class ThumbnailTask(QRunnable):
    def __init__(self, file_path: str, size: int) -> None:
        super().__init__()
        self.file_path = file_path
        self.size = size
        self.signals = ThumbnailTaskSignals()

    def _thumbnail_text(self, image_path: Path) -> dict[str, str]:
        text_chunks: dict[str, str] = {}
        with image_path.open("rb") as fh:
            if fh.read(8) != b"\x89PNG\r\n\x1a\n":
                return text_chunks
            while True:
                header = fh.read(4)
                if not header:
                    break
                chunk_len = struct.unpack(">I", header)[0]
                chunk_type = fh.read(4)
                chunk_data = fh.read(chunk_len)
                fh.read(4)
                if chunk_type == b"tEXt" and b"\x00" in chunk_data:
                    key, value = chunk_data.split(b"\x00", 1)
                    text_chunks[key.decode("latin1")] = value.decode("latin1", "ignore")
                if chunk_type == b"IEND":
                    break
        return text_chunks

    def _linux_cached_thumbnail(self) -> QImage:
        if not sys.platform.startswith("linux"):
            return QImage()

        src = Path(self.file_path)
        if not src.exists():
            return QImage()

        uri_candidates = list(
            dict.fromkeys(
                [
                    bytes(QUrl.fromLocalFile(str(src)).toEncoded()).decode("utf-8"),
                    src.absolute().as_uri(),
                    src.resolve(strict=False).as_uri(),
                ]
            )
        )
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        thumbs_root = cache_root / "thumbnails"
        # #region debug-point A:thumbnail-cache-input
        _debug_report(
            "A",
            "app.py:114",
            "[DEBUG] strict thumbnail cache lookup started",
            {
                "file_path": str(src),
                "uri_candidates": uri_candidates,
                "thumbs_root": str(thumbs_root),
            },
        )
        # #endregion

        source_mtime = str(int(src.stat().st_mtime))
        for uri in uri_candidates:
            digest = hashlib.md5(uri.encode("utf-8")).hexdigest()
            for folder in ["xx-large", "x-large", "large", "normal"]:
                candidate = thumbs_root / folder / f"{digest}.png"
                # #region debug-point A:thumbnail-cache-candidate
                _debug_report(
                    "A",
                    "app.py:127",
                    "[DEBUG] strict thumbnail candidate checked",
                    {
                        "file_path": str(src),
                        "folder": folder,
                        "candidate": str(candidate),
                        "uri": uri,
                        "digest": digest,
                        "exists": candidate.exists(),
                    },
                )
                # #endregion
                if not candidate.exists():
                    continue
                try:
                    metadata = self._thumbnail_text(candidate)
                except Exception:
                    metadata = {}

                candidate_uri = metadata.get("Thumb::URI", "")
                candidate_mtime = metadata.get("Thumb::MTime", "")
                if candidate_uri and candidate_uri not in uri_candidates:
                    continue
                if candidate_mtime and candidate_mtime != source_mtime:
                    # #region debug-point B:thumbnail-cache-stale
                    _debug_report(
                        "B",
                        "app.py:141",
                        "[DEBUG] strict thumbnail candidate rejected by metadata mtime",
                        {
                            "file_path": str(src),
                            "candidate": str(candidate),
                            "candidate_uri": candidate_uri,
                            "candidate_mtime": candidate_mtime,
                            "source_mtime": source_mtime,
                        },
                    )
                    # #endregion
                    continue
                img = QImage(str(candidate))
                if not img.isNull():
                    # #region debug-point A:thumbnail-cache-hit
                    _debug_report(
                        "A",
                        "app.py:155",
                        "[DEBUG] strict thumbnail cache hit",
                        {
                            "file_path": str(src),
                            "candidate": str(candidate),
                            "uri": uri,
                            "width": img.width(),
                            "height": img.height(),
                        },
                    )
                    # #endregion
                    return img

        # #region debug-point A:thumbnail-cache-miss
        _debug_report(
            "A",
            "app.py:168",
            "[DEBUG] strict thumbnail cache miss",
            {"file_path": str(src)},
        )
        # #endregion

        helper_image = self._linux_native_thumbnail_via_helper(src)
        if not helper_image.isNull():
            return helper_image
        return QImage()

    def _linux_native_thumbnail_via_helper(self, src: Path) -> QImage:
        if not UBUNTU_THUMBNAIL_HELPER.exists():
            return QImage()

        command = ["python3", str(UBUNTU_THUMBNAIL_HELPER), str(src)]
        # #region debug-point A:thumbnail-helper-start
        _debug_report(
            "A",
            "app.py:177",
            "[DEBUG] strict thumbnail helper invoked",
            {"file_path": str(src), "command": command},
        )
        # #endregion
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except Exception as exc:
            _debug_report(
                "A",
                "app.py:191",
                "[DEBUG] strict thumbnail helper failed to run",
                {"file_path": str(src), "error": str(exc)},
            )
            return QImage()

        thumb_path = result.stdout.strip()
        _debug_report(
            "A",
            "app.py:200",
            "[DEBUG] strict thumbnail helper completed",
            {
                "file_path": str(src),
                "returncode": result.returncode,
                "stdout": thumb_path,
                "stderr": result.stderr.strip()[:500],
            },
        )
        if result.returncode != 0 or not thumb_path:
            return QImage()

        candidate = Path(thumb_path)
        if not candidate.exists():
            return QImage()

        image = QImage(str(candidate))
        if image.isNull():
            return QImage()

        _debug_report(
            "A",
            "app.py:220",
            "[DEBUG] strict thumbnail helper produced image",
            {
                "file_path": str(src),
                "candidate": str(candidate),
                "width": image.width(),
                "height": image.height(),
            },
        )
        return image

    def run(self) -> None:
        try:
            image = self._linux_cached_thumbnail()
        except Exception:
            image = QImage()
        if not image.isNull():
            image = image.scaled(
                self.size,
                self.size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.signals.ready.emit(self.file_path, self.size, image)


class MainWindow(QMainWindow):
    QUEUE_COL_STATUS = 0
    QUEUE_COL_PROGRESS = 1
    QUEUE_COL_RETRIES = 2
    QUEUE_COL_TITLE = 3
    QUEUE_COL_URL = 4
    QUEUE_COL_SPEED = 5
    QUEUE_COL_ETA = 6
    QUEUE_COL_PREVIEW = 7
    QUEUE_COL_FILE = 8
    QUEUE_COL_ERROR = 9
    THUMBNAIL_RETRY_LIMIT = 12
    THUMBNAIL_RETRY_MS = 1500

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        icon = QIcon.fromTheme(ICON_NAME)
        if icon.isNull():
            icon = QIcon(ICON_PATH)
        self.setWindowIcon(icon)
        self.resize(1550, 930)

        self.items: dict[str, QueueItem] = {}
        self.thread_pool = QThreadPool.globalInstance()
        self.thumb_pool = QThreadPool()
        self.thumb_pool.setMaxThreadCount(2)
        self._thumbnail_cache: dict[str, QPixmap] = {}
        self._thumbnail_waiters: dict[str, list[ThumbnailLabel]] = {}
        self._thumbnail_inflight: set[str] = set()
        self._thumbnail_retry_attempts: dict[str, int] = {}
        self._thumbnail_tasks: dict[str, ThumbnailTask] = {}
        self.history = HistoryStore()

        self.defaults = {
            "output_dir": DEFAULT_OUTPUT,
            "parallel": 3,
            "format": "bv*+ba/b",
            "rate_limit": "",
            "write_subtitles": False,
            "retry_count": 2,
            "retry_backoff": 3,
            "cookie_browser": "none",
            "headers": "",
            "prompt_rename_after_download": False,
        }
        self.settings = {**self.defaults, **load_json(SETTINGS_PATH, self.defaults)}

        self._build_ui()
        self._apply_settings()
        self.refresh_history_table()

    def _thumbnail_size(self) -> int:
        screen = QApplication.primaryScreen()
        dpi = float(screen.logicalDotsPerInch()) if screen else 96.0
        scale = dpi / 96.0
        size = int(128 * scale)
        return max(96, min(160, size))

    def _init_thumbnail_label(self, label: ThumbnailLabel) -> None:
        size = self._thumbnail_size()
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setScaledContents(False)
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        label.setStyleSheet("border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.03);")
        label.open_callback = self.open_expanded_thumbnail

    def _thumbnail_key(self, file_path: str) -> str:
        size = self._thumbnail_size()
        return f"{file_path}|{size}"

    def _start_thumbnail_task(self, file_path: str) -> None:
        key = self._thumbnail_key(file_path)
        if key in self._thumbnail_inflight:
            return
        self._thumbnail_inflight.add(key)
        task = ThumbnailTask(file_path, self._thumbnail_size())
        self._thumbnail_tasks[key] = task
        task.signals.ready.connect(self.on_thumbnail_ready)
        self.thumb_pool.start(task)

    def request_thumbnail(self, file_path: str, label: ThumbnailLabel) -> None:
        size = self._thumbnail_size()
        label.setFixedSize(size, size)
        label.file_path = file_path
        key = self._thumbnail_key(file_path)
        # #region debug-point C:thumbnail-request
        _debug_report(
            "C",
            "app.py:242",
            "[DEBUG] thumbnail requested",
            {
                "file_path": file_path,
                "size": size,
                "key": key,
                "cache_hit": key in self._thumbnail_cache,
                "label_size": [label.width(), label.height()],
            },
        )
        # #endregion
        if key in self._thumbnail_cache:
            cached = self._thumbnail_cache[key]
            if not cached.isNull():
                label.setPixmap(self._thumbnail_cache[key])
            return

        waiters = self._thumbnail_waiters.setdefault(key, [])
        if label not in waiters:
            waiters.append(label)
        self._start_thumbnail_task(file_path)

    @Slot(str, int, QImage)
    def on_thumbnail_ready(self, file_path: str, size: int, image: QImage) -> None:
        key = f"{file_path}|{size}"
        self._thumbnail_inflight.discard(key)
        self._thumbnail_tasks.pop(key, None)
        pixmap = QPixmap()
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
        # #region debug-point C:thumbnail-ready
        _debug_report(
            "C",
            "app.py:274",
            "[DEBUG] thumbnail ready for preview assignment",
            {
                "file_path": file_path,
                "size": size,
                "image_null": image.isNull(),
                "pixmap_null": pixmap.isNull(),
                "waiter_count": len(self._thumbnail_waiters.get(key, [])),
            },
        )
        # #endregion

        if not pixmap.isNull():
            self._thumbnail_cache[key] = pixmap
            self._thumbnail_retry_attempts.pop(key, None)
            labels = self._thumbnail_waiters.pop(key, [])
            for label in labels:
                label.setPixmap(pixmap)
            return

        attempts = self._thumbnail_retry_attempts.get(key, 0) + 1
        self._thumbnail_retry_attempts[key] = attempts
        if key not in self._thumbnail_waiters:
            return
        if attempts >= self.THUMBNAIL_RETRY_LIMIT:
            self._thumbnail_waiters.pop(key, None)
            return
        QTimer.singleShot(self.THUMBNAIL_RETRY_MS, lambda fp=file_path: self._start_thumbnail_task(fp))

    def open_expanded_thumbnail(self, file_path: str) -> None:
        image = ThumbnailTask(file_path, self._thumbnail_size())._linux_cached_thumbnail()
        if image.isNull():
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(Path(file_path).name)
        layout = QVBoxLayout(dialog)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumSize(480, 320)
        scaled = image.scaled(
            720,
            720,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        preview.setPixmap(QPixmap.fromImage(scaled))
        layout.addWidget(preview)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.resize(max(520, scaled.width() + 40), max(420, scaled.height() + 80))
        dialog.exec()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        queue_tab = QWidget()
        queue_layout = QVBoxLayout(queue_tab)
        self.tabs.addTab(queue_tab, "Queue")

        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        self.tabs.addTab(history_tab, "History")

        splitter = QSplitter(Qt.Orientation.Vertical)
        queue_layout.addWidget(splitter)

        top = QWidget()
        top_layout = QGridLayout(top)
        splitter.addWidget(top)

        add_box = QGroupBox("Add links")
        add_layout = QVBoxLayout(add_box)

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "Paste one URL per line, or paste mixed text and extract URLs."
        )
        add_layout.addWidget(self.url_input)

        add_btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add to queue")
        self.import_btn = QPushButton("Import file")
        self.save_urls_btn = QPushButton("Save queue URLs")
        self.clear_input_btn = QPushButton("Clear input")
        add_btn_row.addWidget(self.add_btn)
        add_btn_row.addWidget(self.import_btn)
        add_btn_row.addWidget(self.save_urls_btn)
        add_btn_row.addWidget(self.clear_input_btn)
        add_btn_row.addStretch(1)
        add_layout.addLayout(add_btn_row)

        top_layout.addWidget(add_box, 0, 0, 1, 2)

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
        settings_form.addRow("Parallel downloads", self.parallel_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItems(
            ["bv*+ba/b", "bestvideo+bestaudio/best", "best", "ba/bestaudio"]
        )
        settings_form.addRow("Format selector", self.format_combo)

        self.rate_limit_edit = QLineEdit()
        self.rate_limit_edit.setPlaceholderText("Optional, e.g. 5M")
        settings_form.addRow("Rate limit", self.rate_limit_edit)

        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        settings_form.addRow("Retries", self.retry_spin)

        self.backoff_spin = QSpinBox()
        self.backoff_spin.setRange(1, 60)
        settings_form.addRow("Backoff seconds", self.backoff_spin)

        self.subs_check = QCheckBox("Write subtitles")
        self.prompt_rename_check = QCheckBox("Prompt rename after download")
        settings_form.addRow("Extras", self.subs_check)
        settings_form.addRow("", self.prompt_rename_check)

        top_layout.addWidget(settings_box, 0, 2)

        auth_box = QGroupBox("Cookies and headers")
        auth_form = QFormLayout(auth_box)

        self.cookie_browser_combo = QComboBox()
        self.cookie_browser_combo.addItems(["none", "firefox", "chrome", "chromium"])
        auth_form.addRow("Cookies from browser", self.cookie_browser_combo)

        self.headers_edit = QTextEdit()
        self.headers_edit.setPlaceholderText(
            "Optional headers, one per line. Example:\n"
            "Referer: https://example.com\n"
            "User-Agent: Mozilla/5.0 ..."
        )
        self.headers_edit.setMinimumHeight(120)
        auth_form.addRow("Custom headers", self.headers_edit)

        top_layout.addWidget(auth_box, 0, 3)

        controls_box = QGroupBox("Queue controls")
        controls_layout = QVBoxLayout(controls_box)

        self.start_btn = QPushButton("Start queue")
        self.rename_selected_btn = QPushButton("Rename selected")
        self.cancel_selected_btn = QPushButton("Cancel selected")
        self.remove_selected_btn = QPushButton("Remove selected")
        self.clear_finished_btn = QPushButton("Clear completed/failed")

        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.rename_selected_btn)
        controls_layout.addWidget(self.cancel_selected_btn)
        controls_layout.addWidget(self.remove_selected_btn)
        controls_layout.addWidget(self.clear_finished_btn)
        controls_layout.addStretch(1)

        top_layout.addWidget(controls_box, 0, 4)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        splitter.addWidget(bottom)

        self.queue_table = QTableWidget(0, 10)
        self.queue_table.setHorizontalHeaderLabels(
            [
                "Status",
                "Progress",
                "Retries",
                "Title",
                "URL",
                "Speed",
                "ETA",
                "Preview",
                "File",
                "Error",
            ]
        )
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.queue_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.verticalHeader().setVisible(False)

        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.QUEUE_COL_PREVIEW, QHeaderView.ResizeMode.ResizeToContents)
        for col in [self.QUEUE_COL_TITLE, self.QUEUE_COL_URL, self.QUEUE_COL_FILE, self.QUEUE_COL_ERROR]:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        bottom_layout.addWidget(self.queue_table)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        self.log_output.setPlaceholderText("Event log")
        bottom_layout.addWidget(self.log_output)

        splitter.setSizes([340, 540])

        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(
            ["When", "Status", "Title", "URL", "Preview", "Output", "Error"]
        )
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)

        h_header = self.history_table.horizontalHeader()
        h_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        for col in range(7):
            if col == 4:
                continue
            h_header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        history_layout.addWidget(self.history_table)

        self.add_btn.clicked.connect(self.add_urls_from_input)
        self.import_btn.clicked.connect(self.import_urls_file)
        self.save_urls_btn.clicked.connect(self.save_current_queue_urls)
        self.clear_input_btn.clicked.connect(self.url_input.clear)
        self.output_browse_btn.clicked.connect(self.choose_output_dir)
        self.start_btn.clicked.connect(self.start_queue)
        self.rename_selected_btn.clicked.connect(self.rename_selected)
        self.cancel_selected_btn.clicked.connect(self.cancel_selected)
        self.remove_selected_btn.clicked.connect(self.remove_selected)
        self.clear_finished_btn.clicked.connect(self.clear_finished)

    def _apply_settings(self) -> None:
        output_dir = self.settings.get("output_dir", DEFAULT_OUTPUT)
        self.output_dir_edit.setText(output_dir)
        # Warn if the saved output folder is not accessible (e.g. external
        # drive not mounted) so the user knows downloads won't go there yet.
        output_path = Path(output_dir)
        if output_dir and output_dir != DEFAULT_OUTPUT and not output_path.exists():
            self.log(
                f"Saved output folder not found (drive may be unmounted): {output_dir}"
            )
        self.parallel_spin.setValue(int(self.settings.get("parallel", 3)))
        self.format_combo.setCurrentText(self.settings.get("format", "bv*+ba/b"))
        self.rate_limit_edit.setText(self.settings.get("rate_limit", ""))
        self.subs_check.setChecked(bool(self.settings.get("write_subtitles", False)))
        self.prompt_rename_check.setChecked(
            bool(self.settings.get("prompt_rename_after_download", False))
        )
        self.retry_spin.setValue(int(self.settings.get("retry_count", 2)))
        self.backoff_spin.setValue(int(self.settings.get("retry_backoff", 3)))
        self.cookie_browser_combo.setCurrentText(self.settings.get("cookie_browser", "none"))
        self.headers_edit.setPlainText(self.settings.get("headers", ""))

        self.thread_pool.setMaxThreadCount(self.parallel_spin.value())
        self.parallel_spin.valueChanged.connect(self.thread_pool.setMaxThreadCount)

    def closeEvent(self, event) -> None:
        self.save_settings()
        super().closeEvent(event)

    def save_settings(self) -> None:
        payload = {
            "output_dir": self.output_dir_edit.text().strip() or DEFAULT_OUTPUT,
            "parallel": self.parallel_spin.value(),
            "format": self.format_combo.currentText(),
            "rate_limit": self.rate_limit_edit.text().strip(),
            "write_subtitles": self.subs_check.isChecked(),
            "prompt_rename_after_download": self.prompt_rename_check.isChecked(),
            "retry_count": self.retry_spin.value(),
            "retry_backoff": self.backoff_spin.value(),
            "cookie_browser": self.cookie_browser_combo.currentText(),
            "headers": self.headers_edit.toPlainText(),
        }
        save_json(SETTINGS_PATH, payload)

    def log(self, text: str) -> None:
        self.log_output.append(text)

    def parse_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        for line in self.headers_edit.toPlainText().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()
        return headers

    def choose_output_dir(self) -> None:
        # Open at root so mounted external drives (/media, /mnt, /run/media)
        # are immediately visible instead of starting deep in the home folder.
        start_dir = "/" if not self.output_dir_edit.text() else self.output_dir_edit.text()
        path = QFileDialog.getExistingDirectory(
            self,
            "Choose output folder",
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if path:
            self.output_dir_edit.setText(path)

    def sanitize_filename(self, value: str) -> str:
        value = value.strip()
        value = value.replace("/", " ").replace("\\", " ")
        value = re.sub(r'[:*?"<>|]+', "", value)
        value = re.sub(r"\s+", " ", value)
        value = value.strip(" .")
        return value or "untitled"

    def add_urls_to_queue(self, urls: list[str]) -> None:
        existing = {item.url for item in self.items.values()}
        for url in urls:
            if url in existing:
                continue

            item = QueueItem(id=str(uuid4()), url=url)
            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)
            item.row = row
            self.items[item.id] = item
            existing.add(url)

            self.queue_table.setItem(row, 0, QTableWidgetItem(item.status))

            prog = QProgressBar()
            prog.setRange(0, 100)
            self.queue_table.setCellWidget(row, 1, prog)

            self.queue_table.setItem(row, 2, QTableWidgetItem(str(item.retries)))
            self.queue_table.setItem(row, 3, QTableWidgetItem(item.title))
            self.queue_table.setItem(row, 4, QTableWidgetItem(item.url))
            self.queue_table.setItem(row, 5, QTableWidgetItem(item.speed))
            self.queue_table.setItem(row, 6, QTableWidgetItem(item.eta))

            preview = ThumbnailLabel()
            self._init_thumbnail_label(preview)
            self.queue_table.setCellWidget(row, self.QUEUE_COL_PREVIEW, preview)

            self.queue_table.setItem(row, self.QUEUE_COL_FILE, QTableWidgetItem(item.filename))
            self.queue_table.setItem(row, self.QUEUE_COL_ERROR, QTableWidgetItem(item.error))
            self.queue_table.setRowHeight(row, self._thumbnail_size() + 8)

    def add_urls_from_input(self) -> None:
        raw = self.url_input.toPlainText().strip()
        if not raw:
            QMessageBox.information(self, APP_NAME, "Paste at least one URL first.")
            return

        urls = extract_urls(raw)
        if not urls:
            QMessageBox.warning(self, APP_NAME, "No valid URLs found.")
            return

        self.add_urls_to_queue(urls)
        self.url_input.clear()
        self.log(f"Added {len(urls)} URL(s) to queue.")

    def import_urls_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import URL file",
            str(Path.home()),
            "Text files (*.txt *.csv *.md);;All files (*)",
        )
        if not path:
            return

        urls = extract_urls(load_text_file(path))
        if not urls:
            QMessageBox.warning(self, APP_NAME, "No valid URLs found in that file.")
            return

        self.add_urls_to_queue(urls)
        self.log(f"Imported {len(urls)} URL(s) from {path}.")

    def save_current_queue_urls(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save queue URLs",
            str(Path.home() / "urls.txt"),
            "Text files (*.txt)",
        )
        if not path:
            return

        urls: list[str] = []
        for row in range(self.queue_table.rowCount()):
            cell = self.queue_table.item(row, 4)
            if cell:
                urls.append(cell.text())

        save_url_list(path, urls)
        self.log(f"Saved {len(urls)} queue URL(s) to {path}.")

    def is_cancelled(self, item_id: str) -> bool:
        item = self.items.get(item_id)
        return bool(item and item.cancelled)

    def prompt_rename_item(self, item: QueueItem) -> None:
        if item.status != "Completed" or not item.filename:
            return

        current_path = Path(item.filename)
        if not current_path.exists():
            return

        suggested = self.sanitize_filename(item.title or current_path.stem)

        dialog = QDialog(self)
        dialog.setWindowTitle("Rename downloaded file")
        dialog_layout = QVBoxLayout(dialog)

        row = QHBoxLayout()
        thumb = ThumbnailLabel()
        self._init_thumbnail_label(thumb)
        row.addWidget(thumb)

        form = QVBoxLayout()
        name_label = QLabel(f"File:\n{current_path.name}\n\nLeave off the extension:")
        edit = QLineEdit(suggested)
        form.addWidget(name_label)
        form.addWidget(edit)
        row.addLayout(form, 1)

        dialog_layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)

        self.request_thumbnail(str(current_path), thumb)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_stem = self.sanitize_filename(edit.text())
        if not new_stem:
            return

        new_path = current_path.with_name(new_stem + current_path.suffix)
        if new_path == current_path:
            return

        if new_path.exists():
            QMessageBox.warning(self, APP_NAME, "A file with that name already exists.")
            return

        try:
            current_path.rename(new_path)

            item.filename = str(new_path)
            item.title = new_stem

            self.set_text(item.row, 3, item.title)
            self.set_text(item.row, self.QUEUE_COL_FILE, item.filename)
            self.log(f"Renamed file to: {new_path.name}")

        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Rename failed:\n{exc}")

    def start_queue(self) -> None:
        output_dir = self.output_dir_edit.text().strip() or DEFAULT_OUTPUT
        output_dir = str(Path(output_dir).expanduser())
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.log(f"Output folder unavailable: {output_dir}\n{exc}")
            QMessageBox.warning(
                self,
                APP_NAME,
                "The configured output folder is unavailable.\n\n"
                f"{output_dir}\n\n"
                "Please connect/mount the drive or choose a different folder, then try again.",
            )
            self.output_dir_edit.setText(output_dir)
            self.output_dir_edit.setFocus()
            self.output_dir_edit.selectAll()
            return
        queued = [item for item in self.items.values() if item.status == "Queued"]
        if not queued:
            QMessageBox.information(self, APP_NAME, "No queued items.")
            return

        for item in queued:
            worker = DownloadWorker(
                item_id=item.id,
                url=item.url,
                output_dir=output_dir,
                format_selector=self.format_combo.currentText(),
                write_subtitles=self.subs_check.isChecked(),
                rate_limit=self.rate_limit_edit.text().strip() or None,
                retries=self.retry_spin.value(),
                retry_backoff_seconds=self.backoff_spin.value(),
                cookie_browser=self.cookie_browser_combo.currentText(),
                custom_headers=self.parse_headers(),
                cancel_check=self.is_cancelled,
            )
            worker.signals.status.connect(self.on_status)
            worker.signals.meta.connect(self.on_meta)
            worker.signals.progress.connect(self.on_progress)
            worker.signals.finished.connect(self.on_finished)
            worker.signals.failed.connect(self.on_failed)
            worker.signals.log.connect(self.log)
            self.thread_pool.start(worker)

        self.log(f"Started {len(queued)} queued item(s).")

    def rename_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.queue_table.selectionModel().selectedRows()})
        if not rows:
            QMessageBox.information(self, APP_NAME, "Select one completed download first.")
            return

        if len(rows) > 1:
            QMessageBox.information(self, APP_NAME, "Select only one row to rename.")
            return

        item = self.item_by_row(rows[0])
        if not item or item.status != "Completed" or not item.filename:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Only completed downloads with a saved file can be renamed.",
            )
            return

        self.prompt_rename_item(item)

    def cancel_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.queue_table.selectionModel().selectedRows()})
        for row in rows:
            item = self.item_by_row(row)
            if item and item.status in {"Queued", "Starting", "Downloading"}:
                item.cancelled = True
                item.status = "Cancelling"
                self.set_text(row, 0, "Cancelling")

        self.log(f"Marked {len(rows)} selected item(s) for cancellation.")

    def remove_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.queue_table.selectionModel().selectedRows()},
            reverse=True,
        )
        for row in rows:
            item = self.item_by_row(row)
            if item and item.status in {"Downloading", "Starting"}:
                item.cancelled = True
            if item:
                del self.items[item.id]
            self.queue_table.removeRow(row)

        self.reindex_rows()

    def clear_finished(self) -> None:
        rows = [
            item.row
            for item in self.items.values()
            if item.status in {"Completed", "Failed", "Cancelled"}
        ]
        for row in sorted(rows, reverse=True):
            item = self.item_by_row(row)
            if item:
                del self.items[item.id]
            self.queue_table.removeRow(row)

        self.reindex_rows()

    def item_by_row(self, row: int) -> QueueItem | None:
        for item in self.items.values():
            if item.row == row:
                return item
        return None

    def reindex_rows(self) -> None:
        url_to_item = {item.url: item for item in self.items.values()}
        for row in range(self.queue_table.rowCount()):
            url_cell = self.queue_table.item(row, 4)
            if not url_cell:
                continue
            item = url_to_item.get(url_cell.text())
            if item:
                item.row = row

    def set_text(self, row: int, col: int, value) -> None:
        cell = self.queue_table.item(row, col)
        if cell is None:
            cell = QTableWidgetItem()
            self.queue_table.setItem(row, col, cell)
        cell.setText(str(value))
        cell.setToolTip(str(value))

    def set_progress(self, row: int, value: int) -> None:
        widget = self.queue_table.cellWidget(row, 1)
        if isinstance(widget, QProgressBar):
            widget.setValue(max(0, min(100, int(value))))

    @Slot(str, str)
    def on_status(self, item_id: str, status: str) -> None:
        item = self.items.get(item_id)
        if not item:
            return
        item.status = status
        self.set_text(item.row, 0, status)

    @Slot(str, dict)
    def on_meta(self, item_id: str, info: dict) -> None:
        item = self.items.get(item_id)
        if not item:
            return
        title = str(info.get("title") or item.title or "")
        item.title = title
        self.set_text(item.row, 3, item.title)

    @Slot(str, dict)
    def on_progress(self, item_id: str, data: dict) -> None:
        item = self.items.get(item_id)
        if not item:
            return

        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            progress = int((downloaded / total) * 100) if total else 0

            item.progress = progress
            item.speed = format_bps(data.get("speed"))
            item.eta = format_eta(data.get("eta"))
            item.filename = str(data.get("filename") or item.filename)

            self.set_text(item.row, 0, "Downloading")
            self.set_progress(item.row, progress)
            self.set_text(item.row, 5, item.speed)
            self.set_text(item.row, 6, item.eta)
            self.set_text(item.row, self.QUEUE_COL_FILE, item.filename)

        elif data.get("status") == "finished":
            self.set_progress(item.row, 100)
            self.set_text(item.row, 0, "Processing")

    @Slot(str, dict)
    def on_finished(self, item_id: str, info: dict) -> None:
        item = self.items.get(item_id)
        if not item:
            return

        item.status = "Completed"

        final_path = str(info.get("__final_filepath") or "")
        title = str(info.get("title") or item.title or "")

        if final_path:
            item.filename = final_path
        if title:
            item.title = title

        self.set_text(item.row, 0, "Completed")
        self.set_progress(item.row, 100)
        self.set_text(item.row, 3, item.title)
        self.set_text(item.row, self.QUEUE_COL_FILE, item.filename)
        # #region debug-point E:completed-item-preview-request
        _debug_report(
            "E",
            "app.py:466",
            "[DEBUG] completed item requesting queue preview",
            {
                "item_id": item.id,
                "row": item.row,
                "filename": item.filename,
                "title": item.title,
            },
        )
        # #endregion

        widget = self.queue_table.cellWidget(item.row, self.QUEUE_COL_PREVIEW)
        if isinstance(widget, ThumbnailLabel) and item.filename:
            self.request_thumbnail(item.filename, widget)

        if self.prompt_rename_check.isChecked():
            self.prompt_rename_item(item)

        self.history.add_row(item.url, item.title, "Completed", item.filename, "")
        self.refresh_history_table()
        self.log(f"Completed: {item.url}")

    @Slot(str, str)
    def on_failed(self, item_id: str, error: str) -> None:
        item = self.items.get(item_id)
        if not item:
            return

        final_status = "Cancelled" if item.cancelled or error == "Cancelled" else "Failed"
        item.status = final_status
        item.error = error

        self.set_text(item.row, 0, final_status)
        self.set_text(item.row, self.QUEUE_COL_ERROR, error)

        self.history.add_row(item.url, item.title, final_status, item.filename, error)
        self.refresh_history_table()
        self.log(f"{final_status}: {item.url}\n{error}")

    def refresh_history_table(self) -> None:
        rows = self.history.list_rows()
        self.history_table.setRowCount(0)

        for record in rows:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            created_at, status, title, url, output_path, error = record

            self.history_table.setItem(row, 0, QTableWidgetItem(str(created_at or "")))
            self.history_table.setItem(row, 1, QTableWidgetItem(str(status or "")))
            self.history_table.setItem(row, 2, QTableWidgetItem(str(title or "")))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(url or "")))

            preview = ThumbnailLabel()
            self._init_thumbnail_label(preview)
            self.history_table.setCellWidget(row, 4, preview)
            self.history_table.setRowHeight(row, self._thumbnail_size() + 8)

            out_text = str(output_path or "")
            self.history_table.setItem(row, 5, QTableWidgetItem(out_text))
            self.history_table.setItem(row, 6, QTableWidgetItem(str(error or "")))

            if str(status) == "Completed" and out_text:
                # #region debug-point E:history-preview-request
                _debug_report(
                    "E",
                    "app.py:510",
                    "[DEBUG] history row requesting preview",
                    {
                        "row": row,
                        "output_path": out_text,
                        "status": str(status),
                    },
                )
                # #endregion
                self.request_thumbnail(out_text, preview)


def main() -> None:
    app = QApplication(sys.argv)
    # Application/WM identity must match the installed desktop entry
    # (packaging/gayzed-media.desktop: StartupWMClass / Icon).
    app.setApplicationName(ICON_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setDesktopFileName("gayzed-media")
    icon = QIcon.fromTheme(ICON_NAME)
    if icon.isNull():
        icon = QIcon(ICON_PATH)
    app.setWindowIcon(icon)
    app.setStyleSheet(get_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
