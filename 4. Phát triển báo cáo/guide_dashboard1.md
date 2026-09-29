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
SUMX(
    FILTER(
        VALUES('silver fact_cashflow'[account_no]),
        'silver fact_cashflow'[account_no] IN {"34111", "34113", "34114"}
    ),
    CALCULATE(
        MAXX(
            TOPN(1, 'silver fact_cashflow', 'silver fact_cashflow'[posting_date], DESC, 'silver fact_cashflow'[id], DESC),
            'silver fact_cashflow'[credit_balance]
        )
    )
) / 1000000000
```

### 1.2 Dư nợ dài hạn
- **DAX:**
```dax
Dư nợ dài hạn (Tỷ VNĐ) = 
SUMX(
    FILTER(
        VALUES('silver fact_cashflow'[account_no]),
        'silver fact_cashflow'[account_no] = "34112"
    ),
    CALCULATE(
        MAXX(
            TOPN(1, 'silver fact_cashflow', 'silver fact_cashflow'[posting_date], DESC, 'silver fact_cashflow'[id], DESC),
            'silver fact_cashflow'[credit_balance]
        )
    )
) / 1000000000
```

### 1.3 Hạn mức còn lại (Room tín dụng)
- **DAX:**
```dax
Hạn mức còn lại (Tỷ VNĐ) = 
SUM('silver fact_creditlimitsummary'[remaining_disbursement]) / 1000000000
```

### 1.4 Dự báo thời gian sống của Tiền mặt (Cash Runway)
- **Mô tả:** Tổng dư tiền mặt (Mã 110 cuối kỳ) chia cho Tốc độ đốt tiền (Tổng dòng chi ra trong tháng), quy đổi ra số ngày bằng cách nhân 30.
- **DAX:**
```dax
Cash Runway (Ngày) = 
VAR MaxDate = MAX('silver fact_balancesheet'[reporting_date])
VAR TienMat = 
    CALCULATE(
        SUM('silver fact_balancesheet'[ending_balance]), 
        'silver fact_balancesheet'[indicator_code] = "B01-DN_110",
        'silver fact_balancesheet'[reporting_date] = MaxDate
    )
VAR TongChi = 
    CALCULATE(
        SUM('silver fact_cashflow'[credit_amount]),
        LEFT('silver fact_cashflow'[account_no], 3) IN {"111", "112"},
        LEFT('silver fact_cashflow'[voucher_no], 4) <> "CTNB",
        YEAR('silver fact_cashflow'[posting_date]) = YEAR(MaxDate),
        MONTH('silver fact_cashflow'[posting_date]) = MONTH(MaxDate)
    )
RETURN DIVIDE(TienMat, TongChi, 0) * 30
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
    SUM('silver fact_creditlimitsummary'[granted_limit]),
    SUM('silver fact_collateral'[appraised_value]),
    0
)
```
- **Format:** Chọn kiểu % trên thanh Measure Tools.

### 1.8 Tỷ lệ nợ / vốn (D/E)
- **DAX:**
```dax
Tỷ lệ D/E (Lần) = 
VAR TongNo = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_300")
VAR TongNguonVon = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_440")
RETURN DIVIDE(TongNo, TongNguonVon, 0)
```

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

> **Cột bổ trợ cần có trong bảng `fact_cashflow`:**
> Nhóm các tài khoản vay thành "Ngắn hạn" và "Dài hạn":
> ```dax
> term_type = IF('silver fact_cashflow'[account_no] IN {"34111", "34113", "34114"}, "Ngắn hạn", IF('silver fact_cashflow'[account_no] = "34112", "Dài hạn", BLANK()))
> ```

### 2.1 Nợ ngắn hạn / Dài hạn / Tổng dư nợ
- **Loại:** Line & Stacked Column Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Column Y-axis:** Kéo 2 Measure `Dư nợ ngắn hạn (Tỷ VNĐ)` và `Dư nợ dài hạn (Tỷ VNĐ)`
- **Line Y-axis:** Measure `Tổng Dư Nợ = [Dư nợ ngắn hạn (Tỷ VNĐ)] + [Dư nợ dài hạn (Tỷ VNĐ)]`

### 2.2 Chi phí nợ theo tháng
- **Loại:** Line Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Trục Y:** Kéo 2 Measure sau vào:
```dax
CP Lãi Vay (Thực tế) = CALCULATE(SUM('fact_incomestatement'[Current_Period_Amount]), 'fact_incomestatement'[Indicator_Code] = "B02-DN_24")
CP Lãi Vay (Kế hoạch) = CALCULATE(SUM('fact_businessplan'[Target_Amount]), 'fact_businessplan'[Indicator_Code] = "B02-DN_24")
```

### 2.3 Lãi suất bình quân từng bank
- **[ĐÃ LƯỢC BỎ]** Biểu đồ này tạm thời không sử dụng do bảng `fact_loan` (nhập tay) đã bị loại bỏ khỏi Single Source of Truth vì thiếu chính xác.

### 2.4 Dư nợ tại từng ngân hàng
- **Loại:** Column Chart
- **Trục X:** `dim_bank[Bank_Name]`
- **Trục Y:** Measure `Tổng Dư Nợ = [Dư nợ ngắn hạn (Tỷ VNĐ)] + [Dư nợ dài hạn (Tỷ VNĐ)]`

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
- **[ĐÃ LƯỢC BỎ]** Bảng này tạm thời không sử dụng do bảng `fact_loan` (nhập tay) đã bị loại bỏ khỏi Single Source of Truth vì thiếu chính xác.
