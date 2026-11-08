# AI Business Assistant v2 — Phase 2 (Knowledge + SQL + Synthetic Data) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng Tầng Tri thức Ngữ nghĩa (`T2`), Pipeline Text-to-SQL 6 bước có Chấm điểm Tin cậy & Tự sửa lỗi (`T3-SQL`), và Bộ sinh Dữ liệu Mô phỏng 12 tháng cô lập theo profile (`T1-synth`) trong `7. AI-Business-Assistant/v2/`, đạt `M-05 = 100%` (28/28 KPI chuẩn hoá theo toàn bộ 5 Dashboard của `ISO - BRD_Final.xlsx` có Golden Query), đo được `M-06`/`M-07` trên tập `dev`, và xuất đủ 5 bằng chứng cổng Phase 2 (`EV-03`, `EV-04`, `EV-05`, `EV-07`, `EV-08`).

**Architecture:** Triển khai từ dưới lên theo 3 khối độc lập nhưng khớp chặt hợp đồng giao tiếp:
1. **Dữ liệu Mô phỏng & Cô lập Profile (`T1-synth`):** Dựng database riêng `gml_synth` (tách vật lý khỏi `data_warehouse` chứa `silver`), sinh tất định 12 tháng (`2025-08` → `2026-07`, `--seed 42`) với marker `SYNTH_` và 5 bất thường gắn nhãn trong `anomalies.yaml`, rồi áp cùng template `views.sql.j2` để tầng trên dùng chung tên view `ai_views.*`.
2. **Tầng Tri thức Xác định (`T2`):** Chuẩn hoá trọn vẹn **28 KPI** theo đúng mục `1. Chỉ số tổng quan` của cả 5 Dashboard trong file BRD ISO (`kpi_definitions.yaml`), quy tắc hành động theo mức ngưỡng (`business_rules.yaml`), Ngân hàng Truy vấn Mẫu (`golden_queries/*.sql` + `index.yaml`, `split: dev` khớp UAT `RESULT LOG` và đếm thực tế), và bộ Benchmark 60 câu (`eval/benchmark.yaml`, 40 `dev` / 20 `test` khoá) có kiểm tra chống rò rỉ kép bằng cả cosine câu hỏi (`< 0.92`) lẫn chuẩn hoá cây cú pháp AST (`sqlglot`).
3. **Pipeline Text-to-SQL 6 bước (`T3-SQL`):** `build_sql_prompt_context` (lọc view + KPI + Golden Query theo RBAC) → `SqlLLMClient` sinh ứng viên SQL → `validate` AST (`sqlglot`) → `execute_validated_sql` (`gml_ai_ro`, phân loại `ok`/`no_data`/`execution_error`, khử nhạy cảm lỗi DB) → `repair` tối đa 3 lần thử → `score_sql_confidence` (`0.3` tương đồng Golden + `0.4` nhất quán thực thi 3 ứng viên + `0.3` hợp lý kết quả, cổng bắt buộc AST + exec).

**Tech Stack:** Python 3.11+ (local 3.13), PostgreSQL 15+, SQLAlchemy 2.0+, `psycopg2-binary>=2.9.0`, `pydantic>=2.7.0`, `pydantic-settings>=2.2.0`, `sqlglot>=23.0.0`, `langgraph>=0.1.0`, `langchain-google-genai>=1.0.0`, `scikit-learn>=1.4.0`, `numpy>=1.26.0`, `matplotlib>=3.8.0`, `pyyaml>=6.0.1`, `pytest>=8.0.0`.

**Spec:**
- `7. AI-Business-Assistant/docs/plans/AI_Business_Assistant_v2_Architecture_Detail.md` (§1, §2 C0–C7, §3.1, §5 T1/T2/T3/T8, §6, §8 Phase 2, §9, §10, §11.1, §11.7, §11.9, §11.10)
- `7. AI-Business-Assistant/docs/AI_Business_Assistant_v2_Plan.md` (Phần II §6.1, §6.2, §6.9, §8.1)

## Global Constraints

- **C0 / §11.7 (Cô lập thư mục v2):** Toàn bộ mã nguồn, dữ liệu cấu hình và báo cáo đánh giá của v2 nằm trong `7. AI-Business-Assistant/v2/`. Tuyệt đối không sửa `7. AI-Business-Assistant/v1/` hoặc tài liệu tham khảo gốc.
- **C1 / §6 Note (Mốc khoá sổ & Giới hạn dữ liệu demo):** Mốc chốt số liệu là `AS_OF_DATE = 2026-07-31` (tháng `2026-08` chưa khoá sổ). Trên profile `real`, `B02-DN_11` (giá vốn) và `B02-DN_23` (chi phí lãi vay thực tế) bằng `0`, doanh thu `B02-DN_10` chỉ có tháng `07/2026`; câu hỏi về biên lợi nhuận gộp / YoY 2025 / doanh thu tháng 3/2026 phải trả `no_data` hoặc cảnh báo thiếu dữ liệu, không bịa số.
- **§3.1 / §11.1 (Cô lập vật lý `real` và `synth`):** Hai profile `DATA_PROFILE=real` (`data_warehouse`, schema nguồn `silver`) và `DATA_PROFILE=synth` (`gml_synth`, schema nguồn `synthetic`) nằm ở hai database PostgreSQL riêng, cùng xuất schema `ai_views.*`. Mọi kết quả chạy trên `synth` phải đính kèm `warnings: ["SYNTHETIC_DATA"]`.
- **§6 Warning (Công thức hạn mức tín dụng chuẩn UAT — "UAT thắng"):** Trong `kpi_definitions.yaml` và Golden Query Bank, `ty_le_su_dung_han_muc` (`G-13`) bắt buộc tính bằng `SUM(principal_balance) / NULLIF(SUM(granted_limit), 0)` trên `ai_views.ai_v_no_vay WHERE record_type = 'credit_limit'` (`270,864,478,366 / 295,000,000,000 = 0.918185`), và `han_muc_con_lai` (`G-05`) = `SUM(granted_limit) - SUM(principal_balance) = 24,135,521,634`. Trên `synthetic`, `principal_balance` tại `2026-07` neo bằng `236,070,000,000 / 295,000,000,000 = 0.800237` (`80.0%`, mức Cảnh báo `AL-001`).
- **C7 / §6.9 / §11.10 (Chống rò rỉ dev/test):** Mọi mục trong `eval/benchmark.yaml` có `reviewed_by` và `reviewed_at`. Tập `split: test` bị khoá trước khi tinh chỉnh prompt (`run_eval.py --split test` bắt buộc cờ `--final`), không có câu nào có độ tương đồng cosine `>= 0.92` hoặc trùng khung cây cú pháp AST đã chuẩn hoá với bất kỳ câu nào trong `app/knowledge/golden_queries/`.
- **§8 Phase 2 Gate:** Bắt buộc pass `TC-T1-05…07`, `TC-T2-01…03`, `TC-T3-04…07` (kèm toàn bộ 50 test của Phase 1 không hồi quy); đạt `M-05 = 100%` (28/28 KPI từ 5 Dashboard BRD có golden query), đo được `M-06` & `M-07` trên tập `dev`; tạo đủ `EV-03` (`db/synthetic/CHECKSUM.txt`), `EV-04` (`eval/reports/t2_yaml_lint.txt`), `EV-05` (`eval/reports/t2_leakage_check.txt`), `EV-07` (`eval/reports/sql_accuracy.md`), `EV-08` (`eval/reports/calibration.png`).

## Review Focus

1. **Rò rỉ view nhạy cảm qua Golden Query Few-Shot khi `match_golden()` bỏ qua RBAC:** Nếu `quan_ly_kho` hỏi *"Dư nợ ngắn hạn bao nhiêu?"*, `match_golden(question, role="quan_ly_kho", k=3)` không được trả về truy vấn mẫu đọc `ai_v_no_vay`; mọi Golden Query có `views_used` nằm ngoài `get_allowed_views(role)` phải bị lọc bỏ trước khi đưa vào prompt.
2. **Truy vấn gộp SQL trả về 1 dòng toàn `NULL` (`SELECT SUM(credit_balance) ... WHERE 1=0` → `[(None,)]`) bị nhận nhầm là `ok`:** Trong PostgreSQL, hàm tổng hợp không có `GROUP BY` trên tập rỗng trả `row_count = 1` với tất cả cột là `None`. `execute_validated_sql()` phải xếp trường hợp `len(rows) == 0` **hoặc** mọi giá trị trong mọi dòng đều `None` vào `status = "no_data"` (và `plausibility = 0.0`).
3. **Rò rỉ mẫu SQL sang tập `test` dù câu hỏi tiếng Việt đã diễn đạt khác (`TC-T2-03` chỉ đo cosine mà bỏ sót AST):** Hai câu hỏi có cosine `< 0.50` nhưng câu SQL chuẩn chỉ khác tên alias hoặc hằng số ngày/mã (`'2026-07-31'` vs `'2026-06-30'`) vẫn vi phạm Spec §11.10. Bộ kiểm tra rò rỉ phải chuẩn hoá AST bằng `sqlglot` (bỏ alias cột/bảng, thay literal số/chuỗi bằng placeholder, chuẩn hoá chữ thường) và báo lỗi nếu trùng bất kỳ Golden Query nào.
4. **Trộn lẫn kết nối DB giữa `DATA_PROFILE=real` và `DATA_PROFILE=synth` hoặc quên gắn cảnh báo `SYNTHETIC_DATA`:** `Settings.get_ro_uri(profile)` phải tách biệt rõ URI của `real` và `synth` (từ chối nếu hai URI trỏ tới cùng một tên database), và mọi lần chạy `sql_lookup` ở `data_profile="synth"` phải thêm `"SYNTHETIC_DATA"` vào `warnings`.
5. **Vòng lặp tự sửa lỗi (`repair.py`) gửi nguyên lỗi DB thô chứa `silver.*` hoặc thông tin kết nối lên LLM và log:** Mọi ngoại lệ từ DB/validator trước khi truyền vào `repair_fn` hoặc lưu vào `RepairAttempt.sanitized_error` bắt buộc đi qua `sanitize_db_error()`.

---

## File Map (Phase 2)

```text
7. AI-Business-Assistant/v2/
├── requirements.txt                           # [Modify] Bổ sung scikit-learn, numpy, matplotlib
├── .env.example                               # [Modify] Bổ sung POSTGRES_URI_{ADMIN,RO,APP}_SYNTH
├── app/
│   ├── core/
│   │   └── config.py                          # [Modify] Thêm URI synth & get_{ro,app,admin}_uri(profile)
│   ├── knowledge/
│   │   ├── __init__.py                        # [Create] Public exports cho T2
│   │   ├── models.py                          # [Create] Pydantic schemas: KpiDefinition, BusinessRule, GoldenQuery, BenchmarkItem
│   │   ├── kpi_definitions.yaml               # [Create] 28 KPI chuẩn hoá từ toàn bộ 5 Dashboard BRD + UAT + Storytelling
│   │   ├── business_rules.yaml                # [Create] (kpi, muc) -> hành động đã duyệt + nhãn thẩm quyền
│   │   ├── loader.py                          # [Create] get_kpi, get_business_actions, match_golden (NFC + không dấu + RBAC)
│   │   ├── lint_and_leakage.py                # [Create] Lint YAML (EV-04) & kiểm tra rò rỉ cosine + AST (EV-05)
│   │   └── golden_queries/
│   │       ├── index.yaml                     # [Create] Danh mục Golden Query (split: dev, >= 28 câu phủ 28/28 KPI)
│   │       └── GQ_*.sql                       # [Create] Các file SQL mẫu chạy trên ai_views.*
│   ├── sql/
│   │   ├── __init__.py                        # [Modify] Export pipeline types & functions
│   │   ├── models.py                          # [Create] SqlStatus, SqlDraft, SqlExecutionResult, RepairAttempt, ConfidenceBreakdown
│   │   ├── context.py                         # [Create] Bước 1: dựng prompt context lọc theo RBAC + Golden + KPI + C1 caveats
│   │   ├── generator.py                       # [Create] Bước 2: SqlLLMClient (Gemini, Ollama, Heuristic/Mock deterministic)
│   │   ├── executor.py                        # [Create] Bước 4: thực thi chỉ-đọc qua gml_ai_ro, chuẩn hoá kiểu, phân loại no_data
│   │   ├── confidence.py                      # [Create] Bước 5: chấm điểm tin cậy 0.3 Golden + 0.4 Consistency + 0.3 Plausibility
│   │   └── repair.py                          # [Create] Bước 6: vòng lặp tự sửa lỗi <= 3 lần thử với lỗi đã làm sạch
│   ├── agents/
│   │   ├── __init__.py                        # [Create]
│   │   └── sql_agent.py                       # [Create] run_sql_pipeline() & pure LangGraph node sql_lookup_node, confidence_gate_node
│   └── orchestration/
│       ├── state.py                           # [Modify] Thêm warnings (reducer add) & data_profile vào ChatState
│       └── graph.py                           # [Modify] Bổ sung build_sql_graph() kết nối sql_lookup_node + confidence_gate_node
├── db/
│   ├── catalog.yaml                           # [Modify] Bổ sung cột partner_group, invoice_date, exchange_rate, product_category, tx_id
│   ├── views.sql.j2                           # [Modify] Bổ sung các cột trên để khớp 100% UAT_02, UAT_03, UAT_05
│   ├── apply_db.py                            # [Modify] Hỗ trợ tham số profile ("real"|"synth") & ensure_database_exists()
│   └── synthetic/
│       ├── __init__.py                        # [Create]
│       ├── anomalies.yaml                     # [Create] 5 nhãn bất thường cài sẵn cho 12 tháng 08/2025..07/2026
│       ├── generate.py                        # [Create] CLI `--seed 42` dựng gml_synth + schema synthetic + ai_views + CHECKSUM.txt
│       └── CHECKSUM.txt                       # [Create] EV-03: SHA-256 checksum từng bảng synthetic
├── eval/
│   ├── __init__.py                            # [Create]
│   ├── benchmark.yaml                         # [Create] 60 câu benchmark (40 dev / 20 test khoá) có reviewed_by, reviewed_at
│   ├── run_eval.py                            # [Create] Đánh giá SQL dev, chặn test khi thiếu --final, sinh EV-07 & EV-08
│   └── reports/
│       ├── t2_yaml_lint.txt                   # [Create] EV-04
│       ├── t2_leakage_check.txt               # [Create] EV-05
│       ├── sql_accuracy.md                    # [Create] EV-07 (dev split)
│       └── calibration.png                    # [Create] EV-08
└── tests/
    ├── unit/
    │   ├── test_knowledge_t2.py               # [Create] TC-T2-01, TC-T2-03, M-05, Review Focus #1 & #3
    │   ├── test_sql_pipeline_t3.py            # [Create] TC-T3-04..07, Review Focus #2 & #5
    │   └── test_sql_agent_node.py             # [Create] Node contract, TC-T3-04 graph routing, Review Focus #4 synth warning
    └── integration/
        ├── test_synthetic_t1.py               # [Create] TC-T1-05..07, Review Focus #4 DB isolation, UAT_02/03 view columns
        ├── test_golden_queries_t2.py          # [Create] TC-T2-02 trên PostgreSQL thật
        └── test_sql_eval_dev.py               # [Create] TC-T8-01, TC-T8-02, kiểm chứng sinh EV-07 & EV-08
```

---

### Task 1: Hoàn thiện cột View UAT, Cô lập Profile `real`/`synth` & Bộ sinh Dữ liệu Mô phỏng 12 tháng (`T1-synth`)

**Files:**
- Modify: `7. AI-Business-Assistant/v2/requirements.txt`
- Modify: `7. AI-Business-Assistant/v2/.env.example`
- Modify: `7. AI-Business-Assistant/v2/app/core/config.py`
- Modify: `7. AI-Business-Assistant/v2/db/views.sql.j2`
- Modify: `7. AI-Business-Assistant/v2/db/catalog.yaml`
- Modify: `7. AI-Business-Assistant/v2/db/apply_db.py`
- Create: `7. AI-Business-Assistant/v2/db/synthetic/__init__.py`
- Create: `7. AI-Business-Assistant/v2/db/synthetic/anomalies.yaml`
- Create: `7. AI-Business-Assistant/v2/db/synthetic/generate.py`
- Create: `7. AI-Business-Assistant/v2/db/synthetic/CHECKSUM.txt`
- Test: `7. AI-Business-Assistant/v2/tests/integration/test_synthetic_t1.py`

**Interfaces:**
- Consumes: `app.core.config.Settings`, `db/views.sql.j2`, `db/roles.sql`, `db/migrations/001_init_app_schema.sql`.
- Produces:
  - `Settings.get_ro_uri(profile: str | None = None) -> str`
  - `Settings.get_app_uri(profile: str | None = None) -> str`
  - `Settings.get_admin_uri(profile: str | None = None) -> str` (ném `ValueError` nếu database name của `real` và `synth` trùng nhau — Review Focus #4)
  - `db.apply_db.ensure_database_exists(admin_uri: str) -> None`
  - `db.apply_db.get_ro_engine(ro_uri: str | None = None, profile: str | None = None) -> Engine`
  - `db.synthetic.generate.generate_synthetic_warehouse(seed: int = 42, admin_uri: str | None = None, checksum_path: Path | None = None) -> dict[str, str]` (trả về `{table_name: sha256_hex}` và ghi `EV-03`)

- [ ] **Step 1: Bổ sung cột còn thiếu trong `v2/db/views.sql.j2`, `v2/db/catalog.yaml`, và cấu hình URI `synth` trong `config.py` / `.env.example` / `requirements.txt`**

1. Trong `v2/requirements.txt`, thêm `numpy>=1.26.0`, `scikit-learn>=1.4.0`, `matplotlib>=3.8.0`.
2. Trong `v2/db/views.sql.j2` và `v2/db/catalog.yaml` (giữ nguyên toàn bộ tên cột cũ để không phá Phase 1, chỉ bổ sung cột mới ở cuối mỗi nhánh `UNION ALL` cho khớp kiểu):
   - `ai_v_no_vay`: thêm `tx_id` (`cls.id::bigint`, `col.row_id::bigint`, `fl.id::bigint`, `fc.id::bigint`).
   - `ai_v_dong_tien`: thêm `tx_id` (`c.id::bigint`).
   - `ai_v_ton_kho`: thêm `product_category` (`p.product_category::text`) và `exchange_rate` (`1.0::double precision` cho nhánh `balance`, `i.exchange_rate::double precision` cho nhánh `inward`, `o.exchange_rate::double precision` cho nhánh `outward`).
   - `ai_v_cong_no`: thêm `partner_group` (`p.partner_group::text`), `invoice_date` (`ar.invoice_date::date` / `ap.invoice_date::date`), và `tx_id` (`ar.id::bigint` / `ap.id::bigint`).
3. Trong `v2/app/core/config.py` (và `v2/.env.example`, đồng thời cập nhật `v2/.env` local nếu chưa có biến `*_SYNTH`), thêm:
   - `postgres_uri_ro_synth: str = "postgresql+psycopg2://gml_ai_ro:ro_secret@localhost:5432/gml_synth"`
   - `postgres_uri_app_synth: str = "postgresql+psycopg2://gml_ai_app:app_secret@localhost:5432/gml_synth"`
   - `postgres_uri_admin_synth: str = "postgresql+psycopg2://dev:Inda1234@localhost:5432/gml_synth"` (trong `.env.example` dùng placeholder `postgres:postgres`)
   - Validator hoặc helper `get_ro_uri(profile=None)`, `get_app_uri(profile=None)`, `get_admin_uri(profile=None)` kiểm tra `profile in {"real", "synth"}` và ném `ValueError` nếu tên DB của `real` và `synth` giống nhau (Review Focus #4).

- [ ] **Step 2: Viết failing integration test trong `v2/tests/integration/test_synthetic_t1.py`**

Bao gồm đủ 5 bài kiểm tra:
- `test_profile_uri_isolation_and_no_cross_contamination()`: kiểm tra `Settings` từ chối khi `postgres_uri_ro` và `postgres_uri_ro_synth` trỏ cùng một DB name; kiểm tra `get_ro_uri("real")` != `get_ro_uri("synth")`.
- `test_uat_extended_view_columns_match_uat02_uat03()`: sau `apply_all()`, truy vấn bằng `gml_ai_ro` trên `real`:
  - `ai_v_cong_no` lọc `ar_ap_type='AR' AND partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp') AND rn=1` ra đúng `36326095573.00` (`UAT_03`);
  - `ai_v_cong_no` lọc `ar_ap_type='AP' AND partner_group IN ('Nhà cung cấp', 'Khách hàng/ nhà cung cấp') AND rn=1` ra đúng `60452900187.23` (`UAT_03`);
  - `ai_v_ton_kho` lọc `record_type='inward' AND exchange_rate > 1` ra đúng `163157504466.00` (`UAT_02`).
- `test_tc_t1_05_deterministic_generator_checksum()`: chạy `generate_synthetic_warehouse(seed=42)` hai lần liên tiếp, assert dict checksum lần 1 == lần 2 và file `v2/db/synthetic/CHECKSUM.txt` tồn tại, không rỗng.
- `test_tc_t1_06_real_profile_contains_zero_synth_markers()`: dùng `get_ro_engine(profile="real")` quét cả 7 view `ai_views.*` tìm chuỗi `'SYNTH_'` trên các cột định danh/mô tả → tổng số dòng khớp bằng `0`.
- `test_tc_t1_07_labeled_anomalies_match_synthetic_views()`: đọc `v2/db/synthetic/anomalies.yaml`, kết nối `get_ro_engine(profile="synth")`, thực thi `verification_sql` của từng nhãn bất thường và assert giá trị thực tế khớp `expected_value` trong phạm vi `tolerance`.

- [ ] **Step 3: Chạy pytest để xác nhận test fail**

Run: `pytest "7. AI-Business-Assistant/v2/tests/integration/test_synthetic_t1.py" -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'db.synthetic'` hoặc thiếu cột/hàm).

- [ ] **Step 4: Triển khai `v2/db/synthetic/anomalies.yaml`, `v2/db/synthetic/generate.py`, và cập nhật `v2/db/apply_db.py`**

1. Trong `v2/db/apply_db.py`:
   - Thêm `ensure_database_exists(admin_uri: str) -> None` (kết nối vào DB `postgres` trên cùng host với `isolation_level="AUTOCOMMIT"`, kiểm tra `pg_database` và chạy `CREATE DATABASE gml_synth` nếu chưa tồn tại, đồng thời cấp `GRANT CONNECT ON DATABASE gml_synth TO gml_ai_ro, gml_ai_app`).
   - Mở rộng `get_ro_engine`, `get_app_engine`, `get_admin_engine` nhận `profile: str | None = None`.
2. Trong `v2/db/synthetic/anomalies.yaml`, khai báo 5 nhãn bất thường chuẩn Spec §3.1, §6.1, §6 Warning (mỗi mục gồm `id`, `kpi`, `period`, `metric`, `expected_value`, `tolerance`, `severity`, `description`, `verification_sql` chạy trên `ai_views.*`):
   - `ANOM-01`: `du_no_ngan_han` tại `2026-07` giảm MoM `-0.167889` (`283,700,000,000` ở `2026-06` → `236,070,000,000` ở `2026-07`; đồng thời `2026-01` neo đúng `314,700,000,000` để chuỗi 7 tháng giảm `-24.9857%`).
   - `ANOM-02`: SKU `SYNTH_SKU_MDF17` trong `ai_v_ton_kho` (`record_type='balance'`) có `total_value = 18500000000` tại `2026-03-31`, cao gấp `> 3 MAD` so với trung vị 12 tháng (`~5,000,000,000`).
   - `ANOM-03`: `current_ratio` (`B01-DN_100 / B01-DN_310` trên `ai_v_bctc`) tại `2025-11-30` sụt xuống `1.08` (`< 1.2`, ngưỡng cảnh báo `AL-003`), trong khi 11 tháng còn lại nằm trong `[1.35, 1.55]`.
   - `ANOM-04`: `ty_le_su_dung_han_muc` (`SUM(principal_balance) / SUM(granted_limit)` trên `ai_v_no_vay WHERE record_type='credit_limit'`) tại `2026-07-31` bằng `236070000000 / 295000000000 = 0.80023729` (`80.0%`, kích hoạt mức `canh_bao` `AL-001`, hạn mức còn lại `58,930,000,000`).
   - `ANOM-05`: `dong_tien_rong` (`SUM(debit_amount - credit_amount)` trên `ai_v_dong_tien WHERE is_external_cashflow = TRUE`) tháng `2026-02` âm đột biến `-45000000000` (thiếu hụt dòng tiền sau Tết).
3. Trong `v2/db/synthetic/generate.py`:
   - Dùng `random.Random(seed)` cố định (không dùng timestamp động cho cột dữ liệu; `_loaded_at` cố định `2026-07-31T00:00:00`), dựng `SCHEMA synthetic` trên DB `gml_synth` với đủ 7 bảng `dim_*` và 13 bảng `fact_*` mà `views.sql.j2` tham chiếu, dữ liệu phủ đủ 12 tháng chốt sổ `2025-08-31` → `2026-07-31` (có đủ giá vốn `B02-DN_11 > 0`, lãi vay `B02-DN_23 > 0`, doanh thu `B02-DN_10 > 0` cả 12 tháng), mọi mã chứng từ/đối tác/sản phẩm mang tiền tố `SYNTH_`.
   - Gọi `apply_all(admin_uri=synth_admin_uri, source_schema="synthetic", as_of_date="2026-07-31")`.
   - Tính SHA-256 trên dòng dữ liệu đã sắp xếp xác định của từng bảng `synthetic.*`, ghi ra `v2/db/synthetic/CHECKSUM.txt` (`EV-03`). Hỗ trợ CLI `python "7. AI-Business-Assistant/v2/db/synthetic/generate.py" --seed 42`.

- [ ] **Step 5: Chạy script cập nhật DB, sinh `EV-03` và chạy toàn bộ test T1**

Run:
```powershell
python "7. AI-Business-Assistant/v2/db/apply_db.py"
python "7. AI-Business-Assistant/v2/db/synthetic/generate.py" --seed 42
pytest "7. AI-Business-Assistant/v2/tests/integration/test_db_t1.py" "7. AI-Business-Assistant/v2/tests/integration/test_synthetic_t1.py" -v
```
Expected: Tất cả test PASS; `7. AI-Business-Assistant/v2/db/synthetic/CHECKSUM.txt` (`EV-03`) được tạo sạch.

- [ ] **Step 6: Commit Task 1**

```powershell
git add "7. AI-Business-Assistant/v2/requirements.txt" "7. AI-Business-Assistant/v2/.env.example" "7. AI-Business-Assistant/v2/app/core/config.py" "7. AI-Business-Assistant/v2/db/" "7. AI-Business-Assistant/v2/eval/reports/t1_permissions.txt" "7. AI-Business-Assistant/v2/eval/reports/t1_views_vs_uat.csv" "7. AI-Business-Assistant/v2/tests/integration/test_synthetic_t1.py" -f
git commit -m "feat(v2-p2): add deterministic 12-month synthetic warehouse and profile isolation"
```

---

### Task 2: Tầng Tri thức Ngữ nghĩa (`T2`): 28 KPI YAML (Toàn bộ 5 Dashboard BRD), Business Rules, Golden Query Bank, Benchmark 60 câu & Chống rò rỉ

**Files:**
- Create: `7. AI-Business-Assistant/v2/app/knowledge/__init__.py`
- Create: `7. AI-Business-Assistant/v2/app/knowledge/models.py`
- Create: `7. AI-Business-Assistant/v2/app/knowledge/kpi_definitions.yaml`
- Create: `7. AI-Business-Assistant/v2/app/knowledge/business_rules.yaml`
- Create: `7. AI-Business-Assistant/v2/app/knowledge/golden_queries/index.yaml`
- Create: `7. AI-Business-Assistant/v2/app/knowledge/golden_queries/GQ_*.sql` (28+ file SQL)
- Create: `7. AI-Business-Assistant/v2/app/knowledge/loader.py`
- Create: `7. AI-Business-Assistant/v2/app/knowledge/lint_and_leakage.py`
- Create: `7. AI-Business-Assistant/v2/eval/benchmark.yaml`
- Create: `7. AI-Business-Assistant/v2/eval/reports/t2_yaml_lint.txt` (`EV-04`)
- Create: `7. AI-Business-Assistant/v2/eval/reports/t2_leakage_check.txt` (`EV-05`)
- Test: `7. AI-Business-Assistant/v2/tests/unit/test_knowledge_t2.py`
- Test: `7. AI-Business-Assistant/v2/tests/integration/test_golden_queries_t2.py`

**Interfaces:**
- Consumes: `app.core.security.get_allowed_views`, `db.apply_db.get_ro_engine`, `sqlglot`.
- Produces:
  - `KpiDefinition(BaseModel)`: `key: str`, `ten: str`, `dashboard: str`, `don_vi: str`, `cong_thuc: str`, `nguon_view: list[str]`, `golden_ref: str`, `thanh_phan: list[str] = []`, `y_nghia: str`, `plausible_range: tuple[float, float] | None = None`, `nguong: dict[str, str] = {}`, `data_caveat: str | None = None`
  - `BusinessRuleAction(BaseModel)`: `actions: list[str]`, `authority_role: str`, `disclaimer: str`
  - `GoldenQuery(BaseModel)`: `id: str`, `kpi_key: str | None = None`, `dashboard: str`, `question_vi: str`, `paraphrases: list[str] = []`, `sql_file: str`, `sql_text: str = ""`, `views_used: list[str]`, `split: Literal["dev"] = "dev"`, `uat_expected: float`, `value_column: str | None = None`, `tolerance: float = 1e-4`
  - `GoldenMatch(BaseModel)`: `query: GoldenQuery`, `similarity: float`
  - `BenchmarkExpectation(BaseModel)`: `gia_tri: float | None = None`, `dung_sai_tuong_doi: float = 1e-4`, `so_dong: int | None = None`
  - `BenchmarkItem(BaseModel)`: `id: str`, `loai: Literal["sql", "rag", "both", "follow_up", "ngoai_pham_vi", "an_toan"]`, `do_kho: Literal["de", "vua", "kho"] = "vua"`, `dashboard: str | None = None`, `split: Literal["dev", "test"]`, `profile: Literal["real", "synth"] = "real"`, `role: str = "ceo"`, `cau_hoi: str`, `reference_sql: str | None = None`, `expected_status: Literal["ok", "no_data", "rejected", "blocked"] = "ok"`, `ky_vong: BenchmarkExpectation | None = None`, `expected_source: str | None = None`, `reviewed_by: str`, `reviewed_at: str`
  - `app.knowledge.loader.load_kpis(path: Path | None = None) -> dict[str, KpiDefinition]`
  - `app.knowledge.loader.get_kpi(key: str) -> KpiDefinition` (ném `KeyError` nếu không tồn tại)
  - `app.knowledge.loader.get_business_actions(kpi_key: str, level: str) -> dict` (trả `actions: list[str]`, `authority_role: str`, `disclaimer: str`)
  - `app.knowledge.loader.load_golden_queries(index_path: Path | None = None) -> list[GoldenQuery]`
  - `app.knowledge.loader.load_benchmark(path: Path | None = None) -> list[BenchmarkItem]`
  - `app.knowledge.loader.match_golden(question: str, role: str = "ceo", k: int = 3) -> list[GoldenMatch]` (lọc theo `get_allowed_views(role)` — Review Focus #1; mỗi `GoldenMatch` có `query: GoldenQuery` và `similarity: float` trong `[0.0, 1.0]`)
  - `app.knowledge.lint_and_leakage.normalize_sql_ast_skeleton(sql: str) -> str`
  - `app.knowledge.lint_and_leakage.lint_knowledge_base() -> tuple[bool, list[str], float]` (trả `(ok, messages, m05_coverage)`)
  - `app.knowledge.lint_and_leakage.check_benchmark_leakage(cosine_threshold: float = 0.92) -> tuple[bool, list[str]]`

- [ ] **Step 1: Viết failing unit & integration tests trong `test_knowledge_t2.py` và `test_golden_queries_t2.py`**

Trong `v2/tests/unit/test_knowledge_t2.py`:
- `test_tc_t2_01_yaml_lint_and_m05_full_coverage()`: gọi `lint_knowledge_base()`, assert `ok is True`, đúng 28 KPI trong `kpi_definitions.yaml` (bao quát trọn vẹn 5 Dashboard của `ISO - BRD_Final.xlsx`), `m05_coverage == 1.0` (28/28 KPI có `golden_ref` tồn tại thật trong `golden_queries/`), mọi mức ngưỡng của KPI có quy định cảnh báo đều có hành động tương ứng trong `business_rules.yaml` kèm câu bắt buộc `"Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định"`.
- `test_credit_limit_kpi_uses_uat_winning_formula()`: kiểm tra `get_kpi("ty_le_su_dung_han_muc")` dùng `principal_balance` và `granted_limit` trên `ai_v_no_vay` (không dùng `du_no_ngan_han`).
- `test_match_golden_vietnamese_accented_and_unaccented()`: `"du no ngan han hien tai la bao nhieu"` và `"Dư nợ ngắn hạn hiện tại là bao nhiêu?"` đều trả về `kpi_key == "du_no_ngan_han"` ở top-1 với `similarity > 0.4`.
- `test_match_golden_filters_by_role_rbac()` (Review Focus #1): gọi `match_golden("Dư nợ ngắn hạn hiện tại là bao nhiêu?", role="quan_ly_kho", k=3)` → không phần tử nào có `ai_v_no_vay` trong `views_used`; với `role="quan_tri_he_thong"` trả `[]`.
- `test_tc_t2_03_benchmark_no_leakage()`: kiểm tra `eval/benchmark.yaml` có đúng 60 câu (`40 dev`, `20 test`), mọi câu có `reviewed_by` & `reviewed_at`, và `check_benchmark_leakage(0.92)` trả `ok is True`.
- `test_leakage_detector_catches_identical_ast_with_rewritten_question()` (Review Focus #3): truyền dữ liệu giả gồm 1 câu `split: test` có câu chữ khác hoàn toàn (cosine `< 0.4`) nhưng SQL chỉ đổi alias và đổi ngày `'2026-07-31'` → `'2026-06-30'` so với Golden Query → `check_benchmark_leakage()` phải trả `ok is False` với lý do `AST_SKELETON_LEAK`.

Trong `v2/tests/integration/test_golden_queries_t2.py`:
- `test_tc_t2_02_all_golden_queries_match_uat_on_real_views()`: duyệt toàn bộ entry trong `golden_queries/index.yaml`, thực thi file `.sql` qua `get_ro_engine(profile="real")` (sau khi đi qua `validate(sql, allowed_tables=get_allowed_views("ceo"))`), so sánh giá trị scalar/tổng kiểm tra với `uat_expected` sai số tương đối `<= tolerance` (mặc định `1e-4`).

- [ ] **Step 2: Chạy pytest để xác nhận test fail**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_knowledge_t2.py" -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.knowledge'`).

- [ ] **Step 3: Tạo `models.py`, `kpi_definitions.yaml` (28 KPI), `business_rules.yaml`, và `golden_queries/`**

Danh sách **trọn vẹn 28 KPI** theo đúng mục `1. Chỉ số tổng quan` của cả 5 Dashboard trong `ISO - BRD_Final.xlsx` và UAT được định nghĩa trong `v2/app/knowledge/kpi_definitions.yaml` (mỗi KPI có `ten`, `dashboard`, `don_vi`, `cong_thuc`, `nguon_view: list[str]`, `golden_ref`, `thanh_phan`, `y_nghia`, `plausible_range: [min, max]`, `nguong`, `data_caveat`):

**Dashboard 1 — Quản trị Hoạt động Tài chính (8 KPI):**
1. `du_no_ngan_han` (D1, `ai_v_no_vay`, UAT_01 `G-01` = `236065233815.0`)
2. `du_no_dai_han` (D1, `ai_v_no_vay`, UAT_01 `G-02` = `51174925843.0`)
3. `han_muc_phe_duyet` (D1, `ai_v_no_vay`, UAT_01 `G-03` = `295000000000.0`)
4. `han_muc_duoc_cap` (D1, `ai_v_no_vay`, UAT_01 `G-04` = `295000000000.0`)
5. `han_muc_con_lai` (D1, `ai_v_no_vay`, UAT_01 `G-05` = `24135521634.0`)
6. `ty_le_su_dung_han_muc` (D1, `ai_v_no_vay`, UAT_01 `G-13` = `0.91818467`, `canh_bao: >= 0.70`, `nghiem_trong: >= 0.90`)
7. `ltv_ratio` (D1, `ai_v_no_vay`, Loan to Value, UAT_01 `G-06` = `0.71290864`, `canh_bao: >= 0.75`, `nghiem_trong: > 0.80`)
8. `ty_le_no_tren_tong_nguon_von` (D1, `ai_v_bctc`, D/E `B01-DN_300 / B01-DN_440`, UAT_01 = `0.63580376`, `canh_bao: >= 0.60`, `nghiem_trong: > 0.70`)

**Dashboard 2 — Quản trị Hàng tồn kho (6 KPI):**
9. `so_luong_hang_ton_kho` (D2, `ai_v_ton_kho`, `SUM(ending_quantity)`, UAT_02 = `673125.42`)
10. `gia_tri_hang_ton_kho` (D2, `ai_v_ton_kho`, `SUM(ending_value)`, UAT_02 = `341692285766.0`)
11. `vong_quay_hang_ton_kho` (D2, `ai_v_ton_kho` + `ai_v_bctc`, COGS / Tồn kho; kèm caveat C1 trên `real` do `B02-DN_11 = 0` trả `no_data`, tính đầy đủ trên `synth`)
12. `ty_le_ton_kho_tren_doanh_thu` (D2, `ai_v_ton_kho` + `ai_v_bctc`, UAT_02 = `4.55642883`, `canh_bao: >= 3.0`, `nghiem_trong: > 4.0`)
13. `tong_ma_san_pham` (D2, `ai_v_ton_kho`, `COUNT(DISTINCT product_code)`, UAT_02 = `1246`)
14. `gia_tri_hang_nhap_khau` (D2, `ai_v_ton_kho`, `exchange_rate > 1`, UAT_02 = `163157504466.0`)

**Dashboard 3 — Quản trị Phải thu - Phải trả (6 KPI):**
15. `gia_tri_phai_thu` (D3, `ai_v_cong_no`, `AR` + `partner_group`, UAT_03 = `36326095573.0`)
16. `gia_tri_phai_tra` (D3, `ai_v_cong_no`, `AP` + `partner_group`, UAT_03 = `60452900187.23`)
17. `vong_quay_phai_thu_nam` (D3, `ai_v_cong_no` + `ai_v_bctc`, Doanh thu năm / AR bình quân, kèm caveat C1)
18. `vong_quay_phai_thu_hien_tai` (D3, `ai_v_cong_no` + `ai_v_bctc`, Doanh thu tháng / AR hiện tại, UAT_03 = `2.06439053`)
19. `tong_so_hoa_don` (D3, `ai_v_cong_no`, `COUNT(DISTINCT invoice_no)` nợ AR chưa thu hết, UAT_03 = `2803`)
20. `tong_so_khach_hang` (D3, `ai_v_cong_no`, `COUNT(DISTINCT partner_code)` có dư nợ AR dương, UAT_03 = `694`)

**Dashboard 4 — Quản trị Tiền gửi & Thanh khoản (5 KPI):**
21. `tien_va_tuong_duong_tien` (D4, `ai_v_bctc`, `B01-DN_110`, UAT_04 `G-07` = `91976722608.0`, cutoff T7 = `91975348608.0`)
22. `tien_gui_co_ky_han` (D4, `ai_v_tien_gui`, UAT_04 `G-08` = `40514952541.0`)
23. `so_luong_hop_dong_tien_gui` (D4, `ai_v_tien_gui`, `COUNT(DISTINCT contract_number)`, UAT_04 `G-09` = `6`)
24. `lai_suat_tien_gui_binh_quan` (D4, `ai_v_tien_gui`, UAT_04 `G-10` = `0.04989675`)
25. `thu_nhap_lai_tien_gui` (D4, `ai_v_tien_gui` / TK 515, UAT_04 `G-11` = `1885039837.0`)

**Dashboard 5 — Quản trị Dòng tiền (3 KPI):**
26. `dong_tien_ra` (D5, `ai_v_dong_tien`, `SUM(credit_amount)` dòng tiền ra ngoài T1–T7, UAT_05 = `2302632987134.0`)
27. `dong_tien_vao` (D5, `ai_v_dong_tien`, `SUM(debit_amount)` dòng tiền vào ngoài T1–T7, UAT_05 = `2377257851093.0`)
28. `dong_tien_rong` (D5, `ai_v_dong_tien`, `SUM(debit_amount - credit_amount)`, UAT_05 = `74627611959.0`, cutoff T7 = `74624863959.0`)

*(Các chỉ số tài chính phái sinh bổ trợ: `current_ratio` = `1.3861`, `quick_ratio` = `0.8633`, và `von_luu_dong_rong` = `248,352,741,076` cũng được tạo Golden Query tương ứng).* Mỗi Golden Query khai báo rõ `views_used`, `kpi_key`, `question_vi`, `paraphrases`, `split: dev`, `uat_expected`, `tolerance: 0.0001`.

- [ ] **Step 4: Tạo `v2/eval/benchmark.yaml` (60 câu: 40 `dev` / 20 `test` khoá) và triển khai `loader.py` + `lint_and_leakage.py`**

1. Trong `v2/eval/benchmark.yaml`, biên soạn đủ 60 câu đúng cơ cấu Spec §5 T8 & §6.9:
   - `25` câu `loai: sql` (`15 dev`, `10 test`, phân bố `10 de / 10 vua / 5 kho`): tất cả đáp án lấy từ `RESULT LOG` của `UAT_01..05`. Riêng **10 câu `split: test`** bắt buộc dùng mẫu truy vấn khác hẳn Golden Query Bank theo Spec §11.10 (ví dụ: `GROUP BY bank_code` lãi suất vay ngắn hạn bình quân Woori `0.07` / HDBank `0.0875`; `GROUP BY bank_code` dư nợ khế ước MB `89994431799`; `GROUP BY term` tiền gửi kỳ hạn 6 tháng `21524952541`; `HAVING SUM(debit_amount - credit_amount) > 0` đếm `2803` hoá đơn AR chưa thu hết; đếm `694` khách hàng còn dư nợ dương; Top 1 khách hàng nợ phải thu Yeahome `11468115310`; Top 1 SKU theo số lượng tồn `GP4123T` `119495.72`; tổng xuất kho tháng `06/2026` `81312507829`; dòng tiền vào tháng `06/2026` `557962548602`; chi phí lãi vay kế hoạch tháng `11/2026` `4744470039`).
   - `10` câu `loai: rag` (`7 dev`, `3 test`) gắn `expected_source` + heading từ `guide_dashboard1..5.md`, `Cam_nang_Nghiep_vu_Toan_thu_GML.md`, `Story Telling...md`, `Tai_lieu_Tri_thuc...md`.
   - `10` câu `loai: both` (`7 dev`, `3 test`: `7 [R]` + `3 [S]`).
   - `6` câu `loai: follow_up` (`3 dev` + `3 test`: 2 chuỗi × 3 lượt trên `[S]`).
   - `5` câu `loai: ngoai_pham_vi` (`4 dev`, `1 test` trên `[R]`: biên lợi nhuận gộp T7 `B02-DN_11=0`, giá vốn T7, doanh thu T3/2026, tăng trưởng YoY 2025, lương nhân sự — kỳ vọng `expected_status: no_data`).
   - `4` câu `loai: an_toan` (`4 dev` hoặc `3 dev / 1 test` sao cho tổng toàn bộ 60 câu đúng bằng `40 dev` + `20 test`: `DELETE`/`DROP`, prompt injection, `quan_ly_kho` hỏi nợ vay — kỳ vọng `blocked`/`rejected`).
2. Trong `v2/app/knowledge/loader.py`:
   - Chuẩn hoá văn bản bằng `unicodedata.normalize("NFC", text)` kết hợp ghép chuỗi không dấu (`unidecode`/bỏ dấu Unicode `Mn`), vector hoá bằng `TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))` + word n-gram `(1, 2)` của `scikit-learn` để tìm khớp tốt cả tiếng Việt có dấu lẫn không dấu mà không cần mạng ngoài.
   - `match_golden(question, role="ceo", k=3)` lọc `set(gq.views_used).issubset(get_allowed_views(role))` trước khi xếp hạng.
3. Trong `v2/app/knowledge/lint_and_leakage.py`:
   - `normalize_sql_ast_skeleton(sql)`: parse bằng `sqlglot.parse_one(sql, read="postgres")`, bỏ `LIMIT`, xoá `exp.Alias` (giữ biểu thức con), thay mọi `exp.Literal` bằng placeholder `:lit`, chuyển tên bảng/cột về chữ thường, xuất chuỗi SQL chuẩn hoá.
   - `check_benchmark_leakage(cosine_threshold=0.92)`: kiểm tra mọi mục `split == "test"` trong `benchmark.yaml` có cosine câu hỏi `< 0.92` so với mọi câu mẫu/`paraphrases` trong `golden_queries/index.yaml`, **và** (nếu mục `test` có `reference_sql`) `normalize_sql_ast_skeleton(reference_sql)` không trùng với bất kỳ file `.sql` nào trong `golden_queries/`.
   - Khi chạy trực tiếp `python "7. AI-Business-Assistant/v2/app/knowledge/lint_and_leakage.py"`, xuất `EV-04` (`v2/eval/reports/t2_yaml_lint.txt`) và `EV-05` (`v2/eval/reports/t2_leakage_check.txt`).

- [ ] **Step 5: Chạy lint/leakage sinh `EV-04`, `EV-05` và chạy pytest unit + integration cho T2**

Run:
```powershell
python "7. AI-Business-Assistant/v2/app/knowledge/lint_and_leakage.py"
pytest "7. AI-Business-Assistant/v2/tests/unit/test_knowledge_t2.py" "7. AI-Business-Assistant/v2/tests/integration/test_golden_queries_t2.py" -v
```
Expected: Tất cả test PASS; `M-05 = 28/28 (100.0%)`; `0` rò rỉ trong `EV-05`.

- [ ] **Step 6: Commit Task 2**

```powershell
git add "7. AI-Business-Assistant/v2/app/knowledge/" "7. AI-Business-Assistant/v2/eval/benchmark.yaml" "7. AI-Business-Assistant/v2/eval/reports/t2_yaml_lint.txt" "7. AI-Business-Assistant/v2/eval/reports/t2_leakage_check.txt" "7. AI-Business-Assistant/v2/tests/unit/test_knowledge_t2.py" "7. AI-Business-Assistant/v2/tests/integration/test_golden_queries_t2.py"
git commit -m "feat(v2-p2): add T2 semantic knowledge layer, golden query bank, and 60-item benchmark"
```

---

### Task 3: Động cơ Thực thi SQL Chỉ-đọc, Chấm điểm Tin cậy (`Confidence`) & Vòng lặp Tự sửa lỗi `<= 3` lần (`T3-SQL Core`)

**Files:**
- Create: `7. AI-Business-Assistant/v2/app/sql/models.py`
- Create: `7. AI-Business-Assistant/v2/app/sql/executor.py`
- Create: `7. AI-Business-Assistant/v2/app/sql/confidence.py`
- Create: `7. AI-Business-Assistant/v2/app/sql/repair.py`
- Modify: `7. AI-Business-Assistant/v2/app/sql/__init__.py`
- Test: `7. AI-Business-Assistant/v2/tests/unit/test_sql_pipeline_t3.py`

**Interfaces:**
- Consumes: `app.sql.validator.validate`, `app.core.errors.{SqlRejected, sanitize_db_error}`, `db.apply_db.get_ro_engine`, `app.knowledge.models.KpiDefinition`.
- Produces:
  - `SqlStatus = Literal["ok", "no_data", "execution_error", "rejected"]`
  - `SqlDraft(BaseModel)`: `sql: str`, `explanation_short: str = ""`, `kpi_keys: list[str] = []`, `out_of_scope_reason: str | None = None`
  - `SqlExecutionResult(BaseModel)`: `status: SqlStatus`, `sql: str | None`, `columns: list[str]`, `rows: list[dict[str, Any]]`, `row_count: int`, `error: str | None = None`, `latency_ms: float = 0.0`
  - `RepairAttempt(BaseModel)`: `attempt_no: int`, `sql: str`, `stage: Literal["ast", "exec", "ok"]`, `status: SqlStatus`, `sanitized_error: str | None = None`
  - `ConfidenceBreakdown(BaseModel)`: `total: float`, `passed_mandatory_gate: bool`, `golden_similarity: float`, `consistency: float`, `plausibility: float`
  - `execute_validated_sql(sql: str, profile: str = "real", engine: Engine | None = None, max_rows: int = 1000) -> SqlExecutionResult`
  - `run_validate_execute_with_repair(initial_sql: str, allowed_views: set[str], execute_fn: Callable[[str], SqlExecutionResult], repair_fn: Callable[[str, str], str] | None = None, max_attempts: int = 3, max_rows: int = 1000) -> tuple[SqlExecutionResult, list[RepairAttempt]]`
  - `score_sql_confidence(primary_result: SqlExecutionResult, golden_similarity: float, candidate_results: list[SqlExecutionResult] | None = None, kpi_def: KpiDefinition | None = None) -> ConfidenceBreakdown`

- [ ] **Step 1: Viết failing unit tests trong `v2/tests/unit/test_sql_pipeline_t3.py`**

Bao gồm đầy đủ:
- `test_tc_t3_04_empty_rows_returns_no_data()`: mock DB trả `0` dòng → `status == "no_data"`, `row_count == 0`, `error is None`.
- `test_executor_all_null_aggregate_row_returns_no_data()` (Review Focus #2): mock DB trả 1 dòng `[{"sum": None}]` (tương ứng `SELECT SUM(credit_balance) ... WHERE 1=0`) → `status == "no_data"`, `rows == []`, `row_count == 0`.
- `test_tc_t3_05_db_error_returns_sanitized_execution_error()`: mock DB ném `OperationalError('FATAL: password authentication failed for postgresql://dev:Secret123@localhost/gml on relation silver.fact_cashflow')` → `status == "execution_error"`, `rows == []`, `"Secret123"` không có trong `error`, `"silver."` bị thay bằng `"[REDACTED_SCHEMA]."`.
- `test_tc_t3_06_self_repair_succeeds_on_third_attempt_and_caps_at_three()`:
  - Kịch bản A: lần 1 lỗi cú pháp/bảng, lần 2 lỗi cột DB, lần 3 trả SQL đúng → `result.status == "ok"`, `len(attempts) == 3`, thứ tự `attempt_no == [1, 2, 3]`.
  - Kịch bản B: cả 4+ câu đều lỗi → dừng đúng ở `len(attempts) == 3` (`max_attempts=3`), `repair_fn` chỉ được gọi đúng `2` lần.
- `test_repair_sanitizes_db_error_before_llm_prompt_and_log()` (Review Focus #5): khi `execute_fn` trả lỗi thô chứa `silver.fact_loan` hoặc đường dẫn `D:\secret\db.cfg`, kiểm tra đối số `sanitized_error` truyền vào `repair_fn(broken_sql, sanitized_error)` và `attempts[0].sanitized_error` đều đã được khử nhạy cảm.
- `test_tc_t3_07_confidence_scoring_rules()`:
  - 3 ứng viên SQL cho cùng tập kết quả (khác thứ tự alias cột nhưng cùng giá trị) + `golden_similarity=0.9` + kết quả hợp lý → `consistency == 1.0`, `plausibility == 1.0`, `total == pytest.approx(0.3*0.9 + 0.4*1.0 + 0.3*1.0)`.
  - Kết quả `status == "no_data"` (rỗng hoặc toàn `None`) → `plausibility == 0.0`.
  - Kết quả `status == "rejected"` hoặc `"execution_error"` → cổng bắt buộc chặn, `passed_mandatory_gate is False`, `total == 0.0` bất kể `golden_similarity`.
  - Giá trị nằm ngoài `kpi_def.plausible_range` (ví dụ `ty_le_su_dung_han_muc = 250.0` khi dải hợp lý là `[0.0, 5.0]`) → `plausibility <= 0.2`.

- [ ] **Step 2: Chạy pytest để xác nhận test fail**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_sql_pipeline_t3.py" -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.sql.executor'`).

- [ ] **Step 3: Triển khai `models.py`, `executor.py`, `confidence.py`, `repair.py`, và cập nhật `app/sql/__init__.py`**

1. `executor.py`: chuyển đổi `Decimal -> float`, `date/datetime -> isoformat()`, kiểm tra `all(v is None for row in rows for v in row.values())` → trả `status="no_data", rows=[], row_count=0`. Mọi `Exception` bắt tại biên DB được bọc qua `sanitize_db_error(exc)`.
2. `repair.py`: vòng lặp `for attempt_no in range(1, max_attempts + 1)`:
   - Gọi `validate(current_sql, allowed_tables=allowed_views, max_rows=max_rows)`. Nếu `SqlRejected`, ghi `RepairAttempt(stage="ast", status="rejected", sanitized_error=sanitize_db_error(err))`.
   - Nếu qua AST, gọi `execute_fn(validated_sql)`. Nếu `status == "execution_error"`, ghi `RepairAttempt(stage="exec", status="execution_error", sanitized_error=sanitize_db_error(exec_res.error))`. Nếu `status in ("ok", "no_data")`, ghi `RepairAttempt(stage="ok", status=exec_res.status)` và trả kết quả ngay.
   - Nếu chưa đạt `max_attempts` và có `repair_fn`, gọi `current_sql = repair_fn(current_sql, last_sanitized_error)`.
3. `confidence.py`: chuẩn hoá bảng kết quả thành tuple giá trị làm tròn 6 chữ số có nghĩa để so `consistency` giữa các ứng viên; áp dụng công thức `0.3 * golden_similarity + 0.4 * consistency + 0.3 * plausibility` khi `status in ("ok", "no_data")` (với `no_data` có `plausibility = 0.0`), và ép `total = 0.0` khi `status in ("rejected", "execution_error")`.

- [ ] **Step 4: Chạy pytest xác nhận toàn bộ unit test `T3-SQL` và `validator` cũ đều pass**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_sql_validator.py" "7. AI-Business-Assistant/v2/tests/unit/test_sql_pipeline_t3.py" -v`
Expected: PASS 100%.

- [ ] **Step 5: Commit Task 3**

```powershell
git add "7. AI-Business-Assistant/v2/app/sql/" "7. AI-Business-Assistant/v2/tests/unit/test_sql_pipeline_t3.py"
git commit -m "feat(v2-p2): add read-only SQL executor, self-repair loop, and confidence scorer"
```

---

### Task 4: Tác tử `SQLAgent` 6 bước, Tích hợp LangGraph & Bộ Đánh giá SQL `dev` + Biểu đồ Calibration (`EV-07`, `EV-08`)

**Files:**
- Create: `7. AI-Business-Assistant/v2/app/sql/context.py`
- Create: `7. AI-Business-Assistant/v2/app/sql/generator.py`
- Create: `7. AI-Business-Assistant/v2/app/agents/__init__.py`
- Create: `7. AI-Business-Assistant/v2/app/agents/sql_agent.py`
- Modify: `7. AI-Business-Assistant/v2/app/orchestration/state.py`
- Modify: `7. AI-Business-Assistant/v2/app/orchestration/graph.py`
- Create: `7. AI-Business-Assistant/v2/eval/__init__.py`
- Create: `7. AI-Business-Assistant/v2/eval/run_eval.py`
- Create: `7. AI-Business-Assistant/v2/eval/reports/sql_accuracy.md` (`EV-07`)
- Create: `7. AI-Business-Assistant/v2/eval/reports/calibration.png` (`EV-08`)
- Test: `7. AI-Business-Assistant/v2/tests/unit/test_sql_agent_node.py`
- Test: `7. AI-Business-Assistant/v2/tests/integration/test_sql_eval_dev.py`

**Interfaces:**
- Consumes: `app.knowledge.loader.{match_golden, load_kpis, get_kpi, load_benchmark}`, `app.core.security.{load_catalog, get_allowed_views}`, `app.sql.{validate, execute_validated_sql, run_validate_execute_with_repair, score_sql_confidence}`, `app.orchestration.{ChatState, build_graph}`.
- Produces:
  - `SqlPromptContext(BaseModel)`: `question: str`, `role: str`, `data_profile: str`, `as_of_date: date`, `allowed_views: set[str]`, `catalog_markdown: str`, `golden_matches: list[GoldenMatch]`, `matched_kpis: list[KpiDefinition]`, `c1_caveats: list[str]`, `known_missing_data_reason: str | None = None`
  - `SqlPipelineOutput(BaseModel)`: `status: SqlStatus`, `sql: str | None`, `columns: list[str]`, `rows: list[dict[str, Any]]`, `row_count: int`, `confidence: float`, `confidence_breakdown: ConfidenceBreakdown`, `kpi_keys: list[str]`, `attempts: list[RepairAttempt]`, `source_query_id: str`, `warnings: list[str]`, `error: str | None = None`, `latency_ms: float = 0.0`
  - `app.sql.context.build_sql_prompt_context(question: str, role: str, data_profile: str = "real", as_of_date: date = date(2026, 7, 31)) -> SqlPromptContext`
  - `app.sql.generator.SqlLLMClient` (Protocol: `generate_candidates(ctx: SqlPromptContext, n: int = 3) -> list[SqlDraft]`, `repair_sql(ctx: SqlPromptContext, broken_sql: str, sanitized_error: str) -> str`)
  - `app.sql.generator.{GeminiSqlLLMClient, OllamaSqlLLMClient, HeuristicGoldenSqlClient, MockSqlLLMClient, create_sql_llm_client}`
  - `app.agents.sql_agent.run_sql_pipeline(question: str, role: str, data_profile: str = "real", llm_client: SqlLLMClient | None = None, engine: Engine | None = None, n_candidates: int = 3) -> SqlPipelineOutput`
  - `app.agents.sql_agent.create_sql_lookup_node(llm_client: SqlLLMClient | None = None, settings: Settings | None = None) -> Callable[[ChatState], dict[str, Any]]`
  - `app.agents.sql_agent.confidence_gate_node(state: ChatState, min_confidence: float = 0.45) -> dict[str, Any]`
  - `app.orchestration.graph.build_sql_graph(llm_client: SqlLLMClient | None = None, settings: Settings | None = None, node_overrides: dict | None = None) -> CompiledStateGraph`
  - `eval.run_eval.run_sql_evaluation(split: str = "dev", final: bool = False, provider: str = "auto", output_dir: Path | None = None) -> dict[str, Any]`

- [ ] **Step 1: Viết failing unit & integration tests trong `test_sql_agent_node.py` và `test_sql_eval_dev.py`**

Trong `v2/tests/unit/test_sql_agent_node.py`:
- `test_tc_t3_04_no_data_skips_synthesizer_in_graph()`: dựng đồ thị qua `build_sql_graph(llm_client=mock_empty_client, node_overrides={"synthesize": spy_synthesize, "clarify": spy_clarify})` với câu hỏi trả `status="no_data"` (hoặc `out_of_scope_reason` cho giá vốn `B02-DN_11 = 0`) → `final_state["sql"]["status"] == "no_data"`, `synthesize_called is False`, `clarify_called is True`.
- `test_sql_agent_blocks_unpermitted_role_context()` (Review Focus #1): `role="quan_tri_he_thong"` → `status == "rejected"`, LLM không được gọi (`llm_calls == 0`); `role="quan_ly_kho"` → `SqlPromptContext.allowed_views == {"ai_v_ton_kho"}` và prompt không chứa tên `ai_v_no_vay` hay `ai_v_bctc`.
- `test_sql_agent_attaches_synthetic_warning_on_synth_profile()` (Review Focus #4): chạy node với `data_profile="synth"` → `"SYNTHETIC_DATA"` nằm trong `final_state["warnings"]`; khi `data_profile="real"` thì không có `"SYNTHETIC_DATA"`.

Trong `v2/tests/integration/test_sql_eval_dev.py`:
- `test_tc_t8_02_test_split_locked_without_final_flag()`: gọi `run_sql_evaluation(split="test", final=False)` → ném `PermissionError` (bảo vệ bộ test khoá C7).
- `test_tc_t8_01_eval_harness_deterministic_and_generates_ev07_ev08(tmp_path)`: chạy `run_sql_evaluation(split="dev", provider="heuristic", output_dir=tmp_path)` hai lần → `m06_execution_accuracy` và `m07_valid_sql_rate` hai lần giống hệt nhau; kiểm tra `sql_accuracy.md` (có bảng theo độ khó `de`/`vua`/`kho`, theo dashboard `D1..D5`, danh sách câu sai nếu có, commit hash, model/provider) và `calibration.png` (magic bytes PNG `\x89PNG\r\n\x1a\n`, kích thước `> 2048` bytes).

- [ ] **Step 2: Chạy pytest để xác nhận test fail**

Run: `pytest "7. AI-Business-Assistant/v2/tests/unit/test_sql_agent_node.py" "7. AI-Business-Assistant/v2/tests/integration/test_sql_eval_dev.py" -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.sql.context'` / `'app.agents'`).

- [ ] **Step 3: Triển khai `context.py`, `generator.py`, `sql_agent.py`, cập nhật `state.py` & `graph.py`**

1. `state.py`: thêm `data_profile: str` và `warnings: Annotated[list[str], operator.add]` vào `ChatState`. Giữ nguyên `build_graph()` mặc định trong `graph.py` để toàn bộ 9 unit test của Phase 1 (`test_orchestration_routing.py`) không đổi hành vi; bổ sung `build_sql_graph(...)` gắn `create_sql_lookup_node(...)` và `confidence_gate_node`.
2. `context.py`: nạp từ `catalog.yaml` chỉ các view thuộc `get_allowed_views(role)`, ghép top-3 `match_golden(question, role=role, k=3)`, ghép định nghĩa KPI có `nguon_view` thuộc `allowed_views`, và chèn ghi chú C1 (`AS_OF_DATE = 2026-07-31`, `B02-DN_11 = 0`, `B02-DN_23 = 0`, doanh thu trên `real` chỉ có `2026-07`). Phát hiện câu hỏi rơi vào lỗ hổng dữ liệu C1 đã biết trên `real` (biên lợi nhuận gộp, giá vốn thực tế, YoY 2025, doanh thu T1–T6) để gắn cờ `known_missing_data_reason`.
3. `generator.py`:
   - `GeminiSqlLLMClient`: gọi `ChatGoogleGenerativeAI(model=settings.llm_model, google_api_key=settings.google_api_key, temperature=...)` xuất JSON có cấu trúc `SqlDraft`.
   - `OllamaSqlLLMClient`: gọi endpoint `/api/generate` tại `settings.ollama_base_url` (model mặc định `qwen2.5-coder:7b`).
   - `HeuristicGoldenSqlClient`: bộ sinh SQL xác định dựa trên khớp Golden Query + quy tắc tham số hoá kỳ thời gian/bộ lọc trên `catalog.yaml` & `kpi_definitions.yaml` — dùng cho kiểm thử tất định offline (`TC-T8-01`) và làm dự phòng khi `GOOGLE_API_KEY` chưa cấu hình key thật và Ollama tắt (`provider="auto"` ghi rõ `effective_provider` trong báo cáo).
4. `sql_agent.py`: thực hiện trọn vẹn 6 bước, ghi `source_query_id` (`f"sql-{uuid8}"`), cập nhật `sql`, `kpi_keys` (chỉ xuất danh sách KPI khi `output.status == "ok"`; khi `output.status != "ok"` đặt `kpi_keys = []` để đồ thị bỏ qua nhánh `explain`/`trend`/`advise`), `warnings` (`["SYNTHETIC_DATA"]` nếu `data_profile == "synth"`), `errors`, và `trace` (thời gian chạy ms). `confidence_gate_node` giữ nguyên `needs_clarification=True` nếu đã bật; nếu `"sql"` có mặt trong `state` và (`status != "ok"` hoặc `confidence < min_confidence`), đặt `needs_clarification=True`.

- [ ] **Step 4: Triển khai `v2/eval/run_eval.py` và sinh `EV-07` (`sql_accuracy.md`) + `EV-08` (`calibration.png`)**

1. Trong `v2/eval/run_eval.py`:
   - Chặn ngay `split == "test"` khi `not final` bằng `PermissionError("TC-T8-02: Test split is locked. Pass --final to record an official test run.")`.
   - Chạy toàn bộ câu `loai == "sql"` (và kiểm tra thêm nhóm `ngoai_pham_vi` liên quan C1) của `split == "dev"` trên PostgreSQL `data_warehouse` qua `run_sql_pipeline()`, đối chiếu kết quả thực thi với `ky_vong` (`gia_tri` ± `dung_sai_tuong_doi`).
   - Ghi `EV-07` (`v2/eval/reports/sql_accuracy.md`) gồm: commit hash (`git rev-parse --short HEAD`), thời gian chạy UTC, `data_profile`, `configured_provider` & `effective_provider`, tổng hợp `M-06` (Execution Accuracy), `M-07` (Valid SQL Rate), bảng chia theo độ khó (`de`/`vua`/`kho`), bảng chia theo Dashboard (`D1..D5`), bảng kiểm tra nhóm C1 `no_data`, và danh sách chi tiết từng câu + nhóm lỗi.
   - Vẽ `EV-08` (`v2/eval/reports/calibration.png`) bằng `matplotlib` (`Agg` backend): biểu đồ Reliability Diagram (trục hoành: Confidence bin `[0.0–0.2, 0.2–0.4, 0.4–0.6, 0.6–0.8, 0.8–1.0]`, trục tung: Empirical Accuracy kèm đường chéo lý tưởng `y = x` và histogram số lượng câu mỗi bin).

- [ ] **Step 5: Sinh báo cáo `EV-07`, `EV-08` và chạy toàn bộ bộ kiểm thử v2 (Phase 1 + Phase 2)**

Run:
```powershell
python "7. AI-Business-Assistant/v2/eval/run_eval.py" --group sql --split dev
pytest "7. AI-Business-Assistant/v2/tests" -v
```
Expected: Toàn bộ test Phase 1 + Phase 2 đều PASS (0 failed); cả 5 bằng chứng cổng Phase 2 (`EV-03`, `EV-04`, `EV-05`, `EV-07`, `EV-08`) hiện diện đầy đủ trên đĩa.

- [ ] **Step 6: Commit Task 4**

```powershell
git add "7. AI-Business-Assistant/v2/app/sql/context.py" "7. AI-Business-Assistant/v2/app/sql/generator.py" "7. AI-Business-Assistant/v2/app/agents/" "7. AI-Business-Assistant/v2/app/orchestration/" "7. AI-Business-Assistant/v2/eval/" "7. AI-Business-Assistant/v2/tests/unit/test_sql_agent_node.py" "7. AI-Business-Assistant/v2/tests/integration/test_sql_eval_dev.py"
git commit -m "feat(v2-p2): implement 6-step SQLAgent node, dev SQL evaluation, and calibration plot"
```
