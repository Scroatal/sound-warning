from __future__ import annotations

import math
import tkinter as tk

from .windows import monitors, position_meter


def meter_state(level: float | None, threshold: float) -> tuple[float, str, str]:
    if level is None or not math.isfinite(level):
        return 0.0, "#9ca3af", "Microphone unavailable"
    ratio = max(0.0, level / threshold)
    if ratio >= 1:
        return ratio, "#f34c5b", "Too loud - lower your voice"
    if ratio >= 0.75:
        return ratio, "#f0c34e", "Getting loud"
    return ratio, "#44ce97", "Inside voice"


class MicrophoneMeter:
    HEIGHT = 38

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.screens = []
        self.windows: list[tuple[tk.Toplevel, tk.Canvas, int]] = []
        self.enabled = True
        self.refresh_screens()

    def refresh_screens(self) -> None:
        screens = monitors(self.root)
        if screens == self.screens:
            return
        self.destroy()
        self.screens = screens
        for x, y, width, _height in screens:
            window = tk.Toplevel(self.root)
            window.withdraw()
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            window.attributes("-alpha", 0.94)
            canvas = tk.Canvas(window, bg="#181b20", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            self.windows.append((window, canvas, width))
            position_meter(window, x, y, width, self.HEIGHT)
            if not self.enabled:
                window.withdraw()

    def show(self, enabled: bool) -> None:
        self.enabled = enabled
        for window, _canvas, _width in self.windows:
            window.deiconify() if enabled else window.withdraw()

    def update(self, level: float | None, threshold: float) -> None:
        ratio, color, label = meter_state(level, threshold)
        for _window, canvas, width in self.windows:
            canvas.delete("all")
            left = 256 if width >= 900 else 200
            right = width - (170 if width >= 900 else 105)
            span = max(20, right - left)
            canvas.create_text(12, 19, text=label, fill=color, anchor="w", font=("Segoe UI", 11, "bold"))
            canvas.create_rectangle(left, 12, right, 28, fill="#343a43", outline="")
            canvas.create_rectangle(left, 12, left+span*min(1.0, ratio/1.5), 28, fill=color, outline="")
            limit = left + span / 1.5
            canvas.create_line(limit, 7, limit, 32, fill="white", width=2)
            text = "No signal" if level is None else f"{round(ratio*100)}% of limit"
            canvas.create_text(width-12, 19, text=text, fill="#f4f6f8", anchor="e", font=("Segoe UI", 10))

    def raise_above_warning(self) -> None:
        if self.enabled:
            for window, _canvas, _width in self.windows:
                window.lift()

    def destroy(self) -> None:
        for window, _canvas, _width in self.windows:
            window.destroy()
        self.windows.clear()
