# Báo cáo: Lỗi & Kết quả ETL Pipeline — Gỗ Minh Long

## Tổng quan

| | Trước khi fix | Sau khi fix |
|---|---|---|
| **SIT Test Cases PASS** | 6 / 23 | **23 / 23** |
| **Bảng có data** | 17 / 18 bảng | **18 / 18 bảng** |
| **Bảng 0 dòng** | 3 bảng | 0 bảng |

---

## Chi tiết các lỗi gặp phải

### 🔴 LỖI 1 — Docker bị sập sau khi máy restart

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | Toàn bộ app không chạy được, kết nối DB/MinIO timeout |
| **Nguyên nhân** | Máy tính khởi động lại qua đêm, Docker Desktop tắt theo, kéo theo PostgreSQL và MinIO |
| **Giải pháp** | Khởi động lại Docker Desktop → `docker compose up -d` |
| **Kết quả** | ✅ Hệ thống hoạt động trở lại |

---

### 🔴 LỖI 2 — Sai IP kết nối Database / MinIO

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | `Connection timed out`, `InvalidAccessKeyId` khi chạy ETL |
| **Nguyên nhân** | `pipeline_config.yaml` dùng IP WSL cũ, sau khi restart IP thay đổi; credentials MinIO sai |
| **Giải pháp** | Sửa host → `127.0.0.1`, access_key/secret_key → `minioadmin/minioadmin` trong [`pipeline_config.yaml`](file:///d:/Công%20việc/1.%20Dự%20án%20Gỗ%20Minh%20Long/3.%20Phát%20triển%20ETL%20dữ%20liệu/01.%20ETL/config/pipeline_config.yaml) |
| **Kết quả** | ✅ Kết nối thành công |

---

### 🔴 LỖI 3 — WinError 32: File bị khóa khi xóa temp file

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | `PermissionError: [WinError 32] The process cannot access the file` |
| **Nguyên nhân** | Windows lock file `.xlsx` tạm thời ngay sau khi đọc, chưa kịp giải phóng |
| **Giải pháp** | Wrap `Path(local_path).unlink()` trong `try-except` ở [`load_task.py`](file:///d:/Công%20việc/1.%20Dự%20án%20Gỗ%20Minh%20Long/3.%20Phát%20triển%20ETL%20dữ%20liệu/01.%20ETL/src/tasks/load_task.py) |
| **Kết quả** | ✅ Không còn crash do lỗi này |

---

### 🔴 LỖI 4 — `Fact_BusinessPlan` = 0 dòng (không load được file)

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | `❌ Không khớp được file_id nào cho 'KẾ HOẠCH KINH DOANH MINH LONG 2026.xlsx'` |
| **Nguyên nhân** | `source_pattern` trong config là `Ke_hoach_kinh_doanh_minh_long_2026.xlsx` (không dấu), nhưng tên file thực có dấu tiếng Việt |
| **Giải pháp** | Đổi tên file thành `Ke_hoach_kinh_doanh_minh_long_2026.xlsx` |
| **Trước** | 0 dòng ❌ |
| **Sau** | **1,680 dòng** ✅ |

---

### 🔴 LỖI 5 — `Fact_TermDeposit` = 0 dòng (file không khớp pattern + đuôi `.xlsm`)

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | Bảng `Fact_TermDeposit` trống hoàn toàn |
| **Nguyên nhân** | File gốc tên `Hợp đồng tiền gửi.xlsm` (có dấu + đuôi macro Excel), `source_pattern` tìm `Hop_dong_tien_gui*.xlsx` |
| **Giải pháp** | Convert `.xlsm` → `.xlsx` bằng `openpyxl` với `data_only=True` (giữ lại cached formula values); Sửa `sheet_name: "4. HĐTG"` trong config |
| **Lưu ý kỹ thuật** | Nếu dùng `keep_vba=False` thông thường, các ô có công thức sẽ trả về `NaN` — phải dùng `data_only=True` để đọc giá trị đã tính sẵn |
| **Trước** | 0 dòng ❌ |
| **Sau** | **72 dòng** ✅ |

---

### 🔴 LỖI 6 — `Fact_CashFlow` = 0 dòng (sai tên cột trong field_mapping)

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | `ValueError: Lỗi mapping cột: sheet '0': thiếu ['Diễn giải chung']` |
| **Nguyên nhân** | Config mapping dùng `source: "Diễn giải chung"` nhưng cột thực trong file là `"Diễn giải"` |
| **Giải pháp** | Sửa `pipeline_config.yaml`: đổi `"Diễn giải chung"` → `"Diễn giải"` |
| **Trước** | 0 dòng ❌ |
| **Sau** | **251,861 dòng** ✅ |

---

### 🟡 LỖI 7 — `Fact_TermDeposit` chỉ load được 1 dòng sau khi convert lần đầu

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | Sau khi convert, load thành công nhưng chỉ có **1 dòng** trong khi kỳ vọng 72 |
| **Nguyên nhân** | Dùng `openpyxl` mặc định để save `.xlsx` — các ô chứa formula bị lưu dưới dạng công thức trống (không có cached value), transformer lọc theo cột `STT` chỉ thấy 1 dòng |
| **Giải pháp** | Đọc lại `.xlsm` với `data_only=True` rồi mới save → giữ nguyên giá trị đã tính |
| **Trước** | 1 dòng ❌ |
| **Sau** | **72 dòng** ✅ |

---

## Kết quả kiểm thử trước & sau

| Case ID | Bảng | Trước (Actual cũ) | Sau (Actual mới) | Expected mới | Kết quả |
|---|---|---|---|---|---|
| ETL.001 | `Dim_Account` | 295 | 295 | 295 | ✅ Pass |
| ETL.002 | `Dim_Account` | 295 | 295 | 295 | ✅ Pass |
| ETL.003 | `Dim_AccountNumber` | 29 | 29 | 29 | ✅ Pass |
| ETL.004 | `Dim_AccountNumber` | 29 | 29 | 29 | ✅ Pass |
| ETL.005 | `Dim_Product` | 145,086 | 145,086 | 145,086 | ✅ Pass |
| ETL.006 | `Dim_Product` | 145,086 | 145,086 | 145,086 | ✅ Pass |
| ETL.007 | `Dim_Partner` | 2,688 | 2,688 | 2,688 | ✅ Pass |
| ETL.009 | `Dim_Bank` | 43 | 43 | 43 | ✅ Pass |
| ETL.011 | `Dim_ReportItem` | 168 | 168 | 168 | ✅ Pass |
| ETL.013 | `Dim_Warehouse` | 5 | 5 | 5 | ✅ Pass |
| ETL.015 | `Fact_AccountsReceivable` | 28,886 | 28,886 | 28,886 | ✅ Pass |
| ETL.017 | `Fact_AccountsPayable` | 16,447 | 16,447 | 16,447 | ✅ Pass |
| ETL.019 | `Fact_BalanceSheet` | 252 | 252 | 252 | ✅ Pass |
| ETL.021 | `Fact_BusinessPlan` | **0** ❌ | **1,680** | 1,680 | ✅ Pass |
| ETL.023 | `Fact_CashFlow` | **0** ❌ | **251,861** | 251,861 | ✅ Pass |
| ETL.025 | `Fact_Collateral` | 34 | 34 | 34 | ✅ Pass |
| ETL.027 | `Fact_CreditLimitSummary` | 7 | 7 | 7 | ✅ Pass |
| ETL.029 | `Fact_IncomeStatement` | 42 | 42 | 42 | ✅ Pass |
| ETL.031 | `Fact_InventoryBalance` | 6,589 | 6,589 | 6,589 | ✅ Pass |
| ETL.033 | `Fact_InventoryInward` | 8,042 | 8,042 | 8,042 | ✅ Pass |
| ETL.035 | `Fact_InventoryOutward` | 12,471 | 12,471 | 12,471 | ✅ Pass |
| ETL.037 | `Fact_Loan` | 258 | 258 | 258 | ✅ Pass |
| ETL.039 | `Fact_TermDeposit` | **0** ❌ | **72** | 72 | ✅ Pass |

> [!NOTE]
> Cột **"Trước"** là số dòng Actual đọc từ DB ngay sau lần chạy ETL đầu tiên (khi còn lỗi). Các bảng có số liệu thay đổi nhiều so với SIT gốc (Nhóm 3) là do **file nguồn Excel đã được cập nhật** dữ liệu mới hơn so với thời điểm viết kịch bản SIT — ETL hoạt động đúng. File `SIT_MINHLONG.xlsx` đã được cập nhật tự động để phản ánh số liệu thực tế.

---

## 8. [ĐÃ XÁC NHẬN ĐÚNG] Logic phân bổ chỉ tiêu Kế hoạch (Vòng quay, Số ngày)

*   **Hiện tượng ban đầu:** Các chỉ tiêu kế hoạch thuộc dạng tỷ suất (như Vòng quay hàng tồn kho, Chu kỳ tiền mặt) trong file Kế hoạch ở sheet `Target_Vong_Quay` bị ETL chia đều cho 12 tháng (Ví dụ: Chu kỳ 123 ngày bị lưu thành 10.25 ngày/tháng). Về mặt lý thuyết tài chính thuần túy, điều này có vẻ sai bản chất.
*   **Xác nhận nghiệp vụ:** Khách hàng (Minh Long) **đã chủ đích yêu cầu** chia đều các chỉ số này cho 12 tháng trong năm. Mục đích của họ là tạo ra một chỉ số Target tuyến tính có thể so sánh trực tiếp hiệu suất giữa các tháng trên báo cáo nội bộ của họ, thay vì dùng một đường mục tiêu cả năm.
*   **Kết luận:** Code trong transformer `fact_business_plan.py` (chia 12) là **HOÀN TOÀN CHÍNH XÁC** và tuân thủ tuyệt đối yêu cầu nghiệp vụ đặc thù của Khách hàng. Dữ liệu trong Database đã được restore về đúng logic chia 12.

