"""Login Gate, Cookie Persistence, and Password Change Views (Task 4).

Pure UI presentation module: MUST NOT import app.services, app.agents, app.knowledge, or db.
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.ui.api_client import ApiClientError, HttpApiClient
from app.ui.theme import ML_CRIMSON, ML_NAVY, ML_SLATE, get_logo_base64

COOKIE_NAME = "gml_session"
SESSION_MAX_AGE_SECONDS = 43200  # 12 hours

_ALLOWED_PENDING_QP_KEYS = ("dashboard", "kpi", "screen", "profile", "autoload_last")


def set_session_cookie(token: str, max_age: int = SESSION_MAX_AGE_SECONDS) -> None:
    """Persist session token in browser cookie `gml_session` via zero-height JS snippet."""
    if not token:
        return
    safe_token = json.dumps(str(token))
    try:
        components.html(
            f"""
            <script>
            try {{
                window.parent.document.cookie = "{COOKIE_NAME}=" + encodeURIComponent({safe_token}) + "; path=/; max-age={int(max_age)}; SameSite=Lax";
            }} catch (e) {{}}
            </script>
            """,
            height=0,
        )
    except Exception:
        pass


def clear_session_cookie() -> None:
    """Expire browser cookie `gml_session` via zero-height JS snippet."""
    try:
        components.html(
            f"""
            <script>
            try {{
                window.parent.document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
            }} catch (e) {{}}
            </script>
            """,
            height=0,
        )
    except Exception:
        pass


def flush_pending_cookie_action() -> None:
    """Apply any deferred cookie set/clear operation on the rendered page after rerun."""
    action = st.session_state.pop("_pending_cookie_action", None)
    if not isinstance(action, tuple) or len(action) != 2:
        return
    op, value = action
    if op == "set" and value:
        set_session_cookie(str(value))
    elif op == "clear":
        clear_session_cookie()


def _restore_pending_query_params(pending_query_params: dict[str, str] | None) -> None:
    """Restore non-role Quick Ask / navigation query params into st.query_params after login."""
    saved = pending_query_params or st.session_state.pop("_pending_qp_after_login", None)
    if not isinstance(saved, dict):
        return
    for key in _ALLOWED_PENDING_QP_KEYS:
        val = saved.get(key)
        if val:
            st.query_params[key] = str(val)


def render_login_view(
    api_base_url: str,
    pending_query_params: dict[str, str] | None = None,
) -> None:
    """Render Minh Long branded centered login card and handle /v1/auth/login."""
    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/jpeg;base64,{logo_b64}" alt="Logo Gỗ Minh Long" '
        f'style="height:56px;width:auto;object-fit:contain;border-radius:6px;margin-bottom:8px;" />'
        if logo_b64
        else '<div style="font-size:40px;margin-bottom:6px;">🪵</div>'
    )

    _, col_center, _ = st.columns([1.15, 1.7, 1.15])
    with col_center:
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="text-align:center;padding:8px 4px 12px 4px;border-bottom:2px solid {ML_CRIMSON};margin-bottom:14px;">
                    {logo_html}
                    <div style="font-size:18px;font-weight:700;color:{ML_NAVY};letter-spacing:0.02em;">
                        GỖ MINH LONG · TRỢ LÝ ĐIỀU HÀNH AI
                    </div>
                    <div style="font-size:12px;color:{ML_SLATE};margin-top:2px;">
                        Đăng nhập hệ thống quản trị &amp; phân tích dữ liệu nội bộ
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            flash_err = st.session_state.pop("auth_flash_error", None)
            if flash_err:
                st.error(flash_err)

            flash_ok = st.session_state.pop("auth_flash_success", None)
            if flash_ok:
                st.success(flash_ok)

            username = st.text_input(
                "Tên đăng nhập",
                key="login_username",
                placeholder="Nhập tên đăng nhập (vd: nva.ceo)",
            )
            password = st.text_input(
                "Mật khẩu",
                type="password",
                key="login_password",
                placeholder="Nhập mật khẩu",
            )

            if st.button("Đăng nhập", key="login_submit_btn", type="primary", use_container_width=True):
                clean_user = (username or "").strip()
                if not clean_user or not password:
                    st.warning("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
                else:
                    resp: dict[str, Any] | None = None
                    client = HttpApiClient(base_url=api_base_url, token="")
                    try:
                        resp = client.login(clean_user, password)
                    except ApiClientError as exc:
                        st.error(exc.detail_message)
                    finally:
                        client.close()
                    if isinstance(resp, dict) and resp.get("access_token"):
                        token = str(resp["access_token"])
                        st.session_state["auth_token"] = token
                        st.session_state["auth_user"] = dict(resp.get("user") or {})
                        st.session_state.pop("_logged_out_flag", None)
                        st.session_state.pop("show_change_password", None)
                        st.session_state["_pending_cookie_action"] = ("set", token)
                        _restore_pending_query_params(pending_query_params)
                        st.rerun()

            st.caption("Quên mật khẩu? Liên hệ Quản trị hệ thống.")


def render_change_password_view(
    api_client: HttpApiClient,
    user: dict[str, Any],
    forced: bool = False,
) -> None:
    """Render password change form enforcing NIST 800-63B guidance."""
    _, col_center, _ = st.columns([1.0, 2.0, 1.0])
    with col_center:
        with st.container(border=True):
            title = "🔑 Đổi mật khẩu bắt buộc" if forced else "🔑 Đổi mật khẩu tài khoản"
            st.subheader(title)
            st.caption(
                f"Tài khoản: **{user.get('display_name') or user.get('username') or ''}**"
            )
            if forced:
                st.warning(
                    "Tài khoản đang sử dụng mật khẩu tạm hoặc được yêu cầu đổi mật khẩu ở lần đăng nhập đầu tiên."
                )

            st.info(
                "Quy định mật khẩu (NIST 800-63B): **10–128 ký tự, có chữ và số** "
                "(cho phép dấu cách; không trùng tên đăng nhập, email hoặc từ cấm)."
            )

            current_password = st.text_input(
                "Mật khẩu hiện tại",
                type="password",
                key="cp_current_password",
            )
            new_password = st.text_input(
                "Mật khẩu mới",
                type="password",
                key="cp_new_password",
            )
            confirm_password = st.text_input(
                "Nhập lại mật khẩu mới",
                type="password",
                key="cp_confirm_password",
            )

            col_btn1, col_btn2 = st.columns([2, 1])
            with col_btn1:
                submit_clicked = st.button(
                    "✅ Đổi mật khẩu",
                    key="cp_submit_btn",
                    type="primary",
                    use_container_width=True,
                )
            with col_btn2:
                if not forced and st.button("Quay lại", key="cp_cancel_btn", use_container_width=True):
                    st.session_state["show_change_password"] = False
                    st.rerun()

            if submit_clicked:
                if not current_password or not new_password or not confirm_password:
                    st.warning("Vui lòng nhập đầy đủ cả 3 ô mật khẩu.")
                elif new_password != confirm_password:
                    st.error("Mật khẩu mới và ô nhập lại không khớp.")
                else:
                    try:
                        api_client.change_password(current_password, new_password)
                    except ApiClientError as exc:
                        if exc.status_code == 401 and exc.error_code != "INVALID_CREDENTIALS":
                            raise
                        st.error(exc.detail_message)
                    else:
                        updated_user = dict(user)
                        updated_user["must_change_password"] = False
                        st.session_state["auth_user"] = updated_user
                        st.session_state["show_change_password"] = False
                        st.session_state["auth_flash_success"] = "Đổi mật khẩu thành công."
                        st.rerun()
