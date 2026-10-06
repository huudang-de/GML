# HƯỚNG DẪN TÍCH HỢP AI LÊN POWER BI: LIQUIDITY OPTIMIZATION
**Dashboard Mục tiêu:** Dashboard 4 (Tiền gửi & Tín dụng) / Dashboard 5 (Dòng tiền)
**Nguồn dữ liệu:** `silver.fact_liquidity_actions` (Sinh ra từ Python PuLP Optimizer)

---

## 1. MỤC ĐÍCH (BUSINESS PURPOSE)
Khác với các Dashboard báo cáo quá khứ, trang **AI Liquidity Optimization** đóng vai trò là "Cố vấn Tài chính" (Prescriptive Analytics). 
Khi CFO mở Dashboard này lên, màn hình sẽ hiển thị chính xác số tiền đang thiếu hụt trong tháng và **chỉ định cụ thể** phải rút sổ tiết kiệm nào, vay ngân hàng nào để tốn ít tiền lãi nhất.

---

## 2. KẾT NỐI MÔ HÌNH DỮ LIỆU (DATA MODELING)

### 2.1 Bảng Fact
- **Bảng chính:** `silver.fact_liquidity_actions`
- **Các cột có sẵn:**
  - `Action`: Loại hành động (VD: "Vay Cầm cố Sổ Tiết Kiệm", "Vay Hạn mức (Tín chấp/BĐS)")
  - `Bank`: Mã ngân hàng (VD: "VCB", "MBBank")
  - `Amount_VND`: Số tiền đề xuất giải ngân/gửi.
  - `Interest_Rate_%`: Lãi suất tối ưu tìm được.
  - `Run_ID`, `As_Of_Date`: Để tracking phiên bản AI.

### 2.2 Relationship (Data Lineage)
Nối bảng `fact_liquidity_actions` với các bảng DIM hiện tại của GML:
- `fact_liquidity_actions[Bank]` (Nhiều) ➔ `dim_bank[Bank_Code]` (Một)

---

## 3. CÔNG THỨC DAX (DAX MEASURES)

Tạo các Measure tính toán phục vụ thẻ KPI:

**1. Tổng tiền AI đề xuất Vay/Huy động:**
```dax
AI_Total_Capital_Raised = SUM('fact_liquidity_actions'[Amount_VND])
```

**2. Tổng Chi phí Lãi vay ước tính (Theo AI):**
```dax
AI_Est_Annual_Interest = 
SUMX(
    'fact_liquidity_actions', 
    'fact_liquidity_actions'[Amount_VND] * ('fact_liquidity_actions'[Interest_Rate_%] / 100)
)
```

**3. Lãi suất vay bình quân (Weighted Average Rate):**
```dax
AI_Weighted_Avg_Rate = 
DIVIDE([AI_Est_Annual_Interest], [AI_Total_Capital_Raised], 0)
```

---

## 4. HƯỚNG DẪN THIẾT KẾ GIAO DIỆN (UI/UX LAYOUT)

Trang báo cáo này nên được thiết kế theo phong cách **Action-Oriented (Định hướng hành động)**.

### 4.1. Cụm Thẻ KPI (Top Banner)
- **Card 1 (Màu đỏ nhạt):** Thâm hụt tiền dự kiến (Max Deficit) + Safety Buffer (Ví dụ: 10 Tỷ VNĐ).
- **Card 2 (Màu xanh lá):** Tổng chi phí lãi vay (AI_Est_Annual_Interest) (Ví dụ: 432 Triệu VNĐ).
- **Card 3 (Màu vàng):** Lãi suất đi vay bình quân (Ví dụ: 4.33%). (Highlight: Rẻ hơn rất nhiều so với lãi suất tín chấp thông thường 7-8%).

### 4.2. Biểu đồ Phân bổ Nguồn vốn (Capital Structure)
- **Visual Type:** Donut Chart (Biểu đồ vành khăn)
- **Trục Legend:** `fact_liquidity_actions[Action]`
- **Trục Values:** `[AI_Total_Capital_Raised]`
- **Ý nghĩa:** Cho CFO thấy tỷ trọng vốn được huy động từ "Thế chấp sổ cá nhân" so với "Vay tín chấp BĐS".

### 4.3. Bảng Lệnh Hành Động (Action Execution Matrix)
- **Visual Type:** Table / Matrix
- **Cột hiển thị:**
  - `Ngân hàng` (Bank)
  - `Hành động chỉ định` (Action)
  - `Số tiền` (Amount_VND) - Format: Trillions/Billions
  - `Lãi suất` (Interest_Rate_%)
- **Conditional Formatting:** 
  - Tô nền màu xanh nhạt cho các dòng "Cầm cố sổ tiết kiệm" (Vì rủi ro thấp, lãi rẻ).
  - Tô nền màu cam cho các dòng "Vay tín chấp" (Lãi cao, bào mòn lợi nhuận).

---

## 5. BÀI HỌC "SHIFT-LEFT" TỪ DỰ ÁN
Toàn bộ logic tính toán "Tại sao lại chọn BIDV thay vì VCB?", "Tại sao thế chấp sổ lại rẻ hơn?" đều đã được xử lý bằng thư viện Toán học `PuLP` ở tầng Python (Silver Layer). 
Power BI lúc này chỉ làm đúng nhiệm vụ vinh quang nhất: **Hiển thị quyết định**. Không có bất kỳ vòng lặp hay logic IF/ELSE phức tạp nào phải viết bằng DAX, giúp Dashboard load trong chưa tới 1 giây.
