import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.feature_engineering import get_feature_pipeline, add_exogenous_features

def run():
    print("🚀 Bắt đầu Pha 2: Trích xuất Đặc trưng (Feature Engineering) với Nixtla MLForecast...")
    
    # 1. Tạo Mock Data chuẩn
    print("\n⚙️ Đang tạo dữ liệu chuỗi thời gian liên tục (Tương đương Output của Pha 1)...")
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=40, freq='D')
    df = pd.DataFrame({
        'unique_id': 'VAN-01',
        'ds': dates,
        'y': np.random.randint(10, 50, size=40)
    })
    
    # 2. Thêm Exogenous features
    print("\n⚙️ Bước 1: Tiền xử lý các Biến ngoại sinh (Exogenous Variables)...")
    df = add_exogenous_features(df)
    print("Đã chèn thêm cột 'is_holiday':")
    print(df[['ds', 'y', 'is_holiday']].head(3))
    
    # 3. MLForecast Pipeline
    print("\n⚙️ Bước 2: Cấu hình MLForecast Pipeline (Lags, Rolling Means, Calendar)...")
    mlf = get_feature_pipeline(freq='D')
    print("Đã khởi tạo xong. Đang nạp dữ liệu để trích xuất Tabular Data...")
    
    # 4. Preprocess
    print("\n⚙️ Bước 3: Chạy method .preprocess() để chiêm ngưỡng Dữ liệu Bảng (Tabular)...")
    df_features = mlf.preprocess(df, static_features=[])
    
    print(f"\n📊 [KẾT QUẢ] Kích thước Ma trận Đặc trưng: {df_features.shape}")
    print(f"Số dòng ban đầu: {len(df)} -> Còn lại {len(df_features)} (Hệ thống tự động Drop NaN ở các dòng bị mất dữ liệu trễ)")
    
    print("\n🧐 Cùng xem qua 5 dòng đầu tiên của Bảng Dữ liệu Học máy:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    print(df_features.head())
    
    print("\n✅ Hoàn thành Pha 2! Data đã được nhào nặn hoàn hảo để đút vào thuật toán LightGBM.")

if __name__ == "__main__":
    run()
