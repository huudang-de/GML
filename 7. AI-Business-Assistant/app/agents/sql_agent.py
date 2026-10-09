import os
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
import sqlalchemy

SCHEMA_CONTEXT = """
Bạn là một chuyên gia phân tích dữ liệu (Data Analyst). Hãy viết câu lệnh SQL (PostgreSQL) để trả lời câu hỏi của người dùng.
Chỉ trả về DUY NHẤT câu lệnh SQL, KHÔNG giải thích, KHÔNG bọc trong markdown (```sql).

Các bảng trong schema 'silver':
- fact_balancesheet(indicator_code, ending_balance, beginning_balance, reporting_date): CĐKT (B01-DN_xxx)
- fact_incomestatement(indicator_code, indicator_name, current_period_amount, previous_period_amount, month): KQKD (B02-DN_xxx)
- fact_cashflow(account_no, posting_date, debit_amount, credit_amount, debit_balance, credit_balance, partner_code): Sổ cái
- fact_inventory_balance(warehouse_code, product_code, ending_quantity, ending_value, snapshot_date): Tồn kho
- fact_accountsreceivable(partner_code, invoice_date, debit_amount, credit_amount, ending_debit_balance, ending_credit_balance): Phải thu
- fact_businessplan(indicator_code, month, target_amount): Kế hoạch kinh doanh
- dim_partner(partner_code, partner_name): Danh sách đối tác
- dim_product(product_code, product_name, product_category): Danh sách sản phẩm (tương đương dim_item)
- dim_reportitem(item_code, item_name, report_type): Danh mục các chỉ tiêu báo cáo


Lưu ý:
- Luôn giới hạn kết quả bằng LIMIT 100
- Dùng tiếng Việt trong alias cột
- Số tiền là VNĐ.

Câu hỏi: {question}

Lỗi từ lần chạy trước (nếu có - hãy sửa lỗi này trong câu lệnh mới): {sql_error}
"""

class SQLAgent:
    def __init__(self):
        postgres_uri = os.environ.get("POSTGRES_URI", "postgresql://user:pass@localhost/gml")
        self.db = SQLDatabase.from_uri(postgres_uri, schema="silver")
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        
        self.prompt = ChatPromptTemplate.from_template(SCHEMA_CONTEXT)
        self.chain = self.prompt | self.llm | StrOutputParser()
        
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(dict)

        workflow.add_node("generate_sql", self.generate_sql)
        workflow.add_node("execute_sql", self.execute_sql)

        workflow.set_entry_point("generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        
        workflow.add_conditional_edges(
            "execute_sql",
            self.should_retry,
            {
                "retry": "generate_sql",
                "end": END
            }
        )

        return workflow.compile()

    def generate_sql(self, state: dict) -> dict:
        query = state["query"]
        sql_error = state.get("sql_error", "")
        
        # 1. Generate SQL
        sql_query = self.chain.invoke({
            "question": query, 
            "sql_error": sql_error
        })
        
        # Clean up sql_query if it contains markdown formatting
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        if sql_query.startswith("SQLQuery:"):
            sql_query = sql_query[9:].strip()
            
        return {**state, "sql_query": sql_query}

    def execute_sql(self, state: dict) -> dict:
        sql_query = state.get("sql_query", "")
        retries = state.get("retries", 0)

        try:
            # 2. Execute SQL
            sql_result = str(self.db.run(sql_query))
            
            # Success: Clear error and return result
            return {
                **state, 
                "sql_result": sql_result,
                "sql_error": "" 
            }
        except Exception as e:
            # Error: Save error and increment retries
            return {
                **state,
                "sql_result": "",
                "sql_error": str(e),
                "retries": retries + 1
            }

    def should_retry(self, state: dict) -> str:
        sql_error = state.get("sql_error", "")
        retries = state.get("retries", 0)
        
        if sql_error and retries < 3:
            return "retry"
        else:
            return "end"

    def run(self, state: dict) -> dict:
        # Initialize state for this sub-graph
        sub_state = {
            **state,
            "sql_error": "",
            "retries": 0,
            "sql_query": "",
            "sql_result": ""
        }
        
        # Run the self-healing workflow
        final_state = self.graph.invoke(sub_state)
        
        # If it failed even after retries, format the error nicely
        if final_state.get("sql_error"):
            final_state["sql_result"] = f"Error after {final_state['retries']} retries: {final_state['sql_error']}"
            
        return final_state
