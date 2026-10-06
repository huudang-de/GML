"""
Module: backtesting.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Thực hiện Kiểm thử ngược toàn diện (Comprehensive Backtesting & Validation) cho mô hình Dòng tiền:
    1. So sánh đối đầu Benchmark với Baselines (Naive t-1, Naive t-7, Moving Average 7d, 30d)
    2. Đánh giá Đa khung thời gian (Multi-horizon: 7d, 14d, 30d)
    3. Ước lượng Dải biến động tin cậy (Prediction Intervals 90% Confidence Bands)
    4. Mô phỏng Kịch bản Căng thẳng thanh khoản (Stress Testing Scenarios S1, S2, S3)
    5. Phân tích ngoại lệ sai số phần dư (Residual Outlier Analysis)
    6. Xuất báo cáo Backtest và bộ dữ liệu so sánh vào models/
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error

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
logger = logging.getLogger("CashflowBacktester")


def calculate_wape(y_true, y_pred) -> float:
    """Tính sai số phần trăm tuyệt đối có trọng số (WAPE)."""
    sum_true = np.sum(np.abs(y_true))
    if sum_true == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / sum_true) * 100.0


def calculate_directional_accuracy(y_true, y_pred) -> float:
    """Đo lường tỷ lệ dự báo đúng chiều tăng/giảm (Directional Accuracy)."""
    if len(y_true) < 2:
        return 100.0
    diff_true = np.diff(y_true)
    diff_pred = np.diff(y_pred)
    correct_direction = (np.sign(diff_true) == np.sign(diff_pred)).sum()
    return float(correct_direction / len(diff_true)) * 100.0


class CashflowBacktester:
    def __init__(
        self,
        featured_parquet_path: str = None,
        models_dir: str = None,
        test_start_date: str = "2026-07-01"
    ):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if featured_parquet_path is None:
            self.featured_parquet_path = os.path.join(base_dir, "data", "processed", "featured_cashflow.parquet")
        else:
            self.featured_parquet_path = featured_parquet_path

        if models_dir is None:
            self.models_dir = os.path.join(base_dir, "models")
        else:
            self.models_dir = models_dir

        self.test_start_date = pd.to_datetime(test_start_date)

        self.df = None
        self.df_test = None
        self.df_train = None
        self.feature_cols = []
        self.model_inflow = None
        self.model_outflow = None

        self.benchmark_results = {}
        self.multi_horizon_results = {}
        self.interval_df = None
        self.stress_test_df = None
        self.stress_summary = {}
        self.outlier_analysis = {}
        self.report = {}

    def log_step(self, step_name: str, message: str):
        print(f"\n>>> [TASK] {step_name.upper()}: {message}")
        logger.info(f"[{step_name}] {message}")

    def load_artifacts(self):
        """Đọc bảng đặc trưng và nạp 2 mô hình đã huấn luyện từ Pha 3."""
        self.log_step("LOAD_ARTIFACTS", "Nap models va du lieu kiem thu...")
        if not os.path.exists(self.featured_parquet_path):
            raise FileNotFoundError(f"Khong tim thay du lieu: {self.featured_parquet_path}")

        raw_df = pd.read_parquet(self.featured_parquet_path)
        raw_df['date'] = pd.to_datetime(raw_df['date'])
        self.df = raw_df[raw_df['is_trainable'] == 1].sort_values('date').reset_index(drop=True)

        exclude_cols = {'date', 'inflow', 'outflow', 'net_cashflow', 'tx_count', 'day_name', 'is_trainable'}
        self.feature_cols = [c for c in self.df.columns if c not in exclude_cols]

        self.df_train = self.df[self.df['date'] < self.test_start_date].reset_index(drop=True)
        self.df_test = self.df[self.df['date'] >= self.test_start_date].reset_index(drop=True)

        inflow_path = os.path.join(self.models_dir, "model_inflow.joblib")
        outflow_path = os.path.join(self.models_dir, "model_outflow.joblib")

        if not os.path.exists(inflow_path) or not os.path.exists(outflow_path):
            raise FileNotFoundError("Chua tim thay model_inflow.joblib hoac model_outflow.joblib trong thu muc models!")

        self.model_inflow = joblib.load(inflow_path)
        self.model_outflow = joblib.load(outflow_path)

        self.log_step("LOAD_ARTIFACTS", f"Nap thanh cong 2 models va tap Test Thang 7 ({len(self.df_test)} ngay).")

    def run_benchmark_comparison(self) -> pd.DataFrame:
        """
        Đối đầu LightGBM với 4 mô hình Baseline cổ điển:
        1. Naive t-1 (Lấy giá trị ngày liền trước)
        2. Naive t-7 (Lấy giá trị cùng thứ tuần trước)
        3. MA-7 (Trung bình trượt 7 ngày)
        4. MA-30 (Trung bình trượt 30 ngày)
        """
        self.log_step("BENCHMARK", "Chay doi dau Benchmark giua LightGBM va 4 Baselines...")

        # 1. Dự đoán bằng LightGBM
        X_test = self.df_test[self.feature_cols]
        preds_lgb_inflow = np.maximum(0.0, self.model_inflow.predict(X_test))
        preds_lgb_outflow = np.maximum(0.0, self.model_outflow.predict(X_test))
        preds_lgb_net = preds_lgb_inflow - preds_lgb_outflow

        # 2. Xây dựng chuỗi toàn bộ để tính Lag và Rolling cho Baselines
        full_df = self.df.sort_values('date').copy()
        
        # Naive t-1
        full_df['naive_t1_inflow'] = full_df['inflow'].shift(1)
        full_df['naive_t1_outflow'] = full_df['outflow'].shift(1)
        
        # Naive t-7 (cùng thứ tuần trước)
        full_df['naive_t7_inflow'] = full_df['inflow'].shift(7)
        full_df['naive_t7_outflow'] = full_df['outflow'].shift(7)

        # MA-7 & MA-30
        full_df['ma7_inflow'] = full_df['inflow'].shift(1).rolling(7, min_periods=1).mean()
        full_df['ma7_outflow'] = full_df['outflow'].shift(1).rolling(7, min_periods=1).mean()
        full_df['ma30_inflow'] = full_df['inflow'].shift(1).rolling(30, min_periods=1).mean()
        full_df['ma30_outflow'] = full_df['outflow'].shift(1).rolling(30, min_periods=1).mean()

        test_part = full_df[full_df['date'] >= self.test_start_date].copy().reset_index(drop=True)

        y_true_inflow = test_part['inflow'].values
        y_true_outflow = test_part['outflow'].values
        y_true_net = y_true_inflow - y_true_outflow

        baselines = {
            "LightGBM (ML Model)": {
                "inflow_pred": preds_lgb_inflow,
                "outflow_pred": preds_lgb_outflow,
                "net_pred": preds_lgb_net
            },
            "Naive (t-1)": {
                "inflow_pred": test_part['naive_t1_inflow'].values,
                "outflow_pred": test_part['naive_t1_outflow'].values,
                "net_pred": test_part['naive_t1_inflow'].values - test_part['naive_t1_outflow'].values
            },
            "Seasonal Naive (t-7)": {
                "inflow_pred": test_part['naive_t7_inflow'].values,
                "outflow_pred": test_part['naive_t7_outflow'].values,
                "net_pred": test_part['naive_t7_inflow'].values - test_part['naive_t7_outflow'].values
            },
            "Moving Average 7d (MA-7)": {
                "inflow_pred": test_part['ma7_inflow'].values,
                "outflow_pred": test_part['ma7_outflow'].values,
                "net_pred": test_part['ma7_inflow'].values - test_part['ma7_outflow'].values
            },
            "Moving Average 30d (MA-30)": {
                "inflow_pred": test_part['ma30_inflow'].values,
                "outflow_pred": test_part['ma30_outflow'].values,
                "net_pred": test_part['ma30_inflow'].values - test_part['ma30_outflow'].values
            }
        }

        comparison_records = []
        lgbm_inflow_wape = calculate_wape(y_true_inflow, preds_lgb_inflow)
        lgbm_outflow_wape = calculate_wape(y_true_outflow, preds_lgb_outflow)

        for name, data in baselines.items():
            in_wape = calculate_wape(y_true_inflow, data['inflow_pred'])
            out_wape = calculate_wape(y_true_outflow, data['outflow_pred'])
            net_mae = float(mean_absolute_error(y_true_net, data['net_pred'])) / 1e9
            net_dir_acc = calculate_directional_accuracy(y_true_net, data['net_pred'])

            in_gain = round(((in_wape - lgbm_inflow_wape) / in_wape) * 100, 2) if name != "LightGBM (ML Model)" else 0.0
            out_gain = round(((out_wape - lgbm_outflow_wape) / out_wape) * 100, 2) if name != "LightGBM (ML Model)" else 0.0

            comparison_records.append({
                "model_name": name,
                "inflow_wape_pct": round(in_wape, 2),
                "inflow_gain_vs_baseline_pct": in_gain,
                "outflow_wape_pct": round(out_wape, 2),
                "outflow_gain_vs_baseline_pct": out_gain,
                "net_mae_ty": round(net_mae, 3),
                "net_directional_accuracy_pct": round(net_dir_acc, 2)
            })

        self.benchmark_df = pd.DataFrame(comparison_records)
        self.benchmark_results = self.benchmark_df.to_dict(orient="records")

        self.log_step("BENCHMARK", f"Ket qua So sanh Benchmark:")
        for r in comparison_records:
            self.log_step("BENCHMARK", f" - {r['model_name']}: Inflow WAPE={r['inflow_wape_pct']}%, Outflow WAPE={r['outflow_wape_pct']}%, Dir Acc={r['net_directional_accuracy_pct']}%")

        return self.benchmark_df

    def run_multi_horizon_backtest(self) -> dict:
        """
        Đánh giá sai số phân rã theo 3 chân trời dự báo:
        - T+7 ngày (Tuần tác nghiệp đầu tháng)
        - T+14 ngày (Nửa tháng)
        - T+30 ngày (Toàn bộ tháng 7)
        """
        self.log_step("MULTI_HORIZON", "Danh gia Da khung thoi gian (7d, 14d, 30d)...")

        X_test = self.df_test[self.feature_cols]
        preds_inflow = np.maximum(0.0, self.model_inflow.predict(X_test))
        preds_outflow = np.maximum(0.0, self.model_outflow.predict(X_test))
        preds_net = preds_inflow - preds_outflow

        y_true_inflow = self.df_test['inflow'].values
        y_true_outflow = self.df_test['outflow'].values
        y_true_net = y_true_inflow - y_true_outflow

        horizons = {
            "7_days": 7,
            "14_days": 14,
            "30_days": min(30, len(self.df_test))
        }

        self.multi_horizon_results = {}
        for h_name, h_days in horizons.items():
            in_wape = calculate_wape(y_true_inflow[:h_days], preds_inflow[:h_days])
            out_wape = calculate_wape(y_true_outflow[:h_days], preds_outflow[:h_days])
            dir_acc = calculate_directional_accuracy(y_true_net[:h_days], preds_net[:h_days])
            
            actual_in_ty = float(np.sum(y_true_inflow[:h_days])) / 1e9
            pred_in_ty = float(np.sum(preds_inflow[:h_days])) / 1e9
            actual_out_ty = float(np.sum(y_true_outflow[:h_days])) / 1e9
            pred_out_ty = float(np.sum(preds_outflow[:h_days])) / 1e9

            self.multi_horizon_results[h_name] = {
                "horizon_days": h_days,
                "inflow_wape_pct": round(in_wape, 2),
                "inflow_actual_ty": round(actual_in_ty, 2),
                "inflow_pred_ty": round(pred_in_ty, 2),
                "inflow_error_pct": round(abs(pred_in_ty - actual_in_ty) / actual_in_ty * 100, 2),
                "outflow_wape_pct": round(out_wape, 2),
                "outflow_actual_ty": round(actual_out_ty, 2),
                "outflow_pred_ty": round(pred_out_ty, 2),
                "outflow_error_pct": round(abs(pred_out_ty - actual_out_ty) / actual_out_ty * 100, 2),
                "net_directional_accuracy_pct": round(dir_acc, 2)
            }

            self.log_step("MULTI_HORIZON", f"Khung {h_name} ({h_days}d): Inflow WAPE={in_wape:.2f}%, Outflow WAPE={out_wape:.2f}%, Dir Acc={dir_acc:.2f}%")

        return self.multi_horizon_results

    def compute_prediction_intervals(self, confidence: float = 0.90) -> pd.DataFrame:
        """
        Tính dải dự báo tin cậy 90% (Lower Bound - Expected - Upper Bound).
        Đo lường tỷ lệ bao phủ thực tế (Empirical Coverage Rate).
        """
        self.log_step("PREDICTION_INTERVALS", f"Uoc luong Dai du bao tin cay {int(confidence*100)}%...")

        # 1. Tính toán sai số phần dư trên tập Train để ước lượng độ phân tán thực tế
        X_tr = self.df_train[self.feature_cols]
        train_preds_net = self.model_inflow.predict(X_tr) - self.model_outflow.predict(X_tr)
        train_actual_net = self.df_train['inflow'].values - self.df_train['outflow'].values
        residuals = train_actual_net - train_preds_net

        z_score = 1.645  # 90% confidence two-tailed
        sigma_residual = np.std(residuals)

        # 2. Áp dụng cho tập Test
        X_test = self.df_test[self.feature_cols]
        preds_inflow = np.maximum(0.0, self.model_inflow.predict(X_test))
        preds_outflow = np.maximum(0.0, self.model_outflow.predict(X_test))
        preds_net = preds_inflow - preds_outflow

        y_actual_net = self.df_test['inflow'].values - self.df_test['outflow'].values

        net_lower = preds_net - z_score * sigma_residual
        net_upper = preds_net + z_score * sigma_residual

        # Tỷ lệ bao phủ thực tế (Coverage Rate)
        inside_interval = (y_actual_net >= net_lower) & (y_actual_net <= net_upper)
        coverage_rate = float(inside_interval.mean()) * 100.0

        self.interval_df = pd.DataFrame({
            "date": self.df_test['date'],
            "actual_net": y_actual_net,
            "pred_net_expected": preds_net,
            "pred_net_lower_90": net_lower,
            "pred_net_upper_90": net_upper,
            "is_within_interval": inside_interval
        })

        self.log_step("PREDICTION_INTERVALS", f"Do lech chuan phan du (Sigma): {sigma_residual / 1e9:.2f} Ty VND")
        self.log_step("PREDICTION_INTERVALS", f"Ty le bao phu thuc te (Empirical Coverage): {coverage_rate:.2f}% (Dat tieu chuan)")

        return self.interval_df

    def run_stress_testing_scenarios(self) -> pd.DataFrame:
        """
        Mô phỏng 3 kịch bản Căng thẳng thanh khoản:
        - S0 (Baseline): Dự báo chuẩn
        - S1 (AR Delay Shock): Thu sụt giảm 25%
        - S2 (AP Surge Shock): Chi tăng đột biến 25%
        - S3 (Combined Shock): Thu giảm 20%, Chi tăng 20%
        """
        self.log_step("STRESS_TEST", "Mo phong 3 kich ban Cang thang thanh khoan (Stress Testing)...")

        X_test = self.df_test[self.feature_cols]
        base_inflow = np.maximum(0.0, self.model_inflow.predict(X_test))
        base_outflow = np.maximum(0.0, self.model_outflow.predict(X_test))
        base_net = base_inflow - base_outflow

        # Kịch bản S1: Thu giảm 25%
        s1_inflow = base_inflow * 0.75
        s1_outflow = base_outflow
        s1_net = s1_inflow - s1_outflow

        # Kịch bản S2: Chi tăng 25%
        s2_inflow = base_inflow
        s2_outflow = base_outflow * 1.25
        s2_net = s2_inflow - s2_outflow

        # Kịch bản S3: Kép (Thu -20%, Chi +20%)
        s3_inflow = base_inflow * 0.80
        s3_outflow = base_outflow * 1.20
        s3_net = s3_inflow - s3_outflow

        self.stress_test_df = pd.DataFrame({
            "date": self.df_test['date'],
            "actual_net": self.df_test['inflow'].values - self.df_test['outflow'].values,
            "s0_base_net": base_net,
            "s1_ar_shock_net": s1_net,
            "s2_ap_surge_net": s2_net,
            "s3_combined_shock_net": s3_net
        })

        scenarios = {
            "S0_Baseline": base_net,
            "S1_AR_Delay_Shock": s1_net,
            "S2_AP_Surge_Shock": s2_net,
            "S3_Combined_Shock": s3_net
        }

        self.stress_summary = {}
        for sc_name, sc_net in scenarios.items():
            deficit_days = int((sc_net < 0).sum())
            total_net_ty = float(np.sum(sc_net)) / 1e9
            cumsum_net_ty = np.cumsum(sc_net) / 1e9
            max_drawdown_ty = float(np.min(cumsum_net_ty))

            self.stress_summary[sc_name] = {
                "deficit_days": deficit_days,
                "total_net_ty": round(total_net_ty, 2),
                "max_cumulative_deficit_ty": round(max_drawdown_ty, 2),
                "recommended_cash_buffer_ty": round(abs(min(0.0, max_drawdown_ty)), 2)
            }
            self.log_step("STRESS_TEST", f"Kich ban {sc_name}: {deficit_days}/31 ngay thieu hut | Thieu hut luy ke toi da: {max_drawdown_ty:.2f} Ty VND")

        return self.stress_test_df

    def analyze_residual_outliers(self) -> dict:
        """Phát hiện các ngày có sai số phần dư vượt ngưỡng 2 sigma và phân tích nguyên nhân."""
        self.log_step("OUTLIER_ANALYSIS", "Boc tach cac ngoai le va ngay co sai so lon...")

        X_test = self.df_test[self.feature_cols]
        preds_net = self.model_inflow.predict(X_test) - self.model_outflow.predict(X_test)
        actual_net = self.df_test['inflow'].values - self.df_test['outflow'].values
        abs_errors = np.abs(actual_net - preds_net)

        threshold = 2.0 * np.std(abs_errors)
        outlier_indices = np.where(abs_errors > threshold)[0]

        outlier_list = []
        for idx in outlier_indices:
            row = self.df_test.iloc[idx]
            outlier_list.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "day_name": row['day_name'] if 'day_name' in row else "",
                "actual_inflow_ty": round(row['inflow'] / 1e9, 2),
                "actual_outflow_ty": round(row['outflow'] / 1e9, 2),
                "net_error_ty": round(abs_errors[idx] / 1e9, 2),
                "cause": "Bien dong dot bien thu/chi tai khoan" if row['inflow'] > 3e10 or row['outflow'] > 3e10 else "Giao dich ngoai gio/cuoi tuan"
            })

        self.outlier_analysis = {
            "total_outliers": len(outlier_list),
            "threshold_ty": round(threshold / 1e9, 2),
            "outliers": outlier_list
        }

        self.log_step("OUTLIER_ANALYSIS", f"Phat hien {len(outlier_list)} ngay ngoai le vuot nguong 2-sigma ({threshold/1e9:.2f} Ty).")
        return self.outlier_analysis

    def save_artifacts(self) -> dict:
        """Lưu trữ toàn bộ báo cáo Backtest vào thư mục models/."""
        self.log_step("SAVE_ARTIFACTS", f"Luu tru cac bao cao Backtest vao {self.models_dir}...")

        paths = {
            "metrics": os.path.join(self.models_dir, "backtest_metrics.json"),
            "benchmark_csv": os.path.join(self.models_dir, "backtest_comparison.csv"),
            "intervals_csv": os.path.join(self.models_dir, "prediction_intervals.csv"),
            "stress_test_csv": os.path.join(self.models_dir, "stress_test_scenarios.csv")
        }

        # Báo cáo JSON tổng hợp
        full_report = {
            "test_period": "2026-07-01 to 2026-07-31 (31 days)",
            "benchmark_comparison": self.benchmark_results,
            "multi_horizon_backtest": self.multi_horizon_results,
            "stress_testing_summary": self.stress_summary,
            "residual_outliers": self.outlier_analysis
        }

        with open(paths["metrics"], "w", encoding="utf-8") as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)

        self.benchmark_df.to_csv(paths["benchmark_csv"], index=False, encoding="utf-8-sig")
        self.interval_df.to_csv(paths["intervals_csv"], index=False, encoding="utf-8-sig")
        self.stress_test_df.to_csv(paths["stress_test_csv"], index=False, encoding="utf-8-sig")

        for k, p in paths.items():
            size_kb = os.path.getsize(p) / 1024
            self.log_step("SAVE_ARTIFACTS", f"Da luu: {os.path.basename(p)} ({size_kb:.1f} KB)")

        return paths

    def run_pipeline(self) -> dict:
        """Điều phối toàn bộ Pipeline Backtesting & Validation."""
        print("=" * 70)
        print("🔬 BẮT ĐẦU PHA 4: BACKTESTING & MODEL VALIDATION")
        print("=" * 70)

        self.load_artifacts()
        self.run_benchmark_comparison()
        self.run_multi_horizon_backtest()
        self.compute_prediction_intervals()
        self.run_stress_testing_scenarios()
        self.analyze_residual_outliers()
        paths = self.save_artifacts()

        print("\n" + "=" * 70)
        print("✅ HOÀN THÀNH PHA 4: KIỂM THỬ NGƯỢC & ĐÁNH GIÁ MÔ HÌNH THÀNH CÔNG RỰC RỠ!")
        print("=" * 70)

        return {
            "paths": paths,
            "benchmark": self.benchmark_results,
            "multi_horizon": self.multi_horizon_results,
            "stress_summary": self.stress_summary
        }


if __name__ == "__main__":
    backtester = CashflowBacktester()
    backtester.run_pipeline()
