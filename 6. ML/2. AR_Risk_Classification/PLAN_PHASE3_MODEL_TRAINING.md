# KẾ HOẠCH TRIỂN KHAI PHA 3: HUẤN LUYỆN VÀ LỰA CHỌN MÔ HÌNH (MODEL TRAINING)
**Dự án:** AR Risk Classification
**Thư mục làm việc:** `6. ML\2. AR_Risk_Classification`

## 1. Mục tiêu (Objective)
- Thiết lập đường cơ sở (Baseline) bằng `Logistic Regression` để làm chuẩn đo lường.
- Triển khai 2 mô hình Tree-based cực mạnh là `LightGBM` (Mô hình vô địch - Champion) và `XGBoost` (Mô hình thay thế - Alternative).
- Áp dụng `Stratified K-Fold CV` để đảm bảo mỗi tập test luôn chứa đủ tỷ lệ % của nhóm High Risk (Nợ xấu).
- Ứng dụng AI để tự động tìm bộ siêu tham số tốt nhất (`Optuna hyperparameter tuning`).

## 2. Phân rã công việc (Task Breakdown)

### Task 3.1: Xây dựng Model Zoo (`src/train.py`)
- **Action:** Khởi tạo Logistic Regression với `class_weight='balanced'`.
- **Action:** Khởi tạo LightGBM và XGBoost (Tương thích tốt với class weights và dữ liệu bị khuyết - missing values).

### Task 3.2: Benchmark và Tuning 
- **Action:** Viết hàm `evaluate_models(X, y)` chạy Cross Validation k=5 cho cả 3 model. Sử dụng `f1_macro` vì độ chính xác tổng thể (Accuracy) không có ý nghĩa khi dữ liệu mất cân bằng.
- **Action:** Viết hàm `tune_lightgbm(X, y)` sử dụng thư viện `Optuna` dò tìm tự động qua 10 cấu hình để tối ưu `learning_rate`, `num_leaves`, `max_depth`.

### Task 3.3: Kịch bản Kiểm thử (`tests/test_train.py`)
- **Action:** Viết Unit Tests (PyTest) kiểm chứng Đầu ra của Mô hình (Model Output). Đảm bảo hàm `predict_proba` sinh ra đúng ma trận xác suất của 3 nhãn (Low, Medium, High).

### Task 3.4: Chạy đường ống thực tế (`scratch/run_training.py`)
- **Action:** Chạy script tạo data giả lập (có tính chất imbalanced). Cho 3 mô hình thi đấu (Benchmark). Chạy Optuna tìm Best Params và báo cáo lên chat.

## 3. Kịch bản Kiểm thử (Test Cases)
| Tên Test Case | Đầu vào (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_model_output_shape` | Ma trận X (20 dòng) | Kết quả `predict_proba` trả về ma trận shape (20, 3) đại diện cho 3 xác suất (0, 1, 2) |
| `test_prob_sum_to_one` | Kết quả `predict_proba` | Tổng 3 xác suất của 1 KH cộng lại phải chính xác bằng 1.0 (Bảo vệ tính toàn vẹn toán học) |
