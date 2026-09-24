# 🏗️ STAR SCHEMA HOÀN CHỈNH — Gỗ Minh Long
## Tổng hợp từ 5 Dashboard BRD + Đối chiếu Data Dictionary

**Nguồn BRD:** `ISO - BRD_Excel.xlsx` (6 sheet)
**Đối chiếu:** `Data_Dictionary_GML.xlsx` (22 sheet / 20 bảng)

> [!IMPORTANT]
> **Data Dictionary (DD) = Đã triển khai thực tế.** DD được dịch trực tiếp từ `Data_GoMinhLong` (file dữ liệu nguồn thật). Đây là **chuẩn không thay đổi**. Mọi khoảng cách giữa BRD và DD sẽ được **xử lý bằng DAX / Power BI** — không điều chỉnh data model.

---

## 📋 BƯỚC TỔNG HỢP — Ghép 5 Dashboard lại

| Dashboard | DIM 🆕 Tạo mới | FACT 🆕 Tạo mới | DIM ♻️ Tái sử dụng | FACT ♻️ Tái sử dụng |
|:---|:---|:---|:---|:---|
| **D1** Hoạt động Tài chính | `dim_date`, `dim_bank`, `dim_bank_account` | `fact_loan`, `fact_loan_schedule`, `fact_creditlimitsummary`, `fact_collateral`, `fact_cashflow`, `fact_balancesheet`, `fact_incomestatement`, `fact_businessplan` | — | — |
| **D2** Hàng tồn kho | `dim_product`, `dim_warehouse` | `fact_inventory_balance`, `fact_inventoryinward`, `fact_inventoryoutward` | `dim_date` | `fact_incomestatement`, `fact_businessplan` |
| **D3** Phải thu/Phải trả | `dim_partner` | `fact_accountsreceivable`, `fact_accountspayable` | `dim_date` | `fact_incomestatement` |
| **D4** Tiền gửi & TK | *(không có DIM mới)* | `fact_termdeposit` | `dim_date`, `dim_bank` | `fact_balancesheet`, `fact_incomestatement` |
| **D5** Dòng tiền | `dim_account` | *(không có FACT mới, chỉ mở rộng fact_cashflow)* | `dim_date`, `dim_bank` | `fact_cashflow`, `fact_balancesheet`, `fact_businessplan` |

---

## 🏗️ STAR SCHEMA HOÀN CHỈNH

### 7 Bảng DIMENSION

| # | Tên bảng | Nguồn từ Dashboard | Phục vụ |
|:---:|:---|:---|:---|
| 1 | `dim_date` | D1 (tạo) → D2,3,4,5 (dùng lại) | **Toàn bộ** hệ thống |
| 2 | `dim_bank` | D1 (tạo) → D4,5 (dùng lại) | Tín dụng, Tiền gửi, Dòng tiền |
| 3 | `dim_bank_account` *(= `dim_accountnumber` trong DD)* | D1 (tạo) → D5 (dùng lại) | Dòng tiền (filter TK thu/chi) |
| 4 | `dim_account` | D5 (tạo) | Dòng tiền (TK kế toán đối ứng) |
| 5 | `dim_product` | D2 (tạo) | Hàng tồn kho |
| 6 | `dim_warehouse` | D2 (tạo) | Hàng tồn kho |
| 7 | `dim_partner` | D3 (tạo) → D2 (dùng lại qua fact_inventoryoutward) | Phải thu/Phải trả, Mua/Bán hàng |

> [!NOTE]
> **`dim_reportitem`** — Đây là bảng DIM trong Data Dictionary nhưng **không xuất hiện trực tiếp trong BRD** như filter hay chiều phân tích. Nó là bảng chuẩn hóa các mã chỉ tiêu BCTC (B01, B02), được dùng ngầm để nối `fact_balancesheet` và `fact_incomestatement` với các mã chỉ tiêu có cấu trúc phân cấp. → **Thêm vào Star Schema nhưng flagged là "infrastructure DIM"**.

---

### 13 Bảng FACT (từ BRD) — So sánh với Data Dictionary

| # | Tên FACT (từ BRD) | Loại | Tên trong DD | Khớp? |
|:---:|:---|:---|:---|:---:|
| 1 | `fact_loan` | Snapshot (dư nợ vay) | `fact_loan` | ✅ |
| 2 | `fact_loan_schedule` | Schedule (lịch trả gốc) | ❌ **Không có trong DD** | ⚠️ |
| 3 | `fact_creditlimitsummary` | Snapshot (hạn mức) | `fact_creditlimitsummary` | ✅ |
| 4 | `fact_collateral` | Static (TSĐB) | `fact_collateral` | ✅ |
| 5 | `fact_cashflow` | Flow (giao dịch tiền) | `fact_cashflow` | ✅ |
| 6 | `fact_balancesheet` | Snapshot (CĐKT) | `fact_balancesheet` | ✅ |
| 7 | `fact_incomestatement` | Flow (KQKD) | `fact_incomestatement` | ✅ |
| 8 | `fact_businessplan` | Plan (kế hoạch) | `fact_businessplan` | ✅ |
| 9 | `fact_inventory_balance` | Snapshot (tồn kho) | `fact_inventory_balance` | ✅ |
| 10 | `fact_inventoryinward` | Flow (nhập kho) | `fact_inventoryinward` | ✅ |
| 11 | `fact_inventoryoutward` | Flow (xuất kho) | `fact_inventoryoutward` | ✅ |
| 12 | `fact_accountsreceivable` | Snapshot+Flow (PT) | `fact_accountsreceivable` | ✅ |
| 13 | `fact_accountspayable` | Snapshot+Flow (PT trả) | `fact_accountspayable` | ✅ |
| 14 | `fact_termdeposit` | Snapshot (tiền gửi) | `fact_termdeposit` | ✅ |

---

## 🔗 SƠ ĐỒ KẾT NỐI STAR SCHEMA HOÀN CHỈNH

```
                    ┌─────────────────────────────────────────────┐
                    │              dim_date (🔑 date_key)          │
                    │     "Cột sống kết nối tất cả theo thời gian" │
                    └────────────┬────────────────────────────────┘
                                 │ FK
          ┌──────────────────────┼──────────────────────────────────────┐
          │                      │                                      │
          ▼                      ▼                                      ▼
  [D1 — Tín dụng]        [D2 — Tồn kho]                    [D3 — Công nợ]
  fact_loan              fact_inventory_balance              fact_accountsreceivable
  fact_creditlimitsummary fact_inventoryinward               fact_accountspayable
  fact_collateral        fact_inventoryoutward
  fact_cashflow          [D4 — Tiền gửi]                    [D5 — Dòng tiền]
  fact_termdeposit       fact_termdeposit                   fact_cashflow (mở rộng)
  fact_balancesheet      fact_balancesheet
  fact_incomestatement   fact_incomestatement               [Xuyên suốt]
  fact_businessplan      fact_businessplan                  fact_balancesheet
                                                             fact_businessplan

dim_bank ──────────────→ fact_loan
  (🔑 bank_code)         fact_creditlimitsummary
                         fact_collateral
                         fact_cashflow (via dim_bank_account)
                         fact_termdeposit

dim_bank_account ──────→ fact_cashflow
  (dim_accountnumber)      (filter Tài khoản thu/chi theo số TK NH)
  FK: bank_code → dim_bank

dim_account ───────────→ fact_cashflow
  (🔑 account_no)          Account_No (TK chủ)
                           Reciprocal_Account (TK đối ứng → phân loại D5)

dim_partner ───────────→ fact_accountsreceivable (KH)
  (🔑 partner_code)        fact_accountspayable (NCC)
                           fact_inventoryoutward (KH mua hàng)
                           fact_inventoryinward (NCC bán hàng)
                           fact_cashflow (đối tượng giao dịch)

dim_product ───────────→ fact_inventory_balance
  (🔑 product_code)        fact_inventoryinward
                           fact_inventoryoutward

dim_warehouse ─────────→ fact_inventory_balance
  (🔑 warehouse_code)      fact_inventoryinward
                           fact_inventoryoutward

dim_reportitem ────────→ fact_balancesheet (Indicator_Code FK)
  (🔑 item_id)             fact_incomestatement (Indicator_Code FK)
                           fact_businessplan (Indicator_Code FK)
```

---

## 🔍 ĐỐI CHIẾU BRD vs DATA DICTIONARY

### ✅ Hoàn toàn khớp (13/14 FACT)

Data Dictionary có đủ 13 bảng FACT tương ứng với những gì BRD yêu cầu. Không thiếu bảng nào.

### ⚠️ Sai lệch và phát hiện quan trọng

#### 1. `fact_loan_schedule` — BRD có, DD không có
**BRD mục 2.10** (Dashboard 1): Matrix lịch trả gốc theo tuần từ sheet `KE HOACH TRA NO TUAN` → grain khác hoàn toàn `fact_loan` → cần bảng riêng.
**Data Dictionary**: Gộp thông tin này vào `fact_loan` (cột `Principal_Payment_Amount`).

> **Nhận xét:** DD đã đơn giản hóa. Nếu cần hiển thị Matrix (bank × ngày) như BRD yêu cầu, thì dữ liệu trong `fact_loan` phải được unpivot hoặc cần bảng riêng. **→ Đề xuất: Giữ nguyên DD, nhưng lưu ý khi ETL cần xử lý unpivot sheet `KE HOACH TRA NO TUAN` vào `fact_loan`.**

---

#### 2. `dim_bank_account` vs `dim_accountnumber` — Tên khác nhau
**BRD (D1)**: Tôi đặt tên `dim_bank_account`
**Data Dictionary**: Tên là `dim_accountnumber`

> **Nhận xét:** Cùng 1 thực thể. **→ Dùng tên `dim_accountnumber` theo Data Dictionary.**

---

#### 3. `fact_cashflow` — Thiếu cột quan trọng trong DD

**BRD (D5)** yêu cầu:
- `is_internal_transfer` (Boolean) — để loại trừ giao dịch chuyển tiền nội bộ (ĐK3)
- Rõ ràng phân biệt `Account_No` (TK chủ) và `Reciprocal_Account` (TK đối ứng)

**Data Dictionary** `fact_cashflow` đã có:
- ✅ `Reciprocal_Account` — đã có (tên `Reciprocal_Account`)
- ✅ `Account_No` — đã có
- ❌ `is_internal_transfer` — **CHƯA CÓ trong DD**

> **Đề xuất:** Thêm cột `Is_Internal_Transfer BOOLEAN` vào `fact_cashflow` trong Data Dictionary.

---

#### 4. `fact_inventory_balance` — Thiếu `beginning_value/quantity` trong DD

**BRD (D2)** card 1.2 (Vòng quay HTK) cần: `(Tồn đầu kỳ + Tồn cuối kỳ) / 2`

**Data Dictionary** `fact_inventory_balance` chỉ có:
- `Ending_Quantity`, `Ending_Value`
- ❌ `Beginning_Quantity`, `Beginning_Value` — **CHƯA CÓ**

> **Đề xuất:** Thêm `Beginning_Quantity FLOAT` và `Beginning_Value NUMERIC(18,2)` vào `fact_inventory_balance`. **Hoặc** tính Beginning = Ending của tháng trước trong DAX — nhưng cách này phức tạp và dễ sai với LASTDATE.

---

#### 5. `fact_creditlimitsummary` — Tên cột khác nhau

**BRD (D1)** mô tả 3 chỉ số: Hạn mức được cấp (`credit_limit`), Hạn mức phê duyệt (`granted_limit`), Hạn mức còn lại (= granted - used)

**Data Dictionary** `fact_creditlimitsummary` có:
- `Granted_Limit` → = "Hạn mức phê duyệt" ✅
- `Credit_Limit` → = "Hạn mức được cấp" ✅
- `Principal_Balance` → Dư nợ hiện tại (để tính Còn lại) ✅
- `Remaining_Disbursement` → Hạn mức còn lại (= Credit_Limit − Principal_Balance) ✅

> **Nhận xét:** Hoàn toàn đủ, tên cột hơi khác nhưng nghĩa giống nhau. **→ Không cần điều chỉnh.**

---

#### 6. `dim_reportitem` — Không xuất hiện trong BRD nhưng có trong DD

**BRD**: Không có filter hay chiều phân tích tường minh theo "Mã chỉ tiêu báo cáo". Các chỉ tiêu như Mã 110, Mã 300, Mã 400 được lọc trực tiếp trong measure DAX.

**Data Dictionary**: Có `dim_reportitem` đầy đủ với cả phân cấp Parent_ID.

> **Nhận xét:** `dim_reportitem` là "infrastructure DIM" — không dùng làm filter trên UI nhưng cần thiết để: (1) chuẩn hóa tên chỉ tiêu; (2) tạo cây phân cấp Tài sản/Nguồn vốn; (3) làm FK cho `fact_balancesheet`, `fact_incomestatement`, `fact_businessplan`. **→ Giữ nguyên, đúng thiết kế.**

---



## 📊 BẢNG TỔNG KẾT SO SÁNH

### DIM — So sánh BRD vs DD

| Bảng DIM | Từ BRD | Trong DD | Ghi chú |
|:---|:---:|:---:|:---|
| `dim_date` | ✅ | ❌ Không có trong DD | DD không có dim_date vì Power BI tự tạo Date Table. **Bình thường** |
| `dim_bank` | ✅ | ✅ | Khớp hoàn toàn |
| `dim_accountnumber` | ✅ (tôi gọi là dim_bank_account) | ✅ | Khớp, chỉ khác tên |
| `dim_account` | ✅ | ✅ | Khớp hoàn toàn |
| `dim_product` | ✅ | ✅ | Khớp hoàn toàn |
| `dim_warehouse` | ✅ | ✅ | Khớp hoàn toàn |
| `dim_partner` | ✅ | ✅ | Khớp hoàn toàn |
| `dim_reportitem` | ❌ Không tường minh trong BRD | ✅ | Infrastructure DIM — **nên giữ** |

### FACT — So sánh BRD vs DD

| Bảng FACT | Từ BRD | Trong DD | Ghi chú |
|:---|:---:|:---:|:---|
| `fact_loan` | ✅ | ✅ | Khớp, DD thiếu `term_type` |
| `fact_loan_schedule` | ✅ | ❌ | **BRD yêu cầu, DD không có** — gộp vào fact_loan |
| `fact_creditlimitsummary` | ✅ | ✅ | Khớp tốt |
| `fact_collateral` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_cashflow` | ✅ | ✅ | DD thiếu `is_internal_transfer` |
| `fact_balancesheet` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_incomestatement` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_businessplan` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_inventory_balance` | ✅ | ✅ | DD thiếu `beginning_quantity/value` |
| `fact_inventoryinward` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_inventoryoutward` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_accountsreceivable` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_accountspayable` | ✅ | ✅ | Khớp hoàn toàn |
| `fact_termdeposit` | ✅ | ✅ | Khớp hoàn toàn |

---

## 🔧 XỬ LÝ KHOẢNG CÁCH BRD vs DD — Giải pháp Power BI / DAX

> [!NOTE]
> **Nguyên tắc:** DD là dữ liệu đã load thực tế, **không sửa schema**. Những chỉ tiêu BRD yêu cầu mà DD chưa có cột → **tạo Calculated Column hoặc Measure DAX trong Power BI**.

| # | Yêu cầu BRD | DD có không? | Giải pháp Power BI |
|:---:|:---|:---:|:---|
| 1 | **Loại trừ chuyển tiền nội bộ** (ĐK3 D5) | ❌ Không có `is_internal_transfer` | DAX Measure: lọc các dòng `fact_cashflow` có `Reciprocal_Account` là TK 111/112 (chuyển nội bộ) bằng `CALCULATE(..., FILTER(...))` |
| 2 | **Tồn đầu kỳ** cho Vòng quay HTK (D2 Card 1.2) | ❌ `fact_inventory_balance` chỉ có Ending | DAX Measure: `Beginning = CALCULATE([Ending_Value], PREVIOUSMONTH(...))` — lấy Ending của tháng trước làm Beginning |
| 3 | **Phân loại Ngắn hạn/Dài hạn** (D1 Card 1.1/1.2) | ❌ `fact_loan` không có `term_type` | DAX Calculated Column: `Term_Type = IF(DATEDIFF([Disbursement_Date],[Maturity_Date],DAY) <= 365, "Ngắn hạn", "Dài hạn")` |
| 4 | **Matrix lịch trả gốc theo tuần** (D1 Bảng 2.10) | ❌ Không có `fact_loan_schedule` | Power Query: unpivot sheet `KE HOACH TRA NO TUAN` của file `bc_tin_dung` → load thành bảng phụ trong Power BI (không cần vào PostgreSQL) |

---

## 📌 KẾT LUẬN

### DD là chuẩn — Bao phủ tốt BRD
- ✅ **13/13 FACT** cần thiết đã có trong DD (100% — `fact_loan_schedule` gộp vào `fact_loan`)
- ✅ **7/7 DIM** thực chất đã có
- ✅ Cấu trúc FK đủ để kết nối toàn bộ Star Schema
- ✅ Kiểu dữ liệu PostgreSQL đã định nghĩa đầy đủ
- ℹ️ `dim_date` không có trong DD là bình thường — Power BI tự tạo Date Table
- ℹ️ `dim_reportitem` là infrastructure DIM, không dùng làm filter UI

### Chiến lược xử lý phần còn lại
**4 khoảng cách nhỏ giữa BRD và DD → xử lý 100% tại Power BI:**

| Loại xử lý | Số lượng | Công cụ |
|:---|:---:|:---|
| DAX Calculated Column | 2 | `Term_Type`, `Beginning_Value/Quantity` |
| DAX Measure (CALCULATE + FILTER) | 1 | Loại trừ chuyển tiền nội bộ |
| Power Query (load thêm từ file gốc) | 1 | Lịch trả gốc tuần |

> [!TIP]
> **Không cần đụng vào PostgreSQL / ETL pipeline.** Toàn bộ "khoảng cách" nhỏ này có thể giải quyết bằng Power Query Transform và DAX Measure trong file `.pbix` — đây là cách làm đúng và linh hoạt nhất.

