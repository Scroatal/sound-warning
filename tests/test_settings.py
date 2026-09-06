import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from sound_warning.settings import Settings, load_settings, validate_settings


class SettingsTests(unittest.TestCase):
    def test_fresh_install_has_update_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = load_settings(path)
            self.assertEqual(settings.update_repository, "Scroatal/sound-warning")
            self.assertTrue(settings.auto_update)

    def test_existing_threshold_survives_upgrade(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text('{"loudness_threshold": 0.06, "warning_limit": 4}')
            with patch("sound_warning.settings.bundled_repository", return_value="parent/app"):
                settings = load_settings(path)
            self.assertEqual(settings.loudness_threshold, 0.06)
            self.assertEqual(settings.warning_limit, 4)
            self.assertTrue(settings.show_meter)
            self.assertEqual(settings.update_repository, "parent/app")

    def test_invalid_numeric_settings(self):
        for settings in (Settings(loudness_threshold=float("nan")), Settings(smoothing_factor=float("inf")),
                         Settings(warning_limit=1.5), Settings(show_meter="false")):
            with self.assertRaises(ValueError):
                validate_settings(settings)
