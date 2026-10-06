import sys
import os
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.scoring import RiskScorer, mock_export_to_postgres

def run():
    print("🚀 Bắt đầu Pha 7: Ứng dụng & Xuất dữ liệu Database (Scoring & Export)...")
    
    # 1. Khởi tạo Dummy Model đóng vai trò Model từ MLflow
    np.random.seed(42)
    df_train = pd.DataFrame({'f1': np.random.rand(100), 'f2': np.random.rand(100)})
    y_train = np.random.choice([0, 1, 2], 100)
    print("⚙️ Đang tải Production Model...")
    model = lgb.LGBMClassifier(random_state=42, verbose=-1).fit(df_train, y_train)
    
    # 2. Hệ thống tiếp nhận Khách hàng Active trong ngày
    print("⚙️ Đang quét toàn bộ Khách hàng còn dư nợ (Active Customers)...")
    customer_ids = ['GML-1001', 'GML-1002', 'GML-1003', 'GML-1004', 'GML-1005']
    # Giả lập features của họ được query từ Database
    df_active_features = pd.DataFrame(np.random.rand(5, 2), columns=['f1', 'f2'])
    
    # 3. Chấm điểm
    print("⚙️ Cỗ máy AI đang thực hiện chấm điểm Rủi ro...")
    scorer = RiskScorer(model)
    df_scores = scorer.score_active_customers(df_active_features, customer_ids)
    
    # 4. In kết quả lên màn hình (Mô phỏng bảng SQL)
    print("\n📊 --- KẾT QUẢ SẼ ĐƯỢC ĐẨY LÊN BẢNG [silver.fact_ar_risk_score] ---")
    print(df_scores.to_string(index=False))
    
    # 5. Export
    print("\n")
    mock_export_to_postgres(df_scores, "silver.fact_ar_risk_score")
    
    print("\n✅ Hoàn thành Pha 7! Dashboard PowerBI giờ chỉ việc kéo cột [risk_badge] và [ui_color] để cảnh báo Đỏ chót cho Kế toán!")

if __name__ == "__main__":
    run()
