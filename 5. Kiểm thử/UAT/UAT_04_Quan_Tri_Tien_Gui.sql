-- TONG HOP SQL TEST SCRIPT (UAT)
-- DU AN GO MINH LONG

-- ==========================================
-- DASHBOARD: QUẢN TRỊ TIỀN GỬI VÀ THANH KHOẢN

-- ==========================================
-- VISUAL: Tiền và các khoản tương đương tiền
-- MEASURE: _TienGui&ThanhKhoan[Tien_TuongDuongTien]

SELECT ending_balance
FROM silver.fact_balancesheet
WHERE indicator_code = 'B01-DN_110'
  AND reporting_date = '2026-01-31';

-- VISUAL: Tiền gửi
-- MEASURE: silver fact_termdeposit[remaining_value]
SELECT SUM(original_amount) AS total_original_amount,
       SUM(remaining_value) AS total_remaining_value
FROM silver.fact_termdeposit
WHERE deposit_date >= '2025-04-01'
  AND deposit_date <= '2025-04-30';

-- VISUAL: Số lượng hợp đồng tiền gửi
-- MEASURE: _TienGui&ThanhKhoan[So_HD_Theo_Ngan_Hang]
SELECT COUNT(*) AS total_contracts,
       COUNT(CASE
                 WHEN remaining_value > 0 THEN 1
             END) AS active_contracts
FROM silver.fact_termdeposit
WHERE deposit_date >= '2025-04-01'
  AND deposit_date <= '2025-04-30';

-- VISUAL: Lãi suất bình quân
-- MEASURE: _TienGui&ThanhKhoan[Lai_Suat_BQ]
SELECT ROUND((SUM(original_amount * interest_rate) / SUM(original_amount) * 100)::numeric, 2) AS Lai_Suat_BQ_Percent
FROM silver.fact_termdeposit
WHERE remaining_value > 0;

-- VISUAL: Thu nhập lãi
-- MEASURE: _TienGui&ThanhKhoan[Tong_Dedit_Account_515]
SELECT SUM(debit_amount) AS Tong_Dedit_Account_515
FROM silver.fact_cashflow
WHERE reciprocal_account = '515';

-- VISUAL: Cơ cấu theo Ngân hàng
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Bank]
SELECT bank_code,
       SUM(original_amount) AS tri_gia_goc
FROM silver.fact_termdeposit
GROUP BY bank_code;

-- VISUAL: Cơ cấu theo Kỳ hạn
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Ky_Han]
SELECT term,
       SUM(original_amount) AS tri_gia_goc
FROM silver.fact_termdeposit
GROUP BY term;

-- VISUAL: Chi tiết Hợp đồng tiền gửi
-- MEASURE: _TienGui&ThanhKhoan[Chi_Tiet_HD]
SELECT bank_code,
       interest_rate,
       term,
       passbook_no,
       original_amount,
       deposit_date,
       maturity_date
FROM silver.fact_termdeposit;

