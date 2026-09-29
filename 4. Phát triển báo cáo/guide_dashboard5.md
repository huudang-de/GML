# Hướng dẫn Phát triển Dashboard 5: Quản trị Dòng tiền (Cashflow)

## 1. Yêu cầu Bố cục (Layout)
* **Canvas Size:** `Width: 1920px` x `Height: 2500px`
* **Vùng 1 (H: 80px):** Logo, Tiêu đề, Slicers (Thời gian, Ngân hàng, TK Ngân hàng).
* **Vùng 2 (H: 120px):** 4 thẻ KPI Cards.
* **Vùng 3 (H: 500px):** Biểu đồ Main (2.1) siêu bự chiếm 100% bề ngang để thấy rõ biến động dòng tiền.
* **Vùng 4 (H: 450px):** 2 Biểu đồ so sánh TT vs KH (2.2 & 2.3) ghép đôi.
* **Vùng 5 (H: 450px):** Khối Dịch chuyển dòng tiền & TS/Nợ (2.4 & 2.7) ghép đôi.
* **Vùng 6 (H: 450px):** Khối Cơ cấu Dòng tiền (2 Pie Charts 2.5 & 2.6) + Bảng (3.1).

## 2. Bộ lọc (Slicers)
- **Thời gian (Tháng):** `silver dim_date[Month Year]`
- **Ngân hàng & TK (Bank/Account):** `silver dim_bank[Bank_Name]`, `silver dim_bank_account[Account_No]`

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

> **Cảnh báo Kế toán:** 
> - **Thu tiền** = Phát sinh Nợ = Cột `debit_amount` (Bên Nợ TK 111, 112).
> - **Chi tiền** = Phát sinh Có = Cột `credit_amount` (Bên Có TK 111, 112).

### 1.1 Dòng tiền vào (Total Inflow)
- **DAX:**
```dax
Dòng tiền vào (Tỷ) = 
CALCULATE(
    SUM('silver fact_cashflow'[debit_amount]),
    LEFT('silver fact_cashflow'[account_no], 3) IN {"111", "112"},
    LEFT('silver fact_cashflow'[voucher_no], 4) <> "CTNB"
) / 1000000000
```

### 1.2 Dòng tiền ra (Total Outflow)
- **DAX:**
```dax
Dòng tiền ra (Tỷ) = 
CALCULATE(
    SUM('silver fact_cashflow'[credit_amount]),
    LEFT('silver fact_cashflow'[account_no], 3) IN {"111", "112"},
    LEFT('silver fact_cashflow'[voucher_no], 4) <> "CTNB"
) / 1000000000
```

### 1.3 Số dư tiền mặt
- **Mô tả:** Chốt sổ dư cuối kỳ của Mã 110 trong B01-DN.
- **DAX:**
```dax
Số dư tiền cuối kỳ (Tỷ) = 
CALCULATE(
    SUM('silver fact_balancesheet'[ending_balance]),
    'silver fact_balancesheet'[Indicator_Code] = "B01-DN_110",
    'silver fact_balancesheet'[Reporting_Date] = MAX('silver fact_balancesheet'[Reporting_Date])
) / 1000000000
```

### 1.4 Dự báo thời gian sống của tiền mặt
- **Mô tả:** Nếu công ty không thu được thêm đồng nào, với số tiền mặt hiện có và tốc độ chi tiêu hiện tại, công ty sẽ "sống" được bao nhiêu ngày.
- **DAX:**
```dax
Thời gian sống của tiền (Runway) = 
VAR MaxDate = MAX('silver fact_balancesheet'[reporting_date])
VAR TienMat = 
    CALCULATE(
        SUM('silver fact_balancesheet'[ending_balance]), 
        'silver fact_balancesheet'[Indicator_Code] = "B01-DN_110",
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
- *Mẹo:* Nếu con số này nhỏ hơn 30 ngày (tức là không đủ tiền tiêu trong 1 tháng tới), bạn có thể cài Conditional Formatting cho Card chuyển sang màu Đỏ rực để báo động cho Sếp!

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

### 2.1 Thu / Chi / Dư quỹ theo thời gian
- **Loại:** Stacked Column & Line Chart
- **Trục X:** `silver dim_date[Month Year]`
- **Column Y-axis:** Measure `Dòng tiền vào` và `Dòng tiền ra` (Tạo màu Xanh cho Thu, Đỏ/Cam cho Chi).
- **Line Y-axis:** Measure `Số dư tiền cuối kỳ`.

### 2.2 Thực hiện kế hoạch Thu
- **Loại:** Line and Stacked Column Chart (Cột kết hợp Đường)
- **Trục X:** `silver dim_date[Month Year]`
- **Cột/Đường (Y-axis):** Bạn tạo 2 Measure sau để so sánh (Lấy Doanh thu thuần làm mốc kế hoạch thu):
```dax
Thu Thực tế (Tỷ) = [Dòng tiền vào (Tỷ)]

Thu Kế hoạch (Tỷ) = 
CALCULATE(
    SUM('silver fact_businessplan'[target_amount]),
    'silver fact_businessplan'[Indicator_Code] = "B02-DN_10"
) / 1000000000
```
- *Mẹo UX:* Kéo `Thu Thực tế` làm Cột (Màu Xanh), kéo `Thu Kế hoạch` làm Đường (Line) để thấy rõ thực tế có vượt chỉ tiêu hay không.

### 2.3 Thực hiện kế hoạch Chi
- **Loại:** Line and Stacked Column Chart (Cột kết hợp Đường)
- **Trục X:** `silver dim_date[Month Year]`
- **Cột/Đường (Y-axis):** Tạo 2 Measure sau (Lấy Tổng chi phí Giá vốn + Bán hàng + QLDN làm mốc kế hoạch chi):
```dax
Chi Thực tế (Tỷ) = [Dòng tiền ra (Tỷ)]

Chi Kế hoạch (Tỷ) = 
CALCULATE(
    SUM('silver fact_businessplan'[target_amount]),
    'silver fact_businessplan'[Indicator_Code] IN {"B02-DN_11", "B02-DN_25", "B02-DN_26"}
) / 1000000000
```
- *Mẹo UX:* Kéo `Chi Thực tế` làm Cột (Màu Cam), kéo `Chi Kế hoạch` làm Đường (Line).

### 2.4 Dư quỹ đầu kỳ / Kế hoạch thực hiện (Phân tách trạng thái)
- **Loại:** Clustered Column Chart (Biểu đồ cột cụm)
- **Mô tả:** Thể hiện sự dịch chuyển trạng thái dòng tiền với 4 cột phân tách: Tồn đầu kỳ, Tổng Thu, Tổng Chi, Tồn cuối kỳ.
- **Trục X (X-axis):** Bạn tạo một bảng phụ (Disconnected Table) gồm 4 dòng: `Tồn đầu kỳ`, `Tổng Thu`, `Tổng Chi`, `Tồn cuối kỳ`. Kéo cột đó vào Trục X.
- **Trục Y (Y-axis):** Tạo 1 Measure tổng hợp dùng hàm SWITCH() để xuất ra 4 cột đứng cạnh nhau:
```dax
Trạng thái Dòng tiền (Tỷ) = 
SWITCH(
    SELECTEDVALUE('Bảng_Trạng_Thái'[Trạng thái]),
    "Tồn đầu kỳ", CALCULATE(SUM('silver fact_balancesheet'[beginning_balance]), 'silver fact_balancesheet'[Indicator_Code] = "B01-DN_110") / 1000000000,
    "Tổng Thu", [Dòng tiền vào (Tỷ)],
    "Tổng Chi", [Dòng tiền ra (Tỷ)],
    "Tồn cuối kỳ", CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[Indicator_Code] = "B01-DN_110") / 1000000000
)
```
- *Mẹo UX:* Tô màu khác nhau cho từng cột (Ví dụ: Đầu kỳ Xanh dương, Thu Xanh lá, Chi Đỏ, Cuối kỳ Cam) để Sếp dễ phân biệt 4 trạng thái dòng tiền.

### 2.5 & 2.6 Tỷ lệ đóng góp hoạt động Thu / Chi
- **Loại:** Pie Chart (Biểu đồ tròn)
- **Trục Legend:** Kéo cột `reciprocal_account` (Tài khoản đối ứng) từ bảng `silver fact_cashflow` vào. Cột này giúp phân rã chính xác nguồn tiền (VD: Thu 131, Chi 331).
- **Trục Values:** 
  - Biểu đồ 2.5 (Thu): Kéo Measure `Dòng tiền vào (Tỷ)` (Đã tạo ở mục 1.1)
  - Biểu đồ 2.6 (Chi): Kéo Measure `Dòng tiền ra (Tỷ)` (Đã tạo ở mục 1.2)
- *Mẹo UX:* Cài Data labels hiển thị `% of total` để thấy rõ tiền thu từ bán hàng hay đi vay chiếm tỷ trọng bao nhiêu.

### 2.7 Tài sản ngắn hạn / Nợ ngắn hạn / Vốn lưu động
- **Loại:** Line and Stacked Column Chart (Cột kết hợp Đường)
- **Trục X:** `silver dim_date[Month Year]`
- **Cột/Đường (Y-axis):** Tạo 3 Measure sau:
```dax
Tài sản ngắn hạn (Tỷ) = 
CALCULATE(
    SUM('silver fact_balancesheet'[ending_balance]),
    'silver fact_balancesheet'[Indicator_Code] = "B01-DN_100"
) / 1000000000

Nợ ngắn hạn (Tỷ) = 
CALCULATE(
    SUM('silver fact_balancesheet'[ending_balance]),
    'silver fact_balancesheet'[Indicator_Code] = "B01-DN_310"
) / 1000000000

Vốn lưu động ròng (Tỷ) = [Tài sản ngắn hạn (Tỷ)] - [Nợ ngắn hạn (Tỷ)]
```
- *Mẹo UX:* Kéo `Tài sản ngắn hạn` và `Nợ ngắn hạn` làm Cột (bạn có thể đổi sang biểu đồ Clustered Column Chart để 2 cột đứng cạnh nhau), kéo `Vốn lưu động ròng` làm Đường (Line).

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 3.1 Bảng Chu kỳ tiền mặt (Cash Conversion Cycle - CCC)
- **Loại:** Table (Bảng phẳng)
- **Mô tả:** Đánh giá dòng tiền bị "giam" trong bao nhiêu ngày.
- **DAX:** Tạo lần lượt các Measure sau (với giả định tính cho năm = 365 ngày):
```dax
Vòng quay Hàng tồn kho = 
DIVIDE(
    CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[Indicator_Code] = "B02-DN_11"),
    CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[Indicator_Code] = "B01-DN_140"),
    0
)

Số ngày Tồn kho (DIO) = DIVIDE(365, [Vòng quay Hàng tồn kho], 0)

Vòng quay Phải thu = 
DIVIDE(
    CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[Indicator_Code] = "B02-DN_10"),
    CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[Indicator_Code] = "B01-DN_130"),
    0
)

Số ngày Thu tiền (DSO) = DIVIDE(365, [Vòng quay Phải thu], 0)

Vòng quay Phải trả = 
DIVIDE(
    CALCULATE(SUM('silver fact_incomestatement'[Current_Period_Amount]), 'silver fact_incomestatement'[Indicator_Code] = "B02-DN_11"),
    CALCULATE(SUM('silver fact_balancesheet'[ending_balance]), 'silver fact_balancesheet'[Indicator_Code] = "B01-DN_311"),
    0
)

Số ngày Trả tiền (DPO) = DIVIDE(365, [Vòng quay Phải trả], 0)

Chu kỳ tiền mặt (CCC) = [Số ngày Tồn kho (DIO)] + [Số ngày Thu tiền (DSO)] - [Số ngày Trả tiền (DPO)]
```
- **Cấu hình Cột:** Kéo thả lần lượt các trường sau vào Table: `silver dim_date[Month Year]`, `Số ngày Tồn kho (DIO)`, `Số ngày Thu tiền (DSO)`, `Số ngày Trả tiền (DPO)`, `Chu kỳ tiền mặt (CCC)`.
