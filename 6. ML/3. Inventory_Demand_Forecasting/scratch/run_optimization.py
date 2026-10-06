import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.forecast import train_and_predict
from src.optimize import calculate_rop, calculate_eoq

def run():
    print("🚀 Bắt đầu Pha 4: Tối ưu hóa Hàng tồn kho (Inventory Optimization)...")
    
    # 1. Khởi tạo Data và Chạy Output từ Pha 3
    print("\n⚙️ Đang chạy mô phỏng dự báo AI (Pha 3) để lấy output (Point + Confidence Interval)...")
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    
    df_van = pd.DataFrame({
        'unique_id': 'VAN-01',
        'ds': dates,
        'y': np.random.normal(loc=40, scale=8, size=60) # Avg ~40, Std ~8
    })
    
    df_nep = pd.DataFrame({
        'unique_id': 'NEP-02',
        'ds': dates,
        'y': np.random.normal(loc=120, scale=15, size=60) # Avg ~120, Std ~15
    })
    
    df = pd.concat([df_van, df_nep], ignore_index=True)
    df['y'] = df['y'].clip(lower=0).astype(int)
    
    # Dự báo 7 ngày tới
    forecasts = train_and_predict(df, h=7, freq='D', levels=[95])
    
    # 2. Xử lý Output Dự báo để rút ra Avg Demand và Std Demand
    print("\n⚙️ Bước 1: Trích xuất các tham số Chuỗi cung ứng từ Khoảng tin cậy của MLForecast...")
    # Độ lệch chuẩn (Std Demand) có thể được xấp xỉ từ Khoảng tin cậy 95%
    # z-score (2-sided 95%) = 1.96. Khoảng cách Hi - Lo = 2 * 1.96 * Std
    forecasts['std_demand'] = (forecasts['LGBMRegressor-hi-95'] - forecasts['LGBMRegressor-lo-95']) / (2 * 1.96)
    
    # Gom nhóm lấy trung bình nhu cầu của mỗi SKU trong 7 ngày tới
    supply_chain_params = forecasts.groupby('unique_id').agg(
        avg_demand=('LGBMRegressor', 'mean'),
        std_demand=('std_demand', 'mean')
    ).reset_index()
    
    # 3. Gắn thêm Tham số Kinh doanh giả định
    print("   -> Bổ sung Lead Time, Ordering Cost, Unit Cost (Từ ERP)...")
    # Giả định VAN-01 giao hàng lâu (14 ngày), NEP-02 giao nhanh (7 ngày)
    supply_chain_params['lead_time'] = supply_chain_params['unique_id'].map({'VAN-01': 14, 'NEP-02': 7})
    supply_chain_params['unit_cost'] = supply_chain_params['unique_id'].map({'VAN-01': 500000, 'NEP-02': 50000}) # Giá trị hàng
    supply_chain_params['ordering_cost'] = 100000 # 100k chi phí đặt hàng
    supply_chain_params['holding_cost_rate'] = 0.20 # 20% chi phí lưu kho mỗi năm
    
    # 4. Tính toán ROP & EOQ
    print("\n⚙️ Bước 2: Kích hoạt Hàm Toán học ROP & EOQ để sinh Bảng Kế hoạch...")
    results = []
    for _, row in supply_chain_params.iterrows():
        rop, ss = calculate_rop(
            avg_demand=row['avg_demand'], 
            std_demand=row['std_demand'], 
            lead_time_days=row['lead_time'],
            service_level=0.95
        )
        
        # Nhu cầu năm = nhu cầu ngày * 365
        eoq = calculate_eoq(
            annual_demand=row['avg_demand'] * 365,
            ordering_cost=row['ordering_cost'],
            holding_cost_rate=row['holding_cost_rate'],
            unit_cost=row['unit_cost']
        )
        
        results.append({
            'SKU': row['unique_id'],
            'Nhu Cầu TB/Ngày': round(row['avg_demand'], 1),
            'Độ Lệch Chuẩn': round(row['std_demand'], 1),
            'Thời gian Giao (Ngày)': row['lead_time'],
            'Tồn kho An toàn (SS)': ss,
            'Điểm Báo Động (ROP)': rop,
            'Số Lượng Nhập Tối Ưu (EOQ)': eoq
        })
        
    df_results = pd.DataFrame(results)
    
    print("\n📊 [BẢNG KẾ HOẠCH MUA HÀNG - SILVER LAYER DÀNH CHO POWER BI]")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    print(df_results.to_string(index=False))
    
    print("\n✅ Hoàn thành Pha 4! Chuỗi giá trị từ Dữ liệu Lịch sử -> Phân tích AI -> Ra Kế hoạch Kinh doanh đã được liên thông hoàn toàn.")

if __name__ == "__main__":
    run()
