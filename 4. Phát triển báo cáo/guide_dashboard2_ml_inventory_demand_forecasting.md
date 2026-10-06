# TÀI LIỆU HƯỚNG DẪN THIẾT KẾ: DASHBOARD 5 - ML INVENTORY DEMAND FORECASTING & REORDER OPTIMIZATION

**Dự án:** Trí tuệ Nhân tạo trong Quản trị Chuỗi Cung Ứng (Gỗ Minh Long)
**Người sử dụng mục tiêu:** Giám đốc Chuỗi cung ứng (Supply Chain Manager), Trưởng phòng Mua hàng (Purchasing Manager), Nhân viên Kế hoạch.
**Tần suất cập nhật:** Hàng ngày (Daily Refresh).

---

## 1. Mục đích của Dashboard (Business Purpose)
Dashboard số 5 là điểm chạm cuối cùng của toàn bộ hệ thống Học máy (Machine Learning). Nó biến các thuật toán phức tạp thành giao diện trực quan nhằm:
- Cho phép bộ phận Mua hàng biết **chính xác cần đặt mua mã vật tư nào, với số lượng bao nhiêu** ngay trong ngày hôm nay.
- Cảnh báo các mã vật tư sắp chạm ngưỡng cạn kiệt (Chạm điểm ROP - Reorder Point).
- Minh bạch hóa dự báo của AI bằng cách vẽ biểu đồ đường xu hướng (Trend) kết hợp dải tin cậy 95% (Confidence Interval), giúp ban Giám đốc đánh giá được rủi ro dự báo.

---

## 2. Nguồn dữ liệu (Data Sources)
Các bảng dữ liệu cần lấy (Import) từ **PostgreSQL (Silver Layer)**:

**Bảng Sự kiện (Fact Tables):**
1. `silver.fact_inventory_forecast`: Chứa lịch sử dự báo của AI cho từng ngày (Bao gồm Cận trên - Cận dưới).
2. `silver.fact_reorder_recommendations`: Bản tin kết luận Mua hàng. Chứa ROP, Safety Stock, EOQ mới nhất.
3. `silver.fact_inventory`: (Bảng kho hiện tại) Dùng để so sánh Số tồn kho thực tế so với ROP.

**Bảng Danh mục (Dimension Tables):**
1. `silver.dim_item`: Danh mục vật tư (Mã SKU, Tên vật tư, Nhóm hàng - Category).
2. `silver.dim_date`: Bảng ngày tháng chuẩn để slice/dice dữ liệu.

---

## 3. Kiến trúc Mô hình Dữ liệu (Data Modeling - Star Schema)
- `dim_item[item_code]` --- (1:N) ---> `fact_inventory_forecast[item_code]`
- `dim_item[item_code]` --- (1:N) ---> `fact_reorder_recommendations[item_code]`
- `dim_item[item_code]` --- (1:N) ---> `fact_inventory[item_code]`
- `dim_date[date]`      --- (1:N) ---> `fact_inventory_forecast[forecast_date]`

---

## 4. Các Chỉ số tính toán cốt lõi (DAX Measures)

Tạo một bảng Ảo `_Measures_InventoryAI` để lưu các DAX sau:

```dax
// 1. Số lượng SKU cần phải đặt hàng khẩn cấp (Current Stock <= ROP)
Total_SKU_Urgent_Reorder = 
CALCULATE(
    DISTINCTCOUNT('fact_reorder_recommendations'[item_code]),
    FILTER(
        'fact_reorder_recommendations',
        [Current_Stock_Qty] <= 'fact_reorder_recommendations'[reorder_point]
    )
)

// 2. Tổng giá trị Hàng cần mua (Bằng tiền)
Total_Reorder_Value = 
SUMX(
    'fact_reorder_recommendations',
    'fact_reorder_recommendations'[economic_order_quantity] * RELATED('dim_item'[unit_cost])
)

// 3. Tồn kho an toàn trung bình
Avg_Safety_Stock = AVERAGE('fact_reorder_recommendations'[safety_stock])
```

---

## 5. Bố cục Màn hình (Layout & Visualizations)

### 5.1. Banner & KPI Cards (Nằm ngang trên cùng)
- **KPI Card 1 (Màu đỏ cảnh báo):** `Total_SKU_Urgent_Reorder` (Số lượng vật tư cạn kho, cần nhập gấp).
- **KPI Card 2 (Màu xanh):** `Total_Reorder_Value` (Dự trù Ngân sách cần chi để mua hàng hôm nay).
- **Slicers:** Lọc theo `Nhóm hàng (Category)`, lọc theo `Mã SKU`.

### 5.2. Biểu đồ Dự báo Tương lai & Khoảng tin cậy (Line and Clustered Column Chart)
*Chiếm 50% diện tích bên trái màn hình.*
- **Trục X (X-Axis):** `dim_date[Date]` (Hiển thị 30 ngày qua và 14 ngày tới).
- **Trục Y (Y-Axis):** `point_forecast` (Đường line chính), lượng bán thực tế (Cột Bar).
- **Error Bars (Thanh sai số):** Trong Power BI, sử dụng tính năng "Error Bars" trên đường Line. 
  - Cận trên (Upper bound): Kéo cột `upper_bound_95` vào.
  - Cận dưới (Lower bound): Kéo cột `lower_bound_95` vào.
  - *Mục đích: Giám đốc sẽ thấy dải màu bao quanh đường dự báo. Nếu dải này hẹp -> AI rất tự tin. Nếu dải này rộng toác -> Độ rủi ro biến động cao, cần Safety Stock lớn.*

### 5.3. Bảng Hành động Mua hàng (Actionable Matrix Table)
*Chiếm 50% diện tích bên phải màn hình.*
Đây là công cụ làm việc hằng ngày của Nhân viên Mua hàng.
- **Rows:** `dim_item[Category]`, `dim_item[Item_Code]`
- **Columns / Values:**
  - `Current_Stock` (Tồn kho hiện tại)
  - `reorder_point` (Điểm báo động - ROP)
  - `safety_stock` (Tồn an toàn)
  - `economic_order_quantity` (Số lượng cần nhập - EOQ)
- **Conditional Formatting (Định dạng có điều kiện):**
  - Cột `Current_Stock`: Tô màu Nền (Background) thành **Đỏ** nếu giá trị <= `reorder_point`. Tô màu **Xanh** nếu > `reorder_point`.
  - Giúp nhân viên chỉ cần lướt mắt là biết phải mua mã nào.

### 5.4. Scatter Plot: Phân bổ Điểm đặt hàng (Optional)
- **X-Axis:** `avg_daily_demand` (Tốc độ tiêu thụ).
- **Y-Axis:** `safety_stock` (Mức độ phòng hờ rủi ro).
- **Details:** `item_code`.
- *Phân tích:* Những mã nằm ở góc trên cùng bên phải là những mặt hàng "Cốt lõi" (Bán chạy nhất và Biến động nhất). Cần đặc biệt theo dõi sát sao.

---

## 6. Lưu ý Vận hành (Operations)
- Cần thiết lập **Scheduled Refresh** trên Power BI Service vào lúc 06:00 Sáng hằng ngày, ngay sau khi luồng ETL và pipeline MLForecast chạy xong trong đêm.
- Nhân viên mua hàng không cần phải mở file Excel hay chạy Python, chỉ cần mở Dashboard này vào lúc 08:00 sáng là có ngay danh sách mua hàng tối ưu nhất (EOQ).
