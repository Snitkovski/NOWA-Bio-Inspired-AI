"""HTTP / Streamable-HTTP MCP transport with optional Basic auth.

A live 1C publication is not a special case: it is ``MCPTransport`` plus a
URL and, when the HTTP service requires it, a username/password. Empty
password is valid (1C often publishes a user with no password).
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional
from urllib.request import Request

from .mcp_client import MCPToolDescriptor, descriptor_from_any, normalize_envelope

PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "nowa-body", "version": "0.1"}
REMOTE_TRANSPORTS = frozenset({"http", "sse"})
DEFAULT_TIMEOUT = 30.0
_JSON_ACCEPT = "application/json, text/event-stream"


class HttpMCPError(Exception):
    """Wire-level failure talking to an HTTP MCP server."""


def basic_authorization_header(username: str, password: str = "") -> str:
    """RFC 7617 ``Basic`` value. Empty password is encoded as ``user:``."""
    token = base64.b64encode(
        f"{username}:{password}".encode("utf-8")
    ).decode("ascii")
    return f"Basic {token}"


def should_send_basic_auth(username: str, password: str = "") -> bool:
    """Send Authorization when either field is set (password may be empty)."""
    return bool(username) or bool(password)


def mcp_request_headers(
    username: str = "",
    password: str = "",
    extra: Optional[Dict[str, str]] = None,
    session_id: str = "",
) -> Dict[str, str]:
    headers = {
        "Accept": _JSON_ACCEPT,
        "Content-Type": "application/json",
        "User-Agent": "nowa-body",
    }
    if should_send_basic_auth(username, password):
        headers["Authorization"] = basic_authorization_header(username, password)
    if session_id:
        headers["mcp-session-id"] = session_id
    if extra:
        headers.update({str(k): str(v) for k, v in extra.items()})
    return headers


def mcp_transport_from_server(server: Dict[str, Any]) -> "HttpMCPClient":
    """Build an HTTP client from a role YAML ``mcp_servers[]`` row."""
    transport = str(server.get("transport") or "mock")
    if transport not in REMOTE_TRANSPORTS:
        raise ValueError(f"not a remote MCP transport: {transport}")
    url = str(server.get("url") or "").strip()
    if not url:
        raise ValueError("url is required for http/sse MCP transport")
    timeout_raw = server.get("timeout")
    timeout = DEFAULT_TIMEOUT if timeout_raw in (None, "") else float(timeout_raw)
    return HttpMCPClient(
        url,
        username=str(server.get("username") or ""),
        password=str(server.get("password") or ""),
        timeout=timeout,
    )


def _default_urlopen(request: Request, timeout: float = DEFAULT_TIMEOUT):
    """Open without urllib's BasicAuth retry (it mishandles 401 + WWW-Authenticate)."""
    opener = urllib.request.build_opener(
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(),
    )
    return opener.open(request, timeout=timeout)


class HttpMCPClient:
    """JSON-RPC Streamable HTTP client. SSE GET is not required (1C is POST-only)."""

    def __init__(
        self,
        url: str,
        username: str = "",
        password: str = "",
        timeout: float = DEFAULT_TIMEOUT,
        urlopen: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.url = str(url or "").strip()
        if not self.url:
            raise ValueError("MCP URL is required")
        self.username = str(username or "")
        self.password = str(password or "")
        self.timeout = float(timeout)
        self._urlopen = urlopen or _default_urlopen
        self._rpc_id = 0
        self._session_id = ""
        self._initialized = False

    def list_tools(self) -> List[MCPToolDescriptor]:
        self._ensure_initialized()
        collected: List[Any] = []
        cursor = ""
        for _ in range(64):
            params: Dict[str, Any] = {}
            if cursor:
                params["cursor"] = cursor
            result = self._rpc("tools/list", params)
            batch = []
            next_cursor = ""
            if isinstance(result, dict):
                batch = list(result.get("tools") or [])
                next_cursor = str(result.get("nextCursor") or "")
            elif isinstance(result, list):
                batch = list(result)
            collected.extend(batch)
            if not next_cursor:
                break
            cursor = next_cursor
        return [descriptor_from_any(item) for item in collected]

    def call_tool(self, name: str, arguments: dict) -> dict:
        self._ensure_initialized()
        result = self._rpc(
            "tools/call",
            {"name": str(name or ""), "arguments": dict(arguments or {})},
        )
        if not isinstance(result, dict):
            return normalize_envelope(result)
        if result.get("isError"):
            envelope = normalize_envelope(result)
            envelope["status"] = "error"
            return envelope
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return normalize_envelope(structured)
        unwrapped = _unwrap_text_content(result)
        if isinstance(unwrapped, dict):
            return normalize_envelope(unwrapped)
        return normalize_envelope(result)

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": dict(CLIENT_INFO),
            },
        )
        try:
            self._rpc("notifications/initialized", {}, notification=True)
        except HttpMCPError:
            pass
        self._initialized = True

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _rpc(
        self,
        method: str,
        params: Optional[dict] = None,
        *,
        notification: bool = False,
    ) -> Any:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            payload["id"] = self._next_id()
        status, headers, body = self._post(payload)
        if notification and status in (200, 202, 204) and not body:
            return None
        parsed = _parse_rpc_body(body, headers.get("Content-Type") or headers.get("content-type") or "")
        if parsed is None:
            if notification and status in (200, 202, 204):
                return None
            raise HttpMCPError(f"empty MCP response for {method} (HTTP {status})")
        if not isinstance(parsed, dict):
            raise HttpMCPError(f"MCP {method} returned a non-object payload")
        if "error" in parsed:
            error = parsed.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else error
            raise HttpMCPError(f"MCP {method} error: {message}")
        return parsed.get("result")

    def _post(self, payload: dict) -> tuple:
        data = json.dumps(payload).encode("utf-8")
        headers = mcp_request_headers(
            self.username, self.password, session_id=self._session_id,
        )
        request = Request(self.url, data=data, headers=headers, method="POST")
        try:
            with self._urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                header_map = {k: v for k, v in response.headers.items()}
                session = (
                    response.headers.get("mcp-session-id")
                    or response.headers.get("Mcp-Session-Id")
                    or ""
                )
                if session:
                    self._session_id = session
                return int(getattr(response, "status", 200) or 200), header_map, raw
        except urllib.error.HTTPError as exc:
            raw = b""
            try:
                raw = exc.read() or b""
            except Exception:
                raw = b""
            if int(exc.code) == 401:
                raise HttpMCPError(
                    "MCP server rejected credentials (HTTP 401). "
                    "Check username and password."
                ) from exc
            detail = raw.decode("utf-8", "replace")[:300]
            raise HttpMCPError(
                f"MCP HTTP {exc.code} for {payload.get('method')}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise HttpMCPError(f"MCP connection failed: {exc.reason}") from exc
        except OSError as exc:
            raise HttpMCPError(f"MCP connection failed: {exc}") from exc


def _unwrap_text_content(result: Dict[str, Any]) -> Any:
    """MCP ``content[].text`` often carries the JSON envelope (1C POST-only)."""
    content = result.get("content")
    if not isinstance(content, list) or not content:
        return None
    first = content[0]
    if not isinstance(first, dict):
        return None
    text = first.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_rpc_body(raw: bytes, content_type: str) -> Any:
    text = (raw or b"").decode("utf-8", "replace")
    if not text.strip():
        return None
    lowered = (content_type or "").lower()
    if "text/event-stream" in lowered:
        data_lines = [
            line[5:].strip()
            for line in text.splitlines()
            if line.startswith("data:")
        ]
        if not data_lines:
            return None
        text = data_lines[-1]
        if not text or text == "[DONE]":
            return None
    return json.loads(text)
