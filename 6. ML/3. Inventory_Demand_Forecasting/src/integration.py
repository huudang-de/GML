import pandas as pd
from datetime import datetime

def export_to_fact_inventory_forecast(forecast_df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn bị dữ liệu cho bảng silver.fact_inventory_forecast.
    Input: Bảng dự báo có unique_id, ds, LGBMRegressor, lo-95, hi-95
    Output: DataFrame chuẩn hóa schema Database.
    """
    df = forecast_df.copy()
    df.rename(columns={
        'ds': 'forecast_date',
        'unique_id': 'item_code',
        'LGBMRegressor': 'point_forecast',
        'LGBMRegressor-lo-95': 'lower_bound_95',
        'LGBMRegressor-hi-95': 'upper_bound_95'
    }, inplace=True)
    
    df['generated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Chỉ giữ lại các cột cần thiết
    cols_to_keep = ['forecast_date', 'item_code', 'point_forecast', 'lower_bound_95', 'upper_bound_95', 'generated_at']
    cols = [c for c in cols_to_keep if c in df.columns]
    
    return df[cols]

def export_to_fact_reorder_recommendations(opt_df: pd.DataFrame, current_date: pd.Timestamp) -> pd.DataFrame:
    """
    Chuẩn bị dữ liệu cho bảng silver.fact_reorder_recommendations.
    Input: DataFrame chứa output tối ưu (Pha 4).
    """
    df = opt_df.copy()
    mapping = {
        'SKU': 'item_code',
        'Nhu Cầu TB/Ngày': 'avg_daily_demand',
        'Tồn kho An toàn (SS)': 'safety_stock',
        'Điểm Báo Động (ROP)': 'reorder_point',
        'Số Lượng Nhập Tối Ưu (EOQ)': 'economic_order_quantity',
        'Thời gian Giao (Ngày)': 'lead_time_days'
    }
    
    for old_col, new_col in mapping.items():
        if old_col in df.columns:
            df.rename(columns={old_col: new_col}, inplace=True)
            
    df['recommendation_date'] = current_date
    df['generated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return df
