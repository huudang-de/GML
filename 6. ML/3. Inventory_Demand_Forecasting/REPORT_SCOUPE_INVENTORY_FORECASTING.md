# BÁO CÁO DỰ ÁN: DỰ BÁO VÀ TỐI ƯU HÓA HÀNG TỒN KHO (INVENTORY DEMAND FORECASTING)
**Chuẩn báo cáo:** Mô hình SCOUPE (Situation - Complication - Objective - Utility - Predictors - Evaluation)
**Ngày lập:** 06/10/2026
**Đơn vị ứng dụng:** Công ty TNHH Gỗ Minh Long

---

## S - SITUATION (BỐI CẢNH DOANH NGHIỆP)
Công ty Gỗ Minh Long quản lý một lượng lớn các mã vật tư, ván công nghiệp và phụ kiện (SKU) với đặc thù nhu cầu tiêu thụ dao động mạnh theo từng tháng, mùa vụ và xu hướng của thị trường nội thất.
Trong môi trường chuỗi cung ứng truyền thống, việc lên kế hoạch mua hàng (Purchasing) chủ yếu dựa vào kinh nghiệm cảm tính của nhân viên hoặc sử dụng một tỷ lệ phần trăm tăng trưởng cố định. Điều này dẫn đến sự mất cân đối về luồng vốn.

## C - COMPLICATION (THÁCH THỨC & VẤN ĐỀ CỐT LÕI)
Việc thiếu vắng một công cụ định lượng khoa học tạo ra hai thách thức đối lập nhưng đều gây thiệt hại nghiêm trọng cho doanh nghiệp:
1. **Thiếu hụt hàng hóa (Stockout):** Dẫn đến đứt gãy chuỗi sản xuất, đánh mất cơ hội bán hàng và làm giảm mức độ hài lòng của khách hàng (Service Level).
2. **Dư thừa tồn kho (Overstock):** Khi nhân viên mua hàng "sợ" thiếu hàng, họ có xu hướng nhập quá nhiều (Hiệu ứng cái roi da - Bullwhip effect). Hàng tồn kho tăng làm chôn vốn lưu động, tăng chi phí lưu kho (Holding cost) và rủi ro suy giảm chất lượng vật tư.
**Câu hỏi cốt lõi:** Làm thế nào để biết chính xác *khi nào cần nhập hàng* và *nhập bao nhiêu là đủ* để tối đa hóa tỷ suất lợi nhuận trên vốn?

## O - OBJECTIVE (MỤC TIÊU DỰ ÁN)
Ứng dụng Trí tuệ Nhân tạo (Machine Learning) kết hợp với các Phương trình Toán học Chuỗi cung ứng nhằm xây dựng một hệ thống Tự động hóa Kế hoạch Mua hàng. Mục tiêu cụ thể:
1. Dự báo chính xác lượng tiêu thụ (Demand Forecasting) cho từng mã SKU trong tương lai gần (ví dụ: 7 đến 14 ngày tới).
2. Định lượng rủi ro bằng Khoảng tin cậy 95% (Confidence Intervals).
3. Đề xuất điểm đặt hàng lại (Reorder Point - ROP) và Lượng nhập hàng tối ưu kinh tế (EOQ) cho bộ phận Mua hàng.

## U - UTILITY (TIỆN ÍCH & GIÁ TRỊ ỨNG DỤNG THỰC TẾ)
Kết quả của mô hình Học máy được quy đổi trực tiếp thành các hành động kinh doanh (Actionable Insights) thông qua **Dashboard số 5 (ML Inventory Demand Forecasting & Reorder Optimization)** trên Power BI:
- **Tự động hóa quyết định:** Thay vì nhân viên Mua hàng phải tự mày mò số liệu quá khứ, mỗi sáng (08:00 AM) Dashboard sẽ tự động liệt kê danh sách các mã SKU cạn kho cần nhập gấp (dựa trên ROP).
- **Tối ưu hóa Chi phí:** Hệ thống đưa ra chính xác con số EOQ (Ví dụ: Nhập đúng 707 tấm ván) để đảm bảo chi phí lưu kho và chi phí vận chuyển đạt điểm cực tiểu.
- **Minh bạch Rủi ro:** Giám đốc Chuỗi cung ứng có thể nhìn thấy dải tin cậy của AI. Những mặt hàng có độ phân tán (Volatility) lớn sẽ tự động được cấp mức Tồn kho an toàn (Safety Stock) cao hơn để đề phòng.

## P - PREDICTORS & PIPELINE (ĐẶC TRƯNG & PHƯƠNG PHÁP TRIỂN KHAI)
Dự án được xây dựng trên một Pipeline End-to-End trải qua 7 Pha tuần tự, với trọng tâm là **LightGBM** (Global Model) thông qua nền tảng **Nixtla MLForecast**:
*   **Data Preparation:** Tập hợp và làm sạch chuỗi thời gian lịch sử xuất kho. Xử lý những ngày không có giao dịch (Zero-filling) và loại bỏ các nhiễu loạn cục bộ (Outlier Clipping bằng phương pháp IQR).
*   **Feature Engineering (Các Biến dự báo - Predictors):** 
    *   *Biến Lịch sử (Lag Features):* Trễ 1 ngày, 7 ngày, 14 ngày, 28 ngày.
    *   *Biến Trượt (Rolling Windows):* Trung bình trượt (Rolling Mean) và Độ lệch chuẩn trượt (Rolling Std) để nắm bắt xu hướng (Trend) và độ biến động (Volatility).
    *   *Biến Mùa vụ (Calendar Features):* Ngày trong tuần, Tháng trong năm.
*   **Demand Forecasting:** Mô hình LightGBM học chéo (Cross-learning) trên toàn bộ danh mục sản phẩm, xuất ra dự báo điểm (Point forecast) và dải tin cậy 95%.
*   **Inventory Optimization (Toán Chuỗi cung ứng):** Chuyển đổi dải tin cậy thành độ lệch chuẩn ($\sigma$), từ đó tính Safety Stock, ROP và EOQ.

## E - EVALUATION (ĐÁNH GIÁ & KIỂM ĐỊNH)
- **Đánh giá Mô hình (Backtesting):** 
  Mô hình áp dụng **Walk-Forward Time-Series Cross Validation** (Trượt theo thời gian thực tế) nhằm đảm bảo không rò rỉ dữ liệu.
  Kết quả phân tách hiệu năng theo nhóm (Category Metrics) cho thấy AI đạt độ chính xác xuất sắc ở các mặt hàng tiêu chuẩn (MAPE ~ 2-3%), và tự động phát cảnh báo ở các mặt hàng dị biệt (Nẹp) để con người can thiệp.
- **Giám sát Dài hạn (MLflow):** 
  Toàn bộ độ lỗi (MAE, RMSE, MAPE) và các siêu tham số (Hyperparameters) được Tracking trên hệ thống MLflow, giúp phát hiện sớm hiện tượng Model Drift nếu hành vi mua hàng của thị trường thay đổi trong tương lai.

**Kết luận:** Hệ thống AI Chuỗi cung ứng đã đóng gói thành công. Dữ liệu chạy mượt mà từ SQL -> Nixtla MLForecast -> Supply Chain Math -> Power BI (Silver Layer). Khép lại kỷ nguyên mua hàng bằng cảm tính tại Gỗ Minh Long.
