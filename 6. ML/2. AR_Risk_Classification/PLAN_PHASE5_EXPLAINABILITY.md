# KẾ HOẠCH TRIỂN KHAI PHA 5: GIẢI THÍCH MÔ HÌNH VỚI SHAP (EXPLAINABILITY)
**Dự án:** AR Risk Classification
**Thư mục làm việc:** `6. ML\2. AR_Risk_Classification`

## 1. Mục tiêu (Objective)
- Phá vỡ định kiến "AI là một Hộp đen (Black Box)". Đưa trí tuệ nhân tạo trở thành một công cụ minh bạch, có thể giải trình.
- **Vĩ mô (Global):** Cho Kế toán trưởng biết Top các nguyên nhân hàng đầu sinh ra nợ xấu toàn công ty.
- **Vi mô (Local - Cấp Khách hàng):** Khi hệ thống cảnh báo một hóa đơn sắp nợ xấu, nó phải tự động bóc tách và viết ra lời giải thích chi tiết (VD: *Tại sao khách hàng này lại nguy hiểm? Do mua quá nhiều? Hay do thói quen trả chậm 3 tháng nay?*).

## 2. Phân rã công việc (Task Breakdown)

### Task 5.1: Xây dựng SHAP Engine (`src/explain.py`)
- **Action:** Import thư viện nổi tiếng `shap` (Mô hình Trò chơi hợp tác - Game Theory).
- **Action:** Khởi tạo `shap.TreeExplainer` tương thích trực tiếp với lõi của thuật toán LightGBM.

### Task 5.2: Bóc tách Global & Local Explainers
- **Action:** Viết hàm `get_global_importance(X)`: Tổng hợp trung bình trị tuyệt đối của SHAP values để xếp hạng các Yếu tố quan trọng nhất (Feature Importance).
- **Action:** Viết hàm `explain_local_customer(X_row)` (Thay thế Waterfall Plot bằng Bảng Text Phân tích chi tiết): Chẩn đoán riêng biệt cho 1 khách hàng. Tính xem yếu tố nào ĐẨY rủi ro lên (Màu đỏ), yếu tố nào KÉO rủi ro xuống (Màu xanh).

### Task 5.3: Kịch bản Kiểm thử (`tests/test_explain.py`)
- **Action:** PyTest kiểm tra thuật toán SHAP có hoạt động đúng trên ma trận Multiclass (3 nhãn) hay không. (Output trả về phải là 1 list chứa 3 ma trận kích thước y hệt ma trận Input).

### Task 5.4: Kịch bản Chạy thực tế (`scratch/run_explainability.py`)
- **Action:** Bốc ngẫu nhiên một Khách hàng Nợ Xấu (High Risk). Bắt hệ thống AI tự "đứng ra trước vành móng ngựa" giải trình lý do chẩn đoán của nó thông qua báo cáo Waterfall.

## 3. Kịch bản Kiểm thử (Test Cases)
| Tên Test Case | Đầu vào (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_shap_shape` | Ma trận 15 Khách hàng, 4 Đặc trưng. Shape = (15, 4) | SHAP phải tính ra đủ 3 nhóm (Low, Med, High). Nhóm High Risk phải có ma trận SHAP shape = (15, 4). Bắt buộc 1-1. |
