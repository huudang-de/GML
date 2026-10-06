# KẾ HOẠCH TRIỂN KHAI PHA 4: TỐI ƯU HÓA HÀNG TỒN KHO (INVENTORY OPTIMIZATION)
**Dự án:** Inventory Demand Forecasting
**Thư mục làm việc:** `6. ML\3. Inventory_Demand_Forecasting`

## 1. Mục tiêu (Objective)
- Chuyển hóa kết quả của Mô hình Học máy (từ Pha 3) thành Quyết định Kinh doanh (Supply Chain Decisions) thực tế. 
- AI chỉ cho biết "Tháng sau bán được bao nhiêu", nhưng Pha 4 sẽ trả lời cho Bộ phận Mua hàng câu hỏi: **"Hôm nay cần đặt mua thêm bao nhiêu hàng? Và khi nào thì đặt?"**
- Triển khai 3 công thức Chuỗi cung ứng nền tảng:
  1. **Tồn kho an toàn (Safety Stock):** Bộ đệm hàng hóa để chống lại sự biến động của Nhu cầu.
  2. **Điểm đặt hàng lại (Reorder Point - ROP):** Mức cảnh báo tồn kho. (VD: Trong kho còn đúng 150 tấm ván thì phần mềm phải báo động).
  3. **Lượng đặt hàng kinh tế (EOQ - Economic Order Quantity):** Tối ưu hóa điểm cân bằng giữa Chi phí lưu kho (Chôn vốn) và Chi phí đặt hàng (Vận chuyển, Admin).

---

## 2. Kiến trúc Thư mục (Directory Structure)
Sẽ khởi tạo và phát triển các file sau trong Pha 4:
```text
3. Inventory_Demand_Forecasting/
├── PLAN_PHASE4_INVENTORY_OPTIMIZATION.md (File này)
├── src/
│   └── optimize.py            # Hàm tính toán Safety Stock, ROP và EOQ
├── tests/
│   └── test_optimize.py       # Unit tests kiểm tra toán học
└── scratch/
    └── run_optimization.py    # Kịch bản ráp nối dự báo vào bảng mua hàng
```

---

## 3. Phân rã công việc (Task Breakdown)

### Task 4.1: Tính toán Tồn kho an toàn và ROP (`src/optimize.py`)
- **Mô tả:** Mở rộng từ lượng bán trung bình và độ lệch chuẩn của nhu cầu.
- **Action:** Viết hàm `calculate_rop(avg_demand, std_demand, lead_time_days, service_level=0.95)`
  - **Tra cứu Z-Score:** Dùng thư viện `scipy.stats.norm.ppf(service_level)` để lấy Z-score.
  - **Tính Safety Stock:** Lượng an toàn = $Z \times std\_demand \times \sqrt{lead\_time\_days}$ (Công thức chuẩn APICS).
  - **Tính ROP:** $ROP = (avg\_demand \times lead\_time\_days) + Safety\_Stock$. Trả về 2 giá trị này (đã làm tròn nguyên).

### Task 4.2: Tối ưu lượng đặt hàng EOQ (`src/optimize.py`)
- **Mô tả:** Sử dụng công thức Wilson EOQ kinh điển. Hỗ trợ tùy chọn thư viện `scipy.optimize` nếu sau này nâng cấp thành bài toán có ràng buộc (Discount theo lô hàng).
- **Action:** Viết hàm `calculate_eoq(annual_demand, ordering_cost, holding_cost_rate, unit_cost)`.
  - **Holding cost (H):** Chi phí lưu kho $H = holding\_cost\_rate \times unit\_cost$.
  - **Công thức:** $EOQ = \sqrt{\frac{2 \times D \times S}{H}}$ (Trong đó D là Demand, S là Ordering Cost).
  - Trả về số lượng tấm ván tối ưu cần nhập (Làm tròn).

### Task 4.3: Viết kịch bản kiểm thử Toán học (`tests/test_optimize.py`)
- **Action:** Thiết lập các Test cases cứng dựa trên đáp án kinh điển để đảm bảo không sai công thức vật lý/toán học (Chi tiết ở Mục 4).

### Task 4.4: Ráp nối thành Bảng Khuyến nghị Mua hàng (`scratch/run_optimization.py`)
- **Action:** Viết script mô phỏng:
  - Gọi lại Hàm Dự báo (Pha 3) lấy ra bảng kết quả 7 ngày tới.
  - Từ bảng dự báo, tự động tính `avg_demand` và `std_demand` (Độ lệch chuẩn có thể tính qua Khoảng tin cậy bằng công thức: $\sigma \approx \frac{Hi - Lo}{2 \times Z}$).
  - Gán thêm `lead_time = 5` ngày, `ordering_cost = 50,000` VND.
  - Gọi hàm tính ROP và EOQ.
  - **Đầu ra cuối cùng:** DataFrame hoàn hảo gồm `[unique_id, avg_daily_demand, safety_stock, ROP, EOQ]`. Bảng này sẽ được ném thẳng lên Power BI.

---

## 4. Kịch bản Kiểm thử (Test Cases)

| Tên Test Case | Đầu vào (Input) | Kết quả Kỳ vọng (Expected) |
| :--- | :--- | :--- |
| `test_eoq_standard` | Demand = 10,000 cái/năm. Đặt hàng (S) = $50. Lưu kho (H) = $2/cái/năm. | $\sqrt{\frac{2 \times 10000 \times 50}{2}} = 707.1$. Output = `707`. |
| `test_safety_stock` | Std Demand = 10. Lead time = 4 ngày. Z (95%) $\approx$ 1.645 | Safety Stock = $1.645 \times 10 \times \sqrt{4} = 32.9$. Output = `33`. |
| `test_rop_logic` | Avg Demand = 20. Lead time = 5. Safety Stock (tính ở trên) = 30 | ROP = $(20 \times 5) + 30 = 130$. |

---

## 5. Tiêu chí Hoàn thành (Definition of Done - DoD)
- [ ] Vượt qua 100% Unit Tests để chứng minh các phương trình Chuỗi cung ứng (Supply Chain Math) được code đúng.
- [ ] Script mô phỏng đầu ra thành công một Dashboard-ready Table. (Sẵn sàng phục vụ bộ phận Mua hàng ngay tức khắc).
