# Phase 4 Gate Evidence EV-11: Intent Routing Matrix & Latency Report

- **Generated At**: `2026-11-08 15:27:21 UTC`
- **Git Commit**: `0d4a1be`
- **Dataset Split**: `dev` (DEV SET ONLY)
- **Total Evaluated**: `40`
- **M-11 (Routing Accuracy Target >= 95%)**: `100.00%` (40/40)
- **Gate Status**: `PASSED`
- **EV-12 Trace Sample**: `trace_both_sample.json`

## 5×5 Intent Confusion Matrix

| Expected \ Predicted | sql_only | rag_only | both | alert | blocked | Accuracy |
|---|---|---|---|---|---|---|
| **`sql_only`** | 21 | 0 | 0 | 0 | 0 | **100.0%** |
| **`rag_only`** | 0 | 7 | 0 | 0 | 0 | **100.0%** |
| **`both`** | 0 | 0 | 8 | 0 | 0 | **100.0%** |
| **`alert`** | 0 | 0 | 0 | 0 | 0 | **N/A** |
| **`blocked`** | 0 | 0 | 0 | 0 | 4 | **100.0%** |

## M-12 Node Latency Profile (P50 / P95 / Max)

| Node Name | Executions | P50 Latency (ms) | P95 Latency (ms) | Max Latency (ms) |
|---|---|---|---|---|
| `advise` | 24 | 0.03 ms | 0.19 ms | 28.24 ms |
| `clarify` | 4 | 0.07 ms | 0.26 ms | 0.26 ms |
| `classify_intent` | 40 | 42.67 ms | 100.09 ms | 102.88 ms |
| `confidence_gate` | 36 | 0.0 ms | 0.01 ms | 0.01 ms |
| `explain` | 24 | 2022.27 ms | 2028.5 ms | 2030.9 ms |
| `guard_input` | 40 | 45.84 ms | 97.26 ms | 124.09 ms |
| `guard_output` | 40 | 0.06 ms | 0.11 ms | 0.27 ms |
| `join` | 36 | 0.0 ms | 0.0 ms | 0.02 ms |
| `rag_lookup` | 15 | 2292.78 ms | 2626.38 ms | 2626.38 ms |
| `resolve_context` | 40 | 0.0 ms | 0.01 ms | 0.02 ms |
| `sql_lookup` | 29 | 2532.47 ms | 3195.75 ms | 3292.08 ms |
| `synthesize` | 36 | 0.16 ms | 0.38 ms | 0.46 ms |
| `trend` | 24 | 174.04 ms | 374.44 ms | 382.52 ms |

## Benchmark Items Classification Details

| ID | Role | Expected Intent | Predicted Intent | Match | Execution Path |
|---|---|---|---|---|---|
| `BM_SQL_DEV_01` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_02` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_03` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_04` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_05` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_06` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_07` | `quan_ly_kho` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_08` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_09` | `ke_toan_truong` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_10` | `ke_toan_truong` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_11` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_12` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_13` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_14` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_SQL_DEV_15` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_RAG_DEV_01` | `ceo` | `rag_only` | `rag_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_RAG_DEV_02` | `quan_ly_kho` | `rag_only` | `rag_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_RAG_DEV_03` | `ke_toan_truong` | `rag_only` | `rag_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_RAG_DEV_04` | `ceo` | `rag_only` | `rag_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_RAG_DEV_05` | `ceo` | `rag_only` | `rag_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_RAG_DEV_06` | `ceo` | `rag_only` | `rag_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_RAG_DEV_07` | `ceo` | `rag_only` | `rag_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> join -> confidence_gate -> synthesize -> guard_output` |
| `BM_BOTH_DEV_01` | `ceo` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_BOTH_DEV_02` | `ceo` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_BOTH_DEV_03` | `quan_ly_kho` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_BOTH_DEV_04` | `ke_toan_truong` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_BOTH_DEV_05` | `ceo` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_BOTH_DEV_06` | `ceo` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_BOTH_DEV_07` | `ceo` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_FU_DEV_01` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_FU_DEV_02` | `ceo` | `both` | `both` | ✅ | `guard_input -> resolve_context -> classify_intent -> rag_lookup -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_FU_DEV_03` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> explain -> trend -> advise -> confidence_gate -> synthesize -> guard_output` |
| `BM_OOS_DEV_01` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> confidence_gate -> clarify -> guard_output` |
| `BM_OOS_DEV_02` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> confidence_gate -> clarify -> guard_output` |
| `BM_OOS_DEV_03` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> confidence_gate -> clarify -> guard_output` |
| `BM_OOS_DEV_04` | `ceo` | `sql_only` | `sql_only` | ✅ | `guard_input -> resolve_context -> classify_intent -> sql_lookup -> join -> confidence_gate -> clarify -> guard_output` |
| `BM_SEC_DEV_01` | `ceo` | `blocked` | `blocked` | ✅ | `guard_input -> resolve_context -> classify_intent -> synthesize -> guard_output` |
| `BM_SEC_DEV_02` | `ceo` | `blocked` | `blocked` | ✅ | `guard_input -> resolve_context -> classify_intent -> synthesize -> guard_output` |
| `BM_SEC_DEV_03` | `ceo` | `blocked` | `blocked` | ✅ | `guard_input -> resolve_context -> classify_intent -> synthesize -> guard_output` |
| `BM_SEC_DEV_04` | `quan_ly_kho` | `blocked` | `blocked` | ✅ | `guard_input -> resolve_context -> classify_intent -> synthesize -> guard_output` |
