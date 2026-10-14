"""Feedback must follow the episode id, not the tail of the list.

Refs #5. Once capacity eviction reorders survivors, experiences[-1] is not
the episode that was just stored. Every feedback call has to land on the
id returned by that step.
"""

from agent import Agent
from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import SleepManager


def _build_agent(capacity: int) -> Agent:
    hippocampus = NOWAHippocampus(max_experiences=capacity)
    cortex = CortexMemory()
    intent_memory = IntentMemory()
    sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
    selector = ActionSelector(actions=["keep", "drop"])
    return Agent(hippocampus, cortex, selector, sleep_manager, intent_memory)


def test_feedback_matches_episode_id_at_small_capacity():
    agent = _build_agent(capacity=40)
    mismatches = 0
    trials = 300
    for trial in range(trials):
        context = f"ctx-{trial % 7}"
        action = agent.step([context])
        episode_id = agent.last_episode_id
        assert episode_id
        stored = agent.hippocampus.get_experience(episode_id)
        assert stored is not None
        rating = 2 if trial % 2 == 0 else -2
        tail = agent.hippocampus.experiences[-1]
        tail_reward_before = getattr(tail, "reward", None)
        tail_id = getattr(tail, "episode_id", None)
        result = agent.apply_feedback_to_last_experience(
            rating,
            context_events=[context],
            action_id=action,
            episode_id=episode_id,
        )
        assert result["updated"] is True
        expected_reward = 1.0 if rating > 0 else -1.0
        if abs(float(stored.reward) - expected_reward) > 1e-9:
            mismatches += 1
        if tail_id != episode_id and getattr(tail, "reward", None) != tail_reward_before:
            mismatches += 1

    assert mismatches == 0
    assert len(agent.hippocampus.experiences) <= 40
