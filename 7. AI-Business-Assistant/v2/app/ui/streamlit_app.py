"""Streamlit UI Application v2.0 for Gỗ Minh Long AI Assistant.

Specifications:
- Design §5.6 (Login Gate, F5 Cookie Persistence, Role-Locked Sidebar & 4-Tab Admin Panel)
- Spec §5 T6, §11.7 (5 business screens + Persistent Synthetic Data warning + Power BI Quick Ask)
- No server layer imports (UI communicates exclusively via HttpApiClient)
"""

from __future__ import annotations

import html
import os
from typing import Any
import uuid

import streamlit as st

from app.ui.api_client import ApiClientError, HttpApiClient, get_require_login_for_testing
from app.ui.components import (
    COOKIE_NAME,
    clear_session_cookie,
    flush_pending_cookie_action,
    render_actions_view,
    render_admin_panel,
    render_alert_center,
    render_change_password_view,
    render_chat_view,
    render_history_view,
    render_login_view,
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


def _render_sidebar_brand(logo_b64: str | None) -> None:
    """Render the Minh Long brand header block inside the sidebar."""
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
                <div class="gml-sidebar-brand-sub">Trợ lý Điều hành &amp; Dữ liệu Doanh nghiệp</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_user_card(user: dict[str, Any]) -> None:
    """Render read-only authenticated user identity card in the sidebar."""
    display_name = html.escape(str(user.get("display_name") or user.get("username") or "Người dùng"))
    role = str(user.get("role") or "")
    role_vi = html.escape(ROLE_SHORT_VI.get(role, role))
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #E6E6E6;border-radius:8px;padding:10px 12px;margin-bottom:10px;">
            <div style="font-size:13px;font-weight:700;color:#062F4F;">👤 {display_name}</div>
            <div style="font-size:12px;color:#506B85;margin-top:2px;">{role_vi}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_masthead(
    logo_b64: str | None,
    role: str,
    active_profile: str | None = None,
    extra_badge: str | None = None,
) -> None:
    """Render top brand masthead with role and data profile badges."""
    masthead_logo = (
        f'<img src="data:image/jpeg;base64,{logo_b64}" alt="Logo Gỗ Minh Long" />'
        if logo_b64
        else '<span style="font-size:22px;">🪵</span>'
    )
    role_vi = ROLE_SHORT_VI.get(role, role)
    if extra_badge:
        right_badge = extra_badge
    elif active_profile == "synth":
        right_badge = '<span class="gml-badge gml-badge-warning">Dữ liệu Mô phỏng</span>'
    else:
        right_badge = '<span class="gml-badge gml-badge-navy">Dữ liệu Thực tế</span>'

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
                {right_badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _clear_auth_session_state() -> None:
    """Remove authenticated session keys while preserving non-auth UI scaffolding."""
    for key in (
        "auth_token",
        "auth_user",
        "show_change_password",
        "messages",
        "screen_selector",
        "profile_selector",
        "_applied_qp",
        "_last_loaded_profile",
        "pending_query",
        "nav_screen",
        "admin_temp_password_banner",
    ):
        st.session_state.pop(key, None)


def _handle_logout(api_client: HttpApiClient | None) -> None:
    """Revoke server session best-effort, clear cookie & session state, and rerun."""
    if api_client is not None:
        try:
            api_client.logout()
        except Exception:
            pass
    _clear_auth_session_state()
    st.session_state["_logged_out_flag"] = True
    st.session_state["_pending_cookie_action"] = ("clear", None)
    st.session_state["auth_flash_success"] = "Bạn đã đăng xuất khỏi hệ thống."
    st.rerun()


def _handle_session_expired() -> None:
    """Clear expired session & cookie and redirect to login with Vietnamese notice."""
    _clear_auth_session_state()
    st.session_state["_logged_out_flag"] = True
    st.session_state["_pending_cookie_action"] = ("clear", None)
    st.session_state["auth_flash_error"] = "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại."
    st.rerun()


def _save_pending_query_params(qp: Any) -> dict[str, str]:
    """Capture non-role query parameters before showing the login screen."""
    pending: dict[str, str] = {}
    for key in ("dashboard", "kpi", "screen", "profile", "autoload_last"):
        val = qp.get(key)
        if val:
            pending[key] = str(val)
    if pending:
        st.session_state["_pending_qp_after_login"] = pending
    return pending


def _read_session_cookie() -> str | None:
    """Read gml_session cookie safely via st.context.cookies."""
    try:
        raw = st.context.cookies.get(COOKIE_NAME)
        if raw:
            return str(raw).strip()
    except Exception:
        return None
    return None


def _render_business_main(
    *,
    api_client: HttpApiClient,
    role: str,
    active_profile: str,
    active_screen: str,
    query_dashboard: str | None,
    query_kpi: str | None,
    autoload_last: str | None,
    logo_b64: str | None,
    handle_401: bool,
) -> None:
    """Render business masthead, banners, Quick Ask, and the active business screen."""
    _render_masthead(logo_b64=logo_b64, role=role, active_profile=active_profile)

    # Power BI Quick Ask Pre-loaded Context Banner (Ruling #7)
    if query_dashboard or query_kpi:
        actual_dash_key = DASHBOARD_ALIASES.get(query_dashboard, query_dashboard)
        dash_name = DASHBOARD_LABELS.get(actual_dash_key) if actual_dash_key else None

        kpi_name = query_kpi
        if query_kpi:
            try:
                kpi_data = api_client.get_kpi(query_kpi, profile=active_profile)
                kpi_name = kpi_data.get("kpi_name") or query_kpi
            except ApiClientError as exc:
                if handle_401 and exc.status_code == 401:
                    _handle_session_expired()
                kpi_name = query_kpi
            except Exception:
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

    # Autoload Demo Data for EV-16 Screenshots if requested
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
        except ApiClientError as exc:
            if handle_401 and exc.status_code == 401:
                _handle_session_expired()
        except Exception:
            pass

    # Render Selected Screen (5 Screens)
    try:
        if active_screen == SCREEN_OPTIONS[0]:
            render_overview(api_client=api_client, profile=active_profile, role=role)
        elif active_screen == SCREEN_OPTIONS[1]:
            render_alert_center(api_client=api_client, profile=active_profile)
        elif active_screen == SCREEN_OPTIONS[2]:
            render_chat_view(api_client=api_client, profile=active_profile, role=role)
        elif active_screen == SCREEN_OPTIONS[3]:
            render_actions_view(api_client=api_client, profile=active_profile)
        elif active_screen == SCREEN_OPTIONS[4]:
            render_history_view(api_client=api_client, profile=active_profile)
    except ApiClientError as exc:
        if handle_401 and exc.status_code == 401:
            _handle_session_expired()
        raise


def _run_legacy_test_mode(api_url: str, logo_b64: str | None) -> None:
    """Preserve legacy dev-token UI flow ONLY when running in-process mock-transport UI tests."""
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

    with st.sidebar:
        _render_sidebar_brand(logo_b64)

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

    token = ROLE_TOKENS.get(role, "gml-dev-token-ceo")
    api_client = HttpApiClient(base_url=api_url, token=token)
    try:
        _render_business_main(
            api_client=api_client,
            role=role,
            active_profile=active_profile,
            active_screen=active_screen,
            query_dashboard=query_dashboard,
            query_kpi=query_kpi,
            autoload_last=autoload_last,
            logo_b64=logo_b64,
            handle_401=False,
        )
    finally:
        api_client.close()


def _run_authenticated_app(api_url: str, logo_b64: str | None) -> None:
    """Enforce login gate, F5 cookie restore, role-locked sidebar, and Admin Panel."""
    flush_pending_cookie_action()
    qp = st.query_params

    auth_token = st.session_state.get("auth_token")
    auth_user = st.session_state.get("auth_user")

    # 1. F5 Session Restoration via gml_session cookie -> GET /v1/auth/me
    if not auth_token and not st.session_state.get("_logged_out_flag"):
        cookie_tok = _read_session_cookie()
        if cookie_tok:
            me_client = HttpApiClient(base_url=api_url, token=cookie_tok)
            try:
                user_info = me_client.get_me()
            except ApiClientError as exc:
                if exc.status_code == 401:
                    clear_session_cookie()
                    st.session_state.pop("auth_token", None)
                    st.session_state.pop("auth_user", None)
                    st.session_state["_logged_out_flag"] = True
                    st.session_state["auth_flash_error"] = "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại."
                else:
                    st.error(f"Không thể kết nối máy chủ xác thực: {exc}")
                    return
            except Exception as exc:
                st.error(f"Không thể kết nối máy chủ xác thực: {exc}")
                return
            else:
                st.session_state["auth_token"] = cookie_tok
                st.session_state["auth_user"] = user_info
                auth_token = cookie_tok
                auth_user = user_info
            finally:
                me_client.close()

    # 2. Unauthenticated Gate (?role= is ignored; non-role params preserved for post-login)
    if not auth_token or not isinstance(auth_user, dict):
        pending_qp = _save_pending_query_params(qp)
        render_login_view(api_base_url=api_url, pending_query_params=pending_qp)
        return

    api_client = HttpApiClient(base_url=api_url, token=str(auth_token))
    try:
        role = str(auth_user.get("role") or "")

        # 3. Forced Password Change Gate (must_change_password=True)
        if auth_user.get("must_change_password"):
            with st.sidebar:
                _render_sidebar_brand(logo_b64)
                _render_sidebar_user_card(auth_user)
                st.divider()
                if st.button("↩ Đăng xuất", key="sidebar_logout_btn", use_container_width=True):
                    _handle_logout(api_client)
            _render_masthead(
                logo_b64=logo_b64,
                role=role,
                extra_badge='<span class="gml-badge gml-badge-warning">Đổi mật khẩu bắt buộc</span>',
            )
            try:
                render_change_password_view(api_client, auth_user, forced=True)
            except ApiClientError as exc:
                if exc.status_code == 401:
                    _handle_session_expired()
                raise
            return

        # 4. System Administrator Mode (quan_tri_he_thong -> 4-tab Admin Panel ONLY)
        if role == "quan_tri_he_thong":
            with st.sidebar:
                _render_sidebar_brand(logo_b64)
                _render_sidebar_user_card(auth_user)
                st.divider()
                if st.button("🔑 Đổi mật khẩu", key="sidebar_change_pw_btn", use_container_width=True):
                    st.session_state["show_change_password"] = True
                    st.rerun()
                if st.button("↩ Đăng xuất", key="sidebar_logout_btn", use_container_width=True):
                    _handle_logout(api_client)

            _render_masthead(
                logo_b64=logo_b64,
                role=role,
                extra_badge='<span class="gml-badge gml-badge-navy">Quản trị IAM</span>',
            )
            flash_ok = st.session_state.pop("auth_flash_success", None)
            if flash_ok:
                st.success(flash_ok)

            try:
                if st.session_state.get("show_change_password"):
                    render_change_password_view(api_client, auth_user, forced=False)
                else:
                    render_admin_panel(api_client, auth_user)
            except ApiClientError as exc:
                if exc.status_code == 401:
                    _handle_session_expired()
                raise
            return

        # 5. Authenticated Business Roles (ceo, ke_toan_truong, quan_ly_kho) — Role Locked!
        query_profile = qp.get("profile")
        query_screen = qp.get("screen")
        query_dashboard = qp.get("dashboard")
        query_kpi = qp.get("kpi")
        autoload_last = qp.get("autoload_last")
        has_kpi_or_dashboard = bool(query_dashboard or query_kpi)

        raw_allowed = auth_user.get("allowed_profiles") or ["real"]
        allowed_profiles = [p for p in raw_allowed if p in ("real", "synth")] or ["real"]

        current_qp = {
            "profile": query_profile,
            "screen": query_screen,
            "dashboard": query_dashboard,
            "kpi": query_kpi,
        }
        prev_qp = st.session_state.get("_applied_qp") or {}

        with st.sidebar:
            _render_sidebar_brand(logo_b64)
            _render_sidebar_user_card(auth_user)

            if len(allowed_profiles) > 1:
                if "profile_selector" not in st.session_state or st.session_state["profile_selector"] not in allowed_profiles:
                    if query_profile in allowed_profiles:
                        st.session_state["profile_selector"] = query_profile
                    else:
                        st.session_state["profile_selector"] = allowed_profiles[0]
                elif query_profile != prev_qp.get("profile") and query_profile in allowed_profiles:
                    st.session_state["profile_selector"] = query_profile

                active_profile = st.radio(
                    "🌐 Nguồn dữ liệu (Profile)",
                    options=allowed_profiles,
                    format_func=lambda p: "Dữ liệu Thực tế (Data Warehouse)" if p == "real" else "Dữ liệu Mô phỏng (Synthetic)",
                    key="profile_selector",
                )
            else:
                active_profile = allowed_profiles[0]
                profile_label = "Thực tế (Data Warehouse)" if active_profile == "real" else "Mô phỏng (Synthetic)"
                st.caption(f"🌐 Nguồn dữ liệu: **{profile_label}**")

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
            if st.button("🔑 Đổi mật khẩu", key="sidebar_change_pw_btn", use_container_width=True):
                st.session_state["show_change_password"] = True
                st.rerun()
            if st.button("↩ Đăng xuất", key="sidebar_logout_btn", use_container_width=True):
                _handle_logout(api_client)

        flash_ok = st.session_state.pop("auth_flash_success", None)
        if flash_ok:
            st.success(flash_ok)

        if st.session_state.get("show_change_password"):
            _render_masthead(logo_b64=logo_b64, role=role, active_profile=active_profile)
            try:
                render_change_password_view(api_client, auth_user, forced=False)
            except ApiClientError as exc:
                if exc.status_code == 401:
                    _handle_session_expired()
                raise
            return

        _render_business_main(
            api_client=api_client,
            role=role,
            active_profile=active_profile,
            active_screen=active_screen,
            query_dashboard=query_dashboard,
            query_kpi=query_kpi,
            autoload_last=autoload_last,
            logo_b64=logo_b64,
            handle_401=True,
        )
    finally:
        api_client.close()


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

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"sess-{uuid.uuid4().hex[:12]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    api_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

    if not get_require_login_for_testing():
        _run_legacy_test_mode(api_url=api_url, logo_b64=logo_b64)
        return

    _run_authenticated_app(api_url=api_url, logo_b64=logo_b64)


if __name__ == "__main__":
    main()
