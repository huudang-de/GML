"""Gỗ Minh Long UI Theme, Vietnamese Formatters, and Plotly Simplifica Helpers.

Pure presentation module: MUST NOT import app.services, app.agents, app.knowledge, or db.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
import math
from pathlib import Path
import re
from typing import Any

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Brand Palette (Logo GML + Power BI Simplifica + Fluent 2)
# ---------------------------------------------------------------------------
ML_CRIMSON = "#B82601"
ML_RED = "#E11D24"
ML_NAVY = "#062F4F"
ML_BLUE = "#0375B4"
ML_GREEN = "#7CBB00"
ML_AMBER = "#FFBB00"
ML_TEAL = "#008F95"
ML_SLATE = "#506B85"
ML_BG = "#F6F7F9"
ML_SIDEBAR_BG = "#EDF0F4"
ML_CARD_BORDER = "#E6E6E6"
ML_TEXT = "#1E242B"

SIMPLIFICA_PALETTE = [
    "#062F4F",
    "#B82601",
    "#0375B4",
    "#7CBB00",
    "#FFBB00",
    "#008F95",
    "#945D60",
]

# ---------------------------------------------------------------------------
# Vietnamese Domain / Status / Role Dictionaries
# ---------------------------------------------------------------------------
DOMAIN_LABELS_VI: dict[str, str] = {
    "no_vay": "Hoạt động Tài chính",
    "kho": "Hàng tồn kho",
    "cong_no": "Công nợ AR/AP",
    "tien_gui": "Tiền gửi & Thanh khoản",
    "dong_tien": "Dòng tiền",
}

STATUS_LABELS_VI: dict[str, str] = {
    "open": "Chờ xử lý",
    "in_progress": "Đang xử lý",
    "done": "Hoàn thành",
    "dismissed": "Bỏ qua",
}

ROLE_SHORT_VI: dict[str, str] = {
    "ceo": "Tổng Giám đốc",
    "ke_toan_truong": "Kế toán trưởng",
    "quan_ly_kho": "Quản lý kho",
    "quan_tri_he_thong": "Quản trị hệ thống",
}

_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")
_ISO_DATE_PREFIX_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


# ---------------------------------------------------------------------------
# Logo & Theme Injection
# ---------------------------------------------------------------------------
def get_logo_base64() -> str | None:
    """Read v2/app/ui/assets/logo_gml.jpg and return base64 string, or None if missing."""
    logo_path = Path(__file__).resolve().parent / "assets" / "logo_gml.jpg"
    if not logo_path.is_file():
        return None
    try:
        return base64.b64encode(logo_path.read_bytes()).decode("ascii")
    except OSError:
        return None


def inject_minh_long_theme() -> None:
    """Inject Be Vietnam Pro font, Minh Long Crimson/Simplifica tokens, and Fluent 2 card styling."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');

        html, body, .stApp, .stMarkdown, p, li, label, h1, h2, h3, h4, h5, h6,
        button, input, select, textarea,
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricDelta"],
        [data-testid="stCaptionContainer"], [data-testid="stDataFrame"] {{
            font-family: 'Be Vietnam Pro', 'Segoe UI', system-ui, -apple-system, sans-serif;
            color: {ML_TEXT};
        }}

        [data-testid="stIconMaterial"], .material-icons, .material-symbols-rounded, span[translate="no"] {{
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        }}

        [data-testid="stMetricValue"], [data-testid="stMetricDelta"], .gml-num {{
            font-variant-numeric: tabular-nums;
        }}

        .stApp {{
            background-color: {ML_BG};
        }}

        /* Top Crimson Accent Strip */
        header[data-testid="stHeader"] {{
            border-top: 3px solid {ML_CRIMSON};
            background: rgba(246, 247, 249, 0.92);
            backdrop-filter: blur(8px);
        }}

        /* Cool Slate Sidebar + Rounded Nav Pills */
        [data-testid="stSidebar"] {{
            background-color: {ML_SIDEBAR_BG};
            border-right: 1px solid {ML_CARD_BORDER};
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label {{
            border-radius: 8px;
            padding: 6px 10px;
            margin-bottom: 2px;
            transition: background-color 0.15s ease;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
            background-color: rgba(6, 47, 79, 0.06);
        }}

        /* Fluent 2 Card Containers */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: #FFFFFF;
            border: 1px solid {ML_CARD_BORDER} !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 3px rgba(6, 47, 79, 0.05);
        }}

        /* Minh Long Primary Buttons */
        button[kind="primary"], [data-testid="baseButton-primary"], [data-testid="stBaseButton-primary"] {{
            background-color: {ML_CRIMSON} !important;
            border-color: {ML_CRIMSON} !important;
            color: #FFFFFF !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
        }}
        button[kind="primary"] *, [data-testid="baseButton-primary"] *, [data-testid="stBaseButton-primary"] * {{
            color: #FFFFFF !important;
        }}
        button[kind="primary"]:hover, [data-testid="baseButton-primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
            background-color: #961F01 !important;
            border-color: #961F01 !important;
        }}
        button[kind="secondary"], [data-testid="baseButton-secondary"] {{
            border-radius: 6px !important;
            border-color: #D5DCE4 !important;
        }}

        /* Sidebar Brand Card & Top Masthead */
        .gml-sidebar-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: #FFFFFF;
            border: 1px solid {ML_CARD_BORDER};
            border-left: 4px solid {ML_CRIMSON};
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 10px;
            box-shadow: 0 1px 2px rgba(6, 47, 79, 0.04);
        }}
        .gml-sidebar-brand img {{
            width: 38px;
            height: 38px;
            object-fit: contain;
            border-radius: 4px;
        }}
        .gml-sidebar-brand-title {{
            font-size: 13px;
            font-weight: 700;
            color: {ML_NAVY};
            letter-spacing: 0.02em;
            line-height: 1.25;
        }}
        .gml-sidebar-brand-sub {{
            font-size: 11px;
            color: {ML_SLATE};
            line-height: 1.25;
        }}

        .gml-masthead {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            background: #FFFFFF;
            border: 1px solid {ML_CARD_BORDER};
            border-top: 3px solid {ML_CRIMSON};
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 14px;
            box-shadow: 0 1px 3px rgba(6, 47, 79, 0.05);
        }}
        .gml-masthead-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .gml-masthead-left img {{
            height: 34px;
            width: auto;
            object-fit: contain;
            border-radius: 4px;
        }}
        .gml-masthead-title {{
            font-size: 15px;
            font-weight: 700;
            color: {ML_NAVY};
            letter-spacing: 0.01em;
        }}
        .gml-masthead-sub {{
            font-size: 12px;
            color: {ML_SLATE};
        }}
        .gml-masthead-pills {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        /* Semantic Pills */
        .gml-badge {{
            display: inline-block;
            padding: 2px 9px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            line-height: 1.5;
            white-space: nowrap;
        }}
        .gml-badge-critical {{
            background-color: #FEECEB;
            color: {ML_CRIMSON};
            border: 1px solid #F9C6C2;
        }}
        .gml-badge-warning {{
            background-color: #FFF6E0;
            color: #996600;
            border: 1px solid #FDE3A7;
        }}
        .gml-badge-navy {{
            background-color: #EAF0F6;
            color: {ML_NAVY};
            border: 1px solid #CBD8E6;
        }}
        .gml-badge-count {{
            background-color: #F1F3F5;
            color: #374151;
            border: 1px solid #DCE0E5;
            font-variant-numeric: tabular-nums;
        }}
        .gml-badge-success {{
            background-color: #EEF7DF;
            color: #4E7A00;
            border: 1px solid #CEE6A4;
        }}

        /* Dataframe styling */
        [data-testid="stDataFrame"] {{
            border: 1px solid {ML_CARD_BORDER};
            border-radius: 8px;
            overflow: hidden;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Pure Python Vietnamese Locale Formatters
# ---------------------------------------------------------------------------
def _swap_en_to_vi_separators(en_formatted: str) -> str:
    """Convert English US '1,234.56' string into Vietnamese '1.234,56'."""
    return en_formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _fmt_vi_decimal(num: float, decimals: int = 2) -> str:
    """Format a float with '.' thousand grouping and ',' decimal separator.

    Whole numbers omit trailing decimal zeros (e.g. 26824 -> '26.824').
    """
    if math.isnan(num) or math.isinf(num):
        return "Chưa có dữ liệu"
    sign = "-" if num < 0 else ""
    abs_val = abs(float(num))
    if decimals <= 0 or abs_val.is_integer():
        int_part = f"{int(round(abs_val)):,}".replace(",", ".")
        return f"{sign}{int_part}" if int_part != "0" else "0"
    formatted = _swap_en_to_vi_separators(f"{abs_val:,.{decimals}f}")
    return f"{sign}{formatted}"


def format_vi_number(val: Any, unit: str | None = None) -> str:
    """Format numeric value into Vietnamese locale ('236,07 tỷ VNĐ', '88,5%', '26.824')."""
    if val is None:
        return "Chưa có dữ liệu"
    if isinstance(val, bool):
        return str(val)
    try:
        fval = float(val)
    except (ValueError, TypeError):
        return str(val)

    if math.isnan(fval) or math.isinf(fval):
        return "Chưa có dữ liệu"

    clean_unit = (unit or "").strip()

    if clean_unit == "%":
        pct = fval * 100.0 if abs(fval) <= 1.0 else fval
        sign = "-" if pct < 0 else ""
        pct_str = _swap_en_to_vi_separators(f"{abs(pct):,.1f}")
        return f"{sign}{pct_str}%"

    unit_lower = clean_unit.lower()
    if abs(fval) >= 1_000_000_000:
        scaled = fval / 1_000_000_000.0
        num_str = _fmt_vi_decimal(scaled, decimals=2)
        if unit_lower.startswith("tỷ"):
            suffix = clean_unit
        elif clean_unit:
            suffix = f"tỷ {clean_unit}"
        else:
            suffix = "tỷ"
        return f"{num_str} {suffix}".strip()

    if abs(fval) >= 1_000_000:
        scaled = fval / 1_000_000.0
        num_str = _fmt_vi_decimal(scaled, decimals=2)
        if unit_lower.startswith(("tr", "triệu")):
            suffix = clean_unit
        elif clean_unit:
            suffix = f"tr {clean_unit}"
        else:
            suffix = "tr"
        return f"{num_str} {suffix}".strip()

    num_str = _fmt_vi_decimal(fval, decimals=2)
    return f"{num_str} {clean_unit}".strip()


def format_vi_delta(delta_pct: float | None) -> str | None:
    """Format ratio delta into Vietnamese percentage string ('+5,2%', '-16,8%') for st.metric."""
    if delta_pct is None:
        return None
    try:
        fval = float(delta_pct)
    except (ValueError, TypeError):
        return None
    if math.isnan(fval) or math.isinf(fval):
        return None
    pct = fval * 100.0
    if pct > 0:
        prefix = "+"
    elif pct < 0:
        prefix = "-"
    else:
        prefix = ""
    return f"{prefix}{_swap_en_to_vi_separators(f'{abs(pct):,.1f}')}%"


def format_vi_date(val: Any) -> str:
    """Format ISO date or date object into 'DD/MM/YYYY' (or 'TMM/YYYY' for YYYY-MM)."""
    if val is None or val == "":
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%d/%m/%Y")
    if isinstance(val, date):
        return val.strftime("%d/%m/%Y")

    s = str(val).strip()
    if not s:
        return "—"

    m_date = _ISO_DATE_PREFIX_RE.match(s)
    if m_date:
        year, month, day = m_date.groups()
        return f"{day}/{month}/{year}"

    m_period = _PERIOD_RE.match(s)
    if m_period:
        year, month = m_period.groups()
        return f"T{month}/{year}"

    return s


def format_vi_datetime(val: Any) -> str:
    """Format ISO timestamp into 'HH:MM · DD/MM/YYYY'."""
    if val is None or val == "":
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%H:%M · %d/%m/%Y")
    if isinstance(val, date):
        return val.strftime("%d/%m/%Y")

    s = str(val).strip()
    if not s:
        return "—"

    if _PERIOD_RE.match(s):
        return format_vi_period(s)

    if len(s) == 10 and _ISO_DATE_PREFIX_RE.match(s):
        return format_vi_date(s)

    try:
        normalized = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%H:%M · %d/%m/%Y")
    except ValueError:
        return format_vi_date(s)


def format_vi_period(val: Any) -> str:
    """Format period string 'YYYY-MM' into 'T07/2026' (or 'DD/MM/YYYY' if full date)."""
    if val is None or val == "":
        return "—"
    if isinstance(val, (datetime, date)):
        return f"T{val.month:02d}/{val.year}"

    s = str(val).strip()
    if not s:
        return "—"

    m_period = _PERIOD_RE.match(s)
    if m_period:
        year, month = m_period.groups()
        return f"T{month}/{year}"

    m_date = _ISO_DATE_PREFIX_RE.match(s)
    if m_date:
        year, month, day = m_date.groups()
        return f"{day}/{month}/{year}"

    return s


# ---------------------------------------------------------------------------
# Plotly Simplifica Chart Helpers
# ---------------------------------------------------------------------------
def build_trend_plotly(
    series: list[dict[str, Any]],
    title: str | None = None,
    unit: str | None = None,
    line_color: str = ML_NAVY,
    threshold: float | None = None,
    anomalies: list[dict[str, Any]] | None = None,
    height: int = 280,
    show_bars: bool = False,
) -> go.Figure:
    """Build a transparent Fluent 2 / Power BI Simplifica Plotly line/combo chart."""
    periods_raw: list[str] = []
    periods_vi: list[str] = []
    values: list[float] = []
    hover_texts: list[str] = []

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
        p_str = str(p_raw)
        p_vi = format_vi_period(p_str)
        periods_raw.append(p_str)
        periods_vi.append(p_vi)
        values.append(fval)
        hover_texts.append(f"Kỳ: {p_vi}<br>Giá trị: <b>{format_vi_number(fval, unit)}</b>")

    fig = go.Figure()

    if show_bars and periods_vi:
        fig.add_trace(
            go.Bar(
                x=periods_vi,
                y=values,
                name="Giá trị kỳ",
                marker_color="rgba(3, 117, 180, 0.22)",
                hoverinfo="skip",
            )
        )

    if periods_vi:
        fig.add_trace(
            go.Scatter(
                x=periods_vi,
                y=values,
                mode="lines+markers",
                name="Giá trị",
                line=dict(color=line_color, width=2.5),
                marker=dict(color=line_color, size=6),
                text=hover_texts,
                hovertemplate="%{text}<extra></extra>",
            )
        )

    if anomalies and periods_raw:
        period_val_map = dict(zip(periods_raw, values))
        anom_x: list[str] = []
        anom_y: list[float] = []
        anom_hover: list[str] = []
        for anom in anomalies:
            if not isinstance(anom, dict):
                continue
            ap = str(anom.get("period", ""))
            if ap in period_val_map:
                ap_vi = format_vi_period(ap)
                aval = period_val_map[ap]
                reason = anom.get("reason") or "Điểm bất thường"
                anom_x.append(ap_vi)
                anom_y.append(aval)
                anom_hover.append(
                    f"Kỳ: {ap_vi}<br>Giá trị: <b>{format_vi_number(aval, unit)}</b><br>Bất thường: {reason}"
                )
        if anom_x:
            fig.add_trace(
                go.Scatter(
                    x=anom_x,
                    y=anom_y,
                    mode="markers",
                    name="Bất thường",
                    marker=dict(color=ML_CRIMSON, size=11, symbol="diamond", line=dict(color="#FFFFFF", width=1.5)),
                    text=anom_hover,
                    hovertemplate="%{text}<extra></extra>",
                )
            )

    if threshold is not None:
        try:
            th_val = float(threshold)
            fig.add_hline(
                y=th_val,
                line_dash="dash",
                line_color=ML_CRIMSON,
                line_width=1.5,
                annotation_text=f"Ngưỡng: {format_vi_number(th_val, unit)}",
                annotation_position="top left",
                annotation_font=dict(color=ML_CRIMSON, size=11),
            )
        except (ValueError, TypeError):
            pass

    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=ML_NAVY)) if title else dict(text=""),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro, Segoe UI, sans-serif", color=ML_TEXT, size=12),
        height=height,
        margin=dict(l=12, r=12, t=34 if title else 14, b=16),
        showlegend=bool(anomalies),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=ML_CARD_BORDER, font=dict(color=ML_TEXT, size=12)),
        xaxis=dict(showgrid=False, title=None, type="category", tickfont=dict(size=11, color=ML_SLATE)),
        yaxis=dict(showgrid=True, gridcolor="#EAEEF3", zeroline=False, title=None, tickfont=dict(size=11, color=ML_SLATE)),
    )
    return fig
