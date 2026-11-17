"""Alert Center component (Màn 2: Trung tâm Cảnh báo Master-Detail).

Specifications:
- Spec: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 6)
- Master-Detail layout: st.columns([1.2, 2])
- Left: filters (domain, severity, status) + list of alert selectable buttons
- Right: 3 st.metric (val, threshold, period), evidence series chart, coverage_warning,
         approved_actions with "Tạo hành động" buttons, "Hỏi tiếp Agent", and "Đã xem" ack button.
"""

import json
from typing import Any
import pandas as pd
import streamlit as st

from app.ui.api_client import HttpApiClient

DOMAIN_OPTIONS = ["Tất cả", "no_vay", "kho", "cong_no", "tien_gui", "dong_tien"]
SEVERITY_OPTIONS = ["Tất cả", "nghiem_trong", "canh_bao"]
STATUS_OPTIONS = ["Tất cả", "open", "acked"]


def _format_metric_val(val: Any) -> str:
    """Format numeric values with thousand commas or percentages."""
    if val is None:
        return "N/A"
    try:
        fval = float(val)
        if abs(fval) <= 1.0 and fval != 0:
            return f"{fval * 100:.1f}%"
        if abs(fval) >= 1_000_000_000:
            return f"{fval / 1_000_000_000:,.2f} tỷ"
        if abs(fval) >= 1_000_000:
            return f"{fval / 1_000_000:,.2f} tr"
        if fval.is_integer():
            return f"{int(fval):,}"
        return f"{fval:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def render_alert_center(api_client: HttpApiClient, profile: str) -> None:
    """Render Master-Detail Alert Center with evidence and action generation."""
    st.header("🔔 Trung tâm Cảnh báo Nghiệp vụ")

    col_master, col_detail = st.columns([1.2, 2])

    # 1. Left Column: Filters & Alert List
    with col_master:
        st.markdown("##### 🔍 Bộ lọc")
        f_dom, f_sev, f_sta = st.columns(3)
        with f_dom:
            sel_dom = st.selectbox("Lĩnh vực", DOMAIN_OPTIONS, index=0)
        with f_sev:
            sel_sev = st.selectbox(
                "Mức độ",
                SEVERITY_OPTIONS,
                format_func=lambda s: "Tất cả" if s == "Tất cả" else ("Nghiêm trọng" if s == "nghiem_trong" else "Cảnh báo"),
                index=0,
            )
        with f_sta:
            sel_sta = st.selectbox(
                "Trạng thái",
                STATUS_OPTIONS,
                format_func=lambda st_val: "Tất cả" if st_val == "Tất cả" else ("Mở" if st_val == "open" else "Đã xem"),
                index=0,
            )

        domain_param = None if sel_dom == "Tất cả" else sel_dom
        sev_param = None if sel_sev == "Tất cả" else sel_sev
        status_param = None if sel_sta == "Tất cả" else sel_sta

        try:
            alerts: list[dict[str, Any]] = api_client.list_alerts(
                profile=profile,
                domain=domain_param,
                severity=sev_param,
                status=status_param,
            )
        except Exception as e:
            st.error(f"Lỗi khi tải danh sách cảnh báo: {e}")
            return

        if not alerts:
            st.info("Hiện không có cảnh báo nào phù hợp.")
            return

        st.caption(f"Tổng số: {len(alerts)} cảnh báo")

        alert_ids = [a.get("id") for a in alerts]
        selected_id = st.session_state.get("selected_alert_id")
        if selected_id not in alert_ids:
            selected_id = alert_ids[0]
            st.session_state["selected_alert_id"] = selected_id

        for alert in alerts:
            aid = alert.get("id")
            rule_id = alert.get("rule_id", f"AL-{aid}")
            msg = alert.get("message", "")
            sev = str(alert.get("severity", "")).lower()
            is_ack = bool(alert.get("is_acknowledged", False))

            sev_icon = "🔴" if sev in ("critical", "nghiem_trong") else "🟡"
            ack_icon = "✅" if is_ack else "⏳"
            msg_snippet = msg[:24] + "..." if len(msg) > 24 else msg

            btn_label = f"{sev_icon} [{rule_id}] {msg_snippet} {ack_icon}"
            is_active = (aid == selected_id)

            if st.button(
                btn_label,
                key=f"sel_alert_{aid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["selected_alert_id"] = aid
                st.rerun()

    # 2. Right Column: Alert Detail View
    with col_detail:
        cur_alert = next((a for a in alerts if a.get("id") == selected_id), alerts[0])
        aid = cur_alert.get("id")
        rule_id = cur_alert.get("rule_id", f"AL-{aid}")
        msg = cur_alert.get("message", "")
        kpi_key = cur_alert.get("kpi_key", "N/A")
        sev = str(cur_alert.get("severity", "canh_bao")).lower()
        val = cur_alert.get("value") if cur_alert.get("value") is not None else cur_alert.get("current_value")
        threshold = cur_alert.get("threshold") if cur_alert.get("threshold") is not None else cur_alert.get("threshold_value")
        period = cur_alert.get("period") or cur_alert.get("created_at")
        is_ack = bool(cur_alert.get("is_acknowledged", False))
        ack_by = cur_alert.get("acknowledged_by")
        ack_at = cur_alert.get("acknowledged_at")

        sev_badge = "🔴 NGHIÊM TRỌNG" if sev in ("critical", "nghiem_trong") else "🟡 CẢNH BÁO"
        status_badge = "🟢 Đã xác nhận" if is_ack else "⏳ Chưa xác nhận"

        st.markdown(f"### [{rule_id}] {msg}")
        sub_info = f"Chỉ số: `{kpi_key}` | Mức độ: **{sev_badge}** | Trạng thái: **{status_badge}**"
        if is_ack and ack_by:
            sub_info += f" (bởi `{ack_by}` vào lúc `{ack_at}`)"
        st.caption(sub_info)
        st.divider()

        # 3 Metrics (Giá trị, Ngưỡng, Kỳ)
        m1, m2, m3 = st.columns(3)
        m1.metric("Giá trị ghi nhận", _format_metric_val(val))
        m2.metric("Ngưỡng quy tắc", _format_metric_val(threshold))
        m3.metric("Kỳ / Thời điểm", str(period)[:10] if period else "N/A")
        st.divider()

        # Evidence
        raw_ev = cur_alert.get("evidence")
        if isinstance(raw_ev, str):
            try:
                evidence = json.loads(raw_ev)
            except Exception:
                evidence = {}
        elif isinstance(raw_ev, dict):
            evidence = raw_ev
        else:
            evidence = {}

        # Evidence Series Line Chart
        series = evidence.get("series") or []
        if series:
            st.markdown("##### 📈 Diễn biến chuỗi thời gian")
            try:
                ev_df = pd.DataFrame(series)
                if "period" in ev_df.columns and "value" in ev_df.columns:
                    ev_df = ev_df.set_index("period")
                    st.line_chart(ev_df["value"])
            except Exception:
                pass

        # Coverage Warning
        coverage_warn = evidence.get("coverage_warning")
        if coverage_warn:
            st.warning(f"⚠️ {coverage_warn}")

        # Approved Actions List
        approved_actions = evidence.get("approved_actions") or []
        if approved_actions:
            st.markdown("##### 📋 Hành động đề xuất đã phê duyệt")
            level_norm = "nghiem_trong" if sev in ("critical", "nghiem_trong") else "canh_bao"
            for idx, action_text in enumerate(approved_actions):
                c_act_text, c_act_btn = st.columns([3, 1.2])
                with c_act_text:
                    st.markdown(f"- **{action_text}**")
                with c_act_btn:
                    btn_key = f"create_action_{aid}_{idx}"
                    if st.button("Tạo hành động", key=btn_key):
                        try:
                            api_client.create_action(
                                payload={
                                    "source_type": "alert",
                                    "source_ref": str(aid),
                                    "kpi_key": kpi_key,
                                    "level": level_norm,
                                    "title": action_text,
                                },
                                profile=profile,
                            )
                            st.success("Đã tạo hành động thành công!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Lỗi tạo hành động: {exc}")

        st.divider()

        # Follow-up & Ack Controls
        c_ask, c_ack = st.columns(2)
        with c_ask:
            if st.button("💬 Hỏi tiếp Agent", key=f"ask_agent_{aid}", use_container_width=True):
                st.session_state["pending_query"] = (
                    f"Phân tích nguyên nhân và hướng xử lý cảnh báo {rule_id}: {msg}"
                )
                st.session_state["nav_screen"] = "💬 Hỏi đáp AI"
                st.rerun()

        with c_ack:
            if not is_ack:
                if st.button("Đã xem", key=f"ack_{rule_id}_{aid}", use_container_width=True):
                    try:
                        api_client.ack_alert(alert_id=int(aid), profile=profile)
                        st.success(f"Đã xác nhận [{rule_id}]")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Lỗi xác nhận: {exc}")
            else:
                st.markdown("✅ *Đã xác nhận*")
