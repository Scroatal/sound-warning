from __future__ import annotations

import os
from pathlib import Path


STARTUP_FILE_NAMES = ("Sound Warning.cmd", "Sound Warning.lnk")


def main() -> int:
    startup_dir = get_startup_dir()
    removed = []

    for name in STARTUP_FILE_NAMES:
        path = startup_dir / name
        if path.exists():
            path.unlink()
            removed.append(path)

    if removed:
        print("Removed Sound Warning startup entry:")
        for path in removed:
            print(path)
    else:
        print("No Sound Warning startup entry was found for this Windows user.")

    return 0


def get_startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable is not set")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


if __name__ == "__main__":
    raise SystemExit(main())
