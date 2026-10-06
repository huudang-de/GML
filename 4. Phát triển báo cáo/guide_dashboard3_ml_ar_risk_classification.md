# Hướng dẫn Phát triển Dashboard 3 (Trang 2): Ứng dụng AI Phân loại Rủi ro Nợ Xấu (ML AR Risk Classification)

> **Dự án:** GML Machine Learning Treasury & Liquidity Management  
> **Module liên quan:** `6. ML / 2. AR_Risk_Classification`  
> **Cơ sở dữ liệu nguồn:** PostgreSQL Data Warehouse (`silver.fact_ar_risk_score`, `silver.dim_partner`, `silver.fact_accountsreceivable`)  
> **Đối tượng người dùng:** Giám đốc Tài chính (CFO), Kế toán trưởng, Chuyên viên Thu hồi công nợ  

---

## 1. MỤC TIÊU NGHIỆP VỤ & GIÁ TRỊ MANG LẠI

Khác với Trang 1 (Theo dõi Công nợ Phải thu Lịch sử - Báo cáo Tuổi nợ Aging truyền thống), Trang 2 cung cấp **năng lực cảnh báo sớm (Early Warning System)** được vận hành bởi mô hình Machine Learning LightGBM đã qua tối ưu:

1. **Nhận diện Rủi ro Tiềm ẩn (Proactive Risk Detection):** Không cần chờ khách hàng quá hạn 90 ngày mới biết là nợ xấu. AI sẽ chấm điểm và cấp thẻ "High Risk" ngay khi hóa đơn vừa phát sinh, dựa trên hành vi trả nợ trong quá khứ của khách hàng đó.
2. **Shift-Left Data Processing:** Toàn bộ logic tính toán xác suất, phân hạng, và màu sắc (Hex Code) đã được AI đóng gói sẵn tại tầng Data Warehouse. Power BI chỉ cần tải lên và tự động chuyển màu, giải phóng 100% CPU tính toán của DAX.
3. **Phân bổ Nguồn lực Thu hồi:** Giúp phòng Kế toán tập trung gọi điện hối thúc đúng 20% lượng khách hàng mang lại 80% rủi ro, tối ưu hóa dòng tiền thu về (Cash Inflow).

---

## 2. YÊU CẦU BỐ CỤC (LAYOUT & CANVAS SPECIFICATION)

* **Canvas Size:** `Width: 1920px` x `Height: 2200px` (Khổ dọc chuẩn HD)
* **Vùng 1 (Top Banner & Slicers - H: 90px):**
  * Logo Gỗ Minh Long, Tiêu đề Dashboard: "AI Cảnh báo Sớm Rủi ro Nợ Xấu".
  * 2 Bộ lọc (Slicers): Slicer Lọc Hạng Rủi ro AI (`risk_badge`) và Slicer Ngành hàng/Khu vực.
* **Vùng 2 (Executive KPI Cards - H: 140px):** 4 Thẻ chỉ số tổng quan (Tổng dư nợ High Risk, Số lượng KH High Risk, Xác suất bùng nợ trung bình toàn tệp, Tỷ lệ nợ rủi ro / Tổng nợ).
* **Vùng 3 (Main AI Prediction Chart - H: 520px):** Biểu đồ Bar Chart (Ngang) kết hợp Scatter Plot hiển thị Top 15 khách hàng rủi ro nhất kèm Xác suất bùng nợ cụ thể.
* **Vùng 4 (Deep-Dive Analytical Charts - H: 480px):** Ghép đôi 2 biểu đồ phân tích chuyên sâu:
  * **Biểu đồ 4.1 (Trái):** Ma trận Tuổi nợ Hiện tại vs Hạng Rủi ro AI (Giúp thấy rõ những khách chưa quá hạn nhưng bị AI bắt bài).
  * **Biểu đồ 4.2 (Phải):** Cơ cấu Lý do Bùng nợ - Top Tính năng chi phối Model (SHAP Feature Importance).
* **Vùng 5 (Tactical Collection Matrix - H: 550px):** Bảng danh sách thu hồi nợ ưu tiên, tô màu đỏ rực toàn bộ dòng của khách hàng High Risk.

---

## 3. THIẾT LẬP KẾT NỐI DỮ LIỆU & DATA MODEL

### 3.1. Kết nối PostgreSQL Data Warehouse
1. Mở file Power BI báo cáo, chọn **Home** $\rightarrow$ **Get Data** $\rightarrow$ **PostgreSQL database**.
2. **Server:** `127.0.0.1:5432` | **Database:** `data_warehouse`.
3. Tích chọn các bảng từ schema `silver`:
   * `silver.fact_ar_risk_score` (Bảng AI vừa tạo)
   * `silver.dim_partner` (Danh mục Khách hàng)
   * `silver.fact_accountsreceivable` (Chi tiết Công nợ)

### 3.2. Thiết lập Quan hệ Mô hình (Model Relationships)
Tạo quan hệ trong cửa sổ **Model View**:
* `silver dim_partner[partner_code]` $\xrightarrow{1 \rightarrow 1}$ `silver fact_ar_risk_score[customer_id]` (Cả 2 bảng đều unique mỗi khách hàng 1 dòng tại thời điểm báo cáo, Cross filter direction: Both)
* `silver dim_partner[partner_code]` $\xrightarrow{1 \rightarrow N}$ `silver fact_accountsreceivable[customer_id]`

---

## 4. BỘ CÔNG THỨC DAX MEASURES CHI TIẾT

> **Đơn vị hiển thị:** Tất cả số tiền được quy đổi sang **Tỷ VNĐ**.

### 4.1. Nhóm Measures AI Cảnh Báo (AI Risk Measures)

```dax
// 1. Tổng Dư nợ Hiện tại (Tỷ VNĐ)
[Tổng Dư nợ Phải thu (Tỷ)] = 
DIVIDE(SUM('silver fact_accountsreceivable'[ending_debit_balance]), 1e9, 0)

// 2. Dư nợ thuộc nhóm Rủi ro Cao (High Risk)
[Dư nợ High Risk (Tỷ)] = 
CALCULATE(
    [Tổng Dư nợ Phải thu (Tỷ)],
    'silver fact_ar_risk_score'[risk_badge] = "High Risk"
)

// 3. Tỷ trọng Dư nợ High Risk / Tổng nợ (%)
[% Nợ High Risk] = 
DIVIDE([Dư nợ High Risk (Tỷ)], [Tổng Dư nợ Phải thu (Tỷ)], 0)

// 4. Số lượng Khách hàng thuộc nhóm High Risk
[Số KH High Risk] = 
CALCULATE(
    COUNTROWS('silver fact_ar_risk_score'),
    'silver fact_ar_risk_score'[risk_badge] = "High Risk"
)

// 5. Dự phòng Tổn thất kỳ vọng (Expected Credit Loss - ECL) theo chuẩn IFRS 9
// Công thức: ECL = EAD (Tổng dư nợ) x PD (Xác suất vỡ nợ) x LGD (Giả định mất 100% do nợ tín chấp)
[Dự phòng Rủi ro ECL (Tỷ)] = 
SUMX(
    'silver dim_partner',
    [Tổng Dư nợ Phải thu (Tỷ)] * RELATED('silver fact_ar_risk_score'[default_probability])
)

// 6. Màu nền Cảnh báo UI (Được AI sinh sẵn)
[Color_AI_Risk_Badge] = 
MAX('silver fact_ar_risk_score'[ui_color])
```

---

## 5. HƯỚNG DẪN CẤU HÌNH VISUALS TRÊN POWER BI

### Vùng 1: Bộ lọc (Slicers)
1. **Slicer 1 (AI Risk Selector):**
   * Trường dữ liệu: `silver fact_ar_risk_score[risk_badge]`.
   * Kiểu hiển thị: **Tile** (Dạng nút bấm ngang).
   * Cấu hình *Visual \> Slicer settings \> Selection:* Bật **Single select** để Kế toán tập trung soi từng nhóm.

### Vùng 2: 4 Thẻ KPI Cards
* **Card 1 (High Risk Debt):**
  * Fields: `[Dư nợ High Risk (Tỷ)]`.
  * Label: *Tổng Nợ Nguy cơ Mất trắng*.
  * Cấu hình: Tô chữ đỏ đập vào mắt.
* **Card 2 (High Risk Concentration):**
  * Fields: `[% Nợ High Risk]`.
  * Label: *Tỷ trọng Nợ Độc Hại*.
* **Card 3 (High Risk Clients):**
  * Fields: `[Số KH High Risk]`.
  * Label: *Số Khách Hàng Nằm Trong Danh Sách Đen AI*.
* **Card 4 (Expected Credit Loss - ECL):**
  * Fields: `[Dự phòng Rủi ro ECL (Tỷ)]`.
  * Label: *Dự phòng Tổn thất Kỳ vọng (ECL)*.
  * Cấu hình: Cực kỳ quan trọng với CFO để trích lập dự phòng lợi nhuận (P&L).

---

### Vùng 3: Biểu đồ Chủ đạo (Top 15 KH Nguy hiểm Nhất)
* **Loại Visual:** **Clustered Bar Chart** (Biểu đồ thanh ngang).
* **Trục Y (Y-axis):** `silver dim_partner[partner_name]`.
* **Trục X (X-axis):** `[Dự phòng Rủi ro ECL (Tỷ)]` (Nên dùng ECL thay vì Dư nợ gốc để thấy rõ số tiền thực sự có nguy cơ bốc hơi).
* **Lọc (Filters):** Kéo `[Dự phòng Rủi ro ECL (Tỷ)]` vào *Top N = 15*.
* **Màu tự động AI (Quan trọng):** 
  * Chọn Visual $\rightarrow$ Format $\rightarrow$ Bars $\rightarrow$ Color $\rightarrow$ Chọn ký hiệu `fx` (Conditional Formatting).
  * Format style: **Field value**.
  * Dựa trên: Kéo measure `[Color_AI_Risk_Badge]` vào đây.
  * Bấm **OK**. Lập tức cột nào High Risk sẽ tự chuyển Đỏ `#FF4444`, Low Risk thành Xanh `#00C851`.

---

### Vùng 4: Cặp Biểu đồ Phân tích Sâu

#### Biểu đồ 4.1: Đi tìm Kẻ Giấu Mặt (Nợ chưa quá hạn nhưng AI báo Đỏ)
* **Loại Visual:** **Matrix** (Ma trận).
* **Rows:** `Tuổi Nợ Bảng` (Từ Current, 1-30, 31-60... đến 180+).
* **Columns:** `silver fact_ar_risk_score[risk_badge]`.
* **Values:** `[Dư nợ Phải thu (Tỷ)]`.
* **Phân tích:** Giao điểm giữa hàng `Current` (Đang trong hạn) và cột `High Risk` chính là những "Quả bom nổ chậm". Đây là rổ khách hàng cần bộ phận Tín dụng chặn ngay việc xuất hàng mới.

#### Biểu đồ 4.2: SHAP Feature Importance (Động lực Cảnh báo)
* **Loại Visual:** **Donut Chart** hoặc **Bar Chart**.
* Trực quan hóa các nguyên nhân gốc rễ (Root Causes) khiến khách hàng trễ nợ (Dựa trên báo cáo SHAP của Model): *Lịch sử trễ hạn trung bình (76%)*, *Vòng quay kho chậm (12%)*, *Số dư nợ quá lớn (8%)*.

---

### Vùng 5: Bảng Danh Sách Tróc Nã Kế Toán (Collection Action Matrix)
* **Loại Visual:** **Table**.
* **Các cột kéo vào:**
  1. `silver dim_partner[partner_name]` (Tên Khách hàng).
  2. `silver fact_ar_risk_score[risk_badge]` (Thẻ Cảnh Báo AI).
  3. `silver fact_ar_risk_score[default_probability]` (Xác suất Bùng nợ - Định dạng %).
  4. `[Tổng Dư nợ Phải thu (Tỷ)]`.
  5. `[Dự phòng Rủi ro ECL (Tỷ)]`.
* **Cài đặt Conditional Formatting:**
  * Chọn cột `risk_badge` $\rightarrow$ *Cell elements* $\rightarrow$ *Background color* $\rightarrow$ *Field value* $\rightarrow$ `[Color_AI_Risk_Badge]`. Bảng sẽ nổi bật toàn bộ các dòng Đỏ/Vàng/Xanh đúng chuẩn UI/UX tài chính.

---

## 6. SỔ TAY HƯỚNG DẪN VẬN HÀNH DÀNH CHO KẾ TOÁN TRƯỞNG & CFO

| Tình huống tác nghiệp | Hành động trên Dashboard | Quyết định điều hành (Collection Strategy) |
|:---|:---|:---|
| **Khách hàng xin mua trả chậm thêm 1 tỷ** | Lọc tên khách hàng đó. Xem cột thẻ AI. | Nếu AI báo `High Risk` (Mặc dù khách chưa nợ quá hạn đồng nào), kiên quyết **từ chối bán chịu**, yêu cầu thanh toán tiền mặt 100% trước khi giao hàng. |
| **Cuộc họp Thu hồi nợ sáng Thứ Hai** | Bấm Slicer `High Risk`, trích xuất Bảng 5 (Danh sách thu hồi nợ ưu tiên). | Yêu cầu Sale Manager trực tiếp đến tận xưởng khách hàng gây áp lực thu hồi. Cắt ngay hạn mức tín dụng (Credit Limit) trên ERP đối với 15 khách top đầu. |
| **Thiết lập Dự phòng Tổn thất Phải thu** | Xem thẻ KPI `Tổng Nợ Nguy cơ Mất trắng`. | CFO lấy thẳng số này (Ví dụ: 12.5 Tỷ) đưa vào bút toán chi phí dự phòng rủi ro nợ khó đòi cho kỳ kế toán tháng này, đảm bảo bức tranh Lợi nhuận P&L không bị ảo. |
