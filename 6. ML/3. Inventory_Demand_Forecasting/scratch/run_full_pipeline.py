import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.forecast import train_and_predict, evaluate_cross_validation, calculate_metrics
from src.optimize import calculate_rop, calculate_eoq
from src.tracking import start_experiment, log_metrics, log_params
from src.integration import export_to_fact_inventory_forecast, export_to_fact_reorder_recommendations

def run():
    print("🚀 BẮT ĐẦU CHẠY TOÀN BỘ PIPELINE (PHA 6 & PHA 7)...")
    
    # 1. Tạo Data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=60, freq='D')
    df_van = pd.DataFrame({'unique_id': 'VAN-01', 'ds': dates, 'y': np.random.normal(50, 10, 60)})
    df_nep = pd.DataFrame({'unique_id': 'NEP-02', 'ds': dates, 'y': np.random.normal(150, 20, 60)})
    df = pd.concat([df_van, df_nep], ignore_index=True)
    df['y'] = df['y'].clip(lower=0).astype(int)
    
    # 2. MLFlow Tracking (Pha 6)
    print("\n⚙️ [PHA 6] Tracking thí nghiệm với MLflow (Ghi nhận thông số để giám sát Model Drift sau này)...")
    try:
        import mlflow
        start_experiment("GML_Inventory_Forecasting")
        with mlflow.start_run():
            log_params({"model": "LightGBM", "lags": "[1, 7, 14, 28]", "horizon": 7, "cv_windows": 2})
            
            # Tính CV
            cv_df = evaluate_cross_validation(df, h=7, n_windows=2, freq='D')
            metrics = calculate_metrics(cv_df)
            
            log_metrics(metrics)
            print("   -> Đã log siêu tham số (Hyperparameters) và Global Metrics lên MLflow Dashboard thành công!")
    except Exception as e:
        print(f"   -> Chú ý: Chưa setup MLflow server local (Bỏ qua tracking). Lỗi: {e}")
        
    # 3. Forecast & Optimize (Pha 3 & 4)
    print("\n⚙️ Tiến hành dự báo thực tế và Tối ưu hóa Chuỗi cung ứng (Pha 3 & 4)...")
    forecasts = train_and_predict(df, h=7, freq='D', levels=[95])
    
    forecasts['std_demand'] = (forecasts['LGBMRegressor-hi-95'] - forecasts['LGBMRegressor-lo-95']) / (2 * 1.96)
    supply_params = forecasts.groupby('unique_id').agg(
        avg_demand=('LGBMRegressor', 'mean'), std_demand=('std_demand', 'mean')
    ).reset_index()
    
    supply_params['lead_time'] = supply_params['unique_id'].map({'VAN-01': 14, 'NEP-02': 7})
    supply_params['unit_cost'] = 100000 
    supply_params['ordering_cost'] = 50000
    supply_params['holding_cost_rate'] = 0.2
    
    opt_results = []
    for _, row in supply_params.iterrows():
        rop, ss = calculate_rop(row['avg_demand'], row['std_demand'], row['lead_time'])
        eoq = calculate_eoq(row['avg_demand']*365, row['ordering_cost'], row['holding_cost_rate'], row['unit_cost'])
        opt_results.append({
            'SKU': row['unique_id'], 'Nhu Cầu TB/Ngày': row['avg_demand'], 
            'Tồn kho An toàn (SS)': ss, 'Điểm Báo Động (ROP)': rop, 'Số Lượng Nhập Tối Ưu (EOQ)': eoq,
            'Thời gian Giao (Ngày)': row['lead_time']
        })
    opt_df = pd.DataFrame(opt_results)
    
    # 4. Integration (Pha 7)
    print("\n⚙️ [PHA 7] Chuẩn hóa Data Export để đổ vào PostgreSQL (Silver Layer)...")
    fact_forecast = export_to_fact_inventory_forecast(forecasts)
    # Lấy ngày hiện tại là ngày báo cáo
    fact_reorder = export_to_fact_reorder_recommendations(opt_df, current_date=pd.Timestamp.today().normalize())
    
    print("\n📊 BẢNG 1: silver.fact_inventory_forecast (Lưu lịch sử dự báo Data Warehouse)")
    pd.set_option('display.max_columns', None)
    print(fact_forecast.head(4).to_string(index=False))
    
    print("\n📊 BẢNG 2: silver.fact_reorder_recommendations (Bản tin Khuyến nghị Mua hàng hiển thị trên Power BI)")
    print(fact_reorder.to_string(index=False))
    
    print("\n✅ HOÀN TẤT TOÀN BỘ VÒNG ĐỜI DỰ ÁN DỰ BÁO TỒN KHO! TẤT CẢ ĐÃ SẴN SÀNG ĐƯA VÀO PRODUCTION.")

if __name__ == "__main__":
    run()
