# 🤖 Báo cáo Tham khảo #4: AI Business Assistant
## Dự án: `LangGraph_Txt2SQL_Streamlit_Agent` & Agentic LLM

> **Link tham khảo gốc:** [0xZee/LangGraph_Txt2SQL_Streamlit_Agent](https://github.com/0xZee/LangGraph_Txt2SQL_Streamlit_Agent)
> **Liên quan đến:** `7. AI-Business-Assistant` của GML  
> **Ngày nghiên cứu:** 04/10/2026

---

## 1. Tổng quan Kiến trúc Agentic AI

Dự án này là minh chứng rõ ràng nhất cho xu hướng "Chat with Database" hiện đại. Thay vì chỉ dùng LangChain cơ bản (thường xuyên bị lỗi logic khi query SQL phức tạp), dự án dùng **LangGraph** để tạo ra một **Agentic Workflow** (Luồng suy nghĩ của Agent).

### Tại sao lại là LangGraph?
LangGraph cho phép định nghĩa các State (Trạng thái) và Node (Hành động) dưới dạng đồ thị (Graph). Khi AI nhận câu hỏi:
1. Nó đi vào Node **"Suy nghĩ"** (Cần lấy data ở bảng nào?).
2. Chuyển sang Node **"Viết SQL"**.
3. Chuyển sang Node **"Chạy SQL"**. 
4. Nếu SQL bị lỗi (Ví dụ sai tên cột), nó tự động quay lại vòng lặp Node **"Sửa SQL"** (Self-correction) thay vì báo lỗi cho người dùng.

Đây chính là sự khác biệt giữa AI thời cũ và **Agentic AI**.

---

## 2. Phân tích Flow của 0xZee/LangGraph_Txt2SQL_Streamlit_Agent

Dự án có giao diện chat cực kỳ quen thuộc (giống ChatGPT) làm bằng **Streamlit**.

### Kiến trúc chi tiết:

```text
[Người dùng gõ câu hỏi trên Streamlit UI]
"Doanh thu tháng trước của ván MDF là bao nhiêu?"
                       │
                       ▼
            [State Graph Management]
                       │
       ┌───────────────▼───────────────┐
       │ Node 1: Schema Retrieval (RAG)│ <-- Lấy Schema của DB để LLM hiểu cấu trúc
       └───────────────┬───────────────┘
                       ▼
       ┌───────────────┴───────────────┐
       │ Node 2: SQL Generation        │ <-- Dịch Text sang PostgreSQL
       └───────────────┬───────────────┘
                       ▼
       ┌───────────────┴───────────────┐
       │ Node 3: SQL Execution         │ <-- Chạy thử trên DB (read-only)
       └───────────────┬───────────────┘
             [LỖI?] ───┘ │ [THÀNH CÔNG]
       (Tự sửa code)     ▼
       ┌───────────────┴───────────────┐
       │ Node 4: Natural Language Gen  │ <-- Viết báo cáo: "Doanh thu là 15 tỷ..."
       └───────────────┬───────────────┘
                       ▼
          [Trả kết quả về Streamlit]
```

---

## 3. Áp dụng vào Gỗ Minh Long (GML)

Chúng ta sẽ build một AI Assistant xịn xò hơn cả dự án trên, nhờ kết hợp cả **SQL Agent** và **RAG (Policy) Agent**.

### 3.1 Setup Streamlit UI
- Dùng `st.chat_message("user")` và `st.chat_message("assistant")` để làm giao diện chat.
- Dùng `st.session_state` để lưu trữ lịch sử trò chuyện (Memory), giúp sếp có thể hỏi các câu nối tiếp nhau. (VD: Câu 1: "Chi phí marketing?", Câu 2: "Còn chi phí vận chuyển thì sao?").

### 3.2 Tích hợp RAG cho BRD/Tài liệu nội bộ
Trong GML, sếp không chỉ hỏi số liệu, mà còn hỏi nguyên nhân, quy định.
- Câu hỏi: *"Tại sao vòng quay tồn kho giảm?"*
- **Agent 1 (SQL):** Chạy SQL lấy số vòng quay tồn kho (VQHKT) qua các tháng để vẽ biểu đồ.
- **Agent 2 (RAG):** Đọc file `guide_dashboard.md` hoặc các file phân tích kinh doanh để lấy định nghĩa: *"Vòng quay tồn kho giảm có thể do chính sách nhập hàng ồ ạt hoặc doanh số bán ra chậm."*
- **Supervisor Node (LangGraph):** Tổng hợp cả 2 thông tin thành 1 báo cáo hoàn chỉnh trả cho sếp.

### 3.3 An toàn dữ liệu (Bảo mật)
- **Database Connection:** Khi AI connect vào PostgreSQL (Silver Layer), BẮT BUỘC phải dùng một user role là **`read_only`**. Tuyệt đối không cấp quyền `INSERT/UPDATE/DELETE` để tránh trường hợp AI (hoặc Prompt Injection) vô tình xóa dữ liệu.
- **Schema Filtering:** Không đưa toàn bộ DB cho AI. Chỉ đưa schema của các bảng `fact_businessplan`, `fact_sales`, `dim_indicator` cho Agent.

---

## 4. Công cụ & Tech Stack đề xuất cho GML

| Thành phần | Công nghệ ưu tiên | Giải thích |
|:---|:---|:---|
| **Giao diện (UI)** | Streamlit | Dễ code, chuyên cho Python Data Apps. Hỗ trợ hiển thị cả bảng và biểu đồ (Plotly) trực tiếp trong khung chat. |
| **Agent Framework** | LangGraph | Hỗ trợ cyclic logic (tự sửa lỗi SQL), chia nhỏ Agent (Multi-agent architecture). |
| **Vector DB (Cho RAG)** | ChromaDB / FAISS | Lưu trữ các tài liệu BRD, Word, PDF dưới dạng vector. |
| **LLM Model** | OpenAI GPT-4o / Claude 3.5 | Cần model cực thông minh để viết SQL chính xác. (DeepSeek/Ollama cho local dev). |
| **ORM / DB Toolkit** | LangChain `SQLDatabase` | Thư viện bọc sẵn connection tới PostgreSQL, tự động pull schema. |

---

## 5. Roadmap xây dựng

1. **Giai đoạn 1 (Proof of Concept):** Build Streamlit app đơn giản, kết nối với Langchain `create_sql_agent` để query 1 bảng duy nhất (`fact_sales`). Test khả năng dịch Tiếng Việt sang SQL.
2. **Giai đoạn 2 (LangGraph):** Chuyển sang LangGraph, chia luồng tư duy thành các Node, thêm khả năng tự sửa lỗi (Self-healing).
3. **Giai đoạn 3 (RAG Integration):** Nhúng các file `.docx` và `.md` (BRD, Guide) vào VectorDB. Thêm 1 Agent chuyên đọc tài liệu.
4. **Giai đoạn 4 (Supervisor):** Build con Agent tổng (Router/Supervisor). Phân tích intent người dùng → Quyết định nên gọi SQL Agent hay RAG Agent hay cả hai.
5. **Giai đoạn 5 (Deploy):** Đóng gói Docker, deploy nội bộ kèm xác thực (Authentication).
