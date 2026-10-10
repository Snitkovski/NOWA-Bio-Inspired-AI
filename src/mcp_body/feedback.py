"""Human approval / execution outcome → hippocampus + A(t) via outcome_impulse."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ._compat import apply_impulses, load_experience_types, outcome_impulse
from .approval_gate import ApprovalStatus

if TYPE_CHECKING:
    from .approval_gate import ApprovalRecord
    from .generic_encoder import GenericEncoder
    from .proposed_action import ProposedAction


def approval_to_reward(record: "ApprovalRecord") -> float:
    if record.status == ApprovalStatus.APPROVED:
        return 1.0
    if record.status == ApprovalStatus.MODIFIED:
        return 0.4
    if record.status == ApprovalStatus.REJECTED:
        return -1.0
    if record.status == ApprovalStatus.EXPIRED:
        return -0.2
    return 0.0


def apply_feedback_to_agent(
    agent: Any,
    record: "ApprovalRecord",
    encoder: "GenericEncoder",
) -> None:
    """Store one ACTION episode labelled ``action:<tool_id>`` and step A(t)."""
    reward = approval_to_reward(record)
    execution_result = record.execution_result
    if not isinstance(execution_result, dict):
        execution_result = {"status": record.status.value}

    tool_id = str(getattr(record.proposed_action, "tool_id", "") or "")
    encode_outcome = getattr(encoder, "encode_outcome", None)
    if callable(encode_outcome):
        try:
            tokens, impulse = encode_outcome(
                execution_result.get("status", record.status.value),
                execution_result,
                tool_id=tool_id,
            )
        except TypeError:
            tokens, impulse = encode_outcome(
                getattr(record.proposed_action, "intent_summary", tool_id),
                execution_result,
            )
    else:
        tokens, impulse = ["result:unknown"], outcome_impulse("unknown", 1.0)

    affective_space = getattr(agent, "affective_space", None)
    apply_impulses(affective_space, impulse, source="external")

    hippocampus = getattr(agent, "hippocampus", None)
    store_fn = getattr(hippocampus, "store", None)
    if not callable(store_fn):
        return

    path_cls, event_cls, event_type = load_experience_types()
    path = path_cls()
    for token in tokens or []:
        if str(token).startswith("action:"):
            continue
        path = path.add_event(event_cls(str(token), event_type.CONTEXT))

    action_label = _resolve_action_label(record.proposed_action)
    path = path.add_event(event_cls(f"action:{action_label}", event_type.ACTION))

    consequence = event_cls(
        "approved" if reward > 0 else "rejected",
        event_type.CONSEQUENCE,
    )
    try:
        stored = store_fn(
            path,
            consequence=consequence,
            intensity=abs(reward),
            reward=reward,
        )
    except TypeError:
        try:
            stored = store_fn(path, consequence=consequence, intensity=abs(reward))
        except TypeError:
            try:
                stored = store_fn(path, consequence=consequence)
            except Exception:
                return
        except Exception:
            return
    except Exception:
        return

    try:
        if stored is not None and affective_space is not None:
            create_trace = getattr(affective_space, "create_trace", None)
            if callable(create_trace):
                stored.emotional_trace = create_trace(intensity=min(1.0, abs(reward)))
    except Exception:
        pass


def _resolve_action_label(proposed_action: "ProposedAction") -> str:
    """Feedback ACTION label is always the organ tool_id (spec §6.6)."""
    return str(getattr(proposed_action, "tool_id", "") or "")
