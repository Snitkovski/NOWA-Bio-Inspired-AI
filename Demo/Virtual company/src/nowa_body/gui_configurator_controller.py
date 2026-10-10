"""Headless controller for the Role Configurator GUI.

The Tk view is a thin layer over this object. All RoleConfig / SeedEpisode /
MCPCapability objects are produced by ``role_config`` parsers (spec G1).
Tests drive the controller without opening a window.
"""

from __future__ import annotations

import ast
import copy
import re
import tempfile
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from nowa_body.affect_presets import (
    DEFAULT_INTENSITY,
    PRESET_ID_RE,
    AffectPreset,
    AffectPresetCatalog,
    AffectPresetError,
    load_factory_vectors,
)
from nowa_body.lab_session import (
    ORDER_TOOL,
    SCENARIO_QUIET,
    SCENARIO_STOCK_CRITICAL,
    SCENARIO_SUPPLIER_DEFAULTED,
    SCENARIOS,
    BodyLabSession,
    LabSettings,
)
from nowa_body.gui_configurator_i18n import DEFAULT_LANG, STRINGS
from nowa_body.mcp_capability import CapabilityRisk
from nowa_body.risk_classifier import classify_risk_heuristic
from nowa_body.role_config import (
    RoleConfigError,
    load_role_config,
    load_role_config_from_mapping,
    seed_episodes_to_mappings,
)
from nowa_body._compat import ensure_core_src_on_path

ensure_core_src_on_path()
from affective_space import mapped_event_tokens  # noqa: E402

WAIT_AND_MONITOR = "wait_and_monitor"
ADVANCED_AFFECT_AXES_ENABLED = True
RISK_DOWNGRADE_PREFIX = "[risk downgrade justified:"
HISTORY_DIR_NAME = ".history"

_RISK_RANK = {
    CapabilityRisk.READ_ONLY: 0,
    CapabilityRisk.LOW_WRITE: 1,
    CapabilityRisk.MEDIUM_WRITE: 2,
    CapabilityRisk.HIGH_WRITE: 3,
    CapabilityRisk.IRREVERSIBLE: 4,
}

LOCKED_APPROVAL_RISKS = frozenset({
    CapabilityRisk.HIGH_WRITE,
    CapabilityRisk.IRREVERSIBLE,
})

DEFAULT_EVENT_CLASSIFIER = (
    "nowa_roles.procurement.event_classifier:classify_procurement_events"
)

_ORDER_INPUT_SCHEMA = {
    "type": "object",
    "required": ["supplier_id", "sku", "qty"],
    "properties": {
        "supplier_id": {"type": "string"},
        "sku": {"type": "string"},
        "qty": {"type": "number"},
    },
}

try:
    AFFECT_PRESETS = load_factory_vectors()
except AffectPresetError:
    AFFECT_PRESETS = {}

DEMO_MCP_CATALOG: List[Dict[str, Any]] = [
    {
        "tool_id": "mcp__1c__get_stock_levels",
        "server_name": "1c_erp",
        "display_name": "Get stock levels",
        "description": "READ stock",
        "domain_tags": ["procurement"],
    },
    {
        "tool_id": "mcp__1c__get_suppliers",
        "server_name": "1c_erp",
        "display_name": "Get suppliers",
        "description": "READ suppliers",
        "domain_tags": ["procurement"],
    },
    {
        "tool_id": "mcp__1c__get_budget",
        "server_name": "1c_erp",
        "display_name": "Get budget",
        "description": "READ budget",
        "domain_tags": ["finance"],
    },
    {
        "tool_id": "mcp__1c__create_purchase_order",
        "server_name": "1c_erp",
        "display_name": "Create purchase order",
        "description": "WRITE purchase order",
        "domain_tags": ["procurement"],
        "input_schema": _ORDER_INPUT_SCHEMA,
    },
    {
        "tool_id": "mcp__1c__cancel_order",
        "server_name": "1c_erp",
        "display_name": "Cancel purchase order",
        "description": "Cancel an existing purchase order",
        "domain_tags": ["procurement"],
    },
    {
        "tool_id": "mcp__1c__delete_supplier",
        "server_name": "1c_erp",
        "display_name": "Delete supplier record",
        "description": "Delete supplier record",
        "domain_tags": ["procurement"],
    },
]

MCP_TRANSPORTS = ("mock", "stdio", "sse", "http")
_SERVER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")

DEMO_MCP_SERVERS: List[Dict[str, Any]] = [
    {
        "server_id": "1c_erp",
        "display_name": "1C ERP",
        "transport": "mock",
    },
]

_ORPHAN_ACTIONS_RE = re.compile(
    r"seed_corpus references action\(s\) (\[[^\]]+\])",
    re.IGNORECASE,
)
_UNSEEDED_ACTIONS_RE = re.compile(
    r"(?:action_type\(s\)|WRITE tool_id\(s\)) (\[[^\]]+\]) have\s+no seed_corpus",
    re.IGNORECASE,
)
_JUSTIFY_RE = re.compile(
    r"^\[risk downgrade justified:.*?\]\s*",
    re.DOTALL,
)


class ConfiguratorError(Exception):
    """User-facing controller error (empty justification, missing draft, …)."""


class RiskDowngradeRequired(ConfiguratorError):
    """Raised when a risk drop below the heuristic has no justification."""

    def __init__(self, tool_id: str, heuristic: str, requested: str) -> None:
        super().__init__(
            f"{tool_id}: lowering {heuristic} → {requested} needs a non-empty "
            f"justification"
        )
        self.tool_id = tool_id
        self.heuristic = heuristic
        self.requested = requested


@dataclass
class RoleListItem:
    role_id: str
    display_name: str
    config_path: str
    status: str  # valid | warnings | error
    status_detail: str
    n_tools: int
    n_lessons: int
    domain: str
    mtime: float
    relative_mtime: str


@dataclass
class ConfigIssue:
    severity: str  # error | warning
    code: str
    params: Dict[str, Any]
    technical: str
    jump: str


@dataclass
class ValidationReport:
    errors: List[ConfigIssue] = field(default_factory=list)
    warnings: List[ConfigIssue] = field(default_factory=list)
    n_tools: int = 0
    n_decisions: int = 0
    n_lessons: int = 0

    @property
    def can_save(self) -> bool:
        return not self.errors


@dataclass
class DryRunResult:
    ok: bool
    ticks: List[Dict[str, Any]] = field(default_factory=list)
    log: List[str] = field(default_factory=list)
    summary: str = ""
    n_orders: int = 0
    n_rejected: int = 0
    n_lessons: int = 0
    error: str = ""
    memory_rows: List[dict] = field(default_factory=list)


def default_roles_root() -> Path:
    import nowa_roles
    return Path(nowa_roles.__file__).resolve().parent


def _parse_risk(value: Any) -> CapabilityRisk:
    raw = str(value or "").strip()
    try:
        return CapabilityRisk(raw)
    except ValueError as exc:
        raise ConfiguratorError(f"invalid risk_level {raw!r}") from exc


def _default_requires_approval(risk: CapabilityRisk) -> bool:
    if risk is CapabilityRisk.READ_ONLY:
        return False
    return True


def approval_control_state(risk: CapabilityRisk) -> Dict[str, bool]:
    """Widget contract for the approval toggle (spec G2).

    HIGH_WRITE / IRREVERSIBLE: checked and disabled (cannot turn off).
    READ_ONLY: unchecked and disabled (approval is meaningless).
    """
    if risk is CapabilityRisk.READ_ONLY:
        return {"checked": False, "disabled": True, "locked_on": False}
    if risk in LOCKED_APPROVAL_RISKS:
        return {"checked": True, "disabled": True, "locked_on": True}
    return {"checked": True, "disabled": False, "locked_on": False}


def _is_risk_downgrade(heuristic: CapabilityRisk, requested: CapabilityRisk) -> bool:
    return _RISK_RANK[requested] < _RISK_RANK[heuristic]


def event_to_tokens(event_name: str, mapping_entry: Optional[dict]) -> List[str]:
    """Expand a named affect event into SeedEpisode context tokens."""
    return mapped_event_tokens(event_name, mapping_entry)


_HIDDEN_MEMORY_PREFIXES = ("valence:", "arousal:", "domain:")


def _importance_from_reward(reward: float) -> str:
    if reward >= 0.75:
        return "critical"
    if reward >= 0.45:
        return "high"
    if reward >= 0.2:
        return "moderate"
    return "low"


def _pretty_token(value: str) -> str:
    return str(value or "").replace("_", " ").strip()


def _ui_text(lang: str, key: str, **kwargs: Any) -> str:
    table = STRINGS.get(lang) or STRINGS[DEFAULT_LANG]
    text = table.get(key) or STRINGS[DEFAULT_LANG].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def _ui_label(lang: str, prefix: str, code: str) -> str:
    raw = str(code or "").strip()
    if not raw:
        return ""
    key = f"{prefix}.{raw}"
    table = STRINGS.get(lang) or {}
    english = STRINGS[DEFAULT_LANG]
    if key in table or key in english:
        return _ui_text(lang, key)
    if ":" in raw:
        kind, _, rest = raw.partition(":")
        nested = f"{prefix}.{kind}.{rest}"
        if nested in table or nested in english:
            return _ui_text(lang, nested)
    return _pretty_token(raw)


def _has_ui_key(lang: str, key: str) -> bool:
    table = STRINGS.get(lang) or {}
    return key in table or key in STRINGS[DEFAULT_LANG]


def _code_from_label(lang: str, prefix: str, label: str) -> Optional[str]:
    shown = str(label or "").strip()
    if not shown:
        return None
    prefix_dot = f"{prefix}."
    for table in (STRINGS.get(lang) or {}, STRINGS[DEFAULT_LANG]):
        for key, text in table.items():
            if key.startswith(prefix_dot) and text == shown:
                return key[len(prefix_dot):]
    return None


def describe_memory_row(row: dict) -> dict:
    """Turn a hippocampus episode row into fields a person can read.

    Hides raw affect tokens (valence/arousal/domain) the same way the
    seed tab hides ``context_tokens`` in narrative view (spec G5).
    """
    path = row.get("path") or []
    if not isinstance(path, (list, tuple)):
        path = [path]
    action = str(row.get("action") or "").strip()
    events: List[str] = []
    extra: List[str] = []
    result = ""
    for tok in path:
        text = str(tok or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if any(lowered.startswith(prefix) for prefix in _HIDDEN_MEMORY_PREFIXES):
            continue
        if text.startswith("action:"):
            action = action or text.split(":", 1)[1].strip()
        elif text.startswith("event:"):
            events.append(_pretty_token(text.split(":", 1)[1]))
        elif text.startswith("result:"):
            result = text.split(":", 1)[1].strip()
        else:
            extra.append(_pretty_token(text))
    consequence = str(row.get("consequence") or "").strip()
    try:
        reward = float(row.get("reward") if row.get("reward") is not None else 0.0)
    except (TypeError, ValueError):
        reward = 0.0
    return {
        "action": action,
        "events": events,
        "extra": extra,
        "result": result,
        "consequence": consequence,
        "reward": reward,
        "importance": _importance_from_reward(reward),
    }


def format_relative_mtime(mtime: float, now: Optional[datetime] = None, lang: str = "en") -> str:
    current = now or datetime.now()
    stamp = datetime.fromtimestamp(mtime)
    delta = current - stamp
    seconds = max(0, int(delta.total_seconds()))
    ru = lang == "ru"
    if seconds < 3600:
        minutes = max(1, seconds // 60)
        return f"{minutes} мин назад" if ru else f"{minutes}m ago"
    if stamp.date() == current.date():
        hours = max(1, seconds // 3600)
        return f"{hours} ч назад" if ru else f"{hours}h ago"
    if (current.date() - stamp.date()).days == 1:
        return "вчера" if ru else "yesterday"
    days = max(1, (current.date() - stamp.date()).days)
    return f"{days}д назад" if ru else f"{days}d ago"


def _safe_literal_list(fragment: str) -> List[str]:
    try:
        parsed = ast.literal_eval(fragment)
    except (ValueError, SyntaxError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def classify_role_config_message(technical: str) -> Tuple[str, Dict[str, Any], str]:
    """Map a raw RoleConfigError / warning onto a domain issue code."""
    text = str(technical or "")
    orphan = _ORPHAN_ACTIONS_RE.search(text)
    if orphan:
        actions = _safe_literal_list(orphan.group(1))
        return "orphan_seed", {"actions": actions}, "seed"
    unseeded = _UNSEEDED_ACTIONS_RE.search(text)
    if unseeded:
        actions = _safe_literal_list(unseeded.group(1))
        return "unseeded_action", {"actions": actions}, "seed"
    lowered = text.lower()
    if "invalid risk_level" in lowered:
        return "invalid_risk", {}, "tools"
    if "no 'action'" in lowered:
        return "seed_missing_action", {}, "seed"
    if "not both" in lowered:
        return "seed_source_conflict", {}, "seed"
    if "must be a list" in lowered:
        return "malformed_list", {}, "tools"
    return "raw", {"text": text}, "validation"


def _dump_yaml(payload: dict) -> str:
    return yaml.safe_dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def _normalize_server_id(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _parse_args(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part for part in str(value or "").split() if part]


def _blank_mcp_server(
    server_id: str,
    display_name: str = "",
    transport: str = "mock",
    tools: Optional[List[dict]] = None,
) -> dict:
    chosen = transport if transport in MCP_TRANSPORTS else "mock"
    return {
        "server_id": server_id,
        "display_name": str(display_name or server_id),
        "transport": chosen,
        "enabled": True,
        "command": "",
        "args": [],
        "url": "",
        "username": "",
        "password": "",
        "catalog": [],
        "tools": list(tools or []),
    }


def _blank_role_mapping(role_id: str, display_name: str) -> dict:
    return {
        "role_id": role_id,
        "display_name": display_name,
        "mcp_servers": [],
        "mcp_capabilities": [],
        "affective_mapping": {},
        "seed_corpus": [],
        "field_aliases": {},
        "param_bindings": {},
        "event_classifier": "",
    }


def inspect_role_file(path: str) -> RoleListItem:
    """List-row status via real ``load_role_config`` (spec §2)."""
    config_path = Path(path)
    mtime = config_path.stat().st_mtime if config_path.exists() else 0.0
    role_id = config_path.parent.name
    display_name = role_id
    n_tools = 0
    n_lessons = 0
    domain = role_id
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return RoleListItem(
            role_id=role_id,
            display_name=display_name,
            config_path=str(config_path),
            status="error",
            status_detail=str(exc),
            n_tools=0,
            n_lessons=0,
            domain=domain,
            mtime=mtime,
            relative_mtime=format_relative_mtime(mtime),
        )
    if isinstance(raw, dict):
        display_name = str(raw.get("display_name") or raw.get("role_id") or role_id)
        role_id = str(raw.get("role_id") or role_id)
        caps = raw.get("mcp_capabilities") or []
        if isinstance(caps, list):
            n_tools = len(caps)
            tags: List[str] = []
            for cap in caps:
                if isinstance(cap, dict):
                    tags.extend(str(t) for t in (cap.get("domain_tags") or []))
            if tags:
                domain = tags[0]
        if n_tools == 0:
            servers = raw.get("mcp_servers") or []
            if isinstance(servers, list):
                for server in servers:
                    if not isinstance(server, dict) or not server.get("enabled", True):
                        continue
                    tools = server.get("tools") or []
                    if isinstance(tools, list):
                        n_tools += len(tools)
                        for tool in tools:
                            if isinstance(tool, dict):
                                tags = [str(t) for t in (tool.get("domain_tags") or [])]
                                if tags and domain == role_id:
                                    domain = tags[0]
        inline = raw.get("seed_corpus")
        if isinstance(inline, list):
            n_lessons = len(inline)

    caught: List[warnings.WarningMessage] = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            config = load_role_config(str(config_path))
        n_tools = len(config.capabilities)
        n_lessons = len(config.seed_corpus)
        tags = []
        for cap in config.capabilities:
            tags.extend(cap.domain_tags or [])
        if tags:
            domain = tags[0]
        warn_text = "; ".join(str(item.message) for item in caught)
        if warn_text:
            return RoleListItem(
                role_id=config.role_id,
                display_name=config.display_name,
                config_path=str(config_path),
                status="warnings",
                status_detail=warn_text,
                n_tools=n_tools,
                n_lessons=n_lessons,
                domain=domain,
                mtime=mtime,
                relative_mtime=format_relative_mtime(mtime),
            )
        return RoleListItem(
            role_id=config.role_id,
            display_name=config.display_name,
            config_path=str(config_path),
            status="valid",
            status_detail="",
            n_tools=n_tools,
            n_lessons=n_lessons,
            domain=domain,
            mtime=mtime,
            relative_mtime=format_relative_mtime(mtime),
        )
    except RoleConfigError as exc:
        return RoleListItem(
            role_id=role_id,
            display_name=display_name,
            config_path=str(config_path),
            status="error",
            status_detail=str(exc),
            n_tools=n_tools,
            n_lessons=n_lessons,
            domain=domain,
            mtime=mtime,
            relative_mtime=format_relative_mtime(mtime),
        )


def list_roles(roles_root: Optional[Path] = None) -> List[RoleListItem]:
    root = Path(roles_root or default_roles_root())
    items: List[RoleListItem] = []
    if not root.exists():
        return items
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        config = child / "config.yaml"
        if not config.is_file():
            continue
        items.append(inspect_role_file(str(config)))
    return items


MOTOR_DECISION_CATALOG: Dict[str, Dict[str, str]] = {
    "mcp__drivemcp__create_purchase_order": {
        "display_name": "Create purchase order",
        "description": "Place a purchase order from current stock and suppliers.",
    },
    "mcp__1c__create_purchase_order": {
        "display_name": "Create purchase order",
        "description": "Place a purchase order from current stock and suppliers.",
    },
    "urgent_reorder": {
        "display_name": "Urgent reorder",
        "description": "Order from the fastest supplier, regardless of price.",
    },
    "place_order_reliable_supplier": {
        "display_name": "Reliable supplier",
        "description": "Order from the most reliable supplier.",
    },
    "place_order_cheap_supplier": {
        "display_name": "Cheap supplier",
        "description": "Order from the cheapest available supplier.",
    },
    "diversify_supplier": {
        "display_name": "Diversify suppliers",
        "description": "Order from the least-used supplier to spread risk.",
    },
}


def implemented_write_channels(draft: Dict[str, Any]) -> set:
    """WRITE ``tool_id``s (plus deprecated action_types) a role can execute."""
    found = {WAIT_AND_MONITOR}
    tools: List[Any] = []
    caps = draft.get("mcp_capabilities") if isinstance(draft, dict) else None
    if isinstance(caps, list):
        tools.extend(caps)
    servers = draft.get("mcp_servers") if isinstance(draft, dict) else None
    if isinstance(servers, list):
        for server in servers:
            if not isinstance(server, dict):
                continue
            extra = server.get("tools") or []
            if isinstance(extra, list):
                tools.extend(extra)
    for cap in tools:
        if not isinstance(cap, dict):
            continue
        tool_id = str(cap.get("tool_id") or "").strip()
        risk = str(cap.get("risk_level") or "").strip().lower()
        if tool_id and risk != "read_only":
            found.add(tool_id)
        for action in cap.get("action_types") or []:
            label = str(action).strip()
            if label:
                found.add(label)
    return found


def implemented_action_types(motor_adapter_ref: str) -> Optional[set]:
    """Deprecated alias: WRITE channels no longer come from a MotorAdapter class."""
    del motor_adapter_ref
    return None


def humanize_action_type(action_type: str) -> Dict[str, str]:
    known = MOTOR_DECISION_CATALOG.get(action_type)
    if known:
        return dict(known)
    pretty = str(action_type or "").replace("_", " ").strip()
    if pretty:
        pretty = pretty[:1].upper() + pretty[1:]
    return {"display_name": pretty or action_type, "description": ""}


class RoleConfiguratorController:
    """In-memory role editor. Disk writes happen only in ``save`` / migrate."""

    def __init__(self, roles_root: Optional[Path] = None) -> None:
        self.roles_root = Path(roles_root or default_roles_root())
        self.path: str = ""
        self._original: dict = {}
        self._draft: dict = {}
        self._risk_confirmed: Dict[str, bool] = {}
        self._catalog: Dict[str, dict] = {}
        self._module_seed_cache: List[dict] = []
        self.dirty: bool = False
        self.wizard_mode: bool = False
        self._presets = AffectPresetCatalog(self.roles_root)

    # ------------------------------------------------------------------ load
    def allocate_role_id(self) -> str:
        """Fresh UUID4 that does not collide with an existing role folder or YAML id."""
        taken = set()
        root = Path(self.roles_root)
        if root.exists():
            for child in root.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                taken.add(child.name)
                config = child / "config.yaml"
                if not config.is_file():
                    continue
                try:
                    raw = yaml.safe_load(config.read_text(encoding="utf-8"))
                except (OSError, yaml.YAMLError):
                    continue
                if isinstance(raw, dict) and raw.get("role_id"):
                    taken.add(str(raw["role_id"]).strip())
        for _ in range(16):
            candidate = str(uuid.uuid4())
            if candidate not in taken:
                return candidate
        return str(uuid.uuid4())

    def new_role(self, display_name: str) -> dict:
        title = str(display_name or "").strip()
        if not title:
            raise ConfiguratorError("display name is required")
        role_id = self.allocate_role_id()
        self.path = ""
        self._draft = _blank_role_mapping(role_id, title)
        self._original = copy.deepcopy(self._draft)
        self._risk_confirmed = {}
        self._catalog = {row["tool_id"]: dict(row) for row in DEMO_MCP_CATALOG}
        self._module_seed_cache = []
        self.dirty = True
        self.wizard_mode = True
        return self.draft()

    def open_role(self, path: str) -> dict:
        config_path = Path(path)
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ConfiguratorError(f"{path} is not a YAML mapping")
        self.path = str(config_path)
        self._draft = copy.deepcopy(raw)
        self._catalog = {}
        self._hydrate_mcp_servers()
        self._original = copy.deepcopy(self._draft)
        self._risk_confirmed = {}
        for server in self._servers():
            sid = str(server.get("server_id") or "")
            for item in server.get("catalog") or []:
                if not isinstance(item, dict) or not item.get("tool_id"):
                    continue
                tool_id = str(item["tool_id"])
                payload = dict(item)
                payload["server_name"] = sid or str(item.get("server_name") or "")
                self._catalog[tool_id] = payload
            for cap in server.get("tools") or []:
                if not isinstance(cap, dict):
                    continue
                tool_id = str(cap.get("tool_id") or "")
                if not tool_id:
                    continue
                existing = self._catalog.get(tool_id, {})
                self._risk_confirmed[tool_id] = True
                self._catalog[tool_id] = {
                    "tool_id": tool_id,
                    "server_name": sid or str(cap.get("server_name") or existing.get("server_name") or ""),
                    "display_name": cap.get("display_name") or existing.get("display_name") or tool_id,
                    "description": cap.get("description") or existing.get("description") or "",
                    "input_schema": dict(cap.get("input_schema") or existing.get("input_schema") or {}),
                    "domain_tags": list(cap.get("domain_tags") or existing.get("domain_tags") or []),
                }
        for row in DEMO_MCP_CATALOG:
            self._catalog.setdefault(row["tool_id"], dict(row))
        self._module_seed_cache = []
        if self.uses_seed_module:
            try:
                loaded = load_role_config(self.path)
                self._module_seed_cache = seed_episodes_to_mappings(loaded.seed_corpus)
            except RoleConfigError:
                self._module_seed_cache = []
        self.dirty = False
        self.wizard_mode = False
        return self.draft()

    def draft(self) -> dict:
        if self._draft:
            self._sync_capabilities_from_servers()
        return copy.deepcopy(self._draft)

    def has_draft(self) -> bool:
        return bool(self._draft)

    @property
    def uses_seed_module(self) -> bool:
        return bool(self._draft.get("seed_corpus_module")) and "seed_corpus" not in self._draft

    @property
    def advanced_affect_visible(self) -> bool:
        return ADVANCED_AFFECT_AXES_ENABLED

    # ------------------------------------------------------------------ MCP servers
    def _servers(self) -> List[dict]:
        servers = self._draft.setdefault("mcp_servers", [])
        if not isinstance(servers, list):
            servers = []
            self._draft["mcp_servers"] = servers
        return servers

    def _hydrate_mcp_servers(self) -> None:
        """Canonical in-memory shape is mcp_servers[].tools[]; flatten for role_config."""
        existing = self._draft.get("mcp_servers")
        if isinstance(existing, list) and existing:
            normalized: List[dict] = []
            for server in existing:
                if not isinstance(server, dict):
                    continue
                sid = _normalize_server_id(str(server.get("server_id") or ""))
                server["server_id"] = sid or str(server.get("server_id") or "")
                server.setdefault("display_name", server["server_id"])
                transport = str(server.get("transport") or "mock")
                server["transport"] = transport if transport in MCP_TRANSPORTS else "mock"
                server.setdefault("enabled", True)
                server.setdefault("command", "")
                server["args"] = _parse_args(server.get("args"))
                server.setdefault("url", "")
                server.setdefault("username", "")
                server.setdefault("password", "")
                catalog = server.get("catalog")
                if not isinstance(catalog, list):
                    server["catalog"] = []
                else:
                    for item in catalog:
                        if isinstance(item, dict):
                            item["server_name"] = server["server_id"]
                tools = server.get("tools")
                if not isinstance(tools, list):
                    server["tools"] = []
                for tool in server["tools"]:
                    if isinstance(tool, dict):
                        tool["server_name"] = server["server_id"]
                normalized.append(server)
            self._draft["mcp_servers"] = normalized
            self._sync_capabilities_from_servers()
            return
        grouped: Dict[str, List[dict]] = {}
        order: List[str] = []
        for cap in self._draft.get("mcp_capabilities") or []:
            if not isinstance(cap, dict):
                continue
            sid = _normalize_server_id(str(cap.get("server_name") or "unknown")) or "unknown"
            if sid not in grouped:
                grouped[sid] = []
                order.append(sid)
            grouped[sid].append(cap)
        known = {row["server_id"]: row for row in DEMO_MCP_SERVERS}
        built: List[dict] = []
        for sid in order:
            meta = known.get(sid, {})
            built.append(_blank_mcp_server(
                sid,
                display_name=str(meta.get("display_name") or sid),
                transport=str(meta.get("transport") or "mock"),
                tools=grouped[sid],
            ))
        self._draft["mcp_servers"] = built
        self._sync_capabilities_from_servers()

    def _sync_capabilities_from_servers(self) -> None:
        caps: List[dict] = []
        for server in self._servers():
            if not server.get("enabled", True):
                continue
            sid = str(server.get("server_id") or "")
            for tool in server.get("tools") or []:
                if not isinstance(tool, dict):
                    continue
                tool["server_name"] = sid
                caps.append(tool)
        self._draft["mcp_capabilities"] = caps

    def _server(self, server_id: str, *, missing_ok: bool = False) -> Optional[dict]:
        sid = _normalize_server_id(server_id)
        for server in self._servers():
            if str(server.get("server_id") or "") == sid:
                return server
        if missing_ok:
            return None
        raise ConfiguratorError(f"MCP server not in role: {sid}")

    def _ensure_server(self, server_id: str, display_name: str = "") -> dict:
        sid = _normalize_server_id(server_id)
        if not sid or not _SERVER_ID_RE.match(sid):
            raise ConfiguratorError(
                "server_id must be letters, digits and underscore (e.g. 1c_erp)"
            )
        found = self._server(sid, missing_ok=True)
        if found is not None:
            return found
        known = {row["server_id"]: row for row in DEMO_MCP_SERVERS}
        meta = known.get(sid, {})
        server = _blank_mcp_server(
            sid,
            display_name=display_name or str(meta.get("display_name") or sid),
            transport=str(meta.get("transport") or "mock"),
        )
        self._servers().append(server)
        self.dirty = True
        self._sync_capabilities_from_servers()
        return server

    def _find_tool(self, tool_id: str) -> Optional[Tuple[dict, dict]]:
        for server in self._servers():
            for tool in server.get("tools") or []:
                if isinstance(tool, dict) and tool.get("tool_id") == tool_id:
                    return server, tool
        return None

    def _all_tools(self) -> List[dict]:
        tools: List[dict] = []
        for server in self._servers():
            for tool in server.get("tools") or []:
                if isinstance(tool, dict):
                    tools.append(tool)
        return tools

    def add_server(
        self,
        server_id: str,
        display_name: str = "",
        transport: str = "mock",
    ) -> dict:
        sid = _normalize_server_id(server_id)
        if not sid or not _SERVER_ID_RE.match(sid):
            raise ConfiguratorError(
                "server_id must be letters, digits and underscore (e.g. 1c_erp)"
            )
        if self._server(sid, missing_ok=True) is not None:
            raise ConfiguratorError(f"server already exists: {sid}")
        chosen = transport if transport in MCP_TRANSPORTS else "mock"
        server = _blank_mcp_server(sid, display_name=display_name, transport=chosen)
        self._servers().append(server)
        self.dirty = True
        self._sync_capabilities_from_servers()
        return dict(server)

    def update_server(self, server_id: str, **fields: Any) -> dict:
        server = self._server(server_id)
        if "display_name" in fields:
            title = str(fields.get("display_name") or "").strip()
            server["display_name"] = title or str(server.get("server_id") or "")
        if "transport" in fields:
            transport = str(fields.get("transport") or "mock")
            if transport not in MCP_TRANSPORTS:
                raise ConfiguratorError(f"unsupported MCP transport: {transport}")
            server["transport"] = transport
        if "enabled" in fields:
            server["enabled"] = bool(fields["enabled"])
        if "command" in fields:
            server["command"] = str(fields.get("command") or "")
        if "args" in fields:
            server["args"] = _parse_args(fields.get("args"))
        if "url" in fields:
            server["url"] = str(fields.get("url") or "")
        if "username" in fields:
            server["username"] = str(fields.get("username") or "").strip()
        if "password" in fields:
            server["password"] = str(fields.get("password") or "")
        self.dirty = True
        self._sync_capabilities_from_servers()
        return dict(server)

    def remove_server(self, server_id: str) -> None:
        sid = _normalize_server_id(server_id)
        kept = [s for s in self._servers() if str(s.get("server_id") or "") != sid]
        if len(kept) == len(self._servers()):
            raise ConfiguratorError(f"MCP server not in role: {sid}")
        self._draft["mcp_servers"] = kept
        self.dirty = True
        self._sync_capabilities_from_servers()

    def server_rows(self) -> List[dict]:
        rows: List[dict] = []
        for server in self._servers():
            tools = [t for t in (server.get("tools") or []) if isinstance(t, dict)]
            catalog = [t for t in (server.get("catalog") or []) if isinstance(t, dict)]
            args = _parse_args(server.get("args"))
            n_included = len(tools)
            n_catalog = len(catalog)
            rows.append({
                "server_id": str(server.get("server_id") or ""),
                "display_name": str(server.get("display_name") or server.get("server_id") or ""),
                "transport": str(server.get("transport") or "mock"),
                "enabled": bool(server.get("enabled", True)),
                "command": str(server.get("command") or ""),
                "args": args,
                "args_text": " ".join(args),
                "url": str(server.get("url") or ""),
                "username": str(server.get("username") or ""),
                "password": str(server.get("password") or ""),
                "n_included": n_included,
                "n_catalog": n_catalog,
                "n_tools": n_catalog or n_included,
            })
        return rows

    # ------------------------------------------------------------------ tools
    def _capabilities(self) -> List[dict]:
        self._sync_capabilities_from_servers()
        caps = self._draft.setdefault("mcp_capabilities", [])
        if not isinstance(caps, list):
            caps = []
            self._draft["mcp_capabilities"] = caps
        return caps

    def _cap(self, tool_id: str) -> dict:
        found = self._find_tool(tool_id)
        if found is None:
            raise ConfiguratorError(f"tool not in role: {tool_id}")
        return found[1]

    def discover_tools(self, server_id: Optional[str] = None) -> List[dict]:
        """Discover via the selected server's ``list_tools`` (mock catalog or HTTP)."""
        sid = _normalize_server_id(server_id) if server_id else ""
        if not sid:
            raise ConfiguratorError("select an MCP server before discovering tools")
        server = self._server(sid)
        transport = str(server.get("transport") or "mock")
        if transport in ("http", "sse"):
            return self._discover_remote_tools(server)
        if transport == "stdio":
            raise ConfiguratorError("stdio MCP transport is not implemented yet")
        return self._discover_mock_catalog(sid)

    def discover_mock_tools(self, server_id: Optional[str] = None) -> List[dict]:
        """Backward-compatible alias of ``discover_tools`` (mock catalog path)."""
        if server_id:
            return self.discover_tools(server_id)
        servers = self._servers()
        if not servers:
            return self._discover_mock_catalog("")
        return self.discover_tools(str(servers[0].get("server_id") or ""))

    def _discover_mock_catalog(self, server_id: str) -> List[dict]:
        from nowa_body._compat import ensure_core_src_on_path
        from nowa_body.mock_mcp import MockMCPClient, MockMCPTool

        ensure_core_src_on_path()
        from mcp_body.mcp_client import split_tool_id

        sid = _normalize_server_id(server_id) if server_id else ""
        client = MockMCPClient()
        catalog_by_name: Dict[str, dict] = {}
        for row in DEMO_MCP_CATALOG:
            if sid and str(row.get("server_name") or "") != sid:
                continue
            tool = MockMCPTool(row["tool_id"], lambda _p: {"status": "ok"})
            tool.description = str(row.get("description") or "")
            tool.input_schema = dict(row.get("input_schema") or {})
            client.register(tool)
            _server, name = split_tool_id(row["tool_id"])
            catalog_by_name[name or row["tool_id"]] = dict(row)

        added = 0
        payloads: List[dict] = []
        for descriptor in client.list_tools():
            row = catalog_by_name.get(descriptor.name)
            if row is None:
                continue
            tool_id = row["tool_id"]
            payload = dict(row)
            if descriptor.input_schema:
                payload["input_schema"] = dict(descriptor.input_schema)
            if descriptor.description:
                payload["description"] = descriptor.description
            payloads.append(payload)
            if tool_id not in self._catalog:
                added += 1
            self._catalog[tool_id] = payload
        if sid:
            self._server(sid)["catalog"] = [dict(item) for item in payloads]
        self.dirty = self.dirty or added > 0 or bool(payloads)
        return self.tool_rows(server_id=sid or None)

    def _discover_remote_tools(self, server: dict) -> List[dict]:
        from nowa_body._compat import ensure_core_src_on_path

        ensure_core_src_on_path()
        from mcp_body.mcp_client import make_tool_id
        from mcp_body.mcp_http import HttpMCPError, mcp_transport_from_server

        sid = str(server.get("server_id") or "")
        try:
            client = mcp_transport_from_server(server)
            descriptors = client.list_tools()
        except (HttpMCPError, ValueError, OSError, TypeError) as exc:
            raise ConfiguratorError(str(exc)) from exc
        added = 0
        payloads: List[dict] = []
        for descriptor in descriptors:
            name = str(descriptor.name or "").strip()
            if not name:
                continue
            tool_id = make_tool_id(sid, name)
            payload = {
                "tool_id": tool_id,
                "server_name": sid,
                "display_name": name,
                "description": str(descriptor.description or name),
                "input_schema": dict(descriptor.input_schema or {}),
                "domain_tags": [],
            }
            payloads.append(payload)
            if tool_id not in self._catalog:
                added += 1
            self._catalog[tool_id] = payload
        server["catalog"] = [dict(item) for item in payloads]
        self.dirty = True
        return self.tool_rows(server_id=sid)

    def add_manual_tool(
        self,
        tool_id: str,
        display_name: str = "",
        description: str = "",
        server_name: str = "1c_erp",
        domain_tags: Optional[Sequence[str]] = None,
        included: bool = True,
    ) -> dict:
        tid = str(tool_id or "").strip()
        if not tid:
            raise ConfiguratorError("tool_id is required")
        sid = _normalize_server_id(server_name) or "1c_erp"
        row = {
            "tool_id": tid,
            "server_name": sid,
            "display_name": str(display_name or tid),
            "description": str(description or ""),
            "domain_tags": [str(tag) for tag in (domain_tags or [])],
        }
        self._catalog[tid] = row
        if included:
            self.set_tool_included(tid, True, server_id=sid)
        return row

    def set_tool_included(
        self,
        tool_id: str,
        included: bool,
        server_id: Optional[str] = None,
    ) -> None:
        found = self._find_tool(tool_id)
        if included and found is None:
            catalog = self._catalog.get(tool_id, {"tool_id": tool_id})
            sid = _normalize_server_id(
                server_id or catalog.get("server_name") or ""
            )
            if not sid:
                raise ConfiguratorError("add an MCP server before including a tool")
            server = self._ensure_server(sid)
            heuristic = classify_risk_heuristic(
                tool_id, str(catalog.get("description") or "")
            )
            entry = {
                "tool_id": tool_id,
                "server_name": sid,
                "display_name": catalog.get("display_name") or tool_id,
                "description": catalog.get("description") or "",
                "risk_level": heuristic.value,
                "domain_tags": list(catalog.get("domain_tags") or []),
                "requires_approval": _default_requires_approval(heuristic),
                "action_types": [],
                "input_schema": dict(catalog.get("input_schema") or {}),
                "poll": False,
                "poll_defaults": {},
            }
            self._sync_approval_fields(entry)
            server.setdefault("tools", []).append(entry)
            self._risk_confirmed.setdefault(tool_id, False)
            self.dirty = True
            self._sync_capabilities_from_servers()
            return
        if (not included) and found is not None:
            server, _tool = found
            tools = server.setdefault("tools", [])
            server["tools"] = [
                item for item in tools
                if not (isinstance(item, dict) and item.get("tool_id") == tool_id)
            ]
            self.dirty = True
            self._sync_capabilities_from_servers()

    def set_tool_risk(
        self,
        tool_id: str,
        risk_level: str,
        justification: str = "",
    ) -> dict:
        cap = self._cap(tool_id)
        requested = _parse_risk(risk_level)
        heuristic = classify_risk_heuristic(
            tool_id, str(cap.get("description") or "")
        )
        if _is_risk_downgrade(heuristic, requested):
            if not str(justification or "").strip():
                raise RiskDowngradeRequired(tool_id, heuristic.value, requested.value)
            original = _JUSTIFY_RE.sub("", str(cap.get("description") or ""))
            cap["description"] = (
                f"{RISK_DOWNGRADE_PREFIX} {justification.strip()}] {original}"
            ).strip()
        cap["risk_level"] = requested.value
        self._sync_approval_fields(cap)
        if requested is not CapabilityRisk.READ_ONLY:
            cap["poll"] = False
        self._risk_confirmed[tool_id] = True
        self.dirty = True
        return dict(cap)

    def confirm_heuristic_risk(self, tool_id: str) -> dict:
        cap = self._cap(tool_id)
        heuristic = classify_risk_heuristic(
            tool_id, str(cap.get("description") or "")
        )
        return self.set_tool_risk(tool_id, heuristic.value)

    def is_risk_confirmed(self, tool_id: str) -> bool:
        return bool(self._risk_confirmed.get(tool_id, False))

    def set_requires_approval(self, tool_id: str, value: bool) -> bool:
        """Apply an approval toggle. HIGH/IRREVERSIBLE cannot become False (G2)."""
        cap = self._cap(tool_id)
        risk = _parse_risk(cap.get("risk_level"))
        state = approval_control_state(risk)
        if state["disabled"]:
            cap["requires_approval"] = bool(state["checked"])
            self.dirty = True
            return False
        cap["requires_approval"] = bool(value)
        self.dirty = True
        return True

    def set_tool_poll(self, tool_id: str, poll: bool) -> bool:
        """Poll is a role-level sensor flag. WRITE organs cannot be polled."""
        cap = self._cap(tool_id)
        risk = _parse_risk(cap.get("risk_level"))
        if risk is not CapabilityRisk.READ_ONLY:
            cap["poll"] = False
            self.dirty = True
            return False
        cap["poll"] = bool(poll)
        if cap["poll"]:
            cap.setdefault("poll_defaults", {})
        self.dirty = True
        return True

    def set_poll_default(self, tool_id: str, key: str, value: Any) -> None:
        cap = self._cap(tool_id)
        defaults = cap.setdefault("poll_defaults", {})
        if not isinstance(defaults, dict):
            defaults = {}
            cap["poll_defaults"] = defaults
        name = str(key or "").strip()
        if not name:
            return
        text = value if value is None else str(value)
        if text is None or str(text).strip() == "":
            defaults.pop(name, None)
        else:
            defaults[name] = text
        self.dirty = True

    def _sync_approval_fields(self, cap: dict) -> None:
        risk = _parse_risk(cap.get("risk_level"))
        state = approval_control_state(risk)
        if state["disabled"]:
            cap["requires_approval"] = bool(state["checked"])

    def set_tool_action_types(self, tool_id: str, action_types: Sequence[str]) -> None:
        self._cap(tool_id)["action_types"] = [
            str(item).strip() for item in action_types if str(item).strip()
        ]
        self.dirty = True

    def set_tool_tags(self, tool_id: str, tags: Sequence[str]) -> None:
        self._cap(tool_id)["domain_tags"] = [
            str(item).strip() for item in tags if str(item).strip()
        ]
        self.dirty = True

    def set_tool_description(self, tool_id: str, description: str) -> None:
        self._cap(tool_id)["description"] = str(description or "")
        self.dirty = True

    def tool_rows(self, server_id: Optional[str] = None) -> List[dict]:
        sid_filter = _normalize_server_id(server_id) if server_id else ""
        included_by_id: Dict[str, dict] = {}
        ordered_ids: List[str] = []
        for server in self._servers():
            owner = str(server.get("server_id") or "")
            if sid_filter and owner != sid_filter:
                continue
            for cap in server.get("tools") or []:
                if not isinstance(cap, dict) or not cap.get("tool_id"):
                    continue
                tool_id = str(cap["tool_id"])
                included_by_id[tool_id] = cap
                ordered_ids.append(tool_id)
        rows: List[dict] = []
        seen = set()
        catalog_ids = []
        for tool_id, catalog in self._catalog.items():
            owner = str(catalog.get("server_name") or "")
            if sid_filter and owner != sid_filter:
                continue
            catalog_ids.append(tool_id)
        for tool_id in catalog_ids + ordered_ids:
            if tool_id in seen:
                continue
            seen.add(tool_id)
            catalog = self._catalog.get(tool_id, {"tool_id": tool_id})
            included = tool_id in included_by_id
            cap = included_by_id.get(tool_id, {})
            description = str(cap.get("description") if included else catalog.get("description") or "")
            heuristic = classify_risk_heuristic(tool_id, description)
            if included:
                risk = _parse_risk(cap.get("risk_level") or heuristic.value)
            else:
                risk = heuristic
            state = approval_control_state(risk)
            requires = bool(cap.get("requires_approval", state["checked"])) if included else state["checked"]
            if state["disabled"]:
                requires = bool(state["checked"])
            owner = str(
                cap.get("server_name") if included else catalog.get("server_name") or sid_filter or ""
            )
            schema = cap.get("input_schema") if included else catalog.get("input_schema")
            if not isinstance(schema, dict):
                schema = {}
            required = [str(name) for name in (schema.get("required") or []) if str(name).strip()]
            is_read = risk is CapabilityRisk.READ_ONLY
            poll = bool(cap.get("poll", False)) if included and is_read else False
            poll_defaults = dict(cap.get("poll_defaults") or {}) if included else {}
            rows.append({
                "tool_id": tool_id,
                "server_name": owner,
                "display_name": str(cap.get("display_name") if included else catalog.get("display_name") or tool_id),
                "description": description,
                "included": included,
                "risk_level": risk.value,
                "heuristic_risk": heuristic.value,
                "risk_confirmed": self.is_risk_confirmed(tool_id) if included else False,
                "requires_approval": requires,
                "approval_disabled": state["disabled"],
                "approval_locked_on": state["locked_on"],
                "action_types": list(cap.get("action_types") or []) if included else [],
                "domain_tags": list(cap.get("domain_tags") or catalog.get("domain_tags") or []),
                "irreversible_excluded": (
                    (not included) and risk is CapabilityRisk.IRREVERSIBLE
                ),
                "poll": poll,
                "poll_enabled": included and is_read,
                "poll_defaults": poll_defaults,
                "poll_required": required,
                "input_schema": dict(schema),
            })
        return rows

    # ------------------------------------------------------------------ vocab
    def _vocab(self) -> Dict[str, dict]:
        raw = self._draft.get("action_vocabulary")
        if not isinstance(raw, dict):
            raw = {}
            self._draft["action_vocabulary"] = raw
        return raw

    def declared_action_types(self) -> List[str]:
        names: List[str] = []
        for cap in self._all_tools():
            if not isinstance(cap, dict):
                continue
            for action in cap.get("action_types") or []:
                label = str(action).strip()
                if label and label not in names:
                    names.append(label)
        for key in self._vocab():
            label = str(key).strip()
            if label and label not in names:
                names.append(label)
        return names

    def vocabulary_rows(self) -> List[dict]:
        implemented = implemented_write_channels(self._draft)
        used_by: Dict[str, List[str]] = {}
        for cap in self._all_tools():
            if not isinstance(cap, dict):
                continue
            tool_id = str(cap.get("tool_id") or "")
            if not tool_id:
                continue
            actions = [str(action).strip() for action in (cap.get("action_types") or [])]
            risk = str(cap.get("risk_level") or "").strip().lower()
            if risk != "read_only":
                actions.append(tool_id)
            for action in actions:
                if not action:
                    continue
                bucket = used_by.setdefault(action, [])
                if tool_id not in bucket:
                    bucket.append(tool_id)
        rows = []
        for action in self.declared_action_types():
            meta = self._vocab().get(action) or {}
            needs_code = action not in implemented and action != WAIT_AND_MONITOR
            rows.append({
                "action_type": action,
                "display_name": str(meta.get("display_name") or humanize_action_type(action)["display_name"]),
                "description": str(meta.get("description") or humanize_action_type(action)["description"]),
                "used_in_tools": used_by.get(action, []),
                "needs_motor_adapter": needs_code,
            })
        return rows

    def motor_adapter_decision_choices(self) -> List[dict]:
        """WRITE organs not yet listed as vocabulary decisions."""
        implemented = implemented_write_channels(self._draft)
        already = set(self.declared_action_types())
        already.add(WAIT_AND_MONITOR)
        rows = []
        for action in sorted(implemented):
            if action in already:
                continue
            labels = humanize_action_type(action)
            rows.append({
                "action_type": action,
                "display_name": labels["display_name"],
                "description": labels["description"],
            })
        return rows

    def _new_action_type_id(self) -> str:
        taken = set(self.declared_action_types())
        taken.add(WAIT_AND_MONITOR)
        for _ in range(16):
            candidate = f"decision_{uuid.uuid4().hex}"
            if candidate not in taken:
                return candidate
        return f"decision_{uuid.uuid4().hex}"

    def add_action_type(
        self,
        action_type: str = "",
        display_name: str = "",
        description: str = "",
    ) -> dict:
        title = str(display_name or "").strip()
        label = str(action_type or "").strip()
        if not title:
            title = label
        if not title:
            raise ConfiguratorError("decision name is required")
        if not label:
            label = self._new_action_type_id()
        if label == WAIT_AND_MONITOR:
            raise ConfiguratorError("wait_and_monitor is implicit and is not added")
        if label in self._vocab():
            raise ConfiguratorError(f"decision already exists: {label}")
        self._vocab()[label] = {
            "display_name": title,
            "description": str(description or ""),
        }
        self.dirty = True
        return dict(self._vocab()[label], action_type=label)

    def update_action_type(
        self,
        action_type: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        meta = self._vocab().setdefault(action_type, {})
        if display_name is not None:
            meta["display_name"] = str(display_name)
        if description is not None:
            meta["description"] = str(description)
        self.dirty = True

    def remove_action_type(self, action_type: str) -> None:
        self._vocab().pop(action_type, None)
        for cap in self._all_tools():
            types = [a for a in (cap.get("action_types") or []) if a != action_type]
            cap["action_types"] = types
        self.dirty = True

    def action_display_name(self, action_type: str, lang: str = "en") -> str:
        code = str(action_type or "").strip()
        if not code:
            return ""
        key = f"decision.{code}"
        if _has_ui_key(lang, key):
            return _ui_text(lang, key)
        if code == WAIT_AND_MONITOR:
            return _pretty_token(code)
        meta = self._vocab().get(code) or {}
        custom = str(meta.get("display_name") or "").strip()
        if custom:
            return custom
        return humanize_action_type(code)["display_name"]

    def outcome_display_name(self, code: str, lang: str = "en") -> str:
        raw = str(code or "").strip()
        if not raw:
            return ""
        if _has_ui_key(lang, f"outcome.{raw}"):
            return _ui_label(lang, "outcome", raw)
        if _has_ui_key(lang, f"dryrun.memory.outcome.{raw}"):
            return _ui_text(lang, f"dryrun.memory.outcome.{raw}")
        return _pretty_token(raw)

    def outcome_code_from_label(self, label: str, lang: str = "en") -> str:
        shown = str(label or "").strip()
        if not shown:
            return ""
        mapped = _code_from_label(lang, "outcome", shown)
        if mapped:
            return mapped
        for code in self.existing_consequences():
            if self.outcome_display_name(code, lang) == shown:
                return code
        return shown

    def tag_display_name(self, tag: str, lang: str = "en") -> str:
        raw = str(tag or "").strip()
        if not raw:
            return ""
        if _has_ui_key(lang, f"domain.{raw}"):
            return _ui_text(lang, f"domain.{raw}")
        return _pretty_token(raw)

    # ------------------------------------------------------------------ affect
    def affective_events(self) -> List[str]:
        mapping = self._draft.get("affective_mapping") or {}
        if not isinstance(mapping, dict):
            return []
        return [str(name) for name in mapping]

    def event_display_name(self, event_name: str, lang: str = "en") -> str:
        """Human-readable event label for the current UI language."""
        return _ui_label(lang, "event", event_name)

    def get_affective_event(self, event_name: str) -> dict:
        from affective_space import AXES

        mapping = self._draft.setdefault("affective_mapping", {})
        entry = mapping.get(event_name) or {}
        payload = {
            "event_name": event_name,
            "valence": float(entry.get("valence", 0.0) or 0.0),
            "arousal": float(entry.get("arousal", 0.5) if entry.get("arousal") is not None else 0.5),
            "tags": list(entry.get("tags") or []),
            "intensity": float(
                entry.get("intensity", DEFAULT_INTENSITY)
                if entry.get("intensity") is not None
                else DEFAULT_INTENSITY
            ),
        }
        extra: List[str] = []
        for axis in AXES:
            if axis in ("valence", "arousal"):
                continue
            if axis not in entry or entry.get(axis) is None:
                continue
            payload[axis] = float(entry[axis])
            extra.append(axis)
        payload["axes_set"] = extra
        return payload

    def upsert_affective_event(
        self,
        event_name: str,
        valence: float,
        arousal: float,
        tags: Optional[Sequence[str]] = None,
        axes: Optional[Dict[str, Any]] = None,
        intensity: Optional[float] = None,
    ) -> None:
        from affective_space import AXES

        name = str(event_name or "").strip()
        if not name:
            raise ConfiguratorError("event name is required")
        mapping = self._draft.setdefault("affective_mapping", {})
        if not isinstance(mapping, dict):
            mapping = {}
            self._draft["affective_mapping"] = mapping
        current = dict(mapping.get(name) or {})
        current["valence"] = float(valence)
        current["arousal"] = float(arousal)
        if tags is not None:
            current["tags"] = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            current.setdefault("tags", [])
        if intensity is not None:
            current["intensity"] = float(intensity)
        if axes:
            for key, value in axes.items():
                if key not in AXES:
                    continue
                if value is None:
                    current.pop(key, None)
                else:
                    current[key] = float(value)
        mapping[name] = current
        self.dirty = True

    def apply_affect_preset(self, event_name: str, preset: str) -> dict:
        try:
            item = self._presets.get(preset)
        except AffectPresetError as exc:
            raise ConfiguratorError(str(exc)) from exc
        current = self.get_affective_event(event_name) if event_name in self.affective_events() else {
            "tags": [],
        }
        axes = dict(item.axes)
        valence = float(axes.pop("valence", 0.0))
        arousal = float(axes.pop("arousal", 0.5))
        self.upsert_affective_event(
            event_name,
            valence,
            arousal,
            current.get("tags"),
            axes=axes,
            intensity=item.intensity,
        )
        return self.get_affective_event(event_name)

    def list_visible_affect_presets(self, lang: str = "en") -> List[dict]:
        rows = []
        for item in self._presets.visible_presets():
            rows.append({
                "id": item.id,
                "label": item.label(lang),
                "builtin": item.builtin,
                "overlay": item.overlay,
            })
        return rows

    def list_all_affect_presets(self, lang: str = "en") -> List[dict]:
        rows = []
        for item in self._presets.all_presets():
            rows.append({
                "id": item.id,
                "label": item.label(lang),
                "builtin": item.builtin,
                "overlay": item.overlay,
                "hidden": item.hidden,
                "axes": dict(item.axes),
                "intensity": item.intensity,
                "label_en": item.label_en,
                "label_ru": item.label_ru,
            })
        return rows

    def save_affect_preset(
        self,
        preset_id: str,
        label_en: str,
        label_ru: str,
        *,
        event_name: Optional[str] = None,
        axes: Optional[Dict[str, float]] = None,
        intensity: Optional[float] = None,
    ) -> dict:
        from affective_space import AXES

        pid = str(preset_id or "").strip()
        if not PRESET_ID_RE.match(pid):
            raise ConfiguratorError(f"preset id must match [a-z][a-z0-9_]{{1,47}}, got {pid!r}")
        vector: Dict[str, float] = dict(axes or {})
        intensity_v = DEFAULT_INTENSITY if intensity is None else float(intensity)
        if event_name:
            data = self.get_affective_event(event_name)
            vector = {axis: float(data[axis]) for axis in AXES if axis in data}
            intensity_v = float(data.get("intensity", DEFAULT_INTENSITY))
        try:
            saved = self._presets.upsert_user_preset(
                AffectPreset(
                    id=pid,
                    axes=vector,
                    intensity=intensity_v,
                    label_en=str(label_en or "").strip(),
                    label_ru=str(label_ru or "").strip(),
                )
            )
        except AffectPresetError as exc:
            raise ConfiguratorError(str(exc)) from exc
        return {
            "id": saved.id,
            "label_en": saved.label_en,
            "label_ru": saved.label_ru,
            "builtin": saved.builtin,
            "overlay": saved.overlay,
        }

    def hide_affect_preset(self, preset_id: str, hidden: bool = True) -> None:
        try:
            self._presets.hide(preset_id, hidden=hidden)
        except AffectPresetError as exc:
            raise ConfiguratorError(str(exc)) from exc

    def restore_factory_preset(self, preset_id: str) -> None:
        try:
            self._presets.restore_factory(preset_id)
        except AffectPresetError as exc:
            raise ConfiguratorError(str(exc)) from exc

    def delete_affect_preset(self, preset_id: str) -> None:
        try:
            self._presets.delete_user_preset(preset_id)
        except AffectPresetError as exc:
            raise ConfiguratorError(str(exc)) from exc

    def preview_affective_event(self, event_name: str) -> dict:
        """One-step AffectiveSpace readout for the current mapping entry (not live A(t))."""
        from affective_space import (
            AXES,
            AffectiveSpace,
            DECISION_DIMENSIONS,
            EmotionalImpulse,
            RANK_WEIGHT_KEYS,
        )
        from mcp_body.generic_encoder import MAX_IMPULSE_INTENSITY
        from semantic_emotions import SemanticEmotionsLayer

        entry = self.get_affective_event(event_name)
        vector = {axis: float(entry[axis]) for axis in AXES if axis in entry}
        intensity = min(float(entry.get("intensity", DEFAULT_INTENSITY)), MAX_IMPULSE_INTENSITY)
        space = AffectiveSpace()
        space.step(
            external_impulses=[
                EmotionalImpulse(vector=vector, intensity=intensity, source="external")
            ]
        )
        emotions = SemanticEmotionsLayer().update_from_space(space)
        return {
            "axes": dict(space.axes),
            "decision_bias": space.decision_bias(),
            "rank_weights": space.rank_weights(),
            "emotions": emotions[:3],
            "bias_keys": list(DECISION_DIMENSIONS),
            "rank_keys": list(RANK_WEIGHT_KEYS),
        }

    def outcome_impulse_rows(self) -> List[dict]:
        from affective_space import AffectiveSpace

        rows = []
        for status in ("success", "error", "timeout"):
            impulse = AffectiveSpace.outcome_impulse(status)
            rows.append({
                "status": status,
                "vector": dict(impulse.vector),
                "intensity": float(impulse.intensity),
            })
        return rows

    def remove_affective_event(self, event_name: str) -> None:
        mapping = self._draft.get("affective_mapping") or {}
        if isinstance(mapping, dict):
            mapping.pop(event_name, None)
            self.dirty = True

    # ------------------------------------------------------------------ seed
    def _inline_seed(self) -> List[dict]:
        if self.uses_seed_module:
            return list(self._module_seed_cache)
        corpus = self._draft.setdefault("seed_corpus", [])
        if not isinstance(corpus, list):
            corpus = []
            self._draft["seed_corpus"] = corpus
        return corpus

    def seed_rows(self, technical: bool = False, lang: str = "en") -> List[dict]:
        rows = []
        for idx, entry in enumerate(self._inline_seed()):
            if not isinstance(entry, dict):
                continue
            rows.append({
                "index": idx,
                "narrative": self.lesson_narrative(entry, technical=technical, lang=lang),
                "action": str(entry.get("action") or ""),
                "consequence": str(entry.get("consequence") or ""),
                "technical": technical,
            })
        return rows

    def lesson_narrative(
        self,
        entry: dict,
        technical: bool = False,
        lang: str = "en",
    ) -> str:
        if technical:
            return (
                f"action={entry.get('action')} "
                f"consequence={entry.get('consequence')} "
                f"reward={entry.get('reward')} "
                f"intensity={entry.get('intensity')} "
                f"reinforce={entry.get('reinforce')} "
                f"context_tokens={entry.get('context_tokens')}"
            )
        tokens = [str(tok) for tok in (entry.get("context_tokens") or [])]
        events = [
            _ui_label(lang, "event", tok.split(":", 1)[1])
            for tok in tokens
            if tok.startswith("event:") and ":" in tok
        ]
        extras = [
            _ui_label(lang, "token", tok)
            for tok in tokens
            if ":" in tok
            and not tok.startswith("event:")
            and not tok.startswith("valence:")
            and not tok.startswith("arousal:")
            and not tok.startswith("domain:")
            and not tok.startswith("action:")
        ]
        situation_parts = [part for part in events + extras if part]
        event_text = ", ".join(situation_parts) if situation_parts else _ui_text(
            lang, "seed.unnamed",
        )
        action = str(entry.get("action") or "")
        action_text = self.action_display_name(action, lang=lang)
        consequence_code = str(entry.get("consequence") or "")
        if consequence_code:
            consequence = self.outcome_display_name(consequence_code, lang=lang)
        else:
            consequence = _ui_text(lang, "seed.unspecified_outcome")
        try:
            importance = float(entry.get("reward", 0.0) or 0.0)
        except (TypeError, ValueError):
            importance = 0.0
        importance_label = _ui_text(
            lang, f"seed.importance.{_importance_from_reward(importance)}",
        )
        reinforce = _ui_text(
            lang, "seed.yes" if entry.get("reinforce") else "seed.no",
        )
        return _ui_text(
            lang,
            "seed.story",
            situation=event_text,
            decision=action_text,
            outcome=consequence,
            importance=importance_label,
            reinforce=reinforce,
        )

    def build_lesson_mapping(
        self,
        event_names: Sequence[str],
        action: str,
        consequence: str,
        importance: float,
        reinforce: bool,
    ) -> dict:
        """Produce a seed YAML mapping via the same fields ``_load_seed_corpus`` reads."""
        if not event_names:
            raise ConfiguratorError("select at least one event")
        action_label = str(action or "").strip()
        if not action_label:
            raise ConfiguratorError("select a decision")
        consequence_label = str(consequence or "").strip() or "unspecified_outcome"
        score = max(0.0, min(1.0, float(importance)))
        mapping = self._draft.get("affective_mapping") or {}
        tokens: List[str] = []
        for name in event_names:
            tokens.extend(event_to_tokens(str(name), mapping.get(name) if isinstance(mapping, dict) else None))
        return {
            "context_tokens": tokens,
            "action": action_label,
            "consequence": consequence_label,
            "reward": score,
            "intensity": score,
            "reinforce": bool(reinforce),
        }

    def add_lesson_from_wizard(
        self,
        event_names: Sequence[str],
        action: str,
        consequence: str,
        importance_0_to_10: float,
        reinforce: bool,
        replace_index: Optional[int] = None,
    ) -> dict:
        if self.uses_seed_module:
            raise ConfiguratorError("seed corpus is read-only until migrated inline")
        mapping = self.build_lesson_mapping(
            event_names,
            action,
            consequence,
            float(importance_0_to_10) / 10.0,
            reinforce,
        )
        corpus = list(self._inline_seed())
        if replace_index is None:
            candidate = corpus + [mapping]
        else:
            idx = int(replace_index)
            if not (0 <= idx < len(corpus)):
                raise ConfiguratorError("lesson index out of range")
            candidate = list(corpus)
            candidate[idx] = mapping
        probe = copy.deepcopy(self._draft)
        probe["seed_corpus"] = candidate
        probe.pop("seed_corpus_module", None)
        try:
            load_role_config_from_mapping(probe, self.path or "<draft>")
        except RoleConfigError as exc:
            raise ConfiguratorError(str(exc)) from exc
        self._draft["seed_corpus"] = candidate
        self.dirty = True
        return mapping

    def remove_lesson(self, index: int) -> None:
        if self.uses_seed_module:
            raise ConfiguratorError("seed corpus is read-only until migrated inline")
        corpus = self._inline_seed()
        corpus.pop(int(index))
        self.dirty = True

    def migrate_seed_module_to_inline(self, write_file: bool = True) -> List[dict]:
        """Replace ``seed_corpus_module`` with inline YAML. Does not delete the .py file."""
        if not self._draft.get("seed_corpus_module"):
            raise ConfiguratorError("this role already uses inline seed_corpus")
        source = self.path or "<draft>"
        loaded = load_role_config_from_mapping(self._draft, source)
        rows = seed_episodes_to_mappings(loaded.seed_corpus)
        self._draft.pop("seed_corpus_module", None)
        self._draft["seed_corpus"] = rows
        self._module_seed_cache = []
        self.dirty = True
        if write_file:
            if not self.path:
                raise ConfiguratorError("save the role before migrating to disk")
            self._write_to_path(self.path, create_backup=True)
            self._original = copy.deepcopy(self._draft)
            self.dirty = False
        return rows

    def get_lesson(self, index: int) -> dict:
        corpus = self._inline_seed()
        if not (0 <= int(index) < len(corpus)):
            raise ConfiguratorError("lesson index out of range")
        entry = corpus[int(index)]
        return dict(entry) if isinstance(entry, dict) else {}

    def existing_consequences(self) -> List[str]:
        names: List[str] = []
        for entry in self._inline_seed():
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("consequence") or "").strip()
            if label and label not in names:
                names.append(label)
        return names

    def wizard_action_choices(self) -> List[dict]:
        rows = self.vocabulary_rows()
        rows.append({
            "action_type": WAIT_AND_MONITOR,
            "display_name": "",
            "description": "",
            "used_in_tools": [],
            "needs_motor_adapter": False,
        })
        return rows

    # ------------------------------------------------------------------ validate / save
    def validate(self) -> ValidationReport:
        report = ValidationReport(
            n_tools=len(self._capabilities()),
            n_decisions=len(self.declared_action_types()),
            n_lessons=len(self._inline_seed()),
        )
        source = self.path or "<draft>"
        caught: List[warnings.WarningMessage] = []
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                load_role_config_from_mapping(self._draft, source)
        except RoleConfigError as exc:
            code, params, jump = classify_role_config_message(str(exc))
            report.errors.append(ConfigIssue(
                severity="error",
                code=code,
                params=params,
                technical=str(exc),
                jump=jump,
            ))
        for item in caught:
            technical = str(item.message)
            code, params, jump = classify_role_config_message(technical)
            report.warnings.append(ConfigIssue(
                severity="warning",
                code=code,
                params=params,
                technical=technical,
                jump=jump,
            ))
        for row in self.tool_rows():
            if row["included"] and not row["risk_confirmed"]:
                report.warnings.append(ConfigIssue(
                    severity="warning",
                    code="unconfirmed_risk",
                    params={"tool_id": row["tool_id"], "heuristic": row["heuristic_risk"]},
                    technical=(
                        f"{row['tool_id']}: heuristic risk {row['heuristic_risk']} "
                        f"is not yet confirmed"
                    ),
                    jump="tools",
                ))
        for row in self.vocabulary_rows():
            if row["needs_motor_adapter"]:
                report.warnings.append(ConfigIssue(
                    severity="warning",
                    code="needs_motor_adapter",
                    params={"action_type": row["action_type"]},
                    technical=(
                        f"action_type {row['action_type']} is not a WRITE "
                        f"tool_id (or wait_and_monitor) for this role"
                    ),
                    jump="vocabulary",
                ))
        return report

    def can_save(self) -> bool:
        return self.validate().can_save

    def diff_preview(self) -> List[str]:
        old = self._original or {}
        new = self._draft or {}
        lines: List[str] = []
        old_caps = {
            str(cap.get("tool_id")): cap
            for cap in (old.get("mcp_capabilities") or [])
            if isinstance(cap, dict) and cap.get("tool_id")
        }
        new_caps = {
            str(cap.get("tool_id")): cap
            for cap in (new.get("mcp_capabilities") or [])
            if isinstance(cap, dict) and cap.get("tool_id")
        }
        for tool_id in new_caps:
            if tool_id not in old_caps:
                lines.append(f"+ added tool: {tool_id}")
            else:
                old_risk = str(old_caps[tool_id].get("risk_level") or "")
                new_risk = str(new_caps[tool_id].get("risk_level") or "")
                if old_risk != new_risk:
                    lines.append(f"~ changed: {tool_id}, risk {old_risk} → {new_risk}")
        for tool_id in old_caps:
            if tool_id not in new_caps:
                lines.append(f"- removed tool: {tool_id}")
        old_seed = old.get("seed_corpus") if isinstance(old.get("seed_corpus"), list) else []
        new_seed = new.get("seed_corpus") if isinstance(new.get("seed_corpus"), list) else []
        if len(new_seed) > len(old_seed):
            for extra in new_seed[len(old_seed):]:
                if isinstance(extra, dict):
                    lines.append(
                        f"+ added lesson: {self.lesson_narrative(extra, technical=False)}"
                    )
        if old.get("seed_corpus_module") and not new.get("seed_corpus_module"):
            lines.append("~ seed corpus migrated from Python module to inline YAML")
        old_events = set((old.get("affective_mapping") or {}) if isinstance(old.get("affective_mapping"), dict) else [])
        new_events = set((new.get("affective_mapping") or {}) if isinstance(new.get("affective_mapping"), dict) else [])
        for name in sorted(new_events - old_events):
            lines.append(f"+ added event: {name}")
        old_vocab = set((old.get("action_vocabulary") or {}) if isinstance(old.get("action_vocabulary"), dict) else [])
        new_vocab = set((new.get("action_vocabulary") or {}) if isinstance(new.get("action_vocabulary"), dict) else [])
        for name in sorted(new_vocab - old_vocab):
            lines.append(f"+ added decision: {name}")
        old_servers = {
            str(server.get("server_id") or ""): server
            for server in (old.get("mcp_servers") or [])
            if isinstance(server, dict) and server.get("server_id")
        }
        new_servers = {
            str(server.get("server_id") or ""): server
            for server in (new.get("mcp_servers") or [])
            if isinstance(server, dict) and server.get("server_id")
        }
        for sid, server in new_servers.items():
            if sid not in old_servers:
                lines.append(f"+ added MCP server: {sid}")
                continue
            previous = old_servers[sid]
            for field in ("display_name", "transport", "url", "username", "enabled"):
                if previous.get(field) != server.get(field):
                    lines.append(f"~ changed: {sid} {field}")
            if bool(previous.get("password")) != bool(server.get("password")):
                lines.append(f"~ changed: {sid} password")
            old_catalog = len(previous.get("catalog") or [])
            new_catalog = len(server.get("catalog") or [])
            if old_catalog != new_catalog:
                lines.append(f"~ changed: {sid} catalog {old_catalog} → {new_catalog} tools")
        for sid in old_servers:
            if sid not in new_servers:
                lines.append(f"- removed MCP server: {sid}")
        if not lines and self.dirty:
            lines.append("~ configuration changed")
        return lines

    def save(self, confirmed: bool = False) -> Dict[str, Any]:
        report = self.validate()
        if not report.can_save:
            raise ConfiguratorError("cannot save while validation errors remain")
        diff = self.diff_preview()
        if not confirmed:
            return {"saved": False, "needs_confirm": True, "diff": diff}
        target = self._resolve_save_path()
        self._write_to_path(target, create_backup=Path(target).exists())
        self.path = target
        self._original = copy.deepcopy(self._draft)
        self.dirty = False
        self.wizard_mode = False
        return {"saved": True, "needs_confirm": False, "diff": diff, "path": target}

    def _resolve_save_path(self) -> str:
        if self.path:
            return self.path
        role_id = str(self._draft.get("role_id") or "").strip()
        if not role_id:
            raise ConfiguratorError("role_id is required to save a new role")
        folder = self.roles_root / role_id
        folder.mkdir(parents=True, exist_ok=True)
        return str(folder / "config.yaml")

    def _write_to_path(self, path: str, create_backup: bool) -> None:
        target = Path(path)
        if create_backup and target.exists():
            self._backup_existing(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if self._draft:
            self._sync_capabilities_from_servers()
        target.write_text(_dump_yaml(self._draft), encoding="utf-8")

    def _backup_existing(self, target: Path) -> Path:
        history = target.parent / HISTORY_DIR_NAME
        history.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup = history / f"config_{stamp}.yaml"
        if backup.exists():
            backup = history / f"config_{stamp}_{datetime.now().microsecond}.yaml"
        backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        return backup

    def list_history(self) -> List[dict]:
        if not self.path:
            return []
        history = Path(self.path).parent / HISTORY_DIR_NAME
        if not history.is_dir():
            return []
        rows = []
        for file in sorted(history.glob("config_*.yaml"), reverse=True):
            rows.append({
                "path": str(file),
                "name": file.name,
                "mtime": file.stat().st_mtime,
                "relative_mtime": format_relative_mtime(file.stat().st_mtime),
            })
        return rows

    def history_diff(self, history_path: str) -> List[str]:
        previous = yaml.safe_load(Path(history_path).read_text(encoding="utf-8")) or {}
        saved_original = self._original
        self._original = previous if isinstance(previous, dict) else {}
        try:
            return self.diff_preview()
        finally:
            self._original = saved_original

    def restore_history(self, history_path: str) -> None:
        if not self.path:
            raise ConfiguratorError("no current role file to restore into")
        payload = yaml.safe_load(Path(history_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ConfiguratorError("history file is not a YAML mapping")
        self._draft = copy.deepcopy(payload)
        self._hydrate_mcp_servers()
        self._write_to_path(self.path, create_backup=True)
        self._original = copy.deepcopy(self._draft)
        self.dirty = False

    # ------------------------------------------------------------------ dry run
    def dry_run(
        self,
        scenario: str = SCENARIO_STOCK_CRITICAL,
        n_ticks: int = 20,
        force_action: str = ORDER_TOOL,
    ) -> DryRunResult:
        report = self.validate()
        if not report.can_save:
            return DryRunResult(
                ok=False,
                error=report.errors[0].technical if report.errors else "invalid config",
            )
        chosen = scenario if scenario in SCENARIOS else SCENARIO_STOCK_CRITICAL
        with tempfile.TemporaryDirectory(prefix="nowa_role_dryrun_") as tmp:
            tmp_path = Path(tmp) / "config.yaml"
            tmp_path.write_text(_dump_yaml(self._draft), encoding="utf-8")
            session = BodyLabSession(LabSettings(
                seed_intuition=True,
                auto_execute=False,
                scenario=chosen,
                role_config_path=str(tmp_path),
                force_action=force_action,
                sensor_refresh_interval_s=300.0,
                min_ticks_between_sleep=10_000,
            ))
            ticks: List[Dict[str, Any]] = []
            n_orders = 0
            n_rejected = 0
            episodes_before = session.snapshot()["episodes"]
            for _ in range(max(0, int(n_ticks))):
                result = session.tick_once()
                for pending in list(session.pending_rows()):
                    record = session.approve(pending["action_id"])
                    exec_result = getattr(record, "execution_result", None) or {}
                    status = str(exec_result.get("status") or "")
                    if status in ("accepted", "success", "ok"):
                        n_orders += 1
                    elif status in ("rejected", "failed", "error"):
                        n_rejected += 1
                ticks.append({
                    "tick": session.tick_index,
                    "action": result.get("action_type"),
                    "approval": result.get("approval_status"),
                    "executed": result.get("executed"),
                    "proposed": None if result.get("proposed") is None else {
                        "tool_id": getattr(result["proposed"], "tool_id", ""),
                        "params": dict(getattr(result["proposed"], "tool_params", {}) or {}),
                    },
                    "execution_result": getattr(result.get("record"), "execution_result", None),
                })
            episodes_after = session.snapshot()["episodes"]
            return DryRunResult(
                ok=True,
                ticks=ticks,
                log=list(session.log),
                n_orders=n_orders,
                n_rejected=n_rejected,
                n_lessons=max(0, episodes_after - episodes_before),
                memory_rows=session.episode_rows(),
                summary=(
                    f"{n_ticks} ticks: {n_orders} orders, {n_rejected} rejected, "
                    f"{max(0, episodes_after - episodes_before)} lessons stored"
                ),
            )


__all__ = [
    "ADVANCED_AFFECT_AXES_ENABLED",
    "AFFECT_PRESETS",
    "DEMO_MCP_CATALOG",
    "ConfigIssue",
    "ConfiguratorError",
    "DryRunResult",
    "RiskDowngradeRequired",
    "RoleConfiguratorController",
    "RoleListItem",
    "SCENARIOS",
    "SCENARIO_QUIET",
    "SCENARIO_STOCK_CRITICAL",
    "SCENARIO_SUPPLIER_DEFAULTED",
    "ValidationReport",
    "WAIT_AND_MONITOR",
    "approval_control_state",
    "classify_role_config_message",
    "default_roles_root",
    "describe_memory_row",
    "event_to_tokens",
    "inspect_role_file",
    "list_roles",
]
