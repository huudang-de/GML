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
- **Thời gian (Tháng):** `Dim_Date[Month Year]`
- **Ngân hàng & TK (Bank/Account):** `dim_bank[Bank_Name]`, `dim_bank_account[Account_No]`

---

## 3. Công thức DAX & Cấu hình Chi tiết (Phần Thẻ KPI - Cards)

> **Cảnh báo Kế toán:** 
> - **Thu tiền** = Phát sinh Nợ = Cột `debit_amount` (Bên Nợ TK 111, 112).
> - **Chi tiền** = Phát sinh Có = Cột `credit_amount` (Bên Có TK 111, 112).

### 1.1 Dòng tiền vào (Total Inflow)
- **DAX:**
```dax
Dòng tiền vào (Tỷ) = SUM('fact_cashflow'[debit_amount]) / 1000000000
```

### 1.2 Dòng tiền ra (Total Outflow)
- **DAX:**
```dax
Dòng tiền ra (Tỷ) = SUM('fact_cashflow'[credit_amount]) / 1000000000
```

### 1.3 Số dư tiền mặt
- **Mô tả:** Chốt sổ dư cuối kỳ của Mã 110 trong B01-DN.
- **DAX:**
```dax
Số dư tiền cuối kỳ (Tỷ) = 
CALCULATE(
    SUM('fact_balancesheet'[ending_balance]),
    'fact_balancesheet'[Indicator_Code] = "110",
    MAX('fact_balancesheet'[Reporting_Date])
) / 1000000000
```

### 1.4 Dòng tiền thuần (Net Cashflow)
- **DAX:**
```dax
Dòng tiền Thuần (Tỷ) = [Dòng tiền vào (Tỷ)] - [Dòng tiền ra (Tỷ)]
```
- *Mẹo Conditional Formatting:* Định dạng màu Chữ cho Card này: Trị giá > 0 (Màu Xanh), Trị giá < 0 (Màu Đỏ).

---

## 4. Công thức DAX & Cấu hình Chi tiết (Phần Biểu đồ - Charts)

### 2.1 Thu / Chi / Dư quỹ theo thời gian
- **Loại:** Stacked Column & Line Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Column Y-axis:** Measure `Dòng tiền vào` và `Dòng tiền ra` (Tạo màu Xanh cho Thu, Đỏ/Cam cho Chi).
- **Line Y-axis:** Measure `Số dư tiền cuối kỳ`.

### 2.2 & 2.3 Thực hiện kế hoạch Thu / Chi
- **Loại:** Stacked Column Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Trục Y:** Kéo `Thu Thực tế` và `Thu Kế hoạch` vào. (Làm tương tự cho Biểu đồ Chi).

### 2.4 Dư quỹ đầu kỳ / Kế hoạch thực hiện (Biểu đồ Waterfall / Clustered)
- **Loại:** Clustered Column Chart (hoặc Waterfall Chart nếu có thể)
- **Trục X:** Các trạng thái (Tồn đầu kỳ -> Thu -> Chi -> Tồn cuối kỳ)
- **Giá trị:** Tạo một measure tổng hợp giả lập bảng để Power BI vẽ dịch chuyển trạng thái.

### 2.5 & 2.6 Tỷ lệ đóng góp hoạt động Thu / Chi
- **Loại:** Pie Chart
- **Trục Legend:** `dim_account[cashflow_category]` (Dùng bảng Map tài khoản để gom nhóm dòng tiền như: Thu bán hàng, Chi NCC, Thu từ đi vay...).
- **Trục Values:** Measure `Dòng tiền vào` (cho 2.5) và `Dòng tiền ra` (cho 2.6).

### 2.7 Tài sản ngắn hạn / Nợ ngắn hạn / Vốn lưu động
- **Loại:** Line and Clustered Column Chart
- **Trục X:** `Dim_Date[Month Year]`
- **Column Y-axis:** TSNH (Mã 100) và Nợ NH (Mã 310) trong `fact_balancesheet`.
- **Line Y-axis:** Vốn lưu động = (Mã 100) - (Mã 310).

---

## 5. Bảng Dữ Liệu Chi Tiết (Tables & Matrix)

### 3.1 Bảng Chu kỳ tiền mặt (Cash Conversion Cycle - CCC)
- **Loại:** Table
- **Công thức Tài chính:** CCC = Số ngày tồn kho (DIO) + Số ngày thu tiền (DSO) - Số ngày trả tiền (DPO).
- **Cấu hình Cột:** Kỳ báo cáo, DIO, DSO, DPO, Chu kỳ tiền mặt (CCC).
- **Lợi ích:** Theo dõi chu kỳ ròng để đánh giá hiệu quả giải phóng dòng tiền mặt của Gỗ Minh Long.
