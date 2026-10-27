-- ==========================================
-- DASHBOARD: QUẢN TRỊ PHẢI THU - PHẢI TRẢ
-- ==========================================

--- VISUAL: Giá trị phải thu
WITH latest_transactions AS (
    -- Bước 1: Sử dụng Window Function (ROW_NUMBER) để đánh số thứ tự cho các giao dịch công nợ 
    -- của từng khách hàng, sắp xếp giảm dần theo ngày chứng từ (posting_date) và mã giao dịch (id) 
    -- để xác định đúng dòng số dư ghi nhận mới nhất cuối cùng.
    SELECT 
        f.partner_code,
        f.ending_debit_balance,
        ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM silver.fact_accountsreceivable f
    -- Kết hợp với bảng danh mục đối tác để lọc đúng nhóm đối tượng khách hàng
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    -- Chỉ lọc các đối tượng thuộc nhóm khách hàng thuần túy hoặc nhóm kiêm nhiệm cả nhà cung cấp
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
)
-- Bước 2: Tổng hợp số dư nợ phải thu từ các dòng giao dịch mới nhất (rn = 1) của từng khách hàng
SELECT 
    SUM(ending_debit_balance) AS gia_tri_phai_thu
FROM latest_transactions
WHERE rn = 1;
/* RESULT LOG:
+------------------+
| gia_tri_phai_thu |
+------------------+
|  36326095573.00  |
+------------------+
*/

--- VISUAL: Giá trị phải trả
WITH latest_transactions AS (
    -- Bước 1: Sử dụng Window Function (ROW_NUMBER) để đánh số thứ tự cho các giao dịch công nợ phải trả 
    -- của từng nhà cung cấp, sắp xếp giảm dần theo ngày chứng từ (posting_date) và mã giao dịch (id) 
    -- để xác định đúng dòng số dư ghi nhận mới nhất cuối cùng.
    SELECT 
        f.partner_code,
        f.ending_credit_balance,
        ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM silver.fact_accountspayable f
    -- Kết hợp với bảng danh mục đối tác để lọc đúng nhóm đối tượng nhà cung cấp
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    -- Chỉ lọc các đối tượng thuộc nhóm nhà cung cấp thuần túy hoặc nhóm kiêm nhiệm cả khách hàng
    WHERE p.partner_group IN ('Nhà cung cấp', 'Khách hàng/ nhà cung cấp')
)
-- Bước 2: Tổng hợp số dư có phải trả từ các dòng giao dịch mới nhất (rn = 1) của từng nhà cung cấp
SELECT 
    SUM(ending_credit_balance) AS gia_tri_phai_tra
FROM latest_transactions
WHERE rn = 1;

/* RESULT LOG:
+------------------+
| gia_tri_phai_tra |
+------------------+
|  60452900187.23  |
+------------------+
*/

--- VISUAL: Vòng quay phải thu theo năm
WITH max_date AS (
    -- Bước 1: Tìm mốc ngày giao dịch lớn nhất có trong hệ thống để xác định năm hiện tại cần báo cáo
    SELECT MAX(posting_date) AS dt 
    FROM silver.fact_accountsreceivable
),
doanh_thu_nam AS (
    -- Bước 2: Tổng hợp doanh thu thuần lũy kế trong năm tài chính tương ứng với năm của ngày max_date
    SELECT SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement
    WHERE indicator_code = 'B02-DN_10' 
      AND EXTRACT(YEAR FROM month) = EXTRACT(YEAR FROM (SELECT dt FROM max_date))
),
latest_transactions AS (
    -- Bước 3: Dùng Window Function (ROW_NUMBER) để lọc ra số dư công nợ cuối cùng của từng khách hàng
    SELECT 
        f.partner_code, 
        f.ending_debit_balance,
        ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) AS rn
    FROM silver.fact_accountsreceivable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
),
phai_thu_cuoi_nam AS (
    -- Bước 4: Tổng hợp tổng số dư nợ phải thu cuối kỳ của toàn bộ khách hàng (rn = 1)
    SELECT SUM(ending_debit_balance) AS val
    FROM latest_transactions
    WHERE rn = 1
)
-- Bước 5: Tính hệ số vòng quay phải thu = Doanh thu thuần trong năm / Số dư phải thu cuối kỳ
-- Vì data lịch sử năm trước (2025) không có trong fact_accountsreceivable, 
-- Phải thu năm ngoái = 0, nếu áp dụng DAX IF(ISBLANK) thì Trung bình = Phải thu cuối năm
SELECT (SELECT val FROM doanh_thu_nam) / NULLIF((SELECT val FROM phai_thu_cuoi_nam), 0) AS vong_quay_phai_thu_nam;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code='B02-DN_10' AND EXTRACT(YEAR FROM month) = EXTRACT(YEAR FROM (SELECT dt FROM max_date))
+------------------------+
| vong_quay_phai_thu_nam |
+------------------------+
|   2.0643905335967923   |
+------------------------+
*/

--- VISUAL: Vòng quay phải thu hiện tại
WITH max_date AS (
    -- Bước 1: Tìm mốc ngày giao dịch lớn nhất trong bảng phải thu để làm mốc tham chiếu nếu cần
    SELECT MAX(posting_date) AS dt 
    FROM silver.fact_accountsreceivable
),
doanh_thu_hien_tai AS (
    -- Bước 2: Lấy toàn bộ tổng doanh thu thuần (lũy kế YTD) từ bảng kết quả kinh doanh 
    -- (tương ứng với logic không lọc cứng tháng trên Slicer của Power BI)
    SELECT SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement
    WHERE indicator_code = 'B02-DN_10'
),
latest_transactions AS (
    -- Bước 3: Sử dụng Window Function (ROW_NUMBER) để xác định dòng công nợ mới nhất của từng khách hàng
    SELECT 
        f.partner_code, 
        f.ending_debit_balance,
        ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) AS rn
    FROM silver.fact_accountsreceivable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
),
phai_thu_hien_tai AS (
    -- Bước 4: Tổng hợp tổng số dư nợ phải thu hiện tại (tại các dòng rn = 1) của toàn bộ khách hàng
    SELECT SUM(ending_debit_balance) AS val
    FROM latest_transactions
    WHERE rn = 1
)
-- Bước 5: Tính vòng quay phải thu hiện tại = Tổng doanh thu hiện tại / Tổng số dư phải thu cuối kỳ
-- Sử dụng COALESCE để đảm bảo an toàn dữ liệu trống và NULLIF ở mẫu số để tránh lỗi chia cho số 0
SELECT 
    COALESCE((SELECT val FROM doanh_thu_hien_tai), 0) / NULLIF((SELECT val FROM phai_thu_hien_tai), 0) AS vong_quay_phai_thu_hien_tai;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- Lấy toàn bộ Doanh thu chia cho Phải thu hiện tại
+-----------------------------+
| vong_quay_phai_thu_hien_tai |
+-----------------------------+
|      2.0643905335967923     |
+-----------------------------+
*/

--- VISUAL: Tổng hóa đơn (Số chứng từ đang treo nợ)
SELECT 
    -- Đếm tổng số lượng hóa đơn thỏa mãn điều kiện còn nợ từ bảng tạm bên trong
    COUNT(*) AS tong_hoa_don
FROM (
    -- Bước 1: Gom nhóm dữ liệu công nợ theo từng số hóa đơn từ bảng chi tiết phải thu
    SELECT invoice_no
    FROM silver.fact_accountsreceivable f
    -- Kết hợp với bảng danh mục đối tác để lọc đúng nhóm khách hàng
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
      -- Chỉ xét các dòng có ghi nhận số hóa đơn hợp lệ (không bị trống hoặc NULL)
      AND f.invoice_no IS NOT NULL 
      AND f.invoice_no != ''
    GROUP BY invoice_no
    -- Bước 2: Lọc điều kiện HAVING chỉ lấy những hóa đơn có tổng phát sinh Nợ trừ Có lớn hơn 0 
    -- (nghĩa là hóa đơn này vẫn còn dư nợ chưa thanh toán hết)
    HAVING SUM(debit_amount - credit_amount) > 0
) t;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- Nhóm theo hóa đơn, hóa đơn nào có Tổng phát sinh Nợ > Tổng phát sinh Có thì là chưa thu hết tiền
+--------------+
| tong_hoa_don |
+--------------+
|     2803     |
+--------------+
*/

--- VISUAL: Tổng số khách hàng
WITH latest_transactions AS (
    -- Bước 1: Sử dụng Window Function (ROW_NUMBER) để xác định dòng giao dịch công nợ mới nhất 
    -- của từng khách hàng dựa trên ngày chứng từ (posting_date) và mã giao dịch (id)
    SELECT 
        f.partner_code, 
        f.ending_debit_balance,
        ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) AS rn
    FROM silver.fact_accountsreceivable f
    -- Kết hợp với bảng danh mục đối tác để lọc đúng nhóm đối tượng khách hàng
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
)
-- Bước 2: Đếm số lượng khách hàng từ các dòng giao dịch mới nhất (rn = 1) 
-- mà có số dư nợ cuối kỳ lớn hơn 0 (tức là vẫn đang nợ tiền doanh nghiệp)
SELECT 
    COUNT(*) AS tong_khach_hang
FROM latest_transactions
WHERE rn = 1 
  AND ending_debit_balance > 0;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- Lấy khách hàng có số dư nợ cuối cùng > 0
+-----------------+
| tong_khach_hang |
+-----------------+
|       694       |
+-----------------+
*/

--- VISUAL: Phải thu theo tháng (Phân bổ Trong hạn / Quá hạn bằng logic FIFO)
WITH rng AS (
    -- Bước 1: Xác định khoảng thời gian mốc (ngày bắt đầu và ngày kết thúc tối đa) có phát sinh giao dịch công nợ
    SELECT MIN(posting_date) AS min_d, MAX(posting_date) AS max_d
    FROM silver.fact_accountsreceivable
),
report_months AS (
    -- Bước 2: Tạo danh sách các mốc ngày chốt báo cáo theo từng tháng trong năm 2026 (ngày cuối tháng)
    -- Chỉ lấy những tháng có dữ liệu tính đến trước hoặc bằng ngày giao dịch mới nhất trong hệ thống
    SELECT (date_trunc('month', gs) + interval '1 month - 1 day')::date AS report_date
    FROM generate_series('2026-01-01'::date, '2026-12-01'::date, interval '1 month') gs
    WHERE (date_trunc('month', gs) + interval '1 month - 1 day')::date <= (SELECT max_d FROM rng)
),
cust_balances AS (
    -- Bước 3: Tính toán số dư công nợ lũy kế của từng khách hàng tại từng mốc tháng báo cáo
    SELECT 
        m.report_date, 
        f.partner_code, 
        f.ending_debit_balance AS total_debt,
        ROW_NUMBER() OVER (
            PARTITION BY m.report_date, f.partner_code 
            ORDER BY f.posting_date DESC, f.id DESC
        ) AS rn
    FROM report_months m
    JOIN silver.fact_accountsreceivable f ON f.posting_date <= m.report_date
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
),
positive_balances AS (
    -- Bước 4: Lọc ra các dòng số dư mới nhất (rn = 1) và chỉ lấy những khách hàng đang có dư nợ dương (> 0)
    SELECT report_date, partner_code, total_debt
    FROM cust_balances 
    WHERE rn = 1 AND total_debt > 0
),
invoices AS (
    -- Bước 5: Gom nhóm chi tiết các phát sinh theo từng số hóa đơn của từng khách hàng tính đến thời điểm báo cáo
    SELECT 
        m.report_date, 
        f.partner_code, 
        f.invoice_no,
        MIN(f.invoice_date) AS invoice_date,
        SUM(f.debit_amount) AS debit_amount
    FROM report_months m
    JOIN silver.fact_accountsreceivable f ON f.posting_date <= m.report_date
    JOIN positive_balances pb ON pb.report_date = m.report_date AND pb.partner_code = f.partner_code
    WHERE f.debit_amount > 0 AND f.invoice_no IS NOT NULL AND f.invoice_no <> ''
    GROUP BY m.report_date, f.partner_code, f.invoice_no
),
invoices_running AS (
    -- Bước 6: Sắp xếp hóa đơn theo thời gian giảm dần và tính tổng cộng dồn (running total) giá trị nợ hóa đơn
    SELECT 
        i.*,
        SUM(i.debit_amount) OVER (
            PARTITION BY i.report_date, i.partner_code
            ORDER BY i.invoice_date DESC, i.invoice_no DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_total
    FROM invoices i
),
unpaid_invoices AS (
    -- Bước 7: Áp dụng thuật toán FIFO để phân bổ tổng số dư nợ thực tế vào các hóa đơn chưa thanh toán
    SELECT 
        r.report_date, 
        r.partner_code, 
        r.invoice_no, 
        r.invoice_date,
        LEAST(
            r.debit_amount,
            GREATEST(0, pb.total_debt - (r.running_total - r.debit_amount))
        ) AS unpaid_amount
    FROM invoices_running r
    JOIN positive_balances pb USING (report_date, partner_code)
),
categorized AS (
    -- Bước 8: Phân loại hóa đơn thành "Trong hạn" (<= 30 ngày) hoặc "Quá hạn" (> 30 ngày) dựa trên khoảng cách ngày
    SELECT 
        pb.report_date, 
        pb.partner_code, 
        pb.total_debt,
        COALESCE(SUM(ui.unpaid_amount), 0) AS total_inv_unpaid,
        COALESCE(SUM(CASE WHEN pb.report_date - ui.invoice_date <= 30 THEN ui.unpaid_amount END), 0) AS no_trong_han,
        COALESCE(SUM(CASE WHEN pb.report_date - ui.invoice_date > 30 THEN ui.unpaid_amount END), 0) AS no_qua_han,
        COUNT(DISTINCT CASE WHEN ui.unpaid_amount > 0 THEN ui.invoice_no END) AS so_hd
    FROM positive_balances pb
    LEFT JOIN unpaid_invoices ui USING (report_date, partner_code)
    GROUP BY pb.report_date, pb.partner_code, pb.total_debt
)
-- Bước 9: Tổng hợp kết quả cuối cùng theo từng tháng để đưa lên biểu đồ phân tích
SELECT 
    TO_CHAR(c.report_date, 'YYYY-MM') AS thang_nam,
    SUM(no_trong_han)                                           AS trong_han,
    SUM(no_qua_han)                                             AS qua_han_hoa_don,
    SUM(GREATEST(0, total_debt - total_inv_unpaid))             AS du_dau_ky_khac,
    -- Cộng dồn phần dư đầu kỳ cũ hơn 30 ngày vào tổng nợ quá hạn
    SUM(no_qua_han)
      + CASE WHEN c.report_date - ((SELECT min_d FROM rng) - 1) > 30
             THEN SUM(GREATEST(0, total_debt - total_inv_unpaid)) ELSE 0 END AS qua_han_tong,
    SUM(total_debt)                                             AS tong_du_no,
    SUM(so_hd)                                                  AS tong_so_hoa_don_no
FROM categorized c
GROUP BY c.report_date
ORDER BY c.report_date;


-- VISUAL: Hệ số Vòng quay phải thu theo tháng (Monthly Receivable Turnover with Average Debt)

WITH doanh_thu AS (
    -- Bước 1: Tổng hợp doanh thu thực tế theo từng tháng từ bảng kết quả kinh doanh (Chỉ tiêu Doanh thu thuần B02-DN_10)
    SELECT 
        DATE_TRUNC('month', month) AS MONTH, 
        SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement 
    WHERE indicator_code = 'B02-DN_10' 
    GROUP BY 1
),
months AS (
    -- Bước 2: Tạo chuỗi các mốc thời gian bắt đầu từ tháng 01/2026 đến tháng 08/2026
    SELECT 
        generate_series('2026-01-01'::date, '2026-08-01'::date, '1 month'::interval) AS start_month
),
cust_balances AS (
    -- Bước 3: Xác định số dư công nợ của từng khách hàng tại thời điểm cuối mỗi tháng trong khoảng thời gian đã tạo
    SELECT 
        m.start_month,
        f.partner_code, 
        f.ending_debit_balance,
        ROW_NUMBER() OVER (
            PARTITION BY m.start_month, f.partner_code 
            ORDER BY f.posting_date DESC, f.id DESC
        ) AS rn
    FROM months m
    -- Lấy các giao dịch công nợ phát sinh từ đầu năm đến ngày cuối cùng của tháng đó
    JOIN silver.fact_accountsreceivable f ON f.posting_date <= (m.start_month + interval '1 month - 1 day')
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
),
monthly_debt AS (
    -- Bước 4: Tổng hợp tổng số dư nợ phải thu cuối kỳ của toàn bộ khách hàng (rn = 1) theo từng tháng
    SELECT 
        start_month, 
        SUM(ending_debit_balance) AS total_debt
    FROM cust_balances
    WHERE rn = 1
    GROUP BY start_month
),
monthly_avg_debt AS (
    -- Bước 5: Tính số dư công nợ bình quân tháng (Trung bình cộng giữa dư nợ cuối tháng hiện tại và dư nợ tháng trước)
    -- Sử dụng hàm LAG để lấy số dư của tháng trước, nếu không có (tháng đầu tiên) thì lấy chính giá trị hiện tại
    SELECT 
        start_month, 
        total_debt,
        LAG(total_debt) OVER (ORDER BY start_month) AS prev_debt,
        (total_debt + COALESCE(LAG(total_debt) OVER (ORDER BY start_month), total_debt)) / 2.0 AS avg_debt
    FROM monthly_debt
)
-- Bước 6: Tính hệ số vòng quay phải thu theo tháng = Doanh thu tháng / Số dư nợ phải thu bình quân tháng
-- Sử dụng NULLIF ở mẫu số để tránh lỗi chia cho số 0
SELECT 
    d.start_month AS MONTH, 
    dt.val / NULLIF(d.avg_debt, 0) AS vong_quay_thang
FROM monthly_avg_debt d
LEFT JOIN doanh_thu dt ON d.start_month = dt.MONTH
ORDER BY d.start_month;

/* RESULT LOG:
-- GHI CHÚ FILTER: Tính bằng Doanh thu / Trung bình Cộng dư nợ Phải Thu 2 tháng liên tiếp
+---------------------------+---------------------+
|           month           |   vong_quay_thang   |
+---------------------------+---------------------+
| 2026-01-01 00:00:00+00:00 |         None        |
| 2026-02-01 00:00:00+00:00 |         None        |
| 2026-03-01 00:00:00+00:00 |         None        |
| 2026-04-01 00:00:00+00:00 |         None        |
| 2026-05-01 00:00:00+00:00 |         None        |
| 2026-06-01 00:00:00+00:00 |         None        |
| 2026-07-01 00:00:00+00:00 | 2.5765233603817983  |
| 2026-08-01 00:00:00+00:00 |        0E-28        |
+---------------------------+---------------------+
*/

--- VISUAL: Top 10 KH nợ cao nhất
SELECT 
    -- Lấy tên khách hàng từ bảng danh mục đối tác
    p.partner_name AS ten_khach_hang,
    
    -- Lấy số dư nợ cuối kỳ của khách hàng đó tại giao dịch mới nhất
    f.ending_debit_balance AS du_no_cuoi_ky
FROM silver.fact_accountsreceivable f
-- Kết hợp với bảng danh mục đối tác để lấy tên tương ứng với mã đối tác
JOIN silver.dim_partner p ON f.partner_code = p.partner_code
-- Lọc điều kiện cốt lõi: Chỉ lấy dòng giao dịch có mã định danh (id) lớn nhất của từng khách hàng 
-- (tương ứng với bản ghi/chứng từ cập nhật số dư mới nhất)
WHERE f.id IN (
    SELECT MAX(id)
    FROM silver.fact_accountsreceivable
    GROUP BY partner_code
) 
-- Chỉ lấy các đối tượng thuộc nhóm khách hàng thuần túy hoặc nhóm kiêm nhiệm cả nhà cung cấp
  AND p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
-- Chỉ chọn những khách hàng đang thực sự còn dư nợ dương lớn hơn 0
  AND f.ending_debit_balance > 0
-- Sắp xếp giảm dần theo số dư nợ cuối kỳ để đưa các khách hàng nợ nhiều nhất lên đầu
ORDER BY du_no_cuoi_ky DESC
-- Giới hạn chỉ lấy đúng 10 khách hàng đứng đầu bảng xếp hạng
LIMIT 10;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- Lấy "Dư nợ cuối kỳ" của từng khách hàng (dựa trên bản ghi mới nhất) và lọc Top 10.
+--------------------------------------------------+-----------------+
|                 ten_khach_hang                   |  du_no_cuoi_ky  |
+--------------------------------------------------+-----------------+
| CÔNG TY CỔ PHẦN YEAHOME                          |  11468115310.00 |
| CÔNG TY CỔ PHẦN THƯƠNG MẠI DỊCH VỤ VIỆT ĐỨC HÀ N |   6431709533.00 |
| Công ty TNHH thương mại và khai thác khoáng sản  |   2526943621.00 |
| Anh Lâm AIS                                      |    739242725.00 |
| CÔNG TY TNHH ĐẦU TƯ HÒA PHÚ                      |    599111964.00 |
| CÔNG TY CỔ PHẦN SẢN XUẤT PHÚ QUANG               |    539770700.00 |
| Công ty Cổ phần nội thất Hà Lâm                  |    533196628.00 |
| CÔNG TY CỔ PHẦN KINH DOANH GẠCH ỐP LÁT VIGLACERA |    520000000.00 |
| CÔNG TY CỔ PHẦN ĐẦU TƯ XÂY DỰNG VÀ NỘI THẤT HOÀN |    485914545.00 |
| Nội Thất Phong Lâm                               |    455108097.00 |
+--------------------------------------------------+-----------------+
*/

--- VISUAL: Top 10 KH dư nợ quá hạn (Nợ xấu)
-- THEO ĐÚNG CHUẨN CÔNG THỨC TRONG BRD:
-- + Số tiền còn nợ = Phát sinh nợ - Phát sinh có
-- + Ngày đáo hạn = Ngày hóa đơn + 30
-- + Số ngày quá hạn = Ngày hiện tại - Ngày đáo hạn
-- + Nợ quá hạn = Số tiền còn nợ khi Số ngày quá hạn > 0
WITH max_date AS (
    -- Bước 1: Khởi tạo mốc thời gian hiện tại (giả lập ngày chốt báo cáo cho Power BI)
    SELECT '2026-07-31'::date AS dt
), 
khach_hang_no AS (
    -- Bước 2: Tổng hợp số liệu công nợ theo từng khách hàng dựa trên hóa đơn phát sinh
    SELECT 
        p.partner_name AS ten_khach_hang,
        
        -- Nợ trong hạn: Phân bổ số tiền còn nợ nếu số ngày quá hạn <= 0 (chưa đến hạn thanh toán)
        SUM(CASE WHEN (SELECT dt FROM max_date) - (f.invoice_date + 30) <= 0 
                 THEN f.debit_amount - f.credit_amount ELSE 0 END) AS no_trong_han,
        
        -- Nợ quá hạn (Nợ xấu): Phân bổ số tiền còn nợ nếu số ngày quá hạn > 0 (đã quá thời hạn 30 ngày)
        SUM(CASE WHEN (SELECT dt FROM max_date) - (f.invoice_date + 30) > 0 
                 THEN f.debit_amount - f.credit_amount ELSE 0 END) AS no_qua_han,
        
        -- Số dư tổng (Tổng nợ hiện tại) = Tổng phát sinh nợ trừ đi tổng phát sinh có của khách hàng
        SUM(f.debit_amount - f.credit_amount) AS so_tien_con_no,
        
        -- Thống kê tổng số lượng hóa đơn có phát sinh giao dịch
        COUNT(DISTINCT f.invoice_no) AS so_hoa_don
    FROM silver.fact_accountsreceivable f
    -- Kết hợp với bảng danh mục đối tác để lấy tên khách hàng
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    -- Chỉ xét các đối tượng thuộc nhóm khách hàng và lọc các giao dịch tính đến trước ngày chốt báo cáo
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
      AND f.posting_date <= '2026-07-31'
    GROUP BY p.partner_name
    -- Bước 3: Lọc điều kiện HAVING chỉ lấy những khách hàng thực sự có tổng số tiền nợ quá hạn lớn hơn 0
    HAVING SUM(CASE WHEN (SELECT dt FROM max_date) - (f.invoice_date + 30) > 0 
                    THEN f.debit_amount - f.credit_amount ELSE 0 END) > 0
)
-- Bước 4: Trình bày kết quả chi tiết, tính tỷ lệ quá hạn và giới hạn Top 10 khách hàng nợ xấu cao nhất
SELECT 
    ten_khach_hang,
    no_trong_han,
    no_qua_han,
    so_tien_con_no,
    -- Tính tỷ lệ nợ quá hạn trên tổng số tiền còn nợ (Dùng NULLIF ở mẫu số để tránh lỗi chia cho 0)
    no_qua_han / NULLIF(so_tien_con_no, 0) AS ty_le_qua_han,
    so_hoa_don
FROM khach_hang_no
-- Sắp xếp giảm dần theo giá trị nợ quá hạn để đưa các khách hàng nợ xấu nặng nhất lên đầu
ORDER BY no_qua_han DESC
LIMIT 10;

/* RESULT LOG:
-- GHI CHÚ FILTER: Tính toán hoàn toàn dựa trên công thức Phát Sinh Nợ - Phát Sinh Có của BRD.
+--------------------------------------------------+-----------------+-----------------+-----------------+----------------------+------------+
|                 ten_khach_hang                   |  no_trong_han   |   no_qua_han    | so_tien_con_no  |    ty_le_qua_han     | so_hoa_don |
+--------------------------------------------------+-----------------+-----------------+-----------------+----------------------+------------+
| CÔNG TY TNHH GỖ QUỐC TẾ NTT                      |       0         |  64293042519.00 | -21609121873.00 | -2.9752732733973347  |     48     |
| CÔNG TY TNHH ĐẦU TƯ XÂY DỰNG DACINCO             |       0         |  44130699389.00 |  4660001000.00  |  9.4701051328100573  |    168     |
| CÔNG TY CỔ PHẦN YEAHOME                          |       0         |  35369154900.00 |  14105488530.00 |  2.5074746489478731  |     27     |
| CÔNG TY CỔ PHẦN THƯƠNG MẠI DỊCH VỤ VIỆT ĐỨC HÀ N |       0         |  28230967681.00 |  7975099091.00  |  3.5398892676906050  |     85     |
| CÔNG TY CỔ PHẦN 3T GROUP VIỆT NAM                |       0         |  20454076000.00 |  -1469812829.00 | -13.9161093143513445 |     23     |
| Công ty Cổ phần nội thất Hà Lâm                  |       0         |  10955234838.00 |   479329518.00  | 22.8553310960498786  |     11     |
| CÔNG TY CỔ PHẦN ĐẦU TƯ XÂY DỰNG VÀ NỘI THẤT HOÀN |  1128169190.00  |   8943048994.00 |  -1181163746.00 | -7.5713876020556277  |     38     |
| Công ty TNHH thương mại và khai thác khoáng sản  |       0         |   7053791083.00 | -34509747970.00 | -0.20440010359702220 |    137     |
| CÔNG TY CỔ PHẦN XÂY DỰNG VIDC                    |       0         |   4624894629.00 | -34994273060.00 | -0.13216147116805844 |     51     |
| CÔNG TY CỔ PHẦN ĐẦU TƯ XÂY DỰNG VÀ THƯƠNG MẠI LI |       0         |   2503109070.00 | -29547143924.00 | -0.08471576404285888 |     23     |
+--------------------------------------------------+-----------------+-----------------+-----------------+----------------------+------------+
*/

-- VISUAL: Tuổi nợ Aging
-- MEASURE: _CongNo[Aging]
WITH params AS (SELECT DATE '2026-07-31' AS d),
cust AS (
  SELECT DISTINCT ON (f.partner_code) f.partner_code, f.ending_debit_balance AS total_debt
  FROM silver.fact_accountsreceivable f
  JOIN silver.dim_partner p ON p.partner_code = f.partner_code
  WHERE p.partner_group IN ('Khách hàng','Khách hàng/ nhà cung cấp')
    AND f.posting_date <= (SELECT d FROM params)
  ORDER BY f.partner_code, f.posting_date DESC, f.id DESC),
pos AS (SELECT * FROM cust WHERE total_debt > 0),
docs AS (
  SELECT f.partner_code,
         COALESCE(NULLIF(f.invoice_no,''), 'ROW-' || f.id)  AS doc_key,
         MIN(COALESCE(f.invoice_date, f.posting_date))      AS doc_date,
         SUM(f.debit_amount)                                AS amt
  FROM silver.fact_accountsreceivable f
  JOIN pos USING (partner_code)
  WHERE f.debit_amount > 0 AND f.posting_date <= (SELECT d FROM params)
  GROUP BY 1, 2),
run AS (
  SELECT d.partner_code, d.doc_date, d.amt, pos.total_debt,
         SUM(d.amt) OVER (PARTITION BY d.partner_code
                          ORDER BY d.doc_date DESC, d.doc_key DESC
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum
  FROM docs d JOIN pos USING (partner_code)),
unpaid AS (
  SELECT partner_code, doc_date,
         LEAST(amt, GREATEST(0, total_debt - (cum - amt))) AS unpaid
  FROM run),
rest AS (
  SELECT p.partner_code, GREATEST(0, p.total_debt - COALESCE(SUM(u.unpaid), 0)) AS unpaid
  FROM pos p LEFT JOIN unpaid u USING (partner_code)
  GROUP BY p.partner_code, p.total_debt),
allrows AS (
  SELECT (SELECT d FROM params) - doc_date AS days, unpaid FROM unpaid WHERE unpaid > 0
  UNION ALL
  SELECT NULL, unpaid FROM rest WHERE unpaid > 0)
SELECT CASE WHEN days IS NULL THEN 'Khác (không có chứng từ)'
            WHEN days <= 0   THEN 'Current'
            WHEN days <= 30  THEN '1-30'
            WHEN days <= 60  THEN '31-60'
            WHEN days <= 90  THEN '61-90'
            WHEN days <= 120 THEN '91-120'
            WHEN days <= 150 THEN '121-150'
            WHEN days <= 180 THEN '151-180'
            ELSE '180+' END AS bucket,
       SUM(unpaid) AS gia_tri
FROM allrows
GROUP BY 1
ORDER BY MIN(COALESCE(days, 99999));


-- VISUAL: Bảng chi tiết các hóa đơn đang nợ
-- MEASURE: _CongNo[Chi_Tiet_Hoa_Don]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable)
SELECT voucher_no AS so_chung_tu,
       posting_date AS ngay_hach_toan,
       invoice_no AS so_hoa_don,
       invoice_date AS ngay_hoa_don,
       description AS mo_ta,
       debit_amount AS phat_sinh_no,
       (debit_amount - credit_amount) AS so_tien_con_no,
       ((SELECT dt FROM max_date) - invoice_date - 30) AS so_ngay_qua_han
FROM silver.fact_accountsreceivable
WHERE (debit_amount - credit_amount) > 0;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE (debit_amount - credit_amount) > 0;
+-------------+----------------+------------+--------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+---------------+----------------+-----------------+
| so_chung_tu | ngay_hach_toan | so_hoa_don | ngay_hoa_don |                                                                                                        mo_ta                                                                                                        |  phat_sinh_no | so_tien_con_no | so_ngay_qua_han |
+-------------+----------------+------------+--------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+---------------+----------------+-----------------+
|   BH00729   |   2026-01-22   |  00000760  |  2026-01-22  |                                                                                          MDF 6 DA CA E2 4x8 2M Mine 6124 T                                                                                          |   7055556.00  |   7055556.00   |       161       |
|   BH00729   |   2026-01-22   |  00000760  |  2026-01-22  |                                                                                    Thuế GTGT - MDF 6 DA CA E2 4x8 2M Mine 6124 T                                                                                    |   564444.00   |   564444.00    |       161       |
|   BH03672   |   2026-04-29   |  00002887  |  2026-04-29  |                                                                                                 Nẹp 21x1 Class 226 T                                                                                                |   694500.00   |   694500.00    |        64       |
|   BH03672   |   2026-04-29   |  00002887  |  2026-04-29  |                                                                                           Thuế GTGT - Nẹp 21x1 Class 226 T                                                                                          |    55560.00   |    55560.00    |        64       |
|   BH00041   |   2026-01-06   |  00000103  |  2026-01-06  |                                                                                                Nẹp 21x1 Class 2382 C1                                                                                               |   291700.00   |   291700.00    |       177       |
|   BH00041   |   2026-01-06   |  00000103  |  2026-01-06  |                                                                                          Thuế GTGT - Nẹp 21x1 Class 2382 C1                                                                                         |    23336.00   |    23336.00    |       177       |
|   BH00100   |   2026-01-06   |  00000104  |  2026-01-06  |                                                                                         MDF 17 ML HMR E1 4x9 2M Mine 2382 V4                                                                                        |   5255556.00  |   5255556.00   |       177       |
|   BH00100   |   2026-01-06   |  00000104  |  2026-01-06  |                                                                                   Thuế GTGT - MDF 17 ML HMR E1 4x9 2M Mine 2382 V4                                                                                  |   420444.00   |   420444.00    |       177       |
|   BH00153   |   2026-01-07   |  00000164  |  2026-01-07  |                                                                                                Nẹp 21x1 Class 2382 C1                                                                                               |   291700.00   |   291700.00    |       176       |
|   BH00153   |   2026-01-07   |  00000164  |  2026-01-07  |                                                                                          Thuế GTGT - Nẹp 21x1 Class 2382 C1                                                                                         |    23336.00   |    23336.00    |       176       |
|   BH00198   |   2026-01-08   |  00000210  |  2026-01-08  |                                                                                         MDF 17 ML HMR E2 4x8 2M mine 2041V1                                                                                         |   4893520.00  |   4893520.00   |       175       |
|   BH00198   |   2026-01-08   |  00000210  |  2026-01-08  |                                                                                   Thuế GTGT - MDF 17 ML HMR E2 4x8 2M mine 2041V1                                                                                   |   391482.00   |   391482.00    |       175       |
|   BH00198   |   2026-01-08   |  00000210  |  2026-01-08  |                                                                                                Nẹp 21x1 Class 2041 VI                                                                                               |   291700.00   |   291700.00    |       175       |
|   BH00112   |   2026-01-06   |  00000122  |  2026-01-06  |                                                                                         MDF 5.5 DA CA E2 4x8 1M mine 041 EV                                                                                         |   1466670.00  |   1466670.00   |       177       |
|   BH00112   |   2026-01-06   |  00000122  |  2026-01-06  |                                                                                   Thuế GTGT - MDF 5.5 DA CA E2 4x8 1M mine 041 EV                                                                                   |   117334.00   |   117334.00    |       177       |
|   BH00112   |   2026-01-06   |  00000122  |  2026-01-06  |                                                                                         MDF 5.5 DA CA E2 4x8 1M Mine 2023 EV                                                                                        |   5683338.00  |   5683338.00   |       177       |
|   BH00112   |   2026-01-06   |  00000122  |  2026-01-06  |                                                                                   Thuế GTGT - MDF 5.5 DA CA E2 4x8 1M Mine 2023 EV                                                                                  |   454667.00   |   454667.00    |       177       |
...(TRUNCATED FOR READABILITY)...
*/

--- VISUAL: Bảng chi tiết nợ theo Khách hàng
WITH max_date AS (
    -- Bước 1: Lấy mốc thời gian mới nhất có phát sinh giao dịch trong hệ thống để làm ngày chốt báo cáo ảo
    SELECT MAX(posting_date) AS dt 
    FROM silver.fact_accountsreceivable
)
SELECT 
    partner_code AS ma_khach_hang,
    
    -- 1. NỢ TRONG HẠN: Khoảng cách từ ngày chốt báo cáo đến ngày hóa đơn <= 30 ngày
    SUM(
        CASE WHEN invoice_date IS NOT NULL AND (SELECT dt FROM max_date) <= invoice_date + 30 
             THEN debit_amount - credit_amount ELSE 0 
        END
    ) AS no_trong_han,
    
    -- 2. TỶ TRỌNG TRONG HẠN: = Nợ trong hạn / Tổng dư nợ (Dùng NULLIF ở mẫu số để tránh lỗi Divide by Zero)
    SUM(
        CASE WHEN invoice_date IS NOT NULL AND (SELECT dt FROM max_date) <= invoice_date + 30 
             THEN debit_amount - credit_amount ELSE 0 
        END
    ) / NULLIF(SUM(debit_amount - credit_amount), 0) AS phan_tram_trong_han,
    
    -- 3. NỢ QUÁ HẠN: Khoảng cách từ ngày chốt báo cáo đến ngày hóa đơn > 30 ngày
    SUM(
        CASE WHEN invoice_date IS NOT NULL AND (SELECT dt FROM max_date) > invoice_date + 30 
             THEN debit_amount - credit_amount ELSE 0 
        END
    ) AS no_qua_han,
    
    -- 4. TỶ TRỌNG QUÁ HẠN: = Nợ quá hạn / Tổng dư nợ
    SUM(
        CASE WHEN invoice_date IS NOT NULL AND (SELECT dt FROM max_date) > invoice_date + 30 
             THEN debit_amount - credit_amount ELSE 0 
        END
    ) / NULLIF(SUM(debit_amount - credit_amount), 0) AS phan_tram_qua_han,
    
    -- 5. TỔNG DƯ NỢ: Lấy toàn bộ phát sinh Nợ trừ đi phát sinh Có của khách hàng đó
    SUM(debit_amount - credit_amount) AS du_no_phai_thu

FROM silver.fact_accountsreceivable
GROUP BY 1 -- Gom nhóm theo cột số 1 (partner_code)
-- Bước 2: Bộ lọc mức tập hợp (HAVING) chỉ giữ lại những khách hàng đang thực sự có tổng dư nợ dương
HAVING SUM(debit_amount - credit_amount) > 0;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- HAVING SUM(debit_amount - credit_amount) > 0;
+------------------------+----------------+-------------------------+----------------+------------------------+----------------+
|     ma_khach_hang      |  no_trong_han  |   phan_tram_trong_han   |   no_qua_han   |   phan_tram_qua_han    | du_no_phai_thu |
+------------------------+----------------+-------------------------+----------------+------------------------+----------------+
|       0110643010       |       0        |          0E-24          |  19278758.00   |   6.0006878824984639   |   3212758.00   |
|       0106625675       |       0        |          0E-24          |   3114000.00   | 1.00000000000000000000 |   3114000.00   |
|       2902047024       |       0        |          0E-24          |   1800001.00   | 1.00000000000000000000 |   1800001.00   |
|       0108190010       |       0        |          0E-24          |   7739719.00   | 1.00000000000000000000 |   7739719.00   |
|       0107455169       |       0        |          0E-20          |   3526001.00   |  3526001.000000000000  |      1.00      |
|       0108140549       |   1190000.00   |   29.7462817147856518   |   3075000.00   |  76.8653918260217473   |    40005.00    |
|       8190857186       |       0        |          0E-24          |  63554009.00   | 1.00000000000000000000 |  63554009.00   |
|       0107984606       |   5416001.00   |    2.1663995334401866   |       0        |         0E-24          |   2500001.00   |
|       0106703228       |       0        |          0E-20          |   1554001.00   |  1554001.000000000000  |      1.00      |
|       0901086796       |   5995035.00   |    1.6030778379994347   |  222139668.00  |  59.4003502417170561   |   3739703.00   |
|       0106684141       |       0        |          0E-24          |   1262000.00   | 1.00000000000000000000 |   1262000.00   |
|       2902142415       |   3040000.00   |  0.09553126128541585826 |  219491644.00  |   6.8974715766215395   |  31822044.00   |
|       0111343411       |       0        |          0E-20          |  44680718.00   | 5125.1110346409727002  |    8718.00     |
|       0901236032       |   4019045.00   |    18606.689814814815   |  54456171.00   |  252111.902777777778   |     216.00     |
|       0106184815       |  13476008.00   |  0.44926040765990540600 |  50623976.00   |   1.6876917923412681   |  29995984.00   |
|       0107391733       |       0        |          0E-20          |   6808003.00   |  2269334.333333333333  |      3.00      |
| M300DAH2TMX2340XXXXSX  |  24058554.00   |  1.00000000000000000000 |       0        |         0E-24          |  24058554.00   |
...(TRUNCATED FOR READABILITY)...
*/

