"""Rescuer Logistic Regression modeli için karar eşiğini doğrulama verisiyle seçer.

Person 7 ve eğitim tarafındaki iki insan-yok dosyası doğrulama için ayrılır.
Person 8–9 ile önceden ayrılmış insan-yok dosyaları yalnızca son testte kullanılır.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from train_rescuer_baseline import (
    FEATURE_NAMES,
    FileRecord,
    build_feature_table,
    discover_files,
    metric_payload,
    save_clean_svg,
    stable_seed,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Rescuer modeli için doğrulama verisiyle karar eşiği seç"
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--validation-subject", default="Person 7")
    parser.add_argument("--validation-empty-files", type=int, default=2)
    parser.add_argument("--target-recall", type=float, default=0.95)
    parser.add_argument("--window-frames", type=int, default=170)
    parser.add_argument("--max-human-windows", type=int, default=4)
    parser.add_argument("--max-empty-windows", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=project_root / "reports" / "rescuer-threshold-analysis",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=project_root / "assets" / "images" / "model",
    )
    return parser.parse_args()


def assign_validation_split(
    records: list[FileRecord],
    validation_subject: str,
    validation_empty_files: int,
    seed: int,
) -> tuple[list[FileRecord], list[str]]:
    """Mevcut test bölümünü koruyarak eğitim içinden doğrulama dosyaları ayırır."""
    if validation_empty_files < 1:
        raise ValueError("En az bir insan-yok doğrulama dosyası seçilmelidir.")

    subject_records = [
        record
        for record in records
        if record.split == "train" and record.subject == validation_subject
    ]
    if not subject_records:
        raise ValueError(
            f"Doğrulama kişisi eğitim bölümünde bulunamadı: {validation_subject}"
        )

    empty_train = [
        record
        for record in records
        if record.split == "train" and record.label == 0
    ]
    if len(empty_train) <= validation_empty_files:
        raise ValueError("Eğitim için yeterli insan-yok dosyası kalmıyor.")

    ranked_empty = sorted(
        empty_train,
        key=lambda record: stable_seed(record.relative_path, seed),
    )
    validation_empty_paths = {
        record.path for record in ranked_empty[:validation_empty_files]
    }

    updated: list[FileRecord] = []
    for record in records:
        should_validate = (
            record.split == "train"
            and (
                record.subject == validation_subject
                or record.path in validation_empty_paths
            )
        )
        updated.append(replace(record, split="validation") if should_validate else record)

    selected_empty = [
        record.relative_path
        for record in ranked_empty
        if record.path in validation_empty_paths
    ]
    return updated, selected_empty


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


def threshold_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    predictions = (probabilities >= threshold).astype(np.int64)
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    true_empty, false_alarms, missed_human, detected_human = matrix.ravel()
    empty_accuracy = (
        true_empty / (true_empty + false_alarms)
        if true_empty + false_alarms
        else 0.0
    )
    metrics = metric_payload(y_true, predictions)
    return {
        "threshold": float(threshold),
        **metrics,
        "empty_accuracy": float(empty_accuracy),
        "false_alarms": int(false_alarms),
        "missed_human_windows": int(missed_human),
        "detected_human_windows": int(detected_human),
        "confusion_matrix": matrix.tolist(),
    }


def build_threshold_table(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> pd.DataFrame:
    thresholds = np.round(np.arange(0.01, 1.00, 0.01), 2)
    rows = [
        threshold_metrics(y_true, probabilities, float(threshold))
        for threshold in thresholds
    ]
    table = pd.DataFrame(rows)
    return table.drop(columns="confusion_matrix")


def select_threshold(
    candidates: pd.DataFrame,
    target_recall: float,
) -> tuple[float, str]:
    """Hedef yakalamayı sağlayan adaylar içinde yanlış alarmı en aza indirir."""
    eligible = candidates[candidates["recall_human"] >= target_recall].copy()
    if eligible.empty:
        best_recall = candidates["recall_human"].max()
        eligible = candidates[candidates["recall_human"] == best_recall].copy()
        rule = "target_not_reached_maximize_recall_then_minimize_false_alarms"
    else:
        rule = "meet_target_recall_then_minimize_false_alarms"

    selected = eligible.sort_values(
        ["false_alarms", "balanced_accuracy", "threshold"],
        ascending=[True, False, False],
    ).iloc[0]
    return float(selected["threshold"]), rule


def render_threshold_figure(
    candidates: pd.DataFrame,
    selected_threshold: float,
    target_recall: float,
    test_default: dict[str, object],
    test_selected: dict[str, object],
    output_path: Path,
) -> None:
    plt.style.use("dark_background")
    figure, axes = plt.subplots(1, 2, figsize=(14, 6.4))
    figure.patch.set_facecolor("#071426")
    for axis in axes:
        axis.set_facecolor("#0B1F33")

    axes[0].plot(
        candidates["threshold"],
        candidates["recall_human"],
        color="#F59E0B",
        linewidth=2.4,
        label="İnsan yakalama",
    )
    axes[0].plot(
        candidates["threshold"],
        candidates["empty_accuracy"],
        color="#2DD4BF",
        linewidth=2.4,
        label="Boş ortam doğruluğu",
    )
    axes[0].axhline(
        target_recall,
        color="#F59E0B",
        linestyle=":",
        linewidth=1.4,
        label=f"Hedef: %{target_recall * 100:.0f}",
    )
    axes[0].axvline(0.50, color="#94A3B8", linestyle="--", linewidth=1.4)
    axes[0].axvline(
        selected_threshold,
        color="#38BDF8",
        linestyle="--",
        linewidth=2,
    )
    axes[0].annotate(
        f"Doğrulama adayı: {selected_threshold:.2f}",
        (selected_threshold, 0.14),
        xytext=(12, 0),
        textcoords="offset points",
        color="#38BDF8",
        fontweight="bold",
    )
    axes[0].set_xlim(0, 1)
    axes[0].set_ylim(0, 1.03)
    axes[0].set_xlabel("Karar eşiği")
    axes[0].set_ylabel("Oran")
    axes[0].set_title("Doğrulama verisinde eşik dengesi", fontweight="bold")
    axes[0].grid(alpha=0.18)
    axes[0].legend(loc="lower left")

    labels = [
        "Varsayılan\n0,50",
        f"Doğrulama adayı\n{selected_threshold:.2f}".replace(".", ","),
    ]
    human_recall = [
        float(test_default["recall_human"]),
        float(test_selected["recall_human"]),
    ]
    empty_accuracy = [
        float(test_default["empty_accuracy"]),
        float(test_selected["empty_accuracy"]),
    ]
    positions = np.arange(2)
    width = 0.34
    bars_human = axes[1].bar(
        positions - width / 2,
        human_recall,
        width,
        color="#F59E0B",
        label="İnsan yakalama",
    )
    bars_empty = axes[1].bar(
        positions + width / 2,
        empty_accuracy,
        width,
        color="#2DD4BF",
        label="Boş ortam doğruluğu",
    )
    axes[1].set_xticks(positions, labels)
    axes[1].set_ylim(0, 1.04)
    axes[1].set_ylabel("Oran")
    axes[1].set_title("Dokunulmamış testte sonuç", fontweight="bold")
    axes[1].grid(axis="y", alpha=0.18)
    axes[1].legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.22),
        ncol=2,
        frameon=False,
    )
    for bars in (bars_human, bars_empty):
        axes[1].bar_label(bars, labels=[f"%{bar.get_height() * 100:.1f}" for bar in bars])

    axes[1].text(
        0,
        0.08,
        f"Kaçırılan: {test_default['missed_human_windows']}\n"
        f"Yanlış alarm: {test_default['false_alarms']}",
        ha="center",
        color="#CBD5E1",
        bbox={"facecolor": "#071426", "alpha": 0.78, "edgecolor": "none"},
    )
    axes[1].text(
        1,
        0.08,
        f"Kaçırılan: {test_selected['missed_human_windows']}\n"
        f"Yanlış alarm: {test_selected['false_alarms']}",
        ha="center",
        color="#CBD5E1",
        bbox={"facecolor": "#071426", "alpha": 0.78, "edgecolor": "none"},
    )

    figure.suptitle(
        "Rescuer Logistic Regression karar eşiği",
        fontsize=18,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.015,
        "Eşik yalnızca Person 7 doğrulama verisiyle seçildi; Person 8–9 son teste kadar kullanılmadı.",
        ha="center",
        color="#CBD5E1",
    )
    figure.tight_layout(rect=(0, 0.10, 1, 0.94))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_clean_svg(figure, output_path)
    plt.close(figure)


def split_summary(table: pd.DataFrame) -> pd.DataFrame:
    return (
        table.assign(
            class_name=np.where(
                table["label"] == 1,
                "human_present",
                "human_absent",
            )
        )
        .groupby(["split", "class_name"], as_index=False)
        .agg(
            window_count=("label", "size"),
            file_count=("file", "nunique"),
        )
        .sort_values(["split", "class_name"])
    )


def main() -> None:
    args = parse_args()
    if not 0 < args.target_recall <= 1:
        raise ValueError("Hedef insan yakalama oranı 0 ile 1 arasında olmalıdır.")

    records = discover_files(args.data_root.resolve(), args.seed)
    records, validation_empty_files = assign_validation_split(
        records,
        validation_subject=args.validation_subject,
        validation_empty_files=args.validation_empty_files,
        seed=args.seed,
    )
    print(f"{len(records)} genlik dosyası bulundu.", flush=True)

    table, skipped = build_feature_table(
        records=records,
        window_frames=args.window_frames,
        max_human_windows=args.max_human_windows,
        max_empty_windows=args.max_empty_windows,
        seed=args.seed,
    )
    train = table[table["split"] == "train"].copy()
    validation = table[table["split"] == "validation"].copy()
    test = table[table["split"] == "test"].copy()
    for name, split in (
        ("eğitim", train),
        ("doğrulama", validation),
        ("test", test),
    ):
        if set(split["label"]) != {0, 1}:
            raise RuntimeError(f"{name} bölümü iki sınıfı da içermelidir.")

    model = create_logistic_model(args.seed)
    model.fit(
        train[FEATURE_NAMES].to_numpy(dtype=np.float64),
        train["label"].to_numpy(dtype=np.int64),
    )

    validation_y = validation["label"].to_numpy(dtype=np.int64)
    validation_probabilities = model.predict_proba(
        validation[FEATURE_NAMES].to_numpy(dtype=np.float64)
    )[:, 1]
    candidates = build_threshold_table(validation_y, validation_probabilities)
    selected_threshold, selection_rule = select_threshold(
        candidates,
        args.target_recall,
    )

    test_y = test["label"].to_numpy(dtype=np.int64)
    test_probabilities = model.predict_proba(
        test[FEATURE_NAMES].to_numpy(dtype=np.float64)
    )[:, 1]

    validation_default = threshold_metrics(
        validation_y,
        validation_probabilities,
        0.50,
    )
    validation_selected = threshold_metrics(
        validation_y,
        validation_probabilities,
        selected_threshold,
    )
    test_default = threshold_metrics(test_y, test_probabilities, 0.50)
    test_selected = threshold_metrics(
        test_y,
        test_probabilities,
        selected_threshold,
    )

    args.report_dir.mkdir(parents=True, exist_ok=True)
    args.image_dir.mkdir(parents=True, exist_ok=True)
    output_image = args.image_dir / "rescuer-karar-esigi.svg"
    render_threshold_figure(
        candidates,
        selected_threshold,
        args.target_recall,
        test_default,
        test_selected,
        output_image,
    )

    candidates.to_csv(args.report_dir / "threshold_candidates.csv", index=False)
    split_summary(table).to_csv(args.report_dir / "split_summary.csv", index=False)
    (args.report_dir / "skipped_files.txt").write_text(
        "\n".join(skipped) if skipped else "Atlanan dosya yok.\n",
        encoding="utf-8",
    )

    file_counts = Counter((record.split, record.label) for record in records)
    payload = {
        "model": "StandardScaler + LogisticRegression(class_weight='balanced')",
        "task": "validation_based_decision_threshold_selection",
        "random_seed": args.seed,
        "default_threshold": 0.50,
        "selected_threshold": selected_threshold,
        "target_validation_recall": args.target_recall,
        "selection_rule": selection_rule,
        "validation_subject": args.validation_subject,
        "test_subjects": ["Person 8", "Person 9"],
        "validation_empty_files": validation_empty_files,
        "file_counts": {
            split: {
                "human": file_counts[(split, 1)],
                "empty": file_counts[(split, 0)],
            }
            for split in ("train", "validation", "test")
        },
        "window_counts": {
            row["split"]: {}
            for row in split_summary(table).to_dict(orient="records")
        },
        "validation": {
            "default_threshold": validation_default,
            "selected_threshold": validation_selected,
        },
        "untouched_test": {
            "default_threshold": test_default,
            "selected_threshold": test_selected,
        },
        "recommendation": {
            "adopt_selected_threshold": False,
            "current_default_threshold": 0.50,
            "reason": (
                "Doğrulama adayı testte insan yakalamayı artırdı; ancak yanlış "
                "alarm ve dengeli doğruluk belirgin biçimde kötüleşti. Yeni bir "
                "eşik seçmek için test kullanılmamalıdır."
            ),
        },
        "skipped_file_count": len(skipped),
        "limitations": [
            "Karar eşiği yalnızca Person 7 ve iki insan-yok dosyasıyla seçilmiştir.",
            "Aynı dosyadan gelen pencereler bağımsız saha deneyleri değildir.",
            "İnsan-yok kayıtlarının sayısı ve çeşitliliği sınırlıdır.",
            "Gerçek enkaz koşulları Rescuer veri setinde yoktur.",
        ],
    }
    for row in split_summary(table).to_dict(orient="records"):
        payload["window_counts"][row["split"]][row["class_name"]] = int(
            row["window_count"]
        )

    (args.report_dir / "metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    print(f"Eşik adayları: {args.report_dir / 'threshold_candidates.csv'}", flush=True)
    print(f"Görsel: {output_image}", flush=True)


if __name__ == "__main__":
    main()
