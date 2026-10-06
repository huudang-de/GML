import pandas as pd

def aggregate_demand(df: pd.DataFrame, freq: str = 'W') -> pd.DataFrame:
    """
    Gom nhóm dữ liệu xuất kho theo tần suất thời gian (freq).
    freq: 'D' (ngày) hoặc 'W' (tuần).
    """
    df = df.copy()
    
    # Đảm bảo cột posting_date là datetime
    if 'posting_date' in df.columns:
        df['posting_date'] = pd.to_datetime(df['posting_date'])
    else:
        raise ValueError("DataFrame thiếu cột 'posting_date'")
        
    if 'item_code' not in df.columns or 'quantity' not in df.columns:
        raise ValueError("DataFrame thiếu cột 'item_code' hoặc 'quantity'")
        
    # Tạo chuỗi datetime period hoặc resample
    # Đưa về Timestamp của ngày đầu tiên trong chu kỳ (ví dụ Thứ 2 của tuần)
    if freq == 'W':
        df['ds'] = df['posting_date'] - pd.to_timedelta(df['posting_date'].dt.dayofweek, unit='d')
    elif freq == 'D':
        df['ds'] = df['posting_date'].dt.floor('D')
    else:
        df['ds'] = df['posting_date'].dt.to_period(freq).dt.to_timestamp()
        
    # Gom nhóm
    agg_df = df.groupby(['item_code', 'ds'])['quantity'].sum().reset_index()
    
    # Chuẩn hóa cột sang định dạng Nixtla
    agg_df = agg_df.rename(columns={
        'item_code': 'unique_id',
        'quantity': 'y'
    })
    
    # Đảm bảo sắp xếp đúng
    agg_df = agg_df.sort_values(by=['unique_id', 'ds']).reset_index(drop=True)
    
    return agg_df

def load_outward_data_mock():
    """Mock dữ liệu xuất kho để chạy thử nghiệm"""
    pass
