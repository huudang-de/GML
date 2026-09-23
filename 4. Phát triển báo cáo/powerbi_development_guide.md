# Hướng dẫn Phát triển Báo cáo Power BI — Dự án Gỗ Minh Long

> Tài liệu này được viết dựa trực tiếp trên file `ISO - BRD_20260806.xlsx` đã chốt với đối tác. Yêu cầu tuân thủ 100% logic kế toán và mapping các bảng Data Warehouse.

---

## Chuẩn bị Data Model

### Bảng Lịch (Bắt buộc — tạo bằng DAX trước)
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

### Bảng Relationship tổng hợp (Star Schema)

| Bảng Dim (đầu "1") | Cột nối | Bảng Fact (đầu "*") | Cột nối |
| :--- | :--- | :--- | :--- |
| `Dim_Date` | `Date` | `fact_balancesheet` | `reporting_date` |
| `Dim_Date` | `Date` | `fact_businessplan` | `month` |
| `Dim_Date` | `Date` | `fact_incomestatement` | `month` |
| `Dim_Date` | `Date` | `fact_cashflow` | `posting_date` |
| `Dim_Date` | `Date` | `fact_accountspayable` | `posting_date` |
| `Dim_Date` | `Date` | `fact_accountsreceivable` | `posting_date` |
| `Dim_Date` | `Date` | `fact_inventory_balance` | `snapshot_date` |
| `Dim_Date` | `Date` | `fact_inventoryinward` | `posting_date` |
| `Dim_Date` | `Date` | `fact_inventoryoutward` | `posting_date` |
| `Dim_Date` | `Date` | `fact_loan` | `disbursement_date` |
| `Dim_Date` | `Date` | `fact_termdeposit` | `deposit_date` |
| `dim_reportitem` | `item_id` | `fact_balancesheet` | `indicator_code` |
| `dim_reportitem` | `item_id` | `fact_incomestatement` | `indicator_code` |
| `dim_reportitem` | `item_id` | `fact_businessplan` | `indicator_code` |
| `dim_bank` | `bank_code` | `fact_loan` | `bank_code` |
| `dim_bank` | `bank_code` | `fact_termdeposit` | `bank_code` |
| `dim_bank` | `bank_code` | `fact_collateral` | `bank_code` |
| `dim_bank` | `bank_code` | `fact_creditlimitsummary` | `bank_code` |
| `dim_partner` | `partner_code` | `fact_accountsreceivable` | `partner_code` |
| `dim_partner` | `partner_code` | `fact_accountspayable` | `partner_code` |
| `dim_product` | `product_code` | `fact_inventory_balance` | `product_code` |
| `dim_product` | `product_code` | `fact_inventoryinward` | `product_code` |
| `dim_product` | `product_code` | `fact_inventoryoutward` | `product_code` |
| `dim_warehouse` | `warehouse_code` | `fact_inventory_balance` | `warehouse_code` |
| `dim_account` | `account_no` | `fact_cashflow` | `account_no` |

> [!IMPORTANT]
> **Cross filter direction:** Tất cả các relationship đều đặt là **Single** (chiều lọc từ Dim → Fact). Chỉ đặt **Both** nếu có yêu cầu đặc biệt về tính toán DAX phức tạp.

---

## Báo cáo 1: Quản trị Hoạt động Tài chính

**Bộ lọc (Slicer):** `Dim_Date` (Thời gian) · Ngân hàng

| # | Chỉ tiêu | Loại Chart | Nguồn dữ liệu | Hướng dẫn kéo thả & Ghi chú DAX |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | **Dư nợ ngắn hạn** | Card | `fact_loan` | `SUM(remaining_principal)` filter `term_type` = 'Ngắn hạn'. |
| 1.2 | **Dư nợ dài hạn** | Card | `fact_loan` | `SUM(remaining_principal)` filter `term_type` = 'Dài hạn'. |
| 1.3 | **Hạn mức còn lại** | Card | `fact_creditlimitsummary`, `fact_loan` | Room tín dụng còn lại = `SUM(credit_limit)` - `SUM(remaining_principal)`. |
| 1.4 | **Dự báo thời gian sống của TM** | Card | `fact_balancesheet`, `fact_cashflow` | Tổng số dư tiền mặt (Mã 110) / Trung bình Dòng tiền chi ra hàng ngày. |
| 1.5 | **Hạn mức được cấp** | Card | `fact_creditlimitsummary` | Tổng hạn mức tín dụng = `SUM(credit_limit)`. |
| 1.6 | **Hạn mức được phê duyệt** | Card | `fact_creditlimitsummary` | Tổng hạn mức trần = `SUM(granted_limit)`. |
| 1.7 | **Tỷ lệ vay trên TSĐB (LTV)** | Card | `fact_loan`, `fact_collateral` | `SUM(remaining_principal)` / `SUM(appraised_value)`. |
| 1.8 | **Tỷ lệ nợ / vốn (D/E)** | Card | `fact_balancesheet` | Tổng Nợ (Mã 300) / Vốn CSH (Mã 400). Lưu ý dùng `LASTDATE`. |
| 2.1 | **Nợ ngắn/Dài hạn/Tổng dư nợ** | Clustered Column Chart | `fact_loan` | Trục X: Tháng. Cột: Nợ ngắn/dài hạn. Đường: Tổng dư nợ. |
| 2.2 | **Chi phí nợ theo tháng** | Combo Chart | `fact_incomestatement`, `fact_businessplan` | Chi phí lãi vay thực tế (fact) vs Kế hoạch (plan). |
| 2.3 | **Lãi suất bình quân từng bank** | Bar Chart | `fact_loan`, `dim_bank` | `AVERAGE(interest_rate)` group by Bank. |
| 2.4 | **Dư nợ tại từng ngân hàng** | Bar Chart | `fact_loan`, `dim_bank` | Tổng `remaining_principal` group by Bank. |
| 2.5 | **Chi phí lãi vay thực tế & KH** | Clustered Column Chart | `fact_incomestatement`, `fact_businessplan` | Đo lường tỷ lệ tiêu hao ngân sách. (Cột ghép theo BRD). |
| 2.6 | **Phân tích dòng thu theo bank** | Column Chart | `fact_cashflow`, `dim_bank` | Tổng thu (`debit_amount`) group by Bank. |
| 2.7 | **Phân tích dòng chi theo bank** | Column Chart | `fact_cashflow`, `dim_bank` | Tổng chi (`credit_amount`) group by Bank. |
| 2.8 | **Tổng hợp chỉ số (Vòng quay)** | Table | `fact_incomestatement`, `fact_loan` | Bảng tính Vòng quay (Giá vốn / Dư nợ BQ) và Số ngày. |
| 2.9 | **Chi tiết tài sản đảm bảo** | Table | `fact_collateral` | Chi tiết tài sản, hệ số, định giá. |
| 2.10| **Bảng chi tiết lịch trả gốc** | Matrix | `fact_loan` | Hàng: Bank, Cột: Ngày đáo hạn, Giá trị: Tiền gốc. |

---

## Báo cáo 2: Quản trị Hàng tồn kho

**Bộ lọc (Slicer):** `Dim_Date` (Thời gian) · `dim_product` (Loại SP) · `dim_warehouse` (Kho)

| # | Chỉ tiêu | Loại Chart | Nguồn dữ liệu | Hướng dẫn kéo thả & Ghi chú DAX |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | **Giá trị hàng tồn kho** | Card | `fact_inventory_balance` | `SUM(ending_value)` chốt `LASTDATE(snapshot_date)`. **Tuyệt đối không cộng dồn tháng**. |
| 1.2 | **Vòng quay HTK** | Card | `fact_incomestatement`, `fact_inventory_balance` | Giá vốn / Tồn kho BQ. |
| 1.3 | **Inventory to Sales ratio** | Card | `fact_inventory_balance`, `fact_incomestatement` | Tồn kho cuối kỳ / Doanh thu thuần. |
| 1.4 | **Số lượng hàng tồn kho** | Card | `fact_inventory_balance` | `SUM(ending_quantity)` chốt `LASTDATE`. |
| 1.5 | **Tổng mã sản phẩm** | Card | `fact_inventory_balance` | `DISTINCTCOUNT(product_code)` (hàng > 0). |
| 1.6 | **Giá trị hàng nhập khẩu** | Card | `fact_inventoryinward` | Tổng `inward_value` filter `currency <> 'VND'`. |
| 2.1 | **SL & Giá trị HTK theo tháng** | Line & Clustered Column | `fact_inventory_balance` | Cột: Số lượng, Đường: Giá trị. Dùng `LASTDATE`. |
| 2.2 | **Vòng quay HTK theo thời gian** | Area Chart | `fact_incomestatement`, `fact_inventory_balance`, `fact_businessplan` | Thực tế (DAX) vs Kế hoạch (Target). |
| 2.3 | **Inventory to Sales theo tháng** | Line & Clustered Column | `fact_inventory_balance`, `fact_incomestatement` | Tỷ lệ I/S theo tháng. |
| 2.4 | **Trạng thái Nhập - Xuất - Tồn** | Clustered Column Chart | `fact_inventoryinward`, `fact_inventoryoutward`, `fact_inventory_balance` | Tổng Nhập, Tổng Xuất, và Tồn cuối kỳ. |
| 2.5 | **Top 10 tồn kho cuối kỳ** | Bar Chart | `fact_inventory_balance`, `dim_product` | Filter Top 10 by Value. |
| 2.6 | **Bảng Red Flag chậm luân chuyển**| Table | `fact_inventory_balance`, `fact_inventoryinward` | Table tính DAX số ngày ngâm vốn. Bôi ĐỎ nếu >90 ngày. |
| 3.1 | **Thực tế xuất kho vs Kế hoạch** | Table | `fact_inventoryoutward`, `fact_businessplan` | So sánh thực tế xuất so với kế hoạch (Cảnh báo lệch > 5%). |

---

## Báo cáo 3: Quản trị Phải thu - Phải trả

**Bộ lọc (Slicer):** `Dim_Date` (Thời gian)

> [!CAUTION]
> **Logic Kế toán Khách hàng (TK 131):** Phải thu khách hàng là TÀI SẢN. Chốt số dư phải lấy **DƯ NỢ (`ending_debit_balance`)**. Nếu lấy Dư Có là sai hoàn toàn nghiệp vụ.

| # | Chỉ tiêu | Loại Chart | Nguồn dữ liệu | Hướng dẫn kéo thả & Ghi chú DAX |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | **Giá trị phải thu** | Card | `fact_accountsreceivable` | Tổng `ending_debit_balance` (chốt `LASTDATE`). |
| 1.2 | **Vòng quay phải thu hiện tại** | Card | `fact_incomestatement`, `fact_accountsreceivable` | Doanh thu thuần / Phải thu bình quân. |
| 1.3 | **Số lượng khách hàng** | Card | `fact_accountsreceivable` | `DISTINCTCOUNT(partner_code)` (Dư nợ > 0). |
| 1.4 | **Giá trị phải trả** | Card | `fact_accountspayable` | Tổng `ending_credit_balance` (chốt `LASTDATE`). |
| 1.5 | **Vòng quay phải thu theo năm** | Card | DAX | DAX quy đổi vòng quay theo mốc 1 năm (365/Ngày báo cáo). |
| 1.6 | **Tổng số hóa đơn** | Card | `fact_accountsreceivable`, `fact_accountspayable` | `DISTINCTCOUNT(invoice_no)` (Dư nợ > 0). |
| 2.1 | **Khoản phải thu theo tháng** | Column Chart | `fact_accountsreceivable` | Trục Y: Tổng dư nợ `ending_debit_balance`. |
| 2.2 | **Vòng quay phải thu theo tháng** | Line Chart | `fact_incomestatement`, `fact_accountsreceivable` | Trục Y: Tỷ lệ vòng quay phải thu. |
| 2.3 | **Biểu đồ tuổi nợ** | Column Chart | `fact_accountsreceivable` | Nhóm tuổi nợ (Bucket DAX: Ngày BC - invoice_date). Đỏ >90. |
| 2.4 | **Top 10 khách hàng (tổng số dư)**| Bar Chart | `fact_accountsreceivable`, `dim_partner` | `SUM(ending_debit_balance)` Top 10 by partner. |
| 2.5 | **Top 10 khách hàng (nợ quá hạn)**| Bar Chart | `fact_accountsreceivable` | Lọc các HĐ quá hạn, lấy Top 10. |
| 2.6 | **Bảng chi tiết nợ theo KH** | Table | `fact_accountsreceivable`, `dim_partner` | Matrix tổng hợp dư nợ trong hạn/quá hạn theo KH. |
| 2.7 | **Bảng chi tiết các hóa đơn** | Table | `fact_accountsreceivable` | Bảng list chứng từ: KH, Số HĐ, Trị giá, Dư nợ (`ending_debit_balance`). |

---

## Báo cáo 4: Quản trị Tiền gửi & Thanh khoản

**Bộ lọc (Slicer):** `Dim_Date` (Thời gian)

| # | Chỉ tiêu | Loại Chart | Nguồn dữ liệu | Hướng dẫn kéo thả & Ghi chú DAX |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | **Tiền & tương đương tiền** | Card | `fact_balancesheet` | Số dư Mã 110 cuối kỳ (`LASTDATE`). |
| 1.2 | **Tiền gửi** | Card | `fact_termdeposit` | Tổng `original_amount` các sổ đang còn hiệu lực. |
| 1.3 | **Số lượng hợp đồng tiền gửi** | Card | `fact_termdeposit` | Đếm `passbook_no` các sổ còn hiệu lực. |
| 1.4 | **Lãi suất bình quân** | Card | `fact_termdeposit` | `AVERAGE(interest_rate)` các sổ còn hiệu lực. |
| 1.5 | **Thu nhập lãi** | Card | `fact_incomestatement` | `current_period_amount` của Mã chỉ tiêu 21 (Doanh thu HĐ tài chính). |
| 2.1 | **Cơ cấu tiền gửi theo Ngân hàng** | Pie Chart | `fact_termdeposit`, `dim_bank` | Breakdown gốc tiền gửi theo `bank_code`. |
| 2.2 | **Cơ cấu tiền gửi theo Kỳ hạn** | Column Chart | `fact_termdeposit` | Breakdown gốc tiền gửi theo `term`. |
| 3.1 | **Bảng chi tiết tiền gửi** | Table | `fact_termdeposit` | Liệt kê chi tiết từng hợp đồng/sổ tiết kiệm. |

---

## Báo cáo 5: Quản trị Dòng tiền

**Bộ lọc (Slicer):** `Dim_Date` (Thời gian) · Ngân hàng · Tài khoản thu · Tài khoản chi

> [!CAUTION]
> **Logic Thu - Chi Tiền (TK 111, 112):** 
> - **Thu tiền** = Phát sinh Nợ = Cột `debit_amount`.
> - **Chi tiền** = Phát sinh Có = Cột `credit_amount`.
> (Tuyệt đối không lấy nhầm sang số dư).

| # | Chỉ tiêu | Loại Chart | Nguồn dữ liệu | Hướng dẫn kéo thả & Ghi chú DAX |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | **Dòng tiền vào** | Card | `fact_cashflow` | Tổng Phát sinh Nợ (`debit_amount`). |
| 1.2 | **Dòng tiền ra** | Card | `fact_cashflow` | Tổng Phát sinh Có (`credit_amount`). |
| 1.3 | **Số dư tiền mặt** | Card | `fact_balancesheet` | Tổng Mã 110 (`ending_balance`) cuối kỳ. Dùng `LASTDATE`. |
| 1.4 | **Dự báo thời gian (Cash Runway)** | Card | `fact_balancesheet`, `fact_cashflow` | Số dư tiền mặt / Trung bình chi hàng ngày. |
| 2.1 | **Thu/Chi/Dư quỹ theo thời gian** | Stacked Column & Line Chart | `fact_cashflow`, `fact_balancesheet` | Cột Y1: Tổng Thu, Tổng Chi. Đường Y2: Số dư cuối kỳ. |
| 2.2 | **Kế hoạch thu theo thời gian** | Stacked Column Chart | `fact_cashflow`, `fact_businessplan` | Thực tế Thu vs Kế hoạch Thu. |
| 2.3 | **Kế hoạch chi theo thời gian** | Stacked Column Chart | `fact_cashflow`, `fact_businessplan` | Thực tế Chi vs Kế hoạch Chi. |
| 2.4 | **Dư quỹ đầu kỳ / Kế hoạch TH** | Clustered Column Chart | `fact_balancesheet`, `fact_cashflow` | Đầu kỳ + Thu - Chi = Cuối kỳ. (Theo đúng BRD Excel). |
| 3.1 | **Bảng Chu kỳ tiền mặt (CCC)** | Table | Nhiều bảng Fact | Ngày HTK + Ngày Phải thu - Ngày Phải trả. |
| 2.5 | **Tỷ lệ đóng góp dòng thu** | Pie Chart | `fact_cashflow` | Nhóm theo TK Đối ứng (`reciprocal_account`), Tính Tổng Thu. |
| 2.6 | **Tỷ lệ đóng góp dòng chi** | Pie Chart | `fact_cashflow` | Nhóm theo TK Đối ứng (`reciprocal_account`), Tính Tổng Chi. |
| 2.7 | **Tài sản ngắn hạn/Nợ ngắn hạn/VLĐ**| Column Chart | `fact_balancesheet` | TSNH (Mã 100), Nợ NH (Mã 310). Đường: Vốn lưu động (100 - 310). |

---

## Lưu ý Quan trọng cho Team DA (Giữ nguyên)

> [!TIP]
> **Semi-additive Measure (Tồn kho, Số dư tài khoản, Công nợ):** Không được SUM() qua nhiều tháng. Phải dùng `LASTDATE`.
> ```dax
> Closing_Balance = CALCULATE(SUM(fact_balancesheet[ending_balance]), LASTDATE(Dim_Date[Date]))
> ```
