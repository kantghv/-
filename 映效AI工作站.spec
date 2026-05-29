# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_dir = Path(SPECPATH)
ffmpeg_bin = project_dir / "tools" / "ffmpeg" / "ffmpeg-8.1.1-full_build" / "bin"

datas = [
    (str(project_dir / "assets" / "app_icon.ico"), "assets"),
]

if ffmpeg_bin.exists():
    datas.append((str(ffmpeg_bin), "tools/ffmpeg/ffmpeg-8.1.1-full_build/bin"))


a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="映效AI工作站",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_dir / "assets" / "app_icon.ico"),
    manifest=str(project_dir / "windows" / "app.manifest"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="映效AI工作站",
)
