import numpy as np
import pytest
from src.train import get_models

def test_model_output_shape():
    """Kiểm tra Output của hàm dự báo xác suất (predict_proba) phải có hình dạng (N_samples, 3)"""
    X = np.random.rand(20, 5)
    y = np.random.choice([0, 1, 2], 20)
    
    models = get_models()
    lgbm = models['LightGBM (Champion)']
    
    # Train tạm
    lgbm.fit(X, y)
    
    # Lấy xác suất
    probs = lgbm.predict_proba(X)
    
    # Kiểm tra shape (20 dòng, 3 nhãn)
    assert probs.shape == (20, 3), "Xác suất xuất ra phải là một ma trận kích thước (N, 3)."
    
def test_prob_sum_to_one():
    """Tổng của 3 xác suất (Low, Medium, High) của mỗi hóa đơn phải chính xác = 1.0"""
    X = np.random.rand(10, 5)
    y = np.random.choice([0, 1, 2], 10)
    
    models = get_models()
    lr = models['Logistic Regression (Baseline)']
    lr.fit(X, y)
    probs = lr.predict_proba(X)
    
    # Tính tổng xác suất theo hàng (axis=1)
    sums = np.sum(probs, axis=1)
    
    # Kiểm tra xem tổng có xấp xỉ 1.0 (sai số kỹ thuật siêu nhỏ) không
    np.testing.assert_allclose(sums, np.ones(10), err_msg="Tổng xác suất mỗi dòng (khách hàng) phải bằng 1.")
