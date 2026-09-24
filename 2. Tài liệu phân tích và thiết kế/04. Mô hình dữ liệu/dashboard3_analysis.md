# 📊 PHÂN TÍCH STAR SCHEMA — DASHBOARD 3
## "Quản Trị Phải Thu — Phải Trả"
**Nguồn: `ISO - BRD_Excel.xlsx` → Sheet 4 "BRD_Quản trị phải thu-phải trả"**

---

## 📄 Bước 0 — Đọc Nguyên Liệu Thô

### Nguồn dữ liệu thô

| STT | Nguồn | Chi tiết |
|:---:|:---|:---|
| 1 | **MISA** | `Chi_tiet_cong_no_phai_thu_khach_hang.xlsx` — TK 131: phát sinh nợ (mua nợ), phát sinh có (trả tiền), dư nợ cuối kỳ chi tiết đến từng KH & từng hóa đơn |
| 2 | **MISA** | `Chi_tiet_cong_no_phai_tra_nha_cung_cap.xlsx` — TK 331: phát sinh có (mua nợ NCC), phát sinh nợ (trả tiền NCC), dư phải trả cuối kỳ chi tiết đến từng NCC & hóa đơn |
| 3 | **MISA** | `B02_DN` — Doanh thu thuần và GVHB để tính Vòng quay phải thu/phải trả |

---

### 8.1 Điều kiện ràng buộc

| ĐK | Mô tả |
|:---|:---|
| **ĐK1 — Snapshot (Số dư công nợ)** | Dư nợ phải thu / Dư phải trả → dùng **LASTDATE**, tuyệt đối **không cộng dồn** qua tháng |
| **ĐK2 — Flow (Phát sinh)** | "Phát sinh mua nợ", "Phát sinh trả tiền" → **được cộng dồn** trong kỳ |
| **ĐK3 — Logic Tuổi nợ (Aging)** | Tuổi nợ = Ngày báo cáo − Ngày lập hóa đơn. Phân vào **7 bucket**: Trong hạn, 1-30, 31-60, 61-90, 91-120, 121-150, 151-180, >180 ngày |
| **ĐK4 — Cảnh báo rủi ro cao** | Công nợ rơi vào nhóm **Quá hạn > 90 ngày** → tự động bôi đỏ trên tất cả bảng chi tiết hóa đơn & khách hàng |

---

### 8.2 Filter — 1 bộ lọc chính

| STT | Bộ lọc | Mô tả | Ghi chú quan trọng |
|:---:|:---|:---|:---|
| 1 | **Thời gian** | Chốt số dư công nợ tại thời điểm quá khứ hoặc hiện tại | Filter thời gian tác động làm **"biến thiên"** Tuổi nợ — xem lại 3 tháng trước thì hóa đơn chưa bị coi là quá hạn |

---

### 8.3 Chi tiết — 6 Card + 7 Biểu đồ/Bảng

#### 🟦 Phần 1: 6 Chỉ số tổng quan

| Mã | Tên | Cách tính / Nguồn | File gốc | Loại |
|:---|:---|:---|:---|:---|
| 1.1 | **Giá trị phải thu** | LASTDATE(Dư Nợ TK131) — tổng dư nợ cuối kỳ KH đang chiếm dụng | `Chi_tiet_cong_no_phai_thu` | Snapshot |
| 1.2 | **Vòng quay phải thu hiện tại** | DT thuần trong kỳ / [(PT đầu kỳ + PT cuối kỳ) / 2] | B02_DN + `Chi_tiet_cong_no_phai_thu` | Derived |
| 1.3 | **Số lượng khách hàng** | COUNT DISTINCT(Mã KH) có dư nợ > 0 | `Chi_tiet_cong_no_phai_thu` | Derived |
| 1.4 | **Giá trị phải trả** | LASTDATE(Dư Có TK331) — tổng nợ công ty đang chiếm dụng vốn NCC | `Chi_tiet_cong_no_phai_tra` | Snapshot |
| 1.5 | **Vòng quay phải thu theo năm** | [VQ PT hiện tại] × (365 / Số ngày kỳ BC) | Derived | Derived |
| 1.6 | **Tổng số hóa đơn** | COUNT DISTINCT(Số hóa đơn) có dư nợ còn lại | `Chi_tiet_cong_no_phai_thu` | Derived |

---

#### 🟧 Phần 2: 7 Biểu đồ/Bảng chi tiết

| Mã | Tên | Loại | Nguồn / Cột gốc |
|:---|:---|:---|:---|
| 2.1 | **Khoản phải thu theo tháng** | Stacked Column & Line Chart | Dư Nợ TK131 LASTDATE mỗi tháng |
| 2.2 | **Vòng quay phải thu theo tháng** | Area Chart | DT thuần B02_DN + Dư PT |
| 2.3 | **Biểu đồ Tuổi nợ (Aging)** | Stacked Column Chart | Phân vào 7 bucket, highlight đỏ > 90 ngày |
| 2.4 | **Top 10 KH theo tổng số dư** | Horizontal Bar Chart | SUM dư nợ GROUP BY KH, TOP 10 |
| 2.5 | **Top 10 KH theo nợ quá hạn** | Horizontal Bar Chart | SUM dư nợ quá hạn (ngày > 0) GROUP BY KH, TOP 10 |
| 2.6 | **Bảng chi tiết nợ theo Khách hàng** | Table | Mã KH, Tên KH, Tổng dư nợ, Trong hạn, Quá hạn, Tỷ lệ nợ xấu |
| 2.7 | **Bảng chi tiết các hóa đơn đang nợ** | Table | Tên KH, Số HD, Ngày HD, Trị giá HD, Đã trả, Dư nợ, Trạng thái, Tuổi nợ (bôi đỏ > 90 ngày) |

---

## 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Tín hiệu trong BRD | Câu hỏi tư duy | → Bảng DIM | PK | Attribute |
|:---|:---|:---|:---|:---|
| **Filter Thời gian** | → tái sử dụng | `dim_date` | `date_key` | *(tái sử dụng)* |
| Card 1.3 COUNT KH, biểu đồ 2.4/2.5 GROUP BY KH, bảng 2.6/2.7 phân tích theo KH & NCC | "KH và NCC đều là Đối tác kinh doanh" → cùng 1 thực thể | `dim_partner` | `partner_code` | `partner_name`, `address`, `tax_code`, `partner_group` ('KH'/'NCC'/'Cả hai') |

✅ **Kết quả Bước 1:**
```
dim_date    → ♻️ Tái sử dụng
dim_partner → 🆕 Tạo mới (thực thể Khách hàng + Nhà cung cấp)
```

> [!TIP]
> **Một bảng `dim_partner` cho cả KH lẫn NCC** — dùng cột `partner_group` để phân loại. Đây là thiết kế tốt vì: (1) một công ty có thể vừa là KH vừa là NCC; (2) giảm số bảng DIM; (3) Power BI slicer tên đối tác hoạt động cho cả phải thu lẫn phải trả.

---

## 🔴 BƯỚC 2 — Nhặt MEASURE

### Nhóm A — Từ `Chi_tiet_cong_no_phai_thu.xlsx` (TK 131)

| Measure | Cột gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Dư nợ cuối kỳ (KH đang nợ) | "Dư Nợ" TK 131 | **Snapshot** | `fact_accountsreceivable` | `closing_balance` |
| Phát sinh nợ (KH mua chịu) | "Phát sinh Nợ" TK 131 | **Flow** | `fact_accountsreceivable` | `debit_amount` |
| Phát sinh có (KH trả tiền) | "Phát sinh Có" TK 131 | **Flow** | `fact_accountsreceivable` | `credit_amount` |
| Số hóa đơn | "Số hóa đơn" | Key (degenerate dim) | `fact_accountsreceivable` | `invoice_no` |
| Ngày lập hóa đơn | "Ngày hóa đơn" | Date (dùng tính Tuổi nợ) | `fact_accountsreceivable` | `invoice_date` |
| Trị giá hóa đơn | Giá trị giao dịch | Number | `fact_accountsreceivable` | `invoice_amount` |
| Số đã trả | = invoice_amount − closing_balance | Derived | `fact_accountsreceivable` | *(tính từ debit/credit)* |
| Tuổi nợ (ngày) | = Ngày BC − Ngày HD | Derived | *(tính trong Power BI)* | — |

---

### Nhóm B — Từ `Chi_tiet_cong_no_phai_tra.xlsx` (TK 331)

| Measure | Cột gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Dư phải trả cuối kỳ (nợ NCC) | "Dư Có" TK 331 | **Snapshot** | `fact_accountspayable` | `closing_balance` |
| Phát sinh có (mua nợ NCC) | "Phát sinh Có" TK 331 | **Flow** | `fact_accountspayable` | `credit_amount` |
| Phát sinh nợ (trả tiền NCC) | "Phát sinh Nợ" TK 331 | **Flow** | `fact_accountspayable` | `debit_amount` |
| Số hóa đơn mua hàng | — | Key | `fact_accountspayable` | `invoice_no` |
| Ngày hóa đơn | — | Date | `fact_accountspayable` | `invoice_date` |

---

### Nhóm C — Từ MISA B02_DN

| Measure | Chỉ tiêu | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Doanh thu thuần (để tính VQ PT) | Mã 10 B02_DN | Flow | `fact_incomestatement` | `current_period_amount` WHERE item='Mã10' |
| GVHB (để tính VQ PT trả) | B02_DN | Flow | `fact_incomestatement` | `current_period_amount` WHERE item='GVHB' |

---

✅ **Kết quả Bước 2:**

| Bảng FACT | Trạng thái | Cột chính |
|:---|:---|:---|
| `fact_accountsreceivable` | 🆕 Tạo mới | `closing_balance`, `debit_amount`, `credit_amount`, `invoice_no`, `invoice_date`, `invoice_amount` |
| `fact_accountspayable` | 🆕 Tạo mới | `closing_balance`, `credit_amount`, `debit_amount`, `invoice_no`, `invoice_date` |
| `fact_incomestatement` | ♻️ Tái sử dụng | Bổ sung: DT thuần (Mã10) |

---

## 🔗 BƯỚC 3 — Lắp ráp

### Grain Statement

| Bảng FACT | Grain | Ví dụ 1 dòng |
|:---|:---|:---|
| `fact_accountsreceivable` | 1 hóa đơn × 1 khách hàng × 1 ngày phát sinh | HD001/2026 của KH Công ty A, ngày 05/08/2026, trị giá 100tr, còn nợ 80tr |
| `fact_accountspayable` | 1 hóa đơn × 1 NCC × 1 ngày phát sinh | HD-NCC-456 của NCC Gỗ B, ngày 10/08/2026, còn phải trả 50tr |

---

### Sơ đồ lắp ráp

```
fact_accountsreceivable (Phải thu — TK131)
─────────────────────────────────────────
date_key      (FK) ──→ dim_date
partner_code  (FK) ──→ dim_partner   (Khách hàng)
invoice_no         ── Số hóa đơn (degenerate dim)
─────────────────────────────────────────
invoice_date      [Date]     Ngày lập hóa đơn (tính Tuổi nợ)
invoice_amount    [Number]   Trị giá hóa đơn
debit_amount      [Flow]     Phát sinh Nợ (mua chịu)
credit_amount     [Flow]     Phát sinh Có (KH trả)
closing_balance   [Snapshot] Dư nợ còn lại
```

```
fact_accountspayable (Phải trả — TK331)
─────────────────────────────────────────
date_key      (FK) ──→ dim_date
partner_code  (FK) ──→ dim_partner   (Nhà cung cấp)
invoice_no         ── Số hóa đơn mua hàng
─────────────────────────────────────────
invoice_date    [Date]     Ngày hóa đơn mua
credit_amount   [Flow]     Phát sinh Có (mua nợ NCC)
debit_amount    [Flow]     Phát sinh Nợ (trả tiền NCC)
closing_balance [Snapshot] Dư phải trả còn lại
```

---

## ✅ Tổng kết Dashboard 3

| Loại | Bảng | Trạng thái |
|:---|:---|:---|
| DIM | `dim_date` | ♻️ Tái sử dụng |
| DIM | `dim_partner` | 🆕 Tạo mới (KH + NCC trong 1 bảng) |
| FACT | `fact_accountsreceivable` | 🆕 Tạo mới |
| FACT | `fact_accountspayable` | 🆕 Tạo mới |
| FACT | `fact_incomestatement` | ♻️ Tái sử dụng (bổ sung DT thuần) |

> [!NOTE]
> **Điểm đặc biệt của Dashboard 3:** Chỉ có **1 Filter chính** (Thời gian) — nhưng BRD mô tả rõ rằng filter thời gian này ảnh hưởng đến **Tuổi nợ** (Aging) của từng hóa đơn. Đây là tính năng phức tạp: khi kéo lùi thời gian về quá khứ, hóa đơn có thể chuyển từ "Quá hạn" về "Trong hạn". Logic này thực hiện ở tầng DAX Power BI, không ảnh hưởng đến thiết kế bảng.
