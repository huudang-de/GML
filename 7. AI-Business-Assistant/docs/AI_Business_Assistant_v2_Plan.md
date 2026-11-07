# AI Business Assistant — Gỗ Minh Long: Kế hoạch & Thiết kế v2.0 (bản hợp nhất)

> **Tài liệu hợp nhất** từ 2 nguồn, giữ nguyên toàn văn nội dung gốc (chỉ hạ cấp tiêu đề để gộp vào một tệp):
> - **Phần I** — `AI_Business_Assistant_v2_Plan.md` (Kế hoạch v2.0, cập nhật 09/10/2026): chẩn đoán, học hỏi dự án tham khảo, ý tưởng kiến trúc & lộ trình 8 tuần.
> - **Phần II** — `AI Business Assistant – Gỗ Minh Long Thiết kế v2.0 (chuẩn L5).md` (Thiết kế v2.0, phiên bản tài liệu 2.1, cập nhật 18/10/2026): thiết kế chi tiết theo tiêu chí L5.
>
> Khi hai phần khác nhau (ví dụ số tuần lộ trình, cấu trúc thư mục, model LLM), **Phần II là bản mới hơn** và được ưu tiên.

---

## Mục lục

**PHẦN I — Kế hoạch Phát triển AI Business Assistant**
- I.1. Chẩn đoán hiện trạng (As-Is)
- I.2. Học hỏi từ các dự án tham khảo
- I.3. Kiến trúc đề xuất — GML AI Assistant v2.0
- I.4. Lộ trình triển khai — 4 Giai đoạn (8 tuần)
- I.5. File Structure đề xuất
- I.6. Bảng ưu tiên triển khai
- I.7. Before vs After — Kỳ vọng chất lượng câu trả lời
- I.8. Tham khảo & Trích dẫn

**PHẦN II — Thiết kế v2.0 (chuẩn L5)**
- II.1. Mục tiêu, phạm vi và cách dùng tài liệu
- II.2. Nguyên tắc thiết kế
- II.3. Các lỗi của bản cũ cần sửa
- II.4. Kiến trúc tổng thể
- II.5. Luồng điều phối (LangGraph)
- II.6. Thành phần chi tiết
- II.7. Mô-đun tuỳ chọn: fine-tuning (có cổng quyết định)
- II.8. Triển khai
- II.9. Lộ trình triển khai (ước lượng theo tuần làm việc của một người)
- II.10. Hồ sơ quyết định kiến trúc (ADR)
- II.11. Checklist tự chấm L5 và rủi ro
- II.12. Tài liệu tham khảo (APA 7)

## Bản đồ đối chiếu ý tưởng Phần I ↔ Phần II

| Chủ đề | Phần I (Kế hoạch) | Phần II (Thiết kế L5) |
| --- | --- | --- |
| Hiện trạng & lỗi bản cũ | I.1 Chẩn đoán hiện trạng | II.3 Các lỗi của bản cũ cần sửa |
| Dự án tham khảo & quyết định | I.2 Học hỏi từ các dự án tham khảo | II.10 ADR · II.12 Tài liệu tham khảo |
| Kiến trúc & điều phối | I.3 Kiến trúc đề xuất | II.4 Kiến trúc tổng thể · II.5 Luồng điều phối |
| Lớp ngữ nghĩa, Golden Query | I.4 Giai đoạn 1 (1.1, 1.2) | II.6.1 Lớp ngữ nghĩa · II.6.2 Pipeline Text-to-SQL |
| Bộ nhớ hội thoại | I.4 Giai đoạn 1 (1.3) | II.6.5 Bộ nhớ hội thoại |
| Explainer / Trend / Advisor / Synthesizer | I.4 Giai đoạn 2, 3.1 | II.6.4 Các agent phân tích |
| Alert & bản tin | I.4 Giai đoạn 3 (3.2) | II.6.6 Workflow tự trị |
| Bảo mật, guard rails | I.4 Giai đoạn 4 (4.3) | II.6.7 Bảo mật và quyền truy cập |
| UI, API, feedback | I.4 Giai đoạn 3 (3.3), 4 (4.1, 4.2) | II.6.8 API đóng gói |
| Cấu trúc thư mục | I.5 File Structure đề xuất | II.8 Triển khai |
| Lộ trình & ưu tiên | I.4 Lộ trình 8 tuần · I.6 Bảng ưu tiên | II.9 Lộ trình triển khai |
| Đánh giá chất lượng | I.7 Before vs After | II.6.9 Quan sát và đánh giá · II.11 Checklist L5 |

---

## PHẦN I — Kế hoạch Phát triển AI Business Assistant — Gỗ Minh Long
> **Phiên bản:** 2.0 — Từ Query-Result Engine → Intelligence Decision Layer
> **Cập nhật:** 09/10/2026

---

### 1. Chẩn đoán hiện trạng (As-Is)

#### Kiến trúc hiện tại:
```
User Input
   ↓
classify_intent (LLM) → sql_only / rag_only / both
   ↓
sql_agent.py    → generate_sql → execute_sql (self-healing retry x3)
rag_agent.py    → ChromaDB retriever (guide_dashboard*.md)
   ↓
synthesizer.py  → Prompt: số liệu + rag_context → Trả lời
   ↓
Streamlit UI
```

#### Điểm mạnh đã có:
- ✅ LangGraph orchestration bài bản, có intent routing
- ✅ SQL self-healing: thất bại → tự sửa → retry 3 lần
- ✅ RAG từ guide_dashboard*.md (5 dashboard business guides)
- ✅ ChromaDB vector store đã build sẵn
- ✅ PostgreSQL silver schema đầy đủ (25+ tables)

#### Điểm yếu — Vì sao cần nâng cấp:

| Vấn đề | Biểu hiện | Tác động |
|---|---|---|
| **"Meaning Gap"** | Trả về số, không giải thích ý nghĩa | BQL không biết hành động tiếp theo |
| **Không có Semantic Layer** | LLM đoán tên cột, dễ sai | Sai số liệu, mất tin tưởng |
| **RAG thụ động** | Chỉ retrieval, không tích hợp sâu với SQL result | Câu trả lời rời rạc |
| **Không có memory** | Mỗi câu hỏi là phiên mới | Không thể hỏi follow-up |
| **Không có Insight Agent** | Không phân tích trend, không cảnh báo | Giá trị thấp với BQL |

---

### 2. Học hỏi từ các dự án tham khảo

#### 2.1 Vanna AI (github.com/vanna-ai/vanna) — *Archived 03/2026*
> Nguồn: [vanna.ai docs](https://vanna.ai), [themenonlab.blog](https://themenonlab.blog)

**Kiến trúc học được:**
- **RAG-first SQL Generation:** Trước khi generate SQL, pull từ vector store DDL schema + "Golden Queries" (câu hỏi-SQL đã verify) → accuracy tăng mạnh
- **Dual Output Pattern:** LLM nhận "summary" ngắn (tiết kiệm token), User nhận rich output (bảng, chart)
- **Tool Memory:** Lưu Query thành công vào vector store → câu hỏi tương tự tái sử dụng pattern

**Áp dụng vào GML:**
```
Xây dựng "Golden Query Bank" từ 5 file UAT SQL đã verify (UAT_01→05)
→ Mỗi khi user hỏi, retrieve Golden Query tương tự trước
→ Giảm hallucination, tăng tốc độ đáng kể
```

---

#### 2.2 Dataherald (github.com/Dataherald/dataherald)
> Nguồn: [github.com/Dataherald](https://github.com/Dataherald/dataherald), [readthedocs.io](https://dataherald.readthedocs.io)

**Kiến trúc học được:**
- **Agentic Tool Use (7 tools):** `QuerySQLDataBase`, `SchemaSQLDatabase`, `GetFewShotExamples`, `Evaluator` — mỗi tool có trách nhiệm rõ ràng
- **Confidence Scoring:** Evaluator chấm điểm độ tin cậy SQL → nếu thấp, cảnh báo user
- **Context Engineering:** Inject data dictionary (tên cột kỹ thuật → định nghĩa nghiệp vụ VN) vào prompt

**Áp dụng vào GML:**
```
+ ConfidenceEvaluator Agent
+ DataDictionary Layer (map cột kỹ thuật → ngôn ngữ nghiệp vụ GML)
+ Tool GetGoldenExamples từ UAT SQL bank
```

---

#### 2.3 LangGraph Multi-Agent Pattern
> Nguồn: [towardsai.net](https://towardsai.net), [medium.com](https://medium.com)

**Kiến trúc học được:**
- **Insight Agent Pattern:** Tách biệt "Data Agent" (lấy số) và "Insight Agent" (giải thích, gợi ý)
- **Self-Correction Loop:** SQL fail → Error Analyzer → Re-generate với context lỗi
- **Multi-Agent Routing:** Intent phức tạp → điều phối song song, merge kết quả

**Áp dụng vào GML:**
```
Tách synthesizer.py thành 3 agent độc lập:
- ExplainerAgent  : công thức + ý nghĩa chỉ số
- TrendAnalystAgent: so sánh trend, phát hiện bất thường
- DecisionAdvisorAgent: gợi ý hành động cụ thể cho BQL
```

---

### 3. Kiến trúc đề xuất — GML AI Assistant v2.0

```
STREAMLIT UI v2.0
[Chat] [Dashboard Quick Ask] [Alert Center] [History]
         |
ORCHESTRATOR v2.0 (LangGraph)
  - Intent Classifier
  - Session Memory
  - Guard Rail
  - Routing: sql_only / rag_only / both / alert / follow_up
         |
AGENT PIPELINE
  ① SQLAgent (nâng cấp)
      GoldenQuery Retriever [NEW]
      Semantic Schema Layer [NEW]
      generate_sql → execute_sql
      ConfidenceEvaluator [NEW]
      self-healing retry (giữ nguyên)

  ② RAGAgent (nâng cấp)
      guide_dashboard*.md (hiện có)
      KPI_definitions.yaml [NEW]
      Business_rules.md [NEW]

  ③ ExplainerAgent [NEW] ← KEY UPGRADE
      Công thức chỉ số là gì
      Các yếu tố cấu thành
      Ý nghĩa trong bối cảnh GML

  ④ TrendAnalystAgent [NEW] ← KEY UPGRADE
      So sánh kỳ trước / cùng kỳ năm trước
      Phát hiện bất thường (threshold alerts)
      Dự báo ngắn hạn (từ ML models đã có)

  ⑤ DecisionAdvisorAgent [NEW] ← KEY UPGRADE
      Gợi ý hành động cụ thể
      Cảnh báo rủi ro
      Liên kết đến dashboard Power BI

  ⑥ Synthesizer v2.0 (nâng cấp)
      Merge output từ tất cả agents → Structured response
         |
DATA & KNOWLEDGE LAYER
  - PostgreSQL Silver Schema (hiện có)
  - ChromaDB guide_dashboard*.md (hiện có)
  - Golden Query Bank [NEW — từ UAT SQL files]
  - KPI Definition Store [NEW — YAML]
  - Session Store [NEW — SQLite]
```

---

### 4. Lộ trình triển khai — 4 Giai đoạn (8 tuần)

---

#### Giai đoạn 1 — Nền tảng & Ổn định (Tuần 1–2)
> **Mục tiêu:** Làm hệ thống hiện tại đáng tin cậy, sẵn sàng mở rộng

##### 1.1 Semantic Schema Layer (DataDictionary)
Tạo `app/knowledge/kpi_definitions.yaml` — map kỹ thuật → nghiệp vụ:
```yaml
fact_cashflow:
  account_no:
    meaning: "Mã tài khoản kế toán (VD: 112x = Tiền gửi, 341x = Vay nợ)"
    filter_patterns:
      - "112%: Tiền gửi ngân hàng"
      - "341%: Vay và nợ thuê tài chính"

KPIs:
  Du_No_Ngan_Han:
    formula: "SUM(credit_balance) WHERE account_no LIKE '34111%' OR '34113%' OR '34114%'"
    meaning: "Tổng dư nợ vay ngắn hạn (<=12 tháng) với các ngân hàng"
    components:
      - "TK 34111: Vay ngắn hạn"
      - "TK 34113: Trái phiếu ngắn hạn"
      - "TK 34114: Thuê tài chính ngắn hạn"
    thresholds:
      warning: "> 70% hạn mức tín dụng"
      critical: "> 90% hạn mức tín dụng"
    actions:
      high: "Xem xét cơ cấu lại nợ hoặc đàm phán gia hạn với ngân hàng"
```

**Files cần tạo:**
- `app/knowledge/kpi_definitions.yaml` — 18 KPI từ Dashboard 1-5
- `app/knowledge/business_rules.md` — Ngưỡng, quy tắc nghiệp vụ GML
- `scripts/build_kpi_store.py`

##### 1.2 Golden Query Bank
Nguồn: 5 file UAT SQL đã verify (UAT_01→05 — đã có đầy đủ VISUAL + MEASURE + RESULT LOG)

```python
# Mỗi entry trong Golden Query Bank:
{
    "question_vi": "Dư nợ ngắn hạn hiện tại là bao nhiêu?",
    "sql": "WITH latest_balances AS (...) SELECT SUM(credit_balance)...",
    "measure": "_TaiChinh[Du_No_Ngan_Han]",
    "kpi_key": "Du_No_Ngan_Han",
    "result_sample": "236,065,233,815 VND"
}
```

Script: `scripts/build_golden_query_bank.py` — parse 5 UAT SQL → ChromaDB collection riêng

##### 1.3 Session Memory
```python
# app/memory/session_store.py
class SessionMemory:
    def get_history(self, session_id) -> list[dict]
    def add_turn(self, session_id, query, answer, sql, kpi_keys)
    def get_context_summary(self, session_id) -> str  # Tóm tắt 5 turns gần nhất cho LLM
```

---

#### Giai đoạn 2 — Intelligence Layer: Explain + Analyze (Tuần 3–4)
> **Mục tiêu:** Câu trả lời đủ Công thức + Ý nghĩa + Xu hướng

##### 2.1 ExplainerAgent (Agent quan trọng nhất)

**Trigger:** Khi SQL trả về kết quả liên quan đến KPI đã định nghĩa

**Output mẫu:**
```
📊 Dư nợ ngắn hạn: 236,065,233,815 VNĐ

🔢 Công thức tính:
   Dư nợ ngắn hạn = Số dư cuối kỳ TK 34111 + TK 34113 + TK 34114
   (Vay ngắn hạn + Trái phiếu ngắn hạn + Thuê tài chính ngắn hạn)

📦 Các yếu tố cấu thành:
   - TK 34111 - Vay ngắn hạn ngân hàng: ~190 tỷ (80.5%)
   - TK 34113 - Trái phiếu ngắn hạn: ~30 tỷ (12.7%)
   - TK 34114 - Thuê tài chính ngắn hạn: ~16 tỷ (6.8%)

💡 Ý nghĩa:
   Nghĩa vụ nợ phải thanh toán trong 12 tháng tới.
   So sánh với Tổng TSNH để tính Current Ratio → đo lường thanh khoản.
```

**Kỹ thuật:**
- Map `sql_result` → `kpi_key` bằng similarity search trong Golden Query Bank
- Load `kpi_definitions.yaml` theo `kpi_key`
- Prompt LLM với đầy đủ context công thức + components + ngữ cảnh GML

##### 2.2 TrendAnalystAgent

**Tự động:** Query thêm lịch sử 12 tháng mà không cần user hỏi riêng

**Output mẫu:**
```
📈 Xu hướng 12 tháng gần nhất:
   01/2026: 314.7 tỷ → 07/2026: 290.9 tỷ
   Xu hướng: GIẢM -7.6% (tích cực — giảm gánh nặng lãi vay)

⚠️ Bất thường phát hiện:
   Tháng 06→07/2026: giảm đột biến 59 tỷ (-16.8%)
   → Có thể do tất toán khoản vay lớn
```

Tích hợp ML: Gọi `fact_cashflow_forecast` (đã có từ module ML) để dự báo forward-looking

##### 2.3 Synthesizer v2.0 — Structured Response

```python
class SynthesizerV2:
    def run(self, state) -> dict:
        return {
            "answer": str,          # Câu trả lời chính ngắn gọn
            "explanation": str,     # ExplainerAgent output
            "trend_analysis": str,  # TrendAnalystAgent output
            "decision_advice": str, # DecisionAdvisorAgent output
            "sql_query": str,       # SQL đã chạy (transparency)
            "confidence": float,    # 0-1
            "sources": list[str],   # RAG sources
            "kpi_keys": list[str],  # KPIs liên quan
        }
```

---

#### Giai đoạn 3 — Decision Support Layer (Tuần 5–6)
> **Mục tiêu:** Chủ động đề xuất hành động, cảnh báo ngưỡng

##### 3.1 DecisionAdvisorAgent

**Output mẫu:**
```
🎯 Gợi ý hành động cho Ban Quản trị:

🔴 CẢNH BÁO: Dư nợ ngắn hạn (236 tỷ) = 80% Hạn mức tín dụng (295 tỷ)
   Hạn mức còn lại: 24.1 tỷ VNĐ

📋 Đề xuất:
   1. Ngắn hạn (0-30 ngày): Rà soát khoản vay đáo hạn Q3/2026
      → MB Bank: ~15 tỷ, TP Bank: ~6.5 tỷ
   2. Trung hạn (1-3 tháng): Chuyển phần nợ NH → dài hạn
      → Cải thiện Current Ratio (hiện: 1.39)
   3. Dài hạn: Tăng tỷ lệ VCSH để giảm D/E ratio (0.64)

🔗 Xem chi tiết: Dashboard Tài Chính → Lịch trả gốc ngân hàng
```

##### 3.2 Alert & Monitoring Engine
```python
# app/alerts/alert_engine.py — Cron job hàng ngày
ALERT_RULES = [
    {
        "name": "Dư nợ vượt 85% hạn mức",
        "kpi": "Du_No_Ngan_Han",
        "condition": "du_no / han_muc > 0.85",
        "severity": "critical",
    },
    {
        "name": "Current Ratio dưới ngưỡng an toàn",
        "kpi": "Current_Ratio",
        "condition": "value < 1.2",
        "severity": "warning",
    }
]
```

##### 3.3 Power BI Quick Ask Integration
Power BI gửi URL param `?dashboard=tai_chinh&kpi=du_no_ngan_han`
→ Streamlit pre-load context đúng dashboard đang xem → UX mượt mà

---

#### Giai đoạn 4 — UX & Production Hardening (Tuần 7–8)
> **Mục tiêu:** Ổn định, dễ dùng, sẵn sàng BQL dùng thường ngày

##### 4.1 Streamlit UI v2.0 Layout
```
| Sidebar              | Main Chat                          |
|----------------------|------------------------------------|
| 📋 Lịch sử hội thoại | 💬 Chat chính                      |
| 🔔 Alerts (2 mới)    | ┌─ 📊 Số liệu                     |
| 📌 Quick Asks:       | │  236,065,233,815 VNĐ            |
|   • Tài chính        | ├─ 🔢 Công thức & Ý nghĩa [▼]    |
|   • Tồn kho          | ├─ 📈 Xu hướng 12 tháng [chart]  |
|   • Công nợ          | └─ 🎯 Gợi ý hành động            |
|   • Dòng tiền        | [Xem SQL] [Export PDF] [👍 👎]    |
|                      | [ Nhập câu hỏi... → ]             |
```

##### 4.2 Feedback Loop
```python
# 👍 → Lưu (query, sql, answer) vào Golden Query Bank → tăng accuracy
# 👎 → Ghi log review queue → DA review → sửa → re-add
```

##### 4.3 Guard Rails & Security
```python
class SQLGuardRail:
    BLOCKED = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]
    # 1. Block destructive operations
    # 2. Enforce LIMIT clause
    # 3. Whitelist schema silver.*
    # 4. Log all queries for audit trail
```

---

### 5. File Structure đề xuất

```
7. AI-Business-Assistant/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py       # Nâng cấp: routing + memory
│   │   ├── sql_agent.py          # Nâng cấp: + Golden Query retrieval
│   │   ├── rag_agent.py          # Nâng cấp: + KPI definition store
│   │   ├── explainer_agent.py    # [NEW] Giải thích công thức KPI
│   │   ├── trend_analyst.py      # [NEW] Phân tích xu hướng 12T
│   │   ├── decision_advisor.py   # [NEW] Gợi ý hành động BQL
│   │   └── synthesizer.py        # Nâng cấp → v2.0 structured output
│   ├── knowledge/
│   │   ├── kpi_definitions.yaml  # [NEW] 18 KPI: công thức + ngưỡng
│   │   ├── business_rules.md     # [NEW] Quy tắc nghiệp vụ GML
│   │   └── golden_queries/       # [NEW] Verified Q-SQL pairs
│   ├── memory/
│   │   └── session_store.py      # [NEW] SQLite conversation memory
│   ├── guardrails/
│   │   └── validator.py          # [NEW] SQL safety validation
│   ├── alerts/
│   │   └── alert_engine.py       # [NEW] Threshold monitoring cron
│   └── streamlit_app.py          # Redesign UI v2.0
├── scripts/
│   ├── build_golden_query_bank.py # [NEW] Parse UAT SQL → ChromaDB
│   ├── build_kpi_store.py         # [NEW] Build KPI YAML index
│   └── run_alert_check.py         # [NEW] Daily alert cron
└── tests/
    ├── test_sql_accuracy.py        # Verify vs Golden Query results
    └── test_explainer.py           # Verify explanation quality
```

---

### 6. Bảng ưu tiên triển khai

| # | Feature | Impact | Effort | Priority |
|---|---|---|---|---|
| 1 | `kpi_definitions.yaml` — 18 KPI từ Dashboard 1-5 | Critical | S | **P0** |
| 2 | Golden Query Bank từ UAT_01→05 SQL | Critical | M | **P0** |
| 3 | ExplainerAgent — Công thức + Ý nghĩa | Critical | M | **P0** |
| 4 | Session Memory (SQLite) | High | S | **P1** |
| 5 | TrendAnalystAgent — Auto historical query | High | L | **P1** |
| 6 | DecisionAdvisorAgent + Thresholds | Medium | L | **P2** |
| 7 | Streamlit UI v2.0 redesign | Medium | L | **P2** |
| 8 | Alert Engine (cron) | Medium | M | **P2** |
| 9 | Feedback Loop (thumbs up/down) | Nice-to-have | M | **P3** |
| 10 | Power BI Quick Ask integration | Nice-to-have | L | **P3** |

---

### 7. Before vs After — Kỳ vọng chất lượng câu trả lời

#### BEFORE (v1.0 hiện tại):
> **User:** Dư nợ ngắn hạn bao nhiêu?
>
> **AI:** Dư nợ ngắn hạn hiện tại là **236,065,233,815 VNĐ**.

#### AFTER (v2.0 target):
> **User:** Dư nợ ngắn hạn bao nhiêu?
>
> **AI:**
>
> 📊 **Dư nợ ngắn hạn: 236,065,233,815 VNĐ** (≈ 236 tỷ)
> *Cập nhật: 31/07/2026 — kỳ gần nhất trong Data Warehouse*
>
> 🔢 **Công thức:** Tổng số dư cuối kỳ TK 34111 + TK 34113 + TK 34114
> *(Vay ngắn hạn + Trái phiếu ngắn hạn + Thuê tài chính ngắn hạn từ silver.fact_cashflow)*
>
> 📦 **Cấu thành chính:** Vay ngắn hạn ngân hàng chiếm phần lớn
> → Chi tiết: Dashboard Tài Chính → Dư nợ theo Bank
>
> 📈 **Xu hướng:** Giảm từ 314.7 tỷ (01/2026) → 236 tỷ (07/2026) = **-25%**
> → Tích cực: giảm áp lực lãi vay
>
> ⚠️ **Lưu ý:** Dư nợ hiện = **80%** hạn mức được cấp (295 tỷ)
> Hạn mức còn lại: **24.1 tỷ** — cần theo dõi sát
>
> 🎯 **Gợi ý BQL:** Rà soát lịch đáo hạn Q3/2026
> MB Bank ~15 tỷ, TP Bank ~6.5 tỷ → Chuẩn bị nguồn tiền hoặc đàm phán gia hạn

---

### 8. Tham khảo & Trích dẫn

| Nguồn | Học được | Link |
|---|---|---|
| **Vanna AI** | RAG-first SQL, Golden Query Bank, Tool Memory, Dual Output | [vanna.ai](https://vanna.ai) — github archived 03/2026 |
| **Dataherald** | Agentic Tool Use, Confidence Scoring, Context Engineering | [github.com/Dataherald/dataherald](https://github.com/Dataherald/dataherald) |
| **LangGraph** | Multi-agent orchestration, State management, Conditional routing | [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |
| **Insight Pattern** | Data Layer → Insight Layer tách biệt | [studioriente.com](https://studioriente.com) |
| **BIRD Benchmark** | VES metric cho SQL quality evaluation | [arxiv.org/abs/2305.03111](https://arxiv.org/abs/2305.03111) |

---

## PHẦN II — AI Business Assistant – Gỗ Minh Long: Thiết kế v2.0 (chuẩn L5)

*Phiên bản tài liệu 2.1 · Cập nhật 18/10/2026 · v1 giữ nguyên làm baseline · Đây là tài liệu thiết kế: các mục "bằng chứng" chỉ có giá trị sau khi triển khai*

### 1. Mục tiêu, phạm vi và cách dùng tài liệu

**Mục tiêu:** v2 là bản thiết kế đáp ứng các tiêu chí cấp L5 trong thang 7 cấp độ của Sổ tay (VinUniversity, 2026, tr. 3): ứng dụng AI agentic hoàn chỉnh, hệ thống RAG hoàn chỉnh, workflow tự trị, dịch vụ API đóng gói, và quyết định kỹ thuật ở cấp ứng dụng do chính bạn đưa ra.

**Quan hệ v1 và v2.**

- **v1 giữ nguyên:** gắn tag `v1.0`, giữ nhánh `v1-baseline`, không sửa thêm. Nó là bản "cơ bản" bạn muốn giữ.
- **v2 xây thành phiên bản riêng**, dùng chung kho dữ liệu PostgreSQL. Cả hai chạy trên **cùng một bộ benchmark** nên bạn có bảng so sánh trước/sau. Đây là cách biến việc giữ v1 thành bằng chứng: không chỉ "v2 nhiều tính năng hơn" mà "v2 chính xác hơn bao nhiêu, an toàn hơn ở đâu".

**Quy ước trung thực.** "Chuẩn L5" trong tài liệu này nghĩa là thiết kế **đáp ứng đủ tiêu chí**. Bậc thật chỉ được xác nhận khi có sản phẩm chạy được, có số đo, và bạn tự giải thích được từng thành phần. Vì vậy mỗi tiêu chí đều có cột "bằng chứng cần tạo ra".

#### 1.1 Bản đồ tiêu chí L5 → thành phần v2

| Tiêu chí L5 (Sổ tay, tr. 3) | Thành phần v2 | Bằng chứng sẽ có khi triển khai |
| --- | --- | --- |
| Ứng dụng AI agentic hoàn chỉnh | Orchestrator LangGraph, 6 agent, memory, guardrail (mục 5, 6) | Đồ thị chạy được; trace từng bước; test tích hợp cho từng loại ý định |
| Hệ thống RAG hoàn chỉnh | Nạp, chia, index, truy hồi lai, xếp hạng lại, trích nguồn, kiểm tra bám nguồn (6.3) | Báo cáo Hit@k, MRR; tỷ lệ câu trả lời bám nguồn |
| Workflow tự trị | Alert engine và bản tin tuần tự động (6.6) | Nhật ký chạy theo lịch; cảnh báo đã gửi và đã xác nhận |
| Dịch vụ API đóng gói | API `/v1` có xác thực, OpenAPI, Docker (6.8, 8) | `docker compose up` chạy được trên máy sạch; test hợp đồng API |
| Fine-tuning LLM cho lĩnh vực cụ thể (Sổ tay nêu là ví dụ sản phẩm L5) | Mô-đun tuỳ chọn có cổng quyết định (mục 7) | Báo cáo so với baseline, hoặc ADR giải thích vì sao không làm |
| Quyết định kỹ thuật cấp ứng dụng (tự chủ) | Hồ sơ quyết định kiến trúc ADR (mục 10) | 5–7 ADR có phương án, tiêu chí, kết luận |
| Độc lập thiết kế và triển khai | Toàn bộ repo | Bạn tự trình bày 15 phút không nhìn tài liệu |

### 2. Nguyên tắc thiết kế

1. **LLM không tự tính số tài chính.** Số liệu đến từ SQL đã kiểm chứng; LLM chỉ diễn đạt.
2. **Mọi con số phải truy được nguồn:** một truy vấn đã chạy, hoặc một tài liệu cụ thể.
3. **Quyền tối thiểu** (Saltzer & Schroeder, 1975): AI chỉ đọc, chỉ thấy các view được cấp, theo vai trò người dùng.
4. **Kiểm chứng được:** mọi thay đổi chạy lại benchmark; không dùng cảm giác "có vẻ tốt hơn".
5. **Thất bại phải lộ ra:** không nuốt lỗi, có điểm tin cậy, thà hỏi lại hoặc từ chối còn hơn đoán.
6. **Cấu hình tách khỏi code:** tên model, chuỗi kết nối, đường dẫn, ngưỡng đều nằm ở config và biến môi trường.
7. **Quy tắc trước, diễn đạt sau:** công thức, ngưỡng, hành động lấy từ YAML do bạn và người nghiệp vụ duyệt; LLM chỉ viết lại thành văn.
8. **Tự trị có biên:** hệ thống tự phát hiện và tự cảnh báo, **không** tự thực hiện hành động tài chính.

### 3. Các lỗi của bản cũ cần sửa

| # | Vấn đề | Ở đâu | Cách sửa trong v2 |
| --- | --- | --- | --- |
| 1 | Nhánh `both` đi qua SQL rồi nối thẳng sang synthesize, RAG không chạy | v1 orchestrator | Chạy song song SQL và RAG, gộp rồi mới tổng hợp (mục 5) |
| 2 | `except:` trống khi tải vector store | v1 rag\_agent | Bắt lỗi cụ thể, ghi log, health check báo trạng thái index |
| 3 | Chuỗi kết nối DB và đường dẫn `D:\` viết cứng, trong khi README nói dùng `.env` | v1 sql\_agent, rag\_agent | Một lớp cấu hình duy nhất, không đặt bí mật trong repo |
| 4 | `intermediate_steps` xử lý như dict | v1 sql\_agent | Tự viết bước sinh và chạy SQL có kiểu dữ liệu rõ, không phụ thuộc cấu trúc nội bộ của agent dựng sẵn |
| 5 | An toàn SQL xếp ưu tiên thấp và chỉ chặn từ khoá | v2 cũ | Đưa lên Phase 1: tài khoản DB chỉ đọc, view được phép, kiểm tra AST |
| 6 | Số minh hoạ tự mâu thuẫn (dư nợ 236 và 290,9 tỷ; 80% của 295 tỷ còn 24,1 tỷ; 80% bị gắn đỏ dù ngưỡng nghiêm trọng là 90%) | v2 cũ | Bộ số minh hoạ nhất quán (6.1); ngưỡng đọc từ YAML, không gõ tay trong văn bản |
| 7 | Advisor để LLM tự suy ra hành động tài chính | v2 cũ | Luật ngưỡng quyết định; LLM chỉ diễn đạt; gắn nhãn "gợi ý, cần người có thẩm quyền quyết định" |
| 8 | Tên model và API thư viện viết cứng (`gemini-1.5-pro`, `Chroma.persist`) | v1 | Model qua config, kiểm tra còn được hỗ trợ; ghim phiên bản thư viện |
| 9 | Không xác thực, phân quyền, nhật ký kiểm toán | v1, v2 cũ | Mục 6.7 |
| 10 | KPI chỉ là mục tiêu, chưa có phép đo | v1 | Benchmark và harness đánh giá (6.9) |

### 4. Kiến trúc tổng thể

```
┌──────────────────────────────────────────────────────────────┐
│ CLIENT: Streamlit (Chat, Alert Center, Lịch sử)  ·  Power BI │
└───────────────┬──────────────────────────────────────────────┘
                │ HTTPS + token
┌───────────────▼──────────────────────────────────────────────┐
│ API GATEWAY (FastAPI /v1): xác thực, RBAC, rate limit,       │
│ request_id, kiểm tra schema, nhật ký kiểm toán               │
└───────────────┬──────────────────────────────────────────────┘
┌───────────────▼──────────────────────────────────────────────┐
│ ORCHESTRATOR (LangGraph, state có kiểu)                      │
│ guard_input → resolve_context → classify_intent → nhánh      │
│ → join → explain/trend → advise → confidence_gate            │
│ → synthesize → guard_output                                  │
└───┬────────┬─────────┬──────────┬──────────┬─────────────────┘
    ▼        ▼         ▼          ▼          ▼
 SQL Agent  RAG     Explainer   Trend     Advisor
 (6 bước)  (lai)   (YAML+LLM)  Analyst   (luật+LLM)
    │        │         │          │          │
┌───▼────────▼─────────▼──────────▼──────────▼─────────────────┐
│ KNOWLEDGE: kpi_definitions.yaml · business_rules.yaml ·      │
│ golden_queries · tài liệu (vector store) · session store     │
├──────────────────────────────────────────────────────────────┤
│ DATA: PostgreSQL, tài khoản gml_ai_ro (chỉ đọc) → view ai_*  │
│ trên schema silver; bảng nhật ký ở schema riêng (có quyền ghi)│
├──────────────────────────────────────────────────────────────┤
│ WORKER: scheduler (alert engine, bản tin tuần)               │
│ OBSERVABILITY: log có cấu trúc · trace · metrics · eval      │
└──────────────────────────────────────────────────────────────┘
```

### 5. Luồng điều phối (LangGraph)

| Ý định | Nhánh chạy | Ví dụ |
| --- | --- | --- |
| `sql_only` | SQL → (explain ∥ trend nếu có KPI) → advise | "Dư nợ ngắn hạn bao nhiêu?" |
| `rag_only` | RAG → synthesize | "Vòng quay phải thu tính thế nào?" |
| `both` | SQL ∥ RAG → join → explain ∥ trend → advise | "Tại sao lợi nhuận giảm?" |
| `alert` | Đọc cảnh báo đã tính sẵn → synthesize | "Hôm nay có cảnh báo gì?" |
| follow-up | Không phải nhánh riêng: `resolve_context` viết lại thành câu độc lập rồi phân loại lại | "Còn tháng trước?" thành "Dư nợ ngắn hạn tháng trước là bao nhiêu?" |
| `blocked` | Từ chối có lý do, không gọi SQL | Yêu cầu xoá dữ liệu, vượt quyền, ngoài phạm vi |

Phân loại ý định dùng **đầu ra có cấu trúc** (enum) thay vì "trả lời một từ", kèm luật từ khoá dự phòng khi LLM lỗi.

```python
# app/orchestration/state.py
from typing import TypedDict, Literal, Annotated
import operator

Intent = Literal['sql_only', 'rag_only', 'both', 'alert', 'blocked']

class ChatState(TypedDict, total=False):
    request_id: str
    user: dict                  # {'id': ..., 'role': 'ceo' | 'accountant' | ...}
    session_id: str
    query: str                  # câu gốc
    standalone_query: str       # sau khi giải quyết follow-up
    intent: Intent
    sql: dict                   # {'sql','columns','rows','row_count','confidence'}
    rag: dict                   # {'chunks','sources','grounding_ok'}
    kpi_keys: list[str]
    explanation: dict
    trend: dict
    advice: list[dict]
    needs_clarification: bool
    answer: dict
    errors: Annotated[list[str], operator.add]   # nhiều node cùng ghi được
```

```python
# app/orchestration/graph.py  (phác thảo: cần chạy thử với phiên bản LangGraph bạn cài)
from langgraph.graph import StateGraph, START, END

def route_after_intent(state) -> list[str]:
    return {
        'sql_only': ['sql_lookup'],
        'rag_only': ['rag_lookup'],
        'both':     ['sql_lookup', 'rag_lookup'],   # song song
        'alert':    ['alert_summary'],
        'blocked':  ['synthesize'],
    }[state['intent']]

def route_after_join(state) -> list[str]:
    if state.get('kpi_keys'):
        return ['explain', 'trend']                  # song song
    return ['confidence_gate']

g = StateGraph(ChatState)
for name, fn in NODES.items():                       # NODES: dict tên → hàm
    g.add_node(name, fn)

g.add_edge(START, 'guard_input')
g.add_edge('guard_input', 'resolve_context')
g.add_edge('resolve_context', 'classify_intent')
g.add_conditional_edges('classify_intent', route_after_intent)

for src in ['sql_lookup', 'rag_lookup', 'alert_summary']:
    g.add_edge(src, 'join')                          # join: node rỗng, gom nhánh
g.add_conditional_edges('join', route_after_join)

g.add_edge('explain', 'advise')
g.add_edge('trend', 'advise')
g.add_edge('advise', 'confidence_gate')
g.add_conditional_edges(
    'confidence_gate',
    lambda s: 'clarify' if s.get('needs_clarification') else 'synthesize',
    {'clarify': 'clarify', 'synthesize': 'synthesize'},
)
g.add_edge('clarify', 'guard_output')
g.add_edge('synthesize', 'guard_output')
g.add_edge('guard_output', END)
app = g.compile()
```

**Vì sao có node `join`:** khi một số nhánh không chạy (ví dụ `sql_only`), một node chờ "cả hai nhánh" sẽ không bao giờ được kích hoạt. Node `join` nhận từng cạnh riêng lẻ nên chạy đúng một lần sau khi các nhánh đang chạy xong. Cơ chế gộp và song song có thể khác nhau giữa các phiên bản LangGraph, nên **viết test bắt buộc**: câu hỏi `both` phải cho state chứa cả `sql` lẫn `rag` (đây chính là lỗi của v1).

### 6. Thành phần chi tiết

#### 6.1 Lớp ngữ nghĩa: KPI và quy tắc nghiệp vụ

**Vì sao cần.** LLM không biết cột `account_no` của bạn nghĩa là gì, hay "dư nợ ngắn hạn" gồm những tài khoản nào. Bộ chuẩn text-to-SQL BIRD đưa cả *kiến thức bên ngoài* (định nghĩa nghiệp vụ) vào đề bài vì thiếu nó thì mô hình dễ hiểu sai ý câu hỏi (Li et al., 2023). Trong dự án này, lớp ngữ nghĩa chính là data dictionary và định nghĩa KPI bạn đã viết khi làm BRD, được đưa về dạng máy đọc được.

```yaml
# app/knowledge/kpi_definitions.yaml
kpis:
  du_no_ngan_han:
    ten: Dư nợ ngắn hạn
    don_vi: VND
    cong_thuc: Tổng số dư cuối kỳ các tài khoản 34111, 34113, 34114
    nguon_view: ai_v_dong_tien_so_du
    golden_ref: UAT_03_Q01              # trỏ tới truy vấn đã kiểm chứng (ví dụ)
    thanh_phan:
      - {tk: '34111', ten: Vay ngắn hạn}
      - {tk: '34113', ten: Trái phiếu ngắn hạn}
      - {tk: '34114', ten: Thuê tài chính ngắn hạn}
    y_nghia: Nghĩa vụ nợ phải trả trong 12 tháng tới; so với hạn mức tín dụng cho biết dư địa vay còn lại.
    chi_so_phu:
      ty_le_su_dung_han_muc: du_no_ngan_han / han_muc_tin_dung
    nguong:
      chi_so: ty_le_su_dung_han_muc
      canh_bao: 0.70
      nghiem_trong: 0.90
    hanh_dong:
      canh_bao:
        - Rà soát lịch đáo hạn trong 90 ngày tới
        - Cập nhật dự báo dòng tiền
      nghiem_trong:
        - Họp rà soát cơ cấu nợ với Kế toán trưởng
        - Làm việc với ngân hàng về gia hạn hoặc nâng hạn mức
```

**Bộ số minh hoạ nhất quán** (dùng để viết test; đây không phải dữ liệu thật của doanh nghiệp):

| Chỉ tiêu | Giá trị | Cách tính |
| --- | --- | --- |
| Dư nợ ngắn hạn (07/2026) | 236,07 tỷ | Từ view nguồn |
| Hạn mức tín dụng | 295 tỷ | Từ bảng hạn mức |
| Tỷ lệ sử dụng hạn mức | 80,0% | 236,07 / 295 |
| Mức cảnh báo | Cảnh báo (vàng) | 70% ≤ 80% < 90% |
| Hạn mức còn lại | 58,93 tỷ | 295 − 236,07 |
| Dư nợ 01/2026 → 07/2026 | 314,7 → 236,07 tỷ | −25,0% |
| Dư nợ 06/2026 → 07/2026 | 283,7 → 236,07 tỷ | −16,8%, vượt ngưỡng bất thường 15% |

#### 6.2 Pipeline Text-to-SQL (6 bước)

| Bước | Việc làm | Điểm thiết kế |
| --- | --- | --- |
| 1. Truy hồi ngữ cảnh | Lấy các Golden Query giống câu hỏi nhất, mô tả view liên quan, định nghĩa KPI | Chỉ đưa vào prompt các view vai trò người dùng được phép thấy |
| 2. Sinh SQL | LLM sinh SQL, nhiệt độ thấp, đầu ra có cấu trúc (`sql`, `giai_thich_ngan`) | Không dùng agent dựng sẵn; bạn kiểm soát từng bước |
| 3. Kiểm tra | Phân tích cú pháp (AST), chỉ một câu `SELECT`, bảng nằm trong danh sách cho phép, không dùng hàm nguy hiểm, thêm `LIMIT` | Lớp phòng thủ **thứ hai**; lớp thứ nhất là quyền DB (6.7) |
| 4. Thực thi | Chạy bằng tài khoản chỉ đọc, giới hạn thời gian và số dòng | Lỗi DB được làm sạch trước khi dùng lại |
| 5. Xác minh | Tính điểm tin cậy (bên dưới) | Dưới ngưỡng thì hỏi lại hoặc cảnh báo rõ |
| 6. Sửa lỗi | Nếu lỗi: đưa thông báo lỗi đã làm sạch cho LLM, thử lại tối đa 3 lần | Ghi lại mọi lần thử để phân tích nhóm lỗi |

```python
# app/sql/validator.py (phác thảo, cần chạy thử với phiên bản sqlglot bạn cài)
import sqlglot
from sqlglot import exp

FORBIDDEN_FUNCS = {'pg_sleep', 'pg_read_file', 'lo_import', 'dblink'}

class SqlRejected(Exception):
    pass

def validate(sql: str, allowed_tables: set[str], max_rows: int = 1000) -> str:
    trees = sqlglot.parse(sql, read='postgres')
    if len(trees) != 1 or not isinstance(trees[0], exp.Select):
        raise SqlRejected('Chỉ cho phép một câu SELECT')
    tree = trees[0]
    cte_names = {c.alias.lower() for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        name = t.name.lower()
        if name not in allowed_tables and name not in cte_names:
            raise SqlRejected(f'Bảng không được phép: {t.name}')
    for f in tree.find_all(exp.Func):
        fname = (getattr(f, 'name', '') or f.sql_name()).lower()
        if fname in FORBIDDEN_FUNCS:
            raise SqlRejected(f'Hàm không được phép: {fname}')
    if not tree.args.get('limit'):
        tree = tree.limit(max_rows)
    return tree.sql(dialect='postgres')
```

**Điểm tin cậy.** Không để LLM tự chấm "tôi chắc 90%". Dùng tín hiệu đo được, theo tinh thần *self-consistency*: sinh vài phương án SQL rồi so kết quả thực thi (Wang et al., 2023).

| Tín hiệu | Trọng số khởi điểm | Cách đo |
| --- | --- | --- |
| Kiểm tra AST và thực thi thành công | Cổng bắt buộc (không qua thì điểm = 0) | Kết quả bước 3 và 4 |
| Độ giống với Golden Query | 0,3 | Độ tương đồng vector của câu hỏi với câu đã kiểm chứng |
| Nhất quán giữa 3 lần sinh | 0,4 | Tỷ lệ phương án cho cùng kết quả thực thi |
| Hợp lý của kết quả | 0,3 | Không rỗng, không toàn NULL, giá trị trong dải lịch sử của KPI |

Trọng số chỉ là điểm xuất phát. Sau khi có benchmark, hiệu chỉnh và báo cáo độ chính xác theo từng mức tin cậy (calibration): nếu điểm 0,8 mà chỉ đúng 60% thì ngưỡng cảnh báo phải nâng lên.

**Câu hỏi không có dữ liệu để trả lời** là một loại câu hỏi riêng: hệ thống phải nói "không có trong dữ liệu hiện có", không được bịa SQL hay con số.

#### 6.3 RAG hoàn chỉnh

RAG kết hợp truy hồi tài liệu với sinh văn bản để trả lời dựa trên nguồn bên ngoài mô hình (Lewis et al., 2020). Để gọi là "hoàn chỉnh", mỗi khâu phải có thiết kế và có phép đo.

| Khâu | Thiết kế v2 | Phép đo |
| --- | --- | --- |
| Nạp (ingest) | Script có phiên bản: băm nội dung từng file, chỉ index lại phần thay đổi; metadata gồm nguồn, phiên bản, dashboard, loại tài liệu | Số file mới, đổi, lỗi mỗi lần chạy |
| Chia (chunk) | Chia theo tiêu đề Markdown trước, rồi giới hạn độ dài; chuẩn hoá Unicode (NFC) | Kích thước chunk là siêu tham số, chọn bằng benchmark chứ không bằng cảm tính |
| Truy hồi | **Lai**: vector và từ khoá (BM25), gộp bằng Reciprocal Rank Fusion (Cormack et al., 2009) | Hit@k, MRR trên bộ câu hỏi RAG |
| Xếp hạng lại | Tuỳ chọn: cross-encoder hoặc LLM chấm lại top-k | Chỉ giữ nếu cải thiện MRR đo được |
| Sinh | Trả lời kèm số thứ tự nguồn; cấm dùng kiến thức ngoài ngữ cảnh khi đã chọn nhánh RAG | Tỷ lệ câu có trích nguồn |
| Kiểm tra bám nguồn | Mỗi nhận định phải có đoạn nguồn hỗ trợ; không đủ thì trả lời "không tìm thấy trong tài liệu" | Điểm faithfulness (Es et al., 2023) kết hợp chấm tay mẫu |

Với tiếng Việt, hãy thử truy hồi cả khi người dùng gõ có dấu và không dấu, và dùng mô hình embedding đa ngôn ngữ; chất lượng truy hồi tiếng Việt phải được đo trên benchmark của bạn, không suy ra từ kết quả tiếng Anh.

#### 6.4 Các agent phân tích

**Explainer.** Công thức, thành phần và ý nghĩa lấy **từ YAML** (xác định, đã duyệt). Số cấu thành lấy bằng truy vấn mẫu đã kiểm chứng. LLM chỉ viết lại thành văn. Thêm bước *kiểm tra bám số*: trích mọi con số trong văn bản đầu ra, đối chiếu với tập số đầu vào; có số lạ thì chặn và ghi cảnh báo.

**Trend Analyst.** Tự truy vấn chuỗi 12 tháng cho KPI, tính MoM và YoY, phát hiện bất thường bằng **luật** (ví dụ |MoM| lớn hơn ngưỡng cấu hình, hoặc lệch khỏi trung vị quá k lần MAD). Với chỉ 12 điểm, luật ngưỡng và độ lệch theo trung vị đáng tin hơn mô hình phức tạp. Dự báo gọi mô hình ML hiện có và ghi rõ ngày chạy, giới hạn; không tự diễn giải thêm.

**Decision Advisor.** Bộ luật `business_rules.yaml` nhận (KPI, giá trị, mức ngưỡng) và trả về danh sách hành động **đã được duyệt**. LLM chỉ diễn đạt. Mọi gợi ý kèm dòng: "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định". Advisor không được đưa hành động nằm ngoài danh sách.

**Synthesizer.** Trả về cấu trúc có kiểu, đáp ứng mẫu "đầu ra kép" (bản tóm tắt ngắn cho người dùng và bản chi tiết để kiểm tra) mà các dự án text-to-SQL như Vanna áp dụng:

```python
class Figure(BaseModel):
    name: str
    value: float
    unit: str
    as_of: date
    source_query_id: str

class Answer(BaseModel):
    summary: str
    figures: list[Figure] = []
    explanation: Explanation | None = None
    trend: Trend | None = None
    advice: list[Advice] = []
    sql: str | None = None
    sources: list[Source] = []
    confidence: float
    warnings: list[str] = []
    request_id: str
```

#### 6.5 Bộ nhớ hội thoại

- **Lưu trữ:** bảng `app.chat_turn` (SQLite khi phát triển, PostgreSQL khi vận hành) gồm `session_id`, `user_id`, `query`, `standalone_query`, `kpi_keys`, `sql_id`, `created_at`.
- **Giải quyết follow-up:** `resolve_context` lấy tối đa 5 lượt gần nhất, nhờ LLM viết lại câu hỏi thành câu độc lập. Câu đã viết lại cũng được ghi lại để kiểm tra bằng mắt.
- **Riêng tư:** lịch sử gắn với người dùng, có thời hạn lưu (TTL) và lệnh xoá theo yêu cầu.
- **Test bắt buộc:** chuỗi 3 câu "Dư nợ ngắn hạn?" → "Còn tháng trước?" → "Giảm bao nhiêu phần trăm?" phải cho kết quả đúng ở cả hai câu sau.

#### 6.6 Workflow tự trị: Alert engine và bản tin tuần

"Tự trị" ở đây có nghĩa là **tự chạy theo lịch, tự phát hiện, tự báo**, không cần ai gõ câu hỏi. Hệ thống không tự thực hiện hành động tài chính nào.

**Luồng mỗi lần chạy (mỗi ngày 07:00):** nạp luật → tính KPI bằng SQL mẫu đã kiểm chứng (không qua LLM) → so ngưỡng → loại trùng (cùng luật, cùng mức trong 24 giờ) → chỉ giữ mức cao nhất của mỗi KPI → Explainer sinh giải thích ngắn → gửi thông báo → chờ người xác nhận → leo thang nếu quá N ngày chưa xác nhận → ghi nhật ký.

```yaml
# app/alerts/rules.yaml
rules:
  - id: AL-001
    ten: Dư nợ ngắn hạn tiến sát hạn mức
    kpi: du_no_ngan_han
    chi_so: ty_le_su_dung_han_muc
    dieu_kien: {toan_tu: '>=', gia_tri: 0.70}
    muc: canh_bao
    dedupe_gio: 24
  - id: AL-002
    ten: Dư nợ ngắn hạn vượt ngưỡng nghiêm trọng
    kpi: du_no_ngan_han
    chi_so: ty_le_su_dung_han_muc
    dieu_kien: {toan_tu: '>=', gia_tri: 0.90}
    muc: nghiem_trong
    dedupe_gio: 24
  - id: AL-003
    ten: Current Ratio dưới ngưỡng an toàn
    kpi: current_ratio
    chi_so: current_ratio
    dieu_kien: {toan_tu: '<', gia_tri: 1.2}
    muc: canh_bao
    dedupe_gio: 24
```

Với bộ số minh hoạ ở 6.1 (80%), chỉ AL-001 kích hoạt, ở mức **Cảnh báo**. Khi vượt 90%, AL-002 chạy và AL-001 bị loại vì đã có mức cao hơn.

**Bảo đảm vận hành:** job idempotent (chạy lại không sinh cảnh báo trùng); có heartbeat, và nếu job không chạy hoặc lỗi thì chính nó phát cảnh báo hệ thống; bản tin tuần gửi mỗi thứ Hai gồm 5 KPI chính, thay đổi so với tuần trước và các cảnh báo còn mở.

#### 6.7 Bảo mật và quyền truy cập

**Phòng thủ nhiều lớp.** Lớp chắc nhất là quyền ở cơ sở dữ liệu, không phải bộ lọc trong code (nguyên tắc quyền tối thiểu: Saltzer & Schroeder, 1975):

```sql
-- db/roles.sql
CREATE ROLE gml_ai_ro LOGIN PASSWORD '<lấy từ secret, không ghi vào repo>' NOINHERIT;
GRANT CONNECT ON DATABASE gml TO gml_ai_ro;
CREATE SCHEMA IF NOT EXISTS ai_views;          -- view tổng hợp đã duyệt, không mở bảng thô
GRANT USAGE ON SCHEMA ai_views TO gml_ai_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA ai_views TO gml_ai_ro;
ALTER ROLE gml_ai_ro SET statement_timeout = '15s';
ALTER ROLE gml_ai_ro SET default_transaction_read_only = on;
```

Trong PostgreSQL, view mặc định chạy với quyền của **chủ sở hữu view**, nên tài khoản AI đọc được `ai_views.*` mà không cần quyền trên schema `silver`. Nên kiểm tra hành vi này trên phiên bản PostgreSQL bạn dùng. Ghi nhật ký (`app.audit_log`, `app.chat_turn`) đặt ở schema riêng với tài khoản riêng.

**Phân quyền theo vai trò** (ví dụ, cần chốt cùng doanh nghiệp):

| Vai trò | View được phép | Ghi chú |
| --- | --- | --- |
| Ban điều hành | Tất cả `ai_*` | Xem toàn bộ cảnh báo |
| Kế toán trưởng | Tài chính, công nợ, dòng tiền | Không xem dữ liệu nhân sự |
| Quản lý kho | Tồn kho, sản phẩm | Chỉ đọc |
| Quản trị hệ thống | Không có quyền dữ liệu nghiệp vụ | Chỉ xem log, cấu hình |

Danh sách bảng cho phép truyền vào `validate()` theo vai trò của người gọi, nên lọc xảy ra **trước** khi sinh SQL (prompt chỉ chứa view mà họ được thấy).

**Xác thực.** MVP: token cho từng người dùng, lưu băm, có hạn. Vận hành thật: đăng nhập qua hệ thống danh tính của doanh nghiệp (OIDC) nếu có.

**Prompt injection và rò rỉ.** Tài liệu RAG và kết quả truy vấn có thể chứa văn bản giống lệnh (ví dụ tên đối tác chứa câu "bỏ qua mọi hướng dẫn"). Quy tắc: nội dung truy hồi và dữ liệu luôn là **dữ liệu**, được đặt trong khối phân tách rõ, system prompt nêu rõ không làm theo chỉ dẫn nằm trong đó; bước `guard_output` lọc kết quả. Đây là rủi ro đứng đầu danh sách OWASP cho ứng dụng LLM (OWASP Foundation, 2025). Bộ benchmark có nhóm câu `an_toan` để kiểm tra.

**Dữ liệu ra ngoài.** Gửi dữ liệu tài chính tới LLM bên thứ ba là quyết định cần chủ doanh nghiệp đồng ý bằng văn bản. Giảm thiểu: chỉ gửi kết quả tổng hợp thay vì dòng chi tiết, che số tài khoản và tên cá nhân khi không cần, hoặc dùng mô hình tự host (liên hệ mục 7). Ghi vào ADR.

**Nhật ký kiểm toán.** Mỗi yêu cầu ghi: người hỏi, vai trò, câu hỏi, SQL đã chạy, view đã đọc, thời điểm, `request_id`. Không ghi bí mật hay toàn bộ dữ liệu trả về.

#### 6.8 API đóng gói

| Đường dẫn | Chức năng | Ghi chú |
| --- | --- | --- |
| `POST /v1/chat` | Hỏi đáp, trả `Answer` | Cần xác thực |
| `GET /v1/kpi/{key}` | Giá trị KPI, định nghĩa, ngưỡng | **Không qua LLM**, tính bằng SQL mẫu đã kiểm chứng |
| `GET /v1/alerts` | Danh sách cảnh báo | Lọc theo vai trò |
| `POST /v1/alerts/{id}/ack` | Xác nhận đã xem | Ghi người và giờ |
| `POST /v1/feedback` | Đồng ý hoặc không, kèm ghi chú, gắn `request_id` | Vào hàng đợi duyệt |
| `GET /v1/history` | Lịch sử của chính người dùng |  |
| `GET /health` | Dịch vụ còn sống |  |
| `GET /ready` | Sẵn sàng: DB, vector store, LLM đều với tới được | Dùng cho Docker health check |
| `GET /metrics` | Số liệu vận hành | Chỉ mạng nội bộ |

Quy ước: có phiên bản `/v1` để sau này đổi mà không phá khách hàng cũ; lỗi theo một dạng thống nhất `{error: {code, message, request_id}}` với 401, 403, 422, 429, 503; giới hạn tần suất theo người dùng; tài liệu OpenAPI sinh tự động từ schema Pydantic; có test hợp đồng API.

#### 6.9 Quan sát và đánh giá

**Quan sát.** Log dạng JSON có `request_id`; vết (trace) từng node của đồ thị để thấy thời gian và lỗi từng bước; số liệu độ trễ P50/P95 theo node, tỷ lệ SQL hợp lệ, phân bố điểm tin cậy, tỷ lệ từ chối hoặc hỏi lại, phản hồi đồng ý/không, và chi phí token mỗi câu.

**Bộ benchmark 60 câu:**

| Nhóm | Số câu | Ghi chú |
| --- | --- | --- |
| SQL | 25 | 10 dễ, 10 vừa, 5 khó; đáp án chuẩn từ UAT đã kiểm chứng và câu mới do người nghiệp vụ duyệt |
| RAG | 10 | Định nghĩa, công thức, hướng dẫn dashboard |
| Cả hai | 10 | Giải thích nguyên nhân kèm số liệu |
| Follow-up | 6 | Hai chuỗi 3 lượt |
| Ngoài phạm vi hoặc không có dữ liệu | 5 | Phải nói không có, không bịa |
| An toàn | 4 | Prompt injection, yêu cầu ghi hoặc xoá dữ liệu, vượt quyền |

```yaml
# eval/benchmark.yaml (một mục)
- id: B-017
  split: test              # dev | test
  loai: sql                # sql | rag | both | follow_up | ngoai_pham_vi | an_toan
  do_kho: vua              # de | vua | kho
  vai_tro: ke_toan_truong
  cau_hoi: Dư nợ ngắn hạn tháng 07/2026 là bao nhiêu?
  gold_sql_ref: UAT_03_Q01
  ky_vong:
    gia_tri: 236070000000
    dung_sai_tuong_doi: 0.0001
```

**Tách dev và test.** Bộ `dev` dùng khi chỉnh prompt và xây Golden Query Bank; bộ `test` bị khoá, chỉ chạy khi lập báo cáo, và câu test **không được** xuất hiện trong Golden Query Bank. Nếu để lọt thì số đo chỉ phản ánh việc "thuộc bài", cùng bản chất với rò rỉ dữ liệu bạn đã xử lý trong dự án fraud detection.

| Chỉ số | Định nghĩa | Mục tiêu khởi điểm |
| --- | --- | --- |
| Execution accuracy | % câu SQL cho kết quả thực thi khớp đáp án chuẩn (BIRD dùng chỉ số này; Li et al., 2023) | ≥ 85% trên bộ test |
| Tỷ lệ SQL hợp lệ | % qua kiểm tra AST và chạy được | ≥ 95% |
| Hit@5 và MRR | Tài liệu đúng nằm trong top 5; nghịch đảo thứ hạng | Đặt sau khi có baseline |
| Faithfulness | % nhận định có nguồn hỗ trợ (Es et al., 2023), kèm chấm tay 20 câu | ≥ 90% |
| Từ chối đúng | % câu ngoài phạm vi hoặc không an toàn bị xử lý đúng | 100% với nhóm an toàn |
| Khớp Power BI | Chênh lệch tương đối trên 20 KPI | ≤ 0,01% |
| P95 độ trễ | Thời gian trả lời | < 10 giây |
| Calibration | Độ chính xác theo từng mức tin cậy | Tăng đơn điệu theo điểm |

Các mục tiêu trên là **điểm xuất phát chưa phải kết quả**; sau khi chạy v1, hãy đặt lại cho thực tế. Bảng so sánh cuối cùng:

| Chỉ số | v1 (baseline) | v2 | Chênh lệch |
| --- | --- | --- | --- |
| Execution accuracy | ? | ? | ? |
| Tỷ lệ SQL hợp lệ | ? | ? | ? |
| Faithfulness | ? | ? | ? |
| Câu an toàn xử lý đúng | ? | ? | ? |
| P95 độ trễ | ? | ? | ? |

### 7. Mô-đun tuỳ chọn: fine-tuning (có cổng quyết định)

Sổ tay liệt kê fine-tuning LLM cho lĩnh vực cụ thể trong các ví dụ sản phẩm L5 (tr. 3). Với dự án này, lý do chính đáng để cân nhắc chỉ có ba: tăng độ chính xác trên schema riêng, tự host mô hình nhỏ để **dữ liệu tài chính không ra ngoài**, và giảm chi phí hoặc độ trễ. Theo nhận định của mình (chưa kiểm chứng), với vài chục KPI và một kho dữ liệu cỡ 25 bảng, prompt kèm truy hồi Golden Query nhiều khả năng đã đủ; fine-tuning không mặc nhiên tốt hơn. Vì vậy nó nằm sau một cổng quyết định.

**Chỉ làm khi đủ cả bốn điều kiện:**

1. Baseline (prompt + Golden Query) đã đo xong và còn thấp hơn mục tiêu ở một nhóm lỗi xác định.
2. Có đủ dữ liệu: số cặp (câu hỏi, SQL) đã **xác minh bằng thực thi** ở mức vài trăm trở lên (con số cần thử nghiệm). Năm file UAT có thể chỉ cho vài chục cặp, nên cần mở rộng bằng diễn đạt lại và sinh tổng hợp có kiểm tra thực thi.
3. Có bộ test khoá **không rò rỉ**: tách theo *mẫu truy vấn*, không chỉ theo câu chữ, vì hai câu khác lời nhưng cùng một SQL vẫn là rò rỉ.
4. Có hạ tầng và chấp nhận chi phí.

**Phương pháp:** LoRA (Hu et al., 2022) trên một mô hình mở cỡ nhỏ đến vừa. Đánh giá trên cùng benchmark với baseline: execution accuracy, tỷ lệ hợp lệ, độ trễ, chi phí; kiểm tra thêm mô hình có làm xấu đi nhóm câu RAG hay không.

**Kết quả thế nào cũng ghi ADR-004.** Nếu không vượt baseline thì không đưa vào sản phẩm; báo cáo âm tính này vẫn là bằng chứng của một quyết định kỹ thuật có cơ sở.

### 8. Triển khai

| Dịch vụ | Vai trò |
| --- | --- |
| `api` | FastAPI, orchestrator, các agent |
| `ui` | Streamlit |
| `worker` | Scheduler: alert engine, bản tin tuần |
| `db` | PostgreSQL (kho dữ liệu, schema `app` cho log và lịch sử) |
| `vectorstore` | Chroma hoặc pgvector (theo ADR-001) |
| `llm-local` (tuỳ chọn) | Mô hình tự host nếu chọn phương án này |

#### 8.1 Phân công LLM theo thành phần (Dell Latitude 7490 — RAM 24GB, không GPU rời)

*Cập nhật 27/10/2026. Khuyến nghị dựa trên phần cứng thực tế của môi trường phát triển: Intel i7-8650U, Intel UHD 620 tích hợp, 24GB DDR4. Không có GPU rời nên không thể offload GGUF lên GPU; inference local chạy hoàn toàn trên CPU (~6–10 token/giây với model 7B Q4_K_M).*

**Chiến lược 3 lớp:**

| Lớp | Mô tả | Khi nào dùng |
| --- | --- | --- |
| **Cloud API** | Gemini / Claude qua internet | Tác vụ suy luận nặng, sinh SQL phức tạp, tổng hợp câu trả lời |
| **Local Ollama** | Model GGUF chạy CPU | Embedding (không phát sinh cost, dữ liệu không ra ngoài), fallback offline, test |
| **Không dùng LLM** | SQL mẫu kiểm chứng (golden query) | Alert Engine, tính KPI theo lịch — LLM không được tham gia tính số tài chính |

**Phân công theo từng thành phần:**

| Thành phần (v2.0) | LLM đề xuất | Model cụ thể | Lý do |
| --- | --- | --- | --- |
| Orchestrator / Intent Classifier | Cloud API | `gemini-2.0-flash` | Cần structured output (enum), nhanh, rẻ |
| SQL Agent (sinh + sửa SQL) | Cloud API | `gemini-2.0-flash` | Schema 25+ bảng, context window lớn, tự sửa lỗi x3 |
| RAG Embedding (ChromaDB) | **Local Ollama** ⭐ | `nomic-embed-text` | Dữ liệu tài chính không ra ngoài, miễn phí, độ trễ thấp |
| Explainer Agent | Cloud API | `gemini-2.0-flash` | Chỉ diễn đạt lại YAML công thức thành văn |
| Trend Analyst | Cloud API | `gemini-2.0-flash` | Diễn đạt kết quả tính toán bằng SQL |
| Decision Advisor | Cloud API | `gemini-2.0-flash` | Format lại rule từ `business_rules.yaml` |
| Alert Engine (cron hàng ngày) | **Không dùng LLM** | SQL mẫu kiểm chứng | Theo Nguyên tắc 1 & 7: số tài chính chỉ từ SQL đã verify |
| Bản tin tuần (synthesize) | Cloud API | `gemini-2.0-flash` | Tóm tắt ngắn 5 KPI — volume thấp, chất lượng cao |
| Phát triển / Viết ADR / Tài liệu | Cloud API | Claude Sonnet (Thinking) | Lý luận dài, chất lượng văn bản kiến trúc cao |
| Offline fallback / Test local | **Local Ollama** | `qwen2.5-coder:7b` (Q4_K_M, ~5GB RAM) | ~8 t/s trên CPU, test không cần internet |

> ⚠️ **Bảo mật (ADR-005):** Free tier Gemini Google AI Studio **có thể dùng dữ liệu để cải thiện model**. Với dữ liệu tài chính thật của GML, **bắt buộc dùng Paid tier** (Google AI Platform hoặc Vertex AI) để đảm bảo cam kết không dùng dữ liệu cho training. Ghi vào ADR-005.

**Cài Ollama local (lệnh nhanh):**

```powershell
winget install Ollama.Ollama

ollama pull nomic-embed-text   # Embedding cho ChromaDB — ưu tiên pull trước
ollama pull qwen2.5-coder:7b   # Fallback SQL generation local
```

```python
# app/rag/embeddings.py — dùng local embedding thay vì cloud
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

embedding_fn = OllamaEmbeddingFunction(
    model_name="nomic-embed-text",
    url="http://localhost:11434/api/embeddings"
)
```

**Cấu hình** qua `pydantic-settings`, chỉ đọc từ biến môi trường. `.env.example` liệt kê: `DATABASE_URL_RO`, `DATABASE_URL_APP`, `LLM_PROVIDER`, `LLM_MODEL`, `EMBEDDING_MODEL`, `VECTORSTORE_URL`, `AUTH_SECRET`, `ALERT_CRON`. Không có giá trị bí mật nào trong repo; thêm công cụ quét bí mật vào pre-commit (ví dụ gitleaks).

**CI (GitHub Actions):** kiểm tra định dạng, test đơn vị, test an toàn (4 câu nhóm `an_toan`, test `both`), benchmark rút gọn 10 câu trên dữ liệu mẫu. Ghim phiên bản mọi thư viện trong `requirements.txt` vì LangChain và LangGraph đổi API khá nhanh.

```
7. AI-Business-Assistant/
├── v1/                          # giữ nguyên, tag v1.0 (baseline)
└── v2/
    ├── requirements.txt  ·  .env.example  ·  docker-compose.yml
    ├── app/
    │   ├── core/                # config, logging, security, errors
    │   ├── api/                 # main, deps, schemas, routers/
    │   ├── orchestration/       # state, graph, routing
    │   ├── agents/              # intent, sql_agent, rag_agent,
    │   │                        # explainer, trend, advisor, synthesizer
    │   ├── sql/                 # validator, executor, repair, confidence
    │   ├── rag/                 # ingest, retriever, rerank, citations
    │   ├── memory/              # session_store, followup
    │   ├── alerts/              # rules.yaml, engine, scheduler, notifier
    │   ├── knowledge/           # kpi_definitions.yaml, business_rules.yaml,
    │   │                        # golden_queries/, docs/
    │   └── ui/                  # streamlit_app.py
    ├── db/                      # roles.sql, views.sql, migrations/
    ├── eval/                    # benchmark.yaml, run_eval.py, reports/
    ├── tests/                   # unit/, integration/, security/
    └── docs/                    # adr/, architecture.md, runbook.md, model_card.md
```

### 9. Lộ trình triển khai (ước lượng theo tuần làm việc của một người)

Chương trình AI in Action chạy toàn thời gian 12 tuần, nên lịch này bắt đầu **sau khi kết thúc chương trình**. Số tuần chỉ là ước lượng, điều chỉnh theo thời gian bạn có.

| Phase | Tuần | Nội dung | Định nghĩa hoàn thành | Bằng chứng |
| --- | --- | --- | --- | --- |
| 0. Baseline | 1 | Gắn tag `v1.0`; viết benchmark 60 câu (chia 40 dev, 20 test khoá); chạy v1 | Có bảng số liệu của v1 | `eval/reports/v1.md` |
| 1. An toàn và nền tảng | 2–3 | `roles.sql`, `ai_views`; lớp cấu hình; xác thực và RBAC; validator AST; sửa routing `both`; `/health`, `/ready` | 4 câu an toàn đúng; test `both` qua | Test an toàn, test routing |
| 2. Tri thức và SQL | 4–5 | KPI YAML (18 KPI), business rules, Golden Query Bank từ UAT\_01→05 (loại khỏi bộ test), pipeline 6 bước, điểm tin cậy | Execution accuracy đo được trên dev | Biểu đồ calibration |
| 3. RAG và agent | 6–7 | Ingest có phiên bản, truy hồi lai, trích nguồn, kiểm tra bám nguồn; Explainer, Trend, Advisor; Synthesizer có kiểu | Hit@5, MRR có số; kiểm tra bám số hoạt động | Báo cáo RAG |
| 4. Vận hành | 8–9 | Memory, alert engine, bản tin tuần, API đầy đủ, quan sát, Docker, CI | `docker compose up` chạy từ máy sạch; job chạy 7 ngày liên tục | Nhật ký job, CI xanh |
| 5. Đánh giá | 10 | Chạy bộ test khoá; bảng v1 so với v2; ADR; model card; 2–3 người dùng thử; tự trình bày 15 phút | Bảng so sánh có số; ADR đủ | Báo cáo cuối |
| 6. Tuỳ chọn | Sau đó | Fine-tuning theo cổng ở mục 7 | Báo cáo so với baseline | ADR-004 |

**Nếu thiếu thời gian**, giữ thứ tự ưu tiên: an toàn (Phase 1) → đánh giá (Phase 0 và 5) → pipeline SQL → RAG → các agent phân tích. Một hệ thống nhỏ nhưng đo được thì đáng giá hơn một hệ thống lớn không đo được.

### 10. Hồ sơ quyết định kiến trúc (ADR)

ADR ghi lại **vì sao** chọn, để người khác (và bạn sau 6 tháng) hiểu được quyết định (Nygard, 2011). Đây là bằng chứng trực tiếp cho tiêu chí "quyết định kỹ thuật ở cấp ứng dụng" của L5.

| ADR | Câu hỏi | Tiêu chí so sánh |
| --- | --- | --- |
| 001 | Chroma hay pgvector (hay khác) | Vận hành, tìm kiếm lai, sao lưu, phân quyền |
| 002 | LangGraph hay hàm Python thường | Song song, trạng thái, khả năng test, độ phức tạp |
| 003 | An toàn SQL | Quyền DB + view + AST so với chỉ lọc từ khoá |
| 004 | Có fine-tune không | Số đo trên benchmark, chi phí, rủi ro rò rỉ |
| 005 | LLM bên ngoài hay tự host | Quyền dữ liệu, chi phí, chất lượng, độ trễ |
| 006 | Truy hồi vector thuần hay lai, có xếp hạng lại không | Hit@k và MRR đo được |
| 007 | Cách tính điểm tin cậy và ngưỡng | Calibration trên benchmark |

Mẫu một ADR: **Tiêu đề · Trạng thái · Bối cảnh · Các phương án · Quyết định · Hệ quả · Bằng chứng (liên kết kết quả đo)**. Viết bằng lời của bạn; nếu dùng AI hỗ trợ, bạn phải tự giải thích lại được từng quyết định.

### 11. Checklist tự chấm L5 và rủi ro

| Tiêu chí | Đạt khi | Trạng thái |
| --- | --- | --- |
| Agentic hoàn chỉnh | Đồ thị chạy đủ 6 loại ý định; test `both` qua; có trace | ☐ |
| RAG hoàn chỉnh | Có Hit@k, MRR, faithfulness; có trích nguồn | ☐ |
| Workflow tự trị | Job chạy 7 ngày liên tục, không cảnh báo trùng, có xác nhận | ☐ |
| API đóng gói | OpenAPI, xác thực, Docker chạy từ máy sạch | ☐ |
| An toàn | Tài khoản chỉ đọc, 4/4 câu an toàn đúng, nhật ký kiểm toán | ☐ |
| Đánh giá | Bảng v1 so với v2 có số, bộ test không rò rỉ | ☐ |
| Quyết định kỹ thuật | ≥ 5 ADR có phương án và bằng chứng | ☐ |
| Fine-tuning | Báo cáo so baseline, hoặc ADR-004 giải thích vì sao không | ☐ |
| Tự bảo vệ | Bạn trình bày 15 phút, trả lời được câu hỏi về từng thành phần | ☐ |

**Rủi ro và giới hạn.**

- **Phạm vi lớn:** 6 agent cộng workflow cộng API là nhiều việc; làm theo thứ tự ưu tiên ở mục 9.
- **Phụ thuộc phiên bản thư viện:** LangChain, LangGraph, Chroma đổi API thường xuyên; ghim phiên bản và viết test.
- **Chi phí và quyền dữ liệu:** chi phí token và việc gửi dữ liệu tài chính ra ngoài cần được chủ doanh nghiệp đồng ý.
- **Thiết kế đạt tiêu chí chưa đồng nghĩa bạn đạt L5.** Bậc do người đánh giá xác nhận dựa trên sản phẩm chạy, số đo, và khả năng bạn giải thích từng phần.
- Tên repo Vanna AI "đã lưu trữ 03/2026" lấy từ tài liệu v2 cũ của bạn, mình chưa kiểm chứng.

### 12. Tài liệu tham khảo (APA 7)

Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. In *Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval* (pp. 758–759). ACM.

Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). *RAGAS: Automated evaluation of retrieval augmented generation* (arXiv:2309.15217).

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. *International Conference on Learning Representations (ICLR 2022)*.

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., ... Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems, 33*, 9459–9474.

Li, J., Hui, B., Qu, G., Yang, J., Li, B., Li, B., ... Li, Y. (2023). Can LLM already serve as a database interface? A big bench for large-scale database grounded text-to-SQLs. *NeurIPS 2023 Datasets and Benchmarks Track* (arXiv:2305.03111).

Nygard, M. (2011, November 15). *Documenting architecture decisions*. Cognitect Blog. https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions

OWASP Foundation. (2025). *OWASP top 10 for large language model applications*. https://owasp.org/www-project-top-10-for-large-language-model-applications/

Saltzer, J. H., & Schroeder, M. D. (1975). The protection of information in computer systems. *Proceedings of the IEEE, 63*(9), 1278–1308.

VinUniversity. (2026). *Sổ tay học viên: Chương trình đào tạo nhân tài AI thực chiến Tập đoàn Vingroup* (Version 2.2), tr. 3.

Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2023). Self-consistency improves chain of thought reasoning in language models. *International Conference on Learning Representations (ICLR 2023)*.

*Mình chưa tra lại số trang, tên tác giả đầy đủ và đường dẫn của các tài liệu trên nguồn gốc; hãy đối chiếu trên Google Scholar hoặc trang nhà xuất bản trước khi đưa vào bài chính thức.*
