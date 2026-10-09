from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import os

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
        postgres_uri = os.environ.get("POSTGRES_URI", "postgresql://user:pass@localhost/gml")
        self.db = SQLDatabase.from_uri(postgres_uri, schema="silver")
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
            "sql_query": result.get("intermediate_steps", [{}])[-1].get("query") if result.get("intermediate_steps") else None
        }
