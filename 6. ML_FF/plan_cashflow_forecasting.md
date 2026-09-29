# KẾ HOẠCH CHI TIẾT: DỰ BÁO DÒNG TIỀN (CASHFLOW FORECASTING) TẠI GỖ MINH LONG
**Mô hình đề xuất:** Facebook Prophet / ARIMA
**Công cụ triển khai:** Python (Thư viện `prophet`, `pandas`) tích hợp vào Power BI.

---

## 1. MỤC TIÊU NGHIỆP VỤ (BUSINESS OBJECTIVE)
- **Vấn đề:** Doanh nghiệp sản xuất gỗ thường đối mặt với tính mùa vụ (ví dụ: cuối năm chi trả nhiều tiền mặt cho nhà cung cấp, đầu năm dòng thu chậm). Việc chỉ nhìn vào số dư Tiền mặt hiện tại không đủ để đánh giá rủi ro thanh khoản.
- **Mục tiêu ML:** Dự báo Dòng tiền vào (Inflow), Dòng tiền ra (Outflow) và Dòng tiền ròng (Net Cashflow) trong 3 - 6 tháng tiếp theo. 
- **Kết quả đầu ra:** Cảnh báo sớm "Thời điểm cạn kiệt tiền mặt" (Cash Runway) để CFO chuẩn bị hạn mức tín dụng trước 90 ngày.

## 2. YÊU CẦU DỮ LIỆU TỐI THIỂU
- **Lịch sử tối thiểu:** Facebook Prophet cần ít nhất **2 năm dữ liệu theo ngày (Daily)** để nhận diện tính mùa vụ năm (Yearly Seasonality). Với dữ liệu hiện có từ 2024, mô hình đủ điều kiện chạy thử vào giữa năm 2026.
- **Tần suất cập nhật:** Dữ liệu `fact_cashflow` cần được ETL và cập nhật vào PostgreSQL **hàng ngày** để mô hình có đầu vào mới nhất.

## 3. QUY TRÌNH XỬ LÝ DỮ LIỆU (DATA PIPELINE)
**Nguồn dữ liệu (Input):**
- `fact_cashflow` (tầng Silver): Cung cấp lịch sử thu/chi theo từng giao dịch.
- `fact_balancesheet` (tầng Silver): Dùng để **validate** số dư Tiền mặt (B01-DN_110) cuối kỳ — đảm bảo tổng Inflow - Outflow khớp với số dư thực tế.
**Tiền xử lý (Preprocessing):**
1. **Resampling:** Gom nhóm (Aggregate) dữ liệu giao dịch theo Ngày (Daily) hoặc Tuần (Weekly).
2. **Xử lý Outlier (Nhiễu):** Loại bỏ các giao dịch tài chính bất thường mang tính "một lần" (One-off events) như: Bán tài sản cố định định giá cao, hoặc dòng tiền đầu tư không cốt lõi để tránh làm lệch đường dự báo.
3. **Feature Engineering:**
   - Thêm các biến phân loại Ngày Lễ/Tết (Holiday Effects).
   - Thêm các mốc sự kiện trả lương, trả lãi vay (Thường vào ngày 5, hoặc 25 hàng tháng).

## 4. THIẾT KẾ VÀ HUẤN LUYỆN MÔ HÌNH (MODELING)
**Lý do chọn Facebook Prophet:**
- Rất mạnh mẽ trong việc xử lý chuỗi thời gian (Time-series) có tính chu kỳ (Seasonality) lặp lại theo tuần, tháng, và năm.
- Có khả năng hấp thụ các ngày Lễ/Tết (đặc biệt phù hợp với lịch nghỉ Tết Âm lịch của VN làm đứt gãy dòng tiền).

**Quy trình Training:**
1. Chia tập dữ liệu: Train (3 năm đầu) - Test (6 tháng cuối).
2. Fit mô hình với các Component:
   - `yearly_seasonality=True`
   - `weekly_seasonality=True`
3. Tinh chỉnh Hyperparameters (Changepoint prior scale) để mô hình nhạy bén hơn với các biến động kinh tế vĩ mô gần nhất.

## 5. ĐÁNH GIÁ CHẤT LƯỢNG MÔ HÌNH (MODEL EVALUATION)
Sau khi train xong, đánh giá bắt buộc trên tập Test (6 tháng cuối):
| Metric | Ý nghĩa | Ngưỡng tốt |
|---|---|---|
| **MAE** (Mean Absolute Error) | Sai lệch tuyệt đối trung bình (VNĐ) | < 5% so với giá trị thực tế |
| **MAPE** (Mean Absolute Percentage Error) | Phần trăm sai lệch | < 10% |
| **RMSE** | Phạt nặng các sai lệch lớn (outlier) | So sánh giữa các mô hình |

> ⚠️ Nếu MAPE > 20%, cần xem xét lại chất lượng dữ liệu đầu vào hoặc bổ sung thêm External Features (lãi suất, tỷ giá).

## 6. TÍCH HỢP VÀ TRỰC QUAN HÓA (POWER BI INTEGRATION)
- **Phương pháp:** Viết Python Script trực tiếp trong mục *Get Data > Python script* của Power BI, hoặc chạy qua Jupyter Notebook lưu ra bảng `fact_cashflow_forecast` (tầng Gold).
- **Trực quan hóa:**
  - Sử dụng biểu đồ Line Chart: Đường nét liền (Thực tế - Actual), Đường nét đứt (Dự báo - Forecast).
  - Có các dải ruy-băng mờ (Confidence Interval - Khoảng tin cậy 80% và 95%) để thể hiện độ biến động rủi ro.
- **Hành động kinh doanh (Call-to-Action):** Nếu đường Dự báo dưới mốc 0 (Âm dòng tiền), Dashboard sẽ gửi Alert (Cảnh báo đỏ) yêu cầu huy động vốn.
