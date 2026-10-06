import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.calibration import calibration_curve

def calculate_metrics(y_true, y_pred, y_prob):
    """Tính toán bộ Metrics đa lớp (Multi-class)"""
    # Bắt lỗi khi test với mẫu quá nhỏ chỉ có 1 class
    if len(np.unique(y_true)) == 1:
        return {'roc_auc_macro': 0, 'precision_macro': 0, 'recall_macro': 0, 'f1_macro': 0}
        
    auc = roc_auc_score(y_true, y_prob, multi_class='ovr', average='macro')
    precision = precision_score(y_true, y_pred, average='macro', zero_division=0)
    recall = recall_score(y_true, y_pred, average='macro', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
    
    return {
        'roc_auc_macro': auc,
        'precision_macro': precision,
        'recall_macro': recall,
        'f1_macro': f1
    }

def get_confusion_matrix_df(y_true, y_pred):
    """Tạo Confusion Matrix dạng Bảng (Pandas DataFrame) cho dễ đọc"""
    cm = confusion_matrix(y_true, y_pred)
    labels = ['Low (0)', 'Medium (1)', 'High (2)']
    
    if cm.shape == (3, 3):
        df_cm = pd.DataFrame(cm, index=[f'True {l}' for l in labels], columns=[f'Pred {l}' for l in labels])
        return df_cm
    return pd.DataFrame(cm)

def check_calibration(y_true, y_prob_class_high, n_bins=5):
    """
    Tính Calibration Curve cho riêng class High Risk (nhãn 2).
    """
    # Ép về bài toán Binary: 1 nếu là High Risk, 0 nếu không phải
    y_true_binary = (y_true == 2).astype(int)
    prob_true, prob_pred = calibration_curve(y_true_binary, y_prob_class_high, n_bins=n_bins, strategy='uniform')
    
    return prob_true, prob_pred
