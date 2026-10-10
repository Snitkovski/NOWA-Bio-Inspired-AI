# NOWA Body Layer — Role Configurator (RoleConfig)

Russian version: [NOWA_Body_Layer_RoleConfig_Spec.ru.md](NOWA_Body_Layer_RoleConfig_Spec.ru.md)

## Abstract

The role-configurator specification moves role data into declarative YAML and leaves algorithms in Python, so that a new role does not require an edit to the `nowa_body` package. The configuration contains the capability registry, the `affective_mapping` map, and the seed corpus of professional intuition. The code retains the motor adapter, which turns an intention into parameters, and the classifier, which maps observation conditions to a named event. The criterion of the split is the qualitative specificity of the role: facts about the role's world are data, and the way observations are read into action parameters is an algorithm and differs between a buyer and a salesperson.

For the buyer the document gives four tools. Three reads — stock, suppliers, and budget — have level `read_only` and do not require approval. The order write has level `medium_write`, requires approval, and lists four action types: reliable supplier, cheap supplier, urgent reorder, and diversification. In the map, critically low stock has valence −0.7 and arousal 0.8, a supplier default has −0.5 and 0.6, a favourable deal has 0.8 and 0.6, and a budget exceeded has −0.8 and 0.7. The loader reads the YAML, validates it, and builds the registry, the encoder, the seeder, and two callables from references of the form `package:name`. An inline corpus and a reference to a corpus module are mutually exclusive. A seed action absent from the action types of registered capabilities is a `RoleConfigError`: the document links this class of failure to silent misses, already observed, of the requirement for an `ACTION` event. Import of a reference is limited to `import_module` and `getattr`. The adapter class is checked for inheritance from `MotorAdapter` before an instance is created.

A role in this specification is data about a job, not an instance of a mind. After migration, the laboratory session is built through `load_role_config`, and behaviour over several ticks is compared with episode rows and a snapshot already collected before the migration. Adding a salesperson role requires its own `config.yaml`, its own adapter, and its own classifier, with the body layer unchanged. Constraints C1–C5 make validation an unconditional part of loading, forbid a generic exception without a path to the field, and do not admit execution of arbitrary code while a reference is resolved.

---

**Version:** 1.0
**Parent documents:**
- NOWA_Body_Layer_Phase1_Spec.md (v1.0)
- Phase 1 patches v1.1 (sleep/tick), v1.2 (action label fix)
**Status:** Ready for implementation
**Goal:** Move role data (the capability registry, the affective map, the seed corpus) into declarative YAML, leaving the algorithms (MotorAdapter, event classifier) in code — so that adding a new role does not require touching `nowa_body`, and requires only a new `config.yaml` plus two Python modules.

---

## 0. Separation principle (justification)

```
Config (YAML) — DATA                      Code (Python) — ALGORITHMS
──────────────────────────                ─────────────────────────
MCPCapability registration                MotorAdapter._build_params
AFFECTIVE_MAPPING                          (which supplier, how many,
seed_corpus (professional                  how to read the hippocampus)
intuition)
                                           event_classifier
                                            (which conditions → which
                                             named event)
```

The criterion of separation is not "simple/complex", but the **qualitative specificity of the role**. Data are facts about the role's world ("this tool is dangerous", "this word causes anxiety", "in this situation the right thing to do is the following"). Code is *how* the body-agent interprets observations into action parameters, which differs in principle between a buyer and a salesperson, and is not merely different numbers in one and the same formula.

---

## 1. Project structure

```
nowa_body/
├── ... (unchanged from Phase 1)
├── role_config.py          # RoleConfig, loader, validator
└── tests/
    └── test_role_config.py

nowa_roles/
├── procurement/
│   ├── config.yaml         # NEW — capabilities + affective_mapping + seed_corpus
│   ├── motor_adapter.py    # unchanged (code, not config)
│   ├── event_classifier.py # unchanged (code, not config)
│   └── seed_corpus.py      # remains as a fallback/reference path (section 4.2)
└── sales/                  # future role — the same three-file pattern
    ├── config.yaml
    ├── motor_adapter.py
    └── event_classifier.py
```

---

## 2. Schema of `config.yaml`

```yaml
# nowa_roles/procurement/config.yaml

role_id: procurement
display_name: "Procurement Manager"

# --- Capability registry (raw data → MCPCapability instances) -------------
mcp_capabilities:
  - tool_id: mcp__1c__get_stock_levels
    server_name: 1c_erp
    display_name: "Get stock levels"
    description: "READ stock"
    risk_level: read_only
    domain_tags: [procurement]
    requires_approval: false

  - tool_id: mcp__1c__get_suppliers
    server_name: 1c_erp
    display_name: "Get suppliers"
    description: "READ suppliers"
    risk_level: read_only
    domain_tags: [procurement]
    requires_approval: false

  - tool_id: mcp__1c__get_budget
    server_name: 1c_erp
    display_name: "Get budget"
    description: "READ budget"
    risk_level: read_only
    domain_tags: [finance]
    requires_approval: false

  - tool_id: mcp__1c__create_purchase_order
    server_name: 1c_erp
    display_name: "Create purchase order"
    description: "WRITE purchase order"
    risk_level: medium_write
    domain_tags: [procurement]
    requires_approval: true
    action_types:
      - place_order_reliable_supplier
      - place_order_cheap_supplier
      - urgent_reorder
      - diversify_supplier

# --- Affective mapping (named business event → VAD + tags) ----------------
affective_mapping:
  stock_critical_low:
    valence: -0.7
    arousal: 0.8
    tags: [procurement, urgency, risk]
  supplier_defaulted:
    valence: -0.5
    arousal: 0.6
    tags: [procurement, risk]
  deal_closed_favorable:
    valence: 0.8
    arousal: 0.6
    tags: [procurement, success]
  budget_exceeded:
    valence: -0.8
    arousal: 0.7
    tags: [finance, risk]

# --- Professional intuition seed corpus ------------------------------------
# Either inline (below) OR seed_corpus_module (section 4.2) — not both.
seed_corpus:
  - context_tokens: [event:stock_critical_low, domain:procurement,
                     valence:very_negative, arousal:high]
    action: urgent_reorder
    consequence: stock_restored
    reward: 0.8
    intensity: 0.9
    reinforce: true

  - context_tokens: [event:stock_critical_low, domain:procurement,
                     budget:critical]
    action: place_order_cheap_supplier
    consequence: budget_preserved
    reward: 0.6
    intensity: 0.7
    reinforce: false

  # ... the remaining 6 episodes — see section 4.2 on the transfer from seed_corpus.py

# --- Code pointers (escape hatch — real logic stays in Python) ------------
motor_adapter: "nowa_roles.procurement.motor_adapter:ProcurementBodyMotorAdapter"
event_classifier: "nowa_roles.procurement.event_classifier:classify_procurement_events"
```

---

## 3. `role_config.py`

```python
"""Declarative role configuration: capability registry, affective mapping,
seed corpus as data; motor adapter and event classifier as code pointers.

Loading a role is: read YAML → validate → build MCPToolRegistry,
BusinessEventEncoder, BusinessHippocampusSeeder, and dynamically import
the two role-specific Python callables. Nothing here executes agent logic.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

import yaml

from .mcp_capability import CapabilityRisk, MCPCapability
from .business_event_encoder import BusinessEventEncoder
from .business_hippocampus_seeder import BusinessHippocampusSeeder, SeedEpisode
from .motor_adapter import MotorAdapter
from .tool_registry import MCPToolRegistry


class RoleConfigError(Exception):
    """Raised on malformed config or a failed cross-validation check."""


@dataclass
class RoleConfig:
    role_id: str
    display_name: str
    capabilities: List[MCPCapability]
    affective_mapping: Dict[str, dict]
    seed_corpus: List[SeedEpisode]
    motor_adapter_path: str
    event_classifier_path: str
    source_path: str = ""


def load_role_config(path: str) -> RoleConfig:
    """
    Parse config.yaml into a RoleConfig. Raises RoleConfigError with a
    specific, actionable message on any malformed field — never falls
    back to a partially-loaded silent default, because a silently
    dropped capability or seed episode is exactly the class of bug this
    project has hit three times already (mismatched ACTION tokens).
    """
    raw = _read_yaml(path)

    role_id = _require_str(raw, "role_id", path)
    display_name = str(raw.get("display_name") or role_id)

    capabilities = [
        _parse_capability(entry, idx, path)
        for idx, entry in enumerate(raw.get("mcp_capabilities") or [])
    ]
    affective_mapping = _parse_affective_mapping(
        raw.get("affective_mapping") or {}, path
    )
    seed_corpus = _load_seed_corpus(raw, path)

    motor_adapter_path = _require_str(raw, "motor_adapter", path)
    event_classifier_path = _require_str(raw, "event_classifier", path)

    config = RoleConfig(
        role_id=role_id,
        display_name=display_name,
        capabilities=capabilities,
        affective_mapping=affective_mapping,
        seed_corpus=seed_corpus,
        motor_adapter_path=motor_adapter_path,
        event_classifier_path=event_classifier_path,
        source_path=path,
    )
    validate_role_config(config)  # raises on cross-reference mismatches
    return config


def _read_yaml(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise RoleConfigError(f"role config not found: {path}")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RoleConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RoleConfigError(f"{path} must be a YAML mapping at the top level")
    return data


def _require_str(raw: dict, key: str, path: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RoleConfigError(f"{path}: '{key}' is required and must be a non-empty string")
    return value.strip()


def _parse_capability(entry: Any, idx: int, path: str) -> MCPCapability:
    if not isinstance(entry, dict):
        raise RoleConfigError(f"{path}: mcp_capabilities[{idx}] must be a mapping")
    tool_id = _require_str(entry, "tool_id", f"{path}:mcp_capabilities[{idx}]")
    risk_raw = str(entry.get("risk_level") or "").strip()
    try:
        risk_level = CapabilityRisk(risk_raw)
    except ValueError as exc:
        valid = ", ".join(r.value for r in CapabilityRisk)
        raise RoleConfigError(
            f"{path}: mcp_capabilities[{idx}] ('{tool_id}') has invalid "
            f"risk_level '{risk_raw}'. Valid values: {valid}"
        ) from exc

    return MCPCapability(
        tool_id=tool_id,
        server_name=str(entry.get("server_name") or ""),
        display_name=str(entry.get("display_name") or tool_id),
        description=str(entry.get("description") or ""),
        risk_level=risk_level,
        domain_tags=list(entry.get("domain_tags") or []),
        requires_approval=bool(entry.get("requires_approval", True)),
        action_types=list(entry.get("action_types") or []),
        cost_impact_estimate=entry.get("cost_impact_estimate"),
        max_autonomous_value=entry.get("max_autonomous_value"),
    )


def _parse_affective_mapping(raw: Any, path: str) -> Dict[str, dict]:
    if not isinstance(raw, dict):
        raise RoleConfigError(f"{path}: affective_mapping must be a mapping")
    result: Dict[str, dict] = {}
    for event_name, entry in raw.items():
        if not isinstance(entry, dict):
            raise RoleConfigError(
                f"{path}: affective_mapping['{event_name}'] must be a mapping"
            )
        result[str(event_name)] = {
            "valence": float(entry.get("valence", 0.0)),
            "arousal": float(entry.get("arousal", 0.5)),
            "tags": list(entry.get("tags") or []),
        }
    return result


def _load_seed_corpus(raw: dict, path: str) -> List[SeedEpisode]:
    inline = raw.get("seed_corpus")
    module_ref = raw.get("seed_corpus_module")
    if inline and module_ref:
        raise RoleConfigError(
            f"{path}: specify either 'seed_corpus' (inline) or "
            f"'seed_corpus_module' (Python reference), not both"
        )
    if module_ref:
        return _load_seed_corpus_from_module(str(module_ref), path)
    if not isinstance(inline, list):
        raise RoleConfigError(f"{path}: 'seed_corpus' must be a list")
    episodes: List[SeedEpisode] = []
    for idx, entry in enumerate(inline):
        if not isinstance(entry, dict):
            raise RoleConfigError(f"{path}: seed_corpus[{idx}] must be a mapping")
        action = str(entry.get("action") or "").strip()
        if not action:
            raise RoleConfigError(
                f"{path}: seed_corpus[{idx}] has no 'action' — every seed "
                f"episode must carry an action label (lesson 2: a "
                f"context-only episode is inert)"
            )
        episodes.append(SeedEpisode(
            context_tokens=list(entry.get("context_tokens") or []),
            action=action,
            consequence=str(entry.get("consequence") or "unspecified_outcome"),
            reward=float(entry.get("reward", 0.0)),
            intensity=float(entry.get("intensity", 0.5)),
            reinforce=bool(entry.get("reinforce", False)),
        ))
    return episodes


def _load_seed_corpus_from_module(ref: str, path: str) -> List[SeedEpisode]:
    """
    ref format: "package.module:ATTRIBUTE_NAME", pointing at an existing
    List[SeedEpisode] (e.g. the pre-existing PROCUREMENT_SEED_EPISODES).
    Backward-compat path for roles migrated before this spec, or for
    corpora too large/generated to hand-author as YAML.
    """
    module_path, _, attr_name = ref.partition(":")
    if not module_path or not attr_name:
        raise RoleConfigError(
            f"{path}: seed_corpus_module '{ref}' must be 'module:ATTRIBUTE'"
        )
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise RoleConfigError(f"{path}: cannot import '{module_path}': {exc}") from exc
    corpus = getattr(module, attr_name, None)
    if not isinstance(corpus, list):
        raise RoleConfigError(
            f"{path}: '{ref}' does not resolve to a list of SeedEpisode"
        )
    return list(corpus)


def validate_role_config(config: RoleConfig) -> None:
    """
    Cross-reference checks that catch the exact class of bug this project
    has hit three times: an ACTION label the ActionSelector will never
    see because nothing in the capability registry declares it.

    Raises RoleConfigError with the specific mismatched labels — fails
    loudly at config-load time, not silently at runtime months later.
    """
    known_action_types = set()
    for cap in config.capabilities:
        known_action_types.update(cap.action_types)

    seed_actions = {ep.action for ep in config.seed_corpus}
    orphan_seed_actions = {
        a for a in seed_actions
        if a != "wait_and_monitor" and a not in known_action_types
    }
    if orphan_seed_actions:
        raise RoleConfigError(
            f"{config.source_path}: seed_corpus references action(s) "
            f"{sorted(orphan_seed_actions)} that no mcp_capabilities entry "
            f"declares in action_types. These episodes would be inert — "
            f"the ActionSelector will never recognise them (lesson 2)."
        )

    # Softer check: capability action_types with zero seed coverage are
    # allowed (a new role may start unseeded) but worth a warning, not
    # a hard failure — surfaced via warnings, not exceptions.
    import warnings
    unseeded = known_action_types - seed_actions
    if unseeded:
        warnings.warn(
            f"{config.source_path}: action_type(s) {sorted(unseeded)} have "
            f"no seed_corpus episode — the agent starts with zero "
            f"professional intuition for them.",
            stacklevel=2,
        )


def build_tool_registry(agent_id: str, config: RoleConfig) -> MCPToolRegistry:
    registry = MCPToolRegistry(agent_id)
    for capability in config.capabilities:
        registry.register(capability)
    return registry


def build_encoder(config: RoleConfig) -> BusinessEventEncoder:
    return BusinessEventEncoder(config.affective_mapping)


def build_seeder(config: RoleConfig) -> BusinessHippocampusSeeder:
    return BusinessHippocampusSeeder(list(config.seed_corpus))


def resolve_motor_adapter(
    config: RoleConfig, tool_registry: MCPToolRegistry
) -> MotorAdapter:
    """Dynamically import and instantiate the role's MotorAdapter subclass.

    Validates the imported object actually subclasses MotorAdapter — a
    typo'd or wrong-typed reference fails at load time with a clear
    message, not with an obscure AttributeError deep inside run_cycle().
    """
    cls = _import_ref(config.motor_adapter_path, config.source_path, "motor_adapter")
    if not (isinstance(cls, type) and issubclass(cls, MotorAdapter)):
        raise RoleConfigError(
            f"{config.source_path}: motor_adapter '{config.motor_adapter_path}' "
            f"does not resolve to a MotorAdapter subclass"
        )
    return cls(tool_registry)


def resolve_event_classifier(config: RoleConfig) -> Callable[[str, dict], list]:
    fn = _import_ref(config.event_classifier_path, config.source_path, "event_classifier")
    if not callable(fn):
        raise RoleConfigError(
            f"{config.source_path}: event_classifier "
            f"'{config.event_classifier_path}' is not callable"
        )
    return fn


def _import_ref(ref: str, path: str, field_name: str) -> Any:
    module_path, _, attr_name = ref.partition(":")
    if not module_path or not attr_name:
        raise RoleConfigError(
            f"{path}: '{field_name}' value '{ref}' must be 'module:Attribute'"
        )
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise RoleConfigError(f"{path}: cannot import '{module_path}': {exc}") from exc
    obj = getattr(module, attr_name, None)
    if obj is None:
        raise RoleConfigError(
            f"{path}: '{module_path}' has no attribute '{attr_name}'"
        )
    return obj


__all__ = [
    "RoleConfig",
    "RoleConfigError",
    "load_role_config",
    "validate_role_config",
    "build_tool_registry",
    "build_encoder",
    "build_seeder",
    "resolve_motor_adapter",
    "resolve_event_classifier",
]
```

---

## 4. Migration of the existing procurement role

### 4.1 What moves into `config.yaml`

From `BodyLabSession._build_runtime()` (Phase 1), four `MCPCapability` registrations and `AFFECTIVE_MAPPING` move into YAML value for value. The corresponding inline code is removed from that file; `BodyLabSession` calls `load_role_config` + `build_*` instead of assembling the objects by hand.

### 4.2 Seed corpus — the path of least resistance

`PROCUREMENT_SEED_EPISODES` in `seed_corpus.py` need **not** be rewritten into YAML immediately — `config.yaml` may refer to it through `seed_corpus_module: "nowa_roles.procurement.seed_corpus:PROCUREMENT_SEED_EPISODES"` (section 3, `_load_seed_corpus_from_module`). This gives zero regression risk for an already verified corpus. A move into pure YAML is a separate, non-blocking task (when a procurement expert actually needs to edit intuition without Python).

### 4.3 What is not moved

`motor_adapter.py` and `event_classifier.py` remain as they are — `config.yaml` only points at them by the path `module:Attribute`.

---

## 5. Update of `BodyLabSession`

```python
def _build_runtime(self) -> None:
    from nowa_body.role_config import (
        load_role_config, build_tool_registry, build_encoder,
        build_seeder, resolve_motor_adapter, resolve_event_classifier,
    )

    config = load_role_config(
        str(Path(__file__).resolve().parents[2] / "nowa_roles" / "procurement" / "config.yaml")
    )
    self.registry = build_tool_registry(self.settings.agent_id, config)
    encoder = build_encoder(config)
    seeder = build_seeder(config)
    motor_adapter = resolve_motor_adapter(config, self.registry)
    event_classifier = resolve_event_classifier(config)

    if self.settings.seed_intuition:
        seeder.seed_agent(self.agent)

    # requires_approval override for auto_execute stays a runtime knob,
    # not a config concern — applied AFTER loading, on the specific
    # capability the lab cares about toggling:
    if self.settings.auto_execute:
        write_cap = self.registry.get(ORDER_TOOL)
        if write_cap is not None:
            write_cap.requires_approval = False

    self.runtime = BusinessAgentRuntime(
        agent=self.agent,
        tool_registry=self.registry,
        motor_adapter=motor_adapter,
        approval_gate=ApprovalGate(
            mcp_executor=self._execute,
            capability_lookup=self.registry.get,
        ),
        encoder=encoder,
        sleep_scheduler=SleepScheduler(...),
        sensor_refresh_interval_s=float(self.settings.sensor_refresh_interval_s),
        simulated_tick_seconds=float(self.settings.seconds_per_tick),
        event_classifier=event_classifier,
    )
```

This is at once a simplification of `BodyLabSession` (less inline data) and the first practical check that the configurator actually works — the laboratory harness becomes the first consumer, not only a test.

---

## 6. Test cases

```python
# test_role_config.py

class TestLoadRoleConfig:

    def test_loads_valid_procurement_config(self, tmp_path):
        config = load_role_config(PROCUREMENT_CONFIG_PATH)
        assert config.role_id == "procurement"
        assert len(config.capabilities) == 4
        assert len(config.seed_corpus) == 8

    def test_missing_file_raises(self):
        with pytest.raises(RoleConfigError, match="not found"):
            load_role_config("/nonexistent/config.yaml")

    def test_invalid_risk_level_raises_with_valid_options_listed(self, tmp_path):
        path = _write_config(tmp_path, mcp_capabilities=[
            {"tool_id": "x", "risk_level": "super_dangerous"}
        ])
        with pytest.raises(RoleConfigError, match="read_only"):
            load_role_config(path)


class TestValidateRoleConfig:

    def test_orphan_seed_action_raises(self, tmp_path):
        """The exact bug class this project has hit three times: a seed
        episode's action label that no capability declares."""
        path = _write_config(
            tmp_path,
            mcp_capabilities=[{
                "tool_id": "x", "risk_level": "read_only",
                "action_types": ["known_action"],
            }],
            seed_corpus=[{
                "context_tokens": ["a"], "action": "unknown_action",
                "consequence": "c", "reward": 0.1,
            }],
        )
        with pytest.raises(RoleConfigError, match="unknown_action"):
            load_role_config(path)

    def test_wait_and_monitor_never_flagged_as_orphan(self, tmp_path):
        """wait_and_monitor needs no capability — it means 'do nothing'."""
        path = _write_config(
            tmp_path,
            mcp_capabilities=[],
            seed_corpus=[{
                "context_tokens": ["a"], "action": "wait_and_monitor",
                "consequence": "c", "reward": 0.1,
            }],
        )
        load_role_config(path)  # must not raise

    def test_unseeded_action_type_warns_not_raises(self, tmp_path):
        path = _write_config(
            tmp_path,
            mcp_capabilities=[{
                "tool_id": "x", "risk_level": "read_only",
                "action_types": ["never_seeded"],
            }],
            seed_corpus=[],
        )
        with pytest.warns(UserWarning, match="never_seeded"):
            load_role_config(path)


class TestSeedCorpusModuleReference:

    def test_inline_and_module_together_raises(self, tmp_path):
        path = _write_config(
            tmp_path,
            seed_corpus=[{"action": "a", "context_tokens": [], "consequence": "c", "reward": 0.0}],
            extra={"seed_corpus_module": "nowa_roles.procurement.seed_corpus:PROCUREMENT_SEED_EPISODES"},
        )
        with pytest.raises(RoleConfigError, match="not both"):
            load_role_config(path)

    def test_module_reference_loads_existing_corpus(self, tmp_path):
        path = _write_config(
            tmp_path, seed_corpus=None,
            extra={"seed_corpus_module": "nowa_roles.procurement.seed_corpus:PROCUREMENT_SEED_EPISODES"},
        )
        config = load_role_config(path)
        assert len(config.seed_corpus) == 8


class TestResolveMotorAdapter:

    def test_non_motor_adapter_subclass_raises(self, tmp_path):
        path = _write_config(tmp_path, extra={
            "motor_adapter": "builtins:dict"  # not a MotorAdapter subclass
        })
        config = load_role_config(path)
        with pytest.raises(RoleConfigError, match="MotorAdapter subclass"):
            resolve_motor_adapter(config, MCPToolRegistry("test"))

    def test_valid_motor_adapter_resolves(self):
        config = load_role_config(PROCUREMENT_CONFIG_PATH)
        registry = build_tool_registry("test", config)
        adapter = resolve_motor_adapter(config, registry)
        assert isinstance(adapter, MotorAdapter)


class TestBuildHelpers:

    def test_build_tool_registry_registers_all_capabilities(self):
        config = load_role_config(PROCUREMENT_CONFIG_PATH)
        registry = build_tool_registry("test", config)
        assert len(registry.list_all()) == 4

    def test_build_seeder_seeds_agent(self):
        config = load_role_config(PROCUREMENT_CONFIG_PATH)
        seeder = build_seeder(config)
        agent = make_test_agent()
        n = seeder.seed_agent(agent)
        assert n == 8
```

---

## 7. Constraints

| # | Constraint |
|---|---|
| **C1** | `validate_role_config` is called inside `load_role_config` unconditionally — it is impossible to obtain a `RoleConfig` with orphan seed-actions |
| **C2** | `seed_corpus` and `seed_corpus_module` are mutually exclusive — both set at once is an error, not a priority of one over the other |
| **C3** | `_import_ref` executes no arbitrary code beyond `importlib.import_module` + `getattr` — not `eval`, not `exec` |
| **C4** | `resolve_motor_adapter` checks `issubclass(cls, MotorAdapter)` before instantiation — a type error is caught before the object is created, not at the runtime of the first `resolve()` |
| **C5** | Config errors are always `RoleConfigError` naming the specific file and field, never a generic `Exception`/`KeyError` |

---

## 8. Definition of Done

- [ ] `role_config.py` is implemented, all functions of section 3
- [ ] `nowa_roles/procurement/config.yaml` is created and moves the data from `BodyLabSession` (4 capabilities + affective mapping) value for value
- [ ] `config.yaml` refers to the seed corpus through `seed_corpus_module` (it does not rewrite `PROCUREMENT_SEED_EPISODES` anew — section 4.2)
- [ ] `BodyLabSession._build_runtime` is rewritten to use `load_role_config` + `build_*` (section 5)
- [ ] All tests of section 6 are green, including `test_orphan_seed_action_raises` — this is the principal test, proving that the configurator catches the class of error that passed unnoticed three times in this project
- [ ] A full run of `BodyLabSession` over several ticks after the migration — behaviour identical to the pre-implementation state (a regression check against `episode_rows()`/`snapshot()` already collected before and after the migration)

---

## 9. What this opens for future roles

Adding a salesperson role now requires:

1. `nowa_roles/sales/config.yaml` — new capability/affective/seed data
2. `nowa_roles/sales/motor_adapter.py` — `SalesBodyMotorAdapter(MotorAdapter)` with role-specific parameterisation logic (for example, "offer a discount", "escalate to a manager")
3. `nowa_roles/sales/event_classifier.py` — its own classification of MCP responses

No file under `nowa_body/` is touched. This is the direct fulfilment of the goal stated at the very beginning of the architecture discussion: "a universal body once, roles as configuration and pinpoint code on top".

---

*Role configurator specification v1.0. Ready to hand to the implementing agent.*
