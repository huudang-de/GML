# 📊 Báo cáo Tham khảo #1: Cashflow Forecasting Engine
## Dự án: `Etherlabs-dev/cashflow-forecasting-engine`

> **Link:** https://github.com/Etherlabs-dev/cashflow-forecasting-engine  
> **Liên quan đến:** `6. ML / 1. Cashflow_Forecasting` của GML  
> **Ngày nghiên cứu:** 04/10/2026

---

## 1. Tổng quan dự án

| Thuộc tính | Giá trị |
|:---|:---|
| **Tên chính thức** | 90-Day Cash Flow Intelligence Engine |
| **Tác giả** | Etherlabs-dev |
| **Ngôn ngữ** | Python 3.11, TypeScript (React/Vite) |
| **Trạng thái** | Tested reference implementation / Portfolio system (KHÔNG phải production thực tế) |
| **Mục tiêu** | Deterministic cash forecasting, what-if scenarios, runway alerts, frozen forecast backtesting |

**Mô tả chính thức:**
> "Tested reference implementation for deterministic cash forecasting, isolated what-if scenarios, runway alerts and frozen forecast backtesting."

> [!WARNING]
> Repo này là **portfolio/demo project**, không phải production thực tế. Tác giả ghi rõ: *"No client deployment, production SLA, business outcome or real-world forecast-accuracy claim is made."*
> Tuy nhiên, kiến trúc và các pattern được implement rất đáng học hỏi.

---

## 2. Kiến trúc hệ thống (được tài liệu hóa rõ ràng)

```
providers / files  →  n8n adapters  →  canonical cash events
                                              │
                                              ▼
                             deterministic Python service
                             (assumptions + scenario + as-of date)
                                              │
                                              ▼
                          PostgreSQL immutable runs and forecasts
                                    │                    │
                                    ▼                    ▼
                          deduplicated alerts      React dashboard
                                    │
                                    ▼
                          frozen-run backtesting
```

### Phân tích từng layer:

#### Layer 1 — Data Ingestion (n8n adapters)
- Dùng **n8n** (no-code automation tool, giống Zapier) làm orchestration layer
- n8n nhận dữ liệu từ các providers (bank feeds, ERP files...) và chuẩn hóa thành **"canonical cash events"** (event chuẩn hóa)
- n8n **chỉ orchestrate**, không tính toán — mọi tính toán đẩy về Python service

#### Layer 2 — Python Forecast Service (core)
- Viết bằng Python 3.11
- Dùng **Decimal** (không phải float) để đảm bảo độ chính xác tài chính
- **As-of dates** rõ ràng: mọi forecast đều biết nó được tính "tại thời điểm nào"
- **Freshness checks**: Cảnh báo nếu dữ liệu nguồn stale (quá hạn)
- **Duplicate detection**: Tránh ghi đè kết quả đã chạy

#### Layer 3 — PostgreSQL (persistence)
- Lưu trữ **immutable runs**: mỗi lần chạy = một bản ghi không đổi
- **Provenance tracking**: Biết được forecast này từ dữ liệu nào mà ra
- **Idempotent result persistence**: Chạy lại cùng input → cùng kết quả

#### Layer 4 — React Dashboard (Vite)
- Flattened React/Vite dashboard
- Typed builds với TypeScript
- Hiển thị rõ nhãn `synthetic/configured` để phân biệt dữ liệu thật và dữ liệu test

---

## 3. Các tính năng nổi bật cần học hỏi

### 3.1 Scenario Modeling (⭐ Học ngay)
```python
# Dự án implement 4 loại scenario:
# Base: Kịch bản cơ sở (most likely)
# Best: Kịch bản tốt nhất (optimistic)  
# Worst: Kịch bản xấu nhất (pessimistic)
# Isolated: Chỉ tác động của 1 thay đổi cụ thể (VD: nếu tăng doanh thu 10%)
```
**Áp dụng vào GML:** Khi tích hợp forecast vào Power BI, vẽ 3 đường: Base, Best, Worst để CEO ra quyết định.

### 3.2 Frozen Forecast Backtesting (⭐⭐ Quan trọng)
- **Frozen forecast**: "Đóng băng" kết quả dự báo tại một thời điểm (VD: cuối tháng 8)
- Sau khi có số thực, so sánh: "Forecast ngày 31/8 nói tháng 9 sẽ có 5 tỷ vào, thực tế là 4.8 tỷ — sai 4%"
- Đây là cách đánh giá chất lượng model theo thời gian
- **Áp dụng vào GML:** Thêm bảng `fact_cashflow_forecast_frozen` và cron job monthly comparison.

### 3.3 Assumption Fingerprinting (SHA-256)
```python
# Mỗi lần chạy forecast có một SHA-256 hash của toàn bộ assumptions:
# - Lãi suất được dùng
# - Tỷ giá FX  
# - Historical data range
# Nếu assumptions thay đổi → hash khác → easy audit trail
```

### 3.4 Alert Lifecycle (không trùng lặp)
```python
# Logic đặc biệt: Suppress duplicate active alerts
# Nếu đã có alert "Cash Runway < 2 tháng" đang active, 
# không tạo thêm alert tương tự
# Chỉ tạo alert mới khi severity thay đổi (từ warning → critical)
```

### 3.5 Recurring Events
- Support các luồng tiền định kỳ (lương, thuê nhà, trả nợ vay...)
- Tự động generate cash events từ recurring schedule
- **Áp dụng vào GML:** Các khoản trả nợ ngân hàng định kỳ (tài khoản 341x) là recurring events

---

## 4. Tech Stack chi tiết

| Component | Technology | Ghi chú |
|:---|:---|:---|
| Backend Service | Python 3.11 | Decimal math, strict typing |
| Orchestration | n8n (6 workflow artifacts) | No-code, alternatives: Airflow/Prefect |
| Database | PostgreSQL | Immutable schema |
| Frontend | React + Vite + TypeScript | |
| Data format | Decimal (không float) | Critical cho tài chính |
| Reproducibility | SHA-256 fingerprinting + Run IDs | |

---

## 5. So sánh với kiến trúc GML hiện tại

| Điểm | Etherlabs Engine | GML (kế hoạch) |
|:---|:---|:---|
| Data Source | Generic providers/files | PostgreSQL Silver Layer (MISA data) |
| Orchestration | n8n | Airflow |
| Forecast Algo | Deterministic rules + Python | LightGBM + ETS (ML-based) |
| Visualization | React dashboard | Power BI |
| Alert mechanism | Built-in lifecycle | Power BI alerts |
| Backtesting | Frozen-run comparison | Cần implement thêm |

---

## 6. Những gì nên copy từ dự án này vào GML

| # | Pattern cần học | Cách áp dụng |
|:---|:---|:---|
| 1 | **Decimal không dùng float** | Dùng `Decimal` trong Python cho tất cả tính toán tài chính GML |
| 2 | **As-of date concept** | Mỗi forecast GML phải có `as_of_date` rõ ràng |
| 3 | **Frozen forecast backtesting** | Tạo bảng `fact_cashflow_forecast_frozen` để so sánh sau |
| 4 | **Scenario: Base/Best/Worst** | 3 đường forecast trên Power BI chart |
| 5 | **Alert suppression** | Chỉ push cảnh báo mới khi severity thay đổi |
| 6 | **Run ID + provenance** | Gắn `run_id` vào mỗi batch ETL của GML |

---

## 7. Hướng dẫn clone và chạy thử

```bash
# 1. Clone repo
git clone https://github.com/Etherlabs-dev/cashflow-forecasting-engine.git
cd cashflow-forecasting-engine

# 2. Xem cấu trúc thư mục
ls -la

# 3. Chú ý đặc biệt đến:
# /python-service/   → Core forecast service
# /n8n-workflows/    → 6 workflow JSON files (import vào n8n)
# /dashboard/        → React/Vite frontend
# /sql/              → PostgreSQL schema

# 4. Đọc thứ tự:
# 1. sql/schema.sql → Hiểu data model
# 2. python-service/forecast.py → Core logic
# 3. python-service/scenarios.py → Scenario modeling
# 4. python-service/alerts.py → Alert lifecycle
```

---

## 8. Tài nguyên bổ sung liên quan

| Resource | Link | Mục đích |
|:---|:---|:---|
| GitHub repo gốc | https://github.com/Etherlabs-dev/cashflow-forecasting-engine | Clone và đọc code |
| Cash Flow Forecasting Challenge | Search "Cash Flow Forecasting Challenge" trên Kaggle | Dataset thực tế để train |
| sktime docs | https://www.sktime.net/ | Framework ML chính của GML |
| Prophet Python | https://facebook.github.io/prophet/ | Alternative time-series library |
| MLflow Tracking | https://mlflow.org/ | Model tracking cho GML |

---

## 9. Roadmap học tập đề xuất (thứ tự ưu tiên)

```
Tuần 1: Đọc /sql/schema.sql → Hiểu cách lưu trữ immutable forecasts
Tuần 2: Đọc python-service/forecast.py → Core Decimal-based forecasting
Tuần 3: Implement frozen-run backtesting cho GML fact_cashflow_forecast
Tuần 4: Thêm Scenario modeling (Base/Best/Worst) vào Power BI GML
```
