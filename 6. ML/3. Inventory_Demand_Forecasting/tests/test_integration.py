import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.integration import export_to_fact_inventory_forecast, export_to_fact_reorder_recommendations

def test_export_forecast():
    forecast_df = pd.DataFrame({
        'unique_id': ['A', 'B'],
        'ds': pd.to_datetime(['2023-01-01', '2023-01-01']),
        'LGBMRegressor': [10.5, 20.0],
        'LGBMRegressor-lo-95': [5.0, 15.0],
        'LGBMRegressor-hi-95': [15.0, 25.0]
    })
    
    res = export_to_fact_inventory_forecast(forecast_df)
    
    assert 'forecast_date' in res.columns
    assert 'item_code' in res.columns
    assert 'point_forecast' in res.columns
    assert 'generated_at' in res.columns
    assert res['item_code'].iloc[0] == 'A'
    assert 'lower_bound_95' in res.columns

def test_export_reorder():
    opt_df = pd.DataFrame({
        'SKU': ['A'],
        'Nhu Cầu TB/Ngày': [10],
        'Tồn kho An toàn (SS)': [5],
        'Điểm Báo Động (ROP)': [55],
        'Số Lượng Nhập Tối Ưu (EOQ)': [100]
    })
    
    current_date = pd.Timestamp('2023-01-01')
    res = export_to_fact_reorder_recommendations(opt_df, current_date)
    
    assert 'item_code' in res.columns
    assert 'reorder_point' in res.columns
    assert 'recommendation_date' in res.columns
    assert res['recommendation_date'].iloc[0] == current_date
