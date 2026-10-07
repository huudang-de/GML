-- ==========================================
-- DASHBOARD: QUẢN TRỊ DÒNG TIỀN
-- ==========================================
-- VISUAL: Dòng tiền ra
-- MEASURE: _DongTien[Dong_Tien_Ra]
SELECT SUM(credit_amount)
FROM silver.fact_cashflow
WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%';

-- VISUAL: Dòng tiền vào
-- MEASURE: _DongTien[Dong_Tien_Vao]
SELECT SUM(debit_amount)
FROM silver.fact_cashflow
WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%';

-- VISUAL: Cash Balance
-- MEASURE: _DongTien[Cash_Balance]
SELECT SUM(ending_balance)
FROM silver.fact_balancesheet
WHERE indicator_code = 'B01-DN_110'
  AND reporting_date =
    (SELECT MAX(reporting_date)
     FROM silver.fact_balancesheet);

-- VISUAL: Thu/Chi/Số dư theo tháng
-- MEASURE: _DongTien[Thu_Chi_Thang]
SELECT DATE_TRUNC(''month'', posting_date) AS MONTH,
       SUM(debit_amount) AS dong_tien_vao,
       SUM(credit_amount) AS dong_tien_ra
FROM silver.fact_cashflow
WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%'
GROUP BY 1;

-- VISUAL: Cơ cấu dòng thu theo Bank
-- MEASURE: _DongTien[Dong_Thu_Bank]
SELECT bank_code,
       reciprocal_account,
       SUM(debit_amount) AS gia_tri_thu
FROM silver.fact_cashflow
WHERE account_no LIKE '112%'
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%'
GROUP BY 1, 2;

-- VISUAL: Cơ cấu dòng chi theo Bank
-- MEASURE: _DongTien[Dong_Chi_Bank]
SELECT bank_code,
       reciprocal_account,
       SUM(credit_amount) AS gia_tri_chi
FROM silver.fact_cashflow
WHERE account_no LIKE '112%'
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%'
GROUP BY 1, 2;

-- VISUAL: Tài sản/Nợ/VLĐ
-- MEASURE: _DongTien[Working_Capital]
SELECT DATE_TRUNC(''month'', reporting_date) AS MONTH,
       SUM(CASE WHEN indicator_code=''B01-DN_100'' THEN ending_balance ELSE 0 END) - 
       SUM(CASE WHEN indicator_code=''B01-DN_310'' THEN ending_balance ELSE 0 END) AS vld_rong
FROM silver.fact_balancesheet
GROUP BY 1;

-- VISUAL: Bảng Runway
-- MEASURE: _DongTien[Runway]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet),
cash_balance AS (
    SELECT SUM(ending_balance) AS val
    FROM silver.fact_balancesheet
    WHERE indicator_code = ''B01-DN_110'' AND reporting_date = (SELECT dt FROM max_date)
),
avg_net_cash_out AS (
    SELECT SUM(credit_amount - debit_amount) / NULLIF(COUNT(DISTINCT DATE_TRUNC(''month'', posting_date)), 0) AS val
    FROM silver.fact_cashflow
    WHERE EXTRACT(YEAR FROM posting_date) = EXTRACT(YEAR FROM CURRENT_DATE)
      AND (account_no LIKE ''111%'' OR account_no LIKE ''112%'')
      AND voucher_no NOT LIKE ''CTNB%''
      AND voucher_no NOT LIKE ''NTTK%''
      AND reciprocal_account NOT LIKE ''111%'' 
      AND reciprocal_account NOT LIKE ''112%''
)
SELECT (SELECT val FROM cash_balance) / NULLIF((SELECT val FROM avg_net_cash_out), 0) AS runway;

-- VISUAL: Bảng Chu kỳ tiền mặt CCC
-- MEASURE: _DongTien[CCC]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet),
dso_calc AS (
    SELECT 
        (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code=''B01-DN_130'' AND reporting_date=(SELECT dt FROM max_date)) /
        NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_10'' AND reporting_date=(SELECT dt FROM max_date)), 0) * 365 AS dso
),
dio_calc AS (
    SELECT 
        (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code=''B01-DN_140'' AND reporting_date=(SELECT dt FROM max_date)) /
        NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_11'' AND reporting_date=(SELECT dt FROM max_date)), 0) * 365 AS dio
),
dpo_calc AS (
    SELECT 
        (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code=''B01-DN_311'' AND reporting_date=(SELECT dt FROM max_date)) /
        NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_11'' AND reporting_date=(SELECT dt FROM max_date)), 0) * 365 AS dpo
)
SELECT 
    (SELECT dso FROM dso_calc) AS dso,
    (SELECT dio FROM dio_calc) AS dio,
    (SELECT dpo FROM dpo_calc) AS dpo,
    ((SELECT dso FROM dso_calc) + (SELECT dio FROM dio_calc) - (SELECT dpo FROM dpo_calc)) AS ccc;
