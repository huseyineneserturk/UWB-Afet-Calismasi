"""Rescuer veri setinden başlangıç seviyesine uygun örnek sinyal grafiği üretir."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


HUMAN_FILE = Path(
    "Human Presence/Person 1/No Obstacle/0.2m/2 facing radar abs.csv"
)
EMPTY_FILE = Path(
    "No human Presence/No Movement/Abs/clean amplitude NoPresence Lab_15mins.csv"
)


def read_window(path: Path, frame_count: int) -> tuple[list[float], list[list[float]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.reader(handle)
        distance_axis = [float(value) for value in next(rows)]
        frames: list[list[float]] = []
        for index, row in enumerate(rows):
            if index >= frame_count:
                break
            frames.append([float(value) for value in row])
    return distance_axis, frames


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def standard_deviation(values: list[float]) -> float:
    average = mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * ratio)
    return ordered[index]


def moving_average(values: list[float], width: int = 5) -> list[float]:
    smoothed: list[float] = []
    for index in range(len(values)):
        start = max(0, index - width + 1)
        smoothed.append(mean(values[start : index + 1]))
    return smoothed


def relative_change(values: list[float]) -> list[float]:
    baseline = percentile(values, 0.5)
    return [100 * (value - baseline) / baseline for value in values]


def variability_profile(frames: list[list[float]]) -> list[float]:
    profile: list[float] = []
    for column in zip(*frames):
        values = list(column)
        average = abs(mean(values))
        profile.append(100 * standard_deviation(values) / max(average, 1e-12))
    return profile


def polyline(
    values: list[float],
    left: float,
    top: float,
    width: float,
    height: float,
    minimum: float,
    maximum: float,
) -> str:
    span = max(maximum - minimum, 1e-12)
    points = []
    for index, value in enumerate(values):
        x = left + width * index / max(len(values) - 1, 1)
        y = top + height * (maximum - value) / span
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def render_svg(
    output_path: Path,
    distance_axis: list[float],
    human_frames: list[list[float]],
    empty_frames: list[list[float]],
    sampling_rate: float,
    target_distance: float,
) -> None:
    target_index = min(
        range(len(distance_axis)),
        key=lambda index: abs(distance_axis[index] - target_distance),
    )
    actual_distance = distance_axis[target_index]

    human_raw = [frame[target_index] for frame in human_frames]
    empty_raw = [frame[target_index] for frame in empty_frames]
    human_trace = moving_average(relative_change(human_raw))
    empty_trace = moving_average(relative_change(empty_raw))

    human_cv = 100 * standard_deviation(human_raw) / abs(mean(human_raw))
    empty_cv = 100 * standard_deviation(empty_raw) / abs(mean(empty_raw))

    human_profile = variability_profile(human_frames)
    empty_profile = variability_profile(empty_frames)

    trace_limit = max(
        5.0,
        percentile([abs(value) for value in human_trace + empty_trace], 0.99),
    )
    trace_limit = math.ceil(trace_limit / 5) * 5
    profile_limit = max(
        5.0,
        percentile(human_profile + empty_profile, 0.95),
    )
    profile_limit = math.ceil(profile_limit / 5) * 5

    duration = len(human_trace) / sampling_rate
    trace_left, trace_top, trace_width, trace_height = 92, 182, 885, 245
    profile_left, profile_top, profile_width, profile_height = 92, 545, 885, 175

    human_trace_points = polyline(
        human_trace,
        trace_left,
        trace_top,
        trace_width,
        trace_height,
        -trace_limit,
        trace_limit,
    )
    empty_trace_points = polyline(
        empty_trace,
        trace_left,
        trace_top,
        trace_width,
        trace_height,
        -trace_limit,
        trace_limit,
    )
    human_profile_points = polyline(
        human_profile,
        profile_left,
        profile_top,
        profile_width,
        profile_height,
        0,
        profile_limit,
    )
    empty_profile_points = polyline(
        empty_profile,
        profile_left,
        profile_top,
        profile_width,
        profile_height,
        0,
        profile_limit,
    )

    time_ticks = []
    for seconds in (0, 5, 10, 15, 20):
        x = trace_left + trace_width * seconds / duration
        time_ticks.append(
            f'<line x1="{x:.1f}" y1="{trace_top}" x2="{x:.1f}" '
            f'y2="{trace_top + trace_height}" class="grid"/>'
            f'<text x="{x:.1f}" y="{trace_top + trace_height + 28}" '
            f'class="tick" text-anchor="middle">{seconds} sn</text>'
        )

    distance_ticks = []
    minimum_distance, maximum_distance = distance_axis[0], distance_axis[-1]
    for distance in (0.5, 1, 2, 3, 4, 5, 6):
        x = profile_left + profile_width * (
            (distance - minimum_distance) / (maximum_distance - minimum_distance)
        )
        distance_ticks.append(
            f'<line x1="{x:.1f}" y1="{profile_top}" x2="{x:.1f}" '
            f'y2="{profile_top + profile_height}" class="grid"/>'
            f'<text x="{x:.1f}" y="{profile_top + profile_height + 28}" '
            f'class="tick" text-anchor="middle">{distance:g} m</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="820" viewBox="0 0 1400 820" role="img" aria-labelledby="title desc">
  <title id="title">Rescuer insan var ve yok örnek sinyal karşılaştırması</title>
  <desc id="desc">Gerçek Rescuer genlik kayıtlarından 20 saniyelik örnek pencere ve menzil değişkenliği karşılaştırması</desc>
  <style>
    .title {{ font: 700 34px "Segoe UI", Arial, sans-serif; fill: #F8FAFC; }}
    .subtitle {{ font: 400 18px "Segoe UI", Arial, sans-serif; fill: #94A3B8; }}
    .section {{ font: 700 20px "Segoe UI", Arial, sans-serif; fill: #E2E8F0; }}
    .label {{ font: 600 16px "Segoe UI", Arial, sans-serif; fill: #CBD5E1; }}
    .tick {{ font: 400 13px "Segoe UI", Arial, sans-serif; fill: #94A3B8; }}
    .card-title {{ font: 700 15px "Segoe UI", Arial, sans-serif; fill: #5EEAD4; letter-spacing: 1px; }}
    .card-value {{ font: 750 32px "Segoe UI", Arial, sans-serif; fill: #F8FAFC; }}
    .card-note {{ font: 400 14px "Segoe UI", Arial, sans-serif; fill: #CBD5E1; }}
    .grid {{ stroke: #244055; stroke-width: 1; }}
  </style>
  <rect width="1400" height="820" rx="24" fill="#071426"/>
  <rect x="35" y="35" width="1330" height="750" rx="20" fill="#0B1F33" stroke="#1E3A4D"/>

  <text x="76" y="93" class="title">Rescuer: İnsan var / yok örnek sinyal karşılaştırması</text>
  <text x="76" y="125" class="subtitle">Gerçek genlik kayıtları • {duration:.0f} saniyelik pencere • Yaklaşık {actual_distance:.2f} m menzil kutusu</text>

  <text x="92" y="164" class="section">Zaman içinde bağıl genlik değişimi</text>
  <line x1="{trace_left}" y1="{trace_top + trace_height / 2:.1f}" x2="{trace_left + trace_width}" y2="{trace_top + trace_height / 2:.1f}" class="grid"/>
  <line x1="{trace_left}" y1="{trace_top}" x2="{trace_left + trace_width}" y2="{trace_top}" class="grid"/>
  <line x1="{trace_left}" y1="{trace_top + trace_height}" x2="{trace_left + trace_width}" y2="{trace_top + trace_height}" class="grid"/>
  {''.join(time_ticks)}
  <text x="78" y="{trace_top + 8}" class="tick" text-anchor="end">+{trace_limit:.0f}%</text>
  <text x="78" y="{trace_top + trace_height / 2 + 5:.1f}" class="tick" text-anchor="end">0%</text>
  <text x="78" y="{trace_top + trace_height + 5}" class="tick" text-anchor="end">−{trace_limit:.0f}%</text>
  <polyline points="{human_trace_points}" fill="none" stroke="#2DD4BF" stroke-width="3"/>
  <polyline points="{empty_trace_points}" fill="none" stroke="#F59E0B" stroke-width="2.5" opacity="0.92"/>
  <line x1="720" y1="153" x2="754" y2="153" stroke="#2DD4BF" stroke-width="4"/>
  <text x="764" y="159" class="label">İnsan var</text>
  <line x1="855" y1="153" x2="889" y2="153" stroke="#F59E0B" stroke-width="4"/>
  <text x="899" y="159" class="label">İnsan yok</text>

  <text x="92" y="520" class="section">Menzile göre bağıl değişkenlik</text>
  <line x1="{profile_left}" y1="{profile_top}" x2="{profile_left + profile_width}" y2="{profile_top}" class="grid"/>
  <line x1="{profile_left}" y1="{profile_top + profile_height}" x2="{profile_left + profile_width}" y2="{profile_top + profile_height}" class="grid"/>
  {''.join(distance_ticks)}
  <text x="78" y="{profile_top + 5}" class="tick" text-anchor="end">{profile_limit:.0f}%</text>
  <text x="78" y="{profile_top + profile_height + 5}" class="tick" text-anchor="end">0%</text>
  <polyline points="{human_profile_points}" fill="none" stroke="#2DD4BF" stroke-width="3"/>
  <polyline points="{empty_profile_points}" fill="none" stroke="#F59E0B" stroke-width="2.5" opacity="0.92"/>

  <rect x="1025" y="172" width="290" height="135" rx="16" fill="#102A3D" stroke="#1B5360"/>
  <text x="1050" y="207" class="card-title">İNSAN VAR • ÖRNEK</text>
  <text x="1050" y="251" class="card-value">{human_cv:.1f}%</text>
  <text x="1050" y="280" class="card-note">bağıl değişkenlik (σ / ortalama)</text>

  <rect x="1025" y="327" width="290" height="135" rx="16" fill="#102A3D" stroke="#6B4E17"/>
  <text x="1050" y="362" class="card-title" style="fill:#FBBF24">İNSAN YOK • ÖRNEK</text>
  <text x="1050" y="406" class="card-value">{empty_cv:.1f}%</text>
  <text x="1050" y="435" class="card-note">bağıl değişkenlik (σ / ortalama)</text>

  <rect x="1025" y="496" width="290" height="224" rx="16" fill="#0D2436" stroke="#244055"/>
  <text x="1050" y="533" class="card-title">NASIL OKUNMALI?</text>
  <text x="1050" y="568" class="card-note">• Sabit seviye çıkarıldı.</text>
  <text x="1050" y="596" class="card-note">• Çizgiler 5 kareyle yumuşatıldı.</text>
  <text x="1050" y="624" class="card-note">• Bu yalnızca tek bir örnektir.</text>
  <text x="1050" y="652" class="card-note">• Bir model sonucu değildir.</text>
  <text x="1050" y="690" class="card-note" style="fill:#FBBF24">Fark görmek ≠ kesin insan tespiti</text>

  <text x="76" y="764" class="tick">Kaynak: Yerel Rescuer veri seti • Person 1 / No Obstacle / 0.2m / 2 facing radar abs.csv</text>
</svg>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/images/rescuer/rescuer-sinyal-karsilastirmasi.svg"),
    )
    parser.add_argument("--frames", type=int, default=340)
    parser.add_argument("--sampling-rate", type=float, default=17.0)
    parser.add_argument("--target-distance", type=float, default=2.0)
    args = parser.parse_args()

    human_axis, human_frames = read_window(
        args.data_root / HUMAN_FILE, args.frames
    )
    empty_axis, empty_frames = read_window(
        args.data_root / EMPTY_FILE, args.frames
    )
    if human_axis != empty_axis:
        raise ValueError("İki örneğin menzil eksenleri aynı değil.")

    render_svg(
        args.output,
        human_axis,
        human_frames,
        empty_frames,
        args.sampling_rate,
        args.target_distance,
    )
    print(args.output.as_posix())


if __name__ == "__main__":
    main()
