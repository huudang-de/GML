"""4-Tab Administration Panel Component for quan_tri_he_thong (Task 4).

Pure UI presentation module: MUST NOT import app.services, app.agents, app.knowledge, or db.

Tabs:
1. 👥 Người dùng
2. 🔐 Phiên đăng nhập
3. ⚙️ Dữ liệu Mô phỏng & Dự báo (`synth`)
4. 📜 Nhật ký Truy cập
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import pandas as pd
import streamlit as st

from app.ui.api_client import ApiClientError, HttpApiClient
from app.ui.theme import ROLE_SHORT_VI, format_vi_datetime

ROLE_OPTIONS = ["ceo", "ke_toan_truong", "quan_ly_kho", "quan_tri_he_thong"]
PROFILE_OPTIONS = ["real", "synth"]
AUTH_EVENT_TYPES = [
    "Tất cả",
    "login_success",
    "login_failed",
    "account_locked",
    "logout",
    "session_expired",
    "password_changed",
    "password_reset_by_admin",
    "user_created",
    "user_updated",
    "role_changed",
    "profiles_changed",
    "user_disabled",
    "user_enabled",
    "sessions_revoked",
    "simulation_triggered",
]


def _raise_if_unauthorized(exc: Exception) -> None:
    """Propagate 401 ApiClientError so main app clears session and redirects to login."""
    if isinstance(exc, ApiClientError) and exc.status_code == 401:
        raise exc


def _format_user_status(user: dict[str, Any]) -> str:
    """Return Vietnamese status badge text for an IAM account."""
    if not user.get("is_active", True):
        return "⛔ Vô hiệu"
    locked_until = user.get("locked_until")
    if locked_until:
        try:
            dt = datetime.fromisoformat(str(locked_until).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > datetime.now(timezone.utc):
                return "🔒 Bị khoá"
        except ValueError:
            return "🔒 Bị khoá"
    return "🟢 Hoạt động"


def _format_profiles(profiles: list[str] | None) -> str:
    """Format allowed_profiles list into Vietnamese label."""
    labels = []
    for p in profiles or []:
        labels.append("Thực tế" if p == "real" else "Mô phỏng")
    return ", ".join(labels) if labels else "—"


def _render_temp_password_banner() -> None:
    """Render one-time temporary password box stored across rerun if present."""
    pw_info = st.session_state.pop("admin_temp_password_banner", None)
    if not isinstance(pw_info, dict) or not pw_info.get("password"):
        return
    uname = pw_info.get("username") or pw_info.get("user_id") or ""
    st.warning(
        f"⚠️ Mật khẩu tạm cho tài khoản **{uname}** chỉ hiển thị **một lần duy nhất**. "
        "Hãy sao chép và gửi qua kênh bảo mật; người dùng sẽ phải đổi mật khẩu khi đăng nhập."
    )
    st.code(str(pw_info["password"]), language=None)


def _render_users_tab(api_client: HttpApiClient, current_user: dict[str, Any]) -> None:
    """Render Tab 1: 👥 Người dùng."""
    st.subheader("👥 Quản lý Tài khoản Người dùng")
    _render_temp_password_banner()

    flash_msg = st.session_state.pop("admin_user_flash", None)
    if flash_msg:
        st.success(flash_msg)

    # Create user expander
    with st.expander("➕ Thêm người dùng", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            new_username = st.text_input("Tên đăng nhập *", key="admin_new_username", placeholder="vd: nvb.ktt")
            new_display = st.text_input("Họ và tên *", key="admin_new_display_name", placeholder="vd: Nguyễn Văn B")
            new_email = st.text_input("Email", key="admin_new_email", placeholder="vd: nvb@gominhlong.vn")
        with c2:
            new_role = st.selectbox(
                "Vai trò *",
                options=ROLE_OPTIONS,
                format_func=lambda r: f"{ROLE_SHORT_VI.get(r, r)} ({r})",
                key="admin_new_role",
            )
            new_profiles = st.multiselect(
                "Nguồn dữ liệu được phép",
                options=PROFILE_OPTIONS,
                default=PROFILE_OPTIONS,
                format_func=lambda p: "Thực tế (real)" if p == "real" else "Mô phỏng (synth)",
                key="admin_new_profiles",
            )
            new_must_change = st.checkbox(
                "Bắt buộc đổi mật khẩu ở lần đăng nhập đầu",
                value=True,
                key="admin_new_must_change",
            )

        if st.button("✅ Tạo tài khoản", key="admin_create_user_btn", type="primary"):
            if not new_username.strip() or not new_display.strip():
                st.warning("Vui lòng nhập Tên đăng nhập và Họ tên.")
            else:
                try:
                    created = api_client.admin_create_user(
                        username=new_username.strip(),
                        display_name=new_display.strip(),
                        role=new_role,
                        allowed_profiles=new_profiles or ["real"],
                        email=new_email.strip() or None,
                        must_change_password=new_must_change,
                    )
                except Exception as exc:
                    _raise_if_unauthorized(exc)
                    msg = exc.detail_message if isinstance(exc, ApiClientError) else str(exc)
                    st.error(msg)
                else:
                    temp_pw = created.get("temporary_password")
                    created_user = created.get("user") or {}
                    st.session_state["admin_temp_password_banner"] = {
                        "username": created_user.get("username", new_username.strip()),
                        "password": temp_pw,
                    }
                    st.session_state["admin_user_flash"] = (
                        f"Đã tạo tài khoản '{created_user.get('username', new_username)}'."
                    )
                    st.rerun()

    # Search & Filters
    f1, f2, f3 = st.columns([2.2, 1.4, 1.4])
    with f1:
        q_filter = st.text_input("🔍 Tìm tên / username", key="admin_user_search", placeholder="Nhập từ khoá...")
    with f2:
        role_filter_opts = ["Tất cả"] + ROLE_OPTIONS
        role_filter = st.selectbox(
            "Vai trò",
            options=role_filter_opts,
            format_func=lambda r: "Tất cả" if r == "Tất cả" else ROLE_SHORT_VI.get(r, r),
            key="admin_user_role_filter",
        )
    with f3:
        active_filter = st.selectbox(
            "Trạng thái",
            options=["Tất cả", "active", "inactive"],
            format_func=lambda s: "Tất cả" if s == "Tất cả" else ("Hoạt động" if s == "active" else "Đã vô hiệu"),
            key="admin_user_active_filter",
        )

    is_active_param: bool | None = None
    if active_filter == "active":
        is_active_param = True
    elif active_filter == "inactive":
        is_active_param = False

    try:
        users = api_client.admin_list_users(
            q=q_filter.strip() or None,
            role=None if role_filter == "Tất cả" else role_filter,
            is_active=is_active_param,
        )
    except Exception as exc:
        _raise_if_unauthorized(exc)
        msg = exc.detail_message if isinstance(exc, ApiClientError) else str(exc)
        st.error(f"Không tải được danh sách người dùng: {msg}")
        return

    if not users:
        st.info("Không tìm thấy tài khoản nào phù hợp.")
        return

    rows = [
        {
            "Username": u.get("username", ""),
            "Họ tên": u.get("display_name", ""),
            "Vai trò": ROLE_SHORT_VI.get(u.get("role", ""), u.get("role", "")),
            "Nguồn dữ liệu": _format_profiles(u.get("allowed_profiles")),
            "Trạng thái": _format_user_status(u),
            "Đăng nhập gần nhất": format_vi_datetime(u.get("last_login_at")),
        }
        for u in users
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Selected-user detail & action controls
    st.markdown("---")
    st.markdown("##### 🛠️ Chi tiết & Thao tác tài khoản")
    user_map = {u["user_id"]: u for u in users if u.get("user_id")}
    user_ids = list(user_map.keys())
    if not user_ids:
        return

    selected_uid = st.selectbox(
        "Chọn tài khoản thao tác",
        options=user_ids,
        format_func=lambda uid: (
            f"{user_map[uid].get('username')} — {user_map[uid].get('display_name')} "
            f"({ROLE_SHORT_VI.get(user_map[uid].get('role', ''), '')})"
        ),
        key="admin_selected_user_id",
    )
    target = user_map[selected_uid]
    is_self = selected_uid == current_user.get("user_id")

    with st.container(border=True):
        ec1, ec2 = st.columns(2)
        with ec1:
            edit_display = st.text_input(
                "Họ tên",
                value=str(target.get("display_name") or ""),
                key=f"admin_edit_name_{selected_uid}",
            )
            edit_email = st.text_input(
                "Email",
                value=str(target.get("email") or ""),
                key=f"admin_edit_email_{selected_uid}",
            )
        with ec2:
            cur_role = target.get("role", "ceo")
            role_idx = ROLE_OPTIONS.index(cur_role) if cur_role in ROLE_OPTIONS else 0
            edit_role = st.selectbox(
                "Vai trò",
                options=ROLE_OPTIONS,
                index=role_idx,
                format_func=lambda r: f"{ROLE_SHORT_VI.get(r, r)} ({r})",
                key=f"admin_edit_role_{selected_uid}",
                disabled=is_self,
            )
            edit_profiles = st.multiselect(
                "Nguồn dữ liệu được phép",
                options=PROFILE_OPTIONS,
                default=[p for p in (target.get("allowed_profiles") or ["real"]) if p in PROFILE_OPTIONS],
                format_func=lambda p: "Thực tế (real)" if p == "real" else "Mô phỏng (synth)",
                key=f"admin_edit_profiles_{selected_uid}",
            )
            edit_active = st.checkbox(
                "Tài khoản đang hoạt động",
                value=bool(target.get("is_active", True)),
                key=f"admin_edit_active_{selected_uid}",
                disabled=is_self,
            )

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("💾 Lưu thay đổi", key=f"admin_save_{selected_uid}", type="primary", use_container_width=True):
                try:
                    api_client.admin_update_user(
                        selected_uid,
                        display_name=edit_display.strip() or target.get("display_name"),
                        email=edit_email.strip() or None,
                        role=edit_role if not is_self else None,
                        allowed_profiles=edit_profiles or ["real"],
                        is_active=edit_active if not is_self else None,
                    )
                except Exception as exc:
                    _raise_if_unauthorized(exc)
                    st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
                else:
                    st.session_state["admin_user_flash"] = f"Đã cập nhật tài khoản '{target.get('username')}'."
                    st.rerun()

        with b2:
            if st.button("🔑 Đặt lại mật khẩu", key=f"admin_reset_pw_{selected_uid}", use_container_width=True):
                try:
                    res = api_client.admin_reset_password(selected_uid)
                except Exception as exc:
                    _raise_if_unauthorized(exc)
                    st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
                else:
                    st.session_state["admin_temp_password_banner"] = {
                        "username": target.get("username"),
                        "password": res.get("temporary_password"),
                    }
                    st.rerun()

        with b3:
            if st.button("🔓 Mở khoá", key=f"admin_unlock_{selected_uid}", use_container_width=True):
                try:
                    api_client.admin_unlock_user(selected_uid)
                except Exception as exc:
                    _raise_if_unauthorized(exc)
                    st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
                else:
                    st.session_state["admin_user_flash"] = f"Đã mở khoá tài khoản '{target.get('username')}'."
                    st.rerun()

        with b4:
            if st.button("🚫 Thu hồi phiên", key=f"admin_revoke_u_{selected_uid}", use_container_width=True):
                try:
                    res = api_client.admin_revoke_user_sessions(selected_uid)
                except Exception as exc:
                    _raise_if_unauthorized(exc)
                    st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
                else:
                    cnt = res.get("revoked_count", 0)
                    st.session_state["admin_user_flash"] = (
                        f"Đã thu hồi {cnt} phiên đang mở của '{target.get('username')}'."
                    )
                    st.rerun()


def _render_sessions_tab(api_client: HttpApiClient) -> None:
    """Render Tab 2: 🔐 Phiên đăng nhập."""
    st.subheader("🔐 Phiên đăng nhập đang hoạt động")

    flash_msg = st.session_state.pop("admin_session_flash", None)
    if flash_msg:
        st.success(flash_msg)

    try:
        sessions = api_client.admin_list_sessions()
    except Exception as exc:
        _raise_if_unauthorized(exc)
        st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
        return

    if not sessions:
        st.info("Hiện không có phiên đăng nhập nào đang hoạt động.")
        return

    st.caption(f"Tổng số phiên đang mở: **{len(sessions)}**")
    for sess in sessions:
        sid = sess.get("session_id")
        uname = sess.get("username", "")
        dname = sess.get("display_name", "")
        role_vi = ROLE_SHORT_VI.get(sess.get("role", ""), sess.get("role", ""))
        ip = sess.get("client_ip") or "—"
        ua = sess.get("user_agent") or "—"
        created = format_vi_datetime(sess.get("created_at"))
        last_seen = format_vi_datetime(sess.get("last_seen_at"))
        expires = format_vi_datetime(sess.get("expires_at"))

        with st.container(border=True):
            c_info, c_act = st.columns([4, 1.2])
            with c_info:
                st.markdown(f"**#{sid} · {dname}** (`{uname}`) — {role_vi}")
                st.caption(
                    f"IP: `{ip}` | Đăng nhập: **{created}** | Hoạt động cuối: **{last_seen}** | Hết hạn: **{expires}**"
                )
                st.caption(f"Trình duyệt / Client: `{ua}`")
            with c_act:
                if st.button("Thu hồi phiên", key=f"admin_revoke_sess_{sid}", use_container_width=True):
                    try:
                        api_client.admin_revoke_session(int(sid))
                    except Exception as exc:
                        _raise_if_unauthorized(exc)
                        st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
                    else:
                        st.session_state["admin_session_flash"] = f"Đã thu hồi phiên #{sid} ({uname})."
                        st.rerun()


def _render_simulation_tab(api_client: HttpApiClient) -> None:
    """Render Tab 3: ⚙️ Dữ liệu Mô phỏng & Dự báo (`synth`)."""
    st.subheader("⚙️ Dữ liệu Mô phỏng & Dự báo Tháng (`synth`)")

    try:
        status_info = api_client.admin_get_simulation_status()
    except Exception as exc:
        _raise_if_unauthorized(exc)
        st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
        return

    last_run_at = format_vi_datetime(status_info.get("last_run_at"))
    last_status = status_info.get("last_status") or "Chưa chạy"
    last_message = status_info.get("last_message") or "Chưa có nhật ký chạy mô phỏng tháng."
    checksum_ok = bool(status_info.get("checksum_file_exists"))

    with st.container(border=True):
        m1, m2, m3 = st.columns(3)
        m1.metric("Lần chạy gần nhất", last_run_at)
        m2.metric("Trạng thái", str(last_status).upper() if last_status else "—")
        m3.metric("Checksum EV-03", "Có" if checksum_ok else "Chưa có")
        st.caption(f"Chi tiết: {last_message}")

    c_seed, c_btn = st.columns([1.2, 3])
    with c_seed:
        seed_val = st.number_input(
            "Seed tái lập",
            min_value=1,
            max_value=999999,
            value=42,
            step=1,
            key="admin_sim_seed",
        )
    with c_btn:
        st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
        if st.button(
            "▶ Chạy cập nhật dữ liệu mô phỏng tháng",
            key="admin_run_sim_btn",
            type="primary",
            use_container_width=True,
        ):
            try:
                res = api_client.admin_run_simulation(seed=int(seed_val))
            except Exception as exc:
                _raise_if_unauthorized(exc)
                st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
            else:
                st.success(
                    f"{res.get('message', 'Đã chạy xong.')} "
                    f"(Thời gian: {res.get('duration_ms', 0)} ms · Lúc {format_vi_datetime(res.get('run_at'))})"
                )


def _render_audit_events_tab(api_client: HttpApiClient) -> None:
    """Render Tab 4: 📜 Nhật ký Truy cập."""
    st.subheader("📜 Nhật ký Truy cập & Quản trị")

    c1, c2 = st.columns([1.5, 1.5])
    with c1:
        user_id_filter = st.text_input(
            "Lọc theo User ID",
            key="admin_events_user_filter",
            placeholder="vd: usr_ceo hoặc u_...",
        )
    with c2:
        event_type_filter = st.selectbox(
            "Loại sự kiện",
            options=AUTH_EVENT_TYPES,
            key="admin_events_type_filter",
        )

    try:
        events = api_client.admin_list_auth_events(
            user_id=user_id_filter.strip() or None,
            event_type=None if event_type_filter == "Tất cả" else event_type_filter,
        )
    except Exception as exc:
        _raise_if_unauthorized(exc)
        st.error(exc.detail_message if isinstance(exc, ApiClientError) else str(exc))
        return

    if not events:
        st.info("Chưa có sự kiện nào phù hợp.")
        return

    rows = []
    for ev in events:
        detail = ev.get("detail")
        detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else (str(detail) if detail else "—")
        rows.append(
            {
                "Thời gian": format_vi_datetime(ev.get("created_at")),
                "Sự kiện": ev.get("event_type", ""),
                "User ID": ev.get("user_id") or "—",
                "Username thử": ev.get("username_attempted") or "—",
                "Người thực hiện": ev.get("actor_user_id") or "—",
                "IP": ev.get("client_ip") or "—",
                "Chi tiết": detail_str,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_admin_panel(api_client: HttpApiClient, current_user: dict[str, Any]) -> None:
    """Render the 4-tab System Administration panel exclusively for quan_tri_he_thong."""
    st.header("🛡️ Quản trị Hệ thống & Phân quyền IAM")

    tab_users, tab_sessions, tab_sim, tab_events = st.tabs(
        [
            "👥 Người dùng",
            "🔐 Phiên đăng nhập",
            "⚙️ Dữ liệu Mô phỏng & Dự báo (`synth`)",
            "📜 Nhật ký Truy cập",
        ]
    )

    with tab_users:
        _render_users_tab(api_client, current_user)
    with tab_sessions:
        _render_sessions_tab(api_client)
    with tab_sim:
        _render_simulation_tab(api_client)
    with tab_events:
        _render_audit_events_tab(api_client)
