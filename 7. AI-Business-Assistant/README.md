# 🤖 AI Business Assistant — Gỗ Minh Long (GML)

> **Hệ thống Trợ lý Trí tuệ Doanh nghiệp & Hỗ trợ Ra quyết định Quản trị**  
> Tích hợp Kiến trúc Đa Agent (Multi-Agent Architecture) kết nối Kho dữ liệu Data Warehouse (PostgreSQL) và Tài liệu Tri thức Doanh nghiệp (RAG Vector Store).

---

## 📌 Tổng quan dự án

Dự án **AI Business Assistant** của Gỗ Minh Long ra đời nhằm giải quyết bài toán cốt lõi của Ban Lãnh đạo (C-Levels, Giám đốc khối):  
Thay vì phải thủ công mở từng Dashboard Power BI, lọc slicer để tìm kiếm dữ liệu thô, người quản trị có thể **đặt câu hỏi bằng tiếng Việt tự nhiên** và nhận ngay câu trả lời toàn diện:
1. **Số liệu thực tế chính xác (SQL Data Layer):** Truy vấn trực tiếp từ cơ sở dữ liệu Silver/Gold Data Warehouse.
2. **Giải thích bản chất nghiệp vụ (Semantic & RAG Layer):** Làm rõ công thức cấu thành, chỉ số liên quan, đối chiếu quy chuẩn BRD & cẩm nang ISO.
3. **Phân tích xu hướng & Gợi ý hành động (Decision Support Layer):** Cảnh báo ngưỡng rủi ro và gợi ý kịch bản hành động cụ thể cho Ban Quản trị.

---

## 📁 Cấu trúc thư mục

```bash
7. AI-Business-Assistant/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py      # LangGraph Điều phối Workflow & Routing
│   │   ├── sql_agent.py         # Text-to-SQL Generator & Query Executor
│   │   ├── rag_agent.py         # Truy xuất tài liệu nghiệp vụ từ VectorStore
│   │   └── synthesizer.py      # Tổng hợp câu trả lời & format phản hồi
│   ├── api/
│   │   └── server.py            # FastAPI RESTful API endpoints
│   └── streamlit_app.py         # Giao diện Chat trực quan cho người dùng
├── chroma_db/                   # Cơ sở dữ liệu Vector Store (ChromaDB)
├── docs/                        # 📑 Tài liệu kế hoạch & thiết kế kỹ thuật
│   ├── AI_Business_Assistant_v1_Plan.md  # Kế hoạch & Kiến trúc nền tảng Phase 1
│   └── AI_Business_Assistant_v2_Plan.md  # Kế hoạch nâng cấp v2.0 (Decision & Intelligence Layer)
├── scripts/
│   └── build_vectorstore.py     # Script nạp tài liệu BRD, Guide vào ChromaDB
├── tests/                       # Kịch bản kiểm thử tự động
├── schema.txt                   # DDL lược đồ bảng Data Warehouse
├── docker-compose.yml           # Triển khai hệ thống qua Docker
└── requirements.txt             # Danh sách thư viện Python phụ thuộc
```

---

## 🏛️ Kiến trúc Hệ thống

### 1. Kiến trúc luồng xử lý tổng thể

```
                   ┌──────────────────────────────────────┐
                   │    👤 Người dùng / Ban Quản trị      │
                   │     (Streamlit UI / REST API)        │
                   └──────────────────┬───────────────────┘
                                      │ Câu hỏi tự nhiên
                                      ▼
                   ┌──────────────────────────────────────┐
                   │       Orchestrator Agent             │
                   │    (LangGraph State Machine)         │
                   └──────────┬─────────────────┬─────────┘
                              │                 │
              [Query Dữ liệu] │                 │ [Tra cứu Nghiệp vụ]
                              ▼                 ▼
             ┌─────────────────────┐   ┌────────────────────────┐
             │      SQL Agent      │   │       RAG Agent        │
             │   - Phân tích DDL   │   │  - ChromaDB Retrieval  │
             │   - Sinh câu SQL    │   │  - BRD / Guide Tra cứu │
             │   - Query Postgres  │   └───────────┬────────────┘
             └──────────┬──────────┘               │
                        │                          │
                        └─────────────┬────────────┘
                                      ▼
                   ┌──────────────────────────────────────┐
                   │          Synthesizer Agent           │
                   │ - Kiểm chứng số liệu & logic         │
                   │ - Giải thích công thức & bối cảnh    │
                   │ - Đưa khuyến nghị hành động          │
                   └──────────────────┬───────────────────┘
                                      │
                                      ▼
                   💬 Câu trả lời chuẩn mực & Insight quản trị
```

### 2. Các thành phần chính
- **Streamlit Web UI / FastAPI (`app/`):** Cung cấp giao diện tương tác chat trực quan, quản lý lịch sử trao đổi và phản hồi nhanh qua streaming.
- **SQL Agent (`app/agents/sql_agent.py`):** Ánh xạ câu hỏi tự nhiên thành câu truy vấn SQL chuẩn PostgreSQL trên schema kho dữ liệu `schema.txt`.
- **RAG Agent (`app/agents/rag_agent.py`):** Tìm kiếm ngữ nghĩa trong kho tri thức nghiệp vụ (ISO-BRD, cẩm nang hướng dẫn sử dụng Dashboard 1-5).
- **Orchestrator & Synthesizer (`app/agents/`):** Kết hợp kết quả số liệu định lượng với tài liệu định tính để tạo câu trả lời mạch lạc, hữu ích cho cấp quản lý.

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### Yêu cầu tiên quyết
- Python 3.10+
- PostgreSQL (Đã dựng kho dữ liệu GML)
- OpenAI API Key hoặc Google Gemini API Key

### Bước 1: Khởi tạo môi trường
```bash
# Di chuyển vào thư mục dự án
cd "7. AI-Business-Assistant"

# Tạo và kích hoạt môi trường ảo
python -m venv venv
venv\Scripts\activate      # Windows

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

### Bước 2: Cấu hình biến môi trường
Tạo file `.env` từ file `.env.example`:
```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://postgres:password@localhost:5432/gml_dw
CHROMA_PERSIST_DIR=./chroma_db
```

### Bước 3: Nạp tri thức vào Vector Store
```bash
python scripts/build_vectorstore.py
```

### Bước 4: Khởi chạy ứng dụng
- **Chạy FastAPI Backend:**
  ```bash
  uvicorn app.api.server:app --reload --port 8000
  ```
- **Chạy Giao diện Streamlit:**
  ```bash
  streamlit run app/streamlit_app.py
  ```

---

## 🗺️ Lộ trình Phát triển (Roadmap)

Chi tiết kế hoạch triển khai được quản lý tập trung trong thư mục [docs/](file:///D:/C%C3%B4ng%20vi%E1%BB%87c/1.%20D%E1%BB%B1%20%C3%A1n%20G%E1%BB%97%20Minh%20Long/7.%20AI-Business-Assistant/docs/):

1. **[Plan v1.0 — Foundation & Query-Result Engine](file:///D:/C%C3%B4ng%20vi%E1%BB%87c/1.%20D%E1%BB%B1%20%C3%A1n%20G%E1%BB%97%20Minh%20Long/7.%20AI-Business-Assistant/docs/AI_Business_Assistant_v1_Plan.md):**
   - Xây dựng khung Multi-Agent cơ bản (LangGraph + FastAPI + Streamlit).
   - Triển khai Text-to-SQL trên kho dữ liệu Data Warehouse.
   - Xây dựng Vector DB nạp BRD & tài liệu báo cáo.
2. **[Plan v2.0 — Intelligence & Decision Layer](file:///D:/C%C3%B4ng%20vi%E1%BB%87c/1.%20D%E1%BB%B1%20%C3%A1n%20G%E1%BB%97%20Minh%20Long/7.%20AI-Business-Assistant/docs/AI_Business_Assistant_v2_Plan.md):**
   - Học hỏi từ các kiến trúc mã nguồn mở hàng đầu (*Vanna AI*, *Dataherald*, *LangGraph Multi-Agent*).
   - Bổ sung **Semantic KPI Registry (`kpi_definitions.yaml`)** gắn liền 18 KPI cốt lõi của 5 Dashboard.
   - Thêm các Agent chuyên sâu: **ExplainerAgent** (giải thích cấu thành chỉ số), **TrendAnalystAgent** (so sánh kỳ/kế hoạch), và **DecisionAdvisorAgent** (cảnh báo ngưỡng & gợi ý hành động).
   - Tối ưu bộ nhớ hội thoại ngữ cảnh dài (Session & Thread State).

---
*Dự án thuộc Hệ sinh thái Dữ liệu & Trí tuệ Kinh doanh — Công ty Gỗ Minh Long.*
