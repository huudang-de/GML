# KẾ HOẠCH TRIỂN KHAI PHA 1: CHUẨN BỊ DỮ LIỆU CHUỖI THỜI GIAN (DATA PREPARATION)
**Dự án:** Inventory Demand Forecasting (Dự báo Nhu cầu Tồn kho)
**Thư mục làm việc:** `6. ML\3. Inventory_Demand_Forecasting`

## 1. Mục tiêu (Objective)
- Xây dựng một đường ống (pipeline) làm sạch và định hình dữ liệu từ Database (bảng `silver.fact_inventoryoutward`) thành định dạng chuẩn cho mô hình Time-Series.
- **Tiêu chuẩn Nixtla/MLForecast:** Dữ liệu bắt buộc phải được chuyển về cấu trúc 3 cột: `unique_id` (mã SKU), `ds` (thời gian), `y` (nhu cầu/xuất kho).
- **Tính liên tục:** Bổ sung các ngày/tuần không có giao dịch xuất kho và điền giá trị 0 (Zero-filling) để chuỗi thời gian không bị đứt gãy.
- **Tính bền vững (Robustness):** Phát hiện và làm phẳng các giá trị xuất kho ngoại lai (Outliers) - ví dụ xuất thanh lý, xuất điều chuyển kho ảo - để không làm méo mó khả năng học của AI.

---

## 2. Kiến trúc Thư mục (Directory Structure)
Sẽ khởi tạo và phát triển các file sau trong Pha 1:
```text
3. Inventory_Demand_Forecasting/
├── PLAN_PHASE1_DATA_PREPARATION.md (File này)
├── src/
│   ├── __init__.py
│   ├── data_loader.py         # Hàm kết nối CSDL và Gom nhóm (Aggregation)
│   └── data_prep.py           # Logic xử lý Missing dates và Outliers
├── tests/
│   ├── __init__.py
│   └── test_data_prep.py      # Unit tests bắt buộc vượt qua
└── scratch/
    └── run_data_prep.py       # Script chạy kịch bản mô phỏng trực tiếp
```

---

## 3. Phân rã công việc (Task Breakdown)

### Task 1.1: Trích xuất và Gom nhóm Dữ liệu (`src/data_loader.py`)
- **Mô tả:** Chuyển đổi dữ liệu giao dịch từng dòng thành dữ liệu tổng hợp theo chu kỳ.
- **Action 1:** Viết hàm `aggregate_demand(df, freq='W')`.
  - Tham số `freq` hỗ trợ `'D'` (Daily) hoặc `'W'` (Weekly).
  - Gom nhóm (groupby) theo `item_code` và khoảng thời gian, tính tổng `quantity`.
- **Action 2:** Đổi tên cột chuẩn hóa sang format Nixtla (`item_code` $\rightarrow$ `unique_id`, `date` $\rightarrow$ `ds`, `quantity` $\rightarrow$ `y`).

### Task 1.2: Điền khuyết Thời gian - Zero-filling (`src/data_prep.py`)
- **Mô tả:** Trong thực tế, có những ngày/tuần không bán được hàng nào thì Database sẽ không ghi nhận. AI cần chuỗi thời gian phải liên tục.
- **Action:** Viết hàm `fill_missing_dates(df, freq='W')`.
  - Lặp qua từng `unique_id`.
  - Xác định khoảng thời gian từ ngày bán đầu tiên (Min Date) đến ngày bán cuối cùng (Max Date) của mã hàng đó.
  - Khởi tạo chuỗi thời gian đầy đủ, Merge với dữ liệu gốc.
  - Dùng `.fillna(0)` cho các ô trống ở cột `y`.

### Task 1.3: Phát hiện và Xử lý Ngoại lai (`src/data_prep.py`)
- **Mô tả:** Tránh việc một đơn hàng đột biến (gấp 100 lần bình thường) làm hỏng đường trend dự báo.
- **Action:** Viết hàm `clip_outliers(df, method='iqr', multiplier=1.5)`.
  - Tính toán cho **từng SKU riêng biệt** (Không tính chung toàn bộ dataset).
  - Sử dụng phương pháp Interquartile Range (IQR): `Upper Bound = Q3 + multiplier * IQR`.
  - Áp dụng kỹ thuật **Clipping (Cắt ngọn)**: Nếu giá trị `y` lớn hơn `Upper Bound`, thì đưa nó về bằng đúng `Upper Bound` thay vì xóa bỏ dòng đó (để không làm đứt chuỗi thời gian).

### Task 1.4: Phát triển Kịch bản Kiểm thử (`tests/test_data_prep.py`)
- **Action:** Dùng `pytest` lập trình các Test cases khắt khe (chi tiết ở mục 4).

### Task 1.5: Khớp nối và Chạy kiểm chứng (`scratch/run_data_prep.py`)
- **Action:** Sinh Mock Data cho 2 mã ván gỗ (1 mã bán đều, 1 mã bán chập chờn).
- **Action:** Gọi toàn bộ Pipeline (Aggregate $\rightarrow$ Zero-fill $\rightarrow$ Outlier Clip). In kết quả ra màn hình Console (so sánh số dòng Trước và Sau khi xử lý).

---

## 4. Kịch bản Kiểm thử (Test Cases)

| Tên Test Case | Đầu vào giả định (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_nixtla_columns_format` | DF gốc có các cột: `item_code`, `posting_date`, `qty` | Phải bị hàm từ chối hoặc chuyển đổi thành công về đúng 3 cột: `unique_id`, `ds`, `y`. Cột `ds` bắt buộc là kiểu `datetime`. |
| `test_fill_missing_dates` | Mã "MDF-01" có giao dịch vào Tuần 1 và Tuần 3. | Pipeline tự động chèn thêm 1 dòng cho Tuần 2 với giá trị `y = 0`. Tổng số dòng của MDF-01 là 3. |
| `test_outlier_clipping` | Mã "MFC-02" thường bán 10-20 tấm/tuần. Bất ngờ Tuần 4 bán 5,000 tấm. | Dòng Tuần 4 không bị xóa. Giá trị `y` của Tuần 4 bị "cắt ngọn" về ngưỡng Upper Bound (VD: 35 tấm). Các tuần khác giữ nguyên. |
| `test_no_negative_demand` | Bị lỗi hệ thống có phiếu xuất âm (-5 tấm). | Pipeline có cơ chế `clip(lower=0)` để đảm bảo nhu cầu `y` không bao giờ là số âm. |

---

## 5. Tiêu chí Hoàn thành (Definition of Done - DoD)
- [ ] Chạy lệnh `pytest tests/test_data_prep.py` thành công (100% PASS).
- [ ] Dữ liệu đầu ra thỏa mãn điều kiện `df.isna().sum().sum() == 0` (Tuyệt đối không có Null).
- [ ] Pipeline đã sẵn sàng để được import vào Pha 2 (Feature Engineering).
