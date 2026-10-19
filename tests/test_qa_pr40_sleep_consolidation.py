"""Independent QA checks for PR #40 sleep consolidation.

These probe the sleep contract directly: exactly once, capture at kappa
0.5, the compensated 0.07 channel step, habit EMA, visit transfer, the
guard, and non-finite rewards. They do not retune the core.
"""

from __future__ import annotations

import json
import logging
import math
import os
import subprocess
import sys

import pytest

from agent import Agent
from basal_ganglia import ActionChannel, BasalGangliaLearning
from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from labile_layer import PlasticityConfig
from learning_guard import (
    WakingLearningError,
    learning_is_open,
    stable_fingerprint,
    stable_payload,
)
from selector import ActionSelector
from sleep import SleepManager


def _build(actions=("go", "stop"), seed=1, capacity=80, wake_s=1000.0):
    hippocampus = NOWAHippocampus(max_experiences=capacity)
    cortex = CortexMemory()
    memory = IntentMemory()
    sleep_manager = SleepManager(hippocampus, cortex, memory)
    selector = ActionSelector(actions=list(actions))
    return Agent(
        hippocampus,
        cortex,
        selector,
        sleep_manager,
        memory,
        rng_seed=seed,
        plasticity_config=PlasticityConfig(expected_wake_interval_s=wake_s),
    )


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


def _commit(agent, action, reward, context, **kwargs):
    return agent.commit_executed_transition(
        action=action,
        reward=reward,
        context_events=list(context),
        decided_action=kwargs.pop("decided_action", action),
        terminal=kwargs.pop("terminal", True),
        dt=kwargs.pop("dt", 0.0),
        **kwargs,
    )


def _eta(agent):
    plasticity = agent.plasticity
    kappa = float(plasticity.capture_kappa)
    eta_sleep = float(plasticity.eta_channel_sleep)
    eta_labile = float(plasticity.eta_labile_channel)
    return kappa, eta_sleep - kappa * eta_labile, eta_labile


def test_undecayed_capture_plus_compensated_step_is_the_old_go_step():
    """kappa * tag + eta_eff = 0.08 before replay and SHY. Q is not captured."""
    agent = _build(("go",), seed=1)
    episode_id = _commit(agent, "go", 1.0, ["bin"])
    episode = agent.hippocampus.get_experience(episode_id)
    go_tag, nogo_tag = agent.labile.remaining_channel(episode_id, agent._host_clock_s)
    kappa, eta_eff, eta_labile = _eta(agent)
    assert kappa == pytest.approx(0.5)
    assert eta_eff == pytest.approx(0.07)
    assert go_tag == pytest.approx(eta_labile)
    assert nogo_tag == pytest.approx(-0.5 * eta_labile)
    channel = agent.bg_action_channels["go"]
    go_before = float(channel.go_weight)
    nogo_before = float(channel.nogo_weight)
    q_before = _q(agent, ["bin"], "go")
    stats = agent.sleep(cycles=0)
    assert stats["two_tier_consolidated"] == 1
    assert float(channel.go_weight) - go_before == pytest.approx(kappa * go_tag + eta_eff)
    assert float(channel.nogo_weight) - nogo_before == pytest.approx(
        kappa * nogo_tag + (-0.5 * eta_eff)
    )
    assert float(channel.go_weight) - go_before == pytest.approx(0.08)
    assert _q(agent, ["bin"], "go") == pytest.approx(q_before)
    gain = max(0.25, min(1.5, float(episode.affect_gain_at_encoding)))
    rate = 0.20 * gain
    assert float(channel.habit_strength) == pytest.approx(rate * (1.0 - 0.0))
    strengths = [float(trace.strength) for trace in agent.intent_memory.traces.values()]
    assert max(strengths) == pytest.approx(rate)
    assert agent.labile.max_abs_q(agent._host_clock_s) == pytest.approx(0.0, abs=1e-12)
    assert agent.labile.max_abs_channel(agent._host_clock_s) == pytest.approx(0.0, abs=1e-12)
    assert episode_id not in agent.labile._contributions
    assert episode.consolidated is True
    assert int(episode.consolidated_revision) == int(episode.outcome_revision)
    assert float(episode.consolidated_reward) == pytest.approx(1.0)


def test_high_dopamine_does_not_scale_the_sleep_channel_step():
    agent = _build(("go",), seed=1)
    agent.neuromodulators.dopamine = 0.95
    episode_id = _commit(agent, "go", 1.0, ["bin"])
    go_tag, nogo_tag = agent.labile.remaining_channel(episode_id, agent._host_clock_s)
    assert (go_tag, nogo_tag) == pytest.approx((0.02, -0.01))
    agent.sleep(cycles=0)
    assert agent.bg_action_channels["go"].go_weight == pytest.approx(0.58)


def test_decayed_tag_is_captured_and_the_step_stays_0_07():
    agent = _build(("go",), seed=1, wake_s=1000.0)
    episode_id = _commit(agent, "go", 1.0, ["bin"])
    agent.advance_time(1000.0)
    go_tag, _nogo_tag = agent.labile.remaining_channel(episode_id, agent._host_clock_s)
    assert go_tag == pytest.approx(0.02 * math.exp(-1.0))
    before = float(agent.bg_action_channels["go"].go_weight)
    agent.sleep(cycles=0)
    assert float(agent.bg_action_channels["go"].go_weight) - before == pytest.approx(
        0.5 * go_tag + 0.07
    )
    assert float(agent.bg_action_channels["go"].go_weight) - before < 0.08


def test_second_sleep_does_not_repeat_capture_and_states_shy_decay():
    """cycles=0 repeats nothing. A later cycle only applies SHY, trace decay, cortex DA."""
    agent = _build(("go",), seed=1)
    _commit(agent, "go", 1.0, ["bin"])
    agent.sleep(cycles=0)
    channel = agent.bg_action_channels["go"]
    frozen = (
        float(channel.go_weight),
        float(channel.nogo_weight),
        float(channel.habit_strength),
        _q(agent, ["bin"], "go"),
    )
    fingerprint = stable_fingerprint(agent)
    again = agent.sleep(cycles=0)
    assert again["two_tier_consolidated"] == 0
    assert (
        float(channel.go_weight),
        float(channel.nogo_weight),
        float(channel.habit_strength),
        _q(agent, ["bin"], "go"),
    ) == pytest.approx(frozen)
    assert stable_fingerprint(agent) == fingerprint

    lived = _build(("go",), seed=1)
    _commit(lived, "go", 1.0, ["bin"])
    lived.sleep(cycles=1)
    before = stable_payload(lived)
    q_before = _q(lived, ["bin"], "go")
    da = float(lived.neuromodulators.dopamine)
    second = lived.sleep(cycles=1)
    after = stable_payload(lived)
    assert second["two_tier_consolidated"] == 0
    assert second["total_replays"] == 0
    assert _q(lived, ["bin"], "go") == pytest.approx(q_before)
    assert after["value_layer"] == before["value_layer"]
    assert after["slow_affect"] == before["slow_affect"]
    assert after["visit_counts"] == before["visit_counts"]
    assert after["strategies"] == before["strategies"]
    keep = 1.0 - float(lived.sleep_manager.decay_rate_sleep)
    for left, right in zip(before["channels"], after["channels"]):
        for name, prior_name in (
            ("go_weight", "prior_go"),
            ("nogo_weight", "prior_nogo"),
            ("habit_strength", "prior_habit"),
        ):
            expected = right[prior_name] + (left[name] - right[prior_name]) * keep
            assert right[name] == pytest.approx(expected)
    assert after["intent_strengths"][0]["strength"] == pytest.approx(
        before["intent_strengths"][0]["strength"] * 0.8
    )
    assert after["cortex"][0]["strength"] == pytest.approx(
        before["cortex"][0]["strength"] * (1.0 + da * 0.05)
    )


def test_same_rating_after_consolidation_is_a_noop_and_a_change_is_a_new_observation():
    same = _build(("go",), seed=1)
    episode_id = _commit(same, "go", 1.0, ["bin"])
    same.sleep(cycles=1)
    episode = same.hippocampus.get_experience(episode_id)
    revision = int(episode.outcome_revision)
    fingerprint = stable_fingerprint(same)
    q_before = _q(same, ["bin"], "go")
    result = same.apply_feedback_to_last_experience(
        2, context_events=["bin"], action_id="go", episode_id=episode_id
    )
    assert result["updated"] is True
    assert int(episode.outcome_revision) == revision
    assert stable_fingerprint(same) == fingerprint
    stats = same.sleep(cycles=1)
    assert stats["two_tier_consolidated"] == 0
    assert stats["total_replays"] == 0
    assert _q(same, ["bin"], "go") == pytest.approx(q_before)

    changed = _build(("go",), seed=1)
    episode_id = _commit(changed, "go", 1.0, ["bin"])
    changed.sleep(cycles=0)
    episode = changed.hippocampus.get_experience(episode_id)
    go_after_first = float(changed.bg_action_channels["go"].go_weight)
    habit_after_first = float(changed.bg_action_channels["go"].habit_strength)
    assert go_after_first == pytest.approx(0.58)
    assert habit_after_first == pytest.approx(0.2)
    episode.td_history_snapshot = [1.0, -1.0, 1.0, -1.0]
    episode.td_variance_snapshot = 1.0
    changed.apply_feedback_to_last_experience(
        -2, context_events=["bin"], action_id="go", episode_id=episode_id
    )
    assert int(episode.outcome_revision) != int(episode.consolidated_revision)
    assert _q(changed, ["bin"], "go") == pytest.approx(0.0)
    changed.sleep(cycles=0)
    # The old +0.08 write is kept. The new rating adds its own step on top.
    assert changed.bg_action_channels["go"].go_weight == pytest.approx(go_after_first - 0.04)
    assert changed.bg_action_channels["go"].habit_strength == pytest.approx(
        habit_after_first + 0.20 * (0.0 - habit_after_first)
    )
    assert int(episode.consolidated_revision) == int(episode.outcome_revision)

    replayed = _build(("go",), seed=1)
    episode_id = _commit(replayed, "go", 1.0, ["bin"])
    replayed.sleep(cycles=1)
    episode = replayed.hippocampus.get_experience(episode_id)
    q_positive = _q(replayed, ["bin"], "go")
    episode.td_history_snapshot = [1.0, -1.0, 1.0, -1.0]
    episode.td_variance_snapshot = 1.0
    replayed.apply_feedback_to_last_experience(
        -2, context_events=["bin"], action_id="go", episode_id=episode_id
    )
    stats = replayed.sleep(cycles=1)
    assert stats["two_tier_consolidated"] == 1
    assert stats["rejected_due_to_td_variance"] == 0
    assert stats["total_replays"] > 0
    assert _q(replayed, ["bin"], "go") < q_positive


def test_zero_reward_does_not_move_habit_and_waking_habit_stays_zero():
    waking = _build(("go",), seed=1)
    _commit(waking, "go", 1.0, ["bin"])
    assert waking.bg_action_channels["go"].habit_strength == pytest.approx(0.0)
    assert all(float(trace.strength) == 0.0 for trace in waking.intent_memory.traces.values())

    zero = _build(("go",), seed=1)
    _commit(zero, "go", 0.0, ["bin"])
    zero.sleep_manager.decay_rate_sleep = 0.0
    stats = zero.sleep(cycles=1)
    channel = zero.bg_action_channels["go"]
    assert stats["total_replays"] == 0
    assert stats["two_tier_consolidated"] == 1
    assert channel.go_weight == pytest.approx(0.5)
    assert channel.nogo_weight == pytest.approx(0.5)
    assert channel.habit_strength == pytest.approx(0.0)
    assert all(float(trace.strength) <= 0.0 for trace in zero.intent_memory.traces.values())


def test_unconsolidated_tag_keeps_decaying_and_eviction_writes_nothing():
    agent = _build(("go", "stop"), seed=1, wake_s=1000.0)
    kept_id = _commit(agent, "go", 1.0, ["keep"])
    kept = agent.hippocampus.get_experience(kept_id)
    _commit(agent, "stop", 1.0, ["drop"])
    agent.hippocampus.experiences = [
        episode for episode in agent.hippocampus.experiences if episode is not kept
    ]
    agent.sleep(cycles=1)
    assert kept.episode_id in agent.labile._contributions
    assert getattr(kept, "consolidated", False) is False
    tag = agent.labile.remaining_channel(kept.episode_id, agent._host_clock_s)
    agent.advance_time(1000.0)
    later = agent.labile.remaining_channel(kept.episode_id, agent._host_clock_s)
    assert later[0] == pytest.approx(tag[0] * math.exp(-1.0))
    assert later[1] == pytest.approx(tag[1] * math.exp(-1.0))

    evicted = _build(("red", "green"), seed=1, capacity=1)
    first = _commit(evicted, "red", 1.0, ["north"])
    _commit(evicted, "green", 1.0, ["south"])
    assert evicted.hippocampus.get_experience(first) is None
    assert evicted.lost_unconsolidated == 1
    assert first not in evicted.labile._contributions
    evicted.sleep(cycles=1)
    assert _q(evicted, ["north"], "red") == pytest.approx(0.0, abs=1e-12)
    assert _q(evicted, ["south"], "green") > 0.0


def test_replay_priority_order_is_the_four_term_score_and_hash_stable():
    agent = _build(("go",), seed=1)
    made = []
    for novelty, emotion, reward in ((0.0, 0.0, 1.0), (1.0, 0.0, 0.2), (0.0, 1.0, 0.2)):
        _commit(agent, "go", reward, ["bin"], novelty=novelty, intensity=emotion * 2.0)
        episode = agent.hippocampus.get_experience(agent.last_episode_id)
        episode.novelty = float(novelty)
        episode.emotional_salience = float(emotion)
        made.append(episode)
    order = agent.sleep_manager.consolidation_order(made)
    scores = []
    for episode in order:
        delta = abs(float(agent.sleep_manager._replay_signed_td(episode)))
        reward = abs(float(agent.sleep_manager._offline_reward(episode)))
        manual = (
            1.0 * delta
            + 0.5 * reward
            + 0.25 * float(episode.novelty)
            + 0.25 * float(episode.emotional_salience)
        )
        assert agent.sleep_manager.spec_replay_priority(episode) == pytest.approx(manual)
        scores.append(manual)
    assert scores == sorted(scores, reverse=True)
    assert [episode.episode_id for episode in order] == ["ep-1", "ep-2", "ep-3"]
    capped = [agent.sleep_manager._compute_replay_priority(episode) for episode in made]
    agent.plasticity.replay_priority_weights = (9.0, 9.0, 9.0, 9.0)
    assert [agent.sleep_manager._compute_replay_priority(episode) for episode in made] == pytest.approx(
        capped
    )
    agent.plasticity.replay_priority_weights = (0.0, 0.0, 0.0, 0.0)
    tied = agent.sleep_manager.consolidation_order(made)
    assert [episode.episode_id for episode in tied] == sorted(episode.episode_id for episode in made)

    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    inline = (
        "import json,sys\n"
        "sys.path.insert(0,'src')\n"
        "from agent import Agent\n"
        "from cortex import CortexMemory\n"
        "from hippocampus import NOWAHippocampus\n"
        "from intent_memory import IntentMemory\n"
        "from labile_layer import PlasticityConfig\n"
        "from selector import ActionSelector\n"
        "from sleep import SleepManager\n"
        "hip=NOWAHippocampus(max_experiences=20)\n"
        "cortex=CortexMemory(); mem=IntentMemory(); sm=SleepManager(hip, cortex, mem)\n"
        "sel=ActionSelector(actions=['go'])\n"
        "agent=Agent(hip, cortex, sel, sm, mem, rng_seed=1,\n"
        "    plasticity_config=PlasticityConfig(expected_wake_interval_s=1000.0))\n"
        "rows=[]\n"
        "for novelty, emotion, reward in ((0.0,0.0,1.0),(1.0,0.0,0.2),(0.0,1.0,0.2)):\n"
        "    agent.commit_executed_transition(action='go', reward=reward, context_events=['bin'],\n"
        "        decided_action='go', terminal=True, novelty=novelty, intensity=emotion*2, dt=0.0)\n"
        "    ep=agent.hippocampus.get_experience(agent.last_episode_id)\n"
        "    ep.novelty=float(novelty); ep.emotional_salience=float(emotion)\n"
        "    rows.append(ep)\n"
        "order=agent.sleep_manager.consolidation_order(rows)\n"
        "print(json.dumps([(ep.episode_id, agent.sleep_manager.spec_replay_priority(ep)) for ep in order]))\n"
    )
    outputs = []
    for hash_seed in ("0", "1", "7"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = hash_seed
        env["NOWA_STRICT_LEARNING"] = "1"
        completed = subprocess.run(
            [sys.executable, "-c", inline],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr[-2000:]
        outputs.append(completed.stdout.strip())
    assert outputs[0] == outputs[1] == outputs[2]
    parsed = json.loads(outputs[0])
    assert [item[0] for item in parsed] == ["ep-1", "ep-2", "ep-3"]


def test_visits_transfer_once_and_do_not_decay_while_awake():
    agent = _build(("go",), seed=1)
    for _ in range(3):
        agent.step(["bin"], reward=1.0, terminal=True, dt=0.0)
    assert agent.labile.visit_count("bin", "go") == pytest.approx(3.0)
    assert agent._action_visit_counts.get(("bin", "go"), 0) == 0
    agent.advance_time(500.0)
    assert agent.labile.visit_count("bin", "go") == pytest.approx(3.0)
    agent.sleep(cycles=1)
    assert agent.labile.visit_count("bin", "go") == pytest.approx(0.0)
    assert int(agent._action_visit_counts.get(("bin", "go"), 0)) == 3
    agent.sleep(cycles=1)
    assert int(agent._action_visit_counts.get(("bin", "go"), 0)) == 3


def test_slow_affect_moves_only_in_sleep_and_is_in_the_fingerprint():
    agent = _build(("go",), seed=1)
    before = stable_fingerprint(agent)
    regulation = dict(agent.emotional_regulation.snapshot() or {})
    for _ in range(4):
        agent.step(["bin"], reward=1.0, novelty=0.8, conflict=0.6, terminal=True, dt=1.0)
    assert stable_fingerprint(agent) == before
    assert agent.semantic_emotions.snapshot() == []
    assert agent._pending_slow_affect
    assert dict(agent.emotional_regulation.snapshot() or {}) != regulation
    waking = stable_payload(agent)
    agent.sleep(cycles=1)
    slept = stable_payload(agent)
    assert agent._pending_slow_affect == []
    assert stable_fingerprint(agent) != before
    assert slept["slow_affect"] != waking["slow_affect"]
    assert agent.semantic_emotions.snapshot()


def test_named_guards_raise_in_strict_mode_and_skip_once_in_production(caplog, monkeypatch):
    agent = _build(("go",), seed=1)
    channel = agent.bg_action_channels["go"]
    before = stable_fingerprint(agent)
    with pytest.raises(WakingLearningError):
        channel.go_weight = 0.9
    with pytest.raises(WakingLearningError):
        channel.nogo_weight = 0.1
    with pytest.raises(WakingLearningError):
        channel.habit_strength = 0.4
    with pytest.raises(WakingLearningError):
        agent.value_layer._set_value("state", 0.4)
    with pytest.raises(WakingLearningError):
        agent.bg_learning.consolidate_habits([channel], serotonin=1.0)
    with pytest.raises(WakingLearningError):
        agent.bg_learning.apply_sleep_learning(
            [channel],
            {"go": [(1.0, 0.8, 0.1, 0.2)]},
            agent.neuromodulators,
            forget_rate=0.0,
        )
    assert channel.go_weight == pytest.approx(0.5)
    assert stable_fingerprint(agent) == before
    agent.register_action_channel("seeded", go_weight=0.8, habit_strength=0.3)
    assert agent.bg_action_channels["seeded"].go_weight == pytest.approx(0.8)
    assert learning_is_open() is False

    monkeypatch.setenv("NOWA_STRICT_LEARNING", "0")
    import learning_guard

    learning_guard._SKIP_LOGGED.clear()
    prod = _build(("go",), seed=1)
    prod_channel = prod.bg_action_channels["go"]
    prod_before = stable_fingerprint(prod)
    with caplog.at_level(logging.WARNING, logger="nowa.learning"):
        prod_channel.go_weight = 0.9
        prod_channel.go_weight = 0.2
        prod.bg_learning.consolidate_habits([prod_channel], serotonin=1.0)
        prod.bg_learning.apply_sleep_learning(
            [prod_channel],
            {"go": [(1.0, 0.8, 0.1, 0.2)]},
            prod.neuromodulators,
            forget_rate=0.0,
        )
    assert prod_channel.go_weight == pytest.approx(0.5)
    assert stable_fingerprint(prod) == prod_before
    go_logs = [record for record in caplog.records if "ActionChannel.go_weight skipped" in record.message]
    habit_logs = [
        record
        for record in caplog.records
        if "BasalGangliaLearning.consolidate_habits skipped" in record.message
    ]
    update_logs = [
        record for record in caplog.records if "ActionChannel.update_weights skipped" in record.message
    ]
    assert len(go_logs) == 1
    assert len(habit_logs) == 1
    assert len(update_logs) == 1


def test_nonfinite_rewards_match_across_step_commit_and_feedback():
    nan_step = _build(("go",), seed=1)
    nan_step.step(["bin"], reward=float("nan"), terminal=True, dt=0.0)
    nan_episode = nan_step.hippocampus.experiences[-1]
    assert getattr(nan_episode, "td_outcome_committed", False) is False
    assert nan_step.labile._contributions == {}

    text_step = _build(("go",), seed=1)
    text_step.step(["bin"], reward="nope", terminal=True, dt=0.0)
    assert getattr(text_step.hippocampus.experiences[-1], "td_outcome_committed", False) is False

    inf_step = _build(("go",), seed=1)
    inf_step.step(["bin"], reward=float("inf"), terminal=True, dt=0.0)
    assert float(inf_step.hippocampus.experiences[-1].td_committed_reward) == pytest.approx(1.0)
    neg_step = _build(("go",), seed=1)
    neg_step.step(["bin"], reward=float("-inf"), terminal=True, dt=0.0)
    assert float(neg_step.hippocampus.experiences[-1].td_committed_reward) == pytest.approx(-1.0)

    nan_commit = _build(("go",), seed=1)
    _commit(nan_commit, "go", float("nan"), ["bin"])
    assert getattr(nan_commit.hippocampus.experiences[-1], "td_outcome_committed", False) is False
    text_commit = _build(("go",), seed=1)
    _commit(text_commit, "go", "nope", ["bin"])
    assert getattr(text_commit.hippocampus.experiences[-1], "td_outcome_committed", False) is False
    inf_commit = _build(("go",), seed=1)
    _commit(inf_commit, "go", float("-inf"), ["bin"])
    assert float(inf_commit.hippocampus.experiences[-1].td_committed_reward) == pytest.approx(-1.0)

    feedback = _build(("go",), seed=1)
    feedback.step(["bin"], reward=None, terminal=True, dt=0.0)
    episode_id = feedback.last_episode_id
    before = stable_fingerprint(feedback)
    missing = feedback.apply_feedback_to_last_experience(float("nan"), episode_id=episode_id)
    assert missing["updated"] is False
    text = feedback.apply_feedback_to_last_experience("nope", episode_id=episode_id)
    assert text["updated"] is False
    assert stable_fingerprint(feedback) == before
    applied = feedback.apply_feedback_to_last_experience(float("inf"), episode_id=episode_id)
    assert applied["updated"] is True
    assert applied["reward_signal"] == pytest.approx(1.0)
    assert float(feedback.hippocampus.get_experience(episode_id).td_committed_reward) == pytest.approx(1.0)
    negative = _build(("go",), seed=1)
    negative.step(["bin"], reward=None, terminal=True, dt=0.0)
    result = negative.apply_feedback_to_last_experience(
        float("-inf"), episode_id=negative.last_episode_id
    )
    assert result["reward_signal"] == pytest.approx(-1.0)


def test_tamagotchi_sleep_wrapper_is_what_makes_the_night_learn():
    """The demo's sleep block is this pair of calls inside learning_allowed()."""
    from learning_guard import learning_allowed

    channel = ActionChannel("eat", go_weight=0.5, nogo_weight=0.5, habit_strength=0.0)
    channel.selection_count = 4
    channel.last_outcome = 1.0
    learning = BasalGangliaLearning(learning_rate=0.05)
    memories = {"eat": [(1.0, 0.8, 0.1, 0.4)]}
    with pytest.raises(WakingLearningError):
        learning.apply_sleep_learning([channel], memories, None, forget_rate=0.01)
    assert channel.go_weight == pytest.approx(0.5)
    with learning_allowed():
        updated = learning.apply_sleep_learning([channel], memories, None, forget_rate=0.01)
        updated = learning.consolidate_habits(updated, serotonin=0.4)
    assert float(updated[0].go_weight) > 0.5
    assert float(updated[0].habit_strength) > 0.0
