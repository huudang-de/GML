# 📋 KẾ HOẠCH TRIỂN KHAI PHA 5: INTEGRATION & POWER BI DEPLOYMENT
## Dự án: 01. Cashflow_Forecasting (Dự báo Dòng tiền Ngắn hạn)
> **Mã kế hoạch:** GML-ML01-P5  
> **Trạng thái:** ✅ Đã hoàn thành 100% (7/7 Test Cases PASS)  
> **Bộ công cụ:** Python 3.11+, PostgreSQL Data Warehouse (Docker), SQLAlchemy, psycopg2, Power BI DAX  
> **Đầu vào:** Model artifacts và kết quả dự báo Pha 3 & Pha 4 (`models/prediction_intervals.csv`, `models/stress_test_scenarios.csv`, `models/backtest_metrics.json`)  
> **Đầu ra:** Bảng `gold.fact_cashflow_forecast` và `gold.fact_cashflow_scenarios` trên PostgreSQL; Tài liệu hướng dẫn tích hợp Power BI (Dashboard 5); Báo cáo đối chiếu so sánh với dự án tham khảo `Etherlabs-dev/cashflow-forecasting-engine`.  

---

## 1. MỤC TIÊU & KIẾN TRÚC TÍCH HỢP (INTEGRATION ARCHITECTURE)

Pha 5 là cầu nối quyết định biến kết quả thuật toán Machine Learning thành công cụ tác nghiệp thực tế cho Ban Lãnh đạo Gỗ Minh Long:

```
[Phase 3 & 4: LightGBM Forecast & Stress Tests]
                      │
                      ▼
[Phase 5 Python Integration Service (src/integration.py)]
   - Chuẩn hóa kiểu dữ liệu (Decimal/Numeric)
   - Gắn Metadata truy vết (as_of_date, run_id, model_version)
   - Tạo Schema & Nạp Idempotent vào PostgreSQL
                      │
                      ▼
[PostgreSQL Data Warehouse (Layer Gold)]
   - gold.fact_cashflow_forecast
   - gold.fact_cashflow_scenarios
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
[Subproject 02: Liquidity Opt]    [Power BI Dashboard 5: Treasury & Cash Management]
 - Tối ưu danh mục tiền gửi         - Visual 1: Actual vs Forecast & Confidence Bands (90%)
 - Tối ưu hạn mức thấu chi         - Visual 2: Matrix 30 ngày & Cảnh báo âm tiền
                                   - Visual 3: Slicer What-If Kịch bản (S0, S1, S2, S3)
                                   - Visual 4: KPI Cards (Net Expected, Max Deficit Buffer)
```

---

## 2. BỘ TEST CASES KIỂM ĐỊNH (TEST SUITE SPECIFICATION)

| Mã Test Case | Tên Test Case | Tiêu chuẩn Chấp thuận | Trạng thái |
|:---|:---|:---|:---:|
| **TC-IT-01** | Kiểm tra Input & Tính nhất quán | Đọc đầy đủ các artifacts Pha 3/4, đủ 31 ngày | ✅ PASS |
| **TC-IT-02** | Khởi tạo Schema & Tables Gold | Tạo `gold.fact_cashflow_forecast` và `gold.fact_cashflow_scenarios` | ✅ PASS |
| **TC-IT-03** | Tính Bất biến & Truy vết | Đầy đủ `as_of_date` (2026-06-30), `run_id`, `model_version` | ✅ PASS |
| **TC-IT-04** | Đồng bộ Dữ liệu vào PostgreSQL | 31 dòng vào bảng Forecast, 124 dòng vào bảng Scenarios | ✅ PASS |
| **TC-IT-05** | Tính Idempotency | Chạy lại pipeline không sinh duplicate records | ✅ PASS |
| **TC-IT-06** | Xác thực Truy vấn Tích hợp View | View `gold.view_cashflow_actual_vs_forecast` sẵn sàng cho Power BI | ✅ PASS |
| **TC-IT-07** | Đóng gói Giao diện Subproject 02 | Xuất `data/processed/forecast_for_optimization.parquet` đầy đủ 6 cột | ✅ PASS |

---

## 3. PHÂN CHIA CÁC TASK THỰC HIỆN

- [x] **Task 1:** Soạn thảo Kế hoạch chi tiết & Tiêu chuẩn kiểm thử (`PLAN_PHASE5_INTEGRATION.md`).
- [x] **Task 2:** Xây dựng module tích hợp `src/integration.py` (Tạo bảng Gold, nạp dữ liệu có `as_of_date` và `run_id`).
- [x] **Task 3:** Xây dựng test suite tự động `tests/test_integration.py` bao phủ TC-IT-01 đến TC-IT-07.
- [x] **Task 4:** Chạy tiến trình đồng bộ dữ liệu vào PostgreSQL qua terminal, kiểm tra bản ghi.
- [x] **Task 5:** Chạy kiểm thử tự động, xác nhận 100% Pass.
- [x] **Task 6:** Soạn thảo Tài liệu Hướng dẫn Triển khai Power BI chi tiết (Data Model, DAX Measures, Visual Mockups).
- [x] **Task 7:** Phân tích So sánh Đối chiếu Đa chiều với Dự án Tham khảo (`Etherlabs-dev/cashflow-forecasting-engine`).

---

## 4. KẾT QUẢ TÍCH HỢP DATA WAREHOUSE & GIAO DIỆN HỆ THỐNG

1. **Bảng Cơ sở Dữ liệu Đã tạo (PostgreSQL):**
   * `gold.fact_cashflow_forecast`: 31 bản ghi (Dòng tiền dự báo ngày Tháng 7/2026, dải tin cậy 90% Lower/Upper, thực tế đối soát).
   * `gold.fact_cashflow_scenarios`: 124 bản ghi (Mô phỏng 4 kịch bản S0_Baseline, S1_AR_Delay, S2_AP_Surge, S3_Combined, kèm cờ `is_cash_deficit`).
   * `gold.view_cashflow_actual_vs_forecast`: View phẳng phục vụ kết nối trực tiếp từ Power BI.

2. **File Giao diện cho Subproject 02 (Liquidity Optimization):**
   * Đường dẫn: `data/processed/forecast_for_optimization.parquet` (31 ngày, 6 cột đặc tả `date`, `pred_net`, `pred_inflow`, `pred_outflow`, `pred_net_lower_90`, `pred_net_upper_90`).
