import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.forecast import evaluate_cross_validation, calculate_metrics
from src.evaluation import evaluate_by_category, get_worst_performers

def run():
    print("🚀 Bắt đầu Pha 5: Kiểm định lùi và Đánh giá (Backtesting & Evaluation)...")
    
    # 1. Tạo Mock Data cho 10 SKU
    print("\n⚙️ Bước 1: Tạo dữ liệu giả lập cho 10 SKU thuộc 3 Nhóm hàng (Ván, Giấy, Nẹp)...")
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=80, freq='D')
    
    dfs = []
    # 4 SKU Ván (Biến động trung bình)
    for i in range(1, 5):
        dfs.append(pd.DataFrame({'unique_id': f'VAN-0{i}', 'ds': dates, 'y': np.random.normal(50, 10, 80)}))
    # 3 SKU Giấy (Biến động cực thấp - dễ dự báo)
    for i in range(1, 4):
        dfs.append(pd.DataFrame({'unique_id': f'GIAY-0{i}', 'ds': dates, 'y': np.random.normal(200, 5, 80)}))
    # 3 SKU Nẹp (Biến động cực cao - khó dự báo)
    for i in range(1, 4):
        dfs.append(pd.DataFrame({'unique_id': f'NEP-0{i}', 'ds': dates, 'y': np.random.normal(10, 8, 80)}))
        
    df = pd.concat(dfs, ignore_index=True)
    df['y'] = df['y'].clip(lower=0).astype(int)
    
    # Dimension Table
    dim_item = pd.DataFrame({
        'unique_id': [f'VAN-0{i}' for i in range(1, 5)] + [f'GIAY-0{i}' for i in range(1, 4)] + [f'NEP-0{i}' for i in range(1, 4)],
        'category': ['Ván']*4 + ['Giấy']*3 + ['Nẹp']*3
    })
    
    # 2. Run Cross Validation
    print("\n⚙️ Bước 2: Chạy Walk-Forward Cross Validation (4 Windows x 5 Ngày)...")
    cv_df = evaluate_cross_validation(df, h=5, n_windows=4, freq='D')
    
    # 3. Evaluate by Category
    print("\n📊 BÁO CÁO 1: ĐỘ LỖI THEO NHÓM HÀNG (CATEGORY METRICS)")
    cat_metrics = evaluate_by_category(cv_df, dim_item)
    
    # Format hiển thị MAPE
    cat_mape = cat_metrics[cat_metrics['metric'] == 'mape'].copy()
    cat_mape['LGBMRegressor'] = (cat_mape['LGBMRegressor'] * 100).round(2).astype(str) + '%'
    cat_mape.rename(columns={'LGBMRegressor': 'MAPE (%)', 'category': 'Nhóm Hàng'}, inplace=True)
    print(cat_mape[['Nhóm Hàng', 'MAPE (%)']].to_string(index=False))
    
    # 4. Get Worst Performers
    print("\n🚨 BÁO CÁO 2: CẢNH BÁO TOP 3 SKU DỰ BÁO TỒI NHẤT (WORST PERFORMERS)")
    sku_metrics = calculate_metrics(cv_df)
    worst_skus = get_worst_performers(sku_metrics, top_n=3, metric_name='mape')
    
    worst_skus['LGBMRegressor'] = (worst_skus['LGBMRegressor'] * 100).round(2).astype(str) + '%'
    worst_skus = pd.merge(worst_skus, dim_item, on='unique_id', how='left')
    worst_skus.rename(columns={'LGBMRegressor': 'Lỗi MAPE', 'unique_id': 'Mã SKU', 'category': 'Nhóm Hàng'}, inplace=True)
    print(worst_skus[['Mã SKU', 'Nhóm Hàng', 'Lỗi MAPE']].to_string(index=False))
    
    print("\n✅ Hoàn thành Pha 5! Các báo cáo đã sẵn sàng cho Giám đốc đánh giá độ tin cậy của AI.")

if __name__ == "__main__":
    run()
