# KẾ HOẠCH TRIỂN KHAI PHA 4: ĐÁNH GIÁ MÔ HÌNH CHUYÊN SÂU (MODEL EVALUATION)
**Dự án:** AR Risk Classification
**Thư mục làm việc:** `6. ML\2. AR_Risk_Classification`

## 1. Mục tiêu (Objective)
- Chụp X-Quang toàn diện hiệu năng của mô hình Champion (LightGBM).
- Không chỉ nhìn vào một con số (F1/AUC) mà đi sâu vào `Confusion Matrix` để biết mô hình sẽ làm Kế toán báo động sai (False Positive) hay bỏ lọt nợ xấu (False Negative) bao nhiêu lần.
- Đánh giá độ tin cậy của Xác suất mô hình xuất ra bằng `Calibration Curve`. Nếu mô hình nói rủi ro 90%, ngoài đời có đúng 90% bị nợ xấu không?

## 2. Phân rã công việc (Task Breakdown)

### Task 4.1: Xây dựng Bộ Metric (Thước đo)
- **Action:** Viết hàm `calculate_metrics(y_true, y_pred, y_prob)` (`src/evaluation.py`).
- **Nội dung:** Tính toán `ROC-AUC` (OVR - One vs Rest), `Precision`, `Recall`, và `F1-Score` (Tính theo Macro để không bị bóp méo bởi nhóm đa số).

### Task 4.2: Phân tích Ma trận nhầm lẫn & Chuẩn hóa Xác suất
- **Action:** Viết hàm `get_confusion_matrix_df()` để xuất ra bảng 3x3 rõ ràng (Low, Medium, High).
- **Action:** Viết hàm `check_calibration(y_true, y_prob)` dùng `calibration_curve` của scikit-learn để đối chiếu Xác suất AI Dự báo (Predicted Prob) vs Xác suất Thực tế (True Fraction).

### Task 4.3: Kịch bản Kiểm thử (`tests/test_evaluation.py`)
- **Action:** Viết Unit Tests (PyTest) kiểm tra tính hợp lệ của toán học: Điểm AUC, F1 phải luôn nằm trong dải [0, 1]. Ma trận phải đúng chuẩn 3x3.

### Task 4.4: Kịch bản Chạy thực tế (`scratch/run_evaluation.py`)
- **Action:** Train lại con LightGBM với Best Params từ Pha 3 trên tập Train. Dự báo trên tập Test. In ra Báo cáo Đánh giá (Evaluation Report) toàn diện nhất lên màn hình.

## 3. Kịch bản Kiểm thử (Test Cases)
| Tên Test Case | Input | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_metrics_range` | Mảng y giả định. | Mọi chỉ số đánh giá (AUC, F1, Recall) đều phải thỏa mãn: $0.0 \leq metric \leq 1.0$. |
| `test_confusion_matrix_shape` | Mảng y giả định có đủ 3 nhãn. | Bảng trả về từ hàm confusion_matrix BẮT BUỘC có shape = (3, 3). |
