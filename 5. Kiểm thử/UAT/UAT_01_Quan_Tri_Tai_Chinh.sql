--- VISUAL: Dư nợ ngắn hạn
WITH latest_balances AS (
    SELECT 
        account_no, 
        credit_balance,
        -- Sử dụng hàm cửa sổ ROW_NUMBER() phân vùng theo từng mã tài khoản (account_no).
        -- Sắp xếp giảm dần theo ngày hạch toán (posting_date) và mã định danh bút toán (id)
        -- để đưa dòng giao dịch mới nhất/cuối cùng lên vị trí số 1.
        ROW_NUMBER() OVER(
            PARTITION BY account_no 
            ORDER BY posting_date DESC, id DESC
        ) as rn
    FROM silver.fact_cashflow
    -- Lọc các tiểu khoản thuộc nhóm Vay và nợ thuê tài chính ngắn hạn (theo thông tư kế toán: 34111, 34113, 34114)
    WHERE account_no LIKE '34111%' 
       OR account_no LIKE '34113%' 
       OR account_no LIKE '34114%'
)
SELECT 
    SUM(credit_balance) AS du_no_ngan_han
FROM latest_balances
-- Chỉ lấy dòng giao dịch mới nhất (rn = 1) của mỗi tiểu khoản vay để tránh bị cộng dồn số dư lịch sử trùng lặp
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

--- VISUAL: Dư nợ dài hạn
WITH latest_balances AS (
    SELECT 
        account_no, 
        credit_balance,
        -- Sử dụng hàm cửa sổ ROW_NUMBER() để phân vùng theo từng mã tài khoản (account_no).
        -- Sắp xếp giảm dần theo ngày hạch toán (posting_date) và mã định danh bút toán (id)
        -- nhằm đưa giao dịch hoặc số dư chốt sổ mới nhất lên vị trí số 1 (rn = 1).
        ROW_NUMBER() OVER(
            PARTITION BY account_no 
            ORDER BY posting_date DESC, id DESC
        ) as rn
    FROM silver.fact_cashflow
    -- Lọc các tiểu khoản thuộc nhóm Vay và nợ thuê tài chính dài hạn (theo quy ước bắt đầu bằng 34112)
    WHERE account_no LIKE '34112%'
)
SELECT 
    SUM(credit_balance) AS du_no_dai_han
FROM latest_balances
-- Chỉ lấy dòng số dư mới nhất (rn = 1) của mỗi tài khoản để tránh bị cộng dồn số dư lịch sử trùng lặp
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

--- VISUAL: Hạn mức được phê duyệt
SELECT SUM(credit_limit)
FROM silver.fact_creditlimitsummary;

/* RESULT LOG:
+-----------------+
|       sum       |
+-----------------+
| 485000000000.00 |
+-----------------+
*/

--- VISUAL: Hạn mức được cấp
SELECT SUM(granted_limit)
FROM silver.fact_creditlimitsummary;

/* RESULT LOG:
+-----------------+
|       sum       |
+-----------------+
| 295000000000.00 |
+-----------------+
*/

--- VISUAL: Hạn mức còn lại
SELECT SUM(granted_limit) - SUM(principal_balance)
FROM silver.fact_creditlimitsummary;

/* RESULT LOG:
+----------------+
|    ?column?    |
+----------------+
| 24135521634.00 |
+----------------+
*/

--- VISUAL: Loan to Value (LTV)
  -- Tính tổng hạn mức tín dụng thực tế được cấp từ bảng tổng hợp hạn mức
  (SELECT SUM(granted_limit)
   FROM silver.fact_creditlimitsummary) / NULLIF(
                                                 -- Tính tổng giá trị định giá tài sản bảo đảm từ bảng tài sản bảo đảm
                                                 (SELECT SUM(appraised_value)
                                                  FROM silver.fact_collateral), 0) AS ltv_ratio;

/* RESULT LOG:
+------------------------+
|       ltv_ratio        |
+------------------------+
| 0.71290863549346840628 |
+------------------------+
*/

--- VISUAL: DEBT/EQUITY
-- Bước 1: Khởi tạo CTE (Common Table Expression) để xác định mốc ngày báo cáo (reporting_date) mới nhất có trên hệ thống
WITH bs AS (
    SELECT reporting_date
    FROM silver.fact_balancesheet
    ORDER BY reporting_date DESC
    LIMIT 1
)
SELECT
    -- Bước 2: Tính tổng Nợ phải trả (Mã chỉ tiêu B01-DN_300 trên Bảng cân đối kế toán) tại mốc kỳ báo cáo mới nhất
    (
        SELECT SUM(ending_balance)
        FROM silver.fact_balancesheet
        WHERE indicator_code = 'B01-DN_300'
          AND reporting_date = (SELECT reporting_date FROM bs)
    ) 
    / 
    -- Bước 3: Chia cho Tổng Vốn chủ sở hữu (Mã chỉ tiêu B01-DN_440) tại cùng mốc kỳ báo cáo đó
    -- Sử dụng NULLIF để chống lỗi chia cho 0 trong trường hợp vốn chủ sở hữu bằng 0 hoặc âm
    NULLIF(
        (
            SELECT SUM(ending_balance)
            FROM silver.fact_balancesheet
            WHERE indicator_code = 'B01-DN_440'
              AND reporting_date = (SELECT reporting_date FROM bs)
        ), 0
    ) AS debt_equity_ratio;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B01-DN_300'
-- AND reporting_date =
-- WHERE indicator_code = 'B01-DN_440'
-- AND reporting_date =
+------------------------+
| debt_equity_ratio      |
+------------------------+
| 0.63580376382791085809 |
+------------------------+
*/

--- VISUAL: Nợ ngắn/dài hạn/tổng nợ theo tháng

-- Bước 1: Tạo danh sách các mốc thời gian theo tháng (dựa trên các tháng có phát sinh giao dịch trong bảng dòng tiền)
WITH months AS (
    SELECT DISTINCT DATE_TRUNC('month', posting_date) AS month
    FROM silver.fact_cashflow
),
-- Bước 2: Chốt số dư mới nhất của từng tài khoản vay tại thời điểm cuối mỗi tháng
monthly_balances AS (
    SELECT m.month,
           c.account_no,
           c.credit_balance,
           -- Sử dụng hàm ROW_NUMBER() phân vùng theo từng tháng và từng tiểu khoản tài khoản.
           -- Sắp xếp giảm dần theo ngày hạch toán và ID bút toán để lấy giao dịch chốt sổ cuối tháng làm dòng số 1 (rn = 1).
           ROW_NUMBER() OVER (
               PARTITION BY m.month, c.account_no
               ORDER BY c.posting_date DESC, c.id DESC) AS rn
    FROM months m
    JOIN silver.fact_cashflow c
      -- Lấy toàn bộ các giao dịch phát sinh từ đầu cho đến hết ngày cuối của tháng đó
      ON c.posting_date < m.month + INTERVAL '1 month'
    -- Lọc các tiểu khoản liên quan đến vay và nợ thuê tài chính (tổng hợp ngắn hạn, dài hạn, thuê tài chính và tài khoản tổng)
    WHERE c.account_no IN ('34111','34112','34113','34114','3412','341')
)
-- Bước 3: Tổng hợp và phân loại các khoản nợ theo từng tháng báo cáo
SELECT month,
       -- Tính tổng Nợ ngắn hạn (gộp các tiểu khoản 34111, 34113, 34114)
       SUM(CASE WHEN account_no IN ('34111','34113','34114') THEN credit_balance ELSE 0 END) AS no_ngan_han,
       -- Tính Nợ dài hạn (tiểu khoản 34112)
       SUM(CASE WHEN account_no = '34112' THEN credit_balance ELSE 0 END)                     AS no_dai_han,
       -- Tổng dư nợ theo chuẩn BRD = Nợ ngắn hạn + Nợ dài hạn
       SUM(CASE WHEN account_no IN ('34111','34112','34113','34114') THEN credit_balance ELSE 0 END) AS tong_du_no,
       -- Cột đối chiếu kỹ thuật (Nợ thuê tài chính - không dùng làm KPI chính)
       SUM(CASE WHEN account_no = '3412' THEN credit_balance ELSE 0 END) AS no_thue_tai_chinh,
       -- Cột đối chiếu kỹ thuật (Số dư tài khoản tổng 341)
       SUM(CASE WHEN account_no = '341'  THEN credit_balance ELSE 0 END) AS so_du_tk_341
FROM monthly_balances
-- Chỉ lấy dòng số dư chốt sổ cuối mỗi tháng (rn = 1) đã được xác định ở bước 2
WHERE rn = 1
GROUP BY month
ORDER BY month;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE c.account_no IN ('34111', '34112', '34113', '34114', '341')
-- WHERE rn = 1
-- month           | no_ngan_han      | no_dai_han       | tong_du_no            | no_thue_tai_chinh| so_du_tk_341   
-- 2026-01-01 00:00:00.000 +0700	288810348805.00	21559222373.00	310369571178.00	4333508271.00	314703079449.00
-- 2026-02-01 00:00:00.000 +0700	288888286161.00	34006975424.00	322895261585.00	4197802514.00	327093064099.00
-- 2026-03-01 00:00:00.000 +0700	284783474573.00	52263780975.00	337047255548.00	4062096757.00	341109352305.00
-- 2026-04-01 00:00:00.000 +0700	288730438136.00	52263780975.00	340994219111.00	3926391000.00	344920610111.00
-- 2026-05-01 00:00:00.000 +0700	291258424472.00	52263780975.00	343522205447.00	3898800326.00	347421005773.00
-- 2026-06-01 00:00:00.000 +0700	294141676298.00	52253093475.00	346394769773.00	3742642737.00	350137412510.00
-- 2026-07-01 00:00:00.000 +0700	236065233815.00	51174925843.00	287240159658.00	3742642737.00	290982802395.00
-- 2026-08-01 00:00:00.000 +0700	236065233815.00	51174925843.00	287240159658.00	3742642737.00	290982802395.00
*/

--- VISUAL: Chi phí lãi vay thực tế vs KH
-- Bước 1: Tổng hợp chi phí lãi vay thực tế theo từng tháng từ bảng Báo cáo kết quả kinh doanh
WITH actual AS (
    SELECT DATE_TRUNC('month', month) AS MONTH,
           SUM(current_period_amount) AS chi_phi_thuc_te
    FROM silver.fact_incomestatement
    -- Mã chỉ tiêu 'B02-DN_23' đại diện cho chi phí lãi vay (hoặc chi phí tài chính trong hệ thống kế toán)
    WHERE indicator_code = 'B02-DN_23'
    GROUP BY 1
),
-- Bước 2: Tổng hợp chi phí lãi vay theo kế hoạch định mức từng tháng từ bảng Kế hoạch kinh doanh
PLAN AS (
    SELECT DATE_TRUNC('month', month) AS MONTH,
           SUM(target_amount) AS ke_hoach
    FROM silver.fact_businessplan
    -- Sử dụng chung mã chỉ tiêu 'B02-DN_23' để đối chiếu tương ứng với bên thực tế
    WHERE indicator_code = 'B02-DN_23'
    GROUP BY 1
)
-- Bước 3: Kết hợp dữ liệu thực tế và kế hoạch theo từng mốc thời gian tháng
SELECT COALESCE(a.month, p.month) AS MONTH,
       -- Lấy chi phí thực tế, nếu không có dữ liệu phát sinh thì mặc định bằng 0
       COALESCE(a.chi_phi_thuc_te, 0) AS chi_phi_thuc_te,
       -- Lấy kế hoạch định mức, nếu không có thì mặc định bằng 0
       COALESCE(p.ke_hoach, 0) AS ke_hoach
FROM actual a
-- Sử dụng FULL OUTER JOIN để đảm bảo không bị sót tháng nào (dù tháng đó chỉ có kế hoạch mà chưa phát sinh thực tế, hoặc ngược lại)
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

--- VISUAL: Lãi suất bình quân bank
SELECT 
    bank_code,
    -- Tính giá trị lãi suất trung bình (AVG) của các khoản vay
    AVG(interest_rate) AS lai_suat_binh_quan
FROM silver.fact_creditlimitsummary
-- Lọc chỉ xét riêng các khoản hạn mức thuộc nhóm Ngắn hạn
WHERE limit_type = 'Ngắn hạn'
-- Nhóm kết quả theo từng mã ngân hàng để so sánh mức lãi suất giữa các tổ chức tín dụng
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

--- VISUAL: Interest YTD
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

--- VISUAL: Cost of Debt (Tổng chi phí lãi vay trên Tổng dư nợ)

-- Bước 1: Tổng hợp tổng chi phí lãi vay thực tế phát sinh theo từng tháng từ bảng Kết quả kinh doanh
WITH actual_interest AS (
    SELECT DATE_TRUNC('month', month) AS thang, 
           SUM(current_period_amount) AS tong_chi_phi_lai_vay 
    FROM silver.fact_incomestatement 
    -- Mã chỉ tiêu 'B02-DN_23' đại diện cho chi phí lãi vay / chi phí tài chính trong hệ thống kế toán
    WHERE indicator_code = 'B02-DN_23' 
    GROUP BY 1
),
-- Bước 2: Tạo danh sách các mốc thời gian theo tháng từ bảng dòng tiền
months AS (
    SELECT DISTINCT DATE_TRUNC('month', posting_date) AS month
    FROM silver.fact_cashflow
),
-- Bước 3: Chốt số dư mới nhất của tài khoản tổng hợp khoản vay (tài khoản 341) tại thời điểm cuối mỗi tháng
monthly_balances AS (
    SELECT m.month,
           c.account_no,
           c.credit_balance,
           -- Sử dụng hàm ROW_NUMBER() để phân vùng theo tháng và tài khoản, sắp xếp giảm dần theo ngày và ID để lấy dòng cuối tháng (rn = 1)
           ROW_NUMBER() OVER(PARTITION BY m.month, c.account_no ORDER BY c.posting_date DESC, c.id DESC) as rn
    FROM months m
    JOIN silver.fact_cashflow c ON c.posting_date < m.month + INTERVAL '1 month'
    -- Lọc tài khoản '341' đại diện cho tổng dư nợ gốc vay và nợ thuê tài chính của doanh nghiệp
    WHERE c.account_no = '341'
),
-- Bước 4: Tính tổng dư nợ vay cuối mỗi tháng bằng cách cộng dồn các số dư tài khoản 341 đã chốt ở bước 3
cumulative_debt AS (
    SELECT month, SUM(credit_balance) AS tong_du_no
    FROM monthly_balances
    WHERE rn = 1
    GROUP BY month
)
-- Bước 5: Kết hợp chi phí lãi vay và tổng dư nợ theo từng tháng để tính tỷ lệ Cost of Debt
SELECT i.thang AS month, 
       i.tong_chi_phi_lai_vay, 
       d.tong_du_no,
       -- Tính Cost of Debt = Tổng chi phí lãi vay / Tổng dư nợ vay
       -- Sử dụng hàm NULLIF ở mẫu số để tránh lỗi chia cho số 0
       i.tong_chi_phi_lai_vay / NULLIF(d.tong_du_no, 0) AS cost_of_debt
FROM actual_interest i
-- Sử dụng LEFT JOIN để gắn tổng dư nợ tương ứng với các tháng có phát sinh chi phí lãi vay
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

--- VISUAL: Cơ cấu dòng thu theo Bank

SELECT 
    -- Lấy tên ngân hàng/tài khoản từ bảng danh mục định danh tài khoản
    a.account_name AS bank_name,
    -- Tính tổng giá trị tiền thu vào (phát sinh bên Nợ của tài khoản tiền)
    SUM(c.debit_amount) AS tong_thu
FROM silver.fact_cashflow c
-- Kết nối với bảng danh mục tài khoản (Dim_Account) để ánh xạ mã tài khoản thành tên ngân hàng tương ứng
LEFT JOIN silver.dim_account a ON c.account_no = a.account_no
-- Lọc chỉ xét các tài khoản tiền mặt (111%) hoặc tiền gửi ngân hàng (112%)
WHERE (c.account_no LIKE '111%' OR c.account_no LIKE '112%')
  -- Loại bỏ các bút toán chuyển tiền nội bộ (thường bắt đầu bằng mã CTNB) để tránh tính trùng dòng tiền
  AND c.voucher_no NOT LIKE 'CTNB%'
  -- Loại bỏ các bút toán nộp tiền/chuyển tiền nội bộ tương ứng khác (mã NTTK)
  AND c.voucher_no NOT LIKE 'NTTK%'
  -- Loại bỏ các giao dịch đối ứng nội bộ giữa các tài khoản tiền với nhau (ví dụ rút tiền mặt gửi vào TK ngân hàng)
  AND c.reciprocal_account NOT LIKE '111%' 
  AND c.reciprocal_account NOT LIKE '112%'
-- Nhóm kết quả theo tên ngân hàng để ra cơ cấu dòng thu
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

--- VISUAL: Cơ cấu dòng chi theo Bank

SELECT 
    -- Lấy tên ngân hàng hoặc quỹ tiền mặt tương ứng từ bảng danh mục tài khoản định danh
    a.account_name AS bank_name,
    -- Tính tổng giá trị tiền chi ra (phát sinh bên Có của tài khoản tiền mặt hoặc tiền gửi ngân hàng)
    SUM(c.credit_amount) AS tong_chi
FROM silver.fact_cashflow c
-- Kết nối (LEFT JOIN) với bảng danh mục tài khoản (Dim_Account) để ánh xạ mã tài khoản thành tên ngân hàng hiển thị trên báo cáo
LEFT JOIN silver.dim_account a ON c.account_no = a.account_no
-- Lọc chỉ xét các tài khoản thuộc nhóm Quỹ tiền mặt (111%) hoặc Tiền gửi ngân hàng (112%)
WHERE (c.account_no LIKE '111%' OR c.account_no LIKE '112%')
  -- Loại bỏ các bút toán luân chuyển tiền nội bộ giữa các tài khoản của công ty (mã CTNB) để không làm phồng dòng chi
  AND c.voucher_no NOT LIKE 'CTNB%'
  -- Loại bỏ các bút toán nộp/chuyển tiền nội bộ tương ứng khác (mã NTTK)
  AND c.voucher_no NOT LIKE 'NTTK%'
  -- Loại bỏ các giao dịch có tài khoản đối ứng cũng nằm trong hệ thống tài khoản tiền (ví dụ: rút tiền gửi nhập quỹ tiền mặt)
  AND c.reciprocal_account NOT LIKE '111%' 
  AND c.reciprocal_account NOT LIKE '112%'
-- Nhóm kết quả theo tên ngân hàng để tổng hợp cơ cấu dòng chi thực tế ra bên ngoài
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

--- VISUAL: Bảng tổng hợp toàn diện các chỉ số tài chính (Financial Ratios Dashboard)

WITH md AS (
    -- Bước 1: Khởi tạo mốc ngày chốt số liệu báo cáo (Ví dụ: 31/07/2026)
    SELECT CAST('2026-07-31' AS date) AS dt
),
prev_md AS (
    -- Bước 2: Xác định mốc ngày cùng kỳ năm trước (lùi lại đúng 1 năm) dùng cho các chỉ số bình quân
    SELECT (SELECT dt FROM md) - interval '1 year' AS dt_prev
),
b01_curr AS (
    -- Bước 3: Lấy toàn bộ số dư cuối kỳ của các chỉ tiêu trên Bảng Cân Đối Kế Toán tại mốc báo cáo hiện tại
    SELECT indicator_code, SUM(ending_balance) as val 
    FROM silver.fact_balancesheet 
    WHERE reporting_date = (SELECT dt FROM md) 
    GROUP BY indicator_code
),
b01_prev AS (
    -- Bước 4: Lấy số dư cuối kỳ của các chỉ tiêu Bảng Cân Đối Kế Toán tại mốc cùng kỳ năm trước (dùng tính mẫu số bình quân)
    SELECT indicator_code, SUM(ending_balance) as val 
    FROM silver.fact_balancesheet 
    WHERE reporting_date = (SELECT dt_prev FROM prev_md) 
    GROUP BY indicator_code
),
b02_curr AS (
    -- Bước 5: Lấy số phát sinh trong kỳ của các chỉ tiêu trên Báo Cáo Kết Quả Hoạt Động Kinh Doanh tại tháng báo cáo
    SELECT indicator_code, SUM(current_period_amount) as val 
    FROM silver.fact_incomestatement 
    WHERE month = (SELECT dt FROM md) 
    GROUP BY indicator_code
),
du_no AS (
    -- Bước 6: Tính tổng dư nợ gốc vay lũy kế từ tiểu khoản 341 cho đến hết mốc tháng báo cáo
    SELECT SUM(credit_amount - debit_amount) as total_debt 
    FROM silver.fact_cashflow 
    WHERE account_no LIKE '341%' AND DATE_TRUNC('month', posting_date) <= DATE_TRUNC('month', (SELECT dt FROM md))
),
vars AS (
    -- Bước 7: Gom nhóm và ánh xạ mã chỉ tiêu (MISA / BCTC) thành các biến số tài chính chuẩn hóa
    SELECT 
        -- Nhóm tài sản & nguồn vốn hiện tại
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_100'), 0) AS ts_ngan_han,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_310'), 0) AS no_ngan_han,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_140'), 0) AS ton_kho,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_130'), 0) AS phai_thu,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_400'), 0) AS vcsh,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_300'), 0) AS no_phai_tra,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_330'), 0) AS no_dai_han,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_440'), 0) AS tong_ts,
        COALESCE((SELECT SUM(val) FROM b01_curr WHERE indicator_code='B01-DN_223' OR indicator_code='B01-DN_228'), 0) AS khau_hao,
        
        -- Nhóm số liệu cùng kỳ năm trước (dùng tính bình quân)
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_100'), 0) AS ts_ngan_han_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_310'), 0) AS no_ngan_han_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_140'), 0) AS ton_kho_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_130'), 0) AS phai_thu_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_400'), 0) AS vcsh_prev,
        COALESCE((SELECT SUM(val) FROM b01_prev WHERE indicator_code='B01-DN_440'), 0) AS tong_ts_prev,
        
        -- Nhóm kết quả kinh doanh trong tháng
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_10'), 0) AS dthu_thuan,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_11'), 0) AS gia_von,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_20'), 0) AS ln_gop,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_23'), 0) AS cp_lai_vay,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_30'), 0) AS ln_hdkd,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_51'), 0) + COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_52'), 0) AS cp_thue,
        COALESCE((SELECT SUM(val) FROM b02_curr WHERE indicator_code='B02-DN_60'), 0) AS ln_st,
        COALESCE((SELECT total_debt FROM du_no), 0) AS tong_du_no
)
-- Bước 8: Tính toán chi tiết 17 chỉ số tài chính trọng yếu từ các biến đã gom ở trên
SELECT 
    -- 1. Khả năng thanh toán ngắn hạn (Current Ratio): Tài sản ngắn hạn / Nợ ngắn hạn
    ts_ngan_han / NULLIF(no_ngan_han, 0) AS current_ratio,
    
    -- 2. Khả năng thanh toán nhanh (Quick Ratio): (Tài sản ngắn hạn - Hàng tồn kho) / Nợ ngắn hạn
    (ts_ngan_han - ton_kho) / NULLIF(no_ngan_han, 0) AS quick_ratio,
    
    -- 3. Vòng quay vốn lưu động thuần: Doanh thu thuần / Vốn lưu động thuần bình quân
    dthu_thuan / NULLIF(((ts_ngan_han - no_ngan_han) + (ts_ngan_han_prev - no_ngan_han_prev)) / 2.0, 0) AS vong_quay_vld,
    
    -- 4. Vòng quay hàng tồn kho: Giá vốn hàng bán / Hàng tồn kho bình quân
    gia_von / NULLIF((ton_kho + ton_kho_prev) / 2.0, 0) AS vong_quay_ton_kho,
    
    -- 5. Vòng quay khoản phải thu: Doanh thu thuần / Phải thu khách hàng bình quân
    dthu_thuan / NULLIF((phai_thu + phai_thu_prev) / 2.0, 0) AS vong_quay_phai_thu,
    
    -- 6. Hệ số nợ phải trả trên tổng tài sản: Tổng nợ phải trả / Tổng tài sản
    no_phai_tra / NULLIF(tong_ts, 0) AS no_phai_tra_tren_tong_ts,
    
    -- 7. Hệ số nợ dài hạn trên vốn chủ sở hữu: Nợ dài hạn / Vốn chủ sở hữu
    no_dai_han / NULLIF(vcsh, 0) AS no_dai_han_tren_vcsh,
    
    -- 8. Lợi nhuận trước lãi vay và thuế (EBIT): Lợi nhuận sau thuế + Thuế + Lãi vay
    (ln_st + cp_thue + cp_lai_vay) AS ebit,
    
    -- 9. Lợi nhuận trước lãi vay, thuế và khấu hao (EBITDA): EBIT + Khấu hao tài sản
    (ln_st + cp_thue + cp_lai_vay + ABS(khau_hao)) AS ebitda,
    
    -- 10. Khả năng thanh toán lãi vay dựa trên EBIT: EBIT / Chi phí lãi vay
    (ln_st + cp_thue + cp_lai_vay) / NULLIF(cp_lai_vay, 0) AS ebit_tren_lai_vay,
    
    -- 11. Khả năng thanh toán lãi vay dựa trên EBITDA: EBITDA / Chi phí lãi vay
    (ln_st + cp_thue + cp_lai_vay + ABS(khau_hao)) / NULLIF(cp_lai_vay, 0) AS ebitda_tren_lai_vay,
    
    -- 12. Biên lợi nhuận gộp: Lợi nhuận gộp / Doanh thu thuần
    ln_gop / NULLIF(dthu_thuan, 0) AS bien_ln_gop,
    
    -- 13. Biên lợi nhuận từ hoạt động kinh doanh: Lợi nhuận thuần từ HĐKD / Doanh thu thuần
    ln_hdkd / NULLIF(dthu_thuan, 0) AS bien_ln_hdkd,
    
    -- 14. Biên EBITDA: EBITDA / Doanh thu thuần
    (ln_st + cp_thue + cp_lai_vay + ABS(khau_hao)) / NULLIF(dthu_thuan, 0) AS bien_ebitda,
    
    -- 15. Tỷ suất sinh lời trên vốn chủ sở hữu (ROE): Lợi nhuận sau thuế / Vốn chủ sở hữu bình quân
    ln_st / NULLIF((vcsh + vcsh_prev) / 2.0, 0) AS roe,
    
    -- 16. Tỷ suất sinh lời trên tổng tài sản (ROA): Lợi nhuận sau thuế / Tổng tài sản bình quân
    ln_st / NULLIF((tong_ts + tong_ts_prev) / 2.0, 0) AS roa,
    
    -- 17. Hệ số tổng dư nợ trên EBITDA: Tổng dư nợ vay / EBITDA
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
SELECT 
    -- Lấy thông tin phân loại loại tài sản đảm bảo (ví dụ: bất động sản, máy móc thiết bị, hàng tồn kho...)
    collateral_type AS ten_tai_san,
    
    -- Lấy giá trị định giá độc lập của tài sản do tổ chức thẩm định giá xác định
    appraised_value AS gia_tri_tham_dinh,
    
    -- Lấy hệ số tài sản đảm bảo (tỷ lệ phần trăm tối đa ngân hàng cho phép cho vay dựa trên giá trị định giá)
    collateral_coefficient AS he_so_tsdb,
    
    -- Tính toán giá trị cho vay tối đa thực tế bằng cách nhân giá trị định giá với hệ số đảm bảo (ép kiểu sang numeric để đảm bảo chính xác toán học)
    appraised_value * CAST(collateral_coefficient AS numeric) AS gia_tri_cho_vay
FROM silver.fact_collateral;

/* RESULT LOG:
+-------------+-------------------+--------------------+-------------------------------+
| ten_tai_san | gia_tri_tham_dinh |     he_so_tsdb     |        gia_tri_cho_vay        |
BĐS	7854464000.00	0.9	7069017600.000
BĐS	6347108454.00	0.65	4125620495.1000
BĐS	5349600000.00	0.9	4814640000.000
BĐS	2378899937.00	0.75	1784174952.7500
HĐTG	2000000000.00	1	2000000000.00
MMTB	2087071580.00	0.5	1043535790.000
MMTB	5364349760.00	0.5	2682174880.000
MMTB	10875812640.00	0.5	5437906320.000
MMTB	6915895800.00	0.5	3457947900.000
MMTB	21379150800.00	0.5	10689575400.000
MMTB	21365127000.00	0.5	10682563500.000
PTVT	1978000000.00	0.65	1285700000.0000
PTVT	401800000.00	0.65	261170000.0000
PTVT	500000000.00	0.65	325000000.0000
HTK	53500000000.00	0.7	37450000000.000
TC	10000000000.00	1	10000000000.00
BĐS	7650000000.00	0.9	6885000000.000
BĐS	3885000000.00	0.8993055555555556	3493802083.333333506000000000
BĐS	6675000000.00	0.8995956873315364	6004801212.938005470000000000
HTK	13403973200.00	0.698	9355973293.60000
HĐTG	16334952541.00	1	16334952541.00
HTK	80000000000.00	0.3	24000000000.000
BĐS	18286000000.00	0.7	12800200000.000
BĐS	18670000000.00	0.7	13069000000.000
HĐTG	1300000000.00	0.95	1235000000.0000
BĐS	2958000000.00	0.85	2514300000.0000
HĐTG	4860000000.00	0.97	4714200000.0000
TC	10000000000.00	1	10000000000.00
HĐTG	3000000000.00	1	3000000000.00
HTK	25589559265.00	0.5	12794779632.500
BĐS	7223000000.00	0.75	5417250000.0000
BĐS	11665000000.00	0.8	9332000000.000
HĐTG	12000000000.00	1	12000000000.00
TC	12000000000.00	1	12000000000.00
...(TRUNCATED FOR READABILITY)...
*/

-- VISUAL: Lịch trả gốc ngân hàng
SELECT 
    -- Lấy mã ngân hàng đối tác tài trợ vốn vay
    bank_code,
    
    -- Lấy ngày đến hạn thanh toán gốc của khế ước
    maturity_date AS ngay_can_tra_goc,
    
    -- Tính tổng số tiền gốc còn phải trả (dư nợ gốc còn lại) tại mốc ngày đáo hạn đó
    SUM(remaining_principal) AS so_tien_can_tra
FROM silver.fact_loan
-- Chỉ lọc lấy các khế ước vay còn dư nợ gốc thực tế lớn hơn 0 (chưa tất toán)
WHERE remaining_principal > 0
-- Nhóm kết quả tường minh theo mã ngân hàng và ngày đáo hạn để tránh lỗi cú pháp
GROUP BY 
    bank_code, 
    maturity_date
-- Sắp xếp thứ tự thời gian đáo hạn tăng dần (từ các khoản đến hạn sớm nhất lên trên đầu)
ORDER BY 
    maturity_date ASC;

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

