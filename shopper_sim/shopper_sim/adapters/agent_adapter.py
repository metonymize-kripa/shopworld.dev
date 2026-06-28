"""Agent adapter -- conversational merchant transport.

Speaks to a merchant's chat endpoint / API / MCP server. This is a transport
shell: it implements the ``MerchantAdapter`` protocol by POSTing the shopper
utterance and parsing the reply into a ``MerchantTurn``. The dialogue policy
and turn classifier are transport-agnostic and unchanged.

Network calls use ``httpx`` and are intentionally the ONLY non-deterministic
part of a run (the merchant under test). Everything on the shopper side stays
seeded. ``httpx`` is imported lazily so the engine and offline tests have no
hard dependency on it.
"""

from __future__ import annotations

from typing import Any, Callable

from .base import MerchantAdapter, MerchantTurn


class HTTPAgentAdapter(MerchantAdapter):
    """Drives an HTTP chat endpoint.

    The endpoint contract is configurable via ``request_builder`` and
    ``response_parser`` so any merchant API shape can be adapted without
    touching the policy.
    """

    def __init__(
        self,
        endpoint: str,
        request_builder: Callable[[str, str], dict] | None = None,
        response_parser: Callable[[dict], MerchantTurn] | None = None,
        headers: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._endpoint = endpoint
        self._headers = headers or {}
        self._timeout = timeout_s
        self._session_id: str | None = None
        self._history: list[dict[str, str]] = []
        self._request_builder = request_builder or self._default_request
        self._response_parser = response_parser or self._default_parser
        self._client = None  # lazily created httpx.Client

    def open_session(self, scenario_id: str, seed: int) -> None:
        import httpx  # lazy

        self._session_id = f"{scenario_id}:{seed}"
        self._history = []
        self._client = httpx.Client(timeout=self._timeout, headers=self._headers)

    def send(self, utterance: str) -> MerchantTurn:
        if self._client is None:
            raise RuntimeError("session not open")
        self._history.append({"role": "user", "content": utterance})
        payload = self._request_builder(utterance, self._session_id or "")
        payload["history"] = list(self._history)
        resp = self._client.post(self._endpoint, json=payload)
        resp.raise_for_status()
        data = resp.json()
        turn = self._response_parser(data)
        self._history.append({"role": "assistant", "content": turn.text})
        return turn

    def close_session(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # -- default contract --------------------------------------------------

    @staticmethod
    def _default_request(utterance: str, session_id: str) -> dict[str, Any]:
        return {"message": utterance, "session_id": session_id}

    @staticmethod
    def _default_parser(data: dict) -> MerchantTurn:
        text = data.get("reply") or data.get("message") or data.get("text") or ""
        return MerchantTurn(
            text=str(text),
            has_question="?" in str(text),
            has_action_button=bool(data.get("actions")),
            fields=dict(data.get("fields", {})),
            raw=data,
        )


class MCPAgentAdapter(MerchantAdapter):
    """Drives a merchant exposed as an MCP server.

    Shell only -- a real implementation would speak the MCP protocol over the
    configured transport. Method bodies raise so callers fail loudly until the
    MCP client is wired up.
    """

    def __init__(self, server_url: str, tool_name: str = "chat") -> None:
        self._server_url = server_url
        self._tool_name = tool_name

    def open_session(self, scenario_id: str, seed: int) -> None:  # pragma: no cover
        raise NotImplementedError("wire up an MCP client transport")

    def send(self, utterance: str) -> MerchantTurn:  # pragma: no cover
        raise NotImplementedError("wire up an MCP client transport")

    def close_session(self) -> None:  # pragma: no cover
        raise NotImplementedError("wire up an MCP client transport")
