# KẾ HOẠCH TRIỂN KHAI: TỐI ƯU HÓA THANH KHOẢN (LIQUIDITY OPTIMIZATION ENGINE)
> **Mã dự án:** GML-ML02 | **Framework Engine:** Python (`PuLP`, `pandas`)
> **Core Logic:** Tích hợp luật ngân hàng Việt Nam (LTV, Credit Line, Lãi suất Cá nhân/Doanh nghiệp).

---

## 1. ĐỊNH NGHĨA 6 NGUỒN DỮ LIỆU ĐẦU VÀO CHUẨN KỲ (INPUT SPECIFICATION)

Để bài toán LP (Linear Programming) hội tụ và không bị mâu thuẫn, hệ thống cần hút đủ 6 luồng dữ liệu (3 từ AI Upstream, 3 từ Nghiệp vụ):

| # | Tên Nguồn | Loại | Dữ liệu cung cấp cho Engine (Biến/Tham số) |
|:---:|:---|:---|:---|
| **1** | `gold.fact_cashflow_forecast` | AI DB | Net Cashflow T+4 Tuần (Thu - Chi dự kiến hàng tuần). Biến này xác định ta đang Thừa hay Thiếu tiền. |
| **2** | `silver.fact_ar_risk_score` | AI DB | Khối lượng tiền Thu bị xếp hạng "Rủi ro cao" (High Risk). Sẽ bị trừ đi khỏi dự báo Thu (Trích lập dự phòng thanh khoản). |
| **3** | `silver.fact_reorder_recommendations`| AI DB | Số tiền đột xuất cần để nhập hàng tồn kho (EOQ). Ép Ràng buộc: `Tiền dư >= EOQ_Cost`. |
| **4** | `bc_tin_dung_2026.xlsx` | Tệp Excel | `Hạn mức tổng`, `Dư nợ hiện tại` theo từng Bank. Giới hạn (Upper Bound) cho Biến Vay. |
| **5** | `Hop_dong_tien_gui.xlsm` | Tệp Excel | Tiền gửi hiện có. *Đặc biệt:* Có thêm cột `Owner_Type` (Corp/Individual) và `LTV_Policy` (90-95%) để cầm cố. |
| **6** | `market_interest_rates.csv` | File Crawl | Biểu lãi suất hiện hành. Làm Hệ số (Coefficients) cho Hàm mục tiêu tối ưu lợi nhuận. |

---

## 2. CÔNG THỨC TOÁN HỌC (LINEAR PROGRAMMING FORMULATION)

### 2.1. Biến Quyết định (Decision Variables)
AI cần tìm ra con số tối ưu cho 2 hành động sau tại thời điểm T:
- $Vay\_Moi_{b, k}$: Số tiền vay mới tại ngân hàng $b$, kỳ hạn $k$.
- $Gui\_Moi_{b, k}$: Số tiền nhàn rỗi đem gửi tại ngân hàng $b$, kỳ hạn $k$.

### 2.2. Hàm Mục Tiêu (Objective Function)
**Tối đa hóa Lợi ích Tài chính ròng (Net Financial Benefit):**
$$ Max Z = \sum (Gui\_Moi_{b, k} \times Lai\_Suat\_Tien\_Gui_{b, k}) - \sum (Vay\_Moi_{b, k} \times Lai\_Suat\_Tien\_Vay_{b, k}) $$

### 2.3. Hệ Thống Ràng Buộc (Constraints Matrix)
1. **Ràng buộc Cân bằng Dòng tiền (Cash Balance Constraint):**
   Tiền đầu kỳ + Net Cashflow (đã trừ rủi ro AR, Tồn kho) + $\sum Vay\_Moi$ - $\sum Gui\_Moi$ $\ge$ Vùng đệm an toàn tối thiểu (Safety Buffer).
2. **Ràng buộc Hạn mức Tín dụng (Credit Line Constraint - Không TSĐB/BĐS):**
   $Vay\_Moi_{b}$ $\le$ $(Han\_Muc\_Tong_{b} - Du\_No\_Hien\_Tai_{b})$
3. **Ràng buộc Thế chấp Sổ Tiết Kiệm (Cash-Backed Loan LTV):**
   $Vay\_Cam\_Co_{b}$ $\le$ $So\_Tiet\_Kiem\_Dang\_Co_{b} \times LTV\_Policy_{b}$ *(Ví dụ LTV MBBank = 0.95)*
4. **Ràng buộc Thanh khoản Kỳ hạn (Maturity Matching):**
   Tổng tiền $Gui\_Moi$ kỳ hạn 3 Tháng $\le$ Tổng dòng tiền thặng dư dự báo trong 3 tháng tới.

---

## 3. CHI TIẾT CÁC TASK THỰC THI (WORK BREAKDOWN STRUCTURE)

### Phase 1: Data Preparation & Mocking `[Task 1.x]`
- [ ] **Task 1.1:** Viết script `mock_financial_files.py` để sinh ra 2 file Excel (`bc_tin_dung_2026.xlsx`, `Hop_dong_tien_gui.xlsm`) chứa đủ thông tin Hạn mức, Dư nợ, LTV (90-95%), và Chủ sở hữu (Cá nhân/DN).
- [ ] **Task 1.2:** Load giả lập 3 bảng kết quả AI từ các thư mục dự án trước (Cashflow, AR, Inventory) để tạo Dữ liệu Tổng hợp (State Dictionary).

### Phase 2: Lập trình Optimization Engine bằng PuLP `[Task 2.x]`
- [ ] **Task 2.1:** Code module `src/optimizer.py`. Khởi tạo bài toán `pulp.LpMaximize`.
- [ ] **Task 2.2:** Định nghĩa liên kết giữa `market_interest_rates.csv` và Hàm Mục Tiêu (Objective). Tính toán chênh lệch Lãi suất Doanh nghiệp/Cá nhân.
- [ ] **Task 2.3:** Áp dụng 4 Ràng buộc Toán học (Constraints) ở Mục 2.3 vào code PuLP.

### Phase 3: Giải bài toán & Xuất Khuyến nghị `[Task 3.x]`
- [ ] **Task 3.1:** Chạy Solver (CBC default của PuLP). Nếu bài toán Unfeasible (Vô nghiệm do hụt tiền quá nặng), viết kịch bản Fallback (Xả tồn kho hoặc cắt giảm chi phí).
- [ ] **Task 3.2:** Bóc tách kết quả (Variables) thành Bảng `Action_Recommendations` bằng Tiếng Việt thân thiện.
  *(VD: "Nên cầm cố sổ MBB 5 tỷ để vay 4.5 tỷ thanh toán NCC thay vì giải ngân Vietcombank vì chênh lệch lãi suất ròng rẻ hơn 0.5%").*

### Phase 4: Output Layer & Tracking `[Task 4.x]`
- [ ] **Task 4.1:** Xuất kết quả Khuyến nghị ra file `processed/silver.fact_liquidity_actions.csv` để chuẩn bị đưa lên Power BI.
- [ ] **Task 4.2:** Tích hợp `MLflow` (Track các chỉ số: Total Interest Earned, Total Interest Paid, LTV Variables) để đo lường độ hiệu quả qua từng tuần chạy AI.
