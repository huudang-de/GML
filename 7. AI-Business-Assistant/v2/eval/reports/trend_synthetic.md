# Phase 3 Gate Evidence EV-09: Trend & Anomaly Evaluation Report

- **Generated At**: `2026-11-08 14:08:23 UTC`
- **Git Commit**: `96ee6dc`
- **M-09 (Anomaly Recall Target >= 90%)**: `100.00%` (5/5)
- **M-10 (Max FP Target <= 1/KPI/12m)**: `0` per KPI
- **TC-T3-10 Honest Coverage Guard**: `PASSED`

## Summary Metrics

| Metric | Specification Target | Observed Value | Gate Status |
|---|---|---|---|
| **M-09 (Anomaly Recall)** | >= 90% | **100.00%** (5/5) | PASSED |
| **M-10 (False Positive Rate)** | <= 1 / KPI / 12m | **0** max alarms / KPI | PASSED |
| **TC-T3-10 (Honest 1-Month)** | No fabricated growth rates | 1 month coverage, growth=None | PASSED |

## Labeled Synthetic Anomalies Verification (M-09)

| ID | KPI Key | Period | Expected Severity | Detected | Anomaly Log |
|---|---|---|---|---|---|
| `ANOM-01` | `du_no_ngan_han` | `2026-07` | `canh_bao` | ✅ Yes | 2026-07 (nghiem_trong) |
| `ANOM-02` | `ton_kho_sku` | `2026-03-31` | `nghiem_trong` | ✅ Yes | 2026-03 (nghiem_trong) |
| `ANOM-03` | `current_ratio` | `2025-11-30` | `canh_bao` | ✅ Yes | 2025-11 (canh_bao) |
| `ANOM-04` | `ty_le_su_dung_han_muc` | `2026-07-31` | `canh_bao` | ✅ Yes | 2026-07 (canh_bao) |
| `ANOM-05` | `dong_tien_rong` | `2026-02` | `nghiem_trong` | ✅ Yes | 2026-02 (nghiem_trong) |

## Normal Control KPIs False Positive Analysis (M-10)

| KPI Key | Product Code | Coverage (Months) | False Positive Alarms | Alarm Periods | Status |
|---|---|---|---|---|---|
| `du_no_dai_han` | `-` | 0 | 0 | None (Clean) | ✅ Pass |
| `doanh_thu_thuan` | `-` | 12 | 0 | None (Clean) | ✅ Pass |
| `tien_va_tuong_duong_tien` | `-` | 12 | 0 | None (Clean) | ✅ Pass |
| `ty_le_no_tren_tong_nguon_von` | `-` | 12 | 0 | None (Clean) | ✅ Pass |
| `ton_kho_sku` | `SYNTH_SKU_MFC18` | 12 | 0 | None (Clean) | ✅ Pass |

## TC-T3-10 Single-Month Honest Coverage Guard

- Real profile `doanh_thu_thuan` coverage: `1` month(s)
- `mom_growth`: `None`
- `yoy_growth`: `None`
- Warnings attached: `['Chỉ có 1 tháng dữ liệu, chưa đủ để phân tích xu hướng']`
- Verdict: `PASS - Zero fabricated metrics`
