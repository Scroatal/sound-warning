from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import math
import sys

from .updates import DEFAULT_REPOSITORY, repository_name


APP_NAME = "SoundWarning"


def bundled_repository() -> str:
    path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "build_config.json"
    if not path.is_file():
        return DEFAULT_REPOSITORY
    raw = json.loads(path.read_text(encoding="utf-8"))
    value = raw.get("update_repository", "")
    return repository_name(value) if value else DEFAULT_REPOSITORY


@dataclass(slots=True)
class Settings:
    yell_duration_seconds: float = 1.0
    loudness_threshold: float = 0.08
    smoothing_factor: float = 0.4
    warning_limit: int = 3
    lock_seconds: int = 15
    sample_rate: int = 16000
    chunk_milliseconds: int = 100
    show_meter: bool = True
    auto_update: bool = True
    update_repository: str = ""


def default_settings_path() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / APP_NAME / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    settings_path = path or default_settings_path()
    if not settings_path.exists():
        settings = Settings(update_repository=bundled_repository())
        save_settings(settings, settings_path)
        return settings

    with settings_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    defaults = asdict(Settings(update_repository=bundled_repository()))
    merged: dict[str, Any] = {**defaults, **raw}
    settings = Settings(**{key: merged[key] for key in defaults})
    if not settings.update_repository:
        settings.update_repository = bundled_repository()
    return validate_settings(settings)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    settings_path = path or default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with settings_path.open("w", encoding="utf-8") as file:
        json.dump(asdict(settings), file, indent=2)
        file.write("\n")


def validate_settings(settings: Settings) -> Settings:
    for name in ("yell_duration_seconds", "loudness_threshold", "smoothing_factor"):
        value = getattr(settings, name)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    for name in ("warning_limit", "lock_seconds", "sample_rate", "chunk_milliseconds"):
        if type(getattr(settings, name)) is not int:
            raise ValueError(f"{name} must be a whole number")
    for name in ("show_meter", "auto_update"):
        if type(getattr(settings, name)) is not bool:
            raise ValueError(f"{name} must be true or false")
    if not isinstance(settings.update_repository, str):
        raise ValueError("update_repository must be a GitHub repository name")
    if settings.update_repository:
        settings.update_repository = repository_name(settings.update_repository)
    if settings.yell_duration_seconds <= 0:
        raise ValueError("yell_duration_seconds must be greater than 0")
    if not 0 < settings.loudness_threshold <= 1:
        raise ValueError("loudness_threshold must be between 0 and 1")
    if not 0 <= settings.smoothing_factor <= 1:
        raise ValueError("smoothing_factor must be between 0 and 1")
    if settings.warning_limit < 1:
        raise ValueError("warning_limit must be at least 1")
    if settings.lock_seconds < 1:
        raise ValueError("lock_seconds must be at least 1")
    if settings.sample_rate < 8000:
        raise ValueError("sample_rate must be at least 8000")
    if settings.chunk_milliseconds < 20:
        raise ValueError("chunk_milliseconds must be at least 20")
    return settings
