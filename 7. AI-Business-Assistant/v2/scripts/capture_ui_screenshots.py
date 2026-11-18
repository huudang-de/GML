"""Capture UI screenshots for EV-16 Gate Evidence using headless Edge/Chrome.

Generates 9 high-resolution PNG screen captures (> 15 KB each):
- 01_chat_real.png (?screen=chat&profile=real&autoload_last=1)
- 02_chat_synth.png (?screen=chat&profile=synth&autoload_last=1)
- 03_alert_center.png (?screen=alerts&profile=real)
- 04_history.png (?screen=history&profile=real)
- 05_overview.png (?screen=overview&profile=synth)
- 06_alert_detail.png (?screen=alerts&profile=real -> click [AL-002])
- 07_actions.png (?screen=actions&profile=real)
- 08_login.png (unauthenticated login gate)
- 09_admin_panel.png (4-tab IAM & Simulation Admin Panel as quan_tri_he_thong)
"""

import asyncio
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import sqlalchemy as sa
import websockets

V2_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_DIR))

from app.memory.session_store import SessionStore
from app.agents.series_tools import build_alert_evidence
from app.agents.trend_agent import analyze_kpi_trend
from app.services.iam_service import create_session, revoke_session, seed_default_demo_users
from db.apply_db import get_admin_engine, get_app_engine, get_iam_engine, get_ro_engine

SCREENSHOTS_DIR = V2_DIR / "eval" / "reports" / "ui_screens"


def find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_browser_executable() -> str:
    """Detect available headless Chromium browser (Edge or Chrome)."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    which_edge = shutil.which("msedge")
    if which_edge:
        return which_edge
    which_chrome = shutil.which("chrome")
    if which_chrome:
        return which_chrome
    raise RuntimeError("No headless Chromium browser (Edge or Chrome) found on system.")


def seed_demo_database_state() -> list[str]:
    """Seed representative operational alerts, actions, and history turns into PostgreSQL.

    Returns the list of temporary IAM demo user_ids newly created by this run so
    they can be cleaned up in ``finally`` without leaving stale admin rows.
    """
    print("Seeding demo database state...")
    engine_real = get_app_engine(profile="real")
    engine_synth = get_app_engine(profile="synth")
    ro_synth = get_ro_engine(profile="synth")

    # 1. Build real series analysis on synth
    trend_1 = analyze_kpi_trend("ty_le_su_dung_han_muc", role="ceo", data_profile="synth", engine=ro_synth)[0]
    ev_1 = build_alert_evidence("ty_le_su_dung_han_muc", "critical", 0.885, trend_1).model_dump(mode="json")

    trend_2 = analyze_kpi_trend("du_no_ngan_han", role="ceo", data_profile="synth", engine=ro_synth)[0]
    ev_2 = build_alert_evidence("du_no_ngan_han", "warning", 236065233815.0, trend_2).model_dump(mode="json")

    trend_3 = analyze_kpi_trend("gia_tri_hang_ton_kho", role="ceo", data_profile="synth", engine=ro_synth)[0]
    ev_3 = build_alert_evidence("gia_tri_hang_ton_kho", "warning", 120000000000.0, trend_3).model_dump(mode="json")

    # 2. Seed alerts into both real and synth databases for consistent UI testing
    real_alert_ids: dict[str, int] = {}
    for idx, eng in enumerate((engine_real, engine_synth)):
        with eng.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id IN ('AL-001', 'AL-002', 'AL-003')"))
            rows = conn.execute(
                sa.text("""
                    INSERT INTO app.alert_event (
                        rule_id, kpi_key, severity, message, value, threshold,
                        is_acknowledged, acknowledged_by, acknowledged_at, created_at,
                        period, dedup_key, evidence
                    )
                    VALUES
                    (
                        'AL-001', 'ty_le_su_dung_han_muc', 'critical',
                        'Tỷ lệ sử dụng hạn mức vượt ngưỡng an toàn (88.5% > 85%)',
                        0.885, 0.85, false, null, null, now() - interval '2 hours',
                        '2026-07', 'AL-001:ty_le_su_dung_han_muc:2026-07:critical',
                        CAST(:ev_1 AS jsonb)
                    ),
                    (
                        'AL-002', 'du_no_ngan_han', 'warning',
                        'Dư nợ ngắn hạn đạt đỉnh chu kỳ tích trữ nguyên liệu Q3',
                        236065233815, 200000000000, false, null, null, now() - interval '1 hour',
                        '2026-07', 'AL-002:du_no_ngan_han:2026-07:warning',
                        CAST(:ev_2 AS jsonb)
                    ),
                    (
                        'AL-003', 'gia_tri_hang_ton_kho', 'warning',
                        'Tồn kho melamine tăng cao so với kế hoạch',
                        120000000000, 100000000000, true, 'usr_ceo', now() - interval '10 minutes', now() - interval '3 hours',
                        '2026-07', 'AL-003:gia_tri_hang_ton_kho:2026-07:warning',
                        CAST(:ev_3 AS jsonb)
                    )
                    RETURNING id, rule_id;
                """),
                {"ev_1": json.dumps(ev_1), "ev_2": json.dumps(ev_2), "ev_3": json.dumps(ev_3)},
            ).fetchall()
            if idx == 0:
                real_alert_ids = {r.rule_id: int(r.id) for r in rows}

    # 3. Seed demo actions in app.action_item using valid numeric alert_event.id source_ref values
    with engine_real.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.action_item WHERE title LIKE 'Kích hoạt phương án%' OR title LIKE 'Tạm dừng giải ngân%'"))
        conn.execute(
            sa.text("""
                INSERT INTO app.action_item (
                    title, kpi_key, level, source_type, source_ref,
                    assigned_role, status, due_date, note, created_by, created_at
                )
                VALUES
                (
                    'Kích hoạt phương án khẩn cấp: ngừng toàn bộ các khoản giải ngân mới chưa cấp thiết.',
                    'ty_le_su_dung_han_muc', 'nghiem_trong', 'alert', :ref_1,
                    'ceo', 'open', '2026-08-15', 'CEO phê duyệt khẩn cấp', 'usr_ceo', now() - interval '1 hour'
                ),
                (
                    'Tạm dừng giải ngân mới từ các ngân hàng có tỷ lệ sử dụng trên 80%.',
                    'ty_le_su_dung_han_muc', 'canh_bao', 'alert', :ref_2,
                    'ke_toan_truong', 'in_progress', '2026-08-20', 'KTT đang làm việc với các ngân hàng', 'usr_ceo', now() - interval '30 minutes'
                );
            """),
            {"ref_1": str(real_alert_ids["AL-001"]), "ref_2": str(real_alert_ids["AL-002"])},
        )

    # 4. Seed demo pinned KPI in synth
    with engine_synth.begin() as conn:
        conn.execute(sa.text("DELETE FROM app.pinned_kpi WHERE user_id = 'usr_ceo' AND data_profile = 'synth'"))
        conn.execute(
            sa.text("""
                INSERT INTO app.pinned_kpi (user_id, data_profile, kpi_key, position)
                VALUES ('usr_ceo', 'synth', 'gia_tri_phai_tra', 1);
            """)
        )

    # 5. Seed history in app.chat_turn
    store = SessionStore(engine=engine_real, data_profile="real")
    demo_session = "sess-demo-history-ev16"
    store.add_turn(
        session_id=demo_session,
        user_id="usr_ceo",
        query="Dư nợ ngắn hạn hiện tại là bao nhiêu?",
        standalone_query="Dư nợ ngắn hạn hiện tại là bao nhiêu?",
        intent="sql_only",
        answer={"summary": "Theo số liệu từ hệ thống, Dư nợ ngắn hạn: 236.065.233.815 VNĐ (xấp xỉ 236,07 tỷ VNĐ)."},
        confidence=0.94,
        request_id="req-demo-001",
    )
    store.add_turn(
        session_id=demo_session,
        user_id="usr_ceo",
        query="Tỷ lệ sử dụng hạn mức vay các ngân hàng?",
        standalone_query="Tỷ lệ sử dụng hạn mức vay các ngân hàng?",
        intent="sql_only",
        answer={"summary": "Tỷ lệ sử dụng hạn mức đạt 88.5%, đang vượt ngưỡng cảnh báo 85%."},
        confidence=0.92,
        request_id="req-demo-002",
    )
    store.add_turn(
        session_id=demo_session,
        user_id="usr_ceo",
        query="Tồn kho melamine tháng 7 ra sao?",
        standalone_query="Tồn kho melamine tháng 7 ra sao?",
        intent="kpi_query",
        answer={"summary": "Tổng giá trị tồn kho melamine đạt 120 tỷ VNĐ, vượt ngưỡng an toàn kế hoạch."},
        confidence=0.89,
        request_id="req-demo-003",
    )

    # 6. Seed deterministic IAM demo users (usr_ceo, usr_ktt, usr_kho, usr_admin)
    iam_eng = get_iam_engine()
    demo_ids = ("usr_ceo", "usr_ktt", "usr_kho", "usr_admin")
    with iam_eng.connect() as conn:
        pre_existing = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT user_id FROM iam.app_user WHERE user_id = ANY(:ids)"),
                {"ids": list(demo_ids)},
            ).fetchall()
        }
    seed_default_demo_users(iam_eng)
    created_demo_ids = [uid for uid in demo_ids if uid not in pre_existing]
    print("Demo database state seeded successfully.")
    return created_demo_ids


def _obtain_session_token(
    api_port: int,
    username: str,
    user_id: str,
    password: str = "DemoPass@2026",
) -> str:
    """Obtain a live DB-backed session token via /v1/auth/login (with create_session fallback)."""
    login_url = f"http://127.0.0.1:{api_port}/v1/auth/login"
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        login_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("access_token"):
                return str(data["access_token"])
    except Exception:
        pass
    tok, _ = create_session(
        get_iam_engine(),
        user_id=user_id,
        client_ip="127.0.0.1",
        user_agent="ev16-capture-script",
    )
    return tok


def wait_for_http_ready(url: str, timeout_sec: float = 30.0, label: str = "Service") -> None:
    """Poll URL until 200 OK or timeout."""
    start_time = time.time()
    print(f"Waiting for {label} at {url}...")
    while time.time() - start_time < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "healthcheck"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    print(f"  {label} ready in {time.time() - start_time:.2f}s.")
                    return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"{label} at {url} did not become ready within {timeout_sec}s.")


async def _cdp_call(ws, msg_id: int, method: str, params: dict | None = None) -> dict:
    """Send a CDP command and await the matching response id."""
    payload = {"id": msg_id, "method": method}
    if params is not None:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        raw_res = await ws.recv()
        res = json.loads(raw_res)
        if res.get("id") == msg_id:
            if "error" in res:
                raise RuntimeError(f"CDP {method} failed: {res['error']}")
            return res.get("result", {})


async def _wait_streamlit_idle_and_text(
    ws,
    msg_id_counter: list[int],
    expected_texts: list[str],
    timeout_sec: float = 45.0,
) -> None:
    """Poll CDP DOM until Streamlit is idle (no running indicator/skeleton/spinner) and expected texts appear."""
    expected_js = json.dumps(expected_texts)
    js_expr = f"""
    (() => {{
        if (document.readyState !== 'complete') return {{ ready: false, reason: 'doc_loading' }};
        const status = document.querySelector('[data-testid="stStatusWidget"]');
        if (status) {{
            const txt = (status.innerText || '').trim();
            if (/stop|running/i.test(txt) || status.querySelector('button')) {{
                return {{ ready: false, reason: 'streamlit_running' }};
            }}
        }}
        if (document.querySelectorAll('[data-testid="stSkeleton"]').length > 0) {{
            return {{ ready: false, reason: 'skeletons' }};
        }}
        if (document.querySelectorAll('[data-testid="stSpinner"]').length > 0) {{
            return {{ ready: false, reason: 'spinners' }};
        }}
        const bodyText = document.body ? (document.body.innerText || '') : '';
        if (!bodyText.trim()) return {{ ready: false, reason: 'empty_body' }};
        for (const s of {expected_js}) {{
            if (!bodyText.includes(s)) return {{ ready: false, reason: 'missing:' + s }};
        }}
        return {{ ready: true }};
    }})()
    """
    start = time.time()
    last_reason = "init"
    while time.time() - start < timeout_sec:
        msg_id_counter[0] += 1
        res = await _cdp_call(
            ws,
            msg_id_counter[0],
            "Runtime.evaluate",
            {"expression": js_expr, "returnByValue": True},
        )
        val = (res.get("result") or {}).get("value") or {}
        if val.get("ready"):
            return
        last_reason = val.get("reason", "unknown")
        await asyncio.sleep(0.4)
    raise TimeoutError(f"Streamlit UI did not settle within {timeout_sec}s (last reason: {last_reason})")


async def capture_url_cdp(
    browser_exe: str,
    url: str,
    out_file: Path,
    expected_texts: list[str],
    click_button_text: str | None = None,
    post_click_texts: list[str] | None = None,
    session_token: str | None = None,
    timeout_sec: float = 45.0,
) -> None:
    """Capture pixel-perfect screenshot via Chrome DevTools Protocol after Streamlit completes rendering."""
    cdp_port = find_free_port()
    user_data_dir = tempfile.mkdtemp(prefix="headless_browser_")
    browser_cmd = [
        browser_exe,
        "--headless=new",
        "--disable-extensions",
        f"--remote-debugging-port={cdp_port}",
        f"--user-data-dir={user_data_dir}",
        "--window-size=1440,960",
        "--hide-scrollbars",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "about:blank",
    ]
    proc = subprocess.Popen(browser_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # Wait for CDP endpoint
        start = time.time()
        ws_url = None
        while time.time() - start < 15.0:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json", timeout=1.0) as r:
                    tabs = json.loads(r.read())
                    for t in tabs:
                        if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                            ws_url = t["webSocketDebuggerUrl"]
                            break
                    if ws_url:
                        break
            except Exception:
                await asyncio.sleep(0.3)

        if not ws_url:
            raise RuntimeError(f"Could not connect to CDP at port {cdp_port}")

        async with websockets.connect(ws_url, max_size=25 * 1024 * 1024) as ws:
            msg_id = [0]
            for domain_cmd in ("Runtime.enable", "Page.enable", "Network.enable"):
                msg_id[0] += 1
                await _cdp_call(ws, msg_id[0], domain_cmd)

            if session_token:
                msg_id[0] += 1
                await _cdp_call(
                    ws,
                    msg_id[0],
                    "Network.setCookie",
                    {
                        "name": "gml_session",
                        "value": session_token,
                        "url": url,
                        "path": "/",
                        "sameSite": "Lax",
                    },
                )

            msg_id[0] += 1
            await _cdp_call(ws, msg_id[0], "Page.navigate", {"url": url})

            await _wait_streamlit_idle_and_text(ws, msg_id, expected_texts, timeout_sec=timeout_sec)

            if click_button_text:
                btn_js = json.dumps(click_button_text)
                click_expr = f"""
                (() => {{
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const target = buttons.find(b => (b.innerText || '').includes({btn_js}));
                    if (!target) return false;
                    target.click();
                    return true;
                }})()
                """
                msg_id[0] += 1
                click_res = await _cdp_call(
                    ws,
                    msg_id[0],
                    "Runtime.evaluate",
                    {"expression": click_expr, "returnByValue": True},
                )
                clicked = (click_res.get("result") or {}).get("value")
                if not clicked:
                    raise RuntimeError(f"Could not find button containing {click_button_text!r} on {url}")
                await asyncio.sleep(0.5)
                await _wait_streamlit_idle_and_text(
                    ws,
                    msg_id,
                    post_click_texts or expected_texts,
                    timeout_sec=timeout_sec,
                )

            # Scroll main viewport to top so header, banners, and primary content are visible
            msg_id[0] += 1
            await _cdp_call(
                ws,
                msg_id[0],
                "Runtime.evaluate",
                {
                    "expression": """
                    (() => {
                        window.scrollTo(0, 0);
                        document.querySelectorAll('[data-testid="stMain"], [data-testid="stAppViewContainer"], section.main').forEach(el => {
                            el.scrollTop = 0;
                        });
                    })()
                    """,
                    "returnByValue": True,
                },
            )

            # Brief layout/chart paint settle pause, then re-verify idle before capturing
            await asyncio.sleep(1.5)
            await _wait_streamlit_idle_and_text(
                ws,
                msg_id,
                post_click_texts if (click_button_text and post_click_texts) else expected_texts,
                timeout_sec=10.0,
            )

            msg_id[0] += 1
            shot = await _cdp_call(ws, msg_id[0], "Page.captureScreenshot", {"format": "png"})
            img_data = base64.b64decode(shot["data"])
            with open(out_file, "wb") as f:
                f.write(img_data)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)


def capture_screens() -> None:
    """Launch services, capture 9 UI screenshots (including login & admin), and verify file sizes."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    browser_exe = get_browser_executable()
    print(f"Using browser: {browser_exe}")

    created_demo_ids = seed_demo_database_state()

    api_port = find_free_port()
    st_port = find_free_port()
    while st_port == api_port:
        st_port = find_free_port()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(V2_DIR)
    env["API_BASE_URL"] = f"http://127.0.0.1:{api_port}"
    env["LLM_PROVIDER"] = "heuristic"
    env["GOOGLE_API_KEY"] = "mock_offline"
    env["REQUIRE_LOGIN_FOR_TESTING"] = "1"

    api_proc: subprocess.Popen | None = None
    st_proc: subprocess.Popen | None = None
    issued_tokens: list[str] = []

    try:
        # 1. Start FastAPI backend
        print(f"Starting FastAPI on port {api_port}...")
        api_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
            "--log-level",
            "warning",
        ]
        api_proc = subprocess.Popen(api_cmd, cwd=str(V2_DIR), env=env)
        wait_for_http_ready(f"http://127.0.0.1:{api_port}/health", timeout_sec=45.0, label="FastAPI")

        # Obtain live DB-backed session tokens via /v1/auth/login
        ceo_token = _obtain_session_token(api_port, username="demo.ceo", user_id="usr_ceo")
        admin_token = _obtain_session_token(api_port, username="demo.admin", user_id="usr_admin")
        issued_tokens.extend([ceo_token, admin_token])

        # 2. Start Streamlit frontend
        print(f"Starting Streamlit on port {st_port}...")
        st_cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/ui/streamlit_app.py",
            "--server.headless",
            "true",
            "--server.port",
            str(st_port),
            "--browser.gatherUsageStats",
            "false",
        ]
        st_proc = subprocess.Popen(st_cmd, cwd=str(V2_DIR), env=env)
        wait_for_http_ready(f"http://127.0.0.1:{st_port}/_stcore/health", timeout_sec=30.0, label="Streamlit")

        # 3. Capture all 9 target screens (EV-16)
        targets = [
            (
                "08_login.png",
                f"http://127.0.0.1:{st_port}/",
                [
                    "GỖ MINH LONG · TRỢ LÝ ĐIỀU HÀNH AI",
                    "Đăng nhập hệ thống quản trị",
                    "Tên đăng nhập",
                    "Mật khẩu",
                    "Đăng nhập",
                ],
                None,
                None,
                None,
            ),
            (
                "01_chat_real.png",
                f"http://127.0.0.1:{st_port}/?screen=chat&profile=real&autoload_last=1",
                ["Trợ lý Hỏi đáp Nghiệp vụ AI", "Dư nợ ngắn hạn", "Request ID"],
                None,
                None,
                ceo_token,
            ),
            (
                "02_chat_synth.png",
                f"http://127.0.0.1:{st_port}/?screen=chat&profile=synth&autoload_last=1",
                ["DỮ LIỆU MÔ PHỎNG", "Trợ lý Hỏi đáp Nghiệp vụ AI", "Dư nợ ngắn hạn", "Request ID"],
                None,
                None,
                ceo_token,
            ),
            (
                "03_alert_center.png",
                f"http://127.0.0.1:{st_port}/?screen=alerts&profile=real",
                ["Trung tâm Cảnh báo Nghiệp vụ", "[AL-001]", "Hành động đề xuất đã phê duyệt", "Giá trị ghi nhận"],
                None,
                None,
                ceo_token,
            ),
            (
                "04_history.png",
                f"http://127.0.0.1:{st_port}/?screen=history&profile=real",
                ["Lịch sử Hội thoại", "Tổng số lượt hỏi đáp đã lưu"],
                None,
                None,
                ceo_token,
            ),
            (
                "05_overview.png",
                f"http://127.0.0.1:{st_port}/?screen=overview&profile=synth",
                [
                    "DỮ LIỆU MÔ PHỎNG",
                    "Tổng hợp điều hành",
                    "Chỉ số trọng yếu",
                    "Xu hướng & Biến động theo kỳ",
                    "Phát hiện hôm nay",
                    "Câu hỏi gợi ý",
                ],
                None,
                None,
                ceo_token,
            ),
            (
                "06_alert_detail.png",
                f"http://127.0.0.1:{st_port}/?screen=alerts&profile=real",
                ["Trung tâm Cảnh báo Nghiệp vụ", "[AL-001]", "[AL-002]"],
                "[AL-002]",
                ["[AL-002] Dư nợ ngắn hạn đạt đỉnh", "236,07 tỷ", "Diễn biến chuỗi thời gian"],
                ceo_token,
            ),
            (
                "07_actions.png",
                f"http://127.0.0.1:{st_port}/?screen=actions&profile=real",
                ["Quản lý Hành động Nghiệp vụ", "Tổng số hành động ghi nhận", "Kích hoạt phương án khẩn cấp"],
                None,
                None,
                ceo_token,
            ),
            (
                "09_admin_panel.png",
                f"http://127.0.0.1:{st_port}/",
                [
                    "Quản trị Hệ thống & Phân quyền IAM",
                    "Quản lý Tài khoản Người dùng",
                    "Chi tiết & Thao tác tài khoản",
                    "Phiên đăng nhập",
                    "Nhật ký Truy cập",
                ],
                None,
                None,
                admin_token,
            ),
        ]

        for filename, url, expected_texts, click_btn, post_click_texts, sess_tok in targets:
            out_file = SCREENSHOTS_DIR / filename
            if out_file.exists():
                out_file.unlink()

            print(f"Capturing {filename} from {url}...", flush=True)
            asyncio.run(
                capture_url_cdp(
                    browser_exe,
                    url,
                    out_file,
                    expected_texts=expected_texts,
                    click_button_text=click_btn,
                    post_click_texts=post_click_texts,
                    session_token=sess_tok,
                )
            )

            if not out_file.exists():
                raise FileNotFoundError(f"Failed to generate screenshot: {out_file}")

            size_bytes = out_file.stat().st_size
            size_kb = size_bytes / 1024.0
            print(f"  Saved {filename}: {size_kb:.1f} KB", flush=True)

            if size_kb < 15.0:
                raise ValueError(f"Screenshot {filename} too small ({size_kb:.1f} KB), expected > 15 KB")

        print(f"\nAll {len(targets)} EV-16 UI screenshots captured and verified successfully!")

    finally:
        if issued_tokens:
            try:
                iam_eng = get_iam_engine()
                for tok in issued_tokens:
                    revoke_session(iam_eng, raw_token=tok, reason="capture_cleanup")
            except Exception as exc:
                print(f"Warning: failed to revoke capture sessions: {exc}")
        if created_demo_ids:
            try:
                admin_eng = get_admin_engine(profile="real")
                with admin_eng.begin() as conn:
                    conn.execute(
                        sa.text("DELETE FROM iam.user_session WHERE user_id = ANY(:ids)"),
                        {"ids": created_demo_ids},
                    )
                    conn.execute(
                        sa.text(
                            "DELETE FROM iam.auth_event WHERE user_id = ANY(:ids) "
                            "OR actor_user_id = ANY(:ids)"
                        ),
                        {"ids": created_demo_ids},
                    )
                    conn.execute(
                        sa.text("DELETE FROM iam.app_user WHERE user_id = ANY(:ids)"),
                        {"ids": created_demo_ids},
                    )
            except Exception as exc:
                print(f"Warning: failed to clean up temporary demo users: {exc}")
        print("Cleaning up background processes...")
        for proc, name in [(st_proc, "Streamlit"), (api_proc, "FastAPI")]:
            if proc and proc.poll() is None:
                print(f"Terminating {name} (PID: {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    print(f"Killing {name} (PID: {proc.pid})...")
                    proc.kill()


if __name__ == "__main__":
    capture_screens()
