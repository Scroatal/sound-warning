from __future__ import annotations

import numpy as np

from .detector import LoudnessDetector
from .settings import Settings, validate_settings


def run_self_test() -> int:
    import tkinter as tk
    import sounddevice
    import pystray
    from PIL import Image

    # Exercise bundled Tcl/Tk and native audio dependencies without opening a microphone.
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    root.destroy()
    Image.new("RGB", (1, 1))
    sounddevice.get_portaudio_version()
    validate_settings(Settings())
    detector = LoudnessDetector(
        threshold=0.08,
        yell_duration_seconds=1.0,
        smoothing_factor=1.0,
    )
    loud = np.full((1600, 1), 0.2, dtype=np.float32)
    for _ in range(9):
        if detector.process_chunk(loud, 0.1) is not None:
            return 1
    return 0 if detector.process_chunk(loud, 0.1) is not None else 1
