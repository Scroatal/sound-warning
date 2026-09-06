from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import replace
import time
import os
import sys
import threading
from pathlib import Path
import urllib.error

from .audio_monitor import AudioMonitor
from . import __version__
from .border_warning import BorderWarning
from .meter import MicrophoneMeter
from .windows import enable_dpi_awareness
from .updates import (UpdateResult, check_release, download_release, portable_target,
                      launch_installer, apply_update)
from .detector import DetectionEvent
from .settings import Settings, default_settings_path, load_settings, save_settings, validate_settings
from .self_test import run_self_test


SELF_TEST_ARG = "--self-test"


class SoundWarningApp:
    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self.warning_count = 0
        self.lock_remaining = 0
        self.event_queue: queue.Queue[DetectionEvent | Exception | str | UpdateResult] = queue.Queue()
        self.lock_deadline = 0.0
        self.tray_icon = None
        self.pending_update = None
        self.update_busy = False
        self.quiet_since = time.monotonic()
        self.last_screen_check = 0.0
        self.closed = False

        self.root.title("Sound Warning")
        self.build_control_window()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_main_window)

        self.warning = BorderWarning(root)
        self.lock = FullScreenOverlay(root, background="#8b0000")
        self.meter = MicrophoneMeter(root)
        self.meter.show(settings.show_meter)
        self.meter.update(None, settings.loudness_threshold)

        self.monitor = AudioMonitor(settings, self.queue_event, self.queue_error)
        self.monitor.start()
        if self.start_tray() and "--background" in sys.argv:
            self.root.withdraw()
        self.root.after(100, self.process_events)
        self.root.after(5000, self.scheduled_update_check)

    def build_control_window(self) -> None:
        self.root.geometry("600x570")
        self.root.minsize(560, 570)
        self.root.configure(bg="#f5f5f5")

        title = tk.Label(
            self.root,
            text="Sound Warning",
            font=("Segoe UI", 13, "bold"),
            bg="#f5f5f5",
        )
        title.pack(pady=(22, 8))

        privacy = tk.Label(
            self.root,
            text="No recording, storage, upload, transcription, or word analysis.",
            font=("Segoe UI", 10),
            bg="#f5f5f5",
            wraplength=360,
            justify="center",
        )
        privacy.pack(pady=(0, 14))

        self.status = tk.StringVar(value="Waiting for microphone")
        ttk.Label(self.root, textvariable=self.status).pack(pady=(0, 12))
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=16, pady=8)
        monitoring_page = ttk.Frame(notebook)
        updates_page = ttk.Frame(notebook)
        notebook.add(monitoring_page, text="Monitoring")
        notebook.add(updates_page, text="Updates")
        form = ttk.Frame(monitoring_page, padding=12)
        form.pack(fill="x", padx=12)
        self.setting_inputs = {}
        for row, (key, label) in enumerate((
            ("loudness_threshold", "Loudness threshold (RMS, 0 to 1)"),
            ("warning_limit", "Warnings before quiet time"),
            ("lock_seconds", "Quiet time (seconds)"),
        )):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=8)
            value = tk.StringVar(value=str(getattr(self.settings, key)))
            ttk.Entry(form, textvariable=value, width=10).grid(row=row, column=1, padx=16)
            self.setting_inputs[key] = value
        self.show_meter_input = tk.BooleanVar(value=self.settings.show_meter)
        ttk.Checkbutton(form, text="Show microphone meter on every screen",
                        variable=self.show_meter_input, command=self.toggle_meter).grid(
                            row=3, column=0, columnspan=2, sticky="w", pady=8)

        button_frame = ttk.Frame(monitoring_page)
        button_frame.pack(pady=16)
        tk.Button(button_frame, text="Open Settings", command=self.open_settings).pack(side="left", padx=6)
        tk.Button(button_frame, text="Test Warning", command=self.show_warning).pack(side="left", padx=6)
        tk.Button(button_frame, text="Hide", command=self.hide_main_window).pack(side="left", padx=6)
        tk.Button(button_frame, text="Quit", command=self.shutdown).pack(side="left", padx=6)

        update_form = ttk.Frame(updates_page, padding=20)
        update_form.pack(fill="x")
        ttk.Label(update_form, text=f"Updates | Version {__version__}").pack(anchor="w")
        ttk.Label(update_form, text="GitHub repository (owner/repository)").pack(anchor="w", pady=(10, 4))
        self.repo_input = tk.StringVar(value=self.settings.update_repository)
        ttk.Entry(update_form, textvariable=self.repo_input).pack(fill="x")
        self.auto_update_input = tk.BooleanVar(value=self.settings.auto_update)
        ttk.Checkbutton(update_form, text="Automatically download and install updates",
                        variable=self.auto_update_input).pack(anchor="w", pady=6)
        self.update_status = tk.StringVar(value="No update repository configured" if not self.settings.update_repository
                                         else "Automatic check at startup and every 6 hours")
        ttk.Label(update_form, textvariable=self.update_status, wraplength=490).pack(anchor="w", pady=4)
        actions = ttk.Frame(update_form)
        actions.pack(anchor="w", pady=6)
        ttk.Button(actions, text="Check for Updates", command=lambda: self.check_updates(manual=True)).pack(side="left")
        self.install_button = ttk.Button(actions, text="Install and Restart", command=self.install_update, state="disabled")
        self.install_button.pack(side="left", padx=8)
        ttk.Button(self.root, text="Save Settings", command=self.apply_settings).pack(pady=12)

    def start_tray(self) -> bool:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            return False

        image = Image.new("RGB", (64, 64), "#c50000")
        draw = ImageDraw.Draw(image)
        draw.rectangle((12, 12, 52, 52), outline="white", width=5)
        draw.line((22, 32, 42, 32), fill="white", width=5)

        def show_window(*_args: object) -> None:
            self.event_queue.put("show")

        def open_settings(*_args: object) -> None:
            self.event_queue.put("settings")

        def quit_app(*_args: object) -> None:
            self.event_queue.put("quit")

        self.tray_icon = pystray.Icon(
            "SoundWarning",
            image,
            "Sound Warning",
            menu=pystray.Menu(
                pystray.MenuItem("Show", show_window),
                pystray.MenuItem("Open Settings", open_settings),
                pystray.MenuItem("Quit", quit_app),
            ),
        )
        threading.Thread(target=self.tray_icon.run, name="SoundWarningTray", daemon=True).start()
        return True

    def queue_event(self, event: DetectionEvent) -> None:
        self.event_queue.put(event)

    def queue_error(self, exc: Exception) -> None:
        self.event_queue.put(exc)

    def process_events(self) -> None:
        while True:
            try:
                item = self.event_queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, UpdateResult):
                self.update_busy = False
                if item.repository and item.repository != self.settings.update_repository:
                    continue
                self.update_status.set(item.message)
                if item.exit_for_update:
                    self.shutdown()
                    return
                if item.pending:
                    self.pending_update = item.pending
                    self.install_button.configure(state="normal")
            elif isinstance(item, str):
                if item == "quit":
                    self.shutdown()
                    return
                if item == "show":
                    self.show_main_window()
                elif item == "settings":
                    self.open_settings()
            elif isinstance(item, Exception):
                self.show_error(item)
            elif item.kind == "yell":
                self.handle_yell()

        self.refresh_meter()
        self.root.after(100, self.process_events)

    def toggle_meter(self) -> None:
        self.meter.show(self.show_meter_input.get())

    def refresh_meter(self) -> None:
        now = time.monotonic()
        level, measured_at = self.monitor.latest_level
        live_level = level if measured_at and now - measured_at < 2 else None
        self.meter.update(live_level, self.settings.loudness_threshold)
        self.status.set("Microphone monitoring active" if live_level is not None else "Waiting for microphone")
        if live_level is None or live_level >= self.settings.loudness_threshold:
            self.quiet_since = now
        if now - self.last_screen_check >= 5:
            self.meter.refresh_screens()
            self.last_screen_check = now
        if (self.pending_update and self.settings.auto_update and not self.update_busy
                and self.root.state() in ("withdrawn", "iconic") and not self.lock_remaining
                and not self.warning.is_visible and now - self.quiet_since >= 10):
            self.install_update()

    def scheduled_update_check(self) -> None:
        if self.settings.auto_update and self.settings.update_repository:
            self.check_updates()
        self.root.after(6 * 60 * 60 * 1000, self.scheduled_update_check)

    def check_updates(self, manual: bool = False) -> None:
        if self.update_busy or self.pending_update:
            return
        repository = self.settings.update_repository
        if not repository:
            self.update_status.set("Enter the GitHub repository and click Save Settings first")
            return
        self.update_busy = True
        self.update_status.set("Checking GitHub Releases...")

        def worker():
            try:
                release = check_release(repository)
                if release is None:
                    result = UpdateResult("You have the latest published version", repository=repository)
                else:
                    pending = download_release(release, portable_target())
                    result = UpdateResult(f"Version {release.version} ready. Installs when hidden and quiet, or restart now.",
                                          pending=pending, repository=repository)
            except urllib.error.HTTPError as exc:
                message = "Repository or release unavailable. A public GitHub release is required." if exc.code == 404 else f"GitHub check failed (HTTP {exc.code}); will retry later."
                result = UpdateResult(message, repository=repository)
            except Exception as exc:
                result = UpdateResult(f"Update unavailable: {exc}", repository=repository)
            self.event_queue.put(result)

        threading.Thread(target=worker, name="SoundWarningUpdates", daemon=True).start()

    def install_update(self) -> None:
        if not self.pending_update or self.update_busy:
            return
        if self.lock_remaining or self.warning.is_visible:
            self.update_status.set("Update ready; waiting for the current warning or quiet time to finish")
            return
        self.update_busy = True
        self.install_button.configure(state="disabled")
        self.update_status.set("Preparing update and restart...")
        pending = self.pending_update

        def worker():
            try:
                launch_installer(pending)
                result = UpdateResult("Restarting to finish update", exit_for_update=True)
            except Exception as exc:
                result = UpdateResult(f"Update not installed: {exc}", pending=pending)
            self.event_queue.put(result)

        threading.Thread(target=worker, name="SoundWarningInstaller", daemon=True).start()

    def handle_yell(self) -> None:
        if self.lock_remaining > 0:
            self.lock_deadline += self.settings.lock_seconds
            self.lock_remaining = max(0, int(self.lock_deadline - time.monotonic() + 0.999))
            self.update_lock()
            return

        self.warning_count += 1
        if self.warning_count >= self.settings.warning_limit:
            self.start_lock()
        else:
            self.show_warning()

    def show_warning(self) -> None:
        self.warning.show()
        self.meter.raise_above_warning()

    def start_lock(self) -> None:
        self.warning.hide()
        self.lock_deadline = time.monotonic() + self.settings.lock_seconds
        self.lock_remaining = self.settings.lock_seconds
        self.update_lock()
        self.lock.show("SOUND WARNING", f"Quiet time: {self.lock_remaining}")
        self.meter.raise_above_warning()
        self.tick_lock()

    def update_lock(self) -> None:
        if self.lock.is_visible:
            self.lock.set_text("SOUND WARNING", f"Quiet time: {self.lock_remaining}")

    def tick_lock(self) -> None:
        self.lock_remaining = max(0, int(self.lock_deadline - time.monotonic() + 0.999))
        if self.lock_remaining <= 0:
            self.lock.hide()
            self.warning_count = 0
            return

        self.update_lock()
        self.root.after(100, self.tick_lock)

    def show_error(self, exc: Exception) -> None:
        self.monitor.stop()
        self.status.set("Microphone unavailable")
        settings_path = default_settings_path()
        messagebox.showerror(
            "Sound Warning microphone error",
            "Sound Warning could not start microphone monitoring.\n\n"
            f"{exc}\n\nSettings file:\n{settings_path}",
        )
        self.root.deiconify()

    def hide_main_window(self) -> None:
        if self.tray_icon:
            self.root.withdraw()
        else:
            self.root.iconify()

    def apply_settings(self) -> None:
        if self.update_busy and self.pending_update:
            self.update_status.set("Wait for the update restart to finish before changing settings")
            return
        try:
            updated = validate_settings(replace(
                self.settings,
                loudness_threshold=float(self.setting_inputs["loudness_threshold"].get()),
                warning_limit=int(self.setting_inputs["warning_limit"].get()),
                lock_seconds=int(self.setting_inputs["lock_seconds"].get()),
                show_meter=self.show_meter_input.get(),
                auto_update=self.auto_update_input.get(),
                update_repository=self.repo_input.get().strip(),
            ))
            save_settings(updated)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Settings", str(exc), parent=self.root)
            return
        self.monitor.stop()
        if updated.update_repository != self.settings.update_repository:
            self.pending_update = None
            self.install_button.configure(state="disabled")
        self.settings = updated
        self.monitor = AudioMonitor(updated, self.queue_event, self.queue_error)
        self.monitor.start()
        self.meter.show(updated.show_meter)
        self.repo_input.set(updated.update_repository)
        self.quiet_since = time.monotonic()
        self.status.set("Settings saved. Microphone monitoring active")
        if updated.auto_update and updated.update_repository:
            self.check_updates()

    def show_main_window(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def open_settings(self) -> None:
        path = default_settings_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def shutdown(self) -> None:
        if self.closed:
            return
        self.closed = True
        for job in self.root.tk.call("after", "info"):
            self.root.after_cancel(job)
        self.warning.hide()
        self.meter.destroy()
        self.monitor.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()


class FullScreenOverlay:
    def __init__(self, parent: tk.Tk, background: str) -> None:
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.configure(bg=background)
        self.window.attributes("-fullscreen", True)
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)
        self.is_visible = False

        self.title_label = tk.Label(
            self.window,
            text="",
            fg="white",
            bg=background,
            font=("Segoe UI", 64, "bold"),
        )
        self.title_label.pack(expand=True, fill="both", pady=(120, 0))

        self.message_label = tk.Label(
            self.window,
            text="",
            fg="white",
            bg=background,
            font=("Segoe UI", 36, "bold"),
        )
        self.message_label.pack(expand=True, fill="both", pady=(0, 120))

    def show(self, title: str, message: str) -> None:
        self.set_text(title, message)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.is_visible = True

    def hide(self) -> None:
        self.window.withdraw()
        self.is_visible = False

    def set_text(self, title: str, message: str) -> None:
        self.title_label.configure(text=title)
        self.message_label.configure(text=message)


def main() -> None:
    if "--apply-update" in sys.argv:
        index = sys.argv.index("--apply-update")
        raise SystemExit(apply_update(Path(sys.argv[index + 1])))
    if SELF_TEST_ARG in sys.argv:
        raise SystemExit(run_self_test())

    enable_dpi_awareness()
    root = tk.Tk()
    if "--preview" in sys.argv:
        root.withdraw()
        warning = BorderWarning(root)
        warning.show()
        root.after(4500, root.destroy)
        root.mainloop()
        return
    try:
        settings = load_settings()
    except (ValueError, TypeError, OSError) as exc:
        root.withdraw()
        messagebox.showerror("Sound Warning settings error", str(exc))
        root.destroy()
        return
    app = SoundWarningApp(root, settings)
    root.bind("<Control-Alt-q>", lambda _event: app.shutdown())
    root.mainloop()
