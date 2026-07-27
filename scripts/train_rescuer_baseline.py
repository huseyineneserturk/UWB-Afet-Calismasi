"""Rescuer verisiyle açıklanabilir bir insan var/yok başlangıç modeli kurar.

Bu betik yalnızca genlik (abs/amplitude) dosyalarını kullanır. Ham veriyi
değiştirmez; küçük sonuç dosyalarını ve görselleri proje klasörüne yazar.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


FEATURE_NAMES = [
    "Ortalama bağıl değişkenlik",
    "%90 bağıl değişkenlik",
    "En yüksek bağıl değişkenlik",
    "Ortalama bağıl yayılım",
    "%90 bağıl yayılım",
    "Ortalama kare değişimi",
    "%90 kare değişimi",
    "En yüksek kare değişimi",
    "Ortalama hareket enerjisi",
    "%90 hareket enerjisi",
    "Tepe / ortanca değişkenlik",
    "Hareketli menzil oranı",
]


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative_path: str
    label: int
    subject: str
    split: str


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Rescuer verisiyle Logistic Regression başlangıç modeli"
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--window-frames", type=int, default=170)
    parser.add_argument("--max-human-windows", type=int, default=4)
    parser.add_argument("--max-empty-windows", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=project_root / "reports" / "rescuer-baseline",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=project_root / "assets" / "images" / "model",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=project_root / "models" / "rescuer-logistic-regression.joblib",
    )
    return parser.parse_args()


def is_amplitude_file(path: Path) -> bool:
    name = path.name.casefold()
    return ("abs" in name or "amplitude" in name) and "angle" not in name


def stable_seed(text: str, base_seed: int) -> int:
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") ^ base_seed


def discover_files(data_root: Path, seed: int) -> list[FileRecord]:
    paths = sorted(
        (path for path in data_root.rglob("*.csv") if is_amplitude_file(path)),
        key=lambda path: path.as_posix().casefold(),
    )
    if not paths:
        raise FileNotFoundError(f"Genlik CSV dosyası bulunamadı: {data_root}")

    empty_paths = [
        path for path in paths if "No human Presence" in path.relative_to(data_root).parts
    ]
    empty_rng = np.random.default_rng(seed)
    empty_test_count = max(1, round(len(empty_paths) * 0.25))
    empty_test_indices = set(
        empty_rng.choice(len(empty_paths), size=empty_test_count, replace=False).tolist()
    )
    empty_test_paths = {
        path for index, path in enumerate(empty_paths) if index in empty_test_indices
    }

    records: list[FileRecord] = []
    for path in paths:
        relative = path.relative_to(data_root)
        is_empty = "No human Presence" in relative.parts
        label = 0 if is_empty else 1
        subject = "empty"
        if not is_empty:
            subject = next(
                (part for part in relative.parts if part.casefold().startswith("person ")),
                "unknown",
            )
        split = (
            "test"
            if subject in {"Person 8", "Person 9"} or path in empty_test_paths
            else "train"
        )
        records.append(
            FileRecord(
                path=path,
                relative_path=relative.as_posix(),
                label=label,
                subject=subject,
                split=split,
            )
        )
    return records


def read_distance_axis(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        first_row = next(csv.reader(handle))
    axis = np.asarray(first_row, dtype=np.float64)
    if axis.size != 109:
        raise ValueError(f"Beklenen 109 menzil sütunu bulunamadı: {path}")
    return axis


def extract_features(window: np.ndarray) -> np.ndarray:
    if window.ndim != 2 or window.shape[1] != 109:
        raise ValueError(f"Beklenmeyen pencere biçimi: {window.shape}")
    if not np.isfinite(window).all():
        raise ValueError("Pencerede eksik veya sonsuz değer bulundu.")

    baseline = np.median(window, axis=0)
    scale_floor = max(float(np.median(np.abs(baseline))) * 1e-3, 1e-9)
    scale = np.maximum(np.abs(baseline), scale_floor)
    relative = np.clip((window - baseline) / scale, -20.0, 20.0)

    relative_std = np.std(relative, axis=0)
    relative_iqr = np.percentile(relative, 75, axis=0) - np.percentile(
        relative, 25, axis=0
    )
    frame_change = np.mean(np.abs(np.diff(relative, axis=0)), axis=0)
    energy = np.mean(relative**2, axis=0)
    median_std = max(float(np.median(relative_std)), 1e-9)

    return np.asarray(
        [
            np.mean(relative_std),
            np.percentile(relative_std, 90),
            np.max(relative_std),
            np.mean(relative_iqr),
            np.percentile(relative_iqr, 90),
            np.mean(frame_change),
            np.percentile(frame_change, 90),
            np.max(frame_change),
            np.mean(energy),
            np.percentile(energy, 90),
            np.max(relative_std) / median_std,
            np.mean(relative_std > 0.02),
        ],
        dtype=np.float64,
    )


def sample_file_windows(
    record: FileRecord,
    window_frames: int,
    max_windows: int,
    seed: int,
) -> list[np.ndarray]:
    read_distance_axis(record.path)
    rng = np.random.default_rng(stable_seed(record.relative_path, seed))
    reservoir: list[np.ndarray] = []
    seen = 0

    chunks = pd.read_csv(
        record.path,
        header=None,
        skiprows=1,
        chunksize=window_frames,
        dtype=np.float64,
        engine="c",
    )
    for chunk in chunks:
        if len(chunk) != window_frames:
            continue
        values = chunk.to_numpy(dtype=np.float64, copy=False)
        if values.shape[1] != 109 or not np.isfinite(values).all():
            continue
        features = extract_features(values)
        seen += 1
        if len(reservoir) < max_windows:
            reservoir.append(features)
        else:
            replace_index = int(rng.integers(0, seen))
            if replace_index < max_windows:
                reservoir[replace_index] = features
    return reservoir


def build_feature_table(
    records: list[FileRecord],
    window_frames: int,
    max_human_windows: int,
    max_empty_windows: int,
    seed: int,
) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, object]] = []
    skipped: list[str] = []
    total = len(records)

    for index, record in enumerate(records, start=1):
        limit = max_human_windows if record.label == 1 else max_empty_windows
        try:
            windows = sample_file_windows(record, window_frames, limit, seed)
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            skipped.append(f"{record.relative_path}: {exc}")
            continue
        if not windows:
            skipped.append(f"{record.relative_path}: tam pencere üretilemedi")
            continue
        for window_index, features in enumerate(windows):
            row: dict[str, object] = {
                "file": record.relative_path,
                "subject": record.subject,
                "split": record.split,
                "label": record.label,
                "window_index": window_index,
            }
            row.update(dict(zip(FEATURE_NAMES, features, strict=True)))
            rows.append(row)
        if index % 25 == 0 or index == total:
            print(f"[{index:>3}/{total}] dosya işlendi", flush=True)

    table = pd.DataFrame(rows)
    if table.empty:
        raise RuntimeError("Hiç özellik penceresi üretilemedi.")
    return table, skipped


def metric_payload(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision_human": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall_human": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_human": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def save_clean_svg(figure: plt.Figure, output_path: Path) -> None:
    figure.savefig(output_path, format="svg", facecolor=figure.get_facecolor())
    svg_text = output_path.read_text(encoding="utf-8")
    cleaned = "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n"
    output_path.write_text(cleaned, encoding="utf-8")


def render_result_figure(
    metrics: dict[str, float],
    matrix: np.ndarray,
    output_path: Path,
) -> None:
    plt.style.use("dark_background")
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.8))
    figure.patch.set_facecolor("#071426")
    for axis in axes:
        axis.set_facecolor("#0B1F33")

    names = ["Dengeli doğruluk", "İnsan kesinliği", "İnsan yakalama", "F1"]
    values = [
        metrics["balanced_accuracy"],
        metrics["precision_human"],
        metrics["recall_human"],
        metrics["f1_human"],
    ]
    colors = ["#2DD4BF", "#38BDF8", "#F59E0B", "#A78BFA"]
    axes[0].barh(names, values, color=colors)
    axes[0].set_xlim(0, 1)
    axes[0].set_xlabel("Skor")
    axes[0].set_title("Test sonuçları", fontweight="bold")
    axes[0].grid(axis="x", alpha=0.18)
    for row, value in enumerate(values):
        axes[0].text(value + 0.015, row, f"{value:.1%}", va="center")

    image = axes[1].imshow(matrix, cmap="Blues")
    axes[1].set_xticks([0, 1], ["İnsan yok", "İnsan var"])
    axes[1].set_yticks([0, 1], ["İnsan yok", "İnsan var"])
    axes[1].set_xlabel("Model tahmini")
    axes[1].set_ylabel("Gerçek durum")
    axes[1].set_title("Karmaşıklık matrisi", fontweight="bold")
    for row in range(2):
        for column in range(2):
            axes[1].text(
                column,
                row,
                str(int(matrix[row, column])),
                ha="center",
                va="center",
                fontsize=22,
                fontweight="bold",
                color="white" if matrix[row, column] > matrix.max() / 2 else "#0F172A",
            )
    figure.colorbar(image, ax=axes[1], fraction=0.046, pad=0.04)
    figure.suptitle(
        "Rescuer Logistic Regression başlangıç modeli",
        fontsize=17,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.015,
        "Test: eğitimde görülmeyen Person 8–9 ve ayrılmış insan-yok dosyaları",
        ha="center",
        color="#CBD5E1",
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.94))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_clean_svg(figure, output_path)
    plt.close(figure)


def render_coefficient_figure(
    pipeline: Pipeline,
    output_path: Path,
) -> list[dict[str, float | str]]:
    model = pipeline.named_steps["model"]
    coefficients = model.coef_[0]
    order = np.argsort(np.abs(coefficients))
    ordered_names = [FEATURE_NAMES[index] for index in order]
    ordered_values = coefficients[order]
    colors = ["#2DD4BF" if value >= 0 else "#F59E0B" for value in ordered_values]

    plt.style.use("dark_background")
    figure, axis = plt.subplots(figsize=(10.5, 6.8))
    figure.patch.set_facecolor("#071426")
    axis.set_facecolor("#0B1F33")
    axis.barh(ordered_names, ordered_values, color=colors)
    axis.axvline(0, color="#CBD5E1", linewidth=1)
    axis.set_xlabel("Standartlaştırılmış model katsayısı")
    axis.set_title(
        "Model kararını en çok etkileyen özellikler",
        fontsize=15,
        fontweight="bold",
    )
    axis.grid(axis="x", alpha=0.18)
    figure.text(
        0.5,
        0.015,
        "Turkuaz insan var, turuncu insan yok yönündeki etkiyi gösterir.",
        ha="center",
        color="#CBD5E1",
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.96))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_clean_svg(figure, output_path)
    plt.close(figure)

    return [
        {"feature": FEATURE_NAMES[index], "coefficient": float(coefficients[index])}
        for index in np.argsort(np.abs(coefficients))[::-1]
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

    pipeline = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2_000,
                    random_state=args.seed,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    metrics = metric_payload(y_test, predictions)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])

    args.report_dir.mkdir(parents=True, exist_ok=True)
    args.image_dir.mkdir(parents=True, exist_ok=True)
    args.model_output.parent.mkdir(parents=True, exist_ok=True)

    result_image = args.image_dir / "rescuer-baseline-sonuclari.svg"
    coefficient_image = args.image_dir / "rescuer-baseline-katsayilari.svg"
    render_result_figure(metrics, matrix, result_image)
    coefficients = render_coefficient_figure(pipeline, coefficient_image)

    file_counts = Counter((record.split, record.label) for record in records)
    window_counts = Counter(zip(table["split"], table["label"]))
    payload = {
        "model": "StandardScaler + LogisticRegression(class_weight='balanced')",
        "task": "human_presence_binary_classification",
        "representation": "amplitude_only",
        "sampling_rate_hz": 17.0,
        "window_frames": args.window_frames,
        "window_seconds": args.window_frames / 17.0,
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
        "metrics": metrics,
        "confusion_matrix": {
            "labels": ["human_absent", "human_present"],
            "values": matrix.tolist(),
        },
        "coefficients_by_absolute_importance": coefficients,
        "skipped_file_count": len(skipped),
        "limitations": [
            "Sonuçlar pencere düzeyindedir; bağımsız saha deneyi değildir.",
            "İnsan-yok sınıfı yalnızca 12 kaynak dosyadan gelir.",
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
                "split": split,
                "label": "human_present" if label == 1 else "human_absent",
                "file_count": file_counts[(split, label)],
                "window_count": window_counts[(split, label)],
            }
            for split in ("train", "test")
            for label in (0, 1)
        ]
    ).to_csv(args.report_dir / "split_summary.csv", index=False)
    (args.report_dir / "skipped_files.txt").write_text(
        "\n".join(skipped) if skipped else "Atlanan dosya yok.\n",
        encoding="utf-8",
    )
    joblib.dump(pipeline, args.model_output)

    print(json.dumps(payload["metrics"], indent=2), flush=True)
    print(f"Karmaşıklık matrisi: {matrix.tolist()}", flush=True)
    print(f"Rapor: {args.report_dir}", flush=True)
    print(f"Model (Git'e eklenmez): {args.model_output}", flush=True)


if __name__ == "__main__":
    main()
