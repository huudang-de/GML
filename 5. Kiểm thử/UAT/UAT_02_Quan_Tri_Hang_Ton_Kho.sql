-- ==========================================
-- DASHBOARD: QUẢN TRỊ HÀNG TỒN KHO
-- ==========================================

-- VISUAL: Số lượng HTK
-- MEASURE: _TonKho[So_Luong_Ton]
SELECT SUM(ending_quantity) AS sl_ton_kho
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance);

-- VISUAL: Giá trị HTK
-- MEASURE: _TonKho[Gia_Tri_Ton]
SELECT SUM(ending_value) AS gt_ton_kho
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance);

-- VISUAL: Vòng quay HTK
-- MEASURE: _TonKho[Vong_Quay_HTK]
SELECT
  (SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = ''B02-DN_11'') / 
  NULLIF((SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)), 0) AS vong_quay_htk;

-- VISUAL: Inventory to sales ratio
-- MEASURE: _TonKho[Inventory_To_Sales]
SELECT
  (SELECT SUM(ending_value) FROM silver.fact_inventory_balance WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)) / 
  NULLIF((SELECT SUM(current_period_amount) FROM silver.fact_incomestatement WHERE indicator_code = ''B02-DN_10''), 0) AS i_s_ratio;

-- VISUAL: Tổng mã sản phẩm
-- MEASURE: _TonKho[Tong_SKU]
SELECT COUNT(DISTINCT product_code) AS tong_sku
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
  AND ending_quantity > 0;

-- VISUAL: Giá trị hàng nhập khẩu
-- MEASURE: _TonKho[Gia_Tri_Nhap]
SELECT SUM(inward_value) AS gia_tri_nhap_khau
FROM silver.fact_inventoryinward
WHERE exchange_rate > 1;

-- VISUAL: Tồn kho theo thời gian
-- MEASURE: _TonKho[Ton_Kho_Theo_Thang]
SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH,
       SUM(ending_quantity) AS so_luong,
       SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
GROUP BY 1
ORDER BY 1;

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

-- VISUAL: Trạng thái Inventory
-- MEASURE: _TonKho[Trang_Thai]
SELECT DATE_TRUNC(''month'', snapshot_date) AS MONTH,
       SUM(inward_value) AS tong_nhap,
       SUM(outward_value) AS tong_xuat,
       SUM(ending_value) AS ton_cuoi_ky
FROM silver.fact_inventory_balance
GROUP BY 1
ORDER BY 1;

-- VISUAL: Top 10 dư tồn kho
-- MEASURE: _TonKho[Top_10_Ton]
SELECT product_code,
       SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
GROUP BY 1
ORDER BY gia_tri DESC
LIMIT 10;

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
