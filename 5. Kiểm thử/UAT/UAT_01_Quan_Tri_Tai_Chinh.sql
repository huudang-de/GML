-- TONG HOP SQL TEST SCRIPT (UAT)
-- DU AN GO MINH LONG

-- ==========================================
-- DASHBOARD: QUẢN TRỊ HOẠT ĐỘNG TÀI CHÍNH

-- ==========================================
-- VISUAL: Dư nợ ngắn hạn
-- MEASURE: _TaiChinh[Du_No_Ngan_Han]

SELECT SUM(credit_amount) - SUM(debit_amount)
FROM silver.fact_cashflow
WHERE account_no LIKE '34111%'
  OR account_no LIKE '34113%'
  OR account_no LIKE '34114%';
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '34111%'
-- OR account_no LIKE '34113%'
-- OR account_no LIKE '34114%';
+-----------------+
|     ?column?    |
+-----------------+
| -58676538840.00 |
+-----------------+
*/


-- VISUAL: Dư nợ dài hạn
-- MEASURE: _TaiChinh[Du_No_Dai_Han]
SELECT SUM(credit_amount) - SUM(debit_amount)
FROM silver.fact_cashflow
WHERE account_no LIKE '34112%';
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '34112%';
+----------------+
|    ?column?    |
+----------------+
| 29111738593.00 |
+----------------+
*/


-- VISUAL: Hạn mức được phê duyệt
-- MEASURE: _TaiChinh[Han_Muc_Phe_Duyet]
SELECT SUM(credit_limit)
FROM silver.fact_creditlimitsummary;
/* RESULT LOG:
+-----------------+
|       sum       |
+-----------------+
| 485000000000.00 |
+-----------------+
*/


-- VISUAL: Hạn mức được cấp
-- MEASURE: _TaiChinh[Han_Muc_Duoc_Cap]
SELECT SUM(granted_limit)
FROM silver.fact_creditlimitsummary;
/* RESULT LOG:
+-----------------+
|       sum       |
+-----------------+
| 295000000000.00 |
+-----------------+
*/


-- VISUAL: Hạn mức còn lại
-- MEASURE: _TaiChinh[Han_Muc_Con_Lai]
SELECT SUM(granted_limit) - SUM(principal_balance)
FROM silver.fact_creditlimitsummary;
/* RESULT LOG:
+----------------+
|    ?column?    |
+----------------+
| 24135521634.00 |
+----------------+
*/


-- VISUAL: Loan to Value (LTV)
-- MEASURE: _TaiChinh[LTV_Ratio]
SELECT
  (SELECT SUM(granted_limit)
   FROM silver.fact_creditlimitsummary) / NULLIF(
                                                   (SELECT SUM(appraised_value)
                                                    FROM silver.fact_collateral), 0) AS ltv_ratio;
/* RESULT LOG:
+------------------------+
|       ltv_ratio        |
+------------------------+
| 0.71290863549346840628 |
+------------------------+
*/


-- VISUAL: DEBT/EQUITY
-- MEASURE: _TaiChinh[Debt_Equity]
WITH bs AS
  (SELECT reporting_date
   FROM silver.fact_balancesheet
   ORDER BY reporting_date DESC
   LIMIT 1)
SELECT
  (SELECT SUM(ending_balance)
   FROM silver.fact_balancesheet
   WHERE indicator_code = 'B01-DN_300'
     AND reporting_date =
       (SELECT reporting_date
        FROM bs)) / NULLIF(
                             (SELECT SUM(ending_balance)
                              FROM silver.fact_balancesheet
                              WHERE indicator_code = 'B01-DN_400'
                                AND reporting_date =
                                  (SELECT reporting_date
                                   FROM bs)), 0);
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B01-DN_300'
-- AND reporting_date =
-- WHERE indicator_code = 'B01-DN_400'
-- AND reporting_date =
+--------------------+
|      ?column?      |
+--------------------+
| 1.7457724728585124 |
+--------------------+
*/


-- VISUAL: Nợ ngắn/dài hạn theo thời gian
-- MEASURE: _TaiChinh[Du_No_Theo_Thang]
WITH monthly_delta AS
  (SELECT DATE_TRUNC('month', posting_date) AS MONTH,
          SUM(CASE
                  WHEN account_no LIKE '34111%'
                       OR account_no LIKE '34113%'
                       OR account_no LIKE '34114%' THEN credit_amount - debit_amount
                  ELSE 0
              END) AS delta_ngan_han,
          SUM(CASE
                  WHEN account_no LIKE '34112%' THEN credit_amount - debit_amount
                  ELSE 0
              END) AS delta_dai_han,
          SUM(credit_amount - debit_amount) AS delta_tong
   FROM silver.fact_cashflow
   WHERE account_no LIKE '341%'
   GROUP BY 1)
SELECT MONTH,
       SUM(delta_ngan_han) OVER (
                                 ORDER BY MONTH) AS no_ngan_han,
       SUM(delta_dai_han) OVER (
                                ORDER BY MONTH) AS no_dai_han,
       SUM(delta_tong) OVER (
                             ORDER BY MONTH) AS tong_du_no
FROM monthly_delta;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- OR account_no LIKE '34113%'
-- OR account_no LIKE '34114%' THEN credit_amount - debit_amount
-- WHERE account_no LIKE '341%'
+---------------------------+-----------------+----------------+-----------------+
|           month           |   no_ngan_han   |   no_dai_han   |    tong_du_no   |
+---------------------------+-----------------+----------------+-----------------+
| 2026-01-01 00:00:00+00:00 |  -5931423850.00 | -503964877.00  | -19625237083.00 |
| 2026-02-01 00:00:00+00:00 |  -5853486494.00 | 11943788174.00 |  17680422624.00 |
| 2026-03-01 00:00:00+00:00 |  -9958298082.00 | 30200593725.00 |  59864992999.00 |
| 2026-04-01 00:00:00+00:00 |  -6011334519.00 | 30200593725.00 |  71434472174.00 |
| 2026-05-01 00:00:00+00:00 |  -3483348183.00 | 30200593725.00 |  78963249834.00 |
| 2026-06-01 00:00:00+00:00 |  -600096357.00  | 30189906225.00 |  87268627634.00 |
| 2026-07-01 00:00:00+00:00 | -58676538840.00 | 29111738593.00 | -90195202711.00 |
+---------------------------+-----------------+----------------+-----------------+
*/


-- VISUAL: Chi phí lãi vay thực tế vs KH
-- MEASURE: _TaiChinh[Chi_Phi_Lai_Vay]
WITH actual AS
  (SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
          SUM(current_period_amount) AS chi_phi_thuc_te
   FROM silver.fact_incomestatement
   WHERE indicator_code = 'B02-DN_23'
   GROUP BY 1),
     PLAN AS
  (SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
          SUM(target_amount) AS ke_hoach
   FROM silver.fact_businessplan
   WHERE indicator_code = 'B02-DN_23'
   GROUP BY 1)
SELECT COALESCE(a.month, p.month) AS MONTH,
       COALESCE(a.chi_phi_thuc_te, 0) AS chi_phi_thuc_te,
       COALESCE(p.ke_hoach, 0) AS ke_hoach
FROM actual a
FULL OUTER JOIN PLAN p ON a.month = p.month;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B02-DN_23'
-- WHERE indicator_code = 'B02-DN_23'
ERROR: column "reporting_date" does not exist
LINE 2:   (SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
                                      ^

*/


-- VISUAL: Lãi suất bình quân (Card)
-- MEASURE: _TaiChinh[Lai_Suat_Binh_Quan_Card]
SELECT AVG(interest_rate) AS lai_suat_binh_quan_tong
FROM silver.fact_loan;
/* RESULT LOG:
+-------------------------+
| lai_suat_binh_quan_tong |
+-------------------------+
|   0.08355930232558144   |
+-------------------------+
*/


-- VISUAL: Lãi suất bình quân bank
SELECT bank_code,
       AVG(interest_rate) AS lai_suat_binh_quan
FROM silver.fact_loan
WHERE (maturity_date - disbursement_date) <= 366
GROUP BY 1;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE (maturity_date - disbursement_date) <= 366
+-----------+---------------------+
| bank_code |  lai_suat_binh_quan |
+-----------+---------------------+
|     VP    |       0.082875      |
|     HD    |  0.0879130434782609 |
|    SCB    | 0.08015384615384614 |
|   WOORI   |        0.073        |
|    IVB    | 0.08288043478260869 |
|     TP    |  0.0834736842105263 |
|     MB    | 0.08481359223300965 |
+-----------+---------------------+
*/


-- VISUAL: Interest YTD
-- MEASURE: _TaiChinh[Interest_YTD]
SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
       SUM(SUM(current_period_amount)) OVER (
                                             PARTITION BY DATE_TRUNC('year', reporting_date)
                                             ORDER BY DATE_TRUNC('month', reporting_date)) AS tong_lai_da_tra_luy_ke
FROM silver.fact_incomestatement
WHERE indicator_code = 'B02-DN_23'
GROUP BY 1;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B02-DN_23'
ERROR: column "reporting_date" does not exist
LINE 1: SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
                                   ^

*/


-- VISUAL: Cost of Debt
-- MEASURE: _TaiChinh[Cost_Of_Debt]
WITH actual_interest AS (
    SELECT DATE_TRUNC('month', reporting_date) AS month, 
           SUM(current_period_amount) AS tong_chi_phi_lai_vay 
    FROM silver.fact_incomestatement 
    WHERE indicator_code = 'B02-DN_23' 
    GROUP BY 1
),
monthly_debt AS (
    SELECT DATE_TRUNC('month', posting_date) AS month, 
           SUM(credit_amount - debit_amount) AS net_borrowing 
    FROM silver.fact_cashflow 
    WHERE account_no LIKE '341%' 
    GROUP BY 1
),
cumulative_debt AS (
    SELECT month, 
           SUM(net_borrowing) OVER (ORDER BY month) AS tong_du_no 
    FROM monthly_debt
)
SELECT i.month, 
       i.tong_chi_phi_lai_vay, 
       d.tong_du_no,
       i.tong_chi_phi_lai_vay / NULLIF(d.tong_du_no, 0) AS cost_of_debt
FROM actual_interest i
LEFT JOIN cumulative_debt d ON i.month = d.month;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B02-DN_23'
-- WHERE account_no LIKE '341%'
ERROR: column "reporting_date" does not exist
LINE 2:     SELECT DATE_TRUNC('month', reporting_date) AS month, 
                                       ^

*/


-- VISUAL: Dư nợ theo Bank
-- MEASURE: _TaiChinh[Du_No_Goc]
SELECT bank_code,
       SUM(remaining_principal) AS du_no_goc
FROM silver.fact_loan
GROUP BY bank_code;
/* RESULT LOG:
+-----------+----------------+
| bank_code |   du_no_goc    |
+-----------+----------------+
|     VP    | 9990153526.00  |
|     HD    | 14711831427.00 |
|    SCB    | 31763097880.00 |
|   WOORI   | 24000000000.00 |
|    IVB    | 73656199042.00 |
|     TP    | 26748764692.00 |
|     MB    | 89994431799.00 |
+-----------+----------------+
*/


-- VISUAL: Cơ cấu dòng thu theo Bank
-- MEASURE: _TaiChinh[Dong_Thu_Theo_Bank]
SELECT bank_code,
       SUM(debit_amount) AS tong_thu
FROM silver.fact_cashflow
WHERE account_no LIKE '112%'
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%'
GROUP BY bank_code;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '112%'
-- AND voucher_no NOT LIKE 'CTNB%'
-- AND voucher_no NOT LIKE 'NTTK%'
-- AND reciprocal_account NOT LIKE '111%'
-- AND reciprocal_account NOT LIKE '112%'
ERROR: column "bank_code" does not exist
LINE 1: SELECT bank_code,
               ^

*/


-- VISUAL: Cơ cấu dòng chi theo Bank
-- MEASURE: _TaiChinh[Dong_Chi_Theo_Bank]
SELECT bank_code,
       SUM(credit_amount) AS tong_chi
FROM silver.fact_cashflow
WHERE account_no LIKE '112%'
  AND voucher_no NOT LIKE 'CTNB%'
  AND voucher_no NOT LIKE 'NTTK%'
  AND reciprocal_account NOT LIKE '111%' 
  AND reciprocal_account NOT LIKE '112%'
GROUP BY bank_code;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '112%'
-- AND voucher_no NOT LIKE 'CTNB%'
-- AND voucher_no NOT LIKE 'NTTK%'
-- AND reciprocal_account NOT LIKE '111%'
-- AND reciprocal_account NOT LIKE '112%'
ERROR: column "bank_code" does not exist
LINE 1: SELECT bank_code,
               ^

*/


-- VISUAL: Bảng tổng hợp 18 Chỉ số
-- MEASURE: _TaiChinh[Ratios]
WITH md AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet),
prev_md AS (SELECT (SELECT dt FROM md) - interval '1 year' AS dt_prev),
b01_curr AS (
    SELECT indicator_code, SUM(ending_balance) as val 
    FROM silver.fact_balancesheet 
    WHERE reporting_date = (SELECT dt FROM md) 
    GROUP BY indicator_code
),
b01_prev AS (
    SELECT indicator_code, SUM(ending_balance) as val 
    FROM silver.fact_balancesheet 
    WHERE reporting_date = (SELECT dt_prev FROM prev_md) 
    GROUP BY indicator_code
),
b02_curr AS (
    SELECT indicator_code, SUM(current_period_amount) as val 
    FROM silver.fact_incomestatement 
    WHERE reporting_date = (SELECT dt FROM md) 
    GROUP BY indicator_code
),
du_no AS (
    SELECT SUM(credit_amount - debit_amount) as total_debt 
    FROM silver.fact_cashflow 
    WHERE account_no LIKE '341%' AND DATE_TRUNC('month', posting_date) <= DATE_TRUNC('month', (SELECT dt FROM md))
),
vars AS (
    SELECT 
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_100'), 0) AS ts_ngan_han,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_310'), 0) AS no_ngan_han,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_140'), 0) AS ton_kho,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_130'), 0) AS phai_thu,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_400'), 0) AS vcsh,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_300'), 0) AS no_phai_tra,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_330'), 0) AS no_dai_han,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_440'), 0) AS tong_ts,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_222' OR indicator_code='B01-DN_223'), 0) AS khau_hao,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_100'), 0) AS ts_ngan_han_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_310'), 0) AS no_ngan_han_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_140'), 0) AS ton_kho_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_130'), 0) AS phai_thu_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_400'), 0) AS vcsh_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_440'), 0) AS tong_ts_prev,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_10'), 0) AS dthu_thuan,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_11'), 0) AS gia_von,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_20'), 0) AS ln_gop,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_23'), 0) AS cp_lai_vay,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_30'), 0) AS ln_hdkd,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_51'), 0) + COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_52'), 0) AS cp_thue,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_60'), 0) AS ln_st,
        COALESCE((SELECT total_debt FROM du_no), 0) AS tong_du_no
)
SELECT 
    ts_ngan_han / NULLIF(no_ngan_han, 0) AS current_ratio,
    (ts_ngan_han - ton_kho) / NULLIF(no_ngan_han, 0) AS quick_ratio,
    dthu_thuan / NULLIF(((ts_ngan_han - no_ngan_han) + (ts_ngan_han_prev - no_ngan_han_prev)) / 2.0, 0) AS vong_quay_vld,
    gia_von / NULLIF((ton_kho + ton_kho_prev) / 2.0, 0) AS vong_quay_ton_kho,
    dthu_thuan / NULLIF((phai_thu + phai_thu_prev) / 2.0, 0) AS vong_quay_phai_thu,
    no_phai_tra / NULLIF(tong_ts, 0) AS no_phai_tra_tren_tong_ts,
    no_dai_han / NULLIF(vcsh, 0) AS no_dai_han_tren_vcsh,
    (ln_st + cp_thue + cp_lai_vay) AS ebit,
    (ln_st + cp_thue + cp_lai_vay + ABS(khau_hao)) AS ebitda,
    (ln_st + cp_thue + cp_lai_vay) / NULLIF(cp_lai_vay, 0) AS ebit_tren_lai_vay,
    (ln_st + cp_thue + cp_lai_vay + ABS(khau_hao)) / NULLIF(cp_lai_vay, 0) AS ebitda_tren_lai_vay,
    ln_gop / NULLIF(dthu_thuan, 0) AS bien_ln_gop,
    ln_hdkd / NULLIF(dthu_thuan, 0) AS bien_ln_hdkd,
    (ln_st + cp_thue + cp_lai_vay + ABS(khau_hao)) / NULLIF(dthu_thuan, 0) AS bien_ebitda,
    ln_st / NULLIF((vcsh + vcsh_prev) / 2.0, 0) AS roe,
    ln_st / NULLIF((tong_ts + tong_ts_prev) / 2.0, 0) AS roa,
    tong_du_no / NULLIF((ln_st + cp_thue + cp_lai_vay + ABS(khau_hao)), 0) AS tong_du_no_tren_ebitda
FROM vars;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE reporting_date = (SELECT dt FROM md)
-- WHERE reporting_date = (SELECT dt_prev FROM prev_md)
-- WHERE reporting_date = (SELECT dt FROM md)
-- WHERE account_no LIKE '341%' AND DATE_TRUNC('month', posting_date) <= DATE_TRUNC('month', (SELECT dt FROM md))
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_100'), 0) AS ts_ngan_han,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_310'), 0) AS no_ngan_han,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_140'), 0) AS ton_kho,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_130'), 0) AS phai_thu,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_400'), 0) AS vcsh,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_300'), 0) AS no_phai_tra,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_330'), 0) AS no_dai_han,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_440'), 0) AS tong_ts,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_222' OR indicator_code='B01-DN_223'), 0) AS khau_hao,
-- COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_100'), 0) AS ts_ngan_han_prev,
-- COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_310'), 0) AS no_ngan_han_prev,
-- COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_140'), 0) AS ton_kho_prev,
-- COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_130'), 0) AS phai_thu_prev,
-- COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_400'), 0) AS vcsh_prev,
-- COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_440'), 0) AS tong_ts_prev,
-- COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_10'), 0) AS dthu_thuan,
-- COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_11'), 0) AS gia_von,
-- COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_20'), 0) AS ln_gop,
-- COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_23'), 0) AS cp_lai_vay,
-- COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_30'), 0) AS ln_hdkd,
-- COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_51'), 0) + COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_52'), 0) AS cp_thue,
-- COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_60'), 0) AS ln_st,
ERROR: column "reporting_date" does not exist
LINE 18:     WHERE reporting_date = (SELECT dt FROM md) 
                   ^

*/


-- VISUAL: Chi tiết tài sản đảm bảo
-- MEASURE: _TaiChinh[TSDB]

SELECT collateral_type AS ten_tai_san,
       appraised_value AS gia_tri_tham_dinh,
       collateral_ratio AS he_so_tsdb,
       appraised_value * collateral_ratio AS gia_tri_cho_vay
FROM silver.fact_collateral;
/* RESULT LOG:
ERROR: column "collateral_ratio" does not exist
LINE 3:        collateral_ratio AS he_so_tsdb,
               ^

*/


-- VISUAL: Bảng cảnh báo rủi ro
-- MEASURE: _TaiChinh[Canh_Bao]
SELECT bank_code,
       CASE
           WHEN
                  (SELECT SUM(granted_limit)/SUM(appraised_value)
                   FROM silver.fact_creditlimitsummary c
                   JOIN silver.fact_collateral col ON c.bank_code=col.bank_code) > 0.8 THEN 'LTV > 80%'
           ELSE 'OK'
       END AS warning_ltv
FROM silver.fact_creditlimitsummary
GROUP BY bank_code;
/* RESULT LOG:
+-----------+-------------+
| bank_code | warning_ltv |
+-----------+-------------+
|     VP    |  LTV > 80%  |
|     HD    |  LTV > 80%  |
|   WOORI   |  LTV > 80%  |
|     TP    |  LTV > 80%  |
|     MB    |  LTV > 80%  |
|    IVB    |  LTV > 80%  |
|    SCB    |  LTV > 80%  |
+-----------+-------------+
*/


-- VISUAL: Lịch trả gốc ngân hàng
-- MEASURE: _TaiChinh[Lich_Tra_Goc]
SELECT bank_code,
       maturity_date AS ngay_can_tra_goc,
       SUM(remaining_principal) AS so_tien_can_tra
FROM silver.fact_loan
WHERE remaining_principal > 0
GROUP BY 1,
         2
ORDER BY 2 ASC;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE remaining_principal > 0
+-----------+------------------+-----------------+
| bank_code | ngay_can_tra_goc | so_tien_can_tra |
+-----------+------------------+-----------------+
|     MB    |    2026-05-02    |    4000000.00   |
|     MB    |    2026-05-04    |    1000000.00   |
|     MB    |    2026-05-05    |    2000000.00   |
|     MB    |    2026-05-06    |    2000000.00   |
|     TP    |    2026-05-06    |  1445968152.00  |
|    SCB    |    2026-05-11    |   452595586.00  |
|     MB    |    2026-05-11    |  1164328308.00  |
|     TP    |    2026-05-11    |  1048623840.00  |
|     MB    |    2026-05-12    |  1584343930.00  |
|     TP    |    2026-05-12    |  1288968120.00  |
|    SCB    |    2026-05-12    |   191221322.00  |
|    SCB    |    2026-05-13    |  1168032960.00  |
|     TP    |    2026-05-13    |   440000000.00  |
|     MB    |    2026-05-13    |  2290155812.00  |
|     MB    |    2026-05-14    |  1236602000.00  |
|     TP    |    2026-05-18    |  3228227254.00  |
|     MB    |    2026-05-18    |  3061671130.00  |
|     TP    |    2026-05-19    |  1500964789.00  |
|     MB    |    2026-05-19    |  2750341285.00  |
|     MB    |    2026-05-20    |  2202181607.00  |
|     MB    |    2026-05-21    |   600000000.00  |
|    SCB    |    2026-05-21    |   182214810.00  |
|     TP    |    2026-05-26    |  1338160130.00  |
|     MB    |    2026-06-02    |   600000000.00  |
|     MB    |    2026-06-03    |   479847323.00  |
|     MB    |    2026-06-04    |   254864064.00  |
|     VP    |    2026-06-04    |   426026600.00  |
|     MB    |    2026-06-05    |   244159770.00  |
|     MB    |    2026-06-08    |   192625270.00  |
|     VP    |    2026-06-08    |  3461591610.00  |
|     TP    |    2026-06-08    |  1000000000.00  |
|     TP    |    2026-06-09    |   980042603.00  |
|     TP    |    2026-06-10    |  1478712240.00  |
|     TP    |    2026-06-11    |  1637686080.00  |
|     MB    |    2026-06-12    |  4686251239.00  |
|     MB    |    2026-06-15    |  12815481371.00 |
|     MB    |    2026-06-16    |   699939626.00  |
|     MB    |    2026-06-17    |   527779437.00  |
|     TP    |    2026-06-17    |   500000000.00  |
|     TP    |    2026-06-23    |  1994017756.00  |
|     TP    |    2026-06-24    |  2101735988.00  |
|    IVB    |    2026-06-25    |  9282143512.00  |
|    IVB    |    2026-06-26    |  11653425894.00 |
|     MB    |    2026-06-26    |   918663537.00  |
|     TP    |    2026-06-27    |  2837208320.00  |
|     HD    |    2026-06-29    |  2850154034.00  |
|    IVB    |    2026-06-29    |  4331474146.00  |
|    SCB    |    2026-06-29    |  1337300000.00  |
|    SCB    |    2026-06-30    |  3355939816.00  |
|     MB    |    2026-06-30    |   417960000.00  |
|     HD    |    2026-06-30    |  1853696723.00  |
|     TP    |    2026-07-08    |  1642324540.00  |
|     TP    |    2026-07-09    |  2101124880.00  |
|    SCB    |    2026-07-12    |  3980000000.00  |
|     MB    |    2026-07-13    |  4267543385.00  |
|     HD    |    2026-07-13    |   836930730.00  |
|     MB    |    2026-07-14    |  3051009206.00  |
|     TP    |    2026-07-14    |   185000000.00  |
|     MB    |    2026-07-15    |  1080000000.00  |
|     MB    |    2026-07-16    |  1217742224.00  |
|     MB    |    2026-07-20    |  1455781792.00  |
|     MB    |    2026-07-21    |  1312818537.00  |
|     HD    |    2026-07-21    |   806130339.00  |
|     HD    |    2026-07-23    |   884016000.00  |
|     MB    |    2026-07-23    |   688780184.00  |
|     MB    |    2026-07-26    |   971040551.00  |
|     VP    |    2026-07-27    |  1150842379.00  |
|     VP    |    2026-07-28    |  1347620938.00  |
|    SCB    |    2026-07-28    |   451082095.00  |
|     VP    |    2026-07-29    |  2604071999.00  |
|    IVB    |    2026-07-29    |  2669431680.00  |
|     HD    |    2026-07-30    |   624000000.00  |
|    IVB    |    2026-08-03    |   500000000.00  |
|    IVB    |    2026-08-04    |  1614965040.00  |
|    SCB    |    2026-08-04    |  3601958388.00  |
|    IVB    |    2026-08-06    |  1002646898.00  |
|     HD    |    2026-08-11    |   779979614.00  |
|    IVB    |    2026-08-11    |  1040886685.00  |
|    IVB    |    2026-08-12    |  4354664490.00  |
|    IVB    |    2026-08-13    |  9446835734.00  |
|     MB    |    2026-08-23    |   66666666.00   |
|     MB    |    2026-08-24    |   604538392.00  |
|    IVB    |    2026-08-24    |  1510411536.00  |
|     MB    |    2026-08-25    |   220000000.00  |
|    SCB    |    2026-08-26    |  1981313424.00  |
|    IVB    |    2026-08-27    |   408000240.00  |
|     HD    |    2026-09-04    |   196682063.00  |
|    IVB    |    2026-09-04    |  1375000000.00  |
|    IVB    |    2026-09-09    |  2421336256.00  |
|    IVB    |    2026-09-11    |  1268072852.00  |
|     MB    |    2026-09-12    |   175634100.00  |
|    IVB    |    2026-09-14    |  2396349012.00  |
|     MB    |    2026-09-14    |  2795022288.00  |
|    IVB    |    2026-09-16    |  8494498763.00  |
|     MB    |    2026-09-17    |  1997552960.00  |
|     MB    |    2026-09-18    |  1730000000.00  |
|    IVB    |    2026-09-18    |  5684975959.00  |
|    IVB    |    2026-09-21    |  2948488701.00  |
|     MB    |    2026-09-21    |  1863981560.00  |
|     MB    |    2026-09-23    |   900000000.00  |
|    IVB    |    2026-09-23    |  1505591644.00  |
|     MB    |    2026-09-24    |  2402284143.00  |
|     MB    |    2026-09-25    |  3689135433.00  |
|     MB    |    2026-09-28    |   373222600.00  |
|     MB    |    2026-09-30    |  1017243886.00  |
|     HD    |    2026-10-02    |  1382957805.00  |
|     VP    |    2026-10-03    |  1000000000.00  |
|     MB    |    2026-10-06    |  1100000000.00  |
|    SCB    |    2026-10-06    |  2168422135.00  |
|     HD    |    2026-10-06    |   996548670.00  |
|   WOORI   |    2026-10-07    |  2000000000.00  |
|    SCB    |    2026-10-07    |  7278827630.00  |
|   WOORI   |    2026-10-08    |  12000000000.00 |
|   WOORI   |    2026-10-09    |  10000000000.00 |
|     MB    |    2026-10-09    |  1000000000.00  |
|     MB    |    2026-10-10    |  3485437508.00  |
|     HD    |    2026-10-12    |  2020175450.00  |
|     HD    |    2026-10-14    |   142344000.00  |
|    SCB    |    2026-10-14    |  1101216704.00  |
|     MB    |    2026-10-14    |  1990944340.00  |
|    SCB    |    2026-10-15    |  1050000000.00  |
|     MB    |    2026-10-20    |  4782052423.00  |
|     HD    |    2026-10-20    |   180438213.00  |
|     MB    |    2026-10-21    |  1963889316.00  |
|     MB    |    2026-10-22    |  1901778540.00  |
|     MB    |    2026-10-23    |  1332381260.00  |
|     HD    |    2026-10-23    |  1157777786.00  |
|    SCB    |    2026-10-23    |  3462973010.00  |
|     MB    |    2026-10-24    |  2721754796.00  |
|     MB    |    2026-10-28    |  1100000000.00  |
+-----------+------------------+-----------------+
*/


