# 📘 TÀI LIỆU TRI THỨC QUẢN TRỊ TÀI CHÍNH & RA QUYẾT ĐỊNH CHO AI BUSINESS ASSISTANT — GỖ MINH LONG (GML)

> **Mục tiêu:** Cung cấp cơ sở tri thức nghiệp vụ chuyên sâu ngoài BRD (bao gồm lý thuyết tài chính chuẩn mực, quy chuẩn pháp lý Việt Nam, ngưỡng kiểm soát rủi ro, cẩm nang hành động của CFO và bối cảnh ngành gỗ) để AI Assistant có khả năng:
> 1. **Giải thích bản chất nguyên nhân biến động (Root-cause Analysis).**
> 2. **Đánh giá vị thế tài chính theo hệ quy chiếu chuẩn (Risk Benchmarking).**
> 3. **Đề xuất kịch bản hành động thực thi cụ thể cho Ban Quản trị & CFO (Prescriptive Actions).**

---

## MỤC LỤC
1. [TỔNG QUAN KHUNG TRI THỨC 5 TẦNG](#1-tổng-quan-khung-tri-thức-5-tầng)
2. [NHÓM 1: CHUẨN MỰC QUẢN TRỊ VỐN LƯU ĐỘNG & CHU KỲ CHUYỂN HÓA TIỀN (CCC)](#nhóm-1-chuẩn-mực-quản-trị-vốn-lưu-động--chu-kỳ-chuyển-hóa-tiền-ccc)
3. [NHÓM 2: CHẾ ĐỘ KẾ TOÁN & HỆ THỐNG CHỈ SỐ TÀI CHÍNH VIỆT NAM (TT 200/2014/TT-BTC)](#nhóm-2-chế-độ-kế-toán--hệ-thống-chỉ-số-tài-chính-việt-nam-tt-2002014tt-btc)
4. [NHÓM 3: CẨM NANG HÀNH ĐỘNG CỦA CFO & QUY TRÌNH SOP QUẢN TRỊ RỦI RO](#nhóm-3-cẩm-nang-hành-động-của-cfo--quy-trình-sop-quản-trị-rủi-ro)
5. [NHÓM 4: ĐẶC THÙ MÙA VỤ & CHU KỲ THỊ TRƯỜNG GỖ CÔNG NGHIỆP VIỆT NAM](#nhóm-4-đặc-thù-mùa-vụ--chu-kỳ-thị-trường-gỗ-công-nghiệp-việt-nam)
6. [NHÓM 5: RÀNG BUỘC VẬN HÀNH & DANH MỤC HỢP ĐỒNG NỘI BỘ GML](#nhóm-5-ràng-buộc-vận-hành--danh-mục-hợp-đồng-nội-bộ-gml)
7. [HƯỚNG DẪN TÍCH HỢP VÀO HỆ THỐNG MULTI-AGENT V2.0](#7-hướng-dẫn-tích-hợp-vào-hệ-thống-multi-agent-v20)

---

## 1. TỔNG QUAN KHUNG TRI THỨC 5 TẦNG

Trong hệ thống AI truyền thống (Phase 1), AI chỉ thực hiện:
$$\text{User Query} \longrightarrow \text{Text-to-SQL} \longrightarrow \text{Raw Numbers}$$

Khi tích hợp **Khung Tri thức 5 tầng**, quy trình xử lý của AI được nâng cấp thành:
$$\text{Raw Numbers} + \text{Khung Tri thức 5 Tầng} \longrightarrow \text{Ý nghĩa} + \text{Nguyên nhân gốc rễ} + \text{Khuyến nghị hành động}$$

```
┌────────────────────────────────────────────────────────────────────────┐
│                   KHUNG TRI THỨC CHUYÊN BIỆT GML                       │
├────────────────────────────────────────────────────────────────────────┤
│ Tầng 5: Dữ liệu nội bộ thực tế (bc_tin_dung_2026, Hop_dong_tien_gui)   │
│ Tầng 4: Bối cảnh ngành gỗ & Chu kỳ xây dựng (VIFOREST, VCBS, SSI)     │
│ Tầng 3: Kịch bản hành động CFO Playbooks & SOPs (Steven M. Bragg)      │
│ Tầng 2: Quy chuẩn kế toán & Hệ số tài chính VN (TT 200/2014/TT-BTC)    │
│ Tầng 1: Lý thuyết Chu kỳ tiền CCC & Vốn lưu động (CFI, Wiley)          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## NHÓM 1: CHUẨN MỰC QUẢN TRỊ VỐN LƯU ĐỘNG & CHU KỲ CHUYỂN HÓA TIỀN (CCC)

### 1.1. Tài liệu & Giáo trình cụ thể
1. **Sách chuyên khảo:** *Treasury Management: The Practitioner's Guide*
   - **Tác giả:** Steven M. Bragg (John Wiley & Sons, 2010).
   - **Link tham khảo chính thức:** [Wiley Treasury Management Guide](https://www.wiley.com/en-us/Treasury+Management%3A+The+Practitioner%27s+Guide-p-9780470497081)
   - **Chương cốt lõi:** Chương 4: *Cash Forecasting*, Chương 5: *Cash Concentration* & Chương 7: *Working Capital Management*.
2. **Khung chuyên môn phân tích:** *Cash Conversion Cycle (CCC) & Operating Cycle*
   - **Tổ chức phát hành:** Corporate Finance Institute (CFI).
   - **Link tài liệu:** [CFI Cash Conversion Cycle Guide](https://corporatefinanceinstitute.com/resources/accounting/cash-conversion-cycle/)

### 1.2. Ứng dụng nghiệp vụ vào Gỗ Minh Long
Sợi dây chỉ đỏ xuyên suốt 5 Dashboard của GML là **Chu kỳ chuyển hóa tiền (Cash Conversion Cycle - CCC)**:
$$\text{CCC (Ngày)} = \text{DIO (Tồn kho)} + \text{DSO (Phải thu)} - \text{DPO (Phải trả)}$$

- **Bản chất nghiệp vụ:** 
  - Nếu **DIO tăng** (hàng ván dăm, MDF thô tồn đọng nhiều) hoặc **DSO tăng** (đại lý cấp 1 và xưởng mộc chậm trả tiền) mà **DPO không đổi** $\rightarrow$ CCC kéo dài $\rightarrow$ Doanh nghiệp bị thiếu hụt dòng tiền mặt ngắn hạn $\rightarrow$ Bắt buộc phải rút vốn vay ngắn hạn ngân hàng (TK 341) $\rightarrow$ Đội chi phí lãi vay (TK 635) $\rightarrow$ Bào mòn lợi nhuận ròng.
- **Quy tắc giải thích cho AI:** Khi dòng tiền thuần âm hoặc chi phí lãi vay tăng, AI phải phân tích xem nguyên nhân là do tồn kho ứ đọng (DIO) hay do nợ khó đòi ngoài thị trường (DSO).

---

## NHÓM 2: CHẾ ĐỘ KẾ TOÁN & HỆ THỐNG CHỈ SỐ TÀI CHÍNH VIỆT NAM (TT 200/2014/TT-BTC)

### 2.1. Tài liệu & Quy chuẩn pháp lý
1. **Thông tư số 200/2014/TT-BTC:** *Hướng dẫn Chế độ Kế toán Doanh nghiệp* (Thay thế QĐ 15/2006).
   - **Cơ quan ban hành:** Bộ Tài chính Việt Nam.
   - **Link văn bản đầy đủ:** [Thư Viện Pháp Luật — Thông tư 200/2014/TT-BTC](https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Thong-tu-200-2014-TT-BTC-huong-dan-Che-do-ke-toan-Doanh-nghiep-262024.aspx)
   - **Điều khoản trọng tâm:** Quy định tài khoản Tiền và Tương đương tiền (111, 112, 128), Phải thu (131), Phải trả (331), Vay ngắn hạn (341), Dự phòng nợ khó đòi (2293) và nguyên tắc lập Báo cáo lưu chuyển tiền tệ (Điều 112 - 114).
2. **Giáo trình phân tích:** *Giáo trình Phân tích Báo cáo Tài chính Doanh nghiệp Sản xuất*
   - **Tổ chức:** Đại học Kinh tế Quốc dân (NEU) & Học viện Tài chính (AOF).
   - **Link tham khảo:** [Khoa Tài chính Doanh nghiệp — NEU](https://khoataichinh.neu.edu.vn/)

### 2.2. Ma trận Hệ số Chuẩn & Ngưỡng Giám sát Rủi ro cho Doanh nghiệp Gỗ GML

| Nhóm chỉ số | Chỉ số & Công thức | Ngưỡng Tốt (Xanh) | Ngưỡng Cảnh báo (Vàng) | Ngưỡng Nguy hiểm (Đỏ) | Ý nghĩa quản trị tại GML |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Thanh khoản** | **Current Ratio (CR)** = Tài sản NH / Nợ NH | $\ge 1.5$ | $1.1 - 1.49$ | $< 1.1$ | Khả năng trả nợ vay ngắn hạn bằng tài sản ngắn hạn |
| **Thanh khoản** | **Quick Ratio (QR)** = (Tiền + Đầu tư + Thu) / Nợ NH | $\ge 1.0$ | $0.7 - 0.99$ | $< 0.7$ | Loại trừ tồn kho; đánh giá khả năng thanh toán tức thời |
| **Thanh khoản** | **Cash Runway** = Số dư tiền / Chi phí chi tiền hàng tháng | $> 3.0$ tháng | $1.5 - 3.0$ tháng | $< 1.5$ tháng | Số tháng doanh nghiệp cầm cự nếu không có doanh thu mới |
| **Vốn lưu động** | **DSO** = (Phải thu BQ / Doanh thu) * 365 | $\le 45$ ngày | $46 - 60$ ngày | $> 60$ ngày | Thời gian thu tiền nợ từ các đại lý & xưởng mộc |
| **Vốn lưu động** | **DIO** = (Tồn kho BQ / Giá vốn) * 365 | $\le 60$ ngày | $61 - 90$ ngày | $> 90$ ngày | Thời gian giải phóng hàng ván ép và phủ Melamine |
| **Vốn lưu động** | **DPO** = (Phải trả BQ / Giá vốn) * 365 | $40 - 60$ ngày | $25 - 39$ ngày | $< 25$ ngày | Thời gian tận dụng vốn của nhà cung cấp keo/ván thô |
| **Cấu trúc Nợ** | **D/E** = Tổng nợ vay / Vốn chủ sở hữu | $\le 1.0$ | $1.1 - 1.8$ | $> 1.8$ | Mức độ phụ thuộc vào vốn vay ngân hàng thương mại |
| **An toàn Lãi vay** | **ICR** = EBIT / Chi phí lãi vay (TK 635) | $\ge 3.0$ | $1.5 - 2.9$ | $< 1.5$ | Khả năng tạo lợi nhuận để gánh lãi suất ngân hàng |

---

## NHÓM 3: CẨM NANG HÀNH ĐỘNG CỦA CFO & QUY TRÌNH SOP QUẢN TRỊ RỦI RO

### 3.1. Tài liệu chuyên gia
1. **Sách cẩm nang quản trị:** *The CFO Guidebook* & *Accounting Controls Guidebook*
   - **Tác giả:** Steven M. Bragg (AccountingTools, Inc.).
   - **Link tham khảo:** [AccountingTools CFO Guidebook](https://www.accountingtools.com/cfo-guidebook) | [Working Capital Controls](https://www.accountingtools.com/working-capital-management)
2. **Quy chuẩn tín dụng thương mại:** *Credit and Collection Handbook* — National Association of Credit Management (NACM).
   - **Link tham khảo:** [NACM Bookstore & Guidelines](https://nacm.org/)

### 3.2. 4 Kịch bản Hành động (Playbooks / SOP) Chuẩn hóa cho AI GML

#### Kịch bản 1: Thâm hụt Dòng tiền & Cạn kiệt Thanh khoản (Cash Crunch SOP)
- **Điều kiện kích hoạt:** `Cash Runway < 1.5 tháng` HOẶC `Net Cashflow dự báo 4 tuần tới liên tục âm`.
- **Hành động AI đề xuất:**
  1. *Hành động tức thì (Trong 24h):* Kiểm tra ngay `bc_tin_dung_2026.xlsx`, rà soát hạn mức tín dụng khả dụng tại ngân hàng có lãi suất thấp nhất (ưu tiên giải ngân các khế ước có lãi suất < 6.5%).
  2. *Điều chỉnh thu nợ:* Kích hoạt chính sách chiết khấu thanh toán sớm 1.0 - 1.5% đối với các đại lý nợ lớn trong hạn để khuyến khích nộp tiền mặt ngay.
  3. *Tối ưu dòng tiền ra:* Đàm phán với 3 nhà cung cấp ván thô lớn nhất xin gia hạn thanh toán thêm 10-15 ngày; tạm dừng giải ngân mua sắm TSCĐ (Capex).

#### Kịch bản 2: Dôi dư Tiền mặt Ngắn hạn (Excess Liquidity Optimization SOP)
- **Điều kiện kích hoạt:** `Cash Runway > 3.5 tháng` VÀ `Số dư tiền không kỳ hạn > Đệm tiền an toàn (20 tỷ VNĐ)`.
- **Hành động AI đề xuất:**
  1. *Phân tích lịch đáo hạn:* Kiểm tra lịch trả nợ vay ngân hàng trong 30 ngày tới.
  2. *Gợi ý điều hòa vốn (Treasury):* Trích xuất khoản tiền dôi dư (ví dụ 10 - 15 tỷ) gửi tiết kiệm có kỳ hạn 1 tháng hoặc 3 tháng tại ngân hàng có biểu lãi suất cao nhất (theo dữ liệu `Hop_dong_tien_gui.xlsm`) để tăng doanh thu tài chính (TK 515).
  3. *Tất toán nợ trước hạn:* So sánh: Nếu lãi suất tiền gửi < lãi suất vay ngân hàng của khế ước đang chịu lãi cao (ví dụ 7.5%), đề xuất dùng tiền dôi dư trả bớt nợ gốc để giảm chi phí lãi vay (TK 635).

#### Kịch bản 3: Rủi ro Công nợ Quá hạn Tăng cao (AR Overdue Crisis SOP)
- **Điều kiện kích hoạt:** `DSO > 60 ngày` HOẶC `Tỷ lệ nợ quá hạn > 15% tổng nợ`.
- **Hành động AI đề xuất:**
  1. *Phân rã đối tượng:* Truy vấn Top 5 khách hàng/đại lý có số dư nợ quá hạn lớn nhất từ Fact AR.
  2. *Khóa hạn mức bán hàng:* Đề xuất bộ phận Kinh doanh tự động dừng xuất kho các đơn hàng mới đối với khách hàng có nợ quá hạn > 60 ngày.
  3. *Quy trình thu hồi nợ:* Đề xuất gửi công văn đối chiếu công nợ có xác nhận pháp lý; chuyển hồ sơ sang bộ phận pháp chế nếu quá hạn > 90 ngày.

#### Kịch bản 4: Tồn kho Ứ đọng / Chậm Luân chuyển (Slow-Moving Inventory SOP)
- **Điều kiện kích hoạt:** `DIO > 90 ngày` HOẶC `Tồn kho nhóm ván phủ Melamine tăng > 25% so với cùng kỳ`.
- **Hành động AI đề xuất:**
  1. *Xác định mã SKU ứ đọng:* Bóc tách danh sách các mã bề mặt melamine/ván cốt có vòng quay tồn kho < 1.0 lần/quý.
  2. *Chiến lược giải phóng hàng tồn:* Đề xuất gói khuyến mãi chiết khấu 8-12% cho các nhà thầu thi công dự án trọn gói hoặc xưởng nội thất ngoại thành.
  3. *Giảm định mức sản xuất:* Cảnh báo nhà máy giảm nhập ván thô cho các mã cốt đang dư thừa; ưu tiên ép phủ theo đơn hàng thực tế (Make-to-Order).

---

## NHÓM 4: ĐẶC THÙ MÙA VỤ & CHU KỲ THỊ TRƯỜNG GỖ CÔNG NGHIỆP VIỆT NAM

### 4.1. Báo cáo Chuyên ngành Tham chiếu
1. **Báo cáo Thị trường Ngành Gỗ & Lâm sản Việt Nam — Hiệp hội VIFOREST**
   - **Tổ chức:** Hiệp hội Gỗ và Lâm sản Việt Nam (VIFOREST).
   - **Link tham khảo:** [Trang thông tin VIFOREST](http://vietfores.org.vn/)
2. **Báo cáo Phân tích Ngành Vật liệu Xây dựng & Bất động sản — VCBS & SSI Research**
   - **Tổ chức:** CTCK Vietcombank (VCBS) & SSI Research.
   - **Link tra cứu:** [SSI Research — Báo cáo ngành](https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-phan-tich) | [Vietstock Ngành Gỗ](https://vietstock.vn/)

### 4.2. Lịch biểu Chu kỳ Mùa vụ 4 Quý tại Gỗ Minh Long
AI cần nắm rõ chu kỳ này trong module `TrendAnalystAgent` để tránh diễn giải sai lệch các biến động tự nhiên:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CHU KỲ MÙA VỤ NGÀNH GỖ                          │
├──────────────┬───────────────────────────────┬─────────────────────────┤
│ Giai đoạn    │ Đặc điểm thị trường           │ Trọng tâm tài chính GML │
├──────────────┼───────────────────────────────┼─────────────────────────┤
│ Quý 1        │ Thấp điểm (Sau Tết Nguyên Đán)│ Dòng tiền thu về chậm   │
│ (T1 - T3)    │ Công trình mới khởi công      │ Duy trì đệm tiền mặt    │
├──────────────┼───────────────────────────────┼─────────────────────────┤
│ Quý 2 - 3    │ Nhập nguyên liệu, sản xuất    │ DIO tăng cao            │
│ (T4 - T8)    │ Xưởng mộc tích trữ hàng thô   │ Tận dụng vốn vay nợ NH  │
├──────────────┼───────────────────────────────┼─────────────────────────┤
│ Quý 4        │ CAO ĐIỂM BÀN GIAO NỘI THẤT    │ Doanh thu đạt đỉnh      │
│ (T9 - T12)   │ Hoàn thiện nhà đón Tết        │ Siết chặt DSO thu nợ    │
└──────────────┴───────────────────────────────┴─────────────────────────┘
```
- **Nguyên tắc cảnh báo xu hướng của AI:** Nếu doanh thu tháng 2 giảm 30% so với tháng 12 năm trước, AI phải diễn giải: *"Đây là đặc thù chu kỳ sau Tết Nguyên đán của ngành vật liệu nội thất, không phải suy thoái do mất thị phần"*.

---

## NHÓM 5: RÀNG BUỘC VẬN HÀNH & DANH MỤC HỢP ĐỒNG NỘI BỘ GML

Để các đề xuất của AI có tính thực thi 100%, AI phải được cấp quyền truy xuất các ràng buộc trong các tài liệu nội bộ sau:

1. **Báo cáo Hạn mức Tín dụng & Lãi suất Ngân hàng (`bc_tin_dung_2026.xlsx`):**
   - Hạn mức được cấp (Credit Limit) của từng ngân hàng (BIDV, VietinBank, Techcombank,...).
   - Dư nợ thực tế hiện tại và Hạn mức khả dụng còn lại.
   - Biểu lãi suất vay ngắn hạn từng khế ước.
   - **Ý nghĩa:** Khi đề xuất vay thêm vốn lưu động, AI chỉ đề xuất ngân hàng *còn hạn mức khả dụng* và *lãi suất thấp nhất*.
2. **Sổ theo dõi Hợp đồng Tiền gửi Tiết kiệm (`Hop_dong_tien_gui.xlsm`):**
   - Danh sách các sổ tiết kiệm đang gửi tại các ngân hàng.
   - Ngày gửi, ngày đáo hạn, lãi suất kỳ hạn (ví dụ: 4.5% cho kỳ hạn 1 tháng, 5.8% cho kỳ hạn 6 tháng).
   - Điều khoản phạt rút trước hạn (thường mất toàn bộ lãi kỳ hạn, chuyển về lãi không kỳ hạn 0.1%).
   - **Ý nghĩa:** Khi cần tiền khẩn cấp, AI sẽ đề xuất rút những sổ *gần sát ngày đáo hạn nhất* hoặc sổ có *giá trị phạt lãi suất nhỏ nhất*.
3. **Kế hoạch Ngân sách Kinh doanh Năm (`fact_businessplan`):**
   - Định mức trần chi phí và chỉ tiêu doanh thu từng tháng.
   - **Ý nghĩa:** Đối chiếu thực tế vs kế hoạch (Variance Analysis) để chỉ rõ phòng ban nào đang chi vượt ngân sách.

---

## 7. HƯỚNG DẪN TÍCH HỢP VÀO HỆ THỐNG MULTI-AGENT V2.0

### 7.1. Cấu trúc Tri thức hóa (Knowledge Structuring)
Chúng ta sẽ chuyển hóa toàn bộ tài liệu trên thành 2 tệp tin cấu hình YAML chuẩn trong thư mục `app/knowledge/`:
1. `kpi_benchmarks_and_thresholds.yaml`: Lưu trữ toàn bộ bảng ngưỡng Xanh/Vàng/Đỏ của 18 KPI.
2. `cfo_playbooks.yaml`: Lưu trữ các điều kiện kích hoạt và hành động mẫu của 4 kịch bản SOP.

### 7.2. Tích hợp vào Luồng LangGraph

```
                 ┌────────────────────────────────┐
                 │       User: CEO / CFO          │
                 └──────────────┬─────────────────┘
                                │ "Dòng tiền tháng này thế nào?"
                                ▼
                 ┌────────────────────────────────┐
                 │      Orchestrator Agent        │
                 └──────────────┬─────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│          SQL Agent           │        │          RAG Agent           │
│ Truy vấn Fact Cashflow & AR  │        │ Đọc Playbooks & TT 200       │
│ Kết quả: Net Cash = -4.2 tỷ  │        │ Ngưỡng: Cần duy trì 15 tỷ    │
└──────────────┬───────────────┘        └──────────────┬───────────────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   ▼
        ┌──────────────────────────────────────────────┐
        │       Explainer & Decision Advisor Agent     │
        │ - Bản chất: DSO tăng 14 ngày, CCC kéo dài    │
        │ - Ngưỡng rủi ro: Cash Runway giảm còn 1.1 th │
        │ - SOP đề xuất: Kích hoạt hạn mức BIDV (6.2%) │
        └──────────────────────┬───────────────────────┘
                               ▼
        💬 Câu trả lời chuẩn mực & Có tính hành động cao
```

---
*Tài liệu được biên soạn phục vụ công tác chuẩn hóa nghiệp vụ cho Dự án Trợ lý Trí tuệ Doanh nghiệp — Công ty TNHH Gỗ Minh Long.*
