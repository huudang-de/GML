import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_loader import aggregate_demand
from src.data_prep import fill_missing_dates, clip_outliers

def run():
    print("🚀 Bắt đầu Pha 1: Chuẩn bị Dữ liệu (Data Preparation) cho Nixtla MLForecast...")
    
    # 1. Tạo Mock Data (Giao dịch từng dòng)
    print("⚙️ Đang tạo dữ liệu giao dịch giả lập...")
    np.random.seed(42)
    dates_mdf = pd.date_range('2023-01-01', periods=20, freq='D')
    # Bỏ đi một số ngày để giả lập missing dates
    dates_mdf = np.delete(dates_mdf, [2, 3, 4, 10, 11])
    
    df_mdf = pd.DataFrame({
        'item_code': 'MDF-01',
        'posting_date': dates_mdf,
        'quantity': np.random.randint(5, 15, size=len(dates_mdf))
    })
    
    # Thêm 1 giao dịch outlier (Ví dụ một đơn công trình lớn)
    df_mdf.loc[14, 'quantity'] = 2000
    
    print("\n📊 [Dữ liệu gốc] Giao dịch mã MDF-01 (10 dòng đầu):")
    print(df_mdf.head(10))
    print(f"Tổng số dòng ban đầu: {len(df_mdf)}")
    
    # 2. Aggregate
    print("\n⚙️ Bước 1: Gom nhóm (Aggregate) theo ngày (Daily)...")
    df_agg = aggregate_demand(df_mdf, freq='D')
    print("Cấu trúc mới (Nixtla Format):")
    print(df_agg.head())
    
    # 3. Zero-filling
    print("\n⚙️ Bước 2: Điền khuyết thời gian (Zero-filling)...")
    df_filled = fill_missing_dates(df_agg, freq='D')
    print(f"Số dòng sau khi Zero-filling: {len(df_filled)} (Đã bổ sung các ngày bị đứt gãy)")
    
    # 4. Outlier Clipping
    print("\n⚙️ Bước 3: Phát hiện và cắt ngọn Outliers (Clipping IQR)...")
    max_before = df_filled['y'].max()
    df_clipped = clip_outliers(df_filled, multiplier=1.5)
    max_after = df_clipped['y'].max()
    print(f"Giá trị xuất kho lớn nhất TRƯỚC clipping: {max_before}")
    print(f"Giá trị xuất kho lớn nhất SAU clipping : {max_after}")
    print("-> Outlier 2000 đã bị cắt ngọn để không làm hỏng trend học máy của AI.")
    
    print("\n✅ Hoàn thành Pha 1! Dữ liệu đã sạch, liên tục và sẵn sàng đưa vào mô hình AI.")

if __name__ == "__main__":
    run()
