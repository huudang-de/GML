import pandas as pd

def calculate_days_overdue(df: pd.DataFrame, current_date=None) -> pd.DataFrame:
    """Tính số ngày trễ hạn của từng hóa đơn."""
    if current_date is None:
        current_date = pd.Timestamp.today()
    else:
        current_date = pd.to_datetime(current_date)
        
    df = df.copy()
    
    # Ép kiểu dữ liệu ngày tháng
    df['due_date'] = pd.to_datetime(df['due_date'])
    df['payment_date'] = pd.to_datetime(df['payment_date'])
    
    # Tính ngày trễ
    # Nếu đã trả (payment_date không NaT), lấy payment_date - due_date
    # Nếu chưa trả (payment_date là NaT), lấy current_date - due_date
    df['days_overdue'] = df.apply(
        lambda row: (row['payment_date'] - row['due_date']).days 
                    if pd.notna(row['payment_date']) 
                    else (current_date - row['due_date']).days,
        axis=1
    )
    
    return df

def assign_risk_label(df: pd.DataFrame) -> pd.DataFrame:
    """Phân loại rủi ro (0: Low, 1: Medium, 2: High) dựa trên days_overdue."""
    df = df.copy()
    
    if 'days_overdue' not in df.columns:
        raise ValueError("DataFrame phải chứa cột 'days_overdue'. Hãy chạy calculate_days_overdue trước.")
        
    def categorize(days):
        if days <= 0:
            return 0  # Low Risk
        elif 0 < days <= 60:
            return 1  # Medium Risk
        else:
            return 2  # High Risk
            
    df['risk_label'] = df['days_overdue'].apply(categorize)
    return df
