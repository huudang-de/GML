# AI Business Assistant v2 — Phase 1 (Data + Bảo mật) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng nền tảng Tầng Dữ liệu & Bảo mật (Phase 1) cho AI Business Assistant v2 trong thư mục `7. AI-Business-Assistant/v2/`, bao gồm phân quyền PostgreSQL chỉ-đọc (`gml_ai_ro`), 7 view chuẩn hoá `ai_views.*` khớp 100% đáp án UAT (G-01…G-13), schema nhật ký `app.*`, bộ kiểm tra AST SQL (`sqlglot`) theo RBAC, lớp cấu hình an toàn (`pydantic-settings`), và đồ thị LangGraph sửa lỗi chạy song song nhánh `both`.

**Architecture:** Thiết kế phòng thủ nhiều lớp từ dưới lên (T1 → T3 → T4 → T5):
1. **Lớp DB (T1):** Tài khoản `gml_ai_ro` (`default_transaction_read_only=on`, `statement_timeout=15s`) chỉ có quyền `SELECT` trên schema `ai_views` (7 view dựng từ Jinja2 template `views.sql.j2` theo `DATA_PROFILE` và mốc khoá sổ `AS_OF_DATE='2026-07-31'`), hoàn toàn bị chặn trên schema `silver`. Các bảng vận hành (`chat_turn`, `audit_log`, `alert_event`, `feedback`, `job_heartbeat`) tách riêng vào schema `app` với role `gml_ai_app`.
2. **Lớp Kiểm soát AST & Cấu hình (T3/T5):** `app/sql/validator.py` phân tích cú pháp SQL bằng `sqlglot`, chặn mọi lệnh khác `SELECT`, hàm nguy hiểm (`pg_sleep`, `pg_read_file`...), bảng ngoài `catalog.yaml` theo từng vai trò (`ceo`, `ke_toan_truong`, `quan_ly_kho`, `quan_tri_he_thong`), và ép buộc `LIMIT`. `app/core/config.py` chặn khởi động khi `APP_ENV=production` dùng LLM đám mây gói miễn phí.
3. **Lớp Điều phối (T4):** Đồ thị `StateGraph(ChatState)` rẽ nhánh song song `['sql_lookup', 'rag_lookup']` cho intent `both` và gom tại node `join` trước khi tổng hợp.

**Tech Stack:** Python 3.11+, PostgreSQL 15+, SQLAlchemy 2.0+, `psycopg2-binary>=2.9.0`, `pydantic>=2.7.0`, `pydantic-settings>=2.2.0`, `sqlglot>=23.0.0`, `langgraph>=0.1.0`, `jinja2>=3.1.0`, `pyyaml>=6.0.1`, `pytest>=8.0.0`.

**Spec:**
- `7. AI-Business-Assistant/docs/AI_Business_Assistant_v2_Architecture_Detail.md` (§3.1, §4, §5 T1/T3/T4/T5, §6, §8 Phase 1, §9, §11)
- `7. AI-Business-Assistant/docs/AI_Business_Assistant_v2_Plan.md` (Phần II §5, §6.2, §6.7, §8)

## Global Constraints

- **C0 / §11.7 (Cô lập thư mục v2):** Toàn bộ mã nguồn v2 đặt trong `7. AI-Business-Assistant/v2/`. Không sửa bất kỳ file nào của `v1` (`7. AI-Business-Assistant/app/`).
- **C1 / §6 Note (Mốc khoá sổ):** Mốc "hiện tại" trên dữ liệu thật (`silver`) là `AS_OF_DATE = 2026-07-31` (tháng 8/2026 chưa khoá sổ). View `ai_views.*` lọc dữ liệu theo `as_of_date`.
- **C3 / TC-T5-09 (Bảo vệ môi trường production):** Khi `APP_ENV=production` và `LLM_PROVIDER=gemini` với `LLM_TIER=free`, ứng dụng phải từ chối khởi tạo cấu hình (`UnsafeDeploymentError`).
- **§5 T1 (Hợp đồng lỗi DB):** Lỗi trả về từ tầng DB (`sanitize_db_error`) không được để lộ tên schema nguồn (`silver`), mật khẩu trong URI, hay đường dẫn tệp nội bộ.
- **§6 Warning (Định nghĩa hạn mức tín dụng chuẩn UAT):** Tỷ lệ sử dụng hạn mức (G-13) = `SUM(principal_balance) / SUM(granted_limit)` trên `fact_creditlimitsummary` (`270,864,478,366 / 295,000,000,000 = 0.9181846724`), hạn mức còn lại (G-05) = `SUM(granted_limit) - SUM(principal_balance) = 24,135,521,634`.
- **§8 Phase 1 Gate:** Phải pass toàn bộ `TC-T1-01…04`, `TC-T3-01…03`, `TC-T4-01`, `TC-T5-09`; đạt `M-01 = 100%` (13/13 chỉ tiêu G-01…G-13 khớp UAT sai số tương đối `≤ 1e-4`), `M-02 = 0` (0 lệnh ghi lọt qua `gml_ai_ro`); xuất bằng chứng `EV-01` (`v2/eval/reports/t1_permissions.txt`) và `EV-02` (`v2/eval/reports/t1_views_vs_uat.csv`).

## Review Focus

1. **Truy cập bảng hệ thống hoặc schema nguồn qua tên có tiền tố (`SELECT * FROM silver.fact_cashflow` hoặc `pg_catalog.pg_shadow`):** `validate()` trong `app/sql/validator.py` phải kiểm tra cả `table.db` (schema) lẫn `table.name`; mọi truy vấn chỉ định schema khác `ai_views` (hoặc rỗng) phải bị chặn ngay ở AST với `SqlRejected`.
2. **Vượt giới hạn dòng bằng `LIMIT` lớn (`SELECT * FROM ai_v_dong_tien LIMIT 9999999`):** Nếu câu SQL đã có `LIMIT` nhưng lớn hơn `max_rows` (mặc định 1000), `validate()` phải ép hạ `LIMIT` xuống `max_rows`.
3. **Bỏ qua bộ lọc AST bằng CTE trùng tên hoặc subquery lồng (`WITH silver AS (...)` hoặc `SELECT * FROM (DELETE FROM ... RETURNING *)`):** `sqlglot` parse cây cú pháp phải kiểm tra không có bất kỳ node DML/DDL nào (`exp.Delete`, `exp.Update`, `exp.Insert`, `exp.Drop`, `exp.Create`, `exp.Alter`, `exp.Command`) ở mọi độ sâu của AST, kể cả bên trong CTE.
4. **Rò rỉ chuỗi kết nối hoặc tên bảng `silver` khi DB báo lỗi (`psycopg2.OperationalError` chứa password hoặc `relation "silver.fact_cashflow"`):** Hàm `sanitize_db_error(err: Exception) -> str` phải xoá mọi URI `postgresql://...`, đường dẫn tuyệt đối Windows/Linux, và thay thế tên nội bộ `silver.` bằng `[REDACTED_SCHEMA].`.
5. **Node `join` chạy nhiều lần hoặc ghi đè mất state khi chạy nhánh `both` và `sql_only`:** Trong LangGraph, node `join` phải gom state từ cả `sql_lookup` và `rag_lookup` mà không làm mất `sql` hay `rag`, đồng thời chỉ kích hoạt bước tiếp theo đúng 1 lần.

---

## File Map (Phase 1)

```text
7. AI-Business-Assistant/v2/
├── .env.example
├── requirements.txt
├── pytest.ini
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings (pydantic-settings), TC-T5-09 guard
│   │   ├── errors.py              # UnsafeDeploymentError, SqlRejected, DbAccessError, sanitize_db_error
│   │   └── security.py            # Role enum, load_catalog(), get_allowed_views(role)
│   ├── sql/
│   │   ├── __init__.py
│   │   └── validator.py           # validate(sql, allowed_tables, max_rows) via sqlglot AST
│   └── orchestration/
│       ├── __init__.py
│       ├── state.py               # Intent, ChatState TypedDict
│       ├── routing.py             # route_after_intent, route_after_join
│       └── graph.py               # build_graph(nodes) with parallel `both` + `join` node
├── db/
│   ├── catalog.yaml               # 7 ai_views metadata + RBAC allowed_roles (§11.9)
│   ├── roles.sql                  # gml_ai_ro (read-only, timeout 15s) & gml_ai_app
│   ├── views.sql.j2               # Jinja2 template for 7 views in ai_views.*
│   ├── migrations/
│   │   └── 001_init_app_schema.sql # app.chat_turn, audit_log, alert_event, feedback, job_heartbeat
│   └── apply_db.py                # Renders views.sql.j2, applies roles/views/migrations, runs DB queries safely
├── eval/
│   └── reports/
│       ├── t1_permissions.txt     # EV-01: Permission & timeout test evidence
│       └── t1_views_vs_uat.csv    # EV-02: G-01..G-13 comparison vs UAT RESULT LOG
└── tests/
    ├── unit/
    │   ├── test_config.py                # TC-T5-09 + error sanitization
    │   ├── test_sql_validator.py         # TC-T3-01, TC-T3-02, TC-T3-03
    │   └── test_orchestration_routing.py # TC-T4-01, TC-T4-02
    └── integration/
        └── test_db_t1.py                 # TC-T1-01, TC-T1-02, TC-T1-03, TC-T1-04 + generates EV-01, EV-02
```

---

### Task 1: Khởi tạo cấu trúc `v2/`, Lớp Cấu hình (`pydantic-settings`), Phân quyền RBAC & Chốt chặn Triển khai (`TC-T5-09`)

**Files:**
- Create: `7. AI-Business-Assistant/v2/requirements.txt`
- Create: `7. AI-Business-Assistant/v2/.env.example`
- Create: `7. AI-Business-Assistant/v2/pytest.ini`
- Create: `7. AI-Business-Assistant/v2/app/__init__.py`
- Create: `7. AI-Business-Assistant/v2/app/core/__init__.py`
- Create: `7. AI-Business-Assistant/v2/app/core/errors.py`
- Create: `7. AI-Business-Assistant/v2/app/core/config.py`
- Create: `7. AI-Business-Assistant/v2/app/core/security.py`
- Create: `7. AI-Business-Assistant/v2/db/catalog.yaml`
- Test: `7. AI-Business-Assistant/v2/tests/unit/test_config.py`

**Interfaces:**
- Consumes: Biến môi trường hệ thống / `.env`, file `v2/db/catalog.yaml`.
- Produces:
  - `app.core.errors.UnsafeDeploymentError(Exception)`
  - `app.core.errors.SqlRejected(Exception)`
  - `app.core.errors.DbExecutionError(Exception)`
  - `app.core.errors.sanitize_db_error(err: Exception | str) -> str`
  - `app.core.config.Settings(BaseSettings)` với validator kiểm tra `APP_ENV == "production"`
  - `app.core.security.Role = Literal["ceo", "ke_toan_truong", "quan_ly_kho", "quan_tri_he_thong"]`
  - `app.core.security.load_catalog(catalog_path: Path | None = None) -> dict`
  - `app.core.security.get_allowed_views(role: str, catalog_path: Path | None = None) -> set[str]`

- [ ] **Step 1: Tạo `v2/requirements.txt`, `v2/.env.example`, `v2/pytest.ini`, và `v2/db/catalog.yaml`**

Trong `v2/db/catalog.yaml`, khai báo đầy đủ 7 view đúng theo bảng phân quyền §11.9 của Spec:
- `ai_v_no_vay`: `allowed_roles: ["ceo", "ke_toan_truong"]`
- `ai_v_dong_tien`: `allowed_roles: ["ceo", "ke_toan_truong"]`
- `ai_v_bctc`: `allowed_roles: ["ceo", "ke_toan_truong"]`
- `ai_v_ton_kho`: `allowed_roles: ["ceo", "quan_ly_kho"]`
- `ai_v_cong_no`: `allowed_roles: ["ceo", "ke_toan_truong"]`
- `ai_v_tien_gui`: `allowed_roles: ["ceo", "ke_toan_truong"]`
- `ai_v_ke_hoach`: `allowed_roles: ["ceo", "ke_toan_truong"]`
Mỗi view có `description`, `grain`, `source_tables`, `allowed_roles`, và danh sách `columns` (tên cột, kiểu, đơn vị, ý nghĩa).

- [ ] **Step 2: Viết failing unit test trong `v2/tests/unit/test_config.py`**

```python
import pytest
from datetime import date
from app.core.config import Settings
from app.core.errors import UnsafeDeploymentError, sanitize_db_error
from app.core.security import get_allowed_views

def test_tc_t5_09_block_unsafe_production_config():
    """TC-T5-09: APP_ENV=production + cloud LLM free tier -> refuse startup."""
    with pytest.raises(UnsafeDeploymentError, match="production"):
        Settings(
            app_env="production",
            llm_provider="gemini",
            llm_tier="free",
        )

def test_production_allows_paid_or_local_llm():
    s_paid = Settings(app_env="production", llm_provider="gemini", llm_tier="paid")
    assert s_paid.app_env == "production"
    s_local = Settings(app_env="production", llm_provider="ollama", llm_tier="free")
    assert s_local.llm_provider == "ollama"

def test_default_settings_and_as_of_date():
    s = Settings(_env_file=None)
    assert s.data_profile in ("real", "synth")
    assert s.as_of_date == date(2026, 7, 31)

def test_rbac_allowed_views_match_spec_section_11_9():
    assert get_allowed_views("ceo") == {
        "ai_v_no_vay", "ai_v_dong_tien", "ai_v_bctc",
        "ai_v_ton_kho", "ai_v_cong_no", "ai_v_tien_gui", "ai_v_ke_hoach",
    }
    assert get_allowed_views("ke_toan_truong") == {
        "ai_v_no_vay", "ai_v_dong_tien", "ai_v_bctc",
        "ai_v_cong_no", "ai_v_tien_gui", "ai_v_ke_hoach",
    }
    assert get_allowed_views("quan_ly_kho") == {"ai_v_ton_kho"}
    assert get_allowed_views("quan_tri_he_thong") == set()

def test_sanitize_db_error_strips_silver_and_credentials():
    raw = 'OperationalError: connection to "postgresql://postgres:secret123@localhost:5432/gml" failed: relation "silver.fact_cashflow" does not exist at D:\\secret\\path.py'
    cleaned = sanitize_db_error(raw)
    assert "secret123" not in cleaned
    assert "silver." not in cleaned
    assert "D:\\secret" not in cleaned
```

- [ ] **Step 3: Chạy pytest để xác nhận test fail**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_config.py" -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.core.config'`

- [ ] **Step 4: Triển khai `errors.py`, `config.py`, và `security.py`**

- Trong `v2/app/core/errors.py`: Định nghĩa `UnsafeDeploymentError`, `SqlRejected`, `DbExecutionError`, và hàm `sanitize_db_error(err: Exception | str) -> str` dùng regex che URI `postgresql(?:\+\w+)?://[^\s"']+`, thay `silver\.` (case-insensitive) bằng `[REDACTED_SCHEMA].`, và xoá đường dẫn tệp.
- Trong `v2/app/core/config.py`: Định nghĩa `Settings(BaseSettings)` với `model_validator(mode="after")` ném `UnsafeDeploymentError` khi `app_env == "production" and llm_provider != "ollama" and llm_tier == "free"`.
- Trong `v2/app/core/security.py`: Định nghĩa `load_catalog()` và `get_allowed_views(role: str) -> set[str]`.

- [ ] **Step 5: Chạy lại unit test xác nhận PASS**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_config.py" -v`
Expected: PASS (5/5 tests passed)

- [ ] **Step 6: Commit Task 1**

```bash
git add "7. AI-Business-Assistant/v2"
git commit -m "feat(v2-p1): add config, security RBAC catalog, and production safety gate (TC-T5-09)"
```

---

### Task 2: Triển khai Bộ Kiểm tra AST SQL (`sqlglot`) & Allowlist theo Vai trò (`TC-T3-01…03`)

**Files:**
- Create: `7. AI-Business-Assistant/v2/app/sql/__init__.py`
- Create: `7. AI-Business-Assistant/v2/app/sql/validator.py`
- Test: `7. AI-Business-Assistant/v2/tests/unit/test_sql_validator.py`

**Interfaces:**
- Consumes:
  - `app.core.errors.SqlRejected`
  - `app.core.security.get_allowed_views(role: str) -> set[str]`
- Produces:
  - `app.sql.validator.FORBIDDEN_FUNCS: set[str]`
  - `app.sql.validator.validate(sql: str, allowed_tables: set[str], max_rows: int = 1000) -> str`
  - `app.sql.validator.validate_for_role(sql: str, role: str, max_rows: int = 1000) -> str`

- [ ] **Step 1: Viết failing unit test trong `v2/tests/unit/test_sql_validator.py`**

```python
import pytest
from app.core.errors import SqlRejected
from app.sql.validator import validate, validate_for_role

CEO_VIEWS = {
    "ai_v_no_vay", "ai_v_dong_tien", "ai_v_bctc",
    "ai_v_ton_kho", "ai_v_cong_no", "ai_v_tien_gui", "ai_v_ke_hoach",
}

@pytest.mark.parametrize("bad_sql", [
    "DELETE FROM ai_v_no_vay",
    "UPDATE ai_v_no_vay SET principal_balance = 0",
    "DROP TABLE ai_v_no_vay",
    "INSERT INTO ai_v_no_vay VALUES (1)",
    "SELECT * FROM ai_v_no_vay; DROP TABLE ai_v_no_vay;",
    "SELECT pg_sleep(20) FROM ai_v_no_vay",
    "SELECT pg_read_file('/etc/passwd') FROM ai_v_no_vay",
    "WITH d AS (DELETE FROM ai_v_no_vay RETURNING *) SELECT * FROM d",
])
def test_tc_t3_01_validator_blocks_destructive_multi_and_forbidden_funcs(bad_sql):
    """TC-T3-01: DELETE, UPDATE, multi-statement, pg_sleep -> SqlRejected."""
    with pytest.raises(SqlRejected):
        validate(bad_sql, allowed_tables=CEO_VIEWS)

def test_tc_t3_02_validator_blocks_disallowed_table_for_role():
    """TC-T3-02: Role quan_ly_kho querying ai_v_no_vay -> SqlRejected."""
    with pytest.raises(SqlRejected, match="ai_v_no_vay"):
        validate_for_role("SELECT * FROM ai_v_no_vay", role="quan_ly_kho")

    # Allowed view for quan_ly_kho succeeds:
    out = validate_for_role("SELECT * FROM ai_v_ton_kho", role="quan_ly_kho")
    assert "ai_v_ton_kho" in out.lower()

def test_tc_t3_02_validator_blocks_raw_silver_schema_even_for_ceo():
    """Review Focus #1: Direct access to silver.* or pg_catalog.* is always rejected."""
    with pytest.raises(SqlRejected):
        validate("SELECT * FROM silver.fact_cashflow", allowed_tables=CEO_VIEWS)
    with pytest.raises(SqlRejected):
        validate("SELECT * FROM silver.ai_v_no_vay", allowed_tables=CEO_VIEWS)

def test_tc_t3_03_validator_enforces_and_caps_limit():
    """TC-T3-03 & Review Focus #2: Missing LIMIT gets added; excessive LIMIT gets capped."""
    sql_no_limit = "SELECT bank_code, granted_limit FROM ai_views.ai_v_no_vay"
    out = validate(sql_no_limit, allowed_tables=CEO_VIEWS, max_rows=1000)
    assert "LIMIT 1000" in out.upper()

    sql_huge_limit = "SELECT bank_code FROM ai_v_no_vay LIMIT 50000"
    out_capped = validate(sql_huge_limit, allowed_tables=CEO_VIEWS, max_rows=1000)
    assert "LIMIT 1000" in out_capped.upper()

def test_validator_allows_cte_and_subqueries_on_allowed_views():
    sql = """
    WITH latest AS (
        SELECT bank_code, principal_balance
        FROM ai_views.ai_v_no_vay
    )
    SELECT bank_code, SUM(principal_balance) AS total
    FROM latest
    GROUP BY bank_code
    LIMIT 10
    """
    out = validate(sql, allowed_tables=CEO_VIEWS)
    assert "LIMIT 10" in out.upper()
```

- [ ] **Step 2: Chạy pytest để xác nhận test fail**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_sql_validator.py" -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.sql'`

- [ ] **Step 3: Triển khai `v2/app/sql/validator.py`**

Triển khai `validate(sql: str, allowed_tables: set[str], max_rows: int = 1000) -> str` và `validate_for_role(sql: str, role: str, max_rows: int = 1000) -> str`:
1. Kiểm tra chuỗi không rỗng; dùng `sqlglot.parse(sql, read="postgres")` (bắt `sqlglot.errors.ParseError` -> ném `SqlRejected`).
2. Chỉ chấp nhận đúng 1 câu lệnh và gốc AST phải là `exp.Select` hoặc `exp.Union` (mà mọi nhánh đều là `exp.Select`).
3. Duyệt toàn bộ cây AST chặn mọi node DML/DDL/Transaction (`exp.Insert`, `exp.Update`, `exp.Delete`, `exp.Drop`, `exp.Create`, `exp.Alter`, `exp.Command`, `exp.Transaction`, `exp.Commit`, `exp.Rollback`, `exp.Grant`, `exp.Revoke`, `exp.Into`, `exp.Lock`).
4. Thu thập tập tên CTE (`{c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}`). Với mỗi `t` trong `tree.find_all(exp.Table)`:
   - Nếu `t.name.lower()` nằm trong `cte_names` và không có `t.db`: hợp lệ (là CTE).
   - Nếu `t.db` khác rỗng và `t.db.lower() != "ai_views"`: ném `SqlRejected(f"Schema không được phép: {t.db}")`.
   - Nếu `t.name.lower()` không thuộc `allowed_tables`: ném `SqlRejected(f"Bảng không được phép: {t.name}")`.
5. Kiểm tra tất cả `exp.Func` và `exp.Anonymous`: tên hàm (lowercase) không được nằm trong `FORBIDDEN_FUNCS = {"pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export", "dblink", "dblink_exec", "query_to_xml"}`. Ngoài ra dùng regex kiểm tra tên hàm trong raw SQL phòng trường hợp `sqlglot` parse `pg_sleep` thành kiểu đặc biệt.
6. Kiểm tra `LIMIT`: nếu chưa có `limit`, gọi `tree = tree.limit(max_rows)`. Nếu đã có `limit` mà giá trị số `> max_rows`, cập nhật về `max_rows`.
7. Trả về `tree.sql(dialect="postgres")`.

- [ ] **Step 4: Chạy lại unit test xác nhận PASS**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_sql_validator.py" -v`
Expected: PASS (12/12 tests passed)

- [ ] **Step 5: Commit Task 2**

```bash
git add "7. AI-Business-Assistant/v2/app/sql" "7. AI-Business-Assistant/v2/tests/unit/test_sql_validator.py"
git commit -m "feat(v2-p1): implement sqlglot AST validator and RBAC view allowlist (TC-T3-01..03)"
```

---

### Task 3: Triển khai Đồ thị Điều phối T4 (`StateGraph`) & Sửa lỗi Nhánh Song song `both` (`TC-T4-01…02`)

**Files:**
- Create: `7. AI-Business-Assistant/v2/app/orchestration/__init__.py`
- Create: `7. AI-Business-Assistant/v2/app/orchestration/state.py`
- Create: `7. AI-Business-Assistant/v2/app/orchestration/routing.py`
- Create: `7. AI-Business-Assistant/v2/app/orchestration/graph.py`
- Test: `7. AI-Business-Assistant/v2/tests/unit/test_orchestration_routing.py`

**Interfaces:**
- Consumes: `langgraph.graph.StateGraph`, `START`, `END`.
- Produces:
  - `app.orchestration.state.Intent = Literal["sql_only", "rag_only", "both", "alert", "blocked"]`
  - `app.orchestration.state.ChatState(TypedDict, total=False)`
  - `app.orchestration.routing.route_after_intent(state: ChatState) -> list[str]`
  - `app.orchestration.routing.route_after_join(state: ChatState) -> list[str]`
  - `app.orchestration.routing.route_after_confidence(state: ChatState) -> str`
  - `app.orchestration.graph.build_graph(node_overrides: dict[str, Callable] | None = None)`

- [ ] **Step 1: Viết failing unit test trong `v2/tests/unit/test_orchestration_routing.py`**

```python
from app.orchestration.graph import build_graph

def test_tc_t4_01_both_intent_runs_sql_and_rag_in_parallel():
    """TC-T4-01: Bug v1 fix — intent 'both' must populate BOTH sql and rag in final state."""
    join_count = 0

    def fake_classify(state):
        return {"intent": "both", "kpi_keys": ["du_no_ngan_han"]}

    def fake_sql(state):
        return {"sql": {"sql": "SELECT 1", "rows": [{"val": 236065233815}], "row_count": 1, "status": "ok", "confidence": 0.95}}

    def fake_rag(state):
        return {"rag": {"chunks": ["Định nghĩa dư nợ ngắn hạn"], "sources": ["guide_dashboard1.md"], "grounding_ok": True}}

    def spy_join(state):
        nonlocal join_count
        join_count += 1
        return {}

    app = build_graph({
        "classify_intent": fake_classify,
        "sql_lookup": fake_sql,
        "rag_lookup": fake_rag,
        "join": spy_join,
    })

    final_state = app.invoke({
        "request_id": "req-001",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Vì sao đang vay đắt mà gửi rẻ?",
    })

    assert final_state.get("sql") is not None and final_state["sql"]["row_count"] == 1
    assert final_state.get("rag") is not None and len(final_state["rag"]["chunks"]) == 1
    assert join_count == 1

def test_tc_t4_02_sql_only_does_not_run_rag_and_join_runs_once():
    """TC-T4-02: 'sql_only' does not run RAG; 'join' runs exactly once."""
    join_count = 0
    rag_called = False

    def fake_classify(state):
        return {"intent": "sql_only", "kpi_keys": []}

    def fake_sql(state):
        return {"sql": {"sql": "SELECT 1", "rows": [{"val": 1}], "row_count": 1, "status": "ok", "confidence": 0.9}}

    def spy_rag(state):
        nonlocal rag_called
        rag_called = True
        return {"rag": {"chunks": ["should not run"]}}

    def spy_join(state):
        nonlocal join_count
        join_count += 1
        return {}

    app = build_graph({
        "classify_intent": fake_classify,
        "sql_lookup": fake_sql,
        "rag_lookup": spy_rag,
        "join": spy_join,
    })

    final_state = app.invoke({
        "request_id": "req-002",
        "user": {"id": "u1", "role": "ceo"},
        "session_id": "s1",
        "query": "Dư nợ ngắn hạn là bao nhiêu?",
    })

    assert not rag_called
    assert "rag" not in final_state or not final_state.get("rag")
    assert final_state.get("sql", {}).get("status") == "ok"
    assert join_count == 1
```

- [ ] **Step 2: Chạy pytest để xác nhận test fail**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_orchestration_routing.py" -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.orchestration'`

- [ ] **Step 3: Triển khai `state.py`, `routing.py`, và `graph.py`**

- Trong `v2/app/orchestration/state.py`: Khai báo `Intent` và `ChatState(TypedDict, total=False)` theo đúng Phần II §5 của Spec (`errors: Annotated[list[str], operator.add]`, `trace: Annotated[list[dict], operator.add]`).
- Trong `v2/app/orchestration/routing.py`: Khai báo `route_after_intent(state: ChatState) -> list[str]`, `route_after_join(state: ChatState) -> list[str]`, và `route_after_confidence(state: ChatState) -> str`.
- Trong `v2/app/orchestration/graph.py`: Xây dựng `build_graph(node_overrides: dict | None = None)` với các node chuẩn: `guard_input`, `resolve_context`, `classify_intent`, `sql_lookup`, `rag_lookup`, `alert_summary`, `join`, `explain`, `trend`, `advise`, `confidence_gate`, `clarify`, `synthesize`, `guard_output`. Cho phép truyền `node_overrides` để test độc lập từng node và kiểm chứng luồng song song.

- [ ] **Step 4: Chạy lại unit test xác nhận PASS**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_orchestration_routing.py" -v`
Expected: PASS (2/2 tests passed)

- [ ] **Step 5: Commit Task 3**

```bash
git add "7. AI-Business-Assistant/v2/app/orchestration" "7. AI-Business-Assistant/v2/tests/unit/test_orchestration_routing.py"
git commit -m "feat(v2-p1): implement LangGraph orchestration with parallel 'both' routing (TC-T4-01..02)"
```

---

### Task 4: Triển khai Tầng Dữ liệu T1 (`roles.sql`, `views.sql.j2`, `migrations`, `apply_db.py`) & Kiểm thử Tích hợp xuất Bằng chứng `EV-01`, `EV-02` (`TC-T1-01…04`)

**Files:**
- Create: `7. AI-Business-Assistant/v2/db/roles.sql`
- Create: `7. AI-Business-Assistant/v2/db/views.sql.j2`
- Create: `7. AI-Business-Assistant/v2/db/migrations/001_init_app_schema.sql`
- Create: `7. AI-Business-Assistant/v2/db/apply_db.py`
- Test: `7. AI-Business-Assistant/v2/tests/integration/test_db_t1.py`
- Output Evidence:
  - `7. AI-Business-Assistant/v2/eval/reports/t1_permissions.txt` (`EV-01`)
  - `7. AI-Business-Assistant/v2/eval/reports/t1_views_vs_uat.csv` (`EV-02`)

**Interfaces:**
- Consumes:
  - PostgreSQL local database `gml` (schema `silver`)
  - `app.core.config.Settings`
  - `app.core.errors.sanitize_db_error`
- Produces:
  - PostgreSQL roles `gml_ai_ro` (read-only on `ai_views.*`, `statement_timeout = '15s'`, `default_transaction_read_only = on`, zero privileges on `silver.*`) and `gml_ai_app` (read/write on `app.*`).
  - Schema `ai_views` với 7 view chuẩn hoá:
    1. `ai_views.ai_v_no_vay`: Kết hợp dữ liệu hạn mức (`fact_creditlimitsummary`), tài sản bảo đảm (`fact_collateral`), khế ước vay (`fact_loan`) và số dư các tiểu khoản vay (`34111%`, `34112%`, `34113%`, `34114%`, `3412%`, `341%` từ `fact_cashflow` lọc `posting_date <= '{{ as_of_date }}'`), phân biệt theo cột `record_type` (`'credit_limit'`, `'collateral'`, `'loan_contract'`, `'ledger_balance'`).
    2. `ai_views.ai_v_dong_tien`: Các bút toán từ `fact_cashflow` kết hợp `dim_account` và `dim_accountnumber` (lọc `posting_date <= '{{ as_of_date }}'`), kèm cờ `is_external_cashflow` (loại trừ `CTNB%`, `NTTK%` và đối ứng `111%`/`112%`).
    3. `ai_views.ai_v_bctc`: Kết hợp Bảng cân đối kế toán (`fact_balancesheet`, `report_type = 'B01-DN'`) và Báo cáo KQKD (`fact_incomestatement`, `report_type = 'B02-DN'`) kèm `dim_reportitem`, lọc kỳ `<= '{{ as_of_date }}'`.
    4. `ai_views.ai_v_ton_kho`: Kết hợp số dư tồn kho (`fact_inventory_balance`, `record_type = 'balance'`), nhập kho (`fact_inventoryinward`, `record_type = 'inward'`), xuất kho (`fact_inventoryoutward`, `record_type = 'outward'`) kèm `dim_product` và `dim_warehouse`, lọc ngày `<= '{{ as_of_date }}'`.
    5. `ai_views.ai_v_cong_no`: Kết hợp công nợ phải thu (`fact_accountsreceivable`, `ar_ap_type = 'AR'`) và phải trả (`fact_accountspayable`, `ar_ap_type = 'AP'`) kèm `dim_partner` và cờ `is_latest_partner_tx` (`rn = 1` theo `partner_code` sắp xếp `posting_date DESC, id DESC`), lọc `posting_date <= '{{ as_of_date }}'`.
    6. `ai_views.ai_v_tien_gui`: Các hợp đồng tiền gửi từ `fact_termdeposit` kèm cờ `is_active_at_cutoff` (`deposit_date <= '{{ as_of_date }}' AND (settlement_date > '{{ as_of_date }}' OR settlement_date IS NULL)`).
    7. `ai_views.ai_v_ke_hoach`: Kế hoạch kinh doanh từ `fact_businessplan` kèm `dim_reportitem`.
  - Schema `app` với 5 bảng: `app.chat_turn`, `app.audit_log`, `app.alert_event`, `app.feedback`, `app.job_heartbeat`.
  - Hàm `db.apply_db.apply_all(admin_url: str, source_schema: str = "silver", as_of_date: str = "2026-07-31") -> None` và `db.apply_db.GOLD_UAT_QUERIES: list[dict]`.

- [ ] **Step 1: Tạo `v2/db/roles.sql`, `v2/db/views.sql.j2`, `v2/db/migrations/001_init_app_schema.sql`, và `v2/db/apply_db.py`**

Trong `v2/db/apply_db.py`, định nghĩa danh sách `GOLD_UAT_QUERIES` gồm 13 chỉ tiêu vàng G-01…G-13 từ §6 của Spec truy vấn trực tiếp trên `ai_views.*`:
- `G-01` (Dư nợ ngắn hạn): `236065233815.0`
- `G-02` (Dư nợ dài hạn): `51174925843.0`
- `G-03` (Hạn mức được phê duyệt): `485000000000.0`
- `G-04` (Hạn mức được cấp): `295000000000.0`
- `G-05` (Hạn mức còn lại): `24135521634.0`
- `G-06` (LTV): `0.71290863549`
- `G-07` (Tiền và tương đương tiền): `91976722608.0`
- `G-08` (Tiền gửi còn hiệu lực): `40514952541.0`
- `G-09` (Số hợp đồng tiền gửi còn hiệu lực): `22.0`
- `G-10` (Lãi suất tiền gửi bình quân): `0.049896752996`
- `G-11` (Thu nhập lãi TK 515): `1482534625.0`
- `G-12` (Dư nợ gốc trên hạn mức `SUM(principal_balance)`): `270864478366.0`
- `G-13` (Tỷ lệ sử dụng hạn mức `G-12 / G-04`): `0.918184672427`

- [ ] **Step 2: Viết integration test trong `v2/tests/integration/test_db_t1.py`**

```python
import pytest
import sqlalchemy as sa
from pathlib import Path
from db.apply_db import apply_all, get_ro_engine, get_admin_engine, GOLD_UAT_QUERIES, generate_t1_evidence

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    apply_all()

def test_tc_t1_01_ro_role_cannot_write():
    """TC-T1-01: gml_ai_ro cannot INSERT/UPDATE/DELETE/DROP/CREATE."""
    ro_engine = get_ro_engine()
    for stmt in [
        "CREATE TABLE ai_views.hack_test (id int)",
        "DROP VIEW ai_views.ai_v_no_vay",
        "DELETE FROM ai_views.ai_v_no_vay",
    ]:
        with pytest.raises(Exception) as exc_info:
            with ro_engine.connect() as conn:
                conn.execute(sa.text(stmt))
                conn.commit()
        err_text = str(exc_info.value).lower()
        assert "permission denied" in err_text or "read-only" in err_text or "cannot" in err_text

def test_tc_t1_02_ro_role_cannot_read_raw_silver_schema():
    """TC-T1-02: SELECT * FROM silver.fact_cashflow by gml_ai_ro -> permission denied."""
    ro_engine = get_ro_engine()
    with pytest.raises(Exception) as exc_info:
        with ro_engine.connect() as conn:
            conn.execute(sa.text("SELECT * FROM silver.fact_cashflow LIMIT 1"))
    assert "permission denied" in str(exc_info.value).lower()

def test_tc_t1_03_ro_role_statement_timeout():
    """TC-T1-03: statement_timeout is configured <= 15s and cancels long queries."""
    ro_engine = get_ro_engine()
    with ro_engine.connect() as conn:
        timeout_val = conn.execute(sa.text("SHOW statement_timeout")).scalar()
        assert timeout_val == "15s"
        # Verify cancellation using short local timeout (1s) so test suite stays fast while proving enforcement
        with pytest.raises(Exception) as exc_info:
            conn.execute(sa.text("SELECT pg_sleep(16)"))
        assert "statement timeout" in str(exc_info.value).lower() or "canceled" in str(exc_info.value).lower()

def test_tc_t1_04_views_match_uat_gold_answers():
    """TC-T1-04: Run golden queries on ai_views for G-01..G-13 with relative error <= 1e-4."""
    ro_engine = get_ro_engine()
    with ro_engine.connect() as conn:
        for item in GOLD_UAT_QUERIES:
            actual = float(conn.execute(sa.text(item["sql"])).scalar())
            expected = float(item["expected"])
            rel_err = abs(actual - expected) / max(abs(expected), 1e-9)
            assert rel_err <= 1e-4, f"{item['id']} ({item['name']}): actual={actual}, expected={expected}, rel_err={rel_err}"

def test_generate_ev01_and_ev02_evidence_files():
    """Verify EV-01 and EV-02 artefacts are generated and non-empty."""
    ev01_path, ev02_path = generate_t1_evidence()
    assert Path(ev01_path).exists() and Path(ev01_path).stat().st_size > 100
    assert Path(ev02_path).exists() and Path(ev02_path).stat().st_size > 100
```

- [ ] **Step 3: Chạy `apply_db.py` và chạy pytest cho `test_db_t1.py`**

Run: `pytest "7. AI-Business-Assistant/v2/tests/integration/test_db_t1.py" -v`
Expected: PASS (5/5 tests passed), đồng thời sinh ra 2 file bằng chứng:
- `7. AI-Business-Assistant/v2/eval/reports/t1_permissions.txt` (`EV-01`)
- `7. AI-Business-Assistant/v2/eval/reports/t1_views_vs_uat.csv` (`EV-02`)

- [ ] **Step 4: Chạy toàn bộ bộ test Phase 1 (Unit + Integration)**

Run: `pytest "7. AI-Business-Assistant/v2/tests" -v`
Expected: PASS 100% (`TC-T1-01…04`, `TC-T3-01…03`, `TC-T4-01…02`, `TC-T5-09`; `M-01 = 100%`, `M-02 = 0`).

- [ ] **Step 5: Commit Task 4**

```bash
git add "7. AI-Business-Assistant/v2/db" "7. AI-Business-Assistant/v2/eval/reports" "7. AI-Business-Assistant/v2/tests/integration/test_db_t1.py"
git commit -m "feat(v2-p1): implement T1 DB roles, ai_views, app migrations, and EV-01/EV-02 verification (TC-T1-01..04)"
```

