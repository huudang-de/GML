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
  (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = ''B02-DN_11'') / 
  NULLIF((SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)), 0) AS vong_quay_htk;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = ''B02-DN_11'') /
-- NULLIF((SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)), 0) AS vong_quay_htk;
ERROR: syntax error at or near "B02"
LINE 2: ...ver.fact_incomestatement WHERE indicator_code = ''B02-DN_11'...
                                                             ^

*/


-- VISUAL: Inventory to sales ratio
-- MEASURE: _TonKho[Inventory_To_Sales]
SELECT
  (SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)) / 
  NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = ''B02-DN_10''), 0) AS i_s_ratio;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- (SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)) /
-- NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = ''B02-DN_10''), 0) AS i_s_ratio;
ERROR: syntax error at or near "B02"
LINE 3: ...ver.fact_incomestatement WHERE indicator_code = ''B02-DN_10'...
                                                             ^

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
SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH,
       SUM(ending_quantity) AS so_luong,
       SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
GROUP BY 1
ORDER BY 1;
/* RESULT LOG:
ERROR: syntax error at or near "month"
LINE 1: SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH,
                            ^

*/


-- VISUAL: Vòng quay HTK theo thời gian
-- MEASURE: _TonKho[Vong_Quay_Thang]
WITH ton_kho AS (
    SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH, SUM(ending_value) AS gia_tri_ton
    FROM silver.fact_inventory_balance GROUP BY 1
),
gia_von AS (
    SELECT DATE_TRUNC(''month'', reporting_date) AS MONTH, SUM(current_period_amount) AS cogs
    FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_11'' GROUP BY 1
)
SELECT t.MONTH,
       g.cogs / NULLIF(t.gia_tri_ton, 0) AS he_so_vong_quay
FROM ton_kho t
LEFT JOIN gia_von g ON t.MONTH = g.MONTH;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_11'' GROUP BY 1
ERROR: syntax error at or near "month"
LINE 2:     SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH, SU...
                                ^

*/


-- VISUAL: Inventory to Sales
-- MEASURE: _TonKho[IS_Theo_Thang]
WITH ton_kho AS (
    SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH, SUM(ending_value) AS gia_tri_ton
    FROM silver.fact_inventory_balance GROUP BY 1
),
doanh_thu AS (
    SELECT DATE_TRUNC(''month'', reporting_date) AS MONTH, SUM(current_period_amount) AS dthu
    FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_10'' GROUP BY 1
)
SELECT t.MONTH,
       t.gia_tri_ton / NULLIF(d.dthu, 0) AS ty_le_is
FROM ton_kho t
LEFT JOIN doanh_thu d ON t.MONTH = d.MONTH;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_incomestatement WHERE indicator_code=''B02-DN_10'' GROUP BY 1
ERROR: syntax error at or near "month"
LINE 2:     SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH, SU...
                                ^

*/


-- VISUAL: Trạng thái Inventory
-- MEASURE: _TonKho[Trang_Thai]
SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH,
       SUM(inward_value) AS tong_nhap,
       SUM(outward_value) AS tong_xuat,
       SUM(ending_value) AS ton_cuoi_ky
FROM silver.fact_inventory_balance
GROUP BY 1
ORDER BY 1;
/* RESULT LOG:
ERROR: syntax error at or near "month"
LINE 1: SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH,
                            ^

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
    SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH, SUM(outward_value) AS thuc_te
    FROM silver.fact_inventory_balance GROUP BY 1
),
ke_hoach AS (
    SELECT DATE_TRUNC(''month'', reporting_date) AS MONTH, SUM(target_amount) AS ke_hoach
    FROM silver.fact_businessplan WHERE indicator_code = ''B02-DN_01'' GROUP BY 1
)
SELECT COALESCE(t.MONTH, k.MONTH) AS MONTH,
       COALESCE(t.thuc_te, 0) AS thuc_te,
       COALESCE(k.ke_hoach, 0) AS ke_hoach,
       ABS(COALESCE(t.thuc_te, 0) - COALESCE(k.ke_hoach, 0)) / NULLIF(COALESCE(k.ke_hoach, 0), 0) AS phan_tram_chenh_lech
FROM thuc_te t
FULL OUTER JOIN ke_hoach k ON t.MONTH = k.MONTH;
/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_businessplan WHERE indicator_code = ''B02-DN_01'' GROUP BY 1
ERROR: syntax error at or near "month"
LINE 2:     SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH, SU...
                                ^

*/

