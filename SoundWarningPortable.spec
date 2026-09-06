# -*- mode: python ; coding: utf-8 -*-
import json
import os
from pathlib import Path
import tkinter

config = Path(SPECPATH) / "build" / "build_config.json"
config.parent.mkdir(parents=True, exist_ok=True)
config_text = json.dumps({"update_repository": os.environ.get("SOUND_WARNING_REPOSITORY", "")})
if not config.exists() or config.read_text(encoding="utf-8") != config_text:
    config.write_text(config_text, encoding="utf-8")

# Hosted Python installations are not always discovered by PyInstaller's Tk hook.
# Ask the interpreter for the directories that its working Tk instance actually uses.
tk_root = tkinter.Tk()
tk_root.withdraw()
try:
    tcl_library = Path(tk_root.tk.eval("info library"))
    tk_library = Path(tk_root.tk.eval("set tk_library"))
finally:
    tk_root.destroy()
if not (tcl_library / "init.tcl").is_file() or not (tk_library / "tk.tcl").is_file():
    raise RuntimeError("Cannot locate Tcl/Tk runtime data for the Windows package")


a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[(str(config), "."), (str(tcl_library), "_tcl_data"), (str(tk_library), "_tk_data")],
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
    name="SoundWarningDiagnostic" if os.environ.get("SOUND_WARNING_DIAGNOSTIC") == "1" else "SoundWarningPortable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=os.environ.get("SOUND_WARNING_DIAGNOSTIC") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
