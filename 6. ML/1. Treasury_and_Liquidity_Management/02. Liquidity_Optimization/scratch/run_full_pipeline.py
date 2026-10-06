import sys
import os
import pandas as pd
from datetime import datetime
import mlflow

# Thêm đường dẫn src vào system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_loader import build_state
from src.optimizer import LiquidityOptimizer

def run_pipeline():
    print("🚀 BẮT ĐẦU PIPELINE TỐI ƯU HÓA THANH KHOẢN (LIQUIDITY OPTIMIZATION)")
    
    # 1. Load Data
    print("\n--- PHASE 1: DATA GATHERING ---")
    state = build_state()
    
    # 2. Run Optimizer
    print("\n--- PHASE 2: LINEAR PROGRAMMING OPTIMIZATION ---")
    optimizer = LiquidityOptimizer(state)
    
    # Set MLflow experiment
    mlflow.set_experiment("Liquidity_Optimization")
    
    with mlflow.start_run(run_name=f"Run_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        
        # Buffer 2 Tỷ VNĐ
        result = optimizer.solve(safety_buffer=2e9)
        
        if result:
            df_actions = result['actions']
            target_cap = result['target_capital']
            total_cost = result['total_interest_cost']
            
            print("\n✅ KẾT QUẢ TỐI ƯU (ACTION RECOMMENDATIONS):")
            print(df_actions.to_string(index=False))
            print(f"\n💰 TỔNG CHI PHÍ LÃI VAY ƯỚC TÍNH: {total_cost:,.0f} VND/Năm")
            
            # 3. Export to Silver Layer
            print("\n--- PHASE 3: EXPORT TO SILVER LAYER ---")
            os.makedirs('data/processed', exist_ok=True)
            export_path = 'data/processed/silver.fact_liquidity_actions.csv'
            
            # Gắn thêm metadata
            df_actions['Run_ID'] = mlflow.active_run().info.run_id
            df_actions['As_Of_Date'] = datetime.now().strftime('%Y-%m-%d')
            
            df_actions.to_csv(export_path, index=False)
            print(f"✅ Đã xuất {len(df_actions)} hành động ra: {export_path}")
            
            # Track MLflow
            mlflow.log_param("Safety_Buffer", 2e9)
            mlflow.log_param("Target_Capital_Required", target_cap)
            mlflow.log_metric("Total_Interest_Cost", total_cost)
            mlflow.log_metric("Action_Count", len(df_actions))
            
            print(f"✅ Đã log metrics lên MLflow (Run_ID: {mlflow.active_run().info.run_id[:8]})")
            
if __name__ == "__main__":
    run_pipeline()
