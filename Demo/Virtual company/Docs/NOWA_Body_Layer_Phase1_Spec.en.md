## Abstract

Russian version: [NOWA_Body_Layer_Phase1_Spec.ru.md](NOWA_Body_Layer_Phase1_Spec.ru.md)

The Phase 1 specification carries the cognitive order of sandbox version 2.0 into the universal body layer `nowa_body`, which is not bound to one role or to one external system. Three lessons of the sandbox become obligatory. A `Path` is immutable and is built by reassigning the result of `add_event`. The selector forms pressure only from events of type `ACTION`, so every seed episode contains exactly one such event; a corpus of context tokens alone sits in the hippocampus and creates no pressure. A call to `agent.step` with `decision_only=True` runs activation, the selector, the basal ganglia, and the thalamic gate and does not write the outcome; the body's host writes the episode after the outcome is known. The approval gate, which the sandbox deliberately lacked, becomes the boundary of a write into the external world.

The phase pipeline is arranged as follows. A read-tool result is encoded into `context_events`. The agent step returns an intention. `MotorAdapter` builds a `ProposedAction` that has not yet been executed. `ApprovalGate` executes a read and an explicitly permitted autonomy at once, or places any other write on a human queue. After execution, the outcome encoder updates affective state and the hippocampus, and the episode path again contains an `ACTION` event. `sleep_cycle` is called periodically. An `MCPCapability` record receives a list of `action_types`, so that one tool can serve several selector strategies. `BusinessHippocampusSeeder` is domain-neutral: the corpus is supplied from outside, it touches only `store` and `reinforce`, and it does not alter affective space, neuromodulators, or the value layer. `MockMCPClient` lets the phase be run without a live server.

The cognitive step does not receive a protocol object: the core does not import an MCP description. One agent's capability registry is separate from the transport connection, which may be shared. A high or irreversible write requires approval, and configuration does not lift that constraint. Connection of a real accounting server is deferred until the procurement motor path already analysed in the sandbox has been carried over. Still open at the time of this specification are the moment at which sleep is invoked, the rate of the step relative to sensor polling, and the format of the intention summary shown to a person.

---

# NOWA Body Layer — Phase 1 Specification

**Version:** 1.0
**Parent document:** NOWA_Virtual_Employees_Architecture_Spec.md (sections 1–4)
**Premise:** NOWA_Procurement_Sandbox_Spec v2.0 — the refactoring confirmed
a working cognitive pipeline on a simulated world
**Status:** Ready for implementation
**Goal:** A universal "body" layer — it turns any MCP server into
sensors and muscles of a NOWA agent, without binding to a particular role or system.

---

## 0. Principles (inherited + lessons from the sandbox)

Inherited unchanged from the architecture specification: the agent is
a sovereign unit; the approval gate lies outside the cognitive contour;
money is not valence.

### Three concrete lessons from the sandbox v2.0 refactoring, obligatory here

**Lesson 1 — `Path` is immutable.** `path.add_event(e)` returns a new
`Path` and does not mutate the existing one. Any code that builds a path in a loop does so by
reassignment `path = path.add_event(e)`, and not by a bare call.

**Lesson 2 — The selector reads only `EventType.ACTION` events.**
`ActionSelector.compute_pressures()` forms pressure on actions on
the basis of which `EventType.ACTION` tokens have historically been associated
with the given context. A seed episode made only of `EventType.CONTEXT` tokens
physically lies in the hippocampus, but **creates no pressure** —
a silent no-op. Every seed episode must contain an `action:<label>`
event with `EventType.ACTION`.

**Lesson 3 — Decision/consolidation split via `decision_only=True`.**
`Agent.step(context_events, decision_only=True)` runs the whole pipeline
(`hippocampus.activate → selector → BG → Thalamic`) and returns an action,
but does not write to hippocampus/value_layer/affective regulation. The host
(here, the body-layer runtime) itself writes the episode **after** it
has learned the real outcome of the action — otherwise the episode is marked with a result
that has not yet occurred.

---

## 1. Pipeline architecture (updated for a live MCP)

```
MCP Server (READ_ONLY tool)
    ↓ tool result
BusinessEventEncoder.encode_tool_result()
    → context_events: List[str]
    ↓
agent.step(context_events, decision_only=True)
    (hippocampus.activate → selector.compute_pressures →
     BasalGangliaGate → ThalamicGate)
    → action_intent
    ↓
MotorAdapter.resolve(action_intent, observations)
    → ProposedAction (not yet executed)
    ↓
ApprovalGate.route(proposed_action)
    ├── READ_ONLY / permitted autonomy → execute immediately
    └── otherwise → a queue for human approval
    ↓ (after execution, a real one or a human approve)
MCP Server (WRITE tool call)
    → result
    ↓
BusinessEventEncoder.encode_action_outcome(result)
    → affective_inputs + episode_tokens (with EventType.ACTION!)
    ↓
agent.affective_space.step(affective_inputs)
agent.hippocampus.store(path_with_action_event, consequence, reward)
    ↓ (periodically)
agent.sleep_manager.sleep_cycle()
```

This is a direct continuation of the scheme in the parent specification (section 1),
refined by the three lessons of section 0.

---

## 2. Project structure

```
nowa_body/
├── __init__.py
├── mcp_capability.py          # MCPCapability, CapabilityRisk
├── risk_classifier.py         # heuristics for classifying tool risk
├── tool_registry.py           # MCPToolRegistry
├── business_event_encoder.py  # Sensory Adapter
├── business_hippocampus_seeder.py  # professional intuition (ACTION-aware)
├── motor_adapter.py           # generic MotorAdapter + ProposedAction
├── approval_gate.py           # ApprovalGate (external barrier)
├── hard_constraints.py        # invariants that configuration cannot bypass
├── mock_mcp.py                # a test MCP without a real server
├── runtime.py                 # orchestrator of the full pipeline
├── tests/
│   ├── conftest.py
│   ├── test_mcp_capability.py
│   ├── test_risk_classifier.py
│   ├── test_tool_registry.py
│   ├── test_business_event_encoder.py
│   ├── test_business_hippocampus_seeder.py
│   ├── test_motor_adapter.py
│   ├── test_approval_gate.py
│   ├── test_agent_pipeline_order.py   # analogue of test_agent_pipeline.py from the sandbox
│   └── test_integration.py
└── requirements.txt
```

---

## 3. `mcp_capability.py`

The implementation is unchanged relative to the parent specification
(section 2.2) — the contract is fixed and has already been checked in substance. One
refinement under the sandbox lessons:

```python
@dataclass
class MCPCapability:
    tool_id: str
    server_name: str
    display_name: str
    description: str
    risk_level: CapabilityRisk
    domain_tags: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = True
    cost_impact_estimate: Optional[str] = None
    max_autonomous_value: Optional[float] = None

    # NEW: an explicit link from a capability to the agent's action strategies.
    # Analogue of SUPPLIER_STRATEGIES from ProcurementMotorAdapter — MotorAdapter
    # must know which action_type values from the agent resolve to a call of THIS
    # tool in particular. Without this link MotorAdapter cannot match
    # ActionIntent → a concrete MCP call when several write tools
    # share one domain.
    action_types: List[str] = field(default_factory=list)
    """Action labels the agent's ActionSelector can choose that this
    capability fulfils. E.g. tool_id="mcp__email__send" might have
    action_types=["notify_supplier_urgent", "send_followup"]."""
```

---

## 4. `business_hippocampus_seeder.py` — with lesson 2 applied

A direct copy of the structure of `ProcurementHippocampusSeeder`, but domain-agnostic —
the corpus of seed episodes is supplied from outside (it is not hard-coded in the module), because
different roles (buyer, salesperson, accountant) will have different
professional intuitions.

```python
@dataclass
class SeedEpisode:
    context_tokens: List[str]
    action: str              # REQUIRED — becomes EventType.ACTION
    consequence: str
    reward: float
    intensity: float = 0.5
    reinforce: bool = False


class BusinessHippocampusSeeder:
    """
    Domain-agnostic seeder. Same contract as ProcurementHippocampusSeeder
    (parent spec section 5.2, sandbox v2.0):
    - does NOT touch affective_space, neuromodulators, value_layer
    - only hippocampus.store() / hippocampus.reinforce()
    - each Path carries CONTEXT tokens + exactly one ACTION event
      (lesson 2 — without this the corpus is inert)
    - Path built via reassignment, never mutation (lesson 1)
    """

    def __init__(self, episodes: List[SeedEpisode]):
        self.episodes = episodes

    def seed_agent(self, agent: Any) -> int:
        """Returns count of successfully stored episodes."""
        hippocampus = getattr(agent, "hippocampus", None)
        if hippocampus is None or not hasattr(hippocampus, "store"):
            return 0
        added = 0
        for ep in self.episodes:
            try:
                path = self._build_path(ep.context_tokens, ep.action)
                consequence = self._build_consequence(ep.consequence)
                hippocampus.store(
                    path, consequence=consequence,
                    intensity=ep.intensity, reward=ep.reward,
                )
                added += 1
                if ep.reinforce and hasattr(hippocampus, "reinforce"):
                    hippocampus.reinforce(path, consequence=consequence,
                                          intensity=ep.intensity)
            except Exception:
                continue
        return added

    def _build_path(self, tokens: List[str], action: str) -> Any:
        """Reassignment-based (lesson 1); appends one ACTION event (lesson 2)."""
        from experience import Path, Event, EventType
        path = Path()
        for token in tokens:
            path = path.add_event(Event(str(token), EventType.CONTEXT))
        path = path.add_event(Event(f"action:{action}", EventType.ACTION))
        return path

    def _build_consequence(self, label: str) -> Any:
        from experience import Event, EventType
        return Event(str(label), EventType.CONSEQUENCE)
```

### Corpus constructor for a particular role

A role-specific corpus is a separate module, not part of `nowa_body`:

```
nowa_roles/procurement/seed_corpus.py    → List[SeedEpisode]
nowa_roles/sales/seed_corpus.py          → List[SeedEpisode] (future)
```

This reuses `PROFESSIONAL_SEED_EPISODES` from the sandbox directly —
it is enough to wrap the existing dict episodes in `SeedEpisode`.

---

## 5. `business_event_encoder.py` — Sensory Adapter

Difference from the parent specification (section 3.3): `encode_action_outcome`
is added, symmetric to `encode_tool_result`, for
building episode tokens **after** the action has been executed — with the same
lesson 2 (an ACTION event is obligatory for an episode that will go into
`hippocampus.store()`).

```python
class BusinessEventEncoder:
    def __init__(self, affective_mapping: Dict[str, dict]):
        self.affective_mapping = affective_mapping

    def encode_tool_result(
        self, tool_id: str, result: Dict[str, Any],
        event_classifier: Optional[Callable] = None,
    ) -> List[str]:
        """READ observation → context_events. Same as parent spec 3.3."""
        ...

    def encode_action_outcome(
        self, action_type: str, tool_result: Dict[str, Any],
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Build (episode_tokens, affective_inputs) from a completed action's
        real outcome. episode_tokens is CONTEXT-only here — the caller
        (runtime.py) appends the ACTION event, because only the caller
        knows the exact action_type that was actually realized (the
        encoder should not need to re-derive it).

        Returns affective_inputs suitable for agent.affective_space.step().
        """
        status = str(tool_result.get("status", "unknown"))
        if status in ("accepted", "success", "ok"):
            tokens = ["result:success"]
            affective = {"valence": 0.4, "arousal": 0.2, "trust": 0.3}
        elif status in ("rejected", "failed", "error"):
            tokens = ["result:failure"]
            affective = {"valence": -0.4, "arousal": 0.5, "stress": 0.4}
        else:
            tokens = ["result:unknown"]
            affective = {}
        return tokens, affective
```

---

## 6. `motor_adapter.py` — generic MotorAdapter

A direct generalisation of `ProcurementMotorAdapter` (already implemented and verified
in the sandbox). The key difference: instead of `SUPPLIER_STRATEGIES`
(a hard-coded mapping of procurement strategies), the mapping is built from
`MCPCapability.action_types`, obtained from `MCPToolRegistry`.

```python
@dataclass
class ProposedAction:
    action_id: str
    agent_id: str
    tool_id: str
    tool_params: Dict[str, Any]
    risk_level: CapabilityRisk
    intent_summary: str
    affective_context: Dict[str, float]
    estimated_cost_impact: Optional[float] = None
    requires_approval: bool = True


class MotorAdapter:
    """
    Generic body: ActionIntent → ProposedAction.

    Same discipline as ProcurementMotorAdapter (sandbox v2.0, verified):
    - NEVER calls cognitive methods (hippocampus.activate, selector, step)
    - resolve() never raises — malformed observations yield None
    - reads hippocampus.experiences read-only, only for least_used-style
      resolution when several capabilities could serve one action_type
    """

    def __init__(self, tool_registry: MCPToolRegistry):
        self.tool_registry = tool_registry

    def resolve(
        self,
        action_type: str,
        observations: Dict[str, Any],
        hippocampus: Any = None,
    ) -> Optional[ProposedAction]:
        try:
            capability = self._capability_for_action(action_type)
            if capability is None:
                return None
            params = self._build_params(capability, action_type, observations)
            if params is None:
                return None
            return ProposedAction(
                action_id=self._new_id(),
                agent_id=str(observations.get("agent_id", "")),
                tool_id=capability.tool_id,
                tool_params=params,
                risk_level=capability.risk_level,
                intent_summary=self._summarize(action_type, params),
                affective_context=dict(observations.get("affect_snapshot", {})),
                estimated_cost_impact=self._estimate_cost(capability, params),
                requires_approval=capability.requires_approval,
            )
        except Exception:
            return None

    def _capability_for_action(self, action_type: str) -> Optional[MCPCapability]:
        matches = [
            c for c in self.tool_registry._capabilities.values()
            if action_type in c.action_types
        ]
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        # Several capabilities for one action_type — a deterministic
        # choice by alphabetical tool_id, not a random one. Roles with several
        # equivalent tools must prioritise explicitly through
        # registration order, and must not rely on this tie-break.
        return sorted(matches, key=lambda c: c.tool_id)[0]

    def _build_params(
        self, capability: MCPCapability, action_type: str,
        observations: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Domain-specific parameter resolution. Generic MotorAdapter provides
        no default implementation — subclass per role (see
        ProcurementMotorAdapter as the reference: _select_priority_product,
        _select_most_reliable, _calculate_qty, _cap_qty_to_budget all live
        here for the procurement role specifically).
        """
        raise NotImplementedError(
            "Subclass MotorAdapter per role and implement _build_params; "
            "see ProcurementMotorAdapter (sandbox v2.0) as reference."
        )

    def _summarize(self, action_type: str, params: dict) -> str:
        return f"{action_type}({', '.join(f'{k}={v}' for k, v in params.items())})"

    def _estimate_cost(self, capability, params) -> Optional[float]:
        return None  # role-specific override

    def _new_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
```

**Important:** `MotorAdapter` in this phase is an abstract base class.
`ProcurementMotorAdapter` from the sandbox becomes the first concrete
implementation of `_build_params` — when it is carried into Phase 3 (a real MCP)
the structure is reused, but `stock_obs`/`supplier_obs` are replaced
by `observations` from real MCP READ tools.

---

## 7. `approval_gate.py` + `hard_constraints.py`

No substantial changes relative to the parent specification
(sections 6.2, 6.3) — this code was already specified strictly enough
and has no lessons from the sandbox (the approval gate is the only component
that the sandbox deliberately lacked; section 0 of the sandbox specification: "there is
no real money here — place_order is executed immediately").

One addition — `feedback_loop.py` (section 6.4 of the parent specification)
must now build an episode through the same pattern as
`_store_order_experience` in the sandbox:

```python
def apply_feedback_to_agent(agent: Any, record: ApprovalRecord,
                            encoder: BusinessEventEncoder) -> None:
    """
    Direct analogue of SandboxTrainer._store_order_experience (v2.0).
    Called AFTER the human's decision AND (if approved) the real MCP
    execution result — never before, per lesson 3 (decision_only split).
    """
    reward = approval_to_reward(record)
    tokens, affective_inputs = encoder.encode_action_outcome(
        record.proposed_action.intent_summary,
        record.execution_result or {"status": record.status.value},
    )

    affective_space = getattr(agent, "affective_space", None)
    if affective_space is not None and affective_inputs:
        step_fn = getattr(affective_space, "step", None)
        if callable(step_fn):
            step_fn(inputs=affective_inputs)

    hippocampus = getattr(agent, "hippocampus", None)
    if hippocampus is not None and hasattr(hippocampus, "store"):
        from experience import Path, Event, EventType
        path = Path()
        for t in tokens:
            path = path.add_event(Event(t, EventType.CONTEXT))
        # ACTION event — lesson 2 applies here too.
        path = path.add_event(Event(
            f"action:{record.proposed_action.tool_id}", EventType.ACTION
        ))
        consequence = Event(
            "approved" if reward > 0 else "rejected", EventType.CONSEQUENCE
        )
        hippocampus.store(path, consequence=consequence,
                          intensity=abs(reward), reward=reward)
```

---

## 8. `mock_mcp.py` — a test MCP without a real server

Since there are no real MCP servers yet (only a planned connection
to 1C), Phase 1 must be fully testable without them.

```python
class MockMCPTool:
    """One fake tool: deterministic responses for tests, keyed by input hash."""

    def __init__(self, tool_id: str, response_fn: Callable[[dict], dict]):
        self.tool_id = tool_id
        self.response_fn = response_fn
        self.call_log: List[dict] = []

    def __call__(self, params: dict) -> dict:
        self.call_log.append(dict(params))
        return self.response_fn(params)


class MockMCPClient:
    """
    Registers MockMCPTool instances and dispatches by tool_id — this is
    the `mcp_executor: Callable[[str, dict], Any]` that ApprovalGate expects.
    Never touches a network; safe for CI without real MCP servers.
    """

    def __init__(self):
        self.tools: Dict[str, MockMCPTool] = {}

    def register(self, tool: MockMCPTool) -> None:
        self.tools[tool.tool_id] = tool

    def execute(self, tool_id: str, params: dict) -> dict:
        tool = self.tools.get(tool_id)
        if tool is None:
            return {"status": "error", "reason": f"unknown_tool:{tool_id}"}
        return tool(params)
```

Role tests (procurement and later) build a set of `MockMCPTool`
instances that imitate `get_stock_levels`, `create_purchase_order`, and so on, with
behaviour that repeats `ProcurementWorld` from the sandbox — this allows
the intuition already accumulated about scenarios (stockout,
supplier_defaulted) to be reused without a real MCP.

---

## 9. `runtime.py` — orchestrator of the full pipeline

An analogue of `SandboxTrainer._run_single_quarter`, but for a live or semi-live
mode: not a quarter of 90 ticks, but one cycle per incoming event
(for example, a daily cron, or a trigger on a new MCP notification).

```python
class BusinessAgentRuntime:
    """
    Live/semi-live pipeline orchestrator. One call to run_cycle() =
    one full pass: observe → decide → resolve → gate → (execute) →
    feedback → store.

    Sleep is NOT triggered here automatically — a host process (cron,
    scheduler) calls agent.sleep_manager.sleep_cycle() on its own
    schedule, exactly as SandboxTrainer does on sleep_every_n_days,
    but decoupled from run_cycle() since live cadence is host-defined,
    not a fixed N-day sandbox quarter.
    """

    def __init__(
        self,
        agent: Any,
        tool_registry: MCPToolRegistry,
        motor_adapter: MotorAdapter,
        approval_gate: ApprovalGate,
        encoder: BusinessEventEncoder,
    ):
        self.agent = agent
        self.tool_registry = tool_registry
        self.motor_adapter = motor_adapter
        self.approval_gate = approval_gate
        self.encoder = encoder

    def run_cycle(self, observations: Dict[str, Any]) -> dict:
        """
        observations: pre-fetched results of READ_ONLY MCP calls, built
        by the host BEFORE calling run_cycle — this runtime does not
        itself decide which sensors to poll; that's a host/scheduling
        concern, same separation as ProcurementWorld.observe_* being
        called by SandboxTrainer, not by the agent.
        """
        context_events = self._build_context(observations)

        step_fn = getattr(self.agent, "step", None)
        action_intent = step_fn(context_events, decision_only=True) \
            if callable(step_fn) else "wait_and_monitor"
        action_type = self._intent_to_action_type(action_intent)

        proposed = self.motor_adapter.resolve(
            action_type, observations,
            hippocampus=getattr(self.agent, "hippocampus", None),
        )
        if proposed is None:
            return {"action_type": action_type, "proposed": None}

        record = self.approval_gate.route(proposed)
        if record.executed:
            self._apply_feedback(record)
        return {
            "action_type": action_type,
            "proposed": proposed,
            "approval_status": record.status.value,
        }

    def _build_context(self, observations: Dict[str, Any]) -> List[str]:
        tokens: List[str] = []
        for tool_id, result in observations.get("tool_results", {}).items():
            tokens.extend(self.encoder.encode_tool_result(tool_id, result))
        return tokens or ["quiet_period"]

    def _intent_to_action_type(self, action_intent: Any) -> str:
        # Identical logic to SandboxTrainer._intent_to_action_type (v2.0)
        if isinstance(action_intent, str):
            return action_intent
        if action_intent is None:
            return "wait_and_monitor"
        for attr in ("action_type", "action", "label", "name"):
            value = getattr(action_intent, attr, None)
            if isinstance(value, str):
                return value
        return "wait_and_monitor"

    def _apply_feedback(self, record: ApprovalRecord) -> None:
        from .feedback_loop import apply_feedback_to_agent
        apply_feedback_to_agent(self.agent, record, self.encoder)
```

---

## 10. Constraints

| # | Constraint | Inheritance |
|---|---|---|
| **B1** | `MotorAdapter.resolve()` does not call `hippocampus.activate()`, `selector`, `agent.step()` | R2, confirmed in sandbox v2.0 |
| **B2** | Every seed episode must contain exactly one `EventType.ACTION` token | Lesson 2 |
| **B3** | A `Path` is built by reassignment and is never mutated in place | Lesson 1 |
| **B4** | `agent.step(..., decision_only=True)` is used throughout the runtime; a full `step()` without the flag is not called in the body — learning occurs only in `sleep_cycle()` | Lesson 3, R3/R4 |
| **B5** | `ApprovalGate` is the only point at which write tools are executed; `MotorAdapter`/`runtime.py` never call MCP execute directly | Parent specification, section 6.2 |
| **B6** | A HIGH_WRITE/IRREVERSIBLE capability cannot have `requires_approval=False` — `assert_stage2_invariant` is called in `ApprovalGate.route()` unconditionally | Parent specification, section 6.3 |
| **B7** | `apply_feedback_to_agent` is called only after real execution (`record.executed`), never before | Lesson 3 |

---

## 11. Test cases (the key ones, not an exhaustive list — on the model of the sandbox)

```python
# test_business_hippocampus_seeder.py

def test_seed_episode_without_action_raises_or_defaults():
    """SeedEpisode requires .action; a missing/empty action should not
    silently produce an inert (CONTEXT-only) path — lesson 2."""
    with pytest.raises(TypeError):
        SeedEpisode(context_tokens=["x"], consequence="y", reward=0.1)
        # action is a required positional/keyword field — dataclass enforces

def test_seeded_path_contains_action_event():
    seeder = BusinessHippocampusSeeder([
        SeedEpisode(["event:x"], action="do_thing", consequence="ok", reward=0.5)
    ])
    agent = make_test_agent()
    seeder.seed_agent(agent)
    stored_path = agent.hippocampus.experiences[0].path
    action_events = [e for e in stored_path.events if e.event_type == EventType.ACTION]
    assert len(action_events) == 1
    assert action_events[0].name == "action:do_thing"

def test_seeder_only_touches_hippocampus():
    # identical structure to sandbox test_seeder_only_touches_hippocampus
    ...


# test_motor_adapter.py

def test_resolve_never_raises_on_garbage_observations():
    adapter = SomeRoleMotorAdapter(registry)
    result = adapter.resolve("some_action", {"garbage": object()})
    assert result is None  # not an exception

def test_resolve_does_not_call_hippocampus_activate():
    mock_hippo = MagicMock()
    mock_hippo.experiences = []
    adapter.resolve("some_action", observations, hippocampus=mock_hippo)
    mock_hippo.activate.assert_not_called()


# test_approval_gate.py

def test_high_write_cannot_bypass_approval():
    cap = MCPCapability(
        tool_id="x", server_name="y", display_name="z", description="",
        risk_level=CapabilityRisk.HIGH_WRITE, requires_approval=False,
    )
    with pytest.raises(HardConstraintViolation):
        assert_stage2_invariant(cap)

def test_read_only_executes_immediately():
    gate = ApprovalGate(mcp_executor=mock_executor)
    proposed = ProposedAction(..., risk_level=CapabilityRisk.READ_ONLY,
                              requires_approval=False)
    record = gate.route(proposed)
    assert record.status == ApprovalStatus.APPROVED
    assert record.executed is True


# test_agent_pipeline_order.py — analogue of sandbox test_agent_pipeline.py

def test_runtime_calls_step_before_motor_adapter():
    # same ordering assertion pattern as sandbox test_agent_step_called_before_motor_adapter
    ...

def test_feedback_applied_only_after_real_execution():
    """B7: apply_feedback_to_agent must not run before record.executed."""
    ...
```

---

## 12. Definition of Done

- [ ] All 9 modules of `nowa_body/` are implemented
- [ ] `MockMCPClient` covers at least a READ and one WRITE operation for
      an end-to-end test without a real MCP
- [ ] `BusinessHippocampusSeeder` — the test for an ACTION event is green
- [ ] `MotorAdapter.resolve()` — the test for the absence of calls to
      `hippocampus.activate()` is green
- [ ] `ApprovalGate` — the test that approval cannot be bypassed for
      HIGH_WRITE is green
- [ ] `BusinessAgentRuntime.run_cycle()` — an integration test: a full
      cycle observe→decide→resolve→gate→feedback on MockMCP, without
      exceptions
- [ ] No component of `nowa_body` imports `nowa_sandbox` —
      this is a parallel layer that does not depend on the sandbox (although
      it reuses the sandbox as a reference implementation for
      `ProcurementMotorAdapter._build_params`)

---

## 13. Carrying `ProcurementMotorAdapter` out of the sandbox (the next step)

After Phase 1 is complete (sections 1–12), `ProcurementMotorAdapter` from
`nowa_sandbox` is refactored into `nowa_roles/procurement/motor_adapter.py`,
inheriting from the generic `nowa_body.MotorAdapter`:

```python
class ProcurementBodyMotorAdapter(MotorAdapter):
    def _build_params(self, capability, action_type, observations):
        # Reuses _select_priority_product, _select_most_reliable,
        # and so on from the sandbox ProcurementMotorAdapter almost verbatim —
        # the only difference is the source of observations: previously
        # world.observe_stock_levels(), now the result of a READ_ONLY
        # MCP call (for example, 1C get_stock_levels), already normalised
        # by BusinessEventEncoder to the same dictionary format.
        ...
```

This is the last bridge between the sandbox and a real body — the details
are carried into a separate document when a test 1C database appears
(Phase 3 of the parent specification).

---

*Phase 1 specification v1.0. Ready to be handed to the implementing agent.*
*Lessons 1–3 from the sandbox are obligatory — they are not hypothetical,
but were found empirically during the v2.0 refactoring.*

---

## 14. Separation: capability registry versus the MCP connection

An important refinement, not stated explicitly in the parent specification:
**`MCPToolRegistry` belongs to the agent (sovereignty), but the connection to
the MCP server is shared infrastructure.**

```
Shared infrastructure (may be shared):
  MockMCPClient / a real MCP transport
  ↓ (many agents MAY use one connection to 1C)

Per-agent (sovereignty, never shared):
  agent_A.tool_registry: MCPToolRegistry   → sees only its own capabilities
  agent_B.tool_registry: MCPToolRegistry   → sees only its own capabilities
```

Example: a buyer and an accountant may both technically have access to one
and the same 1C MCP server — but the buyer's `tool_registry` registers
only `get_stock_levels` and `create_purchase_order`, while the accountant's
`tool_registry` registers only `get_invoices` and `post_payment`. These are not two different
MCP servers; they are two different **visibility slices** of one server,
defined at the level of `MCPToolRegistry.register()`, not at the level of
the transport.

**Requirement:** `BusinessAgentRuntime` never stores a reference to
a "global" MCP client — only to the `tool_registry`, which has already
been filtered for a particular agent at initialisation. This is a direct
continuation of the sovereignty principle (section 0, item 1 of the parent
specification) onto the level of integration with the external world.

---

## 15. Update of `tool_registry.py` — an index by `action_type`

`MotorAdapter._capability_for_action` from section 6 scans
`self.tool_registry._capabilities.values()` linearly on every call to
`resolve()`. For an agent with a small number of capabilities (5–15 tools) this is not
a problem, but it is better to build an index at once — especially if later
one role gains access to dozens of MCP tools.

```python
class MCPToolRegistry:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._capabilities: Dict[str, MCPCapability] = {}
        self._by_action_type: Dict[str, List[str]] = {}  # action_type → [tool_id, ...]

    def register(self, capability: MCPCapability) -> None:
        self._capabilities[capability.tool_id] = capability
        for action_type in capability.action_types:
            self._by_action_type.setdefault(action_type, []).append(capability.tool_id)

    def capabilities_for_action(self, action_type: str) -> List[MCPCapability]:
        """O(1) lookup instead of MotorAdapter scanning all capabilities."""
        tool_ids = self._by_action_type.get(action_type, [])
        return [self._capabilities[tid] for tid in tool_ids if tid in self._capabilities]

    # ... the rest is unchanged (get, list_by_risk, list_by_domain,
    # sensory_capabilities, motor_capabilities — section 2.3 of the parent
    # specification)
```

The corresponding simplification in `MotorAdapter._capability_for_action`:

```python
def _capability_for_action(self, action_type: str) -> Optional[MCPCapability]:
    matches = self.tool_registry.capabilities_for_action(action_type)
    if not matches:
        return None
    return sorted(matches, key=lambda c: c.tool_id)[0]
```

---

## 16. Implementation order

### Days 1–2: capability layer (without MCP, without an agent)
1. `mcp_capability.py`, `risk_classifier.py` (carried from the parent
   specification, sections 2.2/2.4, unchanged)
2. `tool_registry.py` with an index by action_type (section 15)
3. Tests `test_mcp_capability.py`, `test_risk_classifier.py`,
   `test_tool_registry.py`

### Day 3: sensory + seeding
4. `business_event_encoder.py`
5. `business_hippocampus_seeder.py` — **begin precisely with the test for an ACTION
   event** (section 11), before writing anything else — this is the only
   component where a silent failure (Lesson 2) is invisible without an explicit test
6. `mock_mcp.py`

### Days 4–5: motor + approval
7. `approval_gate.py`, `hard_constraints.py` (carried from the parent
   specification 6.2/6.3; tests are obligatory — money/risk)
8. `motor_adapter.py` as an abstract class + the first concrete
   `ProcurementBodyMotorAdapter` (section 13), using `MockMCPClient`
   instead of `ProcurementWorld`
9. `feedback_loop.py`

### Day 6: assembly
10. `runtime.py`
11. `test_agent_pipeline_order.py`, `test_integration.py` — a full
    cycle on MockMCP; compare behaviour with an equivalent day in
    the sandbox (the same action_type on the same context should
    yield a comparable decision if the agent is restored from the same
    checkpoint)

### Day 7: diagnostics and documentation
12. Run `test_integration.py` repeatedly with different MockMCP
    scenarios (success, rejected, tool timeout) — make sure that
    `apply_feedback_to_agent` does not fail on any of them
13. Record a differences log: how the behaviour of `BusinessAgentRuntime`
    on MockMCP differs from `SandboxTrainer` on `ProcurementWorld` —
    this will be the checklist for Phase 3 (a real MCP)

---

## 17. Open questions

### Q-Phase1-1: Who calls `sleep_cycle()` in live mode

In the sandbox, `SandboxTrainer` itself decides when
`sleep_every_n_days` has arrived. In live mode this must be an external scheduler
(a cron or Cowork task), not `runtime.py` itself — because a "day" for a real
employee is not identical to the number of calls to `run_cycle()` (the agent may
process several events in an hour, or stand idle for days). It is necessary
to decide: `sleep_cycle()` is triggered by calendar time (once a
day, at night) or by the number of episodes accumulated since the last
sleep. The recommendation for Phase 1 is a calendar trigger outside `nowa_body`,
not inside it; `nowa_body` only exposes `agent.sleep_manager`
for an external call.

### Q-Phase1-2: What to do with several `ProposedAction` values in one cycle

The current `run_cycle()` produces at most one action per call —
a direct inheritance from one tick in the sandbox. In reality, in one
day a buyer may want both to order goods and to write a letter
to a supplier about a delay. It is necessary to decide: `agent.step()` should be called
many times in one `run_cycle()` (several successive decisions
with a context update between them), or `ActionSelector` should be able
to return several parallel `ActionIntent` values. The recommendation is to begin
with one action per cycle (as in the sandbox), and to extend only if
it becomes a bottleneck.

### Q-Phase1-3: The format of `intent_summary` for the approval UI

`ProposedAction.intent_summary` is at present a simple string from `_summarize()`.
For a real approval UI (Slack/email, section 6.2 of the parent
specification) a person needs not "place_order_reliable_supplier(...)", but
a human-readable explanation — this is either an NLG layer (section 4.1 of the parent
specification) or a role-specific templater. It does not block Phase 1
(MockMCP approval is tested through raw data), but it is obligatory for
real human approval in Phase 2.

---

## 18. Glossary (new terms of Phase 1)

| Term | Definition |
|---|---|
| **decision_only** | A flag of `agent.step()`; it runs the cognitive pipeline without writing to memory or learning |
| **ACTION event** | An `EventType.ACTION` token in a `Path` — the only event type read by `ActionSelector.compute_pressures()` |
| **capability view** | A filtered per-agent slice of `MCPToolRegistry` over a shared MCP connection |
| **ProposedAction** | The result of `MotorAdapter.resolve()` — an action not yet executed, but fully parameterised |
| **MockMCPClient** | A deterministic substitute for a real MCP transport, for tests without a network |
| **run_cycle** | One full pass of `BusinessAgentRuntime`: observe → decide → resolve → gate → feedback |

---

## 19. Relation to the original request

This document answers the question "how to make it universal" from the very
beginning of the discussion (section 1 of the parent specification, the answer to "I do not have
1 concrete MCP servers right now, but… I think we ought to
try to make this universal somehow"): `MCPCapability`/`MCPToolRegistry`
do not know about 1C, email, CRM, or anything else — they know only about
the abstract contract "a tool with a risk and action_types". `MockMCPClient`
demonstrates this universality in practice: the whole of `nowa_body` is tested
and works **before** the first real MCP connection appears, and
the only thing that will change in Phase 3 is the transport implementation under
`mcp_executor: Callable[[str, dict], Any]`, which `ApprovalGate` expects.

---

*Phase 1 specification — final version. Sections 1–19.*
*Ready to be handed to the implementing agent.*
