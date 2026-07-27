"""Rescuer verisinde Logistic Regression ve Random Forest'ı karşılaştırır."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from train_rescuer_baseline import (
    FEATURE_NAMES,
    build_feature_table,
    discover_files,
    metric_payload,
    save_clean_svg,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Rescuer verisinde iki başlangıç modelini karşılaştır"
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--window-frames", type=int, default=170)
    parser.add_argument("--max-human-windows", type=int, default=4)
    parser.add_argument("--max-empty-windows", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=project_root / "reports" / "rescuer-model-comparison",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=project_root / "assets" / "images" / "model",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=project_root / "models",
    )
    return parser.parse_args()


def create_models(seed: int) -> dict[str, object]:
    return {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=2_000,
                        random_state=seed,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=400,
            max_depth=8,
            min_samples_leaf=4,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=seed,
            n_jobs=1,
        ),
    }


def evaluate_models(
    models: dict[str, object],
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    trained: dict[str, object] = {}

    for model_name, model in models.items():
        fit_start = perf_counter()
        model.fit(x_train, y_train)
        fit_seconds = perf_counter() - fit_start

        predict_start = perf_counter()
        predictions = model.predict(x_test)
        predict_seconds = perf_counter() - predict_start

        results[model_name] = {
            "metrics": metric_payload(y_test, predictions),
            "confusion_matrix": confusion_matrix(
                y_test, predictions, labels=[0, 1]
            ).tolist(),
            "fit_seconds": fit_seconds,
            "predict_seconds": predict_seconds,
        }
        trained[model_name] = model
    return results, trained


def render_comparison_figure(
    results: dict[str, dict[str, object]],
    output_path: Path,
) -> None:
    plt.style.use("dark_background")
    figure = plt.figure(figsize=(16, 6.2))
    figure.patch.set_facecolor("#071426")
    grid = figure.add_gridspec(1, 3, width_ratios=[1.35, 1, 1])
    axes = [figure.add_subplot(grid[0, index]) for index in range(3)]
    for axis in axes:
        axis.set_facecolor("#0B1F33")

    metric_keys = [
        "balanced_accuracy",
        "precision_human",
        "recall_human",
        "f1_human",
    ]
    metric_labels = [
        "Dengeli doğruluk",
        "İnsan kesinliği",
        "İnsan yakalama",
        "F1",
    ]
    positions = np.arange(len(metric_keys))
    width = 0.36
    logistic_values = [
        results["logistic_regression"]["metrics"][key] for key in metric_keys
    ]
    forest_values = [
        results["random_forest"]["metrics"][key] for key in metric_keys
    ]
    axes[0].barh(
        positions - width / 2,
        logistic_values,
        height=width,
        color="#38BDF8",
        label="Logistic Regression",
    )
    axes[0].barh(
        positions + width / 2,
        forest_values,
        height=width,
        color="#2DD4BF",
        label="Random Forest",
    )
    axes[0].set_yticks(positions, metric_labels)
    axes[0].set_xlim(0, 1.05)
    axes[0].set_xlabel("Skor")
    axes[0].set_title("Aynı testte metrikler", fontweight="bold")
    axes[0].grid(axis="x", alpha=0.18)
    for row, values in enumerate(zip(logistic_values, forest_values, strict=True)):
        for offset, value in zip((-width / 2, width / 2), values, strict=True):
            axes[0].text(
                value + 0.012,
                row + offset,
                f"{value:.1%}",
                va="center",
                fontsize=9,
            )

    for axis, model_name in zip(
        axes[1:],
        ("logistic_regression", "random_forest"),
        strict=True,
    ):
        matrix = np.asarray(results[model_name]["confusion_matrix"])
        axis.imshow(matrix, cmap="Blues")
        axis.set_xticks([0, 1], ["İnsan yok", "İnsan var"])
        axis.set_yticks([0, 1], ["İnsan yok", "İnsan var"])
        axis.set_xlabel("Model tahmini")
        axis.set_ylabel("Gerçek durum")
        axis.set_title(MODEL_LABELS[model_name], fontweight="bold")
        for row in range(2):
            for column in range(2):
                axis.text(
                    column,
                    row,
                    str(int(matrix[row, column])),
                    ha="center",
                    va="center",
                    fontsize=22,
                    fontweight="bold",
                    color=(
                        "white"
                        if matrix[row, column] > matrix.max() / 2
                        else "#0F172A"
                    ),
                )

    figure.suptitle(
        "Rescuer model karşılaştırması",
        fontsize=18,
        fontweight="bold",
    )
    figure.text(
        0.12,
        0.075,
        "■ Logistic Regression",
        color="#38BDF8",
        fontsize=10,
    )
    figure.text(
        0.25,
        0.075,
        "■ Random Forest",
        color="#2DD4BF",
        fontsize=10,
    )
    figure.text(
        0.5,
        0.015,
        "Aynı 12 özellik • Aynı eğitim/test ayrımı • Aynı 398 test penceresi",
        ha="center",
        color="#CBD5E1",
    )
    figure.tight_layout(rect=(0, 0.12, 1, 0.94))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_clean_svg(figure, output_path)
    plt.close(figure)


def render_forest_importance_figure(
    forest: RandomForestClassifier,
    output_path: Path,
) -> list[dict[str, float | str]]:
    importances = forest.feature_importances_
    order = np.argsort(importances)
    names = [FEATURE_NAMES[index] for index in order]
    values = importances[order]

    plt.style.use("dark_background")
    figure, axis = plt.subplots(figsize=(10.5, 6.8))
    figure.patch.set_facecolor("#071426")
    axis.set_facecolor("#0B1F33")
    axis.barh(names, values, color="#2DD4BF")
    axis.set_xlabel("Özellik önemi")
    axis.set_title(
        "Random Forest hangi özelliklerden yararlandı?",
        fontsize=15,
        fontweight="bold",
    )
    axis.grid(axis="x", alpha=0.18)
    figure.text(
        0.5,
        0.015,
        "Yüksek değer, karar ağaçlarının bu özelliği daha sık ve yararlı kullandığını gösterir.",
        ha="center",
        color="#CBD5E1",
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.96))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_clean_svg(figure, output_path)
    plt.close(figure)

    return [
        {"feature": FEATURE_NAMES[index], "importance": float(importances[index])}
        for index in np.argsort(importances)[::-1]
    ]


def main() -> None:
    args = parse_args()
    data_root = args.data_root.resolve()
    records = discover_files(data_root, args.seed)
    print(f"{len(records)} genlik dosyası bulundu.", flush=True)

    table, skipped = build_feature_table(
        records=records,
        window_frames=args.window_frames,
        max_human_windows=args.max_human_windows,
        max_empty_windows=args.max_empty_windows,
        seed=args.seed,
    )
    train = table[table["split"] == "train"].copy()
    test = table[table["split"] == "test"].copy()
    if set(train["label"]) != {0, 1} or set(test["label"]) != {0, 1}:
        raise RuntimeError("Eğitim ve test bölümlerinin ikisi de iki sınıf içermelidir.")

    x_train = train[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y_train = train["label"].to_numpy(dtype=np.int64)
    x_test = test[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y_test = test["label"].to_numpy(dtype=np.int64)

    results, trained_models = evaluate_models(
        create_models(args.seed),
        x_train,
        y_train,
        x_test,
        y_test,
    )

    args.report_dir.mkdir(parents=True, exist_ok=True)
    args.image_dir.mkdir(parents=True, exist_ok=True)
    args.model_dir.mkdir(parents=True, exist_ok=True)

    comparison_image = args.image_dir / "rescuer-model-karsilastirmasi.svg"
    importance_image = args.image_dir / "rescuer-random-forest-onemleri.svg"
    render_comparison_figure(results, comparison_image)
    forest_importances = render_forest_importance_figure(
        trained_models["random_forest"],
        importance_image,
    )

    logistic_balanced = results["logistic_regression"]["metrics"][
        "balanced_accuracy"
    ]
    forest_balanced = results["random_forest"]["metrics"]["balanced_accuracy"]
    logistic_recall = results["logistic_regression"]["metrics"]["recall_human"]
    forest_recall = results["random_forest"]["metrics"]["recall_human"]
    file_counts = Counter((record.split, record.label) for record in records)
    window_counts = Counter(zip(table["split"], table["label"]))

    payload = {
        "task": "human_presence_binary_classification",
        "comparison_rule": "same_features_same_split_no_test_tuning",
        "representation": "amplitude_only",
        "window_frames": args.window_frames,
        "window_seconds": args.window_frames / 17.0,
        "feature_count": len(FEATURE_NAMES),
        "random_seed": args.seed,
        "test_subjects": ["Person 8", "Person 9"],
        "files": {
            "train_empty": file_counts[("train", 0)],
            "train_human": file_counts[("train", 1)],
            "test_empty": file_counts[("test", 0)],
            "test_human": file_counts[("test", 1)],
        },
        "windows": {
            "train_empty": window_counts[("train", 0)],
            "train_human": window_counts[("train", 1)],
            "test_empty": window_counts[("test", 0)],
            "test_human": window_counts[("test", 1)],
        },
        "models": {
            "logistic_regression": {
                "settings": {
                    "scaler": "StandardScaler",
                    "class_weight": "balanced",
                    "max_iter": 2_000,
                },
                **results["logistic_regression"],
            },
            "random_forest": {
                "settings": {
                    "n_estimators": 400,
                    "max_depth": 8,
                    "min_samples_leaf": 4,
                    "max_features": "sqrt",
                    "class_weight": "balanced_subsample",
                },
                **results["random_forest"],
                "feature_importances": forest_importances,
            },
        },
        "difference_random_forest_minus_logistic": {
            "balanced_accuracy": forest_balanced - logistic_balanced,
            "recall_human": forest_recall - logistic_recall,
        },
        "skipped_file_count": len(skipped),
        "limitations": [
            "Karşılaştırma pencere düzeyindedir; bağımsız saha deneyi değildir.",
            "İnsan-yok sınıfı yalnızca 12 kaynak dosyadan gelir.",
            "Random Forest ayarları test sonucuna göre değiştirilmemiştir.",
            "Gerçek enkaz koşulları Rescuer veri setinde yoktur.",
        ],
    }
    (args.report_dir / "metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "model": model_name,
                **model_results["metrics"],
                "false_alarms": model_results["confusion_matrix"][0][1],
                "missed_human_windows": model_results["confusion_matrix"][1][0],
                "fit_seconds": model_results["fit_seconds"],
                "predict_seconds": model_results["predict_seconds"],
            }
            for model_name, model_results in results.items()
        ]
    ).to_csv(args.report_dir / "comparison_summary.csv", index=False)
    (args.report_dir / "skipped_files.txt").write_text(
        "\n".join(skipped) if skipped else "Atlanan dosya yok.\n",
        encoding="utf-8",
    )
    joblib.dump(
        trained_models["random_forest"],
        args.model_dir / "rescuer-random-forest.joblib",
    )

    print(json.dumps(payload["models"], indent=2, ensure_ascii=False), flush=True)
    print(
        "Dengeli doğruluk farkı "
        f"(Random Forest - Logistic): {forest_balanced - logistic_balanced:+.4f}",
        flush=True,
    )
    print(f"Rapor: {args.report_dir}", flush=True)
    print("Random Forest modeli models/ altında yerel olarak kaydedildi.", flush=True)


if __name__ == "__main__":
    main()
