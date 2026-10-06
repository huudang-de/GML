# KẾ HOẠCH TRIỂN KHAI PHA 2: TRÍCH XUẤT ĐẶC TRƯNG (FEATURE ENGINEERING VỚI NIXTLA)
**Dự án:** Inventory Demand Forecasting (Dự báo Nhu cầu Tồn kho)
**Thư mục làm việc:** `6. ML\3. Inventory_Demand_Forecasting`

## 1. Mục tiêu (Objective)
- Chuyển đổi chuỗi thời gian chuẩn hóa từ Pha 1 (3 cột: `unique_id`, `ds`, `y`) thành **Dữ liệu dạng Bảng (Tabular Data)** đa chiều để đưa vào mô hình học máy Gradient Boosting (LightGBM).
- Ứng dụng sức mạnh của thư viện `mlforecast` để tự động hóa việc sinh ra các đặc trưng:
  - **Lags (Độ trễ):** Lấy dữ liệu bán hàng của ngày hôm qua, tuần trước, tháng trước để dự báo ngày mai.
  - **Lag Transforms (Biến đổi trượt):** Tính Trung bình trượt (Rolling Mean) và Độ lệch chuẩn (Rolling STD) để làm mượt các biến động nhiễu.
  - **Calendar Features (Đặc trưng lịch):** Bóc tách Thứ trong tuần, Tháng, Quý để AI học được tính Mùa vụ (Seasonality).

---

## 2. Kiến trúc Thư mục (Directory Structure)
Sẽ khởi tạo và phát triển các file sau trong Pha 2:
```text
3. Inventory_Demand_Forecasting/
├── PLAN_PHASE2_FEATURE_ENGINEERING.md (File này)
├── src/
│   └── feature_engineering.py # Lõi cấu hình MLForecast Feature Pipeline
├── tests/
│   └── test_feature_engineering.py # Unit tests kiểm tra ma trận đặc trưng
└── scratch/
    └── run_feature_engineering.py # Script xuất thử Ma trận Tabular Data
```

---

## 3. Phân rã công việc (Task Breakdown)

### Task 2.1: Cấu hình Đường ống MLForecast (`src/feature_engineering.py`)
- **Mô tả:** Thay vì code chay bằng Pandas `shift()` và `rolling()`, chúng ta sẽ khởi tạo cấu hình `MLForecast` để nó lo toàn bộ.
- **Action:** Viết hàm `get_feature_pipeline(freq='D')`.
  - Nếu `freq='D'`: Lags = `[1, 7, 14, 28]`. Lag Transforms: Trung bình trượt 7 ngày và 14 ngày của Lag 1. Date Features: `dayofweek`, `month`.
  - Nếu `freq='W'`: Lags = `[1, 2, 4, 12]`. Lag Transforms: Trung bình 4 tuần (1 tháng) của Lag 1. Date Features: `month`, `quarter`.
  - Trả về một object `MLForecast` đã được tinh chỉnh thông số.

### Task 2.2: Tiền xử lý Biến ngoại sinh (Exogenous Variables) (Tùy chọn)
- **Mô tả:** Nhu cầu tồn kho đôi khi phụ thuộc vào các sự kiện đặc biệt (Ngày Lễ / Tết) hoặc Biến động giá (Cost Price).
- **Action:** Viết hàm `add_exogenous_features(df)` để sinh thêm một cột ảo `is_holiday` (1/0) dựa trên cột `ds`. Object `MLForecast` sẽ tự động phát hiện và xử lý cột này (Static hoặc Dynamic feature).

### Task 2.3: Phát triển Kịch bản Kiểm thử (`tests/test_feature_engineering.py`)
- **Action:** Viết Unit tests sử dụng method `preprocess(df)` của `mlforecast`. Khác với hàm `fit()`, hàm `preprocess()` sẽ chỉ chạy Feature Engineering và nhả ra cái bảng Dataframe cuối cùng để kiểm tra, rất hữu ích cho TDD (Test-Driven Development).

### Task 2.4: Khớp nối và Chạy kiểm chứng (`scratch/run_feature_engineering.py`)
- **Action:** Sinh Mock Data (Time-series) của 1 SKU. Đẩy qua `get_feature_pipeline()`. Chạy `.preprocess()` và in ra màn hình 5 dòng cuối cùng của DataFrame để chiêm ngưỡng ma trận đặc trưng khổng lồ mà Nixtla sinh ra.

---

## 4. Kịch bản Kiểm thử (Test Cases)

| Tên Test Case | Đầu vào giả định (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_lags_generation` | DF có 3 cột chuẩn Nixtla (`freq='D'`). | Output DF phải có thêm các cột `lag1`, `lag7`, `lag14`. |
| `test_rolling_features` | DF chuẩn Nixtla. | Output DF phải có cột `rolling_mean_lag1_window7`. Tính tay thử 1 dòng và đối chiếu với code phải khớp (Khớp toán học). |
| `test_date_features` | DF chuẩn Nixtla. | Output DF phải có các cột như `month`, `dayofweek`. Nếu `ds` là 2023-01-02 (Thứ 2), `dayofweek` phải = 0. |
| `test_nan_dropping` | DF có 30 dòng thời gian liên tục (`freq='D'`). Lags max là 14. | Quá trình trích xuất độ trễ (Shift) sẽ tạo ra NaN ở 14 dòng đầu tiên. Hàm preprocess phải tự động loại bỏ (Drop) 14 dòng này. DF Output chỉ còn 16 dòng. |

---

## 5. Tiêu chí Hoàn thành (Definition of Done - DoD)
- [ ] Hàm `get_feature_pipeline` trả về đúng object `MLForecast` đã cấu hình.
- [ ] 100% Test cases trong `test_feature_engineering.py` PASS.
- [ ] Ma trận Dữ liệu Bảng (Tabular Data) sẵn sàng đưa thẳng vào mô hình LightGBM ở Pha 3 mà không bị lỗi tương thích.
