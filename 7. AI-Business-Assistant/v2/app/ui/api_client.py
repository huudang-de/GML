"""HTTP API Client for Streamlit UI v2.0 communicating with FastAPI /v1 endpoints.

Specifications:
- Consumes: /v1/chat, /v1/kpi/{key}, /v1/alerts, /v1/alerts/{id}/ack, /v1/feedback, /v1/history, /health
- Supports in-process MockTransport injection for unit testing with AppTest without opening TCP sockets.
"""

from typing import Any, Literal
import httpx

_DEFAULT_TEST_TRANSPORT: httpx.BaseTransport | None = None


class ApiClientError(httpx.HTTPError):
    """Exception raised by HttpApiClient when an API call fails."""

    def __init__(self, message: str = "", status_code: int | None = None, response: httpx.Response | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


def set_default_transport_for_testing(transport: httpx.BaseTransport | None) -> None:
    """Set process-wide mock transport for in-process testing."""
    global _DEFAULT_TEST_TRANSPORT
    _DEFAULT_TEST_TRANSPORT = transport


def get_default_transport_for_testing() -> httpx.BaseTransport | None:
    """Retrieve process-wide mock transport."""
    return _DEFAULT_TEST_TRANSPORT


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

    def close(self) -> None:
        """Close HTTP client connection."""
        self._client.close()

    def __enter__(self) -> "HttpApiClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
