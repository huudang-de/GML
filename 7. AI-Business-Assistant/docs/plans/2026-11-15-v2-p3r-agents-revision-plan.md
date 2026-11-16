# AI Business Assistant v2 — P3r (Sửa đổi Agents: chuỗi từ T2, bằng chứng cảnh báo, hành động đã duyệt) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nối TrendAnalyst vào nguồn SQL chuỗi ở T2, bỏ chuỗi giả, và cung cấp 3 hàm thuần dùng chung cho P4r (API) và P5 (Worker): `summarize_series`, `build_alert_evidence`, `resolve_approved_action`.

**Architecture:** Tách phần "nạp chuỗi" ra khỏi `analyze_kpi_trend` thành `load_kpi_series`. Phần phân tích bất thường giữ nguyên. Các hàm thuần mới nằm trong `app/agents/series_tools.py` (không I/O). `resolve_approved_action` nằm trong `advisor.py`, dùng lại `_normalize_text`. Không đổi đồ thị LangGraph, không đổi `Answer`.

**Tech Stack:** Python 3.11+, Pydantic v2, SQLAlchemy (qua executor hiện có).

**Spec:** `docs/plans/2026-11-15-dataagent-adoption-impact-analysis.md` (§2 R1; §3 D1, D2, D7; §6 phần T3; §7) + Architecture §5 T3.

## Global Constraints

- **Không dùng LLM để tính số** (Nguyên tắc 1, TC-T7-06): cả 3 hàm mới đều tất định.
- **M-08 = 0%:** `AlertEvidence` chỉ chứa số lấy từ chuỗi đầu vào, `value` hoặc ngưỡng đã khai báo.
- **TC-T3-09, TC-T3-10, M-09, M-10 giữ nguyên:** `detect_series_anomalies` và logic coverage `< 6` không đổi.
- Khoá không thuộc 28 KPI (`ton_kho_sku`, `current_ratio`, `doanh_thu_thuan`) vẫn đọc SQL từ một dict cục bộ `_NON_KPI_SERIES_SQL` trong `trend_agent.py`. Chúng được dùng bởi eval/playbook Phase 3, và di chuyển chúng sẽ phải sửa thêm T2. Đây là ngoại lệ có chủ đích và được ghi trong docstring.
- Toàn bộ test hiện có (đã cộng test P1r, P2r) phải pass. EV-09 tạo lại không được giảm M-09.

## Review Focus

1. **KPI hợp lệ nhưng chưa có `series_ref`** (ví dụ `ltv_ratio`): trả `(None, [], "KPI 'ltv_ratio' chưa có truy vấn chuỗi thời gian")`, **không** trả chuỗi `0.0` (TC-T3-14).
2. **RBAC trên chuỗi:** `quan_ly_kho` gọi `load_kpi_series("du_no_ngan_han")` phải bị validator từ chối và trả lỗi quyền, không có dòng nào.
3. **Chuỗi 1 điểm (Real, C1):** `summarize_series` trả `previous_value=None`, `delta_pct=None`. Không chia cho 0 khi kỳ trước bằng 0 (`delta_pct=None`).
4. **Hành động gần đúng nhưng không khớp** (khác một từ): `resolve_approved_action` trả `None`, không chọn "gần nhất".
5. **`build_alert_evidence` khi `trend is None` hoặc coverage < 6:** `series=[]` hoặc chuỗi ngắn kèm `coverage_warning`. Hàm không ném lỗi.

---

## File Map (P3r)

```text
7. AI-Business-Assistant/v2/
├── app/agents/
│   ├── models.py          # [Modify] + SeriesSummary, AlertEvidence
│   ├── series_tools.py    # [Create] summarize_series, build_alert_evidence
│   ├── trend_agent.py     # [Modify] + load_kpi_series; _get_trend_sql chỉ còn _NON_KPI_SERIES_SQL; bỏ fallback giả
│   └── advisor.py         # [Modify] + resolve_approved_action
├── eval/reports/trend_synthetic.md                 # [Regenerate] EV-09
└── tests/unit/test_series_tools_and_trend_p3r.py   # [Create] TC-T3-14, TC-T3-15
```

---

### Task 1: `load_kpi_series` + Trend đọc chuỗi từ T2

**Files:**
- Modify: `v2/app/agents/trend_agent.py:154-430`
- Test: `v2/tests/unit/test_series_tools_and_trend_p3r.py`, `v2/tests/integration/test_trend_db_t3.py` (chạy lại, không sửa)

**Interfaces:**
- Consumes: `get_series_query(kpi_key) -> SeriesQuery | None` (P2r).
- Produces: `load_kpi_series(kpi_key: str, role: str, data_profile: str, engine: Engine | None = None, product_code: str | None = None) -> tuple[list[TrendPoint], str | None, str | None]`, trả `(series_sorted, validated_sql, error)`.
  - Thứ tự: `get_series_query` → nếu `None` thì thử `_NON_KPI_SERIES_SQL` → nếu vẫn không có thì `error = f"KPI '{kpi_key}' chưa có truy vấn chuỗi thời gian"`.
  - `analyze_kpi_trend` gọi `load_kpi_series` thay cho đoạn dòng 399-429. Phần còn lại giữ nguyên.

- [ ] **Step 1: Viết test lỗi**

```python
def test_tc_t3_14_kpi_without_series_ref_has_no_fake_series(fake_engine):
    trend, warnings, err = analyze_kpi_trend("ltv_ratio", role="ceo", data_profile="synth", engine=fake_engine)
    assert trend is None and "chưa có truy vấn chuỗi thời gian" in err
    assert not any("0.0 AS value" in s for s in executed_sql)  # executed_sql: list SQL do monkeypatch execute_validated_sql thu lại

def test_load_kpi_series_uses_knowledge_sql(monkeypatch, fake_engine):
    # monkeypatch get_series_query trả SeriesQuery có sql_text marker "/*S_TEST*/"
    # → SQL thực thi chứa marker
    ...

def test_load_kpi_series_rbac_rejects_kho_on_debt(fake_engine):
    series, sql, err = load_kpi_series("du_no_ngan_han", role="quan_ly_kho", data_profile="synth", engine=fake_engine)
    assert series == [] and sql is None and "quyền" in err.lower()
```

`fake_engine` dùng cùng cách mock executor mà `tests/unit/test_trend_and_advisor_t3.py` đang dùng (monkeypatch `execute_validated_sql`).

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt.
- [ ] **Step 4:** `pytest tests/unit/test_series_tools_and_trend_p3r.py tests/unit/test_trend_and_advisor_t3.py tests/integration/test_trend_db_t3.py -v` → PASS.
- [ ] **Step 5:** Tạo lại EV-09 bằng `python -m eval.run_eval --group trend` (lệnh Phase 3 đã dùng). M-09 ≥ 90% và M-10 ≤ 1 phải giữ nguyên. Nếu số liệu đổi, so diff `trend_synthetic.md` và giải thích trong commit.
- [ ] **Step 6: Commit** `refactor(v2-p3r): TrendAnalyst loads series from knowledge layer; drop fake fallback series (TC-T3-14)`

---

### Task 2: `summarize_series` + `build_alert_evidence`

**Files:**
- Modify: `v2/app/agents/models.py`
- Create: `v2/app/agents/series_tools.py`
- Test: `v2/tests/unit/test_series_tools_and_trend_p3r.py`

**Interfaces:**
- Produces:
  - `class SeriesSummary(BaseModel): points: list[TrendPoint]; last_value: float | None; previous_value: float | None; delta_pct: float | None`
  - `summarize_series(series: list[TrendPoint], limit: int = 12) -> SeriesSummary`: lấy `limit` điểm cuối. `delta_pct = (last - prev) / abs(prev)`; nếu `prev` bằng 0 hoặc không có thì `None`.
  - `class AlertEvidence(BaseModel): kpi_key: str; level: Literal["canh_bao","nghiem_trong"]; period: str | None; value: float | None; threshold_expr: str | None; series: list[TrendPoint] = []; anomalies: list[TrendAnomaly] = []; coverage_warning: str | None = None; approved_actions: list[str] = []; authority_role: str | None = None`
  - `build_alert_evidence(kpi_key: str, level: str, value: float | None, trend: Trend | None, limit: int = 12) -> AlertEvidence`:
    - `threshold_expr = get_kpi(kpi_key).nguong.get(level)`
    - `approved_actions`, `authority_role` lấy từ `get_business_actions(kpi_key, level)`
    - `series = summarize_series(trend.series, limit).points`
    - `anomalies` chỉ giữ các mục có `period` nằm trong `series` đã cắt
    - `period = series[-1].period` nếu có
    - `coverage_warning` = thông điệp coverage hiện có của Trend khi `trend.data_coverage < 6`; `"Không có dữ liệu chuỗi"` khi `trend is None`

- [ ] **Step 1: Viết test lỗi**

```python
P = lambda p, v: TrendPoint(period=p, value=v)

def test_summarize_series_delta():
    s = summarize_series([P("2026-06", 283.7), P("2026-07", 236.07)])
    assert s.last_value == 236.07 and s.previous_value == 283.7
    assert round(s.delta_pct, 3) == -0.168

def test_summarize_series_single_point_and_zero_prev():
    assert summarize_series([P("2026-07", 5.0)]).delta_pct is None
    assert summarize_series([P("2026-06", 0.0), P("2026-07", 5.0)]).delta_pct is None

def test_tc_t3_15_evidence_numbers_grounded():
    trend = Trend(kpi_key="ty_le_su_dung_han_muc", data_coverage=12,
                  series=[P(f"2025-{m:02d}", 0.5) for m in range(8, 13)] + [P(f"2026-{m:02d}", 0.6 + m/100) for m in range(1, 8)],
                  source_query_id="t")
    ev = build_alert_evidence("ty_le_su_dung_han_muc", "nghiem_trong", 0.92, trend)
    allowed = {p.value for p in trend.series} | {0.92, 0.90}
    numbers = [p.value for p in ev.series] + [ev.value]
    assert all(n in allowed for n in numbers)
    assert ev.threshold_expr == ">= 0.90" and ev.authority_role == "ceo"
    assert len(ev.series) == 12 and ev.period == "2026-07"

def test_evidence_without_trend():
    ev = build_alert_evidence("dong_tien_rong", "canh_bao", -1.0, None)
    assert ev.series == [] and ev.coverage_warning
```

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt. **Step 4:** Test → PASS.
- [ ] **Step 5: Commit** `feat(v2-p3r): add deterministic summarize_series and build_alert_evidence (TC-T3-15)`

---

### Task 3: `resolve_approved_action`

**Files:**
- Modify: `v2/app/agents/advisor.py`
- Test: `v2/tests/unit/test_series_tools_and_trend_p3r.py`

**Interfaces:**
- Produces: `resolve_approved_action(kpi_key: str, level: str, text: str) -> tuple[str, str] | None`, trả `(canonical_action_text, authority_role)`. So khớp bằng `_normalize_text` giống `filter_approved_actions`. Không khớp, hoặc KPI/mức không có quy tắc → `None`.

- [ ] **Step 1: Viết test lỗi**

```python
def test_resolve_approved_action_exact_and_normalized():
    acts = get_business_actions("ty_le_su_dung_han_muc", "canh_bao")["actions"]
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", "  " + acts[0].upper() + " ") == (acts[0], "ke_toan_truong")

def test_resolve_approved_action_rejects_near_miss_and_unknown():
    acts = get_business_actions("ty_le_su_dung_han_muc", "canh_bao")["actions"]
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", acts[0] + " ngay") is None
    assert resolve_approved_action("ty_le_su_dung_han_muc", "canh_bao", "Bán bớt tài sản") is None
    assert resolve_approved_action("du_no_ngan_han", "canh_bao", acts[0]) is None
```

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt. **Step 4:** Test + `tests/unit/test_trend_and_advisor_t3.py` → PASS.
- [ ] **Step 5: Commit** `feat(v2-p3r): add resolve_approved_action for action items (TC-T3-11 preserved)`

---

## Cổng hoàn tất P3r

- [ ] `pytest -q` xanh toàn bộ, gồm `tests/integration/test_phase3_eval_e2e.py`.
- [ ] EV-09 đã tạo lại: M-09 ≥ 90%, M-10 ≤ 1.
- [ ] Không file nào trong `app/api/`, `app/ui/`, `app/knowledge/` hay `db/` bị sửa.
