# Báo cáo Đánh giá Độ chính xác Text-to-SQL (EV-07)

- **Tập dữ liệu (Split):** `dev`
- **Thời gian chạy (UTC):** `2026-11-08T11:59:37Z`
- **Git Commit Hash:** `2bee2d0`
- **Configured Provider:** `auto`
- **Effective Provider:** `heuristic`
- **Hồ sơ dữ liệu:** `real` (PostgreSQL `data_warehouse`)

## 1. Tổng quan Chỉ số Đo lường Chính (Key Metrics)

| Chỉ số | Tên chỉ số | Kết quả | Đạt / Mục tiêu | Trạng thái |
| --- | --- | --- | --- | --- |
| **M-06** | Execution Accuracy (Độ chính xác thực thi) | **100.00%** (19/19) | ≥ 90.0% | ✅ ĐẠT |
| **M-07** | Valid SQL Rate (Tỷ lệ SQL hợp lệ) | **100.00%** (19/19) | ≥ 95.0% | ✅ ĐẠT |

## 2. Phân rã theo Độ khó (Difficulty Breakdown)

| Độ khó | Tổng số câu | Hợp lệ (M-07) | Chính xác (M-06) | Tỷ lệ chính xác |
| --- | --- | --- | --- | --- |
| `de` | 12 | 12 | 12 | 100.0% |
| `vua` | 6 | 6 | 6 | 100.0% |
| `kho` | 1 | 1 | 1 | 100.0% |

## 3. Phân rã theo Dashboard Nghiệp vụ

| Dashboard | Tổng số câu | Hợp lệ | Chính xác | Tỷ lệ chính xác |
| --- | --- | --- | --- | --- |
| `D1` | 8 | 8 | 8 | 100.0% |
| `D2` | 5 | 5 | 5 | 100.0% |
| `D3` | 3 | 3 | 3 | 100.0% |
| `D4` | 2 | 2 | 2 | 100.0% |
| `D5` | 1 | 1 | 1 | 100.0% |

## 4. Kiểm định Nhóm Giới hạn Dữ liệu C1 (Known Missing Data / no_data)

| ID | Câu hỏi | Kỳ vọng | Trạng thái thực tế | Kết quả đối soát |
| --- | --- | --- | --- | --- |
| `BM_OOS_DEV_01` | Biên lợi nhuận gộp tháng 7 năm 2026 của công ty đạt bao nhiêu phần trăm? | `no_data` | `no_data` | ✅ ĐÚNG (no_data) |
| `BM_OOS_DEV_02` | Giá vốn hàng bán phát sinh trong kỳ tháng 7 năm 2026 là bao nhiêu tiền? | `no_data` | `no_data` | ✅ ĐÚNG (no_data) |
| `BM_OOS_DEV_03` | Tăng trưởng doanh thu thuần so với cùng kỳ năm 2025 YoY là bao nhiêu? | `no_data` | `no_data` | ✅ ĐÚNG (no_data) |
| `BM_OOS_DEV_04` | Doanh thu thuần của tháng 3 năm 2026 là bao nhiêu tiền? | `no_data` | `no_data` | ✅ ĐÚNG (no_data) |

## 5. Danh sách Chi tiết Toàn bộ Câu Benchmark Đã Đánh giá

| ID | Độ khó | Dash | Câu hỏi | Kỳ vọng | Thực tế | Trạng thái | Conf | M-07 | M-06 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `BM_SQL_DEV_01` | `de` | `D1` | Tổng dư nợ ngắn hạn của công ty hiện tại là bao nhiêu? | 236065233815.00 | 236065233815.00 | `ok` | 0.93 | ✅ | ✅ |
| `BM_SQL_DEV_02` | `de` | `D1` | Tổng dư nợ dài hạn tại các ngân hàng là bao nhiêu? | 51174925843.00 | 51174925843.00 | `ok` | 0.92 | ✅ | ✅ |
| `BM_SQL_DEV_03` | `de` | `D1` | Hạn mức tín dụng được ngân hàng cấp cho công ty là bao nhiêu? | 295000000000.00 | 295000000000.00 | `ok` | 0.89 | ✅ | ✅ |
| `BM_SQL_DEV_04` | `vua` | `D1` | Tỷ lệ sử dụng hạn mức tín dụng hiện tại đạt bao nhiêu phần trăm? | 0.92 | 0.92 | `ok` | 0.95 | ✅ | ✅ |
| `BM_SQL_DEV_05` | `vua` | `D1` | Hệ số nợ trên vốn chủ sở hữu D/E của công ty là bao nhiêu? | 0.64 | 0.64 | `ok` | 0.90 | ✅ | ✅ |
| `BM_SQL_DEV_06` | `de` | `D2` | Tổng giá trị hàng tồn kho của toàn công ty là bao nhiêu? | 341692285766.00 | 341692285766.00 | `ok` | 0.91 | ✅ | ✅ |
| `BM_SQL_DEV_07` | `de` | `D2` | Tổng số lượng hàng tồn kho các loại hiện tại là bao nhiêu? | 673125.42 | 673125.42 | `ok` | 0.96 | ✅ | ✅ |
| `BM_SQL_DEV_08` | `vua` | `D2` | Tổng giá trị các lô hàng nhập khẩu là bao nhiêu tiền? | 163157504466.00 | 163157504466.00 | `ok` | 0.94 | ✅ | ✅ |
| `BM_SQL_DEV_09` | `de` | `D3` | Tổng số tiền phải thu khách hàng chốt sổ kỳ này là bao nhiêu? | 36326095573.00 | 36326095573.00 | `ok` | 0.90 | ✅ | ✅ |
| `BM_SQL_DEV_10` | `de` | `D3` | Tổng công nợ phải trả cho nhà cung cấp là bao nhiêu? | 60452900187.23 | 60452900187.23 | `ok` | 0.93 | ✅ | ✅ |
| `BM_SQL_DEV_11` | `vua` | `D3` | Vòng quay phải thu hiện tại trong tháng là bao nhiêu vòng? | 2.06 | 2.06 | `ok` | 0.95 | ✅ | ✅ |
| `BM_SQL_DEV_12` | `de` | `D4` | Số dư tiền và tương đương tiền cuối kỳ là bao nhiêu? | 91975348608.00 | 91975348608.00 | `ok` | 0.96 | ✅ | ✅ |
| `BM_SQL_DEV_13` | `de` | `D4` | Tổng tiền gửi có kỳ hạn đang gửi tại các ngân hàng là bao nhiêu? | 40514952541.00 | 40514952541.00 | `ok` | 0.89 | ✅ | ✅ |
| `BM_SQL_DEV_14` | `de` | `D5` | Tổng dòng tiền chi ra ngoài công ty từ đầu năm đến nay là bao nhiêu? | 2302632987134.00 | 2302632987134.00 | `ok` | 0.92 | ✅ | ✅ |
| `BM_SQL_DEV_15` | `kho` | `D1` | Hệ số khả năng thanh toán nhanh Quick Ratio của công ty là bao nhiêu? | 0.86 | 0.86 | `ok` | 0.98 | ✅ | ✅ |
| `BM_OOS_DEV_01` | `de` | `D2` | Biên lợi nhuận gộp tháng 7 năm 2026 của công ty đạt bao nhiêu phần trăm? | no_data | - | `no_data` | 0.00 | ✅ | ✅ |
| `BM_OOS_DEV_02` | `de` | `D2` | Giá vốn hàng bán phát sinh trong kỳ tháng 7 năm 2026 là bao nhiêu tiền? | no_data | - | `no_data` | 0.00 | ✅ | ✅ |
| `BM_OOS_DEV_03` | `vua` | `D1` | Tăng trưởng doanh thu thuần so với cùng kỳ năm 2025 YoY là bao nhiêu? | no_data | - | `no_data` | 0.00 | ✅ | ✅ |
| `BM_OOS_DEV_04` | `vua` | `D1` | Doanh thu thuần của tháng 3 năm 2026 là bao nhiêu tiền? | no_data | - | `no_data` | 0.00 | ✅ | ✅ |

## 6. Phân tích Nhóm Lỗi (Error Diagnostics)

🎉 **Không phát hiện lỗi nào trên tập dev.** Toàn bộ 19 câu benchmark đều đạt chuẩn chính xác tuyệt đối.
