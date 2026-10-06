"""
Module: test_integration.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Test suite tự động kiểm định Tích hợp Data Warehouse & Power BI Pha 5
    Bao phủ toàn diện 7 Test Cases: TC-IT-01 đến TC-IT-07.
    Chạy trực tiếp qua lệnh: python tests/test_integration.py
"""

import os
import sys
import unittest
import pandas as pd
from sqlalchemy import create_engine, text

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

from integration import CashflowIntegrator


class TestCashflowIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("🧪 KHỞI ĐỘNG TEST SUITE KIỂM ĐỊNH PHA 5: INTEGRATION & DATA WAREHOUSE")
        print("=" * 70)
        cls.integrator = CashflowIntegrator()
        cls.pipe_res = cls.integrator.run_pipeline()

    def test_tc_it_01_input_readiness(self):
        """TC-IT-01: Kiểm tra Input & Tính nhất quán Dữ liệu."""
        print("\n>>> [RUN TEST] TC-IT-01: Kiem tra Input & Tinh nhat quan Du lieu...")
        df_fc, df_stress = self.integrator.load_forecast_data()
        self.assertEqual(len(df_fc), 31, "Tap du bao phai co dung 31 ngay Thang 7/2026")
        self.assertEqual(len(df_stress), 31, "Tap stress test phai co dung 31 ngay Thang 7/2026")
        self.assertIn("pred_net_lower_90", df_fc.columns)
        self.assertIn("pred_net_upper_90", df_fc.columns)
        print("    [PASS] TC-IT-01: Du lieu du bao va dac trung tu Phase 3/4 nhat quan va du 31 ngay!")

    def test_tc_it_02_schema_and_tables_creation(self):
        """TC-IT-02: Khởi tạo Schema & Tables Gold Layer."""
        print("\n>>> [RUN TEST] TC-IT-02: Kiem tra Schema gold va cac bang Data Warehouse...")
        engine = self.integrator.engine
        with engine.connect() as conn:
            check_tables_sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'gold' AND table_name IN ('fact_cashflow_forecast', 'fact_cashflow_scenarios');
            """
            tables = [r[0] for r in conn.execute(text(check_tables_sql)).fetchall()]
            self.assertIn("fact_cashflow_forecast", tables)
            self.assertIn("fact_cashflow_scenarios", tables)
        print("    [PASS] TC-IT-02: Schema gold va 2 bang Fact ton tai hoan chinh tren PostgreSQL!")

    def test_tc_it_03_provenance_metadata(self):
        """TC-IT-03: Tính Bất biến & Truy vết (Provenance Tracking)."""
        print("\n>>> [RUN TEST] TC-IT-03: Kiem tra Metadata truy vet (Provenance Tracking)...")
        engine = self.integrator.engine
        with engine.connect() as conn:
            row = conn.execute(text("SELECT as_of_date, run_id, model_version FROM gold.fact_cashflow_forecast LIMIT 1;")).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(str(row[0]), "2026-06-30")
            self.assertTrue(str(row[1]).startswith("run_20260630_"))
            self.assertEqual(str(row[2]), "LightGBM-v1.0-L1")
        print("    [PASS] TC-IT-03: Moi ban ghi deu mang day du as_of_date, run_id va model_version!")

    def test_tc_it_04_sync_record_counts(self):
        """TC-IT-04: Đồng bộ Dữ liệu vào PostgreSQL."""
        print("\n>>> [RUN TEST] TC-IT-04: Kiem tra So luong ban ghi dong bo...")
        engine = self.integrator.engine
        with engine.connect() as conn:
            fc_count = conn.execute(text("SELECT COUNT(*) FROM gold.fact_cashflow_forecast WHERE as_of_date = '2026-06-30';")).scalar()
            sc_count = conn.execute(text("SELECT COUNT(*) FROM gold.fact_cashflow_scenarios WHERE as_of_date = '2026-06-30';")).scalar()
            self.assertEqual(fc_count, 31, "Bang fact_cashflow_forecast phai co dung 31 dong")
            self.assertEqual(sc_count, 124, "Bang fact_cashflow_scenarios phai co dung 124 dong (31 * 4)")
        print(f"    [PASS] TC-IT-04: So luong ban ghi khop tuyet doi ({fc_count} forecast rows, {sc_count} scenario rows)!")

    def test_tc_it_05_idempotency_test(self):
        """TC-IT-05: Tính Idempotency (Chống trùng lặp dữ liệu khi nạp lại)."""
        print("\n>>> [RUN TEST] TC-IT-05: Kiem tra Tinh Idempotency (Nap lai lan 2)...")
        # Chạy lại sync lần 2
        res2 = self.integrator.sync_to_postgresql()
        self.assertEqual(res2["forecast_count"], 31)
        self.assertEqual(res2["scenarios_count"], 124)
        
        # Kiểm tra tổng số lượng trên DB vẫn phải là 31 và 124, không bị nhân đôi
        engine = self.integrator.engine
        with engine.connect() as conn:
            fc_count = conn.execute(text("SELECT COUNT(*) FROM gold.fact_cashflow_forecast WHERE as_of_date = '2026-06-30';")).scalar()
            sc_count = conn.execute(text("SELECT COUNT(*) FROM gold.fact_cashflow_scenarios WHERE as_of_date = '2026-06-30';")).scalar()
            self.assertEqual(fc_count, 31, "Khong duoc sinh duplicate rows sau khi sync lai")
            self.assertEqual(sc_count, 124, "Khong duoc sinh duplicate rows sau khi sync lai")
        print("    [PASS] TC-IT-05: Pipeline tuyet doi Idempotent, khong phat sinh duplicate records!")

    def test_tc_it_06_sql_view_for_powerbi(self):
        """TC-IT-06: Xác thực Truy vấn Tích hợp View Power BI."""
        print("\n>>> [RUN TEST] TC-IT-06: Kiem tra View gold.view_cashflow_actual_vs_forecast...")
        engine = self.integrator.engine
        query = "SELECT * FROM gold.view_cashflow_actual_vs_forecast ORDER BY date ASC;"
        df_view = pd.read_sql(query, engine)
        self.assertEqual(len(df_view), 31)
        self.assertTrue('display_net_cashflow' in df_view.columns)
        self.assertTrue('is_forecast_deficit' in df_view.columns)
        self.assertTrue('pred_net_lower_90' in df_view.columns)
        self.assertTrue('pred_net_upper_90' in df_view.columns)
        print("    [PASS] TC-IT-06: View Power BI san sang truy van truc tiep, cau truc chuan!")

    def test_tc_it_07_subproject_02_interface(self):
        """TC-IT-07: Đóng gói Giao diện cho Subproject 02 (Liquidity Optimization)."""
        print("\n>>> [RUN TEST] TC-IT-07: Kiem tra File Parquet giao tiep Subproject 02...")
        parquet_path = self.pipe_res["optimization_parquet"]
        self.assertTrue(os.path.exists(parquet_path), "File parquet giao tiep phai ton tai")
        
        df_opt = pd.read_parquet(parquet_path)
        self.assertEqual(len(df_opt), 31)
        expected_cols = {'date', 'pred_net', 'pred_inflow', 'pred_outflow', 'pred_net_lower_90', 'pred_net_upper_90'}
        self.assertTrue(expected_cols.issubset(set(df_opt.columns)))
        print("    [PASS] TC-IT-07: File forecast_for_optimization.parquet day du dac ta cho Subproject 02!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
