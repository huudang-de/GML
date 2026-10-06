import pandas as pd
import numpy as np
import os
import random

def create_mock_data():
    """Tạo mock data cho Hạn mức tín dụng và Hợp đồng Tiền gửi."""
    os.makedirs('data/raw', exist_ok=True)
    
    # 1. Hạn mức tín dụng
    # VCB: Limit 20T, Debt 15T -> Avail 5T
    # BIDV: Limit 25T, Debt 5T -> Avail 20T
    # Techcombank: Limit 15T, Debt 10T -> Avail 5T
    # MBBank: Limit 10T, Debt 9T -> Avail 1T
    # VietinBank: Limit 30T, Debt 0T -> Avail 30T
    credit_data = {
        'Bank': ['VCB', 'BIDV', 'Techcombank', 'MBBank', 'VietinBank'],
        'Total_Credit_Limit': [20e9, 25e9, 15e9, 10e9, 30e9], 
        'Current_Debt': [15e9, 5e9, 10e9, 9e9, 0]
    }
    df_credit = pd.DataFrame(credit_data)
    df_credit.to_excel('data/raw/bc_tin_dung_2026.xlsx', index=False)
    
    # 2. Hợp đồng tiền gửi hiện có
    # MBBank có sổ 5 tỷ cá nhân (LTV 95%)
    # Techcombank có sổ 3 tỷ công ty (LTV 95%)
    # BIDV có sổ 10 tỷ cá nhân (LTV 90%)
    deposit_data = {
        'Contract_No': ['STK_01', 'STK_02', 'STK_03'],
        'Bank': ['MBBank', 'Techcombank', 'BIDV'],
        'Deposit_Amount': [5e9, 3e9, 10e9],
        'Owner_Type': ['Individual', 'Corp', 'Individual'],
        'LTV_Policy': [0.95, 0.95, 0.90]
    }
    df_deposit = pd.DataFrame(deposit_data)
    df_deposit.to_excel('data/raw/Hop_dong_tien_gui.xlsm', index=False)

def load_market_rates():
    """Load bảng lãi suất thị trường đã crawl"""
    try:
        df = pd.read_csv('market_interest_rates.csv')
        latest_date = df['Date'].max()
        return df[df['Date'] == latest_date]
    except Exception as e:
        print(f"⚠️ Lỗi load market rates: {e}")
        return pd.DataFrame()

def build_state():
    """Hợp nhất 6 nguồn dữ liệu"""
    create_mock_data()
    
    # 1-3. Output từ các dự án AI (Mock)
    # T+1, T+2, T+3, T+4
    cf_forecast = [2e9, -5e9, 1e9, -3e9] # Dự án Cashflow
    ar_risk = [0, -1e9, 0, 0]            # Dự án AR Risk (Hụt thu 1 tỷ ở tuần 2)
    inv_eoq = [0, -2e9, 0, 0]            # Dự án Inventory (Cần 2 tỷ mua hàng tuần 2)
    
    # Tính Total Adjusted Cashflow requirement
    # Nơi nào âm sâu nhất chính là Max Deficit (Số vốn cần gọi)
    adjusted_cf = [c + a + i for c, a, i in zip(cf_forecast, ar_risk, inv_eoq)]
    
    # 4-6. Dữ liệu tài chính
    credit = pd.read_excel('data/raw/bc_tin_dung_2026.xlsx')
    deposit = pd.read_excel('data/raw/Hop_dong_tien_gui.xlsm')
    market = load_market_rates()
    
    return {
        'adjusted_weekly_cashflow': adjusted_cf,
        'credit_limits': credit,
        'existing_deposits': deposit,
        'market_rates': market
    }

if __name__ == "__main__":
    state = build_state()
    print("✅ Đã load và hợp nhất thành công 6 luồng dữ liệu!")
    print(f"Dòng tiền ròng sau điều chỉnh (4 tuần): {state['adjusted_weekly_cashflow']}")
