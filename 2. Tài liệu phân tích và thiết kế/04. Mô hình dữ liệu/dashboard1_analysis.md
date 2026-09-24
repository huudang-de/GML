# 📊 PHÂN TÍCH STAR SCHEMA — DASHBOARD 1
## "Quản Trị Hoạt Động Tài Chính"
**Nguồn gốc: Đọc trực tiếp từ `ISO - BRD_Excel.xlsx` → Sheet "BRD_Quản trị Hoạt động Tài chính"**

---

> [!IMPORTANT]
> **Đây là phân tích từ BRD gốc, KHÔNG phải suy diễn.** Mọi cột, mọi công thức, mọi nguồn file đều trích nguyên văn từ BRD thực tế.

---

## 📄 Bước 0 — Đọc Nguyên Liệu Thô

### Mục đích báo cáo (Mục 1)
> *"Quan sát và phân tích các thông tin hạn mức và tín dụng của Minh Long, ngày trả lãi, quản trị dư nợ"*
> — **Tần suất:** Hàng tuần (thường xem thứ 7, lấy số liệu đến hết thứ 6)

### Nguồn dữ liệu thô (File gốc)

| STT | Nguồn | Chi tiết |
|:---:|:---|:---|
| 1 | **MISA** | Sổ chi tiết các TK / Báo cáo CĐKT (B01_DN) / KQKD (B02_DN) |
| 2 | **Excel** | Sheet `Tổng hợp` — file `MINHLONG_BC_TINDUNG_2026_FIX` |
| 3 | **Excel** | Sheet `Theo dõi vay NH` — file `MINHLONG_BC_TINDUNG_2026_FIX` |
| 4 | **Excel** | Sheet `KQKD_PA1` — file `Kế hoạch kinh doanh Minh Long 2026` |

---

### 8.1 Điều kiện ràng buộc xuyên suốt (quan trọng!)

| Điều kiện | Mô tả |
|:---|:---|
| **ĐK1 — Xử lý dữ liệu "Số dư"** | Chỉ tiêu mang tính Thời điểm (Dư nợ, Hạn mức còn lại...) → luôn lấy **ngày cuối cùng có phát sinh** của kỳ. Tuyệt đối **KHÔNG** cộng dồn qua tháng/năm |
| **ĐK2 — Xử lý dữ liệu "Phát sinh"** | Chỉ tiêu mang tính Thời kỳ (Doanh thu, Chi phí lãi vay, Dòng tiền...) → **tổng cộng dồn** toàn bộ phát sinh trong khoảng thời gian đang chọn |
| **ĐK3 — Tính hợp lệ chứng từ** | Chỉ lấy bút toán/chứng từ có trạng thái **"Đã ghi sổ"** từ MISA. Bỏ qua: nháp, chờ duyệt, đã bị hủy |

> [!NOTE]
> **Tại sao ĐK1 & ĐK2 quan trọng với Star Schema?**
> Đây chính là lý do tại sao ta cần **2 loại bảng FACT khác nhau**:
> - ĐK1 → `fact_*` kiểu **Snapshot** (1 dòng = 1 thời điểm chụp)
> - ĐK2 → `fact_*` kiểu **Flow/Transaction** (1 dòng = 1 phát sinh, cộng dồn được)

---

### 8.2 Filter — 3 bộ lọc

| STT | Bộ lọc | Mô tả gốc từ BRD | Giá trị mẫu | Loại |
|:---:|:---|:---|:---|:---|
| 1 | **Thời gian** | Year - Month - Week, mặc định 2026 | YYYY - MM - WW | Dropdown |
| 2 | **Tài khoản thu** | Filter **số tài khoản ngân hàng** (không phải TK kế toán) | 0141100123005, 114000046412... | Dropdown |
| 3 | **Tài khoản chi** | Filter **số tài khoản ngân hàng** | 0141100123005, 114000046412... | Dropdown |

---

### 8.3 Chi tiết — 8 Card + 10 Biểu đồ

#### 🟦 Phần 1: 8 Chỉ số tổng quan (Cards)

| Mã | Tên chỉ tiêu | Cách tính GỐC trong BRD | Nguồn file gốc | Loại |
|:---|:---|:---|:---|:---|
| 1.1 | **Dư nợ ngắn hạn** | Tổng cột "Dư có" trong Sổ chi tiết TK tại MISA → lọc TK 34111, 34113, 34114 | MISA — Sổ chi tiết TK 341 | Snapshot |
| 1.2 | **Dư nợ dài hạn** | Tổng cột "Dư có" trong Sổ chi tiết TK → TK vay dài hạn (341) | MISA — Sổ chi tiết TK 341 | Snapshot |
| 1.3 | **Hạn mức còn lại** | = Tổng hạn mức tín dụng − Số dư hạn mức đã sử dụng; hoặc lấy trực tiếp cột "Hạn mức đã sử dụng" | File `bc_tin_dung_2026.xlsx` | Snapshot |
| 1.4 | **Dự báo thời gian sống tiền mặt (Ngày)** | = Tổng tiền hiện có (Mã B01-DN_110 = TK111+TK112) ÷ Chi bình quân mỗi ngày (= Tổng chi / 30 ngày) | MISA — B01_DN (Mã 110) + Sổ chi tiết TK 111/112 | Derived |
| 1.5 | **Hạn mức được cấp** | Số tiền DN thực sự làm hồ sơ xin mở hạn mức, dựa trên TSĐB | File `Báo cáo tín dụng` (nội bộ) | Snapshot |
| 1.6 | **Hạn mức được phê duyệt** | Con số TỐI ĐA ngân hàng đồng ý cho vay trong năm | File `Báo cáo tín dụng` (nội bộ) | Snapshot |
| 1.7 | **Loan to Value (LTV)** | = Tổng "Dư nợ gốc vay đến hiện tại" ÷ Tổng "Giá trị định giá TSĐB" | File `bc_tin_dung_2026.xlsx` | Derived |
| 1.8 | **Tỷ lệ Nợ / Vốn (D/E)** | = Tổng Nợ phải trả (Mã 300) ÷ Vốn chủ sở hữu (Mã 400) | MISA — B01_DN (CĐKT) | Derived |

---

#### 🟧 Phần 2: 10 Biểu đồ chi tiết

**7 Charts:**

| Mã | Tên biểu đồ | Loại Chart | Nguồn file gốc / Cột gốc | Chiều phân tích |
|:---|:---|:---|:---|:---|
| 2.1 | **Nợ NH / Nợ DH / Tổng dư nợ theo Tháng** | Line & Stacked Column | MISA — Sổ chi tiết TK 341: cột "Dư có" các khoản "vay ngắn hạn" / "vay dài hạn" | Theo tháng |
| 2.2 | **Chi phí nợ (Tháng) — TT vs KH** | Line Chart | B02_DN (MISA): cột "Phát sinh" chỉ tiêu Chi phí lãi vay + `Ke_hoach_kinh_doanh` | Theo tháng |
| 2.3 | **Lãi suất bình quân theo ngân hàng** | Bar Chart | `bc_tin_dung_2026.xlsx`: AVERAGE cột "Lãi xuất" GROUP BY "Tổ chức tín dụng" | Theo NH |
| 2.4 | **Dư nợ tại từng ngân hàng** | Bar Chart | `bc_tin_dung_2026.xlsx`: SUM cột "Dư nợ gốc vay đến hiện tại" GROUP BY "Tổ chức tín dụng" | Theo NH |
| 2.5 | **Chi phí lãi vay TT và KH** | Combo Chart | B02_DN (MISA): chi phí lãi vay phát sinh ÷ Kế hoạch / 12 tháng | Theo tháng |
| 2.6 | **Phân tích dòng thu theo ngân hàng** | Bar Chart | `So_chi_tiet_cac_tai_khoan.xlsx`: SUM "Phát sinh Nợ" TK 112 GROUP BY Tên ngân hàng | Theo NH |
| 2.7 | **Phân tích dòng chi theo ngân hàng** | Bar Chart | `So_chi_tiet_cac_tai_khoan.xlsx`: SUM "Phát sinh Có" TK 112 GROUP BY Tên ngân hàng | Theo NH |

**3 Tables/Matrix:**

| Mã | Tên | Loại | Nguồn file gốc | Các cột hiển thị |
|:---|:---|:---|:---|:---|
| 2.8 | **Bảng tổng hợp chỉ số tài chính (Vòng quay nợ vay)** | Table | B02_DN (MISA) + `bc_tin_dung_2026.xlsx` + B01_DN | Kỳ báo cáo · GVHB · Dư nợ BQ · Vòng quay · Số ngày · D/E |
| 2.9 | **Chi tiết tài sản đảm bảo** | Table (6 cột) | `bc_tin_dung_2026.xlsx` → Sheet `TSBD Bank` | 2.9.1 Loại TS · 2.9.2 Giá trị thẩm định · 2.9.3 Hệ số TSĐB · 2.9.4 Giá trị cho vay · 2.9.5 Số tiền được vay · 2.9.6 Mã NH |
| 2.10 | **Lịch trả gốc ngân hàng** | Matrix | `bc_tin_dung_2026.xlsx` → Sheet `KE HOACH TRA NO TUAN` | Bank (Rows) · Ngày phát sinh (Cols, tự động giãn) · Số tiền (Values) |

---

## 🟡 BƯỚC 1 — Bóc tách DIMENSION

*Câu hỏi dẫn đường: "Sếp CẮT / LỌC dữ liệu theo chiều nào?"*

### Phân tích từng nguồn DIM

| Tín hiệu trong BRD | Câu hỏi tư duy | → Bảng DIM | PK | Các Attribute |
|:---|:---|:---|:---|:---|
| **Filter 8.2.1 — Thời gian** (Year, Month, Week) | Cắt theo thời gian? → Cần bảng lịch | `dim_date` | `date_key` | `year`, `quarter`, `month`, `week_of_year` |
| **Filter 8.2.2 / 8.2.3 — Tài khoản thu / Tài khoản chi** (số TK NH: 0141100123005...) | "Thu" và "Chi" đều là **số TK ngân hàng thực tế** → cùng 1 thực thể, 1 bảng | `dim_bank_account` | `account_number` | `bank_code` (FK→dim_bank), `account_name`, `account_type` (`THU`/`CHI`/`BOTH`) |
| **Biểu đồ 2.3, 2.4 GROUP BY "Tổ chức tín dụng"**; **2.6, 2.7 GROUP BY "Tên ngân hàng"** | Cắt theo ngân hàng → Ngân hàng là thực thể riêng, là **cha** của TK NH | `dim_bank` | `bank_code` | `bank_name`, `bank_short_name` |
| **Bảng 2.9 — Loại TS** (BĐS, Máy móc, Hàng hóa...) | Chỉ có vài giá trị cố định → **attribute** trong `fact_collateral`, không cần DIM riêng | *(thuộc tính FACT)* | — | `collateral_type` trong fact |

> [!TIP]
> **Insight quan trọng: `dim_bank` KHÔNG xuất hiện trong phần 8.2 Filter, nhưng BẮT BUỘC phải có** vì biểu đồ 2.3, 2.4, 2.6, 2.7 đều GROUP BY ngân hàng. Kỹ năng đọc BRD: filter ẩn trong phần "Biểu đồ chi tiết", không chỉ nằm ở mục "8.2 Filter".

✅ **Kết quả Bước 1 — 3 bảng DIM:**

```
dim_date          → 🆕 Tạo mới (filter Thời gian)
dim_bank_account  → 🆕 Tạo mới (filter Tài khoản thu / Tài khoản chi)
dim_bank          → 🆕 Tạo mới (chiều phân tích ẩn trong các biểu đồ nhóm theo NH)
```

---

## 🔴 BƯỚC 2 — Nhặt MEASURE (Bóc tách FACT)

*Câu hỏi dẫn đường: "Con số nào cần tính? Nó từ file nguồn nào? Loại gì (Snapshot hay Flow)?"*

### Phân tích từng nhóm measure theo file nguồn

---

#### Nhóm A — Từ MISA Sổ chi tiết TK 341 (Vay và nợ tài chính)
→ Cho card 1.1, 1.2 và biểu đồ 2.1

| Measure | Cột gốc trong file | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Dư nợ ngắn hạn | "Dư có" TK 34111, 34113, 34114 | **Snapshot** | `fact_loan` | `remaining_principal` |
| Dư nợ dài hạn | "Dư có" TK 341 (dài hạn) | **Snapshot** | `fact_loan` | `remaining_principal` |
| Phân loại NH/DH | Mã TK (34111... vs dài hạn) | Attribute | `fact_loan` | `term_type` (`Ngắn hạn` / `Dài hạn`) |

> **Grain của `fact_loan`:** *1 dòng = Dư nợ của 1 khoản vay (1 mã TK chi tiết), tại 1 ngân hàng, tại 1 thời điểm*

---

#### Nhóm B — Từ file `bc_tin_dung_2026.xlsx` (Báo cáo tín dụng nội bộ)

| Measure | Sheet gốc | Cột gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|:---|
| Dư nợ gốc vay đến hiện tại | `Tổng hợp` / `Theo dõi vay NH` | "Dư nợ gốc vay đến hiện tại" | **Snapshot** | `fact_loan` | `remaining_principal` |
| Lãi suất (%) | `Theo dõi vay NH` | "Lãi xuất" | Attribute | `fact_loan` | `interest_rate` |
| Hạn mức đã sử dụng | `Tổng hợp` | "Hạn mức đã sử dụng" | **Snapshot** | `fact_creditlimitsummary` | `used_limit` |
| Hạn mức được cấp | `Tổng hợp` | "Hạn mức được cấp" | **Snapshot** | `fact_creditlimitsummary` | `credit_limit` |
| Hạn mức được phê duyệt | `Tổng hợp` | — | **Snapshot** | `fact_creditlimitsummary` | `granted_limit` |
| Dư nợ đầu kỳ (để tính BQ) | `Theo dõi vay NH` | — | **Snapshot** | `fact_loan` | *(2 time points)* |
| Giá trị định giá TSĐB | `TSBD Bank` | "Giá trị thẩm định (VND)" | **Snapshot** | `fact_collateral` | `appraised_value` |
| Hệ số TSĐB | `TSBD Bank` | "Hệ số TSBD" | Attribute | `fact_collateral` | `collateral_coefficient` |
| Giá trị cho vay | `TSBD Bank` | "Giá trị cho vay (VND)" | Calculated | `fact_collateral` | `loan_value` |
| Số tiền được vay | `TSBD Bank` | "Số tiền được vay" | **Snapshot** | `fact_collateral` | `max_loan_amount` |
| Tên tài sản | `TSBD Bank` | "Tên tài sản" | Attribute | `fact_collateral` | `asset_name` |
| Địa chỉ TS | `TSBD Bank` | "Địa chỉ" | Attribute | `fact_collateral` | `asset_address` |
| Chủ sở hữu | `TSBD Bank` | "Chủ sở hữu" | Attribute | `fact_collateral` | `owner_name` |
| Loại TS | `TSBD Bank` | "Loại TS" | Attribute | `fact_collateral` | `collateral_type` |
| Đơn giá | `TSBD Bank` | "Đơn giá" | Attribute | `fact_collateral` | `unit_price` |
| Ngày mở sổ | `TSBD Bank` | "Ngày mở sổ" | Date | `fact_collateral` | `pledge_start_date` |
| Kỳ hạn thế chấp | `TSBD Bank` | "Kỳ hạn" | Attribute | `fact_collateral` | `pledge_term` |
| Lịch trả gốc: Bank | `KE HOACH TRA NO TUAN` | "Bank" | → Link về dim_bank | `fact_loan_schedule` | `bank_code` (FK) |
| Lịch trả gốc: Ngày đến hạn | `KE HOACH TRA NO TUAN` | Các cột ngày trên header | Date | `fact_loan_schedule` | `due_date` |
| Lịch trả gốc: Số tiền | `KE HOACH TRA NO TUAN` | Giá trị trong bảng | **Flow/Schedule** | `fact_loan_schedule` | `payment_amount` |

> [!NOTE]
> **Tại sao tách `fact_loan_schedule` riêng?**
> Vì `fact_loan` có grain "dư nợ tại 1 thời điểm" (Snapshot), còn `fact_loan_schedule` có grain "số tiền cần trả vào 1 ngày cụ thể" (Schedule). Grain khác nhau → bảng khác nhau.

---

#### Nhóm C — Từ MISA B01_DN (Bảng Cân đối Kế toán)
→ Cho card 1.4 (Mã 110), card 1.8 (Mã 300, 400), bảng 2.8.6

| Measure | Mã chỉ tiêu | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Tổng tiền và tương đương tiền | Mã 110 (= TK111 + TK112) | **Snapshot** | `fact_balancesheet` | `ending_balance` WHERE `item_code='110'` |
| Tổng nợ phải trả | Mã 300 | **Snapshot** | `fact_balancesheet` | `ending_balance` WHERE `item_code='300'` |
| Vốn chủ sở hữu | Mã 400 | **Snapshot** | `fact_balancesheet` | `ending_balance` WHERE `item_code='400'` |

---

#### Nhóm D — Từ MISA B02_DN (Báo cáo KQKD)
→ Cho biểu đồ 2.2, 2.5, bảng 2.8.2

| Measure | Chỉ tiêu | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Chi phí lãi vay thực tế (kỳ này) | "Phát sinh" Chi phí lãi vay | **Flow** | `fact_incomestatement` | `current_period_amount` WHERE item = 'Chi phí lãi vay' |
| Giá vốn hàng bán (GVHB) | Dòng GVHB trong B02 | **Flow** | `fact_incomestatement` | `current_period_amount` WHERE item = 'GVHB' |

---

#### Nhóm E — Từ MISA Sổ chi tiết TK 112 (Tiền gửi NH)
→ Cho biểu đồ 2.6, 2.7 và card 1.4

| Measure | Cột gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Dòng thu theo NH (Phát sinh Nợ TK112) | "Phát sinh Nợ" TK 112 GROUP BY Tên NH | **Flow** | `fact_cashflow` | `debit_amount` |
| Dòng chi theo NH (Phát sinh Có TK112) | "Phát sinh Có" TK 112 GROUP BY Tên NH | **Flow** | `fact_cashflow` | `credit_amount` |

---

#### Nhóm F — Từ file Kế hoạch kinh doanh
→ Cho biểu đồ 2.2, 2.5

| Measure | Sheet gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Chi phí lãi vay kế hoạch | `KQKD_PA1` — dòng "Chi phí lãi vay" | **Plan** | `fact_businessplan` | `plan_value` WHERE item = 'Chi phí lãi vay' |

---

✅ **Kết quả Bước 2 — 7 bảng FACT:**

| Bảng FACT | Trạng thái | Loại chính | Cột chính được suy ra |
|:---|:---|:---|:---|
| `fact_loan` | 🆕 Tạo mới | Snapshot | `remaining_principal`, `term_type`, `interest_rate`, `disbursement_date`, `maturity_date` |
| `fact_loan_schedule` | 🆕 Tạo mới | Schedule | `due_date`, `payment_amount` |
| `fact_creditlimitsummary` | 🆕 Tạo mới | Snapshot | `credit_limit`, `granted_limit`, `used_limit` |
| `fact_collateral` | 🆕 Tạo mới | Snapshot/Static | `appraised_value`, `collateral_coefficient`, `loan_value`, `max_loan_amount`, + 6 attribute cột |
| `fact_cashflow` | 🆕 Tạo mới | Flow | `debit_amount`, `credit_amount` |
| `fact_balancesheet` | 🆕 Tạo mới | Snapshot | `ending_balance`, `item_code` |
| `fact_incomestatement` | 🆕 Tạo mới | Flow | `current_period_amount`, `item_code` |
| `fact_businessplan` | 🆕 Tạo mới | Plan | `plan_value`, `item_code` |

---

## 🔗 BƯỚC 3 — Lắp ráp

### Grain Statement (Định nghĩa hạt nhân dữ liệu)

| Bảng FACT | Grain | Ví dụ 1 dòng |
|:---|:---|:---|
| `fact_loan` | 1 khoản vay × 1 ngân hàng × 1 thời điểm chụp | TK 34111 tại VCB, dư nợ ngày 30/08/2026 = 5 tỷ |
| `fact_loan_schedule` | 1 ngân hàng × 1 ngày đến hạn | VCB phải trả 200tr ngày 23/03/2026 |
| `fact_creditlimitsummary` | 1 ngân hàng × 1 thời điểm | VCB: hạn mức cấp 50 tỷ, đã dùng 30 tỷ (ngày 30/08/2026) |
| `fact_collateral` | 1 tài sản đảm bảo | TSĐB "Nhà đất 123 Lê Lợi" thế chấp tại VCB |
| `fact_cashflow` | 1 giao dịch × 1 TK ngân hàng × 1 ngày | TK 0141100123005 (VCB) nhận vào 500tr ngày 15/08/2026 |
| `fact_balancesheet` | 1 mã chỉ tiêu CĐKT × 1 thời điểm cuối kỳ | Mã 110 = 8 tỷ, chốt ngày 31/08/2026 |
| `fact_incomestatement` | 1 chỉ tiêu KQKD × 1 kỳ | GVHB tháng 8/2026 = 12 tỷ |
| `fact_businessplan` | 1 chỉ tiêu kế hoạch × 1 kỳ | KH Chi phí lãi vay năm 2026 = 2.4 tỷ |

---

### Sơ đồ lắp ráp — Star Schema Dashboard 1

```
                            [dim_date]
                            🔑 date_key
        ┌───────────┬────────┴──────┬────────────────┬──────────────────┐
        ▼           ▼               ▼                ▼                  ▼
  fact_loan  fact_cashflow  fact_balancesheet  fact_incomestatement  fact_businessplan
  fact_loan_schedule                           
  fact_creditlimitsummary

[dim_bank]
🔑 bank_code
        ├──→ fact_loan               (dư nợ từng NH)
        ├──→ fact_loan_schedule      (lịch trả gốc từng NH)
        ├──→ fact_creditlimitsummary (hạn mức từng NH)
        ├──→ fact_collateral         (TSĐB thế chấp tại NH)
        └──→ fact_cashflow           (qua dim_bank_account)

[dim_bank_account]
🔑 account_number
  bank_code (FK) ──→ dim_bank
        └──→ fact_cashflow           (filter Tài khoản thu / chi)
```

---

### Sơ đồ chi tiết từng bảng FACT

```
fact_loan (Trung tâm — dư nợ vay)
─────────────────────────────────────────
date_key         (FK) ──→ dim_date
bank_code        (FK) ──→ dim_bank
loan_account_no       ── Mã TK vay (34111, 34113...) — degenerate dim
─────────────────────────────────────────
remaining_principal     [Snapshot] Dư nợ gốc còn lại
term_type               [Attr]     Ngắn hạn / Dài hạn
interest_rate           [Attr]     Lãi suất (%)
disbursement_date       [Date]     Ngày giải ngân
maturity_date           [Date]     Ngày đáo hạn
```

```
fact_loan_schedule (Lịch trả gốc)
─────────────────────────────────────────
bank_code    (FK) ──→ dim_bank
due_date          ── Ngày đến hạn (từ header cột trong bc_tin_dung)
─────────────────────────────────────────
payment_amount    [Schedule] Số tiền gốc/lãi phải trả trong ngày đó
```

```
fact_creditlimitsummary (Hạn mức tín dụng)
─────────────────────────────────────────
date_key    (FK) ──→ dim_date
bank_code   (FK) ──→ dim_bank
─────────────────────────────────────────
credit_limit    [Snapshot] Hạn mức thực tế được dùng
granted_limit   [Snapshot] Hạn mức phê duyệt tối đa
used_limit      [Snapshot] Hạn mức đã sử dụng
```

```
fact_collateral (Tài sản đảm bảo)
─────────────────────────────────────────
bank_code          (FK) ──→ dim_bank
collateral_id           ── Mã TSĐB (STT trong TSBD Bank)
─────────────────────────────────────────
asset_name              [Text]    Tên tài sản
asset_address           [Text]    Địa chỉ
owner_name              [Text]    Chủ sở hữu
collateral_type         [Attr]    BĐS / Máy móc / Hàng hóa...
appraised_value         [Snapshot] Giá trị thẩm định (VND)
collateral_coefficient  [Attr]    Hệ số LTV tối đa (%)
loan_value              [Calc]    = appraised_value × coeff
max_loan_amount         [Snapshot] Số tiền thực tế được vay
unit_price              [Attr]    Đơn giá quy đổi
pledge_start_date       [Date]    Ngày mở sổ thế chấp
pledge_term             [Attr]    Kỳ hạn thế chấp
```

```
fact_cashflow (Giao dịch thu/chi)
─────────────────────────────────────────
date_key       (FK) ──→ dim_date
account_number (FK) ──→ dim_bank_account  (Tài khoản thu / chi)
─────────────────────────────────────────
debit_amount   [Flow] Phát sinh Nợ TK112 — tiền vào
credit_amount  [Flow] Phát sinh Có TK112 — tiền ra
```

```
fact_balancesheet (Cân đối kế toán — BCTC)
─────────────────────────────────────────
date_key   (FK) ──→ dim_date
item_code       ── Mã chỉ tiêu CĐKT (110, 300, 400)
─────────────────────────────────────────
ending_balance  [Snapshot] Giá trị chốt cuối kỳ
```

```
fact_incomestatement (KQKD — BCTC)
─────────────────────────────────────────
date_key             (FK) ──→ dim_date
item_code                 ── Mã chỉ tiêu KQKD (GVHB, Lãi vay...)
─────────────────────────────────────────
current_period_amount [Flow] Giá trị phát sinh trong kỳ
```

```
fact_businessplan (Kế hoạch kinh doanh)
─────────────────────────────────────────
date_key   (FK) ──→ dim_date
item_code       ── Mã chỉ tiêu KH (Chi phí lãi vay...)
─────────────────────────────────────────
plan_value  [Plan] Giá trị kế hoạch
```

---

## ✅ Tổng kết Dashboard 1 — Bảng kiểm đối chiếu BRD

| Chỉ tiêu BRD | → Bảng FACT | Cột | Kiểu |
|:---|:---|:---|:---|
| Card 1.1 Dư nợ NH | `fact_loan` | `remaining_principal` + `term_type='NH'` | Snapshot |
| Card 1.2 Dư nợ DH | `fact_loan` | `remaining_principal` + `term_type='DH'` | Snapshot |
| Card 1.3 Hạn mức còn lại | `fact_creditlimitsummary` | `credit_limit - used_limit` | Derived |
| Card 1.4 Thời gian sống tiền mặt | `fact_balancesheet`(Mã110) + `fact_cashflow`(credit) | `ending_balance`, `credit_amount` | Derived |
| Card 1.5 Hạn mức được cấp | `fact_creditlimitsummary` | `credit_limit` | Snapshot |
| Card 1.6 Hạn mức phê duyệt | `fact_creditlimitsummary` | `granted_limit` | Snapshot |
| Card 1.7 LTV | `fact_loan`+`fact_collateral` | `remaining_principal/appraised_value` | Derived |
| Card 1.8 D/E | `fact_balancesheet` | `ending_balance` Mã300/Mã400 | Derived |
| Chart 2.1 Dư nợ theo tháng | `fact_loan` | `remaining_principal` × `term_type` × `date` | Snapshot |
| Chart 2.2 Chi phí nợ TT vs KH | `fact_incomestatement` + `fact_businessplan` | `current_period_amount`, `plan_value` | Flow vs Plan |
| Chart 2.3 Lãi suất theo NH | `fact_loan` | AVG `interest_rate` GROUP BY `bank_code` | Attr |
| Chart 2.4 Dư nợ theo NH | `fact_loan` | SUM `remaining_principal` GROUP BY `bank_code` | Snapshot |
| Chart 2.5 CP lãi vay TT/KH | `fact_incomestatement` + `fact_businessplan` | — | Flow vs Plan |
| Chart 2.6 Dòng thu theo NH | `fact_cashflow` | SUM `debit_amount` GROUP BY bank | Flow |
| Chart 2.7 Dòng chi theo NH | `fact_cashflow` | SUM `credit_amount` GROUP BY bank | Flow |
| Table 2.8 Vòng quay nợ | `fact_incomestatement`+`fact_loan`+`fact_balancesheet` | GVHB, `remaining_principal`, Mã300/400 | Derived |
| Table 2.9 TSĐB (12 cột) | `fact_collateral` | tất cả attribute | Static |
| Matrix 2.10 Lịch trả gốc | `fact_loan_schedule` | `due_date`, `payment_amount` | Schedule |

---

> [!WARNING]
> **2 điểm khác biệt lớn so với guide cũ `star_schema_guide.md`:**
> 1. **`fact_loan_schedule` là bảng FACT mới** — guide cũ không có, nhưng BRD thực tế có hẳn mục 2.10 (Matrix lịch trả gốc theo tuần từ sheet `KE HOACH TRA NO TUAN`) → grain khác hoàn toàn với `fact_loan` → phải tách ra.
> 2. **`fact_collateral` có tới 11 cột attribute** từ sheet `TSBD Bank` — guide cũ chỉ liệt kê 4 cột. Bảng này gần như là bảng dimension tĩnh (không có date_key) hơn là bảng fact thuần túy.

---
*Làm tiếp Dashboard 2 (Quản trị Hàng tồn kho), 3 (Phải thu/Phải trả), 4 (Dòng tiền), 5 (Tiền gửi & Thanh khoản) → sau đó ghép lại thành Star Schema hoàn chỉnh.*
