"""
Module: test_data_preparation.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Test suite tự động kiểm định chất lượng dữ liệu Pha 1 (TC-01 đến TC-07).
    Chạy trực tiếp qua lệnh: python tests/test_data_preparation.py
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import unittest
import pandas as pd
import numpy as np

# Thêm đường dẫn src vào sys.path để import
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_dir, "src"))

from data_preparation import CashflowDataPreparator


class TestCashflowDataPreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("🧪 KHỞI ĐỘNG TEST SUITE KIỂM ĐỊNH PHA 1: DATA PREPARATION")
        print("=" * 70)
        cls.preparator = CashflowDataPreparator(
            start_date="2026-01-01",
            end_date="2026-07-31"
        )
        # Thực thi pipeline 1 lần duy nhất để tạo dữ liệu phục vụ test
        cls.daily_df, cls.detailed_df, cls.paths = cls.preparator.run_pipeline()

    def test_tc01_connection_and_extraction(self):
        """TC-01: Kết nối & Trích xuất thành công dữ liệu từ PostgreSQL."""
        print("\n>>> [RUN TEST] TC-01: Kiem tra Ket noi & Trich xuat Fact_cashflow...")
        self.assertIsNotNone(self.preparator.raw_df, "raw_df khong duoc phep None")
        self.assertGreater(len(self.preparator.raw_df), 30000, "So ban ghi trich xuat phai > 30,000 (thuc te: 31,717 ban ghi TK 111, 112)")
        required_cols = {'posting_date', 'voucher_no', 'account_no', 'debit_amount', 'credit_amount'}
        self.assertTrue(required_cols.issubset(set(self.preparator.raw_df.columns)), "Thieu cot bat buoc")
        print("    [PASS] TC-01: Trich xuat thanh cong 100% du lieu tu PostgreSQL!")

    def test_tc02_ctnb_exclusion_and_audit_totals(self):
        """TC-02: Khử nhiễu CTNB & Khớp số liệu kiểm toán tài chính."""
        print("\n>>> [RUN TEST] TC-02: Kiem tra Khu nhieu CTNB & Khop so lieu...")
        cleaned = self.preparator.cleaned_df
        # 1. Khong con bat ky chung tu CTNB nao
        has_ctnb = cleaned['voucher_no'].str.upper().str.startswith('CTNB', na=False).any()
        self.assertFalse(has_ctnb, "Van con chung tu CTNB trong du lieu cleaned!")

        # 2. Khop tong so lieu dong tien vao/ra voi UAT PostgreSQL
        # Kỳ vọng: Inflow ~ 2,856.47 Tỷ, Outflow ~ 2,749.32 Tỷ
        total_inflow = cleaned['debit_amount'].sum() / 1e9
        total_outflow = cleaned['credit_amount'].sum() / 1e9

        self.assertAlmostEqual(total_inflow, 2856.47, delta=1.0, msg="Inflow lech qua 1 Ty VND")
        self.assertAlmostEqual(total_outflow, 2749.32, delta=1.0, msg="Outflow lech qua 1 Ty VND")
        print(f"    [PASS] TC-02: 100% CTNB da bi loai bo! Inflow: {total_inflow:,.2f} Ty, Outflow: {total_outflow:,.2f} Ty.")

    def test_tc03_calendar_continuity_212_days(self):
        """TC-03: Tính liên tục của chuỗi thời gian (Đủ 212 ngày liên tục)."""
        print("\n>>> [RUN TEST] TC-03: Kiem tra Tinh lien tuc cua Chuoi thoi gian...")
        # Khoảng thời gian từ 2026-01-01 đến 2026-07-31:
        # Tháng 1 (31) + Tháng 2 (28) + Tháng 3 (31) + Tháng 4 (30) + Tháng 5 (31) + Tháng 6 (30) + Tháng 7 (31) = 212 ngày!
        expected_days = 212
        actual_days = len(self.daily_df)
        self.assertEqual(actual_days, expected_days, f"Chuoi ngay phai dung {expected_days} ngay, thuc te: {actual_days}")

        # Kiểm tra không có ngày nào bị trùng lặp (duplicate)
        self.assertEqual(self.daily_df['date'].nunique(), expected_days, "Co ngay bi trung lap")

        # Kiểm tra bước nhảy ngày là đúng 1 day
        date_diffs = self.daily_df['date'].diff().dropna()
        self.assertTrue((date_diffs == pd.Timedelta(days=1)).all(), "Chuoi ngay bi dut quang, khong lien tuc")
        print(f"    [PASS] TC-03: Chuoi ngay lien tuc 100% (Du {actual_days} ngay tu 01/01 den 31/07/2026)!")

    def test_tc04_no_missing_values(self):
        """TC-04: Kiểm tra giá trị thiếu (Null / NaN check)."""
        print("\n>>> [RUN TEST] TC-04: Kiem tra Triet tieu Missing Values (NaN)...")
        null_counts = self.daily_df.isna().sum().sum()
        self.assertEqual(null_counts, 0, f"Van con {null_counts} gia tri NaN trong daily_df")

        null_detailed = self.detailed_df.isna().sum().sum()
        self.assertEqual(null_detailed, 0, f"Van con {null_detailed} gia tri NaN trong detailed_df")
        print("    [PASS] TC-04: 100% khong con gia tri NaN/Missing!")

    def test_tc05_mathematical_consistency(self):
        """TC-05: Kiểm tra tính hợp lệ toán học (net_cashflow == inflow - outflow)."""
        print("\n>>> [RUN TEST] TC-05: Kiem tra Tinh hop le Toan hoc (Net = Inflow - Outflow)...")
        calculated_net = self.daily_df['inflow'] - self.daily_df['outflow']
        diff = np.abs(self.daily_df['net_cashflow'] - calculated_net).max()
        self.assertLess(diff, 1e-4, f"Sai so toan hoc qua lon: {diff}")
        print("    [PASS] TC-05: Tinh hop le toan hoc dung tuyet doi tren 100% cac ngay!")

    def test_tc06_non_negative_inflow_outflow(self):
        """TC-06: Thu và Chi phải luôn không âm (>= 0)."""
        print("\n>>> [RUN TEST] TC-06: Kiem tra Tinh chat Phi am (Inflow, Outflow >= 0)...")
        min_inflow = self.daily_df['inflow'].min()
        min_outflow = self.daily_df['outflow'].min()
        self.assertGreaterEqual(min_inflow, 0.0, "Co gia tri Inflow am!")
        self.assertGreaterEqual(min_outflow, 0.0, "Co gia tri Outflow am!")
        print(f"    [PASS] TC-06: Min Inflow = {min_inflow:,.0f}, Min Outflow = {min_outflow:,.0f} (Dung nghiep vu)!")

    def test_tc07_file_artifacts_created_and_readable(self):
        """TC-07: Xuất tệp Parquet & CSV và kiểm tra khả năng đọc lại."""
        print("\n>>> [RUN TEST] TC-07: Kiem tra Tep tin Parquet & CSV dau ra...")
        for name, path in self.paths.items():
            self.assertTrue(os.path.exists(path), f"Tep khong ton tai: {path}")
            self.assertGreater(os.path.getsize(path), 0, f"Tep bi rong (0 bytes): {path}")

        # Đọc lại từ Parquet
        df_read_parquet = pd.read_parquet(self.paths["daily_parquet"])
        self.assertEqual(len(df_read_parquet), 212, "Doc lai parquet phai du 212 dong")

        # Đọc lại từ CSV
        df_read_csv = pd.read_csv(self.paths["daily_csv"])
        self.assertEqual(len(df_read_csv), 212, "Doc lai csv phai du 212 dong")
        print("    [PASS] TC-07: Tat ca cac tep Parquet & CSV da duoc tao va doc lai nguyen ven!")


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCashflowDataPreparation)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
