# TÀI LIỆU HƯỚNG DẪN THIẾT KẾ: DASHBOARD 2 - ML INVENTORY DEMAND FORECASTING & REORDER OPTIMIZATION

**Dự án:** Trí tuệ Nhân tạo trong Quản trị Chuỗi Cung Ứng (Gỗ Minh Long)
**Người sử dụng mục tiêu:** Giám đốc Chuỗi cung ứng (Supply Chain Manager), Trưởng phòng Mua hàng (Purchasing Manager), Nhân viên Kế hoạch.
**Tần suất cập nhật:** Hàng ngày (Daily Refresh).

---

## 1. Mục đích của Dashboard (Business Purpose)
Dashboard số 2 là điểm chạm cuối cùng của toàn bộ hệ thống Học máy (Machine Learning). Nó biến các thuật toán phức tạp thành giao diện trực quan nhằm:
- Cho phép bộ phận Mua hàng biết **chính xác cần đặt mua mã vật tư nào, với số lượng bao nhiêu** ngay trong ngày hôm nay.
- Cảnh báo các mã vật tư sắp chạm ngưỡng cạn kiệt (Chạm điểm ROP - Reorder Point).
- Minh bạch hóa dự báo của AI bằng cách vẽ biểu đồ đường xu hướng (Trend) kết hợp dải tin cậy 95% (Confidence Interval), giúp ban Giám đốc đánh giá được rủi ro dự báo.

---

## 2. Nguồn dữ liệu (Data Sources)
Các bảng dữ liệu cần lấy (Import) từ **PostgreSQL (Silver Layer)**:

**Bảng Sự kiện (Fact Tables):**
1. `silver.fact_inventory_forecast`: Chứa lịch sử dự báo của AI cho từng ngày (Bao gồm Cận trên - Cận dưới).
2. `silver.fact_reorder_recommendations`: Bản tin kết luận Mua hàng. Chứa ROP, Safety Stock, EOQ mới nhất.
3. `silver.fact_inventory_balance`: (Bảng kho hiện tại) Dùng để so sánh Số tồn kho thực tế so với ROP.

**Bảng Danh mục (Dimension Tables):**
1. `silver.dim_product`: Danh mục vật tư (Mã SKU, Tên vật tư, Nhóm hàng - Category).
2. `silver.dim_date`: Bảng ngày tháng chuẩn để slice/dice dữ liệu.

---

## 3. Kiến trúc Mô hình Dữ liệu (Data Modeling - Star Schema)
- `dim_product[product_code]` --- (1:N) ---> `fact_inventory_forecast[item_code]`
- `dim_product[product_code]` --- (1:N) ---> `fact_reorder_recommendations[item_code]`
- `dim_date[date]`      --- (1:N) ---> `fact_inventory_forecast[forecast_date]`

---

## 4. Các Chỉ số tính toán cốt lõi (DAX Measures)

Tạo một bảng Ảo `_Measures_InventoryAI` để lưu các DAX sau:

```dax
// 0. Tính số lượng tồn kho hiện tại (Từ bảng fact_inventory_balance của ngày chốt sổ mới nhất)
Current_Stock_Qty = 
CALCULATE(
    SUM('fact_inventory_balance'[ending_quantity]),
    LASTDATE('dim_date'[date])
)

// 1. Số lượng SKU cần phải đặt hàng khẩn cấp (Current Stock <= ROP)
Total_SKU_Urgent_Reorder = 
CALCULATE(
    DISTINCTCOUNT('fact_reorder_recommendations'[item_code]),
    FILTER(
        'fact_reorder_recommendations',
        [Current_Stock_Qty] <= 'fact_reorder_recommendations'[rop]
    )
)

// 2. Đơn giá mua gần nhất (Phản ánh sát nhất với giá thị trường hiện tại)
Latest_Purchase_Price = 
VAR LatestDate = CALCULATE(MAX('fact_inventoryinward'[posting_date]))
RETURN
CALCULATE(
    DIVIDE(SUM('fact_inventoryinward'[inward_value]), SUM('fact_inventoryinward'[inward_quantity])),
    'fact_inventoryinward'[posting_date] = LatestDate
)

// 3. Tổng giá trị Hàng cần mua (Chỉ tính cho các mã chạm ngưỡng ROP)
Total_Reorder_Value = 
CALCULATE(
    SUMX(
        'fact_reorder_recommendations',
        'fact_reorder_recommendations'[eoq] * [Latest_Purchase_Price]
    ),
    FILTER(
        'fact_reorder_recommendations',
        [Current_Stock_Qty] <= 'fact_reorder_recommendations'[rop]
    )
)

// 4. Tồn kho an toàn trung bình
Avg_Safety_Stock = AVERAGE('fact_reorder_recommendations'[safety_stock])
```

---

## 5. Bố cục Màn hình (Layout & Visualizations)

### 5.1. Thanh điều hướng & Các chỉ số thiết yếu (Banner, Slicers & KPI Cards)
*Khu vực này được bố trí nằm ngang ở ngay mép trên cùng của Dashboard, giúp người dùng dễ dàng điều khiển (filter) và nhìn thấy ngay các con số "nhức nhối" nhất.*

- **Bộ lọc (Slicers) - Đặt góc trên cùng bên trái:**
  - `dim_product[product_category]` (Nhóm hàng): Lọc nhanh theo nhóm Ván MDF, Ván dăm, Keo dán, Nẹp chỉ...
  - `dim_product[product_code]` (Mã vật tư): Thanh tìm kiếm (Dropdown Search) để người dùng gõ nhanh tên/mã một mặt hàng cụ thể cần theo dõi.
  - `dim_date[date]` (Kỳ thời gian): Mặc định trỏ về ngày hôm nay (Latest Date), dùng để lùi thời gian xem lại lịch sử tồn kho và dự báo.

- **Thẻ Chỉ số (KPI Cards) - Đặt Nổi bật bên phải:**
  - **KPI 1 - "Cấp Cứu" (Nền Đỏ cảnh báo):** `Total_SKU_Urgent_Reorder`. Thể hiện tổng số lượng mặt hàng đã thủng đáy (Tồn kho <= ROP). Cảnh báo Phòng Mua hàng phải hành động ngay.
  - **KPI 2 - "Ngân Sách" (Nền Xanh tin cậy):** `Total_Reorder_Value`. Hiển thị tổng số tiền (VNĐ) dự kiến phải xin Giám đốc duyệt chi để nhập đủ lượng hàng (EOQ) cho các mã đang cấp cứu ở KPI 1.

### 5.2. Biểu đồ Dự báo Tương lai & Khoảng tin cậy (Line and Clustered Column Chart)
*Chiếm 50% diện tích bên trái màn hình.*
- **Tiêu đề (Visual Title):** "Dự báo Xu hướng Tiêu thụ & Rủi ro Biến động (30 Ngày)"
- **Trục X (X-Axis):** `dim_date[Date]` (Hiển thị 30 ngày qua và 14 ngày tới).
- **Trục Y (Y-Axis):** `demand_mean` (Đường line chính - Số lượng dự báo), lượng bán thực tế (Cột Bar).
- **Error Bars (Thanh sai số):** Trong Power BI, sử dụng tính năng "Error Bars" trên đường Line. 
  - Cận trên (Upper bound): Kéo cột `demand_upper_95` vào.
  - Cận dưới (Lower bound): Kéo cột `demand_lower_95` vào.
  - *Mục đích: Giám đốc sẽ thấy dải màu bao quanh đường dự báo. Nếu dải này hẹp -> AI rất tự tin. Nếu dải này rộng toác -> Độ rủi ro biến động cao, cần Safety Stock lớn.*

### 5.3. Bảng Hành động Mua hàng (Actionable Matrix Table)
*Chiếm 50% diện tích bên phải màn hình.*
Đây là công cụ làm việc hằng ngày của Nhân viên Mua hàng.
- **Rows:** `dim_product[product_category]`, `dim_product[product_code]`
- **Columns:** *(Để trống)*
- **Values:**
  - `[Current_Stock_Qty]` (Tồn kho cuối kỳ)
  - `SUM('fact_reorder_recommendations'[rop])` (Điểm báo động - ROP)
  - `SUM('fact_reorder_recommendations'[safety_stock])` (Tồn an toàn)
  - `SUM('fact_reorder_recommendations'[eoq])` (Số lượng cần nhập - EOQ)
- **Conditional Formatting (Định dạng có điều kiện):**
  - Cột `[Current_Stock_Qty]`: Tô màu Nền (Background) thành **Đỏ** nếu giá trị <= `rop`. Tô màu **Xanh** nếu > `rop`.
  - Giúp nhân viên chỉ cần lướt mắt là biết phải mua mã nào.

### 5.4. Scatter Plot: Phân bổ Điểm đặt hàng (Optional)
- **X-Axis:** `fact_reorder_recommendations[daily_demand_avg]` (Tốc độ tiêu thụ trung bình).
- **Y-Axis:** `fact_reorder_recommendations[safety_stock]` (Mức độ phòng hờ rủi ro).
- **Values / Details:** `dim_product[product_code]` (Kéo thêm `dim_product[product_name]` vào ô Tooltips để hiển thị tên khi trỏ chuột).
- *Phân tích:* Những mã nằm ở góc trên cùng bên phải là những mặt hàng "Cốt lõi" (Bán chạy nhất và Biến động nhất). Cần đặc biệt theo dõi sát sao.

---

## 6. Lưu ý Vận hành (Operations)
- Cần thiết lập **Scheduled Refresh** trên Power BI Service vào lúc 06:00 Sáng hằng ngày, ngay sau khi luồng ETL và pipeline MLForecast chạy xong trong đêm.
- Nhân viên mua hàng không cần phải mở file Excel hay chạy Python, chỉ cần mở Dashboard này vào lúc 08:00 sáng là có ngay danh sách mua hàng tối ưu nhất (EOQ).
