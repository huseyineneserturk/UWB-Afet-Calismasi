"""Rescuer Logistic Regression test hatalarını deney koşullarına göre inceler."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
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


ORIENTATION_ORDER = [
    "facing_up",
    "facing_down",
    "facing_radar",
    "not_facing_radar",
]

DISPLAY_LABELS = {
    "wall": "Duvarlı",
    "no_obstacle": "Duvarsız",
    "facing_up": "Yukarı bakıyor",
    "facing_down": "Aşağı bakıyor",
    "facing_radar": "Radara dönük",
    "not_facing_radar": "Radara dönük değil",
    "Person 8": "Person 8",
    "Person 9": "Person 9",
}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Rescuer başlangıç modelinin koşul bazlı hata analizi"
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--window-frames", type=int, default=170)
    parser.add_argument("--max-human-windows", type=int, default=4)
    parser.add_argument("--max-empty-windows", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=project_root / "reports" / "rescuer-error-analysis",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=project_root / "assets" / "images" / "model",
    )
    return parser.parse_args()


def parse_human_metadata(relative_path: str) -> dict[str, object]:
    path = PurePosixPath(relative_path)
    parts = path.parts
    filename = path.name.casefold()

    subject = next(
        (part for part in parts if part.casefold().startswith("person ")),
        "unknown",
    )
    obstacle = "wall" if "Wall Obstacle" in parts else "no_obstacle"
    distance_match = re.match(r"^(\d+(?:\.\d+)?)\s+", filename)
    distance = float(distance_match.group(1)) if distance_match else np.nan

    if "not facing radar" in filename:
        orientation = "not_facing_radar"
    elif "facing radar" in filename:
        orientation = "facing_radar"
    elif "facing up" in filename:
        orientation = "facing_up"
    elif "facing down" in filename:
        orientation = "facing_down"
    else:
        orientation = "unknown"

    return {
        "subject_condition": subject,
        "obstacle": obstacle,
        "target_distance_m": distance,
        "orientation": orientation,
        "radar_placement": parts[-2] if len(parts) >= 2 else "unknown",
    }


def create_logistic_model(seed: int) -> Pipeline:
    return Pipeline(
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
    )


def summarize_condition(
    human_test: pd.DataFrame,
    column: str,
    order: list[object] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    grouped = human_test.groupby(column, dropna=False)
    for value, group in grouped:
        windows = len(group)
        detected = int(group["prediction"].sum())
        rows.append(
            {
                "dimension": column,
                "group_value": value,
                "window_count": windows,
                "detected_count": detected,
                "missed_count": windows - detected,
                "recall": detected / windows,
                "mean_human_probability": float(group["human_probability"].mean()),
            }
        )
    summary = pd.DataFrame(rows)
    if order is None:
        return summary.sort_values("group_value").reset_index(drop=True)
    order_map = {str(value): index for index, value in enumerate(order)}
    summary["_order"] = summary["group_value"].astype(str).map(order_map).fillna(999)
    return (
        summary.sort_values(["_order", "group_value"])
        .drop(columns="_order")
        .reset_index(drop=True)
    )


def render_error_analysis(
    summaries: dict[str, pd.DataFrame],
    overall_recall: float,
    output_path: Path,
) -> None:
    plt.style.use("dark_background")
    figure, axes = plt.subplots(2, 2, figsize=(14, 9))
    figure.patch.set_facecolor("#071426")
    for axis in axes.flat:
        axis.set_facecolor("#0B1F33")

    def render_bars(
        axis: plt.Axes,
        summary: pd.DataFrame,
        title: str,
    ) -> None:
        labels = [
            DISPLAY_LABELS.get(str(value), str(value))
            for value in summary["group_value"]
        ]
        values = summary["recall"].to_numpy()
        counts = summary["window_count"].to_numpy()
        colors = ["#2DD4BF" if value >= overall_recall else "#F59E0B" for value in values]
        positions = np.arange(len(labels))
        axis.barh(positions, values, color=colors)
        axis.set_yticks(positions, labels)
        axis.set_xlim(0, 1.05)
        axis.set_xlabel("İnsan yakalama oranı")
        axis.set_title(title, fontweight="bold")
        axis.axvline(overall_recall, color="#94A3B8", linestyle="--", linewidth=1.4)
        axis.grid(axis="x", alpha=0.18)
        for row, (value, count) in enumerate(zip(values, counts, strict=True)):
            axis.text(
                value + 0.015,
                row,
                f"{value:.1%} • n={count}",
                va="center",
                fontsize=9,
            )

    render_bars(axes[0, 0], summaries["obstacle"], "Engel koşulu")
    render_bars(axes[0, 1], summaries["orientation"], "Kişinin yönü")
    render_bars(axes[1, 0], summaries["subject_condition"], "Test kişisi")

    distance = summaries["target_distance_m"].copy()
    distance["group_value"] = pd.to_numeric(distance["group_value"])
    distance = distance.sort_values("group_value")
    axes[1, 1].plot(
        distance["group_value"],
        distance["recall"],
        color="#38BDF8",
        marker="o",
        linewidth=2.4,
    )
    axes[1, 1].axhline(
        overall_recall,
        color="#94A3B8",
        linestyle="--",
        linewidth=1.4,
    )
    axes[1, 1].set_ylim(0, 1.05)
    axes[1, 1].set_xlabel("Hedef mesafesi (m)")
    axes[1, 1].set_ylabel("İnsan yakalama oranı")
    axes[1, 1].set_title("Hedef mesafesi", fontweight="bold")
    axes[1, 1].grid(alpha=0.18)
    for _, row in distance.iterrows():
        axes[1, 1].annotate(
            f"{row['recall']:.0%}\nn={int(row['window_count'])}",
            (row["group_value"], row["recall"]),
            textcoords="offset points",
            xytext=(0, 9),
            ha="center",
            fontsize=8,
        )

    figure.suptitle(
        "Rescuer Logistic Regression hata analizi",
        fontsize=18,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.015,
        f"Kesikli çizgi genel insan yakalama oranını gösterir: {overall_recall:.1%}",
        ha="center",
        color="#CBD5E1",
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.95))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_clean_svg(figure, output_path)
    plt.close(figure)


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

    x_train = train[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y_train = train["label"].to_numpy(dtype=np.int64)
    x_test = test[FEATURE_NAMES].to_numpy(dtype=np.float64)
    y_test = test["label"].to_numpy(dtype=np.int64)
    model = create_logistic_model(args.seed)
    model.fit(x_train, y_train)
    test["prediction"] = model.predict(x_test)
    test["human_probability"] = model.predict_proba(x_test)[:, 1]

    overall_metrics = metric_payload(y_test, test["prediction"].to_numpy())
    human_test = test[test["label"] == 1].copy()
    metadata = human_test["file"].apply(parse_human_metadata).apply(pd.Series)
    human_test = pd.concat(
        [human_test.reset_index(drop=True), metadata.reset_index(drop=True)],
        axis=1,
    )
    if human_test["target_distance_m"].isna().any():
        raise ValueError("Bazı test dosyalarında hedef mesafesi okunamadı.")
    if (human_test["orientation"] == "unknown").any():
        raise ValueError("Bazı test dosyalarında kişi yönü okunamadı.")

    summaries = {
        "obstacle": summarize_condition(
            human_test, "obstacle", ["no_obstacle", "wall"]
        ),
        "orientation": summarize_condition(
            human_test, "orientation", ORIENTATION_ORDER
        ),
        "subject_condition": summarize_condition(
            human_test, "subject_condition", ["Person 8", "Person 9"]
        ),
        "target_distance_m": summarize_condition(
            human_test,
            "target_distance_m",
            sorted(human_test["target_distance_m"].unique()),
        ),
    }

    args.report_dir.mkdir(parents=True, exist_ok=True)
    args.image_dir.mkdir(parents=True, exist_ok=True)
    output_image = args.image_dir / "rescuer-hata-analizi-kosullar.svg"
    render_error_analysis(
        summaries,
        overall_metrics["recall_human"],
        output_image,
    )

    condition_summary = pd.concat(summaries.values(), ignore_index=True)
    condition_summary.to_csv(args.report_dir / "condition_summary.csv", index=False)

    file_summary = (
        human_test.groupby(
            [
                "file",
                "subject_condition",
                "obstacle",
                "target_distance_m",
                "orientation",
                "radar_placement",
            ],
            as_index=False,
        )
        .agg(
            window_count=("prediction", "size"),
            detected_count=("prediction", "sum"),
            mean_human_probability=("human_probability", "mean"),
        )
    )
    file_summary["missed_count"] = (
        file_summary["window_count"] - file_summary["detected_count"]
    )
    file_summary["recall"] = (
        file_summary["detected_count"] / file_summary["window_count"]
    )
    file_summary = file_summary.sort_values(
        ["missed_count", "mean_human_probability"],
        ascending=[False, True],
    )
    file_summary.to_csv(args.report_dir / "human_file_errors.csv", index=False)

    empty_test = test[test["label"] == 0]
    false_alarms = int(empty_test["prediction"].sum())
    payload = {
        "model": "StandardScaler + LogisticRegression(class_weight='balanced')",
        "analysis_rule": "same_baseline_model_same_test_split",
        "test_subjects": ["Person 8", "Person 9"],
        "test_windows": {
            "human": len(human_test),
            "empty": len(empty_test),
        },
        "overall_metrics": overall_metrics,
        "false_alarms": false_alarms,
        "missed_human_windows": int(
            len(human_test) - human_test["prediction"].sum()
        ),
        "condition_summaries": {
            dimension: frame.to_dict(orient="records")
            for dimension, frame in summaries.items()
        },
        "skipped_file_count": len(skipped),
        "confounding_notes": [
            "Person 8 test kayıtlarının tamamı duvarlıdır.",
            "Person 9 duvarlı ve duvarsız kayıtlarında radar yerleşimleri farklıdır.",
            "Duvar sonuçları duvarın tek başına nedensel etkisi olarak yorumlanamaz.",
        ],
        "limitations": [
            "Sonuçlar yalnızca Person 8 ve Person 9 test pencerelerini kapsar.",
            "Bazı koşullarda pencere sayısı düşüktür.",
            "Aynı dosyadan gelen pencereler bağımsız saha deneyleri değildir.",
            "Gerçek enkaz koşulları Rescuer veri setinde yoktur.",
        ],
    }
    (args.report_dir / "metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.report_dir / "skipped_files.txt").write_text(
        "\n".join(skipped) if skipped else "Atlanan dosya yok.\n",
        encoding="utf-8",
    )

    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    print(f"Koşul özeti: {args.report_dir / 'condition_summary.csv'}", flush=True)
    print(f"Görsel: {output_image}", flush=True)


if __name__ == "__main__":
    main()
