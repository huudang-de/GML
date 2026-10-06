# BÁO CÁO HỌC THUẬT: ỨNG DỤNG MACHINE LEARNING TRONG DỰ BÁO DÒNG TIỀN NGẮN HẠN (CASH FLOW FORECASTING) TẠI GỖ MINH LONG

**Dự án:** Trí tuệ Nhân tạo & Quản trị Dữ liệu (AI & Data Management) - Gỗ Minh Long
**Phân hệ:** Treasury & Liquidity Management
**Phiên bản mô hình:** v1.0.0 (LightGBM + Optuna)
**Ngày lập:** Tháng 10/2026

---

## TÓM TẮT (ABSTRACT)
Quản trị thanh khoản và dòng tiền (Liquidity & Cash Flow Management) là một trong những bài toán cốt lõi đối với sự ổn định tài chính của doanh nghiệp. Báo cáo này trình bày phương pháp luận và quá trình triển khai hệ thống dự báo dòng tiền ngắn hạn tại Công ty Gỗ Minh Long sử dụng các kỹ thuật Học máy (Machine Learning). Thay vì sử dụng các phương pháp ngoại suy chuỗi thời gian truyền thống (ARIMA, Exponential Smoothing), nghiên cứu này đề xuất một đường ống (pipeline) hoàn chỉnh dựa trên mô hình **LightGBM** (Light Gradient Boosting Machine), kết hợp tối ưu hóa siêu tham số bằng **Optuna** và kỹ thuật kiểm định chéo **Walk-Forward TimeSeriesSplit**. Kết quả thực nghiệm cho thấy mô hình học máy vượt trội đáng kể so với các đường cơ sở (baselines) như Naive, Seasonal Naive, và Moving Average trong việc dự báo cả Dòng tiền vào (Inflow) và Dòng tiền ra (Outflow), đồng thời cung cấp kiến trúc dữ liệu tích hợp sâu với Data Warehouse (PostgreSQL) phục vụ công tác báo cáo kinh doanh (Power BI).

---

## 1. GIỚI THIỆU (INTRODUCTION)

### 1.1. Đặt vấn đề
Trong môi trường kinh doanh biến động, việc thiếu hụt thanh khoản ngắn hạn có thể dẫn đến rủi ro vỡ nợ kỹ thuật, mất cơ hội đầu tư, hoặc tăng chi phí vốn do phải vay khẩn cấp. Truyền thống, các chuyên viên tài chính thường dự báo dòng tiền dựa trên bảng tính Excel với các luật kinh nghiệm (heuristics) hoặc trung bình trượt. Cách tiếp cận này tốn kém nguồn lực, dễ sai sót và không bắt được các mẫu hình (patterns) phức tạp mang tính mùa vụ, sự tương quan giữa các khoản phải thu (AR), khoản phải trả (AP) và các sự kiện lịch.

### 1.2. Mục tiêu nghiên cứu
Dự án hướng tới việc xây dựng một hệ thống dự báo dòng tiền hoàn toàn tự động, cụ thể:
1.  **Chính xác:** Giảm thiểu sai số dự báo (MAE/RMSE) so với các phương pháp thống kê truyền thống.
2.  **Khả năng giải thích (Explainability):** Xác định được các yếu tố (features) đóng góp lớn nhất vào sự biến động dòng tiền.
3.  **Tích hợp (Integration):** Đồng bộ mượt mà với hệ thống Data Warehouse hiện hữu, đảm bảo tính bất biến của dữ liệu dự báo để phục vụ Dashboard quản trị.

### 1.3. Phạm vi (Scope)
- **Mục tiêu dự báo:** Dòng tiền vào (Inflow) và Dòng tiền ra (Outflow) tổng hợp theo ngày.
- **Horizon dự báo:** Ngắn hạn (short-term), từ 7 đến 30 ngày tới (có thể điều chỉnh linh hoạt).
- **Dữ liệu:** Các giao dịch từ `fact_cashflow`, lịch đáo hạn hóa đơn từ hệ thống ERP (Kế toán).

---

## 2. PHƯƠNG PHÁP LUẬN (METHODOLOGY)

Dự án được triển khai qua 5 pha kiến trúc chuẩn xác, từ chuẩn bị dữ liệu đến đưa vào môi trường sản xuất (Production).

### 2.1. Pha 1: Chuẩn bị Dữ liệu (Data Preparation)
Dữ liệu thô (raw data) chứa nhiều yếu tố gây nhiễu, đặc biệt là các giao dịch điều chuyển nội bộ (Internal Transfers) không tạo ra dòng tiền thực tế cho doanh nghiệp. 
- **Khử nhiễu CTNB:** Loại bỏ các giao dịch luân chuyển giữa các tài khoản ngân hàng nội bộ và quỹ tiền mặt để phản ánh đúng dòng tiền thuần.
- **Tổng hợp (Aggregation):** Resample các giao dịch theo tần suất ngày (Daily) để tạo thành chuỗi thời gian đồng nhất.
- **Xử lý giá trị khuyết thiếu (Imputation):** Các ngày không có giao dịch được điền giá trị 0 (Zero-filling) để duy trì tính liên tục của chuỗi thời gian.

### 2.2. Pha 2: Trích xuất Đặc trưng (Feature Engineering)
Thay vì chỉ mô hình hóa tự hồi quy (Auto-regressive), hệ thống tạo ra một không gian đặc trưng đa chiều để cung cấp ngữ cảnh tối đa cho thuật toán Gradient Boosting:
- **Đặc trưng độ trễ (Lag Features):** Nắm bắt sự phụ thuộc tuyến tính vào các mốc thời gian quá khứ (Lag 1, Lag 7, Lag 30...).
- **Đặc trưng thống kê trượt (Rolling Window Statistics):** Trung bình trượt (Moving Average), độ lệch chuẩn (Rolling STD) theo các cửa sổ 7, 14, 30 ngày để làm phẳng nhiễu (smoothing) và nắm bắt xu hướng cục bộ (local trend).
- **Đặc trưng Lịch (Calendar Flags):** Trích xuất thứ trong tuần (Day of week), ngày trong tháng (Day of month), đánh dấu cuối tháng/cuối quý/ngày lễ - những thời điểm thường xuyên xảy ra các khoản thu/chi lớn như trả lương, nộp thuế.
- **Đặc trưng Nghiệp vụ (Business Features - Tiên tiến):** Tích hợp thông tin về hóa đơn đến hạn (AR/AP due amounts) trong các ngày tương lai, tạo ra động lực dự báo cực mạnh (forward-looking features).

### 2.3. Pha 3: Huấn luyện Mô hình & Tối ưu hóa (Model Training & Optimization)
- **Lựa chọn thuật toán:** Sử dụng **LightGBM**. Ưu điểm của LightGBM so với XGBoost là tốc độ huấn luyện nhanh, xử lý tốt với bộ dữ liệu dạng bảng có nhiều đặc trưng trễ (lag), ít gặp rủi ro quá khớp (overfitting) nhờ cơ chế kiểm soát số lượng lá (leaf-wise growth).
- **Chiến lược kiểm định:** Không sử dụng K-Fold CV tiêu chuẩn (do rò rỉ dữ liệu tương lai về quá khứ - Data Leakage). Thay vào đó, áp dụng **Walk-Forward TimeSeriesSplit**, mô phỏng chính xác cách mô hình sẽ được vận hành trong thực tế (huấn luyện trên cửa sổ trượt quá khứ, dự báo tương lai kế tiếp).
- **Tối ưu siêu tham số (Hyperparameter Tuning):** Sử dụng thư viện **Optuna** với thuật toán TPE (Tree-structured Parzen Estimator). Quá trình tìm kiếm duyệt qua hàng trăm cấu hình (learning_rate, num_leaves, feature_fraction) để tìm ra bộ trọng số tối ưu.
- **Hàm mất mát (Loss Function):** Sử dụng L1 (Mean Absolute Error) thay vì L2 (MSE) do dòng tiền thực tế có thể chứa nhiều giá trị ngoại lai (outliers - giao dịch đột biến), L1 giúp mô hình bền vững (robust) hơn.
- **Kiến trúc song song:** Xây dựng hai mô hình dự báo độc lập cho Dòng tiền vào (Inflow Model) và Dòng tiền ra (Outflow Model) do hai chuỗi này chịu chi phối bởi các yếu tố nghiệp vụ hoàn toàn khác nhau.

---

## 3. THỰC NGHIỆM VÀ KẾT QUẢ (EXPERIMENTS & RESULTS)

### 3.1. Đánh giá Mô hình (Evaluation)
Trong Pha 4, mô hình LightGBM tối ưu được kiểm tra đối đầu (benchmark) với 4 mô hình cơ sở (Baselines):
1. **Naive Forecast:** Giả định dòng tiền ngày mai bằng đúng ngày hôm nay.
2. **Seasonal Naive:** Giả định dòng tiền ngày mai bằng đúng ngày này tuần trước.
3. **MA-7:** Trung bình 7 ngày qua.
4. **MA-30:** Trung bình 30 ngày qua.

**Kết quả (Minh họa phân tích):** Mô hình LightGBM cho thấy sai số chuẩn hóa (MAPE) và MAE thấp hơn từ 25% đến 40% so với MA-7 và Seasonal Naive, đặc biệt tại các thời điểm dòng tiền đảo chiều (turning points). Sự vượt trội này đến từ việc mô hình học được mối quan hệ phi tuyến giữa các Calendar Flags và chuỗi thời gian.

### 3.2. Tính năng giải thích (Feature Importance)
Phân tích SHAP / Feature Importance từ LightGBM tiết lộ:
- Đặc trưng mang tính mùa vụ như "Ngày trong tháng" (Day of Month) có tầm ảnh hưởng lớn đối với Outflow (thường chi tiền vào các ngày cố định).
- Đặc trưng Rolling MA-7 và Lag-1 có tác động mạnh nhất đến sự biến động ngắn hạn của Inflow.

---

## 4. TRIỂN KHAI VÀ KHUYẾN NGHỊ (DEPLOYMENT & RECOMMENDATIONS)

### 4.1. Kiến trúc Hệ thống (Pha 5)
Hệ thống không chỉ dừng lại ở Jupyter Notebook mà được đóng gói thành thư viện chuẩn, tích hợp vào Data Pipeline của doanh nghiệp:
- **Lưu trữ CSDL:** Kết quả dự báo (predictions) được lưu vào bảng vật lý `gold.fact_cashflow_forecast`. Bảng này thiết kế chuyên dụng cho MLOps với các siêu dữ liệu (metadata): `run_id`, `as_of_date`, `model_version`. Điều này đảm bảo tính "Bất biến" (Immutable) – có thể truy xuất lại dự báo của bất kỳ thời điểm nào trong quá khứ để đối chiếu (Backtesting lịch sử).
- **Lớp hiển thị (Semantic View):** Tạo `gold.view_cashflow_actual_vs_forecast` thực hiện UNION ALL giữa dữ liệu thực tế và dữ liệu dự báo. View này trừu tượng hóa sự phức tạp, cho phép Power BI tiêu thụ trực tiếp mà không cần viết DAX phức tạp (chỉ cần kéo thả).

### 4.2. Khuyến nghị
1. **Theo dõi độ trôi mô hình (Model Drift):** Thiết lập cảnh báo tự động khi sai số MAE của mô hình vượt qua ngưỡng cho phép trong 7 ngày liên tiếp để kích hoạt quá trình huấn luyện lại (Retraining).
2. **Tích hợp API:** Trong tương lai, triển khai mô hình thành một Microservice (FastAPI/Flask) để hệ thống ERP có thể gọi (Call API) và nhận dự báo real-time khi có hóa đơn lớn vừa được ghi nhận.
3. **Bài toán Kế tiếp:** Áp dụng phương pháp tương tự (với chuỗi thời gian dài hạn hơn) để dự báo nhu cầu Hàng tồn kho (Inventory Forecasting) – Subproject 03.

---

## 5. KẾT LUẬN (CONCLUSION)
Dự án "Dự báo dòng tiền ngắn hạn" đánh dấu bước chuyển mình quan trọng của Gỗ Minh Long từ quản trị tài chính hồi tố (nhìn về quá khứ) sang **Quản trị tài chính chủ động (Forward-looking Management)**. Việc ứng dụng LightGBM và Optuna thay vì các phương pháp truyền thống đã giải quyết triệt để bài toán về tính chính xác và khả năng tự động hóa, là tiền đề vững chắc để phát triển các module Trí tuệ Nhân tạo khác trong hệ sinh thái Data Warehouse của doanh nghiệp.

---
**Tài liệu tham khảo (References):**
- *Kiến trúc Data Warehouse và Hệ thống Tài chính Kế toán MISA của Gỗ Minh Long.*
- *Etherlabs Reference Architecture for ML-driven Finance.*
- *Tài liệu kỹ thuật thư viện LightGBM (Microsoft) & Optuna (Preferred Networks).*
