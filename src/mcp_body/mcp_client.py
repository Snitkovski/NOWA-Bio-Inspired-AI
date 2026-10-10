"""Transport contract for MCP servers (stdio / sse / mock all look the same).

Spec §6.1 / P10: a live 1C MCP server is *not* a special case. It is another
object satisfying ``MCPTransport``. Nothing above this module may branch on
which server it is talking to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, runtime_checkable


@dataclass
class MCPToolDescriptor:
    """One entry of an MCP ``tools/list`` response."""

    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)


@runtime_checkable
class MCPTransport(Protocol):
    """Minimal MCP surface the body depends on."""

    def list_tools(self) -> list: ...  # list[MCPToolDescriptor]

    def call_tool(self, name: str, arguments: dict) -> dict: ...


TOOL_ID_PREFIX = "mcp"
TOOL_ID_SEPARATOR = "__"


def sanitize_tool_name(name: Any) -> str:
    """Reduce a raw MCP tool name to ``[A-Za-z0-9_]``.

    Tool ids double as basal-ganglia action channel names and as hippocampal
    ACTION tokens, so they must survive tokenization unchanged. Case is
    preserved because MCP tool names are case-sensitive on the wire.
    """
    text = str(name or "")
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in text)
    while "___" in cleaned:
        cleaned = cleaned.replace("___", "__")
    cleaned = cleaned.strip("_")
    return cleaned or "tool"


def make_tool_id(server_id: Any, name: Any) -> str:
    """``mcp__<server_id>__<sanitized tool name>`` (spec §6.1)."""
    return TOOL_ID_SEPARATOR.join(
        (TOOL_ID_PREFIX, sanitize_tool_name(server_id), sanitize_tool_name(name))
    )


def split_tool_id(tool_id: Any) -> tuple:
    """Return ``(server_id, tool_name)``; empty strings when unparseable."""
    parts = str(tool_id or "").split(TOOL_ID_SEPARATOR)
    if len(parts) < 3 or parts[0] != TOOL_ID_PREFIX:
        return "", str(tool_id or "")
    return parts[1], TOOL_ID_SEPARATOR.join(parts[2:])


def server_id_from_tool_id(tool_id: Any) -> str:
    return split_tool_id(tool_id)[0]


def tool_name_from_tool_id(tool_id: Any) -> str:
    return split_tool_id(tool_id)[1]


def descriptor_from_any(raw: Any) -> MCPToolDescriptor:
    """Normalize a ``tools/list`` entry.

    Real SDKs return objects with ``inputSchema``; mocks and YAML fallbacks
    return dicts with ``input_schema``. Both are accepted here so no caller
    has to know the difference.
    """
    if isinstance(raw, MCPToolDescriptor):
        return raw
    if isinstance(raw, dict):
        return MCPToolDescriptor(
            name=str(raw.get("name") or ""),
            description=str(raw.get("description") or ""),
            input_schema=dict(raw.get("input_schema") or raw.get("inputSchema") or {}),
            output_schema=dict(raw.get("output_schema") or raw.get("outputSchema") or {}),
        )
    schema = getattr(raw, "input_schema", None)
    if schema is None:
        schema = getattr(raw, "inputSchema", None)
    out_schema = getattr(raw, "output_schema", None)
    if out_schema is None:
        out_schema = getattr(raw, "outputSchema", None)
    return MCPToolDescriptor(
        name=str(getattr(raw, "name", "") or ""),
        description=str(getattr(raw, "description", "") or ""),
        input_schema=dict(schema or {}),
        output_schema=dict(out_schema or {}),
    )


def normalize_envelope(result: Any) -> Dict[str, Any]:
    """Every executor result is a dict carrying ``status`` (spec §6.6)."""
    if isinstance(result, dict):
        envelope = dict(result)
        if "status" not in envelope:
            envelope["status"] = "unknown"
        return envelope
    if result is None:
        return {"status": "unknown"}
    return {"status": "unknown", "value": result}


def list_tool_descriptors(mcp_client: Any) -> List[MCPToolDescriptor]:
    """Call ``list_tools()`` and normalize every entry."""
    list_tools = getattr(mcp_client, "list_tools", None)
    if not callable(list_tools):
        raise TypeError("mcp_client must implement list_tools()")
    raw_tools = list_tools() or []
    return [descriptor_from_any(item) for item in raw_tools]
