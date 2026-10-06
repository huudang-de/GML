import mlflow
from src.mlflow_tracker import RiskModelTracker

def test_mlflow_run():
    """Kiểm tra xem thư viện MLflow có khởi tạo Run thành công với SQLite không"""
    tracker = RiskModelTracker(experiment_name="Test_Experiment", tracking_uri="sqlite:///test_mlflow.db")
    
    with mlflow.start_run(run_name="Test_Run") as run:
        run_id = run.info.run_id
        
        assert run_id is not None
        assert isinstance(run_id, str)
        assert len(run_id) > 5
        
        mlflow.log_param("test_param", 123)
        mlflow.log_metric("test_metric", 0.99)
