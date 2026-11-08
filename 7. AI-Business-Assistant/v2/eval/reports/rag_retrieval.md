# Phase 3 Gate Evidence EV-06: RAG Retrieval Evaluation (DEV Split)

- **Generated At**: `2026-11-08 14:35:22 UTC`
- **Git Commit**: `71d713f`
- **Split**: `dev` (Total items: `14`)
- **M-03 (Hit@5 Target)**: v2 >= v1 + 15 pp (v1: `50.00%`, v2: `85.71%`, Delta: `+35.71 pp`)
- **M-04 (MRR Target)**: v2 >= v1 + 15 pp (v1: `36.90%`, v2: `82.14%`, Delta: `+45.24 pp`)

## Summary Metrics

| Metric | v1 Baseline (Naive Chunking) | v2 Hybrid RAG (Hierarchical + BM25 + RRF) | Delta | Gate Status |
|---|---|---|---|---|
| **M-03 (Hit@5)** | 50.00% | 85.71% | +35.71 pp | PASSED |
| **M-04 (MRR)** | 36.90% | 82.14% | +45.24 pp | PASSED |

## Detailed Question Breakdown

| ID | Type | Question | Expected Target | v1 Rank | v2 Rank | Status |
|---|---|---|---|---|---|---|
| `BM_RAG_DEV_01` | `rag` | Chỉ số LTV trên Dashboard Tài chính được định nghĩa như thế nào và ngưỡng cảnh báo là bao nhiêu? | `guide_dashboard1.md # Muc-1-Chi-so-tong-quan` | Miss | **Rank 1** | ✅ Win |
| `BM_RAG_DEV_02` | `rag` | Quy định về thời gian lưu kho và phân loại hàng tồn kho chậm luân chuyển tại Gỗ Minh Long ra sao? | `guide_dashboard2.md # Quan-tri-hang-ton-kho` | Rank 3 | **Rank 1** | ✅ Both Hit |
| `BM_RAG_DEV_03` | `rag` | Chính sách quản lý hạn mức công nợ và điều khoản thanh toán đối với khách hàng đại lý? | `guide_dashboard3.md # Chinh-sach-cong-no` | Rank 1 | **Miss** | ⚠️ Miss |
| `BM_RAG_DEV_04` | `rag` | Nguyên tắc quản trị tiền gửi và phân bổ thanh khoản theo kỳ hạn của công ty? | `guide_dashboard4.md # Quan-tri-tien-gui-thanh-khoan` | Rank 1 | **Rank 1** | ✅ Both Hit |
| `BM_RAG_DEV_05` | `rag` | Cách phân loại dòng tiền vào, dòng tiền ra và loại trừ giao dịch chuyển tiền nội bộ trên Dashboard 5? | `guide_dashboard5.md # Dinh-nghia-dong-tien` | Rank 1 | **Rank 2** | ✅ Both Hit |
| `BM_RAG_DEV_06` | `rag` | Quy trình phê duyệt tái cấp hạn mức tín dụng ngân hàng theo Cẩm nang Nghiệp vụ Toàn thư GML? | `Cam_nang_Nghiep_vu_Toan_thu_GML.md # Quy-trinh-tin-dung` | Miss | **Rank 1** | ✅ Win |
| `BM_RAG_DEV_07` | `rag` | Kịch bản ứng phó khi tỷ lệ sử dụng hạn mức vượt ngưỡng 90% theo Story Telling báo cáo tài chính? | `Story Telling báo cáo quản trị tài chính – Gỗ Minh Long.md # Kich-ban-rui-ro` | Miss | **Rank 1** | ✅ Win |
| `BM_BOTH_DEV_01` | `both` | Tỷ lệ sử dụng hạn mức hiện tại là bao nhiêu và vượt ngưỡng an toàn thì quy định xử lý thế nào? | `guide_dashboard1.md # Ty-le-su-dung-han-muc` | Miss | **Miss** | ⚠️ Miss |
| `BM_BOTH_DEV_02` | `both` | Hệ số LTV hiện tại là bao nhiêu và tài sản bảo đảm nào đang được thế chấp chủ yếu? | `guide_dashboard1.md # He-so-LTV` | Miss | **Rank 1** | ✅ Win |
| `BM_BOTH_DEV_03` | `both` | Giá trị hàng tồn kho hiện nay là bao nhiêu và tỷ lệ hàng nhập khẩu chiếm tỷ trọng thế nào? | `guide_dashboard2.md # Ty-trong-nhap-khau` | Rank 3 | **Rank 1** | ✅ Both Hit |
| `BM_BOTH_DEV_04` | `both` | Dư nợ phải thu hiện tại là bao nhiêu và quy trình đốc thúc thu nợ quá hạn như thế nào? | `guide_dashboard3.md # Quy-trinh-thu-hoi-no` | Rank 1 | **Rank 1** | ✅ Both Hit |
| `BM_BOTH_DEV_05` | `both` | Lãi suất tiền gửi bình quân là bao nhiêu và ngân hàng nào đang có lãi suất huy động cao nhất? | `guide_dashboard4.md # So-sanh-lai-suat-ngan-hang` | Miss | **Rank 1** | ✅ Win |
| `BM_BOTH_DEV_06` | `both` | Dòng tiền thuần thực tế hiện tại là bao nhiêu và các giải pháp cân đối nguồn tiền thâm hụt? | `guide_dashboard5.md # Can-doi-dong-tien` | Rank 2 | **Rank 1** | ✅ Both Hit |
| `BM_BOTH_DEV_07` | `both` | Dư nợ ngắn hạn và dài hạn hiện tại là bao nhiêu, cơ cấu nợ này phản ánh chiến lược tài chính gì? | `Story Telling báo cáo quản trị tài chính – Gỗ Minh Long.md # Co-cau-no-vay` | Miss | **Rank 1** | ✅ Win |
