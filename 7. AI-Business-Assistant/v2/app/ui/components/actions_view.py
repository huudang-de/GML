"""Operational Actions component (Màn 4: Quản lý Hành động Nghiệp vụ).

Specifications:
- Spec: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 6)
- Filter by status: Tất cả, open, in_progress, done, dismissed
- Action item card: title, KPI, level, assigned_role, due_date, status selectbox
- Status change calls api_client.update_action(action_id, {"status": new_status})
"""

from typing import Any
import streamlit as st

from app.ui.api_client import HttpApiClient, raise_if_unauthorized
from app.ui.theme import ROLE_SHORT_VI, STATUS_LABELS_VI, format_vi_date

STATUS_OPTIONS = ["open", "in_progress", "done", "dismissed"]
FILTER_OPTIONS = ["Tất cả"] + STATUS_OPTIONS


def render_actions_view(api_client: HttpApiClient, profile: str) -> None:
    """Render the operational Action Items screen with status filter and inline updates."""
    st.header("✅ Quản lý Hành động Nghiệp vụ")

    col_flt, _ = st.columns([2, 4])
    with col_flt:
        selected_filter = st.selectbox(
            "Lọc theo trạng thái:",
            FILTER_OPTIONS,
            format_func=lambda s: "Tất cả" if s == "Tất cả" else STATUS_LABELS_VI.get(s, s),
            index=0,
        )

    status_param = None if selected_filter == "Tất cả" else selected_filter

    try:
        actions: list[dict[str, Any]] = api_client.list_actions(profile=profile, status=status_param)
    except Exception as e:
        raise_if_unauthorized(e)
        st.error(f"Lỗi khi tải danh sách hành động: {e}")
        return

    if not actions:
        st.info("Hiện không có hành động nghiệp vụ nào phù hợp.")
        return

    st.caption(f"Tổng số hành động ghi nhận: {len(actions)}")

    for act in actions:
        act_id = act.get("id")
        title = act.get("title", "")
        kpi_key = act.get("kpi_key", "")
        level = act.get("level", "")
        assigned_role = act.get("assigned_role", "")
        assigned_role_vi = ROLE_SHORT_VI.get(assigned_role, assigned_role)
        due_date = format_vi_date(act.get("due_date"))
        cur_status = act.get("status", "open")
        note = act.get("note")

        level_badge = "🔴 Nghiêm trọng" if level in ("critical", "nghiem_trong") else "🟡 Cảnh báo"

        with st.container(border=True):
            col_info, col_ctrl = st.columns([3, 1.2])
            with col_info:
                st.markdown(f"**#{act_id} {title}** ({level_badge})")
                st.caption(
                    f"Chỉ số: `{kpi_key}` | Giao cho: **{assigned_role_vi}** | Hạn xử lý: **{due_date}**"
                )
                if note:
                    st.caption(f"Ghi chú: *{note}*")

            with col_ctrl:
                cur_idx = STATUS_OPTIONS.index(cur_status) if cur_status in STATUS_OPTIONS else 0
                new_status = st.selectbox(
                    "Trạng thái",
                    options=STATUS_OPTIONS,
                    format_func=lambda s: STATUS_LABELS_VI.get(s, s),
                    index=cur_idx,
                    key=f"action_status_{act_id}",
                )
                if new_status != cur_status:
                    try:
                        api_client.update_action(
                            action_id=int(act_id),
                            payload={"status": new_status},
                            profile=profile,
                        )
                        st.success(f"Đã cập nhật trạng thái #{act_id} sang {STATUS_LABELS_VI.get(new_status, new_status)}")
                        st.rerun()
                    except Exception as e:
                        raise_if_unauthorized(e)
                        st.error(f"Lỗi cập nhật: {e}")
