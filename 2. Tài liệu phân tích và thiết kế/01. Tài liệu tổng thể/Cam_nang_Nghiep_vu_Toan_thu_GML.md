# 📘 CẨM NANG NGHIỆP VỤ TOÀN THƯ DỰ ÁN GỖ MINH LONG
## Hệ thống Phân tích Dữ liệu, Báo cáo Quản trị BI & Tối ưu hóa Tài chính Thông minh (AI Financial Brain)

---

## MỤC LỤC
1. [TỔNG QUAN DOANH NGHIỆP & CHUỖI GIÁ TRỊ GỖ MINH LONG](#1-tổng-quan-doanh-nghiệp--chuỗi-giá-trị-gỗ-minh-long)
2. [KIẾN TRÚC DỮ LIỆU & LUỒNG XỬ LÝ (DATA PIPELINE)](#2-kiến-trúc-dữ-liệu--luồng-xử-lý-data-pipeline)
3. [HỆ THỐNG TÀI KHOẢN KẾ TOÁN & CÁC BẢNG DỮ LIỆU NGUỒN](#3-hệ-thống-tài-khoản-kế-toán--các-bảng-dữ-liệu-nguồn)
4. [CÁC QUY TẮC NGHIỆP VỤ ĐẶC THÙ & ĐỐI SOÁT DỮ LIỆU](#4-các-quy-tắc-nghiệp-vụ-đặc-thù--đối-soát-dữ-liệu)
5. [CHI TIẾT NGHIỆP VỤ 5 BÁO CÁO QUẢN TRỊ (BI DASHBOARDS)](#5-chi-tiết-nghiệp-vụ-5-báo-cáo-quản-trị-bi-dashboards)
   - [5.1. Dashboard 1: Quản trị Hoạt động Tài chính & Cấu trúc Nợ](#51-dashboard-1-quản-trị-hoạt-động-tài-chính--cấu-trúc-nợ)
   - [5.2. Dashboard 2: Quản trị Hàng tồn kho](#52-dashboard-2-quản-trị-hàng-tồn-kho)
   - [5.3. Dashboard 3: Quản trị Phải thu - Phải trả](#53-dashboard-3-quản-trị-phải-thu---phải-trả)
   - [5.4. Dashboard 4: Quản trị Tiền gửi & An toàn Thanh khoản](#54-dashboard-4-quản-trị-tiền-gửi--an-toàn-thanh-khoản)
   - [5.5. Dashboard 5: Quản trị Dòng tiền (Cashflow)](#55-dashboard-5-quản-trị-dòng-tiền-cashflow)
6. [HỆ THỐNG TRÍ TUỆ NHÂN TẠO & TỐI ƯU HÓA TÀI CHÍNH (AI FINANCIAL BRAIN)](#6-hệ-thống-trí-tuệ-nhân-tạo--tối-ưu-hóa-tài-chính-ai-financial-brain)
   - [6.1. Khung liên kết Chu kỳ Chuyển hóa Tiền (Cash Conversion Cycle - CCC)](#61-khung-liên-kết-chu-kỳ-chuyển-hóa-tiền-cash-conversion-cycle---ccc)
   - [6.2. Dự báo Dòng tiền ngắn hạn (Cashflow Forecasting)](#62-dự-báo-dòng-tiền-ngắn-hạn-cashflow-forecasting)
   - [6.3. Phân loại Rủi ro & Chấm điểm Tín dụng Công nợ (AR Risk Classification)](#63-phân-loại-rủi-ro--chấm-điểm-tín-dụng-công-nợ-ar-risk-classification)
   - [6.4. Dự báo Nhu cầu & Tối ưu Tồn kho An toàn (Inventory Demand Forecasting)](#64-dự-báo-nhu-cầu--tối-ưu-tồn-kho-an-toàn-inventory-demand-forecasting)
   - [6.5. Tối ưu hóa Nguồn vốn & Thanh khoản (Liquidity & Treasury Optimization - LP/MILP)](#65-tối-ưu-hóa-nguồn-vốn--thanh-khoản-liquidity--treasury-optimization---lpmilp)
   - [6.6. Trợ lý Doanh nghiệp Thông minh (AI Business Assistant)](#66-trợ-lý-doanh-nghiệp-thông-minh-ai-business-assistant)
7. [TỔNG KẾT GIÁ TRỊ DOANH NGHIỆP](#7-tổng-kết-giá-trị-doanh-nghiệp)

---

## 1. TỔNG QUAN DOANH NGHIỆP & CHUỖI GIÁ TRỊ GỖ MINH LONG

### 1.1. Lĩnh vực hoạt động
Công ty TNHH Gỗ Minh Long là một trong những doanh nghiệp sản xuất và phân phối vật liệu nội thất gỗ công nghiệp hàng đầu tại Việt Nam (ván dăm MFC, ván sợi MDF, HDF, ván ép Plywood, phủ bề mặt Melamine, Laminates, Acrylic, V- veneers).

### 1.2. Đặc thù vận hành & Tài chính ngành gỗ
- **Vốn lưu động lớn & chu kỳ sản xuất dài:** Doanh nghiệp phải dự trữ khối lượng lớn gỗ ván thô (raw panels), giấy trang trí và hóa chất keo dán. Nếu tồn kho quá nhiều sẽ gây ứ đọng vốn và nguy cơ ẩm mốc, hư hỏng; nếu tồn kho quá ít sẽ gián đoạn dây chuyền ép phủ.
- **Áp lực công nợ khách hàng (B2B):** Khách hàng chủ yếu là xưởng mộc, công ty tư vấn thiết kế nội thất, nhà thầu dự án và hệ thống đại lý. Chính sách công nợ thường cho nợ từ 30 – 90 ngày. Tình trạng chiếm dụng vốn và thanh toán chậm diễn ra phổ biến.
- **Sử dụng đòn bẩy tài chính ngân hàng linh hoạt:** Để tài trợ vốn lưu động, công ty ký hợp đồng hạn mức tín dụng với nhiều ngân hàng (VietinBank, BIDV, Techcombank,...), vay ngắn hạn theo từng khế ước nhận nợ (thường từ 3 - 6 tháng).
- **Hoạt động điều hòa tiền tệ (Treasury):** Có những giai đoạn công ty dôi dư tiền mặt ngắn hạn (do vừa thu nợ đại lý hoặc tiền hàng về) nhưng chưa đến hạn trả nợ vay, công ty thực hiện gửi tiết kiệm có kỳ hạn (1 tháng, 3 tháng) để sinh lời, tối ưu hóa chi phí lãi ròng.

---

## 2. KIẾN TRÚC DỮ LIỆU & LUỒNG XỬ LÝ (DATA PIPELINE)

Hệ thống được thiết kế theo kiến trúc hồ dữ liệu hiện đại **Medallion Architecture (Bronze - Silver - Gold)**:

```
[Nguồn MISA SME / AMIS]
       │
       ▼ (Xuất định kỳ CSV/Excel sổ kế toán, kho, công nợ)
┌────────────────────────────────────────────────────────┐
│ 🥉 BRONZE LAYER (Data Lake - MinIO / S3)              │
│    - Lưu trữ nguyên trạng dữ liệu thô (Raw Format)     │
│    - Định danh theo thư mục ngày/tháng                 │
└────────────────────────────────────────────────────────┘
       │
       ▼ (ETL bằng Apache Airflow & Python Engine)
┌────────────────────────────────────────────────────────┐
│ 🥈 SILVER LAYER (Data Warehouse - PostgreSQL)         │
│    - Làm sạch dữ liệu, chuẩn hóa kiểu dữ liệu, khử trùng│
│    - Áp dụng các Business Rules (Khử CTNB, Semi-add)  │
│    - Mô hình hóa theo chuẩn STAR SCHEMA:               │
│      + 7 Dimension Tables                              │
│      + 13-14 Fact Tables                               │
│    - Đạt chuẩn "Single Source of Truth" (100% chuẩn xác)│
└────────────────────────────────────────────────────────┘
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
┌─────────────────────────────┐   ┌──────────────────────────────┐
│ 🥇 GOLD: POWER BI DASHBOARDS│   │ 🤖 GOLD: AI & MACHINE LEARNING│
│  - D1: Hoạt động Tài chính   │   │  - Dự báo Dòng tiền (XGB/Prophet)│
│  - D2: Hàng tồn kho          │   │  - Chấm điểm rủi ro AR       │
│  - D3: Phải thu - Phải trả  │   │  - Dự báo tồn kho an toàn    │
│  - D4: Tiền gửi & Thanh khoản│   │  - Tối ưu Thanh khoản (MILP) │
│  - D5: Dòng tiền (Cashflow) │   │  - AI Business Assistant     │
└─────────────────────────────┘   └──────────────────────────────┘
```

---

## 3. HỆ THỐNG TÀI KHOẢN KẾ TOÁN & CÁC BẢNG DỮ LIỆU NGUỒN

Dữ liệu được hạch toán theo Hệ thống Chuẩn mực Kế toán Việt Nam (VAS) / Thông tư 200:

| Mã TK | Tên Tài Khoản | Nghiệp vụ trong Dự án | Bảng Fact tương ứng |
|:---|:---|:---|:---|
| **111** | Tiền mặt | Theo dõi thu/chi quỹ tiền mặt của công ty | `fact_cashflow` |
| **112** | Tiền gửi ngân hàng | Dòng tiền qua các tài khoản ngân hàng thực tế | `fact_cashflow` |
| **128** | Đầu tư nắm giữ đến ngày đáo hạn | Tiền gửi tiết kiệm có kỳ hạn tại ngân hàng | `fact_termdeposit`, `fact_balancesheet` (Mã 120/123) |
| **131** | Phải thu của khách hàng | Theo dõi chi tiết công nợ bán lẻ, đại lý, dự án | `fact_accountsreceivable` |
| **331** | Phải trả người bán | Công nợ nhà cung cấp gỗ ván, giấy, keo | `fact_accountspayable` |
| **152** | Nguyên liệu, vật liệu | Tồn kho gỗ thô, giấy melamine, phụ gia | `fact_inventory_balance`, `inward`, `outward` |
| **155** | Thành phẩm | Tấm ván thành phẩm đã ép bề mặt, đóng gói | `fact_inventory_balance`, `inward`, `outward` |
| **156** | Hàng hóa | Hàng thương mại (mua đi bán lại) | `fact_inventory_balance`, `inward`, `outward` |
| **341** | Vay và nợ thuê tài chính | Dư nợ vay ngắn hạn (34111, 34113, 34114), dài hạn (34112) | `fact_cashflow`, `fact_loan`, `fact_balancesheet` |
| **511** | Doanh thu bán hàng & CCDV | Ghi nhận doanh thu thuần | `fact_incomestatement` |
| **632** | Giá vốn hàng bán | Chi phí xuất kho bán hàng | `fact_incomestatement` |
| **635** | Chi phí tài chính | Chi phí lãi vay ngân hàng | `fact_incomestatement` |
| **B01-DN** | Bảng cân đối kế toán | Chỉ tiêu tài sản, nguồn vốn chốt theo kỳ | `fact_balancesheet` |
| **B02-DN** | Báo cáo KQKD | Doanh thu, chi phí, lợi nhuận lũy kế | `fact_incomestatement` |

---

## 4. CÁC QUY TẮC NGHIỆP VỤ ĐẶC THÙ & ĐỐI SOÁT DỮ LIỆU

Trong quá trình xây dựng hệ thống, 3 bẫy nghiệp vụ lớn đã được giải quyết dứt điểm:

### 4.1. Quy tắc loại trừ giao dịch chuyển tiền nội bộ (`CTNB`)
- **Vấn đề:** Doanh nghiệp thường xuyên chuyển tiền giữa các tài khoản ngân hàng của chính mình (ví dụ rút tiền từ Techcombank nộp vào BIDV để trả nợ). Kế toán ghi nhận Nợ TK 112 (tăng thu) và Có TK 112 (tăng chi). Nếu SUM trực tiếp toàn bộ dòng tiền, doanh số Thu/Chi sẽ bị phồng ảo hàng chục đến hàng trăm tỷ đồng.
- **Quy tắc xử lý:** Lọc bỏ toàn bộ các chứng từ có mã loại chứng từ là `CTNB` hoặc ghi nhận chuyển tiền giữa các tài khoản nội bộ ra khỏi báo cáo dòng tiền hoạt động thuần.

### 4.2. Xử lý thuộc tính Bán cộng dồn (Semi-Additive) của Bảng cân đối kế toán & Kho
- **Vấn đề:** Tiền mặt, Hàng tồn kho, Nợ phải thu/phải trả là các đại lượng **Thời điểm (Point-in-time / Snapshot)**. Chúng không được phép cộng dồn qua thời gian. Nếu người dùng chọn bộ lọc "Quý 1" hoặc "Cả năm", hành vi SUM bình thường sẽ cộng dồn số dư Tháng 1 + Tháng 2 + Tháng 3, dẫn đến con số sai lệch phi lý (gấp 3-12 lần thực tế).
- **Quy tắc xử lý:** Sử dụng kỹ thuật **Closing Balance at Max Date**:
  $$\text{Số dư chỉ tiêu} = \text{CALCULATE}(\text{SUM}(Balance), \text{Date} = \text{MAX}(Date))$$
  Hệ thống luôn tự động lấy số dư tại ngày giao dịch cuối cùng của khoảng thời gian được lọc.

### 4.3. Loại bỏ bảng nhập tay `fact_loan` & Nguồn sự thật duy nhất (Single Source of Truth)
- **Vấn đề:** Ban đầu doanh nghiệp duy trì file Excel khế ước vay (`fact_loan`) nhập tay độc lập. Dữ liệu này thường xuyên vênh lệch với sao kê ngân hàng do con người quên cập nhật hoặc hạch toán trễ.
- **Quy tắc xử lý:** Chuẩn hóa nghiệp vụ dư nợ ngân hàng trực tiếp từ **Sổ cái tiền mặt/ngân hàng (`fact_cashflow`)** tại các tiểu khoản TK 341. Áp dụng logic cửa sổ SQL:
  ```sql
  ROW_NUMBER() OVER (PARTITION BY account_no ORDER BY posting_date DESC, id DESC)
  ```
  Lấy số dư tín dụng (`credit_balance`) mới nhất. Kết quả kiểm thử UAT khớp 100% số liệu thực tế tại mọi thời điểm.

---

## 5. CHI TIẾT NGHIỆP VỤ 5 BÁO CÁO QUẢN TRỊ (BI DASHBOARDS)

### 5.1. Dashboard 1: Quản trị Hoạt động Tài chính & Cấu trúc Nợ
- **Mục tiêu:** Cung cấp bức tranh toàn cảnh cho CFO và Giám đốc Tài chính về đòn bẩy nợ, chi phí tài chính và mức độ an toàn tín dụng.
- **Các chỉ số KPI cốt lõi:**
  1. **Dư nợ ngắn hạn (TK 34111, 34113, 34114):** Vay bổ sung vốn lưu động trả tiền hàng, mua nguyên vật liệu.
  2. **Dư nợ dài hạn (TK 34112):** Vay đầu tư máy móc, nhà xưởng, dây chuyền sản xuất ván ép.
  3. **Room tín dụng (Hạn mức còn lại):** Tổng hạn mức phê duyệt của các ngân hàng trừ đi tổng dư nợ hiện hữu. Cho biết doanh nghiệp còn có thể giải ngân tối đa bao nhiêu để ứng phó sự cố.
  4. **Tỷ lệ bảo đảm / LTV (Loan-to-Value):** Tổng giá trị tài sản thế chấp (bất động sản, máy móc xưởng, hàng hóa) so với tổng nợ vay.
  5. **Hệ số chi trả lãi vay (Interest Service Coverage Ratio - ISR / ICR):**
     $$\text{ISR} = \frac{\text{EBIT}}{\text{Chi phí lãi vay (TK 635)}}$$
     Đánh giá khả năng tạo ra lợi nhuận để gánh lãi ngân hàng.

---

### 5.2. Dashboard 2: Quản trị Hàng tồn kho
- **Mục tiêu:** Giúp Giám đốc Khối Cung ứng & Kho vận kiểm soát hàng hóa, chống đọng vốn, đảm bảo hàng phục vụ đơn hàng kịp thời.
- **Các chỉ số KPI cốt lõi:**
  1. **Giá trị tồn kho cuối kỳ:** Phân tích theo nhóm nguyên vật liệu thô (gỗ keo, ván MDF), giấy trang trí, hóa chất keo dán và ván phủ thành phẩm.
  2. **Số ngày luân chuyển hàng tồn kho (Days Inventory Outstanding - DIO):**
     $$\text{DIO} = \frac{\text{Giá trị HTK bình quân} \times \text{Số ngày trong kỳ}}{\text{Giá vốn hàng bán (COGS - TK 632)}}$$
  3. **Tồn kho an toàn (Safety Stock) & Điểm đặt hàng lại (ROP):** Cảnh báo nguy cơ thiếu hụt nguyên vật liệu gây ngưng trệ sản xuất.
  4. **Tồn kho chậm luân chuyển & Tồn kho chết:** Nhận diện những mã sản phẩm không có lệnh xuất kho trên 90 hoặc 180 ngày để lên phương án thanh lý, thu hồi vốn.

---

### 5.3. Dashboard 3: Quản trị Phải thu - Phải trả
- **Mục tiêu:** Cân đối giữa việc thu hồi nợ khách hàng và chiếm dụng vốn nhà cung cấp hợp lý.
- **Các chỉ số KPI cốt lõi:**
  1. **Số ngày thu tiền bình quân (Days Sales Outstanding - DSO):**
     $$\text{DSO} = \frac{\text{Phải thu khách hàng bình quân (TK 131)} \times \text{Số ngày}}{\text{Tổng doanh thu (TK 511)}}$$
  2. **Số ngày trả tiền nhà cung cấp bình quân (Days Payable Outstanding - DPO):**
     $$\text{DPO} = \frac{\text{Phải trả người bán bình quân (TK 331)} \times \text{Số ngày}}{\text{Tổng giá trị mua hàng / Giá vốn}}$$
  3. **Cơ cấu tuổi nợ (Aging Buckets):** Phân chia chi tiết công nợ thành các dải: *Chưa đến hạn*, *Quá hạn 1-30 ngày*, *Quá hạn 31-60 ngày*, *Quá hạn 61-90 ngày*, *Quá hạn >90 ngày (nguy cơ nợ khó đòi)*.
  4. **Top đối tác nợ lớn & Nợ quá hạn kéo dài:** Danh sách đích danh các khách hàng cần áp dụng biện pháp siết nợ hoặc ngừng giao hàng.

---

### 5.4. Dashboard 4: Quản trị Tiền gửi & An toàn Thanh khoản
- **Mục tiêu:** Giám sát an toàn ngân quỹ tức thời, đánh giá khả năng sống sót của công ty khi có biến động bất ngờ.
- **Các chỉ số KPI cốt lõi:**
  1. **Tiền & Tương đương tiền (Mã B01-DN_110):** Tiền mặt tại quỹ + Tiền gửi ngân hàng không kỳ hạn.
  2. **Hệ số khả năng thanh toán hiện hành (Current Ratio):**
     $$\text{CR} = \frac{\text{Tài sản ngắn hạn}}{\text{Nợ ngắn hạn}}$$
  3. **Hệ số khả năng thanh toán nhanh (Quick Ratio - Acid-test):**
     $$\text{QR} = \frac{\text{Tiền} + \text{Đầu tư ngắn hạn} + \text{Phải thu}}{\text{Nợ ngắn hạn}}$$
     (Loại trừ Hàng tồn kho vì không thể biến ngay thành tiền trong tích tắc).
  4. **Thời gian an toàn dòng tiền (Cash Runway):**
     $$\text{Runway (Tháng)} = \frac{\text{Số dư tiền hiện hữu}}{\text{Chi phí tiền mặt bình quân mỗi tháng (Cash Burn Rate)}}$$

---

### 5.5. Dashboard 5: Quản trị Dòng tiền (Cashflow)
- **Mục tiêu:** Theo dõi luồng tiền thực tế vào - ra, bảo đảm công ty không rơi vào tình trạng "kinh doanh có lãi nhưng phá sản vì hết tiền mặt".
- **Các chỉ số KPI cốt lõi:**
  1. **Dòng tiền vào (Total Cash Inflow):** Tiền thu từ bán hàng, thu hồi nợ, rút vốn vay ngân hàng, thu hồi tiền gửi tiết kiệm.
  2. **Dòng tiền ra (Total Cash Outflow):** Tiền trả nhà cung cấp, chi lương nhân viên, thanh toán nợ gốc/lãi ngân hàng, thuế, mua sắm TSCĐ.
  3. **Dòng tiền thuần (Net Cashflow):** $\Delta \text{Cash} = \text{Tổng Thu} - \text{Tổng Chi}$.
  4. **Đối chiếu Kế hoạch vs Thực tế (Variance Analysis):** So sánh dòng tiền thực nhận/thực chi với kế hoạch kinh doanh (`fact_businessplan`), cảnh báo ngay các khoản chi vượt dự toán.

---

## 6. HỆ THỐNG TRÍ TUỆ NHÂN TẠO & TỐI ƯU HÓA TÀI CHÍNH (AI FINANCIAL BRAIN)

Một trong những bước tiến chiến lược của dự án là không dừng lại ở mức **Phân tích mô tả (Descriptive BI)** mà nâng cấp toàn diện lên **Phân tích dự báo (Predictive)** và **Phân tích đề xuất hành động tối ưu (Prescriptive Optimization)**.

### 6.1. Khung liên kết Chu kỳ Chuyển hóa Tiền (Cash Conversion Cycle - CCC)
Chu kỳ chuyển hóa tiền là "sợi dây chỉ đỏ" kết nối toàn bộ hoạt động:

$$\text{CCC (Ngày)} = \text{DIO (Tồn kho)} + \text{DSO (Phải thu)} - \text{DPO (Phải trả)}$$

- Nếu **Tồn kho đọng lâu** (DIO cao) $\rightarrow$ Tiền bị chôn trong kho.
- Nếu **Khách hàng chậm trả** (DSO cao) $\rightarrow$ Tiền bị chiếm dụng ngoài thị trường.
- Hệ quả tất yếu: Doanh nghiệp bị hụt tiền mặt $\rightarrow$ Buộc phải kích hoạt giải ngân vay ngân hàng $\rightarrow$ Đội chi phí lãi vay (TK 635).

Vì vậy, **3 bài toán ML (Tồn kho, Công nợ, Dòng tiền) chính là ĐẦU VÀO BẮT BUỘC** để giải quyết bài toán lớn nhất: **Tối ưu hóa Thanh khoản & Vốn vay.**

```
 ┌─────────────────────────────────────────────────────────┐
 │             CÁC DỰ ÁN DỰ BÁO ĐẦU VÀO (UPSTREAM)         │
 └─────────────────────────────────────────────────────────┘
  1. AI Tối ưu Tồn kho      ──► Giải phóng vốn đọng kho
  2. AI Phân tích Nợ AR     ──► Dự báo chính xác tiền thu hồi
  3. AI Dự báo Dòng tiền    ──► Xác định vị thế Tiền ròng (Net Cash) mỗi tuần
                                         │
                                         ▼
 ┌─────────────────────────────────────────────────────────┐
 │               DỮ LIỆU RÀNG BUỘC (CONSTRAINTS)          │
 └─────────────────────────────────────────────────────────┘
  - bc_tin_dung_2026.xlsx   ──► Hạn mức vay, Lãi suất vay từng ngân hàng
  - Hop_dong_tien_gui.xlsm  ──► Lãi suất tiền gửi, Kỳ hạn, Điều kiện rút
  - Cash Buffer Tối thiểu    ──► Ngưỡng tiền mặt dự phòng khẩn cấp
                                         │
                                         ▼
 ┌─────────────────────────────────────────────────────────┐
 │       BÀI TOÁN TỐI ƯU THANH KHOẢN (MILP OPTIMIZER)      │
 ├─────────────────────────────────────────────────────────┤
 │  MINIMIZE:  Tổng Chi phí Lãi vay - Tổng Doanh thu Tiền gửi │
 │                                                         │
 │  OUTPUT: Khuyến nghị hành động thời gian thực:           │
 │  - Ngày nào cần giải ngân bao nhiêu, từ ngân hàng nào?  │
 │  - Ngày nào cần gửi tiết kiệm bao nhiêu, kỳ hạn nào?    │
 └─────────────────────────────────────────────────────────┘
```

---

### 6.2. Dự báo Dòng tiền ngắn hạn (Cashflow Forecasting)
- **Thuật toán:** XGBoost Regressor, LightGBM kết hợp Facebook Prophet.
- **Tính năng đầu vào:** Lịch đáo hạn hóa đơn công nợ, đơn hàng đang sản xuất, tính chu kỳ theo mùa (cuối năm xây dựng nhiều, tháng Giêng âm lịch thấp điểm), ngày trả lương, lịch nộp thuế.
- **Đầu ra:** Dự báo dòng tiền ròng thu/chi hàng tuần trong 4 - 12 tuần tới kèm khoảng tin cậy (Confidence Interval 95%).

---

### 6.3. Phân loại Rủi ro & Chấm điểm Tín dụng Công nợ (AR Risk Classification)
- **Thuật toán:** Phân loại đa lớp (Multi-class Classification) bằng XGBoost / Random Forest Classifier.
- **Đầu vào:** Lịch sử thanh toán quá khứ, doanh số trung bình, tỷ lệ nợ quá hạn lịch sử, loại hình khách hàng (đại lý cấp 1, xưởng nội thất, nhà thầu dự án).
- **Đầu ra:** Gán nhãn rủi ro (Low / Medium / High Risk) và dự báo xác suất khách hàng thanh toán trễ hạn trên 30 ngày. Cho phép bộ phận kế toán tự động khóa đơn hàng mới hoặc hạ hạn mức tín dụng trước khi nợ xấu xảy ra.

---

### 6.4. Dự báo Nhu cầu & Tối ưu Tồn kho An toàn (Inventory Demand Forecasting)
- **Thuật toán:** Dự báo chuỗi thời gian kết hợp mô hình phân tích tồn kho cổ điển:
  $$\text{Safety Stock} = Z \times \sigma_{\text{demand}} \times \sqrt{L}$$
  $$\text{Reorder Point (ROP)} = (\text{Nhu cầu TB ngày} \times L) + \text{Safety Stock}$$
- **Đầu ra:** Xác định chính xác lượng nguyên liệu cần đặt cho từng mã ván/giấy melamine theo từng tuần, giảm 15 - 25% lượng vốn chết trong kho.

---

### 6.5. Tối ưu hóa Nguồn vốn & Thanh khoản (Liquidity & Treasury Optimization - LP/MILP)
- **Phương pháp:** Quy hoạch tuyến tính hỗn hợp nguyên (Mixed-Integer Linear Programming - MILP) sử dụng thư viện `PuLP` / `SciPy Optimize`.
- **Hàm mục tiêu:**
  $$\min \sum_{t=1}^{T} \left( \text{Lãi vay phải trả}_t - \text{Lãi tiền gửi thu được}_t + \text{Phạt thiếu thanh khoản}_t \right)$$
- **Ràng buộc:**
  1. $\text{Số dư tiền cuối ngày } t \ge \text{Buffer tối thiểu (ví dụ 10 tỷ VNĐ)}$.
  2. $\text{Tổng dư nợ tại Ngân hàng } b \le \text{Room tín dụng phê duyệt của NH } b$.
  3. Tiền gửi có kỳ hạn không được rút trước hạn trừ khi chịu phạt mất lãi.
  4. Tuân thủ ngày đáo hạn khế ước vay cũ.
- **Giá trị kinh tế:** Tiết kiệm hàng trăm triệu đến hàng tỷ đồng tiền lãi suất ròng mỗi năm cho Gỗ Minh Long thông qua việc tránh vay thừa và tận dụng triệt để tiền gửi kỳ hạn ngắn.

---

### 6.6. Trợ lý Doanh nghiệp Thông minh (AI Business Assistant)
- **Công nghệ:** Large Language Model (LLM) kết hợp RAG (Retrieval-Augmented Generation) và Text-to-SQL.
- **Chức năng:** Cho phép Ban Giám đốc và CFO trò chuyện bằng ngôn ngữ tự nhiên:
  - *"Hôm nay công ty còn bao nhiêu tiền mặt khả dụng?"*
  - *"Tuần tới có khế ước vay nào đến hạn không và ngân hàng nào còn room tín dụng?"*
  - *"Top 5 khách hàng có nguy cơ chậm nợ cao nhất tháng này là ai?"*
  Hệ thống tự động sinh câu truy vấn SQL an toàn vào PostgreSQL Silver Warehouse, kiểm chứng số liệu và trả về câu trả lời súc tích kèm biểu đồ gợi ý.

---

## 7. TỔNG KẾT GIÁ TRỊ DOANH NGHIỆP

| Tiêu chí | Trước khi triển khai (Hiện trạng cũ) | Sau khi triển khai Hệ thống Gỗ Minh Long |
|:---|:---|:---|
| **Phương thức báo cáo** | Báo cáo Excel thủ công rời rạc, mất 3 - 5 ngày sau khi chốt sổ | Tự động hóa 100%, cập nhật gần thời gian thực (Near Real-time) |
| **Độ chính xác dữ liệu** | Thường xuyên sai lệch do lỗi nhập tay, nhiễu tiền ảo CTNB, cộng dồn BCTC | Đạt 100% chuẩn xác theo Single Source of Truth (PostgreSQL) |
| **Quản trị dòng tiền** | Bị động (Reactive): Hết tiền mới cuống cuồng đi làm thủ tục vay | Chủ động (Proactive): Dự báo trước thiếu hụt tiền từ 30 - 90 ngày |
| **Tối ưu chi phí vốn** | Vay và gửi tiền theo cảm tính, lãi vay bị đội cao | Thuật toán MILP tính toán điểm vay/gửi tối ưu, giảm tối đa chi phí lãi |
| **Ra quyết định điều hành** | Dựa trên kinh nghiệm và cảm tính của lãnh đạo | Định hướng bằng dữ liệu (Data-driven) và trợ lực bởi Trí tuệ Nhân tạo (AI) |

---
*Tài liệu được biên soạn đồng bộ với Hệ thống Dữ liệu, Mô hình Star Schema và Bộ quy chuẩn kỹ thuật của Dự án Gỗ Minh Long.*
