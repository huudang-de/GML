"""HTTP API Client for Streamlit UI v2.0 communicating with FastAPI /v1 endpoints.

Specifications:
- Consumes: /v1/chat, /v1/kpi/{key}, /v1/alerts, /v1/alerts/{id}/ack, /v1/feedback, /v1/history, /health
- Supports in-process MockTransport injection for unit testing with AppTest without opening TCP sockets.
"""

from typing import Any, Literal
import httpx

_DEFAULT_TEST_TRANSPORT: httpx.BaseTransport | None = None
_REQUIRE_LOGIN_FOR_TESTING: bool | None = None


class ApiClientError(httpx.HTTPError):
    """Exception raised by HttpApiClient when an API call fails."""

    def __init__(self, message: str = "", status_code: int | None = None, response: httpx.Response | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response

    @property
    def error_code(self) -> str | None:
        """Extract API error code from unified error envelope if available."""
        if self.response is None:
            return None
        try:
            data = self.response.json()
            if isinstance(data, dict) and isinstance(data.get("error"), dict):
                code = data["error"].get("code")
                return str(code) if code else None
        except Exception:
            pass
        return None

    @property
    def detail_message(self) -> str:
        """Extract user-facing Vietnamese error message from unified error envelope."""
        if self.response is not None:
            try:
                data = self.response.json()
                if isinstance(data, dict) and isinstance(data.get("error"), dict):
                    msg = data["error"].get("message")
                    if msg:
                        return str(msg)
            except Exception:
                pass
        return str(self)


def raise_if_unauthorized(exc: BaseException) -> None:
    """Re-raise 401 ApiClientError so top-level app can clear session and redirect to login."""
    if isinstance(exc, ApiClientError) and exc.status_code == 401:
        raise exc


def set_default_transport_for_testing(transport: httpx.BaseTransport | None) -> None:
    """Set process-wide mock transport for in-process testing."""
    global _DEFAULT_TEST_TRANSPORT
    _DEFAULT_TEST_TRANSPORT = transport


def get_default_transport_for_testing() -> httpx.BaseTransport | None:
    """Retrieve process-wide mock transport."""
    return _DEFAULT_TEST_TRANSPORT


def set_require_login_for_testing(enabled: bool | None) -> None:
    """Override login requirement during UI tests; None restores automatic detection."""
    global _REQUIRE_LOGIN_FOR_TESTING
    _REQUIRE_LOGIN_FOR_TESTING = enabled


def get_require_login_for_testing() -> bool:
    """Return True when login gate is active (always True in live app when no test transport is set)."""
    if _REQUIRE_LOGIN_FOR_TESTING is not None:
        return _REQUIRE_LOGIN_FOR_TESTING
    return _DEFAULT_TEST_TRANSPORT is None


class HttpApiClient:
    """Synchronous HTTP client for interacting with the AI Assistant FastAPI /v1 backend."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        token: str = "gml-dev-token-ceo",
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        chat_timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.chat_timeout = chat_timeout
        effective_transport = transport if transport is not None else _DEFAULT_TEST_TRANSPORT
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            transport=effective_transport,
            timeout=timeout,
        )

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        try:
            resp = self._client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise ApiClientError(
                "Hết thời gian chờ phản hồi từ Trợ lý AI. Vui lòng thử lại hoặc thu gọn câu hỏi.",
                status_code=504,
            ) from exc
        except httpx.HTTPError as exc:
            raise ApiClientError(f"HTTP error: {exc}") from exc
        return self._handle_response(resp)

    def _handle_response(self, resp: httpx.Response) -> Any:
        try:
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise ApiClientError(
                f"HTTP {exc.response.status_code}: {exc.response.text}",
                status_code=exc.response.status_code,
                response=exc.response,
            ) from exc
        except httpx.HTTPError as exc:
            raise ApiClientError(f"HTTP error: {exc}") from exc

    def chat(
        self,
        query: str,
        session_id: str | None = None,
        data_profile: str | None = None,
    ) -> dict[str, Any]:
        """Send a natural language query to POST /v1/chat."""
        payload: dict[str, Any] = {"query": query}
        if session_id:
            payload["session_id"] = session_id
        if data_profile:
            payload["data_profile"] = data_profile

        return self._request("POST", "/v1/chat", json=payload, timeout=self.chat_timeout)

    def get_overview(self, profile: str | None = None) -> dict[str, Any]:
        """Retrieve executive overview from GET /v1/overview."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        return self._request("GET", "/v1/overview", params=params)

    def get_kpi(
        self,
        kpi_key: str,
        profile: str | None = None,
        include_series: bool = False,
    ) -> dict[str, Any]:
        """Retrieve deterministic KPI value from GET /v1/kpi/{kpi_key}."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        if include_series:
            params["include"] = "series"
        return self._request("GET", f"/v1/kpi/{kpi_key}", params=params)

    def list_alerts(
        self,
        profile: str | None = None,
        domain: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        dedup: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve operational alerts from GET /v1/alerts."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        if domain:
            params["domain"] = domain
        if severity:
            params["severity"] = severity
        if status:
            params["status"] = status
        if dedup is False:
            params["dedup"] = "false"
        data = self._request("GET", "/v1/alerts", params=params)
        return data.get("alerts", [])

    def ack_alert(self, alert_id: int, profile: str | None = None) -> dict[str, Any]:
        """Acknowledge an alert via POST /v1/alerts/{alert_id}/ack."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        return self._request("POST", f"/v1/alerts/{alert_id}/ack", params=params)

    def list_actions(
        self,
        profile: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve operational action items from GET /v1/actions."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        if status:
            params["status"] = status
        data = self._request("GET", "/v1/actions", params=params)
        return data.get("actions", [])

    def create_action(self, payload: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
        """Create an action item via POST /v1/actions."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        return self._request("POST", "/v1/actions", json=payload, params=params)

    def update_action(
        self,
        action_id: int,
        payload: dict[str, Any],
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Update an action item via PATCH /v1/actions/{action_id}."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        return self._request("PATCH", f"/v1/actions/{action_id}", json=payload, params=params)

    def list_pins(self, profile: str | None = None) -> list[dict[str, Any]]:
        """Retrieve pinned KPIs from GET /v1/pins."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        data = self._request("GET", "/v1/pins", params=params)
        return data.get("pins", [])

    def add_pin(self, kpi_key: str, profile: str | None = None) -> dict[str, Any]:
        """Pin a KPI via POST /v1/pins."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        return self._request("POST", "/v1/pins", json={"kpi_key": kpi_key}, params=params)

    def remove_pin(self, kpi_key: str, profile: str | None = None) -> dict[str, Any]:
        """Unpin a KPI via DELETE /v1/pins/{kpi_key}."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        return self._request("DELETE", f"/v1/pins/{kpi_key}", params=params)

    def submit_feedback(
        self,
        request_id: str,
        rating: Literal["up", "down"],
        note: str = "",
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Submit user feedback via POST /v1/feedback."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        payload = {
            "request_id": request_id,
            "rating": rating,
            "comment": note,
        }
        return self._request("POST", "/v1/feedback", json=payload, params=params)

    def get_history(
        self,
        session_id: str | None = None,
        profile: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve conversational history from GET /v1/history."""
        params: dict[str, str] = {}
        if session_id:
            params["session_id"] = session_id
        if profile:
            params["profile"] = profile
        data = self._request("GET", "/v1/history", params=params)
        return data.get("turns", [])

    def clear_history(
        self,
        session_id: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        """Clear user conversation history via DELETE /v1/history."""
        params: dict[str, str] = {}
        if session_id:
            params["session_id"] = session_id
        if profile:
            params["profile"] = profile
        return self._request("DELETE", "/v1/history", params=params)

    def health(self) -> dict[str, Any]:
        """Check API gateway health via GET /health."""
        return self._request("GET", "/health")

    # ------------------------------------------------------------------
    # Authentication Endpoints (/v1/auth/*)
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate username/password via POST /v1/auth/login."""
        return self._request(
            "POST",
            "/v1/auth/login",
            json={"username": username, "password": password},
        )

    def logout(self) -> dict[str, Any]:
        """Revoke the current session via POST /v1/auth/logout."""
        return self._request("POST", "/v1/auth/logout")

    def get_me(self) -> dict[str, Any]:
        """Retrieve authenticated user identity via GET /v1/auth/me."""
        return self._request("GET", "/v1/auth/me")

    def change_password(self, current_password: str, new_password: str) -> dict[str, Any]:
        """Change current user password via POST /v1/auth/change-password."""
        return self._request(
            "POST",
            "/v1/auth/change-password",
            json={
                "current_password": current_password,
                "new_password": new_password,
            },
        )

    # ------------------------------------------------------------------
    # Admin & Simulation Endpoints (/v1/admin/*)
    # ------------------------------------------------------------------

    def admin_list_users(
        self,
        q: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        """List internal IAM accounts from GET /v1/admin/users."""
        params: dict[str, str] = {}
        if q:
            params["q"] = q
        if role:
            params["role"] = role
        if is_active is not None:
            params["is_active"] = "true" if is_active else "false"
        data = self._request("GET", "/v1/admin/users", params=params)
        return data.get("users", [])

    def admin_create_user(
        self,
        username: str,
        display_name: str,
        role: str,
        allowed_profiles: list[str] | None = None,
        email: str | None = None,
        password: str | None = None,
        must_change_password: bool = True,
    ) -> dict[str, Any]:
        """Create an IAM account via POST /v1/admin/users."""
        payload: dict[str, Any] = {
            "username": username,
            "display_name": display_name,
            "role": role,
            "must_change_password": must_change_password,
        }
        if allowed_profiles is not None:
            payload["allowed_profiles"] = allowed_profiles
        if email is not None:
            payload["email"] = email
        if password is not None:
            payload["password"] = password
        return self._request("POST", "/v1/admin/users", json=payload)

    def admin_update_user(
        self,
        user_id: str,
        payload: dict[str, Any] | None = None,
        *,
        display_name: str | None = None,
        email: str | None = None,
        role: str | None = None,
        allowed_profiles: list[str] | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Update an IAM user via PATCH /v1/admin/users/{user_id}."""
        body: dict[str, Any] = dict(payload) if payload is not None else {}
        if display_name is not None:
            body["display_name"] = display_name
        if email is not None:
            body["email"] = email
        if role is not None:
            body["role"] = role
        if allowed_profiles is not None:
            body["allowed_profiles"] = allowed_profiles
        if is_active is not None:
            body["is_active"] = is_active
        return self._request("PATCH", f"/v1/admin/users/{user_id}", json=body)

    def admin_reset_password(self, user_id: str) -> dict[str, Any]:
        """Generate a one-time temporary password via POST /v1/admin/users/{user_id}/reset-password."""
        return self._request("POST", f"/v1/admin/users/{user_id}/reset-password")

    def admin_unlock_user(self, user_id: str) -> dict[str, Any]:
        """Clear account login lockout via POST /v1/admin/users/{user_id}/unlock."""
        return self._request("POST", f"/v1/admin/users/{user_id}/unlock")

    def admin_revoke_user_sessions(self, user_id: str) -> dict[str, Any]:
        """Revoke all active sessions for a user via POST /v1/admin/users/{user_id}/revoke-sessions."""
        return self._request("POST", f"/v1/admin/users/{user_id}/revoke-sessions")

    def admin_list_sessions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """List active sessions from GET /v1/admin/sessions."""
        params: dict[str, str] = {}
        if user_id:
            params["user_id"] = user_id
        data = self._request("GET", "/v1/admin/sessions", params=params)
        return data.get("sessions", [])

    def admin_revoke_session(self, session_id: int) -> dict[str, Any]:
        """Revoke a specific session via DELETE /v1/admin/sessions/{session_id}."""
        return self._request("DELETE", f"/v1/admin/sessions/{int(session_id)}")

    def admin_list_auth_events(
        self,
        user_id: str | None = None,
        event_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List IAM audit events from GET /v1/admin/auth-events."""
        params: dict[str, Any] = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if event_type:
            params["event_type"] = event_type
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        data = self._request("GET", "/v1/admin/auth-events", params=params)
        return data.get("events", [])

    def admin_get_simulation_status(self) -> dict[str, Any]:
        """Get monthly synthetic/forecast simulation status via GET /v1/admin/simulation/status."""
        return self._request("GET", "/v1/admin/simulation/status")

    def admin_run_simulation(self, seed: int = 42) -> dict[str, Any]:
        """Trigger monthly simulation regeneration via POST /v1/admin/simulation/run."""
        return self._request(
            "POST",
            "/v1/admin/simulation/run",
            json={"seed": int(seed)},
            timeout=self.chat_timeout,
        )

    def close(self) -> None:
        """Close HTTP client connection."""
        self._client.close()

    def __enter__(self) -> "HttpApiClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
