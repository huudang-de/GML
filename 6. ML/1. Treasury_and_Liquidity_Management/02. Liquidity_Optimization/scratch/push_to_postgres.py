import os
import pandas as pd
from sqlalchemy import create_engine

def push_liquidity_to_postgres():
    print("🚀 Đang đọc file CSV Output của Liquidity Optimization...")
    
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'silver.fact_liquidity_actions.csv')
    
    if not os.path.exists(csv_path):
        print(f"❌ Không tìm thấy file: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    
    # Đẩy lên PostgreSQL
    engine = create_engine('sqlite:///../../../../gml_database.db')
    
    df.to_sql('fact_liquidity_actions', engine, schema=None, if_exists='replace', index=False)
    
    print("✅ Đã đẩy thành công [fact_liquidity_actions] lên Database (Silver Layer)!")

if __name__ == "__main__":
    push_liquidity_to_postgres()
