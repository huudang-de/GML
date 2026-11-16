# AI Business Assistant v2 — P1r (Sửa đổi Data & RBAC lõi cho DataAgent) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sửa đổi một lần duy nhất tầng T1 và lõi RBAC để phục vụ cả P4r lẫn P5: migration `002` (bảng `app.action_item`, `app.pinned_kpi`; cột bằng chứng/chống trùng/leo thang cho `app.alert_event`), `apply_db` chạy mọi migration, và hàm RBAC theo KPI dùng chung.

**Architecture:** Thay đổi chỉ chạm `db/` và `app/core/security.py`, cộng một refactor nhỏ ở `app/api/routers/alerts.py` để dùng hàm RBAC chung (hành vi giữ nguyên). Không thêm endpoint, không đổi UI.

**Tech Stack:** PostgreSQL, SQLAlchemy 2, pytest. Thư viện giữ nguyên như `requirements.txt` hiện tại.

**Spec:** `docs/plans/2026-11-15-dataagent-adoption-impact-analysis.md` (§2 R2–R4, R9; §3 D3–D6; §6; §7) + `docs/AI_Business_Assistant_v2_Architecture_Detail.md` §5 T1.

## Global Constraints

- **C0 / §11.7:** Toàn bộ code nằm trong `7. AI-Business-Assistant/v2/`. Không sửa `v1/`.
- Toàn bộ **137** test hiện có phải pass sau mỗi task.
- Migration chỉ dùng `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`, nên chạy lại nhiều lần vẫn an toàn (idempotent).
- `gml_ai_ro` **không** có quyền gì trên schema `app`. Chỉ `gml_ai_app` được ghi.
- Áp dụng trên cả hai hồ sơ dữ liệu `real` (`data_warehouse`) và `synth` (`gml_synth`). Không trộn dữ liệu giữa hai hồ sơ.

## Review Focus

1. **Chạy lại migration trên DB đã có dữ liệu `alert_event` cũ:** cột `dedup_key` mới là `NULL` cho các dòng cũ. Ràng buộc unique phải chấp nhận nhiều giá trị `NULL` (unique index thường của PostgreSQL đã cho phép), và migration không được thất bại.
2. **Thứ tự migration theo tên:** `apply_all` phải chạy `001` trước `002`. Sắp xếp theo `Path.name`, không theo thứ tự `glob` của hệ điều hành.
3. **`can_access_kpi` với KPI không tồn tại:** giữ đúng hành vi cũ của `_user_can_access_kpi` (chỉ `ceo` và `quan_tri_he_thong` được phép), để TC-T5 và Review Focus #5 của P4 không đổi.
4. **`kpi_domain` với `dashboard` lạ:** ném `ValueError`, không âm thầm trả `None`. Lint ở P2r dựa vào điều này.
5. **Ràng buộc `status` của `action_item`:** chỉ nhận `open`, `in_progress`, `done`, `dismissed`. Giá trị khác phải bị DB từ chối (dùng `CHECK`), không chỉ chặn ở API.

---

## File Map (P1r)

```text
7. AI-Business-Assistant/
├── docs/AI_Business_Assistant_v2_Architecture_Detail.md   # [Modify] Áp dụng §6 của impact analysis (T1..T7 + bản đồ tầng)
└── v2/
    ├── db/
    │   ├── migrations/002_dataagent_adoption.sql          # [Create]
    │   └── apply_db.py                                    # [Modify] apply_all chạy mọi file migrations/*.sql theo tên
    ├── app/core/security.py                               # [Modify] + can_access_kpi, kpi_domain, DOMAIN_BY_DASHBOARD
    ├── app/api/routers/alerts.py                          # [Modify] dùng can_access_kpi, xoá _user_can_access_kpi
    └── tests/
        ├── unit/test_security_kpi_rbac_p1r.py             # [Create]
        └── integration/test_db_migration_002_p1r.py       # [Create] TC-T1-08, TC-T1-09
```

---

### Task 1: Sửa spec kiến trúc

**Files:**
- Modify: `docs/AI_Business_Assistant_v2_Architecture_Detail.md` (§4 dòng 101; §5 T1 dòng 128 + bảng test; T2 dòng 160-184; T3 dòng 192-219; T5 dòng 258-272; T6 dòng 282-298; T7 dòng 304-324)

**Interfaces:** Không có (chỉ sửa tài liệu).

- [ ] **Step 1:** Chép nguyên văn từng gạch đầu dòng của impact analysis §6 và §7 vào đúng section tương ứng. Thêm một dòng tham chiếu `Xem thêm: docs/plans/2026-11-15-dataagent-adoption-impact-analysis.md` ở cuối §4.
- [ ] **Step 2:** Kiểm tra: `Select-String -Path docs\AI_Business_Assistant_v2_Architecture_Detail.md -Pattern "TC-T1-08|TC-T2-08|TC-T3-14|TC-T5-10|TC-T6-06|TC-T7-10"` phải ra đủ 6 dòng.
- [ ] **Step 3: Commit** `docs(v2-p1r): amend architecture spec for DataAgent adoption`

---

### Task 2: Migration 002 + `apply_all` chạy mọi migration

**Files:**
- Create: `v2/db/migrations/002_dataagent_adoption.sql`
- Modify: `v2/db/apply_db.py:250-255`
- Test: `v2/tests/integration/test_db_migration_002_p1r.py`

**Interfaces:**
- Produces (lược đồ DB mà P3r, P4r và P5 dùng):
  - `app.alert_event` + `period VARCHAR(7)`, `evidence JSONB`, `dedup_key VARCHAR(200)`, `escalated_at TIMESTAMP`. Unique index `uq_alert_event_dedup_key ON app.alert_event(dedup_key)`.
  - `app.action_item(id BIGSERIAL PK, title TEXT NOT NULL, kpi_key VARCHAR(100) NOT NULL, level VARCHAR(20) NOT NULL CHECK (level IN ('canh_bao','nghiem_trong')), source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('alert','chat')), source_ref VARCHAR(100) NOT NULL, assigned_role VARCHAR(50) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','done','dismissed')), due_date DATE, note TEXT, created_by VARCHAR(100) NOT NULL, created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now())`. Index trên `(assigned_role, status)` và `kpi_key`. Unique `(source_type, source_ref, title)` để không tạo trùng hành động.
  - `app.pinned_kpi(id BIGSERIAL PK, user_id VARCHAR(100) NOT NULL, data_profile VARCHAR(10) NOT NULL CHECK (data_profile IN ('real','synth')), kpi_key VARCHAR(100) NOT NULL, position INT NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT now(), UNIQUE (user_id, data_profile, kpi_key))`.
  - Cuối file `GRANT ALL PRIVILEGES` trên bảng và sequence cho `gml_ai_app`, giống `001`.

- [ ] **Step 1: Viết test lỗi**

```python
APP_COLUMNS = {"period", "evidence", "dedup_key", "escalated_at"}

def test_tc_t1_08_migration_002_idempotent_and_schema():
    apply_all(); apply_all()  # chạy 2 lần không lỗi
    with get_admin_engine().connect() as c:
        cols = {r[0] for r in c.execute(sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='app' AND table_name='alert_event'"))}
        assert APP_COLUMNS <= cols
        tables = {r[0] for r in c.execute(sa.text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='app'"))}
        assert {"action_item", "pinned_kpi"} <= tables

def test_action_item_status_check_rejects_unknown():
    with pytest.raises(Exception):
        with get_app_engine().begin() as c:
            c.execute(sa.text("INSERT INTO app.action_item (title,kpi_key,level,source_type,source_ref,"
                              "assigned_role,status,created_by) VALUES ('x','k','canh_bao','alert','1','ceo','hack','u')"))

def test_alert_dedup_key_unique_but_nulls_allowed():
    # chèn 2 dòng dedup_key NULL → OK; 2 dòng cùng dedup_key 'T:k:2026-07' → lần 2 lỗi IntegrityError
    ...

def test_tc_t1_09_ro_role_cannot_touch_new_tables():
    for stmt in ("SELECT 1 FROM app.action_item", "INSERT INTO app.pinned_kpi (user_id,data_profile,kpi_key) VALUES ('u','real','k')"):
        with pytest.raises(Exception) as e:
            with get_ro_engine().connect() as c:
                c.execute(sa.text(stmt)); c.commit()
        assert "permission denied" in str(e.value).lower()
```

Test dọn dữ liệu bằng `DELETE … WHERE created_by='u' OR rule_id LIKE 'TEST_%'` ở fixture teardown.

- [ ] **Step 2:** Chạy `pytest tests/integration/test_db_migration_002_p1r.py -v` → FAIL (thiếu cột/bảng).
- [ ] **Step 3:** Viết `002_dataagent_adoption.sql`. Trong `apply_all`, thay khối 3 bằng vòng lặp `for mig_path in sorted((DB_DIR / "migrations").glob("*.sql"), key=lambda p: p.name)`, mỗi file chạy trong một `connect()` + `commit()`.
- [ ] **Step 4:** Chạy lại test → PASS. Chạy `pytest tests/integration/test_db_t1.py -v` → PASS (không hồi quy).
- [ ] **Step 5:** Áp dụng lên hồ sơ `synth` theo đúng cách Phase 1 đã làm cho `gml_synth`, rồi chạy `pytest tests/integration/test_synthetic_t1.py -v` → PASS.
- [ ] **Step 6: Commit** `feat(v2-p1r): add migration 002 (action_item, pinned_kpi, alert evidence/dedup) and ordered migration runner`

---

### Task 3: RBAC theo KPI dùng chung

**Files:**
- Modify: `v2/app/core/security.py`
- Modify: `v2/app/api/routers/alerts.py:23,29-37,65,131`
- Test: `v2/tests/unit/test_security_kpi_rbac_p1r.py`

**Interfaces:**
- Produces:
  - `DOMAIN_BY_DASHBOARD: dict[str, str] = {"D1": "no_vay", "D2": "kho", "D3": "cong_no", "D4": "tien_gui", "D5": "dong_tien"}`
  - `can_access_kpi(role: str, kpi_key: str) -> bool`: dùng `get_kpi(kpi_key).nguon_view ⊆ get_allowed_views(role)`. Nếu `KeyError` → `role in ("ceo", "quan_tri_he_thong")`.
  - `kpi_domain(kpi_key: str) -> str`: tra `DOMAIN_BY_DASHBOARD[get_kpi(kpi_key).dashboard]`. Dashboard lạ → `ValueError`.
  - Import `get_kpi` **bên trong hàm** để tránh vòng import (`knowledge.loader` có thể import `core`).

- [ ] **Step 1: Viết test lỗi**

```python
@pytest.mark.parametrize("role,kpi,ok", [
    ("ceo", "du_no_ngan_han", True),
    ("ke_toan_truong", "du_no_ngan_han", True),
    ("quan_ly_kho", "du_no_ngan_han", False),
    ("quan_ly_kho", "gia_tri_hang_ton_kho", True),
    ("quan_ly_kho", "vong_quay_hang_ton_kho", False),   # R9: cần ai_v_bctc
    ("ke_toan_truong", "gia_tri_hang_ton_kho", False),
    ("quan_tri_he_thong", "du_no_ngan_han", False),
    ("ceo", "khong_ton_tai", True),
    ("quan_ly_kho", "khong_ton_tai", False),
])
def test_can_access_kpi(role, kpi, ok):
    assert can_access_kpi(role, kpi) is ok

def test_kpi_domain_maps_all_28_kpis():
    assert kpi_domain("du_no_ngan_han") == "no_vay"
    assert kpi_domain("gia_tri_hang_ton_kho") == "kho"
    assert kpi_domain("gia_tri_phai_thu") == "cong_no"
    assert kpi_domain("tien_gui_co_ky_han") == "tien_gui"
    assert kpi_domain("dong_tien_rong") == "dong_tien"
    assert all(kpi_domain(k) for k in load_kpis())

def test_kpi_domain_unknown_dashboard_raises(monkeypatch):
    # monkeypatch get_kpi để trả KpiDefinition có dashboard="D9" → ValueError
    ...
```

- [ ] **Step 2:** Chạy `pytest tests/unit/test_security_kpi_rbac_p1r.py -v` → FAIL (ImportError).
- [ ] **Step 3:** Thêm 3 symbol vào `security.py`. Trong `alerts.py`, đổi hai chỗ gọi sang `can_access_kpi` và xoá `_user_can_access_kpi` cùng import `get_kpi` không còn dùng.
- [ ] **Step 4:** Chạy test mới, `tests/unit/test_api_core_and_resources_t5.py` và `tests/integration/test_api_contract_t5.py` → PASS.
- [ ] **Step 5:** Chạy toàn bộ `pytest -q` → **137 + test mới** đều pass.
- [ ] **Step 6: Commit** `refactor(v2-p1r): centralize KPI-level RBAC and domain mapping in core.security`

---

## Cổng hoàn tất P1r

- [ ] `pytest -q` xanh toàn bộ, trên cả hai hồ sơ đã migrate.
- [ ] `eval/reports/t1_permissions.txt` (EV-01) được tạo lại bằng `generate_t1_evidence()` và không có lệnh ghi nào lọt qua (M-02 = 0).
- [ ] Không có file nào ngoài File Map bị sửa (`git diff --stat`).
