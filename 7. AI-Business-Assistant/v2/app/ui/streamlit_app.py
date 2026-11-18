"""Streamlit UI Application v2.0 for Gỗ Minh Long AI Assistant.

Specifications:
- Spec §5 T6, §11.7
- 5 screens: Tổng quan, Cảnh báo, Hỏi đáp AI, Hành động, Lịch sử
- Persistent Synthetic Data warning banner (§6.4)
- Power BI Quick Ask URL parameter pre-loading (?dashboard=...&kpi=...&profile=...&screen=...)
- No server layer imports (UI communicates exclusively via HttpApiClient)
"""

import os
import uuid
import streamlit as st

from app.ui.api_client import ApiClientError, HttpApiClient
from app.ui.components import (
    render_actions_view,
    render_alert_center,
    render_chat_view,
    render_history_view,
    render_overview,
)
from app.ui.theme import (
    ROLE_SHORT_VI,
    get_logo_base64,
    inject_minh_long_theme,
)

ROLE_TOKENS = {
    "ceo": "gml-dev-token-ceo",
    "ke_toan_truong": "gml-dev-token-ktt",
    "quan_ly_kho": "gml-dev-token-kho",
    "quan_tri_he_thong": "gml-dev-token-admin",
}

ROLE_LABELS = {
    "ceo": "Nguyễn Văn A (CEO)",
    "ke_toan_truong": "Trần Thị B (Kế toán trưởng)",
    "quan_ly_kho": "Lê Văn C (Quản lý kho)",
    "quan_tri_he_thong": "Quản trị hệ thống",
}

SCREEN_OPTIONS = [
    "🏠 Tổng quan",
    "🔔 Cảnh báo",
    "💬 Hỏi đáp AI",
    "✅ Hành động",
    "📋 Lịch sử",
]

DASHBOARD_LABELS = {
    "no_vay": "Nợ vay & Hạn mức",
    "kho": "Hàng tồn kho",
    "cong_no": "Công nợ AR/AP",
    "tien_gui": "Tiền gửi & Thanh khoản",
    "dong_tien": "Dòng tiền & Doanh thu",
}

DASHBOARD_ALIASES = {
    "tai_chinh": "no_vay",
}


def _resolve_screen_index(screen_param: str | None, has_kpi_or_dashboard: bool = False) -> int:
    """Map URL query screen param to navigation option index."""
    if screen_param:
        sp = screen_param.strip().lower()
        if sp in ("overview", "tong_quan"):
            return 0
        if sp in ("alerts", "alert", "canh_bao"):
            return 1
        if sp in ("chat", "hoi_dap"):
            return 2
        if sp in ("actions", "action", "hanh_dong"):
            return 3
        if sp in ("history", "lich_su"):
            return 4
    if has_kpi_or_dashboard:
        return 2  # Quick Ask navigates directly to Chat screen
    return 0  # Default landing screen is Overview


def _resolve_profile_index(profile_param: str | None) -> int:
    """Map URL query profile param to selector index."""
    if not profile_param:
        return 0
    return 1 if profile_param.strip().lower() == "synth" else 0


def main() -> None:
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="Gỗ Minh Long · Trợ lý Điều hành AI",
        page_icon="🪵",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_minh_long_theme()
    logo_b64 = get_logo_base64()

    # 1. Initialize session variables
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"sess-{uuid.uuid4().hex[:12]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 2. Extract query parameters
    qp = st.query_params
    query_role = qp.get("role")
    query_profile = qp.get("profile")
    query_screen = qp.get("screen")
    query_dashboard = qp.get("dashboard")
    query_kpi = qp.get("kpi")
    autoload_last = qp.get("autoload_last")
    has_kpi_or_dashboard = bool(query_dashboard or query_kpi)

    current_qp = {
        "role": query_role,
        "profile": query_profile,
        "screen": query_screen,
        "dashboard": query_dashboard,
        "kpi": query_kpi,
    }
    prev_qp = st.session_state.get("_applied_qp") or {}

    # 3. Sidebar Configuration
    with st.sidebar:
        logo_img_html = (
            f'<img src="data:image/jpeg;base64,{logo_b64}" alt="Logo Gỗ Minh Long" />'
            if logo_b64
            else '<span style="font-size:24px;">🪵</span>'
        )
        st.markdown(
            f"""
            <div class="gml-sidebar-brand">
                {logo_img_html}
                <div>
                    <div class="gml-sidebar-brand-title">GỖ MINH LONG · AI ASSISTANT</div>
                    <div class="gml-sidebar-brand-sub">Trợ lý Điều hành & Dữ liệu Doanh nghiệp</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        role_options = list(ROLE_TOKENS.keys())
        if "role_selector" not in st.session_state:
            st.session_state["role_selector"] = query_role if query_role in role_options else role_options[0]
        elif query_role != prev_qp.get("role") and query_role in role_options:
            st.session_state["role_selector"] = query_role

        role = st.selectbox(
            "👤 Vai trò người dùng",
            options=role_options,
            format_func=lambda r: f"{ROLE_LABELS.get(r, r)} · {ROLE_SHORT_VI.get(r, r)}",
            key="role_selector",
        )

        profile_options = ["real", "synth"]
        if "profile_selector" not in st.session_state:
            st.session_state["profile_selector"] = (
                "synth" if _resolve_profile_index(query_profile) == 1 else "real"
            )
        elif query_profile != prev_qp.get("profile") and query_profile is not None:
            st.session_state["profile_selector"] = (
                "synth" if _resolve_profile_index(query_profile) == 1 else "real"
            )

        active_profile = st.radio(
            "🌐 Nguồn dữ liệu (Profile)",
            options=profile_options,
            format_func=lambda p: "Dữ liệu Thực tế (Data Warehouse)" if p == "real" else "Dữ liệu Mô phỏng (Synthetic)",
            key="profile_selector",
        )

        # Cross-screen programmatic navigation handling
        nav_screen = st.session_state.pop("nav_screen", None)
        qp_screen_changed = (
            query_screen != prev_qp.get("screen")
            or query_dashboard != prev_qp.get("dashboard")
            or query_kpi != prev_qp.get("kpi")
        )
        if nav_screen and nav_screen in SCREEN_OPTIONS:
            st.session_state["screen_selector"] = nav_screen
        elif "screen_selector" not in st.session_state:
            initial_screen_idx = _resolve_screen_index(
                query_screen,
                has_kpi_or_dashboard=has_kpi_or_dashboard,
            )
            st.session_state["screen_selector"] = SCREEN_OPTIONS[initial_screen_idx]
        elif qp_screen_changed and (query_screen is not None or has_kpi_or_dashboard):
            target_idx = _resolve_screen_index(
                query_screen,
                has_kpi_or_dashboard=has_kpi_or_dashboard,
            )
            st.session_state["screen_selector"] = SCREEN_OPTIONS[target_idx]

        st.session_state["_applied_qp"] = current_qp

        active_screen = st.radio(
            "📌 Chức năng",
            options=SCREEN_OPTIONS,
            key="screen_selector",
        )

        st.divider()
        if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
            st.session_state.session_id = f"sess-{uuid.uuid4().hex[:12]}"
            st.session_state.messages = []
            st.rerun()

    # 4. Instantiate API Client
    api_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    token = ROLE_TOKENS.get(role, "gml-dev-token-ceo")
    api_client = HttpApiClient(base_url=api_url, token=token)

    # Top Masthead Bar
    masthead_logo = (
        f'<img src="data:image/jpeg;base64,{logo_b64}" alt="Logo Gỗ Minh Long" />'
        if logo_b64
        else '<span style="font-size:22px;">🪵</span>'
    )
    role_vi = ROLE_SHORT_VI.get(role, role)
    profile_badge = (
        '<span class="gml-badge gml-badge-warning">Dữ liệu Mô phỏng</span>'
        if active_profile == "synth"
        else '<span class="gml-badge gml-badge-navy">Dữ liệu Thực tế</span>'
    )
    st.markdown(
        f"""
        <div class="gml-masthead">
            <div class="gml-masthead-left">
                {masthead_logo}
                <div>
                    <div class="gml-masthead-title">GỖ MINH LONG · TRỢ LÝ ĐIỀU HÀNH AI</div>
                    <div class="gml-masthead-sub">Báo cáo Quản trị Thông minh · Power BI Simplifica</div>
                </div>
            </div>
            <div class="gml-masthead-pills">
                <span class="gml-badge gml-badge-count">{role_vi}</span>
                {profile_badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Persistent Synthetic Data Warning Banner (TC-T6-02)
    has_synth_warning = any(
        "SYNTHETIC_DATA" in (msg.get("warnings") or [])
        for msg in st.session_state.messages
    )
    if active_profile == "synth" or has_synth_warning:
        st.warning(
            "⚠️ DỮ LIỆU MÔ PHỎNG (SYNTHETIC DATA) — Chỉ dùng cho kiểm thử & phân tích kịch bản, không dùng cho quyết định tài chính thực tế."
        )

    # 6. Power BI Quick Ask Pre-loaded Context Banner (Ruling #7)
    if query_dashboard or query_kpi:
        actual_dash_key = DASHBOARD_ALIASES.get(query_dashboard, query_dashboard)
        dash_name = DASHBOARD_LABELS.get(actual_dash_key) if actual_dash_key else None

        kpi_name = query_kpi
        if query_kpi:
            try:
                kpi_data = api_client.get_kpi(query_kpi, profile=active_profile)
                kpi_name = kpi_data.get("kpi_name") or query_kpi
            except (ApiClientError, Exception):
                kpi_name = query_kpi

        if dash_name and kpi_name:
            banner_text = f"⚡ **Power BI Quick Ask**: Ngữ cảnh được nạp từ **{dash_name}** cho chỉ số **{kpi_name}**."
        elif dash_name:
            banner_text = f"⚡ **Power BI Quick Ask**: Ngữ cảnh được nạp từ **{dash_name}**."
        else:
            banner_text = f"⚡ **Power BI Quick Ask**: Ngữ cảnh được nạp cho chỉ số **{kpi_name}**."

        st.info(banner_text)
        if kpi_name:
            col_qa1, _ = st.columns([2, 5])
            with col_qa1:
                if st.button(f"Hỏi nhanh: {kpi_name}", key="pbi_quick_ask_btn"):
                    st.session_state["pending_query"] = f"{kpi_name} hiện tại là bao nhiêu?"
                    st.session_state["nav_screen"] = SCREEN_OPTIONS[2]
                    st.rerun()

    # 7. Autoload Demo Data for EV-16 Screenshots if requested
    if autoload_last and (not st.session_state.messages or st.session_state.get("_last_loaded_profile") != active_profile):
        try:
            demo_resp = api_client.chat(
                query="Dư nợ ngắn hạn hiện tại là bao nhiêu?",
                session_id=st.session_state.session_id,
                data_profile=active_profile,
            )
            st.session_state.messages = [
                {
                    "role": "user",
                    "content": "Dư nợ ngắn hạn hiện tại là bao nhiêu?",
                },
                {
                    "role": "assistant",
                    "content": demo_resp.get("answer", {}),
                    "request_id": demo_resp.get("request_id", "req-demo"),
                    "kpi_keys": demo_resp.get("kpi_keys", []),
                    "warnings": demo_resp.get("warnings", []),
                },
            ]
            st.session_state["_last_loaded_profile"] = active_profile
        except Exception:
            pass

    # 8. Render Selected Screen (5 Screens)
    if active_screen == SCREEN_OPTIONS[0]:
        render_overview(api_client=api_client, profile=active_profile)
    elif active_screen == SCREEN_OPTIONS[1]:
        render_alert_center(api_client=api_client, profile=active_profile)
    elif active_screen == SCREEN_OPTIONS[2]:
        render_chat_view(api_client=api_client, profile=active_profile, role=role)
    elif active_screen == SCREEN_OPTIONS[3]:
        render_actions_view(api_client=api_client, profile=active_profile)
    elif active_screen == SCREEN_OPTIONS[4]:
        render_history_view(api_client=api_client, profile=active_profile)


if __name__ == "__main__":
    main()
