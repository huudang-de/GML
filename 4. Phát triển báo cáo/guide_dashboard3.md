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
- **DAX:**
```dax
Vòng quay PT hiện tại = 
VAR ThangNay = MAX('silver Dim_Date'[Date])
VAR ThangTruoc = EOMONTH(ThangNay, -1)

VAR PhaiThu_CuoiKy = [Phải thu Cuối Kỳ]
VAR PhaiThu_DauKy = 
    CALCULATE(
        [Phải thu Cuối Kỳ],
        'silver Dim_Date'[Date] <= ThangTruoc
    )

VAR DuNoBQN = 
    IF(
        ISBLANK(PhaiThu_DauKy) || PhaiThu_DauKy = 0,
        PhaiThu_CuoiKy,
        (PhaiThu_CuoiKy + PhaiThu_DauKy) / 2
    )

RETURN
DIVIDE(
    CALCULATE(SUM('silver fact_incomestatement'[current_period_amount]), 'silver fact_incomestatement'[indicator_code] = "B02-DN_10"),
    DuNoBQN,
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
CALCULATE(
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
    ),
    'silver dim_partner'[partner_group] IN {"Khách hàng", "Khách hàng/ nhà cung cấp"}
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
- **Line Y-axis:** Measure `Tổng hóa đơn` (Đường line xu hướng tổng số hóa đơn treo nợ theo yêu cầu BRD).

> [!TIP]
> **BÍ QUYẾT XỬ LÝ FIFO BẰNG DAX (KHÔNG CẦN NHỜ DE):**
> Vì sếp muốn AE DA tự xử lý logic FIFO (cấn trừ lùi) ngay trên Power BI mà không cần DE làm bảng phụ ở Backend, sếp có thể dùng kỹ thuật **Bảng không liên kết (Disconnected Table)** kết hợp hàm `GENERATE` để tạo vòng lặp tính Running Total ảo trong DAX. Dưới đây là công thức chuẩn mực!
> 
> **Bước 1: Tạo bảng nhóm Tuổi Nợ (Enter Data)**
> Tạo một bảng tên `Dim_TuoiNo` gồm 1 cột `Nhom`: "Trong hạn" và "Quá hạn". KHÔNG tạo relationship với bất kỳ bảng nào.
> Kéo cột `Nhom` này vào **Column Legend** của biểu đồ.
> 
> **Bước 2: Viết Measure Phân bổ FIFO cực mạnh này:**
> ```dax
> Phải thu FIFO (Tỷ) = 
> VAR _MaxDate = MAX('silver Dim_Date'[Date])
> VAR _IsTrongHan = SELECTEDVALUE('Dim_TuoiNo'[Nhom]) = "Trong hạn"
> VAR _IsQuaHan = SELECTEDVALUE('Dim_TuoiNo'[Nhom]) = "Quá hạn"
> 
> RETURN
> DIVIDE(
>     SUMX(
>         VALUES('silver dim_partner'[partner_code]),
>         VAR _Customer = 'silver dim_partner'[partner_code]
>         
>         -- 1. Chốt Số dư nợ của khách hàng tại mốc _MaxDate
>         VAR _TotalDebt = 
>             CALCULATE(
>                 MAXX(
>                     TOPN(1, 'silver fact_accountsreceivable', 'silver fact_accountsreceivable'[posting_date], DESC, 'silver fact_accountsreceivable'[id], DESC),
>                     'silver fact_accountsreceivable'[ending_debit_balance]
>                 ),
>                 'silver fact_accountsreceivable'[posting_date] <= _MaxDate,
>                 ALL('silver Dim_Date')
>             )
>         
>         RETURN
>         IF(ISBLANK(_TotalDebt) || _TotalDebt <= 0, BLANK(),
>             
>             -- 2. Lấy danh sách hóa đơn từ mới đến cũ
>             VAR _Invoices = 
>                 CALCULATETABLE(
>                     SELECTCOLUMNS(
>                         'silver fact_accountsreceivable',
>                         "InvNo", 'silver fact_accountsreceivable'[invoice_no],
>                         "InvDate", 'silver fact_accountsreceivable'[invoice_date],
>                         "InvAmt", 'silver fact_accountsreceivable'[debit_amount]
>                     ),
>                     'silver fact_accountsreceivable'[debit_amount] > 0,
>                     'silver fact_accountsreceivable'[posting_date] <= _MaxDate,
>                     ALL('silver Dim_Date')
>                 )
>                 
>             -- 3. Chạy vòng lặp cấn trừ FIFO ảo
>             VAR _UnpaidInvoices = 
>                 GENERATE(
>                     _Invoices,
>                     VAR _CurrentInvDate = [InvDate]
>                     VAR _CurrentInvNo = [InvNo]
>                     VAR _RunningTotal = 
>                         SUMX(
>                             FILTER(_Invoices, [InvDate] > _CurrentInvDate || ([InvDate] = _CurrentInvDate && [InvNo] >= _CurrentInvNo)),
>                             [InvAmt]
>                         )
>                     VAR _UnpaidAmt = MIN([InvAmt], MAX(0, _TotalDebt - (_RunningTotal - [InvAmt])))
>                     RETURN ROW("UnpaidAmt", _UnpaidAmt)
>                 )
>                 
>             -- 4. Phân bổ phần chưa trả vào nhóm Trong hạn / Quá hạn
>             RETURN
>             SUMX(
>                 FILTER(_UnpaidInvoices, [UnpaidAmt] > 0 &&
>                     (
>                         (_IsTrongHan && DATEDIFF([InvDate], _MaxDate, DAY) <= 30) ||
>                         (_IsQuaHan && DATEDIFF([InvDate], _MaxDate, DAY) > 30) ||
>                         (NOT(_IsTrongHan) && NOT(_IsQuaHan))
>                     )
>                 ),
>                 [UnpaidAmt]
>             )
>         )
>     ),
>     1000000000, 0
> )
> ```
> Sếp lấy Measure `Phải thu FIFO (Tỷ)` này thả vào **Column Y-axis** là Biểu đồ Cột Chồng của sếp sẽ chạy bao mượt, chuẩn logic FIFO 100% y như SQL mà không cần phiền tới Data Engineer!

### 2.2 Vòng quay phải thu theo tháng
- **Loại:** Area Chart
- **Trục X:** `silver Dim_Date[Month]`
- **Trục Y:** Measure `Vòng quay PT hiện tại`

### 2.3 Biểu đồ tuổi nợ (Aging Report)
- **Trục Y:** `Nợ FIFO Aging (Tỷ)` (Tạo Measure ở bên dưới)
- **Cách tạo Measure Phân bổ FIFO Tuổi Nợ (BẮT BUỘC):**
Tuyệt đối KHÔNG dùng cột Calculated Column với hàm `TODAY()` để tính tuổi nợ! Vì `TODAY()` luôn lấy ngày hôm nay (hiện tại là tháng 10) để trừ đi ngày xuất hóa đơn (tháng 7), làm cho toàn bộ hóa đơn bị đẩy lùi về dải `61-90` hoặc `90+`. Và nếu sếp chọn xem dữ liệu tháng 1, nó vẫn lấy tháng 10 để trừ!

Để tuổi nợ nhảy chính xác theo bộ lọc Tháng, sếp BẮT BUỘC phải làm theo 2 bước sau:

**Bước 1: Tạo bảng phụ `Dim_AgingBucket` (Bảng rời, không nối cáp)**
1. Chọn **Enter Data** trên thanh công cụ.
2. Tạo 2 cột: `Bucket` và `Sort`. Nhập y hệt thế này:
   - Current | 1
   - 1-30    | 2
   - 31-60   | 3
   - 61-90   | 4
   - 91-120  | 5
   - 121-150 | 6
   - 151-180 | 7
   - 180+    | 8
3. Đặt tên bảng là `Dim_AgingBucket` rồi Load.
4. Chọn cột `Bucket` > **Sort by Column** > `Sort`.
5. Kéo cột `Bucket` này thả vào **Trục X** của biểu đồ.

**Bước 2: Tạo Measure `Nợ FIFO Aging (Tỷ)` cực mạnh sau đây:**
```dax
Nợ FIFO Aging (Tỷ) = 
VAR _SelectedMaxDate = MAX('silver Dim_Date'[Date])
VAR _ActualMaxDate = CALCULATE(MAX('silver fact_accountsreceivable'[posting_date]), REMOVEFILTERS())
VAR _MaxDate = MIN(_SelectedMaxDate, _ActualMaxDate)

-- Lấy dải Tuổi Nợ đang được chọn trên Trục X (của bảng phụ Dim_AgingBucket)
VAR _SelectedBuckets = VALUES('Dim_AgingBucket'[Bucket])

RETURN
DIVIDE(
    SUMX(
        VALUES('silver dim_partner'[partner_code]),
        VAR _Customer = 'silver dim_partner'[partner_code]
        
        -- 1. Chốt Số dư nợ tại mốc MaxDate
        VAR _TotalDebt = 
            CALCULATE(
                MAXX(
                    TOPN(1, 'silver fact_accountsreceivable', 'silver fact_accountsreceivable'[posting_date], DESC, 'silver fact_accountsreceivable'[id], DESC),
                    'silver fact_accountsreceivable'[ending_debit_balance]
                ),
                'silver fact_accountsreceivable'[posting_date] <= _MaxDate,
                ALL('silver Dim_Date')
            )
        
        RETURN
        IF(ISBLANK(_TotalDebt) || _TotalDebt <= 0, BLANK(),
            
            -- 2. Lấy danh sách hóa đơn
            VAR _Invoices = 
                CALCULATETABLE(
                    SELECTCOLUMNS(
                        'silver fact_accountsreceivable',
                        "InvNo", 'silver fact_accountsreceivable'[invoice_no],
                        "InvDate", 'silver fact_accountsreceivable'[invoice_date],
                        "InvAmt", 'silver fact_accountsreceivable'[debit_amount]
                    ),
                    'silver fact_accountsreceivable'[debit_amount] > 0,
                    'silver fact_accountsreceivable'[posting_date] <= _MaxDate,
                    ALL('silver Dim_Date')
                )
                
            -- 3. Chạy vòng lặp FIFO & Tính Tuổi nợ ĐỘNG theo _MaxDate
            VAR _UnpaidInvoices = 
                GENERATE(
                    _Invoices,
                    VAR _CurrentInvDate = [InvDate]
                    VAR _CurrentInvNo = [InvNo]
                    VAR _RunningTotal = 
                        SUMX(
                            FILTER(_Invoices, [InvDate] > _CurrentInvDate || ([InvDate] = _CurrentInvDate && [InvNo] >= _CurrentInvNo)),
                            [InvAmt]
                        )
                    VAR _UnpaidAmt = MIN([InvAmt], MAX(0, _TotalDebt - (_RunningTotal - [InvAmt])))
                    
                    -- Tính tuổi nợ động (KHÔNG DÙNG TODAY)
                    VAR _DaysSinceInvoice = DATEDIFF(_CurrentInvDate, _MaxDate, DAY)
                    VAR _DynamicBucket = 
                        SWITCH(TRUE(),
                            _DaysSinceInvoice <= 0, "Current",
                            _DaysSinceInvoice <= 30, "1-30",
                            _DaysSinceInvoice <= 60, "31-60",
                            _DaysSinceInvoice <= 90, "61-90",
                            _DaysSinceInvoice <= 120, "91-120",
                            _DaysSinceInvoice <= 150, "121-150",
                            _DaysSinceInvoice <= 180, "151-180",
                            "180+"
                        )
                    RETURN ROW("UnpaidAmt", _UnpaidAmt, "Bucket", _DynamicBucket)
                )
                
            -- 4. Lọc lại chỉ lấy tiền của hóa đơn nằm trong dải Tuổi Nợ được chọn
            RETURN
            SUMX(
                FILTER(_UnpaidInvoices, [UnpaidAmt] > 0 && [Bucket] IN _SelectedBuckets),
                [UnpaidAmt]
            )
        )
    ),
    1000000000, 0
)
```
- *Mẹo UX:* Sếp nhớ kéo cột `Dim_AgingBucket[Bucket]` vào cột Filters của biểu đồ, bỏ tích ô "Current" đi để biểu đồ chỉ hiện nợ quá hạn. Tô màu Đỏ thẫm cho nhóm `180+` để thu hút sự chú ý.

### 2.4 Top 10 khách hàng (Tổng số dư)
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `silver dim_partner[Partner_Name]`
- **Trục X:** `Phải thu (Tỷ)`
- **Top N Filter:** Lấy Top 10 theo giá trị Phải thu.

### 2.5 Top 10 khách hàng (Nợ quá hạn)
- **Loại:** Horizontal Bar Chart
- **Trục Y:** `silver dim_partner[Partner_Name]`
- **Trục X:** Kéo Measure `Nợ FIFO Aging (Tỷ)` vào.
- **Lọc phụ (Rất quan trọng):** Mở cột **Filters** (Bộ lọc). Kéo cột `Dim_AgingBucket[Bucket]` thả vào ô *Filters on this visual*. Bỏ tích ô "Current" (Chỉ giữ lại các nhóm quá hạn). Biểu đồ sẽ tự động rút gọn thành nợ quá hạn.

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
Để cột `% Quá hạn` chỉ xuất hiện đúng 1 lần ở cuối bảng, chúng ta BẮT BUỘC phải dùng biểu đồ **Table** (Bảng phẳng), không được dùng Matrix.

**Tạo các Measure rời cho từng độ tuổi nợ (Sử dụng bảng Dim_AgingBucket)**
Bạn click **New Measure** để tạo lần lượt các cột nợ:
```dax
Nợ Current = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "Current")
Nợ 1-30 = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "1-30")
Nợ 31-60 = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "31-60")
Nợ 61-90 = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "61-90")
Nợ 91-120 = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "91-120")
Nợ 121-150 = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "121-150")
Nợ 151-180 = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "151-180")
Nợ 180+ = CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] = "180+")

% Quá hạn = 
DIVIDE(
    CALCULATE([Nợ FIFO Aging (Tỷ)], 'Dim_AgingBucket'[Bucket] <> "Current"),
    [Phải thu (Tỷ)],
    0
)
```

**Kéo thả vào Table**
- **Loại biểu đồ:** Chọn biểu tượng **Table** (Bảng phẳng).
- **Columns (Kéo thả tuần tự các mục sau vào ô Columns):** 
  1. Kéo `Partner_Name` từ bảng `silver dim_partner` vào (Click đúp sửa tên thành **Customer**).
  2. Kéo 8 Measure nợ từ `Nợ Current` đến `Nợ 180+` thả vào.
  3. Kéo Measure `[Phải thu (Tỷ)]` vào (Click đúp sửa tên thành **Số tiền**).
  4. Kéo Measure `[% Quá hạn]` vào cuối cùng.

### 2.7 Bảng chi tiết các hóa đơn đang nợ
- **Loại:** Table (Bảng phẳng)
- **Columns (Kéo thả tuần tự):**
  1. `silver dim_partner[Partner_Name]` (Tên Khách hàng)
  2. `silver fact_accountsreceivable[invoice_no]` (Số hóa đơn)
  3. `silver fact_accountsreceivable[invoice_date]` (Ngày xuất Hóa đơn)
  4. Tạo 1 Measure `Tuổi Nợ Động` để thả vào bảng này (Vì bảng không cho phép dùng Cột Calculated tĩnh):
```dax
Tuổi Nợ Động = 
VAR _SelectedMaxDate = MAX('silver Dim_Date'[Date])
VAR _ActualMaxDate = CALCULATE(MAX('silver fact_accountsreceivable'[posting_date]), REMOVEFILTERS())
VAR _MaxDate = MIN(_SelectedMaxDate, _ActualMaxDate)
VAR _InvDate = MAX('silver fact_accountsreceivable'[invoice_date])
VAR _Days = DATEDIFF(_InvDate, _MaxDate, DAY)
RETURN 
SWITCH(TRUE(),
    ISBLANK(_InvDate), BLANK(),
    _Days <= 0, "Current",
    _Days <= 30, "1-30",
    _Days <= 60, "31-60",
    _Days <= 90, "61-90",
    _Days <= 120, "91-120",
    _Days <= 150, "121-150",
    _Days <= 180, "151-180",
    "180+"
)
```
  5. Kéo Measure `Tuổi Nợ Động` vào.
  6. Thêm 1 cột hiển thị Số nợ còn lại của Hóa đơn (Phải viết measure tính riêng phần chưa thanh toán cho từng bill):
```dax
Hóa đơn (Chưa thanh toán) = 
VAR _SelectedMaxDate = MAX('silver Dim_Date'[Date])
VAR _ActualMaxDate = CALCULATE(MAX('silver fact_accountsreceivable'[posting_date]), REMOVEFILTERS())
VAR _MaxDate = MIN(_SelectedMaxDate, _ActualMaxDate)
VAR _TotalDebt = CALCULATE(MAXX(TOPN(1, 'silver fact_accountsreceivable', 'silver fact_accountsreceivable'[posting_date], DESC, 'silver fact_accountsreceivable'[id], DESC), 'silver fact_accountsreceivable'[ending_debit_balance]), 'silver fact_accountsreceivable'[posting_date] <= _MaxDate, ALL('silver Dim_Date'))
VAR _Invoices = CALCULATETABLE(SELECTCOLUMNS('silver fact_accountsreceivable', "InvNo", 'silver fact_accountsreceivable'[invoice_no], "InvDate", 'silver fact_accountsreceivable'[invoice_date], "InvAmt", 'silver fact_accountsreceivable'[debit_amount]), 'silver fact_accountsreceivable'[debit_amount] > 0, 'silver fact_accountsreceivable'[posting_date] <= _MaxDate, ALL('silver Dim_Date'))
VAR _CurrentInvDate = MAX('silver fact_accountsreceivable'[invoice_date])
VAR _CurrentInvNo = MAX('silver fact_accountsreceivable'[invoice_no])
VAR _InvAmt = CALCULATE(SUM('silver fact_accountsreceivable'[debit_amount]), 'silver fact_accountsreceivable'[invoice_no] = _CurrentInvNo)
VAR _RunningTotal = SUMX(FILTER(_Invoices, [InvDate] > _CurrentInvDate || ([InvDate] = _CurrentInvDate && [InvNo] >= _CurrentInvNo)), [InvAmt])
RETURN IF(ISBLANK(_TotalDebt) || ISBLANK(_CurrentInvNo), BLANK(), MIN(_InvAmt, MAX(0, _TotalDebt - (_RunningTotal - _InvAmt))))
```
  7. Kéo Measure `Hóa đơn (Chưa thanh toán)` vào cột cuối. Lọc bảng này `is greater than 0`.
- *Mẹo UX:* Bấm mũi tên trỏ xuống ở cột `Hóa đơn (Chưa thanh toán)` > Conditional Formatting > Data bars (Thanh dữ liệu). Hóa đơn nào nợ càng nhiều thì thanh màu đỏ càng dài.


---

