# Hướng dẫn Phát triển Dashboard 1: Quản trị Hoạt động Tài chính

## 1. Yêu cầu Bố cục (Layout)
* **Canvas Size:** `Width: 1920px` x `Height: 2850px`
* **Vùng 1 (H: 80px):** Logo, Tiêu đề, Bộ lọc (Slicer)
* **Vùng 2 (H: 260px):** 8 thẻ KPI Cards (Xếp thành 2 hàng x 4 cột)
* **Vùng 3 (H: 600px):** Khối Bất đối xứng (Biểu đồ 2.1 bên trái, 2.2 và 2.3 xếp chồng bên phải)
* **Vùng 4 (H: 780px):** Khối 2x2 Cân bằng (Biểu đồ 2.4, 2.5, 2.6, 2.7)
* **Vùng 5 (H: 1050px):** Bảng chi tiết xếp chồng (2.8, 2.9, 2.10)

## 2. Bộ lọc (Slicers)
- **Thời gian (Month/Year):** Kéo từ bảng `Dim_Date`
- **Ngân hàng (Bank):** Kéo từ bảng `dim_bank`

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

**Lưu ý chung:** Khuyến nghị chuẩn hóa hiển thị thành đơn vị **Tỷ VNĐ** cho tất cả các thẻ Card để Sếp dễ đọc.

### 1.1 Dư nợ ngắn hạn
- **DAX:**
```dax
Dư nợ ngắn hạn (Tỷ VNĐ) = 
CALCULATE (
    SUM('fact_loan'[remaining_principal]),
    'fact_loan'[term_type] = "Ngắn hạn"
) / 1000000000
```

### 1.2 Dư nợ dài hạn
- **DAX:**
```dax
Dư nợ dài hạn (Tỷ VNĐ) = 
CALCULATE (
    SUM('fact_loan'[remaining_principal]),
    'fact_loan'[term_type] = "Dài hạn"
) / 1000000000
```

### 1.3 Hạn mức còn lại (Room tín dụng)
- **DAX:**
```dax
Hạn mức còn lại (Tỷ VNĐ) = 
( SUM('fact_creditlimitsummary'[credit_limit]) - SUM('fact_loan'[remaining_principal]) ) / 1000000000
```

### 1.4 Dự báo thời gian sống của Tiền mặt (Cash Runway)
- **Mô tả:** Tổng dư tiền mặt (Mã 110 cuối kỳ) chia cho Tốc độ đốt tiền (Trung bình dòng chi hàng ngày).
- **DAX:**
```dax
Cash Runway (Ngày) = 
VAR TienMat = CALCULATE(SUM('fact_balancesheet'[ending_balance]), 'fact_balancesheet'[Indicator_Code] = "110")
VAR TrungBinhChi = AVERAGEX('fact_cashflow', 'fact_cashflow'[credit_amount])
RETURN DIVIDE(TienMat, TrungBinhChi, 0)
```

### 1.5 & 1.6 Hạn mức được cấp & Hạn mức được phê duyệt
- **DAX:**
```dax
Hạn mức tín dụng (Tỷ VNĐ) = SUM('fact_creditlimitsummary'[credit_limit]) / 1000000000
Hạn mức phê duyệt (Tỷ VNĐ) = SUM('fact_creditlimitsummary'[granted_limit]) / 1000000000
```

### 1.7 Tỷ lệ vay trên TSĐB (LTV)
- **DAX:**
```dax
Tỷ lệ LTV (%) = 
DIVIDE(
    SUM('fact_loan'[remaining_principal]),
    SUM('fact_collateral'[appraised_value]),
    0
)
```
- **Format:** Chọn kiểu % trên thanh Measure Tools.

### 1.8 Tỷ lệ nợ / vốn (D/E)
- **DAX:**
```dax
Tỷ lệ D/E (Lần) = 
VAR TongNo = CALCULATE(SUM('fact_balancesheet'[ending_balance]), 'fact_balancesheet'[Indicator_Code] = "300")
VAR VonCSH = CALCULATE(SUM('fact_balancesheet'[ending_balance]), 'fact_balancesheet'[Indicator_Code] = "400")
RETURN DIVIDE(TongNo, VonCSH, 0)
```

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

> **Cột bổ trợ cần có trong bảng `fact_loan`:**
> Nếu dữ liệu chưa có `term_type`, hãy tạo Calculated Column này trước:
> ```dax
> term_type = IF(DATEDIFF('fact_loan'[Disbursement_Date], 'fact_loan'[Maturity_Date], MONTH) <= 12, "Ngắn hạn", "Dài hạn")
> ```

### 2.1 Nợ ngắn hạn / Dài hạn / Tổng dư nợ
- **Loại:** Line & Stacked Column Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Column Y-axis:** Measure `Tổng Dư Nợ = SUM('fact_loan'[remaining_principal])`
- **Column Legend:** `fact_loan[term_type]` (Chia màu Cột Ngắn/Dài)
- **Line Y-axis:** Measure `Tổng Dư Nợ` (Vẽ đường Line tổng bọc trên đỉnh cột)

### 2.2 Chi phí nợ theo tháng
- **Loại:** Line Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Trục Y:** Kéo 2 Measure sau vào:
```dax
CP Lãi Vay (Thực tế) = CALCULATE(SUM('fact_incomestatement'[Current_Period_Amount]), 'fact_incomestatement'[Indicator_Code] = "B02-DN_24")
CP Lãi Vay (Kế hoạch) = CALCULATE(SUM('fact_businessplan'[Target_Amount]), 'fact_businessplan'[Indicator_Code] = "B02-DN_24")
```

### 2.3 Lãi suất bình quân từng bank
- **Loại:** Bar Chart
- **Trục Y:** `dim_bank[Bank_Name]`
- **Trục X:** Measure `Lãi suất BQ (%) = AVERAGE('fact_loan'[Interest_Rate])`

### 2.4 Dư nợ tại từng ngân hàng
- **Loại:** Column Chart
- **Trục X:** `dim_bank[Bank_Name]`
- **Trục Y:** Measure `Tổng Dư Nợ`

### 2.5 Chi phí lãi vay thực tế & KH
- **Loại:** Clustered Column Chart
- **Trục X:** `Dim_Date[Month]`
- **Trục Y:** Kéo 2 Measure `CP Lãi Vay (Thực tế)` và `CP Lãi Vay (Kế hoạch)` vào để cột đứng song song so sánh.

### 2.6 Phân tích dòng thu theo bank
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `dim_bank[Bank_Name]`
- **Trục X:** Measure `Tổng Dòng Thu = SUM('fact_cashflow'[debit_amount])`

### 2.7 Phân tích dòng chi theo bank
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `dim_bank[Bank_Name]`
- **Trục X:** Measure `Tổng Dòng Chi = SUM('fact_cashflow'[credit_amount])`

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 2.8 Tổng hợp chỉ số (Vòng quay)
- **Loại:** Table
- **Cột:** Kỳ báo cáo, Giá vốn hàng bán (Mã 11 trong B02), Dư nợ vay BQ, Vòng quay nợ vay, Số ngày luân chuyển, Tỷ lệ D/E.
- **DAX Vòng quay Nợ Vay:** `DIVIDE( Giá Vốn Hàng Bán, Trung bình cộng Dư Nợ đầu và cuối kỳ )`

### 2.9 Chi tiết tài sản đảm bảo
- **Loại:** Table
- **Cột:** Kéo từ bảng `fact_collateral`: STT, Loại TS, Giá trị thẩm định, Hệ số TSĐB, Giá trị cho vay, Số tiền được vay.

### 2.10 Bảng chi tiết lịch trả gốc
- **Loại:** Matrix
- **Rows:** `dim_bank[Bank_Name]`
- **Columns:** `fact_loan[Maturity_Date]`
- **Values:** `SUM(fact_loan[Principal_Payment_Amount])`
- **Tính năng mở rộng:** Cho phép Drill-down từ Bank -> Hợp đồng tín dụng.
