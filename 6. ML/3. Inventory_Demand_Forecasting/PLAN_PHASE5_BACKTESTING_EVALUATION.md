# KẾ HOẠCH TRIỂN KHAI PHA 5: KIỂM ĐỊNH LÙI VÀ ĐÁNH GIÁ (BACKTESTING & EVALUATION)
**Dự án:** Inventory Demand Forecasting
**Thư mục làm việc:** `6. ML\3. Inventory_Demand_Forecasting`

## 1. Mục tiêu (Objective)
- Nếu Pha 3 tập trung vào việc "Làm sao để sinh ra số dự báo", thì Pha 5 tập trung vào việc **"Số dự báo đó đáng tin cậy đến mức nào?"**.
- Thực hiện **Backtesting** (Kiểm định lùi) một cách hệ thống và quy mô lớn trên toàn bộ danh mục sản phẩm.
- Phân tích sâu độ lỗi (MAE, RMSE, MAPE) ở nhiều lăng kính:
  - Cấp độ vi mô: Từng mã vật tư (SKU).
  - Cấp độ vĩ mô: **Nhóm hàng hóa (Category)** (Ví dụ: Ván MDF, Nẹp nhựa, Giấy trang trí) để tìm ra nhóm nào AI dự báo tốt nhất, nhóm nào kém nhất để tinh chỉnh.
- Đánh giá Benchmark (Chỉ số tham chiếu): Tính tỷ lệ % cải thiện (Improvement) của mô hình AI so với các thuật toán Naive (Dự báo ngây thơ - Lấy doanh số ngày hôm qua đắp cho ngày mai).

---

## 2. Kiến trúc Thư mục (Directory Structure)
Sẽ khởi tạo và phát triển các file sau trong Pha 5:
```text
3. Inventory_Demand_Forecasting/
├── PLAN_PHASE5_BACKTESTING_EVALUATION.md (File này)
├── src/
│   └── evaluation.py          # Chứa logic đánh giá chuyên sâu theo Category
├── tests/
│   └── test_evaluation.py     # Unit tests kiểm tra hàm đo lường độ lỗi
└── scratch/
    └── run_backtesting.py     # Kịch bản sinh Báo cáo Backtest chi tiết
```

---

## 3. Phân rã công việc (Task Breakdown)

### Task 5.1: Xây dựng Module Đánh giá theo Phân loại (`src/evaluation.py`)
- **Mô tả:** Nhóm các chỉ số lỗi rời rạc của hàng trăm SKU lại thành các bản tin dễ đọc cho Giám đốc Mua hàng.
- **Action:** Viết hàm `evaluate_by_category(cv_df, item_dim_df)`.
  - Nhận bảng kết quả Time-Series Cross Validation (Pha 3).
  - Hợp nhất (Merge) với danh mục sản phẩm (`silver.dim_item`) để lấy thông tin Nhóm hàng (Category).
  - Dùng hàm `evaluate()` để tính toán.
  - Gom nhóm (Groupby) tính độ lỗi trung bình theo `category`.

### Task 5.2: Phân loại Tốp dẫn đầu và Tốp chót (Top/Worst Performers)
- **Mô tả:** Nhận diện những mã hàng bị dự báo sai quá lớn (để loại khỏi AI hoặc chuyển sang mua thủ công).
- **Action:** Viết hàm `get_worst_performers(metrics_df, top_n=5, metric='mape')`.
  - Trích xuất ra N mã hàng có độ lỗi MAPE/RMSE cao nhất.

### Task 5.3: Viết kịch bản kiểm thử (`tests/test_evaluation.py`)
- **Action:** Viết Unit Tests (Xem chi tiết tại Mục 4). Bắt buộc phải tính đúng toán học của các chỉ số MAE (Sai số tuyệt đối trung bình) và MAPE (Sai số phần trăm tuyệt đối trung bình).

### Task 5.4: Kịch bản Chạy Backtesting Toàn diện (`scratch/run_backtesting.py`)
- **Action:** Lập trình script End-to-End:
  - Sinh Mock Data cho **10 SKU**, chia làm 3 nhóm (Ván, Giấy, Nẹp).
  - Chạy `evaluate_cross_validation` (Walk-Forward CV với 4 Windows).
  - Đưa dữ liệu qua `evaluation.py`.
  - **In ra Console 3 Báo cáo:** 
    1. Báo cáo Độ lỗi theo Nhóm Hàng (Category Report).
    2. Báo cáo Toàn hệ thống (Global Metrics).
    3. Cảnh báo Top 3 SKU có dự báo tồi nhất (Worst Performers Alert).

---

## 4. Kịch bản Kiểm thử (Test Cases)

| Tên Test Case | Đầu vào giả định (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_category_aggregation` | Dữ liệu CV của 2 SKU ('VAN-01', 'VAN-02') cùng thuộc nhóm 'Ván'. | Output trả về 1 dòng duy nhất cho nhóm 'Ván', trong đó `mape` của nhóm 'Ván' = trung bình `mape` của VAN-01 và VAN-02. |
| `test_missing_category_handling` | Dữ liệu CV có 'SKU-999' nhưng mã này chưa khai báo trong bảng `dim_item`. | Kịch bản không bị Crash (sập). Mã này tự động được gán nhãn Category là `'Unknown'`. |
| `test_worst_performers` | Bảng Metrics có 5 SKU với MAPE lần lượt: 5%, 10%, 80%, 20%, 90%. | Hàm `get_worst_performers(top_n=2)` trả về 2 SKU có lỗi 90% và 80%. |
| `test_metric_math_logic` | Mock CV có 1 dòng: `y_true = 10`, `y_pred = 8` | Đảm bảo thư viện tính đúng: `MAE = 2`, `MAPE = 20%`. |

---

## 5. Tiêu chí Hoàn thành (Definition of Done - DoD)
- [ ] 100% Kịch bản kiểm thử trong `test_evaluation.py` báo PASS.
- [ ] Script Backtesting chạy mượt mà, phân cấp rành mạch độ tin cậy của AI thành các báo cáo trực quan, sẵn sàng làm Dashboard "Đánh giá Hiệu năng AI" trên Power BI.
