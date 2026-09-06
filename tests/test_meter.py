import time
import tkinter as tk
import unittest
from unittest.mock import patch

from sound_warning.meter import MicrophoneMeter, meter_state
from sound_warning.app import SoundWarningApp
from sound_warning.settings import Settings


class MeterTests(unittest.TestCase):
    def test_threshold_colours(self):
        self.assertEqual(meter_state(0.02, 0.08)[2], "Inside voice")
        self.assertEqual(meter_state(0.06, 0.08)[2], "Getting loud")
        self.assertEqual(meter_state(0.08, 0.08)[2], "Too loud - lower your voice")
        self.assertEqual(meter_state(None, 0.08)[2], "Microphone unavailable")

    def test_meter_survives_hiding_control_window_and_marks_stale_audio(self):
        root = tk.Tk()
        with patch("sound_warning.app.AudioMonitor"), patch.object(SoundWarningApp, "start_tray", return_value=False):
            app = SoundWarningApp(root, Settings())
        try:
            root.withdraw()
            app.monitor.latest_level = (0.09, time.monotonic())
            app.refresh_meter()
            root.update_idletasks()
            self.assertTrue(all(window.state() == "normal" for window, _canvas, _width in app.meter.windows))
            canvas = app.meter.windows[0][1]
            self.assertEqual(canvas.itemcget(canvas.find_all()[0], "text"), "Too loud - lower your voice")
            app.monitor.latest_level = (0.09, time.monotonic() - 3)
            app.refresh_meter()
            self.assertEqual(canvas.itemcget(canvas.find_all()[0], "text"), "Microphone unavailable")
        finally:
            app.shutdown()

    def test_multiple_screens_and_disconnect(self):
        root = tk.Tk()
        root.withdraw()
        screens = [(0, 0, 1000, 800), (-800, 0, 800, 600)]
        with patch("sound_warning.meter.monitors", return_value=screens):
            meter = MicrophoneMeter(root)
        try:
            self.assertEqual(len(meter.windows), 2)
            meter.update(0.05, 0.08)
            meter.show(False)
            with patch("sound_warning.meter.monitors", return_value=screens[:1]):
                meter.refresh_screens()
            self.assertEqual(len(meter.windows), 1)
            self.assertEqual(meter.windows[0][0].state(), "withdrawn")
        finally:
            meter.destroy()
            root.destroy()
