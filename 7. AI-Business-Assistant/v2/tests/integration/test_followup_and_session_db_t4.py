"""Database integration tests for Task 1: Session Memory TTL/erasure, Cross-User Isolation, and 3-turn Follow-up.

Specifications:
- TC-T2-07: Session TTL cutoff, expired purge, and user-initiated history deletion.
- Review Focus #1: Cross-user session isolation (no cross-user history leakage even with identical session_id).
- TC-T4-06: 3-turn follow-up on synthetic data warehouse (gml_synth) preserving conversational context.
"""

from datetime import datetime, timedelta, timezone
import pytest
import sqlalchemy as sa

from app.memory.session_store import SessionStore
from app.orchestration.graph import build_v2_graph
from app.orchestration.state import ChatState
from db.apply_db import get_app_engine


def test_tc_t2_07_session_ttl_purge_and_user_delete():
    """TC-T2-07: SessionStore enforces TTL cutoff on retrieval, purges expired records, and allows user erasure."""
    store = SessionStore(data_profile="synth", ttl_days=30)
    now = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
    t_35d_ago = now - timedelta(days=35)
    t_1d_ago = now - timedelta(days=1)

    user_a = "test-user-a-t2"
    user_b = "test-user-b-t2"
    session_a = "sess-ttl-a"
    session_b = "sess-ttl-b"

    # Clean existing test data first
    store.delete_user_history(user_a)
    store.delete_user_history(user_b)

    try:
        # Insert turn 35 days ago for user A
        store.add_turn(
            session_id=session_a,
            user_id=user_a,
            query="Dư nợ ngắn hạn kỳ trước?",
            standalone_query="Dư nợ ngắn hạn kỳ trước?",
            created_at=t_35d_ago,
        )

        # Insert turn 1 day ago for user A
        store.add_turn(
            session_id=session_a,
            user_id=user_a,
            query="Tỷ lệ sử dụng hạn mức hiện tại?",
            standalone_query="Tỷ lệ sử dụng hạn mức hiện tại?",
            created_at=t_1d_ago,
        )

        # Insert turn for user B (control user)
        store.add_turn(
            session_id=session_b,
            user_id=user_b,
            query="Giá trị hàng tồn kho?",
            standalone_query="Giá trị hàng tồn kho?",
            created_at=t_1d_ago,
        )

        # 1. get_history excludes expired turns (older than 30 days)
        hist_a = store.get_history(session_id=session_a, user_id=user_a, n=5, now=now)
        assert len(hist_a) == 1, f"Expected 1 non-expired turn for user A, got {len(hist_a)}"
        assert hist_a[0].query == "Tỷ lệ sử dụng hạn mức hiện tại?"

        # 2. purge_expired removes 35d old turn
        deleted_count = store.purge_expired(ttl_days=30, now=now)
        assert deleted_count >= 1, f"Expected at least 1 purged turn, got {deleted_count}"

        # 3. delete_user_history deletes user A's remaining turns without touching user B
        deleted_a = store.delete_user_history(user_a)
        assert deleted_a >= 1

        hist_a_after = store.get_history(session_id=session_a, user_id=user_a, n=5, now=now)
        assert len(hist_a_after) == 0

        hist_b = store.get_history(session_id=session_b, user_id=user_b, n=5, now=now)
        assert len(hist_b) == 1, "User B's history must remain intact"
        assert hist_b[0].query == "Giá trị hàng tồn kho?"

    finally:
        store.delete_user_history(user_a)
        store.delete_user_history(user_b)


def test_review_focus_1_cross_user_session_isolation():
    """Review Focus #1: Verify strict cross-user session isolation.
    
    A session_id reused by another user must return zero turns and prevent context leakage.
    """
    store = SessionStore(data_profile="synth")
    shared_session_id = "sess-shared-cross-user-test"
    user_ceo = "user-ceo-isolation"
    user_kho = "user-kho-isolation"

    store.delete_user_history(user_ceo)
    store.delete_user_history(user_kho)

    try:
        # CEO asks financial query
        store.add_turn(
            session_id=shared_session_id,
            user_id=user_ceo,
            query="Dư nợ ngắn hạn?",
            standalone_query="Tổng dư nợ ngắn hạn của công ty hiện tại là bao nhiêu?",
            kpi_keys=["du_no_ngan_han"],
        )

        # Warehouse user asks about the same session_id
        hist_kho = store.get_history(session_id=shared_session_id, user_id=user_kho)
        assert len(hist_kho) == 0, "Warehouse user must not see CEO's conversation history"

        # Warehouse user running build_v2_graph must not inherit CEO's query context
        graph = build_v2_graph(session_store=store)
        state_kho = graph.invoke({
            "request_id": "req-iso-kho",
            "user": {"id": user_kho, "role": "quan_ly_kho"},
            "session_id": shared_session_id,
            "query": "Còn tháng trước?",
            "data_profile": "synth",
        })

        # Since kho user has no previous turn in this session, standalone_query does not inherit du_no_ngan_han
        assert state_kho["standalone_query"] == "Còn tháng trước?" or "dư nợ" not in state_kho["standalone_query"].lower()

    finally:
        store.delete_user_history(user_ceo)
        store.delete_user_history(user_kho)


def test_tc_t4_06_three_turn_followup_on_synth():
    """TC-T4-06: Sequential 3-turn follow-up on synthetic data warehouse resolving context.
    
    Turn 1: 'Dư nợ ngắn hạn?' -> ~236,070,000,000.0 (236,07 tỷ)
    Turn 2: 'Còn tháng trước?' -> standalone query includes 'dư nợ ngắn hạn' & '06/2026', ~283,700,000,000.0 (283,7 tỷ)
    Turn 3: 'Giảm bao nhiêu %?' -> standalone query rewrites MoM comparison 07/2026 vs 06/2026, ~-0.167889 (-16.8%), SYNTHETIC_DATA in warnings
    """
    store = SessionStore(data_profile="synth")
    session_id = "sess-3turn-followup-synth"
    user_id = "user-ceo-3turn"

    store.delete_user_history(user_id)

    try:
        graph = build_v2_graph(session_store=store)

        # ----------------- Turn 1 -----------------
        state_t1 = graph.invoke({
            "request_id": "req-turn-1",
            "user": {"id": user_id, "role": "ceo"},
            "session_id": session_id,
            "query": "Dư nợ ngắn hạn?",
            "data_profile": "synth",
        })

        assert state_t1.get("intent") in ("sql_only", "both")
        ans_t1 = state_t1.get("answer") or {}
        assert len(ans_t1.get("figures", [])) > 0
        fig_t1 = ans_t1["figures"][0]["value"]
        assert abs(fig_t1 - 236_070_000_000.0) / 236_070_000_000.0 < 0.005, f"Turn 1 expected ~236.07B, got {fig_t1}"
        assert "SYNTHETIC_DATA" in ans_t1.get("warnings", [])

        # Store turn 1 into SessionStore
        store.add_turn(
            session_id=session_id,
            user_id=user_id,
            query=state_t1["query"],
            standalone_query=state_t1.get("standalone_query"),
            intent=state_t1.get("intent"),
            kpi_keys=state_t1.get("kpi_keys"),
            sql_query=(state_t1.get("sql") or {}).get("sql"),
            answer=ans_t1,
            confidence=ans_t1.get("confidence"),
            request_id=state_t1.get("request_id"),
        )

        # ----------------- Turn 2 -----------------
        state_t2 = graph.invoke({
            "request_id": "req-turn-2",
            "user": {"id": user_id, "role": "ceo"},
            "session_id": session_id,
            "query": "Còn tháng trước?",
            "data_profile": "synth",
        })

        sq_t2 = (state_t2.get("standalone_query") or "").lower()
        assert "dư nợ ngắn hạn" in sq_t2 or "du no ngan han" in sq_t2 or "34111" in sq_t2
        assert "06/2026" in sq_t2 or "tháng 6" in sq_t2 or "thang 6" in sq_t2 or "2026-06" in sq_t2

        ans_t2 = state_t2.get("answer") or {}
        assert len(ans_t2.get("figures", [])) > 0
        fig_t2 = ans_t2["figures"][0]["value"]
        assert abs(fig_t2 - 283_700_000_000.0) / 283_700_000_000.0 < 0.005, f"Turn 2 expected ~283.7B, got {fig_t2}"
        assert "SYNTHETIC_DATA" in ans_t2.get("warnings", [])

        # Store turn 2 into SessionStore
        store.add_turn(
            session_id=session_id,
            user_id=user_id,
            query=state_t2["query"],
            standalone_query=state_t2.get("standalone_query"),
            intent=state_t2.get("intent"),
            kpi_keys=state_t2.get("kpi_keys"),
            sql_query=(state_t2.get("sql") or {}).get("sql"),
            answer=ans_t2,
            confidence=ans_t2.get("confidence"),
            request_id=state_t2.get("request_id"),
        )

        # ----------------- Turn 3 -----------------
        state_t3 = graph.invoke({
            "request_id": "req-turn-3",
            "user": {"id": user_id, "role": "ceo"},
            "session_id": session_id,
            "query": "Giảm bao nhiêu %?",
            "data_profile": "synth",
        })

        sq_t3 = (state_t3.get("standalone_query") or "").lower()
        assert "giảm" in sq_t3 or "thay đổi" in sq_t3 or "%" in sq_t3 or "phần trăm" in sq_t3
        assert ("07/2026" in sq_t3 or "tháng 7" in sq_t3) and ("06/2026" in sq_t3 or "tháng 6" in sq_t3)

        ans_t3 = state_t3.get("answer") or {}
        assert len(ans_t3.get("figures", [])) > 0
        fig_t3 = ans_t3["figures"][0]["value"]
        # Expected around -0.167889 (-16.8%)
        assert abs(fig_t3 - (-0.167889)) < 0.005, f"Turn 3 expected ~-0.1679 (-16.8%), got {fig_t3}"
        assert "SYNTHETIC_DATA" in ans_t3.get("warnings", [])

    finally:
        store.delete_user_history(user_id)
