# AI Business Assistant v2 — P2r (Sửa đổi Knowledge: chuỗi thời gian & hồ sơ vai trò) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa SQL chuỗi thời gian 12 kỳ của KPI và hồ sơ hiển thị theo vai trò (KPI tổng quan, câu hỏi gợi ý) vào tầng T2 Knowledge, có lint bảo vệ RBAC, phạm vi view và chống rò rỉ benchmark.

**Architecture:** SQL chuỗi chuyển nguyên văn từ `trend_agent._get_trend_sql` (14 trong 17 nhánh là KPI chuẩn) sang `app/knowledge/golden_queries/series/*.sql`, được khai báo trong `series_index.yaml` và tham chiếu qua trường mới `series_ref` của `KpiDefinition`. Thêm SQL chuỗi mới cho 2 KPI tổng quan của kho chưa có. `role_profiles.yaml` khai báo KPI tổng quan và câu hỏi gợi ý cho từng vai trò. Lint mở rộng trong `lint_and_leakage.py`. P2r **chưa** đổi `trend_agent.py`; việc đó thuộc P3r.

**Tech Stack:** PyYAML, Pydantic v2, sqlglot (validator hiện có), scikit-learn TF-IDF (hàm leakage hiện có).

**Spec:** `docs/plans/2026-11-15-dataagent-adoption-impact-analysis.md` (§2 R1, R8, R9; §3 D1, D2, D10; §6 phần T2) + Architecture §5 T2.

## Global Constraints

- **C7 / TC-T8-02:** Không đọc thủ công các mục `split: test` trong `eval/benchmark.yaml`. Kiểm tra rò rỉ của câu hỏi gợi ý chỉ chạy qua hàm tự động. Nếu bị báo rò rỉ thì **viết lại câu hỏi gợi ý**, không mở file benchmark ra xem.
- **Nguyên tắc 1:** SQL chuỗi là SQL tất định trên `ai_views.*`. Không có LLM.
- SQL chuỗi phải trả đúng 2 cột `period` (`'YYYY-MM'`) và `value`, kèm `ORDER BY period` (hoặc `ORDER BY 1`).
- Giữ nguyên `lint_knowledge_base()` đối với 28 KPI và M-05 = 1,0. Phần lint mới tách thành hàm riêng để không đổi kiểu trả về của hàm cũ.
- Toàn bộ test hiện có (đã cộng test của P1r) phải pass.

## Review Focus

1. **KPI tổng quan vượt quyền (R9):** `quan_ly_kho` có `vong_quay_hang_ton_kho` (cần `ai_v_bctc`) → lint phải báo lỗi. Test với một fixture YAML cố ý sai.
2. **SQL chuỗi dùng view ngoài `views_used`:** ví dụ khai báo `[ai_v_ton_kho]` nhưng SQL `JOIN ai_v_bctc` → lint báo lỗi, vì RBAC của chuỗi dựa trên `views_used`.
3. **`series_ref` trỏ tới id không tồn tại, hoặc `kpi_key` trong index không khớp KPI** → lint báo lỗi.
4. **Câu hỏi gợi ý gần trùng benchmark test** (cosine ≥ 0,92) → lint báo lỗi qua `check_benchmark_leakage(custom_test_items=…)` theo chiều ngược: coi câu gợi ý là "corpus", câu test là truy vấn.
5. **Vai trò `quan_tri_he_thong`** (không có view nào) → `overview_kpis: []` và `suggested_questions: []` hợp lệ. `get_role_profile("vai_tro_la")` trả hồ sơ rỗng, không ném lỗi.

---

## File Map (P2r)

```text
7. AI-Business-Assistant/v2/
├── app/knowledge/
│   ├── models.py                         # [Modify] KpiDefinition.series_ref; SeriesQuery; RoleProfile
│   ├── kpi_definitions.yaml              # [Modify] + series_ref cho 16 KPI
│   ├── golden_queries/series/            # [Create] 16 file SQL chuỗi (S_<kpi_key>.sql)
│   ├── golden_queries/series_index.yaml  # [Create]
│   ├── role_profiles.yaml                # [Create]
│   ├── loader.py                         # [Modify] + load_series_queries, get_series_query, load_role_profiles, get_role_profile
│   └── lint_and_leakage.py               # [Modify] + lint_series_and_role_profiles; generate_reports ghi thêm vào EV-04
└── tests/unit/test_knowledge_series_profiles_p2r.py   # [Create] TC-T2-08, TC-T2-09, TC-T2-10, M-05b
```

---

### Task 1: Mô hình + loader + dữ liệu chuỗi thời gian

**Files:**
- Modify: `v2/app/knowledge/models.py`, `v2/app/knowledge/loader.py`, `v2/app/knowledge/kpi_definitions.yaml`
- Create: `v2/app/knowledge/golden_queries/series_index.yaml`, `v2/app/knowledge/golden_queries/series/S_*.sql`
- Test: `v2/tests/unit/test_knowledge_series_profiles_p2r.py`

**Interfaces:**
- Produces:
  - `KpiDefinition.series_ref: str | None = None`
  - `class SeriesQuery(BaseModel): id: str; kpi_key: str; sql_file: str; sql_text: str = ""; views_used: list[str]; grain: Literal["month"] = "month"`
  - `load_series_queries(index_path: Path | None = None) -> dict[str, SeriesQuery]` (key = `kpi_key`, đọc `sql_text` từ file như `load_golden_queries`)
  - `get_series_query(kpi_key: str) -> SeriesQuery | None` (trả `None` nếu KPI không có `series_ref`)
- Dữ liệu:
  - 14 KPI chuyển **nguyên văn** từ `trend_agent.py:156-371` (17 nhánh, chỉ lấy các khoá có trong `kpi_definitions.yaml`): `du_no_ngan_han`, `du_no_dai_han`, `ty_le_su_dung_han_muc`, `dong_tien_rong`, `dong_tien_vao`, `dong_tien_ra`, `tien_va_tuong_duong_tien`, `ty_le_no_tren_tong_nguon_von`, `gia_tri_hang_ton_kho`, `gia_tri_phai_thu`, `gia_tri_phai_tra`, `han_muc_phe_duyet`, `han_muc_duoc_cap`, `han_muc_con_lai`. Các khoá `ton_kho_sku`, `current_ratio`, `doanh_thu_thuan` **không** phải KPI trong 28 KPI, nên vẫn để trong `trend_agent.py`. P3r quyết định cách xử lý chúng.
  - Hai SQL chuỗi **mới** cho kho:
    - `so_luong_hang_ton_kho`: `SELECT to_char(tx_date,'YYYY-MM') AS period, SUM(quantity) AS value FROM ai_views.ai_v_ton_kho WHERE record_type='balance' GROUP BY 1 ORDER BY 1`
    - `tong_ma_san_pham`: đếm `DISTINCT product_code` có `quantity > 0` tại `MAX(tx_date)` **của từng tháng** (CTE lấy ngày lớn nhất mỗi tháng, rồi đếm), cùng logic với `GQ_13`.
  - Đặt `id` theo dạng `S_<kpi_key>`.

- [ ] **Step 1: Viết test lỗi**

```python
def test_series_query_loaded_verbatim_for_du_no_ngan_han():
    sq = get_series_query("du_no_ngan_han")
    assert sq is not None and sq.views_used == ["ai_v_no_vay"]
    assert "34111%" in sq.sql_text and "period" in sq.sql_text.lower()

def test_kpi_without_series_ref_returns_none():
    assert get_series_query("ltv_ratio") is None

def test_new_inventory_series_exist():
    for k in ("so_luong_hang_ton_kho", "tong_ma_san_pham"):
        assert get_series_query(k).views_used == ["ai_v_ton_kho"]
```

- [ ] **Step 2:** `pytest tests/unit/test_knowledge_series_profiles_p2r.py -v` → FAIL.
- [ ] **Step 3:** Cài đặt mô hình, loader và dữ liệu như phần Interfaces.
- [ ] **Step 4:** Test → PASS. `pytest tests/unit/test_knowledge_t2.py -v` → PASS.
- [ ] **Step 5 (DB thật):** Thêm vào `tests/integration/test_golden_queries_t2.py` một test tham số hoá theo từng `SeriesQuery`: validate với `allowed_tables=set(sq.views_used)`, chạy bằng `gml_ai_ro` trên `synth`, rồi assert `status == "ok"`, mọi dòng có `period` khớp `^\d{4}-\d{2}$`, `period` tăng dần. Chạy → PASS.
- [ ] **Step 6: Commit** `feat(v2-p2r): move KPI time-series SQL into knowledge layer with series_ref`

---

### Task 2: Hồ sơ vai trò

**Files:**
- Create: `v2/app/knowledge/role_profiles.yaml`
- Modify: `v2/app/knowledge/models.py`, `v2/app/knowledge/loader.py`
- Test: `v2/tests/unit/test_knowledge_series_profiles_p2r.py`

**Interfaces:**
- Produces:
  - `class RoleProfile(BaseModel): role: str; greeting_title: str; overview_kpis: list[str] = []; suggested_questions: list[str] = []`
  - `load_role_profiles(path: Path | None = None) -> dict[str, RoleProfile]`
  - `get_role_profile(role: str) -> RoleProfile`: vai trò lạ → `RoleProfile(role=role, greeting_title="", overview_kpis=[], suggested_questions=[])`
- Dữ liệu `role_profiles.yaml`:

| role | greeting_title | overview_kpis (theo thứ tự) |
| --- | --- | --- |
| `ceo` | `Tổng Giám đốc` | `du_no_ngan_han`, `ty_le_su_dung_han_muc`, `tien_va_tuong_duong_tien`, `dong_tien_rong`, `gia_tri_phai_thu`, `gia_tri_hang_ton_kho` |
| `ke_toan_truong` | `Kế toán trưởng` | `du_no_ngan_han`, `ty_le_su_dung_han_muc`, `tien_va_tuong_duong_tien`, `dong_tien_rong`, `gia_tri_phai_thu`, `gia_tri_phai_tra` |
| `quan_ly_kho` | `Quản lý kho` | `gia_tri_hang_ton_kho`, `so_luong_hang_ton_kho`, `tong_ma_san_pham` |
| `quan_tri_he_thong` | `Quản trị hệ thống` | *(rỗng)* |

  - Mỗi vai trò có dữ liệu thì có **4 câu hỏi gợi ý**, viết mới. Ví dụ cho `quan_ly_kho`: "Giá trị tồn kho thay đổi thế nào trong 6 tháng gần đây?". Câu hỏi chỉ nói về KPI trong `overview_kpis` của chính vai trò đó.

- [ ] **Step 1: Viết test lỗi**

```python
def test_role_profiles_shape():
    p = get_role_profile("quan_ly_kho")
    assert p.overview_kpis == ["gia_tri_hang_ton_kho", "so_luong_hang_ton_kho", "tong_ma_san_pham"]
    assert len(p.suggested_questions) == 4
    assert get_role_profile("quan_tri_he_thong").overview_kpis == []
    assert get_role_profile("unknown").suggested_questions == []
```

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt. **Step 4:** Test → PASS.
- [ ] **Step 5: Commit** `feat(v2-p2r): add role profiles (overview KPIs, suggested questions)`

---

### Task 3: Lint mới (TC-T2-08, TC-T2-09, TC-T2-10, M-05b) + EV-04

**Files:**
- Modify: `v2/app/knowledge/lint_and_leakage.py` (thêm hàm; `generate_reports` ghi thêm một khối vào `eval/reports/t2_yaml_lint.txt`)
- Test: `v2/tests/unit/test_knowledge_series_profiles_p2r.py`

**Interfaces:**
- Consumes: `can_access_kpi`, `kpi_domain` (P1r); `get_allowed_views`; `validate` (`app/sql/validator.py`); `check_benchmark_leakage`.
- Produces: `lint_series_and_role_profiles(profiles_path: Path | None = None, series_index_path: Path | None = None) -> tuple[bool, list[str], float]`, trả `(is_ok, messages, m05b_series_coverage)`. Hàm kiểm tra:
  1. Với mọi `series_ref`: id có trong index, `kpi_key` khớp, `views_used ⊆ kpi.nguon_view`, SQL qua `validate(sql, allowed_tables=set(views_used))`, và mọi bảng `ai_views.*` mà sqlglot tìm thấy trong SQL đều thuộc `views_used`.
  2. Với mọi vai trò và mọi `k ∈ overview_kpis`: KPI tồn tại, `can_access_kpi(role, k)` đúng, và `kpi_domain(k)` không ném lỗi.
  3. Rò rỉ: dựng `BenchmarkItem` giả từ từng câu gợi ý, rồi gọi `check_benchmark_leakage(custom_test_items=…)`. Thông báo lỗi **chỉ ghi id hồ sơ và số thứ tự câu gợi ý**, không in câu benchmark (C7).
  4. `m05b = |{k ∈ ∪overview_kpis : get_series_query(k) is not None}| / |∪overview_kpis|`. Lint đạt khi `m05b == 1.0`.
  - Lưu ý chiều kiểm tra ở mục 3: `check_benchmark_leakage` so test item với golden corpus. Để so **câu gợi ý với câu test**, thêm tham số tuỳ chọn `custom_corpus: list[str] | None = None` vào hàm này (mặc định giữ hành vi cũ). Khi có `custom_corpus`, corpus là danh sách câu gợi ý, còn test item là benchmark `split: test` tự nạp. Mỗi thông báo lỗi chỉ gồm `id` của mục test và chỉ số câu gợi ý.

- [ ] **Step 1: Viết test lỗi**

```python
def test_tc_t2_08_overview_kpis_accessible():
    ok, msgs, _ = lint_series_and_role_profiles()
    assert ok, msgs

def test_tc_t2_08_detects_forbidden_overview(tmp_path):
    bad = tmp_path / "rp.yaml"
    bad.write_text("quan_ly_kho:\n  role: quan_ly_kho\n  greeting_title: X\n  overview_kpis: [vong_quay_hang_ton_kho]\n  suggested_questions: []\n", encoding="utf-8")
    ok, msgs, _ = lint_series_and_role_profiles(profiles_path=bad)
    assert not ok and any("vong_quay_hang_ton_kho" in m for m in msgs)

def test_tc_t2_10_series_view_scope_violation(tmp_path):
    # series_index giả: views_used=[ai_v_ton_kho] nhưng SQL JOIN ai_views.ai_v_bctc → báo lỗi
    ...

def test_tc_t2_09_leakage_message_does_not_echo_test_question(monkeypatch):
    # ép một câu gợi ý trùng chính câu test giả (custom), assert msg không chứa chuỗi câu test
    ...

def test_m05b_series_coverage_is_full():
    assert lint_series_and_role_profiles()[2] == 1.0
```

- [ ] **Step 2:** Test → FAIL. **Step 3:** Cài đặt. **Step 4:** Test → PASS. `pytest tests/unit/test_knowledge_t2.py -v` → PASS (hành vi cũ của leakage không đổi).
- [ ] **Step 5:** Chạy `python -m app.knowledge.lint_and_leakage` (hoặc entrypoint mà Phase 2 dùng để tạo EV-04/EV-05). Xác nhận `t2_yaml_lint.txt` có thêm khối `M-05b = 1.00`, và `t2_leakage_check.txt` vẫn `OK`.
- [ ] **Step 6: Commit** `feat(v2-p2r): lint series scope, role-profile RBAC and suggested-question leakage (TC-T2-08..10, M-05b)`

---

## Cổng hoàn tất P2r

- [ ] `pytest -q` xanh toàn bộ.
- [ ] EV-04 và EV-05 đã được tạo lại và cùng được commit.
- [ ] `trend_agent.py` **chưa** bị sửa (`git diff --stat` không có file này). Việc nối Trend vào T2 thuộc P3r.
