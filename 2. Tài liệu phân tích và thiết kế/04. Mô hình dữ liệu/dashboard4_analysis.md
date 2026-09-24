# 📊 PHÂN TÍCH STAR SCHEMA — DASHBOARD 4
## "Quản Trị Tiền Gửi & Thanh Khoản"
**Nguồn: `ISO - BRD_Excel.xlsx` → Sheet 5 "BRD_Quản trị tiền gửi & Thanh khoản"**

---

## 📄 Bước 0 — Đọc Nguyên Liệu Thô

### Nguồn dữ liệu thô

| STT | Nguồn | Chi tiết |
|:---:|:---|:---|
| 1 | **MISA** | Sổ chi tiết các tài khoản (TK 111, 112) + Báo cáo CĐKT B01_DN |
| 2 | **Excel** | `20260531_Minh Long BC tín dụng 2026` — thông tin hạn mức |
| 3 | **Excel** | `Hop_dong_tien_gui.xlsm` — danh sách hợp đồng tiền gửi có kỳ hạn |

---

### 8.1 Điều kiện ràng buộc

| ĐK | Mô tả |
|:---|:---|
| **ĐK1 — Số dư Tiền mặt (Snapshot)** | Chỉ tiêu "Tiền & tương đương tiền" (B01_DN) → lấy số dư chốt ngày cuối kỳ, **không cộng dồn** |
| **ĐK2 — Trạng thái Hợp đồng Tiền gửi** | Chỉ tính sổ tiết kiệm/HĐ tiền gửi **còn hiệu lực**: Ngày gửi ≤ Ngày BC **VÀ** (Ngày tất toán > Ngày BC **HOẶC** Chưa tất toán). Sổ đã rút không được cộng vào tổng |
| **ĐK3 — Phân tích bắt buộc 2 chiều** | Toàn bộ dữ liệu tiền gửi phải luôn hỗ trợ phân tích theo **Tên ngân hàng** và **Kỳ hạn gửi** |

---

### 8.2 Filter — 2 bộ lọc

| STT | Bộ lọc | Mô tả | Giá trị mẫu |
|:---:|:---|:---|:---|
| 1 | **Thời gian** | Chốt số dư tiền mặt & thống kê HĐ còn hiệu lực tại thời điểm đó | Tháng 1/2026, Q1/2026, Năm 2026 |
| 2 | **Ngân hàng** | Phân bổ tiền gửi & tiền thanh toán tại NH nào | MB, VCB, BIDV... |

---

### 8.3 Chi tiết — 5 Card + 2 Biểu đồ + 1 Bảng

#### 🟦 Phần 1: 5 Chỉ số tổng quan

| Mã | Tên | Cách tính / Nguồn | File gốc | Loại |
|:---|:---|:---|:---|:---|
| 1.1 | **Tiền & tương đương tiền** | Tổng tiền mặt + tiền gửi NH + tương đương tiền → lấy mục I CĐKT (B01-DN: Mã 110) | MISA — B01_DN | Snapshot |
| 1.2 | **Tiền gửi** (còn hiệu lực) | SUM(Trị giá gốc) HĐ tiền gửi thỏa ĐK2 — chưa đến ngày tất toán | `Hop_dong_tien_gui.xlsm` | Snapshot |
| 1.3 | **Số lượng HĐ tiền gửi** | COUNT DISTINCT(Số sổ/Khế ước) còn hiệu lực | `Hop_dong_tien_gui.xlsm` | Derived |
| 1.4 | **Lãi suất bình quân** | AVERAGE(Lãi suất) của các sổ còn hiệu lực | `Hop_dong_tien_gui.xlsm`: cột "LS (%)" | Derived |
| 1.5 | **Thu nhập lãi** | Tổng "Doanh thu hoạt động tài chính" thực nhận trong kỳ → Mã chỉ tiêu 21 trong B02_DN | MISA — B02_DN, Mã 21 | Flow |

---

#### 🟧 Phần 2: 2 Biểu đồ + 1 Bảng chi tiết

| Mã | Tên | Loại | Nguồn | Nội dung |
|:---|:---|:---|:---|:---|
| 2.1 | **Cơ cấu tiền gửi theo Ngân hàng** | Donut Chart | `Hop_dong_tien_gui.xlsm` | Nhóm: Tên NH, Giá trị: Tổng gốc tiền gửi |
| 2.2 | **Cơ cấu tiền gửi theo Kỳ hạn** | Donut Chart | `Hop_dong_tien_gui.xlsm` | Nhóm: Kỳ hạn gửi, Giá trị: Tổng gốc |
| 3.1 | **Bảng chi tiết Tiền gửi** (10 cột) | Table | `Hop_dong_tien_gui.xlsm` | 3.1.1 STT · 3.1.2 CTY · 3.1.3 BANK · 3.1.4 LS(%) · 3.1.5 Kỳ hạn · 3.1.6 Số sổ · 3.1.7 Trị giá gốc · 3.1.8 Ngày gửi · 3.1.9 Ngày đáo hạn · 3.1.10 Ngày tất toán |

---

## 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Tín hiệu trong BRD | Câu hỏi tư duy | → Bảng DIM | PK | Attribute |
|:---|:---|:---|:---|:---|
| **Filter Thời gian** | → tái sử dụng | `dim_date` | `date_key` | *(tái sử dụng)* |
| **Filter Ngân hàng** (MB, VCB, BIDV...) + Biểu đồ 2.1 GROUP BY Tên NH | → tái sử dụng từ Dashboard 1 | `dim_bank` | `bank_code` | *(tái sử dụng)* |
| Bảng 3.1: Số sổ/Khế ước | "Mỗi HĐ tiền gửi là 1 thực thể đủ để thành DIM không?" → Không, vì chỉ có 1 nhóm measure — **giữ như degenerate dim** | *(degenerate dim trong FACT)* | — | `deposit_no` trong fact |
| Bảng 3.1: Kỳ hạn gửi | Chỉ vài giá trị → **attribute** trong FACT, không cần DIM riêng | — | — | `term_months` trong fact |

✅ **Kết quả Bước 1:**
```
dim_date → ♻️ Tái sử dụng
dim_bank → ♻️ Tái sử dụng từ Dashboard 1
(Không tạo DIM mới nào)
```

---

## 🔴 BƯỚC 2 — Nhặt MEASURE

### Nhóm A — Từ `Hop_dong_tien_gui.xlsm` (Hợp đồng tiền gửi)

| Measure | Cột gốc trong file | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Trị giá gốc gửi | "TRỊ GIÁ GỐC" | **Snapshot** | `fact_termdeposit` | `original_amount` |
| Lãi suất | "LS (%)" | Attribute | `fact_termdeposit` | `interest_rate` |
| Kỳ hạn | "KỲ HẠN" | Attribute | `fact_termdeposit` | `term` |
| Số sổ/Khế ước | "SỐ SỔ" | Degenerate dim | `fact_termdeposit` | `passbook_no` |
| Ngày gửi | "NGÀY GỬI" | Date | `fact_termdeposit` | `deposit_date` |
| Ngày đáo hạn | "NGÀY ĐÁO HẠN" | Date | `fact_termdeposit` | `maturity_date` |
| Ngày tất toán | "NGÀY TẤT TOÁN" | Date (NULL nếu chưa rút) | `fact_termdeposit` | `settlement_date` |

---

### Nhóm B — Từ MISA B01_DN

| Measure | Mã chỉ tiêu | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Tiền & tương đương tiền | Mã 110 (TK111 + TK112) | **Snapshot** | `fact_balancesheet` | `ending_balance` WHERE `item_code='110'` |

---

### Nhóm C — Từ MISA B02_DN

| Measure | Mã chỉ tiêu | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| Thu nhập lãi (Doanh thu HĐTC) | Mã 21 B02_DN | **Flow** | `fact_incomestatement` | `current_period_amount` WHERE `item_code='21'` |

---

✅ **Kết quả Bước 2:**

| Bảng FACT | Trạng thái | Cột mới |
|:---|:---|:---|
| `fact_termdeposit` | 🆕 Tạo mới | `original_amount`, `interest_rate`, `term`, `passbook_no`, `deposit_date`, `maturity_date`, `settlement_date` |
| `fact_balancesheet` | ♻️ Tái sử dụng | Bổ sung: Mã 110 |
| `fact_incomestatement` | ♻️ Tái sử dụng | Bổ sung: Mã 21 (Thu nhập lãi) |

---

## 🔗 BƯỚC 3 — Lắp ráp

### Grain Statement

| Bảng FACT | Grain | Ví dụ 1 dòng |
|:---|:---|:---|
| `fact_termdeposit` | 1 hợp đồng tiền gửi có kỳ hạn | Sổ số MB-2026-001 tại MB Bank, gửi 2 tỷ, LS 5.5%/năm, kỳ hạn 6 tháng, đáo hạn 30/09/2026 |

---

### Sơ đồ lắp ráp

```
fact_termdeposit (Hợp đồng tiền gửi)
─────────────────────────────────────────
bank_code     (FK) ──→ dim_bank     (lọc Ngân hàng + biểu đồ 2.1)
deposit_date  (FK) ──→ dim_date     (lọc Thời gian — ngày gửi)
passbook_no        ── Số sổ/Khế ước (degenerate dim) — cột 3.1.6
─────────────────────────────────────────
original_amount  [Snapshot] Trị giá gốc gửi — cột 3.1.7
interest_rate    [Attr]     Lãi suất (%) — cột 3.1.4
term             [Attr]     Kỳ hạn (tháng) — cột 3.1.5, chiều phân tích biểu đồ 2.2
deposit_date     [Date]     Ngày gửi — cột 3.1.8
maturity_date    [Date]     Ngày đáo hạn — cột 3.1.9
settlement_date  [Date]     Ngày tất toán (NULL = chưa rút) — cột 3.1.10
```

> [!NOTE]
> **Tại sao `fact_termdeposit` không có `date_key` FK chuẩn?**
> HĐ tiền gửi có 3 mốc ngày quan trọng: **Ngày gửi**, **Ngày đáo hạn**, **Ngày tất toán**. Không có 1 `date_key` đơn giản đại diện. Giải pháp phổ biến: dùng `deposit_date` làm FK chính, còn `maturity_date` và `settlement_date` lưu dạng Date thường. Filter "Thời gian" trên dashboard sẽ dùng logic: `deposit_date <= [FilterDate] AND (settlement_date > [FilterDate] OR settlement_date IS NULL)`.

---

## ✅ Tổng kết Dashboard 4

| Loại | Bảng | Trạng thái |
|:---|:---|:---|
| DIM | `dim_date` | ♻️ Tái sử dụng |
| DIM | `dim_bank` | ♻️ Tái sử dụng |
| FACT | `fact_termdeposit` | 🆕 Tạo mới |
| FACT | `fact_balancesheet` | ♻️ Tái sử dụng (bổ sung: Mã 110) |
| FACT | `fact_incomestatement` | ♻️ Tái sử dụng (bổ sung: Mã 21 Thu nhập lãi) |

> [!TIP]
> **Dashboard 4 là dashboard "nhẹ" nhất** — không tạo DIM mới, chỉ tạo 1 FACT mới (`fact_termdeposit`). Điều này hợp lý vì tiền gửi đơn giản về chiều phân tích (chỉ theo NH và Kỳ hạn — đều đã có sẵn trong data).
