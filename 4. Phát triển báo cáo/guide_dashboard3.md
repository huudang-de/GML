# Hướng dẫn Phát triển Dashboard 3: Quản trị Phải Thu - Phải Trả

## 1. Yêu cầu Bố cục (Layout)
* **Canvas Size:** `Width: 1920px` x `Height: 2500px`
* **Vùng 1 (H: 80px):** Logo, Tiêu đề, Slicer (Thời gian, Khách hàng)
* **Vùng 2 (H: 120px):** 6 thẻ KPI Cards (Xếp ngang).
* **Vùng 3 (H: 500px):** Cụm Biểu đồ Xu hướng Phải thu (2.1 & 2.2) 
* **Vùng 4 (H: 500px):** Cụm Phân tích Tuổi nợ và Khách hàng (2.3, 2.4, 2.5) 
* **Vùng 5 (H: 1200px):** 2 Bảng siêu chi tiết xếp chồng (2.6 Khách hàng & 2.7 Hóa đơn)

## 2. Bộ lọc (Slicers)
- **Thời gian:** `Dim_Date[Date]`
- **Khách hàng (Customer):** `dim_partner[Partner_Name]` (Lọc theo Đối tượng là KH)

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

### 1.1 & 1.4 Giá trị Phải Thu & Phải Trả (Cuối kỳ)
- **Mô tả:** Số dư công nợ chốt tại ngày cuối kỳ báo cáo.
- **DAX:**
```dax
Phải thu (Tỷ) = 
CALCULATE(
    SUM('fact_accountsreceivable'[ending_debit_balance]),
    MAX('fact_accountsreceivable'[Reporting_Date]) 
) / 1000000000

Phải trả (Tỷ) = 
CALCULATE(
    SUM('fact_accountspayable'[ending_credit_balance]),
    MAX('fact_accountspayable'[Reporting_Date]) 
) / 1000000000
```

### 1.2 Vòng quay phải thu hiện tại
- **Mô tả:** Doanh thu / Trung bình dư nợ Phải thu.
- **DAX:**
```dax
Vòng quay PT = 
VAR DoanhThu = CALCULATE(SUM('fact_incomestatement'[Current_Period_Amount]), 'fact_incomestatement'[Indicator_Code] = "B02-DN_01")
VAR DưNoPT_BQ = ([Phải thu Đầu Kỳ] + [Phải thu Cuối Kỳ]) / 2
RETURN DIVIDE(DoanhThu, DưNoPT_BQ, 0)
```

### 1.5 Vòng quay phải thu theo năm
- **DAX:**
```dax
Số ngày thu tiền BQ (DSO) = DIVIDE(365, [Vòng quay PT], 0)
```

### 1.3 & 1.6 Số lượng Khách hàng & Hóa đơn nợ
- **DAX:**
```dax
Số lượng KH nợ = CALCULATE(DISTINCTCOUNT('fact_accountsreceivable'[partner_code]), 'fact_accountsreceivable'[ending_debit_balance] > 0)
Số lượng HĐ nợ = CALCULATE(DISTINCTCOUNT('fact_accountsreceivable'[invoice_no]), 'fact_accountsreceivable'[ending_debit_balance] > 0)
```

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

### 2.1 Khoản phải thu theo tháng
- **Loại:** Stacked Column & Line Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Column Y-axis:** Measure `Phải thu (Tỷ)` (Chia theo nhóm Trong Hạn / Quá Hạn)
- **Line Y-axis:** Measure Tổng dư nợ.

### 2.2 Vòng quay phải thu theo tháng
- **Loại:** Area Chart
- **Trục X:** `Dim_Date[Month]`
- **Trục Y:** Measure `Vòng quay PT`

### 2.3 Biểu đồ tuổi nợ (Aging Report)
- **Loại:** Stacked Column Chart
- **Trục X:** Nhóm tuổi nợ (Dưới 30 ngày, 30-60 ngày, 60-90 ngày, Trên 90 ngày).
- **Trục Y:** `Phải thu (Tỷ)`
- **Cách tạo Bucket Tuổi nợ (Calculated Column):**
```dax
Tuổi Nợ Bucket = 
VAR DaysOverdue = DATEDIFF('fact_accountsreceivable'[invoice_date], TODAY(), DAY)
RETURN 
SWITCH(TRUE(),
    DaysOverdue <= 0, "Trong hạn",
    DaysOverdue <= 30, "Quá hạn 1-30 ngày",
    DaysOverdue <= 60, "Quá hạn 31-60 ngày",
    DaysOverdue <= 90, "Quá hạn 61-90 ngày",
    "Quá hạn >90 ngày (Red Flag)"
)
```
- *Mẹo UX:* Tô màu Đỏ thẫm cho nhóm `>90 ngày` để thu hút sự chú ý.

### 2.4 Top 10 khách hàng (Tổng số dư)
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `dim_partner[Partner_Name]`
- **Trục X:** `Phải thu (Tỷ)`
- **Top N Filter:** Lấy Top 10 theo giá trị Phải thu.

### 2.5 Top 10 khách hàng (Nợ quá hạn)
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `dim_partner[Partner_Name]`
- **Trục X:** `Phải thu quá hạn (Tỷ)`
- **Lọc phụ:** Cần thêm Filter (Tuổi nợ Bucket <> "Trong hạn").

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 2.6 Bảng chi tiết nợ theo Khách hàng
- **Loại:** Matrix
- **Rows:** `dim_partner[Partner_Name]`
- **Columns:** `Tuổi Nợ Bucket`
- **Values:** `SUM(fact_accountsreceivable[ending_debit_balance])`
- *Lợi ích:* Kế toán có thể nhìn lướt ma trận để biết công ty A đang nợ bao nhiêu trong hạn, bao nhiêu cục quá hạn 90 ngày.

### 2.7 Bảng chi tiết các hóa đơn đang nợ
- **Loại:** Table
- **Cột:** Tên KH, Số Hóa đơn, Ngày xuất HĐ, Ngày đến hạn, Số ngày quá hạn, Trị giá HĐ, Số tiền còn nợ.
- *Mẹo:* Bật Conditional Formatting (Data bars) cho cột "Số ngày quá hạn" để nhìn độ dài thanh ngang biết ngay HĐ nào nợ dai dẳng nhất.
