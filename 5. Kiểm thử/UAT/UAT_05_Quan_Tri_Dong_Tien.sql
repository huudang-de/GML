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
SELECT 
    b.bank_code AS bank_code,           -- Mã ngân hàng (VD: VCB, BIDV, TCB,...)
    c.reciprocal_account,               -- Tài khoản đối ứng (VD: 131 - Phải thu khách hàng, 331,...)
    SUM(c.debit_amount) AS gia_tri_thu  -- Tổng giá trị tiền thu vào (Phát sinh Nợ của tài khoản tiền gửi 112)
FROM silver.fact_cashflow c
-- Liên kết với bảng danh mục tài khoản kế toán để xác định tài khoản ngân hàng nào đang phát sinh giao dịch
LEFT JOIN silver.dim_account a 
    ON c.account_no = a.account_no
-- Liên kết với bảng danh mục số tài khoản ngân hàng để quy đổi ra mã viết tắt của ngân hàng
LEFT JOIN silver.dim_accountnumber b 
    ON a.account_bank = b.account_bank
WHERE 
    -- 1. Chỉ lọc các giao dịch phát sinh trên hệ thống tài khoản Tiền gửi ngân hàng (TK 112 theo Chế độ kế toán doanh nghiệp Việt Nam)
    c.account_no LIKE '112%'
    
    -- 2. Loại trừ các chứng từ chuyển tiền nội bộ (Mã ký hiệu CTNB trên MISA)
    AND c.voucher_no NOT LIKE 'CTNB%'
    
    -- 3. Loại trừ các chứng từ nộp tiền/chuyển tiền nội bộ khác (Mã ký hiệu NTTK)
    AND c.voucher_no NOT LIKE 'NTTK%'
    
    -- 4. Lọc sạch các giao dịch đối ứng nội bộ: Không lấy tài khoản đối ứng là Tiền mặt (111) hoặc các TK Tiền gửi khác (112)
    -- Giúp báo cáo dòng tiền chỉ phản ánh các khoản thu thực tế từ bên ngoài (Khách hàng thanh toán, đối tác chuyển tiền...), 
    -- tránh bị sai lệch do nghiệp vụ rút tiền gửi về quỹ tiền mặt hoặc luân chuyển nội bộ giữa các tài khoản cty.
    AND c.reciprocal_account NOT LIKE '111%' 
    AND c.reciprocal_account NOT LIKE '112%'
GROUP BY 
    b.bank_code, 
    c.reciprocal_account;

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

-- VISUAL: Cơ cấu dòng chi theo Bank (Phân tích dòng tiền chi thực tế từ các tài khoản ngân hàng ra bên ngoài)

SELECT 
    b.bank_code AS bank_code,           -- Mã ngân hàng chi tiền (VD: VCB, BIDV, TCB,...)
    c.reciprocal_account,               -- Tài khoản đối ứng (VD: 331 - Phải trả người bán, 334, 333,...)
    SUM(c.credit_amount) AS gia_tri_chi -- Tổng giá trị tiền chi ra (Phát sinh Có của tài khoản tiền gửi 112)
FROM silver.fact_cashflow c
-- Liên kết với danh mục tài khoản kế toán để ánh xạ số hiệu tài khoản
LEFT JOIN silver.dim_account a 
    ON c.account_no = a.account_no
-- Liên kết với danh mục ngân hàng để quy đổi ra mã định danh ngân hàng rút tiền
LEFT JOIN silver.dim_accountnumber b 
    ON a.account_bank = b.account_bank
WHERE 
    -- 1. Chỉ tập trung vào các giao dịch xuất quỹ tiền gửi ngân hàng (TK 112)
    c.account_no LIKE '112%'
    
    -- 2. Loại trừ các chứng từ chuyển tiền nội bộ hệ thống công ty (Mã CTNB)
    AND c.voucher_no NOT LIKE 'CTNB%'
    
    -- 3. Loại trừ các chứng từ nộp/chuyển tiền nội bộ khác (Mã NTTK)
    AND c.voucher_no NOT LIKE 'NTTK%'
    
    -- 4. Loại bỏ các bút toán đối ứng nội bộ: Không lấy tài khoản đối ứng là Tiền mặt (111) hoặc Tiền gửi khác (112)
    -- Đảm bảo chỉ đo lường đúng dòng tiền thanh toán thực tế ra bên ngoài (trả tiền nhà cung cấp, nộp thuế, chi phí vận hành...), 
    -- tránh làm sai lệch số liệu do nghiệp vụ rút tiền gửi nhập quỹ tiền mặt hoặc điều chuyển vốn nội bộ giữa các tài khoản.
    AND c.reciprocal_account NOT LIKE '111%' 
    AND c.reciprocal_account NOT LIKE '112%'
GROUP BY 
    b.bank_code, 
    c.reciprocal_account;

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

-- VISUAL: Bảng theo dõi Tài sản ngắn hạn, Nợ ngắn hạn và Vốn lưu động ròng theo tháng

SELECT
    DATE_TRUNC('month', reporting_date) AS thang_bao_cao,
    
    -- 1. Tài sản ngắn hạn (Mã chỉ tiêu B01-DN_100 theo chuẩn VAS)
    SUM(CASE WHEN indicator_code = 'B01-DN_100' THEN ending_balance ELSE 0 END) AS tai_san_ngan_han,
    
    -- 2. Nợ ngắn hạn (Mã chỉ tiêu B01-DN_310 theo chuẩn VAS)
    SUM(CASE WHEN indicator_code = 'B01-DN_310' THEN ending_balance ELSE 0 END) AS no_ngan_han,
    
    -- 3. Vốn lưu động ròng = Tài sản ngắn hạn - Nợ ngắn hạn
    SUM(CASE WHEN indicator_code = 'B01-DN_100' THEN ending_balance ELSE 0 END) - 
    SUM(CASE WHEN indicator_code = 'B01-DN_310' THEN ending_balance ELSE 0 END) AS von_luu_dong_rong

FROM silver.fact_balancesheet
-- Lọc trước các mã chỉ tiêu cần thiết để tối ưu hóa hiệu năng truy vấn (Performance)
WHERE indicator_code IN ('B01-DN_100', 'B01-DN_310')
GROUP BY 1
ORDER BY thang_bao_cao ASC;

/* RESULT LOG:
+---------------------------+-----------------+
|           month           |     vld_rong    |
+---------------------------+-----------------+
| 2026-08-01 00:00:00+00:00 | 248352741076.00 |
| 2026-07-01 00:00:00+00:00 | 248352741076.00 |
+---------------------------+-----------------+
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

