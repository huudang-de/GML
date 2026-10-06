import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.forecast import train_and_predict, evaluate_cross_validation, calculate_metrics

def generate_mock_data():
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    
    df1 = pd.DataFrame({
        'unique_id': 'SKU_1',
        'ds': dates,
        'y': np.random.randint(10, 50, size=50)
    })
    
    df2 = pd.DataFrame({
        'unique_id': 'SKU_2',
        'ds': dates,
        'y': np.random.randint(20, 60, size=50)
    })
    
    return pd.concat([df1, df2], ignore_index=True)

def test_predict_horizon_shape():
    df = generate_mock_data()
    # 2 SKU, h=5 -> output 10 dòng
    preds = train_and_predict(df, h=5, freq='D', levels=[95])
    assert len(preds) == 10
    assert set(preds['unique_id'].unique()) == {'SKU_1', 'SKU_2'}

def test_confidence_intervals():
    df = generate_mock_data()
    preds = train_and_predict(df, h=3, freq='D', levels=[80, 95])
    
    assert 'LGBMRegressor' in preds.columns
    assert 'LGBMRegressor-lo-80' in preds.columns
    assert 'LGBMRegressor-hi-80' in preds.columns
    assert 'LGBMRegressor-lo-95' in preds.columns
    assert 'LGBMRegressor-hi-95' in preds.columns

def test_cross_validation_windows():
    df = generate_mock_data()
    # 2 SKU, h=2, n_windows=2 -> 2 * 2 * 2 = 8 dòng
    cv_res = evaluate_cross_validation(df, h=2, n_windows=2, freq='D')
    
    assert len(cv_res) == 8
    assert 'cutoff' in cv_res.columns
    assert cv_res['cutoff'].nunique() == 2

def test_metrics_calculation():
    df = generate_mock_data()
    cv_res = evaluate_cross_validation(df, h=2, n_windows=2, freq='D')
    
    metrics = calculate_metrics(cv_res)
    assert 'unique_id' in metrics.columns
    assert 'metric' in metrics.columns
    assert 'LGBMRegressor' in metrics.columns
    assert metrics['unique_id'].nunique() == 2 # 2 SKU
