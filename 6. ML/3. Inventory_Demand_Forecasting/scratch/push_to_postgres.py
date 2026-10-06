import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.optimize import calculate_reorder_point

def push_inventory_to_postgres():
    print("🚀 Đang khởi tạo Dữ liệu Inventory Forecast & Reorder...")
    
    # Giả lập dữ liệu Forecast của AI
    dates = pd.date_range(start="2026-10-01", periods=30)
    df_forecast = pd.DataFrame({
        'item_code': ['MDF-18MM'] * 30,
        'forecast_date': dates,
        'demand_mean': np.random.normal(50, 5, 30),
        'demand_lower_95': np.random.normal(40, 5, 30),
        'demand_upper_95': np.random.normal(60, 5, 30)
    })
    
    # Tính ROP & EOQ
    # Lead time = 7 days, holding cost = 1000, ordering cost = 500000
    df_reorder = pd.DataFrame([{
        'item_code': 'MDF-18MM',
        'lead_time_days': 7,
        'daily_demand_avg': 50,
        'demand_std_dev': 5,
        'rop': 50 * 7 + 1.65 * 5 * np.sqrt(7),
        'safety_stock': 1.65 * 5 * np.sqrt(7),
        'eoq': np.sqrt((2 * 50 * 30 * 500000) / 1000) # monthly approx
    }])
    
    # Đẩy lên PostgreSQL
    engine = create_engine('sqlite:///../../gml_database.db')
    
    df_forecast.to_sql('fact_inventory_forecast', engine, schema=None, if_exists='replace', index=False)
    df_reorder.to_sql('fact_reorder_recommendations', engine, schema=None, if_exists='replace', index=False)
    
    print("✅ Đã đẩy thành công [fact_inventory_forecast] và [fact_reorder_recommendations] lên Database (Silver Layer)!")

if __name__ == "__main__":
    push_inventory_to_postgres()
