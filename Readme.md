# 🎬 AV Combiner

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge" alt="Platform">
  <img src="https://img.shields.io/badge/Python-3.15-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/UI-PySide6_6-41CD52?style=for-the-badge&logo=qt" alt="PySide6">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<p align="center">
  <b>A fast, premium-dark desktop application to merge any video file with any audio file in seconds.</b><br>
  Powered by FFmpeg, featuring intelligent stream-copying, hardware-accelerated re-encoding, and a clean modern UI.
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-download">Download</a> •
  <a href="#-how-to-use">How to Use</a> •
  <a href="#-build-from-source">Build from Source</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## ✨ Features

### ⚡ Blazing-Fast Combining
- **Instant mode** copies video and audio streams without re-encoding — an 18-minute file finishes in **under 3 seconds**.
- Smart codec-aware container selection: if your video codec can't fit into `.mp4`, the app automatically switches the output to `.mkv` instead of silently re-encoding the whole file.

### 🚀 Hardware Acceleration
Auto-detects and verifies your GPU encoder with a real test-encode, then offers:
- **NVIDIA NVENC**
- **Intel Quick Sync (QSV)**
- **AMD AMF**
- **Apple VideoToolbox**

###  Hybrid CPU + GPU Mode
For full re-encodes, the app can split the video into two segments and encode them **in parallel** — one on the GPU, one on the CPU — then losslessly concatenate the result. This gives a real 2–4× speedup on supported hardware.

### 🛡️ Smart Fallback Chain
- Instant copy → Full re-encode (auto-fallback)
- Strict copy mode (errors instead of silently re-encoding)
- Full re-encode with any detected GPU or ultrafast CPU preset

### 🎛️ Advanced Controls
- **Audio track mode**: replace original audio or add as a second track
- **Length policies**: stop at shortest input, keep full video length, or loop audio until video ends
- **Live plan preview**: see exactly what the app will do *before* you click Combine
- **Real-time progress** with elapsed time and percentage

### 🌑 Premium Dark UI
- Deep charcoal surfaces with restrained blue accents
- Resizable console panel with draggable splitter
- Scrollable settings area, keyboard shortcuts, and tooltips
- Settings persistence (geometry, mode, hardware choice) across sessions

### 📦 Fully Portable
The released `.zip` contains everything — no installation, no Python, no FFmpeg setup required. Just unzip and run.

---

## 📥 Download

Go to the **[Releases](https://github.com/Aronno01/AV-Combiner/releases)** page and download the latest `AV.Combiner.zip`.

### Installation
1. Download `AV.Combiner.zip` from the Releases page.
2. Extract the zip to any folder (Desktop, Documents, etc.).
3. **Keep all files together** inside the `AV Combiner` folder:
AV Combiner/
├── AV Combiner.exe
├── _internal/
├── ffmpeg.exe
└── ffprobe.exe
4. Double-click `AV Combiner.exe`.

> ⚠️ **Do not** move `AV Combiner.exe` out of its folder — it needs `_internal`, `ffmpeg.exe`, and `ffprobe.exe` next to it to run.

### First-run note
Windows SmartScreen may warn you about an "unrecognized app" on first launch. This is normal for unsigned executables. Click **More info → Run anyway**.

---

## 🎯 How to Use

### Basic workflow
1. Click **Browse** next to **Video** and select your source video file.
2. Click **Browse** next to **Audio** and select your source audio file.
3. (Optional) Click **Save as** to choose where the output goes.
4. Click the blue **Combine** button.

That's it. For most files, the job finishes in seconds.

### Understanding the modes

| Mode | When to use | Speed |
|------|-------------|-------|
| **Instant** (recommended) | You just want to merge files. | Seconds |
| **Strict copy** | You want to guarantee no re-encoding; errors if impossible. | Seconds |
| **Full re-encode** | You must change format, codec, or container. | Minutes (GPU helps) |

### Understanding the "Plan" line
After you pick both files, a **Plan:** line appears under Settings. It tells you exactly what will happen:
- `COPY video + COPY audio (instant, disk-speed)` → fast path ✅
- `COPY video + convert audio only (mp3 -> aac)` → still fast, only audio re-encoded
- `RE-ENCODE video [NVIDIA GPU (NVENC)] + encode audio (slow path)` → full re-encode using your GPU

If the plan says the container will auto-switch to `.mkv`, that means your video codec couldn't fit into `.mp4` without re-encoding — the app is saving you from a 3-minute surprise.

### Length policies
When video and audio have different durations:
- **Stop output when shortest input ends** — output length = min(video, audio)
- **Keep full video length** — output = full video, silent tail if audio is shorter
- **Loop audio until video ends** — audio repeats to fill the video

---

## ️ Build from Source

### Prerequisites
- Python 3.11 or newer
- FFmpeg (installed via `winget install Gyan.FFmpeg`, or placed next to the script)
- Git (optional, for cloning)

### Clone and run
```bash
git clone https://github.com/Aronno01/AV-Combiner.git
cd AV-Combiner
python -m pip install -r requirements.txt
python main.py
----
Build the executable
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --onedir --windowed --name "AV Combiner" --icon icon.ico main.py

Then copy ffmpeg.exe and ffprobe.exe into dist\AV Combiner\ next to AV Combiner.exe.
Regenerate the icon
If you want to tweak the icon design:
bash 
python -m pip install pillow
python make_icon.py
This redraws icon.ico from the Python script.

🏗️ Architecture
The project is split into four clean modules:
AV-Combiner/
├── main.py          # Entry point, FFmpeg discovery, crash guard
├── core.py          # Pure logic: probing, planning, codec tables, hardware detection
├── workers.py       # QThread workers: Probe, Detect, Combine (QProcess orchestration)
├── ui.py            # PySide6 widgets + centralized QSS theme
├── make_icon.py     # Icon generator (uses Pillow)
├── build.bat        # One-click PyInstaller build script
├── requirements.txt # Python dependencies
└── .gitignore       # Keeps the repo clean

Key design decisions
Logic/UI separation: core.py has zero Qt imports — it's pure Python and fully testable.
Workers never touch widgets: all communication is via Qt signals/slots, keeping the GUI thread responsive.
Real progress: the worker injects -progress pipe:1 into every FFmpeg command, so the progress bar shows actual encode progress (not just a jump at the end).
Bounded log: the console caps at 2000 blocks to prevent memory growth on long sessions.
Hardware verification: GPU encoders are tested with a real 0.2-second encode before being offered — no false positives.
Settings persistence: window geometry, splitter position, and user choices are saved via QSettings.

🧪 Testing
Run the GUI-free test suite:
python -m pip install pytest
python -m pytest tests/ -v

The suite covers:
Output filename always appended to the FFmpeg command (regression test for the original "3-minute bug")
Instant mode auto-switches to .mkv for foreign codecs
Strict mode raises PlanError on incompatible pairs
Per-container audio codec selection
Duration formatting

Project Structure Reference
<img width="530" height="304" alt="{66B806A9-E21C-4146-94EC-2D4B760ED0B9}" src="https://github.com/user-attachments/assets/93a876bb-afb0-4042-addc-3a32f3424294" />

🤝 Contributing
Contributions, issues, and feature requests are welcome!
Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
Please keep the logic/UI separation intact and add tests for new core functionality.
📝 License
This project is licensed under the MIT License. You are free to use, modify, and distribute it, even commercially, as long as you include the original license notice.
🙏 Acknowledgments
FFmpeg — the backbone of this app. Without FFmpeg, none of this would be possible.
PySide6 — for the premium Qt6 Python bindings.
PyInstaller — for turning Python into a portable Windows executable.
Gyan's FFmpeg builds — the full Windows FFmpeg build used during development.
📬 Contact
GitHub: @Aronno01
Repository: github.com/Aronno01/AV-Combiner
Issues: Report a bug or request a feature

Made with ❤️ by https://github.com/Aronno01 .

PEACE OUT ! 

