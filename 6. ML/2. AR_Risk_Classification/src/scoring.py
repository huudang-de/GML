import pandas as pd
import numpy as np
from datetime import datetime

class RiskScorer:
    def __init__(self, model):
        """Khởi tạo cỗ máy chấm điểm với Model đã train"""
        self.model = model
        
        # Ánh xạ từ Label số sang Badge chữ và Mã màu Hex cho Power BI
        self.mapping = {
            0: {'badge': 'Low Risk', 'color': '#00C851'},    # Xanh lá
            1: {'badge': 'Medium Risk', 'color': '#FFBB33'}, # Vàng cam
            2: {'badge': 'High Risk', 'color': '#FF4444'}    # Đỏ cảnh báo
        }
        
    def score_active_customers(self, df_features, customer_ids):
        """
        Thực hiện chấm điểm và xuất Dataframe chuẩn hóa cho Power BI
        df_features: DataFrame chứa các features của khách hàng
        customer_ids: List mã khách hàng tương ứng
        """
        # 1. Dự báo nhãn (0, 1, 2)
        preds = self.model.predict(df_features)
        
        # 2. Lấy xác suất Nợ xấu (Cột thứ 3 tức index 2)
        probs = self.model.predict_proba(df_features)[:, 2]
        
        # 3. Tạo DataFrame Kết quả chuẩn Schema Database
        results = []
        for cid, pred, prob in zip(customer_ids, preds, probs):
            info = self.mapping[pred]
            results.append({
                'customer_id': cid,
                'score_date': datetime.now().strftime("%Y-%m-%d"),
                'risk_badge': info['badge'],
                'default_probability': round(prob, 4), # Làm tròn 4 chữ số
                'ui_color': info['color']
            })
            
        return pd.DataFrame(results)

def mock_export_to_postgres(df_scores, table_name="silver.fact_ar_risk_score"):
    """Mô phỏng hàm đẩy dữ liệu lên PostgreSQL"""
    # Trong thực tế sẽ dùng sqlalchemy: df_scores.to_sql(table_name, engine, if_exists='append')
    print(f"[Database Pipeline] Đã Export thành công {len(df_scores)} dòng vào bảng {table_name}")
    return True
