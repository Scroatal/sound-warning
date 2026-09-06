from __future__ import annotations

import os
import sys
from pathlib import Path


STARTUP_FILE_NAME = "Sound Warning.cmd"


def main() -> int:
    app_dir = get_app_dir()
    exe_path = find_app_exe(app_dir)
    if not exe_path:
        print(f"Could not find SoundWarning.exe or SoundWarningPortable.exe beside this installer: {app_dir}")
        print("Put this installer in the same folder as the Sound Warning app and run it again.")
        return 1

    startup_dir = get_startup_dir()
    startup_dir.mkdir(parents=True, exist_ok=True)
    startup_file = startup_dir / STARTUP_FILE_NAME
    startup_file.write_text(
        "@echo off\n"
        f'start "" "{exe_path}" --background\n',
        encoding="ascii",
    )

    print("Sound Warning startup has been installed for this Windows user.")
    print(f"Startup file: {startup_file}")
    print("It will start automatically the next time this user signs in.")
    return 0


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1] / "dist" / "SoundWarning"


def find_app_exe(app_dir: Path) -> Path | None:
    for name in ("SoundWarningPortable.exe", "SoundWarning.exe"):
        path = app_dir / name
        if path.exists():
            return path
    return None


def get_startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable is not set")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


if __name__ == "__main__":
    raise SystemExit(main())
