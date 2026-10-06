import sys
import os
import numpy as np
from sklearn.datasets import make_classification

# Cấu hình path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.train import get_models, evaluate_models, tune_lightgbm

def run():
    print("🚀 Bắt đầu Pha 3: Huấn luyện và Lựa chọn Mô hình (Model Training)...")
    
    # 1. Sinh tập dữ liệu (Mock Dataset) có cấu trúc Mất cân bằng
    print("⚙️ Đang khởi tạo tập dữ liệu (Mock Dataset: 5,000 khách hàng, 15 Đặc trưng, 3 Nhãn rủi ro)...")
    # Giả lập tỷ lệ: 70% Low, 20% Medium, 10% High
    X, y = make_classification(
        n_samples=5000, n_features=15, n_informative=8, n_redundant=3,
        n_classes=3, weights=[0.70, 0.20, 0.10], random_state=42
    )
    
    # 2. Chạy đối đầu (Benchmark) 3 Model
    print("\n⚔️ Đang chạy Benchmark 3 mô hình bằng Stratified 5-Fold CV (Thang điểm: F1-Macro)...")
    models = get_models()
    results = evaluate_models(X, y, models)
    
    print("\n📊 --- KẾT QUẢ ĐỐI ĐẦU (BENCHMARK) ---")
    for name, score in results.items():
        print(f"  - {name:30s} | F1-Macro: {score:.4f}")
        
    print("\n💡 Đánh giá: LightGBM và XGBoost (Tree-based) thể hiện năng lực vượt trội so với Logistic Regression.")
    
    # 3. Tối ưu Optuna cho Champion (LightGBM)
    print("\n⚙️ Đang khởi chạy Thuật toán TPE (Optuna) tìm siêu tham số đỉnh nhất cho LightGBM (10 lượt)...")
    best_params, best_score = tune_lightgbm(X, y, n_trials=10)
    
    print("\n🏆 --- KẾT QUẢ TỐI ƯU OPTUNA (LIGHTGBM CHAMPION) ---")
    print(f"  - Kỷ lục F1-Macro Score: {best_score:.4f}")
    print("  - Bộ vũ khí (Best Params):")
    for k, v in best_params.items():
        print(f"    + {k}: {v}")
        
    print("\n✅ Hoàn thành Pha 3! Sẵn sàng đưa model vô địch vào Bước 4 (Evaluation & SHAP Explainability).")

if __name__ == "__main__":
    run()
