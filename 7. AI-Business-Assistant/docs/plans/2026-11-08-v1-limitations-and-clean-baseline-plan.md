# Kế hoạch Hoàn thiện Phân tích Giới hạn v1 & Chuẩn hóa Baseline v1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung phân tích giới hạn kiến trúc v1 vào tài liệu kế hoạch v1 (`AI_Business_Assistant_v1_Plan.md`), dọn dẹp và chuẩn hóa mã nguồn v1 thành bản Baseline nguyên bản sạch sẽ, sau đó đóng băng bằng Git tag `v1.0-baseline` làm mốc đối chứng khoa học cho v2.

**Architecture:** Giữ nguyên v1 làm mốc lịch sử không sửa đổi (Frozen Baseline). Bổ sung tài liệu giải thích nguyên nhân gốc rễ (Root Cause) của lỗi ảo giác và giới hạn cấu trúc. Chuẩn bị môi trường độc lập cho `v2/` để bắt đầu Phase 1 với source code mới 100%.

**Tech Stack:** Git, Markdown, Python 3.10+, LangChain, FastAPI.

**Spec:** [docs/AI_Business_Assistant_v1_Plan.md](docs/AI_Business_Assistant_v1_Plan.md) và [docs/AI_Business_Assistant_v2_Plan.md](docs/AI_Business_Assistant_v2_Plan.md).

## Global Constraints
- Không làm gãy khả năng khởi chạy của v1 hiện tại (v1 vẫn phải import và chạy được khi cần kiểm tra đối chứng).
- Giữ nguyên các tài liệu tham khảo nghiên cứu lỗi trong thư mục `Tài liệu tham khảo/` để làm bằng chứng thực nghiệm cho khóa luận.
- Mọi tài liệu bổ sung phải bám sát ngôn ngữ và văn phong của dự án Gỗ Minh Long.

## Review Focus
1. Phân tích giới hạn v1 phải trung thực, chỉ rõ 4 rào cản kiến trúc (thiếu Semantic Layer, thiếu AST Parser, luồng `both` bị đứt, và rủi ro khi vá chắp vá).
2. Mã nguồn v1 sau khi làm sạch phải chạy được các lệnh cơ bản mà không bị lỗi thiếu file hoặc xung đột import.
3. Git tag `v1.0-baseline` được tạo đúng vị trí để vĩnh viễn lưu vết mốc xuất phát của đồ án.

---

### Task 1: Bổ sung Mục 9 "Giới hạn Kiến trúc & Bài học kinh nghiệm" vào cuối `AI_Business_Assistant_v1_Plan.md`

**Files:**
- Modify: `7. AI-Business-Assistant/docs/AI_Business_Assistant_v1_Plan.md:535-546`

**Interfaces:**
- Consumes: Báo cáo thực nghiệm lỗi ảo giác và các phân tích giới hạn kiến trúc từ Plan v2.
- Produces: Mục 9 đầy đủ, đóng vai trò là cơ sở khoa học (Scientific Justification) cho sự ra đời của v2.

- [ ] **Step 1: Soạn thảo nội dung Mục 9 cho `AI_Business_Assistant_v1_Plan.md`**
  - Nội dung bao gồm:
    - 9.1 Hiện tượng ảo giác số liệu (Hallucination) trong quá trình thử nghiệm thực tế.
    - 9.2 Bốn giới hạn kiến trúc cốt lõi của phiên bản v1:
      1. *Thiếu Lớp ngữ nghĩa (Semantic Layer):* CSDL kho dữ liệu phức tạp nhưng prompt chỉ cung cấp schema thô; LLM phải tự đoán mã tài khoản kế toán (111, 112, 341).
      2. *Thiếu bộ kiểm tra cú pháp AST (AST Parser):* An toàn CSDL chỉ dựa vào dặn dò trong prompt (dễ bị vượt qua hoặc sinh sai cú pháp PostgreSQL).
      3. *Đồ thị điều phối sơ khai:* Nhánh `both` bị rẽ nhánh lỗi (chỉ chạy SQL rồi nhảy thẳng vào Synthesizer mà bỏ qua RAG).
      4. *Bẫy "chắp vá giải pháp" (~30% Patching Trap):* Việc cố gắng cài cắm `sql_contracts.py` vào v1 gây nợ kỹ thuật và code lai tạp, không giải quyết được gốc rễ bài toán.
    - 9.3 Quyết định chiến lược: Đóng băng `v1.0` làm Baseline đối chứng và xây mới toàn diện phiên bản `v2.0` (chuẩn L5).

- [ ] **Step 2: Cập nhật tệp `AI_Business_Assistant_v1_Plan.md`**
  - Ghi nội dung vào cuối tệp sau Mục 8.

- [ ] **Step 3: Kiểm tra định dạng Markdown và tính nhất quán**
  - Đảm bảo các đề mục, bảng biểu và danh sách hiển thị chuẩn mực.

---

### Task 2: Chuẩn hóa và làm sạch mã nguồn v1 (Clean Baseline v1)

**Files:**
- Modify: `7. AI-Business-Assistant/app/agents/orchestrator.py`
- Modify: `7. AI-Business-Assistant/app/agents/sql_agent.py`
- Modify: `7. AI-Business-Assistant/app/api/main.py`
- Clean/Archive: Giữ hoặc tách riêng các file giải pháp chắp vá không thuộc bản chất v1 nguyên bản.

**Interfaces:**
- Consumes: Mã nguồn hiện tại trong `app/`.
- Produces: Thư mục `app/` đại diện chính xác cho phiên bản v1 chuẩn (nguyên bản, hoạt động ổn định, không lai tạp).

- [ ] **Step 1: Rà soát các thay đổi chắp vá ở commit `70da479`**
  - Kiểm tra `sql_contracts.py` và các chốt chặn thử nghiệm trong `orchestrator.py` và `sql_agent.py`.
  - Giữ lại các cải tiến ổn định về model Gemini Flash, loại bỏ các đoạn code lai tạp chưa hoàn chỉnh.

- [ ] **Step 2: Chạy kiểm thử xác nhận v1 hoạt động ổn định**
  - Kiểm tra import tất cả các agent trong v1:
    `python -c "from app.agents.orchestrator import OrchestratorAgent; print('Orchestrator v1 OK')"`

---

### Task 3: Đóng băng Git và gắn thẻ `v1.0-baseline`

**Files:**
- Git repository tracking.

- [ ] **Step 1: Kiểm tra trạng thái Git**
  - Chạy: `git status`

- [ ] **Step 2: Commit các thay đổi hoàn thiện tài liệu v1**
  - Chạy:
    ```bash
    git add docs/AI_Business_Assistant_v1_Plan.md app/
    git commit -m "docs(ai-assistant): document v1 architectural limitations and freeze clean baseline"
    ```

- [ ] **Step 3: Tạo Git tag `v1.0-baseline`**
  - Chạy:
    ```bash
    git tag -a v1.0-baseline -m "Release v1.0 Baseline: Original functional implementation with documented architectural limits"
    ```

- [ ] **Step 4: Xác nhận hoàn tất và sẵn sàng cho Phase 1 (Xây mới v2 trong `v2/`)**
  - Xuất log xác nhận tag đã được tạo thành công.

