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
