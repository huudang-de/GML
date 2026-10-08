# Hướng dẫn Phát triển Dashboard 3: Quản trị Phải Thu - Phải Trả

## 1. Yêu cầu Bố cục (Layout)
* **Canvas Size:** `Width: 1920px` x `Height: 2500px`
* **Vùng 1 (H: 80px):** Logo, Tiêu đề, Slicer (Thời gian).
* **Vùng 2 (H: 240px):** 6 thẻ KPI Cards (Xếp thành 2 hàng: 3 thẻ trên, 3 thẻ dưới).
* **Vùng 3 (H: 400px):** Biểu đồ 2.1 & 2.2 (Xếp cạnh nhau).
* **Vùng 4 (H: 400px):** Biểu đồ 2.3 & 2.4 (Xếp cạnh nhau).
* **Vùng 5 (H: 400px):** Biểu đồ 2.5 & Bảng 2.6 (Xếp cạnh nhau).
* **Vùng 6 (H: 600px):** Cuối cùng là Bảng 2.7 (Phủ ngang toàn bộ phần đuôi báo cáo).

## 2. Bộ lọc (Slicers)
- **Thời gian:** `silver Dim_Date[Date]`

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

### 1.1 & 1.4 Giá trị Phải Thu & Phải Trả (Cuối kỳ)
- **Mô tả:** Số dư công nợ chốt tại ngày cuối kỳ báo cáo.
- **DAX:** Hãy tạo **Measure Gốc (Đơn vị VNĐ)** trước để dùng tính toán:

```dax
Phải thu Cuối Kỳ = 
VAR _MaxDate = MAX('silver Dim_Date'[Date])
RETURN
SUMX(
    FILTER('silver dim_partner', 'silver dim_partner'[partner_group] IN {"Khách hàng", "Khách hàng/ nhà cung cấp"}),
    CALCULATE(
        MAXX(
            TOPN(1, 'silver fact_accountsreceivable', 'silver fact_accountsreceivable'[posting_date], DESC, 'silver fact_accountsreceivable'[id], DESC),
            'silver fact_accountsreceivable'[ending_debit_balance]
        ),
        'silver fact_accountsreceivable'[posting_date] <= _MaxDate,
        ALL('silver Dim_Date')
    )
)

Phải trả Cuối Kỳ = 
VAR _MaxDate = MAX('silver Dim_Date'[Date])
RETURN
SUMX(
    FILTER('silver dim_partner', 'silver dim_partner'[partner_group] IN {"Nhà cung cấp", "Khách hàng/ nhà cung cấp"}),
    CALCULATE(
        MAXX(
            TOPN(1, 'silver fact_accountspayable', 'silver fact_accountspayable'[posting_date], DESC, 'silver fact_accountspayable'[id], DESC),
            'silver fact_accountspayable'[ending_credit_balance]
        ),
        'silver fact_accountspayable'[posting_date] <= _MaxDate,
        ALL('silver Dim_Date')
    )
)
```

Sau đó tạo **Measure Hiển thị (Tỷ VND)** để hiển thị lên Card:
```dax
Phải thu (Tỷ) = DIVIDE([Phải thu Cuối Kỳ], 1000000000, 0)
Phải trả (Tỷ) = DIVIDE([Phải trả Cuối Kỳ], 1000000000, 0)
```

### 1.2 Vòng quay phải thu hiện tại
- **Mô tả:** Doanh thu / Trung bình dư nợ Phải thu.
- **DAX:** (Đảm bảo không dùng VAR)
```dax
Vòng quay PT hiện tại = 
DIVIDE(
    CALCULATE(SUM('silver fact_incomestatement'[current_period_amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_10"),
    [Phải thu Cuối Kỳ],
    0
)
```

### 1.5 Vòng quay phải thu theo năm
- **DAX:**
```dax
Phải thu Năm Ngoái = 
CALCULATE(
    [Phải thu Cuối Kỳ],
    SAMEPERIODLASTYEAR('silver dim_date'[Date])
)

Vòng quay PT theo năm = 
VAR DuNoBQN = 
    IF(
        ISBLANK([Phải thu Năm Ngoái]) || [Phải thu Năm Ngoái] = 0,
        [Phải thu Cuối Kỳ],
        ([Phải thu Cuối Kỳ] + [Phải thu Năm Ngoái]) / 2
    )
RETURN
DIVIDE(
    CALCULATE(SUM('silver fact_incomestatement'[current_period_amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_10"),
    DuNoBQN,
    0
)
```

### 1.3 & 1.6 Số lượng Khách hàng & Hóa đơn nợ
- **DAX:**
```dax
Số lượng KH nợ = 
VAR _MaxDate = MAX('silver Dim_Date'[Date])
RETURN
COUNTROWS(
    FILTER(
        ADDCOLUMNS(
            FILTER('silver dim_partner', 'silver dim_partner'[partner_group] IN {"Khách hàng", "Khách hàng/ nhà cung cấp"}),
            "DuNo", CALCULATE(
                MAXX(
                    TOPN(1, 'silver fact_accountsreceivable', 'silver fact_accountsreceivable'[posting_date], DESC, 'silver fact_accountsreceivable'[id], DESC),
                    'silver fact_accountsreceivable'[ending_debit_balance]
                ),
                'silver fact_accountsreceivable'[posting_date] <= _MaxDate,
                ALL('silver Dim_Date')
            )
        ),
        [DuNo] > 0
    )
)

Tổng hóa đơn = 
COUNTROWS(
    FILTER(
        SUMMARIZE(
            'silver fact_accountsreceivable',
            'silver fact_accountsreceivable'[invoice_no],
            "DaThu", SUM('silver fact_accountsreceivable'[credit_amount]),
            "PhaiThu", SUM('silver fact_accountsreceivable'[debit_amount])
        ),
        [PhaiThu] - [DaThu] > 0 && NOT(ISBLANK('silver fact_accountsreceivable'[invoice_no]))
    )
)
```

---

**Sub-metrics:**
```dax
-- 1.6.1 YTD (Latest Snapshot)
[Tổng khách hàng nợ (Hiện tại)] = CALCULATE([Tổng khách hàng], REMOVEFILTERS(\'Dim_Date\'))

-- 1.6.2 %MoM
[Tổng khách hàng nợ (%MoM)] = 
VAR ThangTruoc = CALCULATE([Tổng khách hàng], PREVIOUSMONTH(\'Dim_Date\'[Date]))
RETURN DIVIDE([Tổng khách hàng] - ThangTruoc, ThangTruoc, 0)
```


## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

### 2.1 Khoản phải thu theo tháng
- **Loại:** Stacked Column & Line Chart
- **Trục X:** `silver Dim_Date[Month Year]`
- **Column Y-axis:** Measure `Phải thu (Tỷ)`
- **Column Legend:** Cột `Tuổi Nợ Biểu Đồ` (Chia thành 5 nhóm đến 90+)
- **Line Y-axis:** Kéo lại Measure `Phải thu (Tỷ)` vào đây một lần nữa (Đường line sẽ tự động cộng tổng thành Tổng dư nợ).

### 2.2 Vòng quay phải thu theo tháng
- **Loại:** Area Chart
- **Trục X:** `silver Dim_Date[Month]`
- **Trục Y:** Measure `Vòng quay PT hiện tại`

### 2.3 Biểu đồ tuổi nợ (Aging Report)
- **Loại:** Stacked Column Chart
- **Trục X:** Kéo cột `Tuổi Nợ Biểu Đồ` vào.
- **Lọc phụ (Rất quan trọng):** Trọng tâm của biểu đồ này là Nợ quá hạn. Bạn kéo `Tuổi Nợ Biểu Đồ` vào cột Filters, **bỏ tích ô "Current"** đi nhé (Chỉ giữ lại 4 nhóm: 1-30, 31-60, 61-90, 90+).
- **Trục Y:** `Phải thu (Tỷ)`
- **Cách tạo Cột Tuổi nợ dành riêng cho Biểu Đồ (Calculated Column):**
Bạn click **New Column** (Cột mới) 2 lần để tạo 2 cột tính toán tách biệt nhé:

**Cột 1 (Dùng để hiển thị phân nhóm):**
```dax
Tuổi Nợ Biểu Đồ = 
SWITCH(TRUE(),
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 0, "Current",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 30, "1-30",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 60, "31-60",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 90, "61-90",
    "90+"
)
```

**Cột 2 (Cột ẩn dùng để sắp xếp cho chuẩn):**
```dax
Tuổi Nợ Biểu Đồ Sort = 
SWITCH(TRUE(),
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 0, 1,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 30, 2,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 60, 3,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 90, 4,
    5
)
```
- *Mẹo UX:* Để biểu đồ không bị xếp lộn xộn, bạn chọn cột `Tuổi Nợ Biểu Đồ`, lên thanh công cụ chọn **Sort by Column** > `Tuổi Nợ Biểu Đồ Sort`.
- *Mẹo UX:* Tô màu Đỏ thẫm cho nhóm `90+` để thu hút sự chú ý.

### 2.4 Top 10 khách hàng (Tổng số dư)
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `silver dim_partner[Partner_Name]`
- **Trục X:** `Phải thu (Tỷ)`
- **Top N Filter:** Lấy Top 10 theo giá trị Phải thu.

### 2.5 Top 10 khách hàng (Nợ quá hạn)
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `silver dim_partner[Partner_Name]`
- **Trục X:** Kéo Measure `Phải thu (Tỷ)` vào.
- **Lọc phụ (Rất quan trọng):** Mở cột **Filters** (Bộ lọc). Kéo cột `Tuổi Nợ Biểu Đồ` thả vào ô *Filters on this visual*. Bỏ tích ô "Current" (Chỉ giữ lại các nhóm quá hạn). Biểu đồ sẽ tự động rút gọn thành nợ quá hạn.

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 2.6 Bảng chi tiết nợ theo Khách hàng (Bảng Tuổi nợ)
**Cấu trúc bảng yêu cầu:**
| STT | Tên trường    | Ý nghĩa                                       |
| --: | ------------- | --------------------------------------------- |
|   1 | **Customer**  | Tên khách hàng                                |
|   2 | **Current**   | Khoản nợ hiện tại/chưa quá hạn                |
|   3 | **1–30**      | Khoản nợ quá hạn từ 1 đến 30 ngày             |
|   4 | **31–60**     | Khoản nợ quá hạn từ 31 đến 60 ngày            |
|   5 | **61–90**     | Khoản nợ quá hạn từ 61 đến 90 ngày            |
|   6 | **91–120**    | Khoản nợ quá hạn từ 91 đến 120 ngày           |
|   7 | **121–150**   | Khoản nợ quá hạn từ 121 đến 150 ngày          |
|   8 | **151–180**   | Khoản nợ quá hạn từ 151 đến 180 ngày          |
|   9 | **180+**      | Khoản nợ quá hạn trên 180 ngày                |
|  10 | **Số tiền**   | Tổng số tiền nợ của khách hàng                |
|  11 | **% quá hạn** | Tỷ lệ số tiền nợ quá hạn trên tổng số tiền nợ |

**Cách thao tác (Sử dụng Table phẳng để không bị lặp % Quá hạn):**
Để cột `% Quá hạn` chỉ xuất hiện đúng 1 lần ở cuối bảng, chúng ta BẮT BUỘC phải dùng biểu đồ **Table** (Bảng phẳng), không được dùng Matrix. Việc dùng Table đòi hỏi bạn phải tạo các Measure rời cho từng khung tuổi nợ.

**Bước 1: Tạo Cột tính toán `Tuổi Nợ Bảng`**
*(Tạo 2 cột này trong bảng `silver fact_accountsreceivable`)*.
Bạn click **New Column** 2 lần để tạo 2 cột rời nhau:

**Cột 1:**
```dax
Tuổi Nợ Bảng = 
SWITCH(TRUE(),
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 0, "Current",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 30, "1-30",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 60, "31-60",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 90, "61-90",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 120, "91-120",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 150, "121-150",
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 180, "151-180",
    "180+"
)
```

**Cột 2 (Dùng để Sort Cột 1):**
```dax
Tuổi Nợ Bảng Sort = 
SWITCH(TRUE(),
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 0, 1,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 30, 2,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 60, 3,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 90, 4,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 120, 5,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 150, 6,
    DATEDIFF('silver fact_accountsreceivable'[invoice_date], TODAY(), DAY) <= 180, 7,
    8
)
```

**Bước 2: Tạo các Measure rời cho từng độ tuổi nợ**
Bạn click **New Measure** để tạo lần lượt các cột nợ:
```dax
Nợ Current = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "Current")
Nợ 1-30 = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "1-30")
Nợ 31-60 = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "31-60")
Nợ 61-90 = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "61-90")
Nợ 91-120 = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "91-120")
Nợ 121-150 = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "121-150")
Nợ 151-180 = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "151-180")
Nợ 180+ = CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] = "180+")

% Quá hạn = 
DIVIDE(
    CALCULATE([Phải thu Cuối Kỳ], 'silver fact_accountsreceivable'[Tuổi Nợ Bảng] <> "Current"),
    [Phải thu Cuối Kỳ],
    0
)
```

**Bước 3: Kéo thả vào Table**
- **Loại biểu đồ:** Chọn biểu tượng **Table** (Bảng phẳng).
- **Columns (Kéo thả tuần tự các mục sau vào ô Columns):** 
  1. Kéo `Partner_Name` từ bảng `silver dim_partner` vào (Click đúp sửa tên thành **Customer**).
  2. Kéo 8 Measure nợ từ `Nợ Current` đến `Nợ 180+` thả vào.
  3. Kéo Measure `[Phải thu Cuối Kỳ]` vào (Click đúp sửa tên thành **Số tiền**).
  4. Kéo Measure `[% Quá hạn]` vào cuối cùng.

### 2.7 Bảng chi tiết các hóa đơn đang nợ
- **Loại:** Table (Bảng phẳng)
- **Columns (Kéo thả tuần tự):**
  1. `silver dim_partner[Partner_Name]` (Tên Khách hàng)
  2. `silver fact_accountsreceivable[invoice_no]` (Số hóa đơn)
  3. `silver fact_accountsreceivable[invoice_date]` (Ngày xuất Hóa đơn)
  4. Cột tính toán `Tuổi Nợ Bảng` (Hiển thị chi tiết đến 180+)
  5. Measure `[Phải thu Cuối Kỳ]` (Số tiền còn nợ)
- **Lọc phụ (Bắt buộc):** Ở cột Filters bên phải, kéo Measure `[Phải thu Cuối Kỳ]` vào mục *Filters on this visual* và cài đặt điều kiện **is greater than 0** (Lớn hơn 0). Điều này giúp bảng ẩn đi những hóa đơn khách đã trả sạch tiền!
- *Mẹo UX:* Bấm mũi tên trỏ xuống ở cột Phải thu Cuối Kỳ > Conditional Formatting > Data bars (Thanh dữ liệu). Hóa đơn nào nợ càng nhiều thì thanh màu đỏ càng dài.


---

