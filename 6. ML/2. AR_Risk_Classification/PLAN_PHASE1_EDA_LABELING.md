# KẾ HOẠCH TRIỂN KHAI PHA 1: KHÁM PHÁ DỮ LIỆU & TẠO NHÃN (EDA & LABEL ENGINEERING)
**Dự án:** AR Risk Classification (Phân loại rủi ro công nợ)
**Thư mục làm việc:** `6. ML\2. AR_Risk_Classification`

## 1. Mục tiêu (Objective)
- Chuyển đổi dữ liệu thô từ hệ thống Kế toán (Silver layer) thành dữ liệu có nhãn phục vụ cho học máy có giám sát (Supervised Learning).
- Định lượng chính xác số ngày trễ hạn (`days_overdue`) cho toàn bộ lịch sử thanh toán.
- Khám phá sự mất cân bằng dữ liệu (Class Imbalance) giữa các nhóm Low, Medium và High Risk để lên chiến lược xử lý ở Pha 2.

## 2. Kiến trúc Thư mục (Directory Structure)
Sẽ khởi tạo và phát triển các file sau trong Pha này:
```text
2. AR_Risk_Classification/
├── PLAN_PHASE1_EDA_LABELING.md (File này)
├── src/
│   ├── __init__.py
│   ├── data_loader.py         # Hàm kết nối và load data từ DB
│   └── label_engineering.py   # Chứa logic gán nhãn
├── tests/
│   ├── __init__.py
│   └── test_labeling.py       # Unit tests đảm bảo tính toàn vẹn của nhãn
└── scratch/
    └── run_eda.py             # Script chạy phân tích thống kê (EDA)
```

## 3. Phân rã công việc (Task Breakdown)

### Task 1: Xây dựng Data Loader (`src/data_loader.py`)
- **Action:** Viết class `PostgresDataLoader` dùng `sqlalchemy` và `pandas`.
- **Query:** Join bảng `silver.fact_accountsreceivable` với `silver.dim_partner`.
- **Output:** Trả về một Pandas DataFrame chuẩn hóa.

### Task 2: Cài đặt Logic Kỹ thuật Nhãn (`src/label_engineering.py`)
- **Action:** Xây dựng hàm `calculate_days_overdue(df, current_date)`.
  - Nếu hóa đơn ĐÃ thanh toán: `days_overdue = payment_date - due_date`.
  - Nếu hóa đơn CHƯA thanh toán: `days_overdue = current_date - due_date`.
- **Action:** Xây dựng hàm `assign_risk_label(df)`.
  - `days_overdue <= 0` $\rightarrow$ Nhãn `0` (Low Risk - An toàn).
  - `0 < days_overdue <= 60` $\rightarrow$ Nhãn `1` (Medium Risk - Trễ hạn nhẹ).
  - `days_overdue > 60` $\rightarrow$ Nhãn `2` (High Risk - Nợ xấu).

### Task 3: Phát triển Kịch bản Kiểm thử (`tests/test_labeling.py`)
- **Action:** Dùng `pytest` lập trình 3 kịch bản kiểm thử tĩnh để chặn lỗi rò rỉ dữ liệu (data leakage) và lỗi phân loại.

### Task 4: Chạy Phân tích Thống kê - EDA (`scratch/run_eda.py`)
- **Action:** Lắp ghép Task 1 và 2 để chạy trên dữ liệu thật. Tính toán tổng số lượng dòng, tỷ lệ % của từng nhãn (0, 1, 2) và xuất báo cáo ra log.

## 4. Kịch bản Kiểm thử (Test Cases)
| Tên Test Case | Mô tả (Dữ liệu giả lập) | Kết quả Kỳ vọng |
| :--- | :--- | :--- |
| `test_paid_on_time` | Đáo hạn 10/10/2026. Trả ngày 05/10. | days_overdue = -5, label = 0 |
| `test_unpaid_overdue_short`| Đáo hạn 01/09. Chưa trả. (Chấm ngày 06/10) | days_overdue = 35, label = 1 |
| `test_paid_late_long` | Đáo hạn 01/06. Trả ngày 01/10. | days_overdue = 122, label = 2 |

## 5. Tiêu chí Hoàn thành (Definition of Done - DoD)
- [ ] Các file script Python được tạo không có lỗi cú pháp (Syntax error-free).
- [ ] Chạy lệnh `pytest tests/test_labeling.py` trả về kết quả 100% PASS.
- [ ] Chạy thành công `run_eda.py` và lấy được báo cáo phân phối nhãn (Class distribution).
- [ ] Toàn bộ pipeline này sẵn sàng để được import vào Pha 2 (Feature Engineering).
