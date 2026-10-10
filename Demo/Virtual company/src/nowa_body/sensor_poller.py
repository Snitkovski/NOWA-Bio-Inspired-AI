"""Poll only organs the role marked ``poll: true`` — never every READ, never WRITE."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from .mcp_capability import CapabilityRisk, MCPCapability


def required_fields(schema: Any) -> List[str]:
    if not isinstance(schema, dict):
        return []
    raw = schema.get("required")
    if not isinstance(raw, list):
        return []
    return [str(name) for name in raw if str(name).strip()]


def poll_capabilities(capabilities: Sequence[MCPCapability]) -> List[MCPCapability]:
    """Organs the host is allowed to call as sensors."""
    sensors: List[MCPCapability] = []
    for cap in capabilities:
        if not getattr(cap, "poll", False):
            continue
        risk = getattr(cap.risk_level, "value", cap.risk_level)
        if str(risk) != CapabilityRisk.READ_ONLY.value:
            continue
        sensors.append(cap)
    return sensors


def resolve_poll_arguments(
    cap: MCPCapability,
    world_state: Any,
    binder: Any,
    *,
    param_bindings: Optional[Dict[str, Any]] = None,
    field_aliases: Optional[Dict[str, Any]] = None,
    hippocampus: Any = None,
) -> Optional[Dict[str, Any]]:
    """Return call args, or None when this cycle should skip the sensor."""
    defaults = dict(getattr(cap, "poll_defaults", None) or {})
    required = required_fields(getattr(cap, "input_schema", None) or {})
    bound: Dict[str, Any] = {}
    if binder is not None and hasattr(binder, "bind"):
        try:
            result = binder.bind(
                cap,
                world_state,
                hippocampus=hippocampus,
                param_bindings=param_bindings,
                field_aliases=field_aliases,
            )
        except Exception:
            result = None
        if isinstance(result, dict):
            bound = dict(result)
    params = dict(bound)
    params.update(defaults)
    if not required:
        return dict(defaults) if defaults else dict(params)
    if all(name in params and params[name] not in (None, "") for name in required):
        return params
    return None


def poll_sensors(
    capabilities: Sequence[MCPCapability],
    router: Any,
    world_state: Any,
    binder: Any,
    *,
    agent_id: str = "",
    param_bindings: Optional[Dict[str, Any]] = None,
    field_aliases: Optional[Dict[str, Any]] = None,
    hippocampus: Any = None,
    log_warning: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Call poll sensors. One READ error is an envelope; the cycle continues."""
    tool_results: Dict[str, Any] = {}
    for cap in poll_capabilities(capabilities):
        args = resolve_poll_arguments(
            cap,
            world_state,
            binder,
            param_bindings=param_bindings,
            field_aliases=field_aliases,
            hippocampus=hippocampus,
        )
        if args is None:
            required = required_fields(getattr(cap, "input_schema", None) or {})
            message = (
                f"skip poll {cap.tool_id}: required {required} not filled "
                f"(set poll_defaults or wait for WorldState)"
            )
            if log_warning is not None:
                log_warning(message)
            continue
        try:
            envelope = router.call_tool(cap.tool_id, args)
        except Exception as exc:
            envelope = {"status": "error", "reason": str(exc)}
        if not isinstance(envelope, dict):
            envelope = {"status": "error", "reason": "non_dict_result", "value": envelope}
        tool_results[cap.tool_id] = envelope
    return {
        "agent_id": agent_id,
        "tool_results": tool_results,
    }


__all__ = [
    "poll_capabilities",
    "poll_sensors",
    "required_fields",
    "resolve_poll_arguments",
]
