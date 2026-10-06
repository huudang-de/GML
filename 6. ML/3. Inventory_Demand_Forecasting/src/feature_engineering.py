import pandas as pd
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean, RollingStd
from lightgbm import LGBMRegressor

def get_feature_pipeline(freq='D'):
    """
    Tạo MLForecast pipeline để tự động Feature Engineering.
    Chưa fit mô hình, chỉ định nghĩa cấu trúc để trích xuất đặc trưng.
    """
    if freq == 'D':
        lags = [1, 7, 14, 28]
        lag_transforms = {
            1: [RollingMean(window_size=7), RollingMean(window_size=14), RollingStd(window_size=7)]
        }
        date_features = ['dayofweek', 'month']
    elif freq == 'W' or freq.startswith('W'):
        lags = [1, 2, 4, 12]
        lag_transforms = {
            1: [RollingMean(window_size=4), RollingMean(window_size=12)]
        }
        date_features = ['month', 'quarter']
    else:
        raise ValueError("Chỉ hỗ trợ freq = 'D' hoặc 'W'")
        
    # Tạo dummy model để khởi tạo MLForecast. 
    # Ở Pha 2 này chúng ta chỉ dùng MLForecast như một Feature Engineer Tool.
    models = [LGBMRegressor(random_state=42, verbose=-1)]
    
    mlf = MLForecast(
        models=models,
        freq=freq,
        lags=lags,
        lag_transforms=lag_transforms,
        date_features=date_features,
        num_threads=1
    )
    
    return mlf

def add_exogenous_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo biến ngoại sinh (Exogenous Variables).
    Bóc tách các ngày lễ/sự kiện đặc biệt.
    """
    df = df.copy()
    if 'ds' not in df.columns:
        raise ValueError("Cột 'ds' không tồn tại")
        
    df['ds'] = pd.to_datetime(df['ds'])
    
    # Ví dụ: Mặc định ngày 1/1 và 2/9 là ngày lễ
    is_new_year = (df['ds'].dt.month == 1) & (df['ds'].dt.day == 1)
    is_national_day = (df['ds'].dt.month == 9) & (df['ds'].dt.day == 2)
    
    df['is_holiday'] = (is_new_year | is_national_day).astype(int)
    
    return df
