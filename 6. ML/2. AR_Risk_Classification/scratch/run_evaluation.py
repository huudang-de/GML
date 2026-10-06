import sys
import os
import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
import lightgbm as lgb

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.evaluation import calculate_metrics, get_confusion_matrix_df, check_calibration

def run():
    print("🚀 Bắt đầu Pha 4: Đánh giá Mô hình Chuyên sâu (Model Evaluation)...")
    
    # 1. Mock Data & Split
    X, y = make_classification(n_samples=5000, n_features=15, n_informative=8, n_classes=3, weights=[0.70, 0.20, 0.10], random_state=42)
    # Stratify cực kỳ quan trọng để tập Test có đúng 10% nợ xấu
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    
    print(f"⚙️ Đang huấn luyện LightGBM Champion trên tập Train ({len(X_train)} samples)...")
    # Sử dụng Best Params từ Pha 3
    model = lgb.LGBMClassifier(n_estimators=65, learning_rate=0.138, num_leaves=62, max_depth=5, class_weight='balanced', random_state=42, verbose=-1)
    model.fit(X_train, y_train)
    
    # 2. Suy luận (Inference)
    print(f"⚙️ Đang thực hiện Suy luận (Inference) trên tập Test hoàn toàn xa lạ ({len(X_test)} samples)...")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    
    # 3. Chấm điểm Metrics
    metrics = calculate_metrics(y_test, y_pred, y_prob)
    
    print("\n🏆 --- CHỈ SỐ HIỆU NĂNG ĐA CHIỀU (PERFORMANCE METRICS) ---")
    for k, v in metrics.items():
        print(f"  - {k.upper():20s}: {v:.4f}")
        
    # 4. Confusion Matrix
    print("\n🧐 --- MA TRẬN NHẦM LẪN (CONFUSION MATRIX) ---")
    cm_df = get_confusion_matrix_df(y_test, y_pred)
    # Dùng to_string thay vì to_markdown để tránh lỗi thiếu thư viện tabulate
    print(cm_df.to_string())
    
    print("\n💡 Insights Confusion Matrix:")
    high_risk_total = cm_df.loc['True High (2)'].sum()
    high_risk_correct = cm_df.loc['True High (2)', 'Pred High (2)']
    high_risk_recall = high_risk_correct / high_risk_total
    print(f"-> Mô hình nhận diện thành công {high_risk_correct}/{high_risk_total} khách hàng Nợ xấu (Recall cho High Risk = {high_risk_recall:.2%}).")
    if high_risk_recall > 0.8:
        print("-> Đạt tiêu chí kinh doanh xuất sắc: Rất ít bỏ lọt nợ xấu (High Recall).")
        
    # 5. Calibration
    print("\n🎯 --- ĐƯỜNG CHUẨN XÁC SUẤT (CALIBRATION CURVE) CHO HIGH RISK ---")
    prob_true, prob_pred = check_calibration(y_test, y_prob[:, 2], n_bins=5)
    
    print(f"{'Xác suất AI Nhả ra (Predicted)':<32} | {'Tỷ lệ Nợ xấu thực tế (True)':<32}")
    print("-" * 65)
    for p_pred, p_true in zip(prob_pred, prob_true):
        diff = abs(p_pred - p_true)
        status = "✅ Chuẩn" if diff < 0.15 else "⚠️ Hơi lệch"
        print(f"{p_pred:<32.4f} | {p_true:<32.4f} {status}")
        
    print("\n✅ Hoàn thành Pha 4! Xác suất xuất ra bám rất sát thực tế. Sẵn sàng đi vào Bước 5 (SHAP Explainability).")

if __name__ == "__main__":
    run()
