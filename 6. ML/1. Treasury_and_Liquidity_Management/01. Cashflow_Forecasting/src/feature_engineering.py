"""
Module: feature_engineering.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Kỹ nghệ đặc trưng (Feature Engineering) cho bài toán dự báo dòng tiền ngắn hạn:
    - Lag features (1, 7, 14, 21, 28, 30 ngày)
    - Rolling window statistics (7, 14, 30 ngày) với shift(1) chống rò rỉ dữ liệu
    - Lịch biểu & Quy luật kinh doanh (Lương 10-15, Thuế 20-25, Tết Nguyên Đán, Cuối tuần)
    - Biến ngoại sinh (Exogenous variables): Lịch đáo hạn hóa đơn AR/AP từ PostgreSQL
    - Xuất dữ liệu sẵn sàng cho LightGBM / XGBoost vào data/processed/featured_cashflow.parquet
"""

import os
import sys
import logging
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

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CashflowFeatureEngineer")


class CashflowFeatureEngineer:
    def __init__(
        self,
        daily_parquet_path: str = None,
        db_url: str = "postgresql+psycopg2://dev:Inda1234@127.0.0.1:5432/data_warehouse"
    ):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if daily_parquet_path is None:
            self.daily_parquet_path = os.path.join(base_dir, "data", "processed", "daily_cashflow.parquet")
        else:
            self.daily_parquet_path = daily_parquet_path

        self.db_url = db_url
        self.df = None
        self.featured_df = None

    def log_step(self, step_name: str, message: str):
        print(f"\n>>> [TASK] {step_name.upper()}: {message}")
        logger.info(f"[{step_name}] {message}")

    def load_data(self) -> pd.DataFrame:
        """Đọc bảng dữ liệu chuỗi thời gian đã làm sạch từ Pha 1."""
        self.log_step("LOAD", f"Doc du lieu chuoi ngay tu {self.daily_parquet_path}...")
        if not os.path.exists(self.daily_parquet_path):
            raise FileNotFoundError(f"Khong tim thay tep: {self.daily_parquet_path}")

        self.df = pd.read_parquet(self.daily_parquet_path)
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df = self.df.sort_values('date').reset_index(drop=True)
        self.log_step("LOAD", f"Da doc thanh cong: {len(self.df)} ngay (tu {self.df['date'].min().strftime('%Y-%m-%d')} den {self.df['date'].max().strftime('%Y-%m-%d')}).")
        return self.df

    def extract_exogenous_ar_ap(self) -> pd.DataFrame:
        """
        Trích xuất và gom nhóm lịch đáo hạn hóa đơn AR và AP từ PostgreSQL Data Warehouse.
        Giả định kỳ hạn thanh toán bình quân ngành gỗ:
        - Khách hàng (AR): 30 ngày kể từ ngày xuất hóa đơn (invoice_date)
        - Nhà cung cấp (AP): 45 ngày kể từ ngày nhận hàng/hóa đơn
        """
        self.log_step("EXOGENOUS", "Trich xuat lich hoa don AR/AP tu PostgreSQL lam bien ngoai sinh...")
        engine = create_engine(self.db_url)

        # 1. Trích xuất hóa đơn Phải thu (AR)
        q_ar = text("""
            SELECT 
                invoice_date,
                debit_amount as amount
            FROM silver.fact_accountsreceivable
            WHERE invoice_date IS NOT NULL 
              AND debit_amount > 0;
        """)

        # 2. Trích xuất hóa đơn Phải trả (AP)
        q_ap = text("""
            SELECT 
                invoice_date,
                credit_amount as amount
            FROM silver.fact_accountspayable
            WHERE invoice_date IS NOT NULL 
              AND credit_amount > 0;
        """)

        with engine.connect() as conn:
            ar_df = pd.read_sql(q_ar, conn)
            ap_df = pd.read_sql(q_ap, conn)

        # Chuẩn hóa ngày hóa đơn
        ar_df['invoice_date'] = pd.to_datetime(ar_df['invoice_date'])
        ap_df['invoice_date'] = pd.to_datetime(ap_df['invoice_date'])

        # Tính ngày đến hạn ước tính (Expected Due Date)
        ar_df['expected_due_date'] = ar_df['invoice_date'] + pd.Timedelta(days=30)
        ap_df['expected_due_date'] = ap_df['invoice_date'] + pd.Timedelta(days=45)

        # Gom nhóm tổng số tiền đến hạn theo từng ngày
        ar_daily = ar_df.groupby('expected_due_date')['amount'].sum().reset_index()
        ar_daily.rename(columns={'expected_due_date': 'date', 'amount': 'ar_expected_due_today'}, inplace=True)

        ap_daily = ap_df.groupby('expected_due_date')['amount'].sum().reset_index()
        ap_daily.rename(columns={'expected_due_date': 'date', 'amount': 'ap_expected_due_today'}, inplace=True)

        # Hợp nhất với trục 212 ngày của dòng tiền
        merged = pd.merge(self.df, ar_daily, on='date', how='left').fillna({'ar_expected_due_today': 0.0})
        merged = pd.merge(merged, ap_daily, on='date', how='left').fillna({'ap_expected_due_today': 0.0})

        # Tính tổng tiền công nợ đến hạn trong 7 ngày tới (Forward Rolling Sum)
        # Sử dụng rolling window lộn ngược (reverse rolling) để phản ánh "tuần tới sẽ có bao nhiêu tiền đến hạn"
        merged['ar_expected_due_next_7d'] = merged['ar_expected_due_today'].iloc[::-1].rolling(window=7, min_periods=1).sum().iloc[::-1]
        merged['ap_expected_due_next_7d'] = merged['ap_expected_due_today'].iloc[::-1].rolling(window=7, min_periods=1).sum().iloc[::-1]

        self.df = merged
        self.log_step("EXOGENOUS", "Tich hop thanh cong 4 dac trung ngoai sinh: AR today, AR next 7d, AP today, AP next 7d.")
        return self.df

    def create_lag_features(self, lags=(1, 7, 14, 21, 28, 30)) -> pd.DataFrame:
        """
        Tạo các đặc trưng độ trễ (Lags) cho Inflow, Outflow và Net Cashflow.
        Độ trễ phản ánh tính tự tương quan (Autocorrelation) và chu kỳ lặp lại theo tuần/tháng.
        """
        self.log_step("LAGS", f"Tao cac dac trung Do tre (Lags: {lags}) cho Inflow, Outflow va Net Cashflow...")
        df = self.df.copy()

        for lag in lags:
            df[f'inflow_lag_{lag}'] = df['inflow'].shift(lag)
            df[f'outflow_lag_{lag}'] = df['outflow'].shift(lag)
            df[f'net_lag_{lag}'] = df['net_cashflow'].shift(lag)

        self.df = df
        self.log_step("LAGS", f"Da tao thanh cong {len(lags) * 3} dac trung Do tre.")
        return self.df

    def create_rolling_features(self, windows=(7, 14, 30)) -> pd.DataFrame:
        """
        Tạo các đặc trưng thống kê trượt (Rolling Mean, Std, Min, Max).
        LƯU Ý: Phải gọi .shift(1) trước khi .rolling() để TRÁNH RÒ RỈ DỮ LIỆU TƯƠNG LAI (No Data Leakage).
        Tại ngày t, model chỉ được biết thống kê của các ngày từ t-1 trở về trước!
        """
        self.log_step("ROLLING", f"Tao dac trung Thong ke truot (Windows: {windows}) voi shift(1) phong ngua Data Leakage...")
        df = self.df.copy()

        # Áp dụng shift(1) để lấy giá trị quá khứ
        inflow_past = df['inflow'].shift(1)
        outflow_past = df['outflow'].shift(1)
        net_past = df['net_cashflow'].shift(1)

        for w in windows:
            # Inflow rolling
            df[f'inflow_rolling_mean_{w}d'] = inflow_past.rolling(w, min_periods=1).mean()
            df[f'inflow_rolling_std_{w}d'] = inflow_past.rolling(w, min_periods=1).std().fillna(0.0)
            df[f'inflow_rolling_min_{w}d'] = inflow_past.rolling(w, min_periods=1).min()
            df[f'inflow_rolling_max_{w}d'] = inflow_past.rolling(w, min_periods=1).max()

            # Outflow rolling
            df[f'outflow_rolling_mean_{w}d'] = outflow_past.rolling(w, min_periods=1).mean()
            df[f'outflow_rolling_std_{w}d'] = outflow_past.rolling(w, min_periods=1).std().fillna(0.0)
            df[f'outflow_rolling_min_{w}d'] = outflow_past.rolling(w, min_periods=1).min()
            df[f'outflow_rolling_max_{w}d'] = outflow_past.rolling(w, min_periods=1).max()

            # Net cashflow rolling
            df[f'net_rolling_mean_{w}d'] = net_past.rolling(w, min_periods=1).mean()
            df[f'net_rolling_std_{w}d'] = net_past.rolling(w, min_periods=1).std().fillna(0.0)

        self.df = df
        self.log_step("ROLLING", f"Da tao thanh cong {len(windows) * 10} dac trung thong ke truot.")
        return self.df

    def create_calendar_and_business_features(self) -> pd.DataFrame:
        """
        Tạo các đặc trưng Lịch biểu và Quy luật kinh doanh kế toán:
        - Chu kỳ tuần, tháng, quý
        - Kỳ chi lương (10-15), Kỳ nộp thuế (20-25)
        - Kỳ nghỉ Tết Nguyên Đán 2026 (14/02 - 22/02/2026)
        - Biến đổi lượng giác Cyclical Encoding (sin/cos)
        """
        self.log_step("CALENDAR", "Tao cac dac trung Lich bieu & Quy luat kinh doanh GML...")
        df = self.df.copy()

        dates = df['date'].dt

        # 1. Các trường thời gian cơ bản
        df['day_of_week'] = dates.dayofweek
        df['day_of_month'] = dates.day
        df['day_of_year'] = dates.dayofyear
        df['week_of_year'] = dates.isocalendar().week.astype(int)
        df['month'] = dates.month
        df['quarter'] = dates.quarter

        # 2. Cờ đánh dấu mốc thời gian
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_month_start'] = (df['day_of_month'] <= 3).astype(int)
        df['is_month_end'] = (df['day_of_month'] >= 28).astype(int)
        df['is_quarter_end'] = (df['month'].isin([3, 6, 9, 12]) & (df['day_of_month'] >= 25)).astype(int)

        # 3. Đặc thù nghiệp vụ kế toán Gỗ Minh Long
        # Kỳ chi lương: Ngày 10 - 15 hàng tháng
        df['is_salary_period'] = df['day_of_month'].between(10, 15).astype(int)

        # Kỳ nộp thuế: Ngày 20 - 25 hàng tháng
        df['is_tax_period'] = df['day_of_month'].between(20, 25).astype(int)

        # Kỳ nghỉ Tết Nguyên Đán 2026 (14/02/2026 - 22/02/2026)
        tet_start = pd.to_datetime('2026-02-14')
        tet_end = pd.to_datetime('2026-02-22')
        df['is_tet_holiday'] = df['date'].between(tet_start, tet_end).astype(int)

        # 4. Cyclical Encodings (Chu kỳ lượng giác liên tục)
        # Giúp Tree-based model hiểu rằng Chủ nhật (6) và Thứ hai (0) liền kề nhau
        df['sin_day_of_week'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['cos_day_of_week'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
        df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)

        # 5. Cờ đánh dấu dữ liệu hoàn thiện (Warm-up Period: 30 ngày đầu để lấp đầy Lags)
        df['is_trainable'] = (df.index >= 30).astype(int)

        # Điền số 0 cho các giá trị NaN ở 30 ngày đầu do độ trễ
        self.featured_df = df.fillna(0.0)
        self.log_step("CALENDAR", f"Da tao xong toan bo dac trung Lich bieu. Tong cong: {len(self.featured_df.columns)} cot.")
        return self.featured_df

    def save_artifacts(self, output_dir: str = None) -> dict:
        """Lưu bảng đặc trưng vào data/processed/featured_cashflow.parquet và .csv."""
        self.log_step("SAVE", "Luu tru Feature Matrix vao thu muc data/processed/...")
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, "data", "processed")

        os.makedirs(output_dir, exist_ok=True)

        paths = {
            "featured_parquet": os.path.join(output_dir, "featured_cashflow.parquet"),
            "featured_csv": os.path.join(output_dir, "featured_cashflow.csv")
        }

        self.featured_df.to_parquet(paths["featured_parquet"], index=False, engine='pyarrow')
        self.featured_df.to_csv(paths["featured_csv"], index=False, encoding='utf-8-sig')

        for name, p in paths.items():
            size_kb = os.path.getsize(p) / 1024
            self.log_step("SAVE", f"Da tao: {os.path.basename(p)} ({size_kb:.1f} KB, {len(self.featured_df)} dong, {len(self.featured_df.columns)} cot).")

        return paths

    def run_pipeline(self) -> tuple[pd.DataFrame, dict]:
        """Điều phối toàn bộ Pipeline Feature Engineering."""
        print("=" * 70)
        print("🚀 BẮT ĐẦU PHA 2: FEATURE ENGINEERING - CASHFLOW FORECASTING")
        print("=" * 70)

        self.load_data()
        self.extract_exogenous_ar_ap()
        self.create_lag_features()
        self.create_rolling_features()
        self.create_calendar_and_business_features()
        paths = self.save_artifacts()

        print("\n" + "=" * 70)
        print("✅ HOÀN THÀNH PHA 2: FEATURE ENGINEERING THÀNH CÔNG RỰC RỠ!")
        print("=" * 70)

        return self.featured_df, paths


if __name__ == "__main__":
    engineer = CashflowFeatureEngineer()
    engineer.run_pipeline()
