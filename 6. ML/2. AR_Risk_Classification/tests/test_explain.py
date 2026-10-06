import numpy as np
import pandas as pd
import lightgbm as lgb
from src.explain import RiskExplainer

def test_shap_shape():
    """Kiểm tra ma trận SHAP values có bảo toàn kích thước của dữ liệu đầu vào không"""
    X = np.random.rand(15, 4)
    y = np.random.choice([0, 1, 2], 15)
    
    model = lgb.LGBMClassifier(random_state=42, verbose=-1)
    model.fit(X, y)
    
    explainer = RiskExplainer(model)
    shap_vals = explainer.get_shap_values(X)
    
    # Ở version mới, Multiclass có thể trả về array 3D (15, 4, 3) hoặc list [3 ma trận (15, 4)]
    if isinstance(shap_vals, list):
        assert len(shap_vals) == 3
        assert shap_vals[2].shape == (15, 4)
    else:
        # Nếu là array numpy
        assert len(shap_vals.shape) == 3, "SHAP values của multiclass phải có 3 chiều"
        assert shap_vals.shape == (15, 4, 3), "Kích thước array SHAP bị lệch so với dữ liệu gốc"
