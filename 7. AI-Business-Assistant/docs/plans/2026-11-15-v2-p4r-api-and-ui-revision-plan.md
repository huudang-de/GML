# AI Business Assistant v2 — P4r (Sửa đổi API + UI theo DataAgent) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa 6 tính năng F1–F6 lên dịch vụ `/v1` và giao diện Streamlit: Tổng quan theo vai trò, KPI có sparkline/delta, Cảnh báo Master–Detail có bằng chứng, Chat giàu thông tin + câu hỏi gợi ý, Hành động, Ghim KPI. Mọi endpoint mới có RBAC, audit, contract test và có trong OpenAPI snapshot.

**Architecture:** Logic tính KPI chuyển từ router sang `app/services/kpi_service.py`. `app/services/briefing.py` dựng Tổng quan. Router `kpi`, `overview` và sau này P5 `weekly_brief` cùng gọi hai service này. Router mới: `overview`, `actions`, `pins`. UI thêm 2 màn (`Tổng quan`, `Hành động`), nâng cấp `alert_center` và `chat_view`, và vẫn **chỉ** giao tiếp qua `HttpApiClient`.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, Streamlit (`st.metric`, `st.line_chart`, `st.columns`, `st.pills`/`st.button`), httpx, Streamlit `AppTest`.

**Spec:** `docs/plans/2026-11-15-dataagent-adoption-impact-analysis.md` (toàn bộ; đặc biệt §2 R4–R8, §3 D5–D9, §6 phần T5/T6) + Architecture §5 T5, T6.

## Global Constraints

- **Lỗi thống nhất (§6.8):** mọi lỗi mới (`403`, `404`, `409`, `422`) trả `{"error": {"code", "message", "request_id"}}` qua `ApiException`.
- **M-13 = 100%:** mọi endpoint mới có contract test trong `tests/integration/test_api_contract_p4r.py`.
- **M-14 = 100%:** mọi request nghiệp vụ, kể cả bị `403`/`404`/`409`, đều ghi `app.audit_log`. Không lưu giá trị KPI, `title`, `note` hay bằng chứng vào audit. Chỉ lưu `query` = method + path và `views_accessed`.
- **RBAC trước dữ liệu:** kiểm tra `can_access_kpi` trước khi tra cache, đọc DB hoặc ghi DB.
- **Tách hồ sơ dữ liệu:** `pinned_kpi.data_profile`, cache và engine đều theo `target_profile`. Hồ sơ `synth` luôn có `"SYNTHETIC_DATA"` trong `warnings` của mọi response mới.
- **Tương thích ngược:** `GET /v1/kpi/{key}` không có `include` phải trả **đúng** payload cũ. Mọi trường mới trong schema là tuỳ chọn và có mặc định. Toàn bộ test P1–P4 + P1r–P3r phải pass.
- **UI chỉ qua HTTP:** `app/ui/**` không được import `app.services`, `app.agents`, `app.knowledge` hay `db`.

## Review Focus

1. **Tạo hành động trên cảnh báo/lượt chat của người khác:** `quan_ly_kho` gửi `source_type="alert", source_ref=<id cảnh báo nợ vay>` → `403` (vì KPI). `ke_toan_truong` gửi `source_type="chat", source_ref=<request_id của ceo>` → `404` (không lộ là có tồn tại), vì truy vấn `app.chat_turn` phải lọc `request_id = :rid AND user_id = :uid`.
2. **Hành động không thuộc danh sách đã duyệt:** `title` khác văn bản của `business_rules.yaml` → `422 ACTION_NOT_APPROVED`. Trùng `(source_type, source_ref, title)` → `409 ACTION_DUPLICATE`.
3. **Ghim rồi mất quyền / đổi hồ sơ:** pin của `ceo` trên `real` không xuất hiện ở `synth`. Pin trên KPI mà vai trò không còn quyền thì bị bỏ khỏi thẻ Tổng quan, không trả `403` cho cả trang.
4. **Một KPI lỗi trong Tổng quan** (golden query lỗi/`no_data`) → `/v1/overview` vẫn `200`. Thẻ KPI đó có `error`, các thẻ khác bình thường (TC-T5-12).
5. **Quick Ask từ Power BI sau khi đổi màn mặc định:** URL có `kpi=` hoặc `dashboard=` phải mở màn Chat với câu hỏi điền sẵn như trước. Không có tham số thì mở Tổng quan (TC-T6-06).

---

## File Map (P4r)

```text
7. AI-Business-Assistant/v2/
├── app/services/
│   ├── __init__.py                 # [Create]
│   ├── kpi_service.py              # [Create] compute_kpi_value, compute_kpi_series (cache + golden + audit-agnostic)
│   └── briefing.py                 # [Create] build_briefing
├── app/api/
│   ├── schemas.py                  # [Modify] KpiValueResponse+, AlertItem+, ChatResponse.kpi_keys, Overview*, Action*, Pin*
│   ├── main.py                     # [Modify] include overview, actions, pins routers
│   └── routers/
│       ├── kpi.py                  # [Modify] dùng kpi_service; ?include=series
│       ├── alerts.py               # [Modify] trả period/evidence/domain/escalated_at; lọc domain/severity/status
│       ├── chat.py                 # [Modify] trả kpi_keys
│       ├── overview.py             # [Create] GET /v1/overview
│       ├── actions.py              # [Create] GET/POST /v1/actions, PATCH /v1/actions/{id}
│       └── pins.py                 # [Create] GET/POST /v1/pins, DELETE /v1/pins/{kpi_key}
├── app/ui/
│   ├── api_client.py               # [Modify] + get_overview, get_kpi(include_series), list_alerts(filters), list/create/update_action, list/add/remove_pin
│   ├── streamlit_app.py            # [Modify] 5 màn; mặc định Tổng quan trừ Quick Ask; bỏ KPI_DISPLAY_NAMES; sửa DASHBOARD_LABELS
│   └── components/
│       ├── overview_view.py        # [Create]
│       ├── actions_view.py         # [Create]
│       ├── alert_center.py         # [Modify] Master–Detail
│       └── chat_view.py            # [Modify] metric cards, trend/advice mở sẵn, gợi ý, Ghim, Tạo hành động
├── scripts/capture_ui_screenshots.py   # [Modify] seed evidence bằng build_alert_evidence; chụp thêm 3 màn
├── docs/openapi.json                   # [Regenerate] EV-13
├── eval/reports/{api_contract.txt, audit_log_sample.json, ui_screens/}   # [Regenerate] EV-14, EV-15, EV-16
└── tests/
    ├── unit/test_services_p4r.py
    ├── unit/test_ui_streamlit_p4r.py
    └── integration/test_api_contract_p4r.py
```

---

### Task 1: `kpi_service` + `GET /v1/kpi/{key}?include=series`

**Files:**
- Create: `v2/app/services/__init__.py`, `v2/app/services/kpi_service.py`
- Modify: `v2/app/api/routers/kpi.py`, `v2/app/api/schemas.py:52-61`
- Test: `v2/tests/unit/test_services_p4r.py`, `v2/tests/integration/test_api_contract_p4r.py`

**Interfaces:**
- Consumes: `can_access_kpi` (P1r), `load_kpi_series` (P3r), `summarize_series` (P3r), `ScopedTTLCache.make_kpi_key`.
- Produces:
  - `class KpiForbidden(Exception)`, `class KpiNotFound(Exception)`, `class KpiComputationError(Exception)` trong `kpi_service.py`
  - `compute_kpi_value(key: str, role: str, profile: str, settings: Settings, cache: ScopedTTLCache) -> tuple[dict, str | None, list[str], float | None, bool]`, trả `(payload_như_cũ, sql_executed_hoặc_"[CACHE_HIT]", views, latency_ms, cached)`. Thứ tự: KPI tồn tại → RBAC → cache → golden query. Đây là thân hàm hiện tại tại `kpi.py:49-146`.
  - `compute_kpi_series(key: str, role: str, profile: str, settings: Settings, cache: ScopedTTLCache, limit: int = 12) -> SeriesSummary | None`. Khoá cache: `make_kpi_key(profile, role, f"{key}#series", str(settings.as_of_date))` (D9). Không có chuỗi → `None`.
  - `KpiValueResponse` thêm `series: list[dict] | None = None`, `previous_value: float | None = None`, `delta_pct: float | None = None`, `series_warning: str | None = None`.
  - Router: `include: Literal["series"] | None = Query(None)`, map `KpiForbidden→403 FORBIDDEN`, `KpiNotFound→404 KPI_NOT_FOUND`, `KpiComputationError→500 KPI_EXECUTION_FAILED`. Router vẫn tự ghi audit như cũ, mỗi request đúng 1 dòng.

- [ ] **Step 1: Viết test lỗi**

```python
def test_kpi_without_include_is_byte_compatible(client_ceo_synth):
    r = client_ceo_synth.get("/v1/kpi/du_no_ngan_han?profile=synth")
    assert r.status_code == 200
    body = r.json()
    assert body["series"] is None and body["delta_pct"] is None
    assert set(body) >= {"kpi_key","kpi_name","value","unit","as_of_date","data_profile","sql_executed","warnings","cached"}

def test_kpi_include_series_synth(client_ceo_synth):
    b = client_ceo_synth.get("/v1/kpi/du_no_ngan_han?profile=synth&include=series").json()
    assert len(b["series"]) <= 12 and b["series"][-1]["period"] == "2026-07"
    assert round(b["delta_pct"], 3) == -0.168          # 283,7 → 236,07 (TC-T4-06)
    assert "SYNTHETIC_DATA" in b["warnings"]

def test_series_cache_does_not_collide_with_value(cache):
    # gọi value rồi series với cùng key → 2 entry khác nhau trong cache (len(cache) == 2)
    ...

def test_kho_series_forbidden_before_cache(client_kho):
    assert client_kho.get("/v1/kpi/du_no_ngan_han?include=series").status_code == 403
```

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt.
- [ ] **Step 4:** Test mới + `tests/integration/test_api_contract_t5.py` + `tests/unit/test_api_core_and_resources_t5.py` → PASS (TC-T5-02, TC-T5-05, Review Focus #2 của P4 không đổi).
- [ ] **Step 5: Commit** `refactor(v2-p4r): extract kpi_service and add ?include=series with delta/sparkline`

---

### Task 2: Cảnh báo có bằng chứng + bộ lọc; Chat trả `kpi_keys`

**Files:**
- Modify: `v2/app/api/routers/alerts.py:40-98`, `v2/app/api/schemas.py:68-87`, `v2/app/api/routers/chat.py`
- Test: `v2/tests/integration/test_api_contract_p4r.py`

**Interfaces:**
- Consumes: cột `period`, `evidence`, `escalated_at` (P1r); `kpi_domain` (P1r).
- Produces:
  - `AlertItem` thêm `period: str | None = None`, `evidence: dict | None = None`, `domain: str | None = None`, `escalated_at: str | None = None`.
  - `GET /v1/alerts` thêm query `domain: str | None`, `severity: str | None`, `status: Literal["open","acked"] | None`. Lọc trong SQL với `severity`/`status`; lọc `domain` sau RBAC, trong Python. Thứ tự sắp xếp: chưa ack trước, rồi `nghiem_trong`/`critical` trước, rồi `created_at DESC`.
  - `ChatResponse.kpi_keys: list[str] = []`, lấy từ `ChatState` (giá trị đã ghi vào `app.chat_turn.kpi_keys`).

- [ ] **Step 1: Viết test lỗi**

```python
def test_alerts_include_evidence_and_domain(seed_alert_with_evidence, client_ceo):
    a = next(x for x in client_ceo.get("/v1/alerts").json()["alerts"] if x["rule_id"] == "TEST_AL")
    assert a["domain"] == "no_vay" and a["evidence"]["threshold_expr"] == ">= 0.90"

def test_alerts_filters(client_ceo):
    assert all(x["domain"] == "kho" for x in client_ceo.get("/v1/alerts?domain=kho").json()["alerts"])
    assert all(not x["is_acknowledged"] for x in client_ceo.get("/v1/alerts?status=open").json()["alerts"])

def test_alert_filters_do_not_bypass_rbac(client_kho):
    assert client_kho.get("/v1/alerts?domain=no_vay").json()["total"] == 0

def test_chat_returns_kpi_keys(client_ceo_synth_mock_llm):
    assert "du_no_ngan_han" in client_ceo_synth_mock_llm.post("/v1/chat", json={"query": "Dư nợ ngắn hạn?"}).json()["kpi_keys"]
```

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt. **Step 4:** Test + test P4 cũ → PASS.
- [ ] **Step 5: Commit** `feat(v2-p4r): alerts expose evidence/domain with filters; chat returns kpi_keys`

---

### Task 3: Hành động — `/v1/actions`

**Files:**
- Create: `v2/app/api/routers/actions.py`
- Modify: `v2/app/api/schemas.py`, `v2/app/api/main.py:168-174`
- Test: `v2/tests/integration/test_api_contract_p4r.py`

**Interfaces:**
- Consumes: `app.action_item` (P1r), `can_access_kpi` (P1r), `resolve_approved_action` (P3r).
- Produces:
  - `ActionCreateRequest(source_type: Literal["alert","chat"], source_ref: str, kpi_key: str, level: Literal["canh_bao","nghiem_trong"], title: str, due_date: date | None = None, note: str | None = Field(None, max_length=1000))`
  - `ActionItem(id: int, title: str, kpi_key: str, level: str, domain: str, source_type: str, source_ref: str, assigned_role: str, status: str, due_date: date | None, note: str | None, created_by: str, created_at: str, updated_at: str)`
  - `ActionListResponse(actions: list[ActionItem], total: int)`, `ActionUpdateRequest(status: Literal["open","in_progress","done","dismissed"] | None = None, note: str | None = Field(None, max_length=1000))`
  - `POST /v1/actions` → `201 ActionItem`. Thứ tự kiểm tra: `can_access_kpi` (403) → nguồn tồn tại và thuộc phạm vi (alert: `id` tồn tại và `kpi_key` khớp; chat: `chat_turn` có `request_id` **và** `user_id` của người gọi, và `kpi_key ∈ kpi_keys`) (404 `SOURCE_NOT_FOUND`) → `resolve_approved_action` (422 `ACTION_NOT_APPROVED`) → insert (trùng → 409 `ACTION_DUPLICATE`). `title` lưu bằng văn bản chuẩn trả về. `assigned_role` = `authority_role`.
  - `GET /v1/actions?status=` → chỉ trả mục mà `can_access_kpi(role, kpi_key)` đúng **và** (`role == "ceo"` hoặc `assigned_role == role` hoặc `created_by == user_id`).
  - `PATCH /v1/actions/{id}` → cùng điều kiện thấy được như trên, nếu không thì `404`. Cập nhật `status`/`note`/`updated_at`.

- [ ] **Step 1: Viết test lỗi** (Review Focus #1, #2; TC-T5-10, TC-T5-11)

```python
def test_create_action_from_alert_assigns_authority_role(client_ceo, seed_alert_id, approved_text_nt):
    r = client_ceo.post("/v1/actions", json={"source_type":"alert","source_ref":str(seed_alert_id),
        "kpi_key":"ty_le_su_dung_han_muc","level":"nghiem_trong","title":approved_text_nt})
    assert r.status_code == 201 and r.json()["assigned_role"] == "ceo" and r.json()["status"] == "open"

def test_tc_t5_10_kho_cannot_create_finance_action(client_kho, seed_alert_id, approved_text_nt):
    r = client_kho.post("/v1/actions", json={...})
    assert r.status_code == 403 and audit_rows_for(r.headers["X-Request-ID"]) == 1

def test_tc_t5_11_chat_source_of_other_user_is_404(client_ktt, ceo_request_id, approved_text_cb): ...
def test_unapproved_title_422_and_duplicate_409(client_ceo, ...): ...
def test_list_and_patch_visibility(client_ktt, client_kho, ...): ...
def test_audit_has_no_title_or_note(client_ceo, ...): ...   # app.audit_log.query không chứa title/note
```

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt. **Step 4:** Test → PASS.
- [ ] **Step 5: Commit** `feat(v2-p4r): add /v1/actions with approved-action validation, RBAC and audit (TC-T5-10, TC-T5-11)`

---

### Task 4: Ghim KPI — `/v1/pins`

**Files:**
- Create: `v2/app/api/routers/pins.py`
- Modify: `v2/app/api/schemas.py`, `v2/app/api/main.py`
- Test: `v2/tests/integration/test_api_contract_p4r.py`

**Interfaces:**
- Produces:
  - `PinRequest(kpi_key: str)`, `PinItem(kpi_key: str, position: int, created_at: str)`, `PinListResponse(pins: list[PinItem], total: int)`
  - `GET /v1/pins?profile=`: chỉ trả pin của `user_id` + `profile` mà vai trò còn quyền.
  - `POST /v1/pins`: KPI không tồn tại → 404. `can_access_kpi` sai → 403. Ghim lại KPI đã ghim → trả 200 với pin cũ (idempotent). Pin mới → 201 với `position = max + 1`.
  - `DELETE /v1/pins/{kpi_key}?profile=` → `{"deleted": 0|1}`.

- [ ] **Step 1: Viết test lỗi** (Review Focus #3)

```python
def test_pin_scoped_by_profile(client_ceo):
    client_ceo.post("/v1/pins?profile=real", json={"kpi_key": "gia_tri_phai_tra"})
    assert [p["kpi_key"] for p in client_ceo.get("/v1/pins?profile=synth").json()["pins"]] == []

def test_pin_idempotent_and_forbidden(client_ceo, client_kho):
    assert client_ceo.post("/v1/pins?profile=synth", json={"kpi_key":"gia_tri_phai_tra"}).status_code == 201
    assert client_ceo.post("/v1/pins?profile=synth", json={"kpi_key":"gia_tri_phai_tra"}).status_code == 200
    assert client_kho.post("/v1/pins?profile=synth", json={"kpi_key":"du_no_ngan_han"}).status_code == 403
```

- [ ] **Step 2:** FAIL → **Step 3:** cài đặt → **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(v2-p4r): add /v1/pins scoped by user and data profile`

---

### Task 5: `build_briefing` + `GET /v1/overview`

**Files:**
- Create: `v2/app/services/briefing.py`, `v2/app/api/routers/overview.py`
- Modify: `v2/app/api/schemas.py`, `v2/app/api/main.py`
- Test: `v2/tests/unit/test_services_p4r.py`, `v2/tests/integration/test_api_contract_p4r.py`

**Interfaces:**
- Consumes: `get_role_profile` (P2r), `compute_kpi_value`, `compute_kpi_series` (Task 1), `app.alert_event`, `app.action_item`, `app.pinned_kpi`, `app.job_heartbeat`.
- Produces:
  - `OverviewKpiCard(kpi_key: str, kpi_name: str | None, unit: str | None, domain: str, value: float | None, previous_value: float | None, delta_pct: float | None, series: list[dict] = [], pinned: bool = False, error: str | None = None, series_warning: str | None = None)`
  - `OverviewResponse(greeting_title: str, data_profile: str, as_of_date: str, last_alert_job_at: str | None, open_alerts: dict[str, int], open_actions: int, kpis: list[OverviewKpiCard], top_alerts: list[AlertItem], suggested_questions: list[str], warnings: list[str])`
  - `build_briefing(user: UserPrincipal, profile: str, settings: Settings, cache: ScopedTTLCache, app_engine: Engine) -> OverviewResponse`:
    - `kpis` = `overview_kpis` của vai trò, sau đó là các pin không trùng. Bỏ KPI mà `can_access_kpi` sai.
    - Mỗi thẻ được bọc `try` riêng. Lỗi `KpiComputationError` → `error` (TC-T5-12).
    - `open_alerts` = `{"nghiem_trong": n, "canh_bao": m}` sau lọc RBAC, chỉ tính cảnh báo chưa ack.
    - `open_actions` = số hành động `open`/`in_progress` mà người dùng thấy được (cùng luật với `GET /v1/actions`).
    - `top_alerts` = tối đa 3 cảnh báo chưa ack, theo thứ tự của Task 2.
    - `last_alert_job_at` = `created_at` mới nhất của `job_heartbeat` có `job_name='alert_engine' AND status='ok'`, hoặc `None`.
  - `GET /v1/overview?profile=` ghi đúng 1 dòng audit với `views_accessed` là hợp các view của các thẻ.

- [ ] **Step 1: Viết test lỗi**

```python
def test_tc_t5_12_one_failing_kpi_does_not_break_overview(monkeypatch, client_ceo_synth):
    # monkeypatch compute_kpi_value ném KpiComputationError cho 'dong_tien_rong'
    b = client_ceo_synth.get("/v1/overview?profile=synth").json()
    card = next(c for c in b["kpis"] if c["kpi_key"] == "dong_tien_rong")
    assert card["error"] and any(c["value"] is not None for c in b["kpis"] if c["kpi_key"] != "dong_tien_rong")

def test_overview_role_scoping(client_kho_synth):
    b = client_kho_synth.get("/v1/overview?profile=synth").json()
    assert [c["kpi_key"] for c in b["kpis"]] == ["gia_tri_hang_ton_kho", "so_luong_hang_ton_kho", "tong_ma_san_pham"]
    assert all(a["domain"] == "kho" for a in b["top_alerts"])

def test_overview_includes_pins_after_profile_kpis(client_ktt_synth): ...
def test_overview_admin_empty_but_200(client_admin): ...
```

- [ ] **Step 2:** FAIL → **Step 3:** cài đặt → **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat(v2-p4r): add build_briefing service and GET /v1/overview (TC-T5-12)`

---

### Task 6: Giao diện Streamlit — 5 màn

**Files:**
- Modify: `v2/app/ui/api_client.py`, `v2/app/ui/streamlit_app.py`, `v2/app/ui/components/alert_center.py`, `v2/app/ui/components/chat_view.py`, `v2/app/ui/components/__init__.py`
- Create: `v2/app/ui/components/overview_view.py`, `v2/app/ui/components/actions_view.py`
- Test: `v2/tests/unit/test_ui_streamlit_p4r.py`, `v2/tests/unit/test_ui_streamlit_t6.py` (chỉnh để chọn màn tường minh)

**Interfaces:**
- `HttpApiClient` thêm: `get_overview(profile)`, `get_kpi(kpi_key, profile=None, include_series=False)`, `list_alerts(profile=None, domain=None, severity=None, status=None)`, `list_actions(profile=None, status=None)`, `create_action(payload: dict, profile=None)`, `update_action(action_id, payload, profile=None)`, `list_pins(profile)`, `add_pin(kpi_key, profile)`, `remove_pin(kpi_key, profile)`.
- `SCREEN_OPTIONS = ["🏠 Tổng quan", "🔔 Cảnh báo", "💬 Hỏi đáp AI", "✅ Hành động", "📋 Lịch sử"]`. `_resolve_screen_index` thêm `overview`/`tong_quan` → 0, `actions`/`hanh_dong` → 3. Có `kpi` hoặc `dashboard` mà không có `screen` → màn Chat.
- `DASHBOARD_LABELS` sửa theo D6 của impact analysis (`no_vay`, `kho`, `cong_no`, `tien_gui`, `dong_tien`). Giữ `DASHBOARD_ALIASES = {"tai_chinh": "no_vay"}` để link Power BI cũ (`dashboard=tai_chinh`) vẫn chạy; khoá cũ không có ánh xạ thì vẫn mở Chat nhưng không ghi nhãn dashboard. Xoá `KPI_DISPLAY_NAMES`. Tên KPI lấy từ `kpi_name` trong response.
- Chuyển màn có ngữ cảnh: `st.session_state["pending_query"]` (được Chat dùng một lần rồi xoá) và `st.session_state["nav_screen"]`.
- **Tổng quan** (`render_overview(api_client, profile)`): banner tiêu đề `f"Chào {greeting_title}, hôm nay có {nghiem_trong + canh_bao} cảnh báo và {open_actions} hành động cần xử lý"`, kèm dòng phụ `Dữ liệu chốt {as_of_date}` + `· Cảnh báo cập nhật {last_alert_job_at}` (nếu có). Thẻ KPI xếp lưới 3 cột: `st.metric(label, value_formatted, delta=f"{delta_pct:+.1%}")` + `st.line_chart` mini khi có `series`. Thẻ có `error` hiện `st.warning`. Có mục "Phát hiện hôm nay" (`top_alerts`, nút "Xem chi tiết" chuyển sang màn Cảnh báo với `selected_alert_id`) và chip câu hỏi gợi ý (bấm vào thì đặt `pending_query` và chuyển sang Chat).
- **Cảnh báo** (`render_alert_center`): `st.columns([1.2, 2])`. Cột trái: bộ lọc `domain`/`severity`/`status` + danh sách nút chọn. Cột phải: 3 `st.metric` (giá trị, ngưỡng, kỳ), biểu đồ `evidence.series`, `coverage_warning`, danh sách `approved_actions` (mỗi dòng có nút "Tạo hành động"), và các nút "Hỏi tiếp Agent" / "Đã xem". Câu hỏi mồi: `f"Phân tích nguyên nhân và hướng xử lý cảnh báo {rule_id}: {message}"`.
- **Chat** (`render_assistant_response`): `figures` → lưới `st.metric`. `trend` (biểu đồ + bất thường) và `advice` hiển thị trực tiếp, không trong expander. SQL và nguồn giữ trong expander. Mỗi advice action có nút "Tạo hành động" (`source_type="chat"`, `source_ref=request_id`). Mỗi KPI trong `kpi_keys` có nút "📌 Ghim". Câu hỏi gợi ý (từ `get_overview(...).suggested_questions`, lấy một lần mỗi phiên) hiện phía trên ô nhập khi chưa có tin nhắn.
- **Hành động** (`render_actions_view`): lọc theo trạng thái. Mỗi dòng gồm tiêu đề, KPI, mức, người được giao, hạn, và `st.selectbox` đổi trạng thái → `update_action`.

- [ ] **Step 1: Viết test lỗi (AppTest + ASGI transport, như `test_ui_streamlit_t6.py`)**

```python
def test_tc_t6_06_default_overview_but_quick_ask_opens_chat(app_test_factory):
    at = app_test_factory(); at.run()
    assert "Chào" in at.markdown[0].value or any("Chào" in m.value for m in at.markdown)
    at2 = app_test_factory(query_params={"kpi": "du_no_ngan_han", "dashboard": "tai_chinh"}); at2.run()
    assert at2.chat_input  # đang ở màn Chat

def test_overview_metrics_rendered_for_kho(app_test_factory):
    at = app_test_factory(role="quan_ly_kho", profile="synth"); at.run()
    assert len(at.metric) == 3

def test_tc_t6_07_create_action_from_alert_detail(app_test_factory, seeded_alert):
    at = app_test_factory(screen="alerts"); at.run()
    at.button(key=f"create_action_{seeded_alert}_0").click().run()
    assert spy_requests.last("POST", "/v1/actions")

def test_ui_does_not_import_server_layers():
    import ast, pathlib
    for f in pathlib.Path("app/ui").rglob("*.py"):
        mods = {n.module for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))) if isinstance(n, ast.ImportFrom) and n.module}
        assert not {m for m in mods if m.split(".")[1:2] and m.split(".")[1] in ("services","agents","knowledge")}, f
```

- [ ] **Step 2:** FAIL → **Step 3:** cài đặt. Chỉnh `test_ui_streamlit_t6.py` để mở màn tường minh bằng `?screen=chat|alerts|history`. Assertion TC-T6-01..04 giữ nguyên.
- [ ] **Step 4:** `pytest tests/unit/test_ui_streamlit_p4r.py tests/unit/test_ui_streamlit_t6.py -v` → PASS.
- [ ] **Step 5:** Chạy thử thủ công `uvicorn app.api.main:app` + `streamlit run app/ui/streamlit_app.py`, đóng vai lần lượt `ceo`, `ke_toan_truong`, `quan_ly_kho` trên `synth`.
- [ ] **Step 6: Commit** `feat(v2-p4r): Streamlit 5 screens — overview, master-detail alerts, rich chat, actions (TC-T6-06, TC-T6-07)`

---

### Task 7: Bằng chứng & hợp đồng

**Files:**
- Modify: `v2/scripts/capture_ui_screenshots.py:65-80` (seed `period`, `dedup_key`, `evidence = build_alert_evidence(kpi, level, value, analyze_kpi_trend(...)[0]).model_dump(mode="json")`; chụp thêm `05_overview.png`, `06_alert_detail.png`, `07_actions.png`)
- Regenerate: `v2/docs/openapi.json`, `v2/eval/reports/api_contract.txt`, `v2/eval/reports/audit_log_sample.json`, `v2/eval/reports/ui_screens/*`
- Test: `v2/tests/integration/test_api_contract_p4r.py`

- [ ] **Step 1: Viết test lỗi**

```python
NEW_ENDPOINTS = [("GET","/v1/overview"),("GET","/v1/actions"),("POST","/v1/actions"),("PATCH","/v1/actions/{action_id}"),
                 ("GET","/v1/pins"),("POST","/v1/pins"),("DELETE","/v1/pins/{kpi_key}")]

def test_m13_new_endpoints_in_openapi_snapshot():
    spec = json.loads(Path("docs/openapi.json").read_text(encoding="utf-8"))
    for m, p in NEW_ENDPOINTS:
        assert m.lower() in spec["paths"][p]

def test_m14_every_new_endpoint_writes_one_audit_row(all_clients): ...   # gồm cả case 403/404/409/422
```

- [ ] **Step 2:** FAIL → **Step 3:** tạo lại snapshot bằng đúng lệnh P4 đã dùng cho EV-13. Kiểm `git diff docs/openapi.json`: chỉ có **thêm** path/field, không xoá/đổi field cũ. Chạy script chụp màn hình và lệnh xuất EV-14/EV-15 của P4.
- [ ] **Step 4:** `pytest -q` → toàn bộ PASS. `test_api_contract_t5.py::...openapi...` (TC-T5-08) PASS với snapshot mới.
- [ ] **Step 5: Commit** `chore(v2-p4r): regenerate OpenAPI snapshot and evidence EV-13..EV-16 for DataAgent features`

---

## Cổng hoàn tất P4r

- [ ] `pytest -q` xanh toàn bộ (P1–P4 + P1r–P4r).
- [ ] M-13 = 100%, M-14 = 100% cho cả endpoint cũ và mới.
- [ ] EV-13..EV-16 đã tạo lại và commit cùng code.
- [ ] TC-T6-05 (thử với người dùng thật) được bổ sung 2 nhiệm vụ: "tìm cảnh báo nghiêm trọng và tạo hành động" và "ghim một KPI".
- [ ] Ghi lại cho P5: `build_briefing`, `build_alert_evidence`, `dedup_key` sẵn sàng theo §7 của impact analysis.
