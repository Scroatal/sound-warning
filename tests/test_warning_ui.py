import tkinter as tk
import unittest
from unittest.mock import patch

from sound_warning.app import SoundWarningApp
from sound_warning.settings import Settings


class WarningUITests(unittest.TestCase):
    def test_preview_repeat_and_lock_transition(self):
        root = tk.Tk()
        with patch("sound_warning.app.AudioMonitor"), patch.object(SoundWarningApp, "start_tray", return_value=False):
            app = SoundWarningApp(root, Settings())
        try:
            root.update()
            self.assertEqual(root.state(), "normal")
            app.show_warning()
            root.update()
            self.assertTrue(app.warning.is_visible)
            self.assertEqual(len(app.warning.canvas.find_withtag("edge")), 4)
            first_timer = app.warning._hide_job
            app.show_warning()
            self.assertNotEqual(first_timer, app.warning._hide_job)
            app.warning._flash()
            self.assertEqual(app.warning.canvas.itemcget("edge", "fill"), "#701722")
            app.start_lock()
            self.assertFalse(app.warning.is_visible)
            self.assertEqual(app.lock_remaining, 15)
            before = app.lock_deadline
            app.handle_yell()
            self.assertAlmostEqual(app.lock_deadline, before + 15)
            app.lock_deadline = 0
            app.tick_lock()
            self.assertFalse(app.lock.is_visible)
        finally:
            app.shutdown()


if __name__ == "__main__":
    unittest.main()
