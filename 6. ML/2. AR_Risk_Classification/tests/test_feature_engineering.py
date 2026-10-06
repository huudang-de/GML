import pandas as pd
import numpy as np
import pytest
from src.feature_engineering import aggregate_customer_features, get_balanced_class_weights

def test_customer_aggregation():
    df = pd.DataFrame({
        'customer_code': ['C001', 'C001', 'C002'],
        'invoice_no': ['INV1', 'INV2', 'INV3'],
        'days_overdue': [0, 30, 90],
        'risk_label': [0, 1, 2],
        'invoice_amount': [1000, 2000, 5000]
    })
    
    res = aggregate_customer_features(df)
    
    # Kiểm tra C001
    c1 = res[res['customer_code'] == 'C001'].iloc[0]
    assert c1['avg_days_overdue'] == 15, "Sai trung bình ngày trễ"
    assert c1['pct_on_time'] == 0.5, "Sai tỷ lệ đúng hạn"
    assert c1['target_risk_label'] == 1, "Sai Target Label (Phải lấy max risk)"
    
    # Kiểm tra C002
    c2 = res[res['customer_code'] == 'C002'].iloc[0]
    assert c2['max_days_overdue'] == 90
    assert c2['target_risk_label'] == 2

def test_class_weights():
    # Giả lập tập nhãn mất cân bằng: Đa số là 0, thiểu số là 2
    y = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 2])
    weights = get_balanced_class_weights(y)
    
    assert weights[2] > weights[0], "Trọng số của class thiểu số (2) phải lớn hơn class đa số (0)"
