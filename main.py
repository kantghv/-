import sys
import atexit
import base64
import ctypes
import ipaddress
import json
import logging
import os
import random
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QParallelAnimationGroup, QPropertyAnimation, QRect, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap, QPixmapCache
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    import psutil
except ImportError:
    psutil = None

try:
    import GPUtil
except ImportError:
    GPUtil = None

try:
    from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat
except ImportError:
    Image = None
    ImageChops = None
    ImageDraw = None
    ImageEnhance = None
    ImageFilter = None
    ImageOps = None
    ImageStat = None


APP_STYLE = """
QMainWindow {
    background: #0b0d12;
}
QLabel {
    color: #edf3f7;
}
QComboBox,
QPushButton {
    min-height: 36px;
    padding: 0 12px;
    border: 1px solid #2e3a4c;
    border-radius: 6px;
    background: #151a23;
    color: #edf3f7;
}
QPushButton {
    font-weight: 700;
}
QPushButton:hover {
    border-color: #49d6c8;
    background: #1d2632;
}
QPushButton:pressed {
    background: #10161f;
}
QPushButton:disabled {
    color: #657386;
    background: #111620;
}
QPushButton#primaryButton {
    color: #07100f;
    border-color: #6ff1d7;
    background: #58dcc7;
}
QPushButton#primaryButton:hover {
    background: #73f1dc;
}
QPushButton#dangerButton:hover {
    border-color: #ff8c77;
    background: #302027;
}
QComboBox::drop-down {
    width: 28px;
    border-left: 1px solid #2e3a4c;
}
QProgressBar {
    height: 22px;
    border: 1px solid #2e3a4c;
    border-radius: 5px;
    background: #101722;
    color: #edf3f7;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 5px;
    background-color: #58dcc7;
}
QSlider::groove:horizontal {
    height: 5px;
    border-radius: 2px;
    background: #242d3a;
}
QSlider::sub-page:horizontal {
    border-radius: 2px;
    background: #58dcc7;
}
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #f2c763;
}
QMenuBar {
    background: #0b0d12;
    color: #d9e3ef;
    border-bottom: 1px solid #202735;
}
QMenuBar::item {
    padding: 7px 12px;
}
QMenuBar::item:selected {
    background: #171e29;
}
QMenu {
    background: #141a23;
    color: #edf3f7;
    border: 1px solid #2e3a4c;
}
QMenu::item {
    padding: 7px 28px;
}
QMenu::item:selected {
    background: #243144;
}
QStatusBar {
    background: #0b0d12;
    color: #8fa3b8;
    border-top: 1px solid #202735;
}
"""


APP_NAME = "映效AI工作站"
APP_VERSION = "0.4.9"
APP_ID = "Kaet.YingXiaoAI.Workstation"
APP_ASCII_NAME = "YingXiaoAIWorkstation"

_GPU_SUMMARY_CACHE = None
_FFMPEG_CACHE = None


def is_windows() -> bool:
    return os.name == "nt"


def enable_system_dpi_awareness() -> str:
    """尽早启用 Windows DPI 感知，避免高分屏和多屏缩放发糊。"""
    if not is_windows():
        return "not-windows"
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return "per-monitor"
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            return "system"
        except Exception:
            return "failed"


def set_windows_app_id() -> bool:
    """设置任务栏 AppUserModelID，让图标、任务栏分组和通知归到本软件。"""
    if not is_windows():
        return False
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        return True
    except Exception:
        return False


def known_folder(name: str, fallback: Path) -> Path:
    """读取 Windows 用户目录，失败时回退到 home 下的常见目录。"""
    if is_windows():
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            )
            value, _ = winreg.QueryValueEx(key, name)
            return Path(os.path.expandvars(value))
        except Exception:
            pass
    return fallback


def documents_root() -> Path:
    return known_folder("Personal", Path.home() / "Documents")


def desktop_root() -> Path:
    return known_folder("Desktop", Path.home() / "Desktop")


def local_app_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    root = base / APP_ASCII_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def resource_root() -> Path:
    """返回软件资源目录，兼容源码运行和 PyInstaller 打包运行。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def runtime_root() -> Path:
    """返回用户可写的运行目录，输出和缓存不写进程序内部。"""
    root = documents_root() / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    for folder in ("outputs", "outputs/images", "outputs/video", "outputs/export", "presets", "models"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root


def cache_root() -> Path:
    root = local_app_root()
    for folder in ("cache", "logs", "settings"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root


def default_output_dir(kind: str) -> str:
    path = runtime_root() / "outputs" / kind
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def video_diagnostics_dir() -> Path:
    path = runtime_root() / "logs" / "video"
    path.mkdir(parents=True, exist_ok=True)
    return path


def model_registry_path() -> Path:
    path = runtime_root() / "models" / "model_registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def deployment_records_dir() -> Path:
    path = runtime_root() / "models" / "deployments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def mobile_api_root() -> Path:
    path = runtime_root() / "mobile_api"
    for folder in ("tasks", "uploads", "outputs"):
        (path / folder).mkdir(parents=True, exist_ok=True)
    return path


def mobile_api_config_path() -> Path:
    path = cache_root() / "settings" / "mobile_api.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def harden_private_file(path: Path):
    """Best-effort ACL hardening for local token/config files on Windows."""
    if not is_windows():
        return
    try:
        user = os.environ.get("USERNAME") or ""
        if not user:
            return
        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"{user}:F",
                "SYSTEM:F",
                "Administrators:F",
            ],
            check=False,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        logging.debug("Failed to harden ACL for %s", path, exc_info=True)


def is_private_client_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(str(value or "").split("%", 1)[0])
        return bool(ip.is_loopback or ip.is_private or ip.is_link_local)
    except ValueError:
        return False


def builtin_model_catalog() -> list[dict]:
    return [
        {
            "id": "builtin_flux1",
            "name": "FLUX.1",
            "kind": "图像生成",
            "source": "ComfyUI / FLUX.1 Kontext Dev",
            "launch": "ComfyUI workflow",
            "min_vram": "8GB",
            "notes": "适合图像生成、局部重绘和参考图风格迁移。",
            "custom": False,
        },
        {
            "id": "builtin_whisper",
            "name": "Whisper",
            "kind": "音频识别",
            "source": "OpenAI Whisper / faster-whisper",
            "launch": "python service",
            "min_vram": "CPU可用",
            "notes": "适合字幕、语音转文字和视频素材整理。",
            "custom": False,
        },
        {
            "id": "builtin_sd",
            "name": "Stable Diffusion",
            "kind": "图像生成",
            "source": "Diffusers / ComfyUI",
            "launch": "ComfyUI workflow",
            "min_vram": "6GB",
            "notes": "适合通用文生图、图生图和风格化。",
            "custom": False,
        },
        {
            "id": "builtin_llama",
            "name": "Llama",
            "kind": "语言模型",
            "source": "Ollama / llama.cpp / local API",
            "launch": "local endpoint",
            "min_vram": "按模型大小",
            "notes": "适合本地文案、提示词和自动化助手。",
            "custom": False,
        },
        {
            "id": "builtin_deepseek_api",
            "name": "DeepSeek API",
            "kind": "语言模型",
            "source": "用户自填 HTTPS API Key / Endpoint",
            "launch": "remote endpoint",
            "min_vram": "远程API",
            "notes": "适合提示词优化、生成方案规划、渲染失败诊断和自动化脚本解释。",
            "custom": False,
        },
        {
            "id": "builtin_video_rescue",
            "name": "Video AI Rescue",
            "kind": "视频生成",
            "source": "FFmpeg + ComfyUI + 本机硬件编码",
            "launch": "native fallback pipeline",
            "min_vram": "CPU可用",
            "notes": "视频失败后自动改音频、换 H.264/H.265 编码器、关闭硬件解码并写诊断日志。",
            "custom": False,
        },
    ]


def load_custom_models() -> list[dict]:
    path = model_registry_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        models = data.get("models", []) if isinstance(data, dict) else []
        return [model for model in models if isinstance(model, dict)]
    except Exception:
        return []


def save_custom_models(models: list[dict]):
    path = model_registry_path()
    payload = {
        "version": 1,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "models": models,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_model_catalog() -> list[dict]:
    catalog = builtin_model_catalog()
    catalog.extend(load_custom_models())
    return catalog


def app_executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    run_bat = Path(__file__).resolve().parent / "run.bat"
    return run_bat if run_bat.exists() else Path(sys.executable)


def program_root() -> Path:
    """返回用户能看到的程序目录，打包版为 exe 所在目录，源码版为工程目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def create_desktop_shortcut() -> Path:
    """创建桌面快捷方式，打包版指向 exe，源码版指向 run.bat。"""
    shortcut = desktop_root() / f"{APP_NAME}.lnk"
    if not is_windows():
        return shortcut
    target = app_executable_path()
    icon = resource_root() / "assets" / "app_icon.ico"
    command = (
        "$s=(New-Object -COM WScript.Shell).CreateShortcut('{shortcut}');"
        "$s.TargetPath='{target}';"
        "$s.WorkingDirectory='{workdir}';"
        "$s.IconLocation='{icon}';"
        "$s.Description='{desc}';"
        "$s.Save();"
    ).format(
        shortcut=str(shortcut).replace("'", "''"),
        target=str(target).replace("'", "''"),
        workdir=str(target.parent).replace("'", "''"),
        icon=str(icon).replace("'", "''"),
        desc=APP_NAME,
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0,
    )
    return shortcut


def setup_logging() -> Path:
    path = cache_root() / "logs" / "workstation.log"
    logging.basicConfig(
        filename=str(path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    logging.info("%s %s starting", APP_NAME, APP_VERSION)
    return path


def write_system_profile(screen_profile: dict | None = None, hardware_profile: dict | None = None, defer_hardware: bool = False) -> Path:
    """写入系统适配档案，方便用户和软件后续判断设备能力。"""
    if defer_hardware:
        ffmpeg = {"status": "deferred"}
        gpu = {"name": "后台检测中", "vram_mb": 0, "load": 0, "temperature": None}
    elif hardware_profile:
        ffmpeg = hardware_profile.get("ffmpeg", {})
        gpu = hardware_profile.get("gpu", {})
    else:
        ffmpeg = detect_ffmpeg() if "detect_ffmpeg" in globals() else {}
        gpu = detect_gpu_summary() if "detect_gpu_summary" in globals() else {}
    profile = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "app_id": APP_ID,
        "resource_root": str(resource_root()),
        "runtime_root": str(runtime_root()),
        "cache_root": str(cache_root()),
        "screen": screen_profile or {},
        "ffmpeg": ffmpeg,
        "gpu": gpu,
        "dpi_awareness": SYSTEM_DPI_MODE,
        "windows_app_id": WINDOWS_APP_ID_SET,
        "python": sys.version,
        "frozen": bool(getattr(sys, "frozen", False)),
    }
    path = cache_root() / "settings" / "system_profile.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def install_exception_hook():
    def handle_exception(exc_type, exc_value, exc_traceback):
        message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical("Unhandled exception\n%s", message)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


SYSTEM_DPI_MODE = enable_system_dpi_awareness()
WINDOWS_APP_ID_SET = set_windows_app_id()


def format_bytes(size: float) -> str:
    """把字节转换成更适合界面展示的单位。"""
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", text.strip())
    return slug.strip("-")[:64] or "model"


def detect_screen_profile(app: QApplication) -> dict:
    """读取当前主屏幕尺寸、可用区域和 DPI 缩放，返回 UI 自适应档位。"""
    screen = app.primaryScreen()
    if screen is None:
        return {
            "width": 1280,
            "height": 720,
            "device_pixel_ratio": 1.0,
            "mode": "compact",
        }
    geometry = screen.availableGeometry()
    width = geometry.width()
    height = geometry.height()
    ratio = float(screen.devicePixelRatio())
    screens = app.screens()
    virtual_width = sum(item.availableGeometry().width() for item in screens) if screens else width
    virtual_height = max((item.availableGeometry().height() for item in screens), default=height)
    if width < 1440 or height < 820:
        mode = "compact"
    elif width >= 1800 and height >= 1000:
        mode = "spacious"
    else:
        mode = "regular"
    return {
        "width": width,
        "height": height,
        "screen_count": len(screens),
        "virtual_width": virtual_width,
        "virtual_height": virtual_height,
        "device_pixel_ratio": ratio,
        "dpi_awareness": SYSTEM_DPI_MODE,
        "mode": mode,
    }


def enable_qt_application_attributes():
    """启用 Qt 事件压缩，降低高频鼠标/触摸事件造成的界面卡顿。"""
    for name in ("AA_CompressHighFrequencyEvents", "AA_CompressTabletEvents"):
        attribute = getattr(Qt.ApplicationAttribute, name, None)
        if attribute is not None:
            QApplication.setAttribute(attribute, True)


def build_performance_profile(screen_profile: dict) -> dict:
    """按设备资源决定动画、刷新和缓存策略。"""
    cpu_threads = os.cpu_count() or 4
    memory_gb = 8.0
    if psutil is not None:
        try:
            memory_gb = psutil.virtual_memory().total / 1024 / 1024 / 1024
        except Exception:
            memory_gb = 8.0

    mode = screen_profile.get("mode", "regular")
    ratio = float(screen_profile.get("device_pixel_ratio", 1.0) or 1.0)
    if memory_gb < 10 or cpu_threads <= 4 or mode == "compact":
        level = "eco"
    elif memory_gb >= 24 and cpu_threads >= 12 and mode == "spacious":
        level = "high"
    else:
        level = "balanced"

    return {
        "level": level,
        "cpu_threads": cpu_threads,
        "memory_gb": round(memory_gb, 1),
        "reduce_motion": level == "eco" or ratio >= 1.75,
        "page_fade": level == "high",
        "page_slide": level != "eco",
        "nav_motion": True,
        "toast_motion": level != "eco",
        "animation_ms": 120 if level == "eco" else 180 if level == "balanced" else 240,
        "gpu_refresh_ms": 3600 if level == "eco" else 2600,
        "preview_cache_mb": 96 if level == "eco" else 192 if level == "balanced" else 320,
        "batch_ui_interval": 8 if level == "eco" else 4,
    }


def configure_qt_runtime_cache(performance: dict):
    """按性能档位设置 Qt 图片缓存，减少重复预览时的重采样压力。"""
    cache_mb = int(performance.get("preview_cache_mb", 128))
    QPixmapCache.setCacheLimit(max(64, cache_mb) * 1024)


def fast_default_video_profile() -> dict:
    """启动阶段的轻量视频配置，真实硬件检测交给后台线程完成。"""
    return {
        "gpu": {"name": "后台检测中", "vram_mb": 0, "load": 0, "temperature": None},
        "ffmpeg": {"ffmpeg": "", "ffprobe": "", "nvenc": False, "qsv": False, "amf": False, "libx264": False},
        "edge": 1080,
        "fps": 60,
        "sharpen": 0.32,
        "encoder": "auto",
        "threads": max(2, min((os.cpu_count() or 4) // 2, 8)),
    }


def find_executable(name: str) -> str:
    """寻找本机可执行文件，优先使用工作站自带工具，再回退到系统目录。"""
    direct = os.environ.get(f"{name.upper()}_PATH", "")
    if direct and Path(direct).exists():
        return direct
    app_root = resource_root()
    bundled_roots = [
        app_root / "tools" / "ffmpeg",
        app_root / "tools",
    ]
    for root in bundled_roots:
        if root.exists():
            direct_candidate = root / "bin" / f"{name}.exe"
            if direct_candidate.exists():
                return str(direct_candidate)
            for candidate in root.glob(f"**/{name}.exe"):
                if candidate.exists():
                    return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    candidates = []
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        program_data = os.environ.get("ProgramData", "C:\\ProgramData")
        candidates.extend([
            str(Path(program_data) / "GamePPPublic" / "PCBenchmark" / f"{name}.exe"),
            str(Path(local) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"),
        ])
        if name.lower() == "nvidia-smi":
            candidates.extend([
                str(Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe"),
                str(Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32" / "nvidia-smi.exe"),
            ])
        package_root = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if package_root.exists():
            candidates.extend(str(path) for path in package_root.glob(f"**/{name}.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def detect_gpu_summary() -> dict:
    """读取 GPU 名称和显存，优先使用 GPUtil。"""
    global _GPU_SUMMARY_CACHE
    if _GPU_SUMMARY_CACHE is not None:
        return dict(_GPU_SUMMARY_CACHE)
    summary = {"name": "未检测到独立 GPU", "vram_mb": 0, "load": 0, "temperature": None}
    if GPUtil is not None:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                summary.update({
                    "name": gpu.name,
                    "vram_mb": int(gpu.memoryTotal or 0),
                    "load": int((gpu.load or 0) * 100),
                    "temperature": gpu.temperature,
                })
                _GPU_SUMMARY_CACHE = dict(summary)
                return summary
        except Exception:
            pass
    if os.name == "nt":
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object -First 1 Name,AdapterRAM | ConvertTo-Json -Compress",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="ignore",
            )
            if completed.stdout.strip():
                row = json.loads(completed.stdout)
                summary["name"] = str(row.get("Name") or summary["name"])
                adapter_ram = row.get("AdapterRAM") or 0
                summary["vram_mb"] = int(float(adapter_ram) / 1024 / 1024)
                if "rtx 4060" in summary["name"].lower() and summary["vram_mb"] <= 4096:
                    summary["vram_mb"] = 8192
        except Exception:
            pass
    _GPU_SUMMARY_CACHE = dict(summary)
    return summary


def detect_live_gpu_metrics() -> dict:
    """读取 GPU 实时数据，优先 nvidia-smi，避免 GPUtil 缺 distutils 时失效。"""
    fallback = detect_gpu_summary()
    metrics = {
        "available": fallback.get("vram_mb", 0) > 0 or "未检测" not in fallback.get("name", ""),
        "source": "WMI",
        "name": fallback.get("name", "未检测到独立 GPU"),
        "load": fallback.get("load", 0) or 0,
        "temperature": fallback.get("temperature"),
        "memory_used": 0,
        "memory_total": fallback.get("vram_mb", 0) or 0,
    }

    nvidia_smi = find_executable("nvidia-smi")
    if nvidia_smi:
        try:
            completed = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            line = (completed.stdout or "").strip().splitlines()[0]
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 5:
                name, load, temperature, memory_used, memory_total = parts[:5]
                metrics.update({
                    "available": True,
                    "source": "nvidia-smi",
                    "name": name or metrics["name"],
                    "load": float(load) if load.replace(".", "", 1).isdigit() else 0,
                    "temperature": float(temperature) if temperature.replace(".", "", 1).isdigit() else None,
                    "memory_used": float(memory_used) if memory_used.replace(".", "", 1).isdigit() else 0,
                    "memory_total": float(memory_total) if memory_total.replace(".", "", 1).isdigit() else metrics["memory_total"],
                })
                return metrics
        except Exception:
            pass

    if GPUtil is not None:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                metrics.update({
                    "available": True,
                    "source": "GPUtil",
                    "name": gpu.name,
                    "load": float(gpu.load or 0) * 100,
                    "temperature": gpu.temperature,
                    "memory_used": float(gpu.memoryUsed or 0),
                    "memory_total": float(gpu.memoryTotal or 0),
                })
                return metrics
        except Exception:
            pass

    return metrics


def detect_ffmpeg() -> dict:
    """检测 FFmpeg、FFprobe 和硬件编码器。"""
    global _FFMPEG_CACHE
    if _FFMPEG_CACHE is not None:
        return dict(_FFMPEG_CACHE)
    ffmpeg = find_executable("ffmpeg")
    ffprobe = find_executable("ffprobe")
    encoders_text = ""
    if ffmpeg:
        try:
            completed = subprocess.run(
                [ffmpeg, "-hide_banner", "-encoders"],
                check=False,
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="ignore",
            )
            encoders_text = (completed.stdout or "") + (completed.stderr or "")
        except Exception:
            encoders_text = ""
    result = {
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "nvenc": "h264_nvenc" in encoders_text,
        "hevc_nvenc": "hevc_nvenc" in encoders_text,
        "qsv": "h264_qsv" in encoders_text,
        "hevc_qsv": "hevc_qsv" in encoders_text,
        "amf": "h264_amf" in encoders_text,
        "hevc_amf": "hevc_amf" in encoders_text,
        "libx264": "libx264" in encoders_text,
        "libx265": "libx265" in encoders_text,
    }
    _FFMPEG_CACHE = dict(result)
    return result


def build_medium_video_profile() -> dict:
    """按用户设备选择中等调用策略，不把机器资源打满。"""
    gpu = detect_gpu_summary()
    ffmpeg = detect_ffmpeg()
    vram = gpu.get("vram_mb", 0)
    if vram >= 10000:
        edge = 1440
        fps = 60
        sharpen = 0.48
    elif vram >= 6000:
        edge = 1080
        fps = 60
        sharpen = 0.36
    else:
        edge = 720
        fps = 30
        sharpen = 0.24
    encoder = "libx264"
    if ffmpeg.get("nvenc"):
        encoder = "h264_nvenc"
    elif ffmpeg.get("qsv"):
        encoder = "h264_qsv"
    elif ffmpeg.get("amf"):
        encoder = "h264_amf"
    return {
        "gpu": gpu,
        "ffmpeg": ffmpeg,
        "edge": edge,
        "fps": fps,
        "sharpen": sharpen,
        "encoder": encoder,
        "threads": max(2, min((os.cpu_count() or 4) // 2, 8)),
    }


VIDEO_MODE_SETTINGS = {
    "极速预览": {
        "edge": 720,
        "fps": 30,
        "sharpen": 0.16,
        "scale_flags": "bicubic",
        "denoise": False,
        "interpolate": False,
        "nvenc_preset": "p2",
        "cq": "25",
        "crf": "23",
        "audio": "copy",
        "note": "最快预览，适合先看构图和节奏",
    },
    "均衡加速": {
        "edge": 1080,
        "fps": 60,
        "sharpen": 0.32,
        "scale_flags": "bicubic",
        "denoise": False,
        "interpolate": False,
        "nvenc_preset": "p3",
        "cq": "22",
        "crf": "20",
        "audio": "copy",
        "note": "默认推荐，速度和清晰度比较均衡",
    },
    "高清输出": {
        "edge": 1440,
        "fps": 60,
        "sharpen": 0.58,
        "scale_flags": "lanczos",
        "denoise": True,
        "interpolate": False,
        "nvenc_preset": "p5",
        "cq": "19",
        "crf": "18",
        "audio": "aac",
        "note": "画质优先，会比默认模式更慢",
    },
    "120帧补帧": {
        "edge": 1080,
        "fps": 120,
        "sharpen": 0.42,
        "scale_flags": "bicubic",
        "denoise": False,
        "interpolate": True,
        "nvenc_preset": "p4",
        "cq": "21",
        "crf": "19",
        "audio": "copy",
        "note": "AI补帧最吃CPU，适合短视频片段",
    },
    "移动端清晰": {
        "edge": 1080,
        "fps": 60,
        "sharpen": 0.28,
        "scale_flags": "bicubic",
        "denoise": False,
        "interpolate": False,
        "nvenc_preset": "p3",
        "cq": "23",
        "crf": "21",
        "audio": "aac",
        "note": "面向手机端播放，控制体积同时保持清晰",
    },
}


def video_mode_options(mode_name: str) -> dict:
    return VIDEO_MODE_SETTINGS.get(mode_name, VIDEO_MODE_SETTINGS["均衡加速"])


VIDEO_GRADE_PRESETS = {
    "自然增强": {"contrast": 1.06, "saturation": 1.08, "brightness": 0.01, "gamma": 1.00, "rs": 0.0, "bs": 0.0, "note": "自然提亮和轻微增艳，适合日常素材"},
    "电影胶片": {"contrast": 1.10, "saturation": 0.90, "brightness": -0.01, "gamma": 1.04, "rs": 0.035, "bs": -0.045, "note": "压一点饱和和亮度，偏胶片叙事感"},
    "霓虹赛博": {"contrast": 1.16, "saturation": 1.32, "brightness": 0.015, "gamma": 0.98, "rs": -0.025, "bs": 0.085, "note": "强化蓝紫霓虹和高对比，适合科技感视频"},
    "商业干净": {"contrast": 1.04, "saturation": 1.03, "brightness": 0.018, "gamma": 1.00, "rs": 0.0, "bs": -0.01, "note": "干净、明亮、少风格化，适合产品展示"},
    "建筑HDR": {"contrast": 1.20, "saturation": 1.10, "brightness": 0.0, "gamma": 0.96, "rs": -0.01, "bs": 0.018, "note": "加强建筑线条、暗部和天空层次"},
    "人像通透": {"contrast": 1.03, "saturation": 1.06, "brightness": 0.018, "gamma": 1.03, "rs": 0.025, "bs": -0.02, "note": "肤色更暖更通透，避免过度锐化"},
    "暗调电影": {"contrast": 1.22, "saturation": 0.84, "brightness": -0.035, "gamma": 1.08, "rs": 0.02, "bs": 0.035, "note": "暗部压低、反差更强，适合情绪短片"},
}


ENCODE_QUALITY_SETTINGS = {
    "极速": {"cq_delta": 3, "crf_delta": 3, "preset_bias": -1, "bitrate": "8M", "audio_bitrate": "160k"},
    "均衡": {"cq_delta": 0, "crf_delta": 0, "preset_bias": 0, "bitrate": "14M", "audio_bitrate": "192k"},
    "高画质": {"cq_delta": -3, "crf_delta": -3, "preset_bias": 1, "bitrate": "24M", "audio_bitrate": "256k"},
    "母版": {"cq_delta": -6, "crf_delta": -6, "preset_bias": 2, "bitrate": "45M", "audio_bitrate": "320k"},
}


def video_grade_options(grade_name: str) -> dict:
    return VIDEO_GRADE_PRESETS.get(grade_name, VIDEO_GRADE_PRESETS["自然增强"])


def encode_quality_options(quality_name: str, mode_name: str) -> dict:
    options = dict(video_mode_options(mode_name))
    quality = ENCODE_QUALITY_SETTINGS.get(quality_name, ENCODE_QUALITY_SETTINGS["均衡"])
    options["cq"] = str(max(12, min(34, int(options["cq"]) + int(quality["cq_delta"]))))
    options["crf"] = str(max(12, min(30, int(options["crf"]) + int(quality["crf_delta"]))))
    options["bitrate"] = quality["bitrate"]
    options["audio_bitrate"] = quality["audio_bitrate"]
    options["quality_name"] = quality_name
    return options


def resolve_auto_encoder(ffmpeg: dict, codec_mode: str) -> str:
    wants_hevc = codec_mode == "H.265高压缩"
    if wants_hevc:
        if ffmpeg.get("hevc_nvenc"):
            return "hevc_nvenc"
        if ffmpeg.get("hevc_qsv"):
            return "hevc_qsv"
        if ffmpeg.get("hevc_amf"):
            return "hevc_amf"
        if ffmpeg.get("libx265"):
            return "libx265"
    if ffmpeg.get("nvenc"):
        return "h264_nvenc"
    if ffmpeg.get("qsv"):
        return "h264_qsv"
    if ffmpeg.get("amf"):
        return "h264_amf"
    return "libx264"


def compatible_h264_encoder(ffmpeg: dict) -> str:
    if ffmpeg.get("nvenc"):
        return "h264_nvenc"
    if ffmpeg.get("qsv"):
        return "h264_qsv"
    if ffmpeg.get("amf"):
        return "h264_amf"
    return "libx264"


def encoder_arguments(encoder: str, mode_name: str = "均衡加速", quality_name: str = "均衡") -> list[str]:
    """返回真实进入 FFmpeg 的编码参数。"""
    options = encode_quality_options(quality_name, mode_name)
    cq = options["cq"]
    crf = options["crf"]
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", options["nvenc_preset"], "-rc", "vbr", "-cq", cq, "-b:v", "0"]
    if encoder == "hevc_nvenc":
        return ["-c:v", "hevc_nvenc", "-preset", options["nvenc_preset"], "-rc", "vbr", "-cq", cq, "-b:v", "0", "-tag:v", "hvc1"]
    if encoder == "h264_qsv":
        return ["-c:v", "h264_qsv", "-global_quality", cq]
    if encoder == "hevc_qsv":
        return ["-c:v", "hevc_qsv", "-global_quality", cq, "-tag:v", "hvc1"]
    if encoder == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "speed" if mode_name == "极速预览" else "balanced", "-qp_i", cq, "-qp_p", str(int(cq) + 2)]
    if encoder == "hevc_amf":
        return ["-c:v", "hevc_amf", "-quality", "balanced", "-qp_i", cq, "-qp_p", str(int(cq) + 2), "-tag:v", "hvc1"]
    if encoder == "libx265":
        preset = "ultrafast" if quality_name == "极速" else "medium" if quality_name in ("均衡", "高画质") else "slow"
        return ["-c:v", "libx265", "-preset", preset, "-crf", crf, "-tag:v", "hvc1"]
    preset = "veryfast" if quality_name == "极速" else "medium" if quality_name in ("均衡", "高画质") else "slow"
    return ["-c:v", "libx264", "-preset", preset, "-crf", crf]


def audio_arguments(mode_name: str, audio_mode: str = "自动", quality_name: str = "均衡") -> list[str]:
    options = encode_quality_options(quality_name, mode_name)
    if audio_mode == "静音":
        return ["-an"]
    if audio_mode == "复制原音" or (audio_mode == "自动" and video_mode_options(mode_name).get("audio") == "copy"):
        return ["-c:a", "copy"]
    bitrate = "320k" if audio_mode == "AAC 320k" else options.get("audio_bitrate", "192k")
    return ["-c:a", "aac", "-b:a", bitrate]


def video_grade_filter(grade_name: str, strength: int) -> str:
    preset = video_grade_options(grade_name)
    amount = max(0.0, min(1.0, strength / 100))
    contrast = 1 + (preset["contrast"] - 1) * amount
    saturation = 1 + (preset["saturation"] - 1) * amount
    brightness = preset["brightness"] * amount
    gamma = 1 + (preset["gamma"] - 1) * amount
    filters = [f"eq=contrast={contrast:.3f}:saturation={saturation:.3f}:brightness={brightness:.3f}:gamma={gamma:.3f}"]
    rs = preset.get("rs", 0) * amount
    bs = preset.get("bs", 0) * amount
    if abs(rs) > 0.001 or abs(bs) > 0.001:
        filters.append(f"colorbalance=rs={rs:.3f}:bs={bs:.3f}:rm={rs * 0.45:.3f}:bm={bs * 0.45:.3f}:rh={rs * 0.3:.3f}:bh={bs * 0.3:.3f}")
    return ",".join(filters)


def video_filter_chain(edge: int, fps: int, sharpen: float, mode_name: str = "均衡加速", grade_name: str = "自然增强", grade_strength: int = 65) -> str:
    options = video_mode_options(mode_name)
    filters = [
        f"scale='if(gte(iw,ih),{edge},-2)':'if(gte(iw,ih),-2,{edge})':flags={options['scale_flags']}",
    ]
    if options.get("denoise"):
        filters.append("hqdn3d=0.8:0.7:2.4:2.0")
    if grade_strength > 0:
        filters.append(video_grade_filter(grade_name, grade_strength))
    if fps >= 120 and options.get("interpolate"):
        filters.append(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    else:
        filters.append(f"fps={fps}")
    if sharpen > 0:
        filters.append(f"unsharp=5:5:{sharpen:.2f}:3:3:{sharpen * 0.42:.2f}")
    filters.append("format=yuv420p")
    return ",".join(filters)


def find_comfyui_root() -> str:
    """查找常见 ComfyUI 安装目录；找到 main.py 才认为可启动。"""
    app_root = resource_root()
    raw_candidates = [
        os.environ.get("COMFYUI_PATH", ""),
        app_root / "tools" / "ComfyUI",
        app_root / "ComfyUI",
        Path("D:/ComfyUI"),
        Path("E:/ComfyUI"),
        Path("D:/AI/ComfyUI"),
        Path("E:/AI/ComfyUI"),
        Path("D:/ComfyUI_windows_portable/ComfyUI"),
        Path("E:/ComfyUI_windows_portable/ComfyUI"),
    ]
    for candidate in raw_candidates:
        if not candidate:
            continue
        root = Path(candidate)
        if (root / "main.py").exists():
            return str(root)
    return ""


def comfy_status(url: str = "http://127.0.0.1:8188") -> dict:
    """检测本机 ComfyUI 和 FLUX.1 Kontext Dev 常用模型文件。"""
    candidates = []
    for value in (url, os.environ.get("COMFYUI_URL", ""), "http://127.0.0.1:8188", "http://localhost:8188", "http://127.0.0.1:8189"):
        if value:
            normalized = value.strip().rstrip("/")
            if normalized and normalized not in candidates:
                candidates.append(normalized)

    preferred_url = candidates[0] if candidates else ""
    status = {"reachable": False, "url": preferred_url, "model_ready": False, "detail": "ComfyUI 未连接"}
    last_error = ""
    preferred_error = ""
    for index, base in enumerate(candidates):
        try:
            with urllib.request.urlopen(f"{base}/system_stats", timeout=3) as response:
                status["system"] = json.loads(response.read().decode("utf-8", errors="ignore") or "{}")
            status["reachable"] = True
            status["url"] = base
            status["detail"] = "ComfyUI 已连接"
            break
        except urllib.error.HTTPError as error:
            last_error = f"{base} 有响应，但不是 ComfyUI API：HTTP {error.code}"
        except urllib.error.URLError as error:
            reason = str(error.reason) if hasattr(error, "reason") else str(error)
            if "actively refused" in reason.lower() or "积极拒绝" in reason:
                last_error = f"{base} 连接被拒绝：ComfyUI 没有启动或端口不对"
            else:
                last_error = f"{base} 无法连接：{reason[:120]}"
        except Exception as error:
            last_error = f"{base} 检测失败：{str(error)[:120]}"
        if index == 0:
            preferred_error = last_error

    if not status["reachable"]:
        root = find_comfyui_root()
        status["url"] = preferred_url
        status["detail"] = f"{preferred_error or last_error or 'ComfyUI 未启动'}；视频本地 FFmpeg/NVENC 渲染仍可用"
        status["install_path"] = root
        return status

    model_names = {
        "flux1-dev-kontext_fp8_scaled.safetensors",
        "clip_l.safetensors",
        "t5xxl_fp8_e4m3fn_scaled.safetensors",
        "ae.safetensors",
    }
    found_text = ""
    for folder in ("diffusion_models", "unet", "text_encoders", "clip", "vae"):
        try:
            with urllib.request.urlopen(f"{base}/models/{folder}", timeout=5) as response:
                found_text += response.read().decode("utf-8", errors="ignore").lower()
        except Exception:
            pass
    status["model_ready"] = all(name.lower() in found_text for name in model_names)
    if status["reachable"] and not status["model_ready"]:
        status["detail"] = "ComfyUI 已连接，FLUX.1 Kontext Dev 模型文件待确认"
    if status["model_ready"]:
        status["detail"] = "ComfyUI + FLUX.1 Kontext Dev 就绪"
    return status


def pil_to_pixmap(image, max_width=520, max_height=340):
    """把 PIL Image 转成适合 QLabel 展示的 QPixmap。"""
    if Image is None:
        return QPixmap()

    preview = image.convert("RGB").copy()
    preview.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    data = preview.tobytes("raw", "RGB")
    qimage = QImage(data, preview.width, preview.height, preview.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


def load_preview_pixmap(path, max_width=520, max_height=340):
    """读取图片并生成预览图。"""
    if Image is None:
        return QPixmap()
    with Image.open(path) as image:
        return pil_to_pixmap(image, max_width, max_height)


def resize_for_processing(image, max_edge):
    """限制处理尺寸，避免桌面端首次生成时占用过高内存。"""
    working = image.convert("RGB")
    edge = max(512, int(max_edge))
    if max(working.size) <= edge:
        return working
    scale = edge / max(working.size)
    width = max(1, int(working.width * scale))
    height = max(1, int(working.height * scale))
    return working.resize((width, height), Image.Resampling.LANCZOS)


def fit_size_to_edge(size, max_edge):
    width, height = size
    edge = max(1, int(max_edge))
    if max(width, height) <= edge:
        return width, height
    scale = edge / max(width, height)
    return max(1, int(width * scale)), max(1, int(height * scale))


def output_size_for_policy(original_size, processed_size, settings):
    policy = settings.get("output_resolution", "source_native")
    cap = max(1600, min(16384, int(settings.get("output_max_edge", settings.get("max_edge", 8192)))))
    original_size = fit_size_to_edge(original_size, cap)
    if policy in ("processed", "processing"):
        return processed_size
    if policy in ("source_native", "native", "原图原生"):
        return original_size
    if policy in ("long_4k", "4k"):
        return fit_size_to_edge(original_size, 4096)
    if policy in ("long_8k", "8k"):
        return fit_size_to_edge(original_size, min(cap, 8192))
    if policy in ("smart_2x", "2x"):
        doubled = (original_size[0] * 2, original_size[1] * 2)
        return fit_size_to_edge(doubled, cap)
    return original_size


def progressive_resize(image, target_size):
    """Upscale in small steps so large output does not become soft and smeared."""
    if image.size == target_size:
        return image

    target_w, target_h = target_size
    output = image
    if target_w > output.width or target_h > output.height:
        while output.width * 2 < target_w and output.height * 2 < target_h:
            output = output.resize((output.width * 2, output.height * 2), Image.Resampling.LANCZOS)
            output = output.filter(ImageFilter.UnsharpMask(radius=0.38, percent=34, threshold=2))

    return output.resize(target_size, Image.Resampling.LANCZOS)


def guided_detail_reconstruction(output, original_source, settings):
    """Use the original photo's luma edges as a guide for crisp high-resolution output."""
    strength = max(0.0, min(1.0, settings.get("super_detail", 86) / 100.0))
    if strength <= 0:
        return output

    source_guide = progressive_resize(original_source.convert("RGB"), output.size)
    output_y, output_cb, output_cr = output.convert("YCbCr").split()
    guide_y = source_guide.convert("L")

    edge_mask = guide_y.filter(ImageFilter.FIND_EDGES)
    edge_mask = ImageEnhance.Contrast(edge_mask).enhance(3.0 + strength * 2.0)
    edge_mask = edge_mask.point(lambda value: 255 if value > 18 else int(value * 0.25))
    edge_mask = edge_mask.filter(ImageFilter.GaussianBlur(0.65))

    detail_y = guide_y.filter(
        ImageFilter.UnsharpMask(radius=0.55, percent=int(145 + 120 * strength), threshold=2)
    )
    blended_y = Image.blend(output_y, detail_y, 0.18 + 0.28 * strength)
    reconstructed_y = Image.composite(blended_y, output_y, edge_mask)

    reconstructed = Image.merge("YCbCr", (reconstructed_y, output_cb, output_cr)).convert("RGB")
    return reconstructed.filter(
        ImageFilter.UnsharpMask(radius=0.45, percent=int(65 + 85 * strength), threshold=2)
    )


def reconstruct_super_resolution(image, original_source, target_size, settings):
    output = progressive_resize(image, target_size)
    if max(target_size) > max(image.size):
        output = guided_detail_reconstruction(output, original_source, settings)
    elif settings.get("super_detail", 86) > 0:
        output = output.filter(ImageFilter.UnsharpMask(radius=0.35, percent=36, threshold=2))
    return output


def finalize_output_resolution(image, original_source, settings):
    if hasattr(original_source, "size"):
        original_size = original_source.size
        detail_source = original_source
    else:
        original_size = original_source
        detail_source = image

    target_size = output_size_for_policy(original_size, image.size, settings)
    if target_size == image.size:
        return reconstruct_super_resolution(image, detail_source, target_size, settings)
    return reconstruct_super_resolution(image, detail_source, target_size, settings)


def clamp_channel(value):
    return max(0, min(255, int(round(value))))


def transfer_reference_color(source, reference, amount):
    """按 RGB 通道均值和方差迁移参考图色彩，作为原生版基础算法。"""
    if amount <= 0:
        return source

    source_channels = source.split()
    reference_channels = reference.resize(source.size, Image.Resampling.BICUBIC).split()
    source_stat = ImageStat.Stat(source)
    reference_stat = ImageStat.Stat(reference.resize(source.size, Image.Resampling.BICUBIC))

    result_channels = []
    for index, channel in enumerate(source_channels):
        source_mean = source_stat.mean[index]
        source_std = max(1.0, source_stat.stddev[index])
        reference_mean = reference_stat.mean[index]
        reference_std = max(1.0, reference_stat.stddev[index])
        ratio = reference_std / source_std
        lut = [clamp_channel((value - source_mean) * ratio + reference_mean) for value in range(256)]
        transferred = channel.point(lut)
        result_channels.append(Image.blend(channel, transferred, amount))
    return Image.merge("RGB", result_channels)


def transfer_reference_tone(source, reference, amount):
    """迁移参考图明暗范围，并保留原图结构。"""
    if amount <= 0:
        return source

    reference_gray = ImageOps.grayscale(reference.resize(source.size, Image.Resampling.BICUBIC))
    source_gray = ImageOps.grayscale(source)
    source_stat = ImageStat.Stat(source_gray)
    reference_stat = ImageStat.Stat(reference_gray)
    source_mean = source_stat.mean[0]
    source_std = max(1.0, source_stat.stddev[0])
    reference_mean = reference_stat.mean[0]
    reference_std = max(1.0, reference_stat.stddev[0])
    ratio = reference_std / source_std
    lut = [clamp_channel((value - source_mean) * ratio + reference_mean) for value in range(256)]
    tone = ImageOps.grayscale(source).point(lut).convert("RGB")
    color = Image.blend(source, ImageChops.multiply(source, tone), 0.18)
    return Image.blend(source, color, amount)


def apply_bloom(image, amount):
    """给亮部增加轻微辉光。"""
    if amount <= 0:
        return image
    glow = image.filter(ImageFilter.GaussianBlur(radius=10 + amount * 18))
    screened = ImageChops.screen(image, glow)
    return Image.blend(image, screened, min(0.55, amount))


def apply_temperature_tint(image, temperature, tint):
    """模拟冷暖和青洋红偏移。"""
    if temperature == 0 and tint == 0:
        return image
    r, g, b = image.split()
    r = r.point(lambda value: clamp_channel(value + temperature * 0.42 + tint * 0.12))
    g = g.point(lambda value: clamp_channel(value - abs(tint) * 0.08))
    b = b.point(lambda value: clamp_channel(value - temperature * 0.36 - tint * 0.18))
    return Image.merge("RGB", (r, g, b))


def apply_highlights_shadows(image, highlights, shadows):
    """对高光和暗部做基础保护/提升。"""
    if highlights == 0 and shadows == 0:
        return image
    gray = ImageOps.grayscale(image)
    highlight_mask = gray.point(lambda value: max(0, min(255, int((value - 150) * 2.4))))
    shadow_mask = gray.point(lambda value: max(0, min(255, int((120 - value) * 2.2))))
    if highlights:
        target = ImageEnhance.Brightness(image).enhance(1 + highlights / 180)
        image = Image.composite(target, image, highlight_mask)
    if shadows:
        target = ImageEnhance.Brightness(image).enhance(1 + shadows / 160)
        image = Image.composite(target, image, shadow_mask)
    return image


def apply_fade(image, amount):
    """模拟胶片褪黑。"""
    if amount <= 0:
        return image
    veil = Image.new("RGB", image.size, (28, 31, 34))
    lifted = ImageChops.screen(image, veil)
    return Image.blend(image, lifted, min(0.42, amount))


def apply_vignette(image, amount):
    """添加轻微暗角。"""
    if amount <= 0:
        return image
    width, height = image.size
    scale = min(1.0, 420 / max(width, height))
    mask_size = (max(2, int(width * scale)), max(2, int(height * scale)))
    mask = Image.new("L", mask_size, 0)
    pixels = mask.load()
    center_x, center_y = mask_size[0] / 2, mask_size[1] / 2
    max_distance = (center_x * center_x + center_y * center_y) ** 0.5
    for y in range(mask_size[1]):
        for x in range(mask_size[0]):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            value = int(max(0, min(255, ((distance / max_distance) - 0.32) * 360 * amount)))
            pixels[x, y] = value
    mask = mask.resize((width, height), Image.Resampling.BICUBIC)
    dark = ImageEnhance.Brightness(image).enhance(max(0.35, 1 - amount * 0.72))
    return Image.composite(dark, image, mask.filter(ImageFilter.GaussianBlur(18)))


def apply_grain(image, amount):
    """增加细颗粒。"""
    if amount <= 0:
        return image
    random.seed(42)
    noise = Image.effect_noise(image.size, 22 + amount * 70).convert("L")
    noise = ImageEnhance.Contrast(noise).enhance(1.2)
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(image, ImageChops.overlay(image, noise_rgb), min(0.28, amount * 0.42))


def apply_mode_grade(image, mode, strength):
    """没有参考图时，按专业模式生成一个目标风格。"""
    if mode == "film":
        image = apply_temperature_tint(image, 14 * strength, 4 * strength)
        image = apply_fade(image, 0.18 * strength)
        image = apply_grain(image, 0.22 * strength)
    elif mode == "neon":
        image = apply_temperature_tint(image, -12 * strength, 18 * strength)
        image = ImageEnhance.Color(image).enhance(1 + 0.38 * strength)
        image = apply_bloom(image, 0.25 * strength)
    elif mode == "clean":
        image = ImageEnhance.Color(image).enhance(0.96)
        image = ImageEnhance.Contrast(image).enhance(1 + 0.08 * strength)
    elif mode == "hdr":
        image = apply_highlights_shadows(image, -22 * strength, 34 * strength)
        image = ImageEnhance.Contrast(image).enhance(1 + 0.28 * strength)
    elif mode == "portrait":
        image = apply_temperature_tint(image, 8 * strength, 5 * strength)
        image = ImageEnhance.Contrast(image).enhance(1 - 0.08 * strength)
    elif mode == "travel":
        image = apply_temperature_tint(image, 4 * strength, -4 * strength)
        image = ImageEnhance.Color(image).enhance(1 + 0.22 * strength)
    elif mode == "moody":
        image = ImageEnhance.Brightness(image).enhance(1 - 0.12 * strength)
        image = ImageEnhance.Contrast(image).enhance(1 + 0.34 * strength)
        image = apply_vignette(image, 0.28 * strength)
    elif mode == "product":
        image = ImageEnhance.Sharpness(image).enhance(1 + 1.2 * strength)
        image = ImageEnhance.Contrast(image).enhance(1 + 0.16 * strength)
    elif mode == "sunset":
        image = apply_temperature_tint(image, 34 * strength, 10 * strength)
        image = apply_bloom(image, 0.16 * strength)
    return image


def _small_analysis_image(image, max_edge=760):
    working = image.convert("RGB")
    if max(working.size) <= max_edge:
        return working
    scale = max_edge / max(working.size)
    return working.resize((max(1, int(working.width * scale)), max(1, int(working.height * scale))), Image.Resampling.BICUBIC)


def _finish_mask(mask, size, blur=18, strength=1.0):
    if mask.size != size:
        mask = mask.resize(size, Image.Resampling.BICUBIC)
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    if strength < 1:
        mask = mask.point(lambda value: int(value * strength))
    return mask


def ai_center_subject_mask(image):
    """轻量主体权重：中心区域 + 边缘结构，模拟本地 AI 的关注区域。"""
    small = _small_analysis_image(image)
    width, height = small.size
    radial = Image.new("L", small.size, 0)
    pixels = radial.load()
    center_x, center_y = width / 2, height / 2
    radius = max(width, height) * 0.58
    for y in range(height):
        for x in range(width):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            pixels[x, y] = max(0, min(255, int(255 * (1 - distance / radius))))
    edges = ImageOps.grayscale(small).filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges).point(lambda value: 170 if value > 32 else 0)
    mask = ImageChops.lighter(radial, edges.filter(ImageFilter.GaussianBlur(5)))
    return _finish_mask(mask, image.size, blur=22, strength=0.86)


def ai_luminance_mask(image, kind):
    small = _small_analysis_image(image)
    gray = ImageOps.grayscale(small)
    if kind == "highlights":
        mask = gray.point(lambda value: max(0, min(255, int((value - 146) * 2.25))))
        return _finish_mask(mask, image.size, blur=16, strength=0.9)
    mask = gray.point(lambda value: max(0, min(255, int((132 - value) * 2.4))))
    return _finish_mask(mask, image.size, blur=18, strength=0.92)


def ai_edge_mask(image):
    small = _small_analysis_image(image)
    edges = ImageOps.grayscale(small).filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges).point(lambda value: 255 if value > 28 else 0)
    return _finish_mask(edges, image.size, blur=2, strength=0.76)


def ai_skin_mask(image):
    """基于肤色范围的快速人物保护蒙版；没有明显肤色时回退到主体蒙版。"""
    small = _small_analysis_image(image, 620)
    source = small.convert("RGB")
    mask = Image.new("L", source.size, 0)
    source_pixels = source.load()
    mask_pixels = mask.load()
    hits = 0
    for y in range(source.height):
        for x in range(source.width):
            r, g, b = source_pixels[x, y]
            warm_skin = r > 84 and g > 38 and b > 24 and r > g * 1.05 and r > b * 1.18 and abs(r - g) > 10
            soft_skin = r > 120 and g > 82 and b > 58 and r > g and g > b and (r - b) > 24
            if warm_skin or soft_skin:
                mask_pixels[x, y] = 235
                hits += 1
    if hits < source.width * source.height * 0.006:
        return ai_center_subject_mask(image)
    return _finish_mask(mask, image.size, blur=14, strength=0.82)


def choose_ai_local_mode(source, settings):
    requested = settings.get("local_mode", "auto")
    if requested not in ("auto", "smart"):
        return requested
    prompt = settings.get("creative_prompt", "").lower()
    style = settings.get("style_mode", "")
    if any(word in prompt for word in ("肤色", "皮肤", "人像", "脸", "portrait")) or style == "portrait":
        return "skin"
    if any(word in prompt for word in ("天空", "高光", "过曝")) or settings.get("highlights", 0) < -18:
        return "highlights"
    if any(word in prompt for word in ("暗部", "阴影", "夜景")) or settings.get("shadows", 0) > 24:
        return "shadows"
    if any(word in prompt for word in ("边缘", "超清", "细节", "锐化")) or settings.get("clarity", 0) > 56 or style in ("product", "hdr"):
        return "edges"
    if any(word in prompt for word in ("背景", "氛围", "虚化")):
        return "background"

    gray = ImageOps.grayscale(_small_analysis_image(source, 420))
    stat = ImageStat.Stat(gray)
    if stat.mean[0] < 92:
        return "shadows"
    if stat.mean[0] > 176:
        return "highlights"
    return "subject"


def apply_ai_local_enhancement(source, image, settings):
    """按自动区域蒙版做局部增强，让处理不再只是整张图统一套滤镜。"""
    local_mode = choose_ai_local_mode(source, settings)
    if local_mode == "global":
        return image

    strength = max(0.18, min(1.0, settings.get("strength", 72) / 100))
    if local_mode == "skin":
        mask = ai_skin_mask(source)
        enhanced = apply_temperature_tint(image, 5 * strength, 4 * strength)
        enhanced = ImageEnhance.Contrast(enhanced).enhance(1 - 0.05 * strength)
        enhanced = Image.blend(enhanced, enhanced.filter(ImageFilter.SMOOTH_MORE), 0.16 * strength)
    elif local_mode == "highlights":
        mask = ai_luminance_mask(source, "highlights")
        enhanced = apply_highlights_shadows(image, -34 * strength, 0)
        enhanced = ImageEnhance.Contrast(enhanced).enhance(1 + 0.08 * strength)
    elif local_mode == "shadows":
        mask = ai_luminance_mask(source, "shadows")
        enhanced = apply_highlights_shadows(image, 0, 42 * strength)
        enhanced = ImageEnhance.Color(enhanced).enhance(1 + 0.08 * strength)
    elif local_mode == "edges":
        mask = ai_edge_mask(source)
        enhanced = image.filter(ImageFilter.UnsharpMask(radius=1.15, percent=int(92 + 70 * strength), threshold=3))
        enhanced = ImageEnhance.Contrast(enhanced).enhance(1 + 0.08 * strength)
    elif local_mode == "background":
        mask = ImageOps.invert(ai_center_subject_mask(source)).filter(ImageFilter.GaussianBlur(10))
        enhanced = apply_bloom(image, 0.12 * strength)
        enhanced = ImageEnhance.Color(enhanced).enhance(1 + 0.12 * strength)
    else:
        mask = ai_center_subject_mask(source)
        enhanced = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=int(68 + 58 * strength), threshold=4))
        enhanced = ImageEnhance.Contrast(enhanced).enhance(1 + 0.08 * strength)
        enhanced = ImageEnhance.Brightness(enhanced).enhance(1 + 0.025 * strength)

    mask_strength = 0.58 + strength * 0.32
    return Image.composite(enhanced, image, _finish_mask(mask, image.size, blur=0, strength=mask_strength))


def manual_ellipse_window_mask(image, settings):
    small = _small_analysis_image(image, 720)
    width, height = small.size
    center_x = width * max(0, min(100, settings.get("window_x", 50))) / 100
    center_y = height * max(0, min(100, settings.get("window_y", 50))) / 100
    size = max(12, min(170, settings.get("window_size", 100))) / 100
    aspect = max(35, min(220, settings.get("window_aspect", 100))) / 100
    radius_x = max(8, width * 0.43 * size * aspect)
    radius_y = max(8, height * 0.38 * size / max(0.35, aspect))
    mask = Image.new("L", small.size, 0)
    pixels = mask.load()
    for y in range(height):
        for x in range(width):
            distance = ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2
            pixels[x, y] = max(0, min(255, int((1.18 - distance) * 255)))
    return _finish_mask(mask, image.size, blur=8)


def davinci_power_window_mask(image, window_name, settings):
    """达芬奇式 Power Window：用窗口控制局部调整影响范围。"""
    if window_name in ("关闭", "全画面"):
        return Image.new("L", image.size, 255)
    if window_name == "中心圆窗":
        return manual_ellipse_window_mask(image, settings)
    if window_name == "上半天空":
        small = _small_analysis_image(image, 720)
        width, height = small.size
        mask = Image.new("L", small.size, 0)
        pixels = mask.load()
        boundary = max(0.12, min(0.92, settings.get("window_y", 50) / 100))
        softness = max(0.18, min(1.2, settings.get("window_size", 100) / 100))
        for y in range(height):
            value = max(0, min(255, int((boundary + 0.18 * softness - y / max(1, height)) * 430 / softness)))
            for x in range(width):
                pixels[x, y] = value
        return _finish_mask(mask, image.size, blur=14)
    if window_name == "线性渐变":
        small = _small_analysis_image(image, 720)
        width, height = small.size
        mask = Image.new("L", small.size, 0)
        pixels = mask.load()
        start = max(0.02, min(0.92, settings.get("window_y", 50) / 100))
        softness = max(0.2, min(1.6, settings.get("window_size", 100) / 100))
        for y in range(height):
            value = max(0, min(255, int((y / max(1, height) - start + 0.32 * softness) * 330 / softness)))
            for x in range(width):
                pixels[x, y] = value
        return _finish_mask(mask, image.size, blur=18)
    if window_name == "反选背景":
        return ImageOps.invert(ai_center_subject_mask(image))
    subject = ai_center_subject_mask(image)
    return ImageChops.multiply(subject, manual_ellipse_window_mask(image, settings))


def manual_luma_range_mask(image, settings):
    low = max(0, min(255, int(settings.get("luma_low", 0))))
    high = max(0, min(255, int(settings.get("luma_high", 255))))
    if low > high:
        low, high = high, low
    softness = max(1, min(100, int(settings.get("qualifier_softness", 32))))
    small = _small_analysis_image(image, 720)
    gray = ImageOps.grayscale(small)
    def band(value):
        lower = 255 if value >= low else max(0, int(255 * (value - (low - softness)) / softness))
        upper = 255 if value <= high else max(0, int(255 * ((high + softness) - value) / softness))
        return min(lower, upper)
    return _finish_mask(gray.point(band), image.size, blur=3, strength=1.0)


def davinci_qualifier_mask(image, qualifier_name, settings):
    """达芬奇式 Qualifier：用亮度/颜色/边缘条件二次限定局部调整。"""
    if qualifier_name in ("关闭", "智能限定"):
        base_mask = Image.new("L", image.size, 255)
    elif qualifier_name == "肤色限定":
        base_mask = ai_skin_mask(image)
    elif qualifier_name == "高光限定":
        base_mask = ai_luminance_mask(image, "highlights")
    elif qualifier_name == "暗部限定":
        base_mask = ai_luminance_mask(image, "shadows")
    elif qualifier_name == "边缘限定":
        base_mask = ai_edge_mask(image)
    elif qualifier_name == "暖色限定":
        small = _small_analysis_image(image, 620)
        mask = Image.new("L", small.size, 0)
        pixels = small.convert("RGB").load()
        mask_pixels = mask.load()
        tolerance = max(0, min(100, settings.get("color_tolerance", 55)))
        threshold = 46 - tolerance * 0.38
        gain = 1.4 + tolerance / 72
        for y in range(small.height):
            for x in range(small.width):
                r, g, b = pixels[x, y]
                value = max(0, min(255, int((r - b + g * 0.16 - threshold) * gain)))
                mask_pixels[x, y] = value
        base_mask = _finish_mask(mask, image.size, blur=10, strength=0.86)
    else:
        base_mask = Image.new("L", image.size, 255)

    luma_mask = manual_luma_range_mask(image, settings)
    return ImageChops.multiply(base_mask, luma_mask)


def davinci_smart_qualifier(source, settings):
    qualifier = settings.get("qualifier", "智能限定")
    if qualifier != "智能限定":
        return qualifier
    prompt = settings.get("creative_prompt", "").lower()
    if any(word in prompt for word in ("肤色", "皮肤", "脸", "人像", "portrait")):
        return "肤色限定"
    if any(word in prompt for word in ("天空", "高光", "过曝")) or settings.get("local_exposure", 0) < -8:
        return "高光限定"
    if any(word in prompt for word in ("暗部", "阴影", "夜景")) or settings.get("local_exposure", 0) > 8:
        return "暗部限定"
    if any(word in prompt for word in ("细节", "质感", "锐化", "边缘")) or settings.get("local_detail", 0) > 34:
        return "边缘限定"
    return "关闭"


def compose_davinci_mask(source, settings):
    window_mask = davinci_power_window_mask(source, settings.get("power_window", "主体窗口"), settings)
    qualifier_name = davinci_smart_qualifier(source, settings)
    qualifier_mask = davinci_qualifier_mask(source, qualifier_name, settings)
    if qualifier_name == "关闭":
        combined = window_mask
    else:
        combined = ImageChops.multiply(window_mask, qualifier_mask)
    feather = max(0, min(100, int(settings.get("mask_feather", 42))))
    if feather:
        combined = combined.filter(ImageFilter.GaussianBlur(2 + feather * 0.34))
    range_amount = max(0.12, min(1.0, settings.get("qualifier_range", 72) / 100))
    mix_amount = max(0.0, min(1.0, settings.get("local_mix", 72) / 100))
    return _finish_mask(combined, source.size, blur=0, strength=range_amount * mix_amount), qualifier_name


def apply_davinci_local_adjustments(source, image, settings):
    """局部调色台：窗口 + 限定器 + 曝光/对比/饱和/细节，只影响目标区域。"""
    exposure = settings.get("local_exposure", 0)
    contrast = settings.get("local_contrast", 0)
    saturation = settings.get("local_saturation", 0)
    detail = settings.get("local_detail", 0)
    mix = settings.get("local_mix", 0)
    if all(value == 0 for value in (exposure, contrast, saturation, detail)) or mix <= 0:
        return image

    adjusted = image
    if exposure:
        adjusted = ImageEnhance.Brightness(adjusted).enhance(max(0.12, 1 + exposure / 135))
    if contrast:
        adjusted = ImageEnhance.Contrast(adjusted).enhance(max(0.18, 1 + contrast / 120))
    if saturation:
        adjusted = ImageEnhance.Color(adjusted).enhance(max(0.0, 1 + saturation / 105))
    if detail > 0:
        adjusted = adjusted.filter(ImageFilter.UnsharpMask(radius=1.0, percent=int(70 + detail * 1.9), threshold=3))
    elif detail < 0:
        adjusted = Image.blend(adjusted, adjusted.filter(ImageFilter.SMOOTH_MORE), min(0.45, abs(detail) / 100))

    mask, qualifier_name = compose_davinci_mask(source, settings)
    settings["_resolved_qualifier"] = qualifier_name
    return Image.composite(adjusted, image, mask)


def make_histogram_pixmap(image, width=520, height=120):
    """生成直方图预览。"""
    canvas = Image.new("RGB", (width, height), "#101418")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width - 1, height - 1), outline="#283242")
    gray = ImageOps.grayscale(image.resize((max(1, image.width // 3), max(1, image.height // 3))))
    hist = gray.histogram()
    peak = max(hist) or 1
    for x in range(width):
        index = min(255, int(x / width * 256))
        bar = int(hist[index] / peak * (height - 18))
        draw.line((x, height - 8, x, height - 8 - bar), fill="#54e8c5")
    return pil_to_pixmap(canvas, width, height)


def render_effect_image(source_path, reference_path, settings):
    """映效工作站原生版核心处理流程。"""
    if Image is None:
        raise RuntimeError("Pillow 未安装，无法处理图片")

    original_source = Image.open(source_path).convert("RGB")
    source = resize_for_processing(original_source, settings["max_edge"])
    result = source
    strength = settings["strength"] / 100
    match_mode = settings.get("match_mode", "balanced")

    if reference_path:
        reference = resize_for_processing(Image.open(reference_path), settings["max_edge"])
        color_amount = strength * settings["color"] / 100
        tone_amount = strength * settings["tone"] / 100
        if match_mode == "exact":
            color_amount = min(0.94, color_amount * 1.18)
            tone_amount = min(0.94, tone_amount * 1.14)
        elif match_mode == "creative":
            color_amount = min(0.88, color_amount * 0.92)
            tone_amount = min(0.86, tone_amount * 0.88)
        result = transfer_reference_color(result, reference, color_amount)
        result = transfer_reference_tone(result, reference, tone_amount)
        if match_mode == "creative":
            result = apply_mode_grade(result, settings.get("style_mode", "balanced"), strength * 0.45)
    else:
        result = apply_mode_grade(result, settings.get("style_mode", "balanced"), strength)

    contrast_factor = 1 + settings["contrast"] / 100
    saturation_factor = settings["saturation"] / 100
    sharpness_factor = 1 + settings["clarity"] / 55

    result = apply_temperature_tint(result, settings.get("temperature", 0), settings.get("tint", 0))
    result = apply_highlights_shadows(result, settings.get("highlights", 0), settings.get("shadows", 0))
    result = ImageEnhance.Contrast(result).enhance(max(0.25, contrast_factor))
    result = ImageEnhance.Color(result).enhance(max(0.0, saturation_factor))
    result = ImageEnhance.Sharpness(result).enhance(max(0.2, sharpness_factor))
    result = apply_ai_local_enhancement(source, result, settings)
    result = apply_davinci_local_adjustments(source, result, settings)
    result = apply_fade(result, settings.get("fade", 0) / 100)
    result = apply_bloom(result, settings["bloom"] / 100)
    result = apply_grain(result, settings.get("grain", 0) / 100)
    result = apply_vignette(result, settings.get("vignette", 0) / 100)
    return finalize_output_resolution(result, original_source, settings)


def local_lan_ips() -> list[str]:
    ips = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            ips.append(probe.getsockname()[0])
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = item[4][0]
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips or ["127.0.0.1"]


def load_mobile_api_config() -> dict:
    path = mobile_api_config_path()
    config = {"host": "0.0.0.0", "port": 8765, "discovery_port": 8766, "token": secrets.token_urlsafe(18)}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config.update({key: data[key] for key in ("host", "port", "discovery_port", "token") if key in data})
        except Exception:
            pass
    if not config.get("token"):
        config["token"] = secrets.token_urlsafe(18)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    harden_private_file(path)
    return config


def mobile_task_id(kind: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_slug(kind)}-{secrets.token_hex(3)}"


def mobile_image_settings(payload: dict) -> dict:
    mode = str(payload.get("mode") or "自然校色")
    preset_name = {"霓虹赛博": "霓虹赛博", "商业干净": "商业干净", "自然校色": "自然校色"}.get(mode, "自然校色")
    settings = dict(PRESET_VALUES.get(preset_name, PRESET_VALUES["自然校色"]))
    settings["strength"] = int(payload.get("strength") or settings.get("strength", 78))
    output_config = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    requested_edge = payload.get("max_edge") or output_config.get("max_size") or 4096
    settings["max_edge"] = min(8192, max(1600, int(requested_edge)))
    output_policy = str(output_config.get("resolution") or payload.get("output_resolution") or "source_native")
    settings["output_resolution"] = {
        "native": "source_native",
        "source": "source_native",
        "2k": "long_4k",
        "4k": "long_4k",
        "8k": "long_8k",
        "2x": "smart_2x",
    }.get(output_policy.lower(), output_policy)
    settings["output_max_edge"] = min(16384, max(settings["max_edge"], int(output_config.get("max_size") or settings["max_edge"])))
    settings["creative_prompt"] = str(payload.get("prompt") or "")
    if not payload.get("local_mask", True):
        settings["ai_local_mode"] = "global"
        settings["local_mix"] = 0
    else:
        settings["ai_local_mode"] = "auto"
        settings.setdefault("local_mix", 66)
        settings.setdefault("local_detail", 18)
    settings.setdefault("match_mode", "balanced")
    settings.setdefault("power_window", "主体窗口")
    settings.setdefault("qualifier", "智能限定")
    settings.setdefault("window_x", 50)
    settings.setdefault("window_y", 50)
    settings.setdefault("window_size", 100)
    settings.setdefault("window_aspect", 100)
    settings.setdefault("luma_low", 0)
    settings.setdefault("luma_high", 255)
    settings.setdefault("qualifier_softness", 32)
    settings.setdefault("qualifier_range", 72)
    settings.setdefault("mask_feather", 42)
    settings.setdefault("color_tolerance", 55)
    return settings


def maybe_decode_mobile_upload(task_id: str, payload: dict) -> str:
    media_base64 = payload.get("media_base64")
    if not isinstance(media_base64, str) or not media_base64:
        return ""
    file_name = safe_slug(str(payload.get("file_name") or task_id))
    suffix = (Path(file_name).suffix or ".bin").lower()
    allowed_suffixes = {
        ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
        ".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi",
    }
    if suffix not in allowed_suffixes:
        suffix = ".bin"
    output = mobile_api_root() / "uploads" / f"{task_id}{suffix}"
    output.write_bytes(base64.b64decode(media_base64, validate=True))
    return str(output)


def write_mobile_task(kind: str, payload: dict, client: str = "") -> dict:
    task_id = mobile_task_id(kind)
    root = mobile_api_root()
    source_from_upload = maybe_decode_mobile_upload(task_id, payload)
    if source_from_upload:
        payload = dict(payload)
        payload.pop("media_base64", None)
        payload["source_uri"] = source_from_upload

    record = {
        "id": task_id,
        "kind": kind,
        "status": "queued",
        "client": client,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "payload": payload,
    }

    try:
        if kind == "image":
            source = str(payload.get("source_uri") or "").strip()
            reference = str(payload.get("reference_uri") or "").strip()
            if source and Path(source).exists():
                settings = mobile_image_settings(payload)
                image = render_effect_image(source, reference if reference and Path(reference).exists() else "", settings)
                output = root / "outputs" / f"{task_id}.png"
                image.save(output, "PNG")
                record["status"] = "success"
                record["output"] = str(output)
                record["detail"] = "图片已生成"
            else:
                record["detail"] = "任务已接收；source_uri 不是电脑可访问路径，等待后续上传/同步处理"
        elif kind == "model":
            model = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
            record_path = deployment_records_dir() / f"{task_id}.json"
            record_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
            record["status"] = "success"
            record["output"] = str(record_path)
            record["detail"] = "模型部署请求已记录"
        else:
            record["detail"] = "视频任务已接收，等待桌面端渲染队列处理"
    except Exception as error:
        record["status"] = "failed"
        record["detail"] = str(error)

    task_path = root / "tasks" / f"{task_id}.json"
    task_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


class MobileApiService:
    """给手机端使用的轻量 HTTP API 服务。"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, token: str = "", discovery_port: int = 8766):
        self.host = host
        self.port = int(port)
        self.discovery_port = int(discovery_port)
        self.token = token
        self.httpd = None
        self.thread = None
        self.discovery_socket = None
        self.discovery_thread = None
        self.discovery_stop = threading.Event()
        self.last_error = ""
        self.pairing_code = ""
        self.pairing_expires_at = 0.0
        self.pair_attempts = {}
        self.rotate_pairing_code()

    def start(self) -> bool:
        if self.is_running():
            return True
        try:
            handler = self._make_handler()
            self.httpd = ThreadingHTTPServer((self.host, self.port), handler)
            self.httpd.daemon_threads = True
            self.thread = threading.Thread(target=self.httpd.serve_forever, name="YingXiaoMobileApi", daemon=True)
            self.thread.start()
            self._start_discovery()
            self.last_error = ""
            logging.info("Mobile API started at %s:%s", self.host, self.port)
            return True
        except Exception as error:
            self.last_error = str(error)
            logging.exception("Mobile API start failed")
            self.httpd = None
            return False

    def stop(self):
        self._stop_discovery()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        self.httpd = None
        self.thread = None

    def is_running(self) -> bool:
        return bool(self.httpd and self.thread and self.thread.is_alive())

    def urls(self) -> list[str]:
        return [f"http://{ip}:{self.port}" for ip in local_lan_ips()]

    def url_for_client(self, client_ip: str) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect((client_ip, max(1, self.discovery_port)))
                ip = probe.getsockname()[0]
                if ip and not ip.startswith("127."):
                    return f"http://{ip}:{self.port}"
        except Exception:
            pass
        urls = self.urls()
        return urls[0] if urls else f"http://127.0.0.1:{self.port}"

    def rotate_pairing_code(self) -> str:
        self.pairing_code = f"{secrets.randbelow(1000000):06d}"
        self.pairing_expires_at = time.time() + 10 * 60
        return self.pairing_code

    def current_pairing_code(self) -> str:
        if not self.pairing_code or self.pairing_seconds_left() <= 0:
            self.rotate_pairing_code()
        return self.pairing_code

    def pairing_seconds_left(self) -> int:
        return max(0, int(self.pairing_expires_at - time.time()))

    def verify_pairing_code(self, code: str) -> bool:
        normalized = "".join(ch for ch in str(code or "") if ch.isdigit())
        expected = self.current_pairing_code()
        return bool(
            len(normalized) == 6
            and self.pairing_seconds_left() > 0
            and secrets.compare_digest(normalized, expected)
        )

    def pair_attempt_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - 5 * 60
        attempts = [item for item in self.pair_attempts.get(client_ip, []) if item >= window_start]
        self.pair_attempts[client_ip] = attempts
        return len(attempts) < 8

    def record_pair_attempt(self, client_ip: str, success: bool):
        if success:
            self.pair_attempts.pop(client_ip, None)
            return
        now = time.time()
        attempts = self.pair_attempts.setdefault(client_ip, [])
        attempts.append(now)
        if len(self.pair_attempts) > 256:
            cutoff = now - 5 * 60
            self.pair_attempts = {
                ip: [item for item in values if item >= cutoff]
                for ip, values in self.pair_attempts.items()
                if any(item >= cutoff for item in values)
            }

    def discovery_payload(self) -> dict:
        return {
            "type": "yingxiao_service",
            "app": APP_NAME,
            "version": APP_VERSION,
            "status": "online" if self.is_running() else "starting",
            "http_port": self.port,
            "discovery_port": self.discovery_port,
            "urls": self.urls(),
            "pairing_required": bool(self.token),
            "token_required": bool(self.token),
            "time": datetime.now().isoformat(timespec="seconds"),
        }

    def _start_discovery(self):
        if self.discovery_thread and self.discovery_thread.is_alive():
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.discovery_port))
            sock.settimeout(0.5)
            self.discovery_socket = sock
            self.discovery_stop.clear()
            self.discovery_thread = threading.Thread(
                target=self._discovery_loop,
                args=(sock,),
                name="YingXiaoMobileDiscovery",
                daemon=True,
            )
            self.discovery_thread.start()
            logging.info("Mobile discovery started at UDP :%s", self.discovery_port)
        except Exception:
            logging.exception("Mobile discovery start failed")

    def _stop_discovery(self):
        self.discovery_stop.set()
        sock = self.discovery_socket
        self.discovery_socket = None
        if sock:
            try:
                sock.close()
            except Exception:
                pass
        if self.discovery_thread and self.discovery_thread.is_alive():
            self.discovery_thread.join(timeout=0.8)
        self.discovery_thread = None

    def _discovery_loop(self, sock):
        while not self.discovery_stop.is_set():
            try:
                data, address = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception:
                logging.exception("Mobile discovery receive failed")
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
                payload = json.loads(text) if text.strip().startswith("{") else {}
                probe_type = str(payload.get("type", "")) if isinstance(payload, dict) else ""
                if "yingxiao_discover" not in text and probe_type not in {"yingxiao_discover", "yingxiao_mobile_discover"}:
                    continue
                if not is_private_client_ip(address[0]):
                    logging.warning("Blocked mobile discovery from non-private client %s", address[0])
                    continue
                response = self.discovery_payload()
                response["client_ip"] = address[0]
                response["url"] = self.url_for_client(address[0])
                encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
                sock.sendto(encoded, address)
            except OSError:
                break
            except Exception:
                logging.exception("Mobile discovery response failed")

    def _make_handler(self):
        service = self

        class MobileApiHandler(BaseHTTPRequestHandler):
            server_version = "YingXiaoMobileApi/0.2"

            def log_message(self, fmt, *args):
                logging.info("Mobile API %s - %s", self.client_address[0], fmt % args)

            def do_OPTIONS(self):
                if not self._private_client():
                    self._send_json({"ok": False, "error": "forbidden_network"}, status=403)
                    return
                if self.headers.get("Origin") and not self._cors_origin():
                    self._send_json({"ok": False, "error": "cors_origin_denied"}, status=403)
                    return
                self._send_json({"ok": True})

            def do_GET(self):
                if not self._private_client():
                    self._send_json({"ok": False, "error": "forbidden_network"}, status=403)
                    return
                if self.path.split("?", 1)[0] in ("/", "/health"):
                    payload = {
                        "ok": True,
                        "app": APP_NAME,
                        "version": APP_VERSION,
                        "status": "online",
                        "token_required": bool(service.token),
                        "pairing_required": bool(service.token),
                        "pairing_expires_in": service.pairing_seconds_left(),
                        "discovery_port": service.discovery_port,
                        "time": datetime.now().isoformat(timespec="seconds"),
                        "endpoints": ["/health", "/pair", "/api/tasks/image", "/api/tasks/video", "/api/models/deploy"],
                    }
                    if self._authorized():
                        payload["lan_urls"] = service.urls()
                    self._send_json(payload)
                    return
                if self.path.split("?", 1)[0] == "/system_stats":
                    if not self._authorized():
                        self._send_json({"ok": False, "error": "unauthorized"}, status=401)
                        return
                    self._send_json({
                        "ok": True,
                        "app": APP_NAME,
                        "gpu": detect_gpu_summary(),
                        "ffmpeg": detect_ffmpeg(),
                        "time": datetime.now().isoformat(timespec="seconds"),
                    })
                    return
                self._send_json({"ok": False, "error": "not_found"}, status=404)

            def do_POST(self):
                if not self._private_client():
                    self._send_json({"ok": False, "error": "forbidden_network"}, status=403)
                    return
                path = self.path.split("?", 1)[0]
                if path == "/pair":
                    try:
                        client_ip = self.client_address[0]
                        if not service.pair_attempt_allowed(client_ip):
                            self._send_json({"ok": False, "error": "pairing_rate_limited"}, status=429)
                            return
                        body = self._read_body(max_bytes=4096)
                        data = json.loads(body.decode("utf-8") or "{}")
                        code = data.get("code", "") if isinstance(data, dict) else ""
                        success = service.verify_pairing_code(code)
                        service.record_pair_attempt(client_ip, success)
                        if success:
                            token = service.token
                            service.rotate_pairing_code()
                            self._send_json({
                                "ok": True,
                                "app": APP_NAME,
                                "version": APP_VERSION,
                                "token": token,
                                "lan_urls": service.urls(),
                                "message": "配对成功",
                            })
                        else:
                            self._send_json({"ok": False, "error": "pairing_code_invalid"}, status=403)
                    except Exception as error:
                        logging.exception("Mobile pairing failed")
                        self._send_json({"ok": False, "error": "pairing_failed"}, status=500)
                    return
                kind_map = {
                    "/api/tasks/image": "image",
                    "/api/tasks/video": "video",
                    "/api/models/deploy": "model",
                }
                if path not in kind_map:
                    self._send_json({"ok": False, "error": "not_found"}, status=404)
                    return
                if not self._authorized():
                    self._send_json({"ok": False, "error": "unauthorized"}, status=401)
                    return
                try:
                    body = self._read_body(max_bytes=96 * 1024 * 1024)
                    data = json.loads(body.decode("utf-8") or "{}")
                    raw_payload = data.get("payload", data)
                    payload = raw_payload if isinstance(raw_payload, dict) else {}
                    if data.get("prompt") and "prompt" not in payload:
                        payload = dict(payload)
                        payload["prompt"] = data.get("prompt")
                    record = write_mobile_task(kind_map[path], payload, str(data.get("client", "")))
                    self._send_json({
                        "ok": record.get("status") != "failed",
                        "id": record["id"],
                        "task_id": record["id"],
                        "status": record.get("status", "queued"),
                        "message": record.get("detail", "任务已接收"),
                        "output": record.get("output", ""),
                    })
                except ValueError as error:
                    self._send_json({"ok": False, "error": str(error)}, status=413)
                except Exception as error:
                    logging.exception("Mobile API request failed")
                    self._send_json({"ok": False, "error": "request_failed"}, status=500)

            def _private_client(self) -> bool:
                return is_private_client_ip(self.client_address[0])

            def _authorized(self) -> bool:
                if not service.token:
                    return True
                header = self.headers.get("Authorization", "")
                return secrets.compare_digest(header, f"Bearer {service.token}")

            def _read_body(self, max_bytes: int = 80 * 1024 * 1024) -> bytes:
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length < 0 or length > max_bytes:
                    raise ValueError("payload_too_large")
                return self.rfile.read(length)

            def _send_json(self, payload: dict, status: int = 200):
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                origin = self._cors_origin()
                if origin:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
                    self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _cors_origin(self) -> str:
                origin = (self.headers.get("Origin") or "").rstrip("/")
                if not origin:
                    return ""
                allowed_exact = {"http://localhost", "http://127.0.0.1", "https://localhost", "https://127.0.0.1"}
                if origin in allowed_exact:
                    return origin
                if origin.startswith(("http://localhost:", "http://127.0.0.1:", "https://localhost:", "https://127.0.0.1:")):
                    return origin
                return ""

        return MobileApiHandler


class SectionTitle(QWidget):
    """页面标题组件，后续增加页面时可以复用。"""

    def __init__(self, title: str, subtitle: str):
        super().__init__()

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 24px; font-weight: 900; color: #f7f9fb;")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color: #93a7ba;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)


class SummaryTile(QWidget):
    """顶部数据卡片，模拟前面工作站的状态模块。"""

    def __init__(self, label: str, value: str = "--"):
        super().__init__()
        self.setObjectName("summaryTile")

        self.label = QLabel(label)
        self.value = QLabel(value)
        self.label.setStyleSheet("color: #8ea2b6; font-size: 12px; font-weight: 700;")
        self.value.setStyleSheet("color: #f7f9fb; font-size: 19px; font-weight: 900;")

        self.setStyleSheet(
            """
            #summaryTile {
                background: #121822;
                border: 1px solid #263243;
                border-radius: 8px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_value(self, value: str):
        self.value.setText(value)


class MotionToast(QLabel):
    """系统级浮层提示，配合页面切换和后台状态做轻量过渡。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet(
            """
            QLabel {
                color: #07100f;
                background: #58dcc7;
                border: 1px solid #8ff8e6;
                border-radius: 7px;
                padding: 9px 14px;
                font-weight: 900;
            }
            """
        )
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0.0)
        self._show_group = None
        self._hide_animation = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.fade_out)
        self.hide()

    def reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 18
        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.height() - margin)
        self.move(x, y)

    def show_message(self, text: str, performance: dict):
        self.setText(text)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()

        self._hide_timer.stop()
        if not performance.get("toast_motion", True) or performance.get("reduce_motion", False):
            self.effect.setOpacity(1.0)
            self._hide_timer.start(1600)
            return

        if self._show_group:
            self._show_group.stop()
        if self._hide_animation:
            self._hide_animation.stop()

        target = self.pos()
        self.move(target + QPoint(14, 0))
        fade = QPropertyAnimation(self.effect, b"opacity", self)
        fade.setDuration(int(performance.get("animation_ms", 180)))
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide = QPropertyAnimation(self, b"pos", self)
        slide.setDuration(int(performance.get("animation_ms", 180)))
        slide.setStartValue(self.pos())
        slide.setEndValue(target)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        self._show_group = group
        group.start()
        self._hide_timer.start(1800)

    def fade_out(self):
        if self._hide_animation:
            self._hide_animation.stop()
        animation = QPropertyAnimation(self.effect, b"opacity", self)
        animation.setDuration(180)
        animation.setStartValue(self.effect.opacity())
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        animation.finished.connect(self.hide)
        self._hide_animation = animation
        animation.start()


class MotionInteractionFilter(QObject):
    """给按钮增加轻量点击/悬停反馈，不改变布局尺寸。"""

    def __init__(self, performance: dict, parent=None):
        super().__init__(parent)
        self.performance = performance
        self._animations = {}

    def eventFilter(self, watched, event):
        if not isinstance(watched, QPushButton):
            return False
        if event.type() == QEvent.Type.Enter:
            watched.setCursor(Qt.CursorShape.PointingHandCursor)
            self.pulse(watched, 0.92, 130)
        elif event.type() == QEvent.Type.MouseButtonPress:
            self.pulse(watched, 0.78, 160)
        return False

    def pulse(self, button: QPushButton, start_opacity: float, duration: int):
        if self.performance.get("reduce_motion", False) or not button.isEnabled():
            return
        old_animation = self._animations.pop(button, None)
        if old_animation:
            old_animation.stop()
        effect = QGraphicsOpacityEffect(button)
        button.setGraphicsEffect(effect)
        effect.setOpacity(start_opacity)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(duration)
        animation.setStartValue(start_opacity)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: button.setGraphicsEffect(None))
        animation.finished.connect(lambda: self._animations.pop(button, None))
        self._animations[button] = animation
        animation.start()


class HeaderBar(QWidget):
    """内容区顶部标题栏，提供桌面工作站的整体氛围。"""

    def __init__(self):
        super().__init__()

        eyebrow = QLabel("Native AI Workstation")
        eyebrow.setStyleSheet("color: #58dcc7; font-size: 12px; font-weight: 900;")

        title = QLabel("映效 AI 工作站")
        title.setStyleSheet("color: #f7f9fb; font-size: 26px; font-weight: 900;")

        subtitle = QLabel("图像质感迁移、硬件监控、NVENC 视频管线和 ComfyUI / FLUX 接入都在原生窗口里完成。")
        subtitle.setStyleSheet("color: #93a7ba;")

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(3)
        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        for text in ("映效图像", "NVENC视频", "FLUX接入"):
            chip = QLabel(text)
            chip.setStyleSheet(
                """
                QLabel {
                    color: #f7f9fb;
                    background: #121822;
                    border: 1px solid #263243;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-weight: 700;
                }
                """
            )
            chips.addWidget(chip)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 14)
        layout.addLayout(left, 1)
        layout.addLayout(chips)


class MetricRow(QWidget):
    """硬件指标行：左侧说明文字，右侧进度条。"""

    def __init__(self, label: str):
        super().__init__()

        self.label = QLabel(label)
        self.label.setMinimumWidth(250)
        self.label.setStyleSheet("color: #d9e3ef; font-weight: 650;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setColumnStretch(1, 1)
        layout.addWidget(self.label, 0, 0)
        layout.addWidget(self.progress, 0, 1)

    def set_metric(self, text: str, percent: float):
        self.label.setText(text)
        self.progress.setValue(max(0, min(100, int(percent))))


class SliderRow(QWidget):
    """参数滑杆行，方便后续继续扩展控制项。"""

    def __init__(self, label: str, minimum: int, maximum: int, value: int):
        super().__init__()

        self.title = QLabel(label)
        self.title.setMinimumWidth(88)
        self.title.setStyleSheet("color: #d9e3ef; font-weight: 700;")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.value_label = QLabel(str(value))
        self.value_label.setMinimumWidth(42)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setStyleSheet("color: #54e8c5; font-weight: 800;")
        self.slider.valueChanged.connect(lambda number: self.value_label.setText(str(number)))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.title)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)

    def value(self):
        return self.slider.value()


class ImageEffectWorker(QThread):
    """图片生成线程，避免大图处理时卡住界面。"""

    progress_changed = Signal(int)
    log_message = Signal(str)
    finished_image = Signal(object)
    failed = Signal(str)

    def __init__(self, source_path: str, reference_path: str, settings: dict):
        super().__init__()
        self.source_path = source_path
        self.reference_path = reference_path
        self.settings = settings

    def run(self):
        try:
            self.log_message.emit("读取原图")
            self.progress_changed.emit(12)
            if self.reference_path:
                self.log_message.emit("读取参考图并分析色彩/光影/质感")
            else:
                self.log_message.emit("未选择参考图，按当前参数增强原图")
            self.progress_changed.emit(28)
            self.log_message.emit("AI局部识别：主体、高光、暗部、边缘和肤色保护")
            self.progress_changed.emit(42)
            image = render_effect_image(self.source_path, self.reference_path, self.settings)
            self.progress_changed.emit(90)
            self.log_message.emit("生成预览和输出缓存")
            self.progress_changed.emit(100)
            self.finished_image.emit(image)
        except Exception as error:
            self.failed.emit(str(error))


class BatchImageWorker(QThread):
    """批量图片处理线程，避免批处理期间主界面无响应。"""

    progress_changed = Signal(int)
    log_message = Signal(str)
    finished_successfully = Signal()
    failed = Signal(str)

    def __init__(self, paths: list[str], reference_path: str, settings: dict, output_dir: str):
        super().__init__()
        self.paths = paths
        self.reference_path = reference_path
        self.settings = settings
        self.output_dir = output_dir

    def run(self):
        try:
            total = max(1, len(self.paths))
            for index, path in enumerate(self.paths, start=1):
                image = render_effect_image(path, self.reference_path, self.settings)
                output_path = Path(self.output_dir) / f"{Path(path).stem}-effect.png"
                image.save(output_path, "PNG")
                self.progress_changed.emit(int(index / total * 100))
                self.log_message.emit(f"批量完成 {index}/{total}：{output_path.name}")
            self.finished_successfully.emit()
        except Exception as error:
            self.failed.emit(str(error))


class ImageDropPanel(QFrame):
    """图片预览卡片。"""

    dropped = Signal(str)

    def __init__(self, title: str):
        super().__init__()
        self.setAcceptDrops(True)
        self._preview_animation = None
        self.animations_enabled = True
        self.title = QLabel(title)
        self.title.setStyleSheet("color: #8fa3b8; font-size: 12px; font-weight: 800;")
        self.preview = QLabel("等待载入")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(260)
        self.preview.setStyleSheet(
            """
            QLabel {
                color: #6f7d8f;
                background: #10141a;
                border: 1px dashed #334052;
                border-radius: 8px;
            }
            """
        )
        self.meta = QLabel("未选择")
        self.meta.setStyleSheet("color: #8fa3b8;")

        self.setStyleSheet(
            """
            ImageDropPanel {
                background: #151a22;
                border: 1px solid #283242;
                border-radius: 8px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self.title)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.meta)

    def set_pixmap(self, pixmap: QPixmap, meta: str):
        self.preview.setPixmap(pixmap)
        self.preview.setText("")
        self.meta.setText(meta)
        if not self.animations_enabled:
            self.preview.setGraphicsEffect(None)
            return
        effect = QGraphicsOpacityEffect(self.preview)
        self.preview.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(180)
        animation.setStartValue(0.42)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: self.preview.setGraphicsEffect(None))
        self._preview_animation = animation
        animation.start()

    def set_empty(self, text: str):
        self.preview.setPixmap(QPixmap())
        self.preview.setText(text)
        self.meta.setText("未选择")

    def set_preview_height(self, height: int):
        self.preview.setMinimumHeight(height)
        self.preview.setMaximumHeight(max(height + 90, height))

    def set_animation_enabled(self, enabled: bool):
        self.animations_enabled = enabled
        if not enabled:
            self.preview.setGraphicsEffect(None)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.dropped.emit(path)


PRESET_VALUES = {
    "自然校色": {"style_mode": "balanced", "strength": 78, "color": 82, "tone": 76, "contrast": 28, "saturation": 108, "temperature": 0, "tint": 0, "highlights": -8, "shadows": 12, "clarity": 34, "bloom": 6, "fade": 4, "grain": 10, "vignette": 12},
    "电影胶片": {"style_mode": "film", "strength": 76, "color": 70, "tone": 82, "contrast": 18, "saturation": 92, "temperature": 12, "tint": 4, "highlights": -18, "shadows": 8, "clarity": 18, "bloom": 5, "fade": 24, "grain": 28, "vignette": 22},
    "霓虹赛博": {"style_mode": "neon", "strength": 88, "color": 96, "tone": 74, "contrast": 48, "saturation": 142, "temperature": -10, "tint": 18, "highlights": -6, "shadows": 20, "clarity": 38, "bloom": 28, "fade": 6, "grain": 12, "vignette": 18},
    "商业干净": {"style_mode": "clean", "strength": 62, "color": 50, "tone": 66, "contrast": 12, "saturation": 96, "temperature": 0, "tint": -3, "highlights": -12, "shadows": 18, "clarity": 26, "bloom": 0, "fade": 0, "grain": 0, "vignette": 0},
    "建筑 HDR": {"style_mode": "hdr", "strength": 82, "color": 68, "tone": 86, "contrast": 58, "saturation": 104, "temperature": -4, "tint": 0, "highlights": -34, "shadows": 42, "clarity": 70, "bloom": 4, "fade": 0, "grain": 6, "vignette": 8},
    "人像通透": {"style_mode": "portrait", "strength": 68, "color": 58, "tone": 72, "contrast": 8, "saturation": 94, "temperature": 8, "tint": 6, "highlights": -14, "shadows": 20, "clarity": 12, "bloom": 8, "fade": 4, "grain": 4, "vignette": 4},
    "旅拍风景": {"style_mode": "travel", "strength": 84, "color": 86, "tone": 78, "contrast": 36, "saturation": 122, "temperature": 6, "tint": -4, "highlights": -16, "shadows": 18, "clarity": 42, "bloom": 10, "fade": 2, "grain": 8, "vignette": 10},
    "暗调电影": {"style_mode": "moody", "strength": 88, "color": 74, "tone": 86, "contrast": 64, "saturation": 84, "temperature": -8, "tint": 8, "highlights": -28, "shadows": -18, "clarity": 48, "bloom": 6, "fade": 18, "grain": 20, "vignette": 34},
    "产品质感": {"style_mode": "product", "strength": 58, "color": 46, "tone": 62, "contrast": 24, "saturation": 102, "temperature": 0, "tint": 0, "highlights": -8, "shadows": 10, "clarity": 64, "bloom": 0, "fade": 0, "grain": 0, "vignette": 0},
    "落日金调": {"style_mode": "sunset", "strength": 84, "color": 88, "tone": 76, "contrast": 30, "saturation": 128, "temperature": 34, "tint": 10, "highlights": -20, "shadows": 16, "clarity": 30, "bloom": 18, "fade": 10, "grain": 12, "vignette": 18},
}


class ImageEffectPage(QWidget):
    """映效工作站原生页面：原图 + 参考图 + 参数 + 生成输出。"""

    def __init__(self):
        super().__init__()

        self.source_path = ""
        self.reference_path = ""
        self.output_image = None
        self.original_preview_image = None
        self.history = []
        self.batch_paths = []
        self.worker = None
        self.batch_worker = None

        self.source_panel = ImageDropPanel("ORIGINAL 原图")
        self.reference_panel = ImageDropPanel("REFERENCE 参考效果图")
        self.output_panel = ImageDropPanel("GENERATED 生成结果")
        self.pick_source_button = QPushButton("选择原图")
        self.pick_reference_button = QPushButton("选择参考图")
        self.pick_batch_button = QPushButton("批量原图")
        self.clear_reference_button = QPushButton("清空参考")
        self.auto_tune_button = QPushButton("智能推荐")
        self.save_recipe_button = QPushButton("保存方案")
        self.load_recipe_button = QPushButton("导入方案")
        self.compare_button = QPushButton("对比原图")
        self.split_button = QPushButton("分割预览")
        self.generate_button = QPushButton("生成效果图")
        self.save_button = QPushButton("保存 PNG")
        self.process_batch_button = QPushButton("批量处理")
        self.reset_button = QPushButton("重置")
        self.compare_button.setEnabled(False)
        self.split_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.process_batch_button.setEnabled(False)
        self.progress_bar = QProgressBar()
        self.log_box = QTextEdit()
        self.history_list = QListWidget()
        self.batch_list = QListWidget()
        self.histogram_label = QLabel("等待图像")
        self.histogram_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.model_status = QLabel("模型监控待命")
        self.model_status.setStyleSheet("color: #54e8c5; font-weight: 800;")

        self.preset_combo = QComboBox()
        self.match_mode_combo = QComboBox()
        self.local_mode_combo = QComboBox()
        self.power_window_combo = QComboBox()
        self.qualifier_combo = QComboBox()
        self.creative_prompt = QTextEdit()
        self.strength_slider = SliderRow("强度", 0, 100, 78)
        self.color_slider = SliderRow("色彩", 0, 100, 82)
        self.tone_slider = SliderRow("光影", 0, 100, 76)
        self.contrast_slider = SliderRow("对比", -40, 100, 28)
        self.saturation_slider = SliderRow("饱和", 0, 180, 108)
        self.temperature_slider = SliderRow("冷暖", -100, 100, 0)
        self.tint_slider = SliderRow("青洋红", -100, 100, 0)
        self.highlights_slider = SliderRow("高光", -100, 100, -8)
        self.shadows_slider = SliderRow("暗部", -100, 100, 12)
        self.clarity_slider = SliderRow("清晰", 0, 100, 34)
        self.bloom_slider = SliderRow("辉光", 0, 100, 6)
        self.fade_slider = SliderRow("褪黑", 0, 100, 4)
        self.grain_slider = SliderRow("颗粒", 0, 100, 10)
        self.vignette_slider = SliderRow("暗角", 0, 100, 12)
        self.local_exposure_slider = SliderRow("局部曝光", -80, 80, 8)
        self.local_contrast_slider = SliderRow("局部对比", -80, 80, 12)
        self.local_saturation_slider = SliderRow("局部饱和", -80, 90, 8)
        self.local_detail_slider = SliderRow("局部细节", -60, 100, 28)
        self.mask_feather_slider = SliderRow("蒙版羽化", 0, 100, 44)
        self.qualifier_range_slider = SliderRow("限定强度", 0, 100, 74)
        self.local_mix_slider = SliderRow("局部混合", 0, 100, 72)
        self.window_x_slider = SliderRow("窗口X", 0, 100, 50)
        self.window_y_slider = SliderRow("窗口Y", 0, 100, 50)
        self.window_size_slider = SliderRow("窗口大小", 12, 170, 100)
        self.window_aspect_slider = SliderRow("窗口宽高", 35, 220, 100)
        self.luma_low_slider = SliderRow("亮度下限", 0, 255, 0)
        self.luma_high_slider = SliderRow("亮度上限", 0, 255, 255)
        self.qualifier_softness_slider = SliderRow("限定柔和", 1, 100, 32)
        self.color_tolerance_slider = SliderRow("色彩容差", 0, 100, 55)
        self.max_edge_combo = QComboBox()
        self.output_resolution_combo = QComboBox()
        self.split_slider = QSlider(Qt.Orientation.Horizontal)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        title = SectionTitle(
            "映效图像工作站",
            "原生 PySide6 图像效果迁移页面：预设、参考迁移、智能推荐、批量、历史、直方图和 PNG 输出。",
        )

        self.preset_combo.addItems(list(PRESET_VALUES.keys()))
        self.match_mode_combo.addItems(["智能平衡", "一比一还原", "创意增强"])
        self.local_mode_combo.addItems(["自动判断", "AI智能精修", "全图应用", "主体优先", "肤色人物", "高光天空", "暗部细节", "背景氛围", "边缘质感"])
        self.power_window_combo.addItems(["主体窗口", "中心圆窗", "上半天空", "线性渐变", "反选背景", "全画面"])
        self.qualifier_combo.addItems(["智能限定", "肤色限定", "高光限定", "暗部限定", "边缘限定", "暖色限定", "关闭"])
        self.max_edge_combo.addItems(["1600", "2400", "3200", "4096", "5120", "6144", "8192"])
        self.max_edge_combo.setCurrentText("4096")
        self.output_resolution_combo.addItems(["跟随原图", "处理尺寸", "长边4K", "长边8K", "智能2x"])
        self.output_resolution_combo.setCurrentText("智能2x")
        self.split_slider.setRange(0, 100)
        self.split_slider.setValue(50)
        self.split_slider.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.creative_prompt.setMaximumHeight(58)
        self.creative_prompt.setPlaceholderText("赛博朋克、胶片、干净商业、HDR、保留肤色、加强辉光等")
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(118)
        list_style = """
            QListWidget {
                background: #101418;
                color: #d9e3ef;
                border: 1px solid #283242;
                border-radius: 6px;
            }
            QListWidget::item {
                min-height: 26px;
                padding: 4px 8px;
            }
            QListWidget::item:selected {
                background: #273448;
            }
        """
        self.history_list.setStyleSheet(list_style)
        self.batch_list.setStyleSheet(list_style)
        self.histogram_label.setMinimumHeight(110)
        self.histogram_label.setStyleSheet(
            """
            QLabel {
                background: #101418;
                color: #6f7d8f;
                border: 1px solid #283242;
                border-radius: 6px;
            }
            """
        )
        self.log_box.setStyleSheet(
            """
            QTextEdit {
                background: #101418;
                color: #d7f7df;
                border: 1px solid #283242;
                border-radius: 6px;
                font-family: Consolas, Microsoft YaHei UI;
                font-size: 13px;
            }
            """
        )

        self.image_panels = [self.source_panel, self.reference_panel, self.output_panel]
        self.image_grid = QGridLayout()
        self.image_grid.setHorizontalSpacing(12)
        self.image_grid.setVerticalSpacing(12)
        self.reflow_grid(self.image_grid, self.image_panels, 3)

        mode_row = QGridLayout()
        mode_row.setHorizontalSpacing(10)
        mode_row.addWidget(QLabel("专业模式"), 0, 0)
        mode_row.addWidget(self.preset_combo, 0, 1)
        mode_row.addWidget(QLabel("生成模式"), 0, 2)
        mode_row.addWidget(self.match_mode_combo, 0, 3)
        mode_row.addWidget(QLabel("AI局部"), 0, 4)
        mode_row.addWidget(self.local_mode_combo, 0, 5)
        mode_row.addWidget(QLabel("窗口"), 1, 0)
        mode_row.addWidget(self.power_window_combo, 1, 1)
        mode_row.addWidget(QLabel("限定器"), 1, 2)
        mode_row.addWidget(self.qualifier_combo, 1, 3)
        mode_row.setColumnStretch(1, 1)
        mode_row.setColumnStretch(3, 1)
        mode_row.setColumnStretch(5, 1)

        prompt_row = QHBoxLayout()
        prompt_row.addWidget(QLabel("创作要求"))
        prompt_row.addWidget(self.creative_prompt, 1)
        prompt_row.addWidget(self.model_status)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addWidget(self.pick_source_button)
        button_row.addWidget(self.pick_reference_button)
        button_row.addWidget(self.pick_batch_button)
        button_row.addWidget(self.clear_reference_button)
        button_row.addWidget(self.auto_tune_button)
        button_row.addWidget(self.save_recipe_button)
        button_row.addWidget(self.load_recipe_button)
        button_row.addStretch()
        button_row.addWidget(QLabel("生成上限"))
        button_row.addWidget(self.max_edge_combo)
        button_row.addWidget(QLabel("保存尺寸"))
        button_row.addWidget(self.output_resolution_combo)
        button_row.addWidget(self.compare_button)
        button_row.addWidget(self.split_button)
        button_row.addWidget(self.generate_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.reset_button)

        controls = QFrame()
        controls.setStyleSheet(
            """
            QFrame {
                background: #151a22;
                border: 1px solid #283242;
                border-radius: 8px;
            }
            """
        )
        self.controls_layout = QGridLayout(controls)
        self.controls_layout.setContentsMargins(14, 14, 14, 14)
        self.controls_layout.setHorizontalSpacing(18)
        self.controls_layout.setVerticalSpacing(12)
        self.sliders = [
            self.strength_slider,
            self.color_slider,
            self.tone_slider,
            self.contrast_slider,
            self.saturation_slider,
            self.temperature_slider,
            self.tint_slider,
            self.highlights_slider,
            self.shadows_slider,
            self.clarity_slider,
            self.bloom_slider,
            self.fade_slider,
            self.grain_slider,
            self.vignette_slider,
        ]
        self.reflow_grid(self.controls_layout, self.sliders, 3)

        local_controls = QFrame()
        local_controls.setStyleSheet(
            """
            QFrame {
                background: #121822;
                border: 1px solid #263243;
                border-radius: 8px;
            }
            """
        )
        local_header = QLabel("DaVinci Local 调整台")
        local_header.setStyleSheet("color: #f2c763; font-size: 12px; font-weight: 900;")
        self.local_controls_layout = QGridLayout()
        self.local_controls_layout.setHorizontalSpacing(18)
        self.local_controls_layout.setVerticalSpacing(12)
        self.local_sliders = [
            self.window_x_slider,
            self.window_y_slider,
            self.window_size_slider,
            self.window_aspect_slider,
            self.luma_low_slider,
            self.luma_high_slider,
            self.qualifier_softness_slider,
            self.color_tolerance_slider,
            self.local_exposure_slider,
            self.local_contrast_slider,
            self.local_saturation_slider,
            self.local_detail_slider,
            self.mask_feather_slider,
            self.qualifier_range_slider,
            self.local_mix_slider,
        ]
        self.reflow_grid(self.local_controls_layout, self.local_sliders, 3)
        local_layout = QVBoxLayout(local_controls)
        local_layout.setContentsMargins(14, 14, 14, 14)
        local_layout.setSpacing(10)
        local_layout.addWidget(local_header)
        local_layout.addLayout(self.local_controls_layout)

        self.side_grid = QGridLayout()
        self.side_grid.setHorizontalSpacing(12)
        self.side_grid.setVerticalSpacing(12)
        history_card = self._make_side_card("History 最近 5 个版本", self.history_list)
        batch_card = self._make_side_card("Batch 批量队列", self.batch_list)
        histogram_card = self._make_side_card("Histogram 直方图", self.histogram_label)
        self.side_cards = [history_card, batch_card, histogram_card]
        self.reflow_grid(self.side_grid, self.side_cards, 3)

        split_row = QHBoxLayout()
        split_row.addWidget(QLabel("分割位置"))
        split_row.addWidget(self.split_slider, 1)
        split_row.addWidget(self.process_batch_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addLayout(mode_row)
        layout.addLayout(prompt_row)
        layout.addLayout(self.image_grid, 1)
        layout.addLayout(button_row)
        layout.addWidget(controls)
        layout.addWidget(local_controls)
        layout.addLayout(split_row)
        layout.addLayout(self.side_grid)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_box)

    def reflow_grid(self, layout: QGridLayout, widgets: list[QWidget], columns: int):
        while layout.count():
            layout.takeAt(0)
        safe_columns = max(1, columns)
        for index, widget in enumerate(widgets):
            layout.addWidget(widget, index // safe_columns, index % safe_columns)

    def apply_device_profile(self, profile: dict):
        mode = profile.get("mode", "regular")
        performance = profile.get("performance", {})
        if mode == "compact":
            margins = 14
            preview_height = 170
            image_columns = 1
            control_columns = 1
            side_columns = 1
            log_height = 88
            histogram_height = 92
        elif mode == "spacious":
            margins = 26
            preview_height = 280
            image_columns = 3
            control_columns = 3
            side_columns = 3
            log_height = 138
            histogram_height = 128
        else:
            margins = 20
            preview_height = 220
            image_columns = 2 if profile.get("width", 1440) < 1600 else 3
            control_columns = 2
            side_columns = 2
            log_height = 108
            histogram_height = 110
        for panel in self.image_panels:
            panel.set_preview_height(preview_height)
            panel.set_animation_enabled(not performance.get("reduce_motion", False))
        self.reflow_grid(self.image_grid, self.image_panels, image_columns)
        self.reflow_grid(self.controls_layout, self.sliders, control_columns)
        self.reflow_grid(self.local_controls_layout, self.local_sliders, control_columns)
        self.reflow_grid(self.side_grid, self.side_cards, side_columns)
        self.layout().setContentsMargins(margins, margins, margins, margins)
        self.creative_prompt.setMaximumHeight(48 if mode == "compact" else 58)
        self.log_box.setMinimumHeight(log_height)
        self.histogram_label.setMinimumHeight(histogram_height)

    def _make_side_card(self, title: str, widget: QWidget):
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background: #151a22;
                border: 1px solid #283242;
                border-radius: 8px;
            }
            """
        )
        label = QLabel(title)
        label.setStyleSheet("color: #8fa3b8; font-size: 12px; font-weight: 800;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(label)
        layout.addWidget(widget)
        return card

    def _connect_signals(self):
        self.pick_source_button.clicked.connect(self.pick_source_image)
        self.pick_reference_button.clicked.connect(self.pick_reference_image)
        self.pick_batch_button.clicked.connect(self.pick_batch_images)
        self.clear_reference_button.clicked.connect(self.clear_reference)
        self.auto_tune_button.clicked.connect(self.auto_tune_settings)
        self.save_recipe_button.clicked.connect(self.save_recipe)
        self.load_recipe_button.clicked.connect(self.load_recipe)
        self.compare_button.pressed.connect(self.show_original_preview)
        self.compare_button.released.connect(self.restore_output_preview)
        self.split_button.clicked.connect(self.draw_split_preview)
        self.split_slider.valueChanged.connect(self.draw_split_preview)
        self.generate_button.clicked.connect(self.generate_image)
        self.save_button.clicked.connect(self.save_output)
        self.process_batch_button.clicked.connect(self.process_batch_queue)
        self.reset_button.clicked.connect(self.reset_page)
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        self.source_panel.dropped.connect(self.set_source_image)
        self.reference_panel.dropped.connect(self.set_reference_image)
        self.history_list.itemClicked.connect(self.restore_history_item)

    def pick_source_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择原图", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        self.set_source_image(path)

    def set_source_image(self, path: str):
        if not Path(path).exists():
            return
        self.source_path = path
        self.source_panel.set_pixmap(load_preview_pixmap(path), self.image_meta(path))
        self.output_image = None
        self.output_panel.set_empty("生成后显示结果")
        self.save_button.setEnabled(False)
        self.compare_button.setEnabled(False)
        self.split_button.setEnabled(False)
        self.split_slider.setEnabled(False)
        self.update_histogram_from_path(path)
        self.append_log(f"载入原图：{Path(path).name}")

    def pick_reference_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择参考效果图", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        self.set_reference_image(path)

    def set_reference_image(self, path: str):
        if not Path(path).exists():
            return
        self.reference_path = path
        self.reference_panel.set_pixmap(load_preview_pixmap(path), self.image_meta(path))
        self.update_histogram_from_path(path)
        self.append_log(f"载入参考图：{Path(path).name}")

    def pick_batch_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择批量原图", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not paths:
            return
        self.batch_paths = paths
        self.batch_list.clear()
        for path in paths[:50]:
            self.batch_list.addItem(Path(path).name)
        self.process_batch_button.setEnabled(bool(self.batch_paths))
        self.append_log(f"批量队列：{len(paths)} 张原图")

    def clear_reference(self):
        self.reference_path = ""
        self.reference_panel.set_empty("可选：选择参考效果图")
        self.append_log("已清空参考图")

    def image_meta(self, path):
        if Image is None:
            return Path(path).name
        with Image.open(path) as image:
            return f"{Path(path).name} · {image.width} x {image.height}"

    def read_settings(self):
        mode_map = {"智能平衡": "balanced", "一比一还原": "exact", "创意增强": "creative"}
        local_map = {
            "自动判断": "auto",
            "AI智能精修": "smart",
            "全图应用": "global",
            "主体优先": "subject",
            "肤色人物": "skin",
            "高光天空": "highlights",
            "暗部细节": "shadows",
            "背景氛围": "background",
            "边缘质感": "edges",
        }
        preset = PRESET_VALUES.get(self.preset_combo.currentText(), PRESET_VALUES["自然校色"])
        output_map = {
            "跟随原图": "source_native",
            "处理尺寸": "processed",
            "长边4K": "long_4k",
            "长边8K": "long_8k",
            "智能2x": "smart_2x",
        }
        return {
            "preset": self.preset_combo.currentText(),
            "style_mode": preset.get("style_mode", "balanced"),
            "match_mode": mode_map.get(self.match_mode_combo.currentText(), "balanced"),
            "local_mode": local_map.get(self.local_mode_combo.currentText(), "auto"),
            "power_window": self.power_window_combo.currentText(),
            "qualifier": self.qualifier_combo.currentText(),
            "creative_prompt": self.creative_prompt.toPlainText().strip(),
            "strength": self.strength_slider.value(),
            "color": self.color_slider.value(),
            "tone": self.tone_slider.value(),
            "contrast": self.contrast_slider.value(),
            "saturation": self.saturation_slider.value(),
            "temperature": self.temperature_slider.value(),
            "tint": self.tint_slider.value(),
            "highlights": self.highlights_slider.value(),
            "shadows": self.shadows_slider.value(),
            "clarity": self.clarity_slider.value(),
            "bloom": self.bloom_slider.value(),
            "fade": self.fade_slider.value(),
            "grain": self.grain_slider.value(),
            "vignette": self.vignette_slider.value(),
            "local_exposure": self.local_exposure_slider.value(),
            "local_contrast": self.local_contrast_slider.value(),
            "local_saturation": self.local_saturation_slider.value(),
            "local_detail": self.local_detail_slider.value(),
            "mask_feather": self.mask_feather_slider.value(),
            "qualifier_range": self.qualifier_range_slider.value(),
            "local_mix": self.local_mix_slider.value(),
            "window_x": self.window_x_slider.value(),
            "window_y": self.window_y_slider.value(),
            "window_size": self.window_size_slider.value(),
            "window_aspect": self.window_aspect_slider.value(),
            "luma_low": self.luma_low_slider.value(),
            "luma_high": self.luma_high_slider.value(),
            "qualifier_softness": self.qualifier_softness_slider.value(),
            "color_tolerance": self.color_tolerance_slider.value(),
            "max_edge": int(self.max_edge_combo.currentText()),
            "output_resolution": output_map.get(self.output_resolution_combo.currentText(), "source_native"),
            "output_max_edge": 16384,
        }

    def generate_image(self):
        if not self.source_path:
            QMessageBox.warning(self, "缺少原图", "请先选择一张原图。")
            return
        if Image is None:
            QMessageBox.warning(self, "缺少依赖", "请先安装 Pillow。")
            return
        if self.worker and self.worker.isRunning():
            return

        self.progress_bar.setValue(0)
        self.generate_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.append_log("开始生成效果图")

        self.worker = ImageEffectWorker(self.source_path, self.reference_path, self.read_settings())
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished_image.connect(self.on_image_generated)
        self.worker.failed.connect(self.on_image_failed)
        self.worker.start()

    def on_image_generated(self, image):
        self.output_image = image
        self.original_preview_image = resize_for_processing(Image.open(self.source_path), max(image.size)).resize(image.size, Image.Resampling.LANCZOS)
        self.output_panel.set_pixmap(pil_to_pixmap(image), f"PNG 输出 · {image.width} x {image.height}")
        self.update_histogram_from_image(image)
        self.push_history(image)
        self.progress_bar.setValue(100)
        self.generate_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.compare_button.setEnabled(True)
        self.split_button.setEnabled(True)
        self.split_slider.setEnabled(True)
        self.model_status.setText(f"生成完成 · {self.local_mode_combo.currentText()} / {self.power_window_combo.currentText()} · 可对比/分割/保存")
        self.append_log("生成完成")

    def on_image_failed(self, message: str):
        self.generate_button.setEnabled(True)
        self.append_log(f"生成失败：{message}")
        QMessageBox.warning(self, "生成失败", message)

    def save_output(self):
        if self.output_image is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存生成结果", "effect-output.png", "PNG Image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        self.output_image.save(path, "PNG")
        self.append_log(f"已保存：{path}")

    def apply_preset(self, name: str):
        values = PRESET_VALUES.get(name)
        if not values:
            return
        mapping = {
            "strength": self.strength_slider,
            "color": self.color_slider,
            "tone": self.tone_slider,
            "contrast": self.contrast_slider,
            "saturation": self.saturation_slider,
            "temperature": self.temperature_slider,
            "tint": self.tint_slider,
            "highlights": self.highlights_slider,
            "shadows": self.shadows_slider,
            "clarity": self.clarity_slider,
            "bloom": self.bloom_slider,
            "fade": self.fade_slider,
            "grain": self.grain_slider,
            "vignette": self.vignette_slider,
        }
        for key, slider in mapping.items():
            if key in values:
                slider.slider.setValue(values[key])
        self.model_status.setText(f"已应用预设：{name}")

    def auto_tune_settings(self):
        if not self.source_path:
            QMessageBox.warning(self, "缺少原图", "请先选择原图再智能推荐。")
            return
        if Image is None:
            return
        with Image.open(self.source_path) as source:
            source = resize_for_processing(source, 900)
            gray = ImageOps.grayscale(source)
            stat = ImageStat.Stat(gray)
            mean = stat.mean[0]
            std = stat.stddev[0]
        target = PRESET_VALUES.get(self.preset_combo.currentText(), PRESET_VALUES["自然校色"]).copy()
        if self.reference_path:
            with Image.open(self.reference_path) as reference:
                reference = resize_for_processing(reference, 900)
                ref_gray = ImageOps.grayscale(reference)
                ref_stat = ImageStat.Stat(ref_gray)
                ref_mean = ref_stat.mean[0]
                ref_std = ref_stat.stddev[0]
            target["tone"] = max(50, min(96, int(64 + abs(ref_mean - mean) * 0.32 + abs(ref_std - std) * 0.8)))
            target["contrast"] = max(-20, min(92, int(18 + (ref_std - std) * 1.2)))
            target["color"] = 88
            self.model_status.setText("智能推荐：已根据原图和参考图校准")
        else:
            if mean < 92:
                target["shadows"] = 36
            if mean > 190:
                target["highlights"] = -34
            target["clarity"] = max(target.get("clarity", 30), 42 if std < 45 else 28)
            self.model_status.setText("智能推荐：已根据原图状态校准")
        self.apply_settings(target)
        self.local_mode_combo.setCurrentText("AI智能精修")
        self.power_window_combo.setCurrentText("主体窗口")
        self.qualifier_combo.setCurrentText("智能限定")
        self.window_x_slider.slider.setValue(50)
        self.window_y_slider.slider.setValue(50)
        self.window_size_slider.slider.setValue(108)
        self.window_aspect_slider.slider.setValue(105)
        self.luma_low_slider.slider.setValue(0)
        self.luma_high_slider.slider.setValue(255)
        self.qualifier_softness_slider.slider.setValue(36)
        self.color_tolerance_slider.slider.setValue(58)
        if mean > 176:
            self.power_window_combo.setCurrentText("上半天空")
            self.qualifier_combo.setCurrentText("高光限定")
            self.local_exposure_slider.slider.setValue(-10)
            self.window_y_slider.slider.setValue(48)
            self.window_size_slider.slider.setValue(112)
            self.luma_low_slider.slider.setValue(145)
            self.luma_high_slider.slider.setValue(255)
        elif mean < 92:
            self.power_window_combo.setCurrentText("主体窗口")
            self.qualifier_combo.setCurrentText("暗部限定")
            self.local_exposure_slider.slider.setValue(14)
            self.luma_low_slider.slider.setValue(0)
            self.luma_high_slider.slider.setValue(132)
        else:
            self.local_exposure_slider.slider.setValue(8)
        self.local_detail_slider.slider.setValue(34 if std < 45 else 24)
        self.append_log("智能推荐参数已应用")

    def apply_settings(self, settings: dict):
        if settings.get("preset") in PRESET_VALUES:
            self.preset_combo.setCurrentText(settings["preset"])
        mapping = {
            "strength": self.strength_slider,
            "color": self.color_slider,
            "tone": self.tone_slider,
            "contrast": self.contrast_slider,
            "saturation": self.saturation_slider,
            "temperature": self.temperature_slider,
            "tint": self.tint_slider,
            "highlights": self.highlights_slider,
            "shadows": self.shadows_slider,
            "clarity": self.clarity_slider,
            "bloom": self.bloom_slider,
            "fade": self.fade_slider,
            "grain": self.grain_slider,
            "vignette": self.vignette_slider,
            "local_exposure": self.local_exposure_slider,
            "local_contrast": self.local_contrast_slider,
            "local_saturation": self.local_saturation_slider,
            "local_detail": self.local_detail_slider,
            "mask_feather": self.mask_feather_slider,
            "qualifier_range": self.qualifier_range_slider,
            "local_mix": self.local_mix_slider,
            "window_x": self.window_x_slider,
            "window_y": self.window_y_slider,
            "window_size": self.window_size_slider,
            "window_aspect": self.window_aspect_slider,
            "luma_low": self.luma_low_slider,
            "luma_high": self.luma_high_slider,
            "qualifier_softness": self.qualifier_softness_slider,
            "color_tolerance": self.color_tolerance_slider,
        }
        for key, slider in mapping.items():
            if key in settings:
                slider.slider.setValue(int(settings[key]))
        if "max_edge" in settings:
            self.max_edge_combo.setCurrentText(str(settings["max_edge"]))
        output_reverse = {
            "source_native": "跟随原图",
            "native": "跟随原图",
            "processed": "处理尺寸",
            "long_4k": "长边4K",
            "long_8k": "长边8K",
            "smart_2x": "智能2x",
        }
        if settings.get("output_resolution") in output_reverse:
            self.output_resolution_combo.setCurrentText(output_reverse[settings["output_resolution"]])
        if settings.get("power_window"):
            self.power_window_combo.setCurrentText(settings["power_window"])
        if settings.get("qualifier"):
            self.qualifier_combo.setCurrentText(settings["qualifier"])
        if "creative_prompt" in settings:
            self.creative_prompt.setPlainText(settings["creative_prompt"])
        match_reverse = {"balanced": "智能平衡", "exact": "一比一还原", "creative": "创意增强"}
        local_reverse = {
            "auto": "自动判断",
            "smart": "AI智能精修",
            "global": "全图应用",
            "subject": "主体优先",
            "skin": "肤色人物",
            "highlights": "高光天空",
            "shadows": "暗部细节",
            "background": "背景氛围",
            "edges": "边缘质感",
        }
        if settings.get("match_mode") in match_reverse:
            self.match_mode_combo.setCurrentText(match_reverse[settings["match_mode"]])
        if settings.get("local_mode") in local_reverse:
            self.local_mode_combo.setCurrentText(local_reverse[settings["local_mode"]])

    def save_recipe(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存方案", "effect-recipe.json", "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        data = {"version": 1, "settings": self.read_settings()}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.append_log(f"方案已保存：{path}")

    def load_recipe(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入方案", "", "JSON (*.json)")
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        settings = data.get("settings", data)
        self.apply_settings(settings)
        self.append_log(f"方案已导入：{Path(path).name}")

    def show_original_preview(self):
        if self.original_preview_image is not None:
            self.output_panel.set_pixmap(pil_to_pixmap(self.original_preview_image), "正在对比原图")

    def restore_output_preview(self):
        if self.output_image is not None:
            self.output_panel.set_pixmap(pil_to_pixmap(self.output_image), f"PNG 输出 · {self.output_image.width} x {self.output_image.height}")

    def draw_split_preview(self):
        if self.output_image is None or self.original_preview_image is None:
            return
        split = int(self.output_image.width * (self.split_slider.value() / 100))
        preview = self.original_preview_image.copy()
        right = self.output_image.crop((split, 0, self.output_image.width, self.output_image.height))
        preview.paste(right, (split, 0))
        draw = ImageDraw.Draw(preview)
        draw.line((split, 0, split, preview.height), fill=(255, 255, 255), width=3)
        self.output_panel.set_pixmap(pil_to_pixmap(preview), f"分割预览 · {self.split_slider.value()}%")

    def push_history(self, image):
        self.history.insert(0, image.copy())
        self.history = self.history[:5]
        self.history_list.clear()
        for index, item in enumerate(self.history):
            self.history_list.addItem(f"版本 {index + 1} · {item.width} x {item.height}")

    def restore_history_item(self, item):
        index = self.history_list.row(item)
        if 0 <= index < len(self.history):
            self.output_image = self.history[index].copy()
            self.output_panel.set_pixmap(pil_to_pixmap(self.output_image), f"已恢复历史版本 {index + 1}")
            self.save_button.setEnabled(True)
            self.compare_button.setEnabled(bool(self.original_preview_image))
            self.split_button.setEnabled(bool(self.original_preview_image))
            self.split_slider.setEnabled(bool(self.original_preview_image))
            self.update_histogram_from_image(self.output_image)

    def update_histogram_from_path(self, path):
        if Image is None:
            return
        with Image.open(path) as image:
            self.update_histogram_from_image(resize_for_processing(image, 900))

    def update_histogram_from_image(self, image):
        self.histogram_label.setPixmap(make_histogram_pixmap(image))
        self.histogram_label.setText("")

    def process_batch_queue(self):
        if not self.batch_paths:
            return
        if self.batch_worker and self.batch_worker.isRunning():
            return
        output_dir = QFileDialog.getExistingDirectory(self, "选择批量输出文件夹")
        if not output_dir:
            return
        settings = self.read_settings()
        self.append_log(f"开始批量处理：{len(self.batch_paths)} 张")
        self.progress_bar.setValue(0)
        self.process_batch_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.batch_worker = BatchImageWorker(self.batch_paths, self.reference_path, settings, output_dir)
        self.batch_worker.progress_changed.connect(self.progress_bar.setValue)
        self.batch_worker.log_message.connect(self.append_log)
        self.batch_worker.finished_successfully.connect(self.on_batch_finished)
        self.batch_worker.failed.connect(self.on_batch_failed)
        self.batch_worker.finished.connect(self.batch_worker.deleteLater)
        self.batch_worker.finished.connect(lambda: setattr(self, "batch_worker", None))
        self.batch_worker.start()

    def on_batch_finished(self):
        self.progress_bar.setValue(100)
        self.process_batch_button.setEnabled(bool(self.batch_paths))
        self.generate_button.setEnabled(True)
        self.append_log("批量处理完成")

    def on_batch_failed(self, message: str):
        self.process_batch_button.setEnabled(bool(self.batch_paths))
        self.generate_button.setEnabled(True)
        self.append_log(f"批量处理失败：{message}")
        QMessageBox.warning(self, "批量失败", message)

    def reset_page(self):
        self.source_path = ""
        self.reference_path = ""
        self.output_image = None
        self.original_preview_image = None
        self.batch_paths = []
        self.source_panel.set_empty("拖入或选择原始图片")
        self.reference_panel.set_empty("可选：选择参考效果图")
        self.output_panel.set_empty("生成后显示结果")
        self.batch_list.clear()
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.histogram_label.setPixmap(QPixmap())
        self.histogram_label.setText("等待图像")
        self.save_button.setEnabled(False)
        self.compare_button.setEnabled(False)
        self.split_button.setEnabled(False)
        self.split_slider.setEnabled(False)
        self.process_batch_button.setEnabled(False)
        self.preset_combo.setCurrentText("自然校色")
        self.apply_preset("自然校色")
        self.local_mode_combo.setCurrentText("自动判断")
        self.power_window_combo.setCurrentText("主体窗口")
        self.qualifier_combo.setCurrentText("智能限定")
        self.local_exposure_slider.slider.setValue(8)
        self.local_contrast_slider.slider.setValue(12)
        self.local_saturation_slider.slider.setValue(8)
        self.local_detail_slider.slider.setValue(28)
        self.mask_feather_slider.slider.setValue(44)
        self.qualifier_range_slider.slider.setValue(74)
        self.local_mix_slider.slider.setValue(72)
        self.window_x_slider.slider.setValue(50)
        self.window_y_slider.slider.setValue(50)
        self.window_size_slider.slider.setValue(100)
        self.window_aspect_slider.slider.setValue(100)
        self.luma_low_slider.slider.setValue(0)
        self.luma_high_slider.slider.setValue(255)
        self.qualifier_softness_slider.slider.setValue(32)
        self.color_tolerance_slider.slider.setValue(55)
        self.model_status.setText("模型监控待命")

    def append_log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{now}] {message}")


class GpuMetricsWorker(QThread):
    """后台读取 GPU 数据，避免 nvidia-smi/WMI 查询阻塞主界面。"""

    metrics_ready = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            self.metrics_ready.emit(detect_live_gpu_metrics())
        except Exception as error:
            self.failed.emit(str(error))


class SystemProfileWorker(QThread):
    """后台刷新完整系统档案，避免启动阶段等待硬件检测。"""

    finished_profile = Signal(str)
    failed = Signal(str)

    def __init__(self, screen_profile: dict):
        super().__init__()
        self.screen_profile = screen_profile

    def run(self):
        try:
            hardware_profile = build_medium_video_profile()
            path = write_system_profile(self.screen_profile, hardware_profile=hardware_profile)
            self.finished_profile.emit(str(path))
        except Exception as error:
            self.failed.emit(str(error))


class HardwareMonitorPage(QWidget):
    """硬件监控页面。

    CPU 和内存通过 psutil 读取；GPU 优先通过 nvidia-smi 读取，再回退 GPUtil/WMI。
    QTimer 每秒刷新一次，主线程只做轻量 UI 更新，不执行耗时任务。
    """

    def __init__(self):
        super().__init__()

        self.cpu_row = MetricRow("CPU 使用率：--")
        self.memory_row = MetricRow("内存占用：--")
        self.gpu_usage_row = MetricRow("GPU 使用率：--")
        self.vram_row = MetricRow("显存占用：--")
        self.gpu_temperature_label = QLabel("GPU 温度：--")
        self.gpu_name_label = QLabel("GPU：--")
        self.advice_label = QLabel("系统建议：等待硬件数据")
        self.advice_label.setWordWrap(True)
        self.advice_label.setStyleSheet("color: #f2c763; font-weight: 800;")
        self.cpu_tile = SummaryTile("CPU", "--")
        self.memory_tile = SummaryTile("MEMORY", "--")
        self.gpu_tile = SummaryTile("GPU", "--")
        self.temperature_tile = SummaryTile("TEMP", "--")
        self.gpu_worker = None
        self.gpu_refresh_ms = 2800
        self._last_gpu_refresh = 0.0

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_metrics)
        self.timer.start(1000)
        self.refresh_metrics()

    def apply_device_profile(self, profile: dict):
        margins = 14 if profile.get("mode") == "compact" else 24
        self.gpu_refresh_ms = int(profile.get("performance", {}).get("gpu_refresh_ms", self.gpu_refresh_ms))
        self.layout().setContentsMargins(margins, margins, margins, margins)

    def _build_ui(self):
        title = SectionTitle(
            "硬件监控面板",
            "实时显示 CPU、内存、GPU 温度、GPU 使用率和显存占用，方便后续做模型部署策略。",
        )

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            """
            QFrame {
                background: #121822;
                border: 1px solid #263243;
                border-radius: 8px;
            }
            """
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(14)
        card_layout.addWidget(self.cpu_row)
        card_layout.addWidget(self.memory_row)
        card_layout.addWidget(self.gpu_name_label)
        card_layout.addWidget(self.gpu_temperature_label)
        card_layout.addWidget(self.gpu_usage_row)
        card_layout.addWidget(self.vram_row)
        card_layout.addWidget(self.advice_label)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        summary_grid.setVerticalSpacing(12)
        summary_grid.addWidget(self.cpu_tile, 0, 0)
        summary_grid.addWidget(self.memory_tile, 0, 1)
        summary_grid.addWidget(self.gpu_tile, 0, 2)
        summary_grid.addWidget(self.temperature_tile, 0, 3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addLayout(summary_grid)
        layout.addWidget(card)
        layout.addStretch()

    def refresh_metrics(self):
        if psutil is None:
            self.cpu_row.set_metric("CPU 使用率：psutil 未安装", 0)
            self.memory_row.set_metric("内存占用：psutil 未安装", 0)
            self.cpu_tile.set_value("未安装")
            self.memory_tile.set_value("未安装")
        else:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            self.cpu_row.set_metric(f"CPU 使用率：{cpu_percent:.1f}%", cpu_percent)
            self.memory_row.set_metric(
                f"内存占用：{memory.percent:.1f}% ({format_bytes(memory.used)} / {format_bytes(memory.total)})",
                memory.percent,
            )
            self.cpu_tile.set_value(f"{cpu_percent:.0f}%")
            self.memory_tile.set_value(f"{memory.percent:.0f}%")
            if cpu_percent > 85 or memory.percent > 86:
                self.advice_label.setText("系统建议：当前负载偏高，图片建议先用 1600/2400，上视频建议用极速预览。")
            else:
                self.advice_label.setText("系统建议：负载正常，可以使用均衡加速和 2400/3200 图片输出。")

        now = time.monotonic()
        if self.gpu_worker is None and (now - self._last_gpu_refresh) * 1000 >= self.gpu_refresh_ms:
            self.start_gpu_refresh()

    def start_gpu_refresh(self):
        self._last_gpu_refresh = time.monotonic()
        self.gpu_worker = GpuMetricsWorker(self)
        self.gpu_worker.metrics_ready.connect(self.apply_gpu_metrics)
        self.gpu_worker.failed.connect(self.on_gpu_metrics_failed)
        self.gpu_worker.finished.connect(self.gpu_worker.deleteLater)
        self.gpu_worker.finished.connect(lambda: setattr(self, "gpu_worker", None))
        self.gpu_worker.start()

    def apply_gpu_metrics(self, gpu: dict):
        if not gpu.get("available"):
            self.gpu_name_label.setText("GPU：未检测到独立 GPU")
            self.gpu_temperature_label.setText("GPU 温度：--")
            self.gpu_usage_row.set_metric("GPU 使用率：--", 0)
            self.vram_row.set_metric("显存占用：--", 0)
            self.gpu_tile.set_value("未检测")
            self.temperature_tile.set_value("--")
            return

        gpu_usage = float(gpu.get("load", 0) or 0)
        memory_used = float(gpu.get("memory_used", 0) or 0)
        memory_total = float(gpu.get("memory_total", 0) or 0)
        temperature = gpu.get("temperature")
        vram_usage = (memory_used / memory_total * 100) if memory_total else 0

        self.gpu_name_label.setText(f"GPU：{gpu.get('name', '--')} · 数据源 {gpu.get('source', '--')}")
        self.gpu_temperature_label.setText(f"GPU 温度：{temperature:.0f} °C" if temperature is not None else "GPU 温度：--")
        self.gpu_usage_row.set_metric(f"GPU 使用率：{gpu_usage:.1f}%", gpu_usage)
        self.vram_row.set_metric(
            f"显存占用：{vram_usage:.1f}% ({memory_used:.0f} MB / {memory_total:.0f} MB)",
            vram_usage,
        )
        self.gpu_tile.set_value(f"{gpu_usage:.0f}%")
        self.temperature_tile.set_value(f"{temperature:.0f}°C" if temperature is not None else "--")
        if memory_total >= 8000 and gpu_usage < 70:
            self.advice_label.setText("系统建议：GPU 状态良好，可使用 FLUX 图像处理、1080p/60FPS 视频和局部精修。")
        elif gpu_usage >= 85:
            self.advice_label.setText("系统建议：GPU 正忙，先等待渲染完成，避免同时开启多个生成任务。")

    def on_gpu_metrics_failed(self, message: str):
        self.gpu_name_label.setText(f"GPU：后台刷新失败 · {message[:48]}")
        self.gpu_tile.set_value("刷新失败")

    def shutdown(self):
        self.timer.stop()
        worker = self.gpu_worker
        self.gpu_worker = None
        try:
            if worker and worker.isRunning():
                worker.wait(1200)
        except RuntimeError:
            pass


class DeploymentWorker(QThread):
    """模型部署线程。

    当前版本模拟部署过程。以后接入真实部署时，把 run() 中的步骤替换成：
    下载模型、校验 hash、创建虚拟环境、写配置、启动服务等真实逻辑即可。
    """

    progress_changed = Signal(int)
    log_message = Signal(str)
    finished_successfully = Signal()
    failed = Signal(str)

    def __init__(self, model_config: dict):
        super().__init__()
        self.model_config = model_config
        self.model_name = model_config.get("name", "未命名模型")
        self._should_stop = False

    def stop(self):
        self._should_stop = True

    def run(self):
        steps = [
            "检查系统环境",
            "读取 CPU / GPU / 内存信息",
            "创建模型运行目录",
            f"读取模型来源：{self.model_config.get('source', '未填写')}",
            f"准备部署类型：{self.model_config.get('kind', '通用模型')}",
            "准备模型文件或 API 清单",
            "校验模型文件",
            f"生成启动方式：{self.model_config.get('launch', '手动启动')}",
            "生成启动配置",
            "写入部署记录",
            "完成部署检查",
        ]

        try:
            for index, step in enumerate(steps, start=1):
                if self._should_stop:
                    self.log_message.emit("部署已取消")
                    return

                now = datetime.now().strftime("%H:%M:%S")
                self.log_message.emit(f"[{now}] {self.model_name}：{step}")
                self.progress_changed.emit(int(index / len(steps) * 100))
                time.sleep(0.55)

            record = {
                "name": self.model_name,
                "kind": self.model_config.get("kind", "通用模型"),
                "source": self.model_config.get("source", ""),
                "launch": self.model_config.get("launch", ""),
                "min_vram": self.model_config.get("min_vram", ""),
                "deployed_at": datetime.now().isoformat(timespec="seconds"),
                "status": "success",
            }
            output_path = deployment_records_dir() / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_slug(self.model_name)}.json"
            output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log_message.emit(f"部署记录：{output_path}")
            self.finished_successfully.emit()
        except Exception as error:
            self.failed.emit(str(error))


class VideoRenderWorker(QThread):
    """视频渲染线程：自动调用本机 FFmpeg 和可用硬件编码器。"""

    progress_changed = Signal(int)
    log_message = Signal(str)
    finished_video = Signal(str)
    failed = Signal(str)

    def __init__(self, source_path: str, output_dir: str, settings: dict):
        super().__init__()
        self.source_path = source_path
        self.output_dir = output_dir
        self.settings = settings
        self._process = None

    def stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def probe_duration(self) -> float:
        ffprobe_path = self.settings["ffmpeg"].get("ffprobe")
        if not ffprobe_path:
            return 0.0
        try:
            completed = subprocess.run(
                [
                    ffprobe_path,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    self.source_path,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return max(0.0, float((completed.stdout or "0").strip() or 0))
        except Exception:
            return 0.0

    def mode_slug(self, mode_name: str) -> str:
        return {
            "极速预览": "fast",
            "均衡加速": "balanced",
            "高清输出": "hq",
            "120帧补帧": "120fps",
            "移动端清晰": "mobile",
        }.get(mode_name, "balanced")

    def build_attempts(self) -> list[dict]:
        attempts = [dict(self.settings, rescue_name="首选方案")]
        if not self.settings.get("auto_rescue", True):
            return attempts

        ffmpeg = self.settings.get("ffmpeg", {})
        requested_encoder = self.settings.get("encoder", "libx264")
        h264_encoder = compatible_h264_encoder(ffmpeg)

        aac_attempt = dict(self.settings, rescue_name="AI救援：改用 AAC 音频", audio_mode="AAC 192k")
        attempts.append(aac_attempt)

        if requested_encoder != h264_encoder or self.settings.get("codec") == "H.265高压缩":
            attempts.append(dict(
                self.settings,
                rescue_name=f"AI救援：切换兼容 H.264 编码器 {h264_encoder}",
                encoder=h264_encoder,
                codec="H.264兼容",
                audio_mode="AAC 192k",
                container="mp4",
            ))

        attempts.append(dict(
            self.settings,
            rescue_name="AI救援：CPU 兼容渲染",
            encoder="libx264",
            codec="H.264兼容",
            audio_mode="AAC 192k",
            container="mp4",
            hwaccel=False,
            quality="均衡",
        ))

        attempts.append(dict(
            self.settings,
            rescue_name="AI救援：低滤镜安全渲染",
            encoder="libx264",
            codec="H.264兼容",
            audio_mode="AAC 192k",
            container="mp4",
            hwaccel=False,
            quality="极速",
            grade_strength=0,
            fps=min(60, int(self.settings.get("fps", 60))),
        ))

        unique = []
        seen = set()
        for item in attempts:
            key = (
                item.get("encoder"),
                item.get("container"),
                item.get("audio_mode"),
                item.get("quality"),
                item.get("grade_strength"),
                item.get("hwaccel", True),
                item.get("fps"),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def output_path_for_attempt(self, source: Path, output_root: Path, settings: dict, index: int) -> Path:
        mode_name = settings.get("mode", "均衡加速")
        grade_name = settings.get("grade", "自然增强")
        container = settings.get("container", "mp4")
        suffix = "" if index == 1 else f"-rescue{index}"
        return output_root / (
            f"{source.stem}-{self.mode_slug(mode_name)}-{safe_slug(grade_name)}-"
            f"{settings['fps']}fps-{settings['edge']}p{suffix}.{container}"
        )

    def build_command(self, ffmpeg_path: str, source: Path, output_path: Path, settings: dict) -> list[str]:
        mode_name = settings.get("mode", "均衡加速")
        grade_name = settings.get("grade", "自然增强")
        quality_name = settings.get("quality", "均衡")
        container = settings.get("container", "mp4")
        command = [
            ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-stats_period",
            "0.5",
            "-progress",
            "pipe:1",
            "-nostdin",
        ]
        if settings.get("hwaccel", True):
            command.extend(["-hwaccel", "auto"])
        command.extend([
            "-threads",
            str(settings["threads"]),
            "-i",
            str(source),
            "-vf",
            video_filter_chain(
                settings["edge"],
                settings["fps"],
                settings["sharpen"],
                mode_name,
                grade_name,
                settings.get("grade_strength", 65),
            ),
            *encoder_arguments(settings["encoder"], mode_name, quality_name),
            "-pix_fmt",
            "yuv420p",
        ])
        if container in ("mp4", "mov"):
            command.extend(["-movflags", "+faststart"])
        command.extend(audio_arguments(mode_name, settings.get("audio_mode", "自动"), quality_name))
        command.append(str(output_path))
        return command

    def run_ffmpeg_command(self, command: list[str], duration: float, attempt_index: int) -> tuple[int, list[str]]:
        lines = []
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        frame_count = 0
        last_percent = 8
        for line in self._process.stdout or []:
            line = line.strip()
            if not line:
                continue
            lines.append(line)
            if len(lines) > 400:
                lines = lines[-400:]
            if line.startswith(("out_time_us=", "out_time_ms=")) and duration > 0:
                raw_value = float(line.split("=", 1)[1] or 0)
                current_seconds = raw_value / 1_000_000
                last_percent = max(last_percent, min(96, int(8 + current_seconds / duration * 88)))
                self.progress_changed.emit(last_percent)
                continue
            if line.startswith("out_time=") and duration > 0:
                parts = line.split("=", 1)[1].split(":")
                if len(parts) == 3:
                    current_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    last_percent = max(last_percent, min(96, int(8 + current_seconds / duration * 88)))
                    self.progress_changed.emit(last_percent)
                continue
            if line.startswith("frame=") or line.startswith("total_size="):
                frame_count += 1
                last_percent = min(94, max(last_percent, 8 + frame_count))
                self.progress_changed.emit(last_percent)
            if line.startswith("speed=") or "error" in line.lower() or "failed" in line.lower():
                self.log_message.emit(f"尝试 {attempt_index}: {line[-220:]}")
        return_code = self._process.wait()
        return return_code, lines

    def write_failure_log(self, source: Path, attempts: list[dict], failures: list[dict]) -> Path:
        path = video_diagnostics_dir() / f"ffmpeg-failure-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_slug(source.stem)}.log"
        chunks = [
            f"{APP_NAME} {APP_VERSION} video render failure",
            f"time={datetime.now().isoformat(timespec='seconds')}",
            f"source={source}",
            "",
        ]
        for index, failure in enumerate(failures, start=1):
            chunks.extend([
                f"--- attempt {index}: {failure.get('name', '')} ---",
                f"return_code={failure.get('return_code')}",
                "command=" + " ".join(failure.get("command", [])),
                "tail:",
                "\n".join(failure.get("lines", [])[-80:]),
                "",
            ])
        path.write_text("\n".join(chunks), encoding="utf-8")
        return path

    def run(self):
        ffmpeg_path = self.settings["ffmpeg"].get("ffmpeg")
        if not ffmpeg_path:
            self.failed.emit("未检测到 FFmpeg，无法进行视频硬件渲染")
            return

        source = Path(self.source_path)
        output_root = Path(self.output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        duration = self.probe_duration()
        self.progress_changed.emit(8)
        attempts = self.build_attempts()
        failures = []

        for index, attempt in enumerate(attempts, start=1):
            output_path = self.output_path_for_attempt(source, output_root, attempt, index)
            command = self.build_command(ffmpeg_path, source, output_path, attempt)
            self.log_message.emit(f"调用 FFmpeg：{Path(ffmpeg_path).name}")
            self.log_message.emit(f"{attempt.get('rescue_name', '渲染方案')}：{attempt['encoder']} · {attempt.get('quality', '均衡')} · {attempt.get('container', 'mp4').upper()} · {attempt.get('audio_mode', '自动')}")
            self.log_message.emit(
                f"视频AI链路：{attempt.get('mode', '均衡加速')} / {attempt.get('grade', '自然增强')} / "
                f"{attempt['edge']}p / {attempt['fps']}FPS / hwaccel={'开' if attempt.get('hwaccel', True) else '关'}"
            )
            try:
                return_code, lines = self.run_ffmpeg_command(command, duration, index)
            except Exception as error:
                return_code, lines = -1, [str(error)]
            if return_code == 0 and output_path.exists() and output_path.stat().st_size > 0:
                self.progress_changed.emit(100)
                if index > 1:
                    self.log_message.emit(f"AI自动救援成功：第 {index} 套方案完成")
                self.finished_video.emit(str(output_path))
                return
            failures.append({
                "name": attempt.get("rescue_name", ""),
                "return_code": return_code,
                "command": command,
                "lines": lines,
            })
            self.log_message.emit(f"方案失败：退出码 {return_code}，准备自动降级" if index < len(attempts) else f"方案失败：退出码 {return_code}")

        log_path = self.write_failure_log(source, attempts, failures)
        self.failed.emit(f"FFmpeg 渲染失败，已写入诊断日志：{log_path}")


class ComfyStatusWorker(QThread):
    """ComfyUI 状态检测线程，避免 UI 等待网络请求。"""

    finished_status = Signal(dict)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        self.finished_status.emit(comfy_status(self.url))


class ComfyStartWorker(QThread):
    """启动本机 ComfyUI，避免主界面阻塞。"""

    log_message = Signal(str)
    started_process = Signal(object)
    failed = Signal(str)

    def __init__(self, port: int = 8188):
        super().__init__()
        self.port = port

    def run(self):
        root = find_comfyui_root()
        if not root:
            self.failed.emit("未找到 ComfyUI 目录。可放到 tools/ComfyUI，或设置 COMFYUI_PATH 环境变量。")
            return
        root_path = Path(root)
        python_candidates = [
            root_path.parent / "python_embeded" / "python.exe",
            root_path.parent / "python_embedded" / "python.exe",
            root_path / "venv" / "Scripts" / "python.exe",
            Path(sys.executable),
        ]
        python_path = ""
        for candidate in python_candidates:
            if candidate.exists():
                python_path = str(candidate)
                break
        if not python_path:
            self.failed.emit("未找到可用于启动 ComfyUI 的 Python。")
            return
        try:
            process = subprocess.Popen(
                [
                    python_path,
                    "main.py",
                    "--listen",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                ],
                cwd=str(root_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self.log_message.emit(f"已尝试启动 ComfyUI：{root_path}")
            self.started_process.emit(process)
        except Exception as error:
            self.failed.emit(str(error))


class VideoProfileWorker(QThread):
    """后台检测 FFmpeg、编码器和 GPU，避免视频页初始化卡住。"""

    profile_ready = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            self.profile_ready.emit(build_medium_video_profile())
        except Exception as error:
            self.failed.emit(str(error))


class VideoWorkstationPage(QWidget):
    """原生视频工作站：自动识别硬件，中等占用调用系统 FFmpeg 管线。"""

    def __init__(self):
        super().__init__()

        self.source_path = ""
        self.output_dir = default_output_dir("video")
        self.profile = fast_default_video_profile()
        self.profile_worker = None
        self.worker = None
        self.comfy_worker = None
        self.comfy_start_worker = None
        self.comfy_process = None

        self.gpu_tile = SummaryTile("GPU", self.profile["gpu"]["name"][:22])
        self.vram_tile = SummaryTile("VRAM", f"{self.profile['gpu']['vram_mb']} MB")
        self.encoder_tile = SummaryTile("ENCODER", self.profile["encoder"])
        self.mode_tile = SummaryTile("MODE", "均衡加速")
        self.output_tile = SummaryTile("OUTPUT", "1080p / 60FPS")
        self.comfy_tile = SummaryTile("COMFYUI", "待检测")

        self.source_label = QLabel("未选择视频")
        self.output_label = QLabel(self.output_dir)
        self.comfy_url_input = QLineEdit("http://127.0.0.1:8188")
        self.mode_combo = QComboBox()
        self.grade_combo = QComboBox()
        self.grade_strength_slider = SliderRow("专业强度", 0, 100, 65)
        self.codec_combo = QComboBox()
        self.quality_combo = QComboBox()
        self.container_combo = QComboBox()
        self.audio_combo = QComboBox()
        self.ai_rescue_checkbox = QCheckBox("AI自动救援")
        self.fps_combo = QComboBox()
        self.edge_combo = QComboBox()
        self.encoder_combo = QComboBox()
        self.mode_note_label = QLabel("默认推荐：速度和清晰度比较均衡")
        self.encoding_note_label = QLabel("编码链路：等待配置")
        self.pick_video_button = QPushButton("选择视频")
        self.pick_output_button = QPushButton("输出目录")
        self.auto_button = QPushButton("自动中等配置")
        self.render_button = QPushButton("系统硬件渲染")
        self.stop_button = QPushButton("停止")
        self.check_comfy_button = QPushButton("检查 ComfyUI/FLUX")
        self.start_comfy_button = QPushButton("启动 ComfyUI")
        self.progress_bar = QProgressBar()
        self.log_box = QTextEdit()

        self._build_ui()
        self._connect_signals()
        self.apply_video_mode(self.mode_combo.currentText())
        QTimer.singleShot(500, self.refresh_auto_profile)

    def _build_ui(self):
        title = SectionTitle(
            "视频工作站",
            "本机硬件视频管线：优先走 NVENC，默认使用加速模式；需要极致画质或 120 帧时再切换档位。",
        )

        self.mode_combo.addItems(list(VIDEO_MODE_SETTINGS.keys()))
        self.grade_combo.addItems(list(VIDEO_GRADE_PRESETS.keys()))
        self.codec_combo.addItems(["H.264兼容", "H.265高压缩"])
        self.quality_combo.addItems(list(ENCODE_QUALITY_SETTINGS.keys()))
        self.container_combo.addItems(["mp4", "mkv", "mov"])
        self.audio_combo.addItems(["自动", "复制原音", "AAC 192k", "AAC 320k", "静音"])
        self.ai_rescue_checkbox.setChecked(True)
        self.ai_rescue_checkbox.setStyleSheet("color: #58dcc7; font-weight: 900;")
        self.fps_combo.addItems(["30", "48", "60", "120"])
        self.edge_combo.addItems(["720", "1080", "1440", "2048", "2560", "3840"])
        self.encoder_combo.addItems(["auto", "h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv", "h264_amf", "hevc_amf", "libx264", "libx265"])
        self.mode_combo.setCurrentText("均衡加速")
        self.grade_combo.setCurrentText("自然增强")
        self.codec_combo.setCurrentText("H.264兼容")
        self.quality_combo.setCurrentText("均衡")
        self.container_combo.setCurrentText("mp4")
        self.audio_combo.setCurrentText("自动")
        self.progress_bar.setRange(0, 100)
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(180)
        self.render_button.setObjectName("primaryButton")
        self.stop_button.setObjectName("dangerButton")
        self.mode_note_label.setWordWrap(True)
        self.mode_note_label.setStyleSheet("color: #9fb0c4; font-weight: 650;")
        self.encoding_note_label.setWordWrap(True)
        self.encoding_note_label.setStyleSheet("color: #f2c763; font-weight: 800;")
        self.comfy_url_input.setPlaceholderText("http://127.0.0.1:8188")
        self.comfy_url_input.setStyleSheet(
            """
            QLineEdit {
                min-height: 36px;
                padding: 0 10px;
                border: 1px solid #2e3a4c;
                border-radius: 6px;
                background: #151a23;
                color: #edf3f7;
            }
            """
        )
        self.log_box.setStyleSheet(
            """
            QTextEdit {
                background: #0f141d;
                color: #d6f5df;
                border: 1px solid #263243;
                border-radius: 6px;
                font-family: Consolas, Microsoft YaHei UI;
                font-size: 13px;
            }
            """
        )

        tile_grid = QGridLayout()
        tile_grid.setHorizontalSpacing(12)
        tile_grid.setVerticalSpacing(12)
        for index, tile in enumerate([self.gpu_tile, self.vram_tile, self.encoder_tile, self.mode_tile, self.output_tile, self.comfy_tile]):
            tile_grid.addWidget(tile, index // 3, index % 3)

        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background: #121822;
                border: 1px solid #263243;
                border-radius: 8px;
            }
            """
        )
        grid = QGridLayout(card)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)

        self.source_label.setStyleSheet("color: #d9e3ef;")
        self.output_label.setStyleSheet("color: #8fa3b8;")

        grid.addWidget(QLabel("输入视频"), 0, 0)
        grid.addWidget(self.source_label, 0, 1)
        grid.addWidget(self.pick_video_button, 0, 2)
        grid.addWidget(QLabel("输出目录"), 1, 0)
        grid.addWidget(self.output_label, 1, 1)
        grid.addWidget(self.pick_output_button, 1, 2)
        grid.addWidget(QLabel("渲染档位"), 2, 0)
        grid.addWidget(self.mode_combo, 2, 1)
        grid.addWidget(self.mode_note_label, 2, 2)
        grid.addWidget(QLabel("专业模式"), 3, 0)
        grid.addWidget(self.grade_combo, 3, 1)
        grid.addWidget(self.grade_strength_slider, 3, 2)
        grid.addWidget(QLabel("帧率"), 4, 0)
        grid.addWidget(self.fps_combo, 4, 1)
        grid.addWidget(QLabel("长边分辨率"), 5, 0)
        grid.addWidget(self.edge_combo, 5, 1)
        grid.addWidget(QLabel("编码格式"), 6, 0)
        grid.addWidget(self.codec_combo, 6, 1)
        grid.addWidget(self.quality_combo, 6, 2)
        grid.addWidget(QLabel("编码器"), 7, 0)
        grid.addWidget(self.encoder_combo, 7, 1)
        grid.addWidget(self.container_combo, 7, 2)
        grid.addWidget(QLabel("音频"), 8, 0)
        grid.addWidget(self.audio_combo, 8, 1)
        grid.addWidget(self.encoding_note_label, 8, 2)
        grid.addWidget(QLabel("AI能力"), 9, 0)
        grid.addWidget(self.ai_rescue_checkbox, 9, 1)
        grid.addWidget(QLabel("失败后自动换音频/编码器/CPU兼容方案，并写入诊断日志"), 9, 2)
        grid.addWidget(QLabel("ComfyUI 地址"), 10, 0)
        grid.addWidget(self.comfy_url_input, 10, 1)
        grid.addWidget(self.start_comfy_button, 10, 2)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addWidget(self.auto_button)
        button_row.addWidget(self.check_comfy_button)
        button_row.addStretch()
        button_row.addWidget(self.render_button)
        button_row.addWidget(self.stop_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addLayout(tile_grid)
        layout.addWidget(card)
        layout.addLayout(button_row)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_box, 1)

    def _connect_signals(self):
        self.pick_video_button.clicked.connect(self.pick_video)
        self.pick_output_button.clicked.connect(self.pick_output_dir)
        self.auto_button.clicked.connect(self.refresh_auto_profile)
        self.render_button.clicked.connect(self.start_render)
        self.stop_button.clicked.connect(self.stop_render)
        self.check_comfy_button.clicked.connect(self.check_comfy_status)
        self.start_comfy_button.clicked.connect(self.start_comfyui)
        self.mode_combo.currentTextChanged.connect(self.apply_video_mode)
        self.grade_combo.currentTextChanged.connect(self.apply_video_grade)
        self.codec_combo.currentTextChanged.connect(self.update_encoding_preview)
        self.quality_combo.currentTextChanged.connect(self.update_encoding_preview)
        self.container_combo.currentTextChanged.connect(self.update_encoding_preview)
        self.audio_combo.currentTextChanged.connect(self.update_encoding_preview)
        self.encoder_combo.currentTextChanged.connect(self.update_encoding_preview)
        self.fps_combo.currentTextChanged.connect(self.update_encoding_preview)
        self.edge_combo.currentTextChanged.connect(self.update_encoding_preview)
        self.grade_strength_slider.slider.valueChanged.connect(lambda _value: self.update_encoding_preview())

    def apply_device_profile(self, profile: dict):
        margins = 14 if profile.get("mode") == "compact" else 24
        self.layout().setContentsMargins(margins, margins, margins, margins)
        self.log_box.setMinimumHeight(140 if profile.get("mode") == "compact" else 180)

    def append_log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{now}] {message}")

    def resolved_mode_options(self, mode_name: str) -> dict:
        options = dict(video_mode_options(mode_name))
        vram = self.profile.get("gpu", {}).get("vram_mb", 0)
        if mode_name == "均衡加速":
            options["edge"] = self.profile["edge"]
            options["fps"] = self.profile["fps"]
            options["sharpen"] = self.profile["sharpen"]
        elif mode_name == "高清输出":
            if vram >= 10000:
                options["edge"] = 2048
            elif vram < 6000:
                options["edge"] = 1080
        return options

    def apply_video_mode(self, mode_name: str):
        options = self.resolved_mode_options(mode_name)
        self.fps_combo.setCurrentText(str(options["fps"]))
        self.edge_combo.setCurrentText(str(options["edge"]))
        self.mode_note_label.setText(options["note"])
        self.mode_tile.set_value(mode_name)
        self.output_tile.set_value(f"{options['edge']}p / {options['fps']}FPS")
        self.update_encoding_preview()
        if mode_name == "120帧补帧":
            self.append_log("120帧补帧会明显更慢，建议先用短片段测试。")

    def apply_video_grade(self, grade_name: str):
        note = video_grade_options(grade_name).get("note", "")
        self.mode_note_label.setText(f"{video_mode_options(self.mode_combo.currentText())['note']} · {note}")
        self.update_encoding_preview()

    def resolved_encoder(self) -> str:
        encoder = self.encoder_combo.currentText()
        if encoder != "auto":
            return encoder
        return resolve_auto_encoder(self.profile.get("ffmpeg", {}), self.codec_combo.currentText())

    def update_encoding_preview(self, *_args):
        encoder = self.resolved_encoder()
        quality = self.quality_combo.currentText()
        container = self.container_combo.currentText()
        audio = self.audio_combo.currentText()
        self.encoder_tile.set_value(encoder[:18])
        self.encoding_note_label.setText(f"{encoder} · {quality} · {container.upper()} · {audio}")

    def pick_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Video (*.mp4 *.mov *.mkv *.avi *.webm)")
        if not path:
            return
        self.source_path = path
        size = Path(path).stat().st_size if Path(path).exists() else 0
        self.source_label.setText(f"{Path(path).name} · {format_bytes(size)}")
        self.append_log(f"载入视频：{path}")

    def pick_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_dir)
        if not directory:
            return
        self.output_dir = directory
        self.output_label.setText(directory)

    def apply_auto_profile(self):
        self.refresh_auto_profile()

    def refresh_auto_profile(self):
        if self.profile_worker and self.profile_worker.isRunning():
            return
        self.auto_button.setEnabled(False)
        self.encoder_tile.set_value("检测中")
        self.append_log("后台检测 GPU / FFmpeg / 硬件编码器")
        self.profile_worker = VideoProfileWorker(self)
        self.profile_worker.profile_ready.connect(self.on_video_profile_ready)
        self.profile_worker.failed.connect(self.on_video_profile_failed)
        self.profile_worker.finished.connect(self.profile_worker.deleteLater)
        self.profile_worker.finished.connect(lambda: setattr(self, "profile_worker", None))
        self.profile_worker.start()

    def on_video_profile_ready(self, profile: dict):
        self.profile = profile
        self.gpu_tile.set_value(self.profile["gpu"]["name"][:22])
        self.vram_tile.set_value(f"{self.profile['gpu']['vram_mb']} MB")
        self.encoder_tile.set_value(self.profile["encoder"])
        self.mode_combo.setCurrentText("均衡加速")
        self.apply_video_mode(self.mode_combo.currentText())
        self.encoder_combo.setCurrentText("auto")
        self.update_encoding_preview()
        ffmpeg_path = self.profile["ffmpeg"].get("ffmpeg") or "未检测到 FFmpeg"
        self.auto_button.setEnabled(True)
        self.append_log(f"自动配置：{self.profile['edge']}p / {self.profile['fps']}FPS / {self.profile['encoder']}")
        self.append_log(f"FFmpeg：{ffmpeg_path}")

    def on_video_profile_failed(self, message: str):
        self.auto_button.setEnabled(True)
        self.encoder_tile.set_value("检测失败")
        self.append_log(f"自动配置失败：{message}")

    def read_settings(self):
        profile = self.profile
        if not profile.get("ffmpeg", {}).get("ffmpeg"):
            profile = build_medium_video_profile()
        self.profile = profile
        encoder = self.resolved_encoder()
        mode_name = self.mode_combo.currentText()
        options = self.resolved_mode_options(mode_name)
        return {
            "ffmpeg": profile["ffmpeg"],
            "gpu": profile["gpu"],
            "fps": int(self.fps_combo.currentText()),
            "edge": int(self.edge_combo.currentText()),
            "encoder": encoder,
            "mode": mode_name,
            "grade": self.grade_combo.currentText(),
            "grade_strength": self.grade_strength_slider.value(),
            "codec": self.codec_combo.currentText(),
            "quality": self.quality_combo.currentText(),
            "container": self.container_combo.currentText(),
            "audio_mode": self.audio_combo.currentText(),
            "auto_rescue": self.ai_rescue_checkbox.isChecked(),
            "sharpen": options["sharpen"],
            "threads": profile["threads"],
        }

    def start_render(self):
        if not self.source_path:
            QMessageBox.warning(self, "缺少视频", "请先选择一个视频文件。")
            return
        settings = self.read_settings()
        if not settings["ffmpeg"].get("ffmpeg"):
            QMessageBox.warning(self, "缺少 FFmpeg", "未检测到 FFmpeg，无法调用系统硬件渲染。")
            return
        if self.worker and self.worker.isRunning():
            return
        self.progress_bar.setValue(0)
        self.render_button.setEnabled(False)
        self.worker = VideoRenderWorker(self.source_path, self.output_dir, settings)
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished_video.connect(self.on_video_finished)
        self.worker.failed.connect(self.on_video_failed)
        self.worker.start()

    def start_comfyui(self):
        if self.comfy_start_worker and self.comfy_start_worker.isRunning():
            return
        self.comfy_tile.set_value("启动中")
        self.append_log("正在尝试启动本机 ComfyUI")
        self.comfy_start_worker = ComfyStartWorker(8188)
        self.comfy_start_worker.log_message.connect(self.append_log)
        self.comfy_start_worker.started_process.connect(self.on_comfy_started)
        self.comfy_start_worker.failed.connect(self.on_comfy_start_failed)
        self.comfy_start_worker.start()

    def on_comfy_started(self, process):
        self.comfy_process = process
        self.comfy_url_input.setText("http://127.0.0.1:8188")
        self.append_log("ComfyUI 正在后台启动，几秒后自动重试连接")
        QTimer.singleShot(5000, self.check_comfy_status)

    def on_comfy_start_failed(self, message: str):
        self.comfy_tile.set_value("未安装")
        self.append_log(f"ComfyUI 启动失败：{message}")

    def stop_render(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.append_log("已请求停止渲染")

    def on_video_finished(self, path: str):
        self.render_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.append_log(f"视频渲染完成：{path}")
        self.source_label.setText(f"完成：{Path(path).name}")

    def on_video_failed(self, message: str):
        self.render_button.setEnabled(True)
        self.append_log(f"视频渲染失败：{message}")
        QMessageBox.warning(self, "视频渲染失败", message)

    def check_comfy_status(self):
        if self.comfy_worker and self.comfy_worker.isRunning():
            return
        self.comfy_tile.set_value("检测中")
        url = self.comfy_url_input.text().strip() or "http://127.0.0.1:8188"
        self.append_log(f"正在检测 ComfyUI + FLUX.1 Kontext Dev：{url}")
        self.comfy_worker = ComfyStatusWorker(url)
        self.comfy_worker.finished_status.connect(self.on_comfy_status)
        self.comfy_worker.start()

    def on_comfy_status(self, status: dict):
        if status.get("url"):
            self.comfy_url_input.setText(status["url"])
        self.comfy_tile.set_value("就绪" if status.get("model_ready") else "已连接" if status.get("reachable") else "未启动")
        self.append_log(status.get("detail", "ComfyUI 状态未知"))
        if not status.get("reachable"):
            install_path = status.get("install_path") or ""
            if install_path:
                self.append_log(f"已找到 ComfyUI，可点击启动：{install_path}")
            else:
                self.append_log("没有找到本机 ComfyUI。视频 FFmpeg/NVENC 仍可直接渲染，AI 视频模型接入需要先安装 ComfyUI。")


class ModelDeployPage(QWidget):
    """模型自动部署页面。"""

    def __init__(self):
        super().__init__()

        self.worker = None
        self.model_catalog = load_model_catalog()
        self.model_selector = QComboBox()
        self.deploy_button = QPushButton("一键部署")
        self.add_model_button = QPushButton("添加/更新模型")
        self.remove_model_button = QPushButton("删除自定义")
        self.pick_model_source_button = QPushButton("选择路径")
        self.open_model_dir_button = QPushButton("打开模型库")
        self.custom_model_list = QListWidget()
        self.custom_name_input = QLineEdit()
        self.custom_source_input = QLineEdit()
        self.custom_launch_input = QLineEdit()
        self.custom_kind_combo = QComboBox()
        self.custom_vram_combo = QComboBox()
        self.custom_notes_input = QTextEdit()
        self.progress_bar = QProgressBar()
        self.log_box = QTextEdit()
        self.deploy_tile = SummaryTile("DEPLOY MODE", "一键部署")
        self.runtime_tile = SummaryTile("RUNTIME", "QThread")
        self.target_tile = SummaryTile("TARGET", "模型库")

        self._build_ui()
        self.deploy_button.clicked.connect(self.start_deployment)
        self.add_model_button.clicked.connect(self.add_or_update_custom_model)
        self.remove_model_button.clicked.connect(self.remove_custom_model)
        self.pick_model_source_button.clicked.connect(self.pick_model_source)
        self.open_model_dir_button.clicked.connect(lambda: os.startfile(str(model_registry_path().parent)) if is_windows() else None)
        self.model_selector.currentTextChanged.connect(self.on_model_selected)
        self.custom_model_list.itemClicked.connect(lambda item: self.populate_custom_form(item.data(Qt.ItemDataRole.UserRole)))
        self.refresh_model_selector()

    def apply_device_profile(self, profile: dict):
        margins = 14 if profile.get("mode") == "compact" else 24
        self.layout().setContentsMargins(margins, margins, margins, margins)
        self.log_box.setMinimumHeight(210 if profile.get("mode") == "compact" else 280)

    def _build_ui(self):
        title = SectionTitle(
            "模型自动部署",
            "选择模型并执行一键部署。部署任务运行在 QThread 中，避免界面卡顿。",
        )

        self.custom_kind_combo.addItems(["图像生成", "视频生成", "语言模型", "音频识别", "多模态", "工具模型", "API服务"])
        self.custom_vram_combo.addItems(["CPU可用", "4GB", "6GB", "8GB", "12GB", "16GB+", "远程API"])
        self.custom_name_input.setPlaceholderText("例如：我的 FLUX 工作流 / DeepSeek API / 本地视频模型")
        self.custom_source_input.setPlaceholderText("模型目录、权重文件、API 地址或 ComfyUI workflow 路径")
        self.custom_launch_input.setPlaceholderText("启动命令或服务入口，例如 python main.py / http://127.0.0.1:8188")
        self.custom_notes_input.setPlaceholderText("模型用途、注意事项、推荐参数、授权来源")
        self.custom_notes_input.setMaximumHeight(72)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(280)
        self.custom_model_list.setMinimumHeight(150)
        self.custom_model_list.setStyleSheet(
            """
            QListWidget {
                background: #101418;
                color: #d9e3ef;
                border: 1px solid #283242;
                border-radius: 6px;
            }
            QListWidget::item {
                min-height: 30px;
                padding: 5px 8px;
            }
            QListWidget::item:selected {
                background: #273448;
            }
            """
        )
        line_style = """
            QLineEdit {
                min-height: 36px;
                padding: 0 10px;
                border: 1px solid #2e3a4c;
                border-radius: 6px;
                background: #151a23;
                color: #edf3f7;
            }
        """
        for line in (self.custom_name_input, self.custom_source_input, self.custom_launch_input):
            line.setStyleSheet(line_style)
        self.log_box.setStyleSheet(
            """
            QTextEdit {
                background: #101418;
                color: #d7f7df;
                border: 1px solid #283242;
                border-radius: 6px;
                font-family: Consolas, Microsoft YaHei UI;
                font-size: 13px;
            }
            """
        )
        self.custom_notes_input.setStyleSheet(self.log_box.styleSheet())

        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            """
            QFrame {
                background: #151a22;
                border: 1px solid #283242;
                border-radius: 8px;
            }
            """
        )

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        summary_grid.addWidget(self.deploy_tile, 0, 0)
        summary_grid.addWidget(self.runtime_tile, 0, 1)
        summary_grid.addWidget(self.target_tile, 0, 2)

        grid = QGridLayout(card)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(1, 1)

        model_label = QLabel("模型选择")
        model_label.setStyleSheet("color: #d9e3ef; font-weight: 700;")
        progress_label = QLabel("部署进度")
        progress_label.setStyleSheet("color: #d9e3ef; font-weight: 700;")
        log_label = QLabel("部署日志")
        log_label.setStyleSheet("color: #d9e3ef; font-weight: 700;")

        grid.addWidget(model_label, 0, 0)
        grid.addWidget(self.model_selector, 0, 1)
        grid.addWidget(self.deploy_button, 0, 2)
        grid.addWidget(progress_label, 1, 0)
        grid.addWidget(self.progress_bar, 1, 1, 1, 2)
        grid.addWidget(log_label, 2, 0, Qt.AlignTop)
        grid.addWidget(self.log_box, 2, 1, 1, 2)

        custom_card = QFrame()
        custom_card.setStyleSheet(
            """
            QFrame {
                background: #121822;
                border: 1px solid #263243;
                border-radius: 8px;
            }
            """
        )
        custom_grid = QGridLayout(custom_card)
        custom_grid.setContentsMargins(18, 18, 18, 18)
        custom_grid.setHorizontalSpacing(12)
        custom_grid.setVerticalSpacing(12)
        custom_grid.setColumnStretch(1, 1)
        custom_title = QLabel("用户模型库")
        custom_title.setStyleSheet("color: #f2c763; font-size: 13px; font-weight: 900;")
        custom_grid.addWidget(custom_title, 0, 0, 1, 3)
        custom_grid.addWidget(QLabel("自定义模型"), 1, 0)
        custom_grid.addWidget(self.custom_model_list, 1, 1, 1, 2)
        custom_grid.addWidget(QLabel("名称"), 2, 0)
        custom_grid.addWidget(self.custom_name_input, 2, 1, 1, 2)
        custom_grid.addWidget(QLabel("类型"), 3, 0)
        custom_grid.addWidget(self.custom_kind_combo, 3, 1)
        custom_grid.addWidget(self.custom_vram_combo, 3, 2)
        custom_grid.addWidget(QLabel("来源"), 4, 0)
        custom_grid.addWidget(self.custom_source_input, 4, 1)
        custom_grid.addWidget(self.pick_model_source_button, 4, 2)
        custom_grid.addWidget(QLabel("启动/API"), 5, 0)
        custom_grid.addWidget(self.custom_launch_input, 5, 1, 1, 2)
        custom_grid.addWidget(QLabel("备注"), 6, 0, Qt.AlignTop)
        custom_grid.addWidget(self.custom_notes_input, 6, 1, 1, 2)
        custom_buttons = QHBoxLayout()
        custom_buttons.addWidget(self.add_model_button)
        custom_buttons.addWidget(self.remove_model_button)
        custom_buttons.addWidget(self.open_model_dir_button)
        custom_buttons.addStretch()
        custom_grid.addLayout(custom_buttons, 7, 1, 1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addLayout(summary_grid)
        layout.addWidget(card)
        layout.addWidget(custom_card)
        layout.addStretch()

    def refresh_model_selector(self):
        self.model_catalog = load_model_catalog()
        current_id = self.model_selector.currentData()
        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        for model in self.model_catalog:
            prefix = "自定义" if model.get("custom") else "内置"
            self.model_selector.addItem(f"{model.get('name', '未命名')} · {prefix} · {model.get('kind', '通用')}", model.get("id"))
        self.model_selector.blockSignals(False)
        if current_id:
            index = self.model_selector.findData(current_id)
            if index >= 0:
                self.model_selector.setCurrentIndex(index)

        self.custom_model_list.clear()
        for model in self.model_catalog:
            if not model.get("custom"):
                continue
            item = QListWidgetItem(f"{model.get('name', '未命名')} · {model.get('kind', '通用')}")
            item.setData(Qt.ItemDataRole.UserRole, model.get("id"))
            self.custom_model_list.addItem(item)
        self.on_model_selected()

    def selected_model_config(self) -> dict:
        model_id = self.model_selector.currentData()
        for model in self.model_catalog:
            if model.get("id") == model_id:
                return dict(model)
        return dict(self.model_catalog[0]) if self.model_catalog else {}

    def on_model_selected(self):
        model = self.selected_model_config()
        if not model:
            return
        self.deploy_tile.set_value(model.get("name", "--")[:18])
        self.runtime_tile.set_value(model.get("kind", "通用")[:18])
        self.target_tile.set_value(model.get("min_vram", "模型库")[:18])

    def populate_custom_form(self, model_id: str):
        for model in self.model_catalog:
            if model.get("id") != model_id:
                continue
            self.custom_name_input.setText(model.get("name", ""))
            self.custom_kind_combo.setCurrentText(model.get("kind", "图像生成"))
            self.custom_source_input.setText(model.get("source", ""))
            self.custom_launch_input.setText(model.get("launch", ""))
            self.custom_vram_combo.setCurrentText(model.get("min_vram", "CPU可用"))
            self.custom_notes_input.setPlainText(model.get("notes", ""))
            index = self.model_selector.findData(model_id)
            if index >= 0:
                self.model_selector.setCurrentIndex(index)
            return

    def custom_model_from_form(self) -> dict:
        name = self.custom_name_input.text().strip()
        if not name:
            raise ValueError("请先填写模型名称")
        return {
            "id": f"custom_{safe_slug(name)}",
            "name": name,
            "kind": self.custom_kind_combo.currentText(),
            "source": self.custom_source_input.text().strip(),
            "launch": self.custom_launch_input.text().strip(),
            "min_vram": self.custom_vram_combo.currentText(),
            "notes": self.custom_notes_input.toPlainText().strip(),
            "custom": True,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def add_or_update_custom_model(self):
        try:
            model = self.custom_model_from_form()
        except ValueError as error:
            QMessageBox.warning(self, "缺少信息", str(error))
            return
        custom_models = load_custom_models()
        custom_models = [item for item in custom_models if item.get("id") != model["id"]]
        custom_models.append(model)
        save_custom_models(custom_models)
        self.refresh_model_selector()
        index = self.model_selector.findData(model["id"])
        if index >= 0:
            self.model_selector.setCurrentIndex(index)
        self.append_log(f"已加入模型库：{model['name']}")

    def remove_custom_model(self):
        model = self.selected_model_config()
        if not model.get("custom"):
            QMessageBox.information(self, "不能删除", "内置模型不会被删除，只能删除用户添加的模型。")
            return
        custom_models = [item for item in load_custom_models() if item.get("id") != model.get("id")]
        save_custom_models(custom_models)
        self.refresh_model_selector()
        self.append_log(f"已删除自定义模型：{model.get('name', '')}")

    def pick_model_source(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模型文件或工作流", "", "Model / Workflow (*.*)")
        if path:
            self.custom_source_input.setText(path)

    def start_deployment(self):
        if self.worker and self.worker.isRunning():
            return

        model_config = self.selected_model_config()
        model_name = model_config.get("name", self.model_selector.currentText())
        self.log_box.clear()
        self.progress_bar.setValue(0)
        self.deploy_button.setEnabled(False)
        self.model_selector.setEnabled(False)
        self.deploy_tile.set_value(model_name)
        self.target_tile.set_value("部署中")

        self.worker = DeploymentWorker(model_config)
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished_successfully.connect(self.on_deployment_finished)
        self.worker.failed.connect(self.on_deployment_failed)
        self.worker.start()

    def append_log(self, message: str):
        self.log_box.append(message)

    def on_deployment_finished(self):
        self.append_log("部署完成，可以进入下一步真实模型配置。")
        self.progress_bar.setValue(100)
        self.deploy_button.setEnabled(True)
        self.model_selector.setEnabled(True)
        self.target_tile.set_value("完成")

    def on_deployment_failed(self, message: str):
        self.append_log(f"部署失败：{message}")
        self.deploy_button.setEnabled(True)
        self.model_selector.setEnabled(True)
        self.target_tile.set_value("失败")


class MobileApiPage(QWidget):
    """手机端连接服务页面，给 Android 控制台提供局域网 API。"""

    def __init__(self):
        super().__init__()
        self.config = load_mobile_api_config()
        self.service = MobileApiService(
            host=str(self.config.get("host", "0.0.0.0")),
            port=int(self.config.get("port", 8765)),
            discovery_port=int(self.config.get("discovery_port", 8766)),
            token=str(self.config.get("token", "")),
        )
        self.keep_service_running = True
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1600)
        self.refresh_timer.timeout.connect(self.refresh_status)

        self.status_tile = SummaryTile("API", "未启动")
        self.port_tile = SummaryTile("端口", str(self.service.port))
        self.discovery_tile = SummaryTile("发现", f"UDP {self.service.discovery_port}")
        self.token_tile = SummaryTile("令牌", self.mask_token())
        self.pairing_tile = SummaryTile("配对码", self.service.current_pairing_code())
        self.task_tile = SummaryTile("任务", "0")
        self.url_box = QTextEdit()
        self.log_box = QTextEdit()
        self.start_button = QPushButton("启动手机连接服务")
        self.stop_button = QPushButton("停止服务")
        self.reset_token_button = QPushButton("重新生成令牌")
        self.refresh_pairing_button = QPushButton("刷新配对码")
        self.open_tasks_button = QPushButton("打开任务目录")

        self._build_ui()
        self.start_button.clicked.connect(self.start_service)
        self.stop_button.clicked.connect(self.stop_service)
        self.reset_token_button.clicked.connect(self.reset_token)
        self.refresh_pairing_button.clicked.connect(self.refresh_pairing_code)
        self.open_tasks_button.clicked.connect(lambda: os.startfile(str(mobile_api_root() / "tasks")) if is_windows() else None)
        self.start_service()

    def _build_ui(self):
        self.start_button.setObjectName("primaryButton")
        for box in (self.url_box, self.log_box):
            box.setReadOnly(True)
            box.setStyleSheet(
                """
                QTextEdit {
                    color: #dce6ee;
                    background: #10141a;
                    border: 1px solid #263243;
                    border-radius: 8px;
                    padding: 10px;
                }
                """
            )
        self.url_box.setMinimumHeight(120)
        self.log_box.setMinimumHeight(190)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(SectionTitle("手机连接服务", "手机端可自动发现这台电脑，输入一次配对码后会自动保存连接配置。"))

        tile_row = QGridLayout()
        tile_row.setHorizontalSpacing(12)
        tile_row.setVerticalSpacing(12)
        tiles = (self.status_tile, self.port_tile, self.discovery_tile, self.pairing_tile, self.token_tile, self.task_tile)
        for index, tile in enumerate(tiles):
            tile_row.addWidget(tile, index // 3, index % 3)
        layout.addLayout(tile_row)

        button_row = QHBoxLayout()
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.reset_token_button)
        button_row.addWidget(self.refresh_pairing_button)
        button_row.addWidget(self.open_tasks_button)
        layout.addLayout(button_row)

        warning = QLabel("安全提醒：自动发现只在局域网工作，配对码 10 分钟有效。正式公网访问请放到 HTTPS 反向代理后面。")
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #f2c763; font-weight: 800;")
        layout.addWidget(warning)

        layout.addWidget(QLabel("自动配置与高级手动参数"))
        layout.addWidget(self.url_box)
        layout.addWidget(QLabel("服务日志"))
        layout.addWidget(self.log_box, 1)

    def apply_device_profile(self, profile: dict):
        margins = 14 if profile.get("mode") == "compact" else 24
        self.layout().setContentsMargins(margins, margins, margins, margins)
        self.log_box.setMinimumHeight(160 if profile.get("mode") == "compact" else 220)

    def mask_token(self) -> str:
        token = self.service.token
        if len(token) <= 10:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    def start_service(self):
        self.keep_service_running = True
        if self.service.start():
            self.append_log("手机连接服务已启动")
            self.refresh_timer.start()
        else:
            self.append_log(f"启动失败：{self.service.last_error}")
        self.refresh_status()

    def stop_service(self):
        self.keep_service_running = False
        self.service.stop()
        self.append_log("手机连接服务已停止")
        self.refresh_status()

    def reset_token(self):
        self.config["token"] = secrets.token_urlsafe(18)
        config_path = mobile_api_config_path()
        config_path.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")
        harden_private_file(config_path)
        was_running = self.service.is_running()
        self.service.stop()
        self.service = MobileApiService(
            host=str(self.config.get("host", "0.0.0.0")),
            port=int(self.config.get("port", 8765)),
            discovery_port=int(self.config.get("discovery_port", 8766)),
            token=str(self.config.get("token", "")),
        )
        if was_running:
            self.service.start()
        self.append_log("访问令牌已重新生成，旧手机端令牌会失效")
        self.refresh_status()

    def refresh_pairing_code(self):
        code = self.service.rotate_pairing_code()
        self.append_log(f"配对码已刷新：{code}")
        self.refresh_status()

    def refresh_status(self):
        running = self.service.is_running()
        if self.keep_service_running and not running:
            if self.service.start():
                self.append_log("手机连接服务已自动恢复")
                running = True
            else:
                self.append_log(f"自动恢复失败：{self.service.last_error}")
        self.status_tile.set_value("运行中" if running else "已停止")
        self.port_tile.set_value(str(self.service.port))
        self.discovery_tile.set_value(f"UDP {self.service.discovery_port}")
        code = self.service.current_pairing_code()
        seconds = self.service.pairing_seconds_left()
        self.pairing_tile.set_value(f"{code} / {seconds // 60}:{seconds % 60:02d}")
        self.token_tile.set_value(self.mask_token())
        task_count = len(list((mobile_api_root() / "tasks").glob("*.json")))
        self.task_tile.set_value(str(task_count))
        urls = self.service.urls()
        self.url_box.setPlainText(
            "\n".join(
                [
                    "推荐方式：",
                    "1. 手机端打开 连接与安全 -> 自动发现工作站。",
                    f"2. 输入桌面端配对码：{code}（{seconds // 60}:{seconds % 60:02d} 后过期）。",
                    "3. 配对成功后，手机会自动保存地址和令牌。",
                    "",
                    "发现端口：",
                    f"UDP {self.service.discovery_port}",
                    "",
                    "手动地址任选一个：",
                    *urls,
                    "",
                    "访问令牌（高级手动模式）：",
                    self.service.token,
                    "",
                    "安卓设置：同一 Wi-Fi / 热点网络下优先使用自动发现；如手动使用 http://192.168.x.x:8765，请打开“允许局域网 HTTP 调试”。",
                    "正式公网使用请加 HTTPS，不要把 8765 端口直接暴露到公网。",
                ]
            )
        )

    def append_log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{now}] {message}")

    def shutdown(self):
        self.refresh_timer.stop()
        self.service.stop()


class MainWindow(QMainWindow):
    """主窗口。

    左侧 QListWidget 作为功能导航栏，右侧 QStackedWidget 作为页面容器。
    后续新增功能时，只需要 add_page() 添加页面即可。
    """

    def __init__(self, screen_profile=None):
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.screen_profile = screen_profile or {"width": 1280, "height": 720, "device_pixel_ratio": 1.0, "mode": "compact"}
        self.pages = []
        self._maximize_on_show = False
        self._page_animation = None
        self._bar_animation = None
        self._nav_animation = None
        self.interaction_filter = None
        self.system_profile_worker = None

        self.navigation = QListWidget()
        self.page_stack = QStackedWidget()
        self.header_bar = HeaderBar()
        self.transition_bar = QFrame()
        self.nav_indicator = None
        self.toast = None

        self._build_menu_bar()
        self._build_status_bar()
        self._build_layout()
        self._register_pages()
        self.apply_device_profile()
        self.install_motion_interactions()

    def _build_menu_bar(self):
        file_menu = self.menuBar().addMenu("文件")
        data_action = QAction("打开用户数据目录", self)
        data_action.triggered.connect(lambda: self.open_system_path(runtime_root()))
        logs_action = QAction("打开日志目录", self)
        logs_action.triggered.connect(lambda: self.open_system_path(cache_root() / "logs"))
        video_logs_action = QAction("打开视频诊断目录", self)
        video_logs_action.triggered.connect(lambda: self.open_system_path(video_diagnostics_dir()))
        program_action = QAction("打开程序目录", self)
        program_action.triggered.connect(lambda: self.open_system_path(program_root()))
        shortcut_action = QAction("生成桌面快捷方式", self)
        shortcut_action.triggered.connect(self.make_desktop_shortcut)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(data_action)
        file_menu.addAction(logs_action)
        file_menu.addAction(video_logs_action)
        file_menu.addAction(program_action)
        file_menu.addAction(shortcut_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("视图")
        image_action = QAction("映效图像工作站", self)
        hardware_action = QAction("硬件监控面板", self)
        video_action = QAction("视频工作站", self)
        deploy_action = QAction("模型自动部署", self)
        mobile_action = QAction("手机连接服务", self)
        image_action.triggered.connect(lambda: self.switch_page(0))
        hardware_action.triggered.connect(lambda: self.switch_page(1))
        video_action.triggered.connect(lambda: self.switch_page(2))
        deploy_action.triggered.connect(lambda: self.switch_page(3))
        mobile_action.triggered.connect(lambda: self.switch_page(4))
        view_menu.addAction(image_action)
        view_menu.addAction(hardware_action)
        view_menu.addAction(video_action)
        view_menu.addAction(deploy_action)
        view_menu.addAction(mobile_action)

        help_menu = self.menuBar().addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def open_system_path(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        if is_windows():
            os.startfile(str(path))
        else:
            subprocess.run(["open", str(path)], check=False)

    def make_desktop_shortcut(self):
        shortcut = create_desktop_shortcut()
        self.statusBar().showMessage(f"已生成桌面快捷方式：{shortcut}")
        self.show_motion_toast("桌面入口已更新")

    def refresh_system_profile_async(self):
        if self.system_profile_worker and self.system_profile_worker.isRunning():
            return
        self.system_profile_worker = SystemProfileWorker(self.screen_profile)
        self.system_profile_worker.finished_profile.connect(
            lambda path: self.statusBar().showMessage(f"系统档案已后台刷新：{path}", 5000)
        )
        self.system_profile_worker.finished_profile.connect(lambda _path: self.show_motion_toast("系统档案已刷新"))
        self.system_profile_worker.failed.connect(
            lambda message: logging.warning("System profile refresh failed: %s", message)
        )
        self.system_profile_worker.finished.connect(self.system_profile_worker.deleteLater)
        self.system_profile_worker.finished.connect(lambda: setattr(self, "system_profile_worker", None))
        self.system_profile_worker.start()

    def install_motion_interactions(self):
        self.interaction_filter = MotionInteractionFilter(self.screen_profile.get("performance", {}), self)
        for button in self.findChildren(QPushButton):
            button.installEventFilter(self.interaction_filter)

    def show_motion_toast(self, text: str):
        if self.toast:
            self.toast.show_message(text, self.screen_profile.get("performance", {}))

    def _build_status_bar(self):
        status_bar = QStatusBar(self)
        status_bar.showMessage("软件已启动")
        self.setStatusBar(status_bar)

    def _build_layout(self):
        self.navigation.setFixedWidth(220)
        self.navigation.currentRowChanged.connect(self.switch_page)
        self.navigation.setStyleSheet(
            """
            QListWidget {
                background: transparent;
                color: #dce6ee;
                border: none;
                font-size: 15px;
                padding: 8px;
            }
            QListWidget::item {
                height: 44px;
                padding-left: 14px;
                border-radius: 6px;
                margin: 3px 0;
            }
            QListWidget::item:selected {
                background: #58dcc7;
                color: #07100f;
                font-weight: 900;
            }
            QListWidget::item:hover {
                background: #1b2531;
            }
            """
        )

        brand = QLabel("AI WORKSTATION")
        brand.setStyleSheet("color: #f7f9fb; font-size: 18px; font-weight: 900;")
        subtitle = QLabel("Native Studio")
        subtitle.setStyleSheet("color: #58dcc7; font-size: 12px; font-weight: 900;")
        status = QLabel("● 本机控制台在线")
        status.setStyleSheet(
            """
            QLabel {
                color: #f2c763;
                background: #121822;
                border: 1px solid #263243;
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: 700;
            }
            """
        )

        self.screen_status_label = status
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet(
            """
            QWidget {
                background: #0e131b;
                border-right: 1px solid #202735;
            }
            """
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(18, 20, 18, 18)
        sidebar_layout.setSpacing(12)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(10)
        sidebar_layout.addWidget(status)
        sidebar_layout.addSpacing(8)
        sidebar_layout.addWidget(self.navigation, 1)
        self.nav_indicator = QFrame(self.sidebar)
        self.nav_indicator.setFixedWidth(4)
        self.nav_indicator.setStyleSheet(
            """
            QFrame {
                background: #58dcc7;
                border: none;
                border-radius: 2px;
            }
            """
        )
        self.nav_indicator.hide()

        self.content = QWidget()
        self.content.setStyleSheet("background: #0b0d12;")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.transition_bar.setFixedHeight(2)
        self.transition_bar.setMaximumWidth(0)
        self.transition_bar.setStyleSheet(
            """
            QFrame {
                background: #58dcc7;
                border: none;
            }
            """
        )
        content_layout.addWidget(self.header_bar)
        content_layout.addWidget(self.transition_bar)
        content_layout.addWidget(self.page_stack, 1)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.content, 1)
        self.setCentralWidget(root)
        self.toast = MotionToast(self.content)

    def _register_pages(self):
        self.add_page("01 / 映效图像", ImageEffectPage())
        self.add_page("02 / 硬件监控", HardwareMonitorPage())
        self.add_page("03 / 视频工作站", VideoWorkstationPage())
        self.add_page("04 / 模型部署", ModelDeployPage())
        self.add_page("05 / 手机连接", MobileApiPage())
        self.navigation.setCurrentRow(0)

    def add_page(self, title: str, page: QWidget):
        self.navigation.addItem(QListWidgetItem(title))
        self.pages.append(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: #0b0d12; border: none; }")
        scroll.setWidget(page)
        self.page_stack.addWidget(scroll)

    def switch_page(self, index: int):
        if index < 0:
            return
        self.page_stack.setCurrentIndex(index)
        self.animate_current_page()
        if self.navigation.currentRow() != index:
            self.navigation.setCurrentRow(index)

        item = self.navigation.item(index)
        if item:
            self.statusBar().showMessage(f"当前页面：{item.text()}")
            self.show_motion_toast(item.text().split(" / ", 1)[-1])
        self.animate_navigation_indicator(index)

    def animate_navigation_indicator(self, index: int):
        if not self.nav_indicator or index < 0:
            return
        item = self.navigation.item(index)
        if item is None:
            return
        rect = self.navigation.visualItemRect(item)
        if rect.isNull():
            QTimer.singleShot(30, lambda: self.animate_navigation_indicator(index))
            return
        top_left = self.navigation.viewport().mapTo(self.sidebar, rect.topLeft())
        target = QRect(7, top_left.y() + 5, 4, max(28, rect.height() - 10))
        self.nav_indicator.show()
        self.nav_indicator.raise_()

        performance = self.screen_profile.get("performance", {})
        if not performance.get("nav_motion", True) or performance.get("reduce_motion", False):
            self.nav_indicator.setGeometry(target)
            return
        if self._nav_animation:
            self._nav_animation.stop()
        if self.nav_indicator.geometry().isNull() or self.nav_indicator.width() <= 0:
            self.nav_indicator.setGeometry(target)
            return
        animation = QPropertyAnimation(self.nav_indicator, b"geometry", self)
        animation.setDuration(int(performance.get("animation_ms", 180)))
        animation.setStartValue(self.nav_indicator.geometry())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._nav_animation = animation
        animation.start()

    def animate_current_page(self):
        widget = self.page_stack.currentWidget()
        if widget is None:
            return
        if self._page_animation:
            self._page_animation.stop()
        if self._bar_animation:
            self._bar_animation.stop()

        performance = self.screen_profile.get("performance", {})
        duration = int(performance.get("animation_ms", 180))
        self.transition_bar.setMaximumWidth(0)
        bar = QPropertyAnimation(self.transition_bar, b"maximumWidth", self)
        bar.setDuration(duration)
        bar.setStartValue(0)
        bar.setEndValue(max(260, self.content.width()))
        bar.setEasingCurve(QEasingCurve.Type.OutCubic)

        if not performance.get("page_fade", False):
            if performance.get("page_slide", True) and not performance.get("reduce_motion", False):
                base_pos = widget.pos()
                slide = QPropertyAnimation(widget, b"pos", self)
                slide.setDuration(duration)
                slide.setStartValue(base_pos + QPoint(18, 0))
                slide.setEndValue(base_pos)
                slide.setEasingCurve(QEasingCurve.Type.OutCubic)
                group = QParallelAnimationGroup(self)
                group.addAnimation(bar)
                group.addAnimation(slide)
                group.finished.connect(lambda: (widget.move(base_pos), self.transition_bar.setMaximumWidth(0)))
                self._page_animation = group
                self._bar_animation = bar
                group.start()
            else:
                bar.finished.connect(lambda: self.transition_bar.setMaximumWidth(0))
                self._bar_animation = bar
                self._page_animation = None
                bar.start()
            return

        base_pos = widget.pos()
        widget.move(base_pos + QPoint(16, 0))
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity", self)
        fade.setDuration(duration)
        fade.setStartValue(0.62)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide = QPropertyAnimation(widget, b"pos", self)
        slide.setDuration(duration)
        slide.setStartValue(widget.pos())
        slide.setEndValue(base_pos)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.addAnimation(bar)
        group.finished.connect(lambda: (widget.move(base_pos), widget.setGraphicsEffect(None), self.transition_bar.setMaximumWidth(0)))
        self._page_animation = group
        self._bar_animation = bar
        group.start()

    def show_about(self):
        QMessageBox.information(
            self,
            "关于",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "Python + PySide6 原生桌面软件。\n"
            "图像质感迁移、达芬奇式局部调整、硬件监控、NVENC 视频管线和 ComfyUI / FLUX 接入。\n\n"
            f"程序目录：{program_root()}\n"
            f"用户数据：{runtime_root()}\n"
            f"系统缓存：{cache_root()}",
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.toast and self.toast.isVisible():
            self.toast.reposition()
        if self.nav_indicator and self.navigation.currentRow() >= 0:
            QTimer.singleShot(0, lambda: self.animate_navigation_indicator(self.navigation.currentRow()))

    def closeEvent(self, event):
        for page in self.pages:
            if isinstance(page, ModelDeployPage) and page.worker and page.worker.isRunning():
                page.worker.stop()
                page.worker.wait(1200)
            if isinstance(page, ImageEffectPage) and page.worker and page.worker.isRunning():
                page.worker.wait(1200)
            if isinstance(page, ImageEffectPage) and page.batch_worker and page.batch_worker.isRunning():
                page.batch_worker.wait(1200)
            if isinstance(page, HardwareMonitorPage):
                page.shutdown()
            if isinstance(page, VideoWorkstationPage):
                if page.profile_worker and page.profile_worker.isRunning():
                    page.profile_worker.wait(1200)
                if page.worker and page.worker.isRunning():
                    page.worker.stop()
                    page.worker.wait(1200)
                if page.comfy_worker and page.comfy_worker.isRunning():
                    page.comfy_worker.wait(1200)
            if isinstance(page, MobileApiPage):
                page.shutdown()
        if self.system_profile_worker and self.system_profile_worker.isRunning():
            self.system_profile_worker.wait(1200)
        event.accept()

    def apply_device_profile(self):
        profile = self.screen_profile
        width = profile.get("width", 1280)
        height = profile.get("height", 720)
        mode = profile.get("mode", "regular")
        ratio = profile.get("device_pixel_ratio", 1.0)
        screen_count = profile.get("screen_count", 1)
        performance = profile.get("performance", {})
        performance_level = performance.get("level", "balanced")

        if mode == "compact":
            sidebar_width = 214
            target_width = min(width, max(980, int(width * 0.96)))
            target_height = min(height, max(620, int(height * 0.92)))
            nav_font = 14
            self._maximize_on_show = height <= 760 or width <= 1366
            self.header_bar.setMaximumHeight(96)
        elif mode == "spacious":
            sidebar_width = 292
            target_width = min(width, 1560)
            target_height = min(height, 980)
            nav_font = 16
            self.header_bar.setMaximumHeight(124)
        else:
            sidebar_width = 250
            target_width = min(width, max(1180, int(width * 0.88)))
            target_height = min(height, max(720, int(height * 0.86)))
            nav_font = 15
            self.header_bar.setMaximumHeight(112)

        self.sidebar.setFixedWidth(sidebar_width)
        self.navigation.setStyleSheet(
            f"""
            QListWidget {{
                background: transparent;
                color: #dce6ee;
                border: none;
                font-size: {nav_font}px;
                padding: 8px;
            }}
            QListWidget::item {{
                height: {40 if mode == "compact" else 44}px;
                padding-left: 12px;
                border-radius: 6px;
                margin: 3px 0;
            }}
            QListWidget::item:selected {{
                background: #58dcc7;
                color: #07100f;
                font-weight: 900;
            }}
            QListWidget::item:hover {{
                background: #1b2531;
            }}
            """
        )
        for page in self.pages:
            if hasattr(page, "apply_device_profile"):
                page.apply_device_profile(profile)

        self.setMinimumSize(900 if mode == "compact" else 1040, 600 if mode == "compact" else 660)
        self.resize(target_width, target_height)
        self.screen_status_label.setText(f"● {width}x{height} · {ratio:.1f}x · {mode} · {performance_level} · {screen_count}屏")
        self.statusBar().showMessage(
            f"系统级优化：{width} x {height}，缩放 {ratio:.1f}x，布局 {mode}，性能 {performance_level}，DPI {SYSTEM_DPI_MODE}"
        )


def main():
    log_path = setup_logging()
    install_exception_hook()
    enable_qt_application_attributes()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Kaet")
    app.setOrganizationDomain("kaet.local")
    icon_path = resource_root() / "assets" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(APP_STYLE)

    profile = detect_screen_profile(app)
    performance = build_performance_profile(profile)
    profile["performance"] = performance
    configure_qt_runtime_cache(performance)
    system_profile_path = write_system_profile(profile, defer_hardware=True)
    logging.info("System profile written to %s", system_profile_path)
    window = MainWindow(profile)
    window.setProperty("systemLogPath", str(log_path))
    window.setProperty("systemProfilePath", str(system_profile_path))
    window.show()
    if window._maximize_on_show:
        window.showMaximized()
    QTimer.singleShot(900, window.refresh_system_profile_async)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
