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
SELECT b.bank_code AS bank_code,
       c.reciprocal_account,
       SUM(c.debit_amount) AS gia_tri_thu
FROM silver.fact_cashflow c
LEFT JOIN silver.dim_account a ON c.account_no = a.account_no
LEFT JOIN silver.dim_accountnumber b ON a.account_bank = b.account_bank
WHERE c.account_no LIKE '112%'
  AND c.voucher_no NOT LIKE 'CTNB%'
  AND c.voucher_no NOT LIKE 'NTTK%'
  AND c.reciprocal_account NOT LIKE '111%' 
  AND c.reciprocal_account NOT LIKE '112%'
GROUP BY 1, 2;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '112%'
-- Lấy account_bank từ dim_account, sau đó JOIN với dim_accountnumber để bóc chính xác Mã Ngân Hàng (VCB, MB, BIDV...)
-- Gom nhóm thêm theo reciprocal_account để hỗ trợ Power BI cross-filter hoạt động thu/chi
+----------------------------------+--------------------+-----------------+
|            bank_code             | reciprocal_account |   gia_tri_thu   |
+----------------------------------+--------------------+-----------------+
|               VCB                |        131         |  1674726621.00  |
|               MB                 |        131         |  55828245498.00 |
|               MB                 |        515         |      135.00     |
|               TPB                |        131         |   201084000.00  |
|              BIDV                |        131         |  32015004504.00 |
...(TRUNCATED FOR READABILITY)...
*/

-- VISUAL: Cơ cấu dòng chi theo Bank
-- MEASURE: _DongTien[Dong_Chi_Bank]
SELECT b.bank_code AS bank_code,
       c.reciprocal_account,
       SUM(c.credit_amount) AS gia_tri_chi
FROM silver.fact_cashflow c
LEFT JOIN silver.dim_account a ON c.account_no = a.account_no
LEFT JOIN silver.dim_accountnumber b ON a.account_bank = b.account_bank
WHERE c.account_no LIKE '112%'
  AND c.voucher_no NOT LIKE 'CTNB%'
  AND c.voucher_no NOT LIKE 'NTTK%'
  AND c.reciprocal_account NOT LIKE '111%' 
  AND c.reciprocal_account NOT LIKE '112%'
GROUP BY 1, 2;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '112%'
-- Lấy account_bank từ dim_account, sau đó JOIN với dim_accountnumber để bóc chính xác Mã Ngân Hàng (VCB, MB, BIDV...)
-- Gom nhóm thêm theo reciprocal_account để hỗ trợ Power BI cross-filter hoạt động thu/chi
+----------------------------------+--------------------+-----------------+
|            bank_code             | reciprocal_account |   gia_tri_chi   |
+----------------------------------+--------------------+-----------------+
|               VCB                |        331         |  110130000.00   |
|               MB                 |        331         | 33210000000.00  |
|               TPB                |        6352        |  3681059907.00  |
|              BIDV                |        331         |   480690000.00  |
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
doanh_thu AS (
    SELECT SUM(current_period_amount) AS val 
    FROM silver.fact_incomestatement 
    WHERE indicator_code='B02-DN_10' AND month = (SELECT dt FROM max_date)
),
gia_von AS (
    SELECT SUM(current_period_amount) AS val 
    FROM silver.fact_incomestatement 
    WHERE indicator_code='B02-DN_11' AND month = (SELECT dt FROM max_date)
),
du_no_phai_thu AS (
    SELECT SUM(debit_amount - credit_amount) AS val 
    FROM silver.fact_accountsreceivable 
    WHERE DATE_TRUNC('month', posting_date) <= (SELECT dt FROM max_date)
),
du_no_phai_tra AS (
    SELECT SUM(credit_amount - debit_amount) AS val 
    FROM silver.fact_accountspayable 
    WHERE DATE_TRUNC('month', posting_date) <= (SELECT dt FROM max_date)
),
htk_cuoi_ky AS (
    SELECT SUM(ending_value) AS val 
    FROM silver.fact_inventory_balance 
    WHERE DATE_TRUNC('month', snapshot_date) = (SELECT dt FROM max_date)
)
SELECT 
    365 / NULLIF((SELECT val FROM doanh_thu) / NULLIF((SELECT val FROM du_no_phai_thu), 0), 0) AS dso,
    365 / NULLIF((SELECT val FROM gia_von) / NULLIF((SELECT val FROM htk_cuoi_ky), 0), 0) AS dio,
    365 / NULLIF((SELECT val FROM gia_von) / NULLIF((SELECT val FROM du_no_phai_tra), 0), 0) AS dpo,
    (365 / NULLIF((SELECT val FROM doanh_thu) / NULLIF((SELECT val FROM du_no_phai_thu), 0), 0)) + 
    (365 / NULLIF((SELECT val FROM gia_von) / NULLIF((SELECT val FROM htk_cuoi_ky), 0), 0)) - 
    (365 / NULLIF((SELECT val FROM gia_von) / NULLIF((SELECT val FROM du_no_phai_tra), 0), 0)) AS ccc;

/* RESULT LOG:
-- GHI CHÚ FILTER: Tính cho tháng có báo cáo kết quả kinh doanh gần nhất
+-----------------------+------+------+------+
|          dso          | dio  | dpo  | ccc  |
+-----------------------+------+------+------+
|  55.4312961043869590  | ...  | ...  | ...  |
+-----------------------+------+------+------+
*/

