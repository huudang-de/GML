"""
Module: test_model_training.py
Project: 01. Cashflow_Forecasting (Dự án Gỗ Minh Long)
Description:
    Test suite tự động kiểm định Huấn luyện mô hình & Tối ưu Siêu tham số Pha 3
    Bao phủ toàn diện 7 Test Cases: TC-TR-01 đến TC-TR-07.
    Chạy trực tiếp qua lệnh: python tests/test_model_training.py
"""

import os
import sys
import json
import unittest
import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit

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

from model_training import CashflowModelTrainer, calculate_wape, calculate_directional_accuracy


class TestCashflowModelTraining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("🧪 KHỞI ĐỘNG TEST SUITE KIỂM ĐỊNH PHA 3: MODEL TRAINING & OPTUNA TUNING")
        print("=" * 70)
        cls.trainer = CashflowModelTrainer()
        # Chạy pipeline với số trial vừa đủ cho test suite nhanh chóng nhưng đầy đủ
        cls.pipeline_out = cls.trainer.run_pipeline(n_trials=10)

    def test_tc_tr_01_input_and_feature_selection(self):
        """TC-TR-01: Kiểm tra Input & Lựa chọn Features."""
        print("\n>>> [RUN TEST] TC-TR-01: Kiem tra Input & Lua chon Features...")
        self.assertIsNotNone(self.trainer.df, "df khong duoc phep None")
        self.assertGreater(len(self.trainer.df), 150, "Tap du lieu phai co it nhat 150 ngay sau khi loc is_trainable")
        
        # Kiểm tra không có rò rỉ các cột mục tiêu hay metadata trong X
        leakage_cols = {'date', 'inflow', 'outflow', 'net_cashflow', 'tx_count', 'day_name', 'is_trainable'}
        overlap = set(self.trainer.feature_cols).intersection(leakage_cols)
        self.assertEqual(len(overlap), 0, f"Phat hien ro ri cot cam trong features: {overlap}")
        
        # Kiểm tra số lượng feature lớn (> 50)
        self.assertGreaterEqual(len(self.trainer.feature_cols), 50, "So luong features phai >= 50")
        
        # Kiểm tra X_train, X_test
        self.assertEqual(self.trainer.X_train.shape[1], len(self.trainer.feature_cols))
        self.assertEqual(self.trainer.X_test.shape[1], len(self.trainer.feature_cols))
        self.assertEqual(len(self.trainer.X_test), 31, "Tap Test phai co dung 31 ngay cua Thang 7/2026")
        print(f"    [PASS] TC-TR-01: Xac thuc thanh cong {len(self.trainer.feature_cols)} features va du 31 ngay Thang 7!")

    def test_tc_tr_02_walk_forward_integrity(self):
        """TC-TR-02: Tính toàn vẹn của Walk-Forward Split (Chống Data Leakage)."""
        print("\n>>> [RUN TEST] TC-TR-02: Kiem tra Tinh toan ven Walk-Forward Split...")
        max_train_date = self.trainer.df[self.trainer.df['date'] < self.trainer.test_start_date]['date'].max()
        min_test_date = self.trainer.df_test['date'].min()
        
        self.assertLess(max_train_date, min_test_date, "Max train date phai nho hon Min test date!")
        self.assertEqual(max_train_date, pd.to_datetime("2026-06-30"), "Ngay cuoi tap train phai la 2026-06-30")
        self.assertEqual(min_test_date, pd.to_datetime("2026-07-01"), "Ngay dau tap test phai la 2026-07-01")
        
        # Kiểm tra TimeSeriesSplit n_splits=3
        tscv = TimeSeriesSplit(n_splits=3)
        for fold, (tr_idx, val_idx) in enumerate(tscv.split(self.trainer.X_train)):
            self.assertLess(max(tr_idx), min(val_idx), f"Fold {fold}: Train index phai hoan toan truoc Val index!")
        print("    [PASS] TC-TR-02: Walk-Forward Split tuyet doi tuan thu trinh tu thoi gian, khong ro ri tuong lai!")

    def test_tc_tr_03_optuna_tuning_validity(self):
        """TC-TR-03: Tối ưu hóa Siêu tham số bằng Optuna."""
        print("\n>>> [RUN TEST] TC-TR-03: Kiem tra Ket qua Toi uu Sieu tham so Optuna...")
        self.assertTrue(bool(self.trainer.best_params_inflow), "best_params_inflow khong duoc rong")
        self.assertTrue(bool(self.trainer.best_params_outflow), "best_params_outflow khong duoc rong")
        
        required_params = ['learning_rate', 'num_leaves', 'max_depth', 'n_estimators', 'min_child_samples']
        for p in required_params:
            self.assertIn(p, self.trainer.best_params_inflow, f"Thieu param {p} trong best_params_inflow")
            self.assertIn(p, self.trainer.best_params_outflow, f"Thieu param {p} trong best_params_outflow")
            
        self.assertGreater(self.trainer.best_params_inflow['learning_rate'], 0)
        self.assertGreater(self.trainer.best_params_outflow['num_leaves'], 0)
        print("    [PASS] TC-TR-03: Optuna tim ra bo Sieu tham so toi uu hop le cho ca Inflow & Outflow!")

    def test_tc_tr_04_dual_models_training(self):
        """TC-TR-04: Huấn luyện Mô hình Kép (Inflow & Outflow)."""
        print("\n>>> [RUN TEST] TC-TR-04: Kiem tra Huan luyen Mo hinh Kep LightGBM...")
        self.assertIsInstance(self.trainer.model_inflow, lgb.LGBMRegressor)
        self.assertIsInstance(self.trainer.model_outflow, lgb.LGBMRegressor)
        
        # Kiểm tra khả năng dự đoán trên tập train
        preds_in_train = self.trainer.model_inflow.predict(self.trainer.X_train)
        preds_out_train = self.trainer.model_outflow.predict(self.trainer.X_train)
        
        self.assertEqual(len(preds_in_train), len(self.trainer.X_train))
        self.assertEqual(len(preds_out_train), len(self.trainer.X_train))
        self.assertFalse(np.isnan(preds_in_train).any(), "Du bao Inflow train bi chua NaN")
        self.assertFalse(np.isnan(preds_out_train).any(), "Du bao Outflow train bi chua NaN")
        print("    [PASS] TC-TR-04: Ca 2 mo hinh LightGBM hoi tu va du doan hop le tren tap Train!")

    def test_tc_tr_05_out_of_time_evaluation(self):
        """TC-TR-05: Đánh giá Hiệu năng Out-of-Time (Tháng 7/2026)."""
        print("\n>>> [RUN TEST] TC-TR-05: Kiem tra Hieu nang Du bao Thang 7/2026...")
        metrics = self.trainer.evaluation_results
        self.assertIn("inflow", metrics)
        self.assertIn("outflow", metrics)
        self.assertIn("net_cashflow", metrics)
        
        inflow_wape = metrics["inflow"]["wape_pct"]
        outflow_wape = metrics["outflow"]["wape_pct"]
        dir_acc = metrics["net_cashflow"]["directional_accuracy_pct"]
        
        # Kiểm tra WAPE không âm và < 100%
        self.assertGreater(inflow_wape, 0.0)
        self.assertLess(inflow_wape, 100.0)
        self.assertGreater(outflow_wape, 0.0)
        self.assertLess(outflow_wape, 100.0)
        
        # Kiểm tra Directional Accuracy >= 40% (phù hợp chuỗi thời gian ngày có biến động lớn)
        self.assertGreaterEqual(dir_acc, 40.0, f"Directional accuracy {dir_acc}% phai >= 40%")
        
        # Kiểm tra tính toán tổng tiền tháng 7 (tỷ VNĐ)
        self.assertGreater(metrics["inflow"]["total_actual_ty"], 0.0)
        self.assertGreater(metrics["outflow"]["total_actual_ty"], 0.0)
        print(f"    [PASS] TC-TR-05: Thang 7 Inflow WAPE={inflow_wape:.2f}%, Outflow WAPE={outflow_wape:.2f}%, Directional Acc={dir_acc:.2f}%!")

    def test_tc_tr_06_feature_importance_analysis(self):
        """TC-TR-06: Phân tích Mức độ Quan trọng (Feature Importance)."""
        print("\n>>> [RUN TEST] TC-TR-06: Kiem tra Feature Importance...")
        fi = self.trainer.feature_importance
        self.assertIn("top_10_inflow", fi)
        self.assertIn("top_10_outflow", fi)
        
        self.assertEqual(len(fi["top_10_inflow"]), 10)
        self.assertEqual(len(fi["top_10_outflow"]), 10)
        
        # Tất cả importance phải >= 0
        for feat, val in fi["top_10_inflow"].items():
            self.assertGreaterEqual(val, 0)
        for feat, val in fi["top_10_outflow"].items():
            self.assertGreaterEqual(val, 0)
        print(f"    [PASS] TC-TR-06: Trich xuat thanh cong Top 10 dac trung then chot cho ca 2 mo hinh!")

    def test_tc_tr_07_artifacts_and_inference_consistency(self):
        """TC-TR-07: Đóng gói & Tái kiểm tra Mô hình (Inference Test)."""
        print("\n>>> [RUN TEST] TC-TR-07: Kiem tra Dong goi & Tinh nhat quan Inference...")
        models_dir = self.trainer.models_dir
        expected_files = [
            "model_inflow.joblib",
            "model_outflow.joblib",
            "best_params.json",
            "evaluation_metrics.json",
            "feature_importance.json",
            "test_predictions_july2026.csv"
        ]
        
        for f in expected_files:
            file_path = os.path.join(models_dir, f)
            self.assertTrue(os.path.exists(file_path), f"Thieu tep artifact: {f}")
            self.assertGreater(os.path.getsize(file_path), 0, f"Tep artifact bi rong: {f}")
            
        # Tải lại mô hình từ đĩa và kiểm tra tính nhất quán (reproducibility)
        reloaded_inflow = joblib.load(os.path.join(models_dir, "model_inflow.joblib"))
        reloaded_outflow = joblib.load(os.path.join(models_dir, "model_outflow.joblib"))
        
        pred_inflow_reloaded = reloaded_inflow.predict(self.trainer.X_test)
        pred_outflow_reloaded = reloaded_outflow.predict(self.trainer.X_test)
        
        orig_pred_inflow = self.trainer.model_inflow.predict(self.trainer.X_test)
        orig_pred_outflow = self.trainer.model_outflow.predict(self.trainer.X_test)
        
        self.assertTrue(np.allclose(pred_inflow_reloaded, orig_pred_inflow), "Inference Inflow khong khop 100%!")
        self.assertTrue(np.allclose(pred_outflow_reloaded, orig_pred_outflow), "Inference Outflow khong khop 100%!")
        print("    [PASS] TC-TR-07: Dong goi artifacts day du, ket qua Inference tai su dung khop 100%!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
