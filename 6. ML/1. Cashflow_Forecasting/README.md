# 📊 Dự báo Dòng tiền — Cashflow Forecasting

> **Mức ưu tiên:** ⭐⭐⭐⭐⭐ | **Framework chính:** sktime | **Model:** LightGBM/XGBoost + ETS/ARIMA | **Tracking:** MLflow

---

## 1. Bài toán & Mục tiêu

### Vấn đề hiện tại
Chỉ số **Cash Runway** (Thời gian sống của tiền mặt) đang được tính bằng công thức tĩnh đơn giản:
```
Cash Runway = Số dư tiền mặt hiện tại / Tốc độ chi tiêu trung bình tháng gần nhất
```
Công thức này **không thể** nhận diện yếu tố mùa vụ (Seasonality) của ngành gỗ (VD: nhập hàng cao điểm quý 1, quý 3; xuất hàng cao điểm cuối năm).

### Mục tiêu dự án ML
1. **Dự báo dòng tiền vào/ra 3–6 tháng tới** với khoảng tin cậy (Confidence Interval).
2. **Phát hiện sớm (Early Warning)** thời điểm nguy cơ thâm hụt tiền mặt.
3. **Tích hợp kết quả dự báo** vào Dashboard Power BI (Forecast Line Visual).

---

## 2. Nguồn dữ liệu

| Bảng nguồn | Trường sử dụng | Mô tả |
|:---|:---|:---|
| `silver.fact_cashflow` | `posting_date`, `debit_amount`, `credit_amount`, `account_no` | Luồng tiền thực tế hàng ngày |
| `silver.dim_date` | `date`, `month`, `quarter`, `year`, `is_holiday` | Calendar features |
| `silver.fact_businessplan` | `indicator_code`, `target_amount`, `period` | Kế hoạch dòng tiền để so sánh |

### Chuẩn bị dữ liệu
```python
# Lấy dữ liệu dòng tiền vào/ra theo ngày từ PostgreSQL
SQL_CASHFLOW = """
    SELECT
        posting_date::date AS ds,
        SUM(CASE WHEN debit_amount > 0 THEN debit_amount ELSE 0 END)  AS cash_in,
        SUM(CASE WHEN credit_amount > 0 THEN credit_amount ELSE 0 END) AS cash_out
    FROM silver.fact_cashflow
    WHERE posting_date >= '2023-01-01'
    GROUP BY posting_date::date
    ORDER BY ds
"""
```

---

## 3. Kiến trúc Pipeline

```
PostgreSQL (Silver Layer)
        │
        ▼
[1. Data Extraction & EDA]
  - Kiểm tra stationarity (ADF test)
  - Phân rã Trend / Seasonality / Residual (STL Decomposition)
  - Phát hiện outlier (IQR / Z-score)
        │
        ▼
[2. Feature Engineering]
  - Lag features: cash_in_lag_7d, cash_in_lag_30d
  - Rolling stats: rolling_mean_7d, rolling_std_30d
  - Calendar: is_month_end, is_quarter_end, month, day_of_week
  - External: KPI Kế hoạch tháng (fact_businessplan)
        │
        ▼
[3. Model Training]
  ┌─────────────────────────────────────┐
  │  Baseline: ETS / ARIMA (statsmodels)│
  │  Champion: LightGBM (sktime wrapper)│
  │  Ensemble: Weighted Average          │
  └─────────────────────────────────────┘
        │
        ▼
[4. Evaluation & Backtesting]
  - Walk-forward validation (TimeSeriesSplit)
  - Metrics: MAE, RMSE, MAPE, Coverage (CI)
        │
        ▼
[5. MLflow Tracking & Model Registry]
  - Log params, metrics, artifacts
  - Đăng ký model tốt nhất vào Model Registry
        │
        ▼
[6. Serving / Export]
  - Xuất forecast CSV → PostgreSQL table `silver.fact_cashflow_forecast`
  - Power BI đọc bảng này để vẽ Forecast Line
```

---

## 4. Chi tiết từng bước triển khai

### Bước 1 — EDA & Data Preparation (`1_eda.ipynb`)
- [ ] Kết nối PostgreSQL, chạy query lấy `fact_cashflow`
- [ ] Vẽ biểu đồ chuỗi thời gian Cash In / Cash Out
- [ ] STL Decomposition để xác nhận Seasonality
- [ ] ADF Test kiểm tra tính dừng (Stationarity)
- [ ] Xử lý missing dates (forward fill / interpolation)

### Bước 2 — Feature Engineering (`2_feature_engineering.py`)
```python
features = [
    # Lag features
    "cash_in_lag_7", "cash_in_lag_14", "cash_in_lag_30",
    "cash_out_lag_7", "cash_out_lag_14", "cash_out_lag_30",
    # Rolling statistics
    "rolling_mean_7", "rolling_std_7",
    "rolling_mean_30", "rolling_std_30",
    # Calendar
    "day_of_week", "month", "quarter",
    "is_month_end", "is_quarter_end",
    # Business context
    "plan_cash_in_month",  # từ fact_businessplan
]
```

### Bước 3 — Model Training (`3_train_model.ipynb`)
```python
# Baseline: ETS
from sktime.forecasting.ets import AutoETS
model_ets = AutoETS(auto=True, sp=12)

# Champion: LightGBM via sktime
from sktime.forecasting.compose import make_reduction
from lightgbm import LGBMRegressor
model_lgbm = make_reduction(LGBMRegressor(n_estimators=500, learning_rate=0.05),
                             window_length=30, strategy="recursive")

# Hyperparameter tuning with Optuna
import optuna
```

### Bước 4 — Evaluation (`4_evaluate.ipynb`)
```python
from sktime.forecasting.model_evaluation import evaluate
from sktime.forecasting.model_selection import SlidingWindowSplitter

cv = SlidingWindowSplitter(window_length=90, step_length=30, fh=list(range(1, 31)))
results = evaluate(model_lgbm, y=y_train, cv=cv, scoring=MeanAbsolutePercentageError())
```

### Bước 5 — MLflow Tracking (`5_mlflow_logging.py`)
```python
import mlflow

with mlflow.start_run(run_name="cashflow_lgbm_v1"):
    mlflow.log_params({"window_length": 30, "n_estimators": 500})
    mlflow.log_metrics({"MAE": mae, "MAPE": mape, "RMSE": rmse})
    mlflow.sklearn.log_model(model_lgbm, "cashflow_model")
    mlflow.register_model("runs:/.../cashflow_model", "CashflowForecaster")
```

### Bước 6 — Serving & Integration (`6_serve_to_powerbi.py`)
```python
# Xuất forecast ra PostgreSQL để Power BI đọc
forecast_df.to_sql("fact_cashflow_forecast", engine, schema="silver",
                   if_exists="replace", index=False)
```
> **Power BI:** Thêm bảng `silver.fact_cashflow_forecast` vào Data Model → Vẽ Forecast Line với confidence band (Upper/Lower CI).

---

## 5. Cấu trúc thư mục

```
1. Cashflow_Forecasting/
├── README.md               ← File này
├── requirements.txt
├── config.yaml             ← DB connection, hyperparams
├── notebooks/
│   ├── 1_eda.ipynb
│   ├── 2_feature_engineering.ipynb
│   ├── 3_train_model.ipynb
│   ├── 4_evaluate.ipynb
│   └── 5_mlflow_logging.ipynb
├── src/
│   ├── data_loader.py
│   ├── feature_engineering.py
│   ├── train.py
│   └── serve.py
├── models/                 ← Lưu model artifacts
└── outputs/
    └── forecast_results.csv
```

---

## 6. KPIs Đánh giá thành công

| Metric | Target |
|:---|:---|
| MAPE (Mean Absolute % Error) | < 15% trên tập test 3 tháng |
| Coverage (CI 80%) | ≥ 80% actual nằm trong khoảng tin cậy |
| Latency dự báo | < 30 giây/lần chạy |
| Retraining cycle | Hàng tháng (cron Airflow) |

---

## 7. Dependencies

```txt
# requirements.txt
sktime>=0.30.0
lightgbm>=4.0.0
xgboost>=2.0.0
statsmodels>=0.14.0
mlflow>=2.10.0
optuna>=3.5.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pandas>=2.1.0
numpy>=1.26.0
matplotlib>=3.8.0
seaborn>=0.13.0
```
