# 🎓 CẨM NANG BẢO VỆ KHÓA LUẬN: KIẾN TRÚC TỔNG THỂ (PLAN V2)
**Đề tài:** *Hệ thống Trợ lý Trí tuệ Doanh nghiệp Đa Tác tử (Multi-Agent AI Business Assistant) phục vụ Quản trị Tài chính & Hỗ trợ Ra quyết định — Doanh nghiệp Gỗ Minh Long (GML)*

---

## PHẦN 1. GIỚI THIỆU KIẾN TRÚC TỔNG THỂ (OVERVIEW ARCHITECTURE)

### 1.1. Sơ đồ kiến trúc phân tầng (8 Tầng — Layered Architecture)

Hệ thống được thiết kế theo kiến trúc phân tầng hướng dịch vụ kết hợp đồ thị trạng thái điều phối đa tác tử (Orchestrated Multi-Agent State Machine):

```
┌────────────────────────────────────────────────────────────────────────┐
│ [T6] CLIENT LAYER: Streamlit UI (Chat, Alert Center, Audit Logs)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS + Bearer Token (JWT)
┌───────────────────────────────────▼────────────────────────────────────┐
│ [T5] API GATEWAY (FastAPI /v1): Auth, RBAC, Rate-Limit, Audit Log      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Pydantic Typed State
┌───────────────────────────────────▼────────────────────────────────────┐
│ [T4] ORCHESTRATION LAYER (LangGraph StateGraph):                       │
│      Input Guard ➔ Resolve Context ➔ Classify Intent ➔ Branching       │
│      ➔ Join ➔ Explain ∥ Trend ➔ Advise ➔ Confidence Gate ➔ Output Guard│
└───────┬──────────────┬──────────────┬───────────────┬──────────────────┘
        ▼              ▼              ▼               ▼
 ┌─────────────┐┌─────────────┐┌─────────────┐┌───────────────┐
 │  SQL Agent  ││  RAG Agent  ││  Explainer  ││ Trend Analyst │
 │  (6 bước)   ││   (Hybrid)  ││  (YAML+LLM) ││  (Luật + ML)  │
 └──────┬──────┘└──────┬──────┘└──────┬──────┘└───────┬───────┘
        │              │              │               │
        └──────────────┴───────┬──────┴───────────────┘
                               ▼
 ┌────────────────────────────────────────────────────────────┐
 │ [T3] DECISION ADVISOR & SYNTHESIZER (Structured Dual Output│
 └─────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────┴─────────────────────────────────────────┐
│ [T2] KNOWLEDGE LAYER:                                                  │
│      - kpi_definitions.yaml (18 KPI) | business_rules.yaml (Ngưỡng BRD)│
│      - Golden Query Bank (SQL mẫu UAT) | Vector Store (ChromaDB)       │
├────────────────────────────────────────────────────────────────────────┤
│ [T1] DATA LAYER:                                                       │
│      - PostgreSQL (Schema `silver` + view `ai_views.*`)                │
│      - Account `gml_ai_ro` (Read-only, Statement Timeout 15s)          │
├────────────────────────────────────────────────────────────────────────┤
│ [T7] AUTONOMOUS WORKER: Alert Engine (07:00 AM) & Weekly Brief Scheduler│
├────────────────────────────────────────────────────────────────────────┤
│ [T8] OBSERVABILITY: JSON Logging, Trace, Metrics, Benchmark (60 Test Qs)│
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2. Luồng xử lý dữ liệu qua 1 câu hỏi thực tế (End-to-End Trace)
**Ví dụ Ban Lãnh đạo hỏi:** *"Dư nợ ngắn hạn hiện tại là bao nhiêu, có sát hạn mức không và cần làm gì?"*

1. **Client & Gateway (T6, T5):** Đính kèm token định danh Giám đốc điều hành (`role: ceo`), gắn `request_id`, ghi nhận vào nhật ký kiểm toán (`app.audit_log`).
2. **Orchestrator (T4):** 
   - `guard_input`: Quét prompt injection hoặc mã độc.
   - `classify_intent`: Phân loại vào nhóm `both` (vừa cần số liệu, vừa cần giải thích/khuyến nghị).
   - Rẽ nhánh song song: Kích hoạt `SQL Agent` và `RAG Agent`.
3. **Thực thi Agent (T3, T2, T1):**
   - **SQL Agent:** Tìm câu tương đồng trong *Golden Query Bank* (UAT_01), sinh câu lệnh SQL truy vấn view `ai_views.ai_v_no_vay`. Đi qua bộ kiểm tra cú pháp AST (`validator.py` - chỉ cho phép `SELECT`, bắt buộc `LIMIT`). Thực thi với tài khoản `gml_ai_ro` ➔ Trả về: `236.065.233.815 VNĐ`.
   - **RAG Agent:** Tìm kiếm lai (Vector + BM25) trong Cẩm nang quản trị và BRD ➔ Trích xuất tài liệu về chính sách hạn mức tín dụng 295 tỷ và các tài khoản cấu thành (TK 34111, 34113, 34114).
4. **Phân tích chuyên sâu (Explainer, Trend, Advisor):**
   - **Explainer:** Đọc `kpi_definitions.yaml` để diễn giải bản chất chỉ tiêu.
   - **Trend Analyst:** Tính toán tỷ lệ sử dụng hạn mức = $\frac{\Sigma \text{ principal\_balance}}{\Sigma \text{ granted\_limit}} = \frac{270,86}{295} = 91,8\%$ (chuẩn hóa theo kết quả UAT_01 và Storytelling §3).
   - **Advisor:** So khớp `business_rules.yaml`: Ngưỡng cảnh báo vàng là $\ge 70\%$, nghiêm trọng là $\ge 90\%$. Ở mức $91,8\%$, hệ thống kích hoạt mức **Nghiêm trọng (AL-002)**, Advisor tự động lấy hành động đã duyệt cho mức nghiêm trọng: *"Họp rà soát cơ cấu nợ với Kế toán trưởng; làm việc với ngân hàng về kế hoạch dòng tiền và gia hạn/nâng hạn mức tín dụng"*. LLM chỉ biên tập lại câu chữ, **tuyệt đối không tự bịa hành động**.
5. **Synthesizer & Output Guard:** Đóng gói thành định dạng đầu ra kép (*Dual Output*): Bản tóm tắt điều hành trực quan + Bảng số liệu chi tiết + Câu lệnh SQL đã chạy + Nguồn tài liệu đối soát + Điểm tin cậy (Confidence Score).

### 1.3. Bảng phân bổ Công cụ, Mô hình AI & Thư viện theo 8 Tầng (Tool & Tech Stack Mapping)

| Tầng kiến trúc | Tên công cụ / Thư viện (Tool & Tech) | Phiên bản (Version) | Vai trò & Trách nhiệm cụ thể trong hệ thống |
| :--- | :--- | :--- | :--- |
| **[T6] Client Layer** | **Streamlit** | `^1.34.0` | Giao diện Chatbot tương tác cho người dùng, Alert Center xem cảnh báo tài chính, nút xác nhận và hiển thị kết quả phân tích. |
| | **Power BI** | Desktop / Service | Hệ thống báo cáo hiện hữu của GML, nơi người dùng lấy cảm hứng đặt câu hỏi nhanh (Quick Ask). |
| **[T5] API Gateway** | **FastAPI** | `^0.111.0` | Khung ứng dụng RESTful API hiệu năng cao, cung cấp các endpoint `/v1/chat`, `/v1/kpi`, `/v1/alerts`. |
| | **Uvicorn** | `^0.29.0` | ASGI Web Server siêu nhẹ giúp chạy FastAPI mượt mà với async/await. |
| | **Pydantic (v2)** | `^2.7.0` | Định nghĩa schema dữ liệu chặt chẽ (`BaseModel`), tự động xác thực kiểu dữ liệu đầu vào/đầu ra và sinh tài liệu OpenAPI. |
| | **Pydantic-Settings** | `^2.2.0` | Quản lý biến môi trường tập trung từ file `.env` một cách an toàn và có kiểm soát kiểu. |
| **[T4] Orchestrator** | **LangGraph** | `^0.1.0` | Khung điều phối máy trạng thái đồ thị (`StateGraph`), quản lý rẽ nhánh điều kiện (`conditional_edges`) và chạy song song SQL + RAG. |
| | **LangChain Core** | `^0.2.0` | Quản lý Prompt Template, Output Parser, Chat Model abstractions. |
| **[T3] Agents & LLM** | **Google Gemini API** *(Cloud)* | `gemini-2.0-flash` / `gemini-3.8-flash` | Mô hình ngôn ngữ lớn đám mây xử lý phân loại ý định, sinh câu lệnh SQL và biên tập báo cáo tổng hợp. |
| | **Ollama** *(Local Host)* | `v0.1.x+` | Nền tảng chạy mô hình AI cục bộ trên máy trạm (không cần mạng, bảo mật nội bộ). |
| | **Qwen2.5-Coder:7b** *(Local LLM)* | GGUF (Q4_K_M) | Mô hình cục bộ dùng để kiểm thử offline và fallback dự phòng khi mất kết nối đám mây. |
| | **Nomic-embed-text** *(Local Embedding)* | Model 137M param | Mô hình tạo vector nhúng chạy qua Ollama trên CPU máy trạm để dữ liệu tài chính không bị lộ ra ngoài. |
| | **sqlglot** | `^23.0.0` | Bộ phân tích cây cú pháp trừu tượng (AST Parser) kiểm tra an toàn SQL, chặn lệnh ghi và tự thêm `LIMIT`. |
| **[T2] Knowledge Layer** | **ChromaDB** | `^0.5.0` | Cơ sở dữ liệu Vector Store nhúng lưu trữ các đoạn tài liệu BRD và cẩm nang hướng dẫn Dashboard. |
| | **rank-bm25** | `^0.2.2` | Thư viện tìm kiếm từ khóa tần suất (Sparse Search) phục vụ thuật toán tìm kiếm lai Hybrid Retrieval. |
| | **PyYAML** | `^6.0.1` | Đọc và nạp các tệp tri thức tĩnh đã duyệt: `kpi_definitions.yaml` (18 KPI) và `business_rules.yaml`. |
| **[T1] Data Layer** | **PostgreSQL** | `15+` | Hệ quản trị CSDL Kho dữ liệu (Data Warehouse GML), chứa schema `silver` và các view nghiệp vụ `ai_views.*`. |
| | **SQLAlchemy** | `^2.0.0` | Thư viện ORM / Core kết nối CSDL, quản lý Connection Pool và thực thi truy vấn. |
| | **psycopg2-binary** | `^2.9.0` | Driver kết nối C++ hiệu năng cao giữa Python và PostgreSQL. |
| **[T7] Worker & Schedule** | **APScheduler** | `^3.10.4` | Bộ lập lịch tác vụ nền trong Python, tự động kích hoạt Alert Engine vào 07:00 sáng mỗi ngày và bản tin tuần. |
| **[T8] Observability & Eval**| **pytest & pytest-asyncio** | `^8.0.0` / `^0.23.0` | Khung kiểm thử tự động cho Unit Test, Contract Test và Security Guards. |
| | **httpx** | `^0.27.0` | HTTP client async dùng để kiểm thử hợp đồng API (API Contract Testing). |
| | **RAGAS** | `^0.1.0` | Bộ thư viện đánh giá chất lượng RAG tự động (đo độ bám nguồn Faithfulness, Answer Relevance). |
| | **Docker & Docker Compose** | `24+` | Đóng gói toàn bộ hệ thống (API, DB, UI, VectorStore) chạy đồng nhất trên môi trường sạch với 1 lệnh `docker compose up`. |

### 1.4. Lý do lựa chọn công nghệ và tương thích phần cứng (Dell Latitude 7490)
1. **Phù hợp hạ tầng thực tế (RAM 24GB, CPU Intel Core i7-8650U, không GPU rời):**
   - Các tác vụ tạo vector nhúng (Embedding) chạy cục bộ qua Ollama với model siêu nhẹ `nomic-embed-text` chỉ tiêu tốn ~1GB RAM CPU.
   - Các tác vụ suy luận phức tạp (Text-to-SQL, Synthesizer) được ủy thác cho Cloud API (`Gemini Flash`) có tốc độ cao và chi phí cực thấp ($0.10/triệu token).
   - Khi cần kiểm thử offline, máy trạm có thể chạy mô hình lượng tử hóa `Qwen2.5-Coder:7b` (Q4_K_M ~5GB RAM) với tốc độ khả dụng ~8 tokens/s trên CPU.
2. **Kiến trúc bền vững (Decoupled & Standardized):**
   - Sử dụng các thư viện chuẩn công nghiệp (FastAPI, Pydantic, SQLAlchemy, LangGraph) giúp hệ thống dễ bảo trì, dễ thay thế CSDL hoặc mô hình LLM mà không phá vỡ logic nghiệp vụ.

---

## PHẦN 2. TẠI SAO LẠI CHỌN KIẾN TRÚC NÀY? (WHY CHOOSE?)

Khi Hội đồng hỏi: *"Tại sao phải làm phức tạp như vậy mà không dùng 1 con LLM đọc database hoặc viết hàm Python thông thường?"*, đây là **3 luận điểm thuyết phục nhất**:

### 1. Giải quyết triệt để rủi ro "Ảo giác số liệu" (Hallucination) trong Tài chính
* **Nguyên tắc số 1:** *LLM không bao giờ được tự làm toán hay đoán số tài chính.* Một con số sai trên báo cáo quản trị có thể dẫn tới quyết định sai lầm hàng chục tỷ đồng.
* **Giải pháp kiến trúc:** Tách bạch tuyệt đối **Tầng tính toán (PostgreSQL thực thi)** và **Tầng diễn đạt (LLM biên tập)**. Mọi con số trả về đều phải có mã định danh `source_query_id` hoặc trích nguồn từ tài liệu cụ thể. Nếu không có số, hệ thống trả về `no_data` thay vì để LLM "tự biên tự diễn".

### 2. Khắc phục hạn chế của các phương pháp truyền thống
* **So với Naive Text-to-SQL (chỉ dùng prompt + LLM):** Dễ gãy khi gặp lược đồ CSDL lớn (20+ bảng), không hiểu ngữ cảnh kế toán Việt Nam (tài khoản đối ứng 111, 112, 341), sinh câu lệnh chạy chậm hoặc gây quá tải CSDL. Kiến trúc v2 sử dụng **Lớp ngữ nghĩa (Semantic Layer) + Bộ truy vấn mẫu (Golden Query Bank)** với mục tiêu thiết kế đạt tỷ lệ sinh SQL chính xác $\ge 85\%$ (chuẩn BIRD benchmark).
* **So với Naive RAG (Chatbot tài liệu):** RAG chỉ tìm kiếm được văn bản tĩnh (ISO, PDF), hoàn toàn "mù" trước dữ liệu biến động từng ngày trong kho dữ liệu (Data Warehouse).
* **So với Single-Agent (Một Agent ôm hết):** LangGraph Multi-Agent áp dụng tư duy **"Chia để trị" (Separation of Concerns)**. Mỗi tác tử có một phạm vi nhiệm vụ hẹp (Narrow Scope), giúp giảm độ dài context window, giảm chi phí token và dễ viết Unit Test độc lập cho từng phần.

### 3. Nguyên tắc Bảo mật đa tầng (Defense-in-Depth) & Quyền tối thiểu
* Không đặt niềm tin bảo mật vào System Prompt (vì Prompt Injection có thể phá vỡ).
* Kiến trúc bảo vệ 3 lớp:
  1. *Lớp CSDL:* Tài khoản `gml_ai_ro` chỉ có quyền `SELECT` trên schema `ai_views`, khóa timeout 15 giây.
  2. *Lớp Ứng dụng:* Bộ phân tích cú pháp cây cú pháp trừu tượng (AST Parser bằng `sqlglot`) chặn đứng mọi từ khóa nguy hiểm (`DROP`, `DELETE`, `pg_sleep`).
  3. *Lớp Phân quyền (RBAC):* Lọc danh sách bảng ngay trước khi gửi vào prompt của LLM theo vai trò người dùng (Giám đốc kho không thể hỏi về nợ vay hay lương thưởng).

---

## PHẦN 3. HỌC HỎI VÀ KẾ THỪA TỪ ĐÂU? (WHERE LEARN?)

Kiến trúc v2 không phải là sản phẩm suy đoán cảm tính mà được xây dựng trên nền tảng **nghiên cứu khoa học uy tín (Academic Papers)** kết hợp **kiến trúc công nghiệp tốt nhất (Industry Best Practices)**:

| Nguồn tham khảo | Học hỏi & Kế thừa điều gì cho Dự án GML? | Trích dẫn học thuật / Nguồn gốc |
| :--- | :--- | :--- |
| **BIRD Benchmark** | **Lớp ngữ nghĩa (Semantic Layer):** Chứng minh rằng Text-to-SQL trong thực tế bắt buộc phải có *External Knowledge* (định nghĩa công thức, mối quan hệ nghiệp vụ) thì LLM mới hiểu đúng câu hỏi. Dùng chỉ số *Execution Accuracy*. | Li et al. (NeurIPS 2023) |
| **Vanna AI** | **RAG-first SQL & Golden Query Bank:** Ý tưởng lưu trữ các câu SQL chuẩn từ giai đoạn UAT làm ngân hàng truy vấn mẫu; mô hình *Dual Output* (cho C-level xem tóm tắt, cho Data Analyst xem SQL đối soát). | Vanna.ai Architecture |
| **Dataherald** | **Kiểm soát độ tin cậy (Confidence Scoring):** Đo lường độ tin cậy dựa trên tính nhất quán thực thi và độ tương đồng với câu mẫu, không để LLM tự chấm điểm chủ quan. | Dataherald Engine Pattern |
| **RAGAS Framework** | **Đo lường RAG định lượng:** Chuẩn hóa các phép đo *Hit@k, MRR* cho khâu truy hồi và *Faithfulness* (độ bám nguồn, không bịa đặt) cho khâu sinh văn bản. | Es et al. (2023) |
| **LangGraph Multi-Agent** | **Đồ thị trạng thái có kiểu (StateGraph):** Cho phép rẽ nhánh điều kiện linh hoạt, chạy song song (Parallel execution) SQL và RAG, gộp nhánh tại node `join` có kiểm soát. | LangChain / LangGraph Engine |
| **Self-Consistency CoT** | **Lấy mẫu nhất quán:** Sinh nhiều phương án SQL nhiệt độ thấp để đối chiếu kết quả thực thi, tăng độ chính xác của câu truy vấn khó. | Wang et al. (ICLR 2023) |
| **An toàn máy tính** | **Quyền tối thiểu (Least Privilege):** Cô lập tài khoản AI ở tầng DB, không trao quyền ghi. | Saltzer & Schroeder (IEEE 1975) |
| **OWASP for LLM** | **Phòng chống Prompt Injection:** Phân tách rạch ròi giữa câu lệnh điều khiển (System Instructions) và dữ liệu truy xuất (Retrieved Data Context). | OWASP Top 10 for LLM (2025) |

---

## PHẦN 4. PHÂN TÍCH SWOT CHO KIẾN TRÚC GML V2

Một điểm cộng rất lớn khi bảo vệ khóa luận là bạn **dám nhìn thẳng vào ưu điểm và hạn chế** của hệ thống thông qua ma trận SWOT:

```
                  MA TRẬN SWOT — KIẾN TRÚC GML AI ASSISTANT V2
 ┌──────────────────────────────────────┬──────────────────────────────────────┐
 │ STRENGTHS (Điểm mạnh)                │ WEAKNESSES (Điểm yếu)                │
 │ • Chống ảo giác tài chính triệt để.  │ • Độ trễ xử lý (Latency) cao hơn     │
 │ • Tích hợp sâu tri thức GML (UAT+BRD)│   so với gọi 1 API đơn lẻ.           │
 │ • An toàn dữ liệu đa tầng (DB + AST).│ • Độ phức tạp vận hành & bảo trì     │
 │ • Cơ chế tự phục hồi (Self-healing). │   (phải cập nhật YAML và ChromaDB).  │
 │ • Tự động hóa giám sát (Alert Engine)│ • Phụ thuộc vào chất lượng schema.   │
 ├──────────────────────────────────────┼──────────────────────────────────────┤
 │ OPPORTUNITIES (Cơ hội)               │ THREATS (Thách thức & Rủi ro)        │
 │ • Mở rộng quy mô sang Sản xuất, Bán  │ • Schema Drift: CSDL thay đổi cấu    │
 │   hàng, Nhân sự chỉ cần thêm View.   │   trúc làm hỏng câu SQL tự động.     │
 │ • Tích hợp đa kênh (Teams, Zalo, PBI)│ • Chi phí Token API đám mây.         │
 │ • Triển khai Local LLM khi bảo mật   │ • Rủi ro bảo mật dữ liệu ra bên ngoài│
 │   đòi hỏi khắt khe (Ollama Qwen-2.5) │   nếu dùng Free-tier của Cloud LLM.  │
 └──────────────────────────────────────┴──────────────────────────────────────┘
```

### Chi tiết SWOT:
* **Strengths:** Thiết kế hướng tới độ tin cậy và kiểm chứng cao: Mọi con số trả về đều đối soát được ngược lại nguồn gốc bút toán và đối chiếu với đáp án chuẩn UAT (Ground Truth).
* **Weaknesses:** Luồng xử lý qua nhiều Agent (Intent ➔ SQL ➔ AST ➔ DB ➔ Synthesizer) có thể làm tăng độ trễ tổng thể, do đó hệ thống đặt mục tiêu giám sát P95 $\le 15$ giây và cần tối ưu qua streaming response cùng cơ chế caching.
* **Opportunities:** Kiến trúc có tính module hóa cao (Decoupled). Doanh nghiệp có thể thay thế mô hình LLM từ Google Gemini sang Claude hoặc mô hình Local (Qwen 2.5 Coder chạy trên máy chủ nội bộ) mà không phải viết lại logic điều phối của LangGraph.
* **Threats:** Khi đội ngũ Data Engineering thay đổi tên cột hoặc cấu trúc bảng trong CSDL (`Schema Drift`), SQL Agent có thể bị gãy nếu lớp Data Catalog không được cập nhật đồng bộ.

---

## PHẦN 5. BỘ CÂU HỎI HỘI ĐỒNG (COMMITTEE DEFENSE Q&A)

Dưới đây là 5 câu hỏi "kinh điển" mà các thầy cô trong Hội đồng chấm khóa luận thường đặt ra để kiểm tra xem sinh viên thực sự hiểu bản chất hay chỉ sao chép code:

---

### ❓ Câu hỏi 1: *"Tại sao em không dùng ChatGPT/Gemini đọc trực tiếp file Excel/Database mà phải thiết kế hệ thống 6 agent phức tạp như thế này?"*

> **Gợi ý trả lời tự tin:**  
> *"Dạ thưa Thầy/Cô, việc đưa trực tiếp CSDL cho một mô hình LLM nguyên bản (Naive LLM) gặp phải **3 rào cản chí mạng trong doanh nghiệp**:"*
> 1. **Vấn đề kích thước Context Window và Chi phí:** Kho dữ liệu GML có hàng chục bảng với hàng triệu bản ghi giao dịch, không thể nhồi toàn bộ dữ liệu vào prompt mỗi lần hỏi vì sẽ tràn bộ nhớ và chi phí token cực lớn.
> 2. **Rủi ro ảo giác (Hallucination) và tính toán sai:** LLM bản chất là mô hình xác suất từ ngữ (Next-token prediction), khả năng tính toán số học (Arithmetic reasoning) của nó rất kém. Nếu hỏi doanh thu lũy kế, nó có thể tự bịa ra một con số nghe rất hợp lý nhưng sai thực tế.
> 3. **Bảo mật dữ liệu:** Đưa trực tiếp CSDL cho LLM đồng nghĩa với việc cấp quyền tùy tiện cho mô hình.  
> 
> *"Hệ thống của em giải quyết bài toán này bằng kiến trúc **Phân tách trách nhiệm (Separation of Concerns)**: LLM chỉ đóng vai trò 'thông dịch viên' dịch ngôn ngữ tự nhiên thành câu lệnh SQL chuẩn; việc truy vấn và tính toán số học được giao lại cho chính CSDL PostgreSQL — nơi làm toán chính xác 100%. Các Agent khác như Explainer, Advisor chịu trách nhiệm đối chiếu quy chuẩn nghiệp vụ đã được duyệt từ trước."*

---

### ❓ Câu hỏi 2: *"Nếu mô hình sinh ra một câu SQL bị lỗi cú pháp hoặc chạy ra kết quả rỗng (0 dòng) thì hệ thống của em xử lý thế nào? Có bịa ra số không?"*

> **Gợi ý trả lời tự tin:**  
> *"Dạ thưa Thầy/Cô, hệ thống của em được trang bị **2 chốt chặn tự động (Automated Guards)**:"*
> 1. **Cơ chế Tự sửa lỗi (Self-Healing Loop) tối đa 3 lần:** Nếu câu SQL bị lỗi cú pháp CSDL, lỗi đó được làm sạch và gửi ngược lại cho SQL Agent kèm thông báo: *'Lần trước bạn viết lỗi này, hãy sửa lại'*. Đây là mẫu thiết kế chuẩn trong các hệ thống Text-to-SQL hiện đại (như BIRD, Dataherald), giúp khắc phục phần lớn các lỗi cú pháp ban đầu do nhầm tên cột hoặc alias.
> 2. **Chốt chặn hợp đồng dữ liệu (Contract Guard):** Nếu sau 3 lần vẫn lỗi, hoặc câu lệnh chạy đúng nhưng CSDL trả về rỗng (`no_data`), hệ thống **ngay lập tức ngắt luồng điều phối (Short-circuit)**. Trạng thái rẽ nhánh thẳng về node `no_data_response`, tuyệt đối **không chuyển tiếp kết quả này vào Synthesizer Agent**. Nhờ đó, LLM không có cơ hội 'đoán mò' hay bịa ra số liệu giả. Hệ thống sẽ trả lời minh bạch: *'Không tìm thấy dữ liệu phát sinh trong kỳ báo cáo'*.

---

### ❓ Câu hỏi 3: *"Dữ liệu tài chính là bí mật tối mật của doanh nghiệp. Em giải quyết bài toán an toàn thông tin và quyền riêng tư như thế nào khi dùng Cloud LLM?"*

> **Gợi ý trả lời tự tin:**  
> *"Dạ thưa Thầy/Cô, em đã thiết kế bài toán bảo mật theo chuẩn **Phòng thủ đa tầng (Defense-in-Depth)** và ghi nhận cụ thể trong quyết định kiến trúc **ADR-005**:"*
> 1. **Nguyên tắc Che dấu thông tin nhạy cảm:** Câu truy vấn gửi lên Cloud LLM chỉ chứa Metadata (tên cột, tên bảng nghiệp vụ, công thức) và câu hỏi của người dùng. **Toàn bộ dữ liệu chi tiết hàng triệu dòng nằm nguyên vẹn tại PostgreSQL On-premise**. Chỉ kết quả tổng hợp (ví dụ: một con số tổng dư nợ) mới được đưa vào ngữ cảnh diễn đạt.
> 2. **Ràng buộc cấp độ dịch vụ (Enterprise Tier):** Thiết kế quy định bắt buộc dùng API có trả phí (Paid Tier) của các nhà cung cấp đám mây. Theo điều khoản dịch vụ doanh nghiệp, nhà cung cấp cam kết **không lưu trữ và không dùng dữ liệu khách hàng để huấn luyện lại mô hình (Zero Data Retention)**.
> 3. **Khả năng Fallback sang Local LLM:** Tài liệu thiết kế mục 8.1 của em đã chuẩn bị sẵn phương án sử dụng mô hình mã nguồn mở nội bộ (`Ollama Qwen2.5-Coder:7b`) chạy cục bộ trên máy trạm để phục vụ những môi trường yêu cầu cách ly mạng hoàn toàn (Air-gapped).*

---

### ❓ Câu hỏi 4: *"Trong thực tế, dữ liệu dự án GML bị thiếu (ví dụ doanh thu chỉ có tháng 7/2026, giá vốn B02 bằng 0). Nếu người dùng hỏi xu hướng tăng trưởng (Trend) hoặc hỏi về lợi nhuận gộp thì hệ thống xử lý ra sao?"*

> **Gợi ý trả lời tự tin:**  
> *"Dạ thưa Thầy/Cô, đây là một điểm rất đặc biệt mà em đã phân tích sâu trong mục **Ràng buộc C1** và giải quyết bằng **Chiến lược dữ liệu lai (Hybrid Strategy - Phương án B)**:"*
> 1. **Tính trung thực của hệ thống:** Với các chỉ số bị khuyết dữ liệu trên CSDL thật (như giá vốn bằng 0), hệ thống được cấu hình nhận diện các hiện tượng dữ liệu bất thường (dựa trên 12 ranh giới dữ liệu từ UAT). Khi người dùng hỏi biên lợi nhuận gộp, hệ thống sẽ **từ chối khẳng định biên lợi nhuận là 100%**, mà cảnh báo rõ: *'Chỉ tiêu Giá vốn B02-DN_11 hiện tại bằng 0, dữ liệu kế toán chưa được nạp đủ nên chưa thể tính toán'*.
> 2. **Đối với Trend Analyst:** Nếu số tháng lịch sử nhỏ hơn 6 tháng (`data_coverage < 6`), Agent sẽ xuất cảnh báo *'Chưa đủ dữ liệu chuỗi thời gian để phân tích xu hướng MoM/YoY'*.
> 3. **Đối với việc kiểm thử (Testing):** Để chứng minh toàn bộ thuật toán Trend Analyst và Alert Engine hoạt động hoàn hảo mà không bị cản trở bởi dữ liệu thật thiếu thốn, em đã xây dựng thêm một bộ CSDL mô phỏng độc lập (`synthetic`) chuẩn 12 tháng có cài sẵn các bất thường dán nhãn để đo lường độ nhạy của thuật toán.*

---

### ❓ Câu hỏi 5: *"Làm thế nào em đo lường và chứng minh được phiên bản kiến trúc v2 này tốt hơn phiên bản v1? Hay chỉ là cảm giác chủ quan?"*

> **Gợi ý trả lời tự tin:**  
> *"Dạ thưa Thầy/Cô, em không đánh giá hệ thống bằng cảm quan 'trông có vẻ mượt hơn', mà xây dựng một **Khung đánh giá định lượng độc lập (Evaluation Harness) gồm 60 câu hỏi Benchmark** chia làm 2 tập: Dev (40 câu) và Test bị khóa (20 câu):"*
> 1. **Về độ chính xác truy vấn SQL (Execution Accuracy):** Em lấy trực tiếp kết quả số liệu đối soát từ 5 tệp kiểm thử UAT kế toán làm **Đáp án chuẩn (Ground Truth - Gold Queries)**. Câu trả lời của hệ thống phải cho ra kết quả sai số tương đối $\le 0.01\%$ so với đáp án UAT. Mục tiêu của v2 là đạt $\ge 85\%$ trên tập test.
> 2. **Về khả năng bám nguồn RAG (Faithfulness):** Đo lường tỷ lệ các câu khẳng định có trích dẫn đúng tài liệu BRD/Guide, mục tiêu $\ge 90\%$.
> 3. **Về khả năng chặn rủi ro an toàn (Security Guard):** Đạt $100\%$ từ chối các câu hỏi phá hoại, tiêm nhiễm lệnh (Prompt Injection) hoặc vượt quyền xem dữ liệu.
> 
> *"Toàn bộ kết quả so sánh trước/sau giữa v1 và v2 đều được tự động xuất thành các báo cáo Markdown lưu trong thư mục `eval/reports/` làm bằng chứng nghiệm thu minh bạch."*

---

### 💡 Lời khuyên vàng khi đứng trước Hội đồng:
1. **Bình tĩnh, khiêm tốn nhưng chắc chắn:** Luôn nhấn mạnh vào tính **trung thực số liệu** và **giá trị thực tế cho doanh nghiệp**.
2. **Thuật ngữ chuẩn xác:** Dùng đúng các từ khóa kỹ thuật: *StateGraph, AST Parser, Least Privilege, Ground Truth, Execution Accuracy, Data Drift*.
3. **Nếu gặp câu hỏi chưa làm được:** Hãy trả lời theo hướng: *"Dạ thưa Thầy/Cô, đây là một điểm mở rộng rất hay. Trong phạm vi thiết kế v2 hiện tại, em đã ghi nhận giới hạn này vào mục Rủi ro của tài liệu kiến trúc (hoặc ADR) và đã chuẩn bị phương án khắc phục ở giai đoạn tiếp theo như sau..."*

