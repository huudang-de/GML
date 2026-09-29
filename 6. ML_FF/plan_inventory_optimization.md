# KẾ HOẠCH CHI TIẾT: TỐI ƯU HÓA TỒN KHO VÀ DỰ BÁO NHU CẦU (INVENTORY OPTIMIZATION)
**Mô hình đề xuất:** XGBoost (Extreme Gradient Boosting) / LSTM
**Công cụ triển khai:** Python (`xgboost`, `scikit-learn`)

---

## 1. MỤC TIÊU NGHIỆP VỤ (BUSINESS OBJECTIVE)
- **Vấn đề:** Gỗ Minh Long đang duy trì lượng Tồn kho (B01-DN_140) ở mức rất cao (gần 300 Tỷ đồng), làm chôn vốn và kéo dài Chỉ số vòng quay tồn kho (DIO). Nguyên nhân cốt lõi là việc nhập nguyên vật liệu dựa trên "Cảm tính" hoặc số liệu bán hàng năm ngoái, không lường trước được sự thay đổi của thị trường.
- **Mục tiêu ML:** Dự báo chính xác sản lượng bán ra (Demand Forecasting) cho từng SKU (Loại ván gỗ) trong tháng tới.
- **Kết quả đầu ra:** Đưa ra mức Tồn kho an toàn (Safety Stock) và Điểm đặt hàng lại (Reorder Point) tối ưu nhất, vừa không bị đứt gãy chuỗi cung ứng, vừa không bị ứ đọng vốn.

## 2. QUY TRÌNH XỬ LÝ DỮ LIỆU (DATA PIPELINE)
**Nguồn dữ liệu (Input):**
- `fact_incomestatement`: Doanh thu thuần theo từng kỳ.
- `fact_cashflow` (Tài khoản 152/155/156): **Thay thế cho `fact_inventoryoutward`** — vì bảng xuất kho riêng biệt hiện chưa có trong Data Dictionary. Dữ liệu xuất/nhập kho được phản ánh qua các giao dịch ghi nợ/có trên TK 152 (Nguyên vật liệu), 155 (Thành phẩm), 156 (Hàng hóa).
- `fact_balancesheet` (Mã B01-DN_140): Số dư Tồn kho cuối kỳ để **validate** tổng xuất nhập tồn.
**Tiền xử lý & Feature Engineering (Yếu tố quyết định sống còn):**
Thuật toán XGBoost yêu cầu bảng dữ liệu dạng Feature Matrix. Các đặc trưng cần tạo:
1. **Lags Features (Biến trễ):** Nhu cầu của 1 tháng trước (Lag_1), 3 tháng trước (Lag_3) của chính sản phẩm đó.
2. **Rolling Window Features:** Trung bình trượt (Moving Average) doanh số của 3 tháng gần nhất.
3. **Categorical Features:** Nhóm hàng (MDF, HDF), Phân khúc khách hàng, Mùa vụ (Quý 1, Quý 4).
4. **External Features:** (Nếu có) Các chỉ số về thị trường bất động sản, xây dựng (Vì ngành gỗ phụ thuộc mạnh vào chu kỳ xây dựng).

## 3. THIẾT KẾ VÀ HUẤN LUYỆN MÔ HÌNH (MODELING)
**Lý do chọn XGBoost:**
- XGBoost (Tree-based model) xử lý cực kỳ tốt dữ liệu dạng bảng (Tabular data) có nhiều biến phức tạp không tuyến tính (Non-linear).
- Xử lý mượt mà các điểm dữ liệu bị thiếu (Missing Data) và tốc độ huấn luyện rất nhanh.

**Quy trình Training:**
1. **Target Variable (Biến mục tiêu):** Sản lượng gỗ ván (m3) bán ra trong t+1.
2. **Loss Function:** Sử dụng RMSE (Root Mean Square Error) làm hàm mất mát để tối ưu hóa.
3. Tinh chỉnh (Hyperparameter Tuning): Sử dụng `GridSearchCV` để dò tìm độ sâu của cây (max_depth) và tốc độ học (learning_rate) tốt nhất.

## 4. CÔNG THỨC TỒN KHO AN TOÀN (SAFETY STOCK FORMULA)
Đây là phần chuyển hóa kết quả ML thành quyết định mua hàng:

```
Safety Stock = Z × σ_demand × √Lead_time
```
Trong đó:
- **Z**: Hệ số Z-score theo mức độ dịch vụ mong muốn. Ví dụ: Mức dịch vụ 95% → Z = 1.645.
- **σ_demand**: Độ lệch chuẩn (Standard Deviation) của nhu cầu hàng ngày — lấy từ lịch sử `fact_cashflow`.
- **Lead_time**: Thời gian giao hàng của nhà cung cấp (tính bằng ngày).

**Điểm đặt hàng lại:**
```
Reorder Point (ROP) = (Nhu cầu mỗi ngày × Lead_time) + Safety Stock
```

## 5. CHUYỂN HÓA THÀNH QUYẾT ĐỊNH KINH DOANH (BUSINESS ACTION)
Kết quả từ Mô hình ML sẽ được áp dụng vào Công thức Tài chính:
- **Dự báo nhu cầu (Lead Time Demand) = Số lượng tiêu thụ mỗi ngày (Dự báo từ ML) * Thời gian giao hàng của nhà cung cấp.**
- **Điểm đặt hàng lại (Reorder Point - ROP):** Lead Time Demand + Safety Stock.

**Tích hợp Power BI:**
- Dashboard sẽ có một bảng ma trận (Matrix). Cột A: Tên loại ván gỗ; Cột B: Tồn kho hiện tại; Cột C: Dự báo tiêu thụ (ML); Cột D: Khuyến nghị (Trạng thái màu).
- **Quy tắc đèn giao thông:** 
  - Màu Đỏ (Tồn kho < ROP): Yêu cầu Phòng Thu mua (Procurement) nhập hàng khẩn cấp.
  - Màu Xanh (Tồn kho = ROP + Safety Stock): Lý tưởng.
  - Màu Vàng (Tồn kho >> ROP): Chôn vốn, yêu cầu Phòng Sales đẩy mạnh xả kho (Khuyến mãi).

## 6. CƠ CHẾ TÁI HUẤN LUYỆN MÔ HÌNH (RETRAINING STRATEGY)
Mô hình XGBoost sẽ bị lỗi thời khi thị trường thay đổi nếu không được cập nhật.
- **Tần suất Retrain:** Hàng tháng, sau khi ETL pipeline hoàn tất cập nhật dữ liệu tháng mới.
- **Trigger tự động:** Nếu **MAPE trên tập validation vượt ngưỡng 15%**, hệ thống tự động gửi cảnh báo và chạy lại toàn bộ pipeline từ bước Feature Engineering.
- **Lưu trữ phiên bản:** Các phiên bản mô hình (Model Versioning) được lưu bằng thư viện `mlflow` hoặc đơn giản là đặt tên file theo tháng: `xgb_inventory_2026_09.pkl` để có thể rollback khi cần.
