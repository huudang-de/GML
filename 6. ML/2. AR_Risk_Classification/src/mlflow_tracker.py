import mlflow
import mlflow.lightgbm
from mlflow.models import infer_signature
import os

class RiskModelTracker:
    def __init__(self, experiment_name="AR_Risk_Classification", tracking_uri="sqlite:///mlflow.db"):
        """Khởi tạo MLflow Workspace với backend SQLite (thay vì file system cũ)"""
        # Set database lưu trữ
        mlflow.set_tracking_uri(tracking_uri)
        
        # Tạo hoặc kết nối vào Experiment
        mlflow.set_experiment(experiment_name)
        
    def log_training(self, model, params, metrics, X_sample, y_pred_sample, run_name="Release_Run"):
        """Ghi nhận lại một đợt huấn luyện (Run) và đóng gói Mô hình"""
        
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            
            signature = infer_signature(X_sample, y_pred_sample)
            
            model_info = mlflow.lightgbm.log_model(
                lgb_model=model,
                artifact_path="lgbm_risk_model",
                signature=signature
            )
            
            return run.info.run_id, model_info.model_uri
