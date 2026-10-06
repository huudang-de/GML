import pandas as pd
import numpy as np
import lightgbm as lgb
from src.scoring import RiskScorer

def test_scoring_schema_and_mapping():
    """Kiểm tra DataFrame Output có đủ cột cho Power BI và Màu sắc chính xác không"""
    # Tạo dummy model
    X = np.random.rand(10, 3)
    y = np.random.choice([0, 1, 2], 10)
    model = lgb.LGBMClassifier(random_state=42, verbose=-1)
    model.fit(X, y)
    
    # Tạo cỗ máy chấm điểm
    scorer = RiskScorer(model)
    
    # Chấm điểm 3 khách hàng giả định
    df_features = pd.DataFrame(np.random.rand(3, 3))
    customer_ids = ['CUST-001', 'CUST-002', 'CUST-003']
    
    df_output = scorer.score_active_customers(df_features, customer_ids)
    
    # Kịch bản 1: Kiểm tra Schema có đủ 5 cột bắt buộc
    expected_columns = ['customer_id', 'score_date', 'risk_badge', 'default_probability', 'ui_color']
    assert list(df_output.columns) == expected_columns, "Bảng Output bị thiếu cột cho Database!"
    
    # Kịch bản 2: Kiểm tra Ánh xạ Màu sắc
    for _, row in df_output.iterrows():
        if row['risk_badge'] == 'High Risk':
            assert row['ui_color'] == '#FF4444', "Lỗi nghiêm trọng: Cảnh báo High Risk sai màu UI!"
        elif row['risk_badge'] == 'Low Risk':
            assert row['ui_color'] == '#00C851', "Cảnh báo Low Risk sai màu UI!"
