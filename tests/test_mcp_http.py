"""HTTP MCP transport: Basic auth, JSON-RPC discover, live 1C Drive server."""

from __future__ import annotations

import io
import json
import threading
import urllib.error
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from mcp_body.mcp_http import (
    HttpMCPClient,
    HttpMCPError,
    basic_authorization_header,
    mcp_request_headers,
    mcp_transport_from_server,
    should_send_basic_auth,
)

DRIVE_MCP_URL = "http://localhost/DriveDemo/hs/mcp/"
DRIVE_MCP_USER = "suport"
DRIVE_MCP_PASSWORD = ""


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


class _FakeOneCMCP(BaseHTTPRequestHandler):
    """Minimal Streamable-HTTP MCP that mimics 1C (POST JSON-RPC, Basic auth)."""

    expected_auth = basic_authorization_header("suport", "")
    tools = [
        {
            "name": "get_stock_levels",
            "description": "READ stock",
            "inputSchema": {"type": "object", "properties": {"sku": {"type": "string"}}},
        },
        {
            "name": "get_suppliers",
            "description": "READ suppliers",
            "inputSchema": {"type": "object"},
        },
    ]

    def log_message(self, format, *args):  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        auth = self.headers.get("Authorization") or ""
        if auth != self.expected_auth:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="1C:Enterprise 8.3"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8") or "{}")
        method = str(payload.get("method") or "")
        rpc_id = payload.get("id")
        if method == "notifications/initialized":
            self.send_response(204)
            self.end_headers()
            return
        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "fake-1c", "version": "test"},
            }
        elif method == "tools/list":
            result = {"tools": list(self.tools)}
        elif method == "tools/call":
            params = payload.get("params") or {}
            result = {
                "structuredContent": {
                    "status": "ok",
                    "name": params.get("name"),
                    "arguments": params.get("arguments") or {},
                }
            }
        else:
            self._send_json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {"code": -32601, "message": f"unknown method {method}"},
                },
            )
            return
        self._send_json(200, {"jsonrpc": "2.0", "id": rpc_id, "result": result})

    def _send_json(self, status: int, payload: dict) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _serve(handler: type) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def _drive_mcp_available() -> bool:
    try:
        client = HttpMCPClient(
            DRIVE_MCP_URL, username=DRIVE_MCP_USER, password=DRIVE_MCP_PASSWORD, timeout=5,
        )
        tools = client.list_tools()
        return bool(tools)
    except Exception:
        return False


def test_basic_auth_encodes_empty_password_as_user_colon():
    assert should_send_basic_auth("suport", "") is True
    assert should_send_basic_auth("", "") is False
    header = basic_authorization_header("suport", "")
    assert header == "Basic c3Vwb3J0Og=="
    headers = mcp_request_headers("suport", "")
    assert headers["Authorization"] == header
    assert "Authorization" not in mcp_request_headers("", "")


def test_http_client_lists_tools_with_empty_password():
    httpd = _serve(_FakeOneCMCP)
    try:
        url = f"http://127.0.0.1:{httpd.server_port}/mcp/"
        client = HttpMCPClient(url, username="suport", password="")
        tools = client.list_tools()
        names = [tool.name for tool in tools]
        assert names == ["get_stock_levels", "get_suppliers"]
        assert tools[0].input_schema["properties"]["sku"]["type"] == "string"
        result = client.call_tool("get_stock_levels", {"sku": "A"})
        assert result["status"] == "ok"
        assert result["name"] == "get_stock_levels"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_client_unwraps_mcp_text_content_json():
    class _TextEnvelopeMCP(_FakeOneCMCP):
        def do_POST(self) -> None:  # noqa: N802
            auth = self.headers.get("Authorization") or ""
            if auth != self.expected_auth:
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="1C:Enterprise 8.3"')
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8") or "{}")
            method = str(payload.get("method") or "")
            rpc_id = payload.get("id")
            if method == "notifications/initialized":
                self.send_response(204)
                self.end_headers()
                return
            if method == "initialize":
                result = {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "fake-1c", "version": "test"},
                }
            elif method == "tools/list":
                result = {"tools": list(self.tools)}
            elif method == "tools/call":
                inner = json.dumps({"status": "ok", "remaining": 12.5}, ensure_ascii=False)
                result = {
                    "content": [{"type": "text", "text": inner}],
                    "isError": False,
                }
            else:
                self._send_json(
                    200,
                    {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {"code": -32601, "message": f"unknown method {method}"},
                    },
                )
                return
            self._send_json(200, {"jsonrpc": "2.0", "id": rpc_id, "result": result})

    httpd = _serve(_TextEnvelopeMCP)
    try:
        url = f"http://127.0.0.1:{httpd.server_port}/mcp/"
        client = HttpMCPClient(url, username="suport", password="")
        result = client.call_tool("get_budget", {})
        assert result["status"] == "ok"
        assert result["remaining"] == 12.5
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_client_maps_401_to_auth_error():
    headers = Message()
    headers["WWW-Authenticate"] = 'Basic realm="1C:Enterprise 8.3"'

    def boom(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            headers,
            io.BytesIO(b""),
        )

    client = HttpMCPClient("http://127.0.0.1:9/mcp/", urlopen=boom)
    with pytest.raises(HttpMCPError, match="401"):
        client.list_tools()


def test_transport_from_server_passes_auth_fields():
    httpd = _serve(_FakeOneCMCP)
    try:
        url = f"http://127.0.0.1:{httpd.server_port}/mcp/"
        client = mcp_transport_from_server({
            "transport": "http",
            "url": url,
            "username": "suport",
            "password": "",
        })
        names = [tool.name for tool in client.list_tools()]
        assert "get_stock_levels" in names
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_transport_from_server_requires_url():
    with pytest.raises(ValueError, match="url"):
        mcp_transport_from_server({"transport": "http", "username": "suport"})


@pytest.mark.skipif(not _drive_mcp_available(), reason="Drive MCP is not published on localhost")
def test_live_drive_mcp_lists_tools_with_suport_empty_password():
    client = HttpMCPClient(
        DRIVE_MCP_URL, username=DRIVE_MCP_USER, password=DRIVE_MCP_PASSWORD, timeout=20,
    )
    tools = client.list_tools()
    names = {tool.name for tool in tools}
    assert "get_stock_levels" in names
    assert "get_suppliers" in names
    assert "list_metadata_objects" in names
    assert "get_metadata_structure" in names
    assert "get_budget" in names
    assert "create_purchase_order" in names
    assert len(tools) >= 6
