# KẾ HOẠCH TRIỂN KHAI PHA 2: TRÍCH XUẤT ĐẶC TRƯNG & XỬ LÝ MẤT CÂN BẰNG (FEATURE ENGINEERING)
**Dự án:** AR Risk Classification
**Thư mục làm việc:** `6. ML\2. AR_Risk_Classification`

## 1. Mục tiêu (Objective)
- Chuyển đổi dữ liệu từ cấp độ **"Hóa đơn" (Invoice-level)** thành cấp độ **"Khách hàng" (Customer-level)** để huấn luyện mô hình học máy.
- Trích xuất các đặc trưng (Features) về lịch sử thanh toán, quy mô giao dịch.
- Lựa chọn giải pháp xử lý mất cân bằng dữ liệu (Imbalanced Classes) tối ưu cho thuật toán LightGBM.

## 2. Phân rã công việc (Task Breakdown)

### Task 2.1: Xây dựng Feature Aggregator (`src/feature_engineering.py`)
- **Action:** Viết hàm `aggregate_customer_features(df)` để nhóm (groupby) dữ liệu theo `customer_code`.
- **Các Features tạo ra:** 
  - `avg_days_overdue`: Trung bình số ngày trễ (phản ánh thói quen thanh toán).
  - `max_days_overdue`: Số ngày trễ lớn nhất (phản ánh rủi ro tồi tệ nhất).
  - `pct_on_time`: Tỷ lệ thanh toán đúng hạn (độ uy tín).
  - `total_invoices`, `total_amount`, `avg_amount`: Quy mô của khách hàng.

### Task 2.2: Quyết định phương án xử lý Imbalanced Data
- **Phân tích:** Vì nhóm Nợ xấu (High Risk) chỉ chiếm ~15%, nếu để nguyên, mô hình sẽ có xu hướng dự đoán toàn bộ là Low/Medium Risk. Tuy nhiên, việc dùng SMOTE tạo dữ liệu giả đối với Tabular Data (dữ liệu bảng) và mô hình Tree-based (LightGBM) thường làm chậm mô hình và sinh ra các mẫu (samples) không thực tế.
- **Giải pháp:** Sử dụng Kỹ thuật **Class Weights (Trọng số lớp)** tự động phạt mô hình nặng hơn khi nó dự đoán sai lớp thiểu số.
- **Action:** Viết hàm `get_balanced_class_weights(y)` để tự động tính trọng số bù đắp.

### Task 2.3: Phát triển Kịch bản Kiểm thử (`tests/test_feature_engineering.py`)
- **Action:** Viết Unit Tests (PyTest) kiểm tra tính chính xác của hàm groupby và logic gán trọng số.

### Task 2.4: Chạy thử nghiệm Pipeline (`scratch/run_feature_engineering.py`)
- **Action:** Chạy script tạo features từ data hóa đơn, in ra ma trận feature của Khách hàng để kiểm chứng.

## 3. Kịch bản Kiểm thử (Test Cases)
| Tên Test Case | Đầu vào (Input) | Kết quả Kỳ vọng |
| :--- | :--- | :--- |
| `test_customer_aggregation` | KH A có 2 hóa đơn: 1 trả đúng hạn, 1 trễ 30 ngày. | pct_on_time = 50%, avg_days_overdue = 15 |
| `test_class_weights` | Tập nhãn Y có: 80% nhãn 0, 20% nhãn 2. | Trọng số (Weight) của nhãn 2 > nhãn 0 |
