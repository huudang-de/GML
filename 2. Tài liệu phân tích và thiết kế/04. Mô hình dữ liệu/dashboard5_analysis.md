# 📊 PHÂN TÍCH STAR SCHEMA — DASHBOARD 5
## "Quản Trị Dòng Tiền"
**Nguồn: `ISO - BRD_Excel.xlsx` → Sheet 6 "BRD_Quản trị dòng tiền"**

---

## 📄 Bước 0 — Đọc Nguyên Liệu Thô

### Nguồn dữ liệu thô

| STT | Nguồn | Chi tiết |
|:---:|:---|:---|
| 1 | **MISA** | `So_chi_tiet_cac_tai_khoan.xlsx` — **Trái tim của báo cáo dòng tiền**: Toàn bộ phát sinh chi tiết TK 111 (Tiền mặt) và TK 112 (Tiền gửi NH). Thu tiền = Phát sinh Nợ. Chi tiền = Phát sinh Có |
| 2 | **MISA** | `B01_DN` — Chỉ tiêu Tiền mặt và Tiền gửi (Mã 110) để chốt đối chiếu "Tồn quỹ cuối kỳ" |
| 3 | **Excel** | `Ke_hoach_kinh_doanh` — Kế hoạch Thu/Chi để so sánh TT vs KH |

---

### 8.1 Điều kiện ràng buộc — **QUAN TRỌNG NHẤT của toàn hệ thống**

| ĐK | Mô tả |
|:---|:---|
| **ĐK1 — Tồn quỹ (Snapshot)** | "Tồn quỹ đầu kỳ" và "Tồn quỹ cuối kỳ" tuyệt đối **không cộng dồn**. Dùng **LASTDATE/FIRSTDATE** để chốt chính xác tại biên thời gian |
| **ĐK2 — Lưu chuyển tiền (Flow)** | "Thu tiền" (Phát sinh Nợ) và "Chi tiền" (Phát sinh Có) → **được cộng dồn** trong suốt kỳ |
| **ĐK3 — Loại trừ dòng tiền Nội bộ** | Các giao dịch chuyển tiền nội bộ (Rút tiền gửi NH nhập quỹ TM, chuyển tiền NH A sang NH B) → **phải loại trừ tự động** khỏi Tổng Thu và Tổng Chi để tránh "thổi phồng" quy mô |
| **ĐK4 — Quy tắc Map (Phân loại tự động)** | Dựa vào "Tài khoản đối ứng" để phân loại dòng tiền: Chi đối ứng TK 331 → "Chi trả NCC"; Thu đối ứng TK 131 → "Thu tiền KH"; Chi đối ứng TK 341 → "Chi trả nợ gốc vay"... |

> [!IMPORTANT]
> **ĐK3 và ĐK4 là 2 điều kiện kỹ thuật phức tạp nhất** — chúng yêu cầu cột `counterpart_account` (Tài khoản đối ứng) trong `fact_cashflow` và một bảng mapping phân loại. Đây là lý do `dim_account` (Danh mục tài khoản kế toán) cần được tạo.

---

### 8.2 Filter — **4 bộ lọc** (nhiều nhất trong 5 dashboard)

| STT | Bộ lọc | Mô tả | Giá trị mẫu | Tính chất |
|:---:|:---|:---|:---|:---|
| 1 | **Thời gian** | Xem dòng tiền vào/ra trong 1 chu kỳ, chốt tồn quỹ đầu/cuối kỳ | Tháng 1/2026, Q1 2026 | Bắt buộc |
| 2 | **Ngân hàng** | Chi tiết biến động dòng tiền và tồn quỹ của riêng 1 nhóm TK NH | VCB, MB, Tiền mặt... | Bắt buộc |
| 3 | **Tài khoản thu** | Cô lập các nguồn tiền chảy vào theo nhóm TK đối ứng | Thu bán hàng (TK131), Thu đi vay (TK341)... | Bắt buộc |
| 4 | **Tài khoản chi** | Cô lập các mục đích chi tiền theo nhóm TK đối ứng | Chi trả NCC (TK331), Chi lương (TK334)... | Bắt buộc |

> [!NOTE]
> **"Tài khoản thu" và "Tài khoản chi" ở đây là Tài khoản Kế toán đối ứng** (TK 131, 331, 334, 341...) — khác hoàn toàn với "Tài khoản thu/chi" ở Dashboard 1 là **số tài khoản ngân hàng thực tế** (0141100123005...). Đây là 2 bảng DIM khác nhau: `dim_account` vs `dim_bank_account`.

---

### 8.3 Chi tiết — 4 Card + 7 Biểu đồ + 1 Bảng

#### 🟦 Phần 1: 4 Chỉ số tổng quan

| Mã | Tên | Cách tính / Nguồn | File gốc | Loại |
|:---|:---|:---|:---|:---|
| 1.1 | **Dòng tiền vào** | SUM(Phát sinh Nợ) TK111 + TK112 trong kỳ, loại trừ ĐK3 | `So_chi_tiet_cac_tai_khoan.xlsx` | Flow |
| 1.2 | **Dòng tiền ra** | SUM(Phát sinh Có) TK111 + TK112 trong kỳ, loại trừ ĐK3 | `So_chi_tiet_cac_tai_khoan.xlsx` | Flow |
| 1.3 | **Số dư tiền mặt** | LASTDATE(Mã 110 B01_DN) — chốt tồn quỹ cuối kỳ | MISA — B01_DN | Snapshot |
| 1.4 | **Dự báo thời gian sống** | [Số dư tiền mặt cuối kỳ] ÷ [TB Dòng tiền ra hàng ngày] | Derived từ 1.3 và 1.2 | Derived |

---

#### 🟧 Phần 2: 7 Biểu đồ + 1 Bảng chi tiết

| Mã | Tên | Loại | Nguồn | Nội dung |
|:---|:---|:---|:---|:---|
| 2.1 | **Thu/Chi/Dư quỹ theo tháng** | Stacked Column & Line Chart | `So_chi_tiet` | Cột: Thu + Chi; Đường: Số dư quỹ cuối tháng |
| 2.2 | **TH kế hoạch Thu theo tháng** | Stacked Column Chart | `So_chi_tiet` + `Ke_hoach` | Cột TT vs Đường KH (÷12) |
| 2.3 | **TH kế hoạch Chi theo tháng** | Stacked Column Chart | `So_chi_tiet` + `Ke_hoach` | Cột TT vs Đường KH (÷12) |
| 2.4 | **Tồn đầu kỳ → Thặng dư/Thâm hụt → Tồn cuối kỳ** | Clustered Column Chart | `So_chi_tiet` + B01_DN | Biểu đồ dịch chuyển trạng thái dòng tiền |
| 2.5 | **Tỷ lệ đóng góp của hoạt động Thu** | Pie Chart | `So_chi_tiet` (phân loại theo ĐK4) | Tỷ trọng: Thu bán hàng, Thu đi vay, Thu lãi... |
| 2.6 | **Tỷ lệ đóng góp của hoạt động Chi** | Pie Chart | `So_chi_tiet` (phân loại theo ĐK4) | Tỷ trọng: Chi NCC, Chi lương, Chi trả nợ... |
| 2.7 | **TSNH / Nợ NH / Vốn lưu động** | Column Chart | B01_DN | Cột: Mã100 + Mã310; Đường: TSNH - Nợ NH |
| 3.1 | **Bảng Chu kỳ tiền mặt (CCC)** | Table | B01_DN + B02_DN | Số ngày tồn kho + Số ngày PT − Số ngày PTra = CCC (ngày) |

---

## 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Tín hiệu trong BRD | Câu hỏi tư duy | → Bảng DIM | PK | Attribute |
|:---|:---|:---|:---|:---|
| **Filter Thời gian** | → tái sử dụng | `dim_date` | `date_key` | *(tái sử dụng)* |
| **Filter Ngân hàng** (VCB, MB, Tiền mặt...) | → tái sử dụng | `dim_bank` | `bank_code` | *(tái sử dụng)* |
| **Filter Tài khoản thu** (TK131, TK341...) | "Đây là TK kế toán đối ứng, không phải số TK NH" → cần bảng danh mục TK kế toán | `dim_account` | `account_no` | `account_name`, `account_bank` |
| **Filter Tài khoản chi** (TK331, TK334...) | → Cùng thực thể TK kế toán với "Tài khoản thu" | *(cùng `dim_account`)* | — | — |
| Phân loại ĐK4 (map TK đối ứng → nhóm dòng tiền) | Cần bảng mapping TK đối ứng → Label ("Thu bán hàng", "Chi trả NCC"...) → Có thể dùng attribute trong `dim_account` | `dim_account` | — | `cashflow_category` |

✅ **Kết quả Bước 1:**
```
dim_date    → ♻️ Tái sử dụng
dim_bank    → ♻️ Tái sử dụng
dim_account → 🆕 Tạo mới (Danh mục TK kế toán — filter Tài khoản Thu/Chi đối ứng + mapping phân loại dòng tiền)
```

> [!TIP]
> **Phân biệt rõ 2 bảng DIM về "Tài khoản":**
> - `dim_account` → **Tài khoản Kế toán** (TK 131, 331, 341...) — dùng cho filter Tài khoản Thu/Chi ở Dashboard 5
> - `dim_bank_account` (= `dim_accountnumber`) → **Số TK Ngân hàng thực tế** (0141100123005...) — dùng cho filter Tài khoản Thu/Chi ở Dashboard 1

---

## 🔴 BƯỚC 2 — Nhặt MEASURE

### Nhóm A — Từ `So_chi_tiet_cac_tai_khoan.xlsx` TK 111 + 112

| Measure | Cột gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Thu tiền (Dòng vào) | "Phát sinh Nợ" TK111/112 | **Flow** | `fact_cashflow` | `debit_amount` |
| Chi tiền (Dòng ra) | "Phát sinh Có" TK111/112 | **Flow** | `fact_cashflow` | `credit_amount` |
| Tài khoản kế toán chính (111/112) | TK chủ thể giao dịch | FK | `fact_cashflow` | `account_no` (FK → `dim_account`) |
| Tài khoản đối ứng | TK đối ứng phân loại dòng tiền (131, 331, 341...) | FK | `fact_cashflow` | `counterpart_account` (FK → `dim_account`) |
| Số tài khoản NH | Tài khoản NH cụ thể nhận/gửi | FK | `fact_cashflow` | `bank_account_no` (FK → `dim_bank_account`) |
| Ngày hạch toán | Ngày phát sinh | Date | `fact_cashflow` | `posting_date` (FK → `dim_date`) |
| Số chứng từ | Mã chứng từ MISA | Degenerate dim | `fact_cashflow` | `voucher_no` |
| Cờ loại trừ nội bộ | Giao dịch chuyển tiền nội bộ? | Boolean | `fact_cashflow` | `is_internal_transfer` (True/False) |

---

### Nhóm B — Từ MISA B01_DN

| Measure | Mã | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Tồn quỹ cuối kỳ | Mã 110 | **Snapshot** | `fact_balancesheet` | `ending_balance` |
| Tài sản ngắn hạn | Mã 100 | **Snapshot** | `fact_balancesheet` | `ending_balance` |
| Nợ ngắn hạn | Mã 310 | **Snapshot** | `fact_balancesheet` | `ending_balance` |

---

### Nhóm C — Từ Kế hoạch kinh doanh

| Measure | Chỉ tiêu | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Kế hoạch Thu | KH Thu trong kỳ | **Plan** | `fact_businessplan` | `plan_value` WHERE item='KH Thu' |
| Kế hoạch Chi | KH Chi trong kỳ | **Plan** | `fact_businessplan` | `plan_value` WHERE item='KH Chi' |

---

✅ **Kết quả Bước 2:**

| Bảng FACT | Trạng thái | Cột bổ sung quan trọng |
|:---|:---|:---|
| `fact_cashflow` | ♻️ Tái sử dụng + **Mở rộng** | Thêm: `counterpart_account` (FK→`dim_account`), `is_internal_transfer`, `voucher_no` |
| `fact_balancesheet` | ♻️ Tái sử dụng | Bổ sung: Mã 100, Mã 310 |
| `fact_businessplan` | ♻️ Tái sử dụng | Bổ sung: KH Thu, KH Chi |
| *(Không có FACT mới)* | — | — |

---

## 🔗 BƯỚC 3 — Lắp ráp

### Grain Statement

| Bảng FACT | Grain (từ Dashboard 5) |
|:---|:---|
| `fact_cashflow` | **1 dòng = 1 bút toán (line) trong Sổ chi tiết TK 111/112 × 1 ngày × 1 TK NH** |

```
fact_cashflow (Trung tâm — Sổ chi tiết dòng tiền)
─────────────────────────────────────────────────────
posting_date       (FK) ──→ dim_date           (lọc Thời gian)
bank_account_no    (FK) ──→ dim_bank_account   (lọc Ngân hàng theo TK NH)
account_no         (FK) ──→ dim_account        (TK 111 hoặc 112)
counterpart_account (FK) ──→ dim_account       (TK đối ứng — lọc TK Thu/Chi + phân loại ĐK4)
─────────────────────────────────────────────────────
debit_amount        [Flow]    Phát sinh Nợ (tiền vào)
credit_amount       [Flow]    Phát sinh Có (tiền ra)
voucher_no          [Degen]   Số chứng từ MISA
is_internal_transfer [Bool]   True = giao dịch nội bộ → loại trừ ĐK3
```

> [!WARNING]
> **`counterpart_account` là cột kỹ thuật quan trọng nhất** của Dashboard 5 — không có cột này, không thể thực hiện ĐK4 (phân loại tự động "Thu bán hàng" / "Chi trả NCC"...) và không thể có filter "Tài khoản Thu/Chi" đúng nghĩa.

---

## ✅ Tổng kết Dashboard 5

| Loại | Bảng | Trạng thái |
|:---|:---|:---|
| DIM | `dim_date` | ♻️ Tái sử dụng |
| DIM | `dim_bank` | ♻️ Tái sử dụng |
| DIM | `dim_account` | 🆕 Tạo mới (TK kế toán — filter TK Thu/Chi đối ứng) |
| FACT | `fact_cashflow` | ♻️ Tái sử dụng + mở rộng thêm: `counterpart_account`, `is_internal_transfer` |
| FACT | `fact_balancesheet` | ♻️ Tái sử dụng |
| FACT | `fact_businessplan` | ♻️ Tái sử dụng |

> [!NOTE]
> **Dashboard 5 không tạo FACT mới** — nhưng đòi hỏi **mở rộng thiết kế** `fact_cashflow` với 2 cột quan trọng: `counterpart_account` và `is_internal_transfer`. Đây là điểm dễ bỏ sót nếu chỉ nhìn Dashboard 5 mà không đọc kỹ điều kiện ràng buộc.

### Đặc điểm nổi bật — Dashboard 5 vs Dashboard 1

| Điểm | Dashboard 1 (Hoạt động Tài chính) | Dashboard 5 (Dòng tiền) |
|:---|:---|:---|
| "Tài khoản Thu/Chi" | Số TK NH thực tế (0141100123005...) | TK Kế toán đối ứng (131, 331...) |
| Bảng DIM tương ứng | `dim_bank_account` (`dim_accountnumber`) | `dim_account` |
| Mục đích | Xem tiền qua TK NH nào | Xem tiền đến từ/đi đến hoạt động gì |
| Nguồn gốc cột phân loại | `bank_account_no` trong fact_cashflow | `counterpart_account` trong fact_cashflow |
