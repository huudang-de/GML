# Hướng dẫn Phát triển Dashboard 2: Quản trị Hàng tồn kho

## 1. Yêu cầu Bố cục (Layout)
* **Canvas Size:** `Width: 1920px` x `Height: 2200px` (Do ít bảng hơn DB1)
* **Vùng 1 (H: 80px):** Logo, Tiêu đề, Slicer (Tháng, Kho, Ngành hàng)
* **Vùng 2 (H: 120px):** 6 thẻ KPI Cards xếp thành 1 hàng ngang.
* **Vùng 3 (H: 500px):** Cụm 2 Biểu đồ Line & Cột ghép (2.1 & 2.3) chia đôi màn hình.
* **Vùng 4 (H: 500px):** Cụm 3 biểu đồ phụ (2.2, 2.4, 2.5) chia 3 màn hình.
* **Vùng 5 (H: 900px):** 2 Bảng chi tiết cảnh báo (2.6 & 3.1) xếp trên dưới.

## 2. Bộ lọc (Slicers)
- **Thời gian:** `Dim_Date[Date]`
- **Nhóm Sản Phẩm:** `dim_product[product_category]`

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

> **CẢNH BÁO QUAN TRỌNG:** Tồn kho là chỉ số **Semi-additive** (Không được cộng dồn qua các tháng). Phải luôn dùng hàm chốt số lượng/giá trị tại ngày cuối cùng của kỳ báo cáo.

### 1.1 Giá trị hàng tồn kho (Chốt cuối kỳ)
- **DAX:**
```dax
Giá trị HTK (Tỷ) = 
CALCULATE(
    SUM('fact_inventory_balance'[ending_value]),
    'Dim_Date'[Date] = MAX('fact_inventory_balance'[snapshot_date])
) / 1000000000
```

### 1.2 Vòng quay Hàng tồn kho
- **DAX:**
Bạn tạo lần lượt các Measure sau (tạo từng cái một):

```dax
Giá vốn hàng bán = CALCULATE(SUM('fact_incomestatement'[current_period_amount]), 'fact_incomestatement'[indicator_code] = "B02-DN_11")

HTK Cuối Kỳ = CALCULATE(SUM('fact_inventory_balance'[ending_value]), 'Dim_Date'[Date] = MAX('fact_inventory_balance'[snapshot_date]))

HTK Đầu Kỳ = CALCULATE([HTK Cuối Kỳ], PREVIOUSMONTH('Dim_Date'[Date]))

Tồn kho BQ = ([HTK Đầu Kỳ] + [HTK Cuối Kỳ]) / 2

Vòng quay HTK = DIVIDE([Giá vốn hàng bán], [Tồn kho BQ], 0)
```

### 1.3 Tỷ lệ tồn kho / Doanh thu (I/S Ratio)
- **DAX:**
Tạo Doanh thu riêng rồi mới chia:

```dax
Doanh thu thuần = CALCULATE(SUM('fact_incomestatement'[current_period_amount]), 'fact_incomestatement'[indicator_code] = "B02-DN_01")

Tỷ lệ I/S (%) = DIVIDE([HTK Cuối Kỳ], [Doanh thu thuần], 0)
```

### 1.4 & 1.5 Số lượng và Phân loại
- **DAX:**
```dax
Số lượng HTK = CALCULATE(SUM('fact_inventory_balance'[ending_quantity]), 'Dim_Date'[Date] = MAX('fact_inventory_balance'[snapshot_date]))
Tổng mã SP đang tồn = CALCULATE(DISTINCTCOUNT('fact_inventory_balance'[product_code]), 'fact_inventory_balance'[ending_quantity] > 0)
```

### 1.6 Giá trị hàng nhập khẩu
- **DAX:**
```dax
Giá trị Nhập khẩu (Tỷ) = 
CALCULATE(
    SUM('fact_inventoryinward'[inward_value]),
    'fact_inventoryinward'[currency] <> "VND"
) / 1000000000
```

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

### 2.1 Số lượng và giá trị HTK theo thời gian
- **Loại:** Line & Clustered Column Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Column Y-axis:** Measure `Số lượng HTK` (Trục Cột cho Số lượng)
- **Line Y-axis:** Measure `Giá trị HTK (Tỷ)` (Trục Đường cho Giá trị, độc lập scale với cột)

### 2.2 Vòng quay HTK theo thời gian
- **Loại:** Area Chart
- **Trục X:** `Dim_Date[Month]`
- **Trục Y:** Measure `Vòng quay HTK`
- *Mẹo:* Set màu Area là Xanh nhạt trong suốt để thể hiện vùng bao phủ, so sánh với KPI Benchmark nếu có.

### 2.3 Inventory to Sales theo thời gian
- **Loại:** Line & Clustered Column Chart
- **Trục X:** `Dim_Date[Month]`
- **Column Y-axis:** `Doanh Thu`
- **Line Y-axis:** `Tỷ lệ I/S (%)`

### 2.4 Biểu đồ Nhập - Xuất - Tồn
- **Loại:** Clustered Column Chart
- **Trục X:** `Dim_Date[Month]`
- **Trục Y:** Kéo 3 Measure: `Tổng Nhập`, `Tổng Xuất`, `Tồn Cuối Kỳ` để xếp cạnh nhau so sánh xu hướng luân chuyển.

### 2.5 Top 10 dư tồn kho cuối kỳ theo chỉ số chọn (Giá/Số lượng)
- **Chuẩn bị (Tạo Nút bấm chuyển đổi):** 
  Vào thanh menu `Modeling` > `New Parameter` > `Fields`. Kéo 2 measure là `[Giá trị HTK]` và `[Số lượng HTK]` vào. Đặt tên tham số là "Chỉ số tùy chọn". Power BI sẽ sinh ra 1 Slicer để chọn trên màn hình.
- **Loại biểu đồ:** Clustered Bar Chart (Ngang - để dễ đọc tên sản phẩm dài)
- **Trục Y:** `dim_product[Product_Name]`
- **Trục X:** Kéo trường *Chỉ số tùy chọn* vừa tạo ở bước chuẩn bị vào.
- **Lọc (Filter Pane):** Kéo `Product_Name` vào mục Filters của biểu đồ, chọn chế độ lọc `Top N` = `10`. Tại ô *By value*, kéo tham số *Chỉ số tùy chọn* vào > Bấm **Apply**. (Khi đó, nếu bấm nút Giá hay nút Số lượng trên màn hình, danh sách Top 10 sẽ tự động trượt và sắp xếp lại tương ứng).

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 2.6 Bảng Red Flag hàng chậm luân chuyển (Chi tiết DAX & UI)
- **Loại:** Table (Bảng dữ liệu)
- **Mục đích:** Cảnh báo hàng tồn đọng quá lâu không xuất kho, gây giam vốn.

**Bước 1: Viết 2 công thức DAX tính Số ngày tồn kho**
Tạo lần lượt 2 Measure sau:
```dax
Ngày giao dịch gần nhất = 
CALCULATE(
    MAX('fact_inventoryinward'[Posting_Date]),
    'fact_inventory_balance'[ending_quantity] > 0
)

Số ngày tồn kho = 
VAR NgayBaoCao = MAX('fact_inventory_balance'[snapshot_date]) -- Fix: Lấy ngày chốt tồn kho thực tế thay vì lịch Dim_Date
RETURN
IF(
    ISBLANK([Ngày giao dịch gần nhất]), 
    BLANK(), 
    DATEDIFF([Ngày giao dịch gần nhất], NgayBaoCao, DAY)
)
```

**Bước 2: Cấu hình Bảng (Table)**
- Trong ô **Columns**, kéo lần lượt: `dim_warehouse[Warehouse_Name]`, `dim_product[Product_Name]`, `[Số lượng HTK]`, và `[Số ngày tồn kho]`.

**Bước 3: Tô màu Cảnh báo (Conditional Formatting)**
1. Tại khu vực Visual, bấm vào mũi tên trỏ xuống của trường `[Số ngày tồn kho]` đang nằm trong ô Columns của biểu đồ.
2. Chọn **Conditional formatting** > **Background color**.
3. Trong hộp thoại hiện ra, phần *Format style* chọn **Rules**.
4. Thiết lập 2 quy tắc sau (⚠️ **Quan trọng:** Nhớ đổi cái đuôi `Percent` mặc định thành `Number` ở tất cả các ô nhé):
   - **Rule 1:** Nếu giá trị `>= 60` và `< 90` -> Chọn màu **Vàng (Cảnh báo)**.
   - **Rule 2:** Bấm `+ New rule`. Nếu giá trị `>= 90` và `< 99999` -> Chọn màu **Đỏ (Nguy hiểm)**.
5. Bấm **OK**. Lập tức hàng nào nằm kho trên 90 ngày sẽ đỏ rực lên.

### 3.1 Bảng tổng hợp Giá vốn hàng bán (Xuất kho) vs Kế hoạch
- **Loại:** Table hoặc Clustered Column Chart (Biểu đồ cột)
- **Mục đích:** Do dữ liệu Kế hoạch kinh doanh (`fact_businessplan`) của công ty chỉ giao chỉ tiêu theo **Tổng Giá Vốn Toàn Công Ty từng tháng**, không có chỉ tiêu chi tiết cho từng mã sản phẩm, nên bảng này dùng để xem công ty có bị lố ngân sách xuất kho hàng tháng hay không.

**Bước 1: Viết 3 công thức DAX cơ sở**
*(Lưu ý: Chỉ tiêu Giá vốn hàng bán trong bảng Kế hoạch kinh doanh là mã `B02-DN_11`)*

```dax
Tổng Giá Trị Xuất (Thực tế) = 
SUM('fact_inventoryoutward'[outward_value])

Kế Hoạch Giá Vốn = 
CALCULATE(
    SUM('fact_businessplan'[target_amount]),
    'fact_businessplan'[indicator_code] = "B02-DN_11"
)

Tỷ lệ hoàn thành Xuất kho (%) = 
DIVIDE([Tổng Giá Trị Xuất (Thực tế)], [Kế Hoạch Giá Vốn], 0)
```

**Bước 2: Cấu hình Bảng (Table)**
- **Columns:** Kéo `Dim_Date[Month]` vào (Tuyệt đối không kéo Sản phẩm vào đây vì Kế hoạch không chia theo sản phẩm, kéo vào số sẽ bị lặp lặp sai bét).
- Sau đó kéo lần lượt `[Tổng Giá Trị Xuất (Thực tế)]`, `[Kế Hoạch Giá Vốn]`, và `[Tỷ lệ hoàn thành Xuất kho (%)]` vào.

**Bước 3: Cắm Cờ Cảnh Báo (Conditional Formatting > Icons)**
Đây là cái "bẫy" dễ sai nhất, bạn làm thật chậm theo các thông số sau:
1. Bấm vào mũi tên ở Measure `[Tỷ lệ hoàn thành Xuất kho (%)]` > Chọn **Conditional formatting** > **Icons**.
2. Phần *Format style* chọn **Rules**.
3. **QUAN TRỌNG NHẤT:** Ở TẤT CẢ các ô chứa chữ `Percent` (Phần trăm) ở đuôi, bạn phải bấm mũi tên đổi hết thành chữ `Number` (Số). (Kể cả khi cột của bạn đang hiển thị là %, trong cái bảng Rule này Power BI chỉ hiểu số thập phân).
4. Khai báo 3 Rules y hệt như sau:
   - **Rule 1 (Cờ Vàng - Hụt kế hoạch):** 
     If value `>= 0` (Number) and `< 0.95` (Number) -> Chọn Icon Cờ Vàng.
   - **Rule 2 (Cờ Xanh - Đạt chuẩn ±5%):** Bấm `+ New rule`. 
     If value `>= 0.95` (Number) and `< 1.05` (Number) -> Chọn Icon Cờ Xanh ⛳.
   - **Rule 3 (Cờ Đỏ - Vượt lố >5%):** Bấm `+ New rule`. 
     If value `>= 1.05` (Number) and `< 9999` (Number) -> Chọn Icon Cờ Đỏ 🚩.
5. Bấm **OK**.
