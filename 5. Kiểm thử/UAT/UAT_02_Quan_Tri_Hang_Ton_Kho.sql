-- ==========================================
-- DASHBOARD: QUẢN TRỊ HÀNG TỒN KHO
-- ==========================================

--- VISUAL: Số lượng HTK
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

--- VISUAL: Giá trị HTK
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

--- VISUAL: Vòng quay HTK
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

--- VISUAL: Inventory to sales ratio
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

--- VISUAL: Tổng mã sản phẩm
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

--- VISUAL: Giá trị hàng nhập khẩu
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

-- VISUAL: Số lượng và Giá trị Tồn kho theo thời gian
SELECT 
    -- Gom nhóm thời gian theo từng tháng dựa trên ngày chốt số dư tồn kho (snapshot_date)
    DATE_TRUNC('month', snapshot_date) AS MONTH,
    
    -- Tính tổng số lượng vật tư, hàng hóa tồn kho thực tế tại thời điểm cuối mỗi tháng
    SUM(ending_quantity) AS so_luong,
    
    -- Tính tổng giá trị tiền tồn kho (giá trị sổ sách) tại thời điểm cuối mỗi tháng
    SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
-- Nhóm kết quả theo cột thời gian tháng (cột thứ 1 trong SELECT)
GROUP BY 1
-- Sắp xếp thứ tự thời gian tăng dần để trực quan hóa biểu đồ xu hướng theo các tháng
ORDER BY 1;

/* RESULT LOG:
+---------------------------+-----------+-----------------+
|           month           |  so_luong |     gia_tri     |
+---------------------------+-----------+-----------------+
| 2026-07-01 00:00:00+00:00 | 673125.42 | 341692285766.00 |
| 2026-08-01 00:00:00+00:00 | 673125.42 | 341692285766.00 |
+---------------------------+-----------+-----------------+
*/

--- VISUAL: Vòng quay HTK theo thời gian
WITH ton_kho AS (
    -- Bước 1: Tổng hợp giá trị tồn kho bình quân hoặc cuối kỳ theo từng tháng từ bảng số dư tồn kho
    SELECT DATE_TRUNC('month', snapshot_date) AS MONTH, 
           SUM(ending_value) AS gia_tri_ton
    FROM silver.fact_inventory_balance 
    GROUP BY 1
),
gia_von AS (
    -- Bước 2: Lấy tổng chi phí giá vốn hàng bán (COGS) phát sinh trong từng tháng từ Báo cáo kết quả kinh doanh
    SELECT DATE_TRUNC('month', month) AS MONTH, 
           SUM(current_period_amount) AS cogs
    FROM silver.fact_incomestatement 
    -- Mã chỉ tiêu 'B02-DN_11' đại diện cho Giá vốn hàng bán trong hệ thống kế toán doanh nghiệp
    WHERE indicator_code = 'B02-DN_11' 
    GROUP BY 1
)
-- Bước 3: Kết hợp dữ liệu tồn kho và giá vốn theo tháng để tính hệ số vòng quay
SELECT 
    t.MONTH,
    -- Tính hệ số vòng quay = Giá vốn hàng bán / Giá trị tồn kho
    -- Sử dụng NULLIF ở mẫu số để tránh lỗi chia cho số 0 nếu tháng nào không có giá trị tồn kho
    g.cogs / NULLIF(t.gia_tri_ton, 0) AS he_so_vong_quay
FROM ton_kho t
-- Dùng LEFT JOIN để giữ lại toàn bộ các mốc tháng có dữ liệu tồn kho
LEFT JOIN gia_von g ON t.MONTH = g.MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_11' GROUP BY 1
+---------------------------+-----------------+
|           month           | he_so_vong_quay |
+---------------------------+-----------------+
| 2026-07-01 00:00:00+00:00 |      0E-28      |
| 2026-08-01 00:00:00+00:00 |      0E-28      |
+---------------------------+-----------------+
*/

--- VISUAL: Tỷ lệ Tồn kho/Doanh thu (Inventory-to-Sales Ratio)

WITH ton_kho AS (
    -- Bước 1: Tổng hợp tổng giá trị tồn kho theo từng tháng từ bảng số dư tồn kho
    SELECT DATE_TRUNC('month', snapshot_date) AS MONTH, 
           SUM(ending_value) AS gia_tri_ton
    FROM silver.fact_inventory_balance 
    GROUP BY 1
),
doanh_thu AS (
    -- Bước 2: Lấy tổng doanh thu thuần phát sinh trong từng tháng từ Báo cáo kết quả kinh doanh
    SELECT DATE_TRUNC('month', month) AS MONTH, 
           SUM(current_period_amount) AS dthu
    FROM silver.fact_incomestatement 
    -- Mã chỉ tiêu 'B02-DN_10' đại diện cho Doanh thu thuần về bán hàng và cung cấp dịch vụ
    WHERE indicator_code = 'B02-DN_10' 
    GROUP BY 1
)
-- Bước 3: Kết hợp dữ liệu tồn kho và doanh thu theo tháng để tính tỷ lệ tương quan
SELECT 
    t.MONTH,
    -- Tính tỷ lệ Tồn kho trên Doanh thu = Giá trị tồn kho / Doanh thu thuần trong kỳ
    -- Sử dụng hàm NULLIF ở mẫu số để tránh lỗi chia cho số 0 nếu tháng không có doanh thu
    t.gia_tri_ton / NULLIF(d.dthu, 0) AS ty_le_is
FROM ton_kho t
-- Dùng LEFT JOIN để giữ lại toàn bộ các mốc tháng có dữ liệu tồn kho
LEFT JOIN doanh_thu d ON t.MONTH = d.MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_incomestatement WHERE indicator_code='B02-DN_10' GROUP BY 1
+---------------------------+--------------------+
|           month           |      ty_le_is      |
+---------------------------+--------------------+
| 2026-07-01 00:00:00+00:00 | 4.5564288294601285 |
| 2026-08-01 00:00:00+00:00 |        None        |
+---------------------------+--------------------+
*/

---VISUAL: Bảng tổng hợp Biến động Nhập - Xuất - Tồn kho theo thời gian (Inventory Flow Dashboard)

WITH ton_cuoi AS (
    -- Bước 1: Tổng hợp giá trị tồn kho cuối kỳ theo từng tháng từ bảng số dư tồn kho
    SELECT DATE_TRUNC('month', snapshot_date) AS month, 
           SUM(ending_value) AS ton_cuoi_ky
    FROM silver.fact_inventory_balance 
    GROUP BY 1
),
nhap AS (
    -- Bước 2: Tổng hợp giá trị hàng nhập kho phát sinh trong từng tháng từ bảng nhập kho
    SELECT DATE_TRUNC('month', posting_date) AS month, 
           SUM(inward_value) AS tong_nhap
    FROM silver.fact_inventoryinward 
    GROUP BY 1
),
xuat AS (
    -- Bước 3: Tổng hợp giá trị hàng xuất kho phát sinh trong từng tháng từ bảng xuất kho
    SELECT DATE_TRUNC('month', posting_date) AS month, 
           SUM(outward_value) AS tong_xuat
    FROM silver.fact_inventoryoutward 
    GROUP BY 1
)
-- Bước 4: Kết hợp toàn bộ dữ liệu Nhập, Xuất, Tồn của tất cả các tháng bằng FULL OUTER JOIN để tránh sót dữ liệu
SELECT 
    -- Lấy mốc tháng không bị thiếu hụt từ bất kỳ bảng nào (nếu bảng này có tháng mà bảng kia không có)
    COALESCE(t.month, n.month, x.month) AS MONTH,
    
    -- Lấy tổng giá trị nhập kho trong tháng, nếu không có dữ liệu thì quy đổi về 0
    COALESCE(n.tong_nhap, 0) AS tong_nhap,
    
    -- Lấy tổng giá trị xuất kho trong tháng, nếu không có dữ liệu thì quy đổi về 0
    COALESCE(x.tong_xuat, 0) AS tong_xuat,
    
    -- Lấy giá trị tồn cuối kỳ của tháng, nếu không có dữ liệu thì quy đổi về 0
    COALESCE(t.ton_cuoi_ky, 0) AS ton_cuoi_ky
FROM ton_cuoi t
FULL OUTER JOIN nhap n ON t.month = n.month
FULL OUTER JOIN xuat x ON COALESCE(t.month, n.month) = x.month
-- Sắp xếp thứ tự thời gian tăng dần từ quá khứ đến hiện tại để dựng biểu đồ dạng cột kết hợp đường (Column & Line Chart)
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

---VISUAL: Top 10 dư tồn kho (Theo Giá trị)
SELECT 
    -- Lấy mã sản phẩm / mặt hàng trong kho
    product_code,
    
    -- Tính tổng giá trị tồn kho (giá trị sổ sách) của từng mặt hàng
    SUM(ending_value) AS gia_tri
FROM silver.fact_inventory_balance
-- Chỉ lọc lấy dữ liệu tại mốc ngày chốt sổ mới nhất có trong hệ thống (dùng Subquery tìm MAX date)
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
-- Nhóm kết quả theo mã sản phẩm
GROUP BY 1
-- Sắp xếp tổng giá trị tồn kho theo thứ tự giảm dần (từ cao xuống thấp)
ORDER BY gia_tri DESC
-- Giới hạn chỉ lấy ra đúng 10 mặt hàng đứng đầu danh sách
LIMIT 10;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
+--------------------------------+-------------------+
|         product_code           |      gia_tri      |
+--------------------------------+-------------------+
| Thành phẩm                     |   193186257228.00 |
| Nguyên vật liệu                |    19500264169.00 |
| Đèn áp trần Trim NK            |    11257055684.00 |
| M017DAA2T                      |     8371610947.00 |
| M017VCM2T                      |     6593836290.00 |
| Hàng hóa                       |     4150666040.00 |
| M017DOH2T                      |     3605848700.00 |
| D017PBA0T                      |     3116851719.00 |
| Đèn chùm NK 16 bóng mã: L036   |     2901897986.00 |
| M475MLA4T                      |     2843479000.00 |
+--------------------------------+-------------------+
*/

--- VISUAL: Top 10 dư tồn kho (Theo Số lượng)
SELECT 
    -- Lấy mã sản phẩm / mặt hàng trong kho
    product_code,
    
    -- Tính tổng số lượng tồn kho thực tế (theo đơn vị tính vật lý: mét khối, tấm, kg, chiếc...)
    SUM(ending_quantity) AS so_luong
FROM silver.fact_inventory_balance
-- Chỉ lấy dữ liệu tại mốc ngày chốt số liệu gần nhất hiện có trong cơ sở dữ liệu
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
-- Nhóm kết quả theo mã sản phẩm
GROUP BY 1
-- Sắp xếp theo số lượng tồn kho giảm dần (từ mặt hàng nhiều nhất xuống thấp)
ORDER BY so_luong DESC
-- Giới hạn chỉ lấy 10 mặt hàng đứng đầu
LIMIT 10;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
+--------------------------------+-------------------+
|         product_code           |     so_luong      |
+--------------------------------+-------------------+
| GP4123T                        |         119495.72 |
| N1610CLNO01T                   |         109500.00 |
| M475MLA4T                      |          40049.00 |
| M017DAA2T                      |          27904.00 |
| D017PBA0T                      |          18200.00 |
| M017VCM2T                      |          15451.00 |
| M550DAH2T                      |          15101.00 |
| GM107XT                        |          12674.00 |
| N1021VG2                       |          10642.00 |
| GX096-1951                     |          10621.00 |
+--------------------------------+-------------------+
*/

--- VISUAL: Bảng Red Flag những mặt hàng bị chậm luân chuyển
WITH danh_sach_red_flag AS (
    -- Bước 1: Khởi tạo CTE (Common Table Expression) gom danh sách chi tiết các mặt hàng Red Flag
    SELECT 
        b.warehouse_code,
        b.product_code,
        b.ending_quantity AS so_luong_htk,
        i.ngay_nhap_gan_nhat,
        b.snapshot_date AS ngay_bao_cao,
        -- Tính số ngày tồn kho bằng cách lấy ngày chốt báo cáo trừ đi ngày nhập kho gần nhất
        (b.snapshot_date - i.ngay_nhap_gan_nhat) AS so_ngay_ton_kho
    FROM silver.fact_inventory_balance b
    -- Kết hợp với Subquery tìm mốc ngày nhập kho gần nhất (MAX posting_date) của từng mã sản phẩm trong từng kho
    LEFT JOIN (
        SELECT 
            warehouse_code,
            product_code,
            MAX(posting_date) AS ngay_nhap_gan_nhat
        FROM silver.fact_inventoryinward
        GROUP BY warehouse_code, product_code
    ) i ON b.warehouse_code = i.warehouse_code AND b.product_code = i.product_code
    -- Lọc dữ liệu đúng tại mốc ngày chốt số liệu mới nhất trong hệ thống
    WHERE b.snapshot_date = (SELECT MAX(snapshot_date) FROM silver.fact_inventory_balance)
)

-- Bước 2: Truy vấn phần 1 - Lấy toàn bộ danh sách chi tiết các dòng Red Flag bình thường
SELECT 
    warehouse_code,
    product_code,
    so_luong_htk,
    ngay_nhap_gan_nhat,
    ngay_bao_cao,
    so_ngay_ton_kho
FROM danh_sach_red_flag

UNION ALL

-- Bước 3: Truy vấn phần 2 - Tạo một dòng tổng cộng (Grand Total) ghép vào cuối bảng
SELECT 
    -- Gán nhãn nhận diện cho dòng tổng cộng
    '--- TỔNG CỘNG ---' AS warehouse_code,
    -- Các cột mã hoặc ngày không cộng dồn được thì để NULL
    NULL AS product_code,
    -- Dùng hàm SUM để tính tổng số lượng tồn kho (bao gồm cả âm và dương) của toàn bộ danh sách để đối chiếu với Card
    SUM(so_luong_htk) AS so_luong_htk,
    NULL AS ngay_nhap_gan_nhat,
    NULL AS ngay_bao_cao,
    NULL AS so_ngay_ton_kho
FROM danh_sach_red_flag

-- Sắp xếp toàn bộ kết quả giảm dần theo số ngày tồn kho, đồng thời đẩy dòng '--- TỔNG CỘNG ---' (có giá trị NULL) xuống dưới cùng
ORDER BY so_ngay_ton_kho DESC NULLS LAST;

--- VISUAL: Xuất kho Kế hoạch vs Thực tế
WITH thuc_te AS (
    -- Bước 1: Tổng hợp doanh thu thực tế phát sinh theo từng tháng từ bảng chi tiết bán hàng
    SELECT 
        DATE_TRUNC('month', posting_date) AS MONTH, 
        SUM(outward_value) AS thuc_te
    FROM silver.fact_inventoryoutward 
    GROUP BY 1
),
ke_hoach AS (
    -- Bước 2: Lấy dữ liệu doanh thu kế hoạch theo từng tháng từ bảng kế hoạch kinh doanh
    SELECT 
        DATE_TRUNC('month', month) AS MONTH, 
        SUM(target_amount) AS ke_hoach
    FROM silver.fact_businessplan 
    -- Mã chỉ tiêu 'B02-DN_10' đại diện cho chỉ tiêu Doanh thu thuần
    WHERE indicator_code = 'B02-DN_10' 
    GROUP BY 1
)
-- Bước 3: Kết hợp toàn bộ dữ liệu thực tế và kế hoạch bằng FULL OUTER JOIN để tránh sót tháng
SELECT 
    -- Lấy mốc tháng không bị thiếu hụt từ bất kỳ bảng nào
    COALESCE(t.MONTH, k.MONTH) AS MONTH,
    
    -- Lấy giá trị thực tế, nếu tháng nào chưa có dữ liệu thì quy về 0
    COALESCE(t.thuc_te, 0) AS thuc_te,
    
    -- Lấy giá trị kế hoạch, nếu tháng nào chưa có mục tiêu thì quy về 0
    COALESCE(k.ke_hoach, 0) AS ke_hoach,
    
    -- Bước 4: Tính tỷ lệ phần trăm chênh lệch giữa thực tế và kế hoạch
    -- Dùng hàm ABS để tính độ lệch tuyệt đối (không phân biệt vượt hay hụt)
    -- Dùng NULLIF ở mẫu số để tránh lỗi chia cho số 0 nếu tháng đó kế hoạch bằng 0
    ABS(COALESCE(t.thuc_te, 0) - COALESCE(k.ke_hoach, 0)) / NULLIF(COALESCE(k.ke_hoach, 0), 0) AS phan_tram_chenh_lech
FROM thuc_te t
FULL OUTER JOIN ke_hoach k ON t.MONTH = k.MONTH
-- Sắp xếp thứ tự thời gian tăng dần để phục vụ vẽ biểu đồ đường hoặc biểu đồ cột kết hợp (Combo Chart)
ORDER BY MONTH;

/* RESULT LOG:
-- GHI CHÚ FILTER:
-- FROM silver.fact_businessplan WHERE indicator_code = 'B02-DN_10' GROUP BY 1
+---------------------------+-----------------+-----------------+----------------------+
|           month           |     thuc_te     |    ke_hoach     | phan_tram_chenh_lech |
+---------------------------+-----------------+-----------------+----------------------+
| 2026-01-01 00:00:00+00:00 |  52585271668.00 | 105636013549.00 |                 0.50 |
| 2026-02-01 00:00:00+00:00 |  20922802826.00 |  52818006773.00 |                 0.60 |
| 2026-03-01 00:00:00+00:00 |  53646924511.00 |  52818006773.00 |                 0.02 |
| 2026-04-01 00:00:00+00:00 |  76769615088.00 | 105636013546.00 |                 0.27 |
| 2026-05-01 00:00:00+00:00 |  74599184818.00 |  52818006773.00 |                 0.41 |
| 2026-06-01 00:00:00+00:00 |  81312507829.00 |  52818006773.00 |                 0.54 |
| 2026-07-01 00:00:00+00:00 |  76844566080.00 |  52818006773.00 |                 0.45 |
| 2026-08-01 00:00:00+00:00 |            0.00 |  52818006773.00 |                 1.00 |
+---------------------------+-----------------+-----------------+----------------------+
*/

