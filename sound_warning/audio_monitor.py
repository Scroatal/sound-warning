from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable

import numpy as np

from .detector import DetectionEvent, LoudnessDetector, calculate_rms
from .settings import Settings


class AudioMonitor:
    def __init__(
        self,
        settings: Settings,
        on_event: Callable[[DetectionEvent], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        self.settings = settings
        self.on_event = on_event
        self.on_error = on_error
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.latest_level: tuple[float, float] = (0.0, 0.0)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SoundWarningAudio", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self.latest_level = (0.0, 0.0)

    def _run(self) -> None:
        try:
            import sounddevice as sd

            chunk_frames = int(self.settings.sample_rate * self.settings.chunk_milliseconds / 1000)
            chunk_seconds = chunk_frames / self.settings.sample_rate
            detector = LoudnessDetector(
                threshold=self.settings.loudness_threshold,
                yell_duration_seconds=self.settings.yell_duration_seconds,
                smoothing_factor=self.settings.smoothing_factor,
            )
            level_queue: queue.Queue[tuple[float, float, float, bool]] = queue.Queue(maxsize=8)
            dropped = False

            def callback(indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
                nonlocal dropped
                del time_info
                if self._stop.is_set():
                    return
                try:
                    # Only a scalar level leaves the callback; no audio buffers are retained.
                    level_queue.put_nowait((calculate_rms(indata), frames / self.settings.sample_rate,
                                            time.monotonic(), dropped or bool(status)))
                    dropped = False
                except queue.Full:
                    dropped = True

            with sd.InputStream(
                channels=1,
                samplerate=self.settings.sample_rate,
                blocksize=chunk_frames,
                dtype="float32",
                callback=callback,
            ):
                while not self._stop.is_set():
                    try:
                        rms, duration, captured_at, gap = level_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if time.monotonic() - captured_at > 1:
                        detector.reset_run()
                        continue
                    if gap:
                        detector.reset_run()
                    event = detector.process_level(rms, duration)
                    self.latest_level = (detector.smoothed_loudness, captured_at)
                    if event:
                        self.on_event(event)
                        detector.reset_run()
        except Exception as exc:
            self.latest_level = (0.0, 0.0)
            self.on_error(exc)
