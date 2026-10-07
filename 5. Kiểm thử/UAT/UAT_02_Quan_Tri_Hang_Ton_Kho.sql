-- TONG HOP SQL TEST SCRIPT (UAT)
-- DU AN GO MINH LONG

-- ==========================================
-- DASHBOARD: QUẢN TRỊ HÀNG TỒN KHO

-- ==========================================
-- VISUAL: Số lượng HTK
-- MEASURE: _TonKho[So_Luong_Ton]

SELECT SUM(ending_quantity) AS sl_ton_kho
FROM silver.fact_inventory_balance
WHERE snapshot_date =
    (SELECT MAX(reporting_date)
     FROM silver.fact_inventory_balance);

-- VISUAL: Giá trị HTK
-- MEASURE: _TonKho[Gia_Tri_Ton]
SELECT SUM(ending_value) AS gt_ton_kho
FROM silver.fact_inventory_balance
WHERE snapshot_date =
    (SELECT MAX(reporting_date)
     FROM silver.fact_inventory_balance);

-- VISUAL: Vòng quay HTK
-- MEASURE: _TonKho[Vong_Quay_HTK]
SELECT
  (SELECT SUM(current_period_amount)
   FROM silver.fact_incomestatement
   WHERE indicator_code = 'B02-DN_11') / NULLIF(
                                                  (SELECT SUM(ending_value)
                                                   FROM silver.fact_inventory_balance
                                                   WHERE snapshot_date =
                                                       (SELECT MAX(reporting_date)
                                                        FROM silver.fact_inventory_balance)), 0) AS vong_quay_htk;

-- VISUAL: Inventory to sales ratio
-- MEASURE: _TonKho[Inventory_To_Sales]
SELECT
  (SELECT SUM(ending_value)
   FROM silver.fact_inventory_balance
   WHERE snapshot_date =
       (SELECT MAX(reporting_date)
        FROM silver.fact_inventory_balance)) / NULLIF(
                                                        (SELECT SUM(current_period_amount)
                                                         FROM silver.fact_incomestatement
                                                         WHERE indicator_code = 'B02-DN_10'), 0) AS i_s_ratio;

-- VISUAL: Tổng mã sản phẩm
-- MEASURE: _TonKho[Tong_SKU]
SELECT COUNT(DISTINCT product_code) AS tong_sku
FROM silver.fact_inventory_balance
WHERE ending_quantity > 0;

-- VISUAL: Giá trị hàng nhập khẩu
-- MEASURE: _TonKho[Gia_Tri_Nhap]
SELECT SUM(inward_value) AS gia_tri_nhap_khau
FROM silver.fact_inventoryinward
WHERE exchange_rate > 1;

-- VISUAL: Tồn kho theo thời gian
-- MEASURE: _TonKho[Ton_Kho_Theo_Thang]
SELECT DATE_TRUNC('month', snapshot_date) AS MONTH,
       SUM(ending_quantity) AS so_luong,
       SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
GROUP BY 1
ORDER BY 1;

-- VISUAL: Vòng quay HTK theo thời gian
-- MEASURE: _TonKho[Vong_Quay_Thang]
SELECT DATE_TRUNC('month', b.reporting_date) AS MONTH,
       SUM(i.current_period_amount) / NULLIF(SUM(b.ending_value), 0) AS he_so_vong_quay
FROM silver.fact_inventory_balance b
LEFT JOIN silver.fact_incomestatement i ON DATE_TRUNC('month', b.reporting_date) = DATE_TRUNC('month', i.reporting_date)
AND i.indicator_code='B02-DN_11'
GROUP BY 1;

-- VISUAL: Inventory to Sales
-- MEASURE: _TonKho[IS_Theo_Thang]
SELECT DATE_TRUNC('month', b.reporting_date) AS MONTH,
       SUM(b.ending_value) / NULLIF(SUM(i.current_period_amount), 0) AS ty_le_is
FROM silver.fact_inventory_balance b
LEFT JOIN silver.fact_incomestatement i ON DATE_TRUNC('month', b.reporting_date) = DATE_TRUNC('month', i.reporting_date)
AND i.indicator_code='B02-DN_10'
GROUP BY 1;

-- VISUAL: Trạng thái Inventory
-- MEASURE: _TonKho[Trang_Thai]
SELECT DATE_TRUNC('month', posting_date) AS MONTH,
       SUM(inward_value) AS nhap_kho
FROM silver.fact_inventoryinward
GROUP BY 1;

-- VISUAL: Top 10 dư tồn kho
-- MEASURE: _TonKho[Top_10_Ton]
SELECT product_code,
       SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
WHERE snapshot_date =
    (SELECT MAX(reporting_date)
     FROM silver.fact_inventory_balance)
GROUP BY 1
ORDER BY gia_tri DESC
LIMIT 10;

-- VISUAL: Giá trị hàng xuất kho thực tế vs Kế hoạch
-- MEASURE: _TonKho[Xuat_Vs_KH]
SELECT DATE_TRUNC('month', o.posting_date) AS MONTH,
       SUM(o.outward_value) AS gia_tri_xuat_thuc_te,

  (SELECT SUM(target_amount)
   FROM silver.fact_businessplan
   WHERE indicator_code = 'B02-DN_11'
     AND MONTH = DATE_TRUNC('month', o.posting_date)) AS ke_hoach
FROM silver.fact_inventoryoutward o
GROUP BY 1;

