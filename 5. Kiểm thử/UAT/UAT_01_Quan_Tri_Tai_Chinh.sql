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

-- VISUAL: Dư nợ dài hạn
-- MEASURE: _TaiChinh[Du_No_Dai_Han]
SELECT SUM(credit_amount) - SUM(debit_amount)
FROM silver.fact_cashflow
WHERE account_no LIKE '34112%';

-- VISUAL: Hạn mức được phê duyệt
-- MEASURE: _TaiChinh[Han_Muc_Phe_Duyet]
SELECT SUM(credit_limit)
FROM silver.fact_creditlimitsummary;

-- VISUAL: Hạn mức được cấp
-- MEASURE: _TaiChinh[Han_Muc_Duoc_Cap]
SELECT SUM(granted_limit)
FROM silver.fact_creditlimitsummary;

-- VISUAL: Hạn mức còn lại
-- MEASURE: _TaiChinh[Han_Muc_Con_Lai]
SELECT SUM(granted_limit) - SUM(principal_balance)
FROM silver.fact_creditlimitsummary;

-- VISUAL: Loan to Value (LTV)
-- MEASURE: _TaiChinh[LTV_Ratio]
SELECT
  (SELECT SUM(granted_limit)
   FROM silver.fact_creditlimitsummary) / NULLIF(
                                                   (SELECT SUM(appraised_value)
                                                    FROM silver.fact_collateral), 0) AS ltv_ratio;

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

-- VISUAL: Lãi suất bình quân (Card)
-- MEASURE: _TaiChinh[Lai_Suat_Binh_Quan_Card]
SELECT AVG(interest_rate) AS lai_suat_binh_quan_tong
FROM silver.fact_loan;

-- VISUAL: Lãi suất bình quân bank
SELECT bank_code,
       AVG(interest_rate) AS lai_suat_binh_quan
FROM silver.fact_loan
WHERE (maturity_date - disbursement_date) <= 366
GROUP BY 1;

-- VISUAL: Interest YTD
-- MEASURE: _TaiChinh[Interest_YTD]
SELECT DATE_TRUNC('month', reporting_date) AS MONTH,
       SUM(SUM(current_period_amount)) OVER (
                                             PARTITION BY DATE_TRUNC('year', reporting_date)
                                             ORDER BY DATE_TRUNC('month', reporting_date)) AS tong_lai_da_tra_luy_ke
FROM silver.fact_incomestatement
WHERE indicator_code = 'B02-DN_23'
GROUP BY 1;

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

-- VISUAL: Dư nợ theo Bank
-- MEASURE: _TaiChinh[Du_No_Goc]
SELECT bank_code,
       SUM(remaining_principal) AS du_no_goc
FROM silver.fact_loan
GROUP BY bank_code;

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

-- VISUAL: Chi tiết tài sản đảm bảo
-- MEASURE: _TaiChinh[TSDB]

SELECT collateral_type AS ten_tai_san,
       appraised_value AS gia_tri_tham_dinh,
       collateral_ratio AS he_so_tsdb,
       appraised_value * collateral_ratio AS gia_tri_cho_vay
FROM silver.fact_collateral;

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

