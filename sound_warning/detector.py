from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class DetectionEvent:
    kind: str
    smoothed_loudness: float


class LoudnessDetector:
    """Turns short microphone chunks into warning events using RMS only."""

    def __init__(
        self,
        threshold: float,
        yell_duration_seconds: float,
        smoothing_factor: float,
    ) -> None:
        self.threshold = threshold
        self.yell_duration_seconds = yell_duration_seconds
        self.smoothing_factor = smoothing_factor
        self.smoothed_loudness = 0.0
        self._loud_seconds = 0.0
        self._in_loud_run = False

    def process_chunk(self, samples: np.ndarray, chunk_seconds: float) -> DetectionEvent | None:
        return self.process_level(calculate_rms(samples), chunk_seconds)

    def process_level(self, rms: float, chunk_seconds: float) -> DetectionEvent | None:
        alpha = self.smoothing_factor
        self.smoothed_loudness = (alpha * rms) + ((1.0 - alpha) * self.smoothed_loudness)

        if self.smoothed_loudness >= self.threshold:
            self._loud_seconds += chunk_seconds
        else:
            self._loud_seconds = 0.0
            self._in_loud_run = False
            return None

        if not self._in_loud_run and self._loud_seconds + 1e-9 >= self.yell_duration_seconds:
            self._in_loud_run = True
            return DetectionEvent("yell", self.smoothed_loudness)

        return None

    def reset_run(self) -> None:
        self._loud_seconds = 0.0
        self._in_loud_run = False


def calculate_rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    audio = samples.astype(np.float32, copy=False)
    return float(np.sqrt(np.mean(np.square(audio))))
