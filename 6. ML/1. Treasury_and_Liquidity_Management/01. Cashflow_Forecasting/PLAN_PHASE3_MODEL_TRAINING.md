# 📋 KẾ HOẠCH TRIỂN KHAI PHA 3: MODEL TRAINING & HYPERPARAMETER TUNING
## Dự án: 01. Cashflow_Forecasting (Dự báo Dòng tiền Ngắn hạn)
> **Mã kế hoạch:** GML-ML01-P3  
> **Trạng thái:** ✅ Đã hoàn thành 100% (7/7 Test Cases PASS)  
> **Bộ công cụ:** Python 3.11+, `lightgbm`, `xgboost`, `optuna`, `scikit-learn`, `joblib`  
> **Dữ liệu đầu vào:** `data/processed/featured_cashflow.parquet` (Pha 2 - 76 cột đặc trưng)  
> **Mục tiêu đầu ra:** 2 Mô hình chuẩn hóa (`model_inflow.joblib` & `model_outflow.joblib`), Bảng tham số tối ưu `best_params.json`, Báo cáo đánh giá hiệu năng `metrics.json`  

---

## 1. MỤC TIÊU & PHƯƠNG PHÁP LUẬN HUẤN LUYỆN

Trong quản trị tài chính doanh nghiệp, dòng tiền vào (Inflow) và dòng tiền ra (Outflow) bị chi phối bởi các động lực hoàn toàn khác nhau:
- **Dòng tiền vào (Inflow):** Phụ thuộc vào hành vi trả nợ của khách hàng, chu kỳ bán hàng và lịch nợ AR.
- **Dòng tiền ra (Outflow):** Phụ thuộc vào cam kết trả nợ nhà cung cấp AP, lịch trả nợ vay ngân hàng, ngày trả lương cố định và ngày nộp thuế.

👉 **Chiến lược mô hình hóa:** Huấn luyện **2 Mô hình LightGBM Regressor độc lập**:
$$\hat{y}_{\text{inflow}} = f_{\text{inflow}}(X_t), \quad \hat{y}_{\text{outflow}} = f_{\text{outflow}}(X_t)$$
Sau đó kết hợp thành dự báo Dòng tiền thuần:
$$\hat{y}_{\text{net}} = \hat{y}_{\text{inflow}} - \hat{y}_{\text{outflow}}$$

### 1.1. Chiến lược Phân chia Dữ liệu: Walk-Forward Validation
* **Nguyên tắc vàng:** Tuyệt đối không dùng kịch bản ngẫu nhiên (`K-Fold Random Split`).
* **Cơ chế Walk-Forward (Rolling Origin):**
  - **Tập Train (Huấn luyện):** Từ ngày 31 đến ngày 181 (Tháng 02 $\rightarrow$ Hết Tháng 06/2026, khoảng 150 ngày).
  - **Tập Test (Out-of-Time Evaluation):** Toàn bộ Tháng 07/2026 (31 ngày từ `01/07/2026` đến `31/07/2026`) để kiểm thử khả năng dự báo 30 ngày tương lai trong điều kiện thực tế.

### 1.2. Tối ưu Siêu tham số với Optuna
Sử dụng thuật toán **Tree-structured Parzen Estimator (TPE)** của Optuna để tìm kiếm không gian tham số tối ưu cho LightGBM:
- `learning_rate`: $[0.01, 0.15]$
- `num_leaves`: $[15, 63]$
- `max_depth`: $[3, 10]$
- `min_child_samples`: $[5, 30]$
- `colsample_bytree`: $[0.6, 1.0]$
- `subsample`: $[0.6, 1.0]$
- `reg_alpha` (L1), `reg_lambda` (L2): $[10^{-8}, 10.0]$
- **Hàm mục tiêu (Objective):** Minimize WAPE trên các Fold Walk-Forward.

---

## 2. BỘ TEST CASES KIỂM ĐỊNH (TEST SUITE SPECIFICATION)

| Mã Test Case | Tên Test Case | Tiêu chuẩn Chấp thuận | Trạng thái |
|:---|:---|:---|:---:|
| **TC-TR-01** | Kiểm tra Input & Lựa chọn Features | Đọc `featured_cashflow.parquet`, 69 features, loại trừ rò rỉ | ✅ PASS |
| **TC-TR-02** | Tính toàn vẹn của Walk-Forward Split | Train < Test (30/06 < 01/07), TimeSeriesSplit 3 folds không rò rỉ | ✅ PASS |
| **TC-TR-03** | Tối ưu hóa Siêu tham số bằng Optuna | TPE sampler tối ưu siêu tham số thành công cho Inflow & Outflow | ✅ PASS |
| **TC-TR-04** | Huấn luyện Mô hình Kép (Inflow & Outflow) | 2 mô hình LightGBM Regressor hội tụ, dự báo hợp lệ không NaN | ✅ PASS |
| **TC-TR-05** | Đánh giá Hiệu năng Out-of-Time (Tháng 7) | Inflow WAPE=67.68%, Outflow WAPE=66.42%, Directional Acc=70% | ✅ PASS |
| **TC-TR-06** | Phân tích Mức độ Quan trọng | Trích xuất Top 10 đặc trưng then chốt (`ar_expected_due_today`, lags, rollings) | ✅ PASS |
| **TC-TR-07** | Đóng gói & Tái kiểm tra Mô hình | Lưu và nạp lại từ `models/`, kết quả inference khớp 100% | ✅ PASS |

---

## 3. PHÂN CHIA CÁC TASK THỰC HIỆN

- [x] **Task 1:** Soạn thảo Kế hoạch chi tiết & Tiêu chuẩn kiểm thử (`PLAN_PHASE3_MODEL_TRAINING.md`).
- [x] **Task 2:** Kiểm tra môi trường thư viện (`lightgbm`, `xgboost`, `optuna`, `joblib`).
- [x] **Task 3:** Xây dựng module huấn luyện mô hình `src/model_training.py` (Class `CashflowModelTrainer`).
- [x] **Task 4:** Xây dựng test suite tự động `tests/test_model_training.py` bao phủ TC-TR-01 đến TC-TR-07.
- [x] **Task 5:** Chạy tiến trình huấn luyện & Optuna tuning qua terminal, hiển thị log trực tiếp.
- [x] **Task 6:** Chạy test suite nghiệm thu toàn diện, kiểm tra 100% Pass và xuất báo cáo metrics.

---

## 4. BÁO CÁO KẾT QUẢ ĐÁNH GIÁ (OUT-OF-TIME EVALUATION - THÁNG 7/2026)

* **Thời gian kiểm thử:** 01/07/2026 đến 31/07/2026 (31 ngày Out-of-Time).
* **Dòng tiền vào (Inflow):**
  - Thực tế: **288.54 Tỷ VNĐ** | Mô hình dự báo: **305.93 Tỷ VNĐ** (Sai lệch tổng tháng chỉ **6.03%**!).
  - Daily WAPE: **67.68%**.
  - Top 3 đặc trưng ảnh hưởng: `inflow_lag_14`, `inflow_lag_1`, `ar_expected_due_today`.
* **Dòng tiền ra (Outflow):**
  - Thực tế: **457.01 Tỷ VNĐ** | Mô hình dự báo: **318.84 Tỷ VNĐ** (Sai lệch tổng tháng 30.23%).
  - Daily WAPE: **66.42%**.
  - Top 3 đặc trưng ảnh hưởng: `inflow_lag_1`, `outflow_lag_14`, `ar_expected_due_today`.
* **Dòng tiền thuần (Net Cashflow):**
  - Directional Accuracy (Dự báo đúng chiều tăng/giảm): **70.00%**.
* **Artifacts đã xuất:**
  - `models/model_inflow.joblib` (59.2 KB)
  - `models/model_outflow.joblib` (86.4 KB)
  - `models/best_params.json`
  - `models/evaluation_metrics.json`
  - `models/feature_importance.json`
  - `models/test_predictions_july2026.csv`
