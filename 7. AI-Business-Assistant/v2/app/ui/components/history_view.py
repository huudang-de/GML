"""History View component displaying previous query turns and session cleanup."""

from typing import Any
import streamlit as st

from app.ui.api_client import HttpApiClient


def render_history_view(api_client: HttpApiClient, profile: str) -> None:
    """Render conversation history with turn details and deletion options."""
    st.header("📋 Lịch sử Hội thoại")

    col_title, col_del = st.columns([4, 1])
    with col_del:
        if st.button("🗑️ Xoá lịch sử của tôi", type="secondary"):
            try:
                api_client.clear_history(profile=profile)
                if "messages" in st.session_state:
                    st.session_state.messages = []
                st.success("Đã xoá toàn bộ lịch sử hội thoại.")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi xoá lịch sử: {e}")

    try:
        turns: list[dict[str, Any]] = api_client.get_history(profile=profile)
    except Exception as e:
        st.error(f"Lỗi tải lịch sử hội thoại: {e}")
        return

    if not turns:
        st.info("Chưa có lịch sử hội thoại nào được lưu.")
        return

    st.caption(f"Tổng số lượt hỏi đáp đã lưu: {len(turns)}")

    for t in turns:
        turn_id = t.get("turn_id", "")
        query = t.get("query", "")
        summary = t.get("answer_summary") or "Không có tóm tắt"
        created_at = t.get("created_at", "")
        intent = t.get("intent", "kpi_query")

        with st.container(border=True):
            st.markdown(f"**Câu hỏi:** {query}")
            st.markdown(f"**Phản hồi tóm tắt:** {summary}")
            st.caption(f"Mã lượt: `{turn_id}` | Ý định: `{intent}` | Thời gian: `{created_at}`")
