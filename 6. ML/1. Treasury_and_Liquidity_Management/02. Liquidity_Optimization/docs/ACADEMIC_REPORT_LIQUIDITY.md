# BÁO CÁO HỌC THUẬT: TỐI ƯU HÓA THANH KHOẢN QUA QUY HOẠCH TUYẾN TÍNH
**Định dạng:** Bài báo Học thuật chuẩn Scopus (Bản nháp)
**Từ khóa:** Tối ưu hóa Thanh khoản, Quy hoạch Tuyến tính, Quản trị Ngân quỹ, Doanh nghiệp vừa và nhỏ (SME), PuLP, Vay thế chấp sổ tiết kiệm

## Tóm tắt (Abstract)
Quản trị thanh khoản tại các Doanh nghiệp Vừa và Nhỏ (SME) ở các thị trường đang phát triển như Việt Nam bao hàm những ràng buộc đặc thù, chẳng hạn như việc sử dụng tài sản đảm bảo của cá nhân (sổ tiết kiệm) cho các khoản vay doanh nghiệp và sự khác biệt về chính sách tỷ lệ cho vay trên tài sản đảm bảo (LTV) giữa các ngân hàng. Nghiên cứu này đề xuất một Hệ thống Trí tuệ Ngân quỹ (Treasury Intelligence Engine) sử dụng Quy hoạch Tuyến tính (Linear Programming - LP) để tối ưu hóa việc phân bổ lượng tiền mặt nhàn rỗi và nhu cầu vay vốn. Bằng cách tích hợp các dự báo Machine Learning từ hệ thống thượng nguồn (Dự báo Dòng tiền, Rủi ro Công nợ, và Nhu cầu nhập hàng EOQ), bộ tối ưu hóa dựa trên thư viện PuLP giúp giảm thiểu tổng chi phí lãi vay. Kết quả thực nghiệm tại một doanh nghiệp sản xuất thực tế (Gỗ Minh Long) cho thấy sự sụt giảm đáng kể trong chi phí lãi vay bằng cách ưu tiên các khoản vay cầm cố sổ tiết kiệm (4.29% - 4.66%) thay vì các khoản vay tín chấp doanh nghiệp thông thường (7.0% - 8.5%), mang lại mức tiết kiệm ước tính hơn 300 triệu VNĐ mỗi năm cho một khoản thâm hụt thanh khoản 10 tỷ VNĐ.

---

## 1. Giới thiệu (Introduction)
Quản trị ngân quỹ hiệu quả đòi hỏi sự cân bằng giữa tính thanh khoản để đáp ứng nhu cầu vận hành và việc tối đa hóa tỷ suất sinh lời tài chính. Các phương pháp tiếp cận truyền thống thường dựa trên việc ra quyết định theo kinh nghiệm (heuristic), dẫn đến việc phân bổ vốn chưa tối ưu. Trong bài báo này, chúng tôi trình bày một Hệ thống Tối ưu hóa Thanh khoản tự động, giúp xác định chính xác số tiền cần vay hoặc gửi tại các ngân hàng cụ thể, có cân nhắc đến các ràng buộc thực tế như hạn mức tín dụng và sự chênh lệch lãi suất giữa khách hàng cá nhân và doanh nghiệp.

## 2. Tổng quan Tài liệu & Phân tích So sánh (Literature Review)
Mô hình đề xuất được đánh giá và so sánh với ba khung lý thuyết/thực tiễn hiện có:

1. **Mô hình Cash Sweeping của Tập đoàn FPT (2024):** 
   FPT sử dụng chiến lược gom dòng tiền tập trung để tối ưu hóa Tỷ suất sinh lời trên Tài sản (ROA) trên hơn 40 công ty con. Mặc dù rất hiệu quả đối với các tập đoàn lớn, mô hình này thiếu tính ứng dụng cho các SME, nơi dòng vốn thường xuyên luân chuyển chéo giữa cá nhân (Giám đốc) và pháp nhân doanh nghiệp. Mô hình của chúng tôi giới thiệu ràng buộc `Owner_Type` (Loại sở hữu) để giải quyết lỗ hổng này.
2. **Dự án Mã nguồn mở "Cash Liquidity Optimizer" (Trên nền tảng GitHub):** 
   Các kho mã nguồn mở hiện có sử dụng `PuLP` và `SciPy` để phân bổ vốn. Tuy nhiên, chúng giả định lãi suất là tĩnh. Hệ thống của chúng tôi thực hiện crawl (thu thập) dữ liệu thị trường động (`market_interest_rates.csv`) để nắm bắt các biến động hàng ngày của lãi suất cho vay và huy động.
3. **Nghiên cứu Sản xuất Việt Nam (UEH, 2026):** 
   Nghiên cứu gần đây từ Đại học Kinh tế TP.HCM đề xuất một mô hình lai ghép giữa XGBoost-LSTM kết hợp với LP. Chúng tôi áp dụng kiến trúc "Shift-Left" (Dịch trái) này bằng cách tách rời các module dự báo (Cashflow, AR, Inventory) khỏi bộ máy tối ưu hóa, và chỉ đưa luồng dữ liệu "sạch" đã qua xử lý vào bộ giải LP.

## 3. Phương pháp Nghiên cứu (Methodology)
Bài toán tối ưu hóa được công thức hóa dưới dạng mô hình Quy hoạch Tuyến tính Đa ràng buộc (Multi-Constraint LP) và được giải quyết thông qua thuật toán CBC trong thư viện Python `PuLP`.

**Hàm Mục Tiêu (Objective Function):**
$$ \text{Minimize } Z = \sum_{b} \left( X_{b}^{\text{Normal}} \cdot R_{b}^{\text{Normal}} + X_{b}^{\text{CashBacked}} \cdot R_{b}^{\text{CashBacked}} \right) $$

**Các Ràng Buộc (Constraints):**
1. *Yêu cầu Vốn:* $ \sum X_{b} = \text{Thâm hụt Tối đa (Max Deficit)} + \text{Vùng đệm An toàn (Safety Buffer)} $
2. *Giới hạn Hạn mức Tín dụng:* $ X_{b}^{\text{Normal}} \le \text{Hạn\_Mức\_Tổng}_{b} - \text{Dư\_Nợ\_Hiện\_Tại}_{b} $
3. *Giới hạn LTV Cầm cố:* $ X_{b}^{\text{CashBacked}} \le \text{Giá\_Trị\_Sổ\_Tiết\_Kiệm}_{b} \times \text{LTV}_{b} $

Dữ liệu đầu vào được trích xuất từ Kho Dữ liệu PostgreSQL (tầng Silver/Gold), đảm bảo rằng bộ tối ưu hóa xử lý các giá trị mang tính xác định cao thay vì dữ liệu giao dịch thô, nhiều nhiễu.

## 4. Kết quả Thực nghiệm (Empirical Results)
Hệ thống được thử nghiệm trên dữ liệu tài chính của Gỗ Minh Long cho tháng 07/2026. Công ty phải đối mặt với mức thâm hụt thanh khoản đỉnh điểm dự báo là 8 tỷ VNĐ, cùng với mức dự phòng an toàn yêu cầu là 2 tỷ VNĐ (Tổng mục tiêu: 10 tỷ VNĐ).

**Kết quả:**
- Bộ giải LP hội tụ trong thời gian $< 0.1$ giây.
- **Quyết định:** Thuật toán đã bỏ qua các khoản vay SME tiêu chuẩn (7.0% - 8.5%) và tận dụng tối đa các sổ tiết kiệm cá nhân hiện có tại BIDV và Techcombank làm tài sản đảm bảo.
- **Phân bổ chi tiết:** 
  - Vay 9.0 Tỷ VNĐ thế chấp bằng sổ BIDV (Lãi suất: 4.29%)
  - Vay 1.0 Tỷ VNĐ thế chấp bằng sổ Techcombank (Lãi suất: 4.66%)
- **Tác động Tài chính:** Tổng chi phí lãi vay hàng năm được tối ưu hóa xuống còn 432.7 triệu VNĐ, tương đương mức giảm $>40\%$ so với phương pháp vay theo kinh nghiệm truyền thống.

## 5. Kết luận & Khuyến nghị (Conclusion & Recommendations)
Hệ thống Tối ưu hóa Thanh khoản đã thành công trong việc toán học hóa các "luật ngầm" của ngân hàng Việt Nam (tỷ lệ LTV, bảo lãnh cá nhân) thành một ứng dụng Python mạnh mẽ và có khả năng mở rộng. Các nghiên cứu trong tương lai có thể mở rộng mô hình này thành Quy hoạch Tuyến tính Đa thời kỳ (Multi-Period LP), tối ưu hóa vốn trên đường chân trời cuộn 12 tuần để tính toán đến cấu trúc kỳ hạn và đường cong lợi suất.
