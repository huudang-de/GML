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

### 2.2 Cost of Debt (Chi phí nợ theo tháng)
- **Nguồn dữ liệu (BRD Data Dictionary):** 
  - Tử số (Tổng chi phí lãi vay): Lấy từ Báo cáo kết quả kinh doanh MISA (Bảng `fact_incomestatement`, mã chỉ tiêu `B02-DN_23`).
  - Mẫu số (Tổng dư nợ): Lấy từ Sổ chi tiết các tài khoản MISA (Bảng `fact_cashflow`, mã tài khoản `341`).
- **Loại:** Line Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Trục Y:** Kéo Measure `Cost_Of_Debt` vào biểu đồ.
- **Công thức DAX:**
```dax
CP Lãi Vay (Thực tế) = CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[Indicator_Code] = "B02-DN_23")

Cost_Of_Debt = DIVIDE([CP Lãi Vay (Thực tế)], [Tổng Dư Nợ], BLANK())
```

### 2.3 Lãi suất bình quân từng bank
- **Nguồn dữ liệu:** Lấy từ cột `interest_rate` trong bảng `silver fact_creditlimitsummary`.
- **Loại:** Column Chart (hoặc Bar Chart)
- **Trục X:** `dim_bank[Bank_Name]`
- **Trục Y:** Kéo Measure `Lãi suất bình quân (Card)` (hoặc kéo cột `interest_rate` và chọn Average).
- **Công thức DAX tham khảo:**
```dax
Lãi suất bình quân (Card) = AVERAGE('silver fact_creditlimitsummary'[interest_rate])
```

### 2.4 Dư nợ tại từng ngân hàng
- **Loại:** Column Chart
- **Trục X:** `dim_bank[Bank_Name]`
- **Trục Y:** Measure `Tổng Dư Nợ = [Dư nợ ngắn hạn (Tỷ VNĐ)] + [Dư nợ dài hạn (Tỷ VNĐ)]`

### 2.5 Chi phí lãi vay thực tế & KH
- **Loại:** Clustered Column Chart
- **Trục X:** `Dim_Date[Month]`
- **Trục Y:** Kéo 2 Measure `CP Lãi Vay (Thực tế)` và `CP Lãi Vay (Kế hoạch)` vào để cột đứng song song so sánh.
- **Công thức DAX:**
```dax
CP Lãi Vay (Kế hoạch) = CALCULATE(SUM('silver fact_businessplan'[Target_Amount]), 'silver fact_businessplan'[Indicator_Code] = "B02-DN_23")
```

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

---

## 6. Công thức DAX Nhóm Chỉ số Tài chính (Bảng 2.8)

> **LƯU Ý:** Công thức "Vòng quay hàng tồn kho" đã được chuẩn hóa lại. Lấy Giá vốn hàng bán chia cho Giá trị Tồn kho bình quân (Không chia cho số lượng tồn kho vì sai bản chất tài chính).

### Nhóm 1: Measure Lõi (Core Variables)
Tạo các Measure này ẩn đi, chuyên dùng để làm gốc tính toán:
```dax
_TS_NganHan = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_100")
_No_NganHan = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_310")
_TonKho = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_140")
_PhaiThu = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_130")
_VCSH = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_400")
_TongTaiSan = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_440")

_DoanhThuThuan = CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_10")
_GiaVonHangBan = CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_11")
_LoiNhuanGop = CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_20")
_LoiNhuanSauThue = CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_60")
_ChiPhiLaiVay = CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_23")
_ChiPhiThue = CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[indicator_code] IN {"B02-DN_51", "B02-DN_52"})
```

### Nhóm 2: Nhóm Khả năng Thanh toán (Liquidity)
```dax
1. Thanh toán hiện hành (Current Ratio) = DIVIDE([_TS_NganHan], [_No_NganHan], 0)

2. Thanh toán nhanh (Quick Ratio) = DIVIDE([_TS_NganHan] - [_TonKho], [_No_NganHan], 0)
```

### Nhóm 3: Nhóm Vòng quay (Activity / Turnover)
```dax
-- Tính Trung bình (Average) cho các Khoản mục Bảng Cân đối
_TS_NganHan_AVG = DIVIDE([_TS_NganHan] + CALCULATE([_TS_NganHan], PREVIOUSYEAR('Dim_Date'[Date])), 2)
_No_NganHan_AVG = DIVIDE([_No_NganHan] + CALCULATE([_No_NganHan], PREVIOUSYEAR('Dim_Date'[Date])), 2)
_TonKho_AVG = DIVIDE([_TonKho] + CALCULATE([_TonKho], PREVIOUSYEAR('Dim_Date'[Date])), 2)
_PhaiThu_AVG = DIVIDE([_PhaiThu] + CALCULATE([_PhaiThu], PREVIOUSYEAR('Dim_Date'[Date])), 2)
_VCSH_AVG = DIVIDE([_VCSH] + CALCULATE([_VCSH], PREVIOUSYEAR('Dim_Date'[Date])), 2)
_TongTaiSan_AVG = DIVIDE([_TongTaiSan] + CALCULATE([_TongTaiSan], PREVIOUSYEAR('Dim_Date'[Date])), 2)

-- Các chỉ số Vòng quay
3. Vòng quay Vốn lưu động = DIVIDE([_DoanhThuThuan], [_TS_NganHan_AVG] - [_No_NganHan_AVG], 0)
4. Vòng quay Hàng tồn kho = DIVIDE([_GiaVonHangBan], [_TonKho_AVG], 0)
5. Vòng quay Khoản phải thu = DIVIDE([_DoanhThuThuan], [_PhaiThu_AVG], 0)
```

### Nhóm 4: Nhóm Đòn bẩy (Leverage & Coverage)
```dax
6. Nợ phải trả / Tổng tài sản = DIVIDE(CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_300"), [_TongTaiSan], 0)

7. Nợ dài hạn / Vốn CSH = DIVIDE(CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] = "B01-DN_330"), [_VCSH], 0)

-- Tính EBIT và EBITDA
EBIT = [_ChiPhiLaiVay] + [_ChiPhiThue] + [_LoiNhuanSauThue]

EBITDA = 
VAR KhauHao = CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[indicator_code] IN {"B01-DN_223", "B01-DN_228"})
RETURN [EBIT] + ABS(KhauHao)

-- Các chỉ số bảo đảm lãi vay
8. EBIT / Chi phí lãi vay = DIVIDE([EBIT], [_ChiPhiLaiVay], 0)
9. EBITDA / Chi phí lãi vay = DIVIDE([EBITDA], [_ChiPhiLaiVay], 0)
10. Tổng dư nợ / EBITDA = DIVIDE([Tổng Dư Nợ], [EBITDA], 0)
```

### Nhóm 5: Nhóm Sinh lời (Profitability)
```dax
11. Biên Lợi nhuận gộp (%) = DIVIDE([_LoiNhuanGop], [_DoanhThuThuan], 0)
12. Biên Lợi nhuận HĐKD (%) = DIVIDE(CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_30"), [_DoanhThuThuan], 0)
13. Biên EBITDA (%) = DIVIDE([EBITDA], [_DoanhThuThuan], 0)
14. ROE (%) = DIVIDE([_LoiNhuanSauThue], [_VCSH_AVG], 0)
15. ROA (%) = DIVIDE([_LoiNhuanSauThue], [_TongTaiSan_AVG], 0)
```
