# Hướng dẫn Phát triển Dashboard 5 (Trang 2): Dự báo Dòng tiền Thông minh & Kiểm thử Căng thẳng (ML Cashflow Forecasting & Stress Testing)

> **Dự án:** GML Machine Learning Treasury & Liquidity Management  
> **Module liên quan:** `6. ML / 1. Treasury_and_Liquidity_Management / 01. Cashflow_Forecasting`  
> **Cơ sở dữ liệu nguồn:** PostgreSQL Data Warehouse (`gold.fact_cashflow_forecast`, `gold.fact_cashflow_scenarios`, `gold.view_cashflow_actual_vs_forecast`)  
> **Đối tượng người dùng:** Giám đốc Tài chính (CFO), Trưởng phòng Nguồn vốn (Head of Treasury), Kế toán trưởng  

---

## 1. MỤC TIÊU NGHIỆP VỤ & GIÁ TRỊ MANG LẠI

Khác với Trang 1 (Dòng tiền Lịch sử - Historical Cashflow), Trang 2 cung cấp **năng lực dự báo tương lai 30 ngày (Forward-looking Predictive Intelligence)** được vận hành bởi 2 mô hình Machine Learning LightGBM đã qua tối ưu hóa siêu tham số (Optuna) và kiểm thử thực nghiệm:

1. **Dự báo trước dòng tiền vào (Inflow), dòng tiền ra (Outflow) và dòng tiền ròng (Net Position):** Giúp thủ quỹ không bị động trước các đợt giải ngân lớn.
2. **Cung cấp Dải biến động tin cậy 90% (Confidence Bands / Prediction Intervals):** Định lượng rõ kịch bản Lạc quan (Upper Bound) và Bi quan (Lower Bound) với tỷ lệ bao phủ thực tế đạt **96.77%**.
3. **Mô phỏng 4 Kịch bản Căng thẳng thanh khoản (What-If Stress Testing):** Đánh giá số ngày thâm hụt tiền và tính toán ngay hạn mức đệm tín dụng dự phòng khẩn cấp (**138 Tỷ VNĐ**) trong trường hợp khách hàng trễ hạn nợ AR hoặc nhà cung cấp siết nợ AP.

---

## 2. YÊU CẦU BỐ CỤC (LAYOUT & CANVAS SPECIFICATION)

* **Canvas Size:** `Width: 1920px` x `Height: 2200px` (Khổ dọc chuẩn HD, phù hợp cuộn trang phân tích liền mạch)
* **Vùng 1 (Top Banner & Slicers - H: 90px):**
  * Logo Gỗ Minh Long, Tiêu đề Dashboard, Nhãn thời điểm chốt dự báo (`As-of Date: 30/06/2026`).
  * 2 Bộ lọc (Slicers): Bộ lọc Kịch bản What-If và Bộ lọc Khoảng ngày dự báo.
* **Vùng 2 (Executive KPI Cards - H: 140px):** 4 Thẻ chỉ số tổng quan xếp ngang (Net Expected, Inflow Expected, Số ngày thâm hụt, Đệm thanh khoản đề xuất).
* **Vùng 3 (Main Forecast Horizon Chart - H: 520px):** Biểu đồ chủ đạo chiếm 100% bề ngang: Line & Area Chart hiển thị Actual vs Forecast vs Dải tin cậy 90%.
* **Vùng 4 (Deep-Dive Analytical Charts - H: 480px):** Ghép đôi 2 biểu đồ phân tích chuyên sâu:
  * **Biểu đồ 2.2 (Trái):** So sánh Dòng tiền ròng theo 4 Kịch bản Stress Testing (Clustered Column Chart).
  * **Biểu đồ 2.3 (Phải):** Cơ cấu Động lực chi phối Dòng tiền - Top Features quan trọng (Bar Chart).
* **Vùng 5 (Tactical Cash Calendar Matrix - H: 550px):** Bảng lịch chi tiết 30 ngày tác nghiệp kèm định dạng có điều kiện (Conditional Formatting) tô đỏ tự động các ngày có nguy cơ âm tiền.

---

## 3. THIẾT LẬP KẾT NỐI DỮ LIỆU & DATA MODEL

### 3.1. Kết nối PostgreSQL Data Warehouse
1. Mở file Power BI báo cáo, chọn **Home** $\rightarrow$ **Get Data** $\rightarrow$ **PostgreSQL database**.
2. **Server:** `127.0.0.1:5432` | **Database:** `data_warehouse`.
3. **Data Connectivity mode:** Chọn **Import** (hoặc **DirectQuery** nếu muốn đồng bộ tức thời khi model chạy lại).
4. Tích chọn các đối tượng từ schema `gold`:
   * `gold.view_cashflow_actual_vs_forecast` (Đặt tên trong Power BI: `Fact_Cashflow_Forecast`)
   * `gold.fact_cashflow_scenarios` (Đặt tên trong Power BI: `Fact_Cashflow_Scenarios`)

### 3.2. Thiết lập Quan hệ Mô hình (Model Relationships)
Tạo quan hệ trong cửa sổ **Model View**:
* `silver dim_date[date]` $\xrightarrow{1 \rightarrow N}$ `Fact_Cashflow_Forecast[date]` (Single direction, Active)
* `silver dim_date[date]` $\xrightarrow{1 \rightarrow N}$ `Fact_Cashflow_Scenarios[date]` (Single direction, Active)

---

## 4. BỘ CÔNG THỨC DAX MEASURES CHI TIẾT

> **Đơn vị hiển thị:** Tất cả số tiền được quy đổi sang **Tỷ VNĐ** (chia `1,000,000,000`) để giao diện thanh thoát và dễ nắm bắt cho Ban Giám đốc.

### 4.1. Nhóm Measures Dự báo Cốt lõi (Core Forecast Measures)

```dax
// 1. Dòng tiền Thuần Dự báo (Tỷ VNĐ)
[Dòng tiền thuần Dự báo (Tỷ)] = 
DIVIDE(SUM('Fact_Cashflow_Forecast'[pred_net]), 1e9, 0)

// 2. Dòng tiền Thu Dự báo (Inflow)
[Dòng tiền vào Dự báo (Tỷ)] = 
DIVIDE(SUM('Fact_Cashflow_Forecast'[pred_inflow]), 1e9, 0)

// 3. Dòng tiền Chi Dự báo (Outflow)
[Dòng tiền ra Dự báo (Tỷ)] = 
DIVIDE(SUM('Fact_Cashflow_Forecast'[pred_outflow]), 1e9, 0)

// 4. Dòng tiền Thuần Thực tế Đối soát (Tỷ VNĐ)
[Dòng tiền thuần Thực tế (Tỷ)] = 
DIVIDE(SUM('Fact_Cashflow_Forecast'[actual_net]), 1e9, 0)

// 5. Cận dưới Dải Tin cậy 90% (Worst Case / Lower Bound)
[Dải tin cậy Cận dưới 90% (Tỷ)] = 
DIVIDE(SUM('Fact_Cashflow_Forecast'[pred_net_lower_90]), 1e9, 0)

// 6. Cận trên Dải Tin cậy 90% (Best Case / Upper Bound)
[Dải tin cậy Cận trên 90% (Tỷ)] = 
DIVIDE(SUM('Fact_Cashflow_Forecast'[pred_net_upper_90]), 1e9, 0)

// 7. Độ rộng Biên độ Rủi ro (Band Width)
[Biên độ Rủi ro Tin cậy (Tỷ)] = 
[Dải tin cậy Cận trên 90% (Tỷ)] - [Dải tin cậy Cận dưới 90% (Tỷ)]
```

---

### 4.2. Nhóm Measures Đánh giá Độ chính xác & Cảnh báo (KPI & Alert Measures)

```dax
// 8. Tỷ lệ Sai lệch Dự báo vs Thực tế (% Forecast Variance)
[% Lệch Dự báo Tổng tháng] = 
VAR ActualSum = SUM('Fact_Cashflow_Forecast'[actual_inflow])
VAR PredSum = SUM('Fact_Cashflow_Forecast'[pred_inflow])
RETURN
IF(ActualSum > 0, DIVIDE(ABS(PredSum - ActualSum), ActualSum, 0) * 100, BLANK())

// 9. Số ngày dự kiến Thu không đủ bù Chi (Deficit Days)
[Số ngày Thâm hụt Dự kiến] = 
CALCULATE(
    COUNTROWS('Fact_Cashflow_Forecast'),
    'Fact_Cashflow_Forecast'[pred_net] < 0
)

// 10. Cờ Cảnh báo Trạng thái Thanh khoản (Alert Status)
[Trạng thái Cảnh báo Ngày] = 
IF(
    [Dòng tiền thuần Dự báo (Tỷ)] < 0,
    "🔴 Nguy cơ Âm Quỹ",
    "🟢 Dư thừa Thanh khoản"
)

// 11. Màu sắc Định dạng có Điều kiện (Conditional Formatting Color Hex)
[Color_Deficit_Alert] = 
IF([Dòng tiền thuần Dự báo (Tỷ)] < 0, "#E74C3C", "#2ECC71")
```

---

### 4.3. Nhóm Measures Kịch bản Căng thẳng (What-If Stress Testing)

```dax
// 12. Dòng tiền ròng theo Kịch bản được chọn
[Dòng tiền ròng Kịch bản (Tỷ)] = 
DIVIDE(SUM('Fact_Cashflow_Scenarios'[pred_net]), 1e9, 0)

// 13. Thâm hụt Lũy kế Tối đa theo Kịch bản (Maximum Cumulative Drawdown)
[Thâm hụt Lũy kế Lớn nhất (Tỷ)] = 
VAR CurrentDate = MAX('Fact_Cashflow_Scenarios'[date])
VAR CumSum = 
    CALCULATE(
        [Dòng tiền ròng Kịch bản (Tỷ)],
        FILTER(
            ALLSELECTED('Fact_Cashflow_Scenarios'[date]),
            'Fact_Cashflow_Scenarios'[date] <= CurrentDate
        )
    )
RETURN CumSum

// 14. Hạn mức Đệm Thanh khoản Đề xuất (Recommended Cash Buffer)
[Hạn mức Đệm Đề xuất (Tỷ)] = 
VAR MinCum = 
    MINX(
        ALLSELECTED('Fact_Cashflow_Scenarios'[date]),
        CALCULATE(
            [Dòng tiền ròng Kịch bản (Tỷ)],
            FILTER(
                ALLSELECTED('Fact_Cashflow_Scenarios'[date]),
                'Fact_Cashflow_Scenarios'[date] <= EARLIER('Fact_Cashflow_Scenarios'[date])
            )
        )
    )
RETURN IF(MinCum < 0, ABS(MinCum), 0)
```

---

## 5. HƯỚNG DẪN CẤU HÌNH VISUALS TRÊN POWER BI

### Vùng 1: Bộ lọc (Slicers)
1. **Slicer 1 (What-If Scenario Selector):**
   * Trường dữ liệu: `Fact_Cashflow_Scenarios[scenario_name]`.
   * Kiểu hiển thị: **Tile** (Dạng nút bấm ngang) hoặc Dropdown.
   * Danh sách nút:
     * `Kịch bản Cơ sở (Dự báo chuẩn)`
     * `Kịch bản Chậm thu nợ AR (-25%)`
     * `Kịch bản Áp lực chi AP (+25%)`
     * `Kịch bản Kép (Thu -20%, Chi +20%)`
2. **Slicer 2 (Khoảng ngày dự báo):** Kéo `Fact_Cashflow_Forecast[date]`, chọn chế độ **Between** (Mặc định: 01/07/2026 $\rightarrow$ 31/07/2026).

---

### Vùng 2: 4 Thẻ KPI Cards (Executive Summary Cards)
* **Card 1 (Net Expected):**
  * Fields: `[Dòng tiền thuần Dự báo (Tỷ)]`.
  * Callout value: `-12.92 Tỷ VNĐ`.
  * Label: *Tổng Dòng tiền Ròng Dự kiến Tháng*.
* **Card 2 (Inflow Forecast):**
  * Fields: `[Dòng tiền vào Dự báo (Tỷ)]`.
  * Callout value: `305.93 Tỷ VNĐ` (Thực tế: 288.54 Tỷ - Lệch 6.03%).
  * Label: *Tổng Tiền Thu Dự báo (Độ lệch: 6.0%)*.
* **Card 3 (Deficit Days):**
  * Fields: `[Số ngày Thâm hụt Dự kiến]`.
  * Callout value: `15 / 31 Ngày`.
  * Color: Màu cam cảnh báo (`#E67E22`).
  * Label: *Số Ngày Thu Không Đủ Bù Chi*.
* **Card 4 (Safety Buffer Needed):**
  * Fields: `[Hạn mức Đệm Đề xuất (Tỷ)]`.
  * Callout value: `137.87 Tỷ VNĐ`.
  * Color: Màu đỏ báo động (`#C0392B`).
  * Label: *Đệm Tín dụng Khẩn cấp Cần Duy trì*.

---

### Vùng 3: Biểu đồ Chủ đạo (Main Horizon Forecast Chart)
* **Loại Visual:** **Line and Clustered Column Chart** (hoặc Line Chart đa đường).
* **Trục X (X-axis):** `Fact_Cashflow_Forecast[date]`.
* **Đường Line Y-axis:**
  * Đường 1 (Nét liền, màu Tím đậm `#8E44AD`, Width 3px): `[Dòng tiền thuần Dự báo (Tỷ)]`.
  * Đường 2 (Nét chấm mờ, màu Đỏ nhạt `#E74C3C`): `[Dải tin cậy Cận dưới 90% (Tỷ)]`.
  * Đường 3 (Nét chấm mờ, màu Xanh lục `#27AE60`): `[Dải tin cậy Cận trên 90% (Tỷ)]`.
  * Đường 4 (Nét liền, màu Xanh dương `#2980B9`): `[Dòng tiền thuần Thực tế (Tỷ)]` (để đối soát hồi quy).
* **Mẹo UX & Shaded Area:** Trong tab *Format visual* $\rightarrow$ *Error bars* (hoặc *Lines* $\rightarrow$ *Shade area*), bật vùng bóng đổ giữa Cận dưới và Cận trên để tạo dải dao động xác suất 90% trực quan.

---

### Vùng 4: Cặp Biểu đồ Phân tích Sâu

#### Biểu đồ 4.1: So sánh Dòng tiền theo 4 Kịch bản Stress Testing
* **Loại Visual:** **Clustered Column Chart** (Biểu đồ cột cụm).
* **Trục X:** `Fact_Cashflow_Scenarios[date]`.
* **Trục Y:** `[Dòng tiền ròng Kịch bản (Tỷ)]`.
* **Legend:** `Fact_Cashflow_Scenarios[scenario_code]`.
* **Màu sắc chỉ định:**
  * `S0_Baseline`: Xanh dương (`#3498DB`).
  * `S1_AR_Delay`: Vàng nghệ (`#F1C40F`).
  * `S2_AP_Surge`: Cam đất (`#E67E22`).
  * `S3_Combined`: Đỏ sẫm (`#E74C3C`).

#### Biểu đồ 4.2: Động lực Chi phối Dòng tiền (Top Factors Driving Cash)
* **Loại Visual:** **Bar Chart (Ngang)**.
* **Mục đích:** Giúp CFO biết biến động tiền hôm nay do đâu mà ra (Dựa trên kết quả Feature Importance của LightGBM).
* **Thứ tự hiển thị:**
  1. `inflow_lag_14`: Tính chu kỳ nửa tháng của dòng tiền bán hàng (Độ quan trọng: 28).
  2. `inflow_lag_1`: Quán tính tiền thu ngày liền trước (Độ quan trọng: 25).
  3. `outflow_lag_14`: Chu kỳ trả nợ nhà cung cấp 2 tuần (Độ quan trọng: 21).
  4. `ar_expected_due_today`: Lịch hóa đơn nợ AR đáo hạn hôm nay (Độ quan trọng: 21).
  5. `day_of_week`: Quy luật ngày làm việc trong tuần (Độ quan trọng: 16).

---

### Vùng 5: Bảng Lịch Chi Tiết 30 Ngày Tác nghiệp (Tactical Cash Calendar Matrix)
* **Loại Visual:** **Matrix** hoặc **Table**.
* **Các cột kéo vào:**
  1. `Fact_Cashflow_Forecast[date]` (Định dạng: `dd/mm/yyyy`).
  2. `silver dim_date[day_name]` (Thứ Hai $\rightarrow$ Chủ Nhật).
  3. `[Dòng tiền vào Dự báo (Tỷ)]`.
  4. `[Dòng tiền ra Dự báo (Tỷ)]`.
  5. `[Dòng tiền thuần Dự báo (Tỷ)]`.
  6. `[Dải tin cậy Cận dưới 90% (Tỷ)]`.
  7. `[Dải tin cậy Cận trên 90% (Tỷ)]`.
  8. `[Trạng thái Cảnh báo Ngày]`.
* **Cài đặt Conditional Formatting:**
  * Chọn cột `[Dòng tiền thuần Dự báo (Tỷ)]` $\rightarrow$ *Cell elements* $\rightarrow$ *Background color* $\rightarrow$ Chọn *Field value* dựa trên measure `[Color_Deficit_Alert]`.
  * Bất kỳ ngày nào tiền âm sẽ tự động tô màu Đỏ nhạt để thủ quỹ nhận diện ngay lập tức.

---

## 6. SỔ TAY HƯỚNG DẪN VẬN HÀNH DÀNH CHO GIÁM ĐỐC TÀI CHÍNH (CFO)

| Tình huống tác nghiệp | Hành động trên Dashboard | Quyết định điều hành khuyến nghị |
|:---|:---|:---|
| **Đầu tuần lập lịch thanh toán AP** | Xem Vùng 3 (Biểu đồ Main) và Vùng 5 (Bảng chi tiết) trong 7 ngày tới. | Nếu ngày nào xuất hiện cảnh báo 🔴, dời lịch thanh toán các hóa đơn AP không khẩn cấp sang ngày có dòng tiền thu về lớn (được gợi ý bởi `ar_expected_due_today`). |
| **Đàm phán hạn mức tín dụng với Ngân hàng** | Chọn Slicer sang `Kịch bản Kép (S3 - Thu -20%, Chi +20%)`. | Đưa con số thâm hụt lũy kế **138 Tỷ VNĐ** trên Card 4 làm căn cứ đàm phán hạn mức thấu chi (Overdraft Facility) dự phòng với các ngân hàng đối tác (Vietcombank, BIDV...). |
| **Đánh giá rủi ro khách hàng chậm thanh toán** | Chọn Slicer sang `Kịch bản S1 - AR Delay (-25%)`. | Kiểm tra số ngày thâm hụt (tăng từ 15 ngày lên 26 ngày). Lập tức chỉ đạo phòng Kinh doanh / Thu hồi công nợ kích hoạt chính sách chiết khấu thanh toán sớm 1-2% để kéo tiền về kịp thời. |
