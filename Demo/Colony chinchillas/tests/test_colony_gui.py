from __future__ import annotations

import os
import re
import math
import random
import tempfile
from pathlib import Path

from colony_agent import COLONY_ACTIONS, ChinchillaAgent
from colony_gui import (
    ACTION_ANIMATIONS,
    ACTION_SFX,
    NAME_FORMAT_REGEX,
    AgentPanel,
    ColonyGUI,
    InteractionEntry,
    ResourceBar,
    ZONE_RENDER_COORDS,
    format_agent_name,
    get_zone_render_pos,
    is_formatted_name,
)
from colony_gui.app import run_headless_ticks
from colony_gui.app import _pick_capacity_fallback
from colony_gui.app import _pick_local_zone
from colony_gui.app import _adaptive_sim_step_s
from colony_gui.app import _apply_sim_load_adaptation
from colony_gui.app import _compute_sfx_interval_s
from colony_gui.app import _collect_reproduction_diagnostics
from colony_gui.app import _prune_agent_caches
from colony_gui.app import _resolve_visual_animation_id
from colony_gui.app import _resolve_visual_zone
from colony_gui.app import _smooth_position_step
from colony_storage import ColonyStorage
from simulation_runner import SimulationRunner


def test_tc_gui_01_name_format_helpers() -> None:
    assert format_agent_name(0, 1, "M") == "G0A1SM"
    assert format_agent_name(2, 5, "F") == "G2A5SF"
    assert re.match(NAME_FORMAT_REGEX, "G12A3SM")
    assert is_formatted_name("G3A9SF") is True
    assert is_formatted_name("Луна") is False


def test_tc_gui_02_default_agent_names_follow_generation_pattern() -> None:
    founder_a = ChinchillaAgent(sex="F", generation=0)
    founder_b = ChinchillaAgent(sex="M", generation=0)
    child = ChinchillaAgent(sex="F", generation=1)

    assert is_formatted_name(founder_a.name)
    assert is_formatted_name(founder_b.name)
    assert is_formatted_name(child.name)
    assert founder_a.name.startswith("G0A") and founder_a.name.endswith("SF")
    assert founder_b.name.startswith("G0A") and founder_b.name.endswith("SM")
    assert child.name.startswith("G1A") and child.name.endswith("SF")


def test_tc_gui_03_zone_render_positions_are_valid() -> None:
    for zone, coords in ZONE_RENDER_COORDS.items():
        if coords is None:
            continue
        x, y = get_zone_render_pos(zone, agent_index=0, agent_id="agent-1")
        assert 0 <= x <= 1024
        assert 0 <= y <= 768

    x_unknown, y_unknown = get_zone_render_pos("unknown_zone_xyz", agent_index=0, agent_id="agent-2")
    assert 0 <= x_unknown <= 1024
    assert 0 <= y_unknown <= 768


def test_tc_gui_03b_same_zone_slots_have_separation() -> None:
    positions = [
        get_zone_render_pos("bowl_hay", agent_index=i, agent_id=f"agent-{i}")
        for i in range(4)
    ]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            dx = positions[i][0] - positions[j][0]
            dy = positions[i][1] - positions[j][1]
            dist = math.sqrt(dx * dx + dy * dy)
            assert dist >= 60.0


def test_tc_gui_03c_house_slot_offsets_are_compact() -> None:
    base_x, base_y = get_zone_render_pos("house", agent_index=0, agent_id="agent-h0")
    for idx in range(1, 6):
        x, y = get_zone_render_pos("house", agent_index=idx, agent_id=f"agent-h{idx}")
        dx = abs(x - base_x)
        dy = abs(y - base_y)
        assert dx <= 40
        assert dy <= 30


def test_tc_gui_04_manifest_and_action_mappings_are_consistent() -> None:
    runner = SimulationRunner()
    gui = ColonyGUI(runner)
    assert gui.sprite_manifest
    assert gui.sfx_manifest

    for action in COLONY_ACTIONS:
        animation_id = ACTION_ANIMATIONS.get(action, ACTION_ANIMATIONS["idle"])
        assert animation_id in gui.sprite_manifest

        sfx_id = ACTION_SFX.get(action)
        if sfx_id is not None:
            assert sfx_id in gui.sfx_manifest


def test_tc_gui_05_agent_panel_card_contains_affect_and_formatted_name() -> None:
    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="F", name="Луна", generation=1, is_mature=True)
    runner.add_agent(agent)

    gui = ColonyGUI(runner)
    gui._update_snapshot()

    assert gui._snapshot is not None
    panel = AgentPanel(gui._snapshot)
    card = panel.build_card(agent.agent_id, runner)

    assert card["name"].startswith("G1A")
    assert card["name"].endswith("SF")
    assert card["sex"] == "F"
    assert "stress" in card["affect"]
    assert "valence" in card["affect"]
    assert 0.0 <= card["affect"]["stress"] <= 1.0


def test_tc_gui_06_update_snapshot_does_not_modify_runner_state() -> None:
    runner = SimulationRunner()
    for _ in range(3):
        runner.add_agent(ChinchillaAgent(sex="F"))

    original_count = len(runner.agents)
    original_time = runner.sim_time

    gui = ColonyGUI(runner)
    gui._update_snapshot()
    gui._update_snapshot()
    gui._update_snapshot()

    assert len(runner.agents) == original_count
    assert runner.sim_time == original_time


def test_tc_gui_07_sim_tick_respects_pause_and_speed() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="M"))

    gui = ColonyGUI(runner)
    gui.speed = 2.0
    gui.paused = False
    start = runner.sim_time
    gui._sim_tick(0.1)
    after_run = runner.sim_time
    assert abs((after_run - start) - 0.2) < 0.05

    gui.paused = True
    gui._sim_tick(0.1)
    assert runner.sim_time == after_run


def test_tc_gui_08_resource_bar_clamp() -> None:
    assert ResourceBar.clamp_level(0.8) == 0.8
    assert ResourceBar.clamp_level(-0.1) == 0.0
    assert ResourceBar.clamp_level(1.5) == 1.0
    assert ResourceBar.clamp_level(float("nan")) == 0.0


def test_tc_gui_09_interaction_entry_expiry() -> None:
    entry = InteractionEntry(
        agent_a_id="a",
        agent_b_id="b",
        offer_type="allogroom",
        started_real_time=5.0,
        duration=3.0,
    )
    assert entry.is_expired(9.0) is True
    assert entry.is_expired(7.0) is False


def test_tc_gui_10_render_state_uses_formatted_names() -> None:
    runner = SimulationRunner()
    a = ChinchillaAgent(sex="F", name="Луна", generation=2)
    b = ChinchillaAgent(sex="M", generation=2)
    runner.add_agent(a)
    runner.add_agent(b)

    gui = ColonyGUI(runner)
    gui._update_snapshot()
    state = gui.get_render_state()

    assert state["agents"]
    for item in state["agents"]:
        assert is_formatted_name(item["name"])
        assert isinstance(item["render_pos"], tuple)
        assert len(item["render_pos"]) == 2


def test_tc_gui_11_storage_save_load_wrappers() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    runner.add_agent(ChinchillaAgent(sex="M"))
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        file_path = Path(path)
        storage = ColonyStorage(save_dir=file_path.parent)
        saved = storage.save(runner, file_path)
        assert Path(saved).exists()

        loaded = storage.load(saved)
        assert len(loaded.agents) == 2
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_tc_gui_12_headless_entrypoint_state() -> None:
    state = run_headless_ticks(agent_count=3, duration_s=0.5, dt=0.1)
    assert len(state["agents"]) == 3
    assert "sim_time_text" in state
    assert Path(state["sprite_manifest_path"]).name == "manifest.json"
    assert Path(state["sfx_manifest_path"]).name == "sfx_manifest.json"


def test_tc_gui_13_run_wheel_visual_zone_is_exclusive() -> None:
    rng = random.Random(1)
    state = {}
    base_agent = {"agent_id": "agent-1", "action": "run_wheel", "position": "floor"}

    zone_no_lock = _resolve_visual_zone(
        agent=base_agent,
        dt=0.1,
        rng=rng,
        state_by_agent=state,
        wheel_lock_owner=None,
    )
    assert zone_no_lock != "wheel"

    zone_with_lock = _resolve_visual_zone(
        agent=base_agent,
        dt=0.1,
        rng=rng,
        state_by_agent=state,
        wheel_lock_owner="agent-1",
    )
    assert zone_with_lock == "wheel"

    zone_at_wheel = _resolve_visual_zone(
        agent={"agent_id": "agent-2", "action": "run_wheel", "position": "wheel"},
        dt=0.1,
        rng=rng,
        state_by_agent=state,
        wheel_lock_owner="agent-1",
    )
    assert zone_at_wheel != "wheel"


def test_tc_gui_14_run_wheel_animation_requires_wheel_zone() -> None:
    assert (
        _resolve_visual_animation_id(
            action="run_wheel",
            visual_zone="wheel",
            preferred_animation_id="run_wheel_loop",
        )
        == "run_wheel_loop"
    )
    assert (
        _resolve_visual_animation_id(
            action="run_wheel",
            visual_zone="floor",
            preferred_animation_id="run_wheel_loop",
        )
        == ACTION_ANIMATIONS["explore"]
    )


def test_tc_gui_15_capacity_fallback_normalizes_unknown_zone() -> None:
    zone = _pick_capacity_fallback(
        action="run_wheel",
        fallback_zone="unknown_nowhere",
        zone_counts={"wheel": 1},
        rng=random.Random(7),
    )
    assert zone in ZONE_RENDER_COORDS
    assert ZONE_RENDER_COORDS[zone] is not None
    assert zone != "wheel"


def test_tc_gui_16_smooth_position_step_is_bounded() -> None:
    next_x, next_y = _smooth_position_step(
        current_x=10.0,
        current_y=20.0,
        target_x=110.0,
        target_y=220.0,
        dt=0.016,
    )
    assert 10.0 < next_x < 110.0
    assert 20.0 < next_y < 220.0


def test_tc_gui_17_smooth_position_step_clamps_large_dt() -> None:
    capped_x, _ = _smooth_position_step(
        current_x=0.0,
        current_y=0.0,
        target_x=100.0,
        target_y=0.0,
        dt=10.0,
    )
    ref_x, _ = _smooth_position_step(
        current_x=0.0,
        current_y=0.0,
        target_x=100.0,
        target_y=0.0,
        dt=0.05,
    )
    assert abs(capped_x - ref_x) < 1e-6


def test_tc_gui_18_smooth_position_step_respects_speed_cap() -> None:
    next_x, next_y = _smooth_position_step(
        current_x=0.0,
        current_y=0.0,
        target_x=1000.0,
        target_y=0.0,
        dt=0.016,
    )
    moved = math.hypot(next_x, next_y)
    assert moved <= 2.5


def test_tc_gui_19_pick_local_zone_prefers_nearby_candidates() -> None:
    rng = random.Random(3)
    choices = {"bowl_pellets", "bowl_hay", "waterer", "bars_top"}
    picked = _pick_local_zone(
        sanitized_hints=list(choices),
        previous_zone="floor",
        rng=rng,
    )
    assert picked in choices
    assert picked != "bars_top"


def test_tc_gui_20_adaptive_sim_step_grows_and_caps() -> None:
    step_small = _adaptive_sim_step_s(4)
    step_medium = _adaptive_sim_step_s(20)
    step_large = _adaptive_sim_step_s(1000)
    assert step_small < step_medium
    assert step_large >= step_medium
    assert step_large <= 0.25


def test_tc_gui_21_prune_agent_caches_removes_stale_keys() -> None:
    cache_a = {"a": 1, "b": 2}
    cache_b = {"b": 1, "c": 3}
    _prune_agent_caches({"b"}, cache_a, cache_b)
    assert cache_a == {"b": 2}
    assert cache_b == {"b": 1}


def test_tc_gui_22_apply_sim_load_adaptation_scales_and_caps() -> None:
    base = _adaptive_sim_step_s(4)
    same = _apply_sim_load_adaptation(base, 0.0)
    scaled = _apply_sim_load_adaptation(base, 0.1)
    extreme = _apply_sim_load_adaptation(base, 100.0)
    assert abs(same - base) < 1e-9
    assert scaled >= base
    assert extreme <= 0.25


def test_tc_gui_23_visual_zone_prefers_simulation_position() -> None:
    state: dict[str, dict[str, float | str]] = {}
    zone = _resolve_visual_zone(
        agent={"agent_id": "a1", "action": "sleep", "position": "house"},
        dt=0.1,
        rng=random.Random(11),
        state_by_agent=state,
        wheel_lock_owner=None,
    )
    assert zone == "house"


def test_tc_gui_24_visual_zone_does_not_fake_relocation_for_eat() -> None:
    state: dict[str, dict[str, float | str]] = {}
    zone = _resolve_visual_zone(
        agent={"agent_id": "a2", "action": "eat", "position": "floor"},
        dt=3.0,
        rng=random.Random(13),
        state_by_agent=state,
        wheel_lock_owner=None,
    )
    assert zone == "floor"


def test_tc_gui_25_legacy_name_is_upgraded_to_suffix_format() -> None:
    runner = SimulationRunner()
    agent = ChinchillaAgent(sex="M", name="G0A9", generation=0)
    runner.add_agent(agent)

    gui = ColonyGUI(runner)
    gui._update_snapshot()
    state = gui.get_render_state()
    [item] = state["agents"]
    assert item["name"] == "G0A9SM"


def test_tc_gui_26_reproduction_diagnostics_counts_are_correct() -> None:
    runner = SimulationRunner()
    adult_f = ChinchillaAgent(sex="F", is_mature=True, age=120.0)
    adult_m = ChinchillaAgent(sex="M", is_mature=True, age=240.0)
    juvenile_f = ChinchillaAgent(sex="F", is_mature=False, age=60.0)
    runner.add_agent(adult_f)
    runner.add_agent(adult_m)
    runner.add_agent(juvenile_f)

    assert adult_f.heat_cycle is not None
    adult_f.heat_cycle.phase = "estrus"
    adult_f.is_pregnant = True

    diagnostics = _collect_reproduction_diagnostics(runner)
    assert diagnostics["mature_f"] == 1
    assert diagnostics["mature_m"] == 1
    assert diagnostics["estrus_f"] == 1
    assert diagnostics["pregnant"] == 1
    assert abs(float(diagnostics["avg_age_s"]) - 140.0) < 1e-6


def test_tc_gui_27_mount_display_mapping_uses_mating_assets() -> None:
    runner = SimulationRunner()
    gui = ColonyGUI(runner)

    assert ACTION_ANIMATIONS["mount_display"] == "mating_pair_loop"
    assert ACTION_SFX["mount_display"] == "mating_coo"
    assert ACTION_ANIMATIONS["mount_display"] in gui.sprite_manifest
    assert ACTION_SFX["mount_display"] in gui.sfx_manifest


def test_tc_gui_28_sfx_interval_uses_manifest_duration() -> None:
    interval = _compute_sfx_interval_s(
        {"mating_coo": {"duration_s": 0.25}},
        "mating_coo",
    )
    assert 0.20 <= interval <= 0.30


def test_tc_gui_popstats_01_render_state_contains_population_stats() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    gui = ColonyGUI(runner)
    for _ in range(5):
        gui._sim_tick(0.1)
    gui._update_snapshot()

    state = gui.get_render_state()
    assert "population_stats" in state
    stats = state["population_stats"]
    assert isinstance(stats, dict)
    assert "extinction_risk" in stats
    assert "social_cohesion" in stats
    assert "has_data" in stats


def test_tc_gui_popstats_02_has_data_false_before_first_tick() -> None:
    runner = SimulationRunner()
    gui = ColonyGUI(runner)
    gui._update_snapshot()

    state = gui.get_render_state()
    stats = state["population_stats"]
    assert stats["has_data"] is False
    assert stats["extinction_risk"] == 0.0


def test_tc_gui_popstats_03_has_data_true_after_observed_ticks() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    gui = ColonyGUI(runner)
    for _ in range(5):
        gui._sim_tick(0.1)

    state = gui.get_render_state()
    stats = state["population_stats"]
    assert stats["has_data"] is True
    assert stats["agent_count"] == 1


def test_tc_gui_popstats_04_sim_tick_advances_observer_history() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="M"))
    gui = ColonyGUI(runner)

    assert len(gui.observer.history) == 0
    for _ in range(10):
        gui._sim_tick(0.1)

    assert len(gui.observer.history) == 2


def test_tc_gui_popstats_05_population_stats_does_not_mutate_runner() -> None:
    runner = SimulationRunner()
    for _ in range(3):
        runner.add_agent(ChinchillaAgent(sex="F"))
    gui = ColonyGUI(runner)
    for _ in range(5):
        gui._sim_tick(0.1)
    gui._update_snapshot()

    original_count = len(runner.agents)
    original_time = runner.sim_time
    state = gui.get_render_state()
    _ = state["population_stats"]
    assert len(runner.agents) == original_count
    assert runner.sim_time == original_time


def test_tc_gui_popstats_06_extinction_risk_is_in_unit_interval() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    gui = ColonyGUI(runner)
    for _ in range(5):
        gui._sim_tick(0.1)

    risk = gui.get_render_state()["population_stats"]["extinction_risk"]
    assert 0.0 <= risk <= 1.0
    assert risk > 0.3


def test_tc_gui_popstats_07_social_cohesion_is_in_unit_interval() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    runner.add_agent(ChinchillaAgent(sex="M"))
    gui = ColonyGUI(runner)
    for _ in range(5):
        gui._sim_tick(0.1)

    cohesion = gui.get_render_state()["population_stats"]["social_cohesion"]
    assert 0.0 <= cohesion <= 1.0


def test_tc_gui_popstats_08_trends_are_numeric_lists() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    gui = ColonyGUI(runner)
    for _ in range(20):
        gui._sim_tick(0.1)

    stats = gui.get_render_state()["population_stats"]
    assert isinstance(stats["stress_trend"], list)
    assert isinstance(stats["population_trend"], list)
    for value in stats["stress_trend"]:
        assert isinstance(value, float)


def test_tc_gui_popstats_09_summary_is_non_empty_for_non_empty_colony() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    runner.add_agent(ChinchillaAgent(sex="M"))
    gui = ColonyGUI(runner)
    for _ in range(5):
        gui._sim_tick(0.1)

    summary = gui.get_render_state()["population_stats"]["summary"]
    assert isinstance(summary, str)
    assert len(summary) > 5
    assert "2" in summary


def test_tc_gui_popstats_10_load_recreates_observer() -> None:
    runner = SimulationRunner()
    runner.add_agent(ChinchillaAgent(sex="F"))
    gui = ColonyGUI(runner)
    for _ in range(5):
        gui._sim_tick(0.1)
    original_observer_id = id(gui.observer)

    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        save_path = Path(path)
        storage = ColonyStorage(save_dir=save_path.parent)
        saved = storage.save_colony(runner, save_path.name)
        gui.load(saved)
        assert id(gui.observer) != original_observer_id
        assert gui.observer.runner is gui.runner
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_tc_gui_popstats_11_build_population_stats_handles_missing_observer() -> None:
    runner = SimulationRunner()
    gui = ColonyGUI(runner)
    gui.observer = None

    state = gui.get_render_state()
    stats = state["population_stats"]
    assert stats["has_data"] is False
    assert stats["extinction_risk"] == 0.0


def test_tc_gui_popstats_12_population_stats_contains_expected_keys() -> None:
    expected_keys = {
        "extinction_risk",
        "social_cohesion",
        "agent_count",
        "female_count",
        "male_count",
        "juvenile_count",
        "pregnant_count",
        "sleeping_count",
        "births_since_last",
        "deaths_since_last",
        "total_births",
        "total_deaths",
        "mean_stress",
        "mean_valence",
        "mean_energy",
        "mean_affinity",
        "bonded_pairs",
        "total_known_pairs",
        "mean_genome_diversity",
        "stress_trend",
        "energy_trend",
        "population_trend",
        "summary",
        "has_data",
    }
    runner = SimulationRunner()
    gui = ColonyGUI(runner)
    state = gui.get_render_state()
    missing = expected_keys - set(state["population_stats"].keys())
    assert not missing
