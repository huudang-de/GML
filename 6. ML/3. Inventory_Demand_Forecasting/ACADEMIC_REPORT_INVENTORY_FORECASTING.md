# BÁO CÁO HỌC THUẬT: ỨNG DỤNG MACHINE LEARNING TRONG DỰ BÁO VÀ TỐI ƯU HÓA HÀNG TỒN KHO TẠI GỖ MINH LONG

**Dự án:** Trí tuệ Nhân tạo & Quản trị Dữ liệu (AI & Data Management) - Gỗ Minh Long
**Phân hệ:** Supply Chain & Inventory Optimization
**Phiên bản mô hình:** v1.0.0 (Nixtla MLForecast + LightGBM + OR-Tools)
**Ngày lập:** Tháng 10/2026

---

## TÓM TẮT (ABSTRACT)
Quản trị hàng tồn kho (Inventory Management) luôn là bài toán đánh đổi cốt lõi giữa chi phí lưu trữ (Holding Cost) và mức độ đáp ứng dịch vụ (Service Level). Báo cáo này trình bày phương pháp luận và quá trình thiết kế hệ thống cảnh báo mua hàng thông minh tại Công ty Gỗ Minh Long. Bằng cách dịch chuyển từ mô hình dự báo chuỗi thời gian đơn lẻ sang kiến trúc học chéo (Cross-learning Global Model) bằng thuật toán LightGBM thông qua nền tảng Nixtla MLForecast, nghiên cứu đã khắc phục thành công yếu điểm của các phương pháp chuỗi thời gian truyền thống (như ARIMA). Hơn thế nữa, bài báo này chứng minh tính khả thi của việc tích hợp khoảng tin cậy (Confidence Intervals) thu được từ mô hình Học máy vào các phương trình toán học Chuỗi cung ứng cổ điển (Wilson EOQ và ROP) để định lượng Tồn kho an toàn (Safety Stock). Hệ thống đã đạt được độ chính xác dự báo cao (MAPE ~2-3% ở các mặt hàng tiêu chuẩn) thông qua kiểm định chéo Walk-Forward, đồng thời thiết lập luồng vận hành khép kín trực tiếp đến Power BI.

---

## 1. GIỚI THIỆU (INTRODUCTION)

### 1.1. Đặt vấn đề
Khoản mục Hàng tồn kho thường chiếm tỷ trọng khổng lồ trong tổng tài sản của Gỗ Minh Long. Phương pháp lập kế hoạch mua hàng truyền thống chủ yếu mang tính kinh nghiệm hoặc dựa trên các quy tắc tĩnh (Static Rules), dẫn đến Hiệu ứng cái roi da (Bullwhip effect) trong chuỗi cung ứng. Hậu quả là doanh nghiệp thường xuyên đối mặt với nghịch lý: Vừa đứt gãy sản xuất do thiếu hụt cục bộ (Stockout), lại vừa chôn vốn lưu động do trữ thừa mứa các mặt hàng sai lệch xu hướng (Overstock).

### 1.2. Mục tiêu nghiên cứu
Dự án hướng tới tự động hóa quyết định mua hàng (Data-driven Purchasing) với các tiêu chí:
1. **Dự báo chính xác (Accurate Forecasting):** Ước lượng nhu cầu xuất kho trong tương lai gần (7-14 ngày) dựa trên các biến trễ (Lag) và biến động trung bình (Rolling).
2. **Quản trị Rủi ro Tồn kho (Risk Quantification):** Trích xuất độ lệch chuẩn từ Dải tin cậy 95% để tính toán lượng Tồn kho an toàn (Safety Stock) một cách khoa học.
3. **Tối ưu hóa kinh tế (Economic Optimization):** Chuyển hóa kết quả của AI thành con số định lượng chính xác về Điểm đặt hàng lại (ROP) và Sản lượng nhập tối ưu (EOQ).

---

## 2. PHƯƠNG PHÁP NGHIÊN CỨU (METHODOLOGY)

### 2.1. Quy trình xử lý dữ liệu (Data Pipeline)
Dữ liệu xuất kho lịch sử được trích xuất từ Data Warehouse, qua quá trình xử lý đặc thù cho Chuỗi thời gian:
- **Zero-filling:** Điền dữ liệu bằng 0 cho những ngày không phát sinh giao dịch.
- **Outlier Clipping:** Áp dụng phương pháp khoảng tứ phân vị (IQR) cục bộ theo từng mã vật tư (SKU) để loại bỏ các đợt xuất/nhập kho bất thường.

### 2.2. Trích xuất đặc trưng (Feature Engineering)
Nghiên cứu sử dụng kỹ thuật tạo đặc trưng dạng bảng (Tabularization) cho chuỗi thời gian thông qua `Nixtla MLForecast`:
- Lịch sử tự tương quan (Lagged features): $t-1, t-7, t-14, t-28$.
- Khai phá xu hướng và biến động (Window transformations): Rolling Mean (Trung bình trượt) và Rolling Standard Deviation (Độ lệch chuẩn trượt).
- Yếu tố ngoại sinh (Exogenous variables) và Lịch (Calendar).

### 2.3. Mô hình dự báo (Forecasting Model)
Sử dụng **LightGBM** làm Global Model. Thay vì huấn luyện $N$ mô hình cho $N$ SKU, thuật toán học chung một mô hình duy nhất trên toàn bộ tập dữ liệu, giúp khai thác tối đa tính tương đồng trong hành vi tiêu thụ giữa các dòng sản phẩm.
Mô hình được cấu hình để sinh ra dự báo điểm (Point Forecast) cùng khoảng tin cậy (Confidence Intervals ở mức 95%).

### 2.4. Toán học Chuỗi cung ứng (Supply Chain Optimization)
Khoảng tin cậy thu được từ AI được giải mã ngược thành độ lệch chuẩn ($\sigma_{demand}$).
- Tồn kho an toàn (Safety Stock - SS) được tính bằng: $SS = Z \times \sigma_{demand} \times \sqrt{L}$ (với $L$ là Lead time, $Z$ là Z-score của Service Level 95%).
- Điểm tái đặt hàng (ROP) được tính bằng: $ROP = (D_{avg} \times L) + SS$.
- Lượng đặt hàng kinh tế (EOQ) được ước lượng bằng mô hình Wilson: $EOQ = \sqrt{\frac{2DS}{H}}$.

---

## 3. THỰC NGHIỆM VÀ KẾT QUẢ (EXPERIMENTS & RESULTS)

### 3.1. Thiết lập kiểm định (Backtesting Setup)
Nghiên cứu từ bỏ phương pháp K-Fold chéo truyền thống nhằm tránh lỗi rò rỉ dữ liệu tương lai (Data Leakage). Thay vào đó, kỹ thuật **Walk-Forward Time-Series Cross Validation** được áp dụng với nhiều lát cắt thời gian (Windows) để mô phỏng chính xác nhất khả năng dự báo trong thực tế.

### 3.2. Hiệu năng theo Nhóm hàng (Category Performance)
Kết quả thực nghiệm Backtesting chỉ ra sự khác biệt rõ rệt về năng lực dự báo giữa các nhóm hàng hóa:
- Nhóm Giấy trang trí (Tính ổn định cao): Đạt độ chính xác xuất sắc, chỉ số MAPE trung bình rất thấp (~2.26%).
- Nhóm Ván công nghiệp (Tính biến động trung bình): Mức độ lỗi MAPE ở biên độ hoàn toàn có thể chấp nhận để ứng dụng thực tiễn (~19.11%).
- Nhóm Nẹp nhựa (Tính đột biến cục bộ): Độ phân tán rất cao khiến lỗi MAPE nhảy vọt (>80%).
Dựa vào chỉ số này, hệ thống được thiết kế để tự động xuất cảnh báo "Worst Performers" nhằm yêu cầu sự can thiệp và phê duyệt của con người đối với các mặt hàng có độ nhiễu cao.

---

## 4. KẾT LUẬN VÀ KIẾN NGHỊ (CONCLUSION & RECOMMENDATIONS)

### 4.1. Kết luận
Nghiên cứu đã minh chứng được tính khả thi và hiệu quả của việc kết nối giữa Trí tuệ Nhân tạo (AI) và Toán học Chuỗi cung ứng. Bằng cách định lượng hóa rủi ro thành Tồn kho an toàn, điểm đặt hàng (ROP) và số lượng đặt hàng (EOQ) giờ đây là các tham số Động (Dynamic Parameters), liên tục tự thích nghi với nhịp đập của thị trường thay vì bị khóa chặt bởi kinh nghiệm chủ quan.

### 4.2. Kiến nghị
- **Tích hợp Hệ thống (Integration):** Bảng dữ liệu Khuyến nghị Mua hàng khẩn cấp (`silver.fact_reorder_recommendations`) đã hoàn thiện về mặt kiến trúc. Đề xuất nhanh chóng thiết kế Dashboard trên Power BI để Phòng Cung ứng có thể theo dõi hàng ngày (Daily Operation).
- **Cảnh báo Suy giảm chất lượng (Model Drift):** Đề xuất duy trì giám sát liên tục các siêu tham số và chỉ số lỗi trên nền tảng MLflow. Khi MAPE trên toàn hệ thống có dấu hiệu bứt phá khỏi đường cơ sở, cần kích hoạt quy trình tái huấn luyện (Retrain) mô hình tự động.
