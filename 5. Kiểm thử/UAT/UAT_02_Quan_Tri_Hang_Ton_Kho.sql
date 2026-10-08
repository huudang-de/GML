-- ==========================================
-- DASHBOARD: QUẢN TRỊ HÀNG TỒN KHO
-- ==========================================

-- VISUAL: Số lượng HTK
-- MEASURE: _TonKho[So_Luong_Ton]
SELECT SUM(ending_quantity) AS sl_ton_kho
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance);
+------------+
| sl_ton_kho |
+------------+
| 673125.42  |
+------------+
*/

-- VISUAL: Giá trị HTK
-- MEASURE: _TonKho[Gia_Tri_Ton]
SELECT SUM(ending_value) AS gt_ton_kho
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance);

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance);
+-----------------+
|    gt_ton_kho   |
+-----------------+
| 341692285766.00 |
+-----------------+
*/

-- VISUAL: Vòng quay HTK
-- MEASURE: _TonKho[Vong_Quay_HTK]
SELECT
  (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_11') / 
  NULLIF((SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)), 0) AS vong_quay_htk;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_11') /
-- NULLIF((SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)), 0) AS vong_quay_htk;
+---------------+
| vong_quay_htk |
+---------------+
|     0E-28     |
+---------------+
*/

-- VISUAL: Inventory to sales ratio
-- MEASURE: _TonKho[Inventory_To_Sales]
SELECT
  (SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)) / 
  NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_10'), 0) AS i_s_ratio;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- (SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)) /
-- NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = 'B02-DN_10'), 0) AS i_s_ratio;
+--------------------+
|     i_s_ratio      |
+--------------------+
| 4.5564288294601285 |
+--------------------+
*/

-- VISUAL: Tổng mã sản phẩm
-- MEASURE: _TonKho[Tong_SKU]
SELECT COUNT(DISTINCT product_code) AS tong_sku
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
  AND ending_quantity > 0;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
-- AND ending_quantity > 0;
+----------+
| tong_sku |
+----------+
|   1246   |
+----------+
*/

-- VISUAL: Giá trị hàng nhập khẩu
-- MEASURE: _TonKho[Gia_Tri_Nhap]
SELECT SUM(inward_value) AS gia_tri_nhap_khau
FROM silver.fact_inventoryinward
WHERE exchange_rate > 1;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE exchange_rate > 1;
+-------------------+
| gia_tri_nhap_khau |
+-------------------+
|  163157504466.00  |
+-------------------+
*/

-- VISUAL: Tồn kho theo thời gian
-- MEASURE: _TonKho[Ton_Kho_Theo_Thang]
SELECT DATE_TRUNC('month', snapshot_date) AS MONTH,
       SUM(ending_quantity) AS so_luong,
       SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
GROUP BY 1
ORDER BY 1;

/* RESULT LOG:
+---------------------------+-----------+-----------------+
|           month           |  so_luong |     gia_tri     |
+---------------------------+-----------+-----------------+
| 2026-07-01 00:00:00+00:00 | 673125.42 | 341692285766.00 |
| 2026-08-01 00:00:00+00:00 | 673125.42 | 341692285766.00 |
+---------------------------+-----------+-----------------+
*/

-- VISUAL: Vòng quay HTK theo thời gian
-- MEASURE: _TonKho[Vong_Quay_Thang]
WITH ton_kho AS (
    SELECT DATE_TRUNC('month', snapshot_date) AS MONTH, SUM(ending_value) AS gia_tri_ton
    FROM silver.fact_inventory_balance GROUP BY 1
),
gia_von AS (
    SELECT DATE_TRUNC('month', reporting_date) AS MONTH, SUM(current_period_amount) AS cogs
    FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_11' GROUP BY 1
)
SELECT t.MONTH,
       g.cogs / NULLIF(t.gia_tri_ton, 0) AS he_so_vong_quay
FROM ton_kho t
LEFT JOIN gia_von g ON t.MONTH = g.MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_11' GROUP BY 1
ERROR: column "reporting_date" does not exist
LINE 6:     SELECT DATE_TRUNC('month', reporting_date) AS MONTH, SUM...
                                       ^

*/

-- VISUAL: Inventory to Sales
-- MEASURE: _TonKho[IS_Theo_Thang]
WITH ton_kho AS (
    SELECT DATE_TRUNC('month', snapshot_date) AS MONTH, SUM(ending_value) AS gia_tri_ton
    FROM silver.fact_inventory_balance GROUP BY 1
),
doanh_thu AS (
    SELECT DATE_TRUNC('month', reporting_date) AS MONTH, SUM(current_period_amount) AS dthu
    FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' GROUP BY 1
)
SELECT t.MONTH,
       t.gia_tri_ton / NULLIF(d.dthu, 0) AS ty_le_is
FROM ton_kho t
LEFT JOIN doanh_thu d ON t.MONTH = d.MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' GROUP BY 1
ERROR: column "reporting_date" does not exist
LINE 6:     SELECT DATE_TRUNC('month', reporting_date) AS MONTH, SUM...
                                       ^

*/

-- VISUAL: Trạng thái Inventory
-- MEASURE: _TonKho[Trang_Thai]
WITH ton_cuoi AS (
    SELECT DATE_TRUNC('month', snapshot_date) AS month, SUM(ending_value) AS ton_cuoi_ky
    FROM silver.fact_inventory_balance GROUP BY 1
),
nhap AS (
    SELECT DATE_TRUNC('month', posting_date) AS month, SUM(inward_value) AS tong_nhap
    FROM silver.fact_inventoryinward GROUP BY 1
),
xuat AS (
    SELECT DATE_TRUNC('month', posting_date) AS month, SUM(outward_value) AS tong_xuat
    FROM silver.fact_inventoryoutward GROUP BY 1
)
SELECT COALESCE(t.month, n.month, x.month) AS MONTH,
       COALESCE(n.tong_nhap, 0) AS tong_nhap,
       COALESCE(x.tong_xuat, 0) AS tong_xuat,
       COALESCE(t.ton_cuoi_ky, 0) AS ton_cuoi_ky
FROM ton_cuoi t
FULL OUTER JOIN nhap n ON t.month = n.month
FULL OUTER JOIN xuat x ON COALESCE(t.month, n.month) = x.month
ORDER BY 1;

/* RESULT LOG:
+---------------------------+----------------+---------------+-----------------+
|           month           |   tong_nhap    |   tong_xuat   |   ton_cuoi_ky   |
+---------------------------+----------------+---------------+-----------------+
| 2026-01-01 00:00:00+00:00 | 66113395190.00 | 52585271668.0 |        0        |
| 2026-02-01 00:00:00+00:00 | 45788484765.00 | 20922802826.0 |        0        |
| 2026-03-01 00:00:00+00:00 | 60498138162.00 | 53646924511.0 |        0        |
| 2026-04-01 00:00:00+00:00 | 58057886647.00 | 76769615088.0 |        0        |
| 2026-05-01 00:00:00+00:00 | 75817986741.00 | 74599184818.0 |        0        |
| 2026-06-01 00:00:00+00:00 | 41975148988.00 | 81312507829.0 |        0        |
| 2026-07-01 00:00:00+00:00 | 53795968849.00 | 76844566080.0 | 341692285766.00 |
| 2026-08-01 00:00:00+00:00 |       0        |      0.0      | 341692285766.00 |
+---------------------------+----------------+---------------+-----------------+
*/

-- VISUAL: Top 10 dư tồn kho
-- MEASURE: _TonKho[Top_10_Ton]
SELECT product_code,
       SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
GROUP BY 1
ORDER BY gia_tri DESC
LIMIT 10;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
+------------------------------+-----------------+
|         product_code         |     gia_tri     |
+------------------------------+-----------------+
|          Thành phẩm          | 193186257228.00 |
|       Nguyên vật liệu        |  19500264169.00 |
|     Đèn áp trần Trim NK      |  11257055684.00 |
|          M017DAA2T           |  8371610947.00  |
|          M017VCM2T           |  6593836290.00  |
|           Hàng hóa           |  4150666040.00  |
|          M017DOH2T           |  3605848700.00  |
|          D017PBA0T           |  3116851719.00  |
| Đèn chùm NK 16 bóng mã: L036 |  2901897986.00  |
|          M475MLA4T           |  2843479000.00  |
+------------------------------+-----------------+
*/

-- VISUAL: Xuất kho Kế hoạch vs Thực tế
-- MEASURE: _TonKho[Xuat_Kho_ThucTe_KH]
WITH thuc_te AS (
    SELECT DATE_TRUNC('month', posting_date) AS MONTH, SUM(outward_value) AS thuc_te
    FROM silver.fact_inventoryoutward GROUP BY 1
),
ke_hoach AS (
    SELECT DATE_TRUNC('month', reporting_date) AS MONTH, SUM(target_amount) AS ke_hoach
    FROM silver.fact_businessplan WHERE indicator_code = 'B02-DN_01' GROUP BY 1
)
SELECT COALESCE(t.MONTH, k.MONTH) AS MONTH,
       COALESCE(t.thuc_te, 0) AS thuc_te,
       COALESCE(k.ke_hoach, 0) AS ke_hoach,
       ABS(COALESCE(t.thuc_te, 0) - COALESCE(k.ke_hoach, 0)) / NULLIF(COALESCE(k.ke_hoach, 0), 0) AS phan_tram_chenh_lech
FROM thuc_te t
FULL OUTER JOIN ke_hoach k ON t.MONTH = k.MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_businessplan WHERE indicator_code = 'B02-DN_01' GROUP BY 1
ERROR: column "reporting_date" does not exist
LINE 6:     SELECT DATE_TRUNC('month', reporting_date) AS MONTH, SUM...
                                       ^

*/

