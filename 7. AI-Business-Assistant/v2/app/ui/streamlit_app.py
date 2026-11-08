"""Streamlit UI Application v2.0 for Gỗ Minh Long AI Assistant.

Specifications:
- Spec §5 T6, §11.7
- Modular screens: Chat View, Alert Center, History View
- Persistent Synthetic Data warning banner (§6.4)
- Power BI Quick Ask URL parameter pre-loading (?dashboard=...&kpi=...&profile=...&screen=...)
"""

import os
import uuid
import streamlit as st

from app.ui.api_client import HttpApiClient
from app.ui.components.alert_center import render_alert_center
from app.ui.components.chat_view import render_chat_view
from app.ui.components.history_view import render_history_view

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
    "💬 Hỏi đáp AI",
    "🔔 Trung tâm Cảnh báo",
    "📋 Lịch sử Hội thoại",
]

KPI_DISPLAY_NAMES = {
    "du_no_ngan_han": "Dư nợ ngắn hạn",
    "ty_le_su_dung_han_muc": "Tỷ lệ sử dụng hạn mức",
    "gia_tri_hang_ton_kho": "Giá trị hàng tồn kho",
    "doanh_thu_thuan": "Doanh thu thuần",
    "bien_loi_nhuan_gop": "Biên lợi nhuận gộp",
    "vong_quay_hang_ton_kho": "Vòng quay hàng tồn kho",
}

DASHBOARD_LABELS = {
    "tai_chinh": "Dashboard 1: Phân tích Tài chính & Dòng tiền",
    "ban_hang": "Dashboard 2: Doanh số & Khách hàng",
    "mua_hang": "Dashboard 3: Mua hàng & Nhà cung cấp",
    "kho": "Dashboard 4: Quản lý Kho & Tồn kho",
    "san_xuat": "Dashboard 5: Chi phí & Định mức Sản xuất",
}


def _resolve_screen_index(screen_param: str | None) -> int:
    """Map URL query screen param to navigation option index."""
    if not screen_param:
        return 0
    sp = screen_param.strip().lower()
    if sp in ("alerts", "alert", "canh_bao"):
        return 1
    if sp in ("history", "lich_su"):
        return 2
    return 0


def _resolve_profile_index(profile_param: str | None) -> int:
    """Map URL query profile param to selector index."""
    if not profile_param:
        return 0
    return 1 if profile_param.strip().lower() == "synth" else 0


def main() -> None:
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="Gỗ Minh Long AI Assistant",
        page_icon="🪵",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. Initialize session variables
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"sess-{uuid.uuid4().hex[:12]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 2. Extract query parameters
    qp = st.query_params
    query_profile = qp.get("profile")
    query_screen = qp.get("screen")
    query_dashboard = qp.get("dashboard")
    query_kpi = qp.get("kpi")
    autoload_last = qp.get("autoload_last")

    # 3. Sidebar Configuration
    with st.sidebar:
        st.title("🪵 Gỗ Minh Long AI Assistant v2.0")
        st.caption("Trợ lý Giám đốc & Phân tích Dữ liệu Doanh nghiệp")
        st.divider()

        role = st.selectbox(
            "👤 Vai trò người dùng",
            options=list(ROLE_TOKENS.keys()),
            format_func=lambda r: f"{ROLE_LABELS.get(r, r)} ({r})",
            index=0,
        )

        initial_profile_idx = _resolve_profile_index(query_profile)
        target_profile_val = "synth" if initial_profile_idx == 1 else "real"
        if query_profile and st.session_state.get("profile_selector") != target_profile_val:
            st.session_state["profile_selector"] = target_profile_val

        active_profile = st.radio(
            "🌐 Nguồn dữ liệu (Profile)",
            options=["real", "synth"],
            format_func=lambda p: "Dữ liệu Thực tế (Data Warehouse)" if p == "real" else "Dữ liệu Mô phỏng (Synthetic)",
            index=initial_profile_idx,
            key="profile_selector",
        )

        initial_screen_idx = _resolve_screen_index(query_screen)
        target_screen_option = SCREEN_OPTIONS[initial_screen_idx]
        if query_screen and st.session_state.get("screen_selector") != target_screen_option:
            st.session_state["screen_selector"] = target_screen_option

        active_screen = st.radio(
            "📌 Chức năng",
            options=SCREEN_OPTIONS,
            index=initial_screen_idx,
            key="screen_selector",
        )

        st.divider()

        # Power BI Quick Ask Presets (Sidebar Presets)
        with st.expander("⚡ Power BI Quick Ask Presets", expanded=False):
            st.caption("Các câu hỏi mẫu nhanh theo Dashboard Power BI:")
            for pbi_kpi, pbi_label in KPI_DISPLAY_NAMES.items():
                if st.button(f"📊 {pbi_label}", key=f"quick_ask_preset_{pbi_kpi}"):
                    st.session_state.preset_query = f"{pbi_label} hiện tại là bao nhiêu?"

        st.divider()
        if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
            st.session_state.session_id = f"sess-{uuid.uuid4().hex[:12]}"
            st.session_state.messages = []
            st.rerun()

    # 4. Instantiate API Client
    api_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    token = ROLE_TOKENS.get(role, "gml-dev-token-ceo")
    api_client = HttpApiClient(base_url=api_url, token=token)

    # 5. Persistent Synthetic Data Warning Banner (TC-T6-02)
    # Renders if profile is synth or if any message contains SYNTHETIC_DATA warning
    has_synth_warning = any(
        "SYNTHETIC_DATA" in (msg.get("warnings") or [])
        for msg in st.session_state.messages
    )
    if active_profile == "synth" or has_synth_warning:
        st.warning(
            "⚠️ DỮ LIỆU MÔ PHỎNG (SYNTHETIC DATA) — Chỉ dùng cho kiểm thử & phân tích kịch bản, không dùng cho quyết định tài chính thực tế."
        )

    # 6. Power BI Quick Ask Pre-loaded Context Banner
    if query_dashboard or query_kpi:
        kpi_name = KPI_DISPLAY_NAMES.get(query_kpi or "", query_kpi or "Chỉ số được chọn")
        dash_name = DASHBOARD_LABELS.get(query_dashboard or "", query_dashboard or "Power BI")
        st.info(
            f"⚡ **Power BI Quick Ask**: Ngữ cảnh được nạp từ **{dash_name}** cho chỉ số **{kpi_name}**."
        )
        col_qa1, _ = st.columns([2, 5])
        with col_qa1:
            if st.button(f"Hỏi nhanh: {kpi_name}", key="pbi_quick_ask_btn"):
                st.session_state.preset_query = f"{kpi_name} hiện tại là bao nhiêu?"

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
                    "warnings": demo_resp.get("warnings", []),
                },
            ]
            st.session_state["_last_loaded_profile"] = active_profile
        except Exception:
            pass

    # 8. Render Selected Screen
    if active_screen == "💬 Hỏi đáp AI":
        render_chat_view(api_client=api_client, profile=active_profile)
    elif active_screen == "🔔 Trung tâm Cảnh báo":
        render_alert_center(api_client=api_client, profile=active_profile)
    elif active_screen == "📋 Lịch sử Hội thoại":
        render_history_view(api_client=api_client, profile=active_profile)


if __name__ == "__main__":
    main()
