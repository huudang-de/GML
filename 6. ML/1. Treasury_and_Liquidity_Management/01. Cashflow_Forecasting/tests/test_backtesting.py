"""
Module: test_backtesting.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Test suite tự động kiểm định Kiểm thử ngược & Đánh giá mô hình Pha 4
    Bao phủ toàn diện 7 Test Cases: TC-BT-01 đến TC-BT-07.
    Chạy trực tiếp qua lệnh: python tests/test_backtesting.py
"""

import os
import sys
import json
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

# Thêm đường dẫn src vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(project_dir, "src"))

from backtesting import CashflowBacktester


class TestCashflowBacktesting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("🧪 KHỞI ĐỘNG TEST SUITE KIỂM ĐỊNH PHA 4: BACKTESTING & MODEL VALIDATION")
        print("=" * 70)
        cls.backtester = CashflowBacktester()
        cls.results = cls.backtester.run_pipeline()

    def test_tc_bt_01_artifacts_readiness(self):
        """TC-BT-01: Kiểm tra Input & Tính sẵn sàng của Artifacts."""
        print("\n>>> [RUN TEST] TC-BT-01: Kiem tra Input & Tinh san sang cua Artifacts...")
        self.assertIsNotNone(self.backtester.df, "df khong duoc phep None")
        self.assertIsNotNone(self.backtester.model_inflow, "model_inflow khong duoc phep None")
        self.assertIsNotNone(self.backtester.model_outflow, "model_outflow khong duoc phep None")
        
        self.assertEqual(len(self.backtester.df_test), 31, "Tap Test phai co dung 31 ngay cua Thang 7/2026")
        self.assertEqual(self.backtester.df_test['date'].min(), pd.to_datetime("2026-07-01"))
        self.assertEqual(self.backtester.df_test['date'].max(), pd.to_datetime("2026-07-31"))
        print("    [PASS] TC-BT-01: Ca 2 models va tap Test Thang 7 deu san sang va hop le!")

    def test_tc_bt_02_benchmark_comparison(self):
        """TC-BT-02: So sánh Benchmark với Baselines."""
        print("\n>>> [RUN TEST] TC-BT-02: So sanh Benchmark voi 4 Baselines...")
        bench_df = self.backtester.benchmark_df
        self.assertIsNotNone(bench_df)
        self.assertEqual(len(bench_df), 5, "Bang so sanh phai chua 5 mo hinh (LightGBM + 4 Baselines)")
        
        models_in_bench = set(bench_df['model_name'])
        expected_models = {
            "LightGBM (ML Model)",
            "Naive (t-1)",
            "Seasonal Naive (t-7)",
            "Moving Average 7d (MA-7)",
            "Moving Average 30d (MA-30)"
        }
        self.assertEqual(models_in_bench, expected_models)

        # Kiểm tra Directional Accuracy của LightGBM đạt mức cao
        lgb_row = bench_df[bench_df['model_name'] == "LightGBM (ML Model)"].iloc[0]
        self.assertGreaterEqual(lgb_row['net_directional_accuracy_pct'], 50.0)
        print(f"    [PASS] TC-BT-02: Hoan tat doi dau Benchmark. LightGBM Directional Acc={lgb_row['net_directional_accuracy_pct']}%!")

    def test_tc_bt_03_multi_horizon_evaluation(self):
        """TC-BT-03: Đánh giá Đa khung thời gian (Multi-Horizon: 7d, 14d, 30d)."""
        print("\n>>> [RUN TEST] TC-BT-03: Kiem tra Danh gia Da khung thoi gian (7d, 14d, 30d)...")
        mh = self.backtester.multi_horizon_results
        self.assertIn("7_days", mh)
        self.assertIn("14_days", mh)
        self.assertIn("30_days", mh)
        
        self.assertEqual(mh["7_days"]["horizon_days"], 7)
        self.assertEqual(mh["14_days"]["horizon_days"], 14)
        self.assertEqual(mh["30_days"]["horizon_days"], 30)
        
        for h, v in mh.items():
            self.assertGreater(v["inflow_wape_pct"], 0.0)
            self.assertGreater(v["outflow_wape_pct"], 0.0)
            self.assertGreaterEqual(v["net_directional_accuracy_pct"], 40.0)
        print("    [PASS] TC-BT-03: Phan ra da khung thoi gian thanh cong cho ca 3 horizons!")

    def test_tc_bt_04_prediction_intervals(self):
        """TC-BT-04: Tính toán Dải Dự báo Tin cậy (Prediction Intervals 90%)."""
        print("\n>>> [RUN TEST] TC-BT-04: Kiem tra Dai du bao tin cay 90%...")
        int_df = self.backtester.interval_df
        self.assertIsNotNone(int_df)
        self.assertEqual(len(int_df), 31)
        
        # Lower bound phải luôn <= Upper bound
        self.assertTrue((int_df['pred_net_lower_90'] <= int_df['pred_net_upper_90']).all())
        
        coverage_rate = float(int_df['is_within_interval'].mean()) * 100.0
        # Kiểm tra tỷ lệ bao phủ thực tế đạt mức chấp nhận được (>= 75%)
        self.assertGreaterEqual(coverage_rate, 75.0, f"Coverage rate {coverage_rate}% phai >= 75%")
        print(f"    [PASS] TC-BT-04: Ty le bao phu thuc te dat {coverage_rate:.2f}% (Chuan tin cay >= 75%)!")

    def test_tc_bt_05_residual_outliers(self):
        """TC-BT-05: Phân tích Phần dư & Ngoại lệ (Residual Outlier Analysis)."""
        print("\n>>> [RUN TEST] TC-BT-05: Kiem tra Phan tich Ngoai le Sai so Phan du...")
        out_analysis = self.backtester.outlier_analysis
        self.assertIn("total_outliers", out_analysis)
        self.assertIn("threshold_ty", out_analysis)
        self.assertIn("outliers", out_analysis)
        
        # Ngưỡng phải > 0
        self.assertGreater(out_analysis["threshold_ty"], 0.0)
        # Số lượng ngoại lệ hợp lý
        self.assertLessEqual(out_analysis["total_outliers"], 10)
        print(f"    [PASS] TC-BT-05: Xac dinh duoc {out_analysis['total_outliers']} ngay bien dong vuot nguong {out_analysis['threshold_ty']} Ty!")

    def test_tc_bt_06_stress_testing_scenarios(self):
        """TC-BT-06: Mô phỏng Kịch bản Stress Testing."""
        print("\n>>> [RUN TEST] TC-BT-06: Kiem tra Mo phong Stress Testing...")
        st_summary = self.backtester.stress_summary
        required_scenarios = ["S0_Baseline", "S1_AR_Delay_Shock", "S2_AP_Surge_Shock", "S3_Combined_Shock"]
        for sc in required_scenarios:
            self.assertIn(sc, st_summary, f"Thieu kich ban {sc}")
            self.assertIn("deficit_days", st_summary[sc])
            self.assertIn("max_cumulative_deficit_ty", st_summary[sc])
            self.assertIn("recommended_cash_buffer_ty", st_summary[sc])
            
        # Kịch bản kép S3 phải gây thâm hụt lớn hơn hoặc bằng S0
        s0_drawdown = st_summary["S0_Baseline"]["max_cumulative_deficit_ty"]
        s3_drawdown = st_summary["S3_Combined_Shock"]["max_cumulative_deficit_ty"]
        self.assertLessEqual(s3_drawdown, s0_drawdown, "Kich ban S3 phai co do tham hut lon hon Base")
        print("    [PASS] TC-BT-06: 3 kich ban rui ro mo phong chuan xac han muc dem thanh khoan can thiet!")

    def test_tc_bt_07_artifacts_integrity(self):
        """TC-BT-07: Đóng gói & Tính toàn vẹn Báo cáo Backtest."""
        print("\n>>> [RUN TEST] TC-BT-07: Kiem tra Dong goi & Toan ven Tep Bao cao...")
        models_dir = self.backtester.models_dir
        expected_files = [
            "backtest_metrics.json",
            "backtest_comparison.csv",
            "prediction_intervals.csv",
            "stress_test_scenarios.csv"
        ]
        
        for f in expected_files:
            fp = os.path.join(models_dir, f)
            self.assertTrue(os.path.exists(fp), f"Thieu tep: {f}")
            self.assertGreater(os.path.getsize(fp), 0, f"Tep bi rong: {f}")
            
        # Kiểm tra đọc lại JSON
        with open(os.path.join(models_dir, "backtest_metrics.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("benchmark_comparison", data)
            self.assertIn("multi_horizon_backtest", data)
            self.assertIn("stress_testing_summary", data)
        print("    [PASS] TC-BT-07: Luu tru thanh cong toan bo 4 artifacts bao cao Backtest!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
