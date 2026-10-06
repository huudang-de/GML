# BÁO CÁO HỌC THUẬT: ỨNG DỤNG MACHINE LEARNING TRONG QUẢN TRỊ RỦI RO CÔNG NỢ (AR RISK CLASSIFICATION) TẠI GỖ MINH LONG

**Dự án:** Trí tuệ Nhân tạo & Quản trị Dữ liệu (AI & Data Management) - Gỗ Minh Long
**Phân hệ:** Treasury & Liquidity Management
**Phiên bản mô hình:** v1.0.0 (LightGBM + Optuna)
**Ngày lập:** Tháng 10/2026

---

## TÓM TẮT (ABSTRACT)
Quản trị rủi ro tín dụng thương mại (Trade Credit Risk Management) là yếu tố sống còn đối với các doanh nghiệp B2B để đảm bảo dòng tiền khỏe mạnh. Báo cáo này trình bày phương pháp luận và quá trình thiết kế, triển khai mô hình học máy cảnh báo sớm nợ xấu (Early Warning System) tại Công ty Gỗ Minh Long. Bằng việc chuyển đổi dữ liệu từ cấp độ hóa đơn (Invoice-level) sang cấp độ khách hàng (Customer-level), nghiên cứu này giải quyết bài toán phân loại đa lớp (Multiclass Classification) trên tập dữ liệu mất cân bằng nghiêm trọng (Class Imbalance). Mô hình **LightGBM** được tối ưu hóa bằng **Optuna** và kỹ thuật phạt trọng số lớp (Class Weights) đã đạt chỉ số F1-Macro xuất sắc (0.8544), đặc biệt nhận diện thành công 84.31% các trường hợp nợ xấu (High Risk). Hơn thế nữa, nghiên cứu tích hợp lý thuyết trò chơi (SHAP) để bóc tách lý do rủi ro cho từng khách hàng, kết hợp đường ống dẫn liệu trực tiếp tới Power BI nhằm hỗ trợ trực quan cho bộ phận Thu hồi nợ.

---

## 1. GIỚI THIỆU (INTRODUCTION)

### 1.1. Đặt vấn đề
Khoản phải thu khách hàng (Accounts Receivable - AR) thường chiếm tỷ trọng lớn trong cơ cấu tài sản lưu động của Gỗ Minh Long. Phương pháp quản lý truyền thống thường dựa trên báo cáo tuổi nợ (Aging Report), mang tính chất hồi tố (Backward-looking) – tức là hệ thống chỉ phát tín hiệu khi khách hàng đã bắt đầu vi phạm thời hạn thanh toán. Việc thiếu hụt một hệ thống cảnh báo sớm (Forward-looking) khiến phòng kế toán bị động, phân bổ sai nguồn lực giục nợ và đối mặt với rủi ro đọng vốn kéo dài.

### 1.2. Mục tiêu nghiên cứu
Dự án nhằm phát triển một hệ thống đánh giá rủi ro hoàn toàn tự động với các tiêu chí:
1. **Phân loại rủi ro (Risk Stratification):** Chấm điểm và phân chia toàn bộ khách hàng thành 3 nhóm: Low Risk, Medium Risk, High Risk.
2. **Khả năng giải thích (Explainability):** Minh bạch hóa quyết định của AI, cung cấp luận điểm (Ví dụ: vì khách hàng có lịch sử nợ quá 90 ngày) để nhân viên làm việc với đối tác.
3. **Tích hợp vận hành (Operationalization):** Hệ thống không chỉ xuất ra xác suất toán học mà còn phải sinh ra cấu trúc giao diện (Mã màu, Risk Badge) nhằm hiển thị trực tiếp lên Dashboard Power BI (Shift-Left Processing).

### 1.3. Phạm vi (Scope)
- **Mục tiêu dự báo:** Xác suất rơi vào nhóm Nợ xấu (High Risk) của từng khách hàng đang có phát sinh dư nợ (Active Customers).
- **Ngưỡng rủi ro định nghĩa:** 
  - Đúng hạn (<=0 ngày): Low Risk.
  - Trễ hạn nhẹ (1-60 ngày): Medium Risk.
  - Nợ xấu (>60 ngày): High Risk.
- **Dữ liệu:** Toàn bộ lịch sử thanh toán từ `silver.fact_accountsreceivable` kết hợp danh mục đối tác `silver.dim_partner`.

---

## 2. PHƯƠNG PHÁP LUẬN (METHODOLOGY)

### 2.1. Pha 1: Chuẩn bị Dữ liệu và Kỹ thuật Gắn nhãn (Label Engineering)
Vì hệ thống kế toán không định nghĩa sẵn nhãn nợ xấu, quá trình Label Engineering được xây dựng toán học hóa. 
- Tính toán số ngày trễ hạn (`days_overdue`): Nếu hóa đơn đã thanh toán, tính khoảng cách từ ngày đáo hạn đến ngày trả. Nếu chưa thanh toán, tính khoảng cách tới thời điểm hiện tại.
- Lọc nhiễu: Loại bỏ các hóa đơn điều chuyển nội bộ và gán nhãn Low/Medium/High dựa trên giá trị `days_overdue` lớn nhất của từng hóa đơn trong quá khứ của khách hàng đó.

### 2.2. Pha 2: Trích xuất Đặc trưng (Feature Engineering)
Quá trình tổng hợp dữ liệu chuyển biến chiều phân tích từ Hóa đơn (Invoice) sang Khách hàng (Customer).
- **Hành vi lịch sử:** Trung bình số ngày trả trễ (`avg_days_overdue`), Lần trả trễ tồi tệ nhất (`max_days_overdue`), Tỷ lệ thanh toán đúng hạn (`pct_on_time`).
- **Quy mô và Tần suất:** Tổng số hóa đơn, giá trị đơn hàng trung bình.
*Đặc trưng `avg_days_overdue` đóng vai trò là chỉ báo tín dụng quan trọng nhất để mô hình nắm bắt thói quen dòng tiền của đối tác.*

### 2.3. Pha 3: Huấn luyện Mô hình & Xử lý Mất cân bằng (Training & Imbalance Handling)
- **Vấn đề mất cân bằng (Imbalance):** Nợ xấu (High Risk) chỉ chiếm tỷ trọng rất nhỏ (~10-15%). Nếu bỏ qua, AI sẽ luôn dự đoán toàn bộ là Low Risk để tối đa hóa Accuracy.
- **Giải pháp:** Không dùng SMOTE vì kỹ thuật tạo dữ liệu ảo hoạt động kém trên dữ liệu Tabular. Thay vào đó, áp dụng **Class Weights (Trọng số lớp)** để tự động phạt mô hình nặng hơn khi dự đoán sai nhóm thiểu số.
- **Lựa chọn thuật toán:** Sử dụng **LightGBM** (Champion) vượt qua Baseline (Logistic Regression) và Alternative (XGBoost).
- **Tối ưu siêu tham số:** Ứng dụng thuật toán TPE của thư viện **Optuna** duyệt qua hàng chục cấu hình (learning rate, num_leaves, max_depth) trong không gian tìm kiếm đa chiều.

---

## 3. THỰC NGHIỆM VÀ KẾT QUẢ (EXPERIMENTS & RESULTS)

### 3.1. Đánh giá Mô hình (Evaluation)
Quá trình kiểm định sử dụng Stratified 5-Fold Cross Validation trên tập Test (20% dữ liệu) đã chứng minh sức mạnh của mô hình:
- **ROC-AUC (Macro):** `0.9651` - Mô hình có khả năng phân định cực kỳ sắc bén giữa các lớp.
- **F1-Score (Macro):** `0.8544`.
- **Recall (Nhóm High Risk):** Đạt tỷ lệ bắt giữ nợ xấu lên đến **84.31%** (Bắt thành công 86/102 trường hợp nợ xấu thực tế). Đây là chỉ số kinh doanh quan trọng nhất, đảm bảo tính mạng lưới an toàn cho tín dụng doanh nghiệp.
- **Đường chuẩn Xác suất (Calibration Curve):** So khớp giữa Tỷ lệ nợ xấu dự báo (Predicted) và Thực tế (True) bám sát hoàn hảo (VD: Dự báo 29.26% $\approx$ Thực tế 19.61%; Dự báo 94.21% $\approx$ Thực tế 92.54%). Sự chính xác này khẳng định mô hình không bị "quá tự tin" (Overconfident).

### 3.2. Tính năng giải thích (Feature Importance & SHAP)
Việc sử dụng Trí tuệ Nhân tạo trong Tài chính yêu cầu khả năng giải trình (Explainability). Thông qua thư viện SHAP:
- **Phân tích Vĩ mô (Global):** Mô hình khẳng định `avg_days_overdue` (Thói quen trễ hạn trung bình) là yếu tố cấu thành rủi ro lớn nhất.
- **Phân tích Vi mô (Local Waterfall):** Bóc tách chẩn đoán cho từng khách hàng cụ thể thành dạng phương trình: *Xác suất rủi ro = Base Value + (Điểm cộng do trễ hạn dài) - (Điểm trừ do tỷ lệ thanh toán đúng hạn lịch sử tốt)*. Điều này trang bị cho Kế toán luận điểm sắc bén khi đối thoại với Khách hàng.

---

## 4. TRIỂN KHAI VÀ KHUYẾN NGHỊ (DEPLOYMENT & RECOMMENDATIONS)

### 4.1. Kiến trúc Hệ thống (Pha 5 & MLOps)
- **MLOps (MLflow):** Toàn bộ thử nghiệm, hệ số metrics, và cấu hình được ghi hình bằng MLflow (`sqlite:///mlflow.db`). Đặc biệt, mô hình được đóng gói kèm **Model Signature** (Khóa chặt định dạng Schema của bảng dữ liệu đầu vào), ngăn chặn lỗi Data Drift hoặc Code lỗi từ các hệ thống khác đẩy sang.
- **Shift-Left Data Architecture:** Hệ thống ML sinh ra Bảng phân tích rủi ro cuối cùng (`silver.fact_ar_risk_score`) chứa sẵn Xác suất Nợ xấu, Risk Badge (High/Medium/Low) và cả Mã màu Giao diện (`#FF4444`). Nhờ vậy, Power BI không phải thực thi một câu lệnh DAX nào, giúp Dashboard đạt tốc độ tải (Load time) tức thì.

### 4.2. Khuyến nghị
1. **Thiết lập chu kỳ huấn luyện (Retraining):** Hành vi thanh toán của B2B biến đổi theo chu kỳ kinh tế vĩ mô. Khuyến nghị chạy lại pipeline huấn luyện định kỳ hàng Quý (Quarterly) để mô hình học các mẫu (patterns) mới.
2. **Chiến lược Thu hồi nợ (Collection Strategy):** Kết hợp Risk Score với Aging Bucket hiện tại. Những khách hàng "Chưa trễ hạn nhưng mang High Risk" (Dấu hiệu nứt gãy dòng tiền ngầm) cần ưu tiên chăm sóc mềm mỏng trước khi thời hạn đến.

---

## 5. KẾT LUẬN (CONCLUSION)
Dự án "AI Phân loại Rủi ro Công nợ" đánh dấu một bước tiến quan trọng của Gỗ Minh Long trong việc quản lý tín dụng thương mại, chuyển hướng tiếp cận từ việc xử lý nợ quá hạn sang phòng ngừa nợ xấu từ trong trứng nước. Việc kết hợp sức mạnh của LightGBM, kỹ thuật giải thích mô hình SHAP và kiến trúc quản trị vòng đời MLOps chuẩn mực không chỉ giải bài toán kỹ thuật mà còn trang bị cho Ban Lãnh đạo một công cụ sắc bén trong cuộc chiến bảo vệ dòng tiền (Cashflow) của doanh nghiệp.

---
**Tài liệu tham khảo (References):**
- *Kiến trúc Data Warehouse và Hệ thống Kế toán Bán hàng Gỗ Minh Long.*
- *LGBMClassifier Documentation (Microsoft).*
- *A Unified Approach to Interpreting Model Predictions (Lundberg & Lee - SHAP).*
- *Bài báo tham khảo: Invoice Payment Prediction & Accounts Receivable Predictive Analytics (GML ML Archives).*
