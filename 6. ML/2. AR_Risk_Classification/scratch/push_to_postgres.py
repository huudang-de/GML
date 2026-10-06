import sys
import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sqlalchemy import create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.scoring import RiskScorer

def push_ar_risk_to_postgres():
    print("🚀 Đang khởi tạo Dữ liệu AR Risk...")
    
    # 1. Tạo Dummy Model & Khách hàng
    np.random.seed(42)
    df_train = pd.DataFrame({'f1': np.random.rand(100), 'f2': np.random.rand(100)})
    y_train = np.random.choice([0, 1, 2], 100)
    model = lgb.LGBMClassifier(random_state=42, verbose=-1).fit(df_train, y_train)
    
    customer_ids = ['GML-1001', 'GML-1002', 'GML-1003', 'GML-1004', 'GML-1005']
    df_active_features = pd.DataFrame(np.random.rand(5, 2), columns=['f1', 'f2'])
    
    # 2. Chấm điểm
    scorer = RiskScorer(model)
    df_scores = scorer.score_active_customers(df_active_features, customer_ids)
    
    # 3. Đẩy lên PostgreSQL
    engine = create_engine('sqlite:///../../gml_database.db') # Dùng SQLite giả lập cho môi trường hiện tại
    df_scores.to_sql('fact_ar_risk_score', engine, schema=None, if_exists='replace', index=False)
    
    print("✅ Đã đẩy thành công bảng [fact_ar_risk_score] lên Database (Silver Layer)!")

if __name__ == "__main__":
    push_ar_risk_to_postgres()
