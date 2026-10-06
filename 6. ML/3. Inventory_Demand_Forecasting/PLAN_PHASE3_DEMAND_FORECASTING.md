# KẾ HOẠCH TRIỂN KHAI PHA 3: HUẤN LUYỆN MÔ HÌNH DỰ BÁO (DEMAND FORECASTING)
**Dự án:** Inventory Demand Forecasting
**Thư mục làm việc:** `6. ML\3. Inventory_Demand_Forecasting`

## 1. Mục tiêu (Objective)
- Khớp nối (Fit) dữ liệu chuẩn vào đường ống tính năng đã dựng ở Pha 2.
- Huấn luyện **Global Model (LightGBM)**: Chỉ dùng một mô hình duy nhất học chéo trên toàn bộ các mã vật tư (SKU).
- **Dự báo Điểm & Khoảng (Point & Interval Forecasting):** Không chỉ dự báo số lượng xuất kho cụ thể (Point forecast), hệ thống phải xuất ra cả Khoảng tin cậy (Confidence Interval, ví dụ 90%, 95%) để lượng hóa mức độ rủi ro, làm cơ sở tính Tồn kho an toàn (Safety Stock) ở Pha 4.
- Đánh giá sức mạnh mô hình bằng cơ chế **Walk-Forward Time-Series Cross Validation**, tính toán MAPE, RMSE cho từng mã hàng.

---

## 2. Kiến trúc Thư mục (Directory Structure)
Sẽ khởi tạo và phát triển các file sau trong Pha 3:
```text
3. Inventory_Demand_Forecasting/
├── PLAN_PHASE3_DEMAND_FORECASTING.md (File này)
├── src/
│   └── forecast.py            # Lõi Huấn luyện, Dự báo và Tính độ lỗi
├── tests/
│   └── test_forecast.py       # Unit tests kiểm tra output của thuật toán
└── scratch/
    └── run_forecast.py        # Script chạy End-to-End Pipeline (Train + Predict)
```

---

## 3. Phân rã công việc (Task Breakdown)

### Task 3.1: Huấn luyện và Dự báo (Train & Predict) - (`src/forecast.py`)
- **Mô tả:** Sử dụng object MLForecast để train mô hình và xuất ra con số tương lai.
- **Action:** Viết hàm `train_and_predict(df, h=8, freq='D', levels=[80, 95])`.
  - Nhận vào dữ liệu gốc (đã qua Data Prep - Pha 1).
  - Gọi hàm `get_feature_pipeline(freq)` (từ Pha 2) để lấy Pipeline.
  - Chạy `mlf.fit(df, static_features=[])`.
  - Chạy `mlf.predict(h, level=levels)`. Hàm này sẽ tự động sinh các cột điểm cận dưới (lo) và cận trên (hi) của khoảng tin cậy.

### Task 3.2: Kiểm định chéo theo Trục thời gian (Time-Series CV)
- **Mô tả:** Không dùng K-Fold (vì K-Fold trộn lẫn ngẫu nhiên thời gian tương lai vào quá khứ gây Data Leakage). Phải dùng Walk-Forward CV.
- **Action:** Viết hàm `evaluate_cross_validation(df, h=4, n_windows=3)`.
  - Sử dụng phương thức `mlf.cross_validation(df, n_windows, h)`.
  - Cơ chế: Mô hình tự động trượt lùi về quá khứ 3 lần (3 windows), mỗi lần giấu đi `h` bước để làm tập Test, train trên dữ liệu trước đó, rồi dự báo và tính lỗi so với Test thực tế.

### Task 3.3: Tính toán Chỉ số Đánh giá (Metrics Calculation)
- **Action:** Viết hàm `calculate_metrics(cv_df)`.
  - Dùng thư viện `utilsforecast.losses` (đi kèm Nixtla).
  - Tính các chỉ số MAE, RMSE, MAPE.
  - Gom nhóm (Groupby) kết quả theo từng `unique_id` (để biết mã ván nào mô hình học tốt, mã nào học kém) và theo toàn bộ hệ thống (Global Metric).

### Task 3.4: Phát triển Kịch bản Kiểm thử (`tests/test_forecast.py`)
- **Action:** Viết Unit tests sử dụng PyTest (Chi tiết ở Mục 4).

### Task 3.5: Khớp nối và Chạy Mô phỏng (End-to-End Run)
- **Action:** Tạo file `scratch/run_forecast.py`.
- **Dữ liệu giả lập:** Tạo ra 2 SKU.
  - SKU 1: Nhu cầu ổn định đan xen (Stationary).
  - SKU 2: Nhu cầu có xu hướng tăng dần theo chu kỳ (Trending).
- Chạy qua toàn bộ Pha 1 -> Pha 2 -> Pha 3.
- In ra Bảng kết quả dự báo tương lai cùng Khoảng tin cậy (Lower Bound - Upper Bound).

---

## 4. Kịch bản Kiểm thử (Test Cases)

| Tên Test Case | Đầu vào giả định (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_predict_horizon_shape` | DF chứa 3 SKU. Yêu cầu dự báo `h = 5` (5 bước tới). | Bảng dữ liệu dự báo trả về phải có đúng $3 \times 5 = 15$ dòng dữ liệu. |
| `test_confidence_intervals` | DF chứa 1 SKU. `h = 3`. `levels = [95]`. | Cột output bắt buộc phải chứa `LGBMRegressor` (dự báo trung tâm), `LGBMRegressor-lo-95` (cận dưới) và `LGBMRegressor-hi-95` (cận trên). |
| `test_cross_validation_windows` | Yêu cầu CV với `n_windows = 2`, `h = 2` trên 1 SKU. | Hàm phải sinh ra đủ 2 mốc `cutoff` (điểm cắt thời gian) khác nhau, với tổng số lượng dự báo test là $2 \times 2 = 4$ dòng. |
| `test_metrics_calculation` | Truyền DF kết quả CV ảo. | Hàm tính MAPE phải trả về lỗi tương đối chuẩn xác, không bị lỗi khi thực tế $y = 0$ (sử dụng sMAPE hoặc MAPE có kiểm soát). |

---

## 5. Tiêu chí Hoàn thành (Definition of Done - DoD)
- [ ] Hàm Predict trả về đúng số dòng theo công thức: $Số\_lượng\_SKU \times Horizon\_h$.
- [ ] 100% Test cases PASS.
- [ ] Báo cáo kết quả dự báo mô phỏng thành công các dải giá trị Lower - Upper, đóng vai trò sống còn để nạp vào thuật toán tính Safety Stock ở Pha 4.
