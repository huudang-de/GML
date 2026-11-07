# 📌 BÁO CÁO BÀN GIAO TIẾN ĐỘ & QUY TRÌNH (PROCEDURE STATUS & HANDOFF)

*Thời điểm ghi nhận: 07/11/2026 — Trạng thái: Đã lưu vết quy trình an toàn*

---

## 1. 🎯 Tóm tắt hiện trạng phiên làm việc

Trong phiên làm việc này, chúng ta đã hoàn thành 3 khối công việc trọng tâm trước khi gặp giới hạn quota của mô hình Claude:

1. **Hợp nhất thành công 2 file tài liệu kế hoạch thành 1:**
   - **Tệp đích:** [`docs/AI_Business_Assistant_v2_Plan.md`](AI_Business_Assistant_v2_Plan.md) (1.154 dòng).
   - Nội dung gốc được giữ nguyên 100% (đã đối soát script kiểm tra không lệch một dòng), cấu trúc gồm Phần I (Kế hoạch phát triển) và Phần II (Thiết kế v2.0 chuẩn L5), bổ sung bảng đối chiếu chéo (Cross-reference matrix).
   - Tệp cũ `AI Business Assistant – Gỗ Minh Long Thiết kế v2.0 (chuẩn L5).md` đã được dọn dẹp (vẫn lưu vết an toàn trong Git).

2. **Khảo sát toàn diện tài sản sẵn có (Folder 1 → 5):**
   - Đã xác định kho dữ liệu PostgreSQL Star Schema (schema `silver`), 5 file SQL UAT đã đối soát khớp 100% với MISA, 5 cẩm nang Dashboard, và tài liệu Storytelling C-level.
   - Thống nhất bỏ qua nhánh `6. ML` do thiếu chuỗi thời gian lịch sử dài hạn (data shortage).

3. **Thiết kế kiến trúc chi tiết từng tầng (Floor-by-Floor Architecture):**
   - **Tệp mới tạo:** [`docs/AI_Business_Assistant_v2_Architecture_Detail.md`](AI_Business_Assistant_v2_Architecture_Detail.md)
   - **Đã chốt Phương án B (Chiến lược dữ liệu lai - Hybrid Strategy):**
     - Dữ liệu **Real (`silver`)**: Dùng cho SQL Agent, RAG, Security, lấy đáp án chuẩn đối chiếu trực tiếp từ RESULT LOG của UAT (G-01 đến G-11...).
     - Dữ liệu **Synthetic 12 tháng (`synthetic`)**: Dùng cho Trend Analyst, Alert Engine, Weekly Brief với các bất thường được dán nhãn kiểm soát sẵn.
   - Thiết kế chi tiết **8 tầng (T1 đến T8)** kèm mã Test Case (`TC-T<n>-xx`), 22 Phép đo định lượng (`M-01` đến `M-22`), 11 kịch bản nghiệm thu đầu-cuối (`E2E-01` đến `E2E-11`), và Sổ đăng ký bằng chứng chuẩn L5 (`EV-01` đến `EV-27`).
   - Lộ trình 12 tuần (Phase 0 đến Phase 6) có cổng kiểm soát chất lượng rõ ràng.

---

## 2. 📁 Danh mục các tệp tài liệu quan trọng đã tạo / cập nhật

| Tệp tin | Trạng thái | Mô tả |
| :--- | :--- | :--- |
| [`docs/AI_Business_Assistant_v2_Plan.md`](AI_Business_Assistant_v2_Plan.md) | Đã cập nhật (Modified) | Bản quy hoạch v2.0 hợp nhất toàn diện. |
| [`docs/AI_Business_Assistant_v2_Architecture_Detail.md`](AI_Business_Assistant_v2_Architecture_Detail.md) | Mới tạo (Untracked) | Tài liệu kiến trúc 8 tầng, test case, gold UAT, phép đo & bằng chứng L5. |
| `scratch/merge_docs.py` | Đã lưu | Script đối soát kiểm tra tính toàn vẹn khi gộp tài liệu. |

---

## 3. 🚦 Các quyết định kỹ thuật đã thống nhất (Decisions Locked)

1. **Quy tắc đáp án UAT thắng:** Khi có mâu thuẫn số liệu minh họa, số liệu trong RESULT LOG của 5 file UAT (`5. Kiểm thử/UAT/`) luôn là chân lý (Ground Truth) cho các bài test dữ liệu thật [R].
2. **Chiến lược tách biệt DB Real & Synthetic:** Khuyến nghị dùng 2 database riêng biệt (`gml` và `gml_synth`) để tránh tuyệt đối rủi ro JOIN nhầm dữ liệu thật với dữ liệu mô phỏng.
3. **Trend Agent trên dữ liệu thật:** Khi `data_coverage` < 6 tháng (như doanh thu chỉ có T7/2026), hệ thống phải trung thực cảnh báo thiếu dữ liệu lịch sử chứ không tự suy diễn MoM/YoY.
4. **Không dùng LLM để tính toán số tài chính:** Alert Engine và tính toán KPI tự động hoàn toàn sử dụng SQL mẫu đã kiểm chứng (Golden Query), LLM chỉ làm nhiệm vụ diễn đạt văn phong.

---

## 4. 📋 Kế hoạch bước tiếp theo (Next Action Items khi quay lại)

Khi bạn muốn tiếp tục dự án AI Business Assistant (sau khi reset quota hoặc khi rảnh):

- [ ] **Bước 1 — Xem & Duyệt tài liệu kiến trúc:** Đọc lướt qua [`docs/AI_Business_Assistant_v2_Architecture_Detail.md`](AI_Business_Assistant_v2_Architecture_Detail.md) và xác nhận phê duyệt (hoặc điều chỉnh nếu muốn).
- [ ] **Bước 2 — Chuyển sang lập kế hoạch triển khai (Plan Mode):** Kích hoạt skill `superpowers:writing-plans` để bẻ nhỏ **Phase 0 (Baseline v1 & Benchmark 60 câu)** và **Phase 1 (Data & Security - `roles.sql`, `views.sql`, AST validator)** thành danh sách công việc chi tiết dạng commit/TDD.
- [ ] **Bước 3 — Triển khai mã nguồn (Execution):** Bắt đầu code từng bước theo Test-Driven Development (TDD), tạo bằng chứng `EV-xx` đến đâu lưu vào `eval/reports/` đến đó.

---

## 5. 💡 Trạng thái Git khuyến nghị

Để đảm bảo an toàn tuyệt đối cho mã nguồn và tài liệu hiện tại, bạn có thể thực hiện lệnh commit lưu vết:
```powershell
git add docs/
git commit -m "docs(ai-assistant): merge v2 plans and add floor-by-floor architecture specification"
```
*(Nếu bạn chưa muốn commit ngay thì toàn bộ các tệp vẫn đang nằm nguyên vẹn trên ổ cứng cục bộ).*

