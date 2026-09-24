# 📊 PHÂN TÍCH STAR SCHEMA — DASHBOARD 2
## "Quản Trị Hàng Tồn Kho"
**Nguồn: `ISO - BRD_Excel.xlsx` → Sheet 3 "BRD_Quản trị Hàng tồn kho"**

---

## 📄 Bước 0 — Đọc Nguyên Liệu Thô

### Nguồn dữ liệu thô

| STT | Nguồn | Chi tiết |
|:---:|:---|:---|
| 1 | **MISA** | Báo cáo `Tong_hop_ton_kho_...xlsx` — cung cấp: Tồn đầu kỳ, Nhập kho, Xuất kho, Tồn cuối kỳ (số lượng + giá trị) chi tiết theo mã vật tư/SP, từng kho |
| 2 | **MISA** | `B02_DN_Bao_cao_ket_qua_hoat_dong_kinh_doanh_2026.xlsx` — lấy chỉ tiêu **Giá vốn hàng bán (COGS)** |
| 3 | **Excel** | `Ke_hoach_kinh_doanh_minh_long_2026.xlsx` — Kế hoạch doanh thu/xuất kho, Target vòng quay tồn kho |

---

### 8.1 Điều kiện ràng buộc

| ĐK | Mô tả |
|:---|:---|
| **ĐK1 — Snapshot (Tồn kho)** | Số lượng tồn và Giá trị tồn kho **KHÔNG được cộng dồn** qua nhiều kỳ. Dùng hàm **LASTDATE** để chốt số cuối ngày cuối kỳ |
| **ĐK2 — Flow (Nhập/Xuất)** | Nhập kho và Xuất kho **được phép cộng dồn** toàn bộ phát sinh trong khoảng thời gian đang chọn |
| **ĐK3 — Kế hoạch** | Kế hoạch thường chỉ có số tổng theo cả năm → mặc định **chia đều cho 12 tháng** khi so sánh TT vs KH theo tháng |
| **ĐK4 — Cảnh báo ±5%** | Khi xuất kho thực tế so với kế hoạch tháng **chênh lệch vượt quá ±5%** → highlight màu đỏ trong bảng 3.1 |
| **ĐK5 — Phân tích bắt buộc theo Dòng SP** | Toàn bộ biểu đồ/bảng phải hỗ trợ lọc theo nhóm SP: **Giấy, Nẹp, Ván, Khác** |

---

### 8.2 Filter — 3 bộ lọc

| STT | Bộ lọc | Mô tả | Giá trị mẫu | Bắt buộc? |
|:---:|:---|:---|:---|:---|
| 1 | **Thời gian** | Tháng, Quý, Năm | Tháng 1/2026, Q1 2026 | Bắt buộc |
| 2 | **Nhóm sản phẩm** | Phân loại theo mảng kinh doanh | Giấy, Nẹp, Ván, Khác | Bắt buộc |
| 3 | **Kho lưu vực** | Lọc kho cụ thể (thành phẩm vs vật tư) | HANG HOA, NVL CHINH, THANH PHAM | Tùy chọn |

---

### 8.3 Chi tiết — 6 Card + 9 Biểu đồ/Bảng

#### 🟦 Phần 1: 6 Chỉ số tổng quan (Cards)

| Mã | Tên | Cách tính / Nguồn gốc | File gốc / Cột gốc | Loại |
|:---|:---|:---|:---|:---|
| 1.1 | **Giá trị hàng tồn kho** | LASTDATE(ending_value) — tổng cuối kỳ. **Không được cộng dồn qua tháng** | `Tong_hop_ton_kho.xlsx`: cột "Giá trị tồn" | Snapshot |
| 1.2 | **Vòng quay Hàng tồn kho** | = GVHB / [(Tồn đầu kỳ + Tồn cuối kỳ)/2] | B02_DN (GVHB) + `Tong_hop_ton_kho` (ending_value) | Derived |
| 1.3 | **Tỷ lệ Tồn kho / Doanh thu** (Inventory to Sales) | = Giá trị tồn cuối kỳ / Doanh thu thuần (Mã 10 B02_DN) | `Tong_hop_ton_kho` + B02_DN | Derived |
| 1.4 | **Số lượng hàng tồn kho** | LASTDATE(ending_quantity) — tổng số lượng cuối kỳ theo DVT riêng từng mã hàng | `Tong_hop_ton_kho.xlsx`: cột "Số lượng tồn" | Snapshot |
| 1.5 | **Tổng mã sản phẩm** | COUNT DISTINCT(product_code) có ending_quantity > 0 | `Tong_hop_ton_kho.xlsx` | Derived |
| 1.6 | **Giá trị hàng nhập khẩu** | SUM(inward_value) WHERE giao dịch nhập khẩu (có tỷ giá ngoại tệ hoặc loại chứng từ mua hàng nhập khẩu) | Sổ chi tiết mua hàng MISA | Flow |

---

#### 🟧 Phần 2: Chỉ số phân tích theo thời gian (6 Biểu đồ)

| Mã | Tên | Loại Chart | Nguồn / Cột gốc | Chiều |
|:---|:---|:---|:---|:---|
| 2.1 | **Số lượng & Giá trị HTK theo thời gian** | Line & Clustered Column Chart | `Tong_hop_ton_kho`: ending_quantity, ending_value LASTDATE mỗi tháng | Theo tháng |
| 2.2 | **Vòng quay HTK theo thời gian — TT vs KH** | Area Chart | B02_DN (GVHB TT) + `Ke_hoach_KD` (Target vòng quay / 12) | Theo tháng |
| 2.3 | **Inventory to Sales theo thời gian** | Line & Clustered Column Chart | `Tong_hop_ton_kho` (ending_value) + B02_DN (DT thuần Mã 10) | Theo tháng |
| 2.4 | **Waterfall Nhập – Xuất – Tồn** | Clustered Column Chart | [Tồn đầu kỳ] + [Nhập] − [Xuất] = [Tồn cuối kỳ] từ `Tong_hop_ton_kho` | Theo kỳ |
| 2.5 | **Top 10 mặt hàng tồn lớn nhất** (Giá/SL) | Bar Chart | `Tong_hop_ton_kho`: ending_value hoặc ending_quantity TOP 10 | Theo SP |
| 2.6 | **Red Flag — Hàng chậm luân chuyển** | Table | Tên SP, Kho, Tồn cuối kỳ, **Số ngày tồn kho** (từ lần nhập/xuất gần nhất). Highlight đỏ nếu > 90 ngày | Theo SP/Kho |

---

#### 🟥 Phần 3: Bảng chi tiết (3 Bảng)

| Mã | Tên | Loại | Nguồn | Các cột |
|:---|:---|:---|:---|:---|
| 3.1 | **Xuất kho TT vs KH theo tháng** | Table | `Tong_hop_ton_kho` (Xuất TT) + `Ke_hoach_KD` (KH) | Tháng, KH, TT, Chênh lệch, % chênh (cảnh báo >5%) |

---

## 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Tín hiệu trong BRD | Câu hỏi tư duy | → Bảng DIM | PK | Attribute |
|:---|:---|:---|:---|:---|
| **Filter Thời gian** | → đã có từ Dashboard 1 | `dim_date` | `date_key` | *(tái sử dụng)* |
| **Filter Nhóm sản phẩm** (Giấy, Nẹp, Ván, Khác) + card 1.5 COUNT SP | "Cắt theo loại hàng?" → Mỗi mã SP là 1 thực thể | `dim_product` | `product_code` | `product_name`, `unit_of_measure`, `product_category` |
| **Filter Kho lưu vực** (HANG HOA, NVL CHINH, THANH PHAM) | "Cắt theo kho nào?" → Mỗi kho là 1 thực thể | `dim_warehouse` | `warehouse_code` | `warehouse_name` |
| Chart 2.6 — phân tích theo SP, KHO | Chiều SP+Kho đã được nắm bởi 2 DIM trên | *(đã có)* | — | — |

✅ **Kết quả Bước 1 — Dashboard 2:**

```
dim_date       → ♻️  Tái sử dụng từ Dashboard 1
dim_product    → 🆕  Tạo mới (filter Nhóm sản phẩm)
dim_warehouse  → 🆕  Tạo mới (filter Kho lưu vực)
```

---

## 🔴 BƯỚC 2 — Nhặt MEASURE

### Phân tích từng nhóm Measure

#### Nhóm A — Từ `Tong_hop_ton_kho.xlsx` (MISA — báo cáo tồn kho)

| Measure | Cột gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| **Tồn cuối kỳ — Số lượng** | "Số lượng tồn" | **Snapshot** | `fact_inventory_balance` | `ending_quantity` |
| **Tồn cuối kỳ — Giá trị** | "Giá trị tồn" | **Snapshot** | `fact_inventory_balance` | `ending_value` |
| **Tồn đầu kỳ — Số lượng** | "Số lượng tồn đầu kỳ" | **Snapshot** | `fact_inventory_balance` | `beginning_quantity` |
| **Tồn đầu kỳ — Giá trị** | "Giá trị tồn đầu kỳ" | **Snapshot** | `fact_inventory_balance` | `beginning_value` |
| **Nhập kho — Số lượng** | "Số lượng" cột Nhập kho | **Flow** | `fact_inventoryinward` | `inward_quantity` |
| **Nhập kho — Giá trị** | "Giá trị" cột Nhập kho | **Flow** | `fact_inventoryinward` | `inward_value` |
| **Xuất kho — Số lượng** | "Số lượng" cột Xuất kho | **Flow** | `fact_inventoryoutward` | `outward_quantity` |
| **Xuất kho — Giá trị** | "Giá trị" cột Xuất kho | **Flow** | `fact_inventoryoutward` | `outward_value` |
| **Số ngày tồn kho** (Red Flag) | Tính từ ngày nhập/xuất gần nhất | **Derived** | `fact_inventoryinward` / `fact_inventoryoutward` | `posting_date` (để tính khoảng cách) |
| **Giá trị hàng nhập khẩu** | inward_value + điều kiện tỷ giá ngoại tệ | **Flow** | `fact_inventoryinward` | `inward_value`, `exchange_rate`, `currency` |

> [!NOTE]
> **Tại sao cần 3 bảng FACT riêng cho tồn kho?**
> - `fact_inventory_balance` → **Snapshot** (1 dòng/tháng/SP/Kho): chốt đầu kỳ & cuối kỳ
> - `fact_inventoryinward` → **Flow** (1 dòng/giao dịch nhập): grain là từng lần nhập
> - `fact_inventoryoutward` → **Flow** (1 dòng/giao dịch xuất): grain là từng lần xuất
>
> Grain khác nhau **bắt buộc** phải tách bảng — đây là lý do ĐK1 và ĐK2 tồn tại.

---

#### Nhóm B — Từ MISA B02_DN (KQKD)

| Measure | Chỉ tiêu | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| **Giá vốn hàng bán (GVHB/COGS)** | Dòng GVHB trong B02_DN | **Flow** | `fact_incomestatement` | `current_period_amount` WHERE item='GVHB' |
| **Doanh thu thuần** | Mã 10 trong B02_DN | **Flow** | `fact_incomestatement` | `current_period_amount` WHERE item='Mã 10' |

---

#### Nhóm C — Từ Kế hoạch kinh doanh

| Measure | Sheet gốc | Loại | → Bảng FACT | Cột FACT |
|:---|:---|:---|:---|:---|
| **Kế hoạch xuất kho** | KQKD_pa1 — mục A (Doanh thu tổng) | **Plan** | `fact_businessplan` | `plan_value` WHERE item='Doanh thu tổng' |
| **Target vòng quay HTK** | `Ke_hoach_KD` | **Plan** | `fact_businessplan` | `plan_value` WHERE item='Vòng quay HTK' |

---

✅ **Kết quả Bước 2 — Dashboard 2:**

| Bảng FACT | Trạng thái | Cột mới |
|:---|:---|:---|
| `fact_inventory_balance` | 🆕 Tạo mới | `ending_quantity`, `ending_value`, `beginning_quantity`, `beginning_value` |
| `fact_inventoryinward` | 🆕 Tạo mới | `inward_quantity`, `inward_value`, `posting_date`, `voucher_no`, `currency`, `exchange_rate` |
| `fact_inventoryoutward` | 🆕 Tạo mới | `outward_quantity`, `outward_value`, `posting_date`, `voucher_no` |
| `fact_incomestatement` | ♻️ Tái sử dụng | Bổ sung: `current_period_amount` cho GVHB, Doanh thu thuần |
| `fact_businessplan` | ♻️ Tái sử dụng | Bổ sung: `plan_value` cho xuất kho KH, target vòng quay |

---

## 🔗 BƯỚC 3 — Lắp ráp

### Grain Statement

| Bảng FACT | Grain | Ví dụ 1 dòng |
|:---|:---|:---|
| `fact_inventory_balance` | 1 mã SP × 1 kho × 1 thời điểm cuối kỳ | SP "Ván MDF 18mm", Kho NVL, tồn 500 tấm giá trị 25tr cuối tháng 8/2026 |
| `fact_inventoryinward` | 1 giao dịch nhập × 1 mã SP × 1 kho × 1 ngày | Nhập 200 tấm Ván MDF vào Kho NVL ngày 05/08/2026, voucher NVL001 |
| `fact_inventoryoutward` | 1 giao dịch xuất × 1 mã SP × 1 kho × 1 ngày | Xuất 50 tấm Ván MDF từ Kho NVL ngày 10/08/2026 cho KH ABC |

---

### Sơ đồ lắp ráp

```
fact_inventory_balance (Trung tâm — Snapshot)
──────────────────────────────────────────
date_key        (FK) ──→ dim_date        (lọc Tháng/Quý)
product_code    (FK) ──→ dim_product     (lọc Nhóm SP)
warehouse_code  (FK) ──→ dim_warehouse   (lọc Kho lưu vực)
──────────────────────────────────────────
ending_quantity   [Snapshot] Tồn cuối kỳ — SL
ending_value      [Snapshot] Tồn cuối kỳ — Giá trị
beginning_quantity [Snapshot] Tồn đầu kỳ — SL
beginning_value   [Snapshot] Tồn đầu kỳ — Giá trị
```

```
fact_inventoryinward (Nhập kho — Flow)
──────────────────────────────────────────
posting_date    (FK) ──→ dim_date
product_code    (FK) ──→ dim_product
warehouse_code  (FK) ──→ dim_warehouse
voucher_no           ── Số chứng từ nhập
──────────────────────────────────────────
inward_quantity  [Flow] Số lượng nhập
inward_value     [Flow] Giá trị nhập (VND)
currency         [Attr] Loại tiền (VND/USD)
exchange_rate    [Attr] Tỷ giá hạch toán
```

```
fact_inventoryoutward (Xuất kho — Flow)
──────────────────────────────────────────
posting_date    (FK) ──→ dim_date
product_code    (FK) ──→ dim_product
warehouse_code  (FK) ──→ dim_warehouse
partner_code    (FK) ──→ dim_partner   (khách hàng nhận hàng — sẽ có từ D3)
voucher_no           ── Số chứng từ xuất
invoice_no           ── Số hóa đơn GTGT
──────────────────────────────────────────
outward_quantity [Flow] Số lượng xuất
outward_value    [Flow] Giá trị xuất (VND)
```

---

## ✅ Tổng kết Dashboard 2

### Bảng kiểm đối chiếu BRD

| Chỉ tiêu BRD | → Bảng FACT | Cột |
|:---|:---|:---|
| Card 1.1 Giá trị HTK | `fact_inventory_balance` | LASTDATE(`ending_value`) |
| Card 1.2 Vòng quay HTK | `fact_incomestatement` + `fact_inventory_balance` | GVHB / BQ(begin+end value) |
| Card 1.3 Tồn/DT | `fact_inventory_balance` + `fact_incomestatement` | ending_value / DT thuần |
| Card 1.4 SL tồn kho | `fact_inventory_balance` | LASTDATE(`ending_quantity`) |
| Card 1.5 Tổng mã SP | `fact_inventory_balance` | COUNT DISTINCT(`product_code`) |
| Card 1.6 Hàng nhập khẩu | `fact_inventoryinward` | SUM(`inward_value`) WHERE NK |
| Chart 2.1 HTK theo tháng | `fact_inventory_balance` | ending_qty/value × date |
| Chart 2.2 Vòng quay TT vs KH | `fact_incomestatement`+`fact_inventory_balance`+`fact_businessplan` | — |
| Chart 2.3 Tồn/DT theo tháng | `fact_inventory_balance`+`fact_incomestatement` | % |
| Chart 2.4 Waterfall | `fact_inventory_balance`+`fact_inventoryinward`+`fact_inventoryoutward` | begin, nhập, xuất, end |
| Chart 2.5 Top 10 tồn | `fact_inventory_balance` | TOP 10 ending_value/qty |
| Chart 2.6 Red Flag | `fact_inventoryinward`/`fact_inventoryoutward` | posting_date gần nhất |
| Table 3.1 Xuất TT vs KH | `fact_inventoryoutward`+`fact_businessplan` | outward_value vs plan |

### Tổng hợp DIM/FACT từ Dashboard 2

| Loại | Bảng | Trạng thái |
|:---|:---|:---|
| DIM | `dim_date` | ♻️ Tái sử dụng |
| DIM | `dim_product` | 🆕 Tạo mới |
| DIM | `dim_warehouse` | 🆕 Tạo mới |
| FACT | `fact_inventory_balance` | 🆕 Tạo mới |
| FACT | `fact_inventoryinward` | 🆕 Tạo mới |
| FACT | `fact_inventoryoutward` | 🆕 Tạo mới |
| FACT | `fact_incomestatement` | ♻️ Tái sử dụng (bổ sung: GVHB, DT thuần) |
| FACT | `fact_businessplan` | ♻️ Tái sử dụng (bổ sung: KH xuất kho, target vòng quay) |

> [!NOTE]
> **Phát hiện mới:** `fact_inventoryoutward` cần `partner_code` (FK → dim_partner) để biết xuất cho khách hàng nào — điều này kéo `dim_partner` vào sơ đồ, và `dim_partner` sẽ được tạo chính thức ở Dashboard 3.
