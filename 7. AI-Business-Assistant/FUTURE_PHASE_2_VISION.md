# KIẾN TRÚC TỔNG THỂ: AI BUSINESS ASSISTANT & GLOBAL OPTIMIZER
**(Hệ thống Trợ lý Ra quyết định và Phân bổ Vốn lưu động Toàn cục)**

Để trả lời được những câu hỏi chiến lược như: *"Tiền đang kẹt, hàng đang tồn, có nên nhận dự án mới không và xoay tiền từ đâu?"*, chúng ta phải nâng cấp mô hình từ **Tối ưu cục bộ (Local)** lên **Tối ưu toàn cục (Global)**. 

Dưới đây là thiết kế Kiến trúc 3 Lớp (3-Tier Architecture) biến AI thành một "Giám đốc Tài chính thực thụ" (Agentic CFO).

---

## LỚP 1: BỘ NÃO GIAO TIẾP (AGENTIC ORCHESTRATOR)
Đây là "Giao diện" và "Người phân xử" của hệ thống (Sử dụng LLM - Large Language Model như GPT-4/Claude kết hợp với LangChain/AutoGen).

- **Intent Recognition (Nhận diện ý định):** Khi CFO hỏi *"Tại sao công nợ tháng này giảm?"*, AI nhận diện đây là câu hỏi **Giải thích (Descriptive)**. Nó sẽ kích hoạt Tool số 1 (Text-to-SQL) để query vào database và trả lời: *"Do đã áp dụng Factoring bán nợ 5 tỷ cho ngân hàng A"*.
- **Scenario Planning (Lập kế hoạch):** Khi CFO hỏi *"Xoay 10 tỷ cho dự án mới như nào?"*, AI nhận diện đây là câu hỏi **Điều phối (Prescriptive)**. Nó sẽ kích hoạt Tool số 2 (Global Optimizer).

---

## LỚP 2: BỘ MÁY TỐI ƯU HÓA TOÀN CỤC (MILP - GLOBAL OPTIMIZER TOOL)
Đây chính là trái tim của việc "Phân bổ luân chuyển". Thay vì chỉ giải bài toán đi vay, chúng ta lập trình một mô hình **Quy hoạch tuyến tính nguyên hỗn hợp (Mixed-Integer Linear Programming - MILP)**.

Trong mô hình này, mọi thứ đều có thể mang ra "bán" hoặc "cầm cố" với một mức giá (Cost of Capital).

### A. Hàm Mục Tiêu (Objective Function)
**Tối đa hóa Lợi nhuận Ròng (Max Net Profit):**
`Max (Lợi nhuận từ Dự án mới) - (Chi phí huy động vốn tổng hợp)`

### B. Các Biến Quyết Định Luân Chuyển (Decision Variables)
AI sẽ tự động dò tìm tỷ lệ pha trộn tốt nhất giữa 4 hành động:
1. **$Vay\_Ngan\_Hang$:** Đi vay (Chi phí = Lãi suất vay 4% - 8%).
2. **$Ban\_No\_AR (Factoring)$:** Bán các khoản Phải thu cho Ngân hàng (Chi phí = Tỷ lệ chiết khấu thương phiếu, vd: 7%).
3. **$Xa\_Kho\_Inventory$:** Bán tống bán tháo hàng tồn kho chậm luân chuyển để thu tiền mặt (Chi phí = Tỷ lệ giảm giá, vd: 10%).
4. **$Chiem\_Dung\_AP$:** Khất nợ Nhà cung cấp (Chi phí = Phạt trễ hạn hoặc mất chiết khấu thanh toán sớm, vd: 2%).
5. **$Accept\_Project$:** Biến nhị phân (0 hoặc 1) quyết định có làm dự án mới hay không.

### C. Cơ chế Ra quyết định (Decision Engine Logic)
Nếu dự án mới mang lại Tỷ suất sinh lời (IRR) là **15%**. AI sẽ kích hoạt bài toán vét cạn:
- Cắm sổ tiết kiệm vay được 3 Tỷ (Chi phí 4%). 
- Bán nợ (Factoring) thu được 4 Tỷ (Chi phí 7%).
- Khất nợ nhà cung cấp được 3 Tỷ (Chi phí 2%).
=> **Chi phí vốn bình quân (WACC)** cho 10 Tỷ này chỉ là **4.6%**. 
=> Vì **15% (IRR) > 4.6% (WACC)**, AI ra lệnh: **"CHẤP NHẬN DỰ ÁN MỚI"** và in ra Kế hoạch Luân chuyển chính xác 3 bước trên.
- Ngược lại, nếu hết hạn mức vay, hết nợ tốt để bán, bắt buộc phải Xả hàng tồn kho với giá lỗ 20% (Chi phí 20%) -> WACC vọt lên 18%. AI lập tức ra lệnh: **"TỪ CHỐI DỰ ÁN, CHI PHÍ VỐN QUÁ ĐẮT"**.

---

## LỚP 3: LỚP DỮ LIỆU ĐỘNG (DYNAMIC DATA LAYER)
Để Lớp 2 chạy được, nó lấy Input từ chính 3 dự án cũ của chúng ta:
- **Tồn kho:** AI gọi bảng `silver.fact_reorder_recommendations` để biết nhóm hàng nào đang tồn kho > 90 ngày (Aging Inventory). Chỉ cho phép "Xả kho" nhóm hàng này.
- **Công nợ:** AI gọi bảng `silver.fact_ar_risk_score`. Chỉ cho phép bán nợ (Factoring) những hồ sơ có tỷ lệ rủi ro thấp (Ngân hàng mới mua).
- **Dòng tiền:** Gọi bảng `gold.fact_cashflow_forecast` để tính ra điểm đứt gãy vốn.

---

## TỔNG KẾT BỨC TRANH (THE BIG PICTURE)
Kiến trúc này nâng tầm Hệ thống từ một cái "Máy dự báo" thành một **Bộ não Điều phối Chuỗi cung ứng Tài chính (Supply Chain Finance Brain)**. 
- Nó không chỉ biết **Dòng tiền khó khăn**, mà nó biết **Lấy tiền từ Tồn kho hay Công nợ ra để vá vào Dòng tiền**.
- Nó không chỉ giải thích **Tại sao**, mà nó đưa ra **Kịch bản Hành động bằng Ngôn ngữ Tự nhiên** (Ví dụ: Soạn sẵn email xin khất nợ Nhà cung cấp, hoặc Soạn sẵn lệnh Xả hàng tồn kho đưa cho Giám đốc Kinh doanh).
