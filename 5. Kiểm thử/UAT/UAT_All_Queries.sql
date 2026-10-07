-- TONG HOP SQL TEST SCRIPT (UAT)
-- DU AN GO MINH LONG

-- ==========================================
-- DASHBOARD: QUẢN TRỊ HOẠT ĐỘNG TÀI CHÍNH
-- ==========================================

-- VISUAL: Dư nợ ngắn hạn
-- MEASURE: _TaiChinh[Du_No_Ngan_Han]
SELECT SUM(credit_amount) - SUM(debit_amount) FROM silver.fact_cashflow WHERE account_no LIKE '34111%';

-- VISUAL: Dư nợ dài hạn
-- MEASURE: _TaiChinh[Du_No_Dai_Han]
SELECT SUM(credit_amount) - SUM(debit_amount) FROM silver.fact_cashflow WHERE account_no LIKE '34112%';

-- VISUAL: Hạn mức được phê duyệt
-- MEASURE: _TaiChinh[Han_Muc_Phe_Duyet]
SELECT SUM(credit_limit) FROM silver.fact_creditlimitsummary;

-- VISUAL: Hạn mức được cấp
-- MEASURE: _TaiChinh[Han_Muc_Duoc_Cap]
SELECT SUM(granted_limit) FROM silver.fact_creditlimitsummary;

-- VISUAL: Hạn mức còn lại
-- MEASURE: _TaiChinh[Han_Muc_Con_Lai]
SELECT SUM(granted_limit) - SUM(principal_balance) FROM silver.fact_creditlimitsummary;

-- VISUAL: Loan to Value (LTV)
-- MEASURE: _TaiChinh[LTV_Ratio]
SELECT (SELECT SUM(granted_limit) FROM silver.fact_creditlimitsummary) / NULLIF((SELECT SUM(appraised_value) FROM silver.fact_collateral), 0) AS ltv_ratio;

-- VISUAL: DEBT/EQUITY
-- MEASURE: _TaiChinh[Debt_Equity]
WITH bs AS (SELECT reporting_date FROM silver.fact_balancesheet ORDER BY reporting_date DESC LIMIT 1) SELECT (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code = 'B01-DN_300' AND reporting_date = (SELECT reporting_date FROM bs)) / NULLIF((SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code = 'B01-DN_400' AND reporting_date = (SELECT reporting_date FROM bs)), 0);

-- VISUAL: Nợ ngắn/dài hạn theo thời gian
-- MEASURE: _TaiChinh[Du_No_Theo_Thang]
SELECT DATE_TRUNC('month', posting_date) AS month, SUM(CASE WHEN account_no LIKE '34111%' THEN credit_amount - debit_amount ELSE 0 END) AS no_ngan_han, SUM(CASE WHEN account_no LIKE '34112%' THEN credit_amount - debit_amount ELSE 0 END) AS no_dai_han, SUM(credit_amount - debit_amount) AS tong_du_no FROM silver.fact_cashflow WHERE account_no LIKE '341%' GROUP BY 1;

-- VISUAL: Chi phí lãi vay thực tế vs KH
-- MEASURE: _TaiChinh[Chi_Phi_Lai_Vay]
SELECT DATE_TRUNC('month', reporting_date) AS month, SUM(current_period_amount) AS chi_phi_thuc_te, (SELECT SUM(target_amount) FROM silver.fact_businessplan WHERE indicator_code = 'B02-DN_23') AS ke_hoach FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_23' GROUP BY 1;

-- VISUAL: Lãi suất bình quân bank
-- MEASURE: _TaiChinh[Lai_Suat_BQ_Bank]
SELECT bank_code, AVG(interest_rate) AS lai_suat_binh_quan FROM silver.fact_termdeposit GROUP BY 1;

-- VISUAL: Interest YTD
-- MEASURE: _TaiChinh[Interest_YTD]
SELECT DATE_TRUNC('month', reporting_date) AS month, SUM(SUM(current_period_amount)) OVER (ORDER BY DATE_TRUNC('month', reporting_date)) AS tong_lai_da_tra_luy_ke FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_23' GROUP BY 1;

-- VISUAL: Cost of Debt
-- MEASURE: _TaiChinh[Cost_Of_Debt]
SELECT DATE_TRUNC('month', i.posting_date) AS month, SUM(i.current_period_amount) AS tong_chi_phi_lai_vay, (SELECT SUM(credit_amount - debit_amount) FROM silver.fact_cashflow c WHERE DATE_TRUNC('month', c.posting_date) <= DATE_TRUNC('month', i.posting_date) AND c.account_no LIKE '341%') AS tong_du_no FROM silver.fact_incomestatement i WHERE i.indicator_code = 'B02-DN_23' GROUP BY 1;

-- VISUAL: Dư nợ theo Bank
-- MEASURE: _TaiChinh[Du_No_Goc]
SELECT bank_code, SUM(credit_amount - debit_amount) AS du_no_goc FROM silver.fact_cashflow WHERE account_no LIKE '341%' GROUP BY bank_code;

-- VISUAL: Cơ cấu dòng thu theo Bank
-- MEASURE: _TaiChinh[Dong_Thu_Theo_Bank]
SELECT bank_code, SUM(debit_amount) AS tong_thu FROM silver.fact_cashflow WHERE account_no IN ('1111','1121') AND voucher_no NOT LIKE 'CTNB%' GROUP BY bank_code;

-- VISUAL: Cơ cấu dòng chi theo Bank
-- MEASURE: _TaiChinh[Dong_Chi_Theo_Bank]
SELECT bank_code, SUM(credit_amount) AS tong_chi FROM silver.fact_cashflow WHERE account_no IN ('1111','1121') AND voucher_no NOT LIKE 'CTNB%' GROUP BY bank_code;

-- VISUAL: Bảng tổng hợp 18 Chỉ số
-- MEASURE: _TaiChinh[Ratios]
WITH md AS(SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet) SELECT (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_100' AND reporting_date=(SELECT dt FROM md))/NULLIF((SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code='B01-DN_310' AND reporting_date=(SELECT dt FROM md)),0) AS current_ratio; -- Và các chỉ số khác

-- VISUAL: Chi tiết tài sản đảm bảo
-- MEASURE: _TaiChinh[TSDB]
SELECT collateral_type AS ten_tai_san, appraised_value AS gia_tri_tham_dinh, collateral_ratio AS he_so_tsdb, appraised_value * collateral_ratio AS gia_tri_cho_vay FROM silver.fact_collateral;

-- VISUAL: Bảng cảnh báo rủi ro
-- MEASURE: _TaiChinh[Canh_Bao]
SELECT bank_code, CASE WHEN (SELECT SUM(granted_limit)/SUM(appraised_value) FROM silver.fact_creditlimitsummary c JOIN silver.fact_collateral col ON c.bank_code=col.bank_code) > 0.8 THEN 'LTV > 80%' ELSE 'OK' END AS warning_ltv FROM silver.fact_creditlimitsummary GROUP BY bank_code;

-- VISUAL: Lịch trả gốc ngân hàng
-- MEASURE: _TaiChinh[Lich_Tra_Goc]
SELECT bank_code, (CURRENT_DATE + interval '30 days') AS ngay_can_tra_goc, SUM(principal_amount) AS so_tien_can_tra FROM silver.fact_creditlimitsummary GROUP BY 1, 2;

-- ==========================================
-- DASHBOARD: QUẢN TRỊ HÀNG TỒN KHO
-- ==========================================

-- VISUAL: Số lượng HTK
-- MEASURE: _TonKho[So_Luong_Ton]
SELECT SUM(ending_quantity) AS sl_ton_kho FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(reporting_date) FROM silver.fact_inventory_balance);

-- VISUAL: Giá trị HTK
-- MEASURE: _TonKho[Gia_Tri_Ton]
SELECT SUM(ending_value) AS gt_ton_kho FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(reporting_date) FROM silver.fact_inventory_balance);

-- VISUAL: Vòng quay HTK
-- MEASURE: _TonKho[Vong_Quay_HTK]
SELECT (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_11') / NULLIF((SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(reporting_date) FROM silver.fact_inventory_balance)), 0) AS vong_quay_htk;

-- VISUAL: Inventory to sales ratio
-- MEASURE: _TonKho[Inventory_To_Sales]
SELECT (SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(reporting_date) FROM silver.fact_inventory_balance)) / NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_10'), 0) AS i_s_ratio;

-- VISUAL: Tổng mã sản phẩm
-- MEASURE: _TonKho[Tong_SKU]
SELECT COUNT(DISTINCT product_code) AS tong_sku FROM silver.fact_inventory_balance WHERE ending_quantity > 0;

-- VISUAL: Giá trị hàng nhập khẩu
-- MEASURE: _TonKho[Gia_Tri_Nhap]
SELECT SUM(inward_value) AS gia_tri_nhap_khau FROM silver.fact_inventoryinward WHERE exchange_rate > 1;

-- VISUAL: Tồn kho theo thời gian
-- MEASURE: _TonKho[Ton_Kho_Theo_Thang]
SELECT DATE_TRUNC('month', snapshot_date) AS month, SUM(ending_quantity) AS so_luong, SUM(ending_value) AS gia_tri FROM silver.fact_inventory_balance GROUP BY 1 ORDER BY 1;

-- VISUAL: Vòng quay HTK theo thời gian
-- MEASURE: _TonKho[Vong_Quay_Thang]
SELECT DATE_TRUNC('month', b.reporting_date) AS month, SUM(i.current_period_amount) / NULLIF(SUM(b.ending_value), 0) AS he_so_vong_quay FROM silver.fact_inventory_balance b LEFT JOIN silver.fact_incomestatement i ON DATE_TRUNC('month', b.reporting_date) = DATE_TRUNC('month', i.reporting_date) AND i.indicator_code='B02-DN_11' GROUP BY 1;

-- VISUAL: Inventory to Sales
-- MEASURE: _TonKho[IS_Theo_Thang]
SELECT DATE_TRUNC('month', b.reporting_date) AS month, SUM(b.ending_value) / NULLIF(SUM(i.current_period_amount), 0) AS ty_le_is FROM silver.fact_inventory_balance b LEFT JOIN silver.fact_incomestatement i ON DATE_TRUNC('month', b.reporting_date) = DATE_TRUNC('month', i.reporting_date) AND i.indicator_code='B02-DN_10' GROUP BY 1;

-- VISUAL: Trạng thái Inventory
-- MEASURE: _TonKho[Trang_Thai]
SELECT DATE_TRUNC('month', posting_date) AS month, SUM(inward_value) AS nhap_kho FROM silver.fact_inventoryinward GROUP BY 1;

-- VISUAL: Top 10 dư tồn kho
-- MEASURE: _TonKho[Top_10_Ton]
SELECT product_code, SUM(ending_value) AS gia_tri FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(reporting_date) FROM silver.fact_inventory_balance) GROUP BY 1 ORDER BY gia_tri DESC LIMIT 10;

-- VISUAL: Giá trị hàng xuất kho thực tế vs Kế hoạch
-- MEASURE: _TonKho[Xuat_Vs_KH]
SELECT DATE_TRUNC('month', o.posting_date) AS month, SUM(o.outward_value) AS gia_tri_xuat_thuc_te, (SELECT SUM(target_amount) FROM silver.fact_businessplan WHERE indicator_code = 'B02-DN_11' AND month = DATE_TRUNC('month', o.posting_date)) AS ke_hoach FROM silver.fact_inventoryoutward o GROUP BY 1;

-- ==========================================
-- DASHBOARD: QUẢN TRỊ PHẢI THU - PHẢI TRẢ
-- ==========================================

-- VISUAL: Giá trị phải thu
-- MEASURE: _CongNo[Gia_Tri_Phai_Thu]
SELECT SUM(debit_amount - credit_amount) AS gia_tri_phai_thu FROM silver.fact_accountsreceivable;

-- VISUAL: Giá trị phải trả
-- MEASURE: _CongNo[Gia_Tri_Phai_Tra]
SELECT SUM(credit_amount - debit_amount) AS gia_tri_phai_tra FROM silver.fact_accountspayable;

-- VISUAL: Vòng quay phải thu theo năm
-- MEASURE: _CongNo[VQ_Phai_Thu_Nam]
SELECT (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' AND EXTRACT(YEAR FROM reporting_date) = EXTRACT(YEAR FROM CURRENT_DATE)) / NULLIF((SELECT SUM(debit_amount - credit_amount) FROM silver.fact_accountsreceivable), 0);

-- VISUAL: Vòng quay phải thu hiện tại
-- MEASURE: _CongNo[VQ_Phai_Thu_Thang]
SELECT (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' AND EXTRACT(MONTH FROM month) = EXTRACT(MONTH FROM CURRENT_DATE)) / NULLIF((SELECT SUM(debit_amount - credit_amount) FROM silver.fact_accountsreceivable), 0);

-- VISUAL: Tổng hóa đơn
-- MEASURE: _CongNo[Tong_Hoa_Don]
SELECT COUNT(DISTINCT invoice_no) AS tong_hoa_don FROM silver.fact_accountsreceivable;

-- VISUAL: Tổng số khách hàng
-- MEASURE: _CongNo[Tong_KH]
SELECT COUNT(DISTINCT partner_code) AS tong_khach_hang FROM silver.fact_accountsreceivable WHERE debit_amount - credit_amount > 0;

-- VISUAL: Phải thu theo tháng
-- MEASURE: _CongNo[Phai_Thu_Thang]
SELECT DATE_TRUNC('month', posting_date) AS month, SUM(CASE WHEN CURRENT_DATE <= invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) AS no_trong_han FROM silver.fact_accountsreceivable GROUP BY 1;

-- VISUAL: Receivable Turnover
-- MEASURE: _CongNo[VQ_Phai_Thu]
SELECT DATE_TRUNC('month', posting_date) AS month, SUM(debit_amount - credit_amount) AS du_no_thang FROM silver.fact_accountsreceivable GROUP BY 1;

-- VISUAL: Top 10 KH nợ cao nhất
-- MEASURE: _CongNo[Top_10_No]
SELECT partner_code, SUM(debit_amount - credit_amount) AS du_no FROM silver.fact_accountsreceivable GROUP BY 1 ORDER BY du_no DESC LIMIT 10;

-- VISUAL: Top 10 KH dư nợ quá hạn (Nợ xấu)
-- MEASURE: _CongNo[Top_10_Qua_Han]
SELECT partner_code, SUM(CASE WHEN CURRENT_DATE > invoice_date + 30 THEN debit_amount - credit_amount ELSE 0 END) AS no_qua_han FROM silver.fact_accountsreceivable GROUP BY 1 ORDER BY no_qua_han DESC LIMIT 10;

-- VISUAL: Tuổi nợ Aging
-- MEASURE: _CongNo[Aging]
SELECT CASE WHEN CURRENT_DATE <= invoice_date + 30 THEN 'Current' ELSE 'Overdue' END AS age_bucket, SUM(debit_amount - credit_amount) AS gia_tri FROM silver.fact_accountsreceivable GROUP BY 1;

-- VISUAL: Chi tiết nợ theo Khách hàng
-- MEASURE: _CongNo[Chi_Tiet_No_KH]
SELECT partner_code AS ma_kh, SUM(debit_amount - credit_amount) AS tong_phai_thu FROM silver.fact_accountsreceivable GROUP BY 1;

-- VISUAL: Chi tiết hóa đơn nợ
-- MEASURE: _CongNo[Chi_Tiet_HD]
SELECT invoice_no AS so_hoa_don, debit_amount - credit_amount AS so_tien_con_no FROM silver.fact_accountsreceivable WHERE debit_amount - credit_amount > 0;

-- ==========================================
-- DASHBOARD: QUẢN TRỊ TIỀN GỬI VÀ THANH KHOẢN
-- ==========================================

-- VISUAL: Tiền và các khoản tương đương tiền
-- MEASURE: _TienGui&ThanhKhoan[Tien_TuongDuongTien]
SELECT ending_balance FROM silver.fact_balancesheet WHERE indicator_code = 'B01-DN_110' AND reporting_date = '2026-01-31';

-- VISUAL: Tiền gửi
-- MEASURE: silver fact_termdeposit[remaining_value]
SELECT SUM(original_amount) AS total_original_amount, SUM(remaining_value) AS total_remaining_value FROM silver.fact_termdeposit WHERE deposit_date >= '2025-04-01' AND deposit_date <= '2025-04-30';

-- VISUAL: Số lượng hợp đồng tiền gửi
-- MEASURE: _TienGui&ThanhKhoan[So_HD_Theo_Ngan_Hang]
SELECT COUNT(*) AS total_contracts, COUNT(CASE WHEN remaining_value > 0 THEN 1 END) AS active_contracts FROM silver.fact_termdeposit WHERE deposit_date >= '2025-04-01' AND deposit_date <= '2025-04-30';

-- VISUAL: Lãi suất bình quân
-- MEASURE: _TienGui&ThanhKhoan[Lai_Suat_BQ]
SELECT ROUND((SUM(original_amount * interest_rate) / SUM(original_amount) * 100)::numeric, 2) AS Lai_Suat_BQ_Percent FROM silver.fact_termdeposit WHERE remaining_value > 0;

-- VISUAL: Thu nhập lãi
-- MEASURE: _TienGui&ThanhKhoan[Tong_Dedit_Account_515]
SELECT SUM(debit_amount) AS Tong_Dedit_Account_515 FROM silver.fact_cashflow WHERE reciprocal_account = '515';

-- VISUAL: Cơ cấu theo Ngân hàng
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Bank]
SELECT bank_code, SUM(original_amount) AS tri_gia_goc FROM silver.fact_termdeposit GROUP BY bank_code;

-- VISUAL: Cơ cấu theo Kỳ hạn
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Ky_Han]
SELECT term, SUM(original_amount) AS tri_gia_goc FROM silver.fact_termdeposit GROUP BY term;

-- VISUAL: Chi tiết Hợp đồng tiền gửi
-- MEASURE: _TienGui&ThanhKhoan[Chi_Tiet_HD]
SELECT bank_code, interest_rate, term, passbook_no, original_amount, deposit_date, maturity_date FROM silver.fact_termdeposit;

-- ==========================================
-- DASHBOARD: QUẢN TRỊ DÒNG TIỀN
-- ==========================================

-- VISUAL: Dòng tiền ra
-- MEASURE: _DongTien[Dong_Tien_Ra]
SELECT SUM(credit_amount) FROM silver.fact_cashflow WHERE account_no LIKE '111%' OR account_no LIKE '112%';

-- VISUAL: Dòng tiền vào
-- MEASURE: _DongTien[Dong_Tien_Vao]
SELECT SUM(debit_amount) FROM silver.fact_cashflow WHERE account_no LIKE '111%' OR account_no LIKE '112%';

-- VISUAL: Cash Balance
-- MEASURE: _DongTien[Cash_Balance]
SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code = 'B01-DN_110' AND reporting_date = (SELECT MAX(reporting_date) FROM silver.fact_balancesheet);

-- VISUAL: Thu/Chi/Số dư theo tháng
-- MEASURE: _DongTien[Thu_Chi_Thang]
SELECT DATE_TRUNC('month', posting_date) AS month, SUM(debit_amount) AS dong_tien_vao, SUM(credit_amount) AS dong_tien_ra FROM silver.fact_cashflow WHERE account_no LIKE '11%' GROUP BY 1;

-- VISUAL: Cơ cấu dòng thu theo Bank
-- MEASURE: _DongTien[Dong_Thu_Bank]
SELECT bank_code, reciprocal_account, SUM(debit_amount) AS gia_tri_thu FROM silver.fact_cashflow WHERE account_no LIKE '112%' GROUP BY 1, 2;

-- VISUAL: Cơ cấu dòng chi theo Bank
-- MEASURE: _DongTien[Dong_Chi_Bank]
SELECT bank_code, reciprocal_account, SUM(credit_amount) AS gia_tri_chi FROM silver.fact_cashflow WHERE account_no LIKE '112%' GROUP BY 1, 2;

-- VISUAL: Tài sản/Nợ/VLĐ
-- MEASURE: _DongTien[Working_Capital]
SELECT DATE_TRUNC('month', reporting_date) AS month, SUM(CASE WHEN indicator_code='B01-DN_100' THEN ending_balance ELSE 0 END) - SUM(CASE WHEN indicator_code='B01-DN_310' THEN ending_balance ELSE 0 END) AS vld_rong FROM silver.fact_balancesheet GROUP BY 1;

-- VISUAL: Bảng Runway
-- MEASURE: _DongTien[Runway]
SELECT (SELECT SUM(ending_balance) FROM silver.fact_balancesheet WHERE indicator_code = 'B01-DN_110' AND posting_date = (SELECT MAX(posting_date) FROM silver.fact_balancesheet)) / NULLIF((SELECT SUM(credit_amount - debit_amount)/12 FROM silver.fact_cashflow WHERE EXTRACT(YEAR FROM posting_date)=EXTRACT(YEAR FROM CURRENT_DATE) AND account_no LIKE '11%'), 0) AS runway;

-- VISUAL: Bảng Chu kỳ tiền mặt CCC
-- MEASURE: _DongTien[CCC]
SELECT (SELECT SUM(ending_balance)/NULLIF(SUM(current_period_amount),0)*365 FROM silver.fact_balancesheet b JOIN silver.fact_incomestatement i ON b.reporting_date=i.reporting_date WHERE b.indicator_code='B01-DN_130' AND i.indicator_code='B02-DN_10') AS dso, (SELECT SUM(ending_balance)/NULLIF(SUM(current_period_amount),0)*365 FROM silver.fact_balancesheet b JOIN silver.fact_incomestatement i ON b.reporting_date=i.reporting_date WHERE b.indicator_code='B01-DN_140' AND i.indicator_code='B02-DN_11') AS dio, (SELECT SUM(ending_balance)/NULLIF(SUM(current_period_amount),0)*365 FROM silver.fact_balancesheet b JOIN silver.fact_incomestatement i ON b.reporting_date=i.reporting_date WHERE b.indicator_code='B01-DN_311' AND i.indicator_code='B02-DN_11') AS dpo;

