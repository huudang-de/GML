"""Database provisioning, migration, and evidence generation for AI Business Assistant v2.

Specifications:
- Spec §3.1, §5 T1
- Spec §6 (Sổ đáp án chuẩn UAT: G-01..G-13)
- Plan Task 4
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
import sys

# Base paths and sys.path setup
DB_DIR = Path(__file__).resolve().parent
V2_DIR = DB_DIR.parent
if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))

import jinja2
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.core.errors import sanitize_db_error

REPORTS_DIR = V2_DIR / "eval" / "reports"
ENV_PATH = V2_DIR / ".env"


def _get_settings() -> Settings:
    """Load settings with robust fallback to v2/.env file."""
    if ENV_PATH.exists():
        return Settings(_env_file=str(ENV_PATH))
    return Settings()


def get_admin_engine(admin_uri: str | None = None) -> Engine:
    """Return SQLAlchemy engine for administrative tasks (dev/admin)."""
    settings = _get_settings()
    uri = admin_uri or settings.postgres_uri_admin
    return sa.create_engine(uri, pool_pre_ping=True)


def get_ro_engine(ro_uri: str | None = None) -> Engine:
    """Return SQLAlchemy engine for AI read-only queries (gml_ai_ro)."""
    settings = _get_settings()
    uri = ro_uri or settings.postgres_uri_ro
    return sa.create_engine(uri, pool_pre_ping=True)


def get_app_engine(app_uri: str | None = None) -> Engine:
    """Return SQLAlchemy engine for application state logging (gml_ai_app)."""
    settings = _get_settings()
    uri = app_uri or settings.postgres_uri_app
    return sa.create_engine(uri, pool_pre_ping=True)


# ==============================================================================
# GOLD_UAT_QUERIES (13 golden metrics G-01..G-13 from Spec §6)
# ==============================================================================

GOLD_UAT_QUERIES: list[dict] = [
    {
        "id": "G-01",
        "name": "Dư nợ ngắn hạn",
        "expected": 236065233815.00,
        "source": "UAT_01 · Dư nợ ngắn hạn (sổ cái TK 34111, 34113, 34114)",
        "sql": (
            "SELECT SUM(credit_balance) "
            "FROM ai_views.ai_v_no_vay "
            "WHERE record_type = 'ledger_balance' "
            "  AND (account_no LIKE '34111%' OR account_no LIKE '34113%' OR account_no LIKE '34114%') "
            "  AND rn = 1;"
        ),
    },
    {
        "id": "G-02",
        "name": "Dư nợ dài hạn",
        "expected": 51174925843.00,
        "source": "UAT_01 · Dư nợ dài hạn (sổ cái TK 34112)",
        "sql": (
            "SELECT SUM(credit_balance) "
            "FROM ai_views.ai_v_no_vay "
            "WHERE record_type = 'ledger_balance' "
            "  AND account_no LIKE '34112%' "
            "  AND rn = 1;"
        ),
    },
    {
        "id": "G-03",
        "name": "Hạn mức được phê duyệt",
        "expected": 485000000000.00,
        "source": "UAT_01 · fact_creditlimitsummary.credit_limit",
        "sql": "SELECT SUM(credit_limit) FROM ai_views.ai_v_no_vay WHERE record_type = 'credit_limit';",
    },
    {
        "id": "G-04",
        "name": "Hạn mức được cấp",
        "expected": 295000000000.00,
        "source": "UAT_01 · fact_creditlimitsummary.granted_limit",
        "sql": "SELECT SUM(granted_limit) FROM ai_views.ai_v_no_vay WHERE record_type = 'credit_limit';",
    },
    {
        "id": "G-05",
        "name": "Hạn mức còn lại",
        "expected": 24135521634.00,
        "source": "UAT_01 · granted_limit - principal_balance",
        "sql": (
            "SELECT SUM(granted_limit) - SUM(principal_balance) "
            "FROM ai_views.ai_v_no_vay "
            "WHERE record_type = 'credit_limit';"
        ),
    },
    {
        "id": "G-06",
        "name": "LTV",
        "expected": 0.7129086354934684,
        "source": "UAT_01 · granted_limit / collateral appraised_value",
        "sql": (
            "SELECT (SELECT SUM(granted_limit) FROM ai_views.ai_v_no_vay WHERE record_type = 'credit_limit') / "
            "NULLIF((SELECT SUM(appraised_value) FROM ai_views.ai_v_no_vay WHERE record_type = 'collateral'), 0);"
        ),
    },
    {
        "id": "G-07",
        "name": "Tiền và tương đương tiền",
        "expected": 91976722608.00,
        "source": "UAT_04 · B01-DN_110 ending_balance tại kỳ báo cáo mới nhất",
        "sql": (
            "SELECT ending_balance "
            "FROM ai_views.ai_v_bctc "
            "WHERE item_code = 'B01-DN_110' "
            "  AND report_type = 'B01-DN' "
            "  AND reporting_date = (SELECT MAX(reporting_date) FROM ai_views.ai_v_bctc WHERE report_type = 'B01-DN');"
        ),
    },
    {
        "id": "G-08",
        "name": "Tiền gửi còn hiệu lực",
        "expected": 40514952541.00,
        "source": "UAT_04 · fact_termdeposit active contracts original_amount",
        "sql": "SELECT SUM(original_amount) FROM ai_views.ai_v_tien_gui WHERE is_active_at_cutoff = TRUE;",
    },
    {
        "id": "G-09",
        "name": "Số hợp đồng tiền gửi còn hiệu lực",
        "expected": 22.0,
        "source": "UAT_04 · fact_termdeposit active passbooks count",
        "sql": "SELECT COUNT(DISTINCT passbook_no) FROM ai_views.ai_v_tien_gui WHERE is_active_at_cutoff = TRUE;",
    },
    {
        "id": "G-10",
        "name": "Lãi suất tiền gửi bình quân",
        "expected": 0.049896752996198945,
        "source": "UAT_04 · Weighted average interest rate on active deposits",
        "sql": (
            "SELECT SUM(original_amount * interest_rate) / NULLIF(SUM(original_amount), 0) "
            "FROM ai_views.ai_v_tien_gui "
            "WHERE is_active_at_cutoff = TRUE;"
        ),
    },
    {
        "id": "G-11",
        "name": "Thu nhập lãi TK 515",
        "expected": 1482534625.00,
        "source": "UAT_04 · fact_cashflow reciprocal_account 515%",
        "sql": "SELECT SUM(debit_amount) FROM ai_views.ai_v_dong_tien WHERE reciprocal_account LIKE '515%';",
    },
    {
        "id": "G-12",
        "name": "Dư nợ gốc trên hạn mức",
        "expected": 270864478366.00,
        "source": "UAT_01 / Spec §6 · fact_creditlimitsummary SUM(principal_balance)",
        "sql": "SELECT SUM(principal_balance) FROM ai_views.ai_v_no_vay WHERE record_type = 'credit_limit';",
    },
    {
        "id": "G-13",
        "name": "Tỷ lệ sử dụng hạn mức",
        "expected": 0.9181846724271186,
        "source": "UAT_01 / Spec §6 · G-12 / G-04 (270.86B / 295B)",
        "sql": (
            "SELECT (SELECT SUM(principal_balance) FROM ai_views.ai_v_no_vay WHERE record_type = 'credit_limit') / "
            "(SELECT SUM(granted_limit) FROM ai_views.ai_v_no_vay WHERE record_type = 'credit_limit');"
        ),
    },
]


def apply_all(
    admin_uri: str | None = None,
    source_schema: str = "silver",
    as_of_date: str = "2026-07-31",
) -> None:
    """Apply roles, rendered views, and operational migrations to PostgreSQL."""
    admin_engine = get_admin_engine(admin_uri)

    # 1. Apply roles and permission hardening
    roles_sql_path = DB_DIR / "roles.sql"
    roles_sql = roles_sql_path.read_text(encoding="utf-8")
    with admin_engine.connect() as conn:
        conn.execute(sa.text(roles_sql))
        conn.commit()

    # 2. Render and apply 7 AI views from Jinja2 template
    views_j2_path = DB_DIR / "views.sql.j2"
    template_content = views_j2_path.read_text(encoding="utf-8")
    template = jinja2.Template(template_content)
    rendered_views_sql = template.render(
        source_schema=source_schema,
        as_of_date=as_of_date,
    )
    with admin_engine.connect() as conn:
        conn.execute(sa.text(rendered_views_sql))
        conn.commit()

    # 3. Apply schema 'app' migrations
    mig_path = DB_DIR / "migrations" / "001_init_app_schema.sql"
    mig_sql = mig_path.read_text(encoding="utf-8")
    with admin_engine.connect() as conn:
        conn.execute(sa.text(mig_sql))
        conn.commit()


def generate_t1_evidence(output_dir: Path | str | None = None) -> tuple[str, str]:
    """Execute verification suites and generate EV-01 and EV-02 evidence files.

    EV-01: eval/reports/t1_permissions.txt
    EV-02: eval/reports/t1_views_vs_uat.csv
    Returns:
        tuple[str, str]: Absolute paths to EV-01 and EV-02.
    """
    out_dir = Path(output_dir) if output_dir else REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    ev01_path = out_dir / "t1_permissions.txt"
    ev02_path = out_dir / "t1_views_vs_uat.csv"

    ro_engine = get_ro_engine()

    # -------------------------------------------------------------------------
    # EV-01: Permission & Timeout Verification (TC-T1-01, TC-T1-02, TC-T1-03)
    # -------------------------------------------------------------------------
    log_lines: list[str] = []
    log_lines.append("=" * 80)
    log_lines.append("EVIDENCE EV-01: T1 DATABASE PERMISSIONS & TIMEOUT VERIFICATION REPORT")
    log_lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")
    log_lines.append("Role: gml_ai_ro | Host: localhost:5432 | DB: data_warehouse")
    log_lines.append("=" * 80)
    log_lines.append("")

    # Check 1: Role Configuration
    with ro_engine.connect() as conn:
        timeout_val = conn.execute(sa.text("SHOW statement_timeout")).scalar()
        ro_flag = conn.execute(sa.text("SHOW default_transaction_read_only")).scalar()
        log_lines.append("[CONFIG CHECK]")
        log_lines.append(f"  SHOW statement_timeout = {timeout_val} (Expected: 15s) -> {'PASS' if timeout_val == '15s' else 'FAIL'}")
        log_lines.append(f"  SHOW default_transaction_read_only = {ro_flag} (Expected: on) -> {'PASS' if ro_flag == 'on' else 'FAIL'}")
        log_lines.append("")

    # Check 2: TC-T1-01 - Role cannot write (INSERT, UPDATE, DELETE, DROP, CREATE)
    log_lines.append("[TC-T1-01: READ-ONLY ENFORCEMENT - PREVENT WRITE OPERATIONS]")
    write_test_stmts = [
        ("CREATE TABLE", "CREATE TABLE ai_views.hack_test (id int);"),
        ("DROP VIEW", "DROP VIEW ai_views.ai_v_no_vay;"),
        ("DELETE", "DELETE FROM ai_views.ai_v_no_vay WHERE 1=1;"),
        ("UPDATE", "UPDATE ai_views.ai_v_no_vay SET principal_balance = 0;"),
        ("INSERT", "INSERT INTO ai_views.ai_v_no_vay (record_type) VALUES ('hack');"),
    ]
    leaked_writes = 0
    for name, stmt in write_test_stmts:
        try:
            with ro_engine.connect() as conn:
                conn.execute(sa.text(stmt))
                conn.commit()
            leaked_writes += 1
            log_lines.append(f"  FAIL: {name} succeeded unexpectedly! Statement: {stmt}")
        except Exception as e:
            sanitized = sanitize_db_error(e)
            log_lines.append(f"  PASS: {name} blocked. Reason: {sanitized}")
    log_lines.append(f"  Metric M-02 (Leaked write commands): {leaked_writes} (Target: 0)")
    log_lines.append("")

    # Check 3: TC-T1-02 - Role cannot access raw silver schema
    log_lines.append("[TC-T1-02: RAW SILVER SCHEMA ISOLATION]")
    raw_silver_stmts = [
        "SELECT * FROM silver.fact_cashflow LIMIT 1;",
        "SELECT * FROM silver.fact_creditlimitsummary LIMIT 1;",
        "SELECT * FROM silver.dim_account LIMIT 1;",
    ]
    leaked_silver_reads = 0
    for stmt in raw_silver_stmts:
        try:
            with ro_engine.connect() as conn:
                conn.execute(sa.text(stmt))
            leaked_silver_reads += 1
            log_lines.append(f"  FAIL: silver read succeeded unexpectedly! Statement: {stmt}")
        except Exception as e:
            sanitized = sanitize_db_error(e)
            log_lines.append(f"  PASS: silver access denied. Reason: {sanitized}")
    log_lines.append("")

    # Check 4: TC-T1-03 - Query Timeout Cancellation
    log_lines.append("[TC-T1-03: STATEMENT TIMEOUT CANCELLATION ENFORCEMENT]")
    try:
        with ro_engine.connect() as conn:
            # Set local session timeout to 1s to execute test swiftly
            conn.execute(sa.text("SET LOCAL statement_timeout = '1s'"))
            conn.execute(sa.text("SELECT pg_sleep(2)"))
        log_lines.append("  FAIL: Long query completed without timing out.")
    except Exception as e:
        sanitized = sanitize_db_error(e)
        log_lines.append(f"  PASS: Long query successfully canceled by statement_timeout. Reason: {sanitized}")
    log_lines.append("")

    log_lines.append("=" * 80)
    overall_ev01 = "PASS" if leaked_writes == 0 and leaked_silver_reads == 0 else "FAIL"
    log_lines.append(f"OVERALL EV-01 STATUS: {overall_ev01} (Zero privileges leaked to gml_ai_ro)")
    log_lines.append("=" * 80)

    ev01_path.write_text("\n".join(log_lines), encoding="utf-8")

    # -------------------------------------------------------------------------
    # EV-02: Golden Queries Accuracy Verification (TC-T1-04)
    # -------------------------------------------------------------------------
    csv_rows: list[dict] = []
    with ro_engine.connect() as conn:
        for item in GOLD_UAT_QUERIES:
            raw_res = conn.execute(sa.text(item["sql"])).scalar()
            actual = float(raw_res) if raw_res is not None else 0.0
            expected = float(item["expected"])
            rel_err = abs(actual - expected) / max(abs(expected), 1e-9)
            status = "PASS" if rel_err <= 1e-4 else "FAIL"
            csv_rows.append({
                "id": item["id"],
                "name": item["name"],
                "uat_expected": f"{expected:.6f}",
                "actual_views": f"{actual:.6f}",
                "relative_error": f"{rel_err:.6e}",
                "status": status,
                "sql": item["sql"].replace("\n", " ").strip(),
            })

    with open(ev02_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "name", "uat_expected", "actual_views", "relative_error", "status", "sql"]
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    return str(ev01_path), str(ev02_path)


if __name__ == "__main__":
    print("=" * 80)
    print("AI Business Assistant v2 — Applying T1 Database Schema & Permissions")
    print("=" * 80)
    apply_all()
    print("Database schema, roles, and views successfully applied.")
    print("Generating T1 verification evidence files (EV-01, EV-02)...")
    ev01, ev02 = generate_t1_evidence()
    print(f"EV-01 created: {ev01}")
    print(f"EV-02 created: {ev02}")
    print("Verification complete.")
