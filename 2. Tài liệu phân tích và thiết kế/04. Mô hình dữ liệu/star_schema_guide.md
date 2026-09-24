# Xây Dựng Star Schema từ BRD — Gỗ Minh Long
**Phương pháp: Làm từng Dashboard → Ghép lại thành Schema hoàn chỉnh**

> [!IMPORTANT]
> Đây là tài liệu học "từng bước" để hiểu cách tư duy từ **BRD (yêu cầu kinh doanh)** ra **Data Model (cấu trúc dữ liệu)**. Không nhảy kết quả, làm thủ công từng Dashboard một.

---

## DASHBOARD 1: Quản Trị Dòng Tiền

### 📄 Nguyên liệu từ BRD
Nguồn dữ liệu BRD khai báo:
- File `So_chi_tiet_cac_tai_khoan.xlsx` (Sổ chi tiết TK 111, 112)
- File `B01_DN.xlsx` (Bảng CĐKT — lấy mã chỉ tiêu 110)
- File `Ke_hoach_kinh_doanh.xlsx` (Kế hoạch thu/chi)

---

### 🟡 BƯỚC 1 — Bóc tách DIMENSION (Đọc phần "8.2 Filter")

| Đọc trong BRD | Câu hỏi tư duy | → Tên Bảng DIM | Cột PK | Cột Attribute |
|:---|:---|:---|:---|:---|
| Filter: **Thời gian** (Tháng, Quý) | "Sếp cắt theo thời gian?" | `dim_date` | `Date_Key` | `Year`, `Quarter`, `Month` |
| Filter: **Ngân hàng** (VCB, MB, Tiền mặt) | "Cắt theo ngân hàng nào?" | `dim_bank` | `Bank_Code` | `Bank_Name` |
| Filter: **Tài khoản thu** (TK131, TK341...) | "Cắt theo loại giao dịch thu?" | `dim_account` | `Account_No` | `Account_Name`, `Account_Group` |
| Filter: **Tài khoản chi** (TK331, TK334...) | → Cùng bảng `dim_account` trên | *(đã có)* | — | — |

✅ **Kết quả Bước 1 Dashboard 1:** Cần 3 bảng DIM: `dim_date`, `dim_bank`, `dim_account`

---

### 🔴 BƯỚC 2 — Nhặt MEASURE (Đọc phần "8.3 Chi tiết chỉ tiêu")

| Chỉ tiêu trong BRD | Từ khóa tư duy | Loại | → Bảng FACT | Cột |
|:---|:---|:---|:---|:---|
| **Dòng tiền vào** — "Cộng dồn Phát sinh Nợ TK111/112" | "Cộng dồn" → Flow | Flow | `fact_cashflow` | `Debit_Amount` |
| **Dòng tiền ra** — "Cộng dồn Phát sinh Có TK111/112" | "Cộng dồn" → Flow | Flow | `fact_cashflow` | `Credit_Amount` |
| **Số dư tiền mặt** — "Chốt cuối kỳ bằng LASTDATE" | "Cuối kỳ, LASTDATE" → Snapshot | Snapshot | `fact_cashflow` | `Debit_Balance`, `Credit_Balance` |
| **So sánh Thu vs Kế hoạch** — "Từ file Ke_hoach" | "Kế hoạch" → nguồn riêng | Plan | `fact_businessplan` | `Plan_Cash_In` |
| **Tài sản NH / Nợ NH** — "Từ B01_DN mã 100, 310" | Số liệu BCTC | BCTC | `fact_balancesheet` | `Item_Value` |

✅ **Kết quả Bước 2 Dashboard 1:** Cần 3 bảng FACT: `fact_cashflow`, `fact_businessplan`, `fact_balancesheet`

---

### 🔗 BƯỚC 3 — Lắp ráp (Xác định Grain + nối DIM vào FACT)

**Grain của `fact_cashflow`:**
> *"1 dòng = 1 giao dịch của 1 Tài khoản kế toán, mở tại 1 Ngân hàng, vào 1 Ngày cụ thể"*

```
fact_cashflow (TRUNG TÂM)
─────────────────────────
Date_Key   (FK) ──────→ dim_date     (Bộ lọc Thời gian)
Bank_Code  (FK) ──────→ dim_bank     (Bộ lọc Ngân hàng)
Account_No (FK) ──────→ dim_account  (Bộ lọc Loại giao dịch)
─────────────────────────
Debit_Amount    (Thu tiền - Flow)
Credit_Amount   (Chi tiền - Flow)
Debit_Balance   (Dư Nợ cuối ngày - Snapshot)
Credit_Balance  (Dư Có cuối ngày - Snapshot)
```

---
---

## DASHBOARD 2: Quản Trị Hàng Tồn Kho

### 📄 Nguyên liệu từ BRD
- File `Tong_hop_ton_kho.xlsx` (Báo cáo tổng hợp tồn kho từ MISA)
- File `B02_DN.xlsx` (KQKD — lấy chỉ tiêu Giá vốn COGS)
- File `Ke_hoach_kinh_doanh.xlsx` (Kế hoạch xuất kho)

---

### 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Đọc trong BRD | Câu hỏi tư duy | → Tên Bảng DIM | Cột PK | Cột Attribute |
|:---|:---|:---|:---|:---|
| Filter: **Thời gian** (Tháng, Quý) | → đã có từ Dashboard 1 | `dim_date` | *(tái sử dụng)* | — |
| Filter: **Nhóm sản phẩm** (Giấy, Nẹp, Ván, Khác) | "Cắt theo loại hàng?" | `dim_product` | `Product_Code` | `Product_Name`, `Product_Category` |
| Filter: **Kho lưu vực** (NVL, Hàng hóa, TP) | "Cắt theo kho nào?" | `dim_warehouse` | `Warehouse_Code` | `Warehouse_Name` |

✅ **Kết quả Bước 1 Dashboard 2:** Tái sử dụng `dim_date`. Thêm mới 2 bảng: `dim_product`, `dim_warehouse`

---

### 🔴 BƯỚC 2 — Nhặt MEASURE

| Chỉ tiêu trong BRD | Từ khóa tư duy | Loại | → Bảng FACT | Cột |
|:---|:---|:---|:---|:---|
| **Tồn kho cuối kỳ** (Số lượng, Giá trị) | "Cuối kỳ" → Snapshot | Snapshot | `fact_inventory_balance` | `Ending_Quantity`, `Ending_Value` |
| **Nhập kho trong kỳ** | "Cộng dồn nhập" → Flow | Flow | `fact_inventoryinward` | `Inward_Quantity`, `Inward_Value` |
| **Xuất kho trong kỳ** | "Cộng dồn xuất" → Flow | Flow | `fact_inventoryoutward` | `Outward_Quantity`, `Outward_Value` |
| **So sánh Xuất vs Kế hoạch** | "Kế hoạch" → nguồn riêng | Plan | `fact_businessplan` | `Plan_Export_Value` |
| **COGS (Giá vốn)** — "Từ B02_DN" | Số liệu BCTC | BCTC | `fact_incomestatement` | `Item_Value` |

> [!NOTE]
> **Tại sao Tồn kho cần bảng RIÊNG, không gộp chung với Nhập/Xuất?**
> Vì chúng có **Grain khác nhau**: Nhập/Xuất là giao dịch (xảy ra bất kỳ lúc nào), còn Tồn kho cuối kỳ là ảnh chụp 1 tháng 1 lần. Gộp chung sẽ không tính đúng.

✅ **Kết quả Bước 2 Dashboard 2:** Thêm 3 FACT mới: `fact_inventory_balance`, `fact_inventoryinward`, `fact_inventoryoutward`. Tái sử dụng `fact_businessplan`, `fact_incomestatement`

---

### 🔗 BƯỚC 3 — Lắp ráp

**Grain của `fact_inventory_balance`:**
> *"1 dòng = Số lượng tồn của 1 Sản phẩm, tại 1 Kho, chốt vào cuối 1 Tháng"*

```
fact_inventory_balance
──────────────────────────────────
Date_Key        (FK) → dim_date
Product_Code    (FK) → dim_product
Warehouse_Code  (FK) → dim_warehouse
──────────────────────────────────
Ending_Quantity  (Tồn cuối kỳ - Snapshot)
Ending_Value     (Giá trị tồn - Snapshot)
```

---
---

## DASHBOARD 3: Quản Trị Phải Thu — Phải Trả

### 📄 Nguyên liệu từ BRD
- File `Chi_tiet_cong_no_phai_thu.xlsx` (TK 131 từ MISA)
- File `Chi_tiet_cong_no_phai_tra.xlsx` (TK 331 từ MISA)
- File `B02_DN.xlsx` (Lấy Doanh thu thuần để tính Vòng quay)

---

### 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Đọc trong BRD | Câu hỏi tư duy | → Tên Bảng DIM | Cột PK | Cột Attribute |
|:---|:---|:---|:---|:---|
| Filter: **Thời gian** | → tái sử dụng | `dim_date` | *(tái sử dụng)* | — |
| Biểu đồ xem theo **Khách hàng** / **NCC** | "Cắt theo đối tác?" | `dim_partner` | `Partner_Code` | `Partner_Name`, `Partner_Group` |

> **Lưu ý:** BRD Dashboard 3 chỉ có 1 bộ lọc chính là Thời gian. Tuy nhiên BRD ghi rõ có phân tích "Top 10 khách hàng dư nợ lớn nhất" → cần `dim_partner`

✅ **Kết quả Bước 1 Dashboard 3:** Tái sử dụng `dim_date`. Thêm mới: `dim_partner`

---

### 🔴 BƯỚC 2 — Nhặt MEASURE

| Chỉ tiêu trong BRD | Từ khóa tư duy | Loại | → Bảng FACT | Cột |
|:---|:---|:---|:---|:---|
| **Giá trị phải thu** — "Dư nợ cuối kỳ TK131" | "Cuối kỳ" → Snapshot | Snapshot | `fact_accountsreceivable` | `Closing_Balance` |
| **Phát sinh mua nợ / Phát sinh trả tiền** | "Cộng dồn" → Flow | Flow | `fact_accountsreceivable` | `Debit_Amount`, `Credit_Amount` |
| **Giá trị phải trả** — "Dư Có cuối kỳ TK331" | "Cuối kỳ" → Snapshot | Snapshot | `fact_accountspayable` | `Closing_Balance` |
| **Doanh thu thuần** (để tính Vòng quay) | Số liệu BCTC | BCTC | `fact_incomestatement` | *(tái sử dụng)* |

✅ **Kết quả Bước 2 Dashboard 3:** Thêm 2 FACT mới: `fact_accountsreceivable`, `fact_accountspayable`

---

### 🔗 BƯỚC 3 — Lắp ráp

**Grain của `fact_accountsreceivable`:**
> *"1 dòng = Số dư nợ của 1 Khách hàng, theo 1 Hóa đơn, vào 1 Ngày"*

```
fact_accountsreceivable
───────────────────────────────
Date_Key      (FK) → dim_date
Partner_Code  (FK) → dim_partner
Voucher_No         (Mã hóa đơn - để tính Tuổi nợ)
───────────────────────────────
Debit_Amount    (Phát sinh nợ - Flow)
Credit_Amount   (Phát sinh có - Flow)
Closing_Balance (Dư cuối kỳ - Snapshot)
```

---
---

## DASHBOARD 4: Quản Trị Tiền Gửi & Tín Dụng Ngân Hàng

### 📄 Nguyên liệu từ BRD
- File `bc_tin_dung_2026.xlsx` (sheet: TSBĐ Bank, KE HOACH TRA NO)
- Thông tin hạn mức tín dụng theo từng ngân hàng

---

### 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Đọc trong BRD | Câu hỏi tư duy | → Tên Bảng DIM | Cột PK | Cột Attribute |
|:---|:---|:---|:---|:---|
| Filter: **Thời gian** | → tái sử dụng | `dim_date` | *(tái sử dụng)* | — |
| Filter: **Ngân hàng** | → tái sử dụng | `dim_bank` | *(tái sử dụng)* | — |
| Bảng chi tiết theo **Số tài khoản NH** | "Mỗi TK NH là 1 thực thể riêng?" | `dim_accountnumber` | `Account_Number` | `Bank_Code`, `Account_Type` |

✅ **Kết quả Bước 1 Dashboard 4:** Tái sử dụng `dim_date`, `dim_bank`. Thêm mới: `dim_accountnumber`

---

### 🔴 BƯỚC 2 — Nhặt MEASURE

| Chỉ tiêu trong BRD | Từ khóa tư duy | Loại | → Bảng FACT | Cột |
|:---|:---|:---|:---|:---|
| **Tổng giá trị tiền gửi hiệu lực** | "Hợp đồng đang còn" → Snapshot | Snapshot | `fact_termdeposit` | `Deposit_Amount`, `Interest_Rate` |
| **Lịch trả nợ gốc** (theo ngân hàng, theo ngày) | "Kế hoạch trả" | Schedule | `fact_loan` | `Principal_Amount`, `Due_Date` |
| **Dư nợ vay ngắn hạn / dài hạn** | "Tại thời điểm" → Snapshot | Snapshot | `fact_loan` | `Outstanding_Balance` |
| **Tài sản đảm bảo** (Giá trị thẩm định, Hệ số) | Danh sách TSDB | Snapshot | `fact_collateral` | `Collateral_Value`, `LTV_Ratio` |
| **Hạn mức tín dụng** (Được duyệt / Còn lại) | Tổng hợp hạn mức | Snapshot | `fact_creditlimitsummary` | `Approved_Limit`, `Used_Amount` |

✅ **Kết quả Bước 2 Dashboard 4:** Thêm 4 FACT mới: `fact_termdeposit`, `fact_loan`, `fact_collateral`, `fact_creditlimitsummary`

---

### 🔗 BƯỚC 3 — Lắp ráp

**Grain của `fact_loan`:**
> *"1 dòng = Trạng thái dư nợ của 1 Khoản vay, tại 1 Ngân hàng, tại 1 Thời điểm"*

```
fact_loan
─────────────────────────────
Date_Key   (FK) → dim_date
Bank_Code  (FK) → dim_bank
Loan_ID         (Mã khoản vay)
─────────────────────────────
Outstanding_Balance  (Dư nợ - Snapshot)
Principal_Amount     (Trả gốc kỳ này - Flow)
Interest_Amount      (Trả lãi kỳ này - Flow)
Due_Date             (Ngày đến hạn)
```

---
---

## DASHBOARD 5: Quản Trị Hoạt Động Tài Chính (BCTC)

### 📄 Nguyên liệu từ BRD
- File `B01_DN.xlsx` (Bảng Cân đối Kế toán — CĐKT)
- File `B02_DN.xlsx` (Báo cáo KQKD)
- File `Ke_hoach_kinh_doanh.xlsx` (Chỉ tiêu kế hoạch)

---

### 🟡 BƯỚC 1 — Bóc tách DIMENSION

| Đọc trong BRD | Câu hỏi tư duy | → Tên Bảng DIM | Cột PK | Cột Attribute |
|:---|:---|:---|:---|:---|
| Filter: **Thời gian** | → tái sử dụng | `dim_date` | *(tái sử dụng)* | — |
| Các chỉ tiêu BCTC (Mã 100, 110, 310...) | "Mỗi chỉ tiêu là 1 thực thể?" | `dim_reportitem` | `Item_Code` | `Item_Name`, `Report_Type` |

✅ **Kết quả Bước 1 Dashboard 5:** Tái sử dụng `dim_date`. Thêm mới: `dim_reportitem`

---

### 🔴 BƯỚC 2 — Nhặt MEASURE

| Chỉ tiêu trong BRD | Từ khóa tư duy | Loại | → Bảng FACT | Cột |
|:---|:---|:---|:---|:---|
| **CĐKT** (TSNH, TSdH, Nợ NH, VCP) | "Từ B01_DN" → BCTC | Snapshot | `fact_balancesheet` | `Item_Value` |
| **KQKD** (Doanh thu, COGS, EBITDA, Lợi nhuận) | "Từ B02_DN" → BCTC | Flow | `fact_incomestatement` | `Item_Value` |
| **Kế hoạch kinh doanh** (Kế hoạch DT, Chi phí) | "So sánh TT vs KH" | Plan | `fact_businessplan` | `Plan_Value` |

✅ **Kết quả Bước 2 Dashboard 5:** Thêm 1 FACT mới: `fact_incomestatement`. Tái sử dụng `fact_balancesheet`, `fact_businessplan`

---

### 🔗 BƯỚC 3 — Lắp ráp

**Grain của `fact_balancesheet`:**
> *"1 dòng = Giá trị của 1 Chỉ tiêu CĐKT (Mã 100, 110...), tại 1 Thời điểm (Cuối tháng)"*

```
fact_balancesheet
───────────────────────────────
Date_Key   (FK) → dim_date
Item_Code  (FK) → dim_reportitem
───────────────────────────────
Item_Value  (Giá trị chỉ tiêu - Snapshot)
```

---
---

## ✅ GHÉP 5 DASHBOARD LẠI → STAR SCHEMA HOÀN CHỈNH

### Kết quả tổng hợp

| Dashboard | DIM mới tạo | FACT mới tạo | DIM tái sử dụng | FACT tái sử dụng |
|:---|:---|:---|:---|:---|
| 1. Dòng tiền | `dim_date`, `dim_bank`, `dim_account` | `fact_cashflow`, `fact_businessplan`, `fact_balancesheet` | — | — |
| 2. Tồn kho | `dim_product`, `dim_warehouse` | `fact_inventory_balance`, `fact_inventoryinward`, `fact_inventoryoutward`, `fact_incomestatement` | `dim_date` | `fact_businessplan` |
| 3. Công nợ | `dim_partner` | `fact_accountsreceivable`, `fact_accountspayable` | `dim_date` | `fact_incomestatement` |
| 4. Tín dụng NH | `dim_accountnumber` | `fact_loan`, `fact_termdeposit`, `fact_collateral`, `fact_creditlimitsummary` | `dim_date`, `dim_bank` | — |
| 5. BCTC | `dim_reportitem` | — | `dim_date` | `fact_balancesheet`, `fact_incomestatement`, `fact_businessplan` |
| **TỔNG** | **7 DIM** | **13 FACT** | | |

---

### Sơ đồ Star Schema tổng thể

```
                         [dim_date]
                         🔑 Date_Key
          ┌──────────────────┼──────────────────────────┐
          │                  │                           │
          ▼                  ▼                           ▼
[fact_cashflow]   [fact_inventory_balance]   [fact_accountsreceivable]
[fact_loan]       [fact_inventoryinward]     [fact_accountspayable]
[fact_termdeposit][fact_inventoryoutward]    
[fact_collateral] [fact_incomestatement]     
[fact_creditlimit][fact_balancesheet]        
                  [fact_businessplan]        


[dim_bank] ──────→ fact_cashflow, fact_loan, fact_termdeposit, fact_collateral

[dim_account] ───→ fact_cashflow

[dim_partner] ───→ fact_accountsreceivable, fact_accountspayable

[dim_product] ───→ fact_inventory_balance, fact_inventoryinward, fact_inventoryoutward

[dim_warehouse] →  fact_inventory_balance, fact_inventoryinward, fact_inventoryoutward

[dim_reportitem] → fact_balancesheet, fact_incomestatement, fact_businessplan

[dim_accountnumber] → fact_loan, fact_termdeposit
```

> [!TIP]
> **Quy luật vàng:** Một bảng DIM có thể điều khiển NHIỀU bảng FACT cùng lúc. Đó là lý do khi Sếp click chọn "Vietcombank" (`dim_bank`), dữ liệu đồng thời lọc ở cả Dòng tiền, Khoản vay, và Tiền gửi — vì cả 3 bảng FACT đều nối về cùng 1 bảng `dim_bank`.

---

> [!NOTE]
> **Vì sao `dim_date` kết nối với tất cả?**
> Vì mọi dữ liệu kinh doanh đều diễn ra theo thời gian. `dim_date` là "cột sống" của toàn bộ hệ thống — mọi bảng FACT đều phải có `Date_Key` để Sếp có thể lọc xem bất kỳ số liệu nào theo Tháng, Quý, Năm.
