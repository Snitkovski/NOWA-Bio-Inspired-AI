"""Host orchestrator: WorldState → encode → Agent.step → SchemaBinder → ApprovalGate.

The mind chooses a WRITE ``tool_id`` (or ``wait_and_monitor``); the binder
poses the muscle; the gate is the only WRITE into the world.
"""

from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ._compat import apply_impulses
from .approval_gate import ApprovalGate, ApprovalRecord, ApprovalStatus
from .generic_encoder import GenericEncoder
from .mcp_capability import CapabilityRisk
from .organ_registry import MCPToolRegistry
from .proposed_action import ProposedAction, new_action_id, summarize_call
from .schema_binder import SchemaBinder
from .world_state import WorldState

WAIT_AND_MONITOR = "wait_and_monitor"
BIND_FAIL_IMPULSE_INTENSITY = 0.15


class BusinessAgentRuntime:
    """One ``run_cycle(observations)`` is observe → decide → bind → gate → feedback."""

    def __init__(
        self,
        agent: Any,
        tool_registry: MCPToolRegistry,
        approval_gate: ApprovalGate,
        encoder: Optional[GenericEncoder] = None,
        sleep_scheduler: Any = None,
        sensor_refresh_interval_s: float = 300.0,
        simulated_tick_seconds: Optional[float] = None,
        schema_binder: Optional[SchemaBinder] = None,
        param_bindings: Optional[Dict[str, Any]] = None,
        field_aliases: Optional[Dict[str, Any]] = None,
        event_classifier: Optional[Callable[..., Any]] = None,
        **host_compat: Any,
    ) -> None:
        host_compat.pop("motor_adapter", None)
        self.agent = agent
        self.tool_registry = tool_registry
        self.approval_gate = approval_gate
        self.encoder = encoder or GenericEncoder()
        self.sleep_scheduler = sleep_scheduler
        self.sensor_refresh_interval_s = float(sensor_refresh_interval_s)
        self.simulated_tick_seconds = simulated_tick_seconds
        self.schema_binder = schema_binder or SchemaBinder()
        self.param_bindings = dict(param_bindings or {})
        self.field_aliases = dict(field_aliases or {})
        self.event_classifier = event_classifier
        self.world_state = WorldState()
        self.motor_adapter = None
        self._cached_observations: Dict[str, Any] = {}
        self._last_sensor_refresh: Optional[datetime] = None
        self.register_organs_on_agent()

    def register_organs_on_agent(self) -> None:
        """BG channels = WRITE organs + synthetic wait (spec §7.1)."""
        write_ids = [cap.tool_id for cap in self.tool_registry.motor_capabilities()]
        channels = list(write_ids) + [WAIT_AND_MONITOR]
        selector = getattr(self.agent, "selector", None)
        actions = getattr(selector, "actions", None)
        if isinstance(actions, list):
            for channel in channels:
                if channel not in actions:
                    actions.append(channel)
        register = getattr(self.agent, "register_action_channel", None)
        if callable(register):
            for channel in channels:
                try:
                    register(channel)
                except Exception:
                    continue
        set_risk = getattr(self.agent, "set_organ_risk", None)
        if callable(set_risk):
            for cap in self.tool_registry.motor_capabilities():
                try:
                    risk = cap.risk_level.value if hasattr(cap.risk_level, "value") else str(cap.risk_level)
                    set_risk(cap.tool_id, risk)
                except Exception:
                    continue

    def tick(
        self,
        sensor_fetcher: Callable[[], Dict[str, Any]],
        *,
        now: Optional[datetime] = None,
    ) -> dict:
        """Host entry point (~1 Hz). Refreshes sensors only on the interval."""
        now = now or datetime.now()
        refreshed = self._should_refresh_sensors(now)
        if refreshed:
            self._cached_observations = dict(sensor_fetcher() or {})
            self._last_sensor_refresh = now
        result = self.run_cycle(self._cached_observations, now=now)
        result["sensor_refreshed"] = refreshed
        return result

    def run_cycle(
        self,
        observations: Dict[str, Any],
        *,
        now: Optional[datetime] = None,
    ) -> dict:
        """Pure pipeline pass on a given observation snapshot (tests / sandbox)."""
        result = self._run_decision_cycle(observations or {})
        self._accumulate_wakefulness()
        now = now or datetime.now()
        scheduler = self.sleep_scheduler
        if scheduler is not None and hasattr(scheduler, "should_sleep"):
            should_sleep, reason = scheduler.should_sleep(self.agent, now=now)
            if should_sleep:
                sleep_manager = getattr(self.agent, "sleep_manager", None)
                sleep_fn = getattr(sleep_manager, "sleep_cycle", None)
                if callable(sleep_fn):
                    sleep_fn()
                    mark = getattr(scheduler, "mark_slept", None)
                    if callable(mark):
                        try:
                            mark(now=now)
                        except TypeError:
                            mark()
                    result["slept"] = True
                    result["sleep_reason"] = reason
                else:
                    result["slept"] = False
            else:
                result.setdefault("slept", False)
        else:
            result.setdefault("slept", False)
        return result

    def complete_approval(
        self,
        action_id: str,
        decision: ApprovalStatus,
        decided_by: str = "human",
        rejection_reason: Optional[str] = None,
        modified_params: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRecord:
        """Apply a human decision, then record feedback once the outcome exists."""
        record = self.approval_gate.decide(
            action_id,
            decision,
            decided_by,
            rejection_reason=rejection_reason,
            modified_params=modified_params,
        )
        if record.status != ApprovalStatus.PENDING:
            self._apply_feedback(record)
        return record

    def _run_decision_cycle(self, observations: Dict[str, Any]) -> dict:
        self._ingest_observations(observations)
        context_events, read_impulses = self._build_context(observations)
        apply_impulses(
            getattr(self.agent, "affective_space", None),
            read_impulses,
            source="external",
        )

        step_fn = getattr(self.agent, "step", None)
        if callable(step_fn):
            if self._accepts_decision_only(step_fn):
                action_intent = step_fn(context_events, decision_only=True)
            else:
                action_intent = step_fn(context_events)
        else:
            action_intent = WAIT_AND_MONITOR
        tool_id = self._intent_to_tool_id(action_intent)

        if tool_id == WAIT_AND_MONITOR or not tool_id:
            return {
                "action_type": WAIT_AND_MONITOR,
                "tool_id": WAIT_AND_MONITOR,
                "proposed": None,
                "slept": False,
                "context_events": context_events,
                "waited": True,
            }

        capability = self.tool_registry.get(tool_id)
        if capability is None or capability.risk_level == CapabilityRisk.READ_ONLY:
            return {
                "action_type": tool_id,
                "tool_id": tool_id,
                "proposed": None,
                "slept": False,
                "context_events": context_events,
                "waited": True,
            }

        weights = self._rank_weights()
        params = self.schema_binder.bind(
            capability,
            self.world_state,
            rank_weights=weights,
            hippocampus=getattr(self.agent, "hippocampus", None),
            param_bindings=self.param_bindings,
            field_aliases=self.field_aliases,
        )
        if params is None:
            apply_impulses(
                getattr(self.agent, "affective_space", None),
                {
                    "vector": {"curiosity": 0.4},
                    "intensity": BIND_FAIL_IMPULSE_INTENSITY,
                    "source": "internal",
                },
                source="internal",
            )
            return {
                "action_type": tool_id,
                "tool_id": tool_id,
                "proposed": None,
                "slept": False,
                "context_events": context_events,
                "waited": True,
                "bind_failed": True,
            }

        proposed = ProposedAction(
            action_id=new_action_id(),
            agent_id=self._agent_id(observations),
            tool_id=capability.tool_id,
            tool_params=dict(params),
            risk_level=capability.risk_level,
            intent_summary=summarize_call(capability.tool_id, params),
            affective_context=self._affect_snapshot(),
            estimated_cost_impact=None,
            requires_approval=bool(capability.requires_approval),
        )
        record = self.approval_gate.route(proposed)
        if record.executed:
            self._apply_feedback(record)
        return {
            "action_type": tool_id,
            "tool_id": tool_id,
            "proposed": proposed,
            "approval_status": record.status.value,
            "executed": bool(record.executed),
            "record": record,
            "slept": False,
            "context_events": context_events,
            "waited": False,
        }

    def _ingest_observations(self, observations: Dict[str, Any]) -> None:
        if not isinstance(observations, dict):
            return
        tool_results = observations.get("tool_results")
        if isinstance(tool_results, dict):
            for tool_id, payload in tool_results.items():
                envelope = payload if isinstance(payload, dict) else {"status": "unknown", "value": payload}
                self.world_state.update_from_read(str(tool_id), envelope)
        for key, value in observations.items():
            if key in ("agent_id", "tool_results", "tool_params"):
                continue
            if isinstance(value, (dict, list)):
                self.world_state.update_from_read(
                    f"host__{key}",
                    {"status": "ok", key: value},
                )

    def _build_context(self, observations: Dict[str, Any]) -> tuple:
        tokens: List[str]
        impulses: List[Any]
        extra_events = self._classifier_event_names(observations)
        encode = getattr(self.encoder, "encode", None)
        if callable(encode):
            try:
                tokens, impulses = encode(self.world_state, extra_events=extra_events)
            except TypeError:
                try:
                    tokens, impulses = encode(self.world_state)
                except TypeError:
                    tokens, impulses = encode(self.world_state, getattr(self.world_state, "results", {}))
        else:
            tokens, impulses = self._legacy_encode(observations)
        if extra_events:
            tokens = list(tokens) + extra_events
        return (tokens or [WAIT_AND_MONITOR.replace("_", " ")], impulses or [])

    def _classifier_event_names(self, observations: Dict[str, Any]) -> List[str]:
        names: List[str] = []
        if self.event_classifier is None:
            return names
        tool_results = observations.get("tool_results", {}) if isinstance(observations, dict) else {}
        if not isinstance(tool_results, dict):
            return names
        for tool_id, result in tool_results.items():
            payload = result if isinstance(result, dict) else {"value": result}
            try:
                names.extend(str(item) for item in (self.event_classifier(str(tool_id), payload) or []))
            except Exception:
                continue
        return names

    def _legacy_encode(self, observations: Dict[str, Any]) -> tuple:
        tokens: List[str] = []
        encode_tool = getattr(self.encoder, "encode_tool_result", None)
        tool_results = observations.get("tool_results", {}) if isinstance(observations, dict) else {}
        if callable(encode_tool) and isinstance(tool_results, dict):
            for tool_id, result in tool_results.items():
                payload = result if isinstance(result, dict) else {"value": result}
                try:
                    tokens.extend(
                        encode_tool(
                            str(tool_id),
                            payload,
                            event_classifier=self.event_classifier,
                            world_state=self.world_state,
                        )
                    )
                except TypeError:
                    tokens.extend(encode_tool(str(tool_id), payload))
        return tokens or ["quiet_period"], []

    def _overlay_classifier(self, observations: Dict[str, Any]) -> List[str]:
        extra: List[str] = []
        tool_results = observations.get("tool_results", {}) if isinstance(observations, dict) else {}
        if not isinstance(tool_results, dict):
            return extra
        for tool_id, result in tool_results.items():
            payload = result if isinstance(result, dict) else {"value": result}
            try:
                extra.extend(list(self.event_classifier(str(tool_id), payload) or []))
            except Exception:
                continue
        return extra

    def _intent_to_tool_id(self, action_intent: Any) -> str:
        if isinstance(action_intent, str):
            label = action_intent.strip() or WAIT_AND_MONITOR
        elif action_intent is None:
            label = WAIT_AND_MONITOR
        else:
            label = WAIT_AND_MONITOR
            for attr in ("action_type", "action", "label", "name", "tool_id"):
                value = getattr(action_intent, attr, None)
                if isinstance(value, str) and value.strip():
                    label = value.strip()
                    break
        if label == WAIT_AND_MONITOR:
            return WAIT_AND_MONITOR
        if self.tool_registry.get(label) is not None:
            return label
        # Deprecated action_types index — last-resort mapping for old seeds.
        caps = self.tool_registry.capabilities_for_action(label)
        if caps:
            return caps[0].tool_id
        return label

    def _rank_weights(self) -> Dict[str, float]:
        space = getattr(self.agent, "affective_space", None)
        rank = getattr(space, "rank_weights", None)
        if callable(rank):
            try:
                return dict(rank() or {})
            except Exception:
                return {}
        return {}

    def _affect_snapshot(self) -> Dict[str, float]:
        space = getattr(self.agent, "affective_space", None)
        snap_fn = getattr(space, "snapshot", None)
        if callable(snap_fn):
            try:
                snap = snap_fn() or {}
                axes = snap.get("axes") if isinstance(snap, dict) else None
                if isinstance(axes, dict):
                    return {str(k): float(v) for k, v in axes.items() if isinstance(v, (int, float))}
            except Exception:
                pass
        axes = getattr(space, "axes", None)
        if isinstance(axes, dict):
            return {str(k): float(v) for k, v in axes.items() if isinstance(v, (int, float))}
        return {}

    def _agent_id(self, observations: Dict[str, Any]) -> str:
        if isinstance(observations, dict):
            raw = observations.get("agent_id")
            if raw:
                return str(raw)
        return str(
            getattr(self.agent, "agent_id", None)
            or getattr(self.tool_registry, "agent_id", "")
            or "agent"
        )

    def _apply_feedback(self, record: ApprovalRecord) -> None:
        from .feedback import apply_feedback_to_agent

        apply_feedback_to_agent(self.agent, record, self.encoder)

    def _should_refresh_sensors(self, now: datetime) -> bool:
        if self._last_sensor_refresh is None:
            return True
        elapsed = (now - self._last_sensor_refresh).total_seconds()
        return elapsed >= self.sensor_refresh_interval_s

    def _accumulate_wakefulness(self) -> None:
        ws = getattr(self.agent, "wakefulness_state", None)
        if ws is None:
            ws = getattr(self.agent, "wakefulness", None)
        update = getattr(ws, "update_waking", None)
        if not callable(update):
            return
        try:
            if self.simulated_tick_seconds is None:
                update()
            else:
                update(elapsed_seconds=float(self.simulated_tick_seconds))
        except Exception:
            return

    @staticmethod
    def _accepts_decision_only(step_fn: Callable[..., Any]) -> bool:
        try:
            parameters = inspect.signature(step_fn).parameters
        except (TypeError, ValueError):
            return False
        for param in parameters.values():
            if param.kind is inspect.Parameter.VAR_KEYWORD:
                return True
            if param.name == "decision_only" and param.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                return True
        return False
