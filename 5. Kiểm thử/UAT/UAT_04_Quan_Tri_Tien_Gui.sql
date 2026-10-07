-- ==========================================
-- DASHBOARD: QUẢN TRỊ TIỀN GỬI VÀ THANH KHOẢN
-- ==========================================

-- VISUAL: Tiền và các khoản tương đương tiền
-- MEASURE: _TienGui&ThanhKhoan[Tien_TuongDuongTien]
SELECT ending_balance
FROM silver.fact_balancesheet
WHERE indicator_code = ''B01-DN_110''
  AND reporting_date = (SELECT MAX(reporting_date) FROM silver.fact_balancesheet);

-- VISUAL: Tiền gửi
-- MEASURE: silver fact_termdeposit[remaining_value]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT SUM(original_amount) AS total_original_amount
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);

-- VISUAL: Số lượng hợp đồng tiền gửi
-- MEASURE: _TienGui&ThanhKhoan[So_HD_Theo_Ngan_Hang]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT COUNT(DISTINCT passbook_no) AS active_contracts
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);

-- VISUAL: Lãi suất bình quân
-- MEASURE: _TienGui&ThanhKhoan[Lai_Suat_BQ]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT SUM(original_amount * interest_rate) / NULLIF(SUM(original_amount), 0) AS lai_suat_binh_quan
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);

-- VISUAL: Thu nhập lãi
-- MEASURE: _TienGui&ThanhKhoan[Tong_Dedit_Account_515]
SELECT SUM(debit_amount) AS thu_nhap_lai
FROM silver.fact_cashflow
WHERE reciprocal_account LIKE ''515%'';

-- VISUAL: Cơ cấu theo Ngân hàng
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Bank]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT bank_code,
       SUM(original_amount) AS tri_gia_goc
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL)
GROUP BY bank_code;

-- VISUAL: Cơ cấu theo Kỳ hạn
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Ky_Han]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT term,
       SUM(original_amount) AS tri_gia_goc
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL)
GROUP BY term;

-- VISUAL: Chi tiết Hợp đồng tiền gửi
-- MEASURE: _TienGui&ThanhKhoan[Chi_Tiet_HD]
SELECT bank_code,
       interest_rate,
       term,
       passbook_no,
       original_amount,
       deposit_date,
       maturity_date,
       settlement_date
FROM silver.fact_termdeposit;
