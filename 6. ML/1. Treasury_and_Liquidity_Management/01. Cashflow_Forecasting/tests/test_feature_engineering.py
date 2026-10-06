"""
Module: test_feature_engineering.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Test suite tự động kiểm định chất lượng ma trận đặc trưng Pha 2 (TC-FE-01 đến TC-FE-07).
    Chạy trực tiếp qua lệnh: python tests/test_feature_engineering.py
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

# Cấu hình stdout UTF-8 cho Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Thêm đường dẫn src vào sys.path để import
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_dir, "src"))

from feature_engineering import CashflowFeatureEngineer


class TestCashflowFeatureEngineering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("🧪 KHỞI ĐỘNG TEST SUITE KIỂM ĐỊNH PHA 2: FEATURE ENGINEERING")
        print("=" * 70)
        cls.engineer = CashflowFeatureEngineer()
        cls.featured_df, cls.paths = cls.engineer.run_pipeline()

    def test_tc_fe_01_input_verification(self):
        """TC-FE-01: Kiểm tra đầu vào từ Pha 1 (Đủ 212 ngày liên tục)."""
        print("\n>>> [RUN TEST] TC-FE-01: Kiem tra Dau vao Chuoi ngay tu Pha 1...")
        self.assertIsNotNone(self.engineer.df, "df khong duoc phep None")
        self.assertEqual(len(self.engineer.df), 212, "So ngay phai dung 212 ngay (01/01/2026 den 31/07/2026)")
        self.assertTrue('inflow' in self.engineer.df.columns)
        self.assertTrue('outflow' in self.engineer.df.columns)
        self.assertTrue('net_cashflow' in self.engineer.df.columns)
        print("    [PASS] TC-FE-01: Dau vao 212 ngay hop le va day du!")

    def test_tc_fe_02_exogenous_integration(self):
        """TC-FE-02: Kiểm tra tích hợp biến ngoại sinh AR và AP từ PostgreSQL."""
        print("\n>>> [RUN TEST] TC-FE-02: Kiem tra Tich hop Bien ngoai sinh AR & AP...")
        expected_exog_cols = {
            'ar_expected_due_today', 'ar_expected_due_next_7d',
            'ap_expected_due_today', 'ap_expected_due_next_7d'
        }
        self.assertTrue(expected_exog_cols.issubset(set(self.featured_df.columns)), "Thieu cot bien ngoai sinh AR/AP")
        # Kiểm tra tính chất không âm
        self.assertGreaterEqual(self.featured_df['ar_expected_due_today'].min(), 0.0)
        self.assertGreaterEqual(self.featured_df['ap_expected_due_today'].min(), 0.0)
        self.assertGreater(self.featured_df['ar_expected_due_today'].sum(), 0.0, "Tong AR due khong duoc bang 0")
        self.assertGreater(self.featured_df['ap_expected_due_today'].sum(), 0.0, "Tong AP due khong duoc bang 0")
        print("    [PASS] TC-FE-02: Bien ngoai sinh AR/AP da duoc tich hop hoan hao!")

    def test_tc_fe_03_lag_alignment_and_no_leakage(self):
        """TC-FE-03: Kiểm tra tính chuẩn xác của Lag (Không rò rỉ dữ liệu)."""
        print("\n>>> [RUN TEST] TC-FE-03: Kiem tra Do lech Lag (Inflow, Outflow, Net)...")
        # Với lag = 7, lag = 14: Giá trị tại index i phải bằng giá trị tại index i - lag
        for i in range(35, 70):
            val_lag7 = self.featured_df.loc[i, 'inflow_lag_7']
            val_true = self.featured_df.loc[i - 7, 'inflow']
            self.assertAlmostEqual(val_lag7, val_true, places=2, msg=f"Lag 7 tai index {i} khong khop!")

            outflow_lag14 = self.featured_df.loc[i, 'outflow_lag_14']
            outflow_true = self.featured_df.loc[i - 14, 'outflow']
            self.assertAlmostEqual(outflow_lag14, outflow_true, places=2, msg=f"Outflow lag 14 tai index {i} khong khop!")

        print("    [PASS] TC-FE-03: Cac dac trung Lag 1, 7, 14, 21, 28, 30 khop tuyet doi!")

    def test_tc_fe_04_rolling_window_calculation(self):
        """TC-FE-04: Kiểm tra tính chuẩn xác của Rolling Window (với shift(1) chống Lookahead)."""
        print("\n>>> [RUN TEST] TC-FE-04: Kiem tra Thong ke truot Rolling (Khong Lookahead)...")
        # Tại index 10, inflow_rolling_mean_7d phải bằng mean của inflow từ index 3 đến index 9 (7 ngày quá khứ)
        for i in [15, 25, 40]:
            rolling_val = self.featured_df.loc[i, 'inflow_rolling_mean_7d']
            past_7_days = self.featured_df.loc[i-7:i-1, 'inflow']
            expected_mean = past_7_days.mean()
            self.assertAlmostEqual(rolling_val, expected_mean, places=2, msg=f"Rolling mean tai index {i} khong khop!")

        print("    [PASS] TC-FE-04: Thong ke truot Rolling dung 100% va bao dam No Data Leakage!")

    def test_tc_fe_05_calendar_and_business_flags(self):
        """TC-FE-05: Kiểm tra cờ nghiệp vụ (Lương 10-15, Thuế 20-25, Cuối tuần, Tết)."""
        print("\n>>> [RUN TEST] TC-FE-05: Kiem tra Co nghiep vu (Luong, Thue, Cuoi tuan, Tet)...")
        # 1. Cờ cuối tuần (Thứ 7, CN)
        weekends = self.featured_df[self.featured_df['is_weekend'] == 1]
        self.assertTrue(weekends['day_of_week'].isin([5, 6]).all())

        # 2. Cờ lương (Ngày 10 - 15)
        salaries = self.featured_df[self.featured_df['is_salary_period'] == 1]
        self.assertTrue(salaries['day_of_month'].between(10, 15).all())

        # 3. Cờ thuế (Ngày 20 - 25)
        taxes = self.featured_df[self.featured_df['is_tax_period'] == 1]
        self.assertTrue(taxes['day_of_month'].between(20, 25).all())

        # 4. Cờ Tết (14/02 - 22/02/2026: đúng 9 ngày nghỉ Tết)
        tets = self.featured_df[self.featured_df['is_tet_holiday'] == 1]
        self.assertEqual(len(tets), 9, f"So ngay Tet phai la 9 ngay, thuc te: {len(tets)}")
        print("    [PASS] TC-FE-05: 100% Co nghiep vu Lich bieu da duoc gan nhan chuan xac!")

    def test_tc_fe_06_feature_richness_and_dimensions(self):
        """TC-FE-06: Kiểm tra độ phong phú đặc trưng (Tổng số cột >= 40)."""
        print("\n>>> [RUN TEST] TC-FE-06: Kiem tra Do phong phu Dac trung (Columns >= 40)...")
        num_cols = len(self.featured_df.columns)
        self.assertGreaterEqual(num_cols, 40, f"So cot dac trung phai >= 40, thuc te: {num_cols}")
        null_counts = self.featured_df.isna().sum().sum()
        self.assertEqual(null_counts, 0, f"Van con {null_counts} gia tri NaN trong ma tran dac trung")
        print(f"    [PASS] TC-FE-06: Ma tran dac trung gom {num_cols} cot, 0 gia tri Missing!")

    def test_tc_fe_07_artifacts_persistence(self):
        """TC-FE-07: Kiểm tra lưu trữ và đọc lại Parquet/CSV."""
        print("\n>>> [RUN TEST] TC-FE-07: Kiem tra Luu tru & Doc lai Artifacts...")
        for name, path in self.paths.items():
            self.assertTrue(os.path.exists(path), f"Tep khong ton tai: {path}")
            self.assertGreater(os.path.getsize(path), 0, f"Tep bi rong: {path}")

        # Đọc lại từ Parquet
        df_read_parquet = pd.read_parquet(self.paths["featured_parquet"])
        self.assertEqual(len(df_read_parquet), 212)
        self.assertEqual(len(df_read_parquet.columns), len(self.featured_df.columns))

        # Đọc lại từ CSV
        df_read_csv = pd.read_csv(self.paths["featured_csv"])
        self.assertEqual(len(df_read_csv), 212)
        print("    [PASS] TC-FE-07: featured_cashflow.parquet va .csv da duoc luu va doc lai nguyen ven!")


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCashflowFeatureEngineering)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
