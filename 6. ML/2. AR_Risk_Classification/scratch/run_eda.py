import sys
import os
import pandas as pd
import numpy as np

# Thêm đường dẫn src vào system path để import
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_loader import PostgresDataLoader
from src.label_engineering import calculate_days_overdue, assign_risk_label

def run():
    print("🚀 Bắt đầu quá trình Khám phá Dữ liệu (EDA)...")
    try:
        loader = PostgresDataLoader()
        df = loader.fetch_ar_data()
        print(f"✅ Đã tải thành công {len(df)} bản ghi từ CSDL.")
    except Exception as e:
        print(f"⚠️ Không thể kết nối Database gốc (Lỗi: {e}).")
        print("Đang khởi tạo dữ liệu giả lập (Mock Data) gồm 10,000 hóa đơn để tiếp tục phân tích Pipeline...")
        
        # Tạo dữ liệu mock nếu không kết nối được DB
        np.random.seed(42)
        n = 10000
        dates = pd.date_range(start='2025-01-01', end='2026-10-06', periods=n)
        due_dates = dates + pd.Timedelta(days=30)
        
        payment_dates = []
        for d in due_dates:
            rand = np.random.rand()
            if rand < 0.7:  # 70% trả đúng hạn hoặc trễ nhẹ
                payment_dates.append(d + pd.Timedelta(days=np.random.randint(-10, 5)))
            elif rand < 0.85: # 15% trễ hạn mức trung bình
                payment_dates.append(d + pd.Timedelta(days=np.random.randint(15, 55)))
            else: # 15% nợ xấu (quá hạn nặng hoặc bùng nợ)
                if np.random.rand() < 0.5:
                    payment_dates.append(d + pd.Timedelta(days=np.random.randint(65, 150)))
                else:
                    payment_dates.append(pd.NaT)
                    
        df = pd.DataFrame({
            'invoice_no': [f'INV-{i}' for i in range(n)],
            'due_date': due_dates,
            'payment_date': payment_dates
        })
        
    print("\n⚙️ Đang tính toán Số ngày trễ hạn (days_overdue)...")
    df = calculate_days_overdue(df)
    
    print("⚙️ Đang gán Nhãn Rủi ro (0, 1, 2)...")
    df = assign_risk_label(df)
    
    print("\n📊 --- BÁO CÁO PHÂN PHỐI NHÃN (CLASS DISTRIBUTION) ---")
    dist = df['risk_label'].value_counts().sort_index()
    total = len(df)
    
    labels_map = {0: "Low Risk (An toàn, <=0 ngày)", 1: "Medium Risk (Trễ 1-60 ngày)", 2: "High Risk (Nợ xấu >60 ngày)"}
    
    for idx, count in dist.items():
        pct = count / total * 100
        print(f"  - {labels_map.get(idx, 'Unknown')}: {count:,} hóa đơn ({pct:.2f}%)")
        
    print("\n💡 Đánh giá (Insights):")
    if dist.get(2, 0) / total < 0.2:
        print("-> Tỷ lệ High Risk khá thấp. Chúng ta SẼ CẦN sử dụng kỹ thuật SMOTE hoặc Class_Weights ở Pha 2 để xử lý Imbalanced Data.")
    else:
        print("-> Dữ liệu phân bố tương đối tốt để huấn luyện trực tiếp.")
        
    print("✅ Hoàn thành Pha 1!")

if __name__ == "__main__":
    run()
