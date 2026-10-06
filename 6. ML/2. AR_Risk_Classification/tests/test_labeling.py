import pandas as pd
import pytest
from src.label_engineering import calculate_days_overdue, assign_risk_label

def test_paid_on_time():
    data = pd.DataFrame([{
        'due_date': '2026-10-10',
        'payment_date': '2026-10-05'
    }])
    res = calculate_days_overdue(data)
    assert res.iloc[0]['days_overdue'] == -5, "Sai số ngày khi trả trước hạn"
    res = assign_risk_label(res)
    assert res.iloc[0]['risk_label'] == 0, "Sai nhãn (phải là Low Risk)"

def test_unpaid_overdue_short():
    data = pd.DataFrame([{
        'due_date': '2026-09-01',
        'payment_date': pd.NaT
    }])
    res = calculate_days_overdue(data, current_date='2026-10-06')
    assert res.iloc[0]['days_overdue'] == 35, "Sai số ngày với khoản chưa trả"
    res = assign_risk_label(res)
    assert res.iloc[0]['risk_label'] == 1, "Sai nhãn (phải là Medium Risk)"

def test_paid_late_long():
    data = pd.DataFrame([{
        'due_date': '2026-06-01',
        'payment_date': '2026-10-01'
    }])
    res = calculate_days_overdue(data)
    assert res.iloc[0]['days_overdue'] == 122, "Sai số ngày nợ dài hạn"
    res = assign_risk_label(res)
    assert res.iloc[0]['risk_label'] == 2, "Sai nhãn (phải là High Risk)"
