# Gỗ Minh Long UI/UX Redesign, AI Timeout & Alert Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or task-by-task implementation with TDD verification.

**Goal:** Redesign the Streamlit 5-screen web app around Gỗ Minh Long's official Crimson (`#B82601` / `#E11D24`) + Power BI `Simplifica` (`#062F4F`, `#0375B4`, `#7CBB00`, `#FFBB00`) design system with `Be Vietnam Pro` typography and Vietnamese locale formatting (`1.234,56 tỷ`, `DD/MM/YYYY`), fix AI Q&A timeouts, deduplicate repeated warnings (`×N`), and rebuild `Tổng quan` directly on the 5-chapter Power BI template using interactive Plotly visuals.

**Architecture:** Additive, backward-compatible API refinements (`AlertItem.occurrence_count`, `GET /v1/alerts?dedup=true`, fast-fail Gemini timeouts + `HttpApiClient` `chat_timeout=60s`) paired with a pure UI presentation layer (`v2/app/ui/theme.py`, `v2/.streamlit/config.toml`, `v2/app/ui/assets/logo_gml.jpg`, Plotly-powered Power BI `Simplifica` components).

**Tech Stack:** FastAPI, Pydantic v2, PostgreSQL window functions, LangChain `ChatGoogleGenerativeAI`, Streamlit, Plotly, `Be Vietnam Pro` font.

## Global Constraints
- `app/ui/**` MUST NOT import `app.services`, `app.agents`, `app.knowledge`, or `db` (`test_ui_does_not_import_server_layers` AST check).
- Never break existing test contracts (`test_api_contract_t5.py`, `test_api_contract_p4r.py`, `test_ui_streamlit_t6.py`, `test_ui_streamlit_p4r.py`). Specifically:
  - Keep `Overview` default screen greeting (`"Chào {greeting_title}"`), exact `st.metric` count for role KPIs on Overview, `"Phát hiện hôm nay"` + `"Xem chi tiết"` button, Suggested Question chips, `"📌 Bỏ ghim"`, and error `st.warning`.
  - Keep `Alert Center` master-detail layout (`st.columns([1.2, 2])`), `create_action_{id}_{idx}`, `"Hỏi tiếp Agent"`, and `ack_{rule_id}_{id}` button key (`TC-T6-03`).
  - Keep `Chat` figures metric grid + direct Trend/Advice + `📌 Ghim` + SQL/Sources expanders + feedback buttons (`TC-T6-01`..`04`, `TC-T6-06`).
- Any `"synth"` profile response keeps `"SYNTHETIC_DATA"` in `warnings`, and UI continues showing the persistent synthetic data banner (`"DỮ LIỆU MÔ PHỎNG"`).
- `docs/openapi.json` stays strictly additive (no removed paths/fields).
- Reset `eval/reports/t1_permissions.txt` via `git checkout --` after running full `pytest -q`.

---

### Task 1: AI Q&A Timeout Hardening + Alert Deduplication (`occurrence_count` & Group Ack)

**Files:**
- Modify: `v2/app/agents/llm_text.py`, `v2/app/sql/generator.py`, `v2/app/ui/api_client.py`
- Modify: `v2/app/api/schemas.py`, `v2/app/services/briefing.py`, `v2/app/api/routers/alerts.py`
- Test: `v2/tests/unit/test_services_p4r.py`, `v2/tests/integration/test_api_contract_p4r.py`, `v2/tests/unit/test_ui_streamlit_p4r.py`

**Behavior:**
1. **`GeminiTextLLMClient` (`llm_text.py`) & `GeminiSqlLLMClient` (`generator.py`):**
   - Pass explicit `timeout=12, max_retries=1` (wrapped cleanly so both `langchain-google-genai` versions or mocks stay happy) to `ChatGoogleGenerativeAI(...)` so slow/quota-limited Gemini requests fail fast (<15s) to deterministic template / Golden Query SQL instead of hanging 60+ seconds.
2. **`HttpApiClient` (`api_client.py`):**
   - Add `chat_timeout: float = 60.0` (used in `chat(..., timeout=self.chat_timeout)`) while keeping `timeout=30.0` default for lightweight endpoints.
   - Wrap `httpx.TimeoutException` in `chat(...)` (and HTTP calls cleanly via helper) to raise `ApiClientError("Hết thời gian chờ phản hồi từ Trợ lý AI. Vui lòng thử lại hoặc thu gọn câu hỏi.")` instead of leaking raw `httpx.ReadTimeout`.
3. **Alert Deduplication (`schemas.py`, `briefing.py`, `alerts.py`):**
   - `AlertItem` adds additive `occurrence_count: int = 1`.
   - `row_to_alert_item(r)` sets `occurrence_count=int(getattr(r, "occurrence_count", 1) or 1)`.
   - `GET /v1/alerts` adds `dedup: bool = Query(default=True)`. When `dedup=True`, SQL uses `ROW_NUMBER() OVER (PARTITION BY rule_id, kpi_key, severity, is_acknowledged ORDER BY created_at DESC, id DESC) AS rn` and `COUNT(*) OVER (PARTITION BY rule_id, kpi_key, severity, is_acknowledged) AS occurrence_count` inside a CTE, returning `WHERE rn = 1` ordered open -> critical -> `created_at DESC, id DESC LIMIT 100`. When `dedup=False`, returns ungrouped rows (`occurrence_count = 1`).
   - `build_briefing` (`briefing.py`) likewise deduplicates `open_alerts` counts and `top_alerts` using the same window partitioning over `is_acknowledged = FALSE` so repeated identical rule triggers (`BR-02 ×49`, `TEST_UNCAT ×11`) do not inflate badge counts or crowd out distinct alerts in `top_alerts`!
   - `POST /v1/alerts/{alert_id}/ack` (`alerts.py`): acknowledges `id = :id` AND any open sibling rows sharing `(rule_id, kpi_key, severity)` when `is_acknowledged = FALSE`, returning the acked target `AlertAckResponse` (`id=alert_id`) cleanly so acknowledging a grouped alert resolves it immediately.
   - `test_review_focus_5_alerts_rbac_filtering_and_ack_forbidden` in `test_api_core_and_resources_t5.py` remains untouched & passes (cleanup optional or already works cleanly with `dedup=True`). Also make sure `test_api_contract_p4r.py` cleans up its own seeded test alerts cleanly.

---

### Task 2: Minh Long Brand Theme, `Be Vietnam Pro` Font, Logo GML & Vietnamese Formatters

**Files:**
- Create: `v2/.streamlit/config.toml`, `v2/app/ui/theme.py` (with `v2/app/ui/assets/logo_gml.jpg`)
- Modify: `v2/app/ui/streamlit_app.py`, `v2/app/ui/components/alert_center.py`, `v2/app/ui/components/chat_view.py`, `v2/app/ui/components/actions_view.py`, `v2/app/ui/components/history_view.py`
- Test: `v2/tests/unit/test_ui_streamlit_p4r.py`

**Behavior:**
1. **`v2/.streamlit/config.toml`:**
   - Primary accent `#B82601` (Minh Long Crimson), canvas `#F6F7F9`, secondary surface `#EDF0F4` (PBIX cool slate), text `#1E242B`.
2. **`v2/app/ui/theme.py`:**
   - Pure UI utility (zero `app.services`/`app.agents`/`app.knowledge`/`db` imports).
   - Palette constants matching `Logo GML.jpg` + PBIX `Simplifica` + `Fluent 2`:
     - `ML_CRIMSON = "#B82601"`, `ML_RED_BRIGHT = "#E11D24"`, `ML_NAVY = "#062F4F"`, `ML_BLUE = "#0375B4"`, `ML_GREEN = "#7CBB00"`, `ML_AMBER = "#FFBB00"`, `ML_TEAL = "#008F95"`, `ML_SLATE = "#506B85"`, `ML_CARD_BORDER = "#E6E6E6"`, `SIMPLIFICA_PALETTE = ["#062F4F", "#B82601", "#0375B4", "#7CBB00", "#FFBB00", "#008F95", "#945D60"]`.
   - `inject_minh_long_theme()` injects `@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');`, global font rules + `font-variant-numeric: tabular-nums;`, crisp PBIX header banner CSS, sidebar cool-slate pill styling, card elevation & radius (`8px`), semantic pill badges, and Vietnamese alert/metric spacing.
   - `get_logo_base64()` loads `assets/logo_gml.jpg` safely for topbar/sidebar rendering.
   - Vietnamese formatters:
     - `format_vi_number(val, unit=None)`: `.` thousand grouping, `,` decimal comma (`236,07 tỷ VNĐ`, `341,69 tỷ`, `91,8%`, `26.824`).
     - `format_vi_delta(delta_pct)`: `▲ +5,2%` or `▼ -16,8%` (Vietnamese comma decimal).
     - `format_vi_date(iso_str)`: `2026-07-31` -> `31/07/2026`.
     - `format_vi_datetime(iso_str)`: `2026-11-17T08:00:00` -> `08:00 · 17/11/2026`.
     - `format_vi_period(period_str)`: `2026-07` -> `T07/2026`.
3. **Update `streamlit_app.py`, `alert_center.py`, `chat_view.py`, `actions_view.py`, `history_view.py`:**
   - Call `inject_minh_long_theme()` in `streamlit_app.py`, render `Logo GML` cleanly in sidebar brand header & main top header strip.
   - Format ALL metrics, tables, dates, periods, deltas across all screens in Vietnamese locale.
   - Render `"×{occurrence_count} lần"` pill in `alert_center.py` when `occurrence_count > 1`, map role/status/domain codes to clean Vietnamese labels (`"open" -> "Chờ xử lý"`, `"in_progress" -> "Đang xử lý"`, `"done" -> "Hoàn thành"`, `"dismissed" -> "Bỏ qua"`, `"ceo" -> "Tổng Giám đốc (CEO)"`, etc.) while keeping internal `STATUS_OPTIONS` / API payloads unchanged.
   - In `chat_view.py`, use Plotly trend chart styled with Minh Long `Simplifica` palette (and smooth hover tooltips in Vietnamese!) and graceful timeout banner.

---

### Task 3: Power BI `Simplifica` Overview Template (`overview_view.py`)

**Files:**
- Modify: `v2/app/ui/components/overview_view.py`
- Test: `v2/tests/unit/test_ui_streamlit_p4r.py`

**Behavior:**
1. Model `render_overview(api_client, profile)` directly on `Gỗ Minh Long PG.pbix` (`Simplifica` + `Story Telling` 5-chapter structure):
   - **PBIX Header Bar:** Logo GML + greeting `"Chào {greeting_title}, hôm nay có {total_alerts} cảnh báo và {open_actions} hành động cần xử lý"` + formatted Vietnamese date pill `Dữ liệu chốt {format_vi_date(as_of_date)}` & `Cảnh báo cập nhật {format_vi_datetime(last_alert_job_at)}` + semantic summary counters (`Nghiêm trọng`, `Cảnh báo`, `Hành động mở`).
   - **Chapter / Domain Strip (PBIX `pageNavigator`):** Interactive segmented selector or tabs reflecting the 5 Power BI Story chapters accessible in the current role's cards (`⭐ Tổng hợp Vai trò` + domain chapters present in KPIs/alerts: `🏦 Hoạt động Tài chính`, `📦 Hàng tồn kho`, `📄 Phải thu – Phải trả`, `💰 Tiền gửi & Thanh khoản`, `💸 Dòng tiền`), allowing instant focus without leaving Overview!
   - **Row 1 — PBIX KPI Hero Cards Grid (max 3 columns per row, Fluent 2 card borders + semantic top accent bar):** Renders `st.metric(label=kpi_name, value=format_vi_number(val, unit), delta=format_vi_delta(delta_pct))` (preserving exact `len(at.metric)` contract on Overview!), inline mini Plotly sparkline (`#B82601` for `no_vay`/alerts or `#062F4F` navy for primary metrics, transparent grid, Vietnamese tooltip & period `T07/2026`), `"📌 Đã ghim"` + `"Bỏ ghim"` (`unpin_overview_{kpi_key}`) when pinned, and `st.warning` on card errors.
   - **Row 2 — Power BI Asymmetric Visual Row (`cols([1.65, 1])` matching PBIX Vùng 3):**
     - Left (2/3 width): Interactive Plotly **Diễn biến 12 kỳ & Biến động MoM** combo chart (bars for values + crimson/navy trend line across available series in the active chapter/view, `Simplifica` colors, zero clutter).
     - Right (1/3 width): **Bảng đối chiếu Kỳ hiện tại vs Kỳ trước** (clean Vietnamese formatted table showing KPI, Giá trị hiện tại, Kỳ trước, Biến động `%`).
   - **Row 3 — Phát hiện hôm nay (`top_alerts`, showing grouped `×N lần` badge + `"Xem chi tiết"` button navigating to `Cảnh báo`) & Câu hỏi gợi ý chips (2-column pills navigating to `Hỏi đáp AI`).**

---

### Task 4: OpenAPI Snapshot Refresh, EV-14/EV-16 Screenshots & Full Verification

**Files:**
- Regenerate: `v2/docs/openapi.json` (additive `occurrence_count` & `dedup`), `v2/eval/reports/api_contract.txt`, `v2/eval/reports/ui_screens/*.png`
- Modify if needed: `v2/scripts/capture_ui_screenshots.py` (ensure `test_ui_streamlit_p4r` & `t6` & new theme/chart render crisply!)
- Test: full un-filtered `pytest -q`

**Steps:**
1. Verify all unit & integration tests pass after Tasks 1–3.
2. Regenerate `docs/openapi.json` (`AlertItem.occurrence_count`, `GET /v1/alerts?dedup=true`), check `test_m13_new_endpoints_in_openapi_snapshot` and `tc_t5_08_openapi_snapshot` pass.
3. Re-run `capture_ui_screenshots.py` and visually inspect `01_chat_real.png` .. `07_actions.png` via `read_file` to verify the Minh Long theme, `Be Vietnam Pro` typography, Vietnamese numbers (`236,07 tỷ`), Power BI Overview Plotly charts, and grouped Alert Center render cleanly with zero errors/warnings!
4. Run full `pytest -q`, refresh `eval/reports/api_contract.txt`, reset `eval/reports/t1_permissions.txt`, merge cleanly into `master` (per user `"you implementation, i will check after you finnish"` + `"run again web and backend api docs"`), and restart live FastAPI (`8000`) & Streamlit (`8501`) pointing to updated `master`!
