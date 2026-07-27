from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from train_rescuer_baseline import FileRecord  # noqa: E402
from tune_rescuer_threshold import (  # noqa: E402
    assign_validation_split,
    build_threshold_table,
    select_threshold,
    threshold_metrics,
)


class RescuerThresholdTests(unittest.TestCase):
    def test_validation_split_preserves_original_test(self) -> None:
        records = [
            FileRecord(Path("p6.csv"), "Person 6/p6.csv", 1, "Person 6", "train"),
            FileRecord(Path("p7.csv"), "Person 7/p7.csv", 1, "Person 7", "train"),
            FileRecord(Path("p8.csv"), "Person 8/p8.csv", 1, "Person 8", "test"),
            FileRecord(Path("e1.csv"), "Empty/e1.csv", 0, "empty", "train"),
            FileRecord(Path("e2.csv"), "Empty/e2.csv", 0, "empty", "train"),
            FileRecord(Path("e3.csv"), "Empty/e3.csv", 0, "empty", "test"),
        ]

        updated, selected_empty = assign_validation_split(
            records,
            validation_subject="Person 7",
            validation_empty_files=1,
            seed=42,
        )

        splits = {record.relative_path: record.split for record in updated}
        self.assertEqual(splits["Person 7/p7.csv"], "validation")
        self.assertEqual(splits[selected_empty[0]], "validation")
        self.assertEqual(splits["Person 8/p8.csv"], "test")
        self.assertEqual(splits["Empty/e3.csv"], "test")
        self.assertEqual(splits["Person 6/p6.csv"], "train")

    def test_threshold_metrics_returns_expected_errors(self) -> None:
        y_true = np.asarray([0, 0, 1, 1])
        probabilities = np.asarray([0.10, 0.60, 0.40, 0.90])

        result = threshold_metrics(y_true, probabilities, threshold=0.50)

        self.assertEqual(result["false_alarms"], 1)
        self.assertEqual(result["missed_human_windows"], 1)
        self.assertAlmostEqual(result["recall_human"], 0.5)
        self.assertAlmostEqual(result["empty_accuracy"], 0.5)
        self.assertEqual(result["confusion_matrix"], [[1, 1], [1, 1]])

    def test_selection_meets_recall_then_minimizes_false_alarms(self) -> None:
        y_true = np.asarray([0, 0, 0, 1, 1, 1])
        probabilities = np.asarray([0.05, 0.20, 0.65, 0.30, 0.70, 0.90])
        candidates = build_threshold_table(y_true, probabilities)

        selected, rule = select_threshold(candidates, target_recall=2 / 3)
        result = threshold_metrics(y_true, probabilities, selected)

        self.assertGreaterEqual(result["recall_human"], 2 / 3)
        self.assertEqual(result["false_alarms"], 0)
        self.assertEqual(rule, "meet_target_recall_then_minimize_false_alarms")

    def test_threshold_table_has_unique_ordered_candidates(self) -> None:
        y_true = np.asarray([0, 1])
        probabilities = np.asarray([0.25, 0.75])

        table = build_threshold_table(y_true, probabilities)

        self.assertEqual(len(table), 99)
        self.assertTrue(table["threshold"].is_monotonic_increasing)
        self.assertFalse(table["threshold"].duplicated().any())
        self.assertTrue(
            {"recall_human", "empty_accuracy", "false_alarms"}.issubset(table.columns)
        )


if __name__ == "__main__":
    unittest.main()
