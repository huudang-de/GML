# Kế hoạch Phát triển AI Business Assistant — Gỗ Minh Long
> **Phiên bản:** 2.0 — Từ Query-Result Engine → Intelligence Decision Layer
> **Cập nhật:** 09/10/2026

---

## 1. Chẩn đoán hiện trạng (As-Is)

### Kiến trúc hiện tại:
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

### Điểm mạnh đã có:
- ✅ LangGraph orchestration bài bản, có intent routing
- ✅ SQL self-healing: thất bại → tự sửa → retry 3 lần
- ✅ RAG từ guide_dashboard*.md (5 dashboard business guides)
- ✅ ChromaDB vector store đã build sẵn
- ✅ PostgreSQL silver schema đầy đủ (25+ tables)

### Điểm yếu — Vì sao cần nâng cấp:

| Vấn đề | Biểu hiện | Tác động |
|---|---|---|
| **"Meaning Gap"** | Trả về số, không giải thích ý nghĩa | BQL không biết hành động tiếp theo |
| **Không có Semantic Layer** | LLM đoán tên cột, dễ sai | Sai số liệu, mất tin tưởng |
| **RAG thụ động** | Chỉ retrieval, không tích hợp sâu với SQL result | Câu trả lời rời rạc |
| **Không có memory** | Mỗi câu hỏi là phiên mới | Không thể hỏi follow-up |
| **Không có Insight Agent** | Không phân tích trend, không cảnh báo | Giá trị thấp với BQL |

---

## 2. Học hỏi từ các dự án tham khảo

### 2.1 Vanna AI (github.com/vanna-ai/vanna) — *Archived 03/2026*
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

### 2.2 Dataherald (github.com/Dataherald/dataherald)
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

### 2.3 LangGraph Multi-Agent Pattern
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

## 3. Kiến trúc đề xuất — GML AI Assistant v2.0

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

## 4. Lộ trình triển khai — 4 Giai đoạn (8 tuần)

---

### Giai đoạn 1 — Nền tảng & Ổn định (Tuần 1–2)
> **Mục tiêu:** Làm hệ thống hiện tại đáng tin cậy, sẵn sàng mở rộng

#### 1.1 Semantic Schema Layer (DataDictionary)
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

#### 1.2 Golden Query Bank
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

#### 1.3 Session Memory
```python
# app/memory/session_store.py
class SessionMemory:
    def get_history(self, session_id) -> list[dict]
    def add_turn(self, session_id, query, answer, sql, kpi_keys)
    def get_context_summary(self, session_id) -> str  # Tóm tắt 5 turns gần nhất cho LLM
```

---

### Giai đoạn 2 — Intelligence Layer: Explain + Analyze (Tuần 3–4)
> **Mục tiêu:** Câu trả lời đủ Công thức + Ý nghĩa + Xu hướng

#### 2.1 ExplainerAgent (Agent quan trọng nhất)

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

#### 2.2 TrendAnalystAgent

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

#### 2.3 Synthesizer v2.0 — Structured Response

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

### Giai đoạn 3 — Decision Support Layer (Tuần 5–6)
> **Mục tiêu:** Chủ động đề xuất hành động, cảnh báo ngưỡng

#### 3.1 DecisionAdvisorAgent

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

#### 3.2 Alert & Monitoring Engine
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

#### 3.3 Power BI Quick Ask Integration
Power BI gửi URL param `?dashboard=tai_chinh&kpi=du_no_ngan_han`
→ Streamlit pre-load context đúng dashboard đang xem → UX mượt mà

---

### Giai đoạn 4 — UX & Production Hardening (Tuần 7–8)
> **Mục tiêu:** Ổn định, dễ dùng, sẵn sàng BQL dùng thường ngày

#### 4.1 Streamlit UI v2.0 Layout
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

#### 4.2 Feedback Loop
```python
# 👍 → Lưu (query, sql, answer) vào Golden Query Bank → tăng accuracy
# 👎 → Ghi log review queue → DA review → sửa → re-add
```

#### 4.3 Guard Rails & Security
```python
class SQLGuardRail:
    BLOCKED = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]
    # 1. Block destructive operations
    # 2. Enforce LIMIT clause
    # 3. Whitelist schema silver.*
    # 4. Log all queries for audit trail
```

---

## 5. File Structure đề xuất

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

## 6. Bảng ưu tiên triển khai

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

## 7. Before vs After — Kỳ vọng chất lượng câu trả lời

### BEFORE (v1.0 hiện tại):
> **User:** Dư nợ ngắn hạn bao nhiêu?
>
> **AI:** Dư nợ ngắn hạn hiện tại là **236,065,233,815 VNĐ**.

### AFTER (v2.0 target):
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

## 8. Tham khảo & Trích dẫn

| Nguồn | Học được | Link |
|---|---|---|
| **Vanna AI** | RAG-first SQL, Golden Query Bank, Tool Memory, Dual Output | [vanna.ai](https://vanna.ai) — github archived 03/2026 |
| **Dataherald** | Agentic Tool Use, Confidence Scoring, Context Engineering | [github.com/Dataherald/dataherald](https://github.com/Dataherald/dataherald) |
| **LangGraph** | Multi-agent orchestration, State management, Conditional routing | [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |
| **Insight Pattern** | Data Layer → Insight Layer tách biệt | [studioriente.com](https://studioriente.com) |
| **BIRD Benchmark** | VES metric cho SQL quality evaluation | [arxiv.org/abs/2305.03111](https://arxiv.org/abs/2305.03111) |
