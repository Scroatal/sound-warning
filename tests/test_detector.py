import unittest

import numpy as np

from sound_warning.detector import LoudnessDetector, calculate_rms


class LoudnessDetectorTests(unittest.TestCase):
    def test_rms_uses_signal_level_only(self) -> None:
        samples = np.array([0.5, -0.5, 0.5, -0.5], dtype=np.float32)
        self.assertAlmostEqual(calculate_rms(samples), 0.5, places=6)

    def test_yell_event_requires_continuous_duration(self) -> None:
        detector = LoudnessDetector(
            threshold=0.08,
            yell_duration_seconds=1.0,
            smoothing_factor=1.0,
        )
        loud = np.full((1600, 1), 0.2, dtype=np.float32)

        events = [detector.process_chunk(loud, 0.1) for _ in range(9)]
        self.assertTrue(all(event is None for event in events))

        event = detector.process_chunk(loud, 0.1)
        self.assertIsNotNone(event)
        self.assertEqual(event.kind, "yell")

    def test_quiet_chunk_resets_loud_run(self) -> None:
        detector = LoudnessDetector(
            threshold=0.08,
            yell_duration_seconds=1.0,
            smoothing_factor=1.0,
        )
        loud = np.full((1600, 1), 0.2, dtype=np.float32)
        quiet = np.zeros((1600, 1), dtype=np.float32)

        for _ in range(8):
            detector.process_chunk(loud, 0.1)
        detector.process_chunk(quiet, 0.1)

        events = [detector.process_chunk(loud, 0.1) for _ in range(9)]
        self.assertTrue(all(event is None for event in events))
        self.assertIsNotNone(detector.process_chunk(loud, 0.1))


if __name__ == "__main__":
    unittest.main()
