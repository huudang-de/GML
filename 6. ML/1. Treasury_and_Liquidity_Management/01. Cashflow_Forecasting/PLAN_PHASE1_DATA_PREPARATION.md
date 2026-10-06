# 📋 KẾ HOẠCH TRIỂN KHAI PHA 1: DATA PREPARATION (TIỀN XỬ LÝ DỮ LIỆU)
## Dự án: 01. Cashflow_Forecasting (Dự báo Dòng tiền Ngắn hạn)
> **Mã kế hoạch:** GML-ML01-P1  
> **Trạng thái:** 🚀 Đang thực thi  
> **Bộ công cụ:** Python 3.11+, `pandas`, `SQLAlchemy`, `psycopg2`, `pyarrow`  
> **Cơ sở dữ liệu nguồn:** PostgreSQL `silver.fact_cashflow`  
> **Mục tiêu đầu ra:** Bảng chuỗi thời gian dòng tiền theo ngày (`daily_cashflow.parquet` & `.csv`)  

---

## 1. MỤC TIÊU & PHẠM VI KỸ THUẬT

1. **Kết nối & Trích xuất:** Kết nối an toàn vào PostgreSQL schema `silver`, trích xuất sổ cái thu/chi tiền mặt (`TK 111`) và tiền gửi ngân hàng (`TK 112`).
2. **Khử nhiễu nghiệp vụ chuyển tiền nội bộ (`CTNB`):** Loại trừ triệt để các bút toán chuyển vốn giữa các tài khoản nội bộ (để không phồng ảo doanh số dòng tiền).
3. **Chuẩn hóa kiểu dữ liệu & Xử lý giá trị thiếu:**
   - Ngày ghi sổ `posting_date` $\rightarrow$ `pd.Timestamp` (Date format `YYYY-MM-DD`).
   - Các cột số tiền $\rightarrow$ `float64` (Đơn vị VNĐ).
4. **Tạo chuỗi thời gian liên tục (Calendar Continuity):**
   - Tạo trục ngày hoàn chỉnh từ `2026-01-01` đến `2026-07-31` (212 ngày liên tục).
   - Điền số `0.0` cho các ngày nghỉ/Lễ/Tết không phát sinh giao dịch, triệt tiêu hoàn toàn `NaN / NULL`.
5. **Phân rã dòng tiền theo bản chất nghiệp vụ (Detailed Breakdown):**
   - `inflow_total`: Tổng dòng tiền vào (Phát sinh Nợ TK 111, 112).
   - `outflow_total`: Tổng dòng tiền ra (Phát sinh Có TK 111, 112).
   - `net_cashflow`: Dòng tiền thuần $= \text{inflow} - \text{outflow}$.
   - Phân loại chi tiết theo tài khoản đối ứng (`reciprocal_account`):
     * *Thu khách hàng (Operating Inflow):* Đối ứng TK 131, 511.
     * *Chi nhà cung cấp (Operating Outflow):* Đối ứng TK 331, 152, 156.
     * *Chi lương nhân viên:* Đối ứng TK 334.
     * *Chi nộp thuế:* Đối ứng TK 333.
     * *Vay & Trả gốc ngân hàng (Financing):* Đối ứng TK 341.
     * *Chi trả lãi vay:* Đối ứng TK 635.
     * *Thu lãi tiền gửi:* Đối ứng TK 515.
6. **Lưu trữ đầu ra:** Lưu tệp chuẩn hóa vào thư mục `data/processed/` dưới 2 định dạng: Parquet (tối ưu tốc độ huấn luyện) và CSV (dễ mở kiểm tra).

---

## 2. BỘ TEST CASES KIỂM ĐỊNH (TEST SUITE SPECIFICATION)

| Mã Test Case | Tên Test Case | Điều kiện Đạt (Pass Criteria) | Mức độ |
|:---|:---|:---|:---:|
| **TC-01** | Kết nối & Trích xuất Data Warehouse | Kết nối PostgreSQL thành công, trích xuất đầy đủ các dòng phát sinh TK 111, 112. | Bắt buộc |
| **TC-02** | Khử nhiễu CTNB & Khớp số liệu kiểm toán | 100% chứng từ `voucher_no LIKE 'CTNB%'` bị loại trừ. Tổng dòng tiền vào T1-T7 khớp đúng $\approx 2,856.47$ Tỷ, dòng tiền ra khớp đúng $\approx 2,749.32$ Tỷ (độ lệch $< 0.001\%$). | Bắt buộc |
| **TC-03** | Tính liên tục của Chuỗi thời gian (Continuity) | Chuỗi ngày liên tục 100% từ `2026-01-01` đến `2026-07-31` (chính xác 212 ngày), không đứt gãy hoặc nhảy ngày. | Bắt buộc |
| **TC-04** | Kiểm tra Giá trị Thiếu (Null / NaN Check) | Không có bất kỳ giá trị `NaN` hoặc `Null` nào trong toàn bộ bảng kết quả (`df.isna().sum() == 0`). | Bắt buộc |
| **TC-05** | Tính hợp lệ toán học (Mathematical Consistency) | $\text{net\_cashflow} == \text{inflow} - \text{outflow}$ chính xác tuyệt đối trên 100% các dòng (sai số $< 10^{-5}$). | Bắt buộc |
| **TC-06** | Kiểm tra Tính chất Phi âm của Thu/Chi | $\text{inflow} \ge 0$ và $\text{outflow} \ge 0$ trên tất cả các ngày. | Bắt buộc |
| **TC-07** | Xuất tệp & Đọc lại thành công | Tệp `daily_cashflow.parquet` và `daily_cashflow.csv` được tạo trong `data/processed/`, đọc lại kiểm tra số dòng và schema khớp 100%. | Bắt buộc |

---

## 3. PHÂN CHIA NHỎ CÁC TASK THỰC HIỆN

- [x] **Task 1:** Soạn thảo Kế hoạch chi tiết và Tiêu chí kiểm thử (`PLAN_PHASE1_DATA_PREPARATION.md`).
- [ ] **Task 2:** Viết mã nguồn module `src/data_preparation.py` (Class `CashflowDataPreparator` với đầy đủ logging qua Terminal).
- [ ] **Task 3:** Viết test suite tự động `tests/test_data_preparation.py` bao phủ toàn bộ 7 Test Cases (TC-01 đến TC-07).
- [ ] **Task 4:** Chạy tiến trình xử lý dữ liệu qua terminal, hiển thị log từng bước.
- [ ] **Task 5:** Chạy test suite tự động kiểm định lại kết quả, xuất báo cáo nghiệm thu.
