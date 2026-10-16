"""One TD update per transition, and V(s') comes from the real successor.

Refs #6. A later rating revises the same backup instead of stacking a
second one, and a non-terminal step bootstraps max_a Q(s', a).
"""

from agent import Agent
from cortex import CortexMemory
from experience import Event, EventType
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import SleepManager


def _build_agent(actions):
    hippocampus = NOWAHippocampus(max_experiences=200)
    cortex = CortexMemory()
    intent_memory = IntentMemory()
    sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
    selector = ActionSelector(actions=list(actions))
    return Agent(hippocampus, cortex, selector, sleep_manager, intent_memory)


def _q(agent, context, action) -> float:
    snapshot = agent._build_value_state_snapshot(
        context_events=list(context),
        action=action,
        consequence=None,
        intensity=1.0,
        novelty=0.0,
        conflict=0.0,
    )
    return float(agent.value_layer.get_value(snapshot))


def test_feedback_commits_one_td_update_and_reaches_the_reward():
    agent = _build_agent(["go"])
    before = int(agent.value_layer.online_update_count)
    action = agent.step(["goal"], terminal=True)
    agent.apply_feedback_to_last_experience(2, context_events=["goal"], action_id=action)
    once = int(agent.value_layer.online_update_count)
    assert once == before + 1

    agent.apply_feedback_to_last_experience(2, context_events=["goal"], action_id=action)
    assert int(agent.value_layer.online_update_count) == once

    for _ in range(80):
        action = agent.step(["goal"], terminal=True)
        agent.apply_feedback_to_last_experience(2, context_events=["goal"], action_id=action)
    assert _q(agent, ["goal"], "go") > 0.8


def test_successor_value_is_the_real_next_state():
    agent = _build_agent(["go"])
    successor = ["start", "consequence:arrived"]
    for _ in range(80):
        action = agent.step(successor, terminal=True)
        agent.apply_feedback_to_last_experience(
            2,
            context_events=successor,
            action_id=action,
        )
    assert _q(agent, successor, "go") > 0.8

    # Reward 0 on the way into a valuable successor must not stay at 0.
    for _ in range(80):
        action = agent.step(
            ["start"],
            consequence=Event("arrived", event_type=EventType.CONSEQUENCE),
            reward=0.0,
            terminal=False,
        )
    assert _q(agent, ["start"], action) > 0.4
