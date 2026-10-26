"""PySide6 premium-dark UI. Widgets only talk to workers via signals/slots."""
from __future__ import annotations

import os
from typing import List, Optional

from PySide6.QtCore import Qt, QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog,
                               QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMenuBar, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton,
                               QScrollArea, QSplitter, QVBoxLayout, QWidget)

import core
from core import (ACCEL_AUTO, ACCEL_AMD, ACCEL_APPLE, ACCEL_CPU_FAST, ACCEL_CPU_STD,
                  ACCEL_HYBRID, ACCEL_INTEL, ACCEL_NVIDIA, MODE_FULL, MODE_INSTANT,
                  MODE_STRICT, HardwareInfo, MediaInfo, PlanError)
from workers import CombineWorker, DetectWorker, ProbeWorker

BG, CARD, CARD2 = "#14161a", "#1e2126", "#23272e"
BORDER, ACCENT, ACCENT_H = "#313640", "#4da3ff", "#6fb6ff"
TEXT, MUTED = "#e8eaf0", "#9aa3b2"
SUCCESS, WARN, ERROR = "#3ddc84", "#ffb454", "#ff6b6b"

STYLESHEET = f"""
QWidget {{ background:{BG}; color:{TEXT};
    font-family:"Segoe UI Variable Text","Segoe UI",sans-serif; font-size:13px; }}
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {{ background:{BG}; }}
QFrame#Card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:10px; }}
QFrame#ConsolePanel {{ background:{CARD}; border:1px solid {BORDER}; border-radius:10px; }}
QLabel#CardTitle {{ color:{ACCENT}; font-size:11px; font-weight:700;
    letter-spacing:1.2px; background:transparent; }}
QLabel#Muted {{ color:{MUTED}; font-size:11px; background:transparent; }}
QLabel#Title {{ font-size:24px; font-weight:800; background:transparent; }}
QLabel#Subtitle {{ color:{MUTED}; background:transparent; }}
QLabel {{ background:transparent; }}
QLineEdit {{ background:#121417; border:1px solid {BORDER}; border-radius:6px;
    padding:7px 10px; selection-background-color:{ACCENT}; }}
QLineEdit:focus {{ border-color:{ACCENT}; }}
QComboBox {{ background:#121417; border:1px solid {BORDER}; border-radius:6px;
    padding:6px 10px; }}
QComboBox:focus {{ border-color:{ACCENT}; }}
QComboBox::drop-down {{ border:none; width:26px; }}
QComboBox::down-arrow {{ border-left:4px solid transparent;
    border-right:4px solid transparent; border-top:6px solid {MUTED}; margin-right:9px; }}
QComboBox QAbstractItemView {{ background:{CARD2}; border:1px solid {BORDER};
    color:{TEXT}; selection-background-color:{ACCENT};
    selection-color:#081018; outline:none; padding:4px; }}
QPushButton {{ background:{CARD2}; color:{TEXT}; border:1px solid {BORDER};
    border-radius:7px; padding:8px 18px; font-weight:600; }}
QPushButton:hover {{ background:#2c313a; }}
QPushButton:pressed {{ background:#343a45; }}
QPushButton:disabled {{ background:#262a31; color:#7d8590; }}
QProgressBar {{ background:{CARD2}; border:none; border-radius:5px; height:10px;
    text-align:center; color:transparent; }}
QProgressBar::chunk {{ background:{ACCENT}; border-radius:5px; }}
QPlainTextEdit#Console {{ background:#101216; color:#b7c0cf; border:1px solid {BORDER};
    border-radius:8px; font-family:Consolas,"Cascadia Mono",monospace; font-size:12px; }}
QCheckBox {{ spacing:8px; }}
QCheckBox::indicator {{ width:16px; height:16px; border-radius:4px;
    border:1px solid {BORDER}; background:#121417; }}
QCheckBox::indicator:checked {{ background:{ACCENT}; border-color:{ACCENT}; }}
QSplitter::handle:vertical {{ background:#262b33; height:8px; margin:0 18px;
    border-radius:4px; }}
QMenuBar {{ background:{BG}; border-bottom:1px solid {BORDER}; }}
QMenuBar::item:selected {{ background:{CARD2}; border-radius:4px; }}
QMenu {{ background:{CARD2}; border:1px solid {BORDER}; padding:4px; }}
QMenu::item:selected {{ background:{ACCENT}; color:#081018; border-radius:4px; }}
QToolTip {{ background:{CARD2}; color:{TEXT}; border:1px solid {BORDER}; padding:5px; }}
QScrollBar:vertical {{ background:{BG}; width:10px; }}
QScrollBar::handle:vertical {{ background:#3a4150; border-radius:5px; min-height:24px; }}
QScrollBar::handle:vertical:hover {{ background:#4a5262; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
QStatusBar {{ background:{BG}; color:{MUTED}; }}
"""


class FileRow(QWidget):
    def __init__(self, title: str, placeholder: str, button_text: str, parent=None):
        super().__init__(parent)
        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setColumnStretch(1, 1)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight:600;")
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.btn = QPushButton(button_text)
        self.info = QLabel("")
        self.info.setObjectName("Muted")
        lay.addWidget(self.title_label, 0, 0)
        lay.addWidget(self.edit, 0, 1)
        lay.addWidget(self.btn, 0, 2)
        lay.addWidget(self.info, 1, 1)


class Card(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        t = QLabel(title.upper())
        t.setObjectName("CardTitle")
        outer.addWidget(t)
        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(8)
        outer.addLayout(self.grid)


class MainWindow(QMainWindow):
    def __init__(self, ffmpeg: Optional[str], ffprobe: Optional[str]):
        super().__init__()
        self.setWindowTitle("AV Combiner")
        self.resize(1020, 880)
        self.setMinimumSize(880, 640)
        self.setStyleSheet(STYLESHEET)

        self.settings = QSettings("AVCombiner", "AVCombiner")
        self.ffmpeg, self.ffprobe = ffmpeg, ffprobe
        self.hw = HardwareInfo()
        self.vinfo, self.ainfo = MediaInfo(), MediaInfo()
        self._combine: Optional[CombineWorker] = None
        self._probes: List[ProbeWorker] = []
        self._detect: Optional[DetectWorker] = None

        self._build_ui()
        self._build_menus()
        self._restore_settings()

        if self.ffmpeg:
            self._log(f"FFmpeg : {self.ffmpeg}")
            self._log(f"FFprobe: {self.ffprobe or 'not found'}")
            self._detect = DetectWorker(self.ffmpeg)
            self._detect.detect_done.connect(self._on_detect_done)
            self._detect.finished.connect(self._detect.deleteLater)
            self._detect.start()
        else:
            self._log("FFmpeg NOT FOUND.")
            self.combine_btn.setEnabled(False)

    # ------------------------------------------------------------ UI build
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 14, 20, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        glyph = QLabel("▶")
        glyph.setStyleSheet(f"color:{ACCENT}; font-size:26px; font-weight:800;")
        titles = QVBoxLayout()
        t = QLabel("AV Combiner")
        t.setObjectName("Title")
        s = QLabel("Merge any video + any audio in seconds — powered by FFmpeg")
        s.setObjectName("Subtitle")
        titles.addWidget(t)
        titles.addWidget(s)
        header.addWidget(glyph)
        header.addLayout(titles)
        header.addStretch(1)
        root.addLayout(header)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(8)

        # ---- top: scrollable cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        host.setStyleSheet("background:transparent;")
        cards = QVBoxLayout(host)
        cards.setContentsMargins(0, 4, 0, 4)
        cards.setSpacing(10)

        fc = Card("Files")
        self.video_row = FileRow("Video", "Path to source video…", "Browse")
        self.audio_row = FileRow("Audio", "Path to source audio…", "Browse")
        self.output_row = FileRow("Output", "Where to write the result…", "Save as")
        for r, row in enumerate((self.video_row, self.audio_row, self.output_row)):
            fc.grid.addWidget(row, r, 0, 1, 3)
        self.video_row.btn.clicked.connect(self.browse_video)
        self.audio_row.btn.clicked.connect(self.browse_audio)
        self.output_row.btn.clicked.connect(self.browse_output)
        cards.addWidget(fc)

        sc = Card("Settings")
        self.mode_cb = QComboBox()
        self.mode_cb.addItems([MODE_INSTANT, MODE_STRICT, MODE_FULL])
        self.mode_cb.setToolTip("Instant copies streams (seconds). Full re-encode only "
                                "when you must change formats.")
        self.accel_cb = QComboBox()
        self.accel_cb.addItems([ACCEL_AUTO, ACCEL_HYBRID, ACCEL_CPU_STD, ACCEL_CPU_FAST,
                                ACCEL_NVIDIA, ACCEL_INTEL, ACCEL_AMD, ACCEL_APPLE])
        self.accel_cb.setToolTip("Hardware used only when a re-encode is required.")
        self.hw_lbl = QLabel("Detecting hardware…")
        self.hw_lbl.setObjectName("Muted")
        self.plan_lbl = QLabel("Plan: —")
        self.plan_lbl.setStyleSheet(f"color:{ACCENT}; font-size:11px;")
        self.track_cb = QComboBox()
        self.track_cb.addItems(["Replace video audio",
                                "Add selected audio as extra track"])
        self.length_cb = QComboBox()
        self.length_cb.addItems(["Stop output when shortest input ends",
                                 "Keep full video length",
                                 "Loop audio until video ends"])
        self.fallback_chk = QCheckBox("Auto-retry with full re-encode if instant path fails")
        self.fallback_chk.setChecked(True)
        rows = [("Mode", self.mode_cb), ("Hardware / Speed", self.accel_cb)]
        for r, (name, w) in enumerate(rows, start=1):
            lab = QLabel(name)
            lab.setStyleSheet("font-weight:600;")
            sc.grid.addWidget(lab, r, 0)
            sc.grid.addWidget(w, r, 1, 1, 2)
        sc.grid.addWidget(self.hw_lbl, 3, 0, 1, 3)
        sc.grid.addWidget(self.plan_lbl, 4, 0, 1, 3)
        for r, (name, w) in enumerate([("Audio track", self.track_cb),
                                       ("If lengths differ", self.length_cb)], start=5):
            lab = QLabel(name)
            lab.setStyleSheet("font-weight:600;")
            sc.grid.addWidget(lab, r, 0)
            sc.grid.addWidget(w, r, 1, 1, 2)
        sc.grid.addWidget(self.fallback_chk, 7, 0, 1, 3)
        cards.addWidget(sc)

        rc = Card("Run")
        bar = QHBoxLayout()
        
        # FIXED BUTTON: No emoji, solid blue styling
        self.combine_btn = QPushButton("Combine")
        self.combine_btn.setObjectName("Primary")
        self.combine_btn.setStyleSheet(
            "QPushButton { background:#4da3ff; color:#081018; border:none;"
            "border-radius:7px; padding:9px 28px; font-weight:700; }"
            "QPushButton:hover { background:#6fb6ff; }"
            "QPushButton:pressed { background:#3d92ee; }"
            "QPushButton:disabled { background:#262a31; color:#7d8590; }")
        self.combine_btn.setToolTip("Start combining (Ctrl+R)")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setToolTip("Terminate running FFmpeg jobs (Esc)")
        self.open_btn = QPushButton("Open Output Folder")
        self.open_btn.setEnabled(False)
        self.console_btn = QPushButton("Hide Console")
        
        bar.addWidget(self.combine_btn)
        bar.addWidget(self.cancel_btn)
        bar.addWidget(self.open_btn)
        bar.addWidget(self.console_btn)
        bar.addStretch(1)
        rc.grid.addLayout(bar, 1, 0, 1, 3)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        rc.grid.addWidget(self.progress, 2, 0, 1, 3)
        self.status_lbl = QLabel("Ready.")
        rc.grid.addWidget(self.status_lbl, 3, 0, 1, 3)
        cards.addWidget(rc)
        cards.addStretch(1)

        scroll.setWidget(host)
        self.splitter.addWidget(scroll)

        # ---- console panel
        self.console_panel = QFrame()
        self.console_panel.setObjectName("ConsolePanel")
        cl = QVBoxLayout(self.console_panel)
        cl.setContentsMargins(10, 8, 10, 10)
        cl.setSpacing(6)
        toolbar = QHBoxLayout()
        ct = QLabel("CONSOLE")
        ct.setObjectName("CardTitle")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(70)
        toolbar.addWidget(ct)
        toolbar.addStretch(1)
        toolbar.addWidget(self.clear_btn)
        cl.addLayout(toolbar)
        self.console = QPlainTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(2000)   # bounded memory
        self.console.setPlaceholderText("No activity yet.")
        cl.addWidget(self.console)
        self.splitter.addWidget(self.console_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        root.addWidget(self.splitter, 1)

        # ---- wire controls
        self.combine_btn.clicked.connect(self.start)
        self.cancel_btn.clicked.connect(self.cancel_combine)
        self.open_btn.clicked.connect(self.open_output_folder)
        self.console_btn.clicked.connect(self.toggle_console)
        self.clear_btn.clicked.connect(self.console.clear)
        for cb in (self.mode_cb, self.accel_cb, self.track_cb, self.length_cb):
            cb.currentIndexChanged.connect(lambda _=0: self._update_plan())
        self.output_row.edit.textChanged.connect(lambda _t: self._update_plan())

    def _build_menus(self) -> None:
        mb = self.menuBar()
        fm = mb.addMenu("&File")
        fm.addAction("Open &Video…", self.browse_video, QKeySequence("Ctrl+O"))
        fm.addAction("Open &Audio…", self.browse_audio, QKeySequence("Ctrl+Shift+O"))
        fm.addAction("Set &Output…", self.browse_output, QKeySequence("Ctrl+S"))
        fm.addSeparator()
        fm.addAction("E&xit", self.close, QKeySequence("Alt+F4"))
        rm = mb.addMenu("&Run")
        rm.addAction("&Combine", self.start, QKeySequence("Ctrl+R"))
        rm.addAction("Canc&el", self.cancel_combine, QKeySequence("Esc"))
        vm = mb.addMenu("&View")
        vm.addAction("Toggle &Console", self.toggle_console, QKeySequence("Ctrl+K"))
        vm.addAction("C&lear Console", self.console.clear, QKeySequence("Ctrl+L"))
        hm = mb.addMenu("&Help")
        hm.addAction("&About", self._about)

    def _about(self) -> None:
        QMessageBox.about(self, "About AV Combiner",
                          "FFmpeg-driven audio/video muxer.\n"
                          "Instant stream-copy, GPU/Hybrid re-encode, codec-aware "
                          "container selection.")

    # ------------------------------------------------------------ settings
    def _restore_settings(self) -> None:
        s = self.settings
        geo = s.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        state = s.value("splitter")
        if state:
            self.splitter.restoreState(state)
        self.mode_cb.setCurrentIndex(int(s.value("mode_idx", 0)))
        self.accel_cb.setCurrentIndex(int(s.value("accel_idx", 0)))
        self.track_cb.setCurrentIndex(int(s.value("track_idx", 0)))
        self.length_cb.setCurrentIndex(int(s.value("length_idx", 0)))
        self.fallback_chk.setChecked(str(s.value("fallback", "true")) == "true")
        self.console_panel.setVisible(str(s.value("console", "true")) == "true")
        self._sync_console_btn()

    def _save_settings(self) -> None:
        s = self.settings
        s.setValue("geometry", self.saveGeometry())
        s.setValue("splitter", self.splitter.saveState())
        s.setValue("mode_idx", self.mode_cb.currentIndex())
        s.setValue("accel_idx", self.accel_cb.currentIndex())
        s.setValue("track_idx", self.track_cb.currentIndex())
        s.setValue("length_idx", self.length_cb.currentIndex())
        s.setValue("fallback", "true" if self.fallback_chk.isChecked() else "false")
        s.setValue("console", "true" if self.console_panel.isVisible() else "false")

    # ------------------------------------------------------------ helpers
    def _log(self, text: str) -> None:
        if text:
            self.console.appendPlainText(text)

    def _set_status(self, text: str, color: str = SUCCESS) -> None:
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color:{color}; font-size:13px;")

    def _sync_console_btn(self) -> None:
        self.console_btn.setText("Show Console"
                                 if not self.console_panel.isVisible() else "Hide Console")

    def toggle_console(self) -> None:
        self.console_panel.setVisible(not self.console_panel.isVisible())
        self._sync_console_btn()

    # ------------------------------------------------------------ browsing
    def _probe(self, path: str, is_video: bool) -> None:
        w = ProbeWorker(self.ffprobe, path, is_video)
        w.probe_done.connect(self._on_probe_done)
        w.finished.connect(lambda w=w: (self._probes.remove(w) if w in self._probes else None,
                                        w.deleteLater()))
        self._probes.append(w)
        w.start()

    def browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select video file", "",
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts *.flv *.wmv "
            "*.mpg *.mpeg *.3gp *.ogv);;All files (*)")
        if path:
            self.video_row.edit.setText(path)
            if not self.output_row.edit.text().strip():
                self.output_row.edit.setText(os.path.splitext(path)[0] + "_combined.mp4")
            self.video_row.info.setText("Reading file info…")
            self._probe(path, True)

    def browse_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select audio file", "",
            "Audio files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma *.aiff "
            "*.ac3 *.mka);;All files (*)")
        if path:
            self.audio_row.edit.setText(path)
            self.audio_row.info.setText("Reading file info…")
            self._probe(path, False)

    def browse_output(self) -> None:
        cur = self.output_row.edit.text().strip() or os.path.join(
            os.path.expanduser("~"), "output.mp4")
        d = cur if os.path.isdir(cur) else (os.path.dirname(cur) or ".")
        f = "output.mp4" if os.path.isdir(cur) else (os.path.basename(cur) or "output.mp4")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save output file", os.path.join(d, f),
            "MP4 video (*.mp4);;Matroska video (*.mkv);;WebM video (*.webm);;"
            "QuickTime video (*.mov);;AVI video (*.avi);;All files (*)")
        if path:
            self.output_row.edit.setText(path)

    def _on_probe_done(self, info: MediaInfo, is_video: bool) -> None:
        if is_video:
            self.vinfo = info
            self.video_row.info.setText(self._info_text(info))
        else:
            self.ainfo = info
            self.audio_row.info.setText(self._info_text(info))
        self._update_plan()

    @staticmethod
    def _info_text(i: MediaInfo) -> str:
        txt = f"⏱ {core.fmt_duration(i.dur)}"
        if i.video:
            txt += f"   •   video: {i.video}"
        if i.audio:
            txt += f"   •   audio: {i.audio}"
        return txt

    def _on_detect_done(self, hw: HardwareInfo) -> None:
        self.hw = hw
        if hw.gpu_list:
            pretty = hw.gpu_name or hw.gpu_list[0][0]
            self.hw_lbl.setText(f"⚙ Detected: {pretty} [{hw.gpu_list[0][1]}] "
                                f"+ {hw.cores} CPU threads")
        else:
            self.hw_lbl.setText(f" Detected: no usable GPU encoder → CPU ({hw.cores} threads)")
        self._update_plan()

    # ------------------------------------------------------------ planning
    def _flags(self):
        add_extra = self.track_cb.currentIndex() == 1
        loop = self.length_cb.currentIndex() == 2
        shortest = self.length_cb.currentIndex() == 0 or loop
        return add_extra, shortest, loop

    def _accel_resolved(self) -> str:
        a = self.accel_cb.currentText()
        if a == ACCEL_AUTO:
            return self.hw.gpu_list[0][0] if self.hw.gpu_list else ACCEL_CPU_FAST
        return a

    def _update_plan(self) -> None:
        v = self.video_row.edit.text().strip()
        a = self.audio_row.edit.text().strip()
        o = self.output_row.edit.text().strip()
        if not (self.ffmpeg and v and a):
            return
        add_extra, shortest, loop = self._flags()
        try:
            plan = core.plan_command(self.ffmpeg, v, a, o or "output.mp4",
                                     self.mode_cb.currentText(), self._accel_resolved(),
                                     self.hw.gpu_list, self.vinfo.video, self.vinfo.audio,
                                     self.ainfo.audio, add_extra, shortest, loop)
            txt = f"Plan: {plan.plan_text}"
            if plan.notes:
                txt += "  (container auto-switched to .mkv)"
            self.plan_lbl.setText(txt)
            self.plan_lbl.setStyleSheet(f"color:{ACCENT}; font-size:11px;")
        except PlanError as e:
            self.plan_lbl.setText(f"Plan: {e}")
            self.plan_lbl.setStyleSheet(f"color:{ERROR}; font-size:11px;")
        except Exception:
            pass

    def _out_dur(self, shortest: bool, loop: bool):
        v, a = self.vinfo.dur, self.ainfo.dur
        if loop:
            return v
        if shortest:
            vals = [d for d in (v, a) if d]
            return min(vals) if vals else None
        return v

    # ------------------------------------------------------------ run
    def start(self) -> None:
        if self._combine is not None and self._combine.isRunning():
            return  # duplicate-submission guard
        if not self.ffmpeg:
            QMessageBox.critical(self, "FFmpeg missing", "FFmpeg is not available.")
            return
        video = self.video_row.edit.text().strip()
        audio = self.audio_row.edit.text().strip()
        raw_out = self.output_row.edit.text().strip()
        if not video or not os.path.isfile(video):
            QMessageBox.warning(self, "Missing video", "Choose a valid video file.")
            return
        if not audio or not os.path.isfile(audio):
            QMessageBox.warning(self, "Missing audio", "Choose a valid audio file.")
            return
        if not raw_out:
            QMessageBox.warning(self, "Missing output", "Choose an output file name.")
            return

        if self.vinfo.video is None and self.ffprobe:
            self.vinfo = core.probe_media(self.ffprobe, video)
        if self.ainfo.audio is None and self.ffprobe:
            self.ainfo = core.probe_media(self.ffprobe, audio)

        add_extra, shortest, loop = self._flags()
        mode = self.mode_cb.currentText()
        accel = self._accel_resolved()
        output = core.normalize_output(raw_out)

        attempts = []
        try:
            plan = core.plan_command(self.ffmpeg, video, audio, output, mode, accel,
                                     self.hw.gpu_list, self.vinfo.video, self.vinfo.audio,
                                     self.ainfo.audio, add_extra, shortest, loop)
            for n in plan.notes:
                self._log("Note: " + n)
            self._log("PLAN: " + plan.plan_text)
            attempts.append((mode, "cmd", plan.cmd))
            output = plan.output
        except PlanError as e:
            QMessageBox.critical(self, "Cannot combine without re-encode", str(e))
            return

        if mode == MODE_FULL and accel == ACCEL_HYBRID:
            out_dur = self._out_dur(shortest, loop)
            ext = os.path.splitext(output)[1].lower()
            covers = (self.ainfo.dur is not None and out_dur
                      and self.ainfo.dur >= out_dur - 0.5)
            if (self.hw.gpu_list and ext in core.HYBRID_OK_EXTS and not add_extra
                    and not loop and covers and (out_dur or 0) >= 10):
                attempts.insert(0, (ACCEL_HYBRID, "hybrid", {
                    "video": video, "audio": audio, "output": output,
                    "out_dur": out_dur, "ext": ext}))
            else:
                self._log("Note: Hybrid not applicable; using single-pass.")

        if self.fallback_chk.isChecked() and mode != MODE_FULL:
            attempts.append((MODE_FULL + " (auto-fallback)", "cmd", core.build_full_cmd(
                self.ffmpeg, video, audio, output, ACCEL_CPU_STD, self.hw.gpu_list,
                add_extra, shortest, loop)))

        self.output_row.edit.setText(output)
        outdir = os.path.dirname(output)
        if outdir:
            try:
                os.makedirs(outdir, exist_ok=True)
            except Exception as exc:
                QMessageBox.critical(self, "Output folder error", str(exc))
                return
        if os.path.exists(output):
            ans = QMessageBox.question(
                self, "Output exists", f"{output}\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ans != QMessageBox.Yes:
                return

        self._combine = CombineWorker(self.ffmpeg, attempts,
                                      self._out_dur(shortest, loop),
                                      self.hw.gpu_list[0][2] if self.hw.gpu_list else [],
                                      self.hw.cores)
        self._combine.log_line.connect(self._log)
        self._combine.progressed.connect(self._on_progress)
        self._combine.attempt_started.connect(self._on_attempt)
        self._combine.succeeded.connect(self._on_success)
        self._combine.failed_all.connect(self._on_failed)
        self._combine.cancelled.connect(self._on_cancelled)
        self._combine.finished.connect(self._on_worker_finished)

        self.combine_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.open_btn.setEnabled(False)
        self.progress.setRange(0, 0)  # busy until first measurable progress
        self.progress.setValue(0)
        self._combine.start()

    def _on_attempt(self, label: str) -> None:
        self._log(f"\n===== Attempt: {label} =====")
        self._set_status(f"Running: {label}", ACCENT)
        if "copy" in label.lower():
            self.progress.setRange(0, 0)   # copy = disk-bound, no measurable %
        else:
            self.progress.setRange(0, 100)

    def _on_progress(self, pct: float, sec: float) -> None:
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 100)
        self.progress.setValue(int(pct))
        self._set_status(f"Working… {pct:5.1f}%  "
                         f"({core.fmt_duration(sec)} / "
                         f"{core.fmt_duration(self._combine_total())})", ACCENT)

    def _combine_total(self):
        return self._combine._total if self._combine else None

    def _on_success(self, output: str, elapsed: float) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self._set_status(f"✓ Finished in {elapsed:.2f} s", SUCCESS)
        self._log(f"\nSUCCESS -> {output}\nElapsed: {elapsed:.2f} seconds")
        self.open_btn.setEnabled(True)
        QMessageBox.information(self, "Finished", f"Done in {elapsed:.2f} s!\n\n{output}")

    def _on_failed(self, msg: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._set_status("✗ Failed. Check console.", ERROR)
        QMessageBox.critical(self, "FFmpeg failed", msg)

    def _on_cancelled(self) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._set_status("Cancelled.", WARN)
        self._log("\nCancelled by user.")

    def _on_worker_finished(self) -> None:
        self.combine_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._combine = None

    def cancel_combine(self) -> None:
        if self._combine is not None and self._combine.isRunning():
            self._combine.request_cancel()

    def open_output_folder(self) -> None:
        folder = os.path.dirname(self.output_row.edit.text().strip()) or os.getcwd()
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    # ------------------------------------------------------------ shutdown
    def closeEvent(self, event) -> None:
        if self._combine is not None and self._combine.isRunning():
            self._combine.request_cancel()
            self._combine.wait(4000)
        for w in list(self._probes):
            w.wait(1000)
        self._save_settings()
        event.accept()