# -*- mode: python ; coding: utf-8 -*-
import json
import os
from pathlib import Path

config = Path(SPECPATH) / "build" / "build_config.json"
config.parent.mkdir(parents=True, exist_ok=True)
config_text = json.dumps({"update_repository": os.environ.get("SOUND_WARNING_REPOSITORY", "")})
if not config.exists() or config.read_text(encoding="utf-8") != config_text:
    config.write_text(config_text, encoding="utf-8")


a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[(str(config), ".")],
    hiddenimports=["sounddevice", "numpy", "pystray", "PIL"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SoundWarningPortable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
