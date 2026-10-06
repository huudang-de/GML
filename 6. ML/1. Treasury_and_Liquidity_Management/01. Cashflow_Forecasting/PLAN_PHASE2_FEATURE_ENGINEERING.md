# 📋 KẾ HOẠCH TRIỂN KHAI PHA 2: FEATURE ENGINEERING
## Dự án: 01. Cashflow_Forecasting (Dự báo Dòng tiền Ngắn hạn)
> **Mã kế hoạch:** GML-ML01-P2  
> **Trạng thái:** 🚀 Đang thực thi  
> **Bộ công cụ:** Python 3.11+, `mlforecast`, `numpy`, `pandas`, `SQLAlchemy`, `psycopg2`  
> **Dữ liệu đầu vào:** `data/processed/daily_cashflow.parquet` (Pha 1) + `silver.fact_AR` + `silver.fact_AP` (PostgreSQL)  
> **Mục tiêu đầu ra:** Bảng dữ liệu đặc trưng phục vụ huấn luyện mô hình (`featured_cashflow.parquet` & `.csv`)  

---

## 1. MỤC TIÊU & PHẠM VI KỸ NGHỆ ĐẶC TRƯNG

Mục tiêu của Pha 2 là chuyển đổi chuỗi thời gian thô (Daily Cashflow) thành ma trận đặc trưng đa chiều (Feature Matrix) giúp các mô hình Machine Learning (LightGBM, XGBoost, Random Forest) học được các quy luật tài chính phi tuyến tính, chu kỳ tuần, ngày chi lương, ngày nộp thuế và lịch thu/trả nợ thực tế:

### Nhóm 1: Đặc trưng Độ trễ Chuỗi thời gian (Lag Features)
* **Lags cho Inflow, Outflow, Net Cashflow:**
  - $t-1$: Giá trị ngày hôm trước.
  - $t-7, t-14, t-21, t-28$: Chu kỳ tuần (cùng ngày thứ trong tuần của các tuần trước).
  - $t-30$: Chu kỳ tháng (cùng ngày tháng trước).

### Nhóm 2: Thống kê Trượt trên Cửa sổ Thời gian (Rolling Window Statistics)
* **Cửa sổ 7 ngày (Weekly Momentum & Volatility):**
  - `rolling_mean_7d`, `rolling_std_7d`, `rolling_min_7d`, `rolling_max_7d`.
* **Cửa sổ 14 ngày & 30 ngày (Medium-term Trend):**
  - `rolling_mean_14d`, `rolling_std_14d`.
  - `rolling_mean_30d`, `rolling_std_30d`.

### Nhóm 3: Yếu tố Lịch biểu & Quy luật Vận hành Doanh nghiệp (Calendar & Business Cycle)
* **Thời gian cơ bản:** `day_of_week`, `day_of_month`, `day_of_year`, `week_of_year`, `month`, `quarter`.
* **Cờ đánh dấu điểm mốc:** `is_weekend`, `is_month_start`, `is_month_end`, `is_quarter_end`.
* **Đặc thù kế toán Gỗ Minh Long:**
  - `is_salary_period`: Ngày 10 - 15 hàng tháng (Kỳ chi lương nhân viên nhà máy và văn phòng $\rightarrow$ Outflow tăng vọt).
  - `is_tax_period`: Ngày 20 - 25 hàng tháng (Kỳ nộp thuế GTGT/TNDN $\rightarrow$ Outflow đột biến).
  - `is_tet_holiday`: Kỳ nghỉ Tết Nguyên Đán 2026 (14/02/2026 - 22/02/2026 $\rightarrow$ Dòng tiền ngưng trệ).

### Nhóm 4: Biến ngoại sinh Tài chính (Financial Exogenous Variables từ AR/AP)
* **Lịch công nợ khách hàng (Accounts Receivable - TK 131):**
  - `ar_expected_due_today`: Tổng số tiền hóa đơn dự kiến thu đúng ngày $t$.
  - `ar_expected_due_next_7d`: Tổng tiền nợ khách hàng đến hạn trong 7 ngày tới.
* **Lịch trả nợ nhà cung cấp (Accounts Payable - TK 331):**
  - `ap_expected_due_today`: Tổng số tiền hàng phải trả NCC đến hạn đúng ngày $t$.
  - `ap_expected_due_next_7d`: Tổng nghĩa vụ thanh toán trong 7 ngày tới.

---

## 2. BỘ TEST CASES KIỂM ĐỊNH (TEST SUITE SPECIFICATION)

| Mã Test Case | Tên Test Case | Điều kiện Đạt (Pass Criteria) | Mức độ |
|:---|:---|:---|:---:|
| **TC-FE-01** | Kiểm tra Input Pha 1 | Đọc thành công `daily_cashflow.parquet` đủ 212 ngày liên tục từ `01/01/2026` đến `31/07/2026`. | Bắt buộc |
| **TC-FE-02** | Tích hợp Biến Ngoại sinh AR/AP | Trích xuất từ PostgreSQL `fact_AR` và `fact_AP`, ánh xạ chính xác vào trục 212 ngày không mất mát. | Bắt buộc |
| **TC-FE-03** | Tính chuẩn xác của Lag (No Data Leakage) | Giá trị `lag_7` tại ngày $t$ khớp chính xác với giá trị thực tế ngày $t-7$ trên 100% mẫu kiểm tra. | Bắt buộc |
| **TC-FE-04** | Tính chuẩn xác của Rolling Windows | `rolling_mean_7d` khớp trung bình trượt 7 ngày lịch sử trước đó với sai số $< 10^{-4}$. | Bắt buộc |
| **TC-FE-05** | Tính chuẩn xác của Cờ Lịch (Calendar Flags) | Cờ lương (10-15), cờ thuế (20-25), cuối tuần (5, 6), Tết (14-22/02) gán nhãn đúng 100% ngày. | Bắt buộc |
| **TC-FE-06** | Quy mô & Độ phong phú Đặc trưng | Bảng dữ liệu cuối cùng có ít nhất $\ge 30$ cột đặc trưng (features) chất lượng cao. | Bắt buộc |
| **TC-FE-07** | Xuất tệp Parquet & CSV an toàn | Lưu trữ thành công `featured_cashflow.parquet` và `featured_cashflow.csv`, đọc lại kiểm tra số dòng khớp 212 dòng. | Bắt buộc |

---

## 3. PHÂN CHIA CÁC TASK THỰC HIỆN

- [x] **Task 1:** Soạn thảo Kế hoạch chi tiết & Tiêu chuẩn kiểm thử (`PLAN_PHASE2_FEATURE_ENGINEERING.md`).
- [ ] **Task 2:** Kiểm tra cài đặt và môi trường thư viện (`mlforecast`, `numpy`, `pandas`).
- [ ] **Task 3:** Xây dựng module kỹ nghệ đặc trưng `src/feature_engineering.py` (Class `CashflowFeatureEngineer`).
- [ ] **Task 4:** Xây dựng test suite tự động `tests/test_feature_engineering.py` bao phủ TC-FE-01 đến TC-FE-07.
- [ ] **Task 5:** Chạy tiến trình sinh đặc trưng qua terminal, hiển thị log chi tiết từng bước.
- [ ] **Task 6:** Chạy test suite nghiệm thu toàn diện, kiểm tra 100% Pass và xuất báo cáo.
