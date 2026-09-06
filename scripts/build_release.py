"""Build and verify the portable app and startup helpers, then create the copyable ZIP."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sound_warning import __version__
from sound_warning.updates import repository_name, version_tuple


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default="")
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    if args.tag and version_tuple(args.tag) != version_tuple(__version__):
        raise ValueError("Release tag must match sound_warning.__version__")
    env = dict(os.environ)
    env["SOUND_WARNING_REPOSITORY"] = repository_name(args.repository) if args.repository else ""
    # Keep PyInstaller's writable caches in the project too.
    env["PYINSTALLER_CONFIG_DIR"] = str(ROOT / "build" / "pyinstaller-cache")

    def run(*arguments):
        subprocess.run(arguments, cwd=ROOT, env=env, check=True)

    run(sys.executable, "-m", "unittest", "discover", "-s", "tests")
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "SoundWarningPortable.spec")
    for name, source in (("InstallSoundWarningStartup", "startup_installer.py"),
                         ("RemoveSoundWarningStartup", "startup_uninstaller.py")):
        run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--noupx",
            "--name", name, "--distpath", "dist", "--workpath", f"build/{name}",
            "--specpath", f"build/{name}", f"scripts/{source}")
    app = ROOT / "dist" / "SoundWarningPortable.exe"
    try:
        subprocess.run([str(app), "--self-test"], cwd=ROOT, check=True, timeout=30)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # A windowless Python error can otherwise leave an invisible dialog in CI.
        # Rebuild the same payload with a console to capture the actual startup error.
        env["SOUND_WARNING_DIAGNOSTIC"] = "1"
        run(sys.executable, "-m", "PyInstaller", "--noconfirm", "SoundWarningPortable.spec")
        diagnostic = subprocess.run([str(ROOT / "dist" / "SoundWarningDiagnostic.exe"), "--self-test"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        print(diagnostic.stdout, flush=True)
        print(diagnostic.stderr, flush=True)
        raise
    with app.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (ROOT / "dist" / "SoundWarningPortable.exe.sha256").write_text(
        f"{digest}  SoundWarningPortable.exe\n", encoding="ascii")
    with zipfile.ZipFile(ROOT / "dist" / "SoundWarning-Windows.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in ("SoundWarningPortable.exe", "InstallSoundWarningStartup.exe", "RemoveSoundWarningStartup.exe"):
            bundle.write(ROOT / "dist" / name, name)
        bundle.write(ROOT / "QUICK_START.txt", "QUICK_START.txt")
    print(f"Sound Warning {__version__}: build and packaged self-test passed")


if __name__ == "__main__":
    main()
