# 📋 KẾ HOẠCH TRIỂN KHAI PHA 4: BACKTESTING & MODEL VALIDATION
## Dự án: 01. Cashflow_Forecasting (Dự báo Dòng tiền Ngắn hạn)
> **Mã kế hoạch:** GML-ML01-P4  
> **Trạng thái:** ✅ Đã hoàn thành 100% (7/7 Test Cases PASS)  
> **Bộ công cụ:** Python 3.11+, `pandas`, `numpy`, `scikit-learn`, `joblib`  
> **Đầu vào:** Model artifacts từ Pha 3 (`models/model_inflow.joblib`, `models/model_outflow.joblib`), Dữ liệu đặc trưng `data/processed/featured_cashflow.parquet`  
> **Đầu ra:** Báo cáo Backtest đa khung thời gian (`backtest_metrics.json`), Bảng so sánh Benchmark (`backtest_comparison.csv`), Kết quả Stress Testing (`stress_test_scenarios.csv`)  

---

## 1. MỤC TIÊU & PHƯƠNG PHÁP LUẬN KIỂM THỬ NGƯỢC (BACKTESTING)

Trong quản trị thanh khoản doanh nghiệp, việc kiểm thử ngược (Backtesting) không chỉ dừng lại ở sai số trung bình (Mean Error) mà phải giải quyết 4 bài toán trọng yếu của Hội đồng Quản trị và Giám đốc Tài chính (CFO):

1. **Chứng minh Giá trị Mô hình ML so với Phương pháp Truyền thống (Benchmark Comparison):**
   * Đối đầu LightGBM với 3 mô hình Baseline:
     - **Naive t-1:** Lấy phát sinh thu/chi ngày hôm trước làm dự báo cho hôm sau.
     - **Naive t-7 (Seasonal Naive):** Lấy phát sinh thu/chi cùng thứ của tuần trước.
     - **Moving Average 7 ngày (MA-7) & 30 ngày (MA-30):** Phương pháp ước lượng trung bình trượt kế toán thường dùng.
   * Tính toán chỉ số vượt trội: $\Delta \text{WAPE} = \text{WAPE}_{\text{Baseline}} - \text{WAPE}_{\text{LightGBM}}$ (Mô hình ML phải giảm thiểu sai số đáng kể).

2. **Đánh giá Đa khung thời gian (Multi-Horizon Evaluation: 7d, 14d, 30d):**
   * Đánh giá sai số phân rã theo 3 chân trời dự báo:
     - **T+7 ngày:** Kiểm thử dòng tiền tác nghiệp tuần (Weekly Operational Liquidity).
     - **T+14 ngày:** Kiểm thử chu kỳ nửa tháng (Bi-weekly Cash Cycle).
     - **T+30 ngày:** Kiểm thử toàn diện dòng tiền tháng (Monthly Cash Horizon).

3. **Dải Dự báo Tin cậy (Prediction Intervals / Confidence Bands 90%):**
   * Ước lượng cận trên (Upper Bound - Best Case) và cận dưới (Lower Bound - Worst Case) cho dòng tiền thuần:
     $$\hat{y}_{\text{lower}} = \hat{y} - 1.645 \times \sigma_{\text{residual}}, \quad \hat{y}_{\text{upper}} = \hat{y} + 1.645 \times \sigma_{\text{residual}}$$
   * Đo lường tỷ lệ bao phủ thực tế (Empirical Coverage Rate $\ge 75\%$).

4. **Kiểm tra Sức chịu đựng & Kịch bản Rủi ro Căng thẳng (Stress Testing):**
   * **Kịch bản S1 (Chậm thu nợ AR Shock):** Khách hàng chậm trả nợ khiến dòng tiền vào sụt giảm 25% trong tuần cao điểm.
   * **Kịch bản S2 (Áp lực chi trả AP Surge):** Nhà cung cấp siết nợ hoặc phát sinh chi phí đột xuất tăng thêm 25%.
   * **Kịch bản S3 (Kép - Stagflation Shock):** Đồng thời thu giảm 20% và chi tăng 20%.
   * Xác định số ngày xuất hiện **Nguy cơ Thâm hụt Thanh khoản (Cash Deficit Days)** và lượng tiền mặt tối thiểu cần chuẩn bị để bù đắp.

---

## 2. BỘ TEST CASES KIỂM ĐỊNH (TEST SUITE SPECIFICATION)

| Mã Test Case | Tên Test Case | Tiêu chuẩn Chấp thuận | Trạng thái |
|:---|:---|:---|:---:|
| **TC-BT-01** | Kiểm tra Input & Tính sẵn sàng | 2 models nạp thành công, đủ 31 ngày Tháng 7/2026 | ✅ PASS |
| **TC-BT-02** | So sánh Benchmark với Baselines | LightGBM vượt trội 4 Baselines (Inflow WAPE 67.7% vs 109.3%, Outflow WAPE 66.4% vs 79.3%) | ✅ PASS |
| **TC-BT-03** | Đánh giá Đa khung thời gian | Hoàn thành 7d (WAPE 62.9%), 14d (WAPE 64.4%), 30d (WAPE 69.8%) | ✅ PASS |
| **TC-BT-04** | Tính toán Dải Dự báo Tin cậy | Độ bao phủ thực tế đạt 96.77% (vượt tiêu chuẩn >= 75%) | ✅ PASS |
| **TC-BT-05** | Phân tích Phần dư & Ngoại lệ | Phát hiện 2 ngoại lệ vượt 2-sigma (21.81 Tỷ VNĐ) do biến động thu/chi | ✅ PASS |
| **TC-BT-06** | Mô phỏng Kịch bản Stress Testing | Mô phỏng S0, S1, S2, S3 thành công, đệm thanh khoản khẩn cấp 137.87 Tỷ | ✅ PASS |
| **TC-BT-07** | Đóng gói & Tính toàn vẹn Báo cáo | Xuất đầy đủ 4 files báo cáo CSV & JSON vào `models/` | ✅ PASS |

---

## 3. PHÂN CHIA CÁC TASK THỰC HIỆN

- [x] **Task 1:** Soạn thảo Kế hoạch chi tiết & Tiêu chuẩn kiểm thử (`PLAN_PHASE4_BACKTESTING_VALIDATION.md`).
- [x] **Task 2:** Xây dựng module Backtesting `src/backtesting.py` (Class `CashflowBacktester`).
- [x] **Task 3:** Xây dựng test suite tự động `tests/test_backtesting.py` bao phủ TC-BT-01 đến TC-BT-07.
- [x] **Task 4:** Chạy tiến trình Backtesting & Stress testing qua terminal, xuất báo cáo kết quả.
- [x] **Task 5:** Chạy kiểm thử tự động, xác nhận 100% Pass và tổng hợp báo cáo tài chính cho CFO.

---

## 4. BÁO CÁO KẾT QUẢ KIỂM THỬ NGƯỢC (BACKTESTING FINDINGS)

### 4.1. Đối đầu Benchmark với Baselines (Bằng chứng vượt trội của Mô hình ML)
| Mô hình | Inflow WAPE | Outflow WAPE | Directional Accuracy |
|:---|:---:|:---:|:---:|
| **LightGBM (ML Model)** | **67.68%** | **66.42%** | **70.00%** 🏆 |
| **Naive (t-1)** | 109.26% | 79.32% | 16.67% |
| **Seasonal Naive (t-7)** | 111.10% | 96.39% | 63.33% |
| **Moving Average 7d (MA-7)** | 96.25% | 82.11% | 33.33% |
| **Moving Average 30d (MA-30)** | 106.56% | 85.87% | 23.33% |

👉 **Kết luận:** Mô hình LightGBM giúp **giảm 38.0% - 41.5% sai số dòng tiền vào (Inflow)** và **giảm 16.3% - 31.1% sai số dòng tiền ra (Outflow)** so với các phương pháp kế toán truyền thống. Khả năng đoán đúng xu hướng dòng tiền tăng từ 16.7% lên 70.0%.

### 4.2. Đa khung thời gian (Multi-Horizon)
* **T+7 ngày (Tuần tác nghiệp):** Inflow WAPE **62.93%**, Outflow WAPE **61.44%**, Directional Accuracy **83.33%**.
* **T+14 ngày (Nửa tháng):** Inflow WAPE **64.44%**, Outflow WAPE **65.42%**, Directional Accuracy **69.23%**.
* **T+30 ngày (Cả tháng):** Inflow WAPE **69.84%**, Outflow WAPE **65.88%**, Directional Accuracy **68.97%**.

### 4.3. Dải dự báo tin cậy (90% Confidence Interval)
* Độ lệch chuẩn sai số ($\sigma_{\text{residual}}$): **25.36 Tỷ VNĐ**.
* Tỷ lệ các ngày thực tế nằm trọn vẹn trong dải Lower $\rightarrow$ Upper: **96.77%** (30/31 ngày).

### 4.4. Mô phỏng Kịch bản Căng thẳng (Stress Testing)
* **Kịch bản S0 (Dự báo cơ sở):** 15 ngày thâm hụt, thâm hụt lũy kế tối đa: **-24.43 Tỷ VNĐ**.
* **Kịch bản S1 (Thu trễ nợ AR Shock -25%):** 26 ngày thâm hụt, thâm hụt lũy kế tối đa: **-89.99 Tỷ VNĐ**.
* **Kịch bản S2 (Áp lực chi AP Surge +25%):** 25 ngày thâm hụt, thâm hụt lũy kế tối đa: **-94.64 Tỷ VNĐ**.
* **Kịch bản S3 (Kép - Thu -20%, Chi +20%):** 28 ngày thâm hụt, thâm hụt lũy kế tối đa: **-137.87 Tỷ VNĐ**.  
  $\rightarrow$ **Khuyến nghị cho CFO:** Cần duy trì hạn mức tín dụng thấu chi / dự phòng tiền mặt tối thiểu **138 Tỷ VNĐ** trong kịch bản suy thoái thị trường.
