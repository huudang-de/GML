"""HTTP API Client for Streamlit UI v2.0 communicating with FastAPI /v1 endpoints.

Specifications:
- Consumes: /v1/chat, /v1/kpi/{key}, /v1/alerts, /v1/alerts/{id}/ack, /v1/feedback, /v1/history, /health
- Supports in-process MockTransport injection for unit testing with AppTest without opening TCP sockets.
"""

from typing import Any, Literal
import httpx

_DEFAULT_TEST_TRANSPORT: httpx.BaseTransport | None = None


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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
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

        resp = self._client.post("/v1/chat", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_kpi(self, kpi_key: str, profile: str | None = None) -> dict[str, Any]:
        """Retrieve deterministic KPI value from GET /v1/kpi/{kpi_key}."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        resp = self._client.get(f"/v1/kpi/{kpi_key}", params=params)
        resp.raise_for_status()
        return resp.json()

    def list_alerts(self, profile: str | None = None) -> list[dict[str, Any]]:
        """Retrieve active operational alerts from GET /v1/alerts."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        resp = self._client.get("/v1/alerts", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("alerts", [])

    def ack_alert(self, alert_id: int, profile: str | None = None) -> dict[str, Any]:
        """Acknowledge an alert via POST /v1/alerts/{alert_id}/ack."""
        params: dict[str, str] = {}
        if profile:
            params["profile"] = profile
        resp = self._client.post(f"/v1/alerts/{alert_id}/ack", params=params)
        resp.raise_for_status()
        return resp.json()

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
        resp = self._client.post("/v1/feedback", json=payload, params=params)
        resp.raise_for_status()
        return resp.json()

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
        resp = self._client.get("/v1/history", params=params)
        resp.raise_for_status()
        data = resp.json()
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
        resp = self._client.delete("/v1/history", params=params)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict[str, Any]:
        """Check API gateway health via GET /health."""
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        """Close HTTP client connection."""
        self._client.close()

    def __enter__(self) -> "HttpApiClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
