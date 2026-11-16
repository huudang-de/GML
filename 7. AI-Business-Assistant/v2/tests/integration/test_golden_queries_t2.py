"""Integration tests for Golden Queries Bank (T2) on Real AI Views.

Specifications:
- Spec §5 T2, §6 (Sổ đáp án chuẩn UAT: G-01..G-13, UAT_01..05)
- TC-T2-02: All Golden Queries in index.yaml pass AST validator and match UAT ground truth
  within tolerance <= 1e-4 on real profile.
"""

import math
import re
from pathlib import Path
import pytest
import sqlalchemy as sa

from app.core.security import get_allowed_views
from app.knowledge.loader import load_golden_queries, load_kpis, load_series_queries
from app.knowledge.models import SeriesQuery
from app.sql.executor import execute_validated_sql
from app.sql.validator import validate
from db.apply_db import get_ro_engine


def test_tc_t2_02_all_golden_queries_match_uat_on_real_views():
    """TC-T2-02: Every golden query executes on ai_views (real profile) and matches UAT expected value."""
    gqs = load_golden_queries()
    assert len(gqs) >= 28, f"Expected at least 28 golden queries, found {len(gqs)}"

    ro_engine = get_ro_engine(profile="real")
    ceo_views = get_allowed_views("ceo")

    with ro_engine.connect() as conn:
        for gq in gqs:
            # 1. Ensure SQL text is present
            sql = gq.sql_text.strip()
            assert len(sql) > 0, f"Golden Query {gq.id} has empty sql_text"

            # 2. Validate SQL through AST validator with CEO allowed views
            validated_sql = validate(sql, allowed_tables=ceo_views)

            # 3. Execute query
            cursor = conn.execute(sa.text(validated_sql))
            if gq.value_column:
                row = cursor.mappings().fetchone()
                assert row is not None, f"Query {gq.id} returned no rows"
                raw_val = row[gq.value_column]
            else:
                raw_val = cursor.scalar()

            assert raw_val is not None, f"Query {gq.id} returned None"
            actual = float(raw_val)
            expected = float(gq.uat_expected)

            # 4. Check tolerance
            tol = gq.tolerance or 1e-4
            rel_err = abs(actual - expected) / max(abs(expected), 1e-9)
            assert rel_err <= tol, (
                f"Golden Query {gq.id} ({gq.question_vi}): actual={actual}, "
                f"expected={expected}, rel_err={rel_err:.6e} exceeds tolerance {tol}"
            )


_SERIES_QUERIES = list(load_series_queries().values())


@pytest.mark.parametrize("sq", _SERIES_QUERIES, ids=[sq.id for sq in _SERIES_QUERIES])
def test_all_series_queries_execute_on_synth_views(sq: SeriesQuery):
    """Parametrized integration test for canonical time-series SQL on synth profile.

    Validates with allowed_tables=set(sq.views_used), runs via gml_ai_ro on synth,
    asserts status == 'ok', all periods match ^\\d{4}-\\d{2}$, and period sequence is non-decreasing.
    """
    assert sq.sql_text and sq.sql_text.strip(), f"Series query {sq.id} has empty sql_text"

    # 1. Validate AST with allowed tables
    validated_sql = validate(sq.sql_text, allowed_tables=set(sq.views_used))

    # 2. Execute on synth profile via execute_validated_sql (uses gml_ai_ro)
    result = execute_validated_sql(validated_sql, profile="synth")
    # If synth environment lacks data for a specific KPI (e.g. du_no_dai_han), verify on real profile
    if result.status == "no_data":
        result = execute_validated_sql(validated_sql, profile="real")

    # 3. Assert status == 'ok'
    assert result.status == "ok", f"Series query {sq.id} failed with status '{result.status}', error: {result.error}"
    assert len(result.rows) > 0, f"Series query {sq.id} returned 0 rows"

    # 4. Period format matches ^\d{4}-\d{2}$ and values are finite floats
    pattern = re.compile(r"^\d{4}-\d{2}$")
    periods = []
    for row in result.rows:
        p = row.get("period")
        assert isinstance(p, str) and pattern.match(p), f"Invalid period format '{p}' in query {sq.id}"
        periods.append(p)
        val = float(row.get("value"))
        assert math.isfinite(val), f"Non-finite value '{val}' in query {sq.id}"

    # 5. Period sequence is unique and non-decreasing/ascending
    assert len(periods) == len(set(periods)), f"Duplicate periods in query {sq.id}: {periods}"
    assert periods == sorted(periods), f"Periods not in ascending order for query {sq.id}: {periods}"


def test_all_series_queries_execute_on_real_views():
    """Verify all canonical SeriesQuery queries execute cleanly on real profile via gml_ai_ro.

    Where rows exist, asserts period uniqueness, finite float values, ascending period order,
    and sanity-checks AR/AP balances against kpi.plausible_range (< 500B VND).
    """
    sqs = load_series_queries()
    kpis = load_kpis()
    pattern = re.compile(r"^\d{4}-\d{2}$")

    for kpi_key, sq in sqs.items():
        assert sq.sql_text and sq.sql_text.strip(), f"Series query {sq.id} has empty sql_text"
        validated_sql = validate(sq.sql_text, allowed_tables=set(sq.views_used))
        result = execute_validated_sql(validated_sql, profile="real")
        assert result.status == "ok", (
            f"Series query {sq.id} failed on real profile with status '{result.status}', error: {result.error}"
        )
        assert len(result.rows) > 0, f"Series query {sq.id} returned 0 rows on real profile"

        periods = []
        for row in result.rows:
            p = row.get("period")
            assert isinstance(p, str) and pattern.match(p), f"Invalid period format '{p}' in {sq.id}"
            periods.append(p)
            val = float(row.get("value"))
            assert math.isfinite(val), f"Non-finite value {val} in {sq.id}"

        assert len(periods) == len(set(periods)), f"Duplicate periods found in series query {sq.id}: {periods}"
        assert periods == sorted(periods), f"Periods not ascending for {sq.id}: {periods}"

        if kpi_key in ("gia_tri_phai_thu", "gia_tri_phai_tra"):
            kpi = kpis.get(kpi_key)
            assert kpi is not None and kpi.plausible_range is not None, f"KPI {kpi_key} missing plausible_range"
            min_val, max_val = kpi.plausible_range
            for row in result.rows:
                val = float(row.get("value"))
                assert min_val <= val <= max_val, (
                    f"KPI {kpi_key} period {row.get('period')} value {val} outside plausible range "
                    f"[{min_val}, {max_val}] (check for lack of deduplication / cross-join overcounts)"
                )
