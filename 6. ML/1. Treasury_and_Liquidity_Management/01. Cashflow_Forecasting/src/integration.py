"""
Module: integration.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Tích hợp kết quả dự báo Dòng tiền vào PostgreSQL Data Warehouse (Gold Layer)
    và xuất tệp giao tiếp cho Mô hình 02. Liquidity_Optimization:
    1. Tạo bảng gold.fact_cashflow_forecast và gold.fact_cashflow_scenarios
    2. Gắn metadata truy vết (as_of_date, run_id, model_version) chuẩn nguyên tắc Immutable Runs
    3. Tạo View SQL gold.view_cashflow_actual_vs_forecast hỗ trợ Power BI Dashboard 5
    4. Xuất tệp data/processed/forecast_for_optimization.parquet
"""

import os
import sys
import uuid
import logging
import datetime
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# Cấu hình stdout UTF-8 cho Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CashflowIntegration")


class CashflowIntegrator:
    def __init__(
        self,
        db_url: str = "postgresql+psycopg2://dev:Inda1234@127.0.0.1:5432/data_warehouse",
        as_of_date: str = "2026-06-30",
        model_version: str = "LightGBM-v1.0-L1"
    ):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.models_dir = os.path.join(base_dir, "models")
        self.processed_dir = os.path.join(base_dir, "data", "processed")
        os.makedirs(self.processed_dir, exist_ok=True)

        self.db_url = db_url
        self.as_of_date = pd.to_datetime(as_of_date).date()
        self.model_version = model_version
        self.run_id = f"run_{self.as_of_date.strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"

        self.engine = create_engine(self.db_url)

    def log_step(self, step_name: str, message: str):
        print(f"\n>>> [TASK] {step_name.upper()}: {message}")
        logger.info(f"[{step_name}] {message}")

    def init_database_schema(self):
        """Khởi tạo Schema gold, các bảng và view trong PostgreSQL."""
        self.log_step("INIT_SCHEMA", "Khoi tao Schema gold va DDL cac bang Data Warehouse...")

        ddl_script = """
        CREATE SCHEMA IF NOT EXISTS gold;

        -- 1. Bảng lưu trữ chi tiết dự báo dòng tiền chính (có dải tin cậy 90%)
        CREATE TABLE IF NOT EXISTS gold.fact_cashflow_forecast (
            forecast_id VARCHAR(64) PRIMARY KEY,
            date DATE NOT NULL,
            as_of_date DATE NOT NULL,
            run_id VARCHAR(64) NOT NULL,
            model_version VARCHAR(32) NOT NULL,
            pred_inflow NUMERIC(18, 2) NOT NULL,
            pred_outflow NUMERIC(18, 2) NOT NULL,
            pred_net NUMERIC(18, 2) NOT NULL,
            pred_net_lower_90 NUMERIC(18, 2) NOT NULL,
            pred_net_upper_90 NUMERIC(18, 2) NOT NULL,
            actual_inflow NUMERIC(18, 2),
            actual_outflow NUMERIC(18, 2),
            actual_net NUMERIC(18, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_fc_date ON gold.fact_cashflow_forecast(date);
        CREATE INDEX IF NOT EXISTS idx_fc_as_of ON gold.fact_cashflow_forecast(as_of_date);

        -- 2. Bảng lưu trữ kết quả phân tích kịch bản Stress-testing (What-If Scenarios)
        CREATE TABLE IF NOT EXISTS gold.fact_cashflow_scenarios (
            scenario_id VARCHAR(64) PRIMARY KEY,
            date DATE NOT NULL,
            scenario_code VARCHAR(32) NOT NULL,
            scenario_name VARCHAR(128) NOT NULL,
            as_of_date DATE NOT NULL,
            run_id VARCHAR(64) NOT NULL,
            pred_net NUMERIC(18, 2) NOT NULL,
            is_cash_deficit BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_sc_date_code ON gold.fact_cashflow_scenarios(date, scenario_code);

        -- 3. View tổng hợp phục vụ trực quan hóa Power BI Dashboard 5
        CREATE OR REPLACE VIEW gold.view_cashflow_actual_vs_forecast AS
        SELECT 
            f.date,
            f.as_of_date,
            f.run_id,
            f.model_version,
            f.actual_inflow,
            f.actual_outflow,
            f.actual_net,
            f.pred_inflow,
            f.pred_outflow,
            f.pred_net,
            f.pred_net_lower_90,
            f.pred_net_upper_90,
            COALESCE(f.actual_net, f.pred_net) AS display_net_cashflow,
            CASE WHEN f.pred_net < 0 THEN TRUE ELSE FALSE END AS is_forecast_deficit
        FROM gold.fact_cashflow_forecast f;
        """

        with self.engine.begin() as conn:
            conn.execute(text(ddl_script))

        self.log_step("INIT_SCHEMA", "Khoi tao thanh cong DDL gold.fact_cashflow_forecast va gold.fact_cashflow_scenarios!")

    def load_forecast_data(self) -> tuple:
        """Đọc kết quả dự báo và stress testing từ thư mục models/."""
        self.log_step("LOAD_DATA", "Doc ket qua tu Phase 3 va Phase 4...")

        intervals_path = os.path.join(self.models_dir, "prediction_intervals.csv")
        pred_july_path = os.path.join(self.models_dir, "test_predictions_july2026.csv")
        stress_path = os.path.join(self.models_dir, "stress_test_scenarios.csv")

        if not os.path.exists(intervals_path) or not os.path.exists(pred_july_path):
            raise FileNotFoundError("Thieu tep ket qua du bao tu Phase 3 hoac Phase 4 trong models/!")

        df_intervals = pd.read_csv(intervals_path)
        df_july = pd.read_csv(pred_july_path)
        df_stress = pd.read_csv(stress_path)

        # Merge thông tin
        df_forecast = pd.merge(df_july, df_intervals[['date', 'pred_net_lower_90', 'pred_net_upper_90']], on='date')
        df_forecast['date'] = pd.to_datetime(df_forecast['date']).dt.date

        return df_forecast, df_stress

    def sync_to_postgresql(self) -> dict:
        """Đồng bộ dữ liệu vào PostgreSQL đảm bảo tính Idempotency."""
        self.log_step("SYNC_DB", f"Bat dau dong bo du lieu vao PostgreSQL (Run ID: {self.run_id})...")

        df_forecast, df_stress = self.load_forecast_data()

        # 1. Chuẩn bị bảng gold.fact_cashflow_forecast
        forecast_rows = []
        for _, r in df_forecast.iterrows():
            f_id = f"fc_{r['date'].strftime('%Y%m%d')}_{self.run_id}"
            forecast_rows.append({
                "forecast_id": f_id,
                "date": r['date'],
                "as_of_date": self.as_of_date,
                "run_id": self.run_id,
                "model_version": self.model_version,
                "pred_inflow": round(float(r['pred_inflow']), 2),
                "pred_outflow": round(float(r['pred_outflow']), 2),
                "pred_net": round(float(r['pred_net']), 2),
                "pred_net_lower_90": round(float(r['pred_net_lower_90']), 2),
                "pred_net_upper_90": round(float(r['pred_net_upper_90']), 2),
                "actual_inflow": round(float(r['actual_inflow']), 2),
                "actual_outflow": round(float(r['actual_outflow']), 2),
                "actual_net": round(float(r['actual_net']), 2)
            })
        df_fc_insert = pd.DataFrame(forecast_rows)

        # 2. Chuẩn bị bảng gold.fact_cashflow_scenarios
        df_stress['date'] = pd.to_datetime(df_stress['date']).dt.date
        scenario_meta = {
            "s0_base_net": ("S0_Baseline", "Kịch bản Cơ sở (Dự báo chuẩn)"),
            "s1_ar_shock_net": ("S1_AR_Delay", "Kịch bản Chậm thu nợ AR (-25%)"),
            "s2_ap_surge_net": ("S2_AP_Surge", "Kịch bản Áp lực chi AP (+25%)"),
            "s3_combined_shock_net": ("S3_Combined", "Kịch bản Kép (Thu -20%, Chi +20%)")
        }

        scenario_rows = []
        for _, r in df_stress.iterrows():
            d = r['date']
            for col, (code, name) in scenario_meta.items():
                val = round(float(r[col]), 2)
                sc_id = f"sc_{d.strftime('%Y%m%d')}_{code}_{self.run_id}"
                scenario_rows.append({
                    "scenario_id": sc_id,
                    "date": d,
                    "scenario_code": code,
                    "scenario_name": name,
                    "as_of_date": self.as_of_date,
                    "run_id": self.run_id,
                    "pred_net": val,
                    "is_cash_deficit": val < 0
                })
        df_sc_insert = pd.DataFrame(scenario_rows)

        # 3. Ghi vào cơ sở dữ liệu với Transaction & Idempotency
        with self.engine.begin() as conn:
            # Xóa các bản ghi cũ của cùng as_of_date để đảm bảo không trùng lặp
            conn.execute(
                text("DELETE FROM gold.fact_cashflow_forecast WHERE as_of_date = :as_of"),
                {"as_of": self.as_of_date}
            )
            conn.execute(
                text("DELETE FROM gold.fact_cashflow_scenarios WHERE as_of_date = :as_of"),
                {"as_of": self.as_of_date}
            )

            df_fc_insert.to_sql("fact_cashflow_forecast", conn, schema="gold", if_exists="append", index=False)
            df_sc_insert.to_sql("fact_cashflow_scenarios", conn, schema="gold", if_exists="append", index=False)

        self.log_step("SYNC_DB", f"Nap thanh cong {len(df_fc_insert)} dong vao gold.fact_cashflow_forecast!")
        self.log_step("SYNC_DB", f"Nap thanh cong {len(df_sc_insert)} dong vao gold.fact_cashflow_scenarios!")

        return {
            "forecast_count": len(df_fc_insert),
            "scenarios_count": len(df_sc_insert),
            "run_id": self.run_id
        }

    def export_subproject_interface(self) -> str:
        """Xuất file Parquet giao tiếp cho Subproject 02 (Liquidity Optimization)."""
        self.log_step("EXPORT_OPT", "Xuat du lieu giao tiep cho Subproject 02. Liquidity_Optimization...")

        query = """
        SELECT 
            date,
            pred_net,
            pred_inflow,
            pred_outflow,
            pred_net_lower_90,
            pred_net_upper_90
        FROM gold.fact_cashflow_forecast
        WHERE as_of_date = :as_of
        ORDER BY date ASC;
        """
        df_opt = pd.read_sql(text(query), self.engine.connect(), params={"as_of": self.as_of_date})
        out_path = os.path.join(self.processed_dir, "forecast_for_optimization.parquet")
        df_opt.to_parquet(out_path, index=False)

        self.log_step("EXPORT_OPT", f"Da luu {out_path} ({len(df_opt)} dong). San sang cho Subproject 02!")
        return out_path

    def run_pipeline(self) -> dict:
        """Điều phối toàn bộ Pipeline Tích hợp Pha 5."""
        print("=" * 70)
        print("🔗 BẮT ĐẦU PHA 5: INTEGRATION & POWER BI DEPLOYMENT")
        print("=" * 70)

        self.init_database_schema()
        sync_result = self.sync_to_postgresql()
        opt_path = self.export_subproject_interface()

        print("\n" + "=" * 70)
        print("✅ HOÀN THÀNH PHA 5: TÍCH HỢP DATA WAREHOUSE THÀNH CÔNG RỰC RỠ!")
        print("=" * 70)

        return {
            "sync": sync_result,
            "optimization_parquet": opt_path
        }


if __name__ == "__main__":
    integrator = CashflowIntegrator()
    integrator.run_pipeline()
