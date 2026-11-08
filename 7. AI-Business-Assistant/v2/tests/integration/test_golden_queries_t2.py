"""Integration tests for Golden Queries Bank (T2) on Real AI Views.

Specifications:
- Spec §5 T2, §6 (Sổ đáp án chuẩn UAT: G-01..G-13, UAT_01..05)
- TC-T2-02: All Golden Queries in index.yaml pass AST validator and match UAT ground truth
  within tolerance <= 1e-4 on real profile.
"""

from pathlib import Path
import pytest
import sqlalchemy as sa

from app.core.security import get_allowed_views
from app.knowledge.loader import load_golden_queries
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
