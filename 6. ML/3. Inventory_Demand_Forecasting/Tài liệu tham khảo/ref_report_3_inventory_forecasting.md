# 📦 Báo cáo Tham khảo #3: Inventory Demand Forecasting
## Dự án: `Nixtla/mlforecast` & `Google OR-Tools`

> **Link:** https://github.com/Nixtla/mlforecast
> **Liên quan đến:** `6. ML / 3. Inventory_Demand_Forecasting` của GML  
> **Ngày nghiên cứu:** 04/10/2026

---

## 1. Tổng quan thư viện `mlforecast`

`mlforecast` là thư viện mã nguồn mở cực kỳ nổi tiếng (backed bởi startup Nixtla), giúp biến bài toán dự báo Time-Series phức tạp thành bài toán Machine Learning truyền thống bằng cách tự động hóa Feature Engineering.

| Thuộc tính | Giá trị |
|:---|:---|
| **Cốt lõi** | Chuyển đổi Time-Series → Tabular Data |
| **Tốc độ** | Nhanh hơn Prophet gấp nhiều lần (huấn luyện Global Model) |
| **Model hỗ trợ** | Bất kỳ model nào dùng `.fit()`, `.predict()` (LightGBM, XGBoost, Random Forest) |
| **Khả năng Scale** | Có thể dự báo cùng lúc hàng ngàn SKU (Mã vật tư) mà không cần train từng model rời rạc (Cross-learning). |

---

## 2. Kiến trúc Code chuẩn (Dựa trên tutorial của Nixtla)

Bài toán Inventory Demand cho Gỗ Minh Long cần tính toán **Lags** (Độ trễ) và **Rolling Mean** (Trung bình trượt) để LightGBM học được tính chu kỳ của nhu cầu ván gỗ.

### Mẫu code tiêu chuẩn từ `mlforecast`:

```python
import pandas as pd
import lightgbm as lgb
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean

# 1. Định nghĩa Model và Feature Engineering tự động
fcst = MLForecast(
    models=[lgb.LGBMRegressor(n_jobs=-1, random_state=42)],
    freq='D',  # Tần suất ngày (Daily)
    lags=[1, 7, 30],  # Sinh feature: Nhu cầu của 1 ngày trước, 1 tuần trước, 1 tháng trước
    lag_transforms={
        # Từ độ trễ 1 ngày, tính trung bình trượt 7 ngày và 30 ngày (Moving Average)
        1: [RollingMean(window_size=7), RollingMean(window_size=30)]
    },
    date_features=['dayofweek', 'month', 'quarter']  # Tự sinh feature Lịch
)

# 2. Fit model (Huấn luyện GLOBAL MODEL cho tất cả SKU)
# df cần 3 cột: unique_id (Mã vật tư), ds (Ngày), y (Số lượng xuất kho)
fcst.fit(df)

# 3. Dự báo cho 30 ngày tới
predictions = fcst.predict(h=30)
```

**Tại sao kiến trúc này hoàn hảo cho GML?**
- Gỗ Minh Long có hàng trăm mã màu (Mã vật tư/SKU).
- Nếu dùng ARIMA/Prophet: Phải train hàng trăm model rời rạc (rất chậm).
- Dùng `mlforecast` + LightGBM: Chỉ train **1 model duy nhất** (Global Model), model tự nhận biết xu hướng chéo (cross-learning) giữa các mã màu có vân gỗ tương tự nhau.

---

## 3. Exogenous Variables (Biến ngoại sinh)

Nhu cầu tồn kho không chỉ phụ thuộc lịch sử, mà còn phụ thuộc các yếu tố bên ngoài. `mlforecast` hỗ trợ:
- `is_holiday` (Ngày lễ Tết).
- `promotion_flag` (Chương trình khuyến mãi giảm giá ván).
- `price` (Giá bán tại thời điểm đó).

**Cách áp dụng:** Chỉ cần thêm các cột này vào DataFrame, `mlforecast` sẽ tự động coi đó là dynamic exogenous variables.

---

## 4. Tối ưu hóa Lưu kho với OR-Tools (EOQ/ROP)

Dự báo (Forecasting) chỉ cho biết **"Tháng sau bán được bao nhiêu"**.
Nó không trả lời được câu hỏi cốt lõi của Supply Chain: **"Vậy hôm nay cần ĐẶT BAO NHIÊU hàng, và KHI NÀO đặt?"**

Để giải quyết, chúng ta kết hợp **Google OR-Tools** (Linear/Mixed-Integer Programming).

### Luồng tích hợp (Pipeline)

```text
[1. Dự báo bằng mlforecast] 
       Dự báo Demand (D) cho 30 ngày tới là 5000 tấm ván.
               │
               ▼
[2. Thu thập tham số tài chính từ Fact/Dim]
       - Phí lưu kho (Holding cost - H)
       - Phí đặt hàng (Ordering cost - S)
       - Lead time (Thời gian nhà cung cấp giao hàng)
               │
               ▼
[3. Giải thuật OR-Tools / Toán học (EOQ & ROP)]
       - EOQ (Economic Order Quantity) = sqrt((2 * D * S) / H)
       - ROP (Reorder Point) = (Lead Time * Daily Demand) + Safety Stock
               │
               ▼
[4. Output cho Dashboard]
       "Cảnh báo: Tồn kho mã A đang < ROP. Cần đặt ngay số lượng EOQ = 1,200 tấm."
```

### Kiến thức OR-Tools mở rộng (Dành cho Cấp độ Cao cấp)
Nếu bài toán phức tạp hơn (ví dụ: kho chỉ chứa tối đa 10,000 tấm, ngân sách mua hàng chỉ có 5 tỷ), bạn không thể dùng công thức EOQ đơn giản mà phải dùng **MIP Solver** của OR-Tools.

*Tham khảo keyword:* `inventory optimization OR-tools python mixed integer programming constraint`.
Google có thư viện `ortools.linear_solver` chuyên để code các bài toán ràng buộc (constraints) này.

---

## 5. Tổng kết Roadmap Triển khai

1. **Giai đoạn 1 (Baseline):** Query dữ liệu từ `fact_inventory` và `fact_sales` → Gom nhóm theo Ngày + Mã vật tư.
2. **Giai đoạn 2 (Forecasting):** Dùng `mlforecast` để tính Demand Prediction (D) cho 30-90 ngày tới.
3. **Giai đoạn 3 (Optimization):** Tính toán EOQ, ROP, Safety Stock bằng Python (dùng công thức hoặc OR-Tools).
4. **Giai đoạn 4 (Serving):** Ghi kết quả vào bảng `fact_inventory_optimized` để Power BI lên báo cáo trực quan cho khối Mua hàng.
