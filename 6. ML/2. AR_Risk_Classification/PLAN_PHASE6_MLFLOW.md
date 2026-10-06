# KẾ HOẠCH TRIỂN KHAI PHA 6: QUẢN LÝ VÒNG ĐỜI MÔ HÌNH VỚI MLFLOW
**Dự án:** AR Risk Classification
**Thư mục làm việc:** `6. ML\2. AR_Risk_Classification`

## 1. Mục tiêu (Objective)
- **Tuyệt đối không lưu model bằng file `.pkl` thủ công.** Việc lưu thủ công sẽ dẫn đến thảm họa thất lạc cấu hình (Hyperparameters) khi team có nhiều Data Scientist làm việc chung.
- Sử dụng **MLflow** để tự động Tracking (ghi hình) toàn bộ quá trình huấn luyện: Model dùng tham số gì? Train ngày nào? ROC-AUC là bao nhiêu?
- Đóng gói (Registry) mô hình thành một phiên bản sản xuất (Production Version) hoàn chỉnh kèm theo **Model Signature** (Khóa chặt định dạng Dữ liệu Input/Output).

## 2. Phân rã công việc (Task Breakdown)

### Task 6.1: Khởi tạo MLflow Tracker (`src/mlflow_tracker.py`)
- **Action:** Khởi tạo thư mục cục bộ `mlruns/` làm Database lưu trữ thí nghiệm.
- **Action:** Viết class `RiskModelTracker` với hàm `log_training()` để tự động bắt và lưu tham số (params), điểm số (metrics), và file Model (LightGBM).

### Task 6.2: Model Signature & Model Schema
- **Action:** Ứng dụng hàm `mlflow.models.infer_signature(X, y_pred)` của MLflow. Việc này tạo ra một "Bản hợp đồng dữ liệu" (Data Contract). Bất kỳ ai ở Gỗ Minh Long gọi model API trong tương lai với số lượng cột bị sai hoặc kiểu dữ liệu bị sai sẽ bị hệ thống chặn và báo lỗi ngay lập tức.

### Task 6.3: Kịch bản Kiểm thử (`tests/test_mlflow.py`)
- **Action:** PyTest kiểm tra tính khả dụng của MLflow context, đảm bảo hàm `mlflow.start_run()` không bị crash và trả về một Run ID hợp lệ.

### Task 6.4: Kịch bản Chạy thực tế (`scratch/run_mlflow.py`)
- **Action:** Train mô hình LightGBM giả định. Bật MLflow lên để ghi hình lại toàn bộ quá trình, sau đó in ra Terminal cái `Run ID` duy nhất (Unique ID) của đợt huấn luyện này.

## 3. Kịch bản Kiểm thử (Test Cases)
| Tên Test Case | Input | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_mlflow_run` | Lệnh `mlflow.start_run()` | Bắt buộc sinh ra một chuỗi Hash ngẫu nhiên làm `Run ID` (VD: a1b2c3d4e5f6) để chứng minh phiên bản đã được lưu trữ thành công. |
