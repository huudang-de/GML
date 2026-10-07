-- TONG HOP SQL TEST SCRIPT (UAT)
-- DU AN GO MINH LONG

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
SELECT
  (SELECT SUM(current_period_amount)
   FROM silver.fact_incomestatement
   WHERE indicator_code='B02-DN_10'
     AND EXTRACT(YEAR
                 FROM reporting_date) = EXTRACT(YEAR
                                                FROM CURRENT_DATE)) / NULLIF(
                                                                               (SELECT SUM(debit_amount - credit_amount)
                                                                                FROM silver.fact_accountsreceivable), 0);

-- VISUAL: Vòng quay phải thu hiện tại
-- MEASURE: _CongNo[VQ_Phai_Thu_Thang]
SELECT
  (SELECT SUM(current_period_amount)
   FROM silver.fact_incomestatement
   WHERE indicator_code='B02-DN_10'
     AND EXTRACT(MONTH
                 FROM MONTH) = EXTRACT(MONTH
                                       FROM CURRENT_DATE)) / NULLIF(
                                                                      (SELECT SUM(debit_amount - credit_amount)
                                                                       FROM silver.fact_accountsreceivable), 0);

-- VISUAL: Tổng hóa đơn
-- MEASURE: _CongNo[Tong_Hoa_Don]
SELECT COUNT(DISTINCT invoice_no) AS tong_hoa_don
FROM silver.fact_accountsreceivable;

-- VISUAL: Tổng số khách hàng
-- MEASURE: _CongNo[Tong_KH]
SELECT COUNT(DISTINCT partner_code) AS tong_khach_hang
FROM silver.fact_accountsreceivable
WHERE debit_amount - credit_amount > 0;

-- VISUAL: Phải thu theo tháng
-- MEASURE: _CongNo[Phai_Thu_Thang]
SELECT DATE_TRUNC('month', posting_date) AS MONTH,
       SUM(CASE
               WHEN CURRENT_DATE <= invoice_date + 30 THEN debit_amount - credit_amount
               ELSE 0
           END) AS no_trong_han
FROM silver.fact_accountsreceivable
GROUP BY 1;

-- VISUAL: Receivable Turnover
-- MEASURE: _CongNo[VQ_Phai_Thu]
SELECT DATE_TRUNC('month', posting_date) AS MONTH,
       SUM(debit_amount - credit_amount) AS du_no_thang
FROM silver.fact_accountsreceivable
GROUP BY 1;

-- VISUAL: Top 10 KH nợ cao nhất
-- MEASURE: _CongNo[Top_10_No]
SELECT partner_code,
       SUM(debit_amount - credit_amount) AS du_no
FROM silver.fact_accountsreceivable
GROUP BY 1
ORDER BY du_no DESC
LIMIT 10;

-- VISUAL: Top 10 KH dư nợ quá hạn (Nợ xấu)
-- MEASURE: _CongNo[Top_10_Qua_Han]
SELECT partner_code,
       SUM(CASE
               WHEN CURRENT_DATE > invoice_date + 30 THEN debit_amount - credit_amount
               ELSE 0
           END) AS no_qua_han
FROM silver.fact_accountsreceivable
GROUP BY 1
ORDER BY no_qua_han DESC
LIMIT 10;

-- VISUAL: Tuổi nợ Aging
-- MEASURE: _CongNo[Aging]
SELECT CASE
           WHEN CURRENT_DATE <= invoice_date + 30 THEN 'Current'
           ELSE 'Overdue'
       END AS age_bucket,
       SUM(debit_amount - credit_amount) AS gia_tri
FROM silver.fact_accountsreceivable
GROUP BY 1;

-- VISUAL: Chi tiết nợ theo Khách hàng
-- MEASURE: _CongNo[Chi_Tiet_No_KH]
SELECT partner_code AS ma_kh,
       SUM(debit_amount - credit_amount) AS tong_phai_thu
FROM silver.fact_accountsreceivable
GROUP BY 1;

-- VISUAL: Chi tiết hóa đơn nợ
-- MEASURE: _CongNo[Chi_Tiet_HD]
SELECT invoice_no AS so_hoa_don,
       debit_amount - credit_amount AS so_tien_con_no
FROM silver.fact_accountsreceivable
WHERE debit_amount - credit_amount > 0;

