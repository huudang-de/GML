-- ==========================================
-- DASHBOARD: QUẢN TRỊ PHẢI THU - PHẢI TRẢ
-- ==========================================

-- VISUAL: Giá trị phải thu
-- MEASURE: _CongNo[Gia_Tri_Phai_Thu]
WITH latest_transactions AS (
    SELECT 
        f.partner_code,
        f.ending_debit_balance,
        ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM silver.fact_accountsreceivable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
)
SELECT SUM(ending_debit_balance) AS gia_tri_phai_thu
FROM latest_transactions
WHERE rn = 1;

/* RESULT LOG:
+------------------+
| gia_tri_phai_thu |
+------------------+
|  36326095573.00  |
+------------------+
*/

-- VISUAL: Giá trị phải trả
-- MEASURE: _CongNo[Gia_Tri_Phai_Tra]
WITH latest_transactions AS (
    SELECT 
        f.partner_code,
        f.ending_credit_balance,
        ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM silver.fact_accountspayable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Nhà cung cấp', 'Khách hàng/ nhà cung cấp')
)
SELECT SUM(ending_credit_balance) AS gia_tri_phai_tra
FROM latest_transactions
WHERE rn = 1;

/* RESULT LOG:
+------------------+
| gia_tri_phai_tra |
+------------------+
|  60452900187.23  |
+------------------+
*/

-- VISUAL: Vòng quay phải thu theo năm
-- MEASURE: _CongNo[VQ_Phai_Thu_Nam]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable),
doanh_thu_nam AS (
    SELECT SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement
    WHERE indicator_code='B02-DN_10' AND EXTRACT(YEAR FROM month) = EXTRACT(YEAR FROM (SELECT dt FROM max_date))
),
latest_transactions AS (
    SELECT f.partner_code, f.ending_debit_balance,
           ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM silver.fact_accountsreceivable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
),
phai_thu_cuoi_nam AS (
    SELECT SUM(ending_debit_balance) AS val
    FROM latest_transactions
    WHERE rn = 1
)
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

-- VISUAL: Vòng quay phải thu hiện tại
-- MEASURE: _CongNo[VQ_Phai_Thu_Thang]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable),
doanh_thu_hien_tai AS (
    -- Trong DAX, người dùng không chọn tháng cụ thể nên nó lấy toàn bộ Doanh thu (YTD)
    SELECT SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement
    WHERE indicator_code='B02-DN_10'
),
latest_transactions AS (
    SELECT f.partner_code, f.ending_debit_balance,
           ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM silver.fact_accountsreceivable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
),
phai_thu_hien_tai AS (
    SELECT SUM(ending_debit_balance) AS val
    FROM latest_transactions
    WHERE rn = 1
)
-- Vì Đầu kỳ = 0 nên Average = Cuối kỳ (theo logic DAX phòng hờ ISBLANK của user)
SELECT COALESCE((SELECT val FROM doanh_thu_hien_tai), 0) / NULLIF((SELECT val FROM phai_thu_hien_tai), 0) AS vong_quay_phai_thu_hien_tai;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- Lấy toàn bộ Doanh thu chia cho Phải thu hiện tại
+-----------------------------+
| vong_quay_phai_thu_hien_tai |
+-----------------------------+
|      2.0643905335967923     |
+-----------------------------+
*/

-- VISUAL: Tổng hóa đơn (Số chứng từ đang treo nợ)
-- MEASURE: _CongNo[Tong_Hoa_Don]
SELECT COUNT(*) AS tong_hoa_don
FROM (
    SELECT invoice_no
    FROM silver.fact_accountsreceivable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
      AND f.invoice_no IS NOT NULL AND f.invoice_no != ''
    GROUP BY invoice_no
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

-- VISUAL: Tổng số khách hàng
-- MEASURE: _CongNo[Tong_KH]
WITH latest_transactions AS (
    SELECT f.partner_code, f.ending_debit_balance,
           ROW_NUMBER() OVER (PARTITION BY f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM silver.fact_accountsreceivable f
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
)
SELECT COUNT(*) AS tong_khach_hang
FROM latest_transactions
WHERE rn = 1 AND ending_debit_balance > 0;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- Lấy khách hàng có số dư nợ cuối cùng > 0
+-----------------+
| tong_khach_hang |
+-----------------+
|       694       |
+-----------------+
*/

-- VISUAL: Phải thu theo tháng (Phân bổ Trong hạn / Quá hạn bằng logic FIFO)
-- MEASURE: _CongNo[Phai_Thu_Thang]
WITH months AS (
    SELECT generate_series('2026-01-01'::date, '2026-08-01'::date, '1 month'::interval) as end_of_month
),
cust_balances AS (
    SELECT m.end_of_month, f.partner_code, f.ending_debit_balance as total_debt,
           ROW_NUMBER() OVER (PARTITION BY m.end_of_month, f.partner_code ORDER BY f.posting_date DESC, f.id DESC) as rn
    FROM months m
    JOIN silver.fact_accountsreceivable f ON f.posting_date <= (m.end_of_month + interval '1 month - 1 day')
    JOIN silver.dim_partner p ON f.partner_code = p.partner_code
    WHERE p.partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
),
positive_balances AS (
    SELECT end_of_month, partner_code, total_debt
    FROM cust_balances
    WHERE rn = 1 AND total_debt > 0
),
invoices AS (
    SELECT m.end_of_month, f.partner_code, f.invoice_no, f.invoice_date, f.debit_amount
    FROM months m
    JOIN silver.fact_accountsreceivable f ON f.posting_date <= (m.end_of_month + interval '1 month - 1 day')
    WHERE f.debit_amount > 0 AND f.invoice_no IS NOT NULL AND f.invoice_no != ''
),
invoices_running AS (
    SELECT i.end_of_month, i.partner_code, i.invoice_no, i.invoice_date, i.debit_amount,
           SUM(i.debit_amount) OVER (PARTITION BY i.end_of_month, i.partner_code ORDER BY i.invoice_date DESC, i.invoice_no DESC) as running_total
    FROM invoices i
    JOIN positive_balances pb ON i.partner_code = pb.partner_code AND i.end_of_month = pb.end_of_month
),
unpaid_invoices AS (
    SELECT i.end_of_month, i.partner_code, i.invoice_no, i.invoice_date,
           LEAST(i.debit_amount, GREATEST(0, pb.total_debt - (i.running_total - i.debit_amount))) as unpaid_amount
    FROM invoices_running i
    JOIN positive_balances pb ON i.partner_code = pb.partner_code AND i.end_of_month = pb.end_of_month
)
SELECT 
    end_of_month AS MONTH,
    SUM(CASE WHEN (end_of_month + interval '1 month - 1 day')::date - invoice_date <= 30 THEN unpaid_amount ELSE 0 END) as no_trong_han,
    SUM(CASE WHEN (end_of_month + interval '1 month - 1 day')::date - invoice_date > 30 THEN unpaid_amount ELSE 0 END) as no_qua_han,
    SUM(unpaid_amount) as tong_no
FROM unpaid_invoices
WHERE unpaid_amount > 0
GROUP BY end_of_month
ORDER BY end_of_month;

/* RESULT LOG:
-- GHI CHÚ FILTER: Phân bổ FIFO số dư cuối tháng vào các hóa đơn từ mới nhất lùi về cũ nhất (Đã lọc Khách Hàng)
+---------------------------+----------------+----------------+----------------+
|           month           |  no_trong_han  |   no_qua_han   |    tong_no     |
+---------------------------+----------------+----------------+----------------+
| 2026-01-01 00:00:00+00:00 |      0.00      |  8709649703.00 |  8709649703.00 |
| 2026-02-01 00:00:00+00:00 |      0.00      |  3886295551.00 |  3886295551.00 |
| 2026-03-01 00:00:00+00:00 |      0.00      |  7713795212.00 |  7713795212.00 |
| 2026-04-01 00:00:00+00:00 |      0.00      |  7178000526.00 |  7178000526.00 |
| 2026-05-01 00:00:00+00:00 |      0.00      |  3757506658.00 |  3757506658.00 |
| 2026-06-01 00:00:00+00:00 | 5064560731.00  |  6651559108.00 | 11716119839.00 |
| 2026-07-01 00:00:00+00:00 | 9741344485.00  | 13969706983.00 | 23711051468.00 |
| 2026-08-01 00:00:00+00:00 | 1858564036.00  | 21852487432.00 | 23711051468.00 |
+---------------------------+----------------+----------------+----------------+
*/

-- VISUAL: Receivable Turnover
-- MEASURE: _CongNo[VQ_Phai_Thu]
WITH doanh_thu AS (
    SELECT DATE_TRUNC('month', month) AS MONTH, SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' GROUP BY 1
),
du_no AS (
    SELECT DATE_TRUNC('month', posting_date) AS MONTH, SUM(debit_amount - credit_amount) AS val
    FROM silver.fact_accountsreceivable GROUP BY 1
)
SELECT d.MONTH, 
       dt.val / NULLIF(SUM(d.val) OVER (ORDER BY d.MONTH), 0) AS vong_quay_thang
FROM du_no d
LEFT JOIN doanh_thu dt ON d.MONTH = dt.MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' GROUP BY 1
+---------------------------+---------------------+
|           month           |   vong_quay_thang   |
+---------------------------+---------------------+
| 2026-01-01 00:00:00+00:00 |         None        |
| 2026-02-01 00:00:00+00:00 |         None        |
| 2026-03-01 00:00:00+00:00 |         None        |
| 2026-04-01 00:00:00+00:00 |         None        |
| 2026-05-01 00:00:00+00:00 |         None        |
| 2026-06-01 00:00:00+00:00 |         None        |
| 2026-07-01 00:00:00+00:00 | -1.1165575818095942 |
| 2026-08-01 00:00:00+00:00 |        0E-28        |
+---------------------------+---------------------+
*/

-- VISUAL: Top 10 KH nợ cao nhất
-- MEASURE: _CongNo[Top_10_No]
SELECT partner_code,
       SUM(debit_amount - credit_amount) AS du_no
FROM silver.fact_accountsreceivable
GROUP BY 1
HAVING SUM(debit_amount - credit_amount) > 0
ORDER BY du_no DESC
LIMIT 10;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- HAVING SUM(debit_amount - credit_amount) > 0
+--------------+----------------+
| partner_code |     du_no      |
+--------------+----------------+
|  0109506884  | 14105488530.00 |
|  0110888028  | 7975099091.00  |
|  4000443802  | 4660001000.00  |
|   KHÁCH LẺ   | 1920766207.00  |
|  2500513074  | 1598895292.00  |
|  0109953970  |  625364120.00  |
|  0105903697  |  494010946.00  |
|  0104439874  |  485966561.00  |
|  0101731327  |  479329518.00  |
|  0202111231  |  216453294.00  |
+--------------+----------------+
*/

-- VISUAL: Top 10 KH dư nợ quá hạn (Nợ xấu)
-- MEASURE: _CongNo[Top_10_Qua_Han]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable)
SELECT partner_code,
       SUM(CASE WHEN (SELECT dt FROM max_date) > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) AS no_qua_han,
       SUM(debit_amount - credit_amount) AS tong_no,
       SUM(CASE WHEN (SELECT dt FROM max_date) > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) / NULLIF(SUM(debit_amount - credit_amount), 0) AS ty_le_qua_han
FROM silver.fact_accountsreceivable
GROUP BY 1
HAVING SUM(CASE WHEN (SELECT dt FROM max_date) > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) > 0
ORDER BY no_qua_han DESC
LIMIT 10;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- HAVING SUM(CASE WHEN (SELECT dt FROM max_date) > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) > 0
+--------------+----------------+-----------------+----------------------+
| partner_code |   no_qua_han   |     tong_no     |    ty_le_qua_han     |
+--------------+----------------+-----------------+----------------------+
|  2902167353  | 66863269719.00 | -12914560655.00 | -5.1773553514662710  |
|  4000443802  | 44130699389.00 |  4660001000.00  |  9.4701051328100573  |
|  0107845264  | 40889015075.00 | -37098103542.00 | -1.1021861273503693  |
|  0109506884  | 35369154900.00 |  14105488530.00 |  2.5074746489478731  |
|  0110888028  | 28230967681.00 |  7975099091.00  |  3.5398892676906050  |
|  0106999920  | 20454076000.00 |  -1469812829.00 | -13.9161093143513445 |
|  0101587539  | 20131595310.00 |  -1934468215.00 | -10.4067852621708752 |
|  0101731327  | 10955234838.00 |   479329518.00  | 22.8553310960498786  |
|  5000815668  | 10236870882.00 |  -1181163746.00 | -8.6667669209007368  |
|  0106628901  | 10181330782.00 |  -237895571.00  | -42.7974793275995878 |
+--------------+----------------+-----------------+----------------------+
*/

-- VISUAL: Tuổi nợ Aging
-- MEASURE: _CongNo[Aging]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable),
aging_calc AS (
    SELECT 
        (SELECT dt FROM max_date) - invoice_date AS days_overdue,
        debit_amount - credit_amount AS net_amount
    FROM silver.fact_accountsreceivable
)
SELECT 
    CASE
        WHEN days_overdue <= 30 THEN 'Current'
        WHEN days_overdue BETWEEN 31 AND 60 THEN '31-60'
        WHEN days_overdue BETWEEN 61 AND 90 THEN '61-90'
        WHEN days_overdue BETWEEN 91 AND 120 THEN '91-120'
        WHEN days_overdue BETWEEN 121 AND 150 THEN '121-150'
        WHEN days_overdue BETWEEN 151 AND 180 THEN '151-180'
        ELSE '180+'
    END AS age_bucket,
    SUM(net_amount) AS gia_tri
FROM aging_calc
WHERE net_amount > 0
GROUP BY 1;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHEN days_overdue BETWEEN 31 AND 60 THEN '31-60'
-- WHEN days_overdue BETWEEN 61 AND 90 THEN '61-90'
-- WHEN days_overdue BETWEEN 91 AND 120 THEN '91-120'
-- WHEN days_overdue BETWEEN 121 AND 150 THEN '121-150'
-- WHEN days_overdue BETWEEN 151 AND 180 THEN '151-180'
-- WHERE net_amount > 0
+------------+----------------+
| age_bucket |    gia_tri     |
+------------+----------------+
|   91-120   | 68070502738.00 |
|   61-90    | 88216785939.00 |
|   31-60    | 85266702176.00 |
|  151-180   | 24500797265.00 |
|  Current   | 77860236984.00 |
|  121-150   | 70868424373.00 |
|    180+    | 68076009377.00 |
+------------+----------------+
*/

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

-- VISUAL: Bảng chi tiết nợ theo Khách hàng
-- MEASURE: _CongNo[Chi_Tiet_No_KH]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable)
SELECT partner_code AS ma_khach_hang,
       SUM(CASE WHEN (SELECT dt FROM max_date) <= invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) AS no_trong_han,
       SUM(CASE WHEN (SELECT dt FROM max_date) <= invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) / NULLIF(SUM(debit_amount - credit_amount), 0) AS phan_tram_trong_han,
       SUM(CASE WHEN (SELECT dt FROM max_date) > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) AS no_qua_han,
       SUM(CASE WHEN (SELECT dt FROM max_date) > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) / NULLIF(SUM(debit_amount - credit_amount), 0) AS phan_tram_qua_han,
       SUM(debit_amount - credit_amount) AS du_no_phai_thu
FROM silver.fact_accountsreceivable
GROUP BY 1
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

