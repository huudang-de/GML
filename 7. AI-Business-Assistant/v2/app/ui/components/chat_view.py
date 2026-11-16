"""Chat View component (Màn 3: Hỏi đáp Nghiệp vụ AI).

Specifications:
- Spec: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 6)
- Figures: st.metric grid + dataframe table
- Trend: displayed DIRECTLY (chart + anomalies, NOT in expander)
- Advice: displayed DIRECTLY (actions + "Tạo hành động" buttons, NOT in expander)
- Pin button: for each kpi_key in kpi_keys ("📌 Ghim {kpi_key}") calls api_client.add_pin
- SQL & Sources: inside st.expander
- Suggested questions loaded once per session via api_client.get_overview
- Consumes pending_query seamlessly on navigation
"""

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
    kpi_keys: list[str] | None = None,
) -> None:
    """Render structured dual output for assistant answers with rich widgets."""
    summary = answer.get("summary", "")
    figures = answer.get("figures") or []
    explanation = answer.get("explanation")
    trend = answer.get("trend")
    advice = answer.get("advice") or []
    sql = answer.get("sql")
    sources = answer.get("sources") or []
    confidence = answer.get("confidence", 0.0)

    effective_kpis = kpi_keys or answer.get("kpi_keys") or []
    # If kpi_keys still empty, check figures
    if not effective_kpis and figures:
        for f in figures:
            if isinstance(f, dict) and f.get("key"):
                effective_kpis.append(f["key"])

    # 1. Summary text
    if summary:
        st.markdown(summary)

    # 2. Figures: st.metric grid + dataframe
    if figures:
        fig_cols = st.columns(min(len(figures), 3))
        for idx, f in enumerate(figures):
            if isinstance(f, dict):
                col = fig_cols[idx % 3]
                val_formatted = f"{_format_figure_value(f.get('value', 0))} {f.get('unit', '')}".strip()
                col.metric(label=f.get("name", "Chỉ số"), value=val_formatted)

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

    # 3. Pin buttons for KPIs
    if effective_kpis:
        p_cols = st.columns(len(effective_kpis))
        for p_idx, k_key in enumerate(effective_kpis):
            with p_cols[p_idx]:
                if st.button(f"📌 Ghim {k_key}", key=f"pin_{request_id}_{k_key}"):
                    try:
                        api_client.add_pin(kpi_key=k_key, profile=profile)
                        st.success(f"Đã ghim `{k_key}` vào Tổng quan!")
                    except Exception as e:
                        st.error(f"Lỗi khi ghim: {e}")

    # 4. Trend (Directly displayed - NOT inside expander)
    if trend and isinstance(trend, dict):
        st.markdown("##### 📈 Phân tích Xu hướng & Bất thường")
        if trend.get("summary_text"):
            st.markdown(trend.get("summary_text"))
        series = trend.get("series") or []
        if series:
            try:
                trend_df = pd.DataFrame(series)
                if "period" in trend_df.columns and "value" in trend_df.columns:
                    trend_df = trend_df.set_index("period")
                    st.line_chart(trend_df["value"])
            except Exception:
                pass
        anomalies = trend.get("anomalies") or []
        for anom in anomalies:
            if isinstance(anom, dict):
                sev = str(anom.get("severity", "")).upper()
                st.warning(f"⚠️ [{anom.get('period')}] Bất thường ({sev}): {anom.get('reason')}")

    # 5. Advice (Directly displayed - NOT inside expander)
    if advice:
        st.markdown("##### 💡 Gợi ý hành động")
        for adv_idx, adv in enumerate(advice):
            if isinstance(adv, dict):
                actions = adv.get("actions") or []
                adv_kpi = adv.get("kpi_key") or (effective_kpis[0] if effective_kpis else None)
                for act_idx, act in enumerate(actions):
                    col_act, col_btn = st.columns([3, 1.2])
                    with col_act:
                        st.markdown(f"- **{act}**")
                    with col_btn:
                        btn_key = f"create_chat_act_{request_id}_{adv_idx}_{act_idx}"
                        if st.button("Tạo hành động", key=btn_key):
                            try:
                                api_client.create_action(
                                    payload={
                                        "source_type": "chat",
                                        "source_ref": str(request_id),
                                        "kpi_key": adv_kpi,
                                        "level": "canh_bao",
                                        "title": act,
                                    },
                                    profile=profile,
                                )
                                st.success("Đã tạo hành động từ cuộc trò chuyện!")
                            except Exception as e:
                                st.error(f"Lỗi tạo hành động: {e}")
                disclaimer = adv.get(
                    "disclaimer",
                    "Gợi ý tham khảo từ quy tắc nghiệp vụ, cần người có thẩm quyền quyết định",
                )
                st.warning(f"⚠️ {disclaimer}")

    # 6. Explanation expander
    if explanation and isinstance(explanation, dict):
        with st.expander("📖 Công thức & Ý nghĩa nghiệp vụ", expanded=False):
            st.markdown(f"**Chỉ số:** {explanation.get('ten', explanation.get('kpi_key', ''))}")
            st.markdown(f"**Công thức:** `{explanation.get('cong_thuc', '')}`")
            if explanation.get("y_nghia"):
                st.markdown(f"**Ý nghĩa:** {explanation.get('y_nghia')}")
            if explanation.get("narrative"):
                st.markdown(f"**Diễn giải:** {explanation.get('narrative')}")

    # 7. SQL query expander
    if sql:
        with st.expander("🔍 Xem truy vấn SQL", expanded=False):
            st.code(sql, language="sql")

    # 8. RAG references expander
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

    # 9. Confidence & Request ID
    conf_pct = f"{confidence * 100:.0f}%" if isinstance(confidence, (int, float)) else "N/A"
    st.caption(f"🎯 Độ tin cậy: {conf_pct} | Request ID: `{request_id}`")

    # 10. Feedback Controls (👍 / 👎)
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
                msg_kpis = msg.get("kpi_keys") or []
                if isinstance(answer, dict):
                    render_assistant_response(
                        answer=answer,
                        request_id=req_id,
                        api_client=api_client,
                        profile=profile,
                        kpi_keys=msg_kpis,
                    )
                else:
                    st.markdown(str(answer))

    # Suggested questions if chat is empty
    if not st.session_state.messages:
        if "suggested_questions" not in st.session_state:
            try:
                ov = api_client.get_overview(profile=profile)
                st.session_state["suggested_questions"] = ov.get("suggested_questions", [])
            except Exception:
                st.session_state["suggested_questions"] = []

        suggested = st.session_state.get("suggested_questions", [])
        if suggested:
            st.markdown("💡 **Câu hỏi gợi ý:**")
            for idx, sq in enumerate(suggested):
                if st.button(f"💬 {sq}", key=f"chat_suggested_{idx}"):
                    st.session_state["pending_query"] = sq
                    st.rerun()

    # Check for incoming pending query (from cross-screen navigation or Quick Ask)
    incoming_query = st.session_state.pop("pending_query", None) or st.session_state.pop("preset_query", None)

    # User chat input
    user_input = st.chat_input("Nhập câu hỏi phân tích kinh doanh (ví dụ: Dư nợ ngắn hạn hiện tại là bao nhiêu?)...")
    active_query = incoming_query or user_input

    if active_query:
        st.session_state.messages.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)

        session_id = st.session_state.get("session_id")
        with st.chat_message("assistant"):
            with st.spinner("Đang truy vấn số liệu và suy luận..."):
                try:
                    resp = api_client.chat(
                        query=active_query,
                        session_id=session_id,
                        data_profile=profile,
                    )
                    answer = resp.get("answer", {})
                    req_id = resp.get("request_id", "req-default")
                    resp_kpis = resp.get("kpi_keys") or []

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "request_id": req_id,
                        "kpi_keys": resp_kpis,
                        "warnings": resp.get("warnings", []),
                    })
                    render_assistant_response(
                        answer=answer,
                        request_id=req_id,
                        api_client=api_client,
                        profile=profile,
                        kpi_keys=resp_kpis,
                    )
                except Exception as e:
                    st.error(f"Lỗi kết nối máy chủ: {e}")
