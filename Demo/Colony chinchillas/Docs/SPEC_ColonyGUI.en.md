# SPEC: Colony GUI (Current Implementation)

Russian version: [SPEC_ColonyGUI.ru.md](SPEC_ColonyGUI.ru.md)

## Abstract

Scientific account of the colony: [COLONY_SPEC.en.md](COLONY_SPEC.en.md).

This document describes the current implementation of the graphical layer `colony_gui` as a read-only presentation over `SimulationRunner`. The layer reads a state snapshot, builds render data — positions, animations, observer statistics, and resources — and runs the demonstration loop, including a windowless mode. Agent action selection and the cognitive logic of NOWA remain outside this layer.

The specification states the entry points, the composition of scene and panel modules, the canonical individual name format, deterministic placement in cage zones with capacity limits, and consistency of the wheel animation with the lock owner. The visual zone follows the agent's position by default, so that display does not introduce movements of its own. Caching of the static scene, a bound on frame step, an adaptive simulation step, and the resolution order for sprite and sound directories are stated separately.

In the colony installation, this layer provides reproducible observation: demographic and behavioural events stay bound to simulation state, and the interface does not replace the decision loop. The specification separates presentation of the colony from the model of the individual and states the conditions under which the visual protocol does not distort the spatial and resource dynamics of the multi-agent system.

Version: 2.4
Updated: 2026-04-09

## 1. Purpose

`colony_gui` is a read-only presentation layer over `SimulationRunner`.

It does:
- read snapshot data from runner;
- build render state (positions, animations, observer stats, resources);
- run pygame demo loop and headless mode.

It does not:
- decide agent behavior;
- replace NOWA action selection;
- mutate core cognitive logic.

## 2. Entrypoints

All executable code is in `src`.

Primary launchers:
- `src/gui.py` (recommended)
- `python -m colony_gui` via `src/colony_gui/__main__.py`

Examples:

```bash
cd "Demo/Colony chinchillas/src"
python gui.py --agents 4
python gui.py --headless --agents 4 --duration 5
python -m colony_gui --agents 6
```

## 3. GUI Files

- `src/colony_gui/colony_gui.py`: snapshot read-model, render-state builder, speed/pause, save/load wrappers, `population_stats`.
- `src/colony_gui/app.py`: pygame loop, scene drawing, smoothing, adaptive timing, SFX, consolidated stats panel.
- `src/colony_gui/config.py`: render constants, zone coordinates, action->animation/sfx mapping, name format helpers.
- `src/colony_gui/cage_view.py`: deterministic zone slot placement.
- `src/colony_gui/agent_panel.py`: card data model.
- `src/colony_gui/detail_popup.py`: detailed agent info model.
- `src/colony_gui/interaction_overlay.py`: recent social interactions extraction.

## 4. Agent Name Format

Canonical display format:

`G<generation>A<index_in_generation>S<sex>`

Examples:
- `G0A1SM`
- `G2A5SF`

Rules:
- regex: `^G[0-9]+A[0-9]+S[MFU]$`
- generated via `format_agent_name(generation, index_in_generation, sex)`
- if source name is already canonical, it is preserved
- legacy names `GxAy` are upgraded in GUI by adding sex suffix

## 5. Zone Placement and Occupancy

Render zones are defined by `ZONE_RENDER_COORDS`.

Positioning strategy:
- each zone has deterministic slot offsets;
- overflow uses deterministic jitter based on `agent_id`;
- unknown zones fall back to `floor`.

Exclusive visual capacity:
- `wheel: 1`
- `dustbath: 1`

If capacity is full, GUI uses fallback zones from `_pick_capacity_fallback(...)`.

## 6. Wheel Consistency

Wheel rendering is lock-aware:
- wheel-running sprite is allowed only for wheel lock owner;
- if another agent is currently lock owner, non-owner cannot be rendered as wheel runner;
- wheel animation id is downgraded to walk animation when visual zone is not `wheel`.

This prevents the artifact of several agents running one wheel.

## 7. Visual Zone Resolution Policy

Current policy in `app.py`:
- keep visual placement aligned with simulation `agent.position` by default;
- do not force independent GUI relocations for standard actions;
- keep action hints table for compatibility and controlled fallback behavior.

This avoids conflicts between GUI movement and agent movement.

## 8. Performance and Smoothness

Implemented optimizations:
- static cage scene cache (`static_scene`);
- sprite and SFX clip caches;
- name and panel text surface caches;
- stale cache pruning when agents disappear;
- clamped frame delta (`MAX_FRAME_DT_S`);
- bounded smoothing step (`_smooth_position_step`);
- adaptive simulation step size based on agent count and tick-cost EMA;
- capped catch-up steps to avoid spiral slowdown.

## 9. Assets

Manifest-based assets:
- sprites manifest: `manifest.json`
- sfx manifest: `sfx_manifest.json`

Directory resolution order (`resolve_assets_dir`):
1. `Demo/Colony chinchillas/assets/<kind>`
2. `Demo/Colony chinchillas/<kind>`
3. `Demo/Tamagochi Chinchilla/<kind>` (legacy fallback)

## 10. Status Panel and Controls

In current pygame loop:
- `SPACE`: pause/resume
- `+` / `-`: speed up/down
- `M`: sound on/off
- `ESC`: quit

UI layout:
- cage is drawn inside `CAGE_RECT`;
- one consolidated panel is drawn below cage border (not on top of cage);
- panel uses Russian labels and bar indicators.

Panel content:
- line 1: time, population (females/males), average age;
- line 2: sexually mature, estrus, pregnant, births/deaths, ties/strong pairs;
- bar row 1: stress, energy, cohesion, extinction risk;
- bar row 2: resource levels of food, hay, and water;
- line 3: speed/pause/sound state and key bindings.

Interpretation note:
- `estrus` is an instantaneous live counter (`heat_cycle.phase == "estrus"`).
- visual social clustering near food/hay does not imply successful mating.
- mating hearts are rendered only when both agents are in `mount_display` and mutually linked via `_current_mate_id`.

## 11. Validation

Primary GUI tests:

```bash
cd "Demo/Colony chinchillas"
pytest -q tests/test_colony_gui.py
```

Headless smoke:

```bash
cd "Demo/Colony chinchillas/src"
python gui.py --headless --agents 4 --duration 2
```
