import numpy as np
from src.evaluation import calculate_metrics, get_confusion_matrix_df

def test_metrics_range():
    """Kiểm tra các chỉ số đánh giá phải luôn nằm trong khoảng [0.0, 1.0]"""
    y_true = np.array([0, 1, 2, 0, 1, 2, 0, 0, 2])
    y_pred = np.array([0, 0, 2, 0, 1, 1, 0, 2, 2])
    
    # Tạo xác suất ảo (Tổng các cột = 1)
    y_prob = np.array([
        [0.8, 0.1, 0.1], [0.6, 0.3, 0.1], [0.1, 0.2, 0.7],
        [0.7, 0.2, 0.1], [0.2, 0.7, 0.1], [0.1, 0.8, 0.1],
        [0.9, 0.1, 0.0], [0.2, 0.1, 0.7], [0.0, 0.2, 0.8]
    ])
    
    metrics = calculate_metrics(y_true, y_pred, y_prob)
    
    assert 0 <= metrics['roc_auc_macro'] <= 1.0, "AUC nằm ngoài khoảng [0, 1]"
    assert 0 <= metrics['precision_macro'] <= 1.0, "Precision sai khoảng"
    assert 0 <= metrics['recall_macro'] <= 1.0, "Recall sai khoảng"
    assert 0 <= metrics['f1_macro'] <= 1.0, "F1-Score sai khoảng"

def test_confusion_matrix_shape():
    """Kiểm tra ma trận nhầm lẫn của bài toán 3 nhãn phải đúng chuẩn 3x3"""
    y_true = np.array([0, 1, 2, 0, 1, 2])
    y_pred = np.array([0, 0, 2, 0, 1, 1])
    
    df_cm = get_confusion_matrix_df(y_true, y_pred)
    assert df_cm.shape == (3, 3), "Confusion Matrix phải có kích thước 3x3 để đại diện cho Low, Medium, High"
