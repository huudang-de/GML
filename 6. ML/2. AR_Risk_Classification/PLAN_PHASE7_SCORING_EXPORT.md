# KẾ HOẠCH TRIỂN KHAI PHA 7: ỨNG DỤNG VÀ XUẤT DỮ LIỆU (SCORING & EXPORT)
**Dự án:** AR Risk Classification
**Thư mục làm việc:** `6. ML\2. AR_Risk_Classification`

## 1. Mục tiêu (Objective)
- Đưa mô hình AI ra khỏi phòng thí nghiệm và đưa vào vận hành thực tế (Production).
- Quét toàn bộ Khách hàng đang nợ tiền (Active Customers) để dự báo Rủi ro.
- Chuyển đổi xác suất Toán học khô khan thành các tín hiệu UI trực quan (Risk Badge, Màu sắc cảnh báo) cho Power BI.
- Ghi kết quả vào Data Warehouse (Mô phỏng bảng `silver.fact_ar_risk_score` trên PostgreSQL).

## 2. Phân rã công việc (Task Breakdown)

### Task 7.1: Xây dựng Cỗ máy Chấm điểm (`src/scoring.py`)
- **Action:** Viết hàm `score_customers(model, X_active)`:
  - Dự báo nhãn (Low/Medium/High Risk).
  - Trích xuất Xác suất bị Nợ xấu (Probability of Default).
  - Ánh xạ Màu sắc UI (Green, Yellow, Red) tương ứng với từng cấp độ rủi ro để Power BI chỉ việc vẽ lên Dashboard.

### Task 7.2: Trình xuất dữ liệu Database (`src/export.py` / Tích hợp)
- **Action:** Định hình schema cho bảng `silver.fact_ar_risk_score` gồm: `customer_id`, `score_date`, `risk_badge`, `default_probability`, `ui_color`.
- **Action:** Viết hàm mô phỏng tiến trình `to_sql()` để đẩy dữ liệu lên Database.

### Task 7.3: Kịch bản Kiểm thử (`tests/test_scoring.py`)
- **Action:** PyTest kiểm tra bảng output có chứa đầy đủ các cột bắt buộc cho Power BI không. Đảm bảo màu sắc được gắn đúng (High Risk bắt buộc phải là Red).

### Task 7.4: Kịch bản Chạy thực tế (`scratch/run_scoring.py`)
- **Action:** Khởi tạo danh sách 5 khách hàng thật, gọi Model MLflow ra chấm điểm, và in ra bảng DB hoàn chỉnh để người dùng xem trước khi đổ lên Power BI.

## 3. Kịch bản Kiểm thử (Test Cases)
| Tên Test Case | Đầu vào (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_scoring_schema` | DataFrame chứa KH cần chấm điểm | Output phải chứa đủ cột: `customer_id`, `risk_badge`, `default_prob`, `ui_color`. |
| `test_ui_color_mapping` | Nhãn dự báo là 2 (High Risk) | Cột `ui_color` tương ứng BẮT BUỘC phải là `#FF4444` (Đỏ). |
