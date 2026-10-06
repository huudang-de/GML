import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.feature_engineering import aggregate_customer_features, get_balanced_class_weights

def run():
    print("🚀 Bắt đầu Pha 2: Trích xuất đặc trưng (Feature Engineering)...")
    
    # 1. Tạo mock data hóa đơn sau Pha 1
    np.random.seed(42)
    n = 2000
    df = pd.DataFrame({
        'customer_code': np.random.choice([f'KH-{i:03d}' for i in range(150)], n),
        'invoice_no': [f'INV-{i}' for i in range(n)],
        'days_overdue': np.random.randint(-15, 120, n),
        'invoice_amount': np.random.uniform(5000000, 50000000, n)
    })
    
    def assign_risk(d):
        if d <= 0: return 0
        if d <= 60: return 1
        return 2
    df['risk_label'] = df['days_overdue'].apply(assign_risk)
    
    print(f"✅ Đã tải dữ liệu {len(df)} hóa đơn cho {df['customer_code'].nunique()} khách hàng.")
    
    # 2. Aggregation
    print("⚙️ Đang tổng hợp thành Ma trận Đặc trưng Khách hàng (Customer Feature Matrix)...")
    cust_df = aggregate_customer_features(df)
    
    print("\n📊 --- KẾT QUẢ: BẢNG ĐẶC TRƯNG (3 KHÁCH HÀNG ĐẦU) ---")
    print(cust_df.head(3).to_markdown(index=False))
    
    # 3. Class Weights
    print("\n⚙️ Đang phân tích xử lý Imbalanced Data bằng Class Weights...")
    y = cust_df['target_risk_label'].values
    weights = get_balanced_class_weights(y)
    
    print("⚖️ Bảng trọng số Model phạt tự động (Class Weights):")
    for cls, w in weights.items():
        print(f"  - Nhãn {cls}: Trọng số = {w:.4f}")
        
    print("\n✅ Hoàn thành Pha 2!")

if __name__ == "__main__":
    run()
