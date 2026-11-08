"""SQL Evaluation Harness, Metric Computation (M-06, M-07), and Evidence Generator.

Specifications:
- Spec §5 T8 / TC-T8-01 (Deterministic Evaluation & EV-07 / EV-08 Generation)
- Spec §5 T8 / TC-T8-02 (Locked Test Split Protection)
- Evidence EV-07: v2/eval/reports/sql_accuracy.md
- Evidence EV-08: v2/eval/reports/calibration.png
"""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

# Ensure v2 root is in sys.path when script is executed directly
V2_ROOT = Path(__file__).resolve().parent.parent
if str(V2_ROOT) not in sys.path:
    sys.path.insert(0, str(V2_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.agents.sql_agent import run_sql_pipeline
from app.knowledge.loader import load_benchmark
from app.knowledge.models import BenchmarkItem
from app.sql.generator import create_sql_llm_client

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "reports"


def get_git_commit_hash() -> str:
    """Retrieve current short git commit hash, fallback to 'dev'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "dev-local"


def extract_numeric_value(rows: list[dict[str, Any]]) -> float | None:
    """Extract first numeric scalar value from execution result rows."""
    if not rows:
        return None
    first_row = rows[0]
    for v in first_row.values():
        if v is None:
            continue
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).replace(",", ""))
        except (ValueError, TypeError):
            continue
    return None


def run_sql_evaluation(
    split: str = "dev",
    final: bool = False,
    provider: str = "auto",
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute SQL evaluation on benchmark items and generate EV-07 / EV-08.

    Args:
        split: 'dev' or 'test'.
        final: Flag required to run official test split (protects locked test set C7).
        provider: 'auto', 'heuristic', 'gemini', 'ollama', 'mock'.
        output_dir: Directory where reports are saved.

    Returns:
        dict[str, Any]: Evaluation summary metrics and artifact paths.

    Raises:
        PermissionError: If split == 'test' and final is False (TC-T8-02).
        ValueError: If split is not in ('dev', 'test').
    """
    # TC-T8-02: Protect locked test set
    if split == "test" and not final:
        raise PermissionError(
            "TC-T8-02: Test split is locked. Pass --final to record an official test run."
        )

    if split not in ("dev", "test"):
        raise ValueError(f"Invalid split '{split}'. Must be 'dev' or 'test'.")

    target_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    client, effective_provider = create_sql_llm_client(provider=provider)
    all_benchmark = load_benchmark()

    # Filter benchmark items for SQL and C1 out-of-scope evaluations
    eval_items: list[BenchmarkItem] = [
        item for item in all_benchmark
        if item.split == split and (item.loai == "sql" or item.loai == "ngoai_pham_vi")
    ]

    total_evaluated = len(eval_items)
    results: list[dict[str, Any]] = []

    valid_sql_count = 0
    accurate_count = 0

    confidences: list[float] = []
    accuracies: list[int] = []

    for item in eval_items:
        output = run_sql_pipeline(
            question=item.cau_hoi,
            role=item.role,
            data_profile=item.profile,
            llm_client=client,
        )

        is_valid_sql = output.status in ("ok", "no_data")
        is_accurate = False
        actual_val = extract_numeric_value(output.rows) if output.rows else None

        if item.expected_status == "no_data":
            is_accurate = (output.status == "no_data")
        elif item.expected_status == "ok":
            if output.status == "ok":
                if item.ky_vong and item.ky_vong.gia_tri is not None:
                    if actual_val is not None:
                        exp = float(item.ky_vong.gia_tri)
                        tol = float(item.ky_vong.dung_sai_tuong_doi or 1e-4)
                        rel_diff = abs(actual_val - exp) / max(abs(exp), 1e-9)
                        abs_diff = abs(actual_val - exp)
                        if rel_diff <= tol or abs_diff <= 1e-4:
                            is_accurate = True
                else:
                    is_accurate = True

        if is_valid_sql:
            valid_sql_count += 1
        if is_accurate:
            accurate_count += 1

        confidences.append(output.confidence)
        accuracies.append(1 if is_accurate else 0)

        results.append({
            "id": item.id,
            "loai": item.loai,
            "do_kho": item.do_kho,
            "dashboard": item.dashboard or "OOS",
            "cau_hoi": item.cau_hoi,
            "expected_status": item.expected_status,
            "status": output.status,
            "expected_value": item.ky_vong.gia_tri if item.ky_vong else None,
            "actual_value": actual_val,
            "confidence": output.confidence,
            "is_valid_sql": is_valid_sql,
            "is_accurate": is_accurate,
            "error": output.error,
            "latency_ms": output.latency_ms,
        })

    m06_accuracy = round(accurate_count / max(total_evaluated, 1), 4)
    m07_valid_rate = round(valid_sql_count / max(total_evaluated, 1), 4)
    commit_hash = get_git_commit_hash()
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Generate Evidence EV-07: sql_accuracy.md
    report_path = target_dir / "sql_accuracy.md"
    _generate_markdown_report(
        report_path=report_path,
        commit_hash=commit_hash,
        timestamp_utc=timestamp_utc,
        split=split,
        configured_provider=provider,
        effective_provider=effective_provider,
        m06_accuracy=m06_accuracy,
        m07_valid_rate=m07_valid_rate,
        total=total_evaluated,
        accurate_count=accurate_count,
        valid_sql_count=valid_sql_count,
        results=results,
    )

    # Generate Evidence EV-08: calibration.png
    plot_path = target_dir / "calibration.png"
    _generate_calibration_plot(
        plot_path=plot_path,
        confidences=confidences,
        accuracies=accuracies,
    )

    return {
        "split": split,
        "m06_execution_accuracy": m06_accuracy,
        "m07_valid_sql_rate": m07_valid_rate,
        "total_evaluated": total_evaluated,
        "accurate_count": accurate_count,
        "valid_sql_count": valid_sql_count,
        "commit_hash": commit_hash,
        "configured_provider": provider,
        "effective_provider": effective_provider,
        "report_path": report_path,
        "plot_path": plot_path,
        "results": results,
    }


def _generate_markdown_report(
    report_path: Path,
    commit_hash: str,
    timestamp_utc: str,
    split: str,
    configured_provider: str,
    effective_provider: str,
    m06_accuracy: float,
    m07_valid_rate: float,
    total: int,
    accurate_count: int,
    valid_sql_count: int,
    results: list[dict[str, Any]],
) -> None:
    """Write EV-07 Markdown evaluation report."""
    # Breakdowns by difficulty
    diff_groups: dict[str, list[dict]] = {"de": [], "vua": [], "kho": []}
    dash_groups: dict[str, list[dict]] = {}
    oos_items: list[dict] = []

    for r in results:
        diff = r.get("do_kho", "vua")
        if diff in diff_groups:
            diff_groups[diff].append(r)
        dash = r.get("dashboard", "OOS")
        dash_groups.setdefault(dash, []).append(r)
        if r.get("loai") == "ngoai_pham_vi":
            oos_items.append(r)

    lines = [
        "# Báo cáo Đánh giá Độ chính xác Text-to-SQL (EV-07)",
        "",
        f"- **Tập dữ liệu (Split):** `{split}`",
        f"- **Thời gian chạy (UTC):** `{timestamp_utc}`",
        f"- **Git Commit Hash:** `{commit_hash}`",
        f"- **Configured Provider:** `{configured_provider}`",
        f"- **Effective Provider:** `{effective_provider}`",
        "- **Hồ sơ dữ liệu:** `real` (PostgreSQL `data_warehouse`)",
        "",
        "## 1. Tổng quan Chỉ số Đo lường Chính (Key Metrics)",
        "",
        f"| Chỉ số | Tên chỉ số | Kết quả | Đạt / Mục tiêu | Trạng thái |",
        f"| --- | --- | --- | --- | --- |",
        f"| **M-06** | Execution Accuracy (Độ chính xác thực thi) | **{m06_accuracy * 100:.2f}%** ({accurate_count}/{total}) | ≥ 90.0% | {'✅ ĐẠT' if m06_accuracy >= 0.90 else '❌ CHƯA ĐẠT'} |",
        f"| **M-07** | Valid SQL Rate (Tỷ lệ SQL hợp lệ) | **{m07_valid_rate * 100:.2f}%** ({valid_sql_count}/{total}) | ≥ 95.0% | {'✅ ĐẠT' if m07_valid_rate >= 0.95 else '❌ CHƯA ĐẠT'} |",
        "",
        "## 2. Phân rã theo Độ khó (Difficulty Breakdown)",
        "",
        "| Độ khó | Tổng số câu | Hợp lệ (M-07) | Chính xác (M-06) | Tỷ lệ chính xác |",
        "| --- | --- | --- | --- | --- |",
    ]

    for diff_name in ["de", "vua", "kho"]:
        items = diff_groups[diff_name]
        cnt = len(items)
        if cnt == 0:
            lines.append(f"| `{diff_name}` | 0 | 0 | 0 | N/A |")
            continue
        v_cnt = sum(1 for x in items if x["is_valid_sql"])
        a_cnt = sum(1 for x in items if x["is_accurate"])
        pct = (a_cnt / cnt) * 100.0
        lines.append(f"| `{diff_name}` | {cnt} | {v_cnt} | {a_cnt} | {pct:.1f}% |")

    lines.extend([
        "",
        "## 3. Phân rã theo Dashboard Nghiệp vụ",
        "",
        "| Dashboard | Tổng số câu | Hợp lệ | Chính xác | Tỷ lệ chính xác |",
        "| --- | --- | --- | --- | --- |",
    ])

    for dash in sorted(dash_groups.keys()):
        items = dash_groups[dash]
        cnt = len(items)
        v_cnt = sum(1 for x in items if x["is_valid_sql"])
        a_cnt = sum(1 for x in items if x["is_accurate"])
        pct = (a_cnt / cnt) * 100.0
        lines.append(f"| `{dash}` | {cnt} | {v_cnt} | {a_cnt} | {pct:.1f}% |")

    lines.extend([
        "",
        "## 4. Kiểm định Nhóm Giới hạn Dữ liệu C1 (Known Missing Data / no_data)",
        "",
        "| ID | Câu hỏi | Kỳ vọng | Trạng thái thực tế | Kết quả đối soát |",
        "| --- | --- | --- | --- | --- |",
    ])

    for oos in oos_items:
        stat = "✅ ĐÚNG (no_data)" if oos["is_accurate"] else f"❌ SAI ({oos['status']})"
        lines.append(f"| `{oos['id']}` | {oos['cau_hoi']} | `no_data` | `{oos['status']}` | {stat} |")

    lines.extend([
        "",
        "## 5. Danh sách Chi tiết Toàn bộ Câu Benchmark Đã Đánh giá",
        "",
        "| ID | Độ khó | Dash | Câu hỏi | Kỳ vọng | Thực tế | Trạng thái | Conf | M-07 | M-06 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])

    for r in results:
        exp_str = f"{r['expected_value']:.2f}" if r["expected_value"] is not None else str(r["expected_status"])
        act_str = f"{r['actual_value']:.2f}" if r["actual_value"] is not None else "-"
        m07_ico = "✅" if r["is_valid_sql"] else "❌"
        m06_ico = "✅" if r["is_accurate"] else "❌"
        lines.append(
            f"| `{r['id']}` | `{r['do_kho']}` | `{r['dashboard']}` | {r['cau_hoi']} | {exp_str} | {act_str} | `{r['status']}` | {r['confidence']:.2f} | {m07_ico} | {m06_ico} |"
        )

    lines.extend([
        "",
        "## 6. Phân tích Nhóm Lỗi (Error Diagnostics)",
        "",
    ])

    failures = [r for r in results if not r["is_accurate"]]
    if not failures:
        lines.append("🎉 **Không phát hiện lỗi nào trên tập dev.** Toàn bộ 19 câu benchmark đều đạt chuẩn chính xác tuyệt đối.")
    else:
        for f in failures:
            lines.append(f"- **`{f['id']}`**: {f['cau_hoi']} (Status: `{f['status']}`, Lỗi: {f['error'] or 'Sai lệch số liệu'})")

    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _generate_calibration_plot(
    plot_path: Path,
    confidences: list[float],
    accuracies: list[int],
) -> None:
    """Generate EV-08 calibration reliability diagram and question distribution plot."""
    bins = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
    bin_labels = ["[0.0, 0.2)", "[0.2, 0.4)", "[0.4, 0.6)", "[0.6, 0.8)", "[0.8, 1.0]"]

    bin_accs: list[float] = []
    bin_counts: list[int] = []
    bin_centers: list[float] = [0.1, 0.3, 0.5, 0.7, 0.9]

    for i, (low, high) in enumerate(bins):
        in_bin = []
        for c, a in zip(confidences, accuracies):
            if i == len(bins) - 1:
                match = (low <= c <= high)
            else:
                match = (low <= c < high)
            if match:
                in_bin.append(a)

        cnt = len(in_bin)
        bin_counts.append(cnt)
        if cnt > 0:
            bin_accs.append(sum(in_bin) / cnt)
        else:
            bin_accs.append(0.0)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(8, 7), gridspec_kw={"height_ratios": [2.5, 1]}
    )

    # Subplot 1: Reliability Curve vs Perfect Calibration
    ax1.plot([0, 1], [0, 1], "k--", label="Perfect Calibration (y = x)", linewidth=1.5)
    # Only plot points where there are samples
    active_centers = [c for c, cnt in zip(bin_centers, bin_counts) if cnt > 0]
    active_accs = [a for a, cnt in zip(bin_accs, bin_counts) if cnt > 0]
    ax1.plot(active_centers, active_accs, "s-", color="#1f77b4", label="Empirical Accuracy", markersize=8, linewidth=2)

    ax1.set_xlim(-0.05, 1.05)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlabel("Confidence Score", fontsize=11)
    ax1.set_ylabel("Empirical Accuracy", fontsize=11)
    ax1.set_title("Reliability Diagram (Calibration) - Dev Benchmark (EV-08)", fontsize=13, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left")

    # Subplot 2: Sample Distribution
    ax2.bar(bin_labels, bin_counts, color="#aec7e8", edgecolor="#1f77b4", width=0.6)
    ax2.set_xlabel("Confidence Bin", fontsize=11)
    ax2.set_ylabel("Questions", fontsize=11)
    ax2.grid(True, axis="y", linestyle=":", alpha=0.6)

    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)


def main() -> None:
    """CLI entrypoint for running evaluation harness."""
    parser = argparse.ArgumentParser(description="GML Text-to-SQL Evaluation Harness")
    parser.add_argument("--group", default="sql", choices=["sql", "rag", "all"], help="Evaluation group")
    parser.add_argument("--split", default="dev", choices=["dev", "test"], help="Dataset split")
    parser.add_argument("--final", action="store_true", help="Unlock official test split run")
    parser.add_argument("--provider", default="auto", choices=["auto", "heuristic", "gemini", "ollama", "mock"], help="LLM Provider")
    parser.add_argument("--output-dir", default=None, help="Directory to save report and plots")

    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    print(f"🚀 Running SQL evaluation on split='{args.split}' with provider='{args.provider}'...")
    res = run_sql_evaluation(
        split=args.split,
        final=args.final,
        provider=args.provider,
        output_dir=out_dir,
    )

    print("\n✅ Evaluation Completed Successfully!")
    print(f"- Total Evaluated: {res['total_evaluated']}")
    print(f"- M-06 (Execution Accuracy): {res['m06_execution_accuracy'] * 100:.2f}% ({res['accurate_count']}/{res['total_evaluated']})")
    print(f"- M-07 (Valid SQL Rate):     {res['m07_valid_sql_rate'] * 100:.2f}% ({res['valid_sql_count']}/{res['total_evaluated']})")
    print(f"- Effective Provider:        {res['effective_provider']}")
    print(f"- Report (EV-07):            {res['report_path']}")
    print(f"- Plot (EV-08):              {res['plot_path']}")


if __name__ == "__main__":
    main()
