-- TONG HOP SQL TEST SCRIPT (UAT)
-- DU AN GO MINH LONG

-- ==========================================
-- DASHBOARD: QUẢN TRỊ HOẠT ĐỘNG TÀI CHÍNH

-- ==========================================
-- VISUAL: Dư nợ ngắn hạn
-- MEASURE: _TaiChinh[Du_No_Ngan_Han]
WITH latest_balances AS (
    SELECT account_no, credit_balance,
           ROW_NUMBER() OVER(PARTITION BY account_no ORDER BY posting_date DESC, id DESC) as rn
    FROM silver.fact_cashflow
    WHERE account_no LIKE '34111%' OR account_no LIKE '34113%' OR account_no LIKE '34114%'
)
SELECT SUM(credit_balance) AS du_no_ngan_han
FROM latest_balances
WHERE rn = 1;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '34111%' OR account_no LIKE '34113%' OR account_no LIKE '34114%'
-- WHERE rn = 1;
+-----------------+
|  du_no_ngan_han |
+-----------------+
| 236065233815.00 |
+-----------------+
*/

-- VISUAL: Dư nợ dài hạn
-- MEASURE: _TaiChinh[Du_No_Dai_Han]
WITH latest_balances AS (
    SELECT account_no, credit_balance,
           ROW_NUMBER() OVER(PARTITION BY account_no ORDER BY posting_date DESC, id DESC) as rn
    FROM silver.fact_cashflow
    WHERE account_no LIKE '34112%'
)
SELECT SUM(credit_balance) AS du_no_dai_han
FROM latest_balances
WHERE rn = 1;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE account_no LIKE '34112%'
-- WHERE rn = 1;
+----------------+
| du_no_dai_han  |
+----------------+
| 51174925843.00 |
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
                              WHERE indicator_code = 'B01-DN_440'
                                AND reporting_date =
                                  (SELECT reporting_date
                                   FROM bs)), 0);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B01-DN_300'
-- AND reporting_date =
-- WHERE indicator_code = 'B01-DN_440'
-- AND reporting_date =
+------------------------+
|        ?column?        |
+------------------------+
| 0.63580376382791085809 |
+------------------------+
*/

-- VISUAL: Nợ ngắn/dài hạn theo thời gian
-- MEASURE: _TaiChinh[Du_No_Theo_Thang]
WITH months AS (
    SELECT DISTINCT DATE_TRUNC('month', posting_date) AS month
    FROM silver.fact_cashflow
),
monthly_balances AS (
    SELECT m.month,
           c.account_no,
           c.credit_balance,
           ROW_NUMBER() OVER(PARTITION BY m.month, c.account_no ORDER BY c.posting_date DESC, c.id DESC) as rn
    FROM months m
    JOIN silver.fact_cashflow c ON c.posting_date < m.month + INTERVAL '1 month'
    WHERE c.account_no IN ('34111', '34112', '34113', '34114', '341')
)
SELECT month,
       SUM(CASE WHEN account_no IN ('34111', '34113', '34114') THEN credit_balance ELSE 0 END) AS no_ngan_han,
       SUM(CASE WHEN account_no = '34112' THEN credit_balance ELSE 0 END) AS no_dai_han,
       SUM(CASE WHEN account_no = '341' THEN credit_balance ELSE 0 END) AS tong_du_no
FROM monthly_balances
WHERE rn = 1
GROUP BY month
ORDER BY month;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE c.account_no IN ('34111', '34112', '34113', '34114', '341')
-- WHERE rn = 1
+---------------------------+-----------------+----------------+-----------------+
|           month           |   no_ngan_han   |   no_dai_han   |    tong_du_no   |
+---------------------------+-----------------+----------------+-----------------+
| 2026-01-01 00:00:00+00:00 | 288810348805.00 | 21559222373.00 | 314703079449.00 |
| 2026-02-01 00:00:00+00:00 | 288888286161.00 | 34006975424.00 | 327093064099.00 |
| 2026-03-01 00:00:00+00:00 | 284783474573.00 | 52263780975.00 | 341109352305.00 |
| 2026-04-01 00:00:00+00:00 | 288730438136.00 | 52263780975.00 | 344920610111.00 |
| 2026-05-01 00:00:00+00:00 | 291258424472.00 | 52263780975.00 | 347421005773.00 |
| 2026-06-01 00:00:00+00:00 | 294141676298.00 | 52253093475.00 | 350137412510.00 |
| 2026-07-01 00:00:00+00:00 | 236065233815.00 | 51174925843.00 | 290982802395.00 |
| 2026-08-01 00:00:00+00:00 | 236065233815.00 | 51174925843.00 | 290982802395.00 |
+---------------------------+-----------------+----------------+-----------------+
*/

-- VISUAL: Chi phí lãi vay thực tế vs KH
-- MEASURE: _TaiChinh[Chi_Phi_Lai_Vay]
WITH actual AS
  (SELECT DATE_TRUNC('month', month) AS MONTH,
          SUM(current_period_amount) AS chi_phi_thuc_te
   FROM silver.fact_incomestatement
   WHERE indicator_code = 'B02-DN_23'
   GROUP BY 1),
     PLAN AS
  (SELECT DATE_TRUNC('month', month) AS MONTH,
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
+---------------------------+-----------------+---------------+
|           month           | chi_phi_thuc_te |    ke_hoach   |
+---------------------------+-----------------+---------------+
| 2026-01-01 00:00:00+00:00 |        0        | 3162980024.00 |
| 2026-02-01 00:00:00+00:00 |        0        | 1581490013.00 |
| 2026-03-01 00:00:00+00:00 |        0        | 1581490013.00 |
| 2026-04-01 00:00:00+00:00 |        0        | 3162980026.00 |
| 2026-05-01 00:00:00+00:00 |        0        | 1581490013.00 |
| 2026-06-01 00:00:00+00:00 |        0        | 1581490013.00 |
| 2026-07-01 00:00:00+00:00 |       0.00      | 1581490013.00 |
| 2026-08-01 00:00:00+00:00 |       0.00      | 1581490013.00 |
| 2026-09-01 00:00:00+00:00 |        0        | 3162980026.00 |
| 2026-10-01 00:00:00+00:00 |        0        | 3162980026.00 |
| 2026-11-01 00:00:00+00:00 |        0        | 4744470039.00 |
| 2026-12-01 00:00:00+00:00 |        0        | 4744470039.00 |
+---------------------------+-----------------+---------------+
*/

-- VISUAL: Lãi suất bình quân bank
-- MEASURE: _TaiChinh[Lai_Suat_Binh_Quan_Bank]
SELECT bank_code,
       AVG(interest_rate) AS lai_suat_binh_quan
FROM silver.fact_creditlimitsummary
WHERE limit_type = 'Ngắn hạn'
GROUP BY bank_code;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE limit_type = 'Ngắn hạn'
+------------+--------------------+
| bank_code  | lai_suat_binh_quan |
+------------+--------------------+
|   HDBank   |       0.0875       |
|    IVB     |       0.083        |
|     MB     |       0.0861       |
|    SCB     |       0.083        |
|   TPBank   |       0.084        |
|   VPBank   |       0.0805       |
| Woori Bank |        0.07        |
+------------+--------------------+
*/

-- VISUAL: Interest YTD
-- MEASURE: _TaiChinh[Interest_YTD]
WITH monthly AS (
    SELECT DATE_TRUNC('month', month) AS thang, 
           SUM(current_period_amount) AS amount
    FROM silver.fact_incomestatement 
    WHERE indicator_code = 'B02-DN_23' 
    GROUP BY 1
)
SELECT thang AS MONTH, 
       SUM(amount) OVER(PARTITION BY DATE_TRUNC('year', thang) ORDER BY thang) AS tong_lai_da_tra_luy_ke
FROM monthly;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B02-DN_23'
+---------------------------+------------------------+
|           month           | tong_lai_da_tra_luy_ke |
+---------------------------+------------------------+
| 2026-07-01 00:00:00+00:00 |          0.00          |
| 2026-08-01 00:00:00+00:00 |          0.00          |
+---------------------------+------------------------+
*/

-- VISUAL: Cost of Debt
-- MEASURE: _TaiChinh[Cost_Of_Debt]
WITH actual_interest AS (
    SELECT DATE_TRUNC('month', month) AS thang, 
           SUM(current_period_amount) AS tong_chi_phi_lai_vay 
    FROM silver.fact_incomestatement 
    WHERE indicator_code = 'B02-DN_23' 
    GROUP BY 1
),
months AS (
    SELECT DISTINCT DATE_TRUNC('month', posting_date) AS month
    FROM silver.fact_cashflow
),
monthly_balances AS (
    SELECT m.month,
           c.account_no,
           c.credit_balance,
           ROW_NUMBER() OVER(PARTITION BY m.month, c.account_no ORDER BY c.posting_date DESC, c.id DESC) as rn
    FROM months m
    JOIN silver.fact_cashflow c ON c.posting_date < m.month + INTERVAL '1 month'
    WHERE c.account_no = '341'
),
cumulative_debt AS (
    SELECT month, SUM(credit_balance) AS tong_du_no
    FROM monthly_balances
    WHERE rn = 1
    GROUP BY month
)
SELECT i.thang AS month, 
       i.tong_chi_phi_lai_vay, 
       d.tong_du_no,
       i.tong_chi_phi_lai_vay / NULLIF(d.tong_du_no, 0) AS cost_of_debt
FROM actual_interest i
LEFT JOIN cumulative_debt d ON i.thang = d.month;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B02-DN_23'
-- WHERE c.account_no = '341'
-- WHERE rn = 1
+---------------------------+----------------------+-----------------+--------------+
|           month           | tong_chi_phi_lai_vay |    tong_du_no   | cost_of_debt |
+---------------------------+----------------------+-----------------+--------------+
| 2026-07-01 00:00:00+00:00 |         0.00         | 290982802395.00 |    0E-28     |
| 2026-08-01 00:00:00+00:00 |         0.00         | 290982802395.00 |    0E-28     |
+---------------------------+----------------------+-----------------+--------------+
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
SELECT a.account_name AS bank_name,
       SUM(c.debit_amount) AS tong_thu
FROM silver.fact_cashflow c
LEFT JOIN silver.dim_account a ON c.account_no = a.account_no
WHERE (c.account_no LIKE '111%' OR c.account_no LIKE '112%')
  AND c.voucher_no NOT LIKE 'CTNB%'
  AND c.voucher_no NOT LIKE 'NTTK%'
  AND c.reciprocal_account NOT LIKE '111%' 
  AND c.reciprocal_account NOT LIKE '112%'
GROUP BY a.account_name;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE (c.account_no LIKE '111%' OR c.account_no LIKE '112%')
-- AND c.voucher_no NOT LIKE 'CTNB%'
-- AND c.voucher_no NOT LIKE 'NTTK%'
-- AND c.reciprocal_account NOT LIKE '111%'
-- AND c.reciprocal_account NOT LIKE '112%'
+-----------------------------------------------------+-----------------+
|                      bank_name                      |     tong_thu    |
+-----------------------------------------------------+-----------------+
|                       Ngoại tệ                      |  10597708736.00 |
|           TK 0141100123005 - MB Thanh Xuân          | 259354391337.00 |
| TK 0141100810002 Thanh toán Thấu Chi - Ngân hàng MB |   36760669.00   |
|            TK 0145600027008 - MB Linh Đàm           |   519371580.00  |
|  TK 030061999899 NH Sacombank (Sài gòn thương tín)  |  67379782604.00 |
|   TK 097704070005119 HDBANK (TMCP phát triển HCM)   |  33401144194.00 |
|            TK 097840070000031/006 HD Bank           |  10597708736.00 |
|        TK 100300485745 - Ngân hàng Woori Bank       |  98890633612.00 |
|      TK 2035186001 -  Indovina IVB - CN Hà Nội      |  82427030358.00 |
|    TK 2407201007052 - NH AGRIBANK  - Hưng Yên II    |  2316477200.00  |
|                TK 474255166 - VP Bank               |  67330751047.00 |
|           TK 5859222288 NH LPB (Lộc Phát)           |   26820456.00   |
|             TK 89156688 - VPBANK Hội sở             |  3652300000.00  |
|         TK 90900283720 NH TPBank Tiên Phong         |  15720566231.00 |
|              TK 996186186  MB TT lương              |  4700002995.00  |
|                    Tiền Việt Nam                    | 635756032283.00 |
|                Tiền gửi không kỳ hạn                | 646353741019.00 |
|                       Tiền mặt                      | 438199376036.00 |
+-----------------------------------------------------+-----------------+
*/

-- VISUAL: Cơ cấu dòng chi theo Bank
-- MEASURE: _TaiChinh[Dong_Chi_Theo_Bank]
SELECT a.account_name AS bank_name,
       SUM(c.credit_amount) AS tong_chi
FROM silver.fact_cashflow c
LEFT JOIN silver.dim_account a ON c.account_no = a.account_no
WHERE (c.account_no LIKE '111%' OR c.account_no LIKE '112%')
  AND c.voucher_no NOT LIKE 'CTNB%'
  AND c.voucher_no NOT LIKE 'NTTK%'
  AND c.reciprocal_account NOT LIKE '111%' 
  AND c.reciprocal_account NOT LIKE '112%'
GROUP BY a.account_name;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE (c.account_no LIKE '111%' OR c.account_no LIKE '112%')
-- AND c.voucher_no NOT LIKE 'CTNB%'
-- AND c.voucher_no NOT LIKE 'NTTK%'
-- AND c.reciprocal_account NOT LIKE '111%'
-- AND c.reciprocal_account NOT LIKE '112%'
+-----------------------------------------------------+-----------------+
|                      bank_name                      |     tong_chi    |
+-----------------------------------------------------+-----------------+
|                       Ngoại tệ                      |  12506548412.00 |
|           TK 0141100123005 - MB Thanh Xuân          | 310516142916.00 |
| TK 0141100810002 Thanh toán Thấu Chi - Ngân hàng MB |   313760669.00  |
|            TK 0145600027008 - MB Linh Đàm           |       0.00      |
|  TK 030061999899 NH Sacombank (Sài gòn thương tín)  |  74516837258.00 |
|   TK 097704070005119 HDBANK (TMCP phát triển HCM)   |  31615623381.00 |
|            TK 097840070000031/006 HD Bank           |  12506548412.00 |
|        TK 100300485745 - Ngân hàng Woori Bank       |  70475216547.00 |
|      TK 2035186001 -  Indovina IVB - CN Hà Nội      | 135015928766.00 |
|    TK 2407201007052 - NH AGRIBANK  - Hưng Yên II    |  5457605384.00  |
|                TK 474255166 - VP Bank               |  51134663382.00 |
|           TK 5859222288 NH LPB (Lộc Phát)           |    846142.00    |
|             TK 89156688 - VPBANK Hội sở             |       0.00      |
|         TK 90900283720 NH TPBank Tiên Phong         |  32706078649.00 |
|              TK 996186186  MB TT lương              |  15102356152.00 |
|                    Tiền Việt Nam                    | 726855059246.00 |
|                Tiền gửi không kỳ hạn                | 739361607658.00 |
|                       Tiền mặt                      |  84548164160.00 |
+-----------------------------------------------------+-----------------+
*/

-- VISUAL: Bảng tổng hợp 18 Chỉ số
-- MEASURE: _TaiChinh[Ratios]
WITH md AS (SELECT CAST('2026-07-31' AS date) AS dt),
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
    WHERE month = (SELECT dt FROM md) 
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
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_223' OR indicator_code='B01-DN_228'), 0) AS khau_hao,
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
-- WHERE month = (SELECT dt FROM md)
-- WHERE account_no LIKE '341%' AND DATE_TRUNC('month', posting_date) <= DATE_TRUNC('month', (SELECT dt FROM md))
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_100'), 0) AS ts_ngan_han,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_310'), 0) AS no_ngan_han,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_140'), 0) AS ton_kho,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_130'), 0) AS phai_thu,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_400'), 0) AS vcsh,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_300'), 0) AS no_phai_tra,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_330'), 0) AS no_dai_han,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_440'), 0) AS tong_ts,
-- COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_223' OR indicator_code='B01-DN_228'), 0) AS khau_hao,
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
+--------------------+------------------------+------------------------+-------------------+------------------------+--------------------------+----------------------+----------------+-----------------+-------------------+---------------------+------------------------+------------------------+--------------------+------------------------+------------------------+-------------------------+
|   current_ratio    |      quick_ratio       |     vong_quay_vld      | vong_quay_ton_kho |   vong_quay_phai_thu   | no_phai_tra_tren_tong_ts | no_dai_han_tren_vcsh |      ebit      |      ebitda     | ebit_tren_lai_vay | ebitda_tren_lai_vay |      bien_ln_gop       |      bien_ln_hdkd      |    bien_ebitda     |          roe           |          roa           |  tong_du_no_tren_ebitda |
+--------------------+------------------------+------------------------+-------------------+------------------------+--------------------------+----------------------+----------------+-----------------+-------------------+---------------------+------------------------+------------------------+--------------------+------------------------+------------------------+-------------------------+
| 1.3861467792621685 | 0.86334807868217378402 | 0.60390916554491703161 |       0E-28       | 0.38740328066320749642 |  0.63580376382791085809  |        0E-28         | 74991248312.00 | 155376091127.00 |        None       |         None        | 1.00000000000000000000 | 1.00000000000000000000 | 2.0719229860071142 | 0.40710991457805347384 | 0.14826789859766779924 | -0.58049602134267237608 |
+--------------------+------------------------+------------------------+-------------------+------------------------+--------------------------+----------------------+----------------+-----------------+-------------------+---------------------+------------------------+------------------------+--------------------+------------------------+------------------------+-------------------------+
*/

-- VISUAL: Chi tiết tài sản đảm bảo
-- MEASURE: _TaiChinh[TSDB]
SELECT collateral_type AS ten_tai_san,
       appraised_value AS gia_tri_tham_dinh,
       collateral_coefficient AS he_so_tsdb,
       appraised_value * CAST(collateral_coefficient AS numeric) AS gia_tri_cho_vay
FROM silver.fact_collateral;

/* RESULT LOG:
+-------------+-------------------+--------------------+-------------------------------+
| ten_tai_san | gia_tri_tham_dinh |     he_so_tsdb     |        gia_tri_cho_vay        |
+-------------+-------------------+--------------------+-------------------------------+
|     BĐS     |   7854464000.00   |        0.9         |         7069017600.000        |
|     BĐS     |   6347108454.00   |        0.65        |        4125620495.1000        |
|     BĐS     |   5349600000.00   |        0.9         |         4814640000.000        |
|     BĐS     |   2378899937.00   |        0.75        |        1784174952.7500        |
|     HĐTG    |   2000000000.00   |         1          |         2000000000.00         |
|     MMTB    |   2087071580.00   |        0.5         |         1043535790.000        |
|     MMTB    |   5364349760.00   |        0.5         |         2682174880.000        |
|     MMTB    |   10875812640.00  |        0.5         |         5437906320.000        |
|     MMTB    |   6915895800.00   |        0.5         |         3457947900.000        |
|     MMTB    |   21379150800.00  |        0.5         |        10689575400.000        |
|     MMTB    |   21365127000.00  |        0.5         |        10682563500.000        |
|     PTVT    |   1978000000.00   |        0.65        |        1285700000.0000        |
|     PTVT    |    401800000.00   |        0.65        |         261170000.0000        |
|     PTVT    |    500000000.00   |        0.65        |         325000000.0000        |
|     HTK     |   53500000000.00  |        0.7         |        37450000000.000        |
|      TC     |   10000000000.00  |         1          |         10000000000.00        |
|     BĐS     |   7650000000.00   |        0.9         |         6885000000.000        |
...(TRUNCATED FOR READABILITY)...
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
...(TRUNCATED FOR READABILITY)...
*/

