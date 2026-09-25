# Hướng dẫn Phát triển Dashboard 4: Quản trị Tiền gửi & Thanh khoản

## 1. Yêu cầu Bố cục (Layout)
* **Canvas Size:** `Width: 1920px` x `Height: 1200px` (Dashboard này khá gọn nhẹ)
* **Vùng 1 (H: 80px):** Logo, Tiêu đề, Slicer (Thời gian)
* **Vùng 2 (H: 120px):** 5 thẻ KPI Cards (Xếp ngang).
* **Vùng 3 (H: 450px):** 2 Biểu đồ Donut Chart (2.1 & 2.2) song song chia đôi màn hình.
* **Vùng 4 (H: 450px):** 1 Bảng chi tiết (3.1) dàn ngang (Full width).

## 2. Bộ lọc (Slicers)
- **Thời gian (Tháng/Năm):** Kéo từ bảng `Dim_Date`. (Đóng vai trò làm mốc chốt số dư tiền gửi).

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

### 1.1 Tiền & Tương đương tiền
- **Mô tả:** Tổng số dư cuối kỳ của Mã 110 trong Bảng CĐKT.
- **DAX:**
```dax
Tiền mặt & Tương đương (Tỷ) = 
CALCULATE(
    SUM('fact_balancesheet'[ending_balance]),
    'fact_balancesheet'[Indicator_Code] = "110",
    MAX('fact_balancesheet'[Reporting_Date])
) / 1000000000
```

### 1.2 Tiền gửi (Tổng trị giá gốc)
- **Mô tả:** Số dư gốc của các khế ước tiền gửi còn hiệu lực.
- **DAX:**
```dax
Tổng gốc Tiền gửi (Tỷ) = 
CALCULATE(
    SUM('fact_termdeposit'[original_amount]),
    ISBLANK('fact_termdeposit'[settlement_date]) || 'fact_termdeposit'[settlement_date] > MAX('Dim_Date'[Date])
) / 1000000000
```
*(Điều kiện trên lọc ra các sổ tiết kiệm chưa tất toán tính đến thời điểm báo cáo).*

### 1.3 & 1.4 Số lượng hợp đồng & Lãi suất BQ
- **DAX:**
```dax
Số sổ tiết kiệm = 
CALCULATE(
    DISTINCTCOUNT('fact_termdeposit'[passbook_no]),
    ISBLANK('fact_termdeposit'[settlement_date]) || 'fact_termdeposit'[settlement_date] > MAX('Dim_Date'[Date])
)

Lãi suất BQ Tiền gửi (%) = 
CALCULATE(
    AVERAGE('fact_termdeposit'[interest_rate]),
    ISBLANK('fact_termdeposit'[settlement_date]) || 'fact_termdeposit'[settlement_date] > MAX('Dim_Date'[Date])
)
```

### 1.5 Thu nhập lãi
- **Mô tả:** Doanh thu HĐ tài chính (Mã 21 trong B02-DN).
- **DAX:**
```dax
Thu nhập lãi (Tỷ) = 
CALCULATE(
    SUM('fact_incomestatement'[Current_Period_Amount]),
    'fact_incomestatement'[Indicator_Code] = "B02-DN_21"
) / 1000000000
```

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

### 2.1 Cơ cấu tiền gửi theo Ngân hàng
- **Loại:** Donut Chart
- **Legend:** `dim_bank[Bank_Name]`
- **Values:** Measure `Tổng gốc Tiền gửi (Tỷ)`
- *Mẹo UX:* Dùng Donut thay vì Pie chart để hổng phần lõi ở giữa, nhét một Card KPI tổng số tiền gửi vào giữa lõi Donut sẽ trông cực kỳ hiện đại.

### 2.2 Cơ cấu tiền gửi theo Kỳ hạn
- **Loại:** Donut Chart
- **Legend:** `fact_termdeposit[term]` (Kỳ hạn: 1 tháng, 3 tháng, 6 tháng, 1 năm...)
- **Values:** Measure `Tổng gốc Tiền gửi (Tỷ)`

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 3.1 Bảng chi tiết tiền gửi (10 cột)
- **Loại:** Table
- **Cột cấu hình:** 
  1. STT
  2. BANK (`dim_bank[Bank_Name]`)
  3. Lãi suất (`fact_termdeposit[interest_rate]`)
  4. Kỳ hạn (`fact_termdeposit[term]`)
  5. Số sổ/Khế ước (`fact_termdeposit[passbook_no]`)
  6. Trị giá gốc (`fact_termdeposit[original_amount]`)
  7. Ngày gửi (`fact_termdeposit[deposit_date]`)
  8. Ngày đáo hạn (`fact_termdeposit[maturity_date]`)
  9. Ngày tất toán (`fact_termdeposit[settlement_date]`)
  10. Giá trị còn lại (`fact_termdeposit[remaining_amount]`)

- **Bảo mật (RLS) ứng dụng cho Bảng này:** Nhân viên kế toán phụ trách ngân hàng nào (qua bảng Mapping) sẽ chỉ nhìn thấy các sổ tiết kiệm của ngân hàng đó trên bảng này.
