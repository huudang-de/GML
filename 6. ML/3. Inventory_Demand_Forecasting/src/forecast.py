import pandas as pd
from typing import List
from mlforecast import MLForecast
from utilsforecast.losses import mape, rmse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.feature_engineering import get_feature_pipeline

from mlforecast.utils import PredictionIntervals

def train_and_predict(df: pd.DataFrame, h: int = 8, freq: str = 'D', levels: List[int] = [95]) -> pd.DataFrame:
    """
    Huấn luyện Global Model và dự báo tương lai.
    Xuất ra Point forecast và Khoảng tin cậy (levels) để tính Safety Stock.
    """
    mlf = get_feature_pipeline(freq=freq)
    
    # Fit mô hình với prediction_intervals
    mlf.fit(df, static_features=[], prediction_intervals=PredictionIntervals(n_windows=3, h=h))
    
    # Predict tương lai
    forecasts = mlf.predict(h, level=levels)
    
    # Đảm bảo dự báo không xuất hiện số âm
    if 'LGBMRegressor' in forecasts.columns:
        forecasts['LGBMRegressor'] = forecasts['LGBMRegressor'].clip(lower=0)
        for level in levels:
            lo_col = f'LGBMRegressor-lo-{level}'
            if lo_col in forecasts.columns:
                forecasts[lo_col] = forecasts[lo_col].clip(lower=0)
    
    return forecasts

def evaluate_cross_validation(df: pd.DataFrame, h: int = 4, n_windows: int = 3, freq: str = 'D') -> pd.DataFrame:
    """
    Đánh giá mô hình bằng Walk-Forward Time-Series Cross Validation.
    """
    mlf = get_feature_pipeline(freq=freq)
    
    cv_df = mlf.cross_validation(
        df=df,
        n_windows=n_windows,
        h=h,
        step_size=h,
        static_features=[]
    )
    
    # Cắt ngọn số âm cho kết quả CV
    if 'LGBMRegressor' in cv_df.columns:
        cv_df['LGBMRegressor'] = cv_df['LGBMRegressor'].clip(lower=0)
        
    return cv_df

def calculate_metrics(cv_df: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán metrics (MAPE, RMSE) từ kết quả CV.
    """
    from utilsforecast.evaluation import evaluate
    
    # Thư viện utilsforecast tự động groupby unique_id
    metrics_df = evaluate(
        cv_df,
        metrics=[mape, rmse],
        models=['LGBMRegressor']
    )
    
    return metrics_df
