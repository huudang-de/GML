"""Capture UI screenshots for EV-16 Gate Evidence using headless Edge/Chrome.

Generates 4 high-resolution PNG screen captures (> 15 KB each):
- 01_chat_real.png (?screen=chat&profile=real&autoload_last=1)
- 02_chat_synth.png (?screen=chat&profile=synth&autoload_last=1)
- 03_alert_center.png (?screen=alerts&profile=real)
- 04_history.png (?screen=history&profile=real)
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
from db.apply_db import get_app_engine, get_ro_engine

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


def seed_demo_database_state() -> None:
    """Seed representative operational alerts, actions, and history turns into PostgreSQL."""
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
    for eng in (engine_real, engine_synth):
        with eng.begin() as conn:
            conn.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id IN ('AL-001', 'AL-002', 'AL-003')"))
            conn.execute(
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
                    );
                """),
                {"ev_1": json.dumps(ev_1), "ev_2": json.dumps(ev_2), "ev_3": json.dumps(ev_3)},
            )

    # 3. Seed demo actions in app.action_item
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
                    'ty_le_su_dung_han_muc', 'nghiem_trong', 'alert', 'AL-001',
                    'ceo', 'open', '2026-08-15', 'CEO phê duyệt khẩn cấp', 'usr_ceo', now() - interval '1 hour'
                ),
                (
                    'Tạm dừng giải ngân mới từ các ngân hàng có tỷ lệ sử dụng trên 80%.',
                    'ty_le_su_dung_han_muc', 'canh_bao', 'alert', 'AL-002',
                    'ke_toan_truong', 'in_progress', '2026-08-20', 'KTT đang làm việc với các ngân hàng', 'usr_ceo', now() - interval '30 minutes'
                );
            """)
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
    print("Demo database state seeded successfully.")


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


async def capture_url_cdp(browser_exe: str, url: str, out_file: Path, wait_sec: float = 6.0) -> None:
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
        url,
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
            # Allow Streamlit websocket communication and DOM rendering to finish
            await asyncio.sleep(wait_sec)
            await ws.send(json.dumps({"id": 1, "method": "Page.captureScreenshot"}))
            while True:
                raw_res = await ws.recv()
                res = json.loads(raw_res)
                if res.get("id") == 1 and "result" in res:
                    img_data = base64.b64decode(res["result"]["data"])
                    with open(out_file, "wb") as f:
                        f.write(img_data)
                    break
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)


def capture_screens() -> None:
    """Launch services, capture 7 UI screenshots, and verify file sizes."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    browser_exe = get_browser_executable()
    print(f"Using browser: {browser_exe}")

    seed_demo_database_state()

    api_port = find_free_port()
    st_port = find_free_port()
    while st_port == api_port:
        st_port = find_free_port()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(V2_DIR)
    env["API_BASE_URL"] = f"http://127.0.0.1:{api_port}"
    env["LLM_PROVIDER"] = "heuristic"
    env["GOOGLE_API_KEY"] = "mock_offline"

    api_proc: subprocess.Popen | None = None
    st_proc: subprocess.Popen | None = None

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
        wait_for_http_ready(f"http://127.0.0.1:{api_port}/health", timeout_sec=25.0, label="FastAPI")

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

        # 3. Capture the 7 target screens (EV-16)
        targets = [
            ("01_chat_real.png", f"http://127.0.0.1:{st_port}/?screen=chat&profile=real&autoload_last=1", 5.0),
            ("02_chat_synth.png", f"http://127.0.0.1:{st_port}/?screen=chat&profile=synth&autoload_last=1", 5.0),
            ("03_alert_center.png", f"http://127.0.0.1:{st_port}/?screen=alerts&profile=real", 4.0),
            ("04_history.png", f"http://127.0.0.1:{st_port}/?screen=history&profile=real", 4.0),
            ("05_overview.png", f"http://127.0.0.1:{st_port}/?screen=overview&profile=synth", 5.0),
            ("06_alert_detail.png", f"http://127.0.0.1:{st_port}/?screen=alerts&profile=real", 4.0),
            ("07_actions.png", f"http://127.0.0.1:{st_port}/?screen=actions&profile=real", 4.0),
        ]

        for filename, url, wait_time in targets:
            out_file = SCREENSHOTS_DIR / filename
            if out_file.exists():
                out_file.unlink()

            print(f"Capturing {filename} from {url}...", flush=True)
            asyncio.run(capture_url_cdp(browser_exe, url, out_file, wait_sec=wait_time))

            if not out_file.exists():
                raise FileNotFoundError(f"Failed to generate screenshot: {out_file}")

            size_bytes = out_file.stat().st_size
            size_kb = size_bytes / 1024.0
            print(f"  Saved {filename}: {size_kb:.1f} KB", flush=True)

            if size_kb < 15.0:
                raise ValueError(f"Screenshot {filename} too small ({size_kb:.1f} KB), expected > 15 KB")

        print(f"\nAll {len(targets)} EV-16 UI screenshots captured and verified successfully!")

    finally:
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
