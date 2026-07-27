from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from compare_rescuer_models import create_models, evaluate_models  # noqa: E402


class RescuerModelComparisonTests(unittest.TestCase):
    def test_model_factory_is_reproducible(self) -> None:
        models = create_models(seed=42)

        self.assertEqual(
            set(models),
            {"logistic_regression", "random_forest"},
        )
        forest = models["random_forest"]
        self.assertEqual(forest.random_state, 42)
        self.assertEqual(forest.n_estimators, 400)

    def test_both_models_return_metrics_and_two_by_two_matrix(self) -> None:
        rng = np.random.default_rng(42)
        x_train = rng.normal(size=(80, 12))
        y_train = np.asarray([0] * 40 + [1] * 40)
        x_train[y_train == 1, :3] += 1.2
        x_test = rng.normal(size=(30, 12))
        y_test = np.asarray([0] * 15 + [1] * 15)
        x_test[y_test == 1, :3] += 1.2

        results, trained = evaluate_models(
            create_models(seed=42),
            x_train,
            y_train,
            x_test,
            y_test,
        )

        self.assertEqual(set(results), set(trained))
        for model_result in results.values():
            self.assertEqual(np.asarray(model_result["confusion_matrix"]).shape, (2, 2))
            self.assertIn("balanced_accuracy", model_result["metrics"])
            self.assertGreaterEqual(model_result["fit_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
