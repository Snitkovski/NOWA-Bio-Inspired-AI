# Chinchilla Agent — Implementation Specification

Russian version: [IMPLEMENTATION_SPEC.ru.md](IMPLEMENTATION_SPEC.ru.md)

## Abstract

Scientific account of the platform: [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md).

The document sets out a normative protocol for further work on the demonstration organism, the chinchilla, intended for agent implementation. Ten tasks are ordered by priority and are declared atomic and mutually independent. The opening tasks concern the local memory subsystem and the selection of behavioural chains: alignment of the reward-function keys with the affective-state dictionary, invocation of memory saving at session end and at a stated period inside the simulation step, and passage of the local scheduler’s suggestions into the chain-selection procedure.

The subsequent tasks concern temporal stability and expressiveness of the pygame loop. The protocol requires a bound on the time increment in the animation player, inclusion in the chains of eighteen library actions that the specification text classifies as belonging to no chain, filling of the postural layer from affect axes and of the micro layer during intervals between actions, and probabilistic omission of chain steps. Separate items specify circadian tinting of the background and a wellbeing indicator.

The specification records the cause of each discrepancy and the expected form of the edit in the local memory module, the scheduler, the chain configuration, and the graphics engine. It constitutes a protocol of changes that are to be carried out.

---

Specification for an agent implementation. Tasks are ordered by priority.
Each task is atomic and independent of the others.

---

## Task 1 — Correct `_calculate_reward()` in `memory_system.py`

**File:** `memory_system.py`  
**Method:** `_calculate_reward(affect_before, affect_after, chain_name)`  
**Status:** The method returns `0.0` for any input, so learning does not operate.

### Cause

The method reads the keys `'hunger'`, `'happiness'`, `'fear'`, `'calmness'`, and `'sadness'`.
Those keys are absent from `affect.state`. A different dictionary is in use:

| Key in `_calculate_reward()` | Correct key in `affect.state` |
|---|---|
| `'hunger'` | `'hunger'` ✓ (present; added by scheduling) |
| `'tiredness'` | `'tiredness'` ✓ |
| `'boredom'` | `'boredom'` ✓ |
| `'happiness'` | `'valence'` |
| `'fear'` | `'stress'` |
| `'calmness'` | `1.0 - affect.state['stress']` |
| `'sadness'` | `max(0.0, -affect.state['valence'])` |

### What is required

Rewrite the body of `_calculate_reward()`. The scoring logic remains the same; only the keys change:

```python
def _calculate_reward(self, affect_before, affect_after, chain_name):
    reward = 0.0

    # Вычислить производные значения из правильных ключей
    hunger_before   = affect_before.get('hunger', 0.0)
    hunger_after    = affect_after.get('hunger', 0.0)
    tiredness_before = affect_before.get('tiredness', 0.0)
    tiredness_after  = affect_after.get('tiredness', 0.0)
    boredom_before  = affect_before.get('boredom', 0.0)
    boredom_after   = affect_after.get('boredom', 0.0)

    valence_before  = affect_before.get('valence', 0.0)
    valence_after   = affect_after.get('valence', 0.0)
    stress_before   = affect_before.get('stress', 0.0)
    stress_after    = affect_after.get('stress', 0.0)

    # Chain-specific rewards
    if chain_name in ('eating', 'eating_and_grooming'):
        if hunger_after < hunger_before:
            reward += 0.3

    elif chain_name in ('bedtime_routine', 'sleeping'):
        if tiredness_after < tiredness_before:
            reward += 0.3

    elif chain_name in ('play', 'activity_burst', 'exploration', 'hyperactivity'):
        if boredom_after < boredom_before:
            reward += 0.25
        if valence_after > valence_before:
            reward += 0.15

    elif chain_name in ('full_grooming', 'dust_bathing'):
        if stress_after < stress_before:
            reward += 0.2

    # Общее: снижение стресса всегда хорошо
    if stress_after < stress_before:
        reward += (stress_before - stress_after) * 0.1

    # Общее: рост позитивного настроения
    if valence_after > 0.3:
        reward += valence_after * 0.05

    # Патологические цепочки — штраф
    if chain_name == 'chronic_stress':
        reward -= 0.4

    return max(-1.0, min(1.0, reward))
```

---

## Task 2 — Call `save_memory()` on exit

**File:** `main.py`  
**Method:** `cleanup()`

### Cause

`MemorySystem.save_memory()` is fully implemented and writes `saves/memory.json`.
It is called nowhere, so the whole of the learning progress is lost when the window closes.

### What is required

**Step 1.** Add the call in `cleanup()`:

```python
def cleanup(self) -> None:
    self.memory.save_memory()          # ← добавить первой строкой
    self.audio.cleanup()
    if self.pygame_engine:
        self.pygame_engine.cleanup()
    self.logger.info("Cleanup complete")
```

**Step 2.** Add periodic saving in `sim_step()`.
Add an attribute in `__init__`: `self._last_memory_save: float = 0.0`

```python
# В конце sim_step(), после блока memory consolidation:
if self.total_sim_time - self._last_memory_save >= 60.0:
    self.memory.save_memory()
    self._last_memory_save = self.total_sim_time
```

---

## Task 3 — Connect `_build_candidate_chains()` to chain selection

**File:** `main.py`  
**Method:** `_try_start_chain()`

### Cause

`SchedulingSystem.get_drive_suggestions()` returns weights for chains on the basis of hunger, tiredness, and boredom.
`_build_candidate_chains()` accepts those weights and sorts the candidates correctly.
`_try_start_chain()`, however, calls `chain_executor.select_chain()`, which does not see `drive_suggestions`.
The result is that a chinchilla with `hunger=0.95` selects `exploration` as often as `eating_and_grooming`.

### What is required

Replace the call to `select_chain()` with `_build_candidate_chains()` inside `_try_start_chain()`:

```python
def _try_start_chain(self) -> None:
    drive_suggest = self.scheduler.get_drive_suggestions()

    # Было:
    # affect_ctx = self.affect.get_chain_context()
    # chain = self.chain_executor.select_chain(affect_ctx)

    # Стало:
    candidates = self._build_candidate_chains(drive_suggest)
    chain = candidates[0] if candidates else None

    if chain:
        cmd = self.chain_executor.start_chain(chain)
        if cmd:
            self._send_command(cmd)
            self.chain_cooldown_s = random.uniform(
                self.CHAIN_COOLDOWN_MIN_S, self.CHAIN_COOLDOWN_MAX_S
            )
            self.last_chain_name    = chain
            self.chain_start_affect = self.affect.get_state()
            return

    self._dispatch_idle_action()
    self.chain_cooldown_s = random.uniform(
        self.CHAIN_COOLDOWN_MIN_S, self.CHAIN_COOLDOWN_MAX_S
    )
```

> `_build_candidate_chains()` is already implemented in `main.py` (line 539); no change to it is required.

---

## Task 4 — Cap `dt` in `AnimationPlayer`

**File:** `pygame_engine.py`  
**Class:** `AnimationPlayer`, method `update()`

### Cause

When the window is minimised or restored, `wall_dt` jumps to 2–5 s.
`SpriteMovement` is protected by a cap in the main loop (`wall_dt = min(wall_dt, 0.2)`).
`AnimationPlayer` accumulates `time_in_frame += dt` without a bound, so the animation jumps several seconds forward.

### What is required

One line at the start of `AnimationPlayer.update()`:

```python
def update(self, dt: float) -> None:
    dt = min(dt, 0.1)   # не прыгать больше одного кадра за раз
    if self.finished:
        return
    self.time_in_frame += dt
    # ... остальное без изменений
```

---

## Task 5 — Include 18 “dead” actions in the chains

**File:** `config.py`  
**Constant:** `BEHAVIORAL_CHAINS`

### Cause

Eighteen actions are defined in `ACTION_LIBRARY` but belong to no chain:

```
eat_treat, gnaw_mineral, toilet_main, explore_corner, play_toy, gnaw_wood,
problem_solve, overgroom_other, vocalize_squeak, vocalize_alarm,
vocalize_teeth, avoid_hand, follow_finger, thump_hind, fur_slip,
wall_jump, tail_raise, nose_twitch
```

### What is required

Apply the following edits to `BEHAVIORAL_CHAINS`:

| Action | Add to chain | Position |
|---|---|---|
| `eat_treat` | `eating_and_grooming` | after `eat_hay` |
| `gnaw_mineral` | `territorial_patrol` | after `toilet_mark` |
| `toilet_main` | `bedtime_routine` | before `rearrange_bedding` |
| `explore_corner` | `exploration` | replace the second `sniff_air` |
| `play_toy` | `activity_burst` | between `toss_toy` and `chase_toy` |
| `gnaw_wood` | `nesting` | after the first `rearrange_bedding` |
| `problem_solve` | `exploration` | before `rearrange_bedding` |
| `thump_hind` | `mild_fear` | between `freeze` and `ear_flat` |
| `fur_slip` | `extreme_fear` | after `flee_corner` |
| `wall_jump` | `extreme_fear` | before `freeze` |
| `vocalize_squeak` | `mild_fear` | at the start |
| `vocalize_alarm` | `extreme_fear` | at the start (`alarm_call` is already present; insert immediately after it) |
| `vocalize_teeth` | `chronic_stress` | between `bar_chewing` and `stereotypy_pacing` |
| `avoid_hand` | `social_contact` | alternative to `take_treat` when `trust` is low |
| `follow_finger` | `social_contact` | after `watch_owner` |
| `tail_raise` | `territorial_patrol` | after `stand_upright` |
| `nose_twitch` | `exploration` | at the start |
| `overgroom_other` | `chronic_stress` | after `overgroom_fur` |

Final form of the changed chains:

```python
BEHAVIORAL_CHAINS = {
    "eating_and_grooming": [
        "eat_pellets", "eat_hay", "eat_treat",       # ← eat_treat добавлен
        "drink_water", "groom_face", "groom_body", "rest_loaf"
    ],
    "exploration": [
        "nose_twitch",                                # ← добавлен
        "sniff_air", "stand_upright", "explore_corner",  # ← explore_corner вместо approach_door
        "inspect_new_obj", "problem_solve",           # ← problem_solve добавлен
        "sniff_hand", "gnaw_toy", "gnaw_wood",        # ← gnaw_wood добавлен
        "carry_object", "rearrange_bedding"
    ],
    "activity_burst": [
        "stand_upright", "sniff_air", "run_wheel",
        "jump_hop_play", "play_toy", "toss_toy",      # ← play_toy добавлен
        "chase_toy", "jump_shelf_up", "observe_room", "drink_water"
    ],
    "mild_fear": [
        "vocalize_squeak",                            # ← добавлен
        "ear_forward", "whisker_twitch",
        "thump_hind",                                 # ← добавлен
        "freeze", "ear_flat", "press_flat",
        "sniff_air", "stand_upright", "patrol_floor"
    ],
    "extreme_fear": [
        "vocalize_alarm", "alarm_call",               # ← vocalize_alarm добавлен
        "wall_jump",                                  # ← добавлен
        "flee_corner", "fur_slip",                    # ← fur_slip добавлен
        "freeze", "hide_house", "press_flat", "eye_half_close", "doze_shelf"
    ],
    "chronic_stress": [
        "observe_room", "bar_chewing",
        "vocalize_teeth",                             # ← добавлен
        "stereotypy_pacing", "overgroom_fur",
        "overgroom_other",                            # ← добавлен
        "hide_house", "vocalize_bark"
    ],
    "territorial_patrol": [
        "stretch_body", "patrol_floor", "sniff_corners",
        "toilet_mark", "gnaw_mineral",               # ← gnaw_mineral добавлен
        "stand_upright", "tail_raise",               # ← tail_raise добавлен
        "climb_bars", "observe_room"
    ],
    "nesting": [
        "rearrange_bedding", "dig_bedding",
        "gnaw_wood",                                  # ← добавлен
        "carry_object", "cache_food", "rearrange_bedding"
    ],
    "bedtime_routine": [
        "eat_hay", "drink_water", "groom_body",
        "toilet_main",                                # ← добавлен
        "rearrange_bedding", "cache_food", "hide_house", "sleep_house"
    ],
    "social_contact": [
        "watch_owner", "follow_finger",              # ← follow_finger добавлен
        "approach_door", "vocalize_chirp",
        "sniff_hand", "take_treat", "allow_pet",
        "avoid_hand",                                 # ← добавлен (конец — если не понравилось)
        "solicit_pet"
    ],
    # Остальные цепочки без изменений:
    # morning_awakening, full_grooming, dust_bathing, hyperactivity
}
```

---

## Task 6 — Postural layer: ears and posture from affect

**Files:** `main.py`  
**Layer:** `postural` in `pygame_engine.py` (already supported; unused)

### Cause

The engine renders three layers: `action`, `postural`, and `micro`. The `postural` and `micro` layers are never filled, so the multilayer system sits idle. The chinchilla does not express affective state by posture.

Sprites available on the postural layer (from `manifest.json`):

- `ears_forward_hold` — interest, alertness
- `ears_flat_hold` — fear, stress
- `tail_up_hold` — excitement
- `press_flat_hold` — flattened, suppressed posture
- `eyes_droop_hold` — fatigue

### What is required

Add the method `_update_postural_layer()` to `ChinchillaAgent` and call it from `sim_step()` once per second (not on every tick).

Add an attribute in `__init__`: `self._postural_timer: float = 0.0`

```python
def _update_postural_layer(self) -> None:
    """Отправляет постуральную анимацию на основе текущего affect.state."""
    s = self.affect.state
    stress    = s.get('stress', 0.0)
    curiosity = s.get('curiosity', 0.5)
    arousal   = s.get('arousal', 0.5)
    tiredness = s.get('tiredness', 0.0)

    if stress > 0.6:
        anim = 'ears_flat_hold'
    elif tiredness > 0.7:
        anim = 'eyes_droop_hold'
    elif curiosity > 0.65:
        anim = 'ears_forward_hold'
    elif arousal > 0.75:
        anim = 'tail_up_hold'
    else:
        return  # нейтральная поза — не перекрывать action

    if self.pygame_engine:
        self.pygame_engine.queue_action({
            'action_id': f'postural_{anim}',
            'anim':      anim,
            'sfx':       None,
            'position':  'current',
            'duration':  [8, 20],
            'subtitle':  '',
            'loop':      True,
            'layer':     'postural',
        })
```

In `sim_step()`, after the affect update:

```python
self._postural_timer -= dt
if self._postural_timer <= 0:
    self._update_postural_layer()
    self._postural_timer = 1.0   # обновлять раз в секунду
```

---

## Task 7 — Micro-animations during pauses (idle does not freeze)

**File:** `main.py`

### Cause

Between chains the chinchilla stands completely still (`loaf_idle`, 2 frames).
Real chinchillas continuously move the whiskers, twitch the nose, and turn the ears.

Sprites available on the micro layer:

- `whisker_loop` (6 frames, 8 fps)
- `nose_twitch_loop` (4 frames, 8 fps)
- `head_track_loop` (6 frames, 8 fps)

### What is required

Add an attribute in `__init__`: `self._micro_timer: float = random.uniform(2.0, 5.0)`

Add the method:

```python
def _dispatch_micro_action(self) -> None:
    """Проигрывает короткую микро-анимацию на micro-слое, не прерывая action."""
    micro_pool = ['whisker_loop', 'nose_twitch_loop', 'head_track_loop']
    anim = random.choice(micro_pool)
    if self.pygame_engine and hasattr(self.pygame_engine, 'clips'):
        if anim not in self.pygame_engine.clips:
            return
    if self.pygame_engine:
        self.pygame_engine.queue_action({
            'action_id': f'micro_{anim}',
            'anim':      anim,
            'sfx':       None,
            'position':  'current',
            'duration':  [2, 4],
            'subtitle':  '',
            'loop':      False,
            'layer':     'micro',
        })
```

In `sim_step()`, on every tick:

```python
self._micro_timer -= dt
if self._micro_timer <= 0:
    self._dispatch_micro_action()
    self._micro_timer = random.uniform(3.0, 8.0)
```

---

## Task 8 — Variable steps in chains (probabilities)

**Files:** `config.py`, `behavioral_chains.py`

### Cause

`drink_water` occurs in 5 chains, `groom_body` in 4, and `stand_upright` in 4.
Every run of a chain is identical; there is no variation.

### What is required

**Step 1.** Change the chain format in `config.py`:
each element is now a tuple `(action_id, probability)`. For backward compatibility, a string without a probability is interpreted as 1.0.

```python
BEHAVIORAL_CHAINS = {
    "morning_awakening": [
        ("sleep_house",   1.0),
        ("stretch_body",  1.0),
        ("yawn",          0.8),
        ("groom_face",    0.9),
        ("drink_water",   0.6),   # не каждое утро
        ("eat_pellets",   1.0),
        ("patrol_floor",  0.7),
        ("run_wheel",     0.5),
    ],
    "eating_and_grooming": [
        ("eat_pellets",   1.0),
        ("eat_hay",       0.8),
        ("eat_treat",     0.3),   # редкое угощение
        ("drink_water",   0.7),
        ("groom_face",    1.0),
        ("groom_body",    0.8),
        ("rest_loaf",     0.9),
    ],
    # Для остальных цепочек оставить вероятность 1.0 везде,
    # кроме drink_water (0.5–0.7) и rest_loaf (0.8–0.9)
}
```

**Step 2.** Update `BehavioralChainExecutor.get_next_action_in_chain()` in `behavioral_chains.py`:

```python
def get_next_action_in_chain(self):
    if not self.current_chain:
        return None

    chain_actions = BEHAVIORAL_CHAINS[self.current_chain]

    while self.chain_progress < len(chain_actions):
        step = chain_actions[self.chain_progress]
        self.chain_progress += 1

        # Поддержка обоих форматов: строка или (action_id, probability)
        if isinstance(step, tuple):
            action_id, probability = step
        else:
            action_id, probability = step, 1.0

        # Пропустить шаг с заданной вероятностью
        if random.random() > probability:
            self.logger.debug(f"Skipped step {action_id} (p={probability:.1f})")
            continue

        # Реализовать действие
        command = self.action_realizer.realize_action(
            action_id,
            pressure=0.9,
            context={"chain_context": self.current_chain}
        )
        if command:
            self.logger.debug(
                f"Chain step {self.chain_progress}/{len(chain_actions)}: {action_id}"
            )
            return command

    # Цепочка завершена
    self.chain_history.append(self.current_chain)
    if len(self.chain_history) > 50:
        self.chain_history.pop(0)
    self.logger.info(f"Chain '{self.current_chain}' completed")
    self.current_chain = None
    self.chain_progress = 0
    return None
```

---

## Task 9 — Circadian tinting of the background

**File:** `pygame_engine.py`  
**Method:** `render()`

### Cause

`SchedulingSystem` computes `circadian_phase` (0.0 = midnight, 0.5 = noon), but the cage does not change visually.

### What is required

**Step 1.** Add a method to `PygameEngine`:

```python
def set_circadian_phase(self, phase: float) -> None:
    """Обновить фазу циркадного ритма для окраски фона (0.0–1.0)."""
    self._circadian_phase = max(0.0, min(1.0, phase))
```

Add an attribute in `__init__`: `self._circadian_phase: float = 0.5`

**Step 2.** In `render()`, replace the static `screen.fill()`:

```python
# Было:
self.screen.fill((235, 228, 215))

# Стало:
import math
day_t = max(0.0, math.sin(self._circadian_phase * math.pi))  # 0.0 ночь → 1.0 день
r = int(100 + 135 * day_t)
g = int( 90 + 138 * day_t)
b = int( 80 + 135 * day_t)
self.screen.fill((r, g, b))
```

Colours: night `(100, 90, 80)` → day `(235, 228, 215)`.

**Step 3.** In `main.py`, in `sim_step()` after the scheduler update:

```python
if self.pygame_engine and hasattr(self.pygame_engine, 'set_circadian_phase'):
    circadian = self.scheduler.get_circadian_state()
    self.pygame_engine.set_circadian_phase(circadian['phase'])
```

---

## Task 10 — Wellbeing indicator

**File:** `pygame_engine.py`

### Cause

There is no quick way to assess the chinchilla’s state without opening the debug overlay.

### What is required

Add the method `set_wellbeing()` and a call in `render()`.

In `__init__`: `self._wellbeing: float = 1.0`, a value in the range 0.0–1.0.

```python
def set_wellbeing(self, stress: float, valence: float, arousal: float,
                  pathological_chain: bool = False) -> None:
    """Обновить индикатор самочувствия. Вызывать раз в секунду."""
    if pathological_chain:
        self._wellbeing = 0.0       # красный
    elif stress > 0.6:
        self._wellbeing = 0.2
    elif stress > 0.3:
        self._wellbeing = 0.5       # жёлтый
    elif arousal < 0.2:
        self._wellbeing = -1.0      # синий (спит)
    else:
        self._wellbeing = 1.0       # зелёный
```

In `render()`, after `_draw_furniture()`:

```python
self._draw_wellbeing_bar()
```

```python
def _draw_wellbeing_bar(self) -> None:
    """Цветная полоска 12×80 px в правом верхнем углу клетки."""
    wb = self._wellbeing
    if wb < 0:
        color = (70, 130, 200)    # синий — спит
    elif wb < 0.3:
        color = (192, 40, 40)     # красный — стресс/патология
    elif wb < 0.6:
        color = (200, 160, 30)    # жёлтый — беспокойство
    else:
        color = (60, 160, 70)     # зелёный — норма

    bar_rect = pygame.Rect(self.width - 100, 60, 12, 80)
    pygame.draw.rect(self.screen, (50, 50, 50), bar_rect.inflate(2, 2))  # рамка
    pygame.draw.rect(self.screen, color, bar_rect)

    lbl = self.font_dbg.render("wellbeing", True, (160, 150, 140))
    self.screen.blit(lbl, (self.width - 118, 145))
```

In `main.py`, add the attribute `self._wellbeing_timer: float = 0.0`, and in `sim_step()`:

```python
self._wellbeing_timer -= dt
if self._wellbeing_timer <= 0 and self.pygame_engine:
    s = self.affect.state
    pathological = self.chain_executor.current_chain == 'chronic_stress'
    self.pygame_engine.set_wellbeing(
        stress=s.get('stress', 0.0),
        valence=s.get('valence', 0.0),
        arousal=s.get('arousal', 0.5),
        pathological_chain=pathological,
    )
    self._wellbeing_timer = 1.0
```

---

## Implementation order

| # | Task | Files | Complexity | Importance |
|---|---|---|---|---|
| 1 | Correct `_calculate_reward()` | `memory_system.py` | Low | Critical |
| 2 | Call `save_memory()` | `main.py` | Minimal | Critical |
| 3 | Connect `_build_candidate_chains()` | `main.py` | Low | Critical |
| 4 | Cap `dt` in `AnimationPlayer` | `pygame_engine.py` | Minimal | Important |
| 5 | Include dead actions in chains | `config.py` | Low | Important |
| 6 | Postural layer | `main.py` | Medium | Improvement |
| 7 | Micro-animations during pauses | `main.py` | Medium | Improvement |
| 8 | Variable steps (probabilities) | `config.py`, `behavioral_chains.py` | Medium | Improvement |
| 9 | Circadian background tint | `pygame_engine.py`, `main.py` | Low | Proposal |
| 10 | Wellbeing indicator | `pygame_engine.py`, `main.py` | Medium | Proposal |

Tasks 1–3 may be carried out in any order; they are independent.
Task 8 depends on task 5 (edits to the chains are better applied in a single pass).
