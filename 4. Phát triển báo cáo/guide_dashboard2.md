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
- **Kho:** `dim_warehouse[Warehouse_Name]`
- **Nhóm Sản Phẩm:** `dim_product[Product_Group]`

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

> **CẢNH BÁO QUAN TRỌNG:** Tồn kho là chỉ số **Semi-additive** (Không được cộng dồn qua các tháng). Phải luôn dùng hàm chốt số lượng/giá trị tại ngày cuối cùng của kỳ báo cáo.

### 1.1 Giá trị hàng tồn kho (Chốt cuối kỳ)
- **DAX:**
```dax
Giá trị HTK (Tỷ) = 
CALCULATE(
    SUM('fact_inventory_balance'[ending_value]),
    LASTDATE('Dim_Date'[Date]) -- Hoặc MAX('fact_inventory_balance'[Snapshot_Date]) để bọc lỗi lịch
) / 1000000000
```

### 1.2 Vòng quay Hàng tồn kho
- **DAX:**
```dax
Vòng quay HTK = 
VAR GiaVon = CALCULATE(SUM('fact_incomestatement'[Current_Period_Amount]), 'fact_incomestatement'[Indicator_Code] = "B02-DN_11")
VAR TonKhoBQ = ( [Giá trị HTK Đầu Kỳ] + [Giá trị HTK Cuối Kỳ] ) / 2
RETURN DIVIDE(GiaVon, TonKhoBQ, 0)
```

### 1.3 Tỷ lệ tồn kho / Doanh thu (I/S Ratio)
- **DAX:**
```dax
Tỷ lệ I/S (%) = 
VAR DoanhThu = CALCULATE(SUM('fact_incomestatement'[Current_Period_Amount]), 'fact_incomestatement'[Indicator_Code] = "B02-DN_01")
RETURN DIVIDE([Giá trị HTK (Tỷ)], DoanhThu, 0)
```

### 1.4 & 1.5 Số lượng và Phân loại
- **DAX:**
```dax
Số lượng HTK = CALCULATE(SUM('fact_inventory_balance'[ending_quantity]), LASTDATE('Dim_Date'[Date]))
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

### 2.5 Top 10 dư tồn kho
- **Loại:** Bar Chart (Ngang)
- **Trục Y:** `dim_product[Product_Name]`
- **Trục X:** `Giá trị HTK (Tỷ)`
- **Lọc (Filter Pane):** Kéo `Product_Name` vào Filter, chọn Top N = 10 theo `Giá trị HTK`.

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 2.6 Bảng Red Flag hàng chậm luân chuyển
- **Loại:** Table
- **Mục đích:** Cảnh báo hàng tồn trong kho quá lâu (ví dụ > 90 ngày) không có giao dịch xuất.
- **DAX tính Ngày tồn kho:** Dùng hàm `DATEDIFF` giữa Ngày hiện tại (hoặc cuối kỳ BC) và Ngày nhập kho gần nhất (`MAX(fact_inventoryinward[Date])`).
- **Conditional Formatting:** Format màu nền Cột Số ngày tồn kho: >90 ngày (Đỏ), 60-90 (Vàng).

### 3.1 Bảng tổng hợp hàng xuất kho vs Kế hoạch
- **Loại:** Table / Matrix
- **Columns:** Mã SP, Tên SP, Giá trị xuất Thực tế, Giá trị KH, Chênh lệch (%), Cảnh báo.
- **Biểu tượng cảnh báo:** Sử dụng Conditional Formatting > Icons. Nếu Chênh lệch vượt quá 5% (Thực tế > Kế hoạch 105%), gắn cờ Đỏ (Red Flag).
