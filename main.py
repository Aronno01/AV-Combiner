"""Entry point: bootstrap, FFmpeg discovery, crash guard."""
from __future__ import annotations

import os
import sys
import traceback


def _write_crash(msg: str):
    try:
        base = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(base, "crash_log.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(msg)
        return p
    except Exception:
        return None


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
        from PySide6.QtCore import QSettings
    except ImportError:
        print("PySide6 is not installed. Run: pip install -r requirements.txt",
              file=sys.stderr)
        return 2

    import core
    from ui import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("AV Combiner")
    app.setOrganizationName("AVCombiner")

    settings = QSettings("AVCombiner", "AVCombiner")
    ffmpeg, ffprobe = core.find_ffmpeg(settings.value("ffmpeg_path"))
    if not ffmpeg:
        QMessageBox.warning(None, "FFmpeg not found",
                            "Install FFmpeg (winget install Gyan.FFmpeg), copy ffmpeg.exe "
                            "next to this program, or locate it manually now.")
        path, _ = QFileDialog.getOpenFileName(None, "Select FFmpeg executable", "",
                                              "Executables (*.exe);;All files (*)")
        if path and "ffmpeg" in os.path.basename(path).lower():
            settings.setValue("ffmpeg_path", path)   # persisted for next run
            ffmpeg, ffprobe = core.find_ffmpeg(path)

    win = MainWindow(ffmpeg, ffprobe)
    win.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        msg = traceback.format_exc()
        path = _write_crash(msg)
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "AV Combiner failed to start",
                                 f"Details saved to:\n{path or '(unsavable)'}\n\n{msg[:1200]}")
        except Exception:
            print(msg, file=sys.stderr)
        sys.exit(1)