"""
Module: data_preparation.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Trích xuất dữ liệu chuỗi thời gian từ PostgreSQL (silver.fact_cashflow),
    chuẩn hóa kiểu dữ liệu, khử nhiễu giao dịch nội bộ (CTNB),
    gom nhóm theo ngày (Daily Continuity 212 ngày từ 01/01/2026 đến 31/07/2026),
    bóc tách dòng tiền theo tài khoản đối ứng và xuất ra định dạng Parquet/CSV.
"""

import os
import sys
import logging
from datetime import datetime

# Đảm bảo stdout luôn là UTF-8 trên Windows PowerShell
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CashflowDataPreparator")


class CashflowDataPreparator:
    def __init__(
        self,
        db_url: str = "postgresql+psycopg2://dev:Inda1234@127.0.0.1:5432/data_warehouse",
        start_date: str = "2026-01-01",
        end_date: str = "2026-07-31"
    ):
        self.db_url = db_url
        self.start_date = start_date
        self.end_date = end_date
        self.engine = None
        self.raw_df = None
        self.cleaned_df = None
        self.daily_df = None
        self.detailed_daily_df = None

    def log_step(self, step_name: str, message: str):
        print(f"\n>>> [TASK] {step_name.upper()}: {message}")
        logger.info(f"[{step_name}] {message}")

    def connect(self):
        """Khởi tạo kết nối tới cơ sở dữ liệu PostgreSQL."""
        self.log_step("CONNECT", "Khoi tao ket noi toi PostgreSQL Data Warehouse...")
        try:
            self.engine = create_engine(self.db_url)
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT 1;")).fetchone()
                if res and res[0] == 1:
                    self.log_step("CONNECT", "Ket noi thanh cong toi schema silver!")
        except Exception as e:
            logger.error(f"Loi ket noi Database: {e}")
            raise e

    def extract_raw_cashflow(self) -> pd.DataFrame:
        """Trích xuất dữ liệu phát sinh sổ cái TK 111 và TK 112."""
        self.log_step("EXTRACT", f"Trich xuat giao dich fact_cashflow tu {self.start_date} den {self.end_date}...")
        query = text("""
            SELECT 
                posting_date,
                voucher_no,
                account_no,
                reciprocal_account,
                partner_code,
                description,
                debit_amount,
                credit_amount
            FROM silver.fact_cashflow
            WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
              AND posting_date >= :start_date
              AND posting_date <= :end_date
            ORDER BY posting_date, id;
        """)

        with self.engine.connect() as conn:
            self.raw_df = pd.read_sql(query, conn, params={"start_date": self.start_date, "end_date": self.end_date})

        self.log_step("EXTRACT", f"Trich xuat hoan tat: {len(self.raw_df):,} ban ghi.")
        return self.raw_df

    def clean_and_filter_ctnb(self) -> pd.DataFrame:
        """Loại bỏ giao dịch chuyển tiền nội bộ (CTNB) và chuẩn hóa kiểu dữ liệu."""
        self.log_step("CLEAN", "Bat dau lam sach du lieu va loc bo giao dich CTNB...")
        df = self.raw_df.copy()

        # 1. Chuẩn hóa ngày tháng và số tiền
        df['posting_date'] = pd.to_datetime(df['posting_date'])
        df['debit_amount'] = pd.to_numeric(df['debit_amount'], errors='coerce').fillna(0.0)
        df['credit_amount'] = pd.to_numeric(df['credit_amount'], errors='coerce').fillna(0.0)

        total_rows_before = len(df)
        total_inflow_before = df['debit_amount'].sum()
        total_outflow_before = df['credit_amount'].sum()

        # 2. Nhận diện và lọc bỏ CTNB
        # Bút toán có voucher_no bắt đầu bằng CTNB
        is_ctnb = df['voucher_no'].str.upper().str.startswith('CTNB', na=False)
        ctnb_count = is_ctnb.sum()

        self.cleaned_df = df[~is_ctnb].copy()

        total_rows_after = len(self.cleaned_df)
        total_inflow_after = self.cleaned_df['debit_amount'].sum()
        total_outflow_after = self.cleaned_df['credit_amount'].sum()

        self.log_step("CLEAN", f"So ban ghi ban dau: {total_rows_before:,}")
        self.log_step("CLEAN", f"So ban ghi CTNB da loai bo: {ctnb_count:,} ban ghi.")
        self.log_step("CLEAN", f"So ban ghi hop le giu lai: {total_rows_after:,}")
        self.log_step("CLEAN", f"Tong Inflow (sau loc): {total_inflow_after / 1e9:,.2f} Ty VND")
        self.log_step("CLEAN", f"Tong Outflow (sau loc): {total_outflow_after / 1e9:,.2f} Ty VND")

        return self.cleaned_df

    def aggregate_daily(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Gom nhóm dữ liệu theo từng ngày (Daily), tạo chuỗi thời gian liên tục 100%
        không đứt gãy từ start_date đến end_date.
        """
        self.log_step("AGGREGATE", "Gom nhom theo ngay va tao chuoi thoi gian lien tuc...")
        df = self.cleaned_df.copy()

        # 1. Chuẩn bị trục thời gian đầy đủ (Full Calendar Range)
        full_date_range = pd.date_range(start=self.start_date, end=self.end_date, freq='D', name='date')
        total_days = len(full_date_range)
        self.log_step("AGGREGATE", f"Truc thoi gian yeu cau: {total_days} ngay (tu {self.start_date} den {self.end_date}).")

        # 2. Gom nhóm tổng quát (inflow, outflow, net_cashflow)
        daily_summary = df.groupby('posting_date').agg(
            inflow=('debit_amount', 'sum'),
            outflow=('credit_amount', 'sum'),
            tx_count=('debit_amount', 'count')
        ).reset_index().rename(columns={'posting_date': 'date'})

        # Reindex để đảm bảo 100% các ngày trong kỳ đều có mặt
        daily_summary['date'] = pd.to_datetime(daily_summary['date'])
        daily_summary = daily_summary.set_index('date').reindex(full_date_range).fillna(0.0).reset_index()
        daily_summary.rename(columns={'index': 'date'}, inplace=True)

        # Tính Net Cashflow
        daily_summary['net_cashflow'] = daily_summary['inflow'] - daily_summary['outflow']

        # Thêm các cờ lịch cơ bản
        daily_summary['day_of_week'] = daily_summary['date'].dt.dayofweek
        daily_summary['day_name'] = daily_summary['date'].dt.day_name()
        daily_summary['month'] = daily_summary['date'].dt.month
        daily_summary['is_weekend'] = daily_summary['day_of_week'].isin([5, 6]).astype(int)

        self.daily_df = daily_summary

        # 3. Gom nhóm chi tiết theo tài khoản đối ứng (Breakdown)
        # Phân loại luồng tiền theo VAS / Chuẩn mực dòng tiền
        df['recip'] = df['reciprocal_account'].fillna('').astype(str).str.strip()

        # Thu tiền:
        df['inflow_operating_customers'] = np.where(df['recip'].str.startswith(('131', '511')), df['debit_amount'], 0.0)
        df['inflow_financing_borrowing'] = np.where(df['recip'].str.startswith('341'), df['debit_amount'], 0.0)
        df['inflow_interest_received'] = np.where(df['recip'].str.startswith('515'), df['debit_amount'], 0.0)
        df['inflow_other'] = df['debit_amount'] - (df['inflow_operating_customers'] + df['inflow_financing_borrowing'] + df['inflow_interest_received'])

        # Chi tiền:
        df['outflow_operating_suppliers'] = np.where(df['recip'].str.startswith(('331', '152', '156')), df['credit_amount'], 0.0)
        df['outflow_operating_salary'] = np.where(df['recip'].str.startswith('334'), df['credit_amount'], 0.0)
        df['outflow_operating_tax'] = np.where(df['recip'].str.startswith('333'), df['credit_amount'], 0.0)
        df['outflow_financing_repayment'] = np.where(df['recip'].str.startswith('341'), df['credit_amount'], 0.0)
        df['outflow_financing_interest'] = np.where(df['recip'].str.startswith('635'), df['credit_amount'], 0.0)
        df['outflow_other'] = df['credit_amount'] - (
            df['outflow_operating_suppliers'] + df['outflow_operating_salary'] + 
            df['outflow_operating_tax'] + df['outflow_financing_repayment'] + 
            df['outflow_financing_interest']
        )

        detailed_agg = df.groupby('posting_date').agg({
            'debit_amount': 'sum',
            'credit_amount': 'sum',
            'inflow_operating_customers': 'sum',
            'inflow_financing_borrowing': 'sum',
            'inflow_interest_received': 'sum',
            'inflow_other': 'sum',
            'outflow_operating_suppliers': 'sum',
            'outflow_operating_salary': 'sum',
            'outflow_operating_tax': 'sum',
            'outflow_financing_repayment': 'sum',
            'outflow_financing_interest': 'sum',
            'outflow_other': 'sum'
        }).reset_index().rename(columns={
            'posting_date': 'date',
            'debit_amount': 'inflow_total',
            'credit_amount': 'outflow_total'
        })

        detailed_agg['date'] = pd.to_datetime(detailed_agg['date'])
        detailed_agg = detailed_agg.set_index('date').reindex(full_date_range).fillna(0.0).reset_index()
        detailed_agg.rename(columns={'index': 'date'}, inplace=True)
        detailed_agg['net_cashflow'] = detailed_agg['inflow_total'] - detailed_agg['outflow_total']

        self.detailed_daily_df = detailed_agg

        self.log_step("AGGREGATE", f"Gom nhom thanh cong: {len(self.daily_df)} ngay hop le, 0 ngay bi thieu.")
        return self.daily_df, self.detailed_daily_df

    def save_artifacts(self, output_dir: str = None) -> dict:
        """Lưu trữ kết quả chuẩn hóa vào thư mục data/processed/."""
        self.log_step("SAVE", "Luu tru ket qua ra thu muc data/processed/...")
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, "data", "processed")

        os.makedirs(output_dir, exist_ok=True)

        paths = {
            "daily_parquet": os.path.join(output_dir, "daily_cashflow.parquet"),
            "daily_csv": os.path.join(output_dir, "daily_cashflow.csv"),
            "detailed_parquet": os.path.join(output_dir, "daily_cashflow_detailed.parquet"),
            "detailed_csv": os.path.join(output_dir, "daily_cashflow_detailed.csv")
        }

        # Lưu bản tóm tắt
        self.daily_df.to_parquet(paths["daily_parquet"], index=False, engine='pyarrow')
        self.daily_df.to_csv(paths["daily_csv"], index=False, encoding='utf-8-sig')

        # Lưu bản chi tiết
        self.detailed_daily_df.to_parquet(paths["detailed_parquet"], index=False, engine='pyarrow')
        self.detailed_daily_df.to_csv(paths["detailed_csv"], index=False, encoding='utf-8-sig')

        for name, p in paths.items():
            size_kb = os.path.getsize(p) / 1024
            self.log_step("SAVE", f"Da tao: {os.path.basename(p)} ({size_kb:.1f} KB)")

        return paths

    def run_pipeline(self) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
        """Điều phối toàn bộ Pipeline tiền xử lý dữ liệu."""
        print("=" * 70)
        print("🚀 BẮT ĐẦU PHA 1: DATA PREPARATION - CASHFLOW FORECASTING")
        print("=" * 70)

        self.connect()
        self.extract_raw_cashflow()
        self.clean_and_filter_ctnb()
        self.aggregate_daily()
        paths = self.save_artifacts()

        print("\n" + "=" * 70)
        print("✅ HOÀN THÀNH PHA 1: DATA PREPARATION THÀNH CÔNG RỰC RỠ!")
        print("=" * 70)

        return self.daily_df, self.detailed_daily_df, paths


if __name__ == "__main__":
    preparator = CashflowDataPreparator()
    preparator.run_pipeline()
