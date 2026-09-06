from __future__ import annotations

import tkinter as tk


class BorderWarning:
    """A transparent screen-sized window; only its edges and banner are visible."""

    def __init__(self, parent: tk.Tk) -> None:
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", "#010203")
        self.canvas = tk.Canvas(self.window, bg="#010203", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.is_visible = False
        self._flash_job = None
        self._hide_job = None
        self._bright = True

    def show(self, title: str = "SOUND WARNING", message: str = "Boys, you're being too loud") -> None:
        self.hide()
        width = self.window.winfo_screenwidth()
        height = self.window.winfo_screenheight()
        self.window.geometry(f"{width}x{height}+0+0")
        self.canvas.delete("all")
        thickness = 14
        for coords in ((0, 0, width, thickness), (0, height-thickness, width, height),
                       (0, 0, thickness, height), (width-thickness, 0, width, height)):
            self.canvas.create_rectangle(*coords, fill="#e02030", outline="", tags="edge")
        banner_width = min(740, width - 48)
        left = (width - banner_width) / 2
        self.canvas.create_rectangle(left, 32, left + banner_width, 176, fill="#a31324", outline="")
        self.canvas.create_text(width/2, 66, text=title, fill="white", font=("Segoe UI", 16, "bold"))
        self.canvas.create_text(width/2, 122, text=message, width=banner_width-32,
                                fill="white", font=("Segoe UI", 26, "bold"))
        self.window.deiconify()
        self.window.lift()
        self.is_visible = True
        self._bright = True
        self._flash_job = self.parent.after(600, self._flash)
        self._hide_job = self.parent.after(4000, self.hide)

    def _flash(self) -> None:
        self._bright = not self._bright
        self.canvas.itemconfigure("edge", fill="#e02030" if self._bright else "#701722")
        self._flash_job = self.parent.after(600, self._flash)

    def hide(self) -> None:
        for job in (self._flash_job, self._hide_job):
            if job is not None:
                self.parent.after_cancel(job)
        self._flash_job = self._hide_job = None
        self.window.withdraw()
        self.is_visible = False
