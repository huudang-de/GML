# ⚠️ Báo cáo Tham khảo #2: AR Risk Classification (Dự báo nợ xấu)
## Chủ đề: `Invoice Payment Prediction` (Dự đoán ngày trả tiền / trễ hạn)

> **Keyword tìm kiếm:** `invoice payment prediction machine learning`, `accounts receivable predictive analytics xgboost`
> **Liên quan đến:** `6. ML / 2. AR_Risk_Classification` của GML
> **Ngày nghiên cứu:** 04/10/2026

---

## 1. Tổng quan bài toán trên thế giới

Bài toán "Phân loại rủi ro công nợ" trong công nghiệp (B2B) thường được gọi là **Invoice Payment Prediction** (Dự đoán hóa đơn thanh toán).
Mục tiêu là dự đoán **khi nào** một khách hàng sẽ trả tiền, hoặc **khả năng** hóa đơn đó bị trễ hạn (late payment) dựa trên lịch sử giao dịch.

Có 2 hướng giải quyết chính:
1. **Regression (Hồi quy):** Dự đoán chính xác số ngày trễ (delay_days = payment_date - due_date).
2. **Classification (Phân loại):** Phân nhóm rủi ro (Ví dụ: On-time, Late 1-15 days, Late 16-30 days, Late > 60 days / Default).

Với GML, chúng ta sẽ ưu tiên **Classification** kết hợp **Scoring (xác suất)** để phòng thu hồi nợ dễ làm việc.

---

## 2. Kiến trúc giải pháp phổ biến (Dựa trên top GitHub repos)

### 2.1 Thuật toán thống trị: XGBoost / LightGBM
Hầu hết các dự án thành công nhất (như của IBM, hoặc các bài giải TopCoder) đều sử dụng **XGBoost** hoặc **LightGBM**. Lý do:
- Dữ liệu tài chính (tabular data) thường không tuyến tính.
- XGBoost/LightGBM xử lý tốt missing values.
- Hỗ trợ tốt tính năng giải thích mô hình (Explainability) thông qua **SHAP values**.

### 2.2 Feature Engineering (Bí quyết thành công)
Code ML chỉ chiếm 20%, 80% là Feature Engineering. Dưới đây là các Features bắt buộc phải có từ các repo tham khảo:

#### A. Customer-level Features (Lịch sử khách hàng)
- `avg_payment_delay`: Trung bình số ngày trả trễ trong 6 tháng qua của khách hàng này.
- `on_time_ratio`: Tỷ lệ thanh toán đúng hạn trong quá khứ.
- `total_outstanding_amount`: Tổng nợ hiện tại đang chưa trả (Dùng logic lũy kế).

#### B. Invoice-level Features (Đặc trưng hóa đơn)
- `invoice_amount`: Giá trị hóa đơn. (Thường log-transform để giảm skewness).
- `payment_terms`: Thời hạn thanh toán (VD: Net 30, Net 60).

#### C. Temporal/Seasonal Features (Đặc trưng thời gian)
- `due_month`: Tháng đáo hạn (Khách hàng B2B thường kẹt tiền vào dịp cuối năm hoặc trước Tết).
- `due_day_of_week`: Ngày trong tuần (Thứ 6 thường hay bị đẩy sang tuần sau).

---

## 3. Các vấn đề kỹ thuật lớn (Pain Points) và Cách giải quyết

### 3.1 Class Imbalance (Dữ liệu mất cân bằng)
**Vấn đề:** 80-90% hóa đơn thường được trả đúng hạn. Nếu train bình thường, model sẽ luôn đoán "Đúng hạn" để đạt accuracy cao, bỏ qua nợ xấu.
**Cách giải quyết trong các repo open-source:**
- **SMOTE (Synthetic Minority Over-sampling Technique):** Sinh thêm dữ liệu nợ xấu giả.
- **XGBoost `scale_pos_weight`:** Cấu hình trọng số phạt cao hơn nếu đoán sai nợ xấu. (Khuyên dùng cách này cho GML).

### 3.2 Data Leakage (Rò rỉ dữ liệu)
**Vấn đề:** Lấy trung bình số ngày trễ của khách hàng vào năm 2024 để dự đoán cho hóa đơn năm 2023.
**Cách giải quyết:** Chỉ sử dụng dữ liệu *trước* ngày phát hành hóa đơn (strictly historical windows) để tính các Features.

---

## 4. Áp dụng vào dự án Gỗ Minh Long (GML)

### Sơ đồ luồng xử lý (Data Flow)

```text
fact_cashflow & fact_receivable (ERP/MISA)
        │
        ▼
Feature Engineering Pipeline (Python/Pandas)
  ├─ Tính `avg_payment_delay_past_6m`
  ├─ Tính `customer_risk_score_historical`
  └─ Extract `seasonality_flags`
        │
        ▼
Train-Test Split (Time-based split, KHÔNG random split)
        │
        ▼
XGBoost / LightGBM Classifier (predict: 0 = OnTime, 1 = Late)
        │
        ▼
SHAP Explainer (Giải thích lý do)
        │
        ▼
Lưu kết quả dự đoán và SHAP values vào DB → Lên Power BI
```

---

## 5. Roadmap triển khai thực tế

| Giai đoạn | Hành động cụ thể | Tham khảo thư viện |
|:---|:---|:---|
| **Step 1: Data Prep** | Map các cột từ `fact_cashflow` sang format chuẩn: `invoice_id, customer_id, issue_date, due_date, payment_date, amount`. | `pandas`, `numpy` |
| **Step 2: Feature Eng** | Code hàm tính trung bình trễ hạn (rolling mean past 180 days) cho từng khách hàng. | `pandas.DataFrame.rolling` |
| **Step 3: Training** | Setup XGBoost, lưu ý chỉnh tham số `scale_pos_weight` để cân bằng dữ liệu nợ xấu. | `xgboost.XGBClassifier` |
| **Step 4: Explainability**| Tích hợp SHAP để nhân viên thu hồi nợ biết: "Khách hàng này bị cảnh báo rủi ro 85% vì: Lịch sử nợ quá hạn 3 tháng qua rất cao". | `shap` |

---

## 6. Lời khuyên khi build Model
- Đừng dùng **Random Split** (chia 80-20 ngẫu nhiên). Trong chuỗi thời gian/tài chính, phải dùng **Time-based Split** (Train bằng data 2022-2023, Test bằng data 2024) để mô phỏng thực tế.
- Accuracy (Độ chính xác) là vô nghĩa. Hãy đo lường bằng **Recall** (Bắt được bao nhiêu phần trăm nợ xấu thực sự) và **F1-Score**.
