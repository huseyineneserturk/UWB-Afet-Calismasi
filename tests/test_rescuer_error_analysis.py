from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from analyze_rescuer_errors import (  # noqa: E402
    parse_human_metadata,
    summarize_condition,
)


class RescuerErrorAnalysisTests(unittest.TestCase):
    def test_metadata_parser_reads_condition_from_path(self) -> None:
        metadata = parse_human_metadata(
            "Human Presence/Person 8/Wall Obstacle/1m 45°/"
            "2.5 not facing radar abs.csv"
        )

        self.assertEqual(metadata["subject_condition"], "Person 8")
        self.assertEqual(metadata["obstacle"], "wall")
        self.assertEqual(metadata["target_distance_m"], 2.5)
        self.assertEqual(metadata["orientation"], "not_facing_radar")
        self.assertEqual(metadata["radar_placement"], "1m 45°")

    def test_condition_summary_counts_detected_and_missed_windows(self) -> None:
        table = pd.DataFrame(
            {
                "obstacle": ["wall", "wall", "no_obstacle"],
                "prediction": [1, 0, 1],
                "human_probability": [0.8, 0.3, 0.7],
            }
        )

        summary = summarize_condition(
            table,
            "obstacle",
            ["no_obstacle", "wall"],
        )

        no_obstacle = summary.iloc[0]
        wall = summary.iloc[1]
        self.assertEqual(no_obstacle["detected_count"], 1)
        self.assertEqual(no_obstacle["missed_count"], 0)
        self.assertEqual(wall["window_count"], 2)
        self.assertAlmostEqual(wall["recall"], 0.5)
        self.assertTrue(np.isfinite(summary["mean_human_probability"]).all())


if __name__ == "__main__":
    unittest.main()
