"""AV Combiner - pure application logic. No UI imports, no Qt."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

WIN_FLAGS = {"creationflags": 0x08000000} if os.name == "nt" else {}

MODE_INSTANT = "Instant: copy streams, auto-switch container if needed (recommended)"
MODE_STRICT = "Strict copy: never re-encode (error if incompatible)"
MODE_FULL = "Full re-encode (only when you must change format)"

ACCEL_AUTO = "Auto (use detected best)"
ACCEL_HYBRID = "Hybrid CPU + GPU (parallel segments)"
ACCEL_CPU_STD = "CPU (Standard)"
ACCEL_CPU_FAST = "CPU (Ultra Fast)"
ACCEL_NVIDIA = "NVIDIA GPU (NVENC)"
ACCEL_INTEL = "Intel GPU (QSV)"
ACCEL_AMD = "AMD GPU (AMF)"
ACCEL_APPLE = "Apple (VideoToolbox)"

GPU_CANDIDATES: List[Tuple[str, str, List[str]]] = [
    (ACCEL_NVIDIA, "h264_nvenc",
     ["-c:v", "h264_nvenc", "-preset", "p1", "-qp", "20", "-profile:v", "main", "-pix_fmt", "yuv420p"]),
    (ACCEL_INTEL, "h264_qsv",
     ["-c:v", "h264_qsv", "-preset", "veryfast", "-global_quality", "20", "-profile:v", "main", "-pix_fmt", "yuv420p"]),
    (ACCEL_AMD, "h264_amf",
     ["-c:v", "h264_amf", "-quality", "speed", "-profile:v", "main", "-pix_fmt", "yuv420p"]),
    (ACCEL_APPLE, "h264_videotoolbox",
     ["-c:v", "h264_videotoolbox", "-q:v", "50", "-pix_fmt", "yuv420p"]),
]

MP4_VIDEO = {"h264", "hevc", "mpeg4", "mjpeg", "av1", "vp9", "h263"}
MP4_AUDIO = {"aac", "mp3", "ac3", "eac3", "alac", "flac"}
MOV_VIDEO = MP4_VIDEO | {"prores", "dnxhd", "animation"}
MOV_AUDIO = MP4_AUDIO | {"pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le"}
WEBM_VIDEO = {"vp8", "vp9", "av1"}
WEBM_AUDIO = {"opus", "vorbis"}
AVI_VIDEO = {"mpeg4", "mjpeg", "h264", "msmpeg4v3", "wmv3", "flv1"}
AVI_AUDIO = {"mp3", "ac3", "pcm_s16le", "pcm_u8", "adpcm_ms"}

CONTAINER_TABLE = {
    ".mp4": (MP4_VIDEO, MP4_AUDIO),
    ".m4v": (MP4_VIDEO, MP4_AUDIO),
    ".mov": (MOV_VIDEO, MOV_AUDIO),
    ".webm": (WEBM_VIDEO, WEBM_AUDIO),
    ".avi": (AVI_VIDEO, AVI_AUDIO),
}
HYBRID_OK_EXTS = (".mp4", ".m4v", ".mov", ".mkv")


class PlanError(Exception):
    """Raised when a no-re-encode plan is impossible."""


@dataclass
class MediaInfo:
    dur: Optional[float] = None
    video: Optional[str] = None
    audio: Optional[str] = None


@dataclass
class HardwareInfo:
    gpu_list: List[Tuple[str, str, List[str]]] = field(default_factory=list)
    cores: int = 4
    gpu_name: str = ""


@dataclass
class Plan:
    cmd: List[str]
    output: str
    plan_text: str
    notes: List[str]


def exe_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_ffmpeg(manual: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Discovery order: saved manual path -> PATH -> next to executable."""
    def _pair(ff: str) -> Tuple[str, Optional[str]]:
        fp = os.path.join(os.path.dirname(ff),
                          "ffprobe.exe" if os.name == "nt" else "ffprobe")
        return ff, fp if os.path.isfile(fp) else None

    if manual and os.path.isfile(manual) and "ffmpeg" in os.path.basename(manual).lower():
        return _pair(manual)
    which = shutil.which("ffmpeg")
    if which:
        return _pair(which)
    local = os.path.join(exe_dir(), "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if os.path.isfile(local):
        return _pair(local)
    return None, None


def fmt_duration(sec: Optional[float]) -> str:
    if sec is None:
        return "unknown"
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def probe_media(ffprobe: Optional[str], path: str) -> MediaInfo:
    info = MediaInfo()
    if not ffprobe or not path or not os.path.isfile(path):
        return info
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error",
             "-show_entries", "format=duration:stream=codec_type,codec_name",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=60, **WIN_FLAGS)
        for line in (r.stdout or "").strip().splitlines():
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) == 1:
                try:
                    if parts[0].upper() != "N/A":
                        info.dur = float(parts[0])
                except ValueError:
                    pass
            elif len(parts) == 2:
                ctype, cname = parts
                if ctype == "video" and info.video is None:
                    info.video = cname
                elif ctype == "audio" and info.audio is None:
                    info.audio = cname
    except Exception:
        pass
    return info


def video_codec_ok(codec: Optional[str], ext: str) -> bool:
    if codec is None:
        return True
    if ext in (".mkv", ".mka"):
        return True
    t = CONTAINER_TABLE.get(ext)
    return bool(t) and codec.lower() in t[0]


def audio_codec_ok(codec: Optional[str], ext: str) -> bool:
    if codec is None:
        return True
    if ext in (".mkv", ".mka"):
        return True
    t = CONTAINER_TABLE.get(ext)
    return bool(t) and codec.lower() in t[1]


def audio_args_for(ext: str) -> List[str]:
    if ext == ".webm":
        return ["-c:a", "libopus", "-b:a", "160k"]
    if ext == ".avi":
        return ["-c:a", "libmp3lame", "-b:a", "192k"]
    return ["-c:a", "aac", "-b:a", "192k"]


def video_args_for(accel_label: str, gpu_list: Sequence[Tuple[str, str, List[str]]]) -> List[str]:
    if accel_label == ACCEL_CPU_FAST:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p"]
    if accel_label == ACCEL_CPU_STD:
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    for label, _enc, args in gpu_list:
        if label == accel_label:
            return list(args)
    for label in (ACCEL_AUTO,):
        pass
    if gpu_list:
        return list(gpu_list[0][2])
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]


def normalize_output(output: str) -> str:
    output = os.path.abspath(os.path.expanduser(output.strip()))
    if os.path.isdir(output):
        output = os.path.join(output, "combined.mp4")
    ext = os.path.splitext(output)[1].lower()
    if not ext:
        output += ".mp4"
    elif ext not in (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"):
        output = os.path.splitext(output)[0] + ".mkv"
    return output


def cmd_to_text(cmd: Sequence[str]) -> str:
    try:
        return subprocess.list2cmdline(list(cmd)) if os.name == "nt" else shlex.join(cmd)
    except Exception:
        return " ".join(str(c) for c in cmd)


def _test_encoder(ffmpeg: str, enc_id: str) -> bool:
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-v", "error",
             "-f", "lavfi", "-i", "color=c=black:s=128x128:r=30:d=0.2",
             "-c:v", enc_id, "-f", "null", "-"],
            capture_output=True, timeout=30, **WIN_FLAGS)
        return r.returncode == 0
    except Exception:
        return False


def detect_hardware(ffmpeg: Optional[str]) -> HardwareInfo:
    hw = HardwareInfo(cores=os.cpu_count() or 4)
    if not ffmpeg:
        return hw
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-encoders"],
                             capture_output=True, text=True, timeout=30,
                             **WIN_FLAGS).stdout
    except Exception:
        out = ""
    for label, enc_id, args in GPU_CANDIDATES:
        if enc_id in out and _test_encoder(ffmpeg, enc_id):
            hw.gpu_list.append((label, enc_id, args))
            break
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=10, **WIN_FLAGS)
        if r.returncode == 0 and r.stdout.strip():
            hw.gpu_name = r.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return hw


def plan_command(ffmpeg: str, video: str, audio: str, output: str, mode: str,
                 accel: str, gpu_list, v_codec, v_acodec, a_acodec,
                 add_extra: bool, shortest: bool, loop: bool) -> Plan:
    ext = os.path.splitext(output)[1].lower()
    notes: List[str] = []
    needed_audio = [a_acodec] + ([v_acodec] if add_extra else [])

    if mode == MODE_INSTANT:
        if not video_codec_ok(v_codec, ext):
            output = os.path.splitext(output)[0] + ".mkv"
            ext = ".mkv"
            notes.append("Video codec cannot be copied into the chosen container; "
                         "switched output to .mkv so NO re-encode is needed.")
        v_args = ["-c:v", "copy"]
        if all(audio_codec_ok(c, ext) for c in needed_audio):
            a_args = ["-c:a", "copy"]
            plan_text = "COPY video + COPY audio (instant, disk-speed)"
        else:
            a_args = audio_args_for(ext)
            plan_text = f"COPY video + convert audio only ({a_acodec} -> {a_args[1]})"
    elif mode == MODE_STRICT:
        bad = []
        if not video_codec_ok(v_codec, ext):
            bad.append(f"video '{v_codec}'")
        for c in needed_audio:
            if not audio_codec_ok(c, ext):
                bad.append(f"audio '{c}'")
        if bad:
            raise PlanError("Strict copy impossible into '" + ext + "': " +
                            ", ".join(bad) + ". Use Instant mode or Full re-encode.")
        v_args, a_args = ["-c:v", "copy"], ["-c:a", "copy"]
        plan_text = "STRICT COPY video + audio (instant)"
    else:
        v_args = video_args_for(accel, gpu_list)
        if ext == ".webm":
            v_args = ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0"]
        a_args = audio_args_for(ext)
        plan_text = f"RE-ENCODE video [{accel}] + encode audio (slow path)"

    cmd = [ffmpeg, "-hide_banner", "-y", "-i", video]
    if loop:
        cmd += ["-stream_loop", "-1"]
    cmd += ["-i", audio]
    if add_extra:
        cmd += ["-map", "0:v:0", "-map", "0:a:0?", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    if shortest or loop:
        cmd += ["-shortest"]
    cmd += v_args + a_args
    if ext in (".mp4", ".m4v", ".mov"):
        cmd += ["-movflags", "+faststart"]
    cmd.append(output)
    return Plan(cmd=cmd, output=output, plan_text=plan_text, notes=notes)


def build_full_cmd(ffmpeg: str, video: str, audio: str, output: str, accel: str,
                   gpu_list, add_extra: bool, shortest: bool, loop: bool) -> List[str]:
    ext = os.path.splitext(output)[1].lower()
    cmd = [ffmpeg, "-hide_banner", "-y", "-i", video]
    if loop:
        cmd += ["-stream_loop", "-1"]
    cmd += ["-i", audio]
    if add_extra:
        cmd += ["-map", "0:v:0", "-map", "0:a:0?", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    if shortest or loop:
        cmd += ["-shortest"]
    v = video_args_for(accel, gpu_list)
    if ext == ".webm":
        v = ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0"]
    cmd += v + audio_args_for(ext)
    if ext in (".mp4", ".m4v", ".mov"):
        cmd += ["-movflags", "+faststart"]
    cmd.append(output)
    return cmd