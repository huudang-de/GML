# BÁO CÁO DỰ ÁN: DỰ BÁO VÀ TỐI ƯU HÓA HÀNG TỒN KHO (INVENTORY DEMAND FORECASTING)
**Chuẩn báo cáo:** Mô hình SCOPE
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

## P - PREDICTORS & PIPELINE (ĐẶC TRƯNG & PHƯƠNG PHÁP TRIỂN KHAI)
Dự án được xây dựng trên một Pipeline End-to-End trải qua 7 Pha tuần tự, với trọng tâm là **LightGBM** (Global Model) thông qua nền tảng **Nixtla MLForecast**:

*   **Pha 1: Data Preparation:** Tập hợp và làm sạch chuỗi thời gian lịch sử xuất kho. Xử lý những ngày không có giao dịch (Zero-filling) và loại bỏ các nhiễu loạn cục bộ (Outlier Clipping bằng phương pháp IQR).
*   **Pha 2: Feature Engineering:** 
    *   *Lịch sử (Lag Features):* Trễ 1 ngày, 7 ngày, 14 ngày, 28 ngày.
    *   *Trượt (Rolling Windows):* Trung bình trượt (Rolling Mean) và Độ lệch chuẩn trượt (Rolling Std) để nắm bắt xu hướng (Trend) và độ biến động (Volatility).
    *   *Mùa vụ (Calendar Features):* Ngày trong tuần, Tháng trong năm.
*   **Pha 3: Demand Forecasting:** Mô hình LightGBM học chéo (Cross-learning) trên toàn bộ danh mục sản phẩm, xuất ra dự báo điểm (Point forecast) và dải tin cậy 95%.
*   **Pha 4: Inventory Optimization (Toán Chuỗi cung ứng):** 
    *   Quy đổi khoảng tin cậy thành độ lệch chuẩn ($\sigma$).
    *   Tính Tồn kho an toàn (Safety Stock).
    *   Tính Điểm báo động nhập hàng (ROP) và Sản lượng nhập kinh tế (EOQ).

## E - EVALUATION & EXECUTION (ĐÁNH GIÁ & TRIỂN KHAI)

### 1. Đánh giá Mô hình (Backtesting & Evaluation - Pha 5)
Mô hình không sử dụng K-Fold chéo truyền thống mà áp dụng **Walk-Forward Time-Series Cross Validation** nhằm đảm bảo không rò rỉ dữ liệu tương lai.
Kết quả cho thấy AI có khả năng thích ứng cao, hệ thống phân tách hiệu năng theo từng nhóm hàng (Category Metrics):
- Những nhóm có tính chu kỳ ổn định (Ví dụ: Giấy trang trí) đạt độ chính xác xuất sắc, Sai số phần trăm tuyệt đối trung bình (MAPE) dao động ở mức rất thấp (~2-3%).
- Hệ thống có khả năng tự động phát hiện và phát cảnh báo (Worst Performers Alert) với những mã hàng biến động dị biệt (Nẹp nhựa) để chuyển về chế độ quản lý thủ công.

### 2. Triển khai Thực tế (Integration - Pha 6 & 7)
- **MLflow Tracking:** Đảm bảo toàn bộ mã nguồn, siêu tham số (Hyperparameters) và độ lỗi được ghi nhận tự động để giám sát "sức khỏe" mô hình định kỳ (Tránh Model Drift).
- **Silver Layer (PostgreSQL):** Kết quả cuối cùng không nằm ở dạng log kỹ thuật mà được chuẩn hóa thành 2 bảng cơ sở dữ liệu:
  1. `silver.fact_inventory_forecast`: Theo dõi biến động dự báo hằng ngày.
  2. `silver.fact_reorder_recommendations`: Bản tin Mua hàng Khuyến nghị, đưa trực tiếp lên Power BI.

**Kết luận:** Dự án đã thay đổi hoàn toàn quy trình Mua hàng từ thế bị động, dựa trên cảm tính sang thế chủ động, dựa trên Xác suất thống kê (Data-driven). Giải pháp này giúp Gỗ Minh Long cắt giảm lượng vốn chết trong kho, đồng thời duy trì khả năng đáp ứng đơn hàng hoàn hảo.
