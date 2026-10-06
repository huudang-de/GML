import numpy as np
import pandas as pd
import shap

class RiskExplainer:
    def __init__(self, model):
        """Khởi tạo TreeExplainer từ model dạng cây (LightGBM/XGBoost)"""
        self.model = model
        self.explainer = shap.TreeExplainer(model)
        
    def get_shap_values(self, X):
        """Tính toán giá trị SHAP cho toàn bộ Dataset"""
        return self.explainer.shap_values(X)
        
    def get_global_importance(self, X, feature_names):
        """
        Trích xuất Global Feature Importance.
        """
        shap_vals = self.get_shap_values(X)
        
        if isinstance(shap_vals, list):
            shap_abs = np.mean([np.abs(sv).mean(axis=0) for sv in shap_vals], axis=0)
        elif len(shap_vals.shape) == 3: # Array (n_samples, n_features, n_classes)
            shap_abs = np.abs(shap_vals).mean(axis=(0, 2))
        else:
            shap_abs = np.abs(shap_vals).mean(axis=0)
            
        df_imp = pd.DataFrame({
            'Feature': feature_names,
            'Global_Importance': shap_abs
        }).sort_values(by='Global_Importance', ascending=False)
        return df_imp
        
    def explain_local_customer(self, X_row, feature_names, class_index=2):
        """
        Giải thích vi mô (Local) cho 1 Khách hàng cụ thể.
        """
        shap_vals = self.get_shap_values(X_row)
        
        if isinstance(shap_vals, list):
            sv = shap_vals[class_index][0]
        elif len(shap_vals.shape) == 3:
            sv = shap_vals[0, :, class_index]
        else:
            sv = shap_vals[0]
            
        base_value = self.explainer.expected_value
        if isinstance(base_value, list) or isinstance(base_value, np.ndarray):
            base_value = base_value[class_index]
            
        df_local = pd.DataFrame({
            'Feature': feature_names,
            'Actual_Value': X_row.values[0] if isinstance(X_row, pd.DataFrame) else X_row[0],
            'SHAP_Contribution': sv
        })
        
        df_local = df_local.sort_values(by='SHAP_Contribution', key=abs, ascending=False)
        return df_local, base_value
