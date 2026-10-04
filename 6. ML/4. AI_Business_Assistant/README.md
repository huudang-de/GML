# 🤖 AI Business Assistant — Gỗ Minh Long

> **Mức ưu tiên:** ⭐⭐⭐⭐⭐ | **Stack:** Streamlit + FastAPI + PostgreSQL + LLM (Gemini/GPT-4o) + RAG + Power BI

---

## 1. Tầm nhìn & Mục tiêu

Thay vì CEO phải **mở Power BI → chọn Dashboard → tìm biểu đồ → đọc số**, hệ thống AI Business Assistant cho phép CEO **hỏi bằng tiếng Việt tự nhiên** và nhận câu trả lời tổng hợp từ cả **dữ liệu thực tế (SQL)** và **tài liệu chính sách (RAG)** trong vòng vài giây.

```
👤 CEO hỏi: "Tại sao lợi nhuận tháng 9 giảm so với tháng 8?"
                          │
                          ▼
        💬 AI trả lời: "Lợi nhuận giảm 14,2% (từ 2,1 tỷ → 1,8 tỷ).
                        Nguyên nhân chính:
                        1. Giá vốn tăng 8% do nhập gỗ ván giá cao (T9)
                        2. Doanh thu giảm 3,1% — tháng 9 thường thấp điểm (seasonality)
                        3. Chi phí lãi vay tăng do hạn mức tín dụng được giải ngân thêm 5 tỷ"
```

---

## 2. Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│                                                             │
│   ┌────────────────┐              ┌──────────────────────┐  │
│   │   Streamlit    │              │      Power BI        │  │
│   │  (AI Chat UI)  │              │    (Dashboard)       │  │
│   └───────┬────────┘              └──────────────────────┘  │
└───────────┼─────────────────────────────────────────────────┘
            │ HTTP Request
            ▼
┌─────────────────────────────────────────────────────────────┐
│                     API LAYER — FastAPI                      │
│                                                             │
│   POST /chat    GET /kpi     GET /health                    │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Orchestrator Agent (LangChain / LangGraph)         │   │
│   │  - Intent Classification                            │   │
│   │  - Tool Routing (SQL Tool vs RAG Tool)              │   │
│   │  - Response Synthesis                               │   │
│   └──────────────┬──────────────────┬───────────────────┘   │
└──────────────────┼──────────────────┼───────────────────────┘
                   │                  │
        ┌──────────▼──────┐  ┌───────▼──────────────┐
        │   SQL AGENT     │  │     RAG PIPELINE      │
        │                 │  │                       │
        │ Text → SQL      │  │ Query → Embed → Search│
        │ (LLM generates  │  │ (Vector Store)        │
        │  SQL query)     │  │                       │
        │       │         │  │  Documents:           │
        │       ▼         │  │  - ISO-BRD_Final.xlsx │
        │  PostgreSQL     │  │  - guide_dashboard*.md│
        │  Silver Layer   │  │  - Tổng quan dự án    │
        │                 │  │  - KPI definitions    │
        └────────┬────────┘  └───────────────────────┘
                 │                       │
                 └──────────┬────────────┘
                            ▼
                     LLM Synthesis
                    (Gemini / GPT-4o)
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
          Structured JSON         Natural Language
          → Power BI Embed        → Streamlit Chat
```

---

## 3. Chi tiết từng Component

### 3.1 Frontend — Streamlit Chat UI

**File:** `app/streamlit_app.py`

```python
import streamlit as st
import requests

st.set_page_config(page_title="GML AI Assistant", page_icon="🪵", layout="wide")
st.title("🪵 Gỗ Minh Long — AI Business Assistant")

# Sidebar: Suggested questions
with st.sidebar:
    st.header("💡 Câu hỏi gợi ý")
    suggestions = [
        "Lợi nhuận tháng này so với tháng trước?",
        "Top 5 khách hàng có dư nợ lớn nhất?",
        "Tồn kho hiện tại của ván ép?",
        "Cash Runway còn bao nhiêu tháng?",
        "Vòng quay hàng tồn kho Q3 là bao nhiêu?",
    ]
    for q in suggestions:
        if st.button(q, use_container_width=True):
            st.session_state['query'] = q

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Hỏi bất kỳ điều gì về doanh nghiệp..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call FastAPI
    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích dữ liệu..."):
            response = requests.post(
                "http://localhost:8000/chat",
                json={"query": prompt, "session_id": st.session_state.get("session_id", "default")}
            )
            result = response.json()

        # Display answer
        st.markdown(result["answer"])

        # Display supporting data table if available
        if result.get("data"):
            st.dataframe(result["data"])

        # Display SQL query used (expandable, for transparency)
        if result.get("sql_query"):
            with st.expander("🔍 SQL đã thực thi"):
                st.code(result["sql_query"], language="sql")

        # Display sources (RAG)
        if result.get("sources"):
            with st.expander("📄 Nguồn tham khảo"):
                for src in result["sources"]:
                    st.caption(f"• {src}")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
```

---

### 3.2 Backend — FastAPI

**File:** `app/api/main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agents.orchestrator import OrchestratorAgent

app = FastAPI(title="GML AI Business Assistant API", version="1.0.0")
agent = OrchestratorAgent()

class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    sql_query: str | None = None
    data: list | None = None
    sources: list[str] | None = None
    intent: str | None = None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await agent.run(request.query, request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

### 3.3 LLM Orchestrator — LangGraph Agent

**File:** `app/agents/orchestrator.py`

```python
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agents.sql_agent import SQLAgent
from app.agents.rag_agent import RAGAgent
from app.agents.synthesizer import Synthesizer

class OrchestratorAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
        self.sql_agent = SQLAgent()
        self.rag_agent = RAGAgent()
        self.synthesizer = Synthesizer(self.llm)
        self.graph = self._build_graph()

    def _build_graph(self):
        """
        LangGraph Flow:
          classify_intent
               │
        ┌──────┴──────┐
        ▼             ▼
       sql          rag         (parallel hoặc sequential tuỳ intent)
        │             │
        └──────┬──────┘
               ▼
           synthesize
               │
              END
        """
        graph = StateGraph(dict)

        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("sql_lookup", self.sql_agent.run)
        graph.add_node("rag_lookup", self.rag_agent.run)
        graph.add_node("synthesize", self.synthesizer.run)

        graph.set_entry_point("classify_intent")

        graph.add_conditional_edges("classify_intent", self._route, {
            "sql_only":  "sql_lookup",
            "rag_only":  "rag_lookup",
            "both":      "sql_lookup",   # sql first, then rag in parallel
        })
        graph.add_edge("sql_lookup", "synthesize")
        graph.add_edge("rag_lookup", "synthesize")
        graph.add_edge("synthesize", END)

        return graph.compile()

    def _classify_intent(self, state: dict) -> dict:
        """Phân loại câu hỏi: cần SQL, RAG, hay cả hai"""
        prompt = f"""
        Phân loại câu hỏi sau vào 1 trong 3 nhóm: "sql_only", "rag_only", "both"

        - sql_only: Câu hỏi cần số liệu cụ thể (doanh thu, tồn kho, công nợ, dòng tiền...)
        - rag_only: Câu hỏi về chính sách, quy trình, định nghĩa KPI, hướng dẫn sử dụng
        - both: Cần cả số liệu lẫn giải thích nghiệp vụ

        Câu hỏi: "{state['query']}"

        Trả lời chỉ 1 từ: sql_only | rag_only | both
        """
        intent = self.llm.invoke(prompt).content.strip()
        return {**state, "intent": intent}

    async def run(self, query: str, session_id: str) -> dict:
        state = {"query": query, "session_id": session_id}
        result = await self.graph.ainvoke(state)
        return result
```

---

### 3.4 SQL Agent — Text-to-SQL

**File:** `app/agents/sql_agent.py`

```python
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI

SCHEMA_CONTEXT = """
Các bảng quan trọng trong schema 'silver':
- fact_balancesheet(indicator_code, report_date, ending_balance): CĐKT (B01-DN_xxx)
- fact_incomestatement(indicator_code, report_date, current_period_amount): KQKD (B02-DN_xxx)
- fact_cashflow(account_no, posting_date, debit_amount, credit_amount, credit_balance): Sổ cái
- fact_inventory(item_code, report_date, closing_qty, closing_value): Tồn kho
- fact_accountsreceivable(customer_code, invoice_date, invoice_amount, days_overdue): Phải thu
- fact_businessplan(indicator_code, period, target_amount): Kế hoạch kinh doanh
- dim_partner(partner_code, partner_name): Danh sách đối tác
- dim_item(item_code, item_name, category): Danh sách sản phẩm
- dim_date(date, month, quarter, year): Lịch

Lưu ý:
- Luôn giới hạn kết quả bằng LIMIT 100
- Dùng tiếng Việt trong alias cột
- Số tiền đơn vị là VNĐ, khi hiển thị chia 1,000,000,000 để ra tỷ
"""

class SQLAgent:
    def __init__(self):
        self.db = SQLDatabase.from_uri("postgresql://user:pass@localhost/gml", schema="silver")
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type="openai-tools",
            verbose=True,
            prefix=SCHEMA_CONTEXT
        )

    def run(self, state: dict) -> dict:
        result = self.agent.invoke({"input": state["query"]})
        return {
            **state,
            "sql_result": result.get("output"),
            "sql_query": result.get("intermediate_steps", [{}])[-1].get("query")
        }
```

---

### 3.5 RAG Agent — Retrieval từ tài liệu nội bộ

**File:** `app/agents/rag_agent.py`

```python
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Documents được index vào Vector Store
DOCUMENT_SOURCES = [
    r"D:\Công việc\1. Dự án Gỗ Minh Long\4. Phát triển báo cáo\guide_dashboard*.md",
    r"D:\Công việc\1. Dự án Gỗ Minh Long\2. Tài liệu phân tích và thiết kế\**\*.md",
]

class RAGAgent:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.vectorstore = self._load_or_build_vectorstore()

    def _load_or_build_vectorstore(self):
        try:
            return Chroma(persist_directory="./chroma_db", embedding_function=self.embeddings)
        except:
            return self._build_vectorstore()

    def _build_vectorstore(self):
        """Load và index toàn bộ tài liệu nội bộ"""
        loader = DirectoryLoader(".", glob="4. Phát triển báo cáo/guide_dashboard*.md",
                                  loader_cls=UnstructuredMarkdownLoader)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)

        vectorstore = Chroma.from_documents(
            chunks, self.embeddings, persist_directory="./chroma_db"
        )
        vectorstore.persist()
        return vectorstore

    def run(self, state: dict) -> dict:
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.get_relevant_documents(state["query"])
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        sources = [doc.metadata.get("source", "Unknown") for doc in relevant_docs]

        return {**state, "rag_context": context, "sources": sources}
```

---

### 3.6 Response Synthesizer

**File:** `app/agents/synthesizer.py`

```python
SYNTHESIS_PROMPT = """
Bạn là AI Business Assistant của Gỗ Minh Long — một công ty sản xuất và kinh doanh gỗ.
Nhiệm vụ của bạn là trả lời câu hỏi của Ban Lãnh đạo một cách chính xác, ngắn gọn, dễ hiểu.

Câu hỏi: {query}

Dữ liệu từ Database:
{sql_result}

Tài liệu nghiệp vụ liên quan:
{rag_context}

Hướng dẫn trả lời:
1. Bắt đầu bằng số liệu cụ thể (nếu có)
2. Giải thích nguyên nhân (nếu có thể suy luận từ dữ liệu)
3. Đề xuất hành động tiếp theo (nếu phù hợp)
4. Dùng tiếng Việt, văn phong chuyên nghiệp nhưng súc tích
5. Nếu không có dữ liệu, hãy nói rõ lý do

Trả lời:
"""

class Synthesizer:
    def __init__(self, llm):
        self.llm = llm

    def run(self, state: dict) -> dict:
        prompt = SYNTHESIS_PROMPT.format(
            query=state["query"],
            sql_result=state.get("sql_result", "Không có dữ liệu từ SQL"),
            rag_context=state.get("rag_context", "Không có tài liệu liên quan")
        )
        answer = self.llm.invoke(prompt).content
        return {**state, "answer": answer}
```

---

### 3.7 Power BI Integration

**Cách 1 — Embed Power BI vào Streamlit (recommended):**
```python
import streamlit.components.v1 as components

# Nhúng Power BI Report vào tab bên cạnh chat
components.iframe(
    src="https://app.powerbi.com/reportEmbed?reportId=YOUR_REPORT_ID&autoAuth=true",
    height=600, scrolling=True
)
```

**Cách 2 — Push AI insights vào PostgreSQL để Power BI đọc:**
```python
# Lưu AI conversation log → Power BI đọc để phân tích trend câu hỏi CEO
log_df = pd.DataFrame([{
    "session_id": session_id,
    "query": query,
    "intent": intent,
    "answer_summary": answer[:200],
    "timestamp": pd.Timestamp.now()
}])
log_df.to_sql("fact_ai_chat_log", engine, schema="silver", if_exists="append", index=False)
```

---

## 4. Kiến trúc thư mục

```
4. AI_Business_Assistant/
├── README.md                   ← File này
├── requirements.txt
├── .env.example                ← API keys template
├── docker-compose.yml          ← FastAPI + ChromaDB + Streamlit
│
├── app/
│   ├── streamlit_app.py        ← UI Layer
│   │
│   ├── api/
│   │   ├── main.py             ← FastAPI endpoints
│   │   └── models.py           ← Pydantic schemas
│   │
│   └── agents/
│       ├── orchestrator.py     ← LangGraph flow
│       ├── sql_agent.py        ← Text-to-SQL
│       ├── rag_agent.py        ← Vector search
│       └── synthesizer.py      ← LLM answer generation
│
├── scripts/
│   ├── build_vectorstore.py    ← Index tài liệu vào ChromaDB
│   └── test_queries.py         ← Kiểm thử bộ câu hỏi mẫu
│
├── chroma_db/                  ← Vector store (local)
└── tests/
    ├── test_sql_agent.py
    └── test_rag_agent.py
```

---

## 5. Kịch bản sử dụng mẫu (Test Cases)

| # | Câu hỏi CEO | Intent | Tool | Kết quả kỳ vọng |
|:--|:---|:--|:--|:---|
| 1 | "Doanh thu tháng 9 là bao nhiêu?" | sql_only | SQL → fact_incomestatement | Con số cụ thể + so sánh MoM |
| 2 | "Cash Runway còn bao nhiêu tháng?" | sql_only | SQL → fact_cashflow | Số tháng + cảnh báo nếu < 3 |
| 3 | "Vòng quay phải thu được tính thế nào?" | rag_only | RAG → guide_dashboard | Giải thích công thức từ BRD |
| 4 | "Tại sao lợi nhuận giảm?" | both | SQL + RAG | Số liệu + phân tích nguyên nhân |
| 5 | "Top 5 KH nợ quá hạn nhất?" | sql_only | SQL → fact_accountsreceivable | Bảng danh sách + số ngày quá hạn |
| 6 | "Kế hoạch doanh thu Q4 là bao nhiêu?" | sql_only | SQL → fact_businessplan | Target + tiến độ thực hiện |

---

## 6. Hướng dẫn triển khai

### Bước 1 — Setup môi trường
```bash
pip install -r requirements.txt
cp .env.example .env
# Điền GOOGLE_API_KEY, POSTGRES_URI vào .env
```

### Bước 2 — Build Vector Store từ tài liệu nội bộ
```bash
python scripts/build_vectorstore.py
```

### Bước 3 — Khởi động backend
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Bước 4 — Khởi động frontend
```bash
streamlit run app/streamlit_app.py
```

### Bước 5 (Production) — Docker Compose
```bash
docker-compose up -d
```

---

## 7. Dependencies

```txt
# requirements.txt
fastapi>=0.111.0
uvicorn>=0.29.0
streamlit>=1.34.0
langchain>=0.2.0
langchain-google-genai>=1.0.0
langchain-community>=0.2.0
langgraph>=0.1.0
chromadb>=0.5.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
unstructured>=0.14.0
pandas>=2.1.0
pydantic>=2.7.0
python-dotenv>=1.0.0
```

---

## 8. KPIs Đánh giá thành công

| Metric | Target |
|:---|:---|
| Câu trả lời chính xác (so với Dashboard) | > 90% |
| Thời gian phản hồi (P95) | < 8 giây |
| Tỷ lệ SQL query chạy thành công | > 85% |
| Mức độ hài lòng CEO (Survey 1-5) | ≥ 4.0 |
| Số câu hỏi tự phục vụ (không cần hỏi team) | Tăng 50% sau 3 tháng |
