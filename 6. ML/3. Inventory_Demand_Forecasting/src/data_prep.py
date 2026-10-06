import pandas as pd
import numpy as np

def fill_missing_dates(df: pd.DataFrame, freq: str = 'W') -> pd.DataFrame:
    """
    Điền các ngày/tuần bị thiếu trong chuỗi thời gian của từng unique_id bằng 0.
    Cấu trúc đầu vào: ['unique_id', 'ds', 'y']
    """
    if not {'unique_id', 'ds', 'y'}.issubset(df.columns):
        raise ValueError("Dữ liệu đầu vào phải có các cột: 'unique_id', 'ds', 'y'")
        
    df = df.copy()
    df['ds'] = pd.to_datetime(df['ds'])
    
    # Tạo một dataframe chứa tất cả các khoảng thời gian đầy đủ cho TỪNG unique_id
    full_ranges = []
    
    for uid, group in df.groupby('unique_id'):
        min_date = group['ds'].min()
        max_date = group['ds'].max()
        
        # Tạo chuỗi thời gian liên tục từ min_date đến max_date
        # freq='W-MON' là để các ngày luôn rơi vào thứ 2 (đầu tuần) nếu chọn W
        date_freq = 'W-MON' if freq == 'W' else freq
        full_dates = pd.date_range(start=min_date, end=max_date, freq=date_freq)
        
        temp_df = pd.DataFrame({
            'unique_id': uid,
            'ds': full_dates
        })
        full_ranges.append(temp_df)
        
    full_df = pd.concat(full_ranges, ignore_index=True)
    
    # Merge lại với dataframe gốc
    result_df = pd.merge(full_df, df, on=['unique_id', 'ds'], how='left')
    
    # Fill NaN = 0
    result_df['y'] = result_df['y'].fillna(0)
    
    # Đảm bảo không có số âm (phòng ngừa lỗi xuất kho âm)
    result_df['y'] = result_df['y'].clip(lower=0)
    
    return result_df

def clip_outliers(df: pd.DataFrame, multiplier: float = 1.5) -> pd.DataFrame:
    """
    Xử lý outlier bằng kỹ thuật Cắt ngọn (Clipping) theo IQR, áp dụng riêng cho từng unique_id.
    """
    df = df.copy()
    
    def cap_group(group):
        q1 = group['y'].quantile(0.25)
        q3 = group['y'].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + multiplier * iqr
        
        if upper_bound <= 0 and group['y'].max() > 0:
             upper_bound = group['y'].max() # Không cắt nếu quartile bị 0 hết
             
        # Gán lại giá trị y
        group_y = group['y'].copy()
        group_y = group_y.clip(upper=upper_bound)
        group['y'] = group_y
        return group
        
    # Apply capping cho từng SKU
    capped_df = df.groupby('unique_id', group_keys=False).apply(cap_group)
    
    return capped_df
