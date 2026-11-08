"""Alert Center component displaying operational alerts with acknowledgment workflows."""

from typing import Any
import streamlit as st

from app.ui.api_client import HttpApiClient


def render_alert_center(api_client: HttpApiClient, profile: str) -> None:
    """Render the Alert Center view with RBAC-filtered alerts and ack buttons."""
    st.header("🔔 Trung tâm Cảnh báo Nghiệp vụ")

    try:
        alerts: list[dict[str, Any]] = api_client.list_alerts(profile=profile)
    except Exception as e:
        st.error(f"Lỗi khi tải danh sách cảnh báo: {e}")
        return

    if not alerts:
        st.info("Hiện không có cảnh báo nghiệp vụ nào cần xử lý.")
        return

    st.caption(f"Tổng số cảnh báo ghi nhận: {len(alerts)}")

    for alert in alerts:
        alert_id = alert.get("id")
        rule_id = alert.get("rule_id", f"AL-{alert_id}")
        kpi_key = alert.get("kpi_key", "N/A")
        severity = str(alert.get("severity", "warning")).lower()
        message = alert.get("message", "")
        val = alert.get("value") or alert.get("current_value")
        threshold = alert.get("threshold") or alert.get("threshold_value")
        is_ack = bool(alert.get("is_acknowledged", False))
        ack_by = alert.get("acknowledged_by")
        ack_at = alert.get("acknowledged_at")

        sev_badge = "🔴 NGHIÊM TRỌNG" if severity in ("critical", "nghiem_trong") else "🟡 CẢNH BÁO"
        status_badge = "🟢 Đã xác nhận" if is_ack else "⏳ Chưa xác nhận"

        with st.container(border=True):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                st.markdown(f"**[{rule_id}] {message}** ({sev_badge})")
                st.caption(f"Chỉ số: `{kpi_key}` | Giá trị: **{val}** | Ngưỡng quy tắc: **{threshold}** | Trạng thái: **{status_badge}**")
                if is_ack and ack_by:
                    st.caption(f"Đã xác nhận bởi `{ack_by}` vào lúc `{ack_at}`")

            with col_action:
                if not is_ack:
                    if st.button("Đã xem", key=f"ack_{rule_id}_{alert_id}"):
                        try:
                            api_client.ack_alert(alert_id=int(alert_id), profile=profile)
                            st.success(f"Đã xác nhận [{rule_id}]")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi xác nhận: {e}")
                else:
                    st.markdown("✅ *Đã xử lý*")
