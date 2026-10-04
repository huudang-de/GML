# 📦 Tối ưu hóa Chu kỳ Tồn kho — Inventory Demand Forecasting

> **Mức ưu tiên:** ⭐⭐⭐⭐⭐ | **Framework chính:** Nixtla (MLForecast/StatsForecast) | **Model:** LightGBM + Statistical Forecasting | **Bổ trợ:** OR-Tools / scipy

---

## 1. Bài toán & Mục tiêu

### Vấn đề hiện tại
Việc quyết định nhập hàng (gỗ ván, nẹp, giấy) tại Gỗ Minh Long vẫn đang mang tính **cảm tính** hoặc dựa trên kinh nghiệm cá nhân. Hệ quả:
- **Tồn kho chết (Dead Stock):** Nhập quá nhiều, vốn bị chôn vùi, DIO (Days Inventory Outstanding) cao.
- **Out-of-Stock:** Thiếu hàng khi vào mùa cao điểm, ảnh hưởng đơn hàng.

### Mục tiêu dự án ML (2 trong 1)
**Phần 1 — Dự báo nhu cầu (Demand Forecasting):**
Dự báo số lượng xuất kho từng sản phẩm (Giấy, Nẹp, Ván) trong 4–8 tuần tới.

**Phần 2 — Tối ưu Reorder Point (Điểm đặt hàng lại):**
Tính toán `Reorder Point` và `Economic Order Quantity (EOQ)` tối ưu cho từng SKU dựa trên kết quả dự báo.

---

## 2. Nguồn dữ liệu

| Bảng nguồn | Trường sử dụng | Mô tả |
|:---|:---|:---|
| `silver.fact_inventoryoutward` | `posting_date`, `item_code`, `quantity`, `amount` | Lịch sử xuất kho (proxy = demand) |
| `silver.fact_inventoryinward` | `posting_date`, `item_code`, `quantity`, `amount` | Lịch sử nhập kho |
| `silver.fact_inventory` | `report_date`, `item_code`, `closing_qty`, `closing_value` | Tồn kho cuối kỳ |
| `silver.dim_item` | `item_code`, `item_name`, `category` | Danh mục sản phẩm |
| `silver.dim_date` | `date`, `month`, `quarter`, `is_holiday` | Calendar features |

---

## 3. Kiến trúc Pipeline

```
PostgreSQL (Silver Layer)
        │
        ▼
[1. Data Preparation]
  - Tạo chuỗi thời gian xuất kho theo ngày/tuần cho từng SKU
  - Điền missing dates (ngày không xuất kho = 0)
  - Phát hiện và xử lý outlier (ngày nhập kho đặc biệt)
        │
        ▼
[2. Feature Engineering (Nixtla MLForecast style)]
  - Lag features theo SKU (lagged_demand_7, 14, 28)
  - Rolling aggregations (rolling_mean, rolling_std)
  - Calendar: month, quarter, is_month_end
  - Price signal: avg_unit_cost (từ fact_inventoryinward)
        │
        ▼
[3. Demand Forecasting — Nixtla Stack]
  ┌────────────────────────────────────────────────────────┐
  │  StatsForecast:  AutoETS, AutoARIMA, AutoCES           │
  │  MLForecast:     LightGBM, XGBoost                     │
  │  Cross-learning: 1 model cho tất cả SKU (scalable!)    │
  └────────────────────────────────────────────────────────┘
        │
        ▼
[4. Inventory Optimization — OR-Tools / scipy]
  - Tính Safety Stock = Z × σ_demand × √lead_time
  - Tính Reorder Point (ROP) = avg_demand × lead_time + safety_stock
  - Tính EOQ (Economic Order Quantity) với scipy.optimize
        │
        ▼
[5. Backtesting & Evaluation]
  - Cross-validation bằng Nixtla TimeSeriesCrossValidation
  - Metrics: MAE, RMSE, MAPE theo từng SKU & category
        │
        ▼
[6. MLflow Tracking]
        │
        ▼
[7. Export & Integration]
  - Kết quả dự báo → silver.fact_inventory_forecast
  - Reorder recommendations → silver.fact_reorder_recommendations
  - Power BI hiển thị: Forecast vs Actual + Reorder Alerts
```

---

## 4. Chi tiết từng bước triển khai

### Bước 1 — EDA & Time Series Preparation (`1_eda.ipynb`)
- [ ] Aggregate dữ liệu xuất kho theo tuần và theo từng `item_code`
- [ ] Kiểm tra tính liên tục của chuỗi (Intermittent Demand?)
- [ ] Phân tích Seasonality theo loại hàng (Giấy, Nẹp, Ván)
- [ ] Xác định `lead_time` (thời gian từ đặt hàng đến nhập kho)

### Bước 2 — Nixtla StatsForecast Baseline (`2_stats_forecast.ipynb`)
```python
from statsforecast import StatsForecast
from statsforecast.models import AutoETS, AutoARIMA, AutoCES

# Nixtla format: ds, unique_id (item_code), y (quantity)
df_nixtla = df.rename(columns={
    'posting_date': 'ds',
    'item_code': 'unique_id',
    'quantity': 'y'
})

sf = StatsForecast(
    models=[AutoETS(season_length=52), AutoARIMA(season_length=52), AutoCES()],
    freq='W',
    n_jobs=-1   # Chạy song song tất cả SKU!
)
sf.fit(df_nixtla)
forecasts = sf.predict(h=8)  # Dự báo 8 tuần tới
```

### Bước 3 — Nixtla MLForecast Champion (`3_ml_forecast.ipynb`)
```python
from mlforecast import MLForecast
from mlforecast.target_transforms import Differences
from lightgbm import LGBMRegressor
import numpy as np

mlf = MLForecast(
    models=[LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=31)],
    freq='W',
    lags=[1, 2, 4, 8, 13, 26, 52],
    lag_transforms={
        1: [(rolling_mean, 4), (rolling_std, 4)],
        4: [(rolling_mean, 8)],
    },
    date_features=['week', 'month', 'quarter'],
    target_transforms=[Differences([1])]
)

mlf.fit(df_nixtla)
forecasts_ml = mlf.predict(h=8, level=[80, 95])  # Kèm Confidence Interval
```

### Bước 4 — Inventory Optimization (`4_optimization.ipynb`)
```python
from scipy.optimize import minimize
import numpy as np

def calculate_reorder_point(avg_demand, std_demand, lead_time_weeks, service_level=0.95):
    """
    ROP = avg_demand * lead_time + Z * std_demand * sqrt(lead_time)
    Service Level 95% → Z = 1.645
    """
    from scipy.stats import norm
    Z = norm.ppf(service_level)
    safety_stock = Z * std_demand * np.sqrt(lead_time_weeks)
    rop = avg_demand * lead_time_weeks + safety_stock
    return round(rop, 2), round(safety_stock, 2)


def economic_order_quantity(annual_demand, ordering_cost, holding_cost_rate, unit_cost):
    """
    EOQ = sqrt(2 * D * S / (h * C))
    D = annual demand, S = ordering cost, h = holding rate, C = unit cost
    """
    holding_cost = holding_cost_rate * unit_cost
    eoq = np.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
    return round(eoq, 0)
```

### Bước 5 — OR-Tools nâng cao: Multi-SKU Lot Sizing (`5_ortools_optimization.ipynb`)
```python
from ortools.linear_solver import pywraplp

# Bài toán: Tối ưu kế hoạch nhập hàng (lot sizing)
# Constraints: Budget tháng, Sức chứa kho, Lead time
# Objective: Minimize (Holding Cost + Ordering Cost + Stockout Penalty)
solver = pywraplp.Solver.CreateSolver('SCIP')
```

### Bước 6 — MLflow (`6_mlflow_tracking.py`)
```python
import mlflow

with mlflow.start_run(run_name="inventory_lgbm_v1"):
    mlflow.log_params({"lags": "[1,2,4,8,13,26,52]", "h": 8})
    for sku, metrics in sku_metrics.items():
        mlflow.log_metrics({f"mape_{sku}": metrics['mape']}, step=0)
    mlflow.sklearn.log_model(mlf, "inventory_forecast_model")
```

### Bước 7 — Export & Power BI (`7_export.py`)
```python
# Forecast results
forecast_df.to_sql("fact_inventory_forecast", engine, schema="silver",
                   if_exists="replace", index=False)

# Reorder recommendations
reorder_df.to_sql("fact_reorder_recommendations", engine, schema="silver",
                  if_exists="replace", index=False)
```

**Tích hợp Power BI:**
- Visual 1: **Line Chart** — Actual Quantity vs Forecasted Quantity (8 tuần tới) với confidence bands.
- Visual 2: **Alert Table** — Danh sách SKU cần đặt hàng ngay (tồn kho hiện tại < ROP).
- Visual 3: **KPI Card** — DIO (Days Inventory Outstanding) dự kiến sau khi optimize.

---

## 5. Cấu trúc thư mục

```
3. Inventory_Demand_Forecasting/
├── README.md
├── requirements.txt
├── config.yaml
├── notebooks/
│   ├── 1_eda.ipynb
│   ├── 2_stats_forecast.ipynb
│   ├── 3_ml_forecast.ipynb
│   ├── 4_optimization.ipynb
│   ├── 5_ortools_optimization.ipynb
│   └── 6_mlflow_tracking.ipynb
├── src/
│   ├── data_loader.py
│   ├── feature_engineering.py
│   ├── forecast.py
│   ├── optimize.py
│   └── export.py
├── models/
└── outputs/
    ├── demand_forecast.csv
    └── reorder_recommendations.csv
```

---

## 6. KPIs Đánh giá thành công

| Metric | Target |
|:---|:---|
| MAPE tổng hợp (tất cả SKU) | < 20% |
| MAPE nhóm hàng A (top doanh thu) | < 15% |
| % SKU được tính ROP tự động | 100% |
| Giảm DIO sau khi áp dụng EOQ | Mục tiêu giảm 10–15% |
| Stockout rate | < 5% |
| Retraining cycle | Hàng tuần (cron Airflow) |

---

## 7. Dependencies

```txt
# requirements.txt
statsforecast>=1.7.0
mlforecast>=0.13.0
lightgbm>=4.0.0
xgboost>=2.0.0
mlflow>=2.10.0
ortools>=9.8.0
scipy>=1.12.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pandas>=2.1.0
numpy>=1.26.0
matplotlib>=3.8.0
utilsforecast>=0.1.0
```
