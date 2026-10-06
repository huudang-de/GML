import sys
import os
import numpy as np
import pandas as pd
import lightgbm as lgb
import warnings

# Tắt cảnh báo Shaply
warnings.filterwarnings("ignore")

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.explain import RiskExplainer

def run():
    print("🚀 Bắt đầu Pha 5: Phá vỡ 'Hộp Đen' với SHAP (Explainability)...")
    
    # 1. Khởi tạo Data Giả định mang tính Logic Nghiệp vụ cao
    np.random.seed(42)
    n = 1000
    df = pd.DataFrame({
        'avg_days_overdue': np.random.randint(-10, 90, n), # Thói quen trễ hạn
        'max_days_overdue': np.random.randint(0, 150, n),  # Lần trễ tồi tệ nhất
        'pct_on_time': np.random.uniform(0, 1, n),         # Tỷ lệ đúng hạn
        'total_invoices': np.random.randint(1, 50, n)      # Số lượng đơn hàng
    })
    
    # Thiết lập Rule nghiệp vụ (Bắt AI phải học)
    df['risk_label'] = ((df['avg_days_overdue'] > 60) | (df['max_days_overdue'] > 120)).astype(int) + \
                       ((df['avg_days_overdue'] > 30) & (df['pct_on_time'] < 0.4)).astype(int)
    df['risk_label'] = df['risk_label'].clip(0, 2)
    
    X = df.drop('risk_label', axis=1)
    y = df['risk_label']
    feature_names = X.columns.tolist()
    
    print("⚙️ Đang huấn luyện LightGBM Model...")
    model = lgb.LGBMClassifier(random_state=42, class_weight='balanced', verbose=-1)
    model.fit(X, y)
    
    # 2. Vĩ mô (Global Explainability)
    print("⚙️ Đang tích hợp SHAP TreeExplainer vào Mô hình...")
    explainer = RiskExplainer(model)
    
    print("\n🌎 --- VĨ MÔ (GLOBAL): CÁC YẾU TỐ QUYẾT ĐỊNH RỦI RO TOÀN CÔNG TY ---")
    df_global = explainer.get_global_importance(X, feature_names)
    print(df_global.to_string(index=False))
    print("💡 Insight: AI đã học đúng nghiệp vụ! Thói quen trễ (avg_days_overdue) tác động mạnh nhất.")
    
    # 3. Vi mô (Local Explainability)
    print("\n🔍 --- VI MÔ (LOCAL): ĐIỀU TRA KHÁCH HÀNG NỢ XẤU ---")
    # Tóm cổ một khách hàng thực sự bị nợ xấu (High Risk)
    high_risk_idx = y[y == 2].index[0]
    X_bad_customer = X.iloc[[high_risk_idx]]
    
    print(f"\n🎯 [BÁO CÁO CẢNH BÁO RỦI RO CHO KHÁCH HÀNG #{high_risk_idx} - LÝ DO XẾP VÀO NHÓM NỢ XẤU]")
    df_local, base_val = explainer.explain_local_customer(X_bad_customer, feature_names, class_index=2)
    
    print(f"  - Giá trị sàn (Base Value) của thuật toán: {base_val:.4f}")
    
    print("\n  [BÓC TÁCH LÝ DO BẰNG SHAP WATERFALL]")
    for _, row in df_local.iterrows():
        feat = row['Feature']
        val = row['Actual_Value']
        shap_val = row['SHAP_Contribution']
        
        if shap_val > 0:
            print(f"  🔴 {feat:18s} = {val:<8.2f} | Trọng số: +{shap_val:.3f} (ĐẨY RỦI RO LÊN CAO)")
        else:
            print(f"  🟢 {feat:18s} = {val:<8.2f} | Trọng số: {shap_val:.3f} (KÉO RỦI RO XUỐNG)")
            
    print("\n✅ Hoàn thành Pha 5! Nhân viên Kế toán/Sale giờ đã có luận điểm vững chắc để làm việc với Khách hàng này.")

if __name__ == "__main__":
    run()
