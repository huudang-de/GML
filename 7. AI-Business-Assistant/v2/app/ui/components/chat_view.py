"""Chat View component providing dual output, figures, SQL, RAG sources, and feedback."""

from typing import Any
import pandas as pd
import streamlit as st

from app.ui.api_client import HttpApiClient


def _format_figure_value(val: Any) -> str:
    """Format numeric values with comma separators."""
    try:
        fval = float(val)
        if fval.is_integer():
            return f"{int(fval):,}"
        return f"{fval:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def render_assistant_response(
    answer: dict[str, Any],
    request_id: str,
    api_client: HttpApiClient,
    profile: str,
) -> None:
    """Render structured dual output for assistant answers."""
    summary = answer.get("summary", "")
    figures = answer.get("figures") or []
    explanation = answer.get("explanation")
    trend = answer.get("trend")
    advice = answer.get("advice") or []
    sql = answer.get("sql")
    sources = answer.get("sources") or []
    confidence = answer.get("confidence", 0.0)

    # 1. Summary text
    if summary:
        st.markdown(summary)

    # 2. Figures dataframe / table
    if figures:
        fig_rows = []
        for f in figures:
            if isinstance(f, dict):
                fig_rows.append({
                    "Chỉ số": f.get("name", "N/A"),
                    "Giá trị": _format_figure_value(f.get("value", 0)),
                    "Đơn vị": f.get("unit", ""),
                    "Ngày chốt": str(f.get("as_of", "")),
                })
        if fig_rows:
            df = pd.DataFrame(fig_rows)
            st.dataframe(df, use_container_width=True)

    # 3. Explanation expander
    if explanation and isinstance(explanation, dict):
        with st.expander("📖 Công thức & Ý nghĩa nghiệp vụ", expanded=False):
            st.markdown(f"**Chỉ số:** {explanation.get('ten', explanation.get('kpi_key', ''))}")
            st.markdown(f"**Công thức:** `{explanation.get('cong_thuc', '')}`")
            if explanation.get("y_nghia"):
                st.markdown(f"**Ý nghĩa:** {explanation.get('y_nghia')}")
            if explanation.get("narrative"):
                st.markdown(f"**Diễn giải:** {explanation.get('narrative')}")

    # 4. Trend expander
    if trend and isinstance(trend, dict):
        with st.expander("📈 Phân tích Xu hướng & Bất thường", expanded=False):
            if trend.get("summary_text"):
                st.markdown(trend.get("summary_text"))
            series = trend.get("series") or []
            if series:
                trend_df = pd.DataFrame(series)
                if "period" in trend_df.columns and "value" in trend_df.columns:
                    trend_df = trend_df.set_index("period")
                    st.line_chart(trend_df["value"])
            anomalies = trend.get("anomalies") or []
            for anom in anomalies:
                if isinstance(anom, dict):
                    sev = str(anom.get("severity", "")).upper()
                    st.warning(f"⚠️ [{anom.get('period')}] Bất thường ({sev}): {anom.get('reason')}")

    # 5. Advice recommendations
    if advice:
        with st.expander("💡 Gợi ý hành động", expanded=False):
            for adv in advice:
                if isinstance(adv, dict):
                    actions = adv.get("actions") or []
                    for act in actions:
                        st.markdown(f"- {act}")
                    disclaimer = adv.get("disclaimer", "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định")
                    st.warning(f"⚠️ {disclaimer}")

    # 6. SQL query expander
    if sql:
        with st.expander("🔍 Xem truy vấn SQL", expanded=False):
            st.code(sql, language="sql")

    # 7. RAG references expander
    if sources:
        with st.expander("📚 Nguồn tài liệu tham khảo", expanded=False):
            for s in sources:
                if isinstance(s, dict):
                    cid = s.get("citation_id", 1)
                    src = s.get("source", "Tài liệu")
                    path = s.get("heading_path", "")
                    snippet = s.get("snippet", "")
                    st.markdown(f"**[{cid}] {src}** — *{path}*")
                    if snippet:
                        st.caption(snippet)

    # 8. Confidence & Request ID
    conf_pct = f"{confidence * 100:.0f}%" if isinstance(confidence, (int, float)) else "N/A"
    st.caption(f"🎯 Độ tin cậy: {conf_pct} | Request ID: `{request_id}`")

    # 9. Feedback Controls (👍 / 👎)
    fb_col1, fb_col2, _ = st.columns([1, 1, 8])
    with fb_col1:
        if st.button("👍", key=f"btn_up_{request_id}"):
            try:
                api_client.submit_feedback(request_id=request_id, rating="up", note="", profile=profile)
                st.session_state[f"fb_done_{request_id}"] = "up"
            except Exception as e:
                st.error(f"Lỗi gửi phản hồi: {e}")

    with fb_col2:
        if st.button("👎", key=f"btn_down_{request_id}"):
            st.session_state[f"show_down_form_{request_id}"] = True

    if st.session_state.get(f"fb_done_{request_id}") == "up":
        st.success("Cảm ơn bạn đã đánh giá hữu ích!")

    if st.session_state.get(f"show_down_form_{request_id}"):
        note = st.text_input("Góp ý chi tiết:", key=f"note_input_{request_id}")
        if st.button("Gửi phản hồi", key=f"submit_down_{request_id}"):
            try:
                api_client.submit_feedback(request_id=request_id, rating="down", note=note, profile=profile)
                st.session_state[f"fb_done_{request_id}"] = "down"
                st.session_state[f"show_down_form_{request_id}"] = False
                st.success("Đã ghi nhận phản hồi! Cảm ơn bạn.")
            except Exception as e:
                st.error(f"Lỗi gửi phản hồi: {e}")


def render_chat_view(api_client: HttpApiClient, profile: str) -> None:
    """Render the primary Chat screen."""
    st.header("💬 Trợ lý Hỏi đáp Nghiệp vụ AI")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat message history
    for msg in st.session_state.messages:
        role = msg.get("role", "assistant")
        with st.chat_message(role):
            if role == "user":
                st.markdown(msg.get("content", ""))
            else:
                answer = msg.get("content", {})
                req_id = msg.get("request_id", "req-unknown")
                if isinstance(answer, dict):
                    render_assistant_response(
                        answer=answer,
                        request_id=req_id,
                        api_client=api_client,
                        profile=profile,
                    )
                else:
                    st.markdown(str(answer))

    # User chat input
    query = st.chat_input("Nhập câu hỏi phân tích kinh doanh (ví dụ: Dư nợ ngắn hạn hiện tại là bao nhiêu?)...")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        session_id = st.session_state.get("session_id")
        with st.chat_message("assistant"):
            with st.spinner("Đang truy vấn số liệu và suy luận..."):
                try:
                    resp = api_client.chat(
                        query=query,
                        session_id=session_id,
                        data_profile=profile,
                    )
                    answer = resp.get("answer", {})
                    req_id = resp.get("request_id", "req-default")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "request_id": req_id,
                        "warnings": resp.get("warnings", []),
                    })
                    render_assistant_response(
                        answer=answer,
                        request_id=req_id,
                        api_client=api_client,
                        profile=profile,
                    )
                except Exception as e:
                    st.error(f"Lỗi kết nối máy chủ: {e}")
