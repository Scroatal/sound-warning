from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlparse

from . import __version__


ASSET_NAME = "SoundWarningPortable.exe"
DEFAULT_REPOSITORY = "Scroatal/sound-warning"
MAX_BYTES = 150 * 1024 * 1024


def repository_name(value: str) -> str:
    value = value.strip().removesuffix("/").removesuffix(".git")
    if value.startswith("https://github.com/"):
        value = value[len("https://github.com/"):]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", value):
        raise ValueError("Enter a GitHub repository as owner/repository or its HTTPS URL")
    if value.split("/")[1] in (".", ".."):
        raise ValueError("Invalid repository name")
    return value


def version_tuple(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"v?\d+\.\d+\.\d+", value):
        raise ValueError("Release version must be vMAJOR.MINOR.PATCH")
    return tuple(int(part) for part in value.removeprefix("v").split("."))


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    digest: str
    size: int


@dataclass(frozen=True)
class PendingUpdate:
    release: Release
    staged: Path


@dataclass(frozen=True)
class UpdateResult:
    message: str
    pending: PendingUpdate | None = None
    exit_for_update: bool = False
    repository: str = ""


def select_release(data: dict, repository: str, current: str = __version__) -> Release | None:
    if data.get("draft") or data.get("prerelease"):
        return None
    tag = data["tag_name"]
    if version_tuple(tag) <= version_tuple(current):
        return None
    asset = next((asset for asset in data.get("assets", []) if asset.get("name") == ASSET_NAME), None)
    if asset is None:
        raise ValueError(f"Release {tag} has no {ASSET_NAME}")
    url = asset["browser_download_url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith(
        f"/{repository}/releases/download/{tag}/"
    ):
        raise ValueError("Update download must belong to the configured GitHub release")
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError("Release is missing its GitHub SHA-256 checksum")
    size = asset.get("size")
    if type(size) is not int or not 0 < size <= MAX_BYTES:
        raise ValueError("Invalid update size")
    return Release(tag.removeprefix("v"), url, digest[7:].lower(), size)


def open_url(url: str):
    request = urllib.request.Request(url, headers={
        "User-Agent": f"SoundWarning/{__version__}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    response = urllib.request.urlopen(request, timeout=20)
    if urlparse(response.url).scheme != "https":
        response.close()
        raise ValueError("Update connection must remain HTTPS")
    return response


def check_release(repository: str) -> Release | None:
    repository = repository_name(repository)
    with open_url(f"https://api.github.com/repos/{repository}/releases/latest") as response:
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError("Release response too large")
    return select_release(json.loads(body), repository)


def file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download_release(release: Release, target: Path) -> PendingUpdate:
    # Staging beside the EXE proves this installation is writable and keeps rename atomic.
    directory = Path(tempfile.mkdtemp(prefix=".sound-warning-update-", dir=target.parent))
    staged = directory / "download.exe"
    try:
        total = 0
        with open_url(release.url) as response, staged.open("wb") as stream:
            while block := response.read(256 * 1024):
                total += len(block)
                if total > release.size or total > MAX_BYTES:
                    raise ValueError("Update exceeded its declared size")
                stream.write(block)
        if total != release.size or file_digest(staged) != release.digest:
            raise ValueError("Update checksum/size mismatch; current app was not changed")
        with staged.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise ValueError("Update is not a Windows executable")
        return PendingUpdate(release, staged)
    except Exception:
        staged.unlink(missing_ok=True)
        directory.rmdir()
        raise


def portable_target() -> Path:
    if not getattr(sys, "frozen", False) or not hasattr(sys, "_MEIPASS"):
        raise ValueError("Use the portable Windows EXE to install updates")
    target = Path(sys.executable).resolve()
    if Path(sys._MEIPASS).resolve() == target.parent / "_internal":
        raise ValueError("Switch to SoundWarningPortable.exe for automatic updates")
    return target


def launch_installer(pending: PendingUpdate) -> None:
    target = portable_target()
    directory = pending.staged.parent
    helper = directory / "updater.exe"
    shutil.copy2(target, helper)
    manifest = directory / "update.json"
    manifest.write_text(json.dumps({
        "target": str(target), "staged": str(pending.staged), "digest": pending.release.digest,
        "pids": [os.getpid(), os.getppid()], "version": pending.release.version,
    }), encoding="utf-8")
    env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")
    process = subprocess.Popen([str(helper), "--apply-update", str(manifest)], env=env)
    deadline = time.monotonic() + 20
    while not (directory / "ready").exists():
        if process.poll() is not None or time.monotonic() >= deadline:
            process.terminate()
            raise RuntimeError("Update helper did not start; app will keep running")
        time.sleep(0.1)


def replace_with_rollback(target: Path, staged: Path, digest: str, check) -> None:
    if file_digest(staged) != digest:
        raise ValueError("Staged update checksum changed")
    backup = target.with_suffix(target.suffix + ".previous")
    os.replace(target, backup)
    try:
        os.replace(staged, target)
        check(target)
    except Exception:
        os.replace(backup, target)
        raise


def executable_self_test(target: Path) -> None:
    result = subprocess.run([str(target), "--self-test"], timeout=30,
                            env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"))
    if result.returncode != 0:
        raise RuntimeError("New app failed its self-test; previous app restored")


def apply_update(manifest: Path) -> int:
    from .windows import wait_for_process

    directory = manifest.resolve().parent
    target = None
    stopped = False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        target = Path(data["target"]).resolve()
        staged = Path(data["staged"]).resolve()
        if target.suffix.lower() != ".exe" or staged.parent != directory or directory.parent != target.parent:
            raise ValueError("Invalid update paths")
        if file_digest(staged) != data["digest"]:
            raise ValueError("Invalid staged update checksum")
        (directory / "ready").touch()
        for pid in data["pids"]:
            wait_for_process(int(pid))
        stopped = True
        replace_with_rollback(target, staged, data["digest"], executable_self_test)
        (directory / "result.txt").write_text("Updated to " + data["version"], encoding="utf-8")
    except Exception as exc:
        (directory / "result.txt").write_text(str(exc), encoding="utf-8")
        return_code = 1
    else:
        return_code = 0
    finally:
        if stopped and target is not None and target.is_file():
            subprocess.Popen([str(target), "--background"], cwd=target.parent,
                             env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"))
    return return_code
