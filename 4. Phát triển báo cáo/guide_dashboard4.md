# Hướng dẫn Phát triển Dashboard 4: Quản trị Tiền gửi & Thanh khoản

## 1. Yêu cầu Bố cục (Layout)
* **Canvas Size:** `Width: 1920px` x `Height: 1200px` (Dashboard này khá gọn nhẹ)
* **Vùng 1 (H: 80px):** Logo, Tiêu đề, Slicer (Thời gian)
* **Vùng 2 (H: 120px):** 5 thẻ KPI Cards (Xếp ngang).
* **Vùng 3 (H: 450px):** 2 Biểu đồ Donut Chart (2.1 & 2.2) song song chia đôi màn hình.
* **Vùng 4 (H: 450px):** 1 Bảng chi tiết (3.1) dàn ngang (Full width).

## 2. Bộ lọc (Slicers)
- **Thời gian (Tháng/Năm):** Kéo từ bảng `silver dim_date[Date]`.
- **Ngân hàng (Bank):** Kéo từ bảng `silver dim_bank[Bank_Name]`. (Đóng vai trò làm mốc chốt số dư tiền gửi).

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

### 1.1 Tiền & Tương đương tiền
- **Mô tả:** Tổng số dư cuối kỳ của Mã 110 trong Bảng CĐKT.
- **DAX:**
```dax
Tiền mặt & Tương đương (Tỷ) = 
CALCULATE(
    SUM('silver fact_balancesheet'[ending_balance]),
    'silver fact_balancesheet'[Indicator_Code] = "B01-DN_110",
    'silver fact_balancesheet'[Reporting_Date] = MAX('silver fact_balancesheet'[Reporting_Date])
) / 1000000000
```

**Sub-metrics:**
```dax
-- 1.1.1 %MoM
[Tiền mặt & TĐ Tiền (%MoM)] = 
VAR ThangTruoc = CALCULATE([Tiền mặt & Tương đương (Tỷ)], PREVIOUSMONTH(\'Dim_Date\'[Date]))
RETURN DIVIDE([Tiền mặt & Tương đương (Tỷ)] - ThangTruoc, ThangTruoc, 0)
```

### 1.2 Tiền gửi (Tổng trị giá gốc)
- **Mô tả:** Số dư gốc của các khế ước tiền gửi còn hiệu lực.
- **DAX:**
```dax
Tổng gốc Tiền gửi (Tỷ) = 
CALCULATE(
    SUM('silver fact_termdeposit'[remaining_value])
) / 1000000000
```

### 1.3 & 1.4 Số lượng hợp đồng & Lãi suất BQ
- **DAX:**
```dax
Số sổ tiết kiệm = 
CALCULATE(
    COUNTROWS('silver fact_termdeposit'),
    'silver fact_termdeposit'[remaining_value] > 0
)

Lãi suất BQ Tiền gửi (%) = 
CALCULATE(
    DIVIDE(
        SUMX('silver fact_termdeposit', 'silver fact_termdeposit'[original_amount] * 'silver fact_termdeposit'[interest_rate]),
        SUM('silver fact_termdeposit'[original_amount])
    ),
    'silver fact_termdeposit'[remaining_value] > 0
)
```

### 1.5 Thu nhập lãi
- **Mô tả:** Lấy từ dòng tiền phát sinh Có của TK Tiền gửi (hoặc ghi Nợ TK 111/112 đối ứng 515).
- **DAX:**
```dax
Thu nhập lãi (Tỷ) = 
CALCULATE(
    SUM('silver fact_cashflow'[debit_amount]),
    'silver fact_cashflow'[reciprocal_account] = "515"
) / 1000000000
```

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

### 2.1 Cơ cấu tiền gửi theo Ngân hàng
- **Loại:** Pie Chart (Biểu đồ tròn)
- **Legend:** `silver dim_bank[Bank_Name]`
- **Values:** Measure `Tổng gốc Tiền gửi (Tỷ)`
- *Mẹo UX:* Ở mục Format > Data labels, bạn chọn Label style là `Category, percent of total` để hiển thị Tên Ngân hàng kèm theo % chiếm tỷ trọng luôn trên biểu đồ nhé.

### 2.2 Cơ cấu tiền gửi theo Kỳ hạn
- **Loại:** Stacked Column Chart (Biểu đồ cột dọc)
- **Trục X:** `silver fact_termdeposit[term]` (Kỳ hạn: 1 tháng, 3 tháng, 6 tháng, 1 năm...)
- **Trục Y:** Measure `Tổng gốc Tiền gửi (Tỷ)`
- *Mẹo UX:* Bấm vào dấu 3 chấm (...) góc trên cùng bên phải của biểu đồ, chọn **Sort axis > term** và **Sort ascending** (Tăng dần) để các cột được xếp theo đúng thứ tự kỳ hạn từ nhỏ đến lớn nhé.

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 3.1 Bảng chi tiết tiền gửi (10 cột)
- **Loại:** Table
- **Cột cấu hình:** 
  1. STT
  2. BANK (`silver dim_bank[Bank_Name]`)
  3. Lãi suất (`silver fact_termdeposit[interest_rate]`)
  4. Kỳ hạn (`silver fact_termdeposit[term]`)
  5. Số sổ/Khế ước (`silver fact_termdeposit[passbook_no]`)
  6. Trị giá gốc (`silver fact_termdeposit[original_amount]`)
  7. Ngày gửi (`silver fact_termdeposit[deposit_date]`)
  8. Ngày đáo hạn (`silver fact_termdeposit[maturity_date]`)
  9. Ngày tất toán (`silver fact_termdeposit[settlement_date]`)
  10. Giá trị còn lại (`silver fact_termdeposit[remaining_value]`)

- **Bảo mật (RLS) ứng dụng cho Bảng này:** Nhân viên kế toán phụ trách ngân hàng nào (qua bảng Mapping) sẽ chỉ nhìn thấy các sổ tiết kiệm của ngân hàng đó trên bảng này.


---
