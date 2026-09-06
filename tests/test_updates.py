import hashlib
import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from sound_warning.updates import (Release, download_release, replace_with_rollback,
                                   repository_name, select_release, version_tuple)


class UpdateTests(unittest.TestCase):
    def release_data(self):
        return {"tag_name": "v0.4.0", "assets": [{
            "name": "SoundWarningPortable.exe", "size": 10,
            "digest": "sha256:" + "a" * 64,
            "browser_download_url": "https://github.com/parent/sound-warning/releases/download/v0.4.0/SoundWarningPortable.exe",
        }]}

    def test_versions_and_repository(self):
        self.assertGreater(version_tuple("v0.10.0"), version_tuple("0.9.9"))
        self.assertEqual(repository_name("https://github.com/parent/sound-warning.git"), "parent/sound-warning")
        for value in ("https://evil.example/parent/app", "parent/app/extra", "../app", "parent/.."):
            with self.assertRaises(ValueError):
                repository_name(value)
        with self.assertRaises(ValueError):
            version_tuple("v1.0.0-beta1")

    def test_never_downgrade_or_install_prerelease(self):
        self.assertIsNone(select_release(self.release_data(), "parent/sound-warning", current="0.4.0"))
        self.assertIsNone(select_release(self.release_data(), "parent/sound-warning", current="1.0.0"))
        data = self.release_data()
        data["prerelease"] = True
        self.assertIsNone(select_release(data, "parent/sound-warning", current="0.3.0"))

    def test_only_download_asset_from_configured_repository(self):
        data = self.release_data()
        release = select_release(data, "parent/sound-warning", current="0.3.0")
        self.assertEqual(release.version, "0.4.0")
        data["assets"][0]["browser_download_url"] = "https://github.com/other/app/releases/download/v0.4.0/app.exe"
        with self.assertRaises(ValueError):
            select_release(data, "parent/sound-warning", current="0.3.0")

    def test_checksum_required(self):
        data = self.release_data()
        data["assets"][0]["digest"] = None
        with self.assertRaises(ValueError):
            select_release(data, "parent/sound-warning", current="0.3.0")

    def test_download_integrity_and_no_changes_to_current_app(self):
        contents = b"MZtest update"
        digest = hashlib.sha256(contents).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "app.exe"
            target.write_bytes(b"old app")
            release = Release("0.4.0", "https://github.com/example", digest, len(contents))
            with patch("sound_warning.updates.open_url", return_value=io.BytesIO(contents)):
                pending = download_release(release, target)
            self.assertEqual(pending.staged.read_bytes(), contents)
            self.assertEqual(target.read_bytes(), b"old app")
            with patch("sound_warning.updates.open_url", return_value=io.BytesIO(b"MZcorrupted!!")):
                with self.assertRaises(ValueError):
                    download_release(release, target)
            self.assertEqual(target.read_bytes(), b"old app")

    def test_failed_self_test_restores_old_app(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "app.exe"
            staged = Path(folder) / "new.exe"
            target.write_bytes(b"old app")
            staged.write_bytes(b"new app")

            def fail(_target):
                raise RuntimeError("New app does not start")

            with self.assertRaises(RuntimeError):
                replace_with_rollback(target, staged, hashlib.sha256(b"new app").hexdigest(), fail)
            self.assertEqual(target.read_bytes(), b"old app")

    def test_success_retains_backup_and_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "app.exe"
            staged = Path(folder) / "new.exe"
            settings = Path(folder) / "settings.json"
            target.write_bytes(b"old app")
            staged.write_bytes(b"new app")
            settings.write_text('{"loudness_threshold": 0.06}')
            replace_with_rollback(target, staged, hashlib.sha256(b"new app").hexdigest(), lambda _target: None)
            self.assertEqual(target.read_bytes(), b"new app")
            self.assertEqual(target.with_suffix(".exe.previous").read_bytes(), b"old app")
            self.assertEqual(settings.read_text(), '{"loudness_threshold": 0.06}')
