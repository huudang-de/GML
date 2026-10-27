# Định hướng chung

Đúng hướng cần làm không phải “đổi model mạnh hơn”, mà là biến dữ liệu DW thành nguồn sự thật bắt buộc. Gemini, OpenAI và Claude đều có Structured Output/tool calling/citation, nhưng các tính năng này chỉ kiểm soát cấu trúc và luồng dữ liệu; chúng không tự bảo đảm số liệu đúng nếu ứng dụng vẫn cho model tự viết câu trả lời khi SQL rỗng. 

*   **Gemini:** tool calling & structured output
*   **OpenAI:** Structured Outputs
*   **Claude:** prompting & kiểm chứng

---

# Plan sửa chống ảo giác

## P0 — Chặn bịa số liệu bằng code, không chỉ prompt

1. **Chuẩn hóa kết quả SQL thành object có cấu trúc:**
```json
{
  "status": "ok | no_data | execution_error",
  "row_count": 0,
  "columns": [],
  "rows": [],
  "sql": "..."
}
```

2. **Thêm “hard gate” trước Synthesizer:**
    *   `no_data`: Không gọi LLM để phân tích số; trả câu cố định: *“Không có dữ liệu cho ngày 01/08/2026. Dữ liệu gần nhất là…”*
    *   `execution_error`: Không gọi LLM; hiển thị lỗi an toàn và SQL.
    *   `ok`: Mới cho LLM diễn giải.

3. **Cấm LLM tự tính hoặc tự thêm số:** Mọi con số trong câu trả lời phải được sinh từ rows bằng code, kèm nguồn cột/dòng. LLM chỉ viết diễn giải, cảnh báo và gợi ý hành động.

4. **Quản lý UI:** UI luôn hiển thị trạng thái dữ liệu, số dòng trả về, SQL và bảng kết quả. Không có bảng dữ liệu thì không được hiện “insight” định lượng.
*(Đây là phần quan trọng nhất; nó sẽ chặn ngay lỗi 850 triệu/620 triệu vừa gặp).*

## P1 — Làm SQL đúng ngữ nghĩa nghiệp vụ

1. **Tạo semantic/KPI registry:**
    *   Doanh thu thuần → `B02-DN_01`
    *   Định nghĩa đơn vị, thời điểm dữ liệu, công thức, bảng/cột hợp lệ.
    *   Quy tắc “tính đến ngày”, “so sánh kỳ”, “Top N”.

2. **Chạy truy vấn “probe” trước khi sinh SQL:** Lấy ngày khả dụng/mã KPI khả dụng. Với ví dụ vừa rồi, agent sẽ biết chỉ có 31/07 và 02/08, sau đó hỏi lại hoặc tự đề xuất ngày thay thế.

3. **Dùng SQL validator:**
    *   Chỉ `SELECT`, schema/bảng/cột allow-list.
    *   Top 10 bắt buộc là `LIMIT 10`, không bị prompt cố định ghi đè thành `LIMIT 100`.
    *   Kiểm tra `invoice_date =` và `invoice_date <=` theo semantic rule; câu “tính đến” không được hiểu là “phát sinh đúng ngày”.
    *   Chạy `EXPLAIN` và kiểm tra kết quả trước khi trả lời.
    *(Nghiên cứu Text-to-SQL gần đây cũng đi theo hướng “probe dữ liệu thật + rule-based verify”, thay vì chỉ để LLM tự sửa lỗi. VD: PV-SQL (ACL), MRSQLGen).*

## P2 — Kiểm chứng câu trả lời cuối

Buộc model trả JSON thay vì văn bản tự do:
```json
{
  "answer_type": "data_answer | no_data | clarification_needed | execution_error",
  "claims": [
    {
      "text": "Doanh thu là 850.000.000 VNĐ",
      "evidence": {"row": 0, "column": "doanh_thu"}
    }
  ],
  "recommendations": []
}
```

**Server sẽ từ chối response nếu:**
*   Có số nhưng không có evidence.
*   `row_count = 0` mà `answer_type = data_answer`.
*   Claim không khớp kết quả SQL.
*   Câu trả lời dùng ngày/mã KPI ngoài dữ liệu trả về.
*(Gemini hỗ trợ output JSON theo schema; đây phù hợp để áp dụng ngay với model hiện tại. Gemini Structured Output).*

## P3 — Bộ kiểm thử và giám sát

**Lập bộ 40–60 câu nghiệp vụ có đáp án đã được kế toán/data team xác nhận, bao gồm:**
*   Ngày không tồn tại như 01/08/2026.
*   KPI/mã không tồn tại.
*   Top 5/10.
*   “Tính đến ngày”.
*   So sánh hai kỳ.
*   Kết quả rỗng.
*   SQL chạy được nhưng sai nghĩa.

**Theo dõi 4 chỉ số:**
1. Tỷ lệ số liệu không có bằng chứng: mục tiêu 0%.
2. Tỷ lệ truy vấn rỗng được trả đúng dạng `no_data`: 100%.
3. Tỷ lệ SQL đúng nghiệp vụ.
4. Tỷ lệ model yêu cầu làm rõ khi dữ liệu mơ hồ.
*(Google cũng khuyến nghị đánh giá groundedness trên bộ dữ liệu có đánh giá người dùng/chuyên gia, không chỉ dựa vào cảm nhận. Vertex AI evaluation & groundedness).*

---

# Nhật ký Triển khai

> **Kế hoạch:** Mình sẽ triển khai theo thứ tự P0 → P1 → P2 → P3, tách thành các hạng mục nhỏ. Mỗi hạng mục sẽ có test ngay sau khi sửa; chỉ commit khi toàn bộ test liên quan đã đạt. Trước hết mình kiểm tra trạng thái mã và test hiện có để không ghi đè thay đổi của bạn.

*   `[Ran commands]`
*   **Audit Task 1:** Hoàn tất. Chưa có unit test chống ảo giác; luồng hiện tại đưa chuỗi rỗng vào LLM rồi vẫn bắt LLM viết báo cáo. Bắt đầu P0: chuẩn hóa trạng thái thực thi SQL và thêm nhánh trả lời cố định cho `no_data`/`execution_error`, không gọi model ở hai trường hợp này.
*   `[Edited files, ran a command]`
*   **P0 Update 1:** Đã hoàn tất phần mã và 3/3 unit test đạt: SQL rỗng → `no_data`; lỗi SQL → `execution_error`; có dòng dữ liệu → mới được tổng hợp. Mình sẽ khởi động lại API và chạy test tích hợp đúng case ngày 01/08 để xác nhận agent không còn gọi LLM và không thể bịa số.
*   `[Ran commands]`
*   **P0 Update 2:** Test tích hợp vẫn trả về response cũ (không có `answer_type`), nghĩa là request đang đi vào tiến trình API cũ, không phải mã P0 vừa sửa. Mình sẽ xác định đúng PID đang giữ cổng 8000, dừng riêng tiến trình đó rồi chạy lại API mới trước khi kết luận P0 đạt.
*   `[Ran commands] - Worked for 4m 38s`
*   **P0 Update 3 (Thành công):** P0 test tích hợp đã đạt: cùng câu hỏi ngày 01/08 giờ trả `answer_type=no_data`, `row_count=0`, không còn bất kỳ số doanh thu nào. 

> **Next Step:** Sang P1, mình sẽ thêm validator SQL (chỉ cho phép SELECT, chặn nhiều câu lệnh/DML) và ép đúng Top N; đồng thời truy vấn rỗng sẽ trả về các ngày dữ liệu khả dụng gần nhất thay vì để người dùng đoán.