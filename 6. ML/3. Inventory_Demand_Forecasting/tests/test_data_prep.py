import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_loader import aggregate_demand
from src.data_prep import fill_missing_dates, clip_outliers

def test_nixtla_columns_format():
    # Input
    df_raw = pd.DataFrame({
        'item_code': ['MDF-01', 'MDF-01'],
        'posting_date': ['2023-01-01', '2023-01-08'],
        'quantity': [10, 20]
    })
    
    df_agg = aggregate_demand(df_raw, freq='W')
    
    assert 'unique_id' in df_agg.columns
    assert 'ds' in df_agg.columns
    assert 'y' in df_agg.columns
    assert 'item_code' not in df_agg.columns
    
    assert pd.api.types.is_datetime64_any_dtype(df_agg['ds'])

def test_fill_missing_dates():
    # Giả định tuần 1 và tuần 3, thiếu tuần 2
    df = pd.DataFrame({
        'unique_id': ['MDF-01', 'MDF-01'],
        'ds': pd.to_datetime(['2023-01-02', '2023-01-16']), # 2023-01-02 là T2. Tuần 3 là 16 (cách 14 ngày)
        'y': [10.0, 20.0]
    })
    
    df_filled = fill_missing_dates(df, freq='W')
    
    assert len(df_filled) == 3
    assert df_filled['y'].isna().sum() == 0
    # Check dòng mới thêm vào có giá trị y = 0
    missing_date = pd.to_datetime('2023-01-09')
    assert df_filled.loc[df_filled['ds'] == missing_date, 'y'].values[0] == 0.0

def test_outlier_clipping():
    # Dữ liệu MFC-02 thường từ 10-20. Có 1 dòng 5000.
    data = [10, 12, 15, 13, 11, 14, 5000, 15, 12, 10]
    df = pd.DataFrame({
        'unique_id': ['MFC-02'] * 10,
        'ds': pd.date_range('2023-01-02', periods=10, freq='W-MON'),
        'y': data
    })
    
    df_clipped = clip_outliers(df, multiplier=1.5)
    
    assert len(df_clipped) == 10
    
    # 5000 phải bị cắt giảm
    max_y = df_clipped['y'].max()
    assert max_y < 5000
    assert max_y > 15 # Upper bound sẽ lớn hơn 15 một chút

def test_no_negative_demand():
    df = pd.DataFrame({
        'unique_id': ['GIAY-01'],
        'ds': pd.to_datetime(['2023-01-02']),
        'y': [-5.0]
    })
    
    df_filled = fill_missing_dates(df, freq='W')
    assert df_filled['y'].min() == 0.0
