import pandas as pd
from typing import Tuple

def evaluate_by_category(cv_df: pd.DataFrame, item_dim_df: pd.DataFrame) -> pd.DataFrame:
    """
    Tính trung bình độ lỗi theo Nhóm Hàng (Category).
    cv_df: Bảng kết quả Cross Validation từ Pha 3
    item_dim_df: Bảng danh mục chứa cột unique_id và category.
    """
    from utilsforecast.evaluation import evaluate
    from utilsforecast.losses import mape, rmse, mae
    
    # Tính metrics cho từng SKU
    sku_metrics = evaluate(cv_df, metrics=[mape, rmse, mae], models=['LGBMRegressor'])
    
    # Hợp nhất với dim_item
    merged_df = pd.merge(sku_metrics, item_dim_df, on='unique_id', how='left')
    
    # Điền 'Unknown' cho các SKU không tìm thấy Category
    merged_df['category'] = merged_df['category'].fillna('Unknown')
    
    # Tính trung bình theo category và metric
    cat_metrics = merged_df.groupby(['category', 'metric'])['LGBMRegressor'].mean().reset_index()
    
    return cat_metrics

def get_worst_performers(metrics_df: pd.DataFrame, top_n: int = 5, metric_name: str = 'mape') -> pd.DataFrame:
    """
    Trích xuất ra Top N các SKU có dự báo tồi nhất (Độ lỗi cao nhất).
    metrics_df có dạng: unique_id, metric, LGBMRegressor.
    """
    # Lọc đúng loại metric
    filtered_df = metrics_df[metrics_df['metric'] == metric_name].copy()
    
    # Sắp xếp giảm dần theo độ lỗi (Lỗi càng to càng tồi)
    worst_df = filtered_df.sort_values(by='LGBMRegressor', ascending=False).head(top_n)
    
    return worst_df
