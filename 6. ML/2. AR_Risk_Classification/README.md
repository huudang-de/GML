# ⚠️ Phân tích Rủi ro Công nợ — AR Risk Classification

> **Mức ưu tiên:** ⭐⭐⭐⭐⭐ | **Framework chính:** scikit-learn | **Model:** LightGBM/XGBoost | **Bổ trợ:** SHAP + MLflow

---

## 1. Bài toán & Mục tiêu

### Vấn đề hiện tại
Tổng Phải thu (`B01-DN_130`) của Gỗ Minh Long đang ở mức cao. Dashboard Phải thu hiện tại chỉ **mô tả** tình trạng nợ (Aging, Top 10 KH dư nợ lớn nhất), nhưng **chưa thể dự đoán** khách hàng nào sẽ trễ hạn trong tương lai để chủ động xử lý.

### Mục tiêu dự án ML
1. **Phân loại rủi ro** từng khách hàng thành 3 nhóm: `Low Risk`, `Medium Risk`, `High Risk`.
2. **Tính xác suất trễ hạn** (Probability of Default - PD) cho từng khoản nợ.
3. **Giải thích mô hình** bằng SHAP — tại sao khách hàng X bị xếp vào High Risk?
4. **Tích hợp kết quả** vào Dashboard Phải thu (Cột Risk Score + màu cảnh báo).

---

## 2. Định nghĩa nhãn (Label Engineering)

```python
# Dựa trên lịch sử thanh toán thực tế
# Target: 1 = Trễ hạn (overdue > 30 ngày), 0 = Đúng hạn / Sớm hạn

def label_overdue(row):
    if row['days_overdue'] > 60:
        return 2  # High Risk
    elif row['days_overdue'] > 30:
        return 1  # Medium Risk
    else:
        return 0  # Low Risk
```

---

## 3. Nguồn dữ liệu

| Bảng nguồn | Trường sử dụng | Mô tả |
|:---|:---|:---|
| `silver.fact_accountsreceivable` | `customer_code`, `invoice_date`, `due_date`, `invoice_amount`, `payment_date` | Lịch sử hóa đơn & thanh toán |
| `silver.dim_partner` | `partner_code`, `partner_name`, `partner_type` | Thông tin khách hàng |
| `silver.fact_cashflow` | `posting_date`, `debit_amount` | Xác nhận thanh toán thực tế |

---

## 4. Feature Engineering

```python
customer_features = {
    # Lịch sử thanh toán
    "avg_days_overdue_6m":    "Số ngày trễ hạn trung bình 6 tháng gần nhất",
    "max_days_overdue_1y":    "Số ngày trễ hạn lớn nhất trong 1 năm",
    "pct_on_time_payments":   "Tỷ lệ thanh toán đúng hạn lịch sử (%)",
    "total_overdue_amount":   "Tổng giá trị nợ quá hạn hiện tại",
    "num_overdue_invoices":   "Số hóa đơn đang quá hạn",

    # Quy mô giao dịch
    "avg_invoice_amount":     "Giá trị hóa đơn trung bình",
    "total_revenue_ytd":      "Tổng doanh thu với KH trong năm",
    "invoice_frequency":      "Tần suất đặt hàng (đơn/tháng)",

    # Đặc điểm khoản nợ hiện tại
    "days_since_invoice":     "Số ngày kể từ ngày hóa đơn",
    "invoice_amount":         "Giá trị hóa đơn cụ thể",
    "payment_term_days":      "Số ngày công nợ cho phép",
}
```

---

## 5. Kiến trúc Pipeline

```
PostgreSQL (Silver Layer)
        │
        ▼
[1. Label Engineering]
  - Tính days_overdue từ (payment_date - due_date)
  - Phân loại 3 nhóm: Low / Medium / High Risk
        │
        ▼
[2. Feature Engineering]
  - Aggregate features theo customer_code
  - Xử lý imbalanced classes (SMOTE hoặc class_weight)
        │
        ▼
[3. Model Training & Selection]
  ┌─────────────────────────────────────────────────┐
  │  Baseline: Logistic Regression (scikit-learn)   │
  │  Champion: LightGBM Classifier                  │
  │  Alternative: XGBoost Classifier                │
  │  Tuning: Optuna hyperparameter search           │
  └─────────────────────────────────────────────────┘
        │
        ▼
[4. Model Evaluation]
  - ROC-AUC, Precision-Recall, F1-Score
  - Confusion Matrix
  - Calibration Curve (xác suất có nghĩa hay không?)
        │
        ▼
[5. SHAP Explainability]
  - Global: Feature Importance (bar chart)
  - Local: Waterfall plot cho từng khách hàng
        │
        ▼
[6. MLflow Tracking & Registry]
        │
        ▼
[7. Scoring & Export]
  - Chạy model trên toàn bộ active customers
  - Xuất → PostgreSQL: silver.fact_ar_risk_score
  - Power BI đọc để hiển thị Risk Badge + màu cảnh báo
```

---

## 6. Chi tiết từng bước triển khai

### Bước 1 — EDA & Label Engineering (`1_eda_label.ipynb`)
- [ ] Phân tích phân phối `days_overdue` của toàn bộ lịch sử
- [ ] Xác định ngưỡng phân loại (30 ngày, 60 ngày) dựa trên dữ liệu thực
- [ ] Kiểm tra class imbalance: tỷ lệ High/Medium/Low Risk
- [ ] Vẽ biểu đồ Aging Bucket (số hóa đơn theo khoảng ngày)

### Bước 2 — Feature Pipeline (`2_feature_pipeline.py`)
```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from imblearn.over_sampling import SMOTE

preprocessor = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])
```

### Bước 3 — Model Training (`3_train_model.ipynb`)
```python
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.calibration import CalibratedClassifierCV

lgbm = lgb.LGBMClassifier(
    n_estimators=1000,
    learning_rate=0.05,
    num_leaves=31,
    class_weight='balanced',
    random_state=42
)

# Calibrate để xác suất có ý nghĩa thực
calibrated_model = CalibratedClassifierCV(lgbm, cv=5, method='isotonic')
calibrated_model.fit(X_train, y_train)
```

### Bước 4 — SHAP Explainability (`4_shap_explain.ipynb`)
```python
import shap

explainer = shap.TreeExplainer(lgbm)
shap_values = explainer.shap_values(X_test)

# Global importance
shap.summary_plot(shap_values, X_test, plot_type="bar")

# Local explanation cho 1 khách hàng cụ thể
shap.waterfall_plot(shap.Explanation(
    values=shap_values[customer_idx],
    base_values=explainer.expected_value,
    data=X_test.iloc[customer_idx]
))
```

### Bước 5 — MLflow Tracking (`5_mlflow_tracking.py`)
```python
import mlflow

with mlflow.start_run(run_name="ar_risk_lgbm_v1"):
    mlflow.log_params(lgbm.get_params())
    mlflow.log_metrics({
        "roc_auc": roc_auc,
        "f1_macro": f1,
        "precision_high_risk": precision_hr,
        "recall_high_risk": recall_hr
    })
    mlflow.lightgbm.log_model(lgbm, "ar_risk_model")
    mlflow.log_artifact("shap_summary.png")
```

### Bước 6 — Scoring & Export (`6_score_and_export.py`)
```python
# Áp dụng model lên tất cả khách hàng active
risk_df = pd.DataFrame({
    "customer_code": customers,
    "risk_score":    model.predict_proba(X)[:, 2],   # P(High Risk)
    "risk_label":    model.predict(X),                # 0/1/2
    "scoring_date":  pd.Timestamp.today()
})

risk_df.to_sql("fact_ar_risk_score", engine, schema="silver",
               if_exists="replace", index=False)
```

---

## 7. Tích hợp Power BI

```
silver.fact_ar_risk_score
    ├── customer_code  → JOIN với dim_partner
    ├── risk_label     → Conditional color: 🔴 High / 🟡 Medium / 🟢 Low
    ├── risk_score     → Gauge chart hoặc Progress bar
    └── scoring_date   → Timestamp cập nhật lần cuối
```

---

## 8. Cấu trúc thư mục

```
2. AR_Risk_Classification/
├── README.md
├── requirements.txt
├── config.yaml
├── notebooks/
│   ├── 1_eda_label.ipynb
│   ├── 2_feature_engineering.ipynb
│   ├── 3_train_model.ipynb
│   ├── 4_shap_explain.ipynb
│   └── 5_mlflow_tracking.ipynb
├── src/
│   ├── data_loader.py
│   ├── feature_engineering.py
│   ├── train.py
│   ├── explain.py
│   └── score.py
├── models/
└── outputs/
    ├── risk_scores.csv
    └── shap_summary.png
```

---

## 9. KPIs Đánh giá thành công

| Metric | Target |
|:---|:---|
| ROC-AUC (binary: High Risk vs Rest) | > 0.80 |
| Recall (High Risk) | > 75% — Ưu tiên không bỏ sót rủi ro cao |
| Precision (High Risk) | > 60% |
| F1-Macro (3 classes) | > 0.70 |
| Retraining cycle | Hàng quý |

---

## 10. Dependencies

```txt
# requirements.txt
scikit-learn>=1.4.0
lightgbm>=4.0.0
xgboost>=2.0.0
shap>=0.45.0
mlflow>=2.10.0
imbalanced-learn>=0.12.0
optuna>=3.5.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pandas>=2.1.0
numpy>=1.26.0
matplotlib>=3.8.0
seaborn>=0.13.0
```
