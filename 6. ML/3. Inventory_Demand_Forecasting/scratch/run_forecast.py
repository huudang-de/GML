import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.forecast import train_and_predict, evaluate_cross_validation, calculate_metrics

def run():
    print("🚀 Bắt đầu Pha 3: Huấn luyện Mô hình & Dự báo (Demand Forecasting)...")
    
    # 1. Tạo Mock Data chuẩn cho 2 loại hàng hóa
    print("\n⚙️ Bước 1: Khởi tạo dữ liệu giả lập cho 2 SKU (VAN-01 và NEP-02)...")
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    
    # VAN-01: Bán ổn định (Stationary)
    df_van = pd.DataFrame({
        'unique_id': 'VAN-01',
        'ds': dates,
        'y': np.random.normal(loc=50, scale=5, size=100)
    })
    
    # NEP-02: Bán tăng dần (Trending)
    trend = np.linspace(10, 80, 100)
    df_nep = pd.DataFrame({
        'unique_id': 'NEP-02',
        'ds': dates,
        'y': trend + np.random.normal(loc=0, scale=3, size=100)
    })
    
    df = pd.concat([df_van, df_nep], ignore_index=True)
    df['y'] = df['y'].clip(lower=0).astype(int)
    
    # 2. Time-Series Cross Validation
    print("\n⚙️ Bước 2: Chạy Walk-Forward Cross Validation (Trượt thời gian) để đánh giá...")
    print("   -> Đang train Global Model (LightGBM) học chéo cả 2 mã...")
    cv_df = evaluate_cross_validation(df, h=7, n_windows=3, freq='D')
    
    print("\n📊 Bảng kết quả Metrics (MAPE, RMSE):")
    metrics_df = calculate_metrics(cv_df)
    print(metrics_df)
    
    # 3. Dự báo Tương lai (Future Forecasting)
    print("\n⚙️ Bước 3: Dự báo thực tế cho 7 ngày tiếp theo...")
    forecasts = train_and_predict(df, h=7, freq='D', levels=[95])
    
    print("\n🧐 Kết quả dự báo (Kèm dải tin cậy 95%):")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    # Lấy thử 3 ngày của VAN-01 và 3 ngày của NEP-02
    print(pd.concat([forecasts.head(3), forecasts.tail(3)]))
    
    print("\n✅ Hoàn thành Pha 3! Sẵn sàng đưa khoảng tin cậy (lo-hi) sang Pha 4 để tính Tồn kho an toàn (Safety Stock).")

if __name__ == "__main__":
    run()
