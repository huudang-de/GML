-- ==========================================
-- DASHBOARD: QUẢN TRỊ PHẢI THU - PHẢI TRẢ
-- ==========================================

-- VISUAL: Giá trị phải thu
-- MEASURE: _CongNo[Gia_Tri_Phai_Thu]
SELECT SUM(debit_amount - credit_amount) AS gia_tri_phai_thu
FROM silver.fact_accountsreceivable;

-- VISUAL: Giá trị phải trả
-- MEASURE: _CongNo[Gia_Tri_Phai_Tra]
SELECT SUM(credit_amount - debit_amount) AS gia_tri_phai_tra
FROM silver.fact_accountspayable;

-- VISUAL: Vòng quay phải thu theo năm
-- MEASURE: _CongNo[VQ_Phai_Thu_Nam]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable),
doanh_thu AS (
    SELECT SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement
    WHERE indicator_code=''B02-DN_10'' AND EXTRACT(YEAR FROM reporting_date) = EXTRACT(YEAR FROM (SELECT dt FROM max_date))
),
du_no_avg AS (
    SELECT 
        ( (SELECT SUM(debit_amount - credit_amount) FROM silver.fact_accountsreceivable WHERE EXTRACT(YEAR FROM posting_date) <= EXTRACT(YEAR FROM (SELECT dt FROM max_date))) + 
          (SELECT SUM(debit_amount - credit_amount) FROM silver.fact_accountsreceivable WHERE EXTRACT(YEAR FROM posting_date) < EXTRACT(YEAR FROM (SELECT dt FROM max_date))) ) / 2.0 AS val
)
SELECT (SELECT val FROM doanh_thu) / NULLIF((SELECT val FROM du_no_avg), 0) AS vong_quay_phai_thu_nam;

-- VISUAL: Vòng quay phải thu hiện tại
-- MEASURE: _CongNo[VQ_Phai_Thu_Thang]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable),
doanh_thu AS (
    SELECT SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement
    WHERE indicator_code=''B02-DN_10'' AND DATE_TRUNC(''month'', reporting_date) = DATE_TRUNC(''month'', (SELECT dt FROM max_date))
),
du_no_hien_tai AS (
    SELECT SUM(debit_amount - credit_amount) AS val
    FROM silver.fact_accountsreceivable
)
SELECT (SELECT val FROM doanh_thu) / NULLIF((SELECT val FROM du_no_hien_tai), 0) AS vong_quay_phai_thu_hien_tai;

-- VISUAL: Tổng hóa đơn
-- MEASURE: _CongNo[Tong_Hoa_Don]
SELECT COUNT(DISTINCT invoice_no) AS tong_hoa_don
FROM silver.fact_accountsreceivable;

-- VISUAL: Tổng số khách hàng
-- MEASURE: _CongNo[Tong_KH]
SELECT COUNT(*) AS tong_khach_hang
FROM (
    SELECT partner_code
    FROM silver.fact_accountsreceivable
    GROUP BY partner_code
    HAVING SUM(debit_amount - credit_amount) > 0
) t;

-- VISUAL: Phải thu theo tháng
-- MEASURE: _CongNo[Phai_Thu_Thang]
WITH max_date AS (SELECT MAX(posting_date) AS dt FROM silver.fact_accountsreceivable)
SELECT DATE_TRUNC(''month'', posting_date) AS MONTH,
       SUM(CASE WHEN (SELECT dt FROM max_date) <= invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) AS no_trong_han,
       SUM(CASE WHEN (SELECT dt FROM max_date) > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) AS no_qua_han,
       SUM(debit_amount - credit_amount) AS tong_no
FROM silver.fact_accountsreceivable
GROUP BY 1;

-- VISUAL: Receivable Turnover
-- MEASURE: _CongNo[VQ_Phai_Thu]
WITH doanh_thu AS (
    SELECT DATE_TRUNC(''month'', reporting_date) AS MONTH, SUM(current_period_amount) AS val
    FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_10'' GROUP BY 1
),
du_no AS (
    SELECT DATE_TRUNC(''month'', posting_date) AS MONTH, SUM(debit_amount - credit_amount) AS val
    FROM silver.fact_accountsreceivable GROUP BY 1
)
SELECT d.MONTH, 
       dt.val / NULLIF(SUM(d.val) OVER (ORDER BY d.MONTH), 0) AS vong_quay_thang
FROM du_no d
LEFT JOIN doanh_thu dt ON d.MONTH = dt.MONTH;

-- VISUAL: Top 10 KH nợ cao nhất
-- MEASURE: _CongNo[Top_10_No]
SELECT partner_code,
       SUM(debit_amount - credit_amount) AS du_no
FROM silver.fact_accountsreceivable
GROUP BY 1
HAVING SUM(debit_amount - credit_amount) > 0
ORDER BY du_no DESC
LIMIT 10;

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
        WHEN days_overdue <= 30 THEN ''Current''
        WHEN days_overdue BETWEEN 31 AND 60 THEN ''31-60''
        WHEN days_overdue BETWEEN 61 AND 90 THEN ''61-90''
        WHEN days_overdue BETWEEN 91 AND 120 THEN ''91-120''
        WHEN days_overdue BETWEEN 121 AND 150 THEN ''121-150''
        WHEN days_overdue BETWEEN 151 AND 180 THEN ''151-180''
        ELSE ''180+''
    END AS age_bucket,
    SUM(net_amount) AS gia_tri
FROM aging_calc
WHERE net_amount > 0
GROUP BY 1;

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
