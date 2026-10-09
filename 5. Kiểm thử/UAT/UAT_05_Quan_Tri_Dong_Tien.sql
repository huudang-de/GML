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

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
-- AND voucher_no NOT LIKE 'CTNB%'
-- AND voucher_no NOT LIKE 'NTTK%'
-- AND reciprocal_account NOT LIKE '111%'
-- AND reciprocal_account NOT LIKE '112%';
+------------------+
|       sum        |
+------------------+
| 2302632987134.00 |
+------------------+
*/

-- VISUAL: Dòng tiền vào
-- MEASURE: _DongTien[Dong_Tien_Vao]
SELECT SUM(debit_amount)
FROM silver.fact_cashflow
WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%';

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
-- AND voucher_no NOT LIKE 'CTNB%'
-- AND voucher_no NOT LIKE 'NTTK%'
-- AND reciprocal_account NOT LIKE '111%'
-- AND reciprocal_account NOT LIKE '112%';
+------------------+
|       sum        |
+------------------+
| 2377260599093.00 |
+------------------+
*/

-- VISUAL: Cash Balance
-- MEASURE: _DongTien[Cash_Balance]
SELECT SUM(ending_balance)
FROM silver.fact_balancesheet
WHERE indicator_code = 'B01-DN_110'
  AND reporting_date =
    (SELECT MAX(reporting_date)
     FROM silver.fact_balancesheet);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B01-DN_110'
-- AND reporting_date =
+----------------+
|      sum       |
+----------------+
| 91976722608.00 |
+----------------+
*/

-- VISUAL: Thu/Chi/Số dư theo tháng
-- MEASURE: _DongTien[Thu_Chi_Thang]
WITH cashflow AS (
    SELECT DATE_TRUNC('month', posting_date) AS MONTH,
           SUM(debit_amount) AS dong_tien_vao,
           SUM(credit_amount) AS dong_tien_ra
    FROM silver.fact_cashflow
    WHERE (account_no LIKE '111%' OR account_no LIKE '112%')
      AND voucher_no NOT LIKE 'CTNB%'
      AND voucher_no NOT LIKE 'NTTK%'
      AND reciprocal_account NOT LIKE '111%' 
      AND reciprocal_account NOT LIKE '112%'
    GROUP BY 1
),
balance AS (
    SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
           SUM(ending_balance) AS du_quy
    FROM silver.fact_balancesheet
    WHERE indicator_code = 'B01-DN_110'
    GROUP BY 1
)
SELECT c.MONTH,
       c.dong_tien_vao,
       c.dong_tien_ra,
       b.du_quy
FROM cashflow c
LEFT JOIN balance b ON c.MONTH = b.MONTH
ORDER BY c.MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- Kết hợp cả Thu/Chi từ fact_cashflow và Dư quỹ từ fact_balancesheet
+---------------------------+-----------------+-----------------+----------------+
|           month           |  dong_tien_vao  |   dong_tien_ra  |     du_quy     |
+---------------------------+-----------------+-----------------+----------------+
| 2026-01-01 00:00:00+00:00 | 317087950302.00 | 253416739386.00 |  ...           |
| 2026-02-01 00:00:00+00:00 | 113163027098.00 | 218302046659.00 |  ...           |
| 2026-03-01 00:00:00+00:00 | 395958247753.00 | 380681648700.00 |  ...           |
| 2026-04-01 00:00:00+00:00 | 398061744307.00 | 412837030672.00 |  ...           |
| 2026-05-01 00:00:00+00:00 | 337104742101.00 | 305508584452.00 |  ...           |
| 2026-06-01 00:00:00+00:00 | 557962548602.00 | 320799845912.00 |  ...           |
| 2026-07-01 00:00:00+00:00 | 257919590930.00 | 411087091353.00 | 91976722608.00 |
| 2026-08-01 00:00:00+00:00 |    2748000.00   |       0.00      |  ...           |
+---------------------------+-----------------+-----------------+----------------+
*/

-- VISUAL: Cơ cấu dòng thu theo Bank
-- MEASURE: _DongTien[Dong_Thu_Bank]
SELECT partner_code AS bank_code,
       reciprocal_account,
       SUM(debit_amount) AS gia_tri_thu
FROM silver.fact_cashflow
WHERE account_no LIKE '112%'
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%'
GROUP BY 1, 2;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '112%'
-- AND voucher_no NOT LIKE 'CTNB%'
-- AND voucher_no NOT LIKE 'NTTK%'
-- AND reciprocal_account NOT LIKE '111%'
-- AND reciprocal_account NOT LIKE '112%'
+----------------------------------+--------------------+-----------------+
|            bank_code             | reciprocal_account |   gia_tri_thu   |
+----------------------------------+--------------------+-----------------+
|            0101657828            |        131         |  1674726621.00  |
|               TPB                |        6352        |       0.00      |
|            0107351716            |        331         |       0.00      |
|            0110027928            |        331         |       0.00      |
|            2900521383            |        331         |       0.00      |
|           Vương Văn Bộ           |        131         |   201084000.00  |
|            0108641009            |        131         |    7482000.00   |
|            0108587601            |        131         |  55828245498.00 |
|            2901943557            |        131         |   96136503.00   |
|            0111454150            |        515         |      30.00      |
|            0100793514            |        331         |       0.00      |
|               IVB                |        6425        |       0.00      |
|            0100385089            |        131         |  32015004504.00 |
|            0107716452            |        131         |   117018000.00  |
|             NCC1054              |        331         |       0.00      |
|            0103719325            |        515         |      135.00     |
|            0200843159            |        131         |   154809000.00  |
...(TRUNCATED FOR READABILITY)...
*/

-- VISUAL: Cơ cấu dòng chi theo Bank
-- MEASURE: _DongTien[Dong_Chi_Bank]
SELECT partner_code AS bank_code,
       reciprocal_account,
       SUM(credit_amount) AS gia_tri_chi
FROM silver.fact_cashflow
WHERE account_no LIKE '112%'
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%'
GROUP BY 1, 2;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '112%'
-- AND voucher_no NOT LIKE 'CTNB%'
-- AND voucher_no NOT LIKE 'NTTK%'
-- AND reciprocal_account NOT LIKE '111%'
-- AND reciprocal_account NOT LIKE '112%'
+----------------------------------+--------------------+-----------------+
|            bank_code             | reciprocal_account |   gia_tri_chi   |
+----------------------------------+--------------------+-----------------+
|            0101657828            |        131         |       0.00      |
|               TPB                |        6352        |  3681059907.00  |
|            0107351716            |        331         |   110130000.00  |
|            0110027928            |        331         |   480690000.00  |
|            2900521383            |        331         |   43200000.00   |
|           Vương Văn Bộ           |        131         |       0.00      |
|            0108641009            |        131         |       0.00      |
|            0108587601            |        131         |  33210000000.00 |
|            2901943557            |        131         |       0.00      |
|            0111454150            |        515         |       0.00      |
|            0100793514            |        331         |   48438000.00   |
|               IVB                |        6425        |   27353220.00   |
|            0100385089            |        131         |       0.00      |
|            0107716452            |        131         |       0.00      |
|             NCC1054              |        331         |   129595788.00  |
|            0103719325            |        515         |       0.00      |
|            0200843159            |        131         |       0.00      |
...(TRUNCATED FOR READABILITY)...
*/

-- VISUAL: Tài sản/Nợ/VLĐ
-- MEASURE: _DongTien[Working_Capital]
SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
       SUM(CASE WHEN indicator_code='B01-DN_100' THEN ending_balance ELSE 0 END) - 
       SUM(CASE WHEN indicator_code='B01-DN_310' THEN ending_balance ELSE 0 END) AS vld_rong
FROM silver.fact_balancesheet
GROUP BY 1;

/* RESULT LOG:
+---------------------------+-----------------+
|           month           |     vld_rong    |
+---------------------------+-----------------+
| 2026-08-01 00:00:00+00:00 | 248352741076.00 |
| 2026-07-01 00:00:00+00:00 | 248352741076.00 |
+---------------------------+-----------------+
*/

-- VISUAL: Bảng Runway
-- MEASURE: _DongTien[Runway]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet),
cash_balance AS (
    SELECT SUM(ending_balance) AS val
    FROM silver.fact_balancesheet
    WHERE indicator_code = 'B01-DN_110' AND reporting_date = (SELECT dt FROM max_date)
),
avg_net_cash_out AS (
    SELECT SUM(credit_amount - debit_amount) / NULLIF(COUNT(DISTINCT DATE_TRUNC('month', posting_date)), 0) AS val
    FROM silver.fact_cashflow
    WHERE EXTRACT(YEAR FROM posting_date) = EXTRACT(YEAR FROM CURRENT_DATE)
      AND (account_no LIKE '111%' OR account_no LIKE '112%')
      AND voucher_no NOT LIKE 'CTNB%'
      AND voucher_no NOT LIKE 'NTTK%'
      AND reciprocal_account NOT LIKE '111%' 
      AND reciprocal_account NOT LIKE '112%'
)
SELECT (SELECT val FROM cash_balance) / NULLIF((SELECT val FROM avg_net_cash_out), 0) AS runway;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B01-DN_110' AND reporting_date = (SELECT dt FROM max_date)
-- WHERE EXTRACT(YEAR FROM posting_date) = EXTRACT(YEAR FROM CURRENT_DATE)
-- AND (account_no LIKE '111%' OR account_no LIKE '112%')
-- AND voucher_no NOT LIKE 'CTNB%'
-- AND voucher_no NOT LIKE 'NTTK%'
-- AND reciprocal_account NOT LIKE '111%'
-- AND reciprocal_account NOT LIKE '112%'
+---------------------+
|        runway       |
+---------------------+
| -9.8598060630461021 |
+---------------------+
*/

-- VISUAL: Bảng Chu kỳ tiền mặt CCC
-- MEASURE: _DongTien[CCC]
WITH max_date AS (SELECT MAX(month) AS dt FROM silver.fact_incomestatement WHERE current_period_amount > 0),
dso_calc AS (
    SELECT 
        (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_130' AND reporting_date=(SELECT dt FROM max_date)) /
        NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' AND month=(SELECT dt FROM max_date)), 0) * 365 AS dso
),
dio_calc AS (
    SELECT 
        (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_140' AND reporting_date=(SELECT dt FROM max_date)) /
        NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_11' AND month=(SELECT dt FROM max_date)), 0) * 365 AS dio
),
dpo_calc AS (
    SELECT 
        (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_311' AND reporting_date=(SELECT dt FROM max_date)) /
        NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_11' AND month=(SELECT dt FROM max_date)), 0) * 365 AS dpo
)
SELECT 
    (SELECT dso FROM dso_calc) AS dso,
    (SELECT dio FROM dio_calc) AS dio,
    (SELECT dpo FROM dpo_calc) AS dpo,
    ((SELECT dso FROM dso_calc) + (SELECT dio FROM dio_calc) - (SELECT dpo FROM dpo_calc)) AS ccc;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WITH max_date AS (SELECT MAX(month) AS dt FROM silver.fact_incomestatement WHERE current_period_amount > 0),
-- (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_130' AND reporting_date=(SELECT dt FROM max_date)) /
-- NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' AND month=(SELECT dt FROM max_date)), 0) * 365 AS dso
-- (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_140' AND reporting_date=(SELECT dt FROM max_date)) /
-- NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_11' AND month=(SELECT dt FROM max_date)), 0) * 365 AS dio
-- (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_311' AND reporting_date=(SELECT dt FROM max_date)) /
-- NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_11' AND month=(SELECT dt FROM max_date)), 0) * 365 AS dpo
+-----------------------+------+------+------+
|          dso          | dio  | dpo  | ccc  |
+-----------------------+------+------+------+
| 1884.3412961043869590 | None | None | None |
+-----------------------+------+------+------+
*/

