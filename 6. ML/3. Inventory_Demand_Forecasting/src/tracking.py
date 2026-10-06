import pandas as pd

def start_experiment(experiment_name: str = "Inventory_Demand_Forecasting"):
    """Thiết lập MLflow Experiment."""
    import mlflow
    mlflow.set_experiment(experiment_name)

def log_metrics(metrics_df: pd.DataFrame):
    """
    Log metrics tổng thể (Global metrics) lên MLflow.
    Ví dụ: Average MAPE của toàn bộ hệ thống.
    """
    import mlflow
    if metrics_df.empty:
        return
        
    global_metrics = metrics_df.groupby('metric')['LGBMRegressor'].mean().to_dict()
    for metric_name, value in global_metrics.items():
        mlflow.log_metric(f"global_{metric_name}", value)

def log_params(params: dict):
    """Ghi nhận siêu tham số (Hyperparameters)."""
    import mlflow
    mlflow.log_params(params)
