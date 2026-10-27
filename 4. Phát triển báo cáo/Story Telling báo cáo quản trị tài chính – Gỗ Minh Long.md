# Story Telling báo cáo quản trị tài chính – Công ty Gỗ Minh Long

*Dự án báo cáo & phân tích kinh doanh trên Power BI · Căn cứ: BRD “ISO – BRD Final” (5 báo cáo) và 5 bộ SQL UAT · Mốc số liệu UAT: 31/07/2026 · Đơn vị: tỷ đồng (VNĐ) nếu không ghi khác*

## 1. Mục đích và cách đọc tài liệu

Tài liệu này biến 5 dashboard thành câu chuyện quản trị. Với mỗi chỉ số, câu chuyện phải trả lời ba câu hỏi theo thứ tự: (1) chỉ số đo điều gì và vì sao Ban điều hành phải quan tâm; (2) con số hiện tại cho thấy điều gì; (3) nếu chỉ số vượt ngưỡng thì ai quyết định việc gì. Mỗi dashboard được kể theo cấu trúc bối cảnh – xung đột – hành động (Knaflic, 2015); bộ chỉ số được chọn để nhìn doanh nghiệp từ nhiều góc (tài chính, vận hành) thay vì một con số đơn lẻ (Kaplan & Norton, 1992); bố cục đi từ thẻ tổng quan xuống biểu đồ rồi bảng chi tiết để người xem nắm bức tranh chung trong vài giây (Few, 2013).

**Quy ước dùng trong tài liệu**

- **Số UAT**: lấy nguyên từ phần RESULT LOG của 5 file SQL.
- **Suy ra**: do người viết tính ngược từ số UAT, có ghi phép tính; phải đối chiếu số gốc trên MISA trước khi trình Ban điều hành.
- **Ngưỡng BRD**: LTV > 80%; runway < 3 tháng; dư nợ vượt hạn mức; Interest coverage < 1,5; chênh lệch kế hoạch ±5%; nợ quá hạn 60 ngày tô đỏ; nhóm tuổi nợ 180+ ngày tô đỏ.
- **Ngưỡng tham chiếu / đề xuất**: lấy từ giáo trình hoặc do người viết đề xuất, chỉ là điểm xuất phát, cần hiệu chỉnh theo đặc thù ngành gỗ – nội thất.
- Nhịp sử dụng theo BRD: hằng tuần, xem vào thứ Bảy, số liệu chốt hết thứ Sáu. Người yêu cầu: chuyên viên Tài chính (Mai Lan). Người thụ hưởng: Công ty Gỗ Minh Long.

## 2. Đọc trước khi trình bày: 12 điều kiện dữ liệu ảnh hưởng đến “câu chuyện”

Một câu chuyện đúng phải bắt đầu từ số đúng. Qua UAT, có 12 hiện tượng không làm hỏng khung phân tích nhưng quyết định con số nào được phép đưa vào phòng họp. Ở các phần sau, mọi nhận định dựa trên những số này đều được ghi rõ mức độ chắc chắn.

| # | Hiện tượng | Bằng chứng trong UAT | Ảnh hưởng tới câu chuyện | Cách xử lý |
| --- | --- | --- | --- | --- |
| 1 | Giá vốn và chi phí lãi vay thực tế bằng 0 | B02-DN\_11 và B02-DN\_23 = 0 nên vòng quay HTK = 0; biên LN gộp = 100%; EBITDA/Doanh thu = 207%; EBIT/lãi vay = None; Cost of Debt = 0 | Chưa kể được chuyện lợi nhuận và chi phí vốn | Nạp đủ B02-DN tháng 1–7; tạm dùng chỉ số thay thế có ghi chú (giá trị xuất kho làm giá vốn tạm) |
| 2 | Doanh thu chỉ có tháng 7 | Vòng quay phải thu “cả năm” = “hiện tại” = 2,064; doanh thu suy ra ≈ 75,0 (2,064 × 36,3) | Nhãn “YTD” sai nghĩa | Nạp doanh thu T1–T6 hoặc đổi nhãn thành “tháng 7” |
| 3 | Thiếu số dư năm 2025 | Bình quân đầu–cuối kỳ thành số cuối kỳ ÷ 2: vòng quay VLĐ 0,60 = 75,0 ÷ (248,4 ÷ 2); ROE 40,7%, ROA 14,8% bị phóng đại gấp đôi | Không so sánh được ROE, ROA, vòng quay | Nạp B01 ngày 31/07/2025, hoặc dùng số cuối kỳ và ghi chú |
| 4 | Tháng 8/2026 chưa có số | Tồn kho T8 giống hệt T7 (673.125,42 và 341,69); dòng tiền T8 chỉ 2,7 triệu; phải thu T8 hiển thị 100% quá hạn | Điểm cuối biểu đồ chuỗi thời gian sai | Slicer mặc định = tháng đã khóa sổ gần nhất (T7) |
| 5 | Thiếu snapshot tồn kho T1–T6 | “Tồn cuối kỳ” T1–T6 = 0 dù nhập – xuất vẫn phát sinh | Biểu đồ trạng thái Inventory đứt đoạn | Nạp Tổng hợp tồn kho theo từng tháng |
| 6 | DSO/DIO/DPO dùng 365 ngày nhưng tử số chỉ 1 tháng | DSO hiển thị 55,4 ngày = 12 × 4,6 ngày | CCC sai hệ số 12 | Nhân số ngày trong kỳ (30/31) hoặc quy năm hóa doanh thu, giá vốn |
| 7 | Bốn con số “phải thu” khác nhau | 36,3 (thẻ) · 23,7 (biểu đồ T7) · 36,6 (Aging) · 11,4 (suy ra từ DSO trong CCC) | Ban điều hành hỏi “phải thu thật là bao nhiêu?” | Thống nhất một định nghĩa và một bảng số dư theo khách hàng |
| 8 | Top 10 nợ quá hạn không hợp lệ | Tỷ lệ quá hạn 947%, −298%…; nhiều khách có số dư Có (âm) hàng chục tỷ | Danh sách khách rủi ro không đáng tin | Dùng phân bổ FIFO như biểu đồ Aging; tách số dư Có (người mua trả tiền trước) |
| 9 | Tiền gửi “còn hiệu lực” chưa chặt | Hợp đồng HD đáo hạn 2025 nhưng chưa tất toán vẫn được tính; cột kỳ hạn không khớp ngày (kỳ hạn 6 tháng nhưng đáo hạn sau 1 tháng) | 40,5 tỷ có thể tính dư | Bổ sung trạng thái tái tục / đã tất toán |
| 10 | Mã ngân hàng không đồng nhất | SCB (khoản vay) và Sacombank (tài khoản thanh toán); TP/TPBank, VP/VPBank, HD/HDBank | Không ghép được vay – gửi – thu chi cùng một ngân hàng | Chuẩn hóa dim\_bank |
| 11 | Cơ cấu thu/chi ở Dashboard 1 gộp cả dòng tổng hợp | “Tiền Việt Nam” 635,8; “Tiền gửi không kỳ hạn” 646,4; “Tiền mặt” 438,2… xuất hiện cùng từng tài khoản ngân hàng | Đếm trùng | Dùng cách của Dashboard 5 (ghép dim\_account với dim\_accountnumber) |
| 12 | Một số công thức cần rà soát | “Debt/Equity” thực chất là Nợ phải trả ÷ Tổng nguồn vốn; EBITDA cộng số dư hao mòn lũy kế (B01) thay vì khấu hao phát sinh trong kỳ (B01-228 theo mẫu B01-DN còn là nguyên giá TSCĐ vô hình, cần đối chiếu mẫu biểu); Nợ/EBITDA âm vì tử số dùng lũy kế phát sinh (Có – Nợ); B01-330 = 0 trong khi TK 34112 = 51,2 | EBITDA và Nợ/EBITDA chưa dùng được | Dùng khấu hao trong kỳ; dùng số dư TK 341 (290,98); ánh xạ lại phân loại ngắn/dài hạn |

## 3. Mạch kể xuyên suốt: hành trình của một đồng vốn

Vốn lưu động quay vòng theo chu kỳ tiền → hàng tồn kho → phải thu → tiền. Độ dài chu kỳ chuyển đổi tiền mặt (CCC) bằng số ngày tồn kho cộng số ngày phải thu trừ số ngày phải trả (Richards & Laughlin, 1980). Chu kỳ càng dài, doanh nghiệp càng phải vay để lấp khoảng trống (Brigham & Ehrhardt, 2017). Vì vậy 5 dashboard không phải 5 báo cáo rời nhau mà là 5 chương của cùng một câu chuyện.

| Chương | Dashboard | Câu hỏi của chương | Con số nối sang chương sau (UAT, T7/2026) |
| --- | --- | --- | --- |
| 1. Nguồn vốn | Quản trị hoạt động tài chính | Vốn vay từ đâu, giá bao nhiêu, còn dư địa không? | Dư nợ 291,0; lãi suất bình quân ≈ 8,3%; hạn mức còn 24,1 |
| 2. Vốn nằm ở đâu | Quản trị hàng tồn kho | Bao nhiêu vốn đang nằm trong kho, hàng nào, bao lâu? | HTK 341,7 ≈ 4,6 tháng doanh thu |
| 3. Vốn đi theo hóa đơn | Quản trị phải thu – phải trả | Ai đang giữ tiền của ta, ta đang giữ tiền của ai? | Phải thu 36,3; phải trả 60,5 |
| 4. Vốn trở về | Quản trị dòng tiền | Tiền vào – ra có cân bằng, có đủ cho tuần tới? | Vào 2.377,3; ra 2.302,6; ròng +74,6 (T1–T7) |
| 5. Vốn đệm an toàn | Quản trị tiền gửi & thanh khoản | Đệm thanh khoản có đủ và có hiệu quả? | Tiền 92,0; gửi kỳ hạn 40,5 lãi 4,99% |

**Thông điệp tổng thể: “Vay đắt – gửi rẻ – tồn nhiều”.**

- **Vay đắt**: lãi vay ≈ 8,3%/năm (khoảng 7,0–8,75% tùy ngân hàng) trên 270,9 dư nợ ngân hàng; đã dùng 91,8% hạn mức được cấp.
- **Gửi rẻ**: 40,5 tiền gửi kỳ hạn chỉ sinh lãi bình quân 4,99%, thấp hơn lãi vay ≈ 3,3 điểm % → chi phí chênh lệch khoảng 1,3/năm (40,5 × 3,3%).
- **Tồn nhiều**: HTK 341,7 bằng 117% dư nợ vay; vốn lưu động ròng từ thương mại (HTK + phải thu − phải trả = 341,7 + 36,3 − 60,5 ≈ 317,6) bằng khoảng 109% dư nợ vay. Nói cách khác, ngân hàng đang tài trợ gần như toàn bộ chu kỳ tiền mặt.

**Thứ tự đọc 15 phút vào thứ Bảy**: Dòng tiền (tuần qua có đủ tiền không) → Tiền gửi & thanh khoản (đệm còn bao nhiêu ngày) → Hoạt động tài chính (nợ, hạn mức, lịch trả gốc) → Phải thu – phải trả (ai chưa trả) → Tồn kho (hàng nào nằm lâu). Lý do: thanh khoản là ràng buộc cứng nhất trong ngắn hạn, còn tồn kho là đòn bẩy cải thiện lớn nhất trong trung hạn.

## 4. Dashboard 1 – Quản trị hoạt động tài chính: “Vốn đến từ đâu, giá bao nhiêu, còn dư địa không?”

### 4.1 Câu hỏi quản trị

Ban điều hành cần trả lời sáu câu: nợ bao nhiêu và đến hạn khi nào; vay của ai, giá bao nhiêu; còn vay thêm được bao nhiêu; tài sản bảo đảm đủ không; lãi vay thực tế có vượt kế hoạch không; các chỉ số sức khỏe tài chính (thanh khoản, đòn bẩy, khả năng trả lãi) có chạm ngưỡng không.

### 4.2 Cơ sở lý thuyết

- **Cấu trúc vốn**: Modigliani và Miller (1958) chứng minh trong thị trường hoàn hảo, giá trị doanh nghiệp không phụ thuộc tỷ lệ nợ; khi có thuế và chi phí kiệt quệ tài chính thì tồn tại mức nợ hợp lý (lý thuyết đánh đổi) (Brealey et al., 2020). Hàm ý: không có “D/E đúng” tuyệt đối, phải đọc D/E cùng khả năng trả lãi.
- **Khả năng trả lãi**: Times interest earned = EBIT ÷ lãi vay; có thể dùng EBITDA ÷ lãi vay và Nợ ÷ EBITDA (Ross et al., 2019). BRD đặt ngưỡng cảnh báo 1,5.
- **Hạn chế tín dụng**: do thông tin bất cân xứng, ngân hàng thường giới hạn hạn mức thay vì chỉ tăng lãi suất (Stiglitz & Weiss, 1981). Vì vậy hạn mức còn lại và tài sản bảo đảm là nguồn lực chiến lược, không chỉ là con số kế toán.
- **Khớp kỳ hạn**: nợ ngắn hạn tài trợ tài sản ngắn hạn, nợ dài hạn tài trợ tài sản dài hạn (Brigham & Ehrhardt, 2017).
- **DuPont**: ROE = biên lợi nhuận × vòng quay tổng tài sản × đòn bẩy tài chính (Brigham & Ehrhardt, 2017), cho thấy đòn bẩy làm tăng ROE nhưng cũng tăng rủi ro.

### 4.3 Bối cảnh pháp lý – kế toán Việt Nam

- **Chế độ kế toán**: Thông tư 200/2014/TT-BTC quy định TK 341 phản ánh vay và nợ thuê tài chính; chi phí lãi vay ghi vào chi phí tài chính (TK 635) và lên Báo cáo B02-DN ở mã 23. Báo cáo B01-DN dùng các mã 100 (tài sản ngắn hạn), 140 (hàng tồn kho), 300/310/330 (nợ phải trả, ngắn hạn, dài hạn), 400 (vốn chủ sở hữu), 440 (tổng nguồn vốn). Các tiểu khoản 34111–34114 là danh mục riêng của Minh Long (BRD: 34111, 34113, 34114 là ngắn hạn; 34112 là dài hạn).
- **Thuế**: Nghị định 132/2020/NĐ-CP khống chế chi phí lãi vay được trừ khi tính thuế ở mức 30% EBITDA đối với đối tượng thuộc phạm vi áp dụng (doanh nghiệp có giao dịch liên kết). Nếu Minh Long thuộc diện này, cần thêm chỉ tiêu “Chi phí lãi vay ÷ EBITDA” với ngưỡng 30%; phần lãi vượt trần bị loại khỏi chi phí được trừ, làm tăng thuế phải nộp.
- **Bảo đảm tín dụng**: Bộ luật Dân sự 2015 và Nghị định 21/2021/NĐ-CP cho phép bảo đảm nghĩa vụ bằng bất động sản, động sản, tiền gửi, hàng tồn kho…; bảng TSĐB (BĐS, MMTB, PTVT, HTK, hợp đồng tiền gửi) phản ánh đúng các loại tài sản này, kèm hệ số tài sản bảo đảm từ 0,5 đến 1,0.

### 4.4 Đọc từng chỉ số: ý nghĩa – insight – quyết định

| Chỉ số (BRD) | Số UAT | Ý nghĩa | Insight | Quyết định gợi ý |
| --- | --- | --- | --- | --- |
| Dư nợ ngắn hạn / dài hạn (1.1, 1.2, 2.1) | 236,1 / 51,2; tổng TK 341 = 291,0 | Số dư vay phải trả, tách theo kỳ hạn; là nghĩa vụ mà dòng tiền phải gánh | T1→T6 tổng nợ tăng 314,7 → 350,1 (+11,2%), nợ dài hạn tăng 21,6 → 52,3 (×2,4) nên tỷ trọng ngắn hạn giảm 91,8% → 84,0%. T7 tổng nợ giảm 59,2 (−16,9%), gần hết ở nợ ngắn hạn (−58,1) | Xác nhận 59,2 là trả nợ thật (đối chiếu dòng chi có đối ứng 341 ở Dashboard 5); nếu thật, quyết định có vay lại ngay không; giữ nguyên tắc nợ dài hạn tài trợ tài sản dài hạn |
| Hạn mức phê duyệt – được cấp – còn lại (1.3–1.5) | 485,0 – 295,0 – 24,1 | Phê duyệt = khung ngân hàng chấp thuận; được cấp (HMTD) = phần đã ký dùng được; còn lại = được cấp − dư nợ gốc | Dư nợ gốc theo ngân hàng cộng lại 270,9 = 295,0 − 24,1 (khớp). Đã dùng 91,8% hạn mức được cấp; 190,0 (39,2%) hạn mức phê duyệt chưa được cấp | Còn 24,1 (≈ 2,2 ngày chi tiêu gộp, xem Dashboard 5) → chủ động đàm phán nâng HMTD. Đề xuất ngưỡng nội bộ: còn lại < 10% vàng, < 5% đỏ |
| Loan to Value (1.6) | 71,3% | Tổng HMTD ÷ giá trị thẩm định TSĐB; càng cao càng ít dư địa vay thêm | Giá trị thẩm định suy ra ≈ 413,8 (295,0 ÷ 0,7129). Ngưỡng 80% tương ứng HMTD tối đa ≈ 331,0 → dư địa ≈ 36,0 | Muốn tăng hạn mức quá 36 phải bổ sung TSĐB. Thêm chỉ tiêu LTV sau hệ số (theo giá trị cho vay) vì MMTB chỉ được tính 50%, HTK 70% |
| Debt/Equity (1.7) | 0,636 | BRD định nghĩa = Nợ phải trả ÷ Tổng nguồn vốn (B01-300 ÷ B01-440): tỷ trọng nợ trong nguồn vốn | Suy ra: nợ ngắn hạn ≈ 248,35 ÷ (1,3861 − 1) = 643,1; B01-330 = 0 nên nợ phải trả ≈ 643,1; tổng nguồn vốn ≈ 643,1 ÷ 0,6358 ≈ 1.011,5; VCSH ≈ 368,4. D/E đúng nghĩa (nợ phải trả ÷ VCSH) ≈ 1,75; nợ vay ÷ VCSH ≈ 0,79 (290,98 ÷ 368,4) | Đổi tên thành “Nợ phải trả/Tổng nguồn vốn” và bổ sung D/E; đối chiếu điều khoản tài chính trong hợp đồng tín dụng (nếu có) |
| Dư nợ theo ngân hàng (3.2) | MB 90,0; IVB 73,7; SCB 31,8; TP 26,7; Woori 24,0; HD 14,7; VP 10,0 (tổng 270,9) | Mức tập trung nguồn vốn vay | MB + IVB = 60,4%; HHI ≈ 2.200/10.000 (tập trung cao). Woori lãi thấp nhất (7,0%) nhưng chỉ 8,9% dư nợ | Khi tái cấp, ưu tiên chuyển dư nợ sang ngân hàng lãi thấp; đề xuất trần tập trung nội bộ ≤ 30%/ngân hàng |
| Lãi suất bình quân ngắn hạn theo ngân hàng (2.3) | 7,0% (Woori) – 8,75% (HDBank); trung bình giản đơn 8,2%; bình quân theo dư nợ ≈ 8,3% (suy ra) | Giá vốn vay; so với lãi tiền gửi 4,99% | Chênh HD − Woori 1,75 điểm % ≈ 0,26/năm trên 14,7 dư nợ HD (14,7 × 1,75%) | Ưu tiên hoàn trả khoản lãi cao nhất khi có tiền nhàn rỗi; đưa lãi suất bình quân gia quyền vào thẻ thay cho trung bình giản đơn |
| Chi phí lãi vay thực tế vs kế hoạch; Interest YTD; Cost of Debt (2.2, 2.4, 2.5) | Thực tế = 0 (chưa nạp); kế hoạch cả năm 31,6, riêng T1–T7 = 14,2 | Kiểm soát giá vốn vay. Cost of Debt = lãi vay ÷ dư nợ, phải quy năm | Ước tính (suy ra): dư nợ bình quân T1–T7 ≈ 330,9 × 8,3% × 7/12 ≈ 16,0 → vượt kế hoạch khoảng 12–13%. Kế hoạch ngầm định chi phí vốn ≈ 9,6% (31,6 ÷ 330,9) | Nạp số thực tế; nếu vượt kế hoạch > 5%, giao Tài chính đề xuất phương án đàm phán lãi suất hoặc tái cơ cấu; theo dõi trần 30% EBITDA nếu thuộc diện NĐ 132/2020 |
| Lịch trả gốc (3.5) | Các khoản đáo hạn theo ngày (trích log: nhiều khoản tháng 5/2026 vẫn còn dư gốc > 0) | Cho biết tuần nào phải có tiền trả gốc | Khoản có ngày đáo hạn đã qua nhưng dư gốc > 0 cần xác nhận là gia hạn hay quá hạn | Chốt lịch 4 tuần tới mỗi thứ Bảy, đặt cạnh số dư tiền ở Dashboard 5 |
| Chi tiết tài sản đảm bảo (2.7) | BĐS, MMTB, PTVT, HTK, hợp đồng tiền gửi…; hệ số 0,5–1,0 | Sức mạnh bảo đảm của hạn mức | HTK thẩm định 53,5 × 0,7 = 37,5 giá trị cho vay, chỉ khoảng 15,7% hàng tồn 341,7 | Cân nhắc đưa thêm hàng tồn kho đạt chuẩn vào TSĐB thay vì bổ sung BĐS, kèm cơ chế kiểm kê định kỳ |

### 4.5 Bảng 18 chỉ số tài chính: dùng được hay chưa?

| Nhóm | Chỉ số và kết quả UAT | Kết luận |
| --- | --- | --- |
| Dùng được | Khả năng thanh toán hiện hành 1,39 (tham chiếu 1,2–2,0); thanh toán nhanh 0,86; Nợ phải trả/Tổng nguồn vốn 63,6% | Thanh toán nhanh < 1 nghĩa là nếu không bán được hàng tồn kho thì không đủ tài sản ngắn hạn khác để trả nợ ngắn hạn (suy ra: nợ ngắn hạn ≈ 643,1, tài sản ngắn hạn ≈ 891,5) |
| Chưa dùng (thiếu dữ liệu) | Vòng quay VLĐ 0,60; vòng quay HTK 0; vòng quay phải thu 0,39; Nợ dài hạn/VCSH 0; ROE 40,7%; ROA 14,8% | Do thiếu năm 2025, giá vốn = 0, B01-330 = 0 (điều kiện 1, 3, 12) |
| Chưa dùng (sai công thức) | EBITDA 155,4; EBIT 75,0; Biên LN gộp 100%; Biên EBITDA 207%; Nợ/EBITDA −0,58 | Điều kiện 1 và 12 |
| Chưa tính được | EBIT/lãi vay; EBITDA/lãi vay | Lãi vay thực tế = 0 nên mẫu số bằng 0; chỉ tiêu cảnh báo “Interest coverage < 1,5” của BRD hiện ở trạng thái N/A |

### 4.6 Mạch kể 3 hồi (khoảng 5 phút)

- **Hồi 1 – Bối cảnh**: “Dư nợ đang là 291,0, vừa giảm 59,2 trong tháng 7. Công ty vay của 7 ngân hàng với lãi bình quân ≈ 8,3%.”
- **Hồi 2 – Xung đột**: “Nhưng hạn mức đã dùng 91,8%, chỉ còn 24,1; dư địa LTV khoảng 36; hai ngân hàng chiếm 60,4% dư nợ. Tức là khi cần vốn đột xuất, ta có ít đường lùi và phụ thuộc vào hai đối tác.”
- **Hồi 3 – Hành động**: “Đề nghị (1) mở đàm phán nâng hạn mức và bổ sung TSĐB trước khi dùng hết; (2) tái cấp khoản lãi cao sang ngân hàng lãi thấp; (3) nạp chi phí lãi vay thực tế để biết ta đang vượt hay đạt kế hoạch.”

### 4.7 Ma trận quyết định

| Quyết định | Kích hoạt khi | Người quyết | Nhịp |
| --- | --- | --- | --- |
| Đàm phán nâng HMTD / bổ sung TSĐB | Hạn mức còn lại < 10% hoặc LTV > 75% (đề xuất) | Giám đốc Tài chính / Tổng giám đốc | Hằng tháng |
| Tái cấp dư nợ sang ngân hàng lãi thấp | Chênh lãi suất giữa các ngân hàng > 1 điểm % | Giám đốc Tài chính | Hằng quý |
| Chuẩn bị tiền trả gốc | Có khoản đáo hạn trong 4 tuần tới | Kế toán trưởng | Hằng tuần |
| Giảm vay ngắn hạn tài trợ hàng tồn | Thanh toán nhanh < 1 và CCC vượt kế hoạch | Ban điều hành | Hằng tháng |
| Xem xét phương án lãi vay | Lãi thực tế vượt kế hoạch > 5% hoặc Interest coverage < 1,5 | Giám đốc Tài chính | Hằng tháng |

## 5. Dashboard 2 – Quản trị hàng tồn kho: “Bao nhiêu vốn đang nằm trong kho và nằm bao lâu?”

### 5.1 Câu hỏi quản trị

Ban điều hành cần biết: hàng tồn đang chiếm bao nhiêu vốn; hàng quay vòng nhanh hay chậm so với kế hoạch; nhập – xuất – tồn đang cân đối hay lệch; nhóm hàng nào chiếm vốn nhiều nhất; và xuất kho thực tế có lệch kế hoạch quá ±5% hay không.

### 5.2 Cơ sở lý thuyết

- **Vòng quay hàng tồn kho (inventory turnover) và số ngày tồn kho (DIO)**: vòng quay = giá vốn hàng bán ÷ giá trị hàng tồn; số ngày tồn kho = số ngày trong kỳ ÷ vòng quay (Ross et al., 2019; Brigham & Ehrhardt, 2017). Chỉ số cho biết trung bình một đồng hàng nằm trong kho bao nhiêu ngày trước khi thành doanh thu.
- **Không có chuẩn chung cho mọi ngành**: Gaur, Fisher và Raman (2005) cho thấy vòng quay hàng tồn kho khác nhau theo biên lợi nhuận gộp, cường độ vốn và quy mô. Vì vậy Minh Long nên so với kế hoạch của chính mình và so với chính mình theo thời gian, không nên chạy theo một con số “chuẩn” vay mượn.
- **Phân loại ABC và tồn kho an toàn**: dồn nỗ lực quản trị vào nhóm mã hàng chiếm phần lớn giá trị, và đặt tồn kho an toàn theo biến động nhu cầu và thời gian cung ứng (Silver et al., 2016).
- **Chi phí mang hàng tồn**: gồm chi phí vốn, kho bãi, hư hỏng, lỗi thời (Brigham & Ehrhardt, 2017). Với lãi vay ≈ 8,3%, riêng chi phí vốn của 341,7 hàng tồn ≈ 28,4/năm (suy ra: 341,7 × 8,3%), tương đương khoảng 90% toàn bộ kế hoạch chi phí lãi vay cả năm (31,6).

### 5.3 Bối cảnh pháp lý – kế toán Việt Nam

- **Chuẩn mực kế toán số 02 (VAS 02) và Thông tư 200/2014/TT-BTC**: hàng tồn kho được ghi nhận theo giá gốc và trình bày theo giá thấp hơn giữa giá gốc và giá trị thuần có thể thực hiện được; hàng tồn gồm nguyên vật liệu (TK 152), thành phẩm (TK 155), hàng hóa (TK 156)… Thông tư 48/2019/TT-BTC hướng dẫn trích lập dự phòng giảm giá hàng tồn kho. Ý nghĩa: hàng nằm lâu và bán không được giá gốc không chỉ tốn vốn mà còn làm giảm lợi nhuận qua dự phòng.
- **Hàng nhập khẩu (tỷ giá > 1 theo BRD)**: chịu thêm rủi ro tỷ giá và thời gian vận chuyển dài, nên thường phải giữ tồn kho an toàn lớn hơn hàng mua trong nước.

### 5.4 Đọc từng chỉ số: ý nghĩa – insight – quyết định

| Chỉ số (BRD) | Số UAT | Insight | Quyết định gợi ý |
| --- | --- | --- | --- |
| Số lượng HTK (1.1) | 673.125,42 | Cộng lẫn nhiều đơn vị tính (tấm, mét, kg…) nên chỉ cho biết độ phức tạp, không dùng so sánh | Không dùng làm KPI; hiển thị số lượng theo từng đơn vị và dòng sản phẩm (Giấy/Nẹp/Ván) |
| Giá trị HTK (1.2) | 341,7 (T7) | T1–T7 nhập 402,0 < xuất 436,7 nên HTK giảm ròng 34,6; suy ra tồn đầu năm ≈ 376,3. Quý 1 tăng 45,2; từ T4 đến T7 giảm 79,9. Mục tiêu HTK trong kế hoạch (CD KT\_pa1 mục IV) chưa có trong UAT | Nạp mục tiêu HTK để thẻ “so với kế hoạch” hoạt động; đặt trần HTK theo tháng |
| Vòng quay HTK (1.3, 2.2) | UAT = 0 (giá vốn = 0). Dùng xuất kho T7 (76,8) làm giá vốn tạm: 0,225 lần/tháng ≈ 2,7 lần/năm | Số ngày tồn kho (DIO) ≈ 341,7 ÷ 76,8 × 30 ≈ 133 ngày (suy ra) | Mỗi ngày giảm DIO giải phóng ≈ 2,5 vốn (giá vốn bình quân ngày 76,8 ÷ 31); giảm 10 ngày ≈ 24,8 vốn và tiết kiệm ≈ 2,1 lãi/năm |
| Inventory to Sales (1.4, 2.3) | 4,56 (hiển thị số lần; BRD ghi %) | Hàng tồn bằng 4,6 tháng doanh thu; quy năm ≈ 38% (341,7 ÷ (75,0 × 12)) | Đổi định dạng; đặt mục tiêu theo kế hoạch năm; dùng cùng vòng quay để đọc, vì hai chỉ số nói cùng một điều |
| Tổng mã sản phẩm (1.5) | 1.246 SKU có tồn > 0 | Độ “phân mảnh” của danh mục hàng; nhiều SKU làm tăng chi phí quản lý và rủi ro chậm luân chuyển | Rà soát SKU không xuất 90/180 ngày; hợp nhất mã tương đương |
| Giá trị hàng nhập khẩu (1.6) | 163,2 (không lọc kỳ) | Nếu cùng kỳ T1–T7 thì ≈ 40,6% tổng giá trị nhập (402,0): phần lớn nguồn cung chịu rủi ro tỷ giá | Thêm bộ lọc thời gian; đặt tồn an toàn riêng cho hàng nhập khẩu; xem xét điều khoản thanh toán và tỷ giá |
| Trạng thái Inventory (2.4) | Nhập 53,8; xuất 76,8 (T7) | T7 xuất nhiều hơn nhập 23,0; T6 lệch 39,3; T4 lệch 18,7; chỉ T1–T3 và T5 nhập ≥ xuất | Giữ nguyên nhịp nhập ≤ xuất cho đến khi HTK chạm mục tiêu; kiểm tra rủi ro thiếu hàng mùa cao điểm |
| Top 10 theo giá trị (2.5) | Thành phẩm 193,2 (56,5%); Nguyên vật liệu 19,5 (5,7%); Đèn áp trần Trim NK 11,3; M017DAA2T 8,4; M017VCM2T 6,6; Hàng hóa 4,2 (1,2%)… | Ba dòng “Thành phẩm, Nguyên vật liệu, Hàng hóa” là mã cấp tài khoản, chiếm 63,5% giá trị nên không cho biết SKU nào đang chiếm vốn | Tránh để mã tổng hợp vào Top 10; rã “Thành phẩm 193,2” xuống SKU trước khi quyết định thanh lý hay sản xuất thêm |
| Top 10 theo số lượng (2.5) | GP4123T 119.495,72; N1610CLNO01T 109.500; M475MLA4T 40.049… | Số lượng lớn nhưng đơn vị khác nhau, phải đọc cùng giá trị: M475MLA4T xuất hiện ở cả hai bảng (2,8 giá trị, 40.049 đơn vị) → đáng ưu tiên kiểm tra | Kiểm tra các mã xuất hiện ở cả hai bảng (M475MLA4T, M017DAA2T, M017VCM2T, D017PBA0T) trước |

**Xuất kho thực tế vs kế hoạch (3.1)** – chênh lệch ±5% cảnh báo; dấu là suy ra vì UAT dùng giá trị tuyệt đối:

| Tháng | Thực tế | Kế hoạch | Chênh lệch | Cảnh báo |
| --- | --- | --- | --- | --- |
| T1 | 52,6 | 105,6 | −50,2% | Đỏ |
| T2 | 20,9 | 52,8 | −60,4% | Đỏ |
| T3 | 53,6 | 52,8 | +1,6% | Xanh |
| T4 | 76,8 | 105,6 | −27,3% | Đỏ |
| T5 | 74,6 | 52,8 | +41,2% | Đỏ |
| T6 | 81,3 | 52,8 | +54,0% | Đỏ |
| T7 | 76,8 | 52,8 | +45,5% | Đỏ |
| **T1–T7** | **436,7** | **475,4** | **−8,1%** | Vàng |

Insight: 6/7 tháng vượt ±5% nên cảnh báo gần như luôn đỏ (hiện tượng mệt mỏi cảnh báo, alert fatigue) trong khi lũy kế chỉ lệch −8,1%. Kế hoạch phân kỳ không đều (T1 và T4 gấp đôi các tháng còn lại) và hai vế so sánh khác bản chất: BRD lấy kế hoạch là “Doanh thu tổng” (giá bán) còn thực tế là giá trị xuất kho (giá vốn). Quyết định: so sánh cùng bản chất (giá vốn kế hoạch mục B của KQKD\_pa1 với giá trị xuất kho), hiển thị thêm lũy kế và bình quân trượt 3 tháng, và chỉ kích hoạt đỏ khi lệch ±5% liên tục 2 tháng (đề xuất).

### 5.5 Mạch kể 3 hồi

- **Hồi 1 – Tích trữ**: “Quý 1 nhập nhiều hơn xuất 45,2, hàng tồn dày lên. Nếu đây là chủ ý chuẩn bị mùa cao điểm thì cần đối chiếu với kế hoạch bán hàng.”
- **Hồi 2 – Xả kho**: “Từ tháng 4 đến tháng 7, xuất nhiều hơn nhập 79,9, nhưng kho vẫn còn 341,7, tương đương khoảng 133 ngày bán. Nghiệp vụ đã bắt đầu đúng hướng nhưng chưa đủ nhanh.”
- **Hồi 3 – Cấu trúc**: “Thành phẩm chiếm 56,5% (193,2 ≈ 2,6 tháng doanh thu), ngân hàng đang tài trợ phần này với lãi ≈ 8,3%. Đề nghị bóc tách theo SKU, đặt mục tiêu giảm 10 ngày tồn kho (giải phóng ≈ 24,8).”

### 5.6 Ma trận quyết định

| Quyết định | Kích hoạt khi | Người quyết | Nhịp |
| --- | --- | --- | --- |
| Giữ nhập ≤ xuất, tạm dừng mua nhóm hàng chậm | HTK > mục tiêu kế hoạch hoặc DIO > mục tiêu | Giám đốc cung ứng / mua hàng | Hằng tuần |
| Khuyến mãi hoặc thanh lý SKU chậm luân chuyển | SKU không xuất trong 90 ngày (cảnh báo), 180 ngày (hành động) – đề xuất | Giám đốc kinh doanh | Hằng tháng |
| Trích lập dự phòng giảm giá | Giá trị thuần có thể thực hiện < giá gốc (TT 48/2019) | Kế toán trưởng | Cuối kỳ |
| Điều chỉnh kế hoạch sản xuất theo xuất kho thực tế | Lũy kế lệch kế hoạch > 5% | Giám đốc sản xuất | Hằng tháng |
| Chuẩn hóa mã hàng, dòng sản phẩm | Mã tổng hợp chiếm > 20% HTK trong Top 10 | Trưởng phòng kho / kế toán | Một lần, rồi rà soát hàng quý |

## 6. Dashboard 3 – Quản trị phải thu – phải trả: “Ai đang giữ tiền của ta, và ta đang giữ tiền của ai?”

### 6.1 Câu hỏi quản trị

Ban điều hành cần biết: tổng phải thu và phải trả hiện tại; khách nào nợ nhiều và nợ lâu; phần nào đã quá hạn và có nguy cơ không thu được; ta đang dùng tín dụng của nhà cung cấp nhiều hay ít hơn khách dùng tín dụng của ta.

### 6.2 Cơ sở lý thuyết

- **Tín dụng thương mại**: Petersen và Rajan (1997) cho thấy tín dụng thương mại là một nguồn vốn thay thế và nhà cung cấp có lợi thế thông tin về khách hàng. Vì vậy bán chịu cần được xem là một khoản đầu tư có chi phí vốn, không phải miễn phí.
- **Chính sách tín dụng và tuổi nợ**: số ngày thu tiền bình quân (DSO = phải thu ÷ doanh thu × số ngày) và bảng phân tích tuổi nợ (aging) là công cụ kiểm soát, và việc cấp tín dụng dựa trên 5C (Character, Capacity, Capital, Collateral, Conditions) (Brigham & Ehrhardt, 2017).
- **Chi phí bỏ chiết khấu thanh toán**: với điều khoản 2/10 nết 30, chi phí ngầm định khi không trả sớm = \[2% ÷ 98%\] × \[365 ÷ 20\] ≈ 37,2%/năm (Brigham & Ehrhardt, 2017), cao gấp khoảng 4,5 lần lãi vay 8,3%. Nếu nhà cung cấp có chiết khấu tương tự, vay ngân hàng để trả sớm là quyết định có lợi.

### 6.3 Bối cảnh pháp lý – kế toán Việt Nam

- **Thông tư 200/2014/TT-BTC**: TK 131 phản ánh phải thu khách hàng, TK 331 phải trả người bán. Số dư Có của TK 131 là “người mua trả tiền trước”, trình bày ở phần nợ phải trả chứ không được trừ vào phải thu của khách khác; điều này giải thích vì sao các số dư âm lớn trong bảng Top 10 quá hạn phải được tách riêng.
- **Thông tư 48/2019/TT-BTC**: trích lập dự phòng nợ phải thu khó đòi theo thời gian quá hạn; mức tối thiểu 30% khi quá hạn từ 6 tháng đến dưới 1 năm, 50% từ 1 đến dưới 2 năm, 70% từ 2 đến dưới 3 năm và 100% từ 3 năm trở lên (cần đối chiếu văn bản gốc khi áp dụng).
- **Luật Thương mại 2005**: bên chậm thanh toán phải trả lãi trên số tiền chậm trả (điều 306), là căn cứ đưa điều khoản lãi chậm trả vào hợp đồng. **Bộ luật Dân sự 2015** quy định thời hiệu khởi kiện tranh chấp hợp đồng là 3 năm (Điều 429), nên aging là công cụ để không mất quyền đòi nợ.
- **Nghị định 123/2020/NĐ-CP** về hóa đơn, chứng từ: số hóa đơn là khóa đối soát giữa kế toán, khách hàng và cơ quan thuế, vì vậy thẻ “Tổng hóa đơn” và bảng hóa đơn đang nợ có giá trị pháp lý khi đòi nợ.

### 6.4 Đọc từng chỉ số: ý nghĩa – insight – quyết định

| Chỉ số (BRD) | Số UAT | Insight | Quyết định gợi ý |
| --- | --- | --- | --- |
| Giá trị phải thu (1.1), Tổng khách hàng (1.6), Tổng hóa đơn (1.5) | 36,3; 694 khách; 2.803 hóa đơn | Bình quân 52,3 triệu/khách và 13,0 triệu/hóa đơn: nhiều khách nhỏ. Nhưng Top 3 chiếm 56,2% (Yeahome 11,5 = 31,6%; Việt Đức Hà Nội 6,4 = 17,7%; Khoáng sản 2,5 = 7,0%) và Top 10 chiếm 66,9% | Đặt hạn mức công nợ theo khách (đề xuất ≤ 20% tổng phải thu/khách); khách nhỏ xử lý bằng quy trình nhắc nợ tự động, khách lớn do Giám đốc Tài chính theo dõi trực tiếp |
| Giá trị phải trả (1.2) | 60,5 | Phải trả > phải thu 24,1: nhà cung cấp đang tài trợ cho Minh Long nhiều hơn Minh Long tài trợ cho khách. Số ngày trả tiền ≈ 60,5 ÷ 76,8 × 30 ≈ 23,6 ngày (suy ra, dùng xuất kho làm giá vốn) | Kiểm tra điều khoản chiết khấu của từng nhà cung cấp; không kéo dài thanh toán nếu đánh mất chiết khấu có chi phí ngầm cao hơn lãi vay |
| Vòng quay phải thu (1.3, 1.4, 2.4) | 2,06 lần (không hợp lệ vì doanh thu mới có 1 tháng) | Quy năm: 75,0 × 12 ÷ 36,3 ≈ 24,8 lần, DSO ≈ 14,5–14,7 ngày (suy ra) – rất thấp so với hạn 30 ngày, hàm ý khách trả nhanh hoặc bán hàng thu tiền ngay chiếm đa số; hoặc có khách đang ứng trước làm phải thu thấp giả | Định nghĩa lại một con số phải thu duy nhất; so DSO với hạn thanh toán 30 ngày mặc định trong BRD |
| Tuổi nợ (2.7) | Tổng 36,6: xem bảng dưới | Quá 30 ngày kể từ hóa đơn 16,1 (44,0%); trên 90 ngày 8,5 (23,3%); nhóm 180+ 3,07 (8,4%, đỏ theo BRD) | Xem mục 6.6 |
| Phải thu theo tháng: trong hạn / quá hạn (2.1) | Tổng nợ T1→T7: 8,7; 3,9; 7,7; 7,2; 3,8; 11,7; 23,7. Nợ quá hạn: 0; 1,25; 0,92; 1,12; 1,95; 2,87; 4,29 | Tỷ lệ quá hạn: 32,0% (T2), 12,0%, 15,6%, 51,8% (T5), 24,5%, 18,1% (T7). Quá hạn tuyệt đối tăng gấp 4,6 lần từ T3 đến T7 dù tỷ lệ giảm do tổng nợ tăng nhanh hơn | Đừng chỉ nhìn %: nợ quá hạn tuyệt đối mới là tiền bị “mắc”; đặt mục tiêu nợ quá hạn tuyệt đối bên cạnh tỷ lệ |
| Top 10 dư nợ cao nhất (2.5) | Yeahome 11,47; Việt Đức Hà Nội 6,43; Khoáng sản 2,53; Anh Lâm AIS 0,74;… | Tập trung rủi ro: một khách chiếm gần 1/3 phải thu | Đánh giá 5C định kỳ cho top 3 |
| Top 10 quá hạn (2.6) | Không hợp lệ (tỷ lệ 947%, −298%…). Ví dụ: Khoáng sản có số dư +2,5 ở Top 10 nhưng −34,5 ở bảng quá hạn | Yeahome, Việt Đức Hà Nội, Khoáng sản, Hà Lâm xuất hiện ở cả hai danh sách nên là nhóm phải rà trước | Sửa truy vấn theo FIFO; tách số dư Có (người mua trả tiền trước) |

**Biểu đồ tuổi nợ (Aging, tính từ ngày hóa đơn, UAT chốt 31/07/2026)**

| Nhóm tuổi | Giá trị | Tỷ trọng | Ý nghĩa |
| --- | --- | --- | --- |
| 1–30 ngày | 20,49 | 56,1% | Còn trong hạn 30 ngày mặc định |
| 31–60 | 5,30 | 14,5% | Mới quá hạn, nhắc nợ |
| 61–90 | 2,27 | 6,2% | Quá hạn sâu (ngưỡng đỏ 60 ngày theo BRD) |
| 91–120 | 2,03 | 5,5% | Rủi ro cao |
| 121–150 | 1,40 | 3,8% | Rủi ro cao |
| 151–180 | 2,00 | 5,5% | Sắp vào nhóm 180+ trong 30 ngày tới |
| 180+ | 3,07 | 8,4% | Đỏ, cân nhắc dự phòng và biện pháp pháp lý |

### 6.5 Mạch kể 3 hồi

- **Hồi 1 – Điểm sáng**: “Phải thu chỉ 36,3, tương đương khoảng 14,5 ngày doanh thu, và nhà cung cấp đang cho ta chịu nhiều hơn (60,5). Đây là vị thế tín dụng thương mại thuận lợi.”
- **Hồi 2 – Vết nứt**: “Nhưng nợ đang già đi và dồn vào vài khách: 44% quá 30 ngày, 3,07 ở nhóm 180+; Yeahome một mình chiếm 31,6%; quá hạn tuyệt đối tăng gấp 4,6 lần từ tháng 3.”
- **Hồi 3 – Hành động**: “Đề nghị đặt hạn mức công nợ theo khách, đối soát số dư Có, và chốt quy trình thu hồi theo bậc.”

### 6.6 Ma trận quyết định

| Quyết định | Kích hoạt khi | Người quyết | Nhịp |
| --- | --- | --- | --- |
| Nhắc nợ tự động | Hóa đơn quá 30 ngày | Kế toán công nợ | Hằng tuần |
| Tạm dừng giao hàng chịu | Khách có nợ quá 60 ngày (đỏ BRD) hoặc vượt hạn mức công nợ | Giám đốc kinh doanh kết hợp Tài chính | Khi phát sinh |
| Thu hồi bằng biện pháp pháp lý, áp dụng lãi chậm trả theo hợp đồng | Nợ > 90 ngày hoặc nhóm 180+ | Tổng giám đốc | Hằng tháng |
| Trích lập dự phòng phải thu khó đòi | Quá hạn ≥ 6 tháng (≈ 210 ngày kể từ hóa đơn nếu hạn 30 ngày); với 3,07 ở nhóm 180+ mức tối thiểu 30% ≈ 0,92 | Kế toán trưởng | Cuối kỳ |
| Thanh toán sớm lấy chiết khấu | Chi phí ngầm của chiết khấu > lãi vay 8,3% | Giám đốc Tài chính | Mỗi lần đàm phán với nhà cung cấp |

## 7. Dashboard 4 – Quản trị tiền gửi và thanh khoản: “Đệm tiền mặt có đủ dày và có đang sinh lời đúng giá không?”

### 7.1 Câu hỏi quản trị

Ban điều hành cần biết: tiền và tương đương tiền hiện có bao nhiêu, đủ chi bao nhiêu ngày; tiền gửi kỳ hạn đang gửi ở đâu, kỳ hạn nào, lãi bao nhiêu; có thu hồi được khi cần không; và lãi tiền gửi có đủ bù chi phí vốn vay hay không.

### 7.2 Cơ sở lý thuyết

- **Lý do giữ tiền**: doanh nghiệp giữ tiền để giao dịch và để dự phòng. Opler, Pinkowitz, Stulz và Williamson (1999) ghi nhận doanh nghiệp có dòng tiền biến động và khó tiếp cận thị trường vốn có xu hướng giữ nhiều tiền hơn. Minh Long phụ thuộc ngân hàng và có dòng tiền ròng tháng dao động từ −153 đến +237, nên đệm dự phòng là có cơ sở; vấn đề là giữ bao nhiêu và ở dạng nào.
- **Quản trị tiền mặt tối ưu**: Baumol (1952) cân bằng chi phí giao dịch khi chuyển đổi giữa tiền và chứng khoán/tiền gửi với chi phí cơ hội (lãi) khi giữ tiền; Miller và Orr (1966) mở rộng cho dòng tiền biến động ngẫu nhiên: đặt ngưỡng dưới, mức mục tiêu và ngưỡng trên; chạm ngưỡng dưới thì rút tiền gửi/vay thêm, chạm ngưỡng trên thì gửi hoặc trả bớt nợ. Đây là khung phù hợp với bài toán “ngưỡng sau” của Minh Long.
- **Chi phí chênh lệch (negative carry)**: nếu đồng thời vay với lãi cao hơn lãi gửi, phần chênh lệch là chi phí cơ hội của việc giữ tiền nhàn rỗi (Brealey et al., 2020).

### 7.3 Bối cảnh pháp lý – kế toán Việt Nam

- **Chuẩn mực kế toán số 24 (VAS 24) và Thông tư 200/2014/TT-BTC**: “tiền và các khoản tương đương tiền” (B01-DN mã 110) gồm tiền mặt, tiền gửi không kỳ hạn và các khoản đầu tư ngắn hạn có thời hạn gốc không quá 3 tháng, dễ chuyển đổi. Tiền gửi kỳ hạn gốc trên 3 tháng được trình bày ở khoản đầu tư nắm giữ đến ngày đáo hạn, không nằm trong 91,98. Ý nghĩa cho dashboard: chỉ phần gửi 2–3 tháng (4,97) là tương đương tiền; 35,5 gửi 6–12 tháng là thanh khoản có phí.
- **Lãi tiền gửi** ghi nhận vào doanh thu hoạt động tài chính (TK 515), khớp với cách BRD lọc đối ứng 515 trong Sổ chi tiết tài khoản. Quy định rút trước hạn do từng ngân hàng quy định, thường chỉ hưởng lãi suất không kỳ hạn nên cần đọc điều khoản từng sổ.

### 7.4 Đọc từng chỉ số: ý nghĩa – insight – quyết định

| Chỉ số (BRD) | Số UAT | Insight | Quyết định gợi ý |
| --- | --- | --- | --- |
| Tiền & tương đương tiền (1.1) | 91,98 (B01-DN mã 110) | Chi gộp bình quân mỗi ngày T1–T7 ≈ 2.302,6 ÷ 212 = 10,86 → tiền đủ ≈ 8,5 ngày chi; cộng hạn mức còn lại 24,1 thì ≈ 10,7 ngày (suy ra) | Đặt sàn tiền theo số ngày chi hoạt động (ví dụ 7–10 ngày, tức khoảng 76–109 nếu lấy chi gộp), xác lập sau khi tách trả gốc vay |
| Tiền gửi còn hiệu lực (1.2) | 40,5 (≈ 44% số dư tiền); 22 hợp đồng (1.3) | Bình quân 1,84/hợp đồng; nhiều hợp đồng đáo hạn 2025 chưa tất toán vẫn được tính (điều kiện 9) | Rà trạng thái tái tục; tách “đã quá đáo hạn chưa tất toán” thành nhóm riêng |
| Lãi suất bình quân gia quyền (1.4) | 4,99% | Thấp hơn lãi vay ≈ 8,3% khoảng 3,3 điểm %; chi phí chênh lệch ≈ 40,5 × 3,3% ≈ 1,3/năm (suy ra) | Tách tiền gửi bắt buộc (cam kết ngân hàng, thế chấp) khỏi tiền gửi tự nguyện; phần tự nguyện xem xét dùng để giảm vay ngắn hạn (mỗi 10 giảm được ≈ 0,33/năm) |
| Thu nhập lãi (1.5) | 1,48 (T1–T7, đối ứng 515) | Ước tính từ tiền gửi: 40,5 × 4,99% × 7/12 ≈ 1,18, cùng bậc với 1,48 (có thêm lãi tài khoản thanh toán) | Dùng làm kiểm tra chéo: nếu thu nhập lãi thấp hơn nhiều so với lãi danh nghĩa thì có thể có hợp đồng rút trước hạn mất lãi |
| Cơ cấu theo ngân hàng (2.1) | IVB 18,73 (46,2%); Woori 12,0 (29,6%); HD 4,86 (12,0%); VP 3,0 (7,4%); LP 1,02 (2,5%); MB 0,9 (2,2%) | So với dư nợ vay (Dashboard 1): gửi/vay tại IVB 25%, Woori 50%, HD 33%, VP 30%, MB 1%. Khoảng 97,5% tiền gửi nằm ở ngân hàng đang cho vay (chỉ LP không có dư nợ). Danh mục TSĐB có hợp đồng tiền gửi 2,0 hệ số 1,0 | Hỏi từng ngân hàng: phần nào là điều kiện để được hưởng hạn mức hoặc lãi vay ưu đãi (ví dụ Woori vay 7,0% thấp nhất trong khi gửi 50% dư nợ); nếu là điều kiện thì chi phí “chênh lệch” thực ra là một phần giá của hạn mức |
| Cơ cấu theo kỳ hạn (2.2) | 6 tháng 21,52 (53,1%); 12 tháng 14,02 (34,6%); 3 tháng 2,40; 2 tháng 2,57 (cộng 12,3%) | 87,7% kỳ hạn từ 6 tháng trở lên. Trong phần log hiển thị, 7/7 hợp đồng LP đều tất toán trước hạn (có hợp đồng 12 tháng chỉ gửi khoảng 1 tháng) → dấu hiệu cần tiền đột xuất và kỳ hạn không khớp nhu cầu | Xây thang kỳ hạn (liquidity ladder): đề xuất ít nhất 30% tiền gửi tự nguyện ≤ 3 tháng; không để tiền dự phòng nằm trong hợp đồng 12 tháng |
| Chi tiết hợp đồng (2.3) | passbook, lãi suất, ngày gửi, đáo hạn, tất toán | Cho biết hợp đồng nào sắp đáo hạn để chủ động tái tục hoặc rút | Thêm cột “số ngày còn lại” và cảnh báo hợp đồng đáo hạn trong 14 ngày |

**Tổng thanh khoản có thể huy động (suy ra)**: 91,98 tiền + 35,5 tiền gửi 6–12 tháng (nếu rút trước hạn, chịu mất lãi) + 24,1 hạn mức còn lại ≈ 151,7, với giả định 91,98 chưa gồm phần gửi 6–12 tháng và hạn mức còn dùng được ngay.

### 7.5 Mạch kể 3 hồi

- **Hồi 1 – Bối cảnh**: “Công ty đang có 91,98 tiền và 40,5 tiền gửi kỳ hạn ở 6 ngân hàng, lãi bình quân 4,99%.”
- **Hồi 2 – Xung đột**: “Nhưng đệm chỉ đủ khoảng 8,5 ngày chi gộp; 87,7% tiền gửi bị khóa từ 6 tháng; phần lớn gửi tại chính ngân hàng cho vay với lãi thấp hơn lãi vay 3,3 điểm %. Tiền đang vừa khó dùng vừa tốn kém.”
- **Hồi 3 – Hành động**: “Đề nghị phân loại tiền gửi bắt buộc / tự nguyện, dựng thang kỳ hạn, và dùng phần tự nguyện dư để giảm vay lãi cao.”

### 7.6 Ma trận quyết định

| Quyết định | Kích hoạt khi | Người quyết | Nhịp |
| --- | --- | --- | --- |
| Bổ sung thanh khoản (rút tiền gửi/giải ngân) | Số ngày tiền < sàn nội bộ (đề xuất 7 ngày chi hoạt động) | Giám đốc Tài chính | Hằng tuần |
| Tái tục, rút hoặc đổi kỳ hạn hợp đồng | Hợp đồng đáo hạn trong 14 ngày | Chuyên viên Tài chính | Hằng tuần |
| Dùng tiền gửi tự nguyện để giảm vay | Lãi vay − lãi gửi > 2 điểm % và đủ sàn thanh khoản | Giám đốc Tài chính | Hằng quý |
| Đàm phán gói lãi vay – lãi gửi với từng ngân hàng | Tiền gửi > 25% dư nợ tại cùng ngân hàng mà không có ưu đãi | Giám đốc Tài chính | Hằng quý |

## 8. Dashboard 5 – Quản trị dòng tiền: “Tiền vào ra thế nào, và còn sống được bao lâu nếu không có thêm vốn?”

### 8.1 Câu hỏi quản trị

Ban điều hành cần biết: tuần/tháng qua tiền vào và ra bao nhiêu; dòng tiền đến từ hoạt động nào và đi vào ngân hàng nào; số dư đủ dùng bao lâu; vốn lưu động ròng và chu kỳ tiền mặt đang tốt lên hay xấu đi.

### 8.2 Cơ sở lý thuyết

- **Lợi nhuận khác tiền**: báo cáo lưu chuyển tiền tệ phân dòng tiền thành hoạt động kinh doanh, đầu tư và tài chính (VAS 24; Brigham & Ehrhardt, 2017). Dashboard theo BRD gom mọi giao dịch qua TK 111/112 (trừ chuyển nội bộ) nên “tiền vào” gồm cả giải ngân vay và “tiền ra” gồm cả trả gốc, trả lãi (BRD liệt kê rõ hai khoản này). Vì vậy cần tách theo tài khoản đối ứng để biết “trả bằng tiền kinh doanh hay tiền vay mới”.
- **Chu kỳ chuyển đổi tiền mặt**: CCC = DIO + DSO − DPO (Richards & Laughlin, 1980); vốn lưu động ròng = tài sản ngắn hạn − nợ ngắn hạn (Ross et al., 2019).
- **Runway (thời gian tiền còn đủ dùng)** = tiền ÷ mức chi ròng bình quân mỗi tháng. Chỉ số này có ý nghĩa khi doanh nghiệp đang “đốt tiền” (chi ròng dương); khi dòng tiền ròng dương, kết quả âm và không có ý nghĩa quản trị.
- **Dự báo dòng tiền cuốn chiếu 13 tuần**: thực hành phổ biến để chuyển từ báo cáo quá khứ sang dự báo; hợp với nhịp xem hằng tuần vào thứ Bảy của BRD.

### 8.3 Bối cảnh kế toán Việt Nam

- **Chứng từ loại trừ**: BRD yêu cầu loại các chứng từ CTNB (chuyển tiền nội bộ) và NTTK (nộp tiền vào tài khoản) vì chúng không làm thay đổi tổng tiền của doanh nghiệp; nếu không loại, dòng tiền vào và ra đều bị thổi phồng.
- **Tài khoản đối ứng** theo Thông tư 200/2014/TT-BTC: 131 (thu từ khách), 331 (trả nhà cung cấp), 341 (vay), 515 (thu lãi), 635 (chi phí tài chính). Đây là khóa để phân rã dòng tiền theo bản chất.

### 8.4 Đọc từng chỉ số: ý nghĩa – insight – quyết định

**Dòng tiền vào – ra – ròng theo tháng (1.1, 1.2, 2.1; số UAT)**

| Tháng | Tiền vào | Tiền ra | Ròng (suy ra) |
| --- | --- | --- | --- |
| T1 | 317,1 | 253,4 | +63,7 |
| T2 | 113,2 | 218,3 | −105,1 |
| T3 | 396,0 | 380,7 | +15,3 |
| T4 | 398,1 | 412,8 | −14,8 |
| T5 | 337,1 | 305,5 | +31,6 |
| T6 | 558,0 | 320,8 | +237,2 |
| T7 | 257,9 | 411,1 | −153,2 |
| **T1–T7** | **2.377,3** | **2.302,6** | **+74,6** |

T8 mới có 2,7 triệu tiền vào nên chưa đủ số.

| Chỉ số (BRD) | Số UAT | Insight | Quyết định gợi ý |
| --- | --- | --- | --- |
| Tổng tiền vào – ra (1.1, 1.2) | 2.377,3 – 2.302,6 | Ròng +74,6 nhưng biên động từ −153,2 đến +237,2: tháng 6 chiếm 318% ròng lũy kế. Dư nợ vay tháng 6 chỉ tăng 2,7 nên +237,2 không chủ yếu từ vay mới; có thể từ thu tiền khách hoặc tiền khách ứng trước (giả thuyết). Tháng 7 dư nợ giảm 59,2, khoảng 39% mức ròng âm 153,2 (giả thuyết trả gốc) | Phân rã theo tài khoản đối ứng 131/331/341/515/635 để kiểm chứng hai giả thuyết trước khi kết luận |
| Cash Balance (1.3) | 91,98 (B01-DN mã 110) | BRD định nghĩa Cash Balance = Vào − Ra, nhưng đó là dòng tiền ròng (+74,6) chứ không phải số dư; UAT đã lấy số dư từ B01 là đúng | Đổi tên hai thẻ thành “Dòng tiền ròng” và “Số dư tiền” |
| Cơ cấu thu/chi theo ngân hàng (2.2, 2.3) | Thu từ 131: MB 55,8; BIDV 32,0; VCB 1,7; TPB 0,2. Chi cho 331: MB 33,2; BIDV 0,48; VCB 0,11. TPB chi 3,68 đối ứng 6352 | Thu chủ yếu từ khách (131) tập trung ở MB và BIDV. Đối ứng 6352 tại TPB (3,68) là khoản chi chi phí tài chính qua ngân hàng, có thể dùng đối chiếu lãi vay thực tế trong lúc B02-DN mã 23 chưa nạp (cần xác nhận ý nghĩa tiểu khoản) | Cho khách thanh toán vào ngân hàng có dư nợ lớn (MB, IVB) để trả nợ trực tiếp, giảm phí chuyển khoản nội bộ |
| Vốn lưu động (2.4) | 248,4 (T7) | Tài sản ngắn hạn ≈ 891,5, nợ ngắn hạn ≈ 643,1 (suy ra), hiện chỉ có hai điểm dữ liệu T7 và T8 giống nhau nên chưa thấy xu hướng | Nạp B01 theo tháng T1–T7 để vẽ xu hướng; so với kế hoạch bảng cân đối kế toán |
| Runway (3.1) | −9,86 | Dòng tiền ròng T1–T8 là +74,6 nên chi ròng bình quân âm (−9,3/tháng) và runway âm: “hệ thống không đang đốt tiền”. Thẻ để nguyên sẽ gây hiểu nhầm | Hiển thị “N/A – dòng tiền ròng dương” và thêm chỉ số Số ngày tiền = tiền ÷ chi gộp bình quân ngày ≈ 8,5 ngày (ngưỡng BRD < 3 tháng sẽ đỏ theo cách này, nhưng chi gộp có cả trả gốc và đảo nợ nên cần phiên bản chi hoạt động, loại đối ứng 341) |
| Chu kỳ tiền mặt CCC (3.2) | Hiển thị DSO 55,4; DIO, DPO, CCC = null | Cách tính chuẩn hóa (suy ra): DSO ≈ 36,3 ÷ 75,0 × 30 = 14,5 ngày (hoặc 4,6 nếu dùng phải thu ròng 11,4); DIO ≈ 133,4; DPO ≈ 23,6; CCC ≈ 114–124 ngày | DIO chiếm hầu như toàn bộ CCC; mục tiêu nằm ở kho |

**Vì sao CCC ≈ 114–124 ngày quan trọng?** Giá vốn bình quân mỗi ngày ≈ 2,5 (76,8 ÷ 31). Phần vốn lưu động thương mại (HTK + phải thu − phải trả = 341,7 + 36,3 − 60,5) ≈ 317,6, gần bằng dư nợ vay 291,0. Chi phí vốn của phần này ≈ 317,6 × 8,3% ≈ 26,4/năm. Mỗi ngày rút ngắn CCC giải phóng ≈ 2,5 vốn và tiết kiệm ≈ 0,2 lãi/năm.

### 8.5 Mạch kể 3 hồi

- **Hồi 1 – Bối cảnh**: “Bảy tháng đầu năm, tiền vào 2.377 và tiền ra 2.303, dòng tiền ròng dương 74,6.”
- **Hồi 2 – Xung đột**: “Nhưng ròng từng tháng đảo chiều mạnh (+237 rồi −153), số dư cuối kỳ chỉ 92,0 ≈ 8,5 ngày chi gộp, và chu kỳ tiền mặt đồng thời nằm ở khoảng 4 tháng. Tiền chưa kịp quay về thì đã phải ra.”
- **Hồi 3 – Hành động**: “Đề nghị tách dòng tiền kinh doanh khỏi dòng tiền vay, dựng dự báo 13 tuần, đặt sàn tiền theo ngày chi, và đặt mục tiêu rút ngắn CCC bằng giảm tồn kho.”

### 8.6 Ma trận quyết định

| Quyết định | Kích hoạt khi | Người quyết | Nhịp |
| --- | --- | --- | --- |
| Hoãn hoặc dồn khoản chi lớn không khẩn | Dự báo số dư tuần tới < sàn nội bộ | Giám đốc Tài chính | Hằng tuần |
| Đẩy nhanh thu hồi phải thu | Dòng tiền ròng âm 2 tháng liên tiếp | Giám đốc kinh doanh | Hằng tuần |
| Đặt mục tiêu CCC theo kế hoạch năm | CCC > mục tiêu kế hoạch (BRD 3.2 so với kế hoạch Sheet 1) | Ban điều hành | Hằng quý |
| Quyết định vay bổ sung hay không | Số ngày tiền < sàn và dự báo 4 tuần không đủ | Giám đốc Tài chính, Tổng giám đốc duyệt | Khi phát sinh |

## 9. Story kết hợp: n chỉ số × n dashboard

Những câu chuyện dưới đây ghép chỉ số từ nhiều dashboard để trả lời những câu hỏi mà một dashboard đơn lẻ không trả lời được. Dùng cho họp Ban điều hành hằng tháng thay vì đọc từng dashboard.

### 9.1 Story A – “Ngân hàng đang tài trợ chu kỳ tiền mặt” (Dashboard 1 + 2 + 3 + 5)

**Các chỉ số ghép**: dư nợ vay (D1), giá trị HTK và DIO (D2), phải thu/phải trả (D3), CCC và vốn lưu động (D5).

| Thành phần | Giá trị (T7/2026) |
| --- | --- |
| Hàng tồn kho | 341,7 |
| + Phải thu khách hàng | 36,3 |
| − Phải trả nhà cung cấp | 60,5 |
| **= Vốn lưu động thương mại (suy ra)** | **317,6** |
| Dư nợ vay (TK 341) | 291,0 |
| Tiền và tương đương tiền | 92,0 |

- **Insight**: vốn lưu động thương mại 317,6 lớn hơn dư nợ vay 291,0, nghĩa là ngân hàng về cơ bản đang tài trợ chu kỳ tiền mặt (khoảng 114–124 ngày, trong đó tồn kho ≈ 133 ngày). Chi phí vốn của phần này ≈ 317,6 × 8,3% ≈ 26,4/năm.
- **Quyết định**: đặt mục tiêu giảm 10 ngày tồn kho. Kết quả kỳ vọng (suy ra): giải phóng ≈ 24,8 vốn, dùng trả vay thì tiết kiệm ≈ 2,1 lãi/năm, đồng thời hạn mức còn lại tăng từ 24,1 lên ≈ 48,9. Đây là “mỏ” vốn rẻ nhất vì không phải đi vay thêm.

### 9.2 Story B – “Đệm thanh khoản ba lớp” (Dashboard 4 + 1 + 5)

**Các chỉ số ghép**: số dư tiền và tiền gửi (D4), hạn mức còn lại và lịch trả gốc (D1), chi gộp bình quân ngày (D5).

| Lớp | Nguồn | Giá trị | Tương đương số ngày chi gộp (10,86/ngày) | Chi phí dùng |
| --- | --- | --- | --- | --- |
| 1 | Tiền và tương đương tiền | 92,0 | 8,5 ngày | Thấp nhất |
| 2 | Hạn mức tín dụng còn lại | 24,1 | 2,2 ngày | Lãi vay ≈ 8,3% |
| 3 | Tiền gửi 6–12 tháng (rút trước hạn) | 35,5 | 3,3 ngày | Mất lãi đã tích lũy, và có thể là tài sản bảo đảm |
| **Tổng** |  | **151,7** | **≈ 14,0 ngày** |  |

- **Insight**: ngay cả khi huy động cả ba lớp, đệm chỉ khoảng 14 ngày chi gộp. Ngược lại, khi cần 10 trong 1 tháng, rút trước hạn mất khoảng 10 × (4,99% − 0,5%) ÷ 12 ≈ 0,037, trong khi vay thêm tốn 10 × 8,3% ÷ 12 ≈ 0,069 (giả định minh họa lãi không kỳ hạn 0,5%). Nếu tiền gửi không phải tài sản bảo đảm, rút trước hạn rẻ hơn gần một nửa so với vay.
- **Quyết định**: viết thành quy tắc dùng tiền theo thứ tự lớp 1 → 3 → 2 (hoặc 1 → 2 → 3 tùy chi phí từng lần), và chỉ trình Ban điều hành khi số ngày chi chạm sàn nội bộ.

### 9.3 Story C – “Từ doanh thu đến tiền – bán được có thu được không?” (Dashboard 2 + 3 + 5 + 1)

**Các chỉ số ghép**: xuất kho T7 76,8 (D2), doanh thu T7 ≈ 75,0 (D1/D3), phải thu 36,3 và aging (D3), tiền thu từ TK 131 theo ngân hàng (D5).

- **Insight**: xuất kho (76,8) và doanh thu (75,0) cùng bậc, phải thu chỉ ≈ 0,5 tháng doanh thu; vậy phần lớn doanh thu đã thành tiền (tiền thu từ 131 tập trung ở MB 55,8 và BIDV 32,0). Rủi ro nằm ở “đuôi”: 44% phải thu quá 30 ngày và nợ quá hạn tuyệt đối tăng gấp 4,6 lần từ tháng 3.
- **Lưu ý đo lường**: phải thu trong hóa đơn bao gồm thuế GTGT (ví dụ hóa đơn BH00729: 564.444 ÷ 7.055.556 = 8,0%) trong khi doanh thu thuần không gồm thuế, nên DSO sẽ lệch khoảng 8% nếu không đồng nhất.
- **Quyết định**: thêm chỉ số “tỷ lệ thu hồi trong kỳ” = tiền thu đối ứng 131 ÷ (doanh thu + thuế GTGT) để theo dõi bán được có thu được không; giao chỉ tiêu thu hồi cho kinh doanh và kế toán công nợ cùng nhau.

### 9.4 Story D – “Kế hoạch – thực tế – cảnh báo” (Dashboard 1 + 2 + 5)

**Các chỉ số ghép**: xuất kho thực tế vs kế hoạch (D2), chi phí lãi vay thực tế vs kế hoạch (D1), mục tiêu HTK/vòng quay/CCC/dòng tiền trong file Kế hoạch kinh doanh 2026 (D2, D3, D5).

- **Insight**: xuất kho lũy kế lệch −8,1% nhưng 6/7 tháng đơn lẻ đỏ; lãi vay ước tính vượt kế hoạch 12–13%; các mục tiêu HTK, vòng quay phải thu (Target\_Vong\_Quay), LCTT\_pa1 chưa được nạp. Nghiêm trọng là bộ ngưỡng ±5% theo tháng khiến cảnh báo vừa “khoe” vừa “diễn”, dễ bị bỏ qua.
- **Quyết định**: chuyển sang ba lớp cảnh báo (đề xuất): tháng đơn lẻ chỉ để tham khảo; lũy kế lệch > 5% là vàng; lệch > 5% liên tục 2–3 tháng hoặc lũy kế > 10% là đỏ và phải có người chịu trách nhiệm giải trình. Đồng thời phân kỳ lại kế hoạch theo mùa vụ thay vì chia không đều (T1, T4 gấp đôi các tháng còn lại).

### 9.5 Story E – “Rủi ro tập trung ba trụ” (Dashboard 1 + 3 + 4)

| Trụ | Chỉ số | Giá trị |
| --- | --- | --- |
| Nguồn vốn | MB + IVB trên tổng dư nợ ngân hàng; HHI | 60,4%; ≈ 2.200 |
| Khách hàng | Top 3 trên tổng phải thu; Yeahome | 56,2%; 31,6% |
| Nơi gửi tiền | Tiền gửi tại ngân hàng đang cho vay | ≈ 97,5% |

- **Insight**: cả nguồn vốn, nguồn thu và nơi cất tiền đều tập trung vào vài đối tác. Một cú sốc ở MB/IVB (siết hạn mức) hoặc ở Yeahome (chậm trả 11,5) sẽ tác động cùng lúc lên thanh khoản, vì đệm chỉ ≈ 14 ngày.
- **Quyết định**: đặt trần tập trung (đề xuất: ≤ 30% dư nợ mỗi ngân hàng; ≤ 20% phải thu mỗi khách; tiền gửi dự phòng phân bổ ít nhất 2 ngân hàng không cho vay) và báo cáo hàng quý.

## 10. Bảng cảnh báo hợp nhất (mở rộng mục 2.8 của BRD)

Bảng dưới đây gom ngưỡng BRD và các ngưỡng đề xuất thành một màn hình “đèn giao thông” mà Ban điều hành đọc đầu tiên. Cột độ tin cậy cho biết có nên tin trạng thái hay không.

| # | Chỉ số | Giá trị hiện tại | Ngưỡng | Trạng thái | Độ tin cậy dữ liệu |
| --- | --- | --- | --- | --- | --- |
| 1 | LTV | 71,3% | > 80% (BRD) | Xanh (còn 8,7 điểm %) | Trung bình (chưa sau hệ số) |
| 2 | Hạn mức còn lại | 24,1 (8,2% HMTD) | < 10% vàng, < 5% đỏ (đề xuất) | Vàng | Cao (khớp hai nguồn) |
| 3 | Dư nợ vượt hạn mức | 270,9 so với 295,0 | Dư nợ > hạn mức (BRD) | Xanh toàn công ty; kiểm tra từng ngân hàng | Trung bình |
| 4 | Interest coverage | N/A | < 1,5 (BRD) | Chưa đánh giá được | Thấp (lãi vay = 0) |
| 5 | Số ngày tiền (chi gộp) | 8,5 ngày | < 3 tháng (BRD runway) | Đỏ theo chi gộp; N/A theo chi ròng | Trung bình |
| 6 | Xuất kho vs kế hoạch (lũy kế) | −8,1% | ±5% (BRD) | Vàng | Trung bình |
| 7 | Nợ quá hạn sâu (tuổi hóa đơn > 90 ngày) | 8,5 (23,3% phải thu) | Quá hạn 60 ngày đỏ (BRD) | Đỏ | Trung bình |
| 8 | Nhóm 180+ ngày | 3,07 (8,4%) | Đỏ theo BRD | Đỏ | Trung bình |
| 9 | Tập trung khách hàng | Top 3 = 56,2%; Yeahome 31,6% | ≤ 20%/khách (đề xuất) | Đỏ | Trung bình |
| 10 | Tập trung ngân hàng | MB 33,2%; Top 2 = 60,4% | ≤ 30%/ngân hàng (đề xuất) | Đỏ | Cao |
| 11 | Thanh toán nhanh | 0,86 | < 1,0 (tham chiếu) | Vàng | Trung bình (suy ra) |
| 12 | Tiền gửi kỳ hạn ≤ 3 tháng | 12,3% | ≥ 30% (đề xuất) | Đỏ | Trung bình |
| 13 | Số ngày tồn kho (DIO) | ≈ 133 ngày | Theo kế hoạch (chưa nạp) | Chưa đánh giá được | Thấp |

## 11. Lộ trình hiệu chỉnh trước khi trình Ban điều hành

| Ưu tiên | Việc cần làm | Vì sao | Ảnh hưởng |
| --- | --- | --- | --- |
| P1 | Nạp đủ B02-DN tháng 1–7 (doanh thu, giá vốn, lãi vay) và B01-DN theo tháng, kèm số dư 31/07/2025 | Mở khóa vòng quay, biên lợi nhuận, ROE/ROA, Interest coverage, Cost of Debt | D1, D2, D3 |
| P1 | Thống nhất một định nghĩa phải thu; viết lại Top 10 quá hạn theo FIFO; tách số dư Có | Bốn con số phải thu khác nhau làm mất niềm tin vào cả báo cáo | D3, D5 |
| P1 | Sửa công thức DSO/DIO/DPO/CCC (nhân số ngày trong kỳ), EBITDA (khấu hao trong kỳ), Nợ/EBITDA (số dư thay vì lũy kế) | Các chỉ số đang sai hệ số hoặc sai dấu | D1, D5 |
| P2 | Chuẩn hóa dim\_bank; đồng nhất cách ghép thu/chi theo ngân hàng giữa D1 và D5 | Ghép được vay – gửi – thu chi cùng một ngân hàng (Story B, E) | D1, D4, D5 |
| P2 | Bổ sung trạng thái hợp đồng tiền gửi (tái tục, đã tất toán, quá đáo hạn) và sửa cột kỳ hạn | Tiền gửi 40,5 có thể tính dư | D4 |
| P2 | Nạp snapshot tồn kho T1–T6 và mã SKU/dòng sản phẩm; loại mã tổng hợp khỏi Top 10 | Vẽ được xu hướng và phân tích ABC | D2 |
| P2 | Nạp các bảng mục tiêu: HTK (CD KT\_pa1 mục IV), Target\_Vong\_Quay, LCTT\_pa1 | Kích hoạt các thẻ “so với kế hoạch” | D2, D3, D5 |
| P3 | Đặt slicer mặc định = tháng khóa sổ gần nhất; đổi tên chỉ tiêu (Debt/Equity, Cash Balance, Runway) | Tránh hiểu nhầm khi trình bày | Tất cả |

**Câu hỏi cần chuyên viên Tài chính xác nhận để hoàn thiện câu chuyện**

- 59,2 giảm dư nợ tháng 7 có phải trả nợ thật, hay do chưa ghi nhận giải ngân?
- Tiền gửi tại IVB, Woori, HD, VP có gắn điều kiện hạn mức hoặc lãi vay ưu đãi không?
- Minh Long có thuộc diện áp dụng trần 30% EBITDA theo NĐ 132/2020 (có giao dịch liên kết) không?
- Tiểu khoản 6352 đối ứng tại TPBank (3,68) là khoản gì; và phải thu ngắn hạn trên B01 (suy ra ≈ 387, khác xa 36,3 ở TK 131) gồm những khoản nào?
- Ngưỡng nội bộ đề xuất (hạn mức còn lại, trần tập trung, số ngày tiền tối thiểu) có được Ban điều hành chấp thuận không?

## 12. Tài liệu tham khảo (APA 7)

*Ghi chú: văn bản pháp lý ở trên ghi theo số hiệu; khi đưa vào tiểu luận có thể đổi thành dạng (Bộ Tài chính, 2014). Nên đối chiếu số chương, số trang với bản giáo trình nhà trường đang dùng trước khi nộp; tài liệu này chỉ dẫn ở mức tác giả – năm – nhãn đề.*

**Dữ liệu nội bộ**

Công ty Gỗ Minh Long. (2026a). *ISO – BRD Final* \[Tài liệu nội bộ, tệp .xlsx\].

Công ty Gỗ Minh Long. (2026b). *UAT\_01 đến UAT\_05: Kịch bản SQL kiểm thử dashboard Quản trị tài chính, Hàng tồn kho, Phải thu – Phải trả, Tiền gửi, Dòng tiền* \[Tài liệu nội bộ, tệp .sql\].

**Văn bản pháp lý và chuẩn mực**

Bộ Tài chính. (2001). *Quyết định số 149/2001/QĐ-BTC ngày 31/12/2001 về việc ban hành bốn chuẩn mực kế toán Việt Nam (đợt 1)* \[Chuẩn mực số 02 – Hàng tồn kho\].

Bộ Tài chính. (2003). *Quyết định số 234/2003/QĐ-BTC ngày 30/12/2003 về việc ban hành sáu chuẩn mực kế toán Việt Nam (đợt 5)* \[Chuẩn mực số 24 – Báo cáo lưu chuyển tiền tệ\].

Bộ Tài chính. (2014). *Thông tư số 200/2014/TT-BTC ngày 22/12/2014 hướng dẫn Chế độ kế toán doanh nghiệp*.

Bộ Tài chính. (2019). *Thông tư số 48/2019/TT-BTC ngày 08/8/2019 hướng dẫn việc trích lập và xử lý các khoản dự phòng giảm giá hàng tồn kho, tổn thất các khoản đầu tư, nợ phải thu khó đòi và bảo hành sản phẩm, hàng hóa, công trình xây lắp tại doanh nghiệp*.

Chính phủ. (2020a). *Nghị định số 123/2020/NĐ-CP ngày 19/10/2020 quy định về hóa đơn, chứng từ*.

Chính phủ. (2020b). *Nghị định số 132/2020/NĐ-CP ngày 05/11/2020 quy định về quản lý thuế đối với doanh nghiệp có giao dịch liên kết*.

Chính phủ. (2021). *Nghị định số 21/2021/NĐ-CP ngày 19/3/2021 quy định thực hiện Bộ luật Dân sự về bảo đảm thực hiện nghĩa vụ*.

Quốc hội. (2005). *Luật Thương mại số 36/2005/QH11*.

Quốc hội. (2015). *Bộ luật Dân sự số 91/2015/QH13*.

**Sách và bài báo khoa học**

Baumol, W. J. (1952). The transactions demand for cash: An inventory theoretic approach. *The Quarterly Journal of Economics, 66*(4), 545–556.

Brealey, R. A., Myers, S. C., & Allen, F. (2020). *Principles of corporate finance* (13th ed.). McGraw-Hill Education.

Brigham, E. F., & Ehrhardt, M. C. (2017). *Financial management: Theory & practice* (15th ed.). Cengage Learning.

Few, S. (2013). *Information dashboard design: Displaying data for at-a-glance monitoring* (2nd ed.). Analytics Press.

Gaur, V., Fisher, M. L., & Raman, A. (2005). An econometric analysis of inventory turnover performance in retail services. *Management Science, 51*(2), 181–194.

Kaplan, R. S., & Norton, D. P. (1992). The balanced scorecard – Measures that drive performance. *Harvard Business Review, 70*(1), 71–79.

Knaflic, C. N. (2015). *Storytelling with data: A data visualization guide for business professionals*. Wiley.

Miller, M. H., & Orr, D. (1966). A model of the demand for money by firms. *The Quarterly Journal of Economics, 80*(3), 413–435.

Modigliani, F., & Miller, M. H. (1958). The cost of capital, corporation finance and the theory of investment. *The American Economic Review, 48*(3), 261–297.

Opler, T., Pinkowitz, L., Stulz, R., & Williamson, R. (1999). The determinants and implications of corporate cash holdings. *Journal of Financial Economics, 52*(1), 3–46.

Petersen, M. A., & Rajan, R. G. (1997). Trade credit: Theories and evidence. *The Review of Financial Studies, 10*(3), 661–691.

Richards, V. D., & Laughlin, E. J. (1980). A cash conversion cycle approach to liquidity analysis. *Financial Management, 9*(1), 32–38.

Ross, S. A., Westerfield, R. W., & Jordan, B. D. (2019). *Fundamentals of corporate finance* (12th ed.). McGraw-Hill Education.

Silver, E. A., Pyke, D. F., & Thomas, D. J. (2016). *Inventory and production management in supply chains* (4th ed.). CRC Press.

Stiglitz, J. E., & Weiss, A. (1981). Credit rationing in markets with imperfect information. *The American Economic Review, 71*(3), 393–410.
