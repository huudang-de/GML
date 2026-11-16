"""Executive Overview screen component (Màn 1: Tổng quan theo vai trò).

Specifications:
- Spec: 2026-11-15-v2-p4r-api-and-ui-revision-plan.md (Task 6)
- Banner: Chào {greeting_title}, hôm nay có {nghiem_trong + canh_bao} cảnh báo và {open_actions} hành động cần xử lý
- Subline: Dữ liệu chốt {as_of_date} · Cảnh báo cập nhật {last_alert_job_at}
- KPI cards 3-column grid: st.metric + mini st.line_chart when series present; st.warning when card error.
- "Phát hiện hôm nay": top_alerts with "Xem chi tiết" buttons -> navigates to Cảnh báo.
- Suggested questions chips: sets pending_query -> navigates to Hỏi đáp AI.
"""

from typing import Any
import pandas as pd
import streamlit as st

from app.ui.api_client import HttpApiClient


def _format_metric_val(val: Any, unit: str | None = None) -> str:
    """Format KPI value with appropriate scales (tỷ, triệu, %, etc.)."""
    if val is None:
        return "N/A"
    try:
        fval = float(val)
        if unit == "%":
            if abs(fval) <= 1.0:
                return f"{fval * 100:.1f}%"
            return f"{fval:.1f}%"
        if abs(fval) >= 1_000_000_000:
            return f"{fval / 1_000_000_000:,.2f} tỷ {unit or ''}".strip()
        if abs(fval) >= 1_000_000:
            return f"{fval / 1_000_000:,.2f} tr {unit or ''}".strip()
        if fval.is_integer():
            return f"{int(fval):,} {unit or ''}".strip()
        return f"{fval:,.2f} {unit or ''}".strip()
    except (ValueError, TypeError):
        return f"{val} {unit or ''}".strip()


def render_overview(api_client: HttpApiClient, profile: str) -> None:
    """Render Executive Overview dashboard."""
    try:
        data = api_client.get_overview(profile=profile)
    except Exception as e:
        st.error(f"Lỗi khi tải tổng quan: {e}")
        return

    greeting_title = data.get("greeting_title", "Quý khách")
    open_alerts = data.get("open_alerts", {})
    nghiem_trong = open_alerts.get("nghiem_trong", 0)
    canh_bao = open_alerts.get("canh_bao", 0)
    total_alerts = nghiem_trong + canh_bao
    open_actions = data.get("open_actions", 0)

    # 1. Executive Banner
    st.markdown(f"## Chào {greeting_title}, hôm nay có {total_alerts} cảnh báo và {open_actions} hành động cần xử lý")

    as_of_date = data.get("as_of_date", "")
    last_alert_job_at = data.get("last_alert_job_at")
    subline_parts = [f"Dữ liệu chốt {as_of_date}"]
    if last_alert_job_at:
        subline_parts.append(f"Cảnh báo cập nhật {last_alert_job_at}")
    st.caption(" · ".join(subline_parts))
    st.divider()

    # 2. KPI Cards (3-column grid)
    kpis = data.get("kpis", [])
    if kpis:
        st.markdown("### 📊 Chỉ số trọng yếu")
        for i in range(0, len(kpis), 3):
            chunk = kpis[i : i + 3]
            cols = st.columns(3)
            for idx, card in enumerate(chunk):
                with cols[idx]:
                    kpi_key = card.get("kpi_key", "")
                    kpi_name = card.get("kpi_name") or kpi_key
                    unit = card.get("unit")
                    val = card.get("value")
                    err = card.get("error")

                    if err:
                        st.warning(f"⚠️ **{kpi_name}**: {err}")
                    else:
                        formatted_val = _format_metric_val(val, unit)
                        delta_pct = card.get("delta_pct")
                        delta_str = f"{delta_pct:+.1%}" if delta_pct is not None else None

                        st.metric(label=kpi_name, value=formatted_val, delta=delta_str)

                        series = card.get("series") or []
                        if series:
                            try:
                                df = pd.DataFrame(series)
                                if "period" in df.columns and "value" in df.columns:
                                    df = df.set_index("period")
                                    st.line_chart(df["value"], height=120)
                            except Exception:
                                pass

                        series_warn = card.get("series_warning")
                        if series_warn:
                            st.caption(f"ℹ️ {series_warn}")

                        if card.get("pinned"):
                            if st.button("📌 Bỏ ghim", key=f"unpin_overview_{kpi_key}"):
                                try:
                                    api_client.remove_pin(kpi_key=kpi_key, profile=profile)
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Lỗi bỏ ghim: {exc}")
        st.divider()

    # 3. Top Alerts (Phát hiện hôm nay)
    top_alerts = data.get("top_alerts", [])
    if top_alerts:
        st.markdown("### 🚨 Phát hiện hôm nay")
        for alert in top_alerts:
            alert_id = alert.get("id")
            rule_id = alert.get("rule_id", f"AL-{alert_id}")
            msg = alert.get("message", "")
            sev = alert.get("severity", "warning")
            sev_icon = "🔴" if str(sev).lower() in ("critical", "nghiem_trong") else "🟡"

            with st.container(border=True):
                c_info, c_btn = st.columns([4, 1])
                with c_info:
                    st.markdown(f"**{sev_icon} [{rule_id}]** {msg}")
                    st.caption(f"Chỉ số: `{alert.get('kpi_key')}` | Giá trị: **{alert.get('value')}**")
                with c_btn:
                    if st.button("Xem chi tiết", key=f"overview_view_alert_{alert_id}"):
                        st.session_state["selected_alert_id"] = alert_id
                        st.session_state["nav_screen"] = "🔔 Cảnh báo"
                        st.rerun()
        st.divider()

    # 4. Suggested Questions Chips
    suggested = data.get("suggested_questions", [])
    if suggested:
        st.markdown("### 💡 Câu hỏi gợi ý cho vai trò của bạn")
        for idx, q in enumerate(suggested):
            if st.button(f"💬 {q}", key=f"overview_q_{idx}"):
                st.session_state["pending_query"] = q
                st.session_state["nav_screen"] = "💬 Hỏi đáp AI"
                st.rerun()
