"""Executive Overview screen component (Màn 1: Tổng quan theo mẫu Power BI Simplifica).

Pure UI presentation module: MUST NOT import app.services, app.agents, app.knowledge, or db.

Design structure (Gỗ Minh Long PG.pbix 5-Chapter Story):
1. Top Executive Masthead Card: Greeting + Vietnamese date/update subline + semantic alert/action pills.
2. Power BI Chapter Navigator (pageNavigator): "📊 Tổng hợp điều hành" + active 5-chapter domains.
3. Row 1 — Hero cardVisual Grid (3 columns/row): domain badge, st.metric, previous value, Plotly sparkline, unpin.
4. Row 2 — Asymmetric Visual Row ([1.6, 1]): Combo Bar + Moving Trend Plotly chart + Period comparison table.
5. Row 3 — "🚨 Phát hiện hôm nay" (deduplicated ×N badges + Vietnamese formatting) & 2-col Suggested Questions.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.ui.api_client import HttpApiClient
from app.ui.theme import (
    DOMAIN_LABELS_VI,
    ML_AMBER,
    ML_CARD_BORDER,
    ML_CRIMSON,
    ML_NAVY,
    ML_SLATE,
    ML_TEXT,
    build_trend_plotly,
    format_vi_date,
    format_vi_datetime,
    format_vi_delta,
    format_vi_number,
    format_vi_period,
)

ALL_CHAPTER_LABEL = "📊 Tổng hợp điều hành"

CHAPTER_ORDER: list[tuple[str, str]] = [
    ("no_vay", "🏦 Hoạt động Tài chính"),
    ("kho", "📦 Hàng tồn kho"),
    ("cong_no", "📄 Phải thu – Phải trả"),
    ("tien_gui", "💰 Tiền gửi & Thanh khoản"),
    ("dong_tien", "💸 Dòng tiền"),
]


def _extract_series_points(series: list[dict[str, Any]]) -> tuple[list[str], list[float]]:
    """Extract Vietnamese period labels and numeric values from a KPI series list."""
    periods_vi: list[str] = []
    values: list[float] = []
    for item in series:
        if not isinstance(item, dict):
            continue
        p_raw = item.get("period")
        v_raw = item.get("value")
        if p_raw is None or v_raw is None:
            continue
        try:
            fval = float(v_raw)
        except (ValueError, TypeError):
            continue
        periods_vi.append(format_vi_period(str(p_raw)))
        values.append(fval)
    return periods_vi, values


def _infer_alert_unit(
    kpi_key: Any,
    val: Any,
    unit_by_kpi: dict[str, str],
) -> str | None:
    """Resolve unit from KPI catalog card metadata or ratio heuristic."""
    key_str = str(kpi_key or "")
    if key_str in unit_by_kpi:
        return unit_by_kpi[key_str]
    lower_key = key_str.lower()
    if any(tok in lower_key for tok in ("ty_le", "phan_tram", "rate", "ratio")):
        return "%"
    if val is not None:
        try:
            fval = float(val)
            if 0 < abs(fval) <= 1.0 and not any(tok in lower_key for tok in ("vong", "ngay", "so_", "he_so")):
                return "%"
        except (ValueError, TypeError):
            pass
    return None


def _build_combo_bar_trend_plotly(card: dict[str, Any]) -> go.Figure:
    """Build Power BI Simplifica Combo Bar + Moving Trend Plotly chart for a KPI card."""
    unit = card.get("unit")
    kpi_name = card.get("kpi_name") or card.get("kpi_key") or "Chỉ số"
    periods_vi, values = _extract_series_points(card.get("series") or [])

    fig = go.Figure()
    if not periods_vi:
        return fig

    bar_colors = [ML_NAVY] * max(0, len(values) - 1) + [ML_CRIMSON]
    bar_hover = [
        f"Kỳ: {p}<br>Giá trị: <b>{format_vi_number(v, unit)}</b>"
        for p, v in zip(periods_vi, values)
    ]

    fig.add_trace(
        go.Bar(
            x=periods_vi,
            y=values,
            name="Giá trị kỳ",
            marker=dict(color=bar_colors, opacity=0.88),
            text=bar_hover,
            hovertemplate="%{text}<extra></extra>",
        )
    )

    # 3-period trailing moving trend overlay
    trend_values = [
        sum(values[max(0, idx - 2) : idx + 1]) / (idx - max(0, idx - 2) + 1)
        for idx in range(len(values))
    ]
    trend_hover = [
        f"Kỳ: {p}<br>Xu hướng trượt: <b>{format_vi_number(tv, unit)}</b>"
        for p, tv in zip(periods_vi, trend_values)
    ]
    marker_colors = [ML_AMBER] * max(0, len(values) - 1) + [ML_CRIMSON]
    marker_sizes = [6] * max(0, len(values) - 1) + [10]

    fig.add_trace(
        go.Scatter(
            x=periods_vi,
            y=trend_values,
            mode="lines+markers",
            name="Xu hướng trượt",
            line=dict(color=ML_CRIMSON, width=2.4, dash="dot", shape="spline"),
            marker=dict(
                color=marker_colors,
                size=marker_sizes,
                line=dict(color="#FFFFFF", width=1.5),
            ),
            text=trend_hover,
            hovertemplate="%{text}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text=str(kpi_name), font=dict(size=13, color=ML_NAVY)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Be Vietnam Pro, Segoe UI, sans-serif", color=ML_TEXT, size=12),
        height=310,
        margin=dict(l=12, r=12, t=38, b=16),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=ML_CARD_BORDER, font=dict(color=ML_TEXT, size=12)),
        xaxis=dict(showgrid=False, title=None, type="category", tickfont=dict(size=11, color=ML_SLATE)),
        yaxis=dict(showgrid=True, gridcolor="#EAEEF3", zeroline=False, title=None, tickfont=dict(size=11, color=ML_SLATE)),
    )
    return fig


def _render_masthead(data: dict[str, Any]) -> None:
    """Render Top Executive Masthead Card (PBIX Vùng 1)."""
    greeting_title = data.get("greeting_title", "Quý khách")
    open_alerts = data.get("open_alerts") or {}
    nghiem_trong = int(open_alerts.get("nghiem_trong", 0) or 0)
    canh_bao = int(open_alerts.get("canh_bao", 0) or 0)
    total_alerts = nghiem_trong + canh_bao
    open_actions = int(data.get("open_actions", 0) or 0)

    as_of_date = format_vi_date(data.get("as_of_date", ""))
    last_alert_job_at = data.get("last_alert_job_at")
    subline_parts = [f"Dữ liệu chốt {as_of_date}"]
    if last_alert_job_at:
        subline_parts.append(f"Cảnh báo cập nhật {format_vi_datetime(last_alert_job_at)}")

    with st.container(border=True):
        st.markdown(
            f"## Chào {greeting_title}, hôm nay có {total_alerts} cảnh báo và {open_actions} hành động cần xử lý"
        )
        st.caption(" · ".join(subline_parts))
        st.markdown(
            f"""
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;">
                <span class="gml-badge gml-badge-critical">🔴 {nghiem_trong} Nghiêm trọng</span>
                <span class="gml-badge gml-badge-warning">🟡 {canh_bao} Cảnh báo</span>
                <span class="gml-badge gml-badge-success">✅ {open_actions} Hành động đang mở</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_chapter_navigator(kpis: list[dict[str, Any]], role: str = "ceo") -> list[dict[str, Any]]:
    """Render Power BI pageNavigator radio strip and return KPIs in active chapter.

    Only ``ceo`` gets the cross-domain "📊 Tổng hợp điều hành" tab; department roles
    (``ke_toan_truong``, ``quan_ly_kho``) start directly in their domain chapters.
    """
    present_domains = {str(c.get("domain")) for c in kpis if c.get("domain")}
    chapter_options: list[str] = [ALL_CHAPTER_LABEL] if role == "ceo" else []
    label_to_domain: dict[str, str] = {}

    for dom_code, dom_label in CHAPTER_ORDER:
        if dom_code in present_domains:
            chapter_options.append(dom_label)
            label_to_domain[dom_label] = dom_code

    known_domains = {d for d, _ in CHAPTER_ORDER}
    for extra_dom in sorted(present_domains - known_domains):
        extra_label = DOMAIN_LABELS_VI.get(extra_dom, extra_dom)
        chapter_options.append(extra_label)
        label_to_domain[extra_label] = extra_dom

    if not chapter_options:
        return kpis

    if len(chapter_options) > 1:
        if (
            "overview_chapter_selector" in st.session_state
            and st.session_state["overview_chapter_selector"] not in chapter_options
        ):
            st.session_state["overview_chapter_selector"] = chapter_options[0]

        selected_chapter = st.radio(
            "Chương báo cáo",
            options=chapter_options,
            horizontal=True,
            label_visibility="collapsed",
            key="overview_chapter_selector",
        )
    else:
        selected_chapter = chapter_options[0]

    selected_domain = label_to_domain.get(selected_chapter)
    if selected_domain is None:
        return kpis
    return [c for c in kpis if c.get("domain") == selected_domain]


def _render_kpi_card(
    card: dict[str, Any],
    card_idx: int,
    api_client: HttpApiClient,
    profile: str,
) -> None:
    """Render a single Power BI Hero cardVisual inside a Fluent 2 bordered container."""
    kpi_key = str(card.get("kpi_key", ""))
    kpi_name = card.get("kpi_name") or kpi_key
    domain = str(card.get("domain") or "")
    domain_label = DOMAIN_LABELS_VI.get(domain, domain or "Chỉ số")
    unit = card.get("unit")
    val = card.get("value")
    err = card.get("error")
    is_pinned = bool(card.get("pinned"))

    with st.container(border=True):
        pin_html = '<span class="gml-badge gml-badge-warning">📌 Đã ghim</span>' if is_pinned else ""
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:4px;">
                <span class="gml-badge gml-badge-navy">{domain_label}</span>
                {pin_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if err:
            st.warning(f"⚠️ **{kpi_name}**: {err}")
            return

        st.metric(
            label=str(kpi_name),
            value=format_vi_number(val, unit),
            delta=format_vi_delta(card.get("delta_pct")),
        )

        previous_value = card.get("previous_value")
        if previous_value is not None:
            st.caption(f"Kỳ trước: {format_vi_number(previous_value, unit)}")

        series = card.get("series") or []
        if series:
            try:
                is_debt_domain = domain == "no_vay"
                spark_color = ML_CRIMSON if is_debt_domain else ML_NAVY
                fill_rgba = "rgba(184, 38, 1, 0.08)" if is_debt_domain else "rgba(6, 47, 79, 0.08)"
                fig = build_trend_plotly(
                    series=series,
                    unit=unit,
                    line_color=spark_color,
                    height=145,
                )
                if fig.data:
                    fig.update_traces(
                        selector=dict(type="scatter"),
                        fill="tozeroy",
                        fillcolor=fill_rgba,
                        marker=dict(size=4),
                    )
                    fig.update_layout(margin=dict(l=6, r=6, t=8, b=8))
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"ov_spark_{kpi_key}_{card_idx}",
                    )
            except Exception:
                pass

        series_warn = card.get("series_warning")
        if series_warn:
            st.caption(f"ℹ️ {series_warn}")

        if is_pinned:
            if st.button("📌 Bỏ ghim", key=f"unpin_overview_{kpi_key}"):
                try:
                    api_client.remove_pin(kpi_key=kpi_key, profile=profile)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Lỗi bỏ ghim: {exc}")


def _render_asymmetric_visual_row(visible_kpis: list[dict[str, Any]]) -> None:
    """Render Power BI Asymmetric Visual Row ([1.6, 1]): Combo chart + Comparison table."""
    series_cards = [
        c for c in visible_kpis
        if not c.get("error") and _extract_series_points(c.get("series") or [])[0]
    ]
    if not series_cards:
        return

    col_chart, col_table = st.columns([1.6, 1])

    with col_chart:
        with st.container(border=True):
            st.markdown("##### 📈 Xu hướng & Biến động theo kỳ (Mẫu Power BI Simplifica)")
            if len(series_cards) > 1:
                focus_keys = [str(c.get("kpi_key", "")) for c in series_cards]
                name_by_key = {
                    str(c.get("kpi_key", "")): str(c.get("kpi_name") or c.get("kpi_key", ""))
                    for c in series_cards
                }
                if (
                    "overview_focus_kpi" in st.session_state
                    and st.session_state["overview_focus_kpi"] not in focus_keys
                ):
                    st.session_state["overview_focus_kpi"] = focus_keys[0]

                selected_focus_key = st.selectbox(
                    "Chọn chỉ số phân tích chi tiết:",
                    options=focus_keys,
                    format_func=lambda k: name_by_key.get(k, k),
                    key="overview_focus_kpi",
                )
                focus_card = next(
                    (c for c in series_cards if str(c.get("kpi_key", "")) == selected_focus_key),
                    series_cards[0],
                )
            else:
                focus_card = series_cards[0]

            combo_fig = _build_combo_bar_trend_plotly(focus_card)
            if combo_fig.data:
                st.plotly_chart(
                    combo_fig,
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="overview_combo_chart",
                )

    with col_table:
        with st.container(border=True):
            st.markdown("##### 📋 Bảng đối chiếu Kỳ hiện tại & Kỳ trước")
            compare_rows: list[dict[str, str]] = []
            for card in visible_kpis:
                unit = card.get("unit")
                name = str(card.get("kpi_name") or card.get("kpi_key") or "")
                if card.get("error"):
                    compare_rows.append(
                        {
                            "Chỉ số": name,
                            "Kỳ này": "Lỗi dữ liệu",
                            "Kỳ trước": "—",
                            "Biến động": "—",
                        }
                    )
                    continue
                prev_val = card.get("previous_value")
                delta_str = format_vi_delta(card.get("delta_pct"))
                compare_rows.append(
                    {
                        "Chỉ số": name,
                        "Kỳ này": format_vi_number(card.get("value"), unit),
                        "Kỳ trước": format_vi_number(prev_val, unit) if prev_val is not None else "—",
                        "Biến động": delta_str if delta_str is not None else "—",
                    }
                )
            st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)


def _render_top_alerts(
    top_alerts: list[dict[str, Any]],
    unit_by_kpi: dict[str, str],
) -> None:
    """Render '🚨 Phát hiện hôm nay' bordered alert cards."""
    if not top_alerts:
        return

    st.markdown("### 🚨 Phát hiện hôm nay")
    for alert in top_alerts:
        alert_id = alert.get("id")
        rule_id = alert.get("rule_id") or f"AL-{alert_id}"
        msg = alert.get("message", "")
        sev = str(alert.get("severity", "warning")).lower()
        is_critical = sev in ("critical", "nghiem_trong")
        sev_icon = "🔴" if is_critical else "🟡"
        sev_badge = (
            '<span class="gml-badge gml-badge-critical">Nghiêm trọng</span>'
            if is_critical
            else '<span class="gml-badge gml-badge-warning">Cảnh báo</span>'
        )
        occ_count = int(alert.get("occurrence_count", 1) or 1)
        occ_badge = (
            f' <span class="gml-badge gml-badge-count">×{occ_count} lần</span>'
            if occ_count > 1
            else ""
        )

        kpi_key = alert.get("kpi_key")
        val = alert.get("value")
        alert_unit = _infer_alert_unit(kpi_key, val, unit_by_kpi)
        val_str = format_vi_number(val, alert_unit)
        period_str = format_vi_period(alert.get("period"))

        with st.container(border=True):
            c_info, c_btn = st.columns([4, 1])
            with c_info:
                st.markdown(
                    f"**{sev_icon} [{rule_id}]** {sev_badge}{occ_badge} &nbsp; {msg}",
                    unsafe_allow_html=True,
                )
                cap_parts = [f"Chỉ số: `{kpi_key}`", f"Giá trị: **{val_str}**"]
                if period_str != "—":
                    cap_parts.append(f"Kỳ: {period_str}")
                st.caption(" · ".join(cap_parts))
            with c_btn:
                if st.button("Xem chi tiết", key=f"overview_view_alert_{alert_id}", use_container_width=True):
                    st.session_state["selected_alert_id"] = alert_id
                    st.session_state["nav_screen"] = "🔔 Cảnh báo"
                    st.rerun()


def _render_suggested_questions(suggested: list[str]) -> None:
    """Render 2-column suggested question chip buttons."""
    if not suggested:
        return

    st.markdown("### 💡 Câu hỏi gợi ý cho vai trò của bạn")
    for row_start in range(0, len(suggested), 2):
        cols = st.columns(2)
        for col_offset in range(2):
            idx = row_start + col_offset
            if idx < len(suggested):
                q = suggested[idx]
                with cols[col_offset]:
                    if st.button(f"💬 {q}", key=f"overview_q_{idx}", use_container_width=True):
                        st.session_state["pending_query"] = q
                        st.session_state["nav_screen"] = "💬 Hỏi đáp AI"
                        st.rerun()


def render_overview(api_client: HttpApiClient, profile: str, role: str = "ceo") -> None:
    """Render Executive Overview dashboard modeled on Power BI Simplifica 5-Chapter template."""
    try:
        data = api_client.get_overview(profile=profile)
    except Exception as e:
        st.error(f"Lỗi khi tải tổng quan: {e}")
        return

    # 1. Top Executive Masthead Card (PBIX Vùng 1)
    _render_masthead(data)

    kpis = data.get("kpis") or []
    unit_by_kpi = {
        str(c.get("kpi_key")): str(c.get("unit"))
        for c in kpis
        if c.get("kpi_key") and c.get("unit")
    }

    # 2. Power BI Chapter Navigator + Row 1 Hero Cards + Row 2 Asymmetric Visual Row
    if not kpis:
        st.info("Tài khoản Quản trị hệ thống không có KPI tài chính/vận hành được gán.")
    else:
        visible_kpis = _render_chapter_navigator(kpis, role=role)
        st.markdown("### 📊 Chỉ số trọng yếu")
        for i in range(0, len(visible_kpis), 3):
            chunk = visible_kpis[i : i + 3]
            cols = st.columns(3)
            for col_idx, card in enumerate(chunk):
                with cols[col_idx]:
                    _render_kpi_card(
                        card=card,
                        card_idx=i + col_idx,
                        api_client=api_client,
                        profile=profile,
                    )

        _render_asymmetric_visual_row(visible_kpis)

    st.divider()

    # 3. Row 3: Top Alerts & Suggested Questions
    _render_top_alerts(data.get("top_alerts") or [], unit_by_kpi=unit_by_kpi)
    _render_suggested_questions(data.get("suggested_questions") or [])
