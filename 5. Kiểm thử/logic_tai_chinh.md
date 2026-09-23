# Phân tích Logic Nghiệp vụ Tài chính Đặc thù (Custom Logic) - Khách hàng Minh Long

Tài liệu này giải thích sự khác biệt giữa Lý thuyết Tài chính Doanh nghiệp chuẩn và Yêu cầu nghiệp vụ đặc thù của Khách hàng Minh Long đối với các chỉ tiêu "Vòng quay" và "Số ngày".

---

## 1. Yêu cầu Nghiệp vụ Đặc thù của Khách hàng

Tại sheet `Target_Vong_Quay`, Khách hàng chỉ cung cấp một cột "NĂM 2026". Tuy nhiên, trái với nguyên tắc thông thường (giữ nguyên chỉ tiêu năm làm mốc), **Khách hàng đã yêu cầu phải phân bổ (chia đều) các chỉ số này cho 12 tháng**.

Mục đích:
*   Minh Long muốn tạo ra một **chỉ số Target tuyến tính theo tháng** (Monthly Performance Benchmark).
*   Ví dụ: Chu kỳ tiền mặt 123 ngày/năm -> 10.25 ngày/tháng. Khi đó, hiệu suất từng tháng sẽ được đem so sánh trực tiếp với mức chia nhỏ này để đánh giá xem tháng đó team đã đóng góp được bao nhiêu % vào tổng chu kỳ.

## 2. Đối chiếu với Lý thuyết Tài chính (Corporate Finance)

Việc chia 12 này là một **Custom Logic** (Logic tùy biến) phá vỡ nguyên lý Tài chính thông thường:
*   **Theo lý thuyết:** Các chỉ số Tỷ suất (Vòng quay, Chu kỳ) là Non-additive facts. Chúng đo lường tốc độ của cả chu kỳ, không thể cộng dồn hay chia cắt.
*   **Thực tế triển khai:** Tuy nhiên, trong xây dựng hệ thống báo cáo Quản trị Nội bộ, **Yêu cầu của Khách hàng là ưu tiên cao nhất**. Hệ thống Data Warehouse đã được tinh chỉnh (code ETL chia 12) để đáp ứng chính xác góc nhìn quản trị độc đáo này của Ban Lãnh đạo Minh Long.

## 3. Kết luận về luồng dữ liệu hiện tại
Logic Data Engineer áp dụng hàm chia 12 trong transformer `fact_business_plan.py` là **HOÀN TOÀN CHÍNH XÁC** và tuân thủ đúng yêu cầu của khách hàng đưa ra. Team DA khi kéo số liệu lên Power BI cần lưu ý áp dụng đúng logic phân bổ này cho các chart tháng.
