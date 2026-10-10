# NOWA Body Layer — Patch v1.2

Russian version: [NOWA_Body_Layer_Phase1_Patch_v1.2.ru.md](NOWA_Body_Layer_Phase1_Patch_v1.2.ru.md)

## Abstract

Patch v1.2 removes a gap confirmed by a line-by-line reading of the Phase 1.0 and 1.1 implementation, at the boundary of the motor adapter and the feedback loop. `ProcurementBodyMotorAdapter._build_params` writes the strategy chosen by the agent into the action parameters' `strategy` field. `apply_feedback_to_agent` built the `ACTION` event from `tool_id`. The laboratory session's order tool serves all four procurement strategies with one identifier, so every executed order was stored with the token `action:mcp__1c__create_purchase_order`. That token is absent from the `ActionSelector` vocabulary, which contains the four strategies and `wait_and_monitor`. The selector reads only known events of type `ACTION`, so the episode remains in the hippocampus and changes pressure on no strategy. The seed corpus still sets the initial pressure; experience after real execution does not correct it. The seeder, under the same review, is judged correctly implemented, and the defect is localised in the feedback loop.

The correction introduces `_resolve_action_label`. If `tool_params` contains a non-empty `strategy` string, the event is built as `action:` followed by that string. Otherwise the previous `tool_id` is kept, which remains correct for a role in which one tool corresponds to one strategy. Adding an `action_type` field to the universal `ProposedAction` is declined: not every role has an internal strategy inside one tool, and an empty field would be dead weight on the common contract. The meaning of the label stays with the role. The affective step and the call to `store` are otherwise unchanged; the path is still built by reassignment and contains exactly one `ACTION` event.

The regression test is built on this scenario: after execution, the hippocampus must contain the agent's strategy, not the identifier of a tool that serves several strategies. A role without a `strategy` key must keep the previous behaviour with `tool_id`. The patch does not change sandbox physics and does not change the sleep scheduler.

---

**Base documents:**
- NOWA_Body_Layer_Phase1_Spec.md (v1.0)
- NOWA_Body_Layer_Phase1_Patch_v1.1.md (SleepScheduler + tick model)

**Status:** ready for implementation — the only blocking defect
found in a line-by-line review of the v1.0/v1.1 implementation

---

## Diagnosis (confirmed by a line-by-line reading of the code, not a hypothesis)

`ProcurementBodyMotorAdapter._build_params` correctly places the strategy
chosen by the agent into the action parameters:

```python
return {
    "supplier_id": str(supplier_id),
    "product_id": str(priority_product),
    "qty": qty,
    "strategy": str(action_type),   # ← "urgent_reorder" и т.п.
    "confidence": self._estimate_confidence(action_type, supplier_obs),
}
```
But `feedback_loop.py::apply_feedback_to_agent` builds the ACTION event
of the episode not from that field, but from `tool_id`:

```python
path = path.add_event(
    event_cls(f"action:{record.proposed_action.tool_id}", event_type.ACTION)
)
```
`ORDER_TOOL` in the registry (`BodyLabSession`) serves all four
procurement strategies at once:

```python
MCPCapability(
    tool_id=ORDER_TOOL,
    action_types=list(PROCUREMENT_ACTION_TYPES),  # все 4 → один tool_id
)
```
**Consequence:** every order that is actually executed — whether it was
`urgent_reorder`, `diversify_supplier`, or
`place_order_cheap_supplier` — is stored in the hippocampus with one and the
same ACTION token `"action:mcp__1c__create_purchase_order"`. That
token is absent from the `ActionSelector` vocabulary (which contains only the four procurement
strategies plus `wait_and_monitor`). By Lesson 2 (the parent specification,
section 0), `ActionSelector.compute_pressures()` reads only
`EventType.ACTION` events associated with known actions —
an episode with an unknown ACTION token physically lies in memory, but does not
correct the pressure on any real strategy.

**Practical effect:** the seed corpus (`PROCUREMENT_SEED_EPISODES`)
creates the correct initial pressure on all four strategies — that
works. But live experience after real execution **never
reinforces or corrects** that pressure. The agent can start
successfully on the seed intuition, but cannot learn from its own
results — a second Lesson-2 failure, now at the junction of `MotorAdapter →
feedback_loop`, and not in the seeder itself (where, as the review confirmed,
everything is implemented correctly).

---

## Files affected

| File | Kind of change |
|---|---|
| `feedback_loop.py` | Read `action_type` from `tool_params["strategy"]`, falling back to `tool_id` if the field is absent |
| `tests/` | A regression test on the exact scenario of this gap |

---

## Change: `feedback_loop.py`

```python
def apply_feedback_to_agent(
    agent: Any,
    record: "ApprovalRecord",
    encoder: "BusinessEventEncoder",
) -> None:
    """..."""
    reward = approval_to_reward(record)
    execution_result = record.execution_result
    if not isinstance(execution_result, dict):
        execution_result = {"status": record.status.value}
    tokens, affective_inputs = encoder.encode_action_outcome(
        record.proposed_action.intent_summary,
        execution_result,
    )

    # ... affective_space.step(...) unchanged ...

    hippocampus = getattr(agent, "hippocampus", None)
    store_fn = getattr(hippocampus, "store", None)
    if not callable(store_fn):
        return
    path_cls, event_cls, event_type = load_experience_types()
    path = path_cls()
    for token in tokens or []:
        path = path.add_event(event_cls(str(token), event_type.CONTEXT))

    # ИЗМЕНЕНО: action_type берётся из tool_params, если роль его туда
    # положила (procurement кладёт под ключом "strategy" — см.
    # ProcurementBodyMotorAdapter._build_params). Роли, не использующие
    # это соглашение, откатываются на tool_id — прежнее поведение,
    # без регрессии для тех, у кого один tool_id == одна стратегия.
    action_label = _resolve_action_label(record.proposed_action)
    path = path.add_event(
        event_cls(f"action:{action_label}", event_type.ACTION)
    )

    consequence = event_cls(
        "approved" if reward > 0 else "rejected",
        event_type.CONSEQUENCE,
    )
    # ... store_fn(...) unchanged ...


def _resolve_action_label(proposed_action: "ProposedAction") -> str:
    """
    Recover the agent's actual chosen action_type for the ACTION event,
    not the MCP tool_id that happened to fulfil it. A single tool_id may
    serve several action_types (e.g. one 'create_purchase_order' tool
    fulfils all four procurement strategies) — falling back to tool_id
    there would store every outcome under one token the ActionSelector
    does not recognise, silently breaking learning from real outcomes
    (lesson 2, applied a second time at the MotorAdapter -> feedback_loop
    boundary; see patch v1.2 diagnosis).

    Convention: roles that need per-strategy feedback put the label under
    tool_params["strategy"] (see ProcurementBodyMotorAdapter). Roles with
    a 1:1 tool_id<->action_type mapping need not set it — tool_id already
    is the correct label there, and this falls back to it unchanged.
    """
    params = proposed_action.tool_params or {}
    strategy = params.get("strategy")
    if isinstance(strategy, str) and strategy.strip():
        return strategy.strip()
    return proposed_action.tool_id
```
### Why not add `action_type` as a field of `ProposedAction`

An alternative fix was considered — adding `action_type: str` directly
to the `ProposedAction` dataclass in `motor_adapter.py`. It was declined in favour of
the convention through `tool_params["strategy"]`:

- `ProposedAction` is a universal contract for any role (section 6
  of the base specification). Not every role necessarily has a notion
  of a "strategy" inside one action_type — for example, a role with a 1:1
  correspondence of tool_id to action_type would never fill that field,
  and it would always be empty dead weight in a generic dataclass.
- `tool_params["strategy"]` already exists and is used by
  `ProcurementBodyMotorAdapter` for its own purposes (diagnostics,
  possibly the UI). Reading it in `feedback_loop.py` is not a new link between
  components, but a use of a link that already exists.
- This keeps `MotorAdapter` and `ProposedAction` as thin as possible —
  responsibility for what "action_type" means for a particular role
  stays with the role, and does not leak into the generic layer.

---

## Test cases

### `tests/test_feedback_action_label.py` (new file)

```python
"""Regression test for patch v1.2: the ACTION event stored after a real
MCP execution must reflect the agent's chosen strategy, not the tool_id
that happened to fulfil it — otherwise the ActionSelector never learns
from real outcomes for any tool_id that serves multiple action_types."""

import pytest
from nowa_body.approval_gate import ApprovalRecord, ApprovalStatus
from nowa_body.motor_adapter import ProposedAction
from nowa_body.mcp_capability import CapabilityRisk
from nowa_body.business_event_encoder import BusinessEventEncoder
from nowa_body.feedback_loop import apply_feedback_to_agent, _resolve_action_label


def _make_record(strategy_in_params: bool) -> ApprovalRecord:
    params = {"supplier_id": "acme", "product_id": "sku_a", "qty": 30.0}
    if strategy_in_params:
        params["strategy"] = "urgent_reorder"
    proposed = ProposedAction(
        action_id="test-1",
        agent_id="buyer",
        tool_id="mcp__1c__create_purchase_order",
        tool_params=params,
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        intent_summary="urgent_reorder(supplier_id=acme, ...)",
        requires_approval=False,
    )
    return ApprovalRecord(
        proposed_action=proposed,
        status=ApprovalStatus.APPROVED,
        submitted_at=0.0,
        decided_at=0.0,
        decided_by="test",
        executed=True,
        execution_result={"status": "accepted"},
    )


class TestResolveActionLabel:

    def test_uses_strategy_when_present(self):
        record = _make_record(strategy_in_params=True)
        label = _resolve_action_label(record.proposed_action)
        assert label == "urgent_reorder"

    def test_falls_back_to_tool_id_when_absent(self):
        record = _make_record(strategy_in_params=False)
        label = _resolve_action_label(record.proposed_action)
        assert label == "mcp__1c__create_purchase_order"


class TestFeedbackStoresCorrectActionEvent:

    def test_stored_path_has_strategy_as_action_event(self, make_test_agent):
        """The exact bug: without the fix, this ACTION token would be
        'action:mcp__1c__create_purchase_order' for every strategy,
        which ActionSelector does not recognise."""
        agent = make_test_agent()
        encoder = BusinessEventEncoder({})
        record = _make_record(strategy_in_params=True)

        apply_feedback_to_agent(agent, record, encoder)

        stored = agent.hippocampus.experiences[-1]
        action_names = [
            e.name for e in stored.path.events
            if e.event_type.value == "action"
        ]
        assert action_names == ["action:urgent_reorder"]
        assert "action:mcp__1c__create_purchase_order" not in action_names

    def test_two_different_strategies_produce_different_action_events(
        self, make_test_agent
    ):
        """Two orders through the SAME tool_id but different strategies
        must be distinguishable in the hippocampus afterward — this is
        what makes per-strategy learning from real outcomes possible."""
        agent = make_test_agent()
        encoder = BusinessEventEncoder({})

        record_a = _make_record(strategy_in_params=True)
        apply_feedback_to_agent(agent, record_a, encoder)

        record_b = _make_record(strategy_in_params=True)
        record_b.proposed_action.tool_params["strategy"] = "diversify_supplier"
        apply_feedback_to_agent(agent, record_b, encoder)

        stored_actions = []
        for exp in agent.hippocampus.experiences[-2:]:
            names = [
                e.name for e in exp.path.events if e.event_type.value == "action"
            ]
            stored_actions.append(names[0] if names else None)

        assert stored_actions == ["action:urgent_reorder", "action:diversify_supplier"]

    def test_role_without_strategy_convention_unaffected(self, make_test_agent):
        """B4/backward-compat: a role that never sets tool_params['strategy']
        (1:1 tool_id<->action_type) must behave exactly as before this patch."""
        agent = make_test_agent()
        encoder = BusinessEventEncoder({})
        record = _make_record(strategy_in_params=False)

        apply_feedback_to_agent(agent, record, encoder)

        stored = agent.hippocampus.experiences[-1]
        action_names = [
            e.name for e in stored.path.events if e.event_type.value == "action"
        ]
        assert action_names == ["action:mcp__1c__create_purchase_order"]
```
---

## Constraints

| # | Constraint |
|---|---|
| **F1** | `_resolve_action_label` is a pure function, without side effects, and does not mutate `proposed_action` |
| **F2** | The convention of the key `"strategy"` in `tool_params` is not obligatory for every role; absence of the key is not an error, only a fallback to `tool_id` |
| **F3** | The fix does not change `ProcurementBodyMotorAdapter` — that code was already correct, and the gap was only in `feedback_loop.py` |

---

## Definition of Done

- [ ] `_resolve_action_label` is implemented in `feedback_loop.py`
- [ ] `apply_feedback_to_agent` uses `_resolve_action_label` instead of
      the direct `record.proposed_action.tool_id`
- [ ] `test_stored_path_has_strategy_as_action_event` passes
- [ ] `test_two_different_strategies_produce_different_action_events` passes
      — this is the principal test, proving that the gap is closed
- [ ] `test_role_without_strategy_convention_unaffected` passes —
      it confirms the absence of a regression for roles without the convention
- [ ] A repeated run of `BodyLabSession` with several ticks, in which the agent
      actually executes different strategies (`urgent_reorder`,
      `diversify_supplier`, and so on) — check manually, via
      `episode_rows()`, that the ACTION tokens in the stored episodes
      really differ between strategies and do not all coincide on
      `tool_id`

---

*Patch v1.2. The only blocking defect of Phase 1 found in a
line-by-line review. It is justified by the same class of error (Lesson 2) that had
already appeared twice in this project — at the boundary of components, not inside
them taken separately.*
