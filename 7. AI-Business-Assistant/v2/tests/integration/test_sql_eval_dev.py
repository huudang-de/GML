"""Integration tests for SQL Evaluation Harness, Dev Benchmark, and Evidence Generation.

Specifications:
- Spec §5 T8 / TC-T8-01 (Deterministic Evaluation & EV-07 / EV-08 Generation)
- Spec §5 T8 / TC-T8-02 (Locked Test Split Protection)
"""

from pathlib import Path
import pytest

from eval.run_eval import run_sql_evaluation


def test_tc_t8_02_test_split_locked_without_final_flag():
    """TC-T8-02: Evaluating split='test' without --final must raise PermissionError."""
    with pytest.raises(PermissionError) as exc_info:
        run_sql_evaluation(split="test", final=False)

    assert "TC-T8-02" in str(exc_info.value)
    assert "locked" in str(exc_info.value).lower()


def test_tc_t8_01_eval_harness_deterministic_and_generates_ev07_ev08(tmp_path: Path):
    """TC-T8-01: Deterministic offline evaluation runs with heuristic client, producing identical metrics and evidence."""
    # First run
    run1 = run_sql_evaluation(
        split="dev",
        final=False,
        provider="heuristic",
        output_dir=tmp_path,
    )

    # Second run
    run2 = run_sql_evaluation(
        split="dev",
        final=False,
        provider="heuristic",
        output_dir=tmp_path,
    )

    # Determinism assertion: metric results must be strictly identical across runs
    assert run1["m06_execution_accuracy"] == run2["m06_execution_accuracy"]
    assert run1["m07_valid_sql_rate"] == run2["m07_valid_sql_rate"]
    assert run1["total_evaluated"] == run2["total_evaluated"]
    assert run1["m07_valid_sql_rate"] >= 0.90

    # Evidence EV-07 verification: sql_accuracy.md
    report_file = tmp_path / "sql_accuracy.md"
    assert report_file.exists(), "EV-07 sql_accuracy.md was not generated"
    report_text = report_file.read_text(encoding="utf-8")

    assert "M-06" in report_text or "Execution Accuracy" in report_text
    assert "M-07" in report_text or "Valid SQL Rate" in report_text
    assert "de" in report_text.lower()
    assert "vua" in report_text.lower()
    assert "kho" in report_text.lower()
    assert "D1" in report_text
    assert "commit" in report_text.lower()
    assert "heuristic" in report_text.lower()

    # Evidence EV-08 verification: calibration.png
    calib_file = tmp_path / "calibration.png"
    assert calib_file.exists(), "EV-08 calibration.png was not generated"
    png_bytes = calib_file.read_bytes()
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "File is not a valid PNG image"
    assert len(png_bytes) > 2048, f"Calibration plot too small: {len(png_bytes)} bytes"
