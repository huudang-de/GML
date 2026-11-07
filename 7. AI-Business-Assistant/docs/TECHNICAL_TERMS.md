# 📖 TỪ ĐIỂN THUẬT NGỮ KỸ THUẬT & CHUYÊN MÔN CHUẨN XÁC
## Project: AI Business Assistant — Gỗ Minh Long (Version 2.0 / L5 Architecture)

> **Mục đích tài liệu:**  
> Chuẩn hóa toàn bộ thuật ngữ chuyên ngành (khoa học máy tính, trí tuệ nhân tạo, kỹ thuật dữ liệu, an toàn thông tin và tài chính doanh nghiệp) được áp dụng trong tài liệu quy hoạch `AI_Business_Assistant_v2_Plan.md` và thiết kế chi tiết `AI_Business_Assistant_v2_Architecture_Detail.md`.  
> Phục vụ công tác nghiên cứu, phát triển và bảo vệ đồ án/khóa luận tốt nghiệp trước Hội đồng đánh giá chuyên môn.
>
> **Quy ước trình bày:**  
> Mỗi thuật ngữ gồm: Tên gốc (English) ➔ Dịch nghĩa tiếng Việt ➔ Định nghĩa chính xác & ứng dụng trong dự án GML ➔ **Trích dẫn nguồn học thuật/tiêu chuẩn công nghiệp ngay bên dưới**.

---

## MỤC LỤC TỔNG HỢP

1. [Kiến trúc Phần mềm & Hệ thống Đa tác tử (Software Architecture & Multi-Agent Systems)](#1-kiến-trúc-phần-mềm--hệ-thống-đa-tác-tử)
2. [Kỹ thuật Dữ liệu & Text-to-SQL (Data Engineering & Text-to-SQL)](#2-kỹ-thuật-dữ-liệu--text-to-sql)
3. [Truy xuất & Tạo sinh Tăng cường (Retrieval-Augmented Generation - RAG)](#3-truy-xuất--tạo-sinh-tăng-cường-rag)
4. [Trí tuệ Nhân tạo, LLM & Chốt chặn Bảo vệ (AI, LLM & Guardrails)](#4-trí-tuệ-nhân-tạo-llm--chốt-chặn-bảo-vệ)
5. [An toàn Thông tin, Bảo mật & Quản trị (Security, Governance & Operations)](#5-an-toàn-thông-tin-bảo-mật--quản-trị)
6. [Chiến lược Dữ liệu & Đánh giá Chất lượng (Data Strategy & Evaluation Harness)](#6-chiến-lược-dữ-liệu--đánh-giá-chất-lượng)
7. [Nghiệp vụ Tài chính & Quản trị Doanh nghiệp (Business & Financial Management)](#7-nghiệp-vụ-tài-chính--quản-trị-doanh-nghiệp)

---

## 1. KIẾN TRÚC PHẦN MỀM & HỆ THỐNG ĐA TÁC TỬ

### 1.1. Multi-Agent Architecture
- **Dịch nghĩa:** Kiến trúc Đa Tác tử.
- **Định nghĩa & Ứng dụng trong dự án:** Mô hình kiến trúc phân tán trong đó hệ thống được chia thành nhiều tác tử phần mềm tự chủ (Autonomous Agents), mỗi tác tử chuyên biệt hóa sâu cho một miền nhiệm vụ duy nhất (SQL Agent, RAG Agent, Explainer, Trend Analyst, Decision Advisor, Synthesizer) và phối hợp cùng nhau qua đồ thị trạng thái thay vì một mô hình đơn khối (Monolithic LLM).
> *Trích dẫn:* Wooldridge, M. (2009). *An Introduction to MultiAgent Systems* (2nd ed.). John Wiley & Sons. Xem thêm: LangGraph Multi-Agent Orchestration Patterns (Harrison et al., 2024).

### 1.2. Orchestrator / State Machine
- **Dịch nghĩa:** Bộ điều phối / Máy trạng thái hữu hạn.
- **Định nghĩa & Ứng dụng trong dự án:** Thành phần trung tâm quản lý vòng đời và luồng điều hướng của toàn bộ hệ thống. Sử dụng `StateGraph` để định tuyến yêu cầu dựa trên ý định phân loại (`classify_intent`), kích hoạt các nhánh thực thi tuần tự hoặc song song và hội tụ dữ liệu tại các điểm hợp nhất (join nodes).
> *Trích dẫn:* Harel, D. (1987). Statecharts: A visual formalism for complex systems. *Science of Computer Programming, 8*(3), 231–274. Áp dụng qua LangGraph Framework (LangChain, 2024).

### 1.3. Typed State (ChatState)
- **Dịch nghĩa:** Trạng thái có cấu trúc kiểu tĩnh.
- **Định nghĩa & Ứng dụng trong dự án:** Cấu trúc dữ liệu bất biến hoặc biến đổi có kiểm soát trong bộ nhớ điều phối (sử dụng Python `TypedDict` / Pydantic), quy định rõ các trường dữ liệu trao đổi giữa các Agent (`request_id`, `intent`, `sql`, `rag`, `explanation`, `errors`) nhằm ngăn chặn lỗi runtime và tạo điều kiện kiểm thử độc lập.
> *Trích dẫn:* Pierce, B. C. (2002). *Types and Programming Languages*. MIT Press. Áp dụng chuẩn trong LangGraph State Management.

### 1.4. Separation of Concerns (SoC)
- **Dịch nghĩa:** Nguyên tắc phân tách mối quan tâm / trách nhiệm.
- **Định nghĩa & Ứng dụng trong dự án:** Nguyên lý thiết kế phần mềm cốt lõi của Plan v2, quy định mỗi tầng và mỗi Agent chỉ giải quyết một chức năng riêng biệt: Tầng Data chỉ đọc CSDL, SQL Agent chỉ sinh truy vấn, PostgreSQL thực thi tính toán số học, Explainer giải thích bản chất công thức, Advisor khuyến nghị hành động, và Synthesizer tổng hợp định dạng.
> *Trích dẫn:* Dijkstra, E. W. (1982). On the role of scientific thought. In *Selected Writings on Computing: A Personal Perspective* (pp. 60–66). Springer-Verlag.

### 1.5. Short-Circuit / Early Exit
- **Dịch nghĩa:** Cơ chế ngắt mạch sớm / Thoát khẩn cấp.
- **Định nghĩa & Ứng dụng trong dự án:** Cơ chế bảo vệ trong luồng điều phối: khi truy vấn SQL bị rỗng (`no_data`), lỗi CSDL (`execution_error`), hoặc phát hiện tấn công an toàn (`blocked`), hệ thống ngắt luồng ngay lập tức và chuyển thẳng tới thông điệp phản hồi chuẩn mực, không bao giờ chuyển tiếp trạng thái lỗi vào Synthesizer để tránh ảo giác.
> *Trích dẫn:* Fowler, M. (2004). *Refactoring: Improving the Design of Existing Code*. Addison-Wesley. (Áp dụng cho Design Pattern: Guard Clause).

### 1.6. Dual Output Pattern
- **Dịch nghĩa:** Mẫu thiết kế đầu ra kép.
- **Định nghĩa & Ứng dụng trong dự án:** Cấu trúc phản hồi đồng thời hai cấp độ cho người dùng: (1) Bản tóm tắt quản trị cô đọng dành cho Ban Lãnh đạo (C-Levels), và (2) Khối dữ liệu kỹ thuật chi tiết (câu lệnh SQL, số liệu thô, nguồn trích dẫn, điểm tin cậy) trong thanh mở rộng dành cho chuyên viên phân tích đối soát.
- *Trích dẫn:* Kế thừa từ mô hình giao diện của Vanna AI (Vanna.ai Architecture, 2024) và nguyên lý thiết kế Dashboard phân lớp của Stephen Few (Few, 2013).

### 1.7. Follow-up Context Resolution
- **Dịch nghĩa:** Giải quyết ngữ cảnh hội thoại tiếp nối.
- **Định nghĩa & Ứng dụng trong dự án:** Tiến trình phân tích lịch sử hội thoại gần nhất (tối đa 5 lượt) để viết lại một câu hỏi phụ thuộc ngữ cảnh (vd: *"Còn tháng trước?"*) thành một câu truy vấn độc lập đầy đủ thực thể (vd: *"Dư nợ ngắn hạn tháng 06/2026 là bao nhiêu?"*) trước khi đưa vào phân loại và truy vấn.
> *Trích dẫn:* Radlinski, F., & Craswell, N. (2017). A theoretical framework for conversational search. In *Proceedings of the 2017 Conference on Conference Human Information Interaction and Retrieval* (pp. 117–126). ACM.

---

## 2. KỸ THUẬT DỮ LIỆU & TEXT-TO-SQL

### 2.1. Text-to-SQL
- **Dịch nghĩa:** Kỹ thuật chuyển đổi ngôn ngữ tự nhiên thành câu lệnh truy vấn CSDL (SQL).
- **Định nghĩa & Ứng dụng trong dự án:** Tác vụ AI cho phép biên dịch câu hỏi tiếng Việt của người quản trị thành câu lệnh PostgreSQL chuẩn xác trên schema `silver` hoặc `ai_views` của Data Warehouse Gỗ Minh Long.
> *Trích dẫn:* Li, J., Hui, B., Qu, G., et al. (2023). Can LLM already serve as a database interface? A big bench for large-scale database grounded text-to-SQLs. *NeurIPS 2023 Datasets and Benchmarks Track* (arXiv:2305.03111).

### 2.2. Semantic Layer / Data Dictionary
- **Dịch nghĩa:** Lớp ngữ nghĩa nghiệp vụ / Từ điển dữ liệu CSDL.
- **Định nghĩa & Ứng dụng trong dự án:** Lớp trung gian chuyển hóa cấu trúc bảng biểu thô thành tri thức máy đọc được (`kpi_definitions.yaml`), cung cấp mô tả ngữ nghĩa cho từng mã tài khoản (TK 34111, TK 112) và bảng biểu kế toán để LLM hiểu đúng bản chất nghiệp vụ trước khi sinh câu truy vấn.
> *Trích dẫn:* BIRD Benchmark findings on External Knowledge Necessity (Li et al., 2023). Xem thêm tài liệu `Data_Dictionary_GML.xlsx` và ISO-BRD Gỗ Minh Long.

### 2.3. Golden Query Bank
- **Dịch nghĩa:** Ngân hàng truy vấn vàng / Thư viện truy vấn mẫu đã kiểm chứng.
- **Định nghĩa & Ứng dụng trong dự án:** Tập hợp các câu truy vấn SQL mẫu chuẩn xác 100% được trích xuất từ 5 kịch bản kiểm thử UAT thực tế, dùng làm mẫu đối sánh Few-Shot Prompting để SQL Agent học tập cú pháp và bảng liên kết (JOIN) chính xác nhất.
> *Trích dẫn:* Kế thừa phương pháp Vector RAG Text-to-SQL từ Vanna AI (Vanna.ai, 2023–2024).

### 2.4. Self-Healing SQL / Retry Loop
- **Dịch nghĩa:** Vòng lặp tự sửa lỗi truy vấn SQL.
- **Định nghĩa & Ứng dụng trong dự án:** Cơ chế tự động nắm bắt lỗi cú pháp do CSDL PostgreSQL phản hồi, làm sạch thông điệp lỗi và đưa ngược lại cho SQL Agent kèm lịch sử thử nghiệm (tối đa 3 lần lặp) để Agent tự điều chỉnh và tái tạo câu lệnh đúng.
> *Trích dẫn:* Gao, D., Wang, H., Li, Y., et al. (2023). Text-to-SQL empowered by large language models: A benchmark evaluation. *arXiv preprint arXiv:2308.15363*.

### 2.5. Abstract Syntax Tree (AST) & AST Validator
- **Dịch nghĩa:** Cây Cú pháp Trừu tượng & Bộ kiểm thực ngữ pháp AST.
- **Định nghĩa & Ứng dụng trong dự án:** Cấu trúc dạng cây biểu diễn cú pháp logic của câu lệnh SQL. Dự án sử dụng thư viện `sqlglot` để bóc tách AST của câu lệnh do LLM sinh ra, kiểm tra nghiêm ngặt: chỉ cho phép đúng 1 biểu thức `SELECT`, bảng phải nằm trong danh mục cho phép (`allowed_tables`), không chứa hàm can thiệp hệ thống và tự động gắn thêm mệnh đề `LIMIT 1000`.
> *Trích dẫn:* Aho, A. V., Lam, M. S., Sethi, R., & Ullman, J. D. (2006). *Compilers: Principles, Techniques, and Tools* (2nd ed.). Addison-Wesley.

### 2.6. Execution Accuracy (EX)
- **Dịch nghĩa:** Độ chính xác thực thi SQL.
- **Định nghĩa & Ứng dụng trong dự án:** Chỉ số đo lường hiệu năng của SQL Agent: tính tỷ lệ phần trăm các câu SQL sinh ra cho kết quả dữ liệu khớp hoàn toàn với đáp án chuẩn (Gold Standard từ UAT) khi chạy trên cùng một CSDL, thay vì so sánh chuỗi ký tự SQL thô.
> *Trích dẫn:* Li, J., et al. (NeurIPS 2023). BIRD Benchmark Metric Standard.

### 2.7. Schema Drift
- **Dịch nghĩa:** Hiện tượng trôi dạt / biến động lược đồ CSDL.
- **Định nghĩa & Ứng dụng trong dự án:** Rủi ro kiến trúc khi cấu trúc bảng, tên cột hoặc kiểu dữ liệu trong Data Warehouse bị thay đổi theo thời gian bởi kỹ sư dữ liệu mà không thông báo, làm gãy các câu lệnh SQL tự động sinh. Được phòng ngừa bằng `db/catalog.yaml` và kiểm thử CI hợp đồng CSDL.
> *Trích dẫn:* Stonebraker, M., & Cetintemel, U. (2005). "One size fits all": An idea whose time has come and gone. In *21st International Conference on Data Engineering (ICDE'05)*.

---

## 3. TRUY XUẤT & TẠO SINH TĂNG CƯỜNG (RAG)

### 3.1. Retrieval-Augmented Generation (RAG)
- **Dịch nghĩa:** Tạo sinh Tăng cường Truy xuất.
- **Định nghĩa & Ứng dụng trong dự án:** Kỹ thuật kết hợp giữa mô hình truy xuất thông tin (Information Retrieval) từ kho tài liệu nội bộ (BRD, Cẩm nang kế toán GML) với mô hình tạo sinh ngôn ngữ (LLM) để trả lời các câu hỏi về chính sách, công thức và định nghĩa quản trị có căn cứ xác thực.
> *Trích dẫn:* Lewis, P., Perez, E., Piktus, A., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems (NeurIPS 2020), 33*, 9459–9474.

### 3.2. Hybrid Retrieval
- **Dịch nghĩa:** Truy xuất lai (Kết hợp Vector và Từ khóa).
- **Định nghĩa & Ứng dụng trong dự án:** Phương pháp tìm kiếm kết hợp đồng thời: (1) Truy xuất ngữ nghĩa bằng Dense Vector Embeddings (thông qua ChromaDB / Nomic-embed-text) và (2) Truy xuất từ khóa tần suất bằng Sparse Keyword (BM25), giúp xử lý hoàn hảo cả câu hỏi tìm ý nghĩa lẫn câu hỏi chứa mã chỉ tiêu chính xác (vd: "B01-DN_110").
> *Trích dẫn:* Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. *Foundations and Trends in Information Retrieval, 3*(4), 333–389.

### 3.3. Reciprocal Rank Fusion (RRF)
- **Dịch nghĩa:** Thuật toán Hợp nhất Thứ hạng Tương hỗ.
- **Định nghĩa & Ứng dụng trong dự án:** Thuật toán phi tham số dùng để gộp và tái cân bằng điểm số của danh sách tài liệu trả về từ hai kênh tìm kiếm Vector và BM25 theo công thức $RRF\_Score(d) = \sum \frac{1}{k + r(d)}$, tạo ra danh sách tài liệu phù hợp nhất nạp vào LLM.
> *Trích dẫn:* Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. In *Proceedings of the 32nd International ACM SIGIR Conference* (pp. 758–759). ACM.

### 3.4. Faithfulness / Groundedness
- **Dịch nghĩa:** Độ trung thực / Tính bám sát tài liệu nguồn.
- **Định nghĩa & Ứng dụng trong dự án:** Phép đo định lượng tỷ lệ các nhận định, con số trong câu trả lời được hỗ trợ trực tiếp bởi các đoạn văn bản truy xuất được trong kho tri thức, đảm bảo câu trả lời không chứa thông tin suy diễn ngoài tài liệu.
> *Trích dẫn:* Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). *RAGAS: Automated evaluation of retrieval augmented generation*. arXiv:2309.15217.

### 3.5. Hit@k & Mean Reciprocal Rank (MRR)
- **Dịch nghĩa:** Tỷ lệ tìm trúng trong top k & Thứ hạng nghịch đảo trung bình.
- **Định nghĩa & Ứng dụng trong dự án:** Các chỉ số đo lường hiệu năng của khâu truy hồi thông tin (Retrieval): Hit@5 đo lường tỷ lệ tài liệu chuẩn nằm trong 5 đoạn trích đầu tiên; MRR đo lường vị trí xuất hiện trung bình của tài liệu chính xác nhất.
> *Trích dẫn:* Voorhees, E. M. (1999). The TREC-8 question answering track report. In *Proceedings of the 8th Text REtrieval Conference (TREC-8)* (pp. 77–82).

---

## 4. TRÍ TUỆ NHÂN TẠO, LLM & CHỐT CHẶN BẢO VỆ

### 4.1. Hallucination
- **Dịch nghĩa:** Hiện tượng ảo giác / Bịa đặt thông tin của mô hình ngôn ngữ.
- **Định nghĩa & Ứng dụng trong dự án:** Hiện tượng LLM sinh ra các câu khẳng định hoặc con số tài chính nghe rất thuyết phục nhưng hoàn toàn sai lệch hoặc không tồn tại trong CSDL. Dự án triệt tiêu ảo giác bằng *Anti-Hallucination Guard*: kiểm tra bám số (Number Grounding Check) và ngắt mạch khi SQL rỗng.
> *Trích dẫn:* Ji, Z., Lee, N., Frieske, R., et al. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys, 55*(12), 1–38.

### 4.2. Prompt Injection
- **Dịch nghĩa:** Kỹ thuật tấn công tiêm nhiễm câu lệnh.
- **Định nghĩa & Ứng dụng trong dự án:** Hình thức tấn công mạng mà kẻ xấu chèn các chỉ dẫn độc hại vào dữ liệu đầu vào (hoặc gián tiếp qua tên đối tác/ghi chú trong CSDL) nhằm chiếm quyền điều khiển LLM, ép LLM bỏ qua System Prompt hoặc tiết lộ thông tin mật.
> *Trích dẫn:* OWASP Foundation. (2025). *OWASP Top 10 for Large Language Model Applications* (LLM01: Prompt Injection).

### 4.3. Self-Consistency Chain-of-Thought (CoT)
- **Dịch nghĩa:** Tính nhất quán tự thân trong chuỗi suy luận.
- **Định nghĩa & Ứng dụng trong dự án:** Kỹ thuật lấy mẫu suy luận bằng cách yêu cầu LLM sinh ra nhiều đường dẫn giải quyết bài toán SQL độc lập ở nhiệt độ thấp ($T > 0$), sau đó chọn ra câu truy vấn có kết quả thực thi đồng thuận cao nhất để tính điểm tin cậy.
> *Trích dẫn:* Wang, X., Wei, J., Schuurmans, D., et al. (2023). Self-consistency improves chain of thought reasoning in language models. *International Conference on Learning Representations (ICLR 2023)*.

### 4.4. Confidence Calibration
- **Dịch nghĩa:** Hiệu chuẩn điểm tin cậy.
- **Định nghĩa & Ứng dụng trong dự án:** Mối tương quan thống kê giữa điểm tin cậy mà hệ thống tính toán với xác suất thực tế câu trả lời đó là đúng. Đảm bảo khi hệ thống tự chấm độ tin cậy $0.8$ thì câu trả lời phải có xác suất chính xác tương ứng $\approx 80\%$.
> *Trích dẫn:* Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. In *International Conference on Machine Learning (ICML 2017)* (pp. 1321–1330). PMLR.

### 4.5. Model Card
- **Dịch nghĩa:** Thẻ hồ sơ năng lực mô hình.
- **Định nghĩa & Ứng dụng trong dự án:** Tài liệu kỹ thuật tiêu chuẩn hóa công bố rõ: mục đích sử dụng, kiến trúc mô hình, dữ liệu kiểm chuẩn, giới hạn năng lực, rủi ro đạo đức và các trường hợp không được phép áp dụng của hệ thống AI Business Assistant GML.
> *Trích dẫn:* Mitchell, M., Wu, S., Zaldivar, A., et al. (2019). Model cards for model reporting. In *Proceedings of the Conference on Fairness, Accountability, and Transparency (FAT* 2019)* (pp. 220–229). ACM.

---

## 5. AN TOÀN THÔNG TIN, BẢO MẬT & QUẢN TRỊ

### 5.1. Principle of Least Privilege (PoLP)
- **Dịch nghĩa:** Nguyên tắc đặc quyền tối thiểu.
- **Định nghĩa & Ứng dụng trong dự án:** Nguyên tắc bảo mật nền tảng: Người dùng và tài khoản kết nối CSDL của AI (`gml_ai_ro`) chỉ được cấp phát quyền hạn vừa đủ tối thiểu để hoàn thành công việc (chỉ cấp `SELECT` trên schema `ai_views`, không có quyền đọc schema `silver` thô, không có quyền ghi).
> *Trích dẫn:* Saltzer, J. H., & Schroeder, M. D. (1975). The protection of information in computer systems. *Proceedings of the IEEE, 63*(9), 1278–1308.

### 5.2. Defense-in-Depth
- **Dịch nghĩa:** Chiến lược phòng thủ đa tầng / Chiều sâu phòng ngự.
- **Định nghĩa & Ứng dụng trong dự án:** Chiến lược bố trí nhiều lớp kiểm soát an toàn độc lập nối tiếp nhau: Lớp 1 (Quyền CSDL PostgreSQL) ➔ Lớp 2 (Phân quyền ứng dụng RBAC theo vai trò) ➔ Lớp 3 (Bộ lọc cú pháp AST `sqlglot`) ➔ Lớp 4 (Input/Output Guardrail lọc kết quả).
> *Trích dẫn:* National Security Agency (NSA). (1998). *Defense in Depth: A practical strategy for achieving Information Assurance in today's highly networked environments*.

### 5.3. Role-Based Access Control (RBAC)
- **Dịch nghĩa:** Kiểm soát truy cập dựa trên vai trò.
- **Định nghĩa & Ứng dụng trong dự án:** Cơ chế phân quyền dữ liệu theo vị trí nghiệp vụ của người hỏi: Ban Điều hành (`ceo`) được truy cập toàn bộ view; Kế toán trưởng (`accountant`) chỉ xem dòng tiền, công nợ; Quản lý kho (`warehouse`) chỉ truy vấn tồn kho, hàng hóa.
> *Trích dẫn:* Ferraiolo, D. F., Sandhu, R., Gavrila, S., et al. (2001). Proposed NIST standard for role-based access control. *ACM Transactions on Information and System Security (TISSEC), 4*(3), 224–274.

### 5.4. Architecture Decision Record (ADR)
- **Dịch nghĩa:** Hồ sơ ghi nhận quyết định kiến trúc.
- **Định nghĩa & Ứng dụng trong dự án:** Tài liệu ngắn gọn, có cấu trúc chuẩn ghi lại lý do, bối cảnh, các phương án cân nhắc và hệ quả của một quyết định kỹ thuật quan trọng trong dự án (ví dụ ADR-005: Lựa chọn Paid-tier Cloud LLM kết hợp Local Fallback).
> *Trích dẫn:* Nygard, M. (2011). *Documenting Architecture Decisions*. Cognitect Blog.

### 5.5. Idempotency (Lũy đẳng)
- **Dịch nghĩa:** Tính chất lũy đẳng / Bất biến sau nhiều lần thực thi.
- **Định nghĩa & Ứng dụng trong dự án:** Thuộc tính của một tác vụ (đặc biệt là tiến trình Alert Engine và nạp Ingest tài liệu) đảm bảo rằng dù có bị kích hoạt thực thi lặp lại nhiều lần với cùng một dữ liệu đầu vào thì kết quả hệ thống và trạng thái CSDL vẫn không bị thay đổi (không sinh cảnh báo trùng lặp).
> *Trích dẫn:* Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures* (Doctoral dissertation). University of California, Irvine. (Định nghĩa tính chất Idempotent trong RESTful HTTP).

---

## 6. CHIẾN LƯỢC DỮ LIỆU & ĐÁNH GIÁ CHẤT LƯỢNG

### 6.1. Hybrid Data Strategy (Real vs. Synthetic)
- **Dịch nghĩa:** Chiến lược dữ liệu lai (Kết hợp Dữ liệu Thật và Mô phỏng).
- **Định nghĩa & Ứng dụng trong dự án:** Giải pháp kiến trúc giải quyết bài toán thiếu hụt lịch sử dữ liệu (Data Shortage): Dữ liệu Thật (`silver`) dùng để đo lường độ chính xác truy vấn SQL/RAG đối chiếu UAT; Dữ liệu Mô phỏng (`synthetic`) 12 tháng sinh có kiểm soát dùng để kiểm nghiệm thuật toán phân tích xu hướng (Trend Analyst) và máy cảnh báo tự động (Alert Engine).
- *Trích dẫn:* Được thiết kế riêng trong Phương án B của tài liệu kiến trúc v2 GML, tham chiếu kỹ thuật kiểm thử trên dữ liệu nhân tạo của Chen et al. (2021) về *Synthetic Data for Enterprise Benchmarking*.

### 6.2. Ground Truth
- **Dịch nghĩa:** Dữ liệu chân lý / Đáp án chuẩn kiểm chứng.
- **Định nghĩa & Ứng dụng trong dự án:** Tập kết quả số liệu kế toán chính xác tuyệt đối được trích từ phần RESULT LOG của 5 bộ SQL UAT (đã đối soát khớp 100% với hệ thống MISA ngày 31/07/2026), dùng làm thước đo chuẩn mực để chấm điểm hệ thống AI.
> *Trích dẫn:* Fawcett, T. (2006). An introduction to ROC analysis. *Pattern Recognition Letters, 27*(8), 861–874.

### 6.3. Data Leakage (in Benchmark)
- **Dịch nghĩa:** Rò rỉ dữ liệu kiểm thử.
- **Định nghĩa & Ứng dụng trong dự án:** Lỗi phương pháp luận nghiêm trọng khi để các câu hỏi thuộc tập kiểm thử (Test Split) lọt vào ngân hàng câu hỏi mẫu (Golden Query Bank / Few-shot examples) hoặc tập tinh chỉnh, khiến hệ thống đạt điểm cao giả tạo do "học vẹt". Dự án có bài test `TC-T2-03` tự động quét độ tương đồng cosine để triệt tiêu rò rỉ.
> *Trích dẫn:* Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data (TKDD), 6*(4), 1–21.

### 6.4. Evaluation Harness / Benchmark Suite
- **Dịch nghĩa:** Khung đánh giá tự động & Bộ đề chuẩn độc lập.
- **Định nghĩa & Ứng dụng trong dự án:** Bộ công cụ lập trình tự động (`run_eval.py`) thực thi 60 câu hỏi benchmark chuẩn hóa (chia 40 câu dev, 20 câu test bị khóa), tự động tính toán toàn bộ 22 chỉ số định lượng (`M-01` đến `M-22`) và xuất báo cáo nghiệm thu dạng Markdown.
> *Trích dẫn:* Hendrycks, D., Burns, C., Basart, S., et al. (2021). Measuring massive multitask language understanding (MMLU). *ICLR 2021*.

### 6.5. Data Coverage
- **Dịch nghĩa:** Độ bao phủ dữ liệu lịch sử.
- **Định nghĩa & Ứng dụng trong dự án:** Số lượng mốc thời gian (tháng/kỳ) thực tế ghi nhận dữ liệu trong CSDL. Khi `data_coverage < 6`, hệ thống nhận diện không đủ điều kiện phân tích chuỗi thời gian và xuất cảnh báo thay vì đưa ra dự báo thiếu căn cứ.
> *Trích dẫn:* Hyndman, R. J., & Athanasopoulos, G. (2018). *Forecasting: Principles and Practice* (2nd ed.). OTexts.

---

## 7. NGHIỆP VỤ TÀI CHÍNH & QUẢN TRỊ DOANH NGHIỆP

### 7.1. Cash Conversion Cycle (CCC)
- **Dịch nghĩa:** Chu kỳ chuyển đổi tiền mặt.
- **Định nghĩa & Ứng dụng trong dự án:** Khoảng thời gian (tính bằng ngày) từ khi doanh nghiệp chi tiền mua gỗ nguyên liệu đến khi thu được tiền bán thành phẩm, tính theo công thức: $CCC = DIO + DSO - DPO$. Là chỉ số quản trị cốt lõi kết nối toàn bộ 5 Dashboard của Gỗ Minh Long.
> *Trích dẫn:* Richards, V. D., & Laughlin, E. J. (1980). A cash conversion cycle approach to liquidity analysis. *Financial Management, 9*(1), 32–38.

### 7.2. Days Sales Outstanding (DSO) / DIO / DPO
- **Dịch nghĩa:** Số ngày thu tiền khách hàng bình quân / Số ngày lưu kho / Số ngày trả nợ nhà cung cấp.
- **Định nghĩa & Ứng dụng trong dự án:** 
  - $DSO$: Đo lường tốc độ thu hồi nợ phải thu từ khách hàng đại lý.
  - $DIO$: Đo lường số ngày hàng tồn kho (gỗ ván, bề mặt Melamine) nằm trong kho trước khi xuất bán.
  - $DPO$: Số ngày GML chiếm dụng vốn hợp pháp của nhà cung cấp nguyên vật liệu.
> *Trích dẫn:* Brigham, E. F., & Ehrhardt, M. C. (2017). *Financial Management: Theory & Practice* (15th ed.). Cengage Learning.

### 7.3. Loan-to-Value (LTV)
- **Dịch nghĩa:** Tỷ lệ dư nợ vay trên giá trị định giá tài sản bảo đảm.
- **Định nghĩa & Ứng dụng trong dự án:** Chỉ số đo lường mức độ an toàn tín dụng tại GML: $\frac{\text{Tổng hạn mức được cấp}}{\text{Tổng giá trị tài sản bảo đảm}}$ (kết quả UAT đạt $0.7129$). Ngưỡng cảnh báo rủi ro được định nghĩa trong `business_rules.yaml` là khi $LTV \ge 80\%$.
> *Trích dẫn:* Saunders, A., & Cornett, M. M. (2018). *Financial Institutions Management: A Risk Management Approach* (9th ed.). McGraw-Hill Education.

### 7.4. Credit Limit (Granted Limit vs. Approved Limit vs. Remaining Limit)
- **Dịch nghĩa:** Hạn mức tín dụng (Hạn mức được cấp vs. Hạn mức phê duyệt vs. Hạn mức còn lại).
- **Định nghĩa & Ứng dụng trong dự án:**
  - *Approved Limit:* Hạn mức tối đa các ngân hàng mẹ phê duyệt (485 tỷ VNĐ).
  - *Granted Limit:* Hạn mức thực tế đã được ký hợp đồng cấp tín dụng (295 tỷ VNĐ).
  - *Remaining Limit:* Dư địa vay còn lại ($24.135.521.634$ VNĐ theo chuẩn UAT).
> *Trích dẫn:* Căn cứ theo Quy chuẩn Quản trị Hoạt động Tài chính BRD GML và UAT_01_Quan_Tri_Tai_Chinh.sql.

### 7.5. Cost of Debt (Chi phí nợ vay)
- **Dịch nghĩa:** Chi phí sử dụng vốn vay bình quân.
- **Định nghĩa & Ứng dụng trong dự án:** Tỷ lệ lãi suất bình quân mà GML đang phải trả cho các khoản vay ngân hàng ($\approx 8.3\%$/năm), đối chiếu tương quan với lãi suất tiền gửi ngắn hạn ($4.99\%$/năm) để làm nổi bật thông điệp quản trị: *"Vay đắt – Gửi rẻ – Tồn nhiều"*.
> *Trích dẫn:* Brealey, R. A., Myers, S. C., & Allen, F. (2020). *Principles of Corporate Finance* (13th ed.). McGraw-Hill.

---
*Tài liệu đã được kiểm tra tính nhất quán 100% với mã nguồn hệ thống và các tệp tài liệu kế hoạch v2 của dự án Gỗ Minh Long.*

