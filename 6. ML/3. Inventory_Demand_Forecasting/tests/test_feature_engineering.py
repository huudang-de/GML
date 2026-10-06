import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.feature_engineering import get_feature_pipeline, add_exogenous_features

def test_add_exogenous_features():
    df = pd.DataFrame({
        'unique_id': ['A', 'A'],
        'ds': ['2023-01-01', '2023-01-02'],
        'y': [10, 20]
    })
    df_exo = add_exogenous_features(df)
    assert 'is_holiday' in df_exo.columns
    assert df_exo.loc[df_exo['ds'] == '2023-01-01', 'is_holiday'].values[0] == 1
    assert df_exo.loc[df_exo['ds'] == '2023-01-02', 'is_holiday'].values[0] == 0

def test_mlforecast_preprocess():
    df = pd.DataFrame({
        'unique_id': ['A']*30,
        'ds': pd.date_range('2023-01-01', periods=30, freq='D'),
        'y': np.arange(30)
    })
    
    mlf = get_feature_pipeline(freq='D')
    
    # Preprocess sinh ra Tabular Features
    df_features = mlf.preprocess(df)
    
    # Kiểm tra Lags (Độ trễ)
    assert 'lag1' in df_features.columns
    assert 'lag7' in df_features.columns
    assert 'lag14' in df_features.columns
    assert 'lag28' in df_features.columns
    
    # Kiểm tra Calendar features
    assert 'dayofweek' in df_features.columns
    assert 'month' in df_features.columns
    
    # Kiểm tra Lag transforms
    assert any('rolling_mean' in col for col in df_features.columns)
    assert any('rolling_std' in col for col in df_features.columns)
    
    # Kiểm tra NaN dropping (Lag lớn nhất là 28, nên sẽ drop 28 dòng đầu của time-series)
    # Vì time-series dài 30 ngày, trừ đi 28 -> df_features chỉ còn lại 2 dòng
    assert len(df_features) == 2
