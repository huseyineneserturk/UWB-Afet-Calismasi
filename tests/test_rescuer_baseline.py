from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from train_rescuer_baseline import extract_features, is_amplitude_file  # noqa: E402


class RescuerBaselineTests(unittest.TestCase):
    def test_amplitude_file_detection(self) -> None:
        self.assertTrue(is_amplitude_file(Path("2 facing radar abs.csv")))
        self.assertTrue(is_amplitude_file(Path("clean amplitude sample.csv")))
        self.assertFalse(is_amplitude_file(Path("2 facing radar angle.csv")))

    def test_feature_vector_is_finite_and_has_expected_length(self) -> None:
        rng = np.random.default_rng(42)
        window = 0.005 + rng.normal(0, 0.0001, size=(170, 109))
        features = extract_features(window)

        self.assertEqual(features.shape, (12,))
        self.assertTrue(np.isfinite(features).all())
        self.assertTrue((features >= 0).all())

    def test_more_motion_increases_basic_variability(self) -> None:
        time = np.linspace(0, 4 * np.pi, 170)
        quiet = np.full((170, 109), 0.005)
        moving = quiet.copy()
        moving[:, 40] += 0.001 * np.sin(time)

        quiet_features = extract_features(quiet)
        moving_features = extract_features(moving)

        self.assertGreater(moving_features[2], quiet_features[2])
        self.assertGreater(moving_features[7], quiet_features[7])


if __name__ == "__main__":
    unittest.main()
