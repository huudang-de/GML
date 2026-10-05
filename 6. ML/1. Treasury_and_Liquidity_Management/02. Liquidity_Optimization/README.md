# 💰 Dự án 02: Tối ưu hóa Nguồn vốn & Thanh khoản (Liquidity & Treasury Optimization)

> **Mã dự án:** GML-ML-02
> **Phạm vi:** Vốn vay ngân hàng, Hợp đồng tiền gửi, Dòng tiền thuần ngắn hạn
> **Nguồn dữ liệu:** `bc_tin_dung_2026.xlsx` | `Hop_dong_tien_gui.xlsm` | `silver.fact_cashflow` | `silver.fact_accountsreceivable` | `silver.fact_accountspayable`
> **Trạng thái:** 📋 Lập kế hoạch

---

## 0. Tại sao 3 Dự án kia là INPUT BẮT BUỘC? (Business Logic Chain)

> **Vốn vay và Tiền gửi không tự nhiên sinh ra. Chúng là "hệ quả" của Dòng tiền, Công nợ và Tồn kho.**  
> Tất cả được liên kết bằng một khái niệm: **Cash Conversion Cycle (Vòng quay Tiền)**

### Sợi dây liên kết (Business Chain)

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                    NHÓM A: CÁC DỰ ÁN ML UPSTREAM                       │
 │                  (Dự báo Nhu cầu & Rủi ro Dòng tiền)                   │
 └─────────────────────────────────────────────────────────────────────────┘
[AI Tối ưu Tồn kho]  ──(Giải phóng Vốn lưu động)──────────────────────────────┐
  "Hàng tồn kho = Tiền đang ngủ"                                               │
  Ví dụ: Giảm 10 tỷ hàng dư thừa → tiết kiệm 800 triệu lãi vay/năm (8%/năm)   │
                                                                                │
[AI Phân tích Nợ AR] ──(Cảnh báo sớm rủi ro thu tiền chậm)────────────────────+──► [DỰ BÁO DÒNG TIỀN NET]
  "Công nợ = Tiền của mình nhưng người khác đang giữ"                          │      (Net Cash Position
  Ví dụ: KH A trả chậm 30 ngày → chuẩn bị vay 5 tỷ bù đắp trước               │       30-90 ngày tới)
                                                                                │              │
[Cashflow Forecast]  ──(Dự báo Thu/Chi mỗi tuần T+1 đến T+4)──────────────────┘              │
  "Trái tim của hệ thống"                                                                     │
  Net CF > 0 → Bơm vào TG    |    Net CF < 0 → Kích hoạt Vay                                 │
                                                                                              │
 ┌────────────────────────────────────────────────────────────────────────┐                  │
 │                   NHÓM B: DỮ LIỆU CONSTRAINT (BẮT BUỘC)              │                  │
 │               (Giới hạn thực tế mà LP phải tuân theo)                 │                  │
 └────────────────────────────────────────────────────────────────────────┘                  │
                                                                                              │
[bc_tin_dung_2026.xlsx] ──(Hạn mức vay, Lãi suất, Dư nợ hiện tại)─────────────────────────┐ │
  Constraint: Tổng vay ≤ Hạn mức tín dụng còn lại                                          │ │
  Constraint: Lãi vay phải trả = Dư nợ × Lãi suất / 365 × Số ngày                         │ │
  Constraint: Ngày đáo hạn từng khế ước (không được gia hạn tự ý)                           ├─┘
                                                                                             │
[Hop_dong_tien_gui.xlsm] ──(Số tiền, Kỳ hạn, Lãi suất, Ngày đáo hạn TK)──────────────────┘
  Constraint: Không rút sổ TK trước hạn (hoặc tính phạt lãi)
  Constraint: Số tiền gửi thêm ≤ Tiền mặt khả dụng sau khi giữ buffer
  Objective:  Lãi TK thu được = Số tiền × Lãi suất × Số ngày / 365

                                                   │
                                                   ▼
                    ┌──────────────────────────────────────────────────┐
                    │         LIQUIDITY OPTIMIZER (PuLP LP)            │
                    │                                                  │
                    │  Minimize: Chi phí lãi vay                       │
                    │  Maximize: Lãi tiền gửi thu được                 │
                    │  Subject to: Tất cả constraint từ Nhóm A + B     │
                    │                                                  │
                    │  OUTPUT: Action Recommendations                  │
                    │  "Gửi X tỷ, kỳ hạn N tháng, vào ngày DD/MM"     │
                    │  "Giải ngân Z tỷ khế ước số ABC vào ngày..."     │
                    └──────────────────────────────────────────────────┘
```

### 3 "Sợi dây" giải thích cụ thể

#### 🏭 Sợi dây 1: Tồn kho → Tiết kiệm lãi vay
**Tồn kho dư thừa = Tiền mặt bị "nhốt"** vào kho.  
Khi AI Inventory giúp giảm 10 tỷ hàng tồn không cần thiết:
- Doanh nghiệp có thêm 10 tỷ tiền mặt ngay lập tức.
- Không cần vay ngân hàng 10 tỷ đó nữa.
- **Tiết kiệm trực tiếp: 10 tỷ × 8%/năm = 800 triệu đồng/năm.**

#### 📋 Sợi dây 2: Công nợ AR → Cảnh báo thiếu hụt thanh khoản
**Công nợ chưa thu = Tiền của GML nhưng người khác đang giữ.**  
Khi AI AR Risk dự báo KH A (5 tỷ phải thu) sẽ trả chậm 30 ngày:
- Liquidity Optimizer biết trước tuần W+4 sẽ bị hụt 5 tỷ.
- Chủ động chuẩn bị khế ước vay ngắn hạn trước (lãi suất tốt hơn vay khẩn cấp).
- **Tránh được rủi ro vỡ nợ ngắn hạn và chi phí vay "cháy nhà".**

#### 💰 Sợi dây 3: Cashflow Forecast → "Trái tim" của hệ thống
**Không có dự báo dòng tiền = Mù quáng quyết định vay/gửi.**  
Khi AI Cashflow Forecasting vẽ được đường cong Net Cash Position 30-90 ngày:
- Dòng tiền **DƯƠNG** → Optimizer biết được có bao nhiêu tiền nhàn rỗi → **Bơm vào Tiền gửi** đúng kỳ hạn.
- Dòng tiền **ÂM** → Optimizer biết trước cần bao nhiêu → **Giải ngân Vốn vay** đúng thời điểm, đúng số tiền.
- **Không còn tình trạng gửi tiết kiệm rồi phải rút trước hạn (mất lãi), hoặc vay thừa (trả lãi dư).**

---

## 1. Bối cảnh & Động lực (Context)

Gỗ Minh Long đang đồng thời:
- **Duy trì Vốn vay ngân hàng** để phục vụ sản xuất, thu mua nguyên liệu gỗ.
- **Gửi tiền có kỳ hạn** từ phần vốn nhàn rỗi để sinh lãi.

Bài toán mà kế toán/CFO đang phải xử lý mỗi tuần bằng Excel là:

> "Tuần này có nên gửi thêm tiết kiệm không? Hay sắp cần tiền để trả NCC? Hạn mức vay còn bao nhiêu? Nếu mình thu được tiền từ khách hàng A thì có cần rút sổ tiết kiệm B không?"

AI sẽ thay thế hoàn toàn quá trình tư duy thủ công này bằng **Khuyến nghị hành động tự động (Automated Action Recommendations)**.

---

## 2. Nghiên cứu Case Thực Tế (Real-World Benchmarks)

### Case 1: Konica Minolta x HighRadius (Sản xuất thiết bị)
| Chỉ số | Trước AI | Sau AI |
|:---|:---|:---|
| Độ chính xác dự báo dòng tiền | ~70% | **98.6%** |
| Thời gian quản lý tiền mặt | >80 giờ/tháng | **<15 phút/tháng** |
| Tiết kiệm lãi vay hàng năm | - | **$1.6 triệu USD/năm** |
| Hiệu quả quản lý tiền mặt | - | Cải thiện **87%** |

**Cơ chế:** HighRadius dự báo dòng tiền 30-90 ngày, tự động đề xuất mức vay/trả vay tối ưu mỗi ngày.

### Case 2: Kyriba Enterprise Treasury
| Chỉ số | Kết quả |
|:---|:---|
| Tỷ lệ giảm nợ (Deleveraging) | **Giảm ~30% tổng nợ vay** trong 12 tháng đầu |
| Tối ưu hóa tiền nhàn rỗi | Tăng **6% hiệu quả triển khai tiền gửi** |
| Tiết kiệm chi phí vốn | Giảm thiểu vay "khẩn cấp" lãi suất cao |

**Cơ chế:** Kyriba dùng LP (Linear Programming) để phân bổ tiền vào các "túi" tối ưu (Tiền mặt dự phòng, Tiền gửi ngắn hạn, Trả nợ vay) dựa trên dự báo dòng tiền.

### Case 3: Nghiên cứu Sản xuất Việt Nam (UEH 2026)
Kết hợp XGBoost + LSTM cho dự báo và Linear Programming cho tối ưu nguồn vốn:
- Giảm **20-30% sai số dự báo** so với mô hình truyền thống.
- Tối ưu Cash Conversion Cycle phù hợp đặc thù mùa vụ.

**Bài học rút ra cho GML:**
1. Bắt đầu từ "Quick Win" - dự báo dòng tiền trước, tối ưu sau.
2. Dùng XGBoost (không cần nhiều dữ liệu) thay vì LSTM khi chỉ có 7 tháng.
3. Dùng LP đơn giản (PuLP) - đủ mạnh, dễ giải thích cho CFO hơn RL.
4. Luôn có "Human-in-the-Loop" - AI đề xuất, con người quyết định cuối.

---

## 3. Kiến trúc Luồng Dữ liệu (Data Flow Architecture)

Dự án Liquidity Optimization KHÔNG hoạt động độc lập. Nó là **tầng tổng hợp cao nhất** nhận OUTPUT từ 3 dự án ML khác của GML làm INPUT.

```
+-----------------------------+  +------------------------------+  +------------------------------+
| DỰ ÁN 01: Cashflow Forecast |  | DỰ ÁN AR: AR Risk Classification|  | DỰ ÁN INV: Inventory Forecast|
| - Dự báo dòng tiền Thu/Chi  |  | - Phân loại rủi ro nợ KH    |  | - Dự báo nhu cầu NVL         |
|   theo tuần T+1 đến T+4     |  | - Dự báo ngày KH thanh toán |  | - Thời điểm cần vốn mua hàng |
| OUTPUT: cashflow_forecast   |  | OUTPUT: ar_risk_forecast    |  | OUTPUT: inventory_plan       |
+-------------+---------------+  +-------------+---------------+  +-------------+----------------+
              |                                |                                |
              +--------------------------------+--------------------------------+
                                               |
                                               v
                  +------------------------------------------------+
                  |        LIQUIDITY OPTIMIZER (Linear Program)    |
                  |                                                |
                  |  INPUT TỔNG HỢP TỪ 3 DỰ ÁN + FILE NỘI BỘ:   |
                  |  [1] Net Cashflow du bao (Output DuAn01)       |
                  |  [2] Ngay thu hoi cong no KH (Output DuAnAR)  |
                  |  [3] Ke hoach mua NVL (Output DuAnINV)        |
                  |  [4] Hop dong tien gui (.xlsm)                |
                  |  [5] Han muc tin dung (.xlsx)                 |
                  |                                                |
                  |  OBJECTIVE: Max(Lai tien gui) - Min(Lai vay)  |
                  |  CONSTRAINT: Du phong toi thieu, han muc vay  |
                  |                                                |
                  |  OUTPUT: Action Recommendations Dashboard      |
                  +------------------------------------------------+
```

### Bảng Input chi tiết

| # | Nguồn Input | Đến từ | Thông tin Cung cấp |
|:---|:---|:---|:---|
| 1 | `cashflow_forecast.csv` | **Dự án 01 Cashflow Forecasting** | Net Cashflow dự báo mỗi tuần (T+4 tuần tới) |
| 2 | `ar_risk_forecast.csv` | **Dự án AR Risk Classification** | Ngày & số tiền KH dự báo trả; KH có nguy cơ chậm trả |
| 3 | `inventory_plan.csv` | **Dự án Inventory Forecasting** | Nhu cầu mua nguyên vật liệu và thời điểm cần vốn |
| 4 | `Hop_dong_tien_gui.xlsm` | **File nội bộ GML** | Số tiền, kỳ hạn, lãi suất, ngày đáo hạn từng sổ TK |
| 5 | `bc_tin_dung_2026.xlsx` | **File nội bộ GML** | Hạn mức tín dụng, dư nợ hiện tại, lãi suất từng khế ước |

> **Lưu ý thiết kế (Standalone Mode):** Khi 3 dự án ML kia chưa hoàn thành, Optimizer vẫn chạy được bằng cách dùng trực tiếp dữ liệu thô từ `silver.fact_cashflow`, `silver.fact_accountsreceivable`, `silver.fact_accountspayable` trong PostgreSQL — không cần chờ các dự án upstream.

---

## 4. GML Có Gì Ngay Bây Giờ? (Current Assets)

| Dữ liệu | File / Bảng | Thông tin Chứa |
|:---|:---|:---|
| Dòng tiền giao dịch | `silver.fact_cashflow` | 251,861 dòng, 7 tháng (01-07/2026) |
| Công nợ phải thu | `silver.fact_accountsreceivable` | 28,886 dòng, thu tiền từ KH |
| Công nợ phải trả | `silver.fact_accountspayable` | 16,447 dòng, thanh toán NCC |
| Báo cáo tín dụng | `bc_tin_dung_2026.xlsx` | Hạn mức, dư nợ, lãi suất từng khế ước |
| Hợp đồng tiền gửi | `Hop_dong_tien_gui.xlsm` | Số tiền, kỳ hạn, lãi suất, ngày đáo hạn |
 Framework Tổng thể (GML Treasury AI Brain)

```
+------------------+--------------------------------------------------+
| LAYER 1: DATA    | fact_cashflow + fact_ar + fact_ap                |
| INGESTION        | bc_tin_dung + hop_dong_tien_gui                  |
+------------------+--------------------------------------------------+
| LAYER 2:         | Cashflow Forecasting (XGBoost + Prophet)         |
| FORECASTING      | - Du bao Dong tien Thu/Chi moi tuan (T+4)        |
|                  | - Du bao Ngay & So tien KH se thanh toan         |
|                  | - Du bao Ngay phai tra tien NCC                  |
+------------------+--------------------------------------------------+
| LAYER 3:         | Liquidity Optimizer (PuLP Linear Programming)    |
| OPTIMIZATION     | - Objective: Max(Lai tien gui) - Min(Lai vay)    |
|                  | - Constraints:                                   |
|                  |   . So du toi thieu du phong (buffer)            |
|                  |   . Khong vuot han muc tin dung                  |
|                  |   . Ky han so tiet kiem phai phu hop             |
+------------------+--------------------------------------------------+
| LAYER 4:         | Action Recommendations (Streamlit Dashboard)     |
| DECISIONS        | - "Nen gui [X ty] ky han [N thang] vao [ngay]"  |
| (OUTPUT)         | - "Nen giai ngan [Z ty] khe uoc [so X] vao..."  |
|                  | - "Du bao du tien, khong can giai ngan"          |
+------------------+--------------------------------------------------+
```

---

## 5. Tech Stack Chi tiết

### Layer 2 — Forecasting Models
| Model | Vai trò | Lý do chọn |
|:---|:---|:---|
| **XGBoost** | Model chính dự báo Net Cashflow theo tuần | Tốt nhất với tabular data, chỉ cần 7 tháng |
| **Prophet (Meta)** | Phân rã xu hướng + mùa vụ tuần/tháng | Dễ giải thích, tự xử lý outliers |
| **Ensemble** | Kết hợp XGBoost + Prophet | Giảm sai số tổng thể |

### Layer 3 — Optimization Engine
| Công cụ | Vai trò |
|:---|:---|
| **PuLP** | Giải LP tối ưu vay/gửi (Python, open-source) |
| **scipy.optimize** | Bài toán tối ưu phi tuyến nếu cần |

### Framework Bổ trợ
| Công cụ | Mục đích |
|:---|:---|
| **pandas / SQLAlchemy** | Kết nối PostgreSQL, xử lý dữ liệu |
| **openpyxl** | Đọc file .xlsx/.xlsm tín dụng & tiền gửi |
| **Streamlit** | Dashboard hiển thị khuyến nghị cho CFO |
| **MLflow** | Tracking thí nghiệm, quản lý phiên bản model |
| **APScheduler** | Tự động chạy dự báo định kỳ (thứ Hai 8:00 AM) |

---

## 6. Lộ trình Phát triển (Roadmap)

### Phase 1 — EDA & Hiểu Dữ liệu `[2 tuần]`
- [ ] Task 1.1: Parse `bc_tin_dung_2026.xlsx` -> Khế ước, Hạn mức, Dư nợ, Lãi suất, Ngày đáo hạn.
- [ ] Task 1.2: Parse `Hop_dong_tien_gui.xlsm` -> Số HĐ, Số tiền, Kỳ hạn, Lãi suất, Ngày đáo hạn.
- [ ] Task 1.3: EDA trên `fact_cashflow` -> Biểu đồ Thu/Chi theo tuần, phát hiện pattern.
- [ ] Task 1.4: Tạo feature set: DSO, DPO, Net Cashflow Weekly.

### Phase 2 — Mô hình Dự báo `[3 tuần]`
- [ ] Task 2.1: Baseline với Prophet (dự báo Net Cashflow 4 tuần).
- [ ] Task 2.2: XGBoost model với feature engineering đầy đủ.
- [ ] Task 2.3: Đánh giá & chọn model tốt nhất (MAPE ≤ 10%).
- [ ] Task 2.4: Export kết quả dự báo -> `processed/cashflow_forecast.csv`.

### Phase 3 — Optimization Engine `[2 tuần]`
- [ ] Task 3.1: Xây bài toán LP với PuLP.
- [ ] Task 3.2: Nhúng constraint từ hợp đồng thực tế.
- [ ] Task 3.3: Backtest kết quả LP với scenario lịch sử.

### Phase 4 — Dashboard & Triển khai `[1 tuần]`
- [ ] Task 4.1: Streamlit Dashboard: Dòng tiền dự báo + Khuyến nghị hành động.
- [ ] Task 4.2: Lịch chạy tự động hàng tuần.
- [ ] Task 4.3: Hướng dẫn sử dụng cho kế toán trưởng.

---

## 7. KPI Mục tiêu
| Chỉ số | Mục tiêu |
|:---|:---|
| Độ chính xác dự báo (MAPE) | ≤ 10% |
| Tiết kiệm lãi vay (ước tính) | ≥ 5% chi phí tài chính/năm |
| Tỷ lệ tiền nhàn rỗi vào tiền gửi | Tăng ≥ 15% |
| Số lần "hụt tiền khẩn cấp" | Giảm về 0 lần/quý |
