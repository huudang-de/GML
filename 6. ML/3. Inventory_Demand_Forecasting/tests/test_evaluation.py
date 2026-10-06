import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.evaluation import evaluate_by_category, get_worst_performers

def test_category_aggregation():
    cv_df = pd.DataFrame({
        'unique_id': ['VAN-01', 'VAN-02', 'GIAY-01'],
        'ds': pd.to_datetime(['2023-01-01', '2023-01-01', '2023-01-01']),
        'y': [100, 200, 50],
        'LGBMRegressor': [90, 220, 50] # Sai số 10 (10%), 20 (10%), 0 (0%)
    })
    
    dim_item = pd.DataFrame({
        'unique_id': ['VAN-01', 'VAN-02', 'GIAY-01'],
        'category': ['Ván', 'Ván', 'Giấy']
    })
    
    cat_metrics = evaluate_by_category(cv_df, dim_item)
    
    # 2 Category: Ván, Giấy, x 3 metric (mape, mae, rmse) -> 6 dòng
    assert len(cat_metrics) == 6
    
    # Check MAPE của Ván
    mape_van = cat_metrics[(cat_metrics['category'] == 'Ván') & (cat_metrics['metric'] == 'mape')]['LGBMRegressor'].values[0]
    assert abs(mape_van - 0.1) < 1e-6 # (10% + 10%) / 2 = 10%
    
    # Check MAPE của Giấy
    mape_giay = cat_metrics[(cat_metrics['category'] == 'Giấy') & (cat_metrics['metric'] == 'mape')]['LGBMRegressor'].values[0]
    assert abs(mape_giay - 0.0) < 1e-6 

def test_missing_category_handling():
    cv_df = pd.DataFrame({
        'unique_id': ['NEW-999'],
        'ds': pd.to_datetime(['2023-01-01']),
        'y': [100],
        'LGBMRegressor': [90]
    })
    dim_item = pd.DataFrame({'unique_id': ['VAN-01'], 'category': ['Ván']})
    
    cat_metrics = evaluate_by_category(cv_df, dim_item)
    assert 'Unknown' in cat_metrics['category'].values

def test_worst_performers():
    metrics_df = pd.DataFrame({
        'unique_id': ['A', 'B', 'C', 'D', 'E'],
        'metric': ['mape']*5,
        'LGBMRegressor': [0.05, 0.10, 0.80, 0.20, 0.90] # 5%, 10%, 80%, 20%, 90%
    })
    
    worst_2 = get_worst_performers(metrics_df, top_n=2, metric_name='mape')
    assert len(worst_2) == 2
    assert worst_2.iloc[0]['unique_id'] == 'E' # 90%
    assert worst_2.iloc[1]['unique_id'] == 'C' # 80%
