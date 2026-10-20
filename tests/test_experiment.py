import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from phase_demo.experiment import align_for_evaluation

ROOT = Path(__file__).resolve().parents[1]


def test_evaluation_restores_a_nonzero_global_turn_offset():
    truth = np.array([[7.0, 7.2], [7.1, 7.3]])
    unwrapped = truth - 4 * np.pi
    aligned, turns = align_for_evaluation(unwrapped, truth)
    assert turns == 2
    np.testing.assert_allclose(aligned, truth, atol=1e-12)


def test_cli_writes_figures_and_distinguishes_clean_noise_and_drift(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "phase_demo", "--output", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert json.loads(result.stdout) == report
    cases = {case["scenario"]: case for case in report["results"]}
    clean, noise, drift = [cases[name]["unwrapped_rmse_rad"] for name in ("clean", "noise", "drift")]
    assert clean < 1e-12
    assert 0.02 < noise < 0.06
    assert noise < drift < 0.3
    for case in cases.values():
        assert (tmp_path / case["figure"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_cli_rejects_two_steps_without_creating_output(tmp_path):
    output = tmp_path / "invalid"
    result = subprocess.run(
        [sys.executable, "-m", "phase_demo", "--steps", "2", "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 2
    assert "--steps must be at least 3" in result.stderr
    assert not output.exists()
