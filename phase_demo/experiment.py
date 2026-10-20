import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from .core import generate_fringes, recover_phase, unwrap_phase


def _save_figure(path, name, first_frame, wrapped, aligned, error, rmse):
    figure, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    error_limit = max(float(np.max(np.abs(error))), 1e-8)
    panels = [
        (first_frame, "First synthetic fringe", "gray", 0, 1, "Intensity"),
        (wrapped, "Wrapped phase", "twilight", -np.pi, np.pi, "Phase [rad]"),
        (aligned, "Unwrapped phase (whole-turn aligned)", "viridis", 0, 4 * np.pi, "Phase [rad]"),
        (error, "Error relative to synthetic truth", "coolwarm", -error_limit, error_limit, "Error [rad]"),
    ]
    for axis, (data, title, cmap, low, high, label) in zip(axes.flat, panels):
        image = axis.imshow(data, origin="lower", cmap=cmap, vmin=low, vmax=high)
        axis.set(title=title, xlabel="x [pixel]", ylabel="y [pixel]")
        figure.colorbar(image, ax=axis, label=label, shrink=0.8)
    figure.suptitle(f"{name}: synthetic experiment | phase RMSE = {rmse:.4g} rad")
    figure.savefig(path, dpi=140)
    plt.close(figure)


def run_experiment(output, n_steps=5, seed=0):
    """Write three PNG figures and report.json; existing output files are replaced."""
    y, x = np.mgrid[0:64, 0:96]
    x = x / 95
    y = y / 63
    truth = 4 * np.pi * x + 0.6 * np.sin(2 * np.pi * y) * np.sin(np.pi * x)
    scenarios = [
        ("clean", 0.0, 0.0),
        ("noise", 0.02, 0.0),
        ("drift", 0.0, 0.08),
    ]
    output = Path(output)
    results = []
    for name, noise_std, phase_drift in scenarios:
        images = generate_fringes(
            truth, n_steps, noise_std=noise_std, phase_drift=phase_drift, seed=seed
        )
        wrapped, modulation = recover_phase(images)
        unwrapped = unwrap_phase(wrapped)
        # Truth is used only for evaluation: remove a global integer-turn ambiguity.
        turns = int(np.rint(np.mean((truth - unwrapped) / (2 * np.pi))))
        aligned = unwrapped + turns * 2 * np.pi
        error = aligned - truth
        circular_error = np.arctan2(np.sin(wrapped - truth), np.cos(wrapped - truth))
        rmse = float(np.sqrt(np.mean(error**2)))
        result = {
            "scenario": name,
            "noise_std": noise_std,
            "phase_drift_rad_per_frame": phase_drift,
            "whole_turns_added_for_evaluation": turns,
            "wrapped_rmse_rad": float(np.sqrt(np.mean(circular_error**2))),
            "unwrapped_rmse_rad": rmse,
            "max_abs_error_rad": float(np.max(np.abs(error))),
            "min_modulation": float(np.min(modulation)),
            "figure": f"{name}.png",
        }
        output.mkdir(parents=True, exist_ok=True)
        _save_figure(output / result["figure"], name, images[0], wrapped, aligned, error, rmse)
        results.append(result)
    report = {
        "data": "synthetic only",
        "n_steps": n_steps,
        "shape": list(truth.shape),
        "seed": seed,
        "background": 0.5,
        "amplitude": 0.4,
        "results": results,
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description="Run synthetic N-step phase-shifting experiments.")
    parser.add_argument("--output", type=Path, default=Path("out"))
    parser.add_argument("--steps", type=int, default=5, help="number of phase steps, at least 3")
    parser.add_argument("--seed", type=int, default=0, help="nonnegative random seed")
    args = parser.parse_args()
    if args.steps < 3 or args.seed < 0:
        parser.error("--steps must be at least 3 and --seed must be nonnegative")
    try:
        report = run_experiment(args.output, args.steps, args.seed)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0
