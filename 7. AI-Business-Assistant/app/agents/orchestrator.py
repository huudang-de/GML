from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agents.sql_agent import SQLAgent
from app.agents.rag_agent import RAGAgent
from app.agents.synthesizer import Synthesizer

class OrchestratorAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")
        self.sql_agent = SQLAgent()
        self.rag_agent = RAGAgent()
        self.synthesizer = Synthesizer(self.llm)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(dict)

        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("sql_lookup", self.sql_agent.run)
        graph.add_node("rag_lookup", self.rag_agent.run)
        graph.add_node("no_data_response", self._no_data_response)
        graph.add_node("sql_error_response", self._sql_error_response)
        graph.add_node("synthesize", self.synthesizer.run)

        graph.set_entry_point("classify_intent")

        graph.add_conditional_edges("classify_intent", self._route, {
            "sql_only":  "sql_lookup",
            "rag_only":  "rag_lookup",
            "both":      "sql_lookup",   # sql first, then rag in parallel
        })
        graph.add_conditional_edges("sql_lookup", self._after_sql, {
            "synthesize": "synthesize",
            "no_data": "no_data_response",
            "sql_error": "sql_error_response",
        })
        graph.add_edge("no_data_response", END)
        graph.add_edge("sql_error_response", END)
        graph.add_edge("rag_lookup", "synthesize")
        graph.add_edge("synthesize", END)

        return graph.compile()

    def _classify_intent(self, state: dict) -> dict:
        prompt = f"""
        Phân loại câu hỏi sau vào 1 trong 3 nhóm: "sql_only", "rag_only", "both"

        - sql_only: Câu hỏi cần số liệu cụ thể (doanh thu, tồn kho, công nợ, dòng tiền...)
        - rag_only: Câu hỏi về chính sách, quy trình, định nghĩa KPI, hướng dẫn sử dụng
        - both: Cần cả số liệu lẫn giải thích nghiệp vụ

        Câu hỏi: "{state['query']}"

        Trả lời chỉ 1 từ: sql_only | rag_only | both
        """
        response = self.llm.invoke(prompt)
        content = response.content
        intent = str(content[0].get("text", "")) if isinstance(content, list) else str(content)
        intent = intent.strip()
        return {**state, "intent": intent}

    def _route(self, state: dict) -> str:
        intent = state.get("intent", "both").lower()
        if "sql" in intent:
            return "sql_only"
        elif "rag" in intent:
            return "rag_only"
        else:
            return "both"

    def _after_sql(self, state: dict) -> str:
        status = state.get("sql_status")
        if status == "ok":
            return "synthesize"
        if status == "no_data":
            return "no_data"
        return "sql_error"

    @staticmethod
    def _no_data_response(state: dict) -> dict:
        return {
            **state,
            "answer_type": "no_data",
            "answer": (
                "Không có dữ liệu phù hợp với điều kiện bạn hỏi. "
                "Tôi không suy diễn hoặc ước tính số liệu khi truy vấn DW không trả bản ghi."
            ),
            "data": [],
            "row_count": 0,
        }

    @staticmethod
    def _sql_error_response(state: dict) -> dict:
        return {
            **state,
            "answer_type": "execution_error",
            "answer": (
                "Không thể lấy số liệu từ Data Warehouse cho câu hỏi này. "
                "Vui lòng kiểm tra lại điều kiện truy vấn hoặc thử lại sau."
            ),
            "data": [],
            "row_count": 0,
        }

    async def run(self, query: str, session_id: str) -> dict:
        state = {"query": query, "session_id": session_id}
        result = await self.graph.ainvoke(state)
        return result
