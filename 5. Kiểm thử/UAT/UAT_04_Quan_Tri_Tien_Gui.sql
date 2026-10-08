-- ==========================================
-- DASHBOARD: QUẢN TRỊ TIỀN GỬI VÀ THANH KHOẢN
-- ==========================================

-- VISUAL: Tiền và các khoản tương đương tiền
-- MEASURE: _TienGui&ThanhKhoan[Tien_TuongDuongTien]
SELECT ending_balance
FROM silver.fact_balancesheet
WHERE indicator_code = 'B01-DN_110'
  AND reporting_date = (SELECT MAX(reporting_date) FROM silver.fact_balancesheet);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE indicator_code = 'B01-DN_110'
-- AND reporting_date = (SELECT MAX(reporting_date) FROM silver.fact_balancesheet);
+----------------+
| ending_balance |
+----------------+
| 91976722608.00 |
+----------------+
*/

-- VISUAL: Tiền gửi
-- MEASURE: silver fact_termdeposit[remaining_value]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT SUM(original_amount) AS total_original_amount
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE deposit_date <= (SELECT dt FROM max_date)
-- AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);
+-----------------------+
| total_original_amount |
+-----------------------+
|     40514952541.00    |
+-----------------------+
*/

-- VISUAL: Số lượng hợp đồng tiền gửi
-- MEASURE: _TienGui&ThanhKhoan[So_HD_Theo_Ngan_Hang]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT COUNT(DISTINCT passbook_no) AS active_contracts
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE deposit_date <= (SELECT dt FROM max_date)
-- AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);
+------------------+
| active_contracts |
+------------------+
|        22        |
+------------------+
*/

-- VISUAL: Lãi suất bình quân
-- MEASURE: _TienGui&ThanhKhoan[Lai_Suat_BQ]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT SUM(original_amount * interest_rate) / NULLIF(SUM(original_amount), 0) AS lai_suat_binh_quan
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE deposit_date <= (SELECT dt FROM max_date)
-- AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL);
+----------------------+
|  lai_suat_binh_quan  |
+----------------------+
| 0.049896752996198945 |
+----------------------+
*/

-- VISUAL: Thu nhập lãi
-- MEASURE: _TienGui&ThanhKhoan[Tong_Dedit_Account_515]
SELECT SUM(debit_amount) AS thu_nhap_lai
FROM silver.fact_cashflow
WHERE reciprocal_account LIKE '515%';

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE reciprocal_account LIKE '515%';
+---------------+
|  thu_nhap_lai |
+---------------+
| 1482534625.00 |
+---------------+
*/

-- VISUAL: Cơ cấu theo Ngân hàng
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Bank]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT bank_code,
       SUM(original_amount) AS tri_gia_goc
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL)
GROUP BY bank_code;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE deposit_date <= (SELECT dt FROM max_date)
-- AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL)
+-----------+----------------+
| bank_code |  tri_gia_goc   |
+-----------+----------------+
|     MB    |  900000000.00  |
|     VP    | 3000000000.00  |
|    IVB    | 18734952541.00 |
|     LP    | 1020000000.00  |
|     HD    | 4860000000.00  |
|   WOORI   | 12000000000.00 |
+-----------+----------------+
*/

-- VISUAL: Cơ cấu theo Kỳ hạn
-- MEASURE: _TienGui&ThanhKhoan[Co_Cau_Ky_Han]
WITH max_date AS (SELECT MAX(reporting_date) AS dt FROM silver.fact_balancesheet)
SELECT term,
       SUM(original_amount) AS tri_gia_goc
FROM silver.fact_termdeposit
WHERE deposit_date <= (SELECT dt FROM max_date)
  AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL)
GROUP BY term;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE deposit_date <= (SELECT dt FROM max_date)
-- AND (settlement_date > (SELECT dt FROM max_date) OR settlement_date IS NULL)
+------+----------------+
| term |  tri_gia_goc   |
+------+----------------+
|  6   | 21524952541.00 |
|  12  | 14020000000.00 |
|  3   | 2400000000.00  |
|  2   | 2570000000.00  |
+------+----------------+
*/

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

/* RESULT LOG:
+-----------+---------------+------+-----------------+-----------------+--------------+---------------+-----------------+
| bank_code | interest_rate | term |   passbook_no   | original_amount | deposit_date | maturity_date | settlement_date |
+-----------+---------------+------+-----------------+-----------------+--------------+---------------+-----------------+
|     MB    |     0.042     |  6   |  0474678615661  |  2000000000.00  |  2025-04-11  |   2025-10-11  |    2025-10-24   |
|     MB    |     0.042     |  6   |  7422243213798  |  2000000000.00  |  2025-04-11  |   2025-10-11  |    2026-05-11   |
|     MB    |     0.042     |  6   |  1052830331705  |  2200000000.00  |  2025-04-11  |   2025-10-11  |    2025-08-27   |
|     MB    |     0.032     |  6   |  5862620046203  |   715000000.00  |  2025-10-23  |   2025-11-24  |    2026-01-30   |
|     MB    |     0.043     |  6   |   102589613685  |   900000000.00  |  2026-05-08  |   2026-06-08  |       None      |
|     HD    |     0.054     |  12  | 009704060001482 |   500000000.00  |  2024-10-06  |   2025-10-06  |       None      |
|     HD    |     0.054     |  12  | 009704060001488 |   500000000.00  |  2024-11-01  |   2025-11-01  |       None      |
|     HD    |     0.0495    |  6   | 009704060001816 |  1000000000.00  |  2025-05-25  |   2025-11-25  |       None      |
|     HD    |     0.0495    |  6   | 009704060001817 |  1000000000.00  |  2025-05-25  |   2025-11-25  |       None      |
|     HD    |     0.0495    |  6   | 009704060001817 |  1860000000.00  |  2025-12-26  |   2026-06-26  |       None      |
|     LP    |     0.0451    |  12  |   012351227692  |   790000000.00  |  2025-05-05  |   2026-05-05  |    2025-06-04   |
|     LP    |     0.046     |  12  |   089205852087  |  1565000000.00  |  2025-03-17  |   2026-03-17  |    2025-11-19   |
|     LP    |     0.046     |  12  |   120260200541  |   400000000.00  |  2025-02-21  |   2026-02-21  |    2025-07-08   |
|     LP    |     0.046     |  12  |   143219109517  |  1300000000.00  |  2024-12-31  |   2025-12-31  |    2025-09-15   |
|     LP    |     0.046     |  12  |   164540793364  |   220000000.00  |  2024-12-25  |   2025-12-25  |    2025-11-26   |
|     LP    |     0.0451    |  12  |   183488873136  |   370000000.00  |  2025-04-28  |   2026-04-28  |    2025-06-06   |
|     LP    |     0.046     |  12  |   190688286953  |   160000000.00  |  2025-02-20  |   2026-02-20  |    2025-07-08   |
|     LP    |     0.046     |  12  |   196250888606  |   500000000.00  |  2025-01-09  |   2026-01-09  |    2025-07-26   |
|     LP    |     0.0451    |  12  |   197860500320  |   65000000.00   |  2025-03-27  |   2026-03-27  |    2025-06-16   |
|     LP    |     0.046     |  12  |   200897216948  |   370000000.00  |  2024-12-11  |   2025-12-11  |    2025-10-25   |
|     LP    |     0.046     |  12  |   211515988689  |  1500000000.00  |  2024-12-26  |   2025-12-26  |    2025-08-29   |
|     LP    |     0.046     |  12  |   246026319133  |   580000000.00  |  2025-02-19  |   2026-02-19  |    2025-08-12   |
|     LP    |     0.046     |  12  |   304332271613  |   800000000.00  |  2025-01-16  |   2026-01-16  |    2025-08-22   |
|     LP    |     0.046     |  12  |   329106587771  |   665000000.00  |  2025-02-10  |   2026-02-10  |    2025-08-27   |
|     LP    |     0.0451    |  12  |   360987342258  |   885000000.00  |  2025-04-21  |   2026-04-21  |    2025-06-04   |
|     LP    |     0.046     |  12  |   374711074295  |   400000000.00  |  2025-01-21  |   2026-01-21  |    2025-07-26   |
|     LP    |     0.0451    |  12  |   395841696909  |   810000000.00  |  2025-05-08  |   2026-05-08  |    2025-06-16   |
|     LP    |     0.0451    |  12  |   432419773489  |  1020000000.00  |  2025-03-28  |   2026-03-28  |       None      |
|     LP    |     0.046     |  12  |   467856080378  |   580000000.00  |  2024-12-13  |   2025-12-13  |    2025-11-26   |
|     LP    |     0.046     |  12  |   488330267943  |   330000000.00  |  2025-01-20  |   2026-01-20  |    2025-07-31   |
|     LP    |     0.0451    |  12  |   493456093767  |   735000000.00  |  2025-05-06  |   2026-05-06  |    2025-07-02   |
|     LP    |     0.0451    |  12  |   498125795689  |   291000000.00  |  2025-04-09  |   2026-04-09  |    2025-06-06   |
|     LP    |     0.046     |  12  |   502439377626  |   200000000.00  |  2025-01-13  |   2026-01-13  |    2025-07-26   |
|     LP    |     0.046     |  12  |   522088789000  |   650000000.00  |  2024-12-02  |   2025-12-02  |    2025-08-13   |
|     LP    |     0.046     |  12  |   560527792529  |   195000000.00  |  2025-02-27  |   2026-02-27  |    2025-07-08   |
|     LP    |     0.0451    |  12  |   602801378487  |   400000000.00  |  2025-04-10  |   2026-04-10  |    2025-06-16   |
|     LP    |     0.0451    |  12  |   672654771011  |   800000000.00  |  2025-04-10  |   2026-04-10  |    2025-07-22   |
|     LP    |     0.046     |  12  |   708229889671  |   385000000.00  |  2025-03-04  |   2026-03-04  |    2025-07-18   |
|     LP    |     0.046     |  12  |   712290368158  |   760000000.00  |  2025-01-06  |   2026-01-06  |    2025-11-18   |
|     LP    |     0.0451    |  12  |   717827641808  |   985000000.00  |  2025-03-24  |   2026-03-24  |    2025-11-26   |
|     LP    |     0.046     |  12  |   718136302215  |   525000000.00  |  2024-12-23  |   2025-12-23  |    2025-09-18   |
|     LP    |     0.0451    |  12  |   730687340645  |   115000000.00  |  2025-03-27  |   2026-03-27  |    2025-07-18   |
|     LP    |     0.046     |  12  |   742664148922  |   175000000.00  |  2024-12-09  |   2025-12-09  |    2025-08-27   |
|     LP    |     0.046     |  12  |   768764109513  |  1030000000.00  |  2024-12-04  |   2025-12-04  |    2025-08-13   |
|     LP    |     0.046     |  12  |   788744013918  |   855000000.00  |  2025-01-22  |   2026-01-22  |    2025-07-31   |
|     LP    |     0.046     |  12  |   795650972500  |   415000000.00  |  2025-02-17  |   2026-02-17  |    2025-08-08   |
|     LP    |     0.046     |  12  |   818633296522  |   650000000.00  |  2025-02-27  |   2026-02-27  |    2025-07-14   |
|     LP    |     0.046     |  12  |   830658847108  |   230000000.00  |  2025-02-25  |   2026-02-25  |    2025-07-22   |
|     LP    |     0.046     |  12  |   833797161922  |   210000000.00  |  2024-12-19  |   2025-12-19  |    2025-09-18   |
|     LP    |     0.046     |  12  |   846500064249  |   615000000.00  |  2025-03-18  |   2026-03-18  |    2025-07-08   |
|     LP    |     0.046     |  12  |   979029000988  |  1140000000.00  |  2025-01-14  |   2026-01-14  |    2025-09-04   |
|     LP    |     0.046     |  12  |   980766419052  |   940000000.00  |  2024-12-17  |   2025-12-17  |    2025-11-18   |
|    AGR    |     0.068     |  12  |  2407636000139  |  1300000000.00  |  2019-09-10  |   2025-09-10  |    2026-03-30   |
|    IVB    |     0.051     |  6   |   2035186-006   |  1098258274.00  |  2025-09-27  |   2026-03-27  |       None      |
|    IVB    |     0.051     |  6   |   2035186-007   |  1098258274.00  |  2025-09-27  |   2026-03-27  |       None      |
|    IVB    |     0.051     |  6   |   2035186-008   |  1098258274.00  |  2025-09-28  |   2026-03-28  |       None      |
|    IVB    |     0.051     |  6   |   2035186-010   |  1098258274.00  |  2025-09-28  |   2026-03-28  |       None      |
|    IVB    |     0.051     |  6   |   2035186-011   |  1098258274.00  |  2025-09-28  |   2026-03-28  |       None      |
|    IVB    |     0.051     |  6   |   2035186-012   |  1098258274.00  |  2025-09-28  |   2026-03-28  |       None      |
|    IVB    |     0.051     |  6   |   2035186-013   |  1647387412.00  |  2025-09-29  |   2026-03-29  |       None      |
|    IVB    |     0.051     |  6   |   2035186-014   |  1098015485.00  |  2025-10-02  |   2026-04-02  |       None      |
|    IVB    |     0.051     |  6   |   2035186-016   |  2000000000.00  |  2025-04-03  |   2026-10-03  |       None      |
|    IVB    |     0.051     |  6   |   2035186-019   |  2500000000.00  |  2025-04-03  |   2026-10-03  |       None      |
|    IVB    |     0.051     |  6   |   2035186-020   |  1500000000.00  |  2025-04-04  |   2026-10-04  |       None      |
|    IVB    |     0.051     |  6   |   2035186-021   |  1000000000.00  |  2025-04-04  |   2026-10-04  |       None      |
|    IVB    |     0.051     |  3   |   2035186-022   |  2400000000.00  |  2026-01-20  |   2026-04-20  |       None      |
|   WOORI   |      0.05     |  12  |     HĐTG 01     |  4000000000.00  |  2025-04-10  |   2026-04-10  |       None      |
|   WOORI   |      0.05     |  12  |     HĐTG 02     |  4000000000.00  |  2025-04-10  |   2026-04-10  |       None      |
|   WOORI   |      0.05     |  12  |     HĐTG 03     |  4000000000.00  |  2025-04-10  |   2026-04-10  |       None      |
|     VP    |      0.06     |  6   |     HĐTG 01     |   430000000.00  |  2025-12-04  |   2026-06-04  |       None      |
|     VP    |     0.043     |  2   |     HĐTG 02     |  1530000000.00  |  2025-12-05  |   2026-02-05  |       None      |
|     VP    |     0.043     |  2   |     HĐTG 03     |  1040000000.00  |  2025-12-08  |   2026-02-08  |       None      |
+-----------+---------------+------+-----------------+-----------------+--------------+---------------+-----------------+
*/

