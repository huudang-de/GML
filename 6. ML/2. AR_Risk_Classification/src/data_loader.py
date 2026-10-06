import pandas as pd
from sqlalchemy import create_engine

class PostgresDataLoader:
    def __init__(self, connection_string="postgresql://postgres:postgres@localhost:5432/minhlong_dw"):
        self.engine = create_engine(connection_string)

    def fetch_ar_data(self):
        """Lấy dữ liệu hóa đơn phải thu và thông tin khách hàng từ Silver layer"""
        query = """
            SELECT 
                ar.invoice_no,
                ar.customer_code,
                p.partner_name,
                ar.invoice_date,
                ar.due_date,
                ar.payment_date,
                ar.debit_amount as invoice_amount
            FROM silver.fact_accountsreceivable ar
            LEFT JOIN silver.dim_partner p ON ar.customer_code = p.partner_code
            WHERE ar.debit_amount > 0
        """
        df = pd.read_sql(query, self.engine)
        return df
