import pandas as pd
import numpy as np
from sklearn.utils.class_weight import compute_class_weight

def aggregate_customer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp đặc trưng lịch sử thanh toán theo từng khách hàng."""
    if 'days_overdue' not in df.columns or 'risk_label' not in df.columns:
        raise ValueError("DataFrame thiếu cột days_overdue hoặc risk_label.")
        
    df = df.copy()
    # Tạo cờ đúng hạn (Label 0 là Low Risk / đúng hạn)
    df['is_on_time'] = (df['risk_label'] == 0).astype(int)
    
    aggs = {
        'days_overdue': ['mean', 'max'],
        'is_on_time': ['mean'],
        'invoice_no': ['count']
    }
    
    if 'invoice_amount' in df.columns:
        aggs['invoice_amount'] = ['sum', 'mean']
        
    cust_df = df.groupby('customer_code').agg(aggs).reset_index()
    
    # Làm phẳng (flatten) các cột multi-level của Pandas
    new_cols = ['customer_code', 'avg_days_overdue', 'max_days_overdue', 'pct_on_time', 'total_invoices']
    if 'invoice_amount' in df.columns:
        new_cols.extend(['total_amount', 'avg_amount'])
        
    cust_df.columns = new_cols
    
    # Xác định Target Label cho Khách hàng: Lấy mức rủi ro cao nhất trong các hóa đơn hiện tại
    target_df = df.groupby('customer_code')['risk_label'].max().reset_index()
    target_df.rename(columns={'risk_label': 'target_risk_label'}, inplace=True)
    
    cust_df = cust_df.merge(target_df, on='customer_code', how='left')
    return cust_df

def get_balanced_class_weights(y: np.ndarray) -> dict:
    """Tính toán weights tự động cho imbalanced classes"""
    classes = np.unique(y)
    weights = compute_class_weight(class_weight='balanced', classes=classes, y=y)
    return dict(zip(classes, weights))
