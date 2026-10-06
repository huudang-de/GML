"""
Module: model_training.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Huấn luyện mô hình Machine Learning dự báo Dòng tiền (Inflow & Outflow):
    - Walk-Forward Validation (Rolling Origin) chống rò rỉ dữ liệu
    - Tối ưu Siêu tham số (Hyperparameter Tuning) bằng Optuna
    - Huấn luyện mô hình LightGBM Regressor kép (Dual Models)
    - Đánh giá Out-of-Time trên toàn bộ 31 ngày Tháng 7/2026 (WAPE, MAE, RMSE, Directional Accuracy)
    - Trích xuất Feature Importance và lưu trữ Artifacts vào thư mục models/
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import joblib
import optuna
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
import lightgbm as lgb

# Tắt bớt log quá chi tiết của Optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

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
logger = logging.getLogger("CashflowModelTrainer")


def calculate_wape(y_true, y_pred) -> float:
    """Tính sai số phần trăm tuyệt đối có trọng số (Weighted Absolute Percentage Error - WAPE)."""
    sum_true = np.sum(np.abs(y_true))
    if sum_true == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / sum_true) * 100.0


def calculate_directional_accuracy(y_true, y_pred) -> float:
    """Đo lường tỷ lệ dự báo đúng chiều tăng/giảm (Directional Accuracy) giữa ngày t và t-1."""
    if len(y_true) < 2:
        return 100.0
    diff_true = np.diff(y_true)
    diff_pred = np.diff(y_pred)
    correct_direction = (np.sign(diff_true) == np.sign(diff_pred)).sum()
    return float(correct_direction / len(diff_true)) * 100.0


class CashflowModelTrainer:
    def __init__(
        self,
        featured_parquet_path: str = None,
        test_start_date: str = "2026-07-01",
        random_state: int = 42
    ):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if featured_parquet_path is None:
            self.featured_parquet_path = os.path.join(base_dir, "data", "processed", "featured_cashflow.parquet")
        else:
            self.featured_parquet_path = featured_parquet_path

        self.models_dir = os.path.join(base_dir, "models")
        os.makedirs(self.models_dir, exist_ok=True)

        self.test_start_date = pd.to_datetime(test_start_date)
        self.random_state = random_state

        self.df = None
        self.feature_cols = []
        self.X_train = None
        self.y_train_inflow = None
        self.y_train_outflow = None
        self.X_test = None
        self.y_test_inflow = None
        self.y_test_outflow = None
        self.df_test = None

        self.best_params_inflow = {}
        self.best_params_outflow = {}
        self.model_inflow = None
        self.model_outflow = None
        self.evaluation_results = {}
        self.feature_importance = {}

    def log_step(self, step_name: str, message: str):
        print(f"\n>>> [TASK] {step_name.upper()}: {message}")
        logger.info(f"[{step_name}] {message}")

    def load_and_split_data(self) -> tuple:
        """Đọc bảng đặc trưng, loại bỏ warm-up period và phân chia Train/Test theo thời gian."""
        self.log_step("LOAD_DATA", f"Doc ma tran dac trung tu {self.featured_parquet_path}...")
        if not os.path.exists(self.featured_parquet_path):
            raise FileNotFoundError(f"Khong tim thay tep: {self.featured_parquet_path}")

        raw_df = pd.read_parquet(self.featured_parquet_path)
        raw_df['date'] = pd.to_datetime(raw_df['date'])

        # Chỉ lấy các dòng đã hoàn thiện cửa sổ lịch sử (is_trainable == 1)
        self.df = raw_df[raw_df['is_trainable'] == 1].sort_values('date').reset_index(drop=True)

        # Xác định danh sách cột features (loại trừ các cột targets, date, metadata)
        exclude_cols = {'date', 'inflow', 'outflow', 'net_cashflow', 'tx_count', 'day_name', 'is_trainable'}
        self.feature_cols = [c for c in self.df.columns if c not in exclude_cols]

        # Phân chia theo thời gian (Time-based split)
        train_mask = self.df['date'] < self.test_start_date
        test_mask = self.df['date'] >= self.test_start_date

        df_train = self.df[train_mask].reset_index(drop=True)
        self.df_test = self.df[test_mask].reset_index(drop=True)

        self.X_train = df_train[self.feature_cols]
        self.y_train_inflow = df_train['inflow'].values
        self.y_train_outflow = df_train['outflow'].values

        self.X_test = self.df_test[self.feature_cols]
        self.y_test_inflow = self.df_test['inflow'].values
        self.y_test_outflow = self.df_test['outflow'].values

        self.log_step("LOAD_DATA", f"Tap Train: {len(df_train)} ngay ({df_train['date'].min().strftime('%Y-%m-%d')} den {df_train['date'].max().strftime('%Y-%m-%d')})")
        self.log_step("LOAD_DATA", f"Tap Test (Out-of-Time): {len(self.df_test)} ngay ({self.df_test['date'].min().strftime('%Y-%m-%d')} den {self.df_test['date'].max().strftime('%Y-%m-%d')})")
        self.log_step("LOAD_DATA", f"Tong so dac trung (Features): {len(self.feature_cols)} cot.")

        return self.X_train, self.X_test, self.y_train_inflow, self.y_test_inflow

    def tune_hyperparameters_optuna(self, target_type: str = "inflow", n_trials: int = 25) -> dict:
        """
        Sử dụng Optuna để tìm kiếm bộ siêu tham số tối ưu cho LightGBM Regressor
        kết hợp Walk-Forward TimeSeriesSplit trên tập Train.
        """
        self.log_step("OPTUNA_TUNE", f"Bat dau toi uu hoa Sieu tham so bang Optuna cho target: {target_type.upper()} ({n_trials} trials)...")

        y_train = self.y_train_inflow if target_type == "inflow" else self.y_train_outflow
        tscv = TimeSeriesSplit(n_splits=3)

        def objective(trial):
            params = {
                'objective': 'regression_l1',
                'metric': 'mae',
                'boosting_type': 'gbdt',
                'learning_rate': trial.suggest_float('learning_rate', 0.02, 0.15, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 15, 63),
                'max_depth': trial.suggest_int('max_depth', 3, 8),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 25),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 40, 150),
                'verbose': -1,
                'random_state': self.random_state
            }

            cv_wapes = []
            for train_idx, val_idx in tscv.split(self.X_train):
                X_tr, X_val = self.X_train.iloc[train_idx], self.X_train.iloc[val_idx]
                y_tr, y_val = y_train[train_idx], y_train[val_idx]

                model = lgb.LGBMRegressor(**params)
                model.fit(X_tr, y_tr)
                preds = model.predict(X_val)
                cv_wapes.append(calculate_wape(y_val, preds))

            return np.mean(cv_wapes)

        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=self.random_state))
        study.optimize(objective, n_trials=n_trials)

        best_params = study.best_params
        best_params.update({
            'objective': 'regression_l1',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'verbose': -1,
            'random_state': self.random_state
        })

        self.log_step("OPTUNA_TUNE", f"Optuna hoan tat! Best CV WAPE ({target_type}): {study.best_value:.2f}%")
        self.log_step("OPTUNA_TUNE", f"Best Params ({target_type}): {json.dumps(study.best_params, indent=2)}")

        if target_type == "inflow":
            self.best_params_inflow = best_params
        else:
            self.best_params_outflow = best_params

        return best_params

    def train_models(self, n_trials: int = 25):
        """Huấn luyện 2 mô hình LightGBM Regressor (Inflow và Outflow) với siêu tham số đã tối ưu."""
        self.log_step("TRAIN_MODELS", "Bat dau huan luyen Mo hinh Kep (Inflow & Outflow Models)...")

        # 1. Tối ưu siêu tham số
        params_inflow = self.tune_hyperparameters_optuna(target_type="inflow", n_trials=n_trials)
        params_outflow = self.tune_hyperparameters_optuna(target_type="outflow", n_trials=n_trials)

        # 2. Huấn luyện Inflow Model
        self.log_step("TRAIN_MODELS", "Fit LightGBM Inflow Model tren toan bo Tap Train...")
        self.model_inflow = lgb.LGBMRegressor(**params_inflow)
        self.model_inflow.fit(self.X_train, self.y_train_inflow)

        # 3. Huấn luyện Outflow Model
        self.log_step("TRAIN_MODELS", "Fit LightGBM Outflow Model tren toan bo Tap Train...")
        self.model_outflow = lgb.LGBMRegressor(**params_outflow)
        self.model_outflow.fit(self.X_train, self.y_train_outflow)

        self.log_step("TRAIN_MODELS", "Huan luyen thanh cong ca 2 mo hinh!")

    def evaluate_out_of_time(self) -> dict:
        """Đánh giá hiệu năng dự báo trên tập Out-of-Time Test (31 ngày Tháng 7/2026)."""
        self.log_step("EVALUATION", "Danh gia hieu nang Du bao tren Tap Test (Thang 7/2026 - 31 ngay)...")

        # 1. Dự đoán
        preds_inflow = np.maximum(0.0, self.model_inflow.predict(self.X_test))
        preds_outflow = np.maximum(0.0, self.model_outflow.predict(self.X_test))
        preds_net = preds_inflow - preds_outflow
        y_test_net = self.y_test_inflow - self.y_test_outflow

        # 2. Tính toán Metrics cho Inflow
        inflow_wape = calculate_wape(self.y_test_inflow, preds_inflow)
        inflow_mae = float(mean_absolute_error(self.y_test_inflow, preds_inflow))
        inflow_rmse = float(np.sqrt(mean_squared_error(self.y_test_inflow, preds_inflow)))

        # 3. Tính toán Metrics cho Outflow
        outflow_wape = calculate_wape(self.y_test_outflow, preds_outflow)
        outflow_mae = float(mean_absolute_error(self.y_test_outflow, preds_outflow))
        outflow_rmse = float(np.sqrt(mean_squared_error(self.y_test_outflow, preds_outflow)))

        # 4. Tính toán Metrics cho Net Cashflow
        net_wape = calculate_wape(y_test_net, preds_net)
        net_mae = float(mean_absolute_error(y_test_net, preds_net))
        net_dir_acc = calculate_directional_accuracy(y_test_net, preds_net)

        # 5. So sánh Tổng tiền Thu/Chi thực tế vs dự báo cả tháng 7
        total_inflow_true = float(np.sum(self.y_test_inflow)) / 1e9
        total_inflow_pred = float(np.sum(preds_inflow)) / 1e9
        total_outflow_true = float(np.sum(self.y_test_outflow)) / 1e9
        total_outflow_pred = float(np.sum(preds_outflow)) / 1e9
        total_net_true = total_inflow_true - total_outflow_true
        total_net_pred = total_inflow_pred - total_outflow_pred

        self.evaluation_results = {
            "test_period": "2026-07-01 to 2026-07-31 (31 days)",
            "inflow": {
                "wape_pct": round(inflow_wape, 2),
                "mae_ty": round(inflow_mae / 1e9, 3),
                "rmse_ty": round(inflow_rmse / 1e9, 3),
                "total_actual_ty": round(total_inflow_true, 2),
                "total_predicted_ty": round(total_inflow_pred, 2),
                "error_total_pct": round(abs(total_inflow_pred - total_inflow_true) / total_inflow_true * 100, 2)
            },
            "outflow": {
                "wape_pct": round(outflow_wape, 2),
                "mae_ty": round(outflow_mae / 1e9, 3),
                "rmse_ty": round(outflow_rmse / 1e9, 3),
                "total_actual_ty": round(total_outflow_true, 2),
                "total_predicted_ty": round(total_outflow_pred, 2),
                "error_total_pct": round(abs(total_outflow_pred - total_outflow_true) / total_outflow_true * 100, 2)
            },
            "net_cashflow": {
                "wape_pct": round(net_wape, 2),
                "mae_ty": round(net_mae / 1e9, 3),
                "directional_accuracy_pct": round(net_dir_acc, 2),
                "total_net_actual_ty": round(total_net_true, 2),
                "total_net_predicted_ty": round(total_net_pred, 2)
            }
        }

        # Lưu DataFrame dự đoán để vẽ biểu đồ và phân tích
        self.pred_df = pd.DataFrame({
            'date': self.df_test['date'],
            'actual_inflow': self.y_test_inflow,
            'pred_inflow': preds_inflow,
            'actual_outflow': self.y_test_outflow,
            'pred_outflow': preds_outflow,
            'actual_net': y_test_net,
            'pred_net': preds_net
        })

        self.log_step("EVALUATION", f"Ket qua Danh gia Thang 7/2026:")
        self.log_step("EVALUATION", f" - INFLOW WAPE: {inflow_wape:.2f}% | Thuc te: {total_inflow_true:.2f} Ty, Du bao: {total_inflow_pred:.2f} Ty (Lech {self.evaluation_results['inflow']['error_total_pct']}%)")
        self.log_step("EVALUATION", f" - OUTFLOW WAPE: {outflow_wape:.2f}% | Thuc te: {total_outflow_true:.2f} Ty, Du bao: {total_outflow_pred:.2f} Ty (Lech {self.evaluation_results['outflow']['error_total_pct']}%)")
        self.log_step("EVALUATION", f" - NET CASHFLOW Directional Accuracy: {net_dir_acc:.2f}%")

        return self.evaluation_results

    def extract_feature_importance(self) -> dict:
        """Trích xuất mức độ quan trọng (Feature Importance) của các đặc trưng."""
        self.log_step("FEATURE_IMPORTANCE", "Trich xuat Feature Importance cho ca 2 mo hinh...")

        importance_inflow = pd.Series(
            self.model_inflow.feature_importances_, index=self.feature_cols
        ).sort_values(ascending=False)

        importance_outflow = pd.Series(
            self.model_outflow.feature_importances_, index=self.feature_cols
        ).sort_values(ascending=False)

        self.feature_importance = {
            "top_10_inflow": importance_inflow.head(10).to_dict(),
            "top_10_outflow": importance_outflow.head(10).to_dict()
        }

        self.log_step("FEATURE_IMPORTANCE", f"Top 5 Inflow: {list(importance_inflow.head(5).index)}")
        self.log_step("FEATURE_IMPORTANCE", f"Top 5 Outflow: {list(importance_outflow.head(5).index)}")

        return self.feature_importance

    def save_artifacts(self) -> dict:
        """Lưu trữ models, best_params, metrics và predictions vào thư mục models/."""
        self.log_step("SAVE_ARTIFACTS", f"Luu tru Model Artifacts vao {self.models_dir}...")

        paths = {
            "model_inflow": os.path.join(self.models_dir, "model_inflow.joblib"),
            "model_outflow": os.path.join(self.models_dir, "model_outflow.joblib"),
            "best_params": os.path.join(self.models_dir, "best_params.json"),
            "metrics": os.path.join(self.models_dir, "evaluation_metrics.json"),
            "feature_importance": os.path.join(self.models_dir, "feature_importance.json"),
            "test_predictions": os.path.join(self.models_dir, "test_predictions_july2026.csv")
        }

        # Lưu model
        joblib.dump(self.model_inflow, paths["model_inflow"])
        joblib.dump(self.model_outflow, paths["model_outflow"])

        # Lưu JSONs
        with open(paths["best_params"], "w", encoding="utf-8") as f:
            json.dump({
                "inflow": self.best_params_inflow,
                "outflow": self.best_params_outflow
            }, f, ensure_ascii=False, indent=2)

        with open(paths["metrics"], "w", encoding="utf-8") as f:
            json.dump(self.evaluation_results, f, ensure_ascii=False, indent=2)

        with open(paths["feature_importance"], "w", encoding="utf-8") as f:
            json.dump(self.feature_importance, f, ensure_ascii=False, indent=2)

        # Lưu CSV dự đoán
        self.pred_df.to_csv(paths["test_predictions"], index=False, encoding="utf-8-sig")

        for k, p in paths.items():
            size_kb = os.path.getsize(p) / 1024
            self.log_step("SAVE_ARTIFACTS", f"Da luu: {os.path.basename(p)} ({size_kb:.1f} KB)")

        return paths

    def run_pipeline(self, n_trials: int = 25) -> dict:
        """Điều phối toàn bộ Pipeline Huấn luyện, Tối ưu & Đánh giá."""
        print("=" * 70)
        print("🚀 BẮT ĐẦU PHA 3: MODEL TRAINING & HYPERPARAMETER TUNING")
        print("=" * 70)

        self.load_and_split_data()
        self.train_models(n_trials=n_trials)
        self.evaluate_out_of_time()
        self.extract_feature_importance()
        paths = self.save_artifacts()

        print("\n" + "=" * 70)
        print("✅ HOÀN THÀNH PHA 3: HUẤN LUYỆN & TỐI ƯU MÔ HÌNH THÀNH CÔNG RỰC RỠ!")
        print("=" * 70)

        return {
            "paths": paths,
            "metrics": self.evaluation_results,
            "feature_importance": self.feature_importance
        }


if __name__ == "__main__":
    trainer = CashflowModelTrainer()
    trainer.run_pipeline(n_trials=25)
