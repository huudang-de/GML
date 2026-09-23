# 📊 Hướng Dẫn Xây Dựng Data Model — Dự Án Gỗ Minh Long (GML)

> **Dành cho:** Intern / Fresher Data Engineer & Data Analyst  
> **Dự án:** BI System — Gỗ Minh Long (INDA × GML)  
> **Stack:** PostgreSQL · Apache Airflow · Python · MinIO · Power BI  
> **Cập nhật:** 2026-09-22 — Đồng bộ với dữ liệu thực tế đã triển khai

---

## Tổng Quan Hành Trình

```
Bước 1 → Hiểu bài toán & hệ thống
Bước 2 → Xác định nguồn dữ liệu
Bước 3 → Hiểu mã sản phẩm (Naming Convention)
Bước 4 → Thiết kế kiến trúc Warehouse (Star Schema)
Bước 5 → Thiết kế Dimension Tables
Bước 6 → Thiết kế Fact Tables (từng domain)
Bước 7 → Mapping nguồn → đích (Source-to-Target)
Bước 8 → Xác nhận lại với BRD (5 báo cáo)
```

---

## BƯỚC 1 — Hiểu Bài Toán & Kiến Trúc Hệ Thống

### 1.1 Gỗ Minh Long là ai?

Minh Long là **công ty sản xuất & kinh doanh vật liệu gỗ** (ván MDF/HDF/Dăm, nẹp, giấy Melamine, tấm WBP...). Họ cần một hệ thống **BI tập trung** thay thế việc xem báo cáo thủ công trên Excel và phần mềm kế toán MISA.

### 1.2 Kiến trúc tổng thể

```
NGUON DU LIEU: MISA (ERP/Ke toan) + Excel noi bo
      |
      | Extract
      v
ETL LAYER: Apache Airflow + Python --> MinIO (object storage)
      |
      | Load
      v
DATA WAREHOUSE: PostgreSQL
  Bronze (_file_registry) --> Silver (Dim/Fact)
      |
      | Connect (DirectQuery / Import)
      v
POWER BI: 5 Dashboard
```

### 1.3 Năm dashboard báo cáo

| # | Tên Báo cáo | Bảng Fact chính |
|---|---------|----|
| 1 | **Quản trị Hoạt động Tài chính & Tín dụng** | `fact_loan`, `fact_collateral`, `fact_creditlimitsummary`, `fact_cashflow`, `fact_incomestatement`, `fact_businessplan`, `fact_balancesheet` |
| 2 | **Quản trị Hàng tồn kho** | `fact_inventory_balance`, `fact_inventoryinward`, `fact_inventoryoutward`, `fact_incomestatement`, `fact_businessplan` |
| 3 | **Quản trị Phải thu - Phải trả** | `fact_accountsreceivable`, `fact_accountspayable`, `fact_incomestatement`, `fact_businessplan` |
| 4 | **Quản trị Tiền gửi & Thanh khoản** | `fact_termdeposit`, `fact_balancesheet`, `fact_incomestatement` |
| 5 | **Quản trị Dòng tiền** | `fact_cashflow`, `fact_balancesheet`, `fact_businessplan`, `fact_accountsreceivable`, `fact_accountspayable`, `fact_inventory_balance`, `fact_incomestatement` |

---

## BƯỚC 2 — Xác Định Nguồn Dữ Liệu

> [!IMPORTANT]
> Trước khi thiết kế bất kỳ bảng nào, bạn **PHẢI** liệt kê đầy đủ nguồn gốc dữ liệu. Đây là nguyên tắc số 1 trong data engineering.

### 2.1 Bản đồ nguồn dữ liệu

| File nguồn | Hệ thống | Bảng đích (Silver) | Ghi chú |
|-----------|---------|-------------------|----|
| `So_chi_tiet_cac_tai_khoan_...xlsx` | MISA | `fact_cashflow` | Sổ chi tiết TK 111, 112 |
| `B01_DN_Bao_cao_tinh_hinh_tai_chinh_...xlsx` | MISA | `fact_balancesheet` | Bảng cân đối kế toán |
| `B02_DN_Bao_cao_ket_qua_hoat_dong_kinh_doanh_...xlsx` | MISA | `fact_incomestatement` | P&L, COGS |
| `Chi_tiet_cong_no_phai_thu_khach_hang_...xlsx` | MISA | `fact_accountsreceivable` | Công nợ KH |
| `Chi_tiet_cong_no_phai_tra_nha_cung_cap_...xlsx` | MISA | `fact_accountspayable` | Công nợ NCC |
| `Tong_hop_ton_kho_...xlsx` (Nhập) | MISA | `fact_inventoryinward` | Chi tiết nhập kho |
| `Tong_hop_ton_kho_...xlsx` (Xuất) | MISA | `fact_inventoryoutward` | Chi tiết xuất kho |
| `Tong_hop_ton_kho_...xlsx` (Tồn) | MISA | `fact_inventory_balance` | Số dư tồn đầu/cuối kỳ |
| `Danh_sach_hang_hoa_dich_vu_...xlsx` | MISA | `dim_product` | 145,089 mã hàng |
| `Danh_sach_doi_tac_...xlsx` | MISA | `dim_partner` | KH + NCC |
| `So_do_tai_khoan_...xlsx` | MISA | `dim_account` | Hệ thống TK kế toán |
| `BC tín dụng 2026.xlsx` | Excel nội bộ | `fact_loan` | Khoản vay theo ngân hàng |
| `BC tín dụng 2026.xlsx` (sheet TSBĐ) | Excel nội bộ | `fact_collateral` | Tài sản đảm bảo |
| `BC tín dụng 2026.xlsx` (sheet Hạn mức) | Excel nội bộ | `fact_creditlimitsummary` | Hạn mức tín dụng |
| `Hop_dong_tien_gui.xlsx` | Excel nội bộ | `fact_termdeposit` | Sổ tiết kiệm |
| `Ke_hoach_kinh_doanh_2026.xlsx` | Excel nội bộ | `fact_businessplan` | Kế hoạch/Target (3 sheet) |
| Thủ công / config | Team DA | `dim_bank` | Danh sách ngân hàng |
| Thủ công / config | Team DA | `dim_warehouse` | Danh sách kho |
| Thủ công / config | Team DA | `dim_accountnumber` | Số TK ngân hàng |
| Thủ công / config | Team DA | `dim_reportitem` | Chỉ tiêu BCTC |

### 2.2 Câu hỏi cần hỏi PM/khách hàng trước khi bắt đầu

- [ ] Tần suất export data từ MISA là bao nhiêu? (Hàng ngày? Hàng tuần?)
- [ ] Ai là người tạo file Excel nội bộ? Có theo quy trình chuẩn không?
- [ ] Năm dữ liệu lịch sử cần load là từ năm nào?
- [ ] Múi giờ lưu trữ timestamp? (UTC hay GMT+7?)

---

## BƯỚC 3 — Hiểu Quy Ước Đặt Mã Sản Phẩm

> [!NOTE]
> Gỗ Minh Long có quy tắc mã hóa rất cụ thể. Hiểu điều này giúp bạn biết ý nghĩa khi đọc `product_code`. **Trong hệ thống hiện tại, phần parse mã chưa được triển khai** — `dim_product` chỉ lưu nguyên mã, tên, đơn vị và nhóm hàng từ MISA.

### 3.1 Mã Nguyên Vật Liệu (NVL) — Ván cốt thô

```
M  017  ML  H  2  T
|   |    |  |  |  +-- Kích thước: T=4'x8', L=6'x8', N=4'x9'
|   |    |  |  +----> Tiêu chuẩn formaldehyde: 0=E0, 1=E1, 2=E2
|   |    |  +-------> Đặc tính: A=thường, H=chống ẩm HMR, C=chống cháy, M=MMR
|   |    +----------> Nhà cung cấp: ML=Minh Long, DA=Dự án
|   +--------------> Độ dày: 017=17mm, 018=18mm, 025=25mm...
+-----------------> Loại ván: M=MDF, D=Dăm, H=HDF, P=Ván dán, V=Veneer, L=Laminate, A=Acrylic
```

### 3.2 Mã Giấy Mine

```
GM  2401  T
|    |    +-- Kích thước: T/L/N
|    +-------> Màu sắc (4 ký tự)
+----------> GM = Giấy Mine
```

### 3.3 Mã Nẹp (12 ký tự)

```
N  2110  CL  2401  T
|   |     |    |   +-- Bề mặt: T=sần, G=bóng, W=xước
|   |     |    +-----> Màu (4 ký tự)
|   |     +---------> Chủng loại: EC=Eco, CL=Class, LU=Luxury, BL=Ballad, CT=Catania
|   +--------------> Kích thước x độ dày: 2110=21mmx1mm, 2815=28mmx1,5mm
+------------------> N = Nẹp
```

### 3.4 Mã Thành Phẩm Melamine (21 ký tự)

```
M017ML  H  2  T  MM  24012401  G
|         |  |  |   |    |     +-- Film bề mặt
|         |  |  |   |    +-------> Mã màu (8 ký tự = màu1 + màu2)
|         |  |  |   +-----------> Loại phủ: MM=2 mặt Melamine, LL=2 mặt Laminate, MX=1 mặt Mel
|         |  |  +---------------> Kích thước: T/L/N
|         |  +-----------------> Tiêu chuẩn: 0/1/2/3/4
|         +--------------------> Đặc tính: A/H/C/M
+--------------------------------> Ký tự 1-6: Giống NVL (Loại+Dày+NCC)
```

> [!TIP]
> Trong tương lai, có thể viết hàm Python tự động **parse mã sản phẩm** thành các thuộc tính riêng lẻ để filter theo loại ván, độ dày, màu sắc. Hỏi mentor về nhu cầu này khi chiều nay gặp.

---

## BƯỚC 4 — Thiết Kế Kiến Trúc Warehouse (Star Schema)

### 4.1 Tại sao dùng Star Schema?

**Star Schema** là chuẩn vàng trong Data Warehouse vì:
- Power BI hoạt động tốt nhất với mô hình này
- Truy vấn nhanh hơn (ít JOIN hơn Snowflake Schema)
- Dễ hiểu cho người dùng cuối (analyst, finance team)

### 4.2 Các lớp trong Data Warehouse

| Lớp | Schema/Prefix | Mục đích |
|-----|--------|----------|
| Bronze | `bronze._file_registry` | Sổ cái upload: MD5, batch_id, status, rollback |
| Silver — Dim | `silver.dim_*` | Bảng mô tả: partner, product, bank, warehouse... |
| Silver — Fact | `silver.fact_*` | Bảng giao dịch chứa số liệu + FK |
| Power BI | Dim_Date (DAX) | Bảng lịch tạo bằng `CALENDARAUTO()`, không qua ETL |

---

## BƯỚC 5 — Thiết Kế Dimension Tables

> [!IMPORTANT]
> Dimension tables là **"ngữ cảnh"** của dữ liệu. Xây dựng sai dimension sẽ khiến mọi báo cáo sau không lọc được đúng.

> [!NOTE]
> Tất cả các cột dưới đây phản ánh **schema thực tế** trong file CSV đã export từ hệ thống đang chạy. Không thêm cột nếu chưa có trong nguồn.

---

### Dim_Date — Bảng Thời Gian (Tạo bằng DAX trong Power BI)

> [!IMPORTANT]
> `Dim_Date` **KHÔNG** được load qua ETL. Tạo bằng DAX `CALENDARAUTO()` trực tiếp trong Power BI Desktop.

```dax
Dim_Date = 
ADDCOLUMNS (
    CALENDARAUTO(),
    "Year", YEAR([Date]),
    "Quarter", "Q" & FORMAT([Date], "Q"),
    "Month Number", MONTH([Date]),
    "Month Name", FORMAT([Date], "MMM"),
    "Month Year", FORMAT([Date], "MMM YYYY")
)
```

---

### dim_account — Tài Khoản Kế Toán

**Nguồn:** `So_do_tai_khoan_...xlsx` (MISA)  
**Cột thực tế:** `_id`, `account_no`, `account_name`, `account_type`, `_source_file`, `_loaded_at`, `_batch_id`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | Surrogate key |
| `account_no` | VARCHAR | Số TK kế toán (111, 112, 131...) — **Business key** |
| `account_name` | TEXT | Tên tài khoản |
| `account_type` | TEXT | Loại TK |

---

### dim_accountnumber — Số Tài Khoản Ngân Hàng

**Nguồn:** Config / thủ công  
**Cột thực tế:** `_id`, `account_no`, `bank_code`, `account_name`, `_source_file`, `_loaded_at`, `_batch_id`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | Surrogate key |
| `account_no` | VARCHAR | Số TK ngân hàng — **Business key** |
| `bank_code` | VARCHAR | FK → `dim_bank.bank_code` |
| `account_name` | TEXT | Tên chủ tài khoản |

---

### dim_bank — Ngân Hàng

**Nguồn:** Config / thủ công  
**Cột thực tế:** `_id`, `bank_code`, `bank_name`, `_source_file`, `_loaded_at`, `_batch_id`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | Surrogate key |
| `bank_code` | VARCHAR UNIQUE | Mã ngân hàng ('VCB', 'MB', 'BIDV'...) — **Business key** |
| `bank_name` | TEXT | Tên đầy đủ ngân hàng |

---

### dim_partner — Đối Tác (Khách Hàng & Nhà Cung Cấp)

**Nguồn:** `Danh_sach_doi_tac_...xlsx` (MISA) — 2 sheet, load chung 1 bảng  
**Cột thực tế:** `_id`, `partner_code`, `partner_name`, `partner_type`, `tax_code`, `address`, `_source_file`, `_loaded_at`, `_batch_id`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | Surrogate key |
| `partner_code` | VARCHAR UNIQUE | Mã đối tác MISA — **Business key** |
| `partner_name` | TEXT | Tên đối tác |
| `partner_type` | TEXT | 'Khach hang' / 'Nha cung cap' / 'Ca hai' |
| `tax_code` | VARCHAR | Mã số thuế |
| `address` | TEXT | Địa chỉ |

> [!WARNING]
> Tên bảng là `dim_partner`, **KHÔNG phải** `dim_customer`. Một bảng dùng chung cho cả khách hàng lẫn nhà cung cấp, phân biệt qua `partner_type`.

---

### dim_product — Sản Phẩm / Hàng Hóa

**Nguồn:** `Danh_sach_hang_hoa_dich_vu_...xlsx` (MISA) — 145,089 mã hàng  
**Cột thực tế:** `_id`, `product_code`, `product_name`, `unit_of_measure`, `product_category`, `_source_file`, `_loaded_at`, `_batch_id`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | Surrogate key |
| `product_code` | VARCHAR UNIQUE | Mã hàng hóa MISA — **Business key** (dùng JOIN với Fact) |
| `product_name` | TEXT | Tên hàng hóa tiếng Việt |
| `unit_of_measure` | TEXT | Đơn vị tính (Cái, Tấm, Bộ, Kg...) |
| `product_category` | TEXT | Nhóm hàng từ MISA (Phụ kiện, Khác...) |

> [!NOTE]
> **Câu hỏi cho Mentor (chiều nay):** `dim_product` hiện chỉ có 1 cấp nhóm (`product_category`). Có cần enrich thêm từ parse `product_code` không (loại ván, độ dày, màu sắc)? Và MISA có export thêm trường nào khác không (đơn giá vốn tiêu chuẩn)?

---

### dim_reportitem — Chỉ Tiêu Báo Cáo Tài Chính

**Nguồn:** Config / thủ công — 2 sheet (BCTC + Kế hoạch)  
**Cột thực tế:** `_id`, `item_id`, `item_code`, `item_name`, `report_type`, `_source_file`, `_loaded_at`, `_batch_id`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | Surrogate key |
| `item_id` | VARCHAR UNIQUE | VD: `B01-DN_110` — **Business key** (dùng JOIN với Fact) |
| `item_code` | VARCHAR | Mã chỉ tiêu (có thể trùng giữa các loại báo cáo) |
| `item_name` | TEXT | Tên chỉ tiêu |
| `report_type` | TEXT | Loại báo cáo (B01, B02...) |

> [!WARNING]
> Dùng `item_id` để JOIN với `indicator_code` trong Fact. **Không dùng `item_code`** vì bị trùng lặp giữa các loại báo cáo.

---

### dim_warehouse — Kho Hàng

**Nguồn:** Config / thủ công  
**Cột thực tế:** `_id`, `warehouse_code`, `warehouse_name`, `_source_file`, `_loaded_at`, `_batch_id`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | Surrogate key |
| `warehouse_code` | VARCHAR UNIQUE | Mã kho — **Business key** |
| `warehouse_name` | TEXT | Tên kho |

---

## BƯỚC 6 — Thiết Kế Fact Tables

> [!IMPORTANT]
> **Quy tắc vàng của Fact Table:**
> - Chứa các **khóa ngoại** (FK) trỏ đến Dimension tables
> - Chứa các **measure** (số liệu đo được): tiền, số lượng, tỷ lệ...
> - **KHÔNG** lưu text mô tả (để trong Dimension)
> - Mỗi dòng = 1 sự kiện/giao dịch/snapshot

---

### fact_cashflow — Dòng Tiền (Sổ Chi Tiết TK)

**Nguồn:** `So_chi_tiet_cac_tai_khoan_...xlsx` (MISA — TK 111, 112)  
**Dashboard:** BC1 (Tài chính), BC5 (Dòng tiền)

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `posting_date` | DATE | Ngày hạch toán — FK → `Dim_Date` |
| `account_no` | VARCHAR | FK → `dim_account.account_no` |
| `debit_amount` | NUMERIC(20,2) | Phát sinh Nợ (tiền vào) |
| `credit_amount` | NUMERIC(20,2) | Phát sinh Có (tiền ra) |
| `ending_balance` | NUMERIC(20,2) | Dư cuối kỳ (semi-additive) |
| `document_no` | VARCHAR | Số chứng từ MISA |
| `description` | TEXT | Diễn giải giao dịch |

**Logic nghiệp vụ:**
- `debit_amount > 0` → Tiền **VÀO** tài khoản (dòng thu)
- `credit_amount > 0` → Tiền **RA** khỏi tài khoản (dòng chi)
- `ending_balance` là semi-additive → dùng `LASTDATE` trong DAX

---

### fact_balancesheet — Bảng Cân Đối Kế Toán

**Nguồn:** `B01_DN_Bao_cao_tinh_hinh_tai_chinh_...xlsx` (MISA)  
**Dashboard:** BC1, BC4, BC5

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `reporting_date` | DATE | Ngày báo cáo — FK → `Dim_Date` |
| `indicator_code` | VARCHAR | FK → `dim_reportitem.item_id` |
| `ending_balance` | NUMERIC(20,2) | Số dư cuối kỳ |

---

### fact_incomestatement — Kết Quả Hoạt Động Kinh Doanh

**Nguồn:** `B02_DN_Bao_cao_ket_qua_hoat_dong_kinh_doanh_...xlsx` (MISA)  
**Dashboard:** BC1, BC2, BC3, BC4, BC5

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `month` | DATE | Tháng báo cáo — FK → `Dim_Date` |
| `indicator_code` | VARCHAR | FK → `dim_reportitem.item_id` |
| `actual_amount` | NUMERIC(20,2) | Số thực tế |

---

### fact_businessplan — Kế Hoạch Kinh Doanh

**Nguồn:** `Ke_hoach_kinh_doanh_2026.xlsx` (3 sheet: KD, Tài chính, HTK)  
**Dashboard:** BC1, BC2, BC3, BC5

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `month` | DATE | Tháng kế hoạch — FK → `Dim_Date` |
| `indicator_code` | VARCHAR | FK → `dim_reportitem.item_id` |
| `target_amount` | NUMERIC(20,2) | Giá trị kế hoạch/target |

> [!WARNING]
> Các chỉ tiêu vòng quay (`Chu_ky_tien_mat`, `Vong_quay_phai_thu`...) đã được ETL **chia đều cho 12 tháng**. Dùng `SUM(target_amount)` trên filter tháng — **KHÔNG cộng dồn qua nhiều tháng**.

---

### fact_loan — Tín Dụng & Khoản Vay

**Nguồn:** `BC tín dụng 2026.xlsx` (Excel nội bộ)  
**Dashboard:** BC1

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `disbursement_date` | DATE | Ngày giải ngân — FK → `Dim_Date` |
| `bank_code` | VARCHAR | FK → `dim_bank.bank_code` |
| `loan_type` | VARCHAR | 'Ngắn hạn' / 'Dài hạn' |
| `remaining_principal` | NUMERIC(20,2) | Dư nợ gốc còn lại |
| `interest_rate` | NUMERIC(8,4) | Lãi suất %/năm |
| `maturity_date` | DATE | Ngày đáo hạn |

---

### fact_collateral — Tài Sản Đảm Bảo

**Nguồn:** `BC tín dụng 2026.xlsx` — sheet TSBĐ  
**Dashboard:** BC1

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `bank_code` | VARCHAR | FK → `dim_bank.bank_code` |
| `asset_name` | VARCHAR | Tên TSĐB |
| `asset_type` | VARCHAR | 'BDS', 'May moc', 'Hang hoa'... |
| `appraised_value` | NUMERIC(20,2) | Giá trị thẩm định |
| `ltv_coefficient` | NUMERIC(8,4) | Hệ số TSĐB (%) |
| `max_loan_value` | NUMERIC(20,2) | Giá trị cho vay tối đa |

---

### fact_creditlimitsummary — Hạn Mức Tín Dụng

**Nguồn:** `BC tín dụng 2026.xlsx` — sheet Hạn mức  
**Dashboard:** BC1

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `bank_code` | VARCHAR | FK → `dim_bank.bank_code` |
| `credit_limit` | NUMERIC(20,2) | Hạn mức được cấp |
| `granted_limit` | NUMERIC(20,2) | Hạn mức được phê duyệt |

---

### fact_termdeposit — Tiền Gửi Có Kỳ Hạn

**Nguồn:** `Hop_dong_tien_gui.xlsx` (Excel nội bộ)  
**Dashboard:** BC4

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `deposit_date` | DATE | Ngày gửi — FK → `Dim_Date` |
| `maturity_date` | DATE | Ngày đáo hạn |
| `bank_code` | VARCHAR | FK → `dim_bank.bank_code` |
| `passbook_no` | VARCHAR | Số sổ/khế ước |
| `original_amount` | NUMERIC(20,2) | Số tiền gốc |
| `interest_rate` | NUMERIC(8,4) | Lãi suất %/năm |
| `term` | VARCHAR | Kỳ hạn (VD: '3 tháng', '6 tháng') |
| `remaining_value` | NUMERIC(20,2) | Giá trị còn lại (gốc + lãi tích lũy) |

---

### fact_inventory_balance — Tồn Kho Cuối Kỳ (Snapshot)

**Nguồn:** `Tong_hop_ton_kho_...xlsx` (MISA) — phần số dư  
**Dashboard:** BC2, BC5

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `snapshot_date` | DATE | Ngày snapshot (cuối tháng) — FK → `Dim_Date` |
| `product_code` | VARCHAR | FK → `dim_product.product_code` |
| `warehouse_code` | VARCHAR | FK → `dim_warehouse.warehouse_code` |
| `ending_quantity` | NUMERIC(15,3) | Số lượng tồn cuối kỳ |
| `ending_value` | NUMERIC(20,2) | Giá trị tồn cuối kỳ (VND) |

> [!WARNING]
> **Semi-additive** — KHÔNG SUM qua nhiều tháng. Trong DAX: `CALCULATE(SUM(fact_inventory_balance[ending_value]), LASTDATE(Dim_Date[Date]))`

---

### fact_inventoryinward — Nhập Kho

**Nguồn:** `Tong_hop_ton_kho_...xlsx` (MISA) — phần phát sinh nhập  
**Dashboard:** BC2

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `posting_date` | DATE | Ngày nhập — FK → `Dim_Date` |
| `product_code` | VARCHAR | FK → `dim_product.product_code` |
| `warehouse_code` | VARCHAR | FK → `dim_warehouse.warehouse_code` |
| `quantity` | NUMERIC(15,3) | Số lượng nhập |
| `credit_amount` | NUMERIC(20,2) | Giá trị nhập (VND) |

---

### fact_inventoryoutward — Xuất Kho

**Nguồn:** `Tong_hop_ton_kho_...xlsx` (MISA) — phần phát sinh xuất  
**Dashboard:** BC2

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `posting_date` | DATE | Ngày xuất — FK → `Dim_Date` |
| `product_code` | VARCHAR | FK → `dim_product.product_code` |
| `warehouse_code` | VARCHAR | FK → `dim_warehouse.warehouse_code` |
| `quantity` | NUMERIC(15,3) | Số lượng xuất |
| `debit_amount` | NUMERIC(20,2) | Giá trị xuất (VND) |

---

### fact_accountsreceivable — Công Nợ Phải Thu

**Nguồn:** `Chi_tiet_cong_no_phai_thu_khach_hang_...xlsx` (MISA)  
**Dashboard:** BC3, BC5

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `posting_date` | DATE | Ngày hóa đơn — FK → `Dim_Date` |
| `partner_code` | VARCHAR | FK → `dim_partner.partner_code` |
| `invoice_no` | VARCHAR | Số hóa đơn |
| `original_amount` | NUMERIC(20,2) | Giá trị hóa đơn gốc |
| `ending_credit_balance` | NUMERIC(20,2) | Số dư phải thu còn lại |
| `overdue_days` | INT | Số ngày quá hạn |
| `aging_bucket` | VARCHAR | 'Current','1-30','31-60','61-90','>90' |

---

### fact_accountspayable — Công Nợ Phải Trả

**Nguồn:** `Chi_tiet_cong_no_phai_tra_nha_cung_cap_...xlsx` (MISA)  
**Dashboard:** BC3, BC5

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `_id` | BIGSERIAL PK | |
| `posting_date` | DATE | Ngày chứng từ — FK → `Dim_Date` |
| `partner_code` | VARCHAR | FK → `dim_partner.partner_code` |
| `invoice_no` | VARCHAR | Số hóa đơn |
| `original_amount` | NUMERIC(20,2) | Giá trị hóa đơn gốc |
| `ending_credit_balance` | NUMERIC(20,2) | Số dư phải trả còn lại |

---

## BƯỚC 7 — Mapping Nguồn → Đích (Source-to-Target)

> [!NOTE]
> Đây là tài liệu quan trọng nhất khi triển khai ETL. Mỗi cột trong Fact/Dim đều phải có mapping rõ ràng từ nguồn.

### Mapping: fact_cashflow

| Cột đích | File nguồn | Cột nguồn | Phép biến đổi |
|----------|-----------|-----------|--------------|
| `posting_date` | So_chi_tiet_... | Ngày chứng từ | `pd.to_datetime()` |
| `account_no` | So_chi_tiet_... | Số TK kế toán | As-is |
| `debit_amount` | So_chi_tiet_... | Phát sinh Nợ | `COALESCE(value, 0)` |
| `credit_amount` | So_chi_tiet_... | Phát sinh Có | `COALESCE(value, 0)` |
| `ending_balance` | So_chi_tiet_... | Dư cuối kỳ | `COALESCE(value, 0)` |
| `document_no` | So_chi_tiet_... | Số chứng từ | As-is |

### Mapping: fact_inventory_balance

| Cột đích | File nguồn | Cột nguồn | Phép biến đổi |
|----------|-----------|-----------|--------------|
| `snapshot_date` | Tong_hop_ton_kho_... | Kỳ (Tháng/Năm) | Lấy ngày cuối tháng |
| `product_code` | Tong_hop_ton_kho_... | Mã hàng | Lookup `dim_product.product_code` |
| `warehouse_code` | Tong_hop_ton_kho_... | Tên kho | Lookup `dim_warehouse.warehouse_code` |
| `ending_quantity` | Tong_hop_ton_kho_... | Tồn cuối kỳ (SL) | `COALESCE(value, 0)` |
| `ending_value` | Tong_hop_ton_kho_... | Tồn cuối kỳ (GT) | `COALESCE(value, 0)` |

---

## BƯỚC 8 — Xác Nhận Lại với BRD (5 Báo Cáo)

> [!IMPORTANT]
> Sau khi thiết kế xong, bạn **BẮT BUỘC** phải kiểm tra từng chỉ tiêu trong BRD và xác nhận data model có đủ cột để tính được không.

### Checklist BC1: Quản trị Hoạt động Tài chính & Tín dụng

| Chỉ tiêu BRD | Bảng cần | Cột/Công thức DAX | Có thể tính? |
|-------------|---------|---------------------|-------------|
| Dư nợ ngắn hạn | `fact_loan` | `SUM(remaining_principal)` filter `loan_type='Ngắn hạn'` | ✅ |
| Dư nợ dài hạn | `fact_loan` | `SUM(remaining_principal)` filter `loan_type='Dài hạn'` | ✅ |
| Hạn mức còn lại | `fact_creditlimitsummary` | `SUM(credit_limit) - SUM(remaining_principal)` | ✅ |
| Hạn mức được cấp / phê duyệt | `fact_creditlimitsummary` | `SUM(credit_limit)`, `SUM(granted_limit)` | ✅ |
| Loan to Value (LTV) | `fact_loan` + `fact_collateral` | `SUM(remaining_principal) / SUM(appraised_value)` | ✅ |
| Lãi suất bình quân từng ngân hàng | `fact_loan` + `dim_bank` | `AVERAGE(interest_rate)` GROUP BY bank | ✅ |
| Dư nợ theo ngân hàng | `fact_loan` + `dim_bank` | `SUM(remaining_principal)` GROUP BY bank | ✅ |
| Cost of Debt so với Kế hoạch | `fact_incomestatement` + `fact_businessplan` | Thực tế vs Target `indicator_code` | ✅ |
| Chi tiết lịch trả gốc | `fact_loan` | `maturity_date`, `remaining_principal` | ✅ |
| Chi tiết TSĐB | `fact_collateral` + `dim_bank` | `appraised_value`, `ltv_coefficient` | ✅ |
| Dự báo thời gian sống tiền mặt | `fact_balancesheet` + `fact_cashflow` | Tiền mặt / Avg chi hàng tháng | ✅ |

### Checklist BC2: Quản trị Hàng Tồn Kho

| Chỉ tiêu BRD | Bảng cần | Cột/Công thức DAX | Có thể tính? |
|-------------|---------|---------------------|-------------|
| Giá trị hàng tồn kho | `fact_inventory_balance` | `SUM(ending_value)` tại `LASTDATE` | ✅ |
| Số lượng hàng tồn kho | `fact_inventory_balance` | `SUM(ending_quantity)` tại `LASTDATE` | ✅ |
| Vòng quay HTK (thực tế) | `fact_incomestatement` + `fact_inventory_balance` | `COGS / AVG(ending_value)` | ✅ |
| Vòng quay HTK (kế hoạch) | `fact_businessplan` | `SUM(target_amount)` filter `indicator_code` | ✅ |
| Inventory-to-Sales ratio | `fact_inventory_balance` + `fact_incomestatement` | `ending_value / revenue` | ✅ |
| Biểu đồ Nhập - Xuất - Tồn | `fact_inventoryinward` + `fact_inventoryoutward` + `fact_inventory_balance` | SUM nhập, SUM xuất, tồn cuối | ✅ |
| Top 10 mặt hàng tồn nhiều nhất | `fact_inventory_balance` + `dim_product` | `TOPN(10, ..., ending_value)` | ✅ |
| Giá trị hàng nhập khẩu | `fact_inventoryinward` | `SUM(credit_amount)` filter nguồn | ✅ |
| Red Flag hàng chậm luân chuyển | `fact_inventory_balance` + `fact_inventoryoutward` | Tính số ngày tồn kho | ✅ |
| Tổng mã sản phẩm | `dim_product` | `DISTINCTCOUNT(product_code)` | ✅ |

### Checklist BC3: Quản trị Phải Thu - Phải Trả

| Chỉ tiêu BRD | Bảng cần | Cột/Công thức DAX | Có thể tính? |
|-------------|---------|---------------------|-------------|
| Giá trị phải thu | `fact_accountsreceivable` | `SUM(ending_credit_balance)` cuối kỳ | ✅ |
| Giá trị phải trả | `fact_accountspayable` | `SUM(ending_credit_balance)` cuối kỳ | ✅ |
| Vòng quay phải thu (thực tế) | `fact_incomestatement` + `fact_accountsreceivable` | `Doanh thu / Phải thu BQ` | ✅ |
| Vòng quay phải thu (kế hoạch) | `fact_businessplan` | `SUM(target_amount)` filter `indicator_code` | ✅ |
| Số khách hàng | `fact_accountsreceivable` + `dim_partner` | `DISTINCTCOUNT(partner_code)` | ✅ |
| Tổng hóa đơn | `fact_accountsreceivable` | `COUNT(_id)` | ✅ |
| Phân tích tuổi nợ (Ageing) | `fact_accountsreceivable` | `GROUP BY aging_bucket` | ✅ |
| Top 10 KH theo số dư | `fact_accountsreceivable` + `dim_partner` | `TOPN(10, ..., ending_credit_balance)` | ✅ |
| Top 10 KH nợ quá hạn | `fact_accountsreceivable` + `dim_partner` | Filter `overdue_days > 0` | ✅ |

### Checklist BC4: Quản trị Tiền Gửi & Thanh Khoản

| Chỉ tiêu BRD | Bảng cần | Cột/Công thức DAX | Có thể tính? |
|-------------|---------|---------------------|-------------|
| Tiền & tương đương tiền | `fact_balancesheet` | `SUM(ending_balance)` filter TK 111+112 | ✅ |
| Tổng tiền gửi (gốc) | `fact_termdeposit` | `SUM(original_amount)` | ✅ |
| Số lượng hợp đồng | `fact_termdeposit` | `COUNT(passbook_no)` | ✅ |
| Lãi suất bình quân | `fact_termdeposit` | `AVERAGE(interest_rate)` | ✅ |
| Thu nhập lãi | `fact_termdeposit` | `SUM(remaining_value - original_amount)` | ✅ |
| Cơ cấu tiền gửi theo Ngân hàng | `fact_termdeposit` + `dim_bank` | Donut `SUM(original_amount)` by `bank_name` | ✅ |
| Cơ cấu tiền gửi theo Kỳ hạn | `fact_termdeposit` | Donut `SUM(original_amount)` by `term` | ✅ |
| Bảng chi tiết tiền gửi | `fact_termdeposit` + `dim_bank` | Số sổ, Ngân hàng, Gốc, Lãi suất, Kỳ hạn, Ngày | ✅ |

### Checklist BC5: Quản trị Dòng Tiền

| Chỉ tiêu BRD | Bảng cần | Cột/Công thức DAX | Có thể tính? |
|-------------|---------|---------------------|-------------|
| Dòng tiền vào | `fact_cashflow` | `SUM(credit_amount)` trong kỳ | ✅ |
| Dòng tiền ra | `fact_cashflow` | `SUM(debit_amount)` trong kỳ | ✅ |
| Số dư tiền mặt | `fact_balancesheet` | `SUM(ending_balance)` TK 111+112 tại `LASTDATE` | ✅ |
| Dự báo thời gian còn sống | `fact_balancesheet` + `fact_cashflow` | Số dư / Avg chi 3 tháng gần nhất | ✅ |
| Biểu đồ Thu/Chi/Dư quỹ | `fact_cashflow` + `fact_balancesheet` | Cột stack Thu+Chi, Đường dư cuối kỳ | ✅ |
| Kế hoạch thu / chi | `fact_cashflow` + `fact_businessplan` | Thực tế vs Target B01/B02 | ✅ |
| Chu kỳ tiền mặt (CCC) | `fact_businessplan` + `fact_incomestatement` + `fact_accountsreceivable` + `fact_inventory_balance` + `fact_accountspayable` | CCC = Ngày HTK + Ngày PT - Ngày PT trả | ✅ |
| Tỉ lệ đóng góp dòng thu/chi | `fact_cashflow` + `dim_account` | Donut breakdown theo loại hoạt động | ✅ |
| Tài sản ngắn hạn / Nợ ngắn hạn | `fact_balancesheet` | TK 1xx vs TK 31x, Vốn lưu động = TSNH - Nợ NH | ✅ |

---

## Sơ Đồ ERD Tổng Thể (Star Schema)

```
                         [Dim_Date] ←─────── (tạo bằng DAX)
                              │
          ┌───────────────────┼────────────────────────┐
          │                   │                        │
          ▼                   ▼                        ▼
   fact_cashflow       fact_balancesheet       fact_businessplan
   fact_loan           fact_incomestatement    fact_termdeposit
   fact_collateral     fact_creditlimitsummary
   fact_accountsreceivable
   fact_accountspayable
   fact_inventory_balance
   fact_inventoryinward
   fact_inventoryoutward

Dim liên kết:
  dim_bank         ─── fact_loan, fact_collateral, fact_creditlimitsummary,
                        fact_termdeposit, fact_cashflow (qua dim_accountnumber)
  dim_partner      ─── fact_accountsreceivable, fact_accountspayable
  dim_product      ─── fact_inventory_balance, fact_inventoryinward, fact_inventoryoutward
  dim_warehouse    ─── fact_inventory_balance, fact_inventoryinward, fact_inventoryoutward
  dim_account      ─── fact_cashflow
  dim_accountnumber─── fact_cashflow (qua account_no → bank)
  dim_reportitem   ─── fact_balancesheet, fact_incomestatement, fact_businessplan
```

**Tổng kết: 7 Dim (+ Dim_Date DAX) + 13 Fact = 20 bảng Silver**

---

## Lộ Trình Thực Hiện (Dành Cho Intern)

### Tuần 1-2: Nền tảng
- [ ] Đọc hiểu toàn bộ BRD 5 báo cáo trong `ISO - BRD_20260806.xlsx`
- [ ] Tìm hiểu PostgreSQL cơ bản: CREATE TABLE, INSERT, SELECT, JOIN
- [ ] Học đọc file Excel bằng Python (`openpyxl`, `pandas`)
- [ ] Setup môi trường: PostgreSQL local + DBeaver (GUI)

### Tuần 3-4: Dimension Tables
- [ ] Tạo schema `silver` trên PostgreSQL
- [ ] Chạy ETL cho 7 Dim: `dim_bank`, `dim_warehouse`, `dim_account`, `dim_accountnumber`, `dim_reportitem`, `dim_partner`, `dim_product`
- [ ] `Dim_Date` tạo bằng DAX trong Power BI (không cần ETL)

### Tuần 5-6: Fact Tables ưu tiên cao (P1)
- [ ] `fact_cashflow` từ Sổ chi tiết TK 111/112
- [ ] `fact_loan` + `fact_collateral` + `fact_creditlimitsummary` từ file tín dụng
- [ ] `fact_balancesheet` + `fact_incomestatement` từ BCTC MISA

### Tuần 7-8: Fact Tables còn lại (P2/P3)
- [ ] `fact_inventory_balance` + `fact_inventoryinward` + `fact_inventoryoutward`
- [ ] `fact_accountsreceivable` + `fact_accountspayable`
- [ ] `fact_termdeposit`
- [ ] `fact_businessplan` (3 sheet kế hoạch)

### Tuần 9+: Kết nối Power BI
- [ ] Kết nối PostgreSQL → Power BI Desktop (Import mode)
- [ ] Tạo `Dim_Date` bằng DAX `CALENDARAUTO()`
- [ ] Tạo Relationship đúng theo bảng Star Schema (Single direction, Dim → Fact)
- [ ] Viết DAX measure cho các chỉ tiêu P1

---

## Những Sai Lầm Phổ Biến Của Người Mới

| Sai lầm | Hậu quả | Cách đúng |
|---------|---------|-----------|
| Lưu tên ngân hàng/đối tác trực tiếp trong Fact | Khó filter, không nhất quán | Dùng FK (`bank_code`, `partner_code`) → JOIN Dim |
| Không tạo `Dim_Date` riêng | Power BI không làm được time intelligence (YTD, MTD...) | Tạo `Dim_Date` bằng DAX `CALENDARAUTO()` |
| SUM tồn kho qua các tháng | Số ảo, sai nghiệp vụ hoàn toàn | Dùng `LASTDATE` hoặc snapshot cuối tháng |
| SUM số dư tài khoản qua các tháng | Cùng sai như tồn kho | Measure semi-additive: `CALCULATE(..., LASTDATE(...))` |
| Dùng `item_code` JOIN `dim_reportitem` | Trùng lặp, kết quả sai | Dùng `item_id` (VD: `B01-DN_110`) |
| Cộng dồn target vòng quay qua nhiều tháng | Sai gấp nhiều lần | ETL đã chia 12, dùng filter theo tháng |
| Không track `_source_file` & `_loaded_at` | Không trace được khi debug lỗi | Luôn có 2 cột metadata này trong mọi bảng |
| Đặt tên cột tiếng Việt hoặc có dấu | PostgreSQL lỗi, team khó đọc | Dùng snake_case tiếng Anh |
| Bỏ qua NULL handling | ETL fail hoặc tính sai | `COALESCE(col, 0)` cho số, `COALESCE(col, 'Unknown')` cho text |
| Không validate với MISA | Báo cáo sai mà không biết | Đối chiếu tổng số với báo cáo gốc MISA sau mỗi load |

---

## Tài Liệu Tham Khảo Trong Dự Án

- [BRD chi tiết](file:///D:/Công việc/1. Dự án Gỗ Minh Long/2. Tài liệu phân tích và thiết kế/02. BRD & Template/ISO - BRD_20260806.xlsx) — `ISO - BRD_20260806.xlsx`
- [Template báo cáo](file:///D:/Công việc/1. Dự án Gỗ Minh Long/2. Tài liệu phân tích và thiết kế/02. BRD & Template/TEMPLATE_ML.xlsx) — `TEMPLATE_ML.xlsx`
- [PowerBI Development Guide](file:///D:/Công việc/1. Dự án Gỗ Minh Long/2. Tài liệu phân tích và thiết kế/powerbi_development_guide.md) — Mapping visual từng báo cáo
- [ETL README](file:///D:/Công việc/1. Dự án Gỗ Minh Long/3. Phát triển ETL dữ liệu/01. ETL/README.md) — Hướng dẫn chạy pipeline ETL
- [Quy định mã NVL](file:///D:/Công việc/1. Dự án Gỗ Minh Long/1. Giới thiệu và khảo sát dự án/2. Quy ước đặt tên sản phẩm/BH02-QD01 Quy định đặt mã code sản phẩm cho NVL 2024.docx) — `BH02-QD01`
- [Quy định mã Thành phẩm](file:///D:/Công việc/1. Dự án Gỗ Minh Long/1. Giới thiệu và khảo sát dự án/2. Quy ước đặt tên sản phẩm/BH02-QD02 Quy định đặt mã code sản phẩm cho thành phẩm 2024.docx) — `BH02-QD02`
