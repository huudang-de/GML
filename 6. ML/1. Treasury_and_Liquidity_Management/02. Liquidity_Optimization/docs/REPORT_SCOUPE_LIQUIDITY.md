# BÁO CÁO DỰ ÁN: AI BUSINESS ASSISTANT - LIQUIDITY OPTIMIZATION
**Ngày báo cáo:** Tháng 10/2026
**Tác giả:** Kỹ sư AI & Tài chính Gỗ Minh Long
**Phương pháp:** Báo cáo theo chuẩn SCOUPE (Situation - Complication - Objective - Utility - Predictors/Optimizer - Evaluation)

---

## 1. SITUATION (Tình huống)
Công ty TNHH Gỗ Minh Long thường xuyên đối mặt với trạng thái **"thừa thiếu tiền đan xen"**.
- Có những tuần công ty dư dả hàng chục tỷ đồng nhưng để "nằm chết" trên tài khoản thanh toán không sinh lãi.
- Ngược lại, có tuần đột xuất hụt dòng tiền (do khách hàng trả chậm hoặc phải nhập hàng nguyên vật liệu EOQ khẩn cấp), kế toán cuống cuồng đi vay tín chấp với lãi suất rất cao (7 - 8.5%/năm).

## 2. COMPLICATION (Điểm nghẽn/Trở ngại)
Bài toán vay và gửi tiền không đơn giản chỉ là "thấy thiếu thì vay". Nó bị ràng buộc bởi hàng vạn "luật ngầm" của ngân hàng thương mại Việt Nam:
- **Khác biệt Lãi suất:** Techcombank có thể cho vay tín chấp 8.5%, nhưng nếu thế chấp bằng Sổ tiết kiệm của sếp (Cash-backed loan), lãi vay chỉ còn 4.6%.
- **Hạn mức Tín dụng (Credit Line):** Ngân hàng VietinBank duyệt hạn mức 30 tỷ nhưng công ty đã vay 29 tỷ, nên chỉ còn room vay thêm 1 tỷ.
- **Con người:** Kế toán trưởng không thể dùng Excel để dò tìm 6 ngân hàng khác nhau mỗi ngày xem nên rút sổ nào, vay ở đâu thì có lợi nhất. Họ thường chỉ "vay chỗ quen", gây thất thoát hàng trăm triệu tiền chênh lệch lãi suất mỗi năm.

## 3. OBJECTIVE (Mục tiêu Dự án)
Xây dựng một **Treasury Intelligence Engine (Công cụ Tối ưu hóa Ngân quỹ)** tự động nhận diện thời điểm hụt dòng tiền (lấy từ các dự án AI Upstream) và đề xuất chính xác nên vay/gửi ở ngân hàng nào, dùng hình thức gì để **Tối thiểu hóa chi phí lãi vay** và **Tối đa hóa tiền lãi nhận được**.

## 4. UTILITY (Tính Ứng dụng)
- **Hệ thống Shift-Left:** Engine này nằm ở Layer cuối cùng, tiêu thụ toàn bộ "tinh hoa" của 3 dự án AI đi trước (Dự báo Dòng tiền, Phân loại Rủi ro Công nợ, Dự báo Tồn kho).
- Giao diện đầu ra được đẩy thẳng vào **Power BI** dưới dạng các thông điệp chỉ định rành mạch cho CFO: *"Hôm nay cầm cố sổ BIDV 9 tỷ, sổ Techcombank 1 tỷ, không vay tín chấp"*.

## 5. PREDICTORS / OPTIMIZER (Mô hình Toán học)
Thay vì sử dụng Machine Learning hay Deep Learning, bài toán này áp dụng **Quy hoạch tuyến tính (Linear Programming - LP)** sử dụng thư viện `PuLP` (Thuật toán Simplex/CBC).

**Biến Quyết Định (Decision Variables):**
- Tiền vay Tín chấp/BĐS ($Vay\_Tieu\_Chuan$)
- Tiền vay Cầm cố sổ tiết kiệm ($Vay\_Cam\_Co$)

**Hàm Mục Tiêu (Objective):**
- Minimize(Tổng Lãi Vay Phải Trả)

**Hệ thống 3 Ràng Buộc Cốt Lõi (Constraints):**
1. Tổng tiền vay = 10,000,000,000 VND (8 tỷ hụt dòng tiền + 2 tỷ Buffer an toàn).
2. $Vay\_Tieu\_Chuan \le Han\_Muc\_Kha\_Dung$ (Từ file `bc_tin_dung_2026.xlsx`).
3. $Vay\_Cam\_Co \le Gia\_Tri\_So\_Tiet\_Kiem \times LTV (90-95\%)$ (Từ file `Hop_dong_tien_gui.xlsm`).

## 6. EVALUATION (Đánh giá Hiệu quả)
**Kết quả chạy thử nghiệm tháng 07/2026:**
Trong bối cảnh công ty bị thâm hụt 8 tỷ đồng dòng tiền, và cần thêm 2 tỷ đồng dự phòng (Tổng cần gọi vốn = 10 tỷ):

- **Hành vi cũ (Không có AI):** Kế toán sẽ vay tín chấp tại VietinBank (7.0%) hoặc Techcombank (8.5%). Tổng chi phí lãi vay 1 năm cho 10 tỷ này dao động từ **700 - 850 triệu đồng**.
- **Hành vi mới (Có AI LP Optimizer):** Thuật toán PuLP phát hiện ra GML đang có sẵn các Sổ tiết kiệm của các cá nhân ủy quyền tại BIDV và Techcombank. AI ra quyết định:
  - Vay cầm cố Sổ tiết kiệm BIDV: **9.0 Tỷ VNĐ** (Lãi suất cực rẻ: ~4.29%).
  - Vay cầm cố Sổ tiết kiệm Techcombank: **1.0 Tỷ VNĐ** (Lãi suất ~4.66%).

=> **Tổng chi phí lãi vay ước tính:** Giảm mạnh chỉ còn **432.7 Triệu VNĐ/Năm**.
=> **ROI của AI:** Giúp công ty tiết kiệm trực tiếp hơn **300 Triệu VNĐ** chi phí tài chính chỉ trong 1 quyết định phân bổ vốn đơn giản.
=> Hệ thống đã sinh thành công file `silver.fact_liquidity_actions.csv` để Power BI hiển thị.

---
**TỔNG KẾT:** Dự án 02 đã hoàn thiện hệ sinh thái AI Treasury của Gỗ Minh Long. Bằng việc số hóa toàn bộ Hạn mức và Lãi suất, AI đã đóng vai trò như một vị Giám đốc Tài chính (CFO) với khả năng tính nhẩm ma trận lãi suất siêu tốc.
