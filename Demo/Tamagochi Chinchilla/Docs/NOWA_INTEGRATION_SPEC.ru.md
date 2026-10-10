## Аннотация

English version: [NOWA_INTEGRATION_SPEC.en.md](NOWA_INTEGRATION_SPEC.en.md)

Научное описание установки: [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md).

Документ задаёт нормативный протокол интеграции демонстрационного организма «шиншилла» с когнитивным ядром репозитория. Протокол предписывает замену локальных подсистем каноническими компонентами: четырёхмерного адаптера аффекта — восьмимерным аффективным пространством; локального планировщика трёх циклов потребностей — системой драйвов и системой энергии; эвристического отбора поведенческих цепочек — конкурирующим контуром базальных ганглиев с таламическим выбором; консолидации локальной памяти — менеджером сна, гиппокампом и корковой памятью. Отдельными задачами вводятся нейромодуляторное состояние, состояние бодрствования, слой эмоциональной регуляции и слой арбитража конфликта.

Десять задач образуют последовательность интерфейсных замен. Для каждой фиксируются удаляемая или сохраняемая локальная точка входа, инициализация модуля ядра, отображение драйвов на поведенческие цепочки и место вызова внутри шага симуляции. Обучение каналов базальных ганглиев и корковая консолидация отнесены к фазе сна. Бодрствование связывается с предпочтением цепочек отхода ко сну и с оценкой когнитивной надёжности, передаваемой слою визуализации. Завершающие задачи задают отладочное отображение слоёв ядра и сериализацию его состояния между сеансами.

Протокол фиксирует целевой состав замены и порядок работ. Точка входа демонстрации одновременно импортирует модули ядра, в том числе аффективное пространство, базальные ганглии, гиппокамп, сон, нейромодуляторы и бодрствование, и локальные классы SchedulingSystem и MemorySystem. Подключение отдельных модулей и завершение программы замены представляют собой различные статусы.

---

# NOWA-Powered Chinchilla — Спецификация интеграции

Цель: заменить все кастомные подсистемы тамагочи настоящими NOWA-компонентами.
После реализации демо должно наглядно показывать работу каждого слоя NOWA.

---

## Архитектурная карта замен

| Что сейчас | NOWA-компонент | Файл |
|---|---|---|
| `AffectAdapter` (четырёхмерная заглушка) | `AffectiveSpace` (8D) + `AffectiveState` | `affective_space.py` |
| `SchedulingSystem` (3 цикла) | `DriveSystem` из `autonomous_organism.py` | `autonomous_organism.py` |
| `_build_candidate_chains()` | `BasalGangliaGate` + `ThalamicGate` | `basal_ganglia.py` |
| Нет аналога | `NeuromodulatorState` | `neuromodulators.py` |
| Нет аналога | `WakefulnessState` | `wakefulness.py` |
| `memory.consolidate_memory()` | `SleepManager` + `CortexMemory` | `sleep.py` |
| Нет аналога | `EmotionalRegulationLayer` | `emotional_regulation.py` |
| Нет аналога | `ConflictArbitrationLayer` | `conflict_arbitration.py` |

---

## Задача 1 — Заменить SchedulingSystem на DriveSystem

**Удалить:** `scheduling_system.py` и все импорты `SchedulingSystem` из `main.py`  
**Файл:** `main.py`, класс `ChinchillaAgent.__init__()`

### Инициализация

```python
from autonomous_organism import DriveSystem, DriveRule, default_drive_rules, EnergySystem

# В __init__():
self.drives = DriveSystem(
    rules={
        # Переопределяем дефолтные правила под биологию шиншиллы
        "energy_need": DriveRule(
            accumulation_rate=0.006,   # голод нарастает медленнее человека
            discharge_rate=0.001,
            decay_rate=0.001,
            affect_weights={"stress": 0.010, "arousal": 0.004},
        ),
        "exploration": DriveRule(
            accumulation_rate=0.011,
            discharge_rate=0.0012,
            decay_rate=0.0012,
            affect_weights={"curiosity": 0.020, "dominance": 0.008, "stress": -0.005},
        ),
        "social_drive": DriveRule(
            accumulation_rate=0.008,
            discharge_rate=0.0015,
            decay_rate=0.0010,
            affect_weights={"trust": 0.020, "attachment": 0.014, "stress": -0.010},
        ),
        "curiosity": DriveRule(
            accumulation_rate=0.018,
            discharge_rate=0.001,
            decay_rate=0.001,
            affect_weights={"curiosity": 0.025, "stress": -0.005, "stability": 0.004},
        ),
        "goal_tension": DriveRule(
            accumulation_rate=0.010,
            discharge_rate=0.0010,
            decay_rate=0.0015,
            affect_weights={"dominance": 0.018, "stability": 0.006, "stress": 0.008},
        ),
    }
)
self.energy = EnergySystem()
```

### Маппинг DriveSystem → BEHAVIORAL_CHAINS

Заменить `DRIVE_TO_CHAINS` в `_build_candidate_chains()`:

```python
DRIVE_TO_CHAINS = {
    "energy_need":   ["eating_and_grooming", "morning_awakening", "bedtime_routine"],
    "exploration":   ["exploration", "territorial_patrol", "nesting"],
    "social_drive":  ["social_contact"],
    "curiosity":     ["activity_burst", "hyperactivity", "exploration"],
    "goal_tension":  ["territorial_patrol", "nesting", "full_grooming"],
}
```

### Вызов DriveSystem.update() в sim_step()

Заменить блок `cycle_changes = self.scheduler.update(...)`:

```python
# Обновить DriveSystem — принимает 8D снимок аффекта
affect_snapshot = self.affect_space.legacy_axes_snapshot()
discharge_overrides = {}

# Разрядить drive если шиншилла активно в цепочке
current_chain = self.chain_executor.current_chain
if current_chain in ("eating_and_grooming", "morning_awakening", "bedtime_routine"):
    discharge_overrides["energy_need"] = 0.08   # быстрое снижение голода
if current_chain in ("exploration", "territorial_patrol", "nesting"):
    discharge_overrides["exploration"] = 0.06
if current_chain == "social_contact":
    discharge_overrides["social_drive"] = 0.07
if current_chain in ("activity_burst", "hyperactivity"):
    discharge_overrides["curiosity"] = 0.05

drive_snapshot = self.drives.update(
    dt=dt,
    affect_snapshot={"axes": affect_snapshot},
    discharge_overrides=discharge_overrides,
    energy_level=self.energy.snapshot()["level"],
)

# Обновить EnergySystem
physiology_mode = "low_energy" if drive_snapshot.get("energy_need", 0) > 0.7 else "passive"
self.energy.update(dt=dt, cognitive_load=0.3, rest_time=0.0)
```

### get_drive_suggestions() — адаптер

`_build_candidate_chains()` принимает `drive_suggestions: Dict[str, float]`.
Передавать `drive_snapshot` напрямую — DriveSystem уже возвращает `{drive_name: value}`.

---

## Задача 2 — Заменить AffectAdapter на AffectiveSpace

**Удалить:** класс `AffectAdapter` из `main.py`  
**Добавить:** обёртку вокруг `AffectiveSpace`

### Инициализация

```python
from affective_space import AffectiveSpace, EmotionalImpulse

# В __init__():
self.affect_space = AffectiveSpace(
    # Начальное состояние шиншиллы — спокойная, любопытная
    initial_state={
        "valence":    0.3,
        "arousal":    0.5,
        "dominance":  0.4,
        "stress":     0.0,
        "trust":      0.5,
        "curiosity":  0.6,
        "stability":  0.5,
        "attachment": 0.3,
    },
    # Параметры затухания к нейтралю
    decay_params={
        "valence": 0.98, "arousal": 0.97, "dominance": 0.99,
        "stress": 0.96, "trust": 0.995, "curiosity": 0.97,
        "stability": 0.995, "attachment": 0.998,
    },
)

# Совместимость: self.affect.state остаётся как псевдоним
@property
def _affect_state(self):
    return self.affect_space.legacy_axes_snapshot()
```

### Обновление AffectiveSpace в sim_step()

Заменить `self.affect.update(dt=dt)`:

```python
# 1. Импульс от нейромодуляторов (Task 3)
nm_impulse = EmotionalImpulse(
    source="neuromodulators",
    payload={
        "valence":   self.neuromod.dopamine * 0.3 - self.neuromod.cortisol * 0.4,
        "arousal":   self.neuromod.norepinephrine * 0.5 + self.neuromod.dopamine * 0.2,
        "stress":    self.neuromod.cortisol * 0.6,
        "curiosity": self.neuromod.acetylcholine * 0.4,
        "stability": self.neuromod.serotonin * 0.3 - self.neuromod.cortisol * 0.2,
    },
    intensity=0.4,
)
self.affect_space.update(
    dt=dt,
    impulses=[nm_impulse],
    wakefulness=self.wakefulness.wakefulness,
)
```

### Обратная совместимость: self.affect.state

Везде где код читает `self.affect.state` — заменить на:

```python
# Добавить property в ChinchillaAgent:
@property
def affect(self):
    """Обратная совместимость: возвращает псевдо-объект с .state"""
    return _AffectProxy(self.affect_space, self.drives)

class _AffectProxy:
    def __init__(self, space, drives):
        snap = space.legacy_axes_snapshot()
        # Дополнить drives → affect-ключи для SchedulingSystem-совместимости
        d = drives.snapshot()
        self.state = {
            **snap,
            "hunger":    d.get("energy_need", 0.0),
            "tiredness": d.get("goal_tension", 0.0),   # goal_tension ≈ усталость от задач
            "boredom":   1.0 - d.get("curiosity", 0.5),
        }
    def get_state(self): return dict(self.state)
    def get_chain_context(self): return {"affect": self.state, **self.state}
```

---

## Задача 3 — Добавить NeuromodulatorState

**Файл:** `main.py`

### Инициализация

```python
from neuromodulators import NeuromodulatorState

# В __init__():
self.neuromod = NeuromodulatorState()
```

### Обновление в sim_step()

```python
# 1. Decay каждый тик
self.neuromod.decay_over_time(elapsed=dt)

# 2. Дельты от WakefulnessState (Task 4)
wake_deltas = self.wakefulness.get_neuromodulator_deltas()
self.neuromod.cortisol      += wake_deltas["cortisol"]      * dt
self.neuromod.norepinephrine += wake_deltas["norepinephrine"] * dt
self.neuromod.serotonin     += wake_deltas["serotonin"]     * dt
self.neuromod._clamp_all()

# 3. Обновление по цепочкам — цепочки влияют на нейромодуляторы
chain = self.chain_executor.current_chain
if chain == "hyperactivity":
    self.neuromod.update_from_signals(novelty=0.6, reward=0.1)  # NE↑ DA↑
elif chain == "chronic_stress":
    self.neuromod.update_from_signals(conflict=0.7, reward=-0.3)  # CORT↑
elif chain in ("eating_and_grooming", "full_grooming", "dust_bathing"):
    self.neuromod.update_from_signals(reward=0.3, stable_repetition=True)  # 5HT↑
elif chain in ("activity_burst", "exploration"):
    self.neuromod.update_from_signals(novelty=0.4, reward=0.15)  # ACh↑ NE↑
elif chain == "social_contact":
    self.neuromod.update_from_signals(reward=0.2, stable_repetition=False)  # DA↑
```

### Передача нейромодуляторов в BG (Task 5)

`BasalGangliaGate.process()` принимает `dopamine_level`, `cortisol_level`, `norepinephrine_level` напрямую из `self.neuromod`.

---

## Задача 4 — Добавить WakefulnessState

**Файл:** `main.py`

### Инициализация

```python
from wakefulness import WakefulnessState

# В __init__():
self.wakefulness = WakefulnessState(initial_wakefulness=0.1)  # слегка отдохнувшая
```

### Обновление в sim_step()

```python
# Детектировать режим сна по текущей цепочке
sleeping_chains = {"bedtime_routine", "extreme_fear"}  # hide_house/doze_shelf
sleeping_actions = {"sleep_house", "doze_shelf", "hide_house"}
is_sleeping = (
    self.chain_executor.current_chain in sleeping_chains or
    (self.current_action or {}).get("action_id", "") in sleeping_actions
)

if is_sleeping:
    self.wakefulness.update_sleeping(elapsed_seconds=dt)
else:
    self.wakefulness.update_waking(elapsed_seconds=dt)

# Передать в PygameEngine для постурального слоя
reliability = self.wakefulness.get_cognitive_reliability()
# reliability < 0.3 → шиншилла зевает, глаза закрываются
```

### Влияние wakefulness на выбор цепочек

```python
# В _build_candidate_chains(): если wakefulness > 0.7 → boost bedtime_routine
wake = self.wakefulness.wakefulness
if wake > 0.7:
    chain_scores["bedtime_routine"] = chain_scores.get("bedtime_routine", 0.1) + wake * 0.5
    chain_scores["full_grooming"]   = chain_scores.get("full_grooming", 0.1)  + wake * 0.2
```

---

## Задача 5 — Заменить _build_candidate_chains() на контур базальных ганглиев

**Удалить:** текущую реализацию `_build_candidate_chains()`  
**Добавить:** `BasalGangliaGate` + `ActionChannel` per chain

### Инициализация

```python
from basal_ganglia import BasalGangliaGate, ActionChannel, BasalGangliaLearning, NO_ACTION

# В __init__():
# Один ActionChannel на каждую поведенческую цепочку
self.bg_channels: Dict[str, ActionChannel] = {
    chain_name: ActionChannel(action_id=chain_name)
    for chain_name in BEHAVIORAL_CHAINS
}
self.bg_gate = BasalGangliaGate(
    temperature=0.8,
    threshold=0.0,
    go_gain_alpha=0.9,
    habit_gain_beta=0.6,
    cortisol_gain_gamma=1.2,
    aversion_gain_delta=0.8,
)
self.bg_learning = BasalGangliaLearning(learning_rate=0.05)
```

### Новый _build_candidate_chains()

```python
def _build_candidate_chains(self, drive_suggestions: Dict[str, float]) -> List[str]:
    """BG Go/NoGo competition over chain channels."""

    DRIVE_TO_CHAINS = {
        "energy_need":  ["eating_and_grooming", "morning_awakening", "bedtime_routine"],
        "exploration":  ["exploration", "territorial_patrol", "nesting"],
        "social_drive": ["social_contact"],
        "curiosity":    ["activity_burst", "hyperactivity", "exploration"],
        "goal_tension": ["territorial_patrol", "nesting", "full_grooming"],
    }

    # Построить pressure_vector из drive_suggestions → chains
    pressure_vector: Dict[str, float] = {}
    for drive, chains in DRIVE_TO_CHAINS.items():
        drive_val = drive_suggestions.get(drive, 0.0)
        for chain in chains:
            pressure_vector[chain] = pressure_vector.get(chain, 0.0) + drive_val * 0.5

    # Базовый pressure для всех цепочек чтобы они не выпадали из конкуренции
    for chain in BEHAVIORAL_CHAINS:
        pressure_vector.setdefault(chain, 0.05)

    # Habit strengths из ActionChannels
    habit_strengths = {
        chain: ch.habit_strength
        for chain, ch in self.bg_channels.items()
    }

    # BG processing
    gated_scores = self.bg_gate.process(
        pressure_vector=pressure_vector,
        dopamine_level=self.neuromod.dopamine,
        cortisol_level=self.neuromod.cortisol,
        norepinephrine_level=self.neuromod.norepinephrine,
        habit_strengths=habit_strengths,
        aversive_signal=self.affect_space.legacy_axes_snapshot().get("stress", 0.0),
        exploration_bias=self.neuromod.get_exploration_level(),
    )

    # ThalamicGate stochastic selection
    selected = self.bg_gate.thalamic_gate.select(
        gated_scores=gated_scores,
        norepinephrine_level=self.neuromod.norepinephrine,
        exploration_bias=self.neuromod.get_exploration_level(),
    )

    if selected == NO_ACTION:
        return []

    # Топ-3 из gated_scores как fallback список
    sorted_chains = sorted(gated_scores.items(), key=lambda x: x[1], reverse=True)
    candidates = [selected] + [c for c, _ in sorted_chains if c != selected][:2]
    return candidates
```

### Запись исходов для BG learning (Sleep Task 7)

```python
# В sim_step() после завершения цепочки:
if prev_chain and prev_chain != self.chain_executor.current_chain:
    reward = self._calculate_chain_reward(prev_chain)
    if prev_chain in self.bg_channels:
        self.bg_channels[prev_chain].record_outcome(reward)
```

---

## Задача 6 — Добавить EmotionalRegulationLayer

**Файл:** `main.py`

### Инициализация

```python
from emotional_regulation import EmotionalRegulationLayer

# В __init__():
self.cer = EmotionalRegulationLayer()
```

### Вызов в sim_step() — авторегуляция аффекта

```python
# Обновить CER после обновления AffectiveSpace
axes = self.affect_space.legacy_axes_snapshot()
cer_result = self.cer.update(
    reward=last_chain_reward,                    # reward от последней цепочки
    prediction_error=abs(last_chain_reward),     # неожиданность исхода
    novelty=self.neuromod.get_exploration_level(),
    resolution=1.0 if chain_just_finished else 0.0,
)

# CER emits modulation factors — применить к BG в следующем цикле
# cer_result.exploration_bias → BasalGangliaGate exploration_bias
# cer_result.decision_threshold_shift → BasalGangliaGate decision_threshold_shift
# cer_result.habit_gain_scale → BasalGangliaGate habit_gain_scale

# Прямое применение: снижение стресса через авторегуляцию
if axes.get("stress", 0) > 0.6:
    # CER применяет переоценку — импульс антистресс
    reg_impulse = EmotionalImpulse(
        source="cer_regulation",
        payload={"stress": -cer_result.valence * 0.15, "stability": 0.05},
        intensity=0.3,
    )
    self.affect_space.update(dt=0.0, impulses=[reg_impulse])
```

---

## Задача 7 — Заменить memory.consolidate_memory() на SleepManager

**Удалить:** `memory_system.py` (или оставить только `save_memory()`/`load_memory()` для persistence)  
**Добавить:** `SleepManager` + `CortexMemory` + `NOWAHippocampus`

### Инициализация

```python
from sleep import SleepManager, CortexMemory
from hippocampus import NOWAHippocampus

# В __init__():
self.hippocampus = NOWAHippocampus(capacity=500)
self.cortex = CortexMemory()
self.sleep_manager = SleepManager(
    hippocampus=self.hippocampus,
    cortex=self.cortex,
    clustering_similarity_threshold=0.7,
    forget_stability_threshold=0.15,
)
self._sleep_consolidation_pending = False
```

### Запись эпизодов в hippocampus во время цепочек

```python
# В sim_step() после завершения цепочки:
from experience import Event, Path, EventType

if chain_just_finished and last_chain_name:
    # Создать Path из цепочки для гиппокампа
    chain_reward = self._calculate_chain_reward(last_chain_name)
    events = [
        Event(
            event_type=EventType.ACTION,
            name=last_chain_name,
            features={last_chain_name, self._affect_label()},
        )
    ]
    path = Path(events=events)
    self.hippocampus.store(
        path=path,
        consequence=chain_reward,
        intensity=abs(chain_reward) + 0.1,
    )
```

### Консолидация ТОЛЬКО во время сна

```python
# В sim_step():
is_deep_sleep = (
    (self.current_action or {}).get("action_id") == "sleep_house" and
    self.wakefulness.wakefulness < 0.3
)

if is_deep_sleep and not self._sleep_consolidation_pending:
    self._sleep_consolidation_pending = True
    self._run_sleep_consolidation()

if not is_deep_sleep:
    self._sleep_consolidation_pending = False

def _run_sleep_consolidation(self) -> None:
    """NOWA: обучение происходит ТОЛЬКО во сне."""
    self.sleep_manager.consolidate(
        neuromodulators=self.neuromod,
        max_patterns=20,
    )
    # BG sleep learning
    memories: Dict[str, List] = {}
    for chain, channel in self.bg_channels.items():
        if channel.last_outcome is not None:
            memories[chain] = [(
                channel.last_outcome,
                self.neuromod.dopamine,
                self.neuromod.cortisol,
                self.neuromod.serotonin,
            )]
    self.bg_channels_list = list(self.bg_channels.values())
    updated = self.bg_learning.apply_sleep_learning(
        channels=self.bg_channels_list,
        memories=memories,
        neuromodulators=self.neuromod,
    )
    updated = self.bg_learning.consolidate_habits(updated, self.neuromod.serotonin)
    for ch in updated:
        self.bg_channels[ch.action_id] = ch
    self.logger.info(
        f"[NOWA] Sleep consolidation: "
        f"DA={self.neuromod.dopamine:.2f} "
        f"5HT={self.neuromod.serotonin:.2f} "
        f"CORT={self.neuromod.cortisol:.2f}"
    )
```

---

## Задача 8 — Добавить ConflictArbitrationLayer

**Файл:** `main.py`

### Инициализация

```python
from conflict_arbitration import ConflictArbitrationLayer

# В __init__():
self.conflict_arb = ConflictArbitrationLayer()
```

### Вызов перед выбором цепочки

```python
# В _try_start_chain(), перед вызовом _build_candidate_chains():
gated = self.bg_gate.last_gated  # из предыдущего вызова process()

if gated:
    scores = list(gated.values())
    # Энтропия = мера неопределённости выбора
    import math
    total = sum(scores) + 1e-9
    entropy = -sum((s/total) * math.log(s/total + 1e-9) for s in scores)
    # top-2 gap
    sorted_s = sorted(scores, reverse=True)
    top2_gap = (sorted_s[0] - sorted_s[1]) / (sorted_s[0] + 1e-9) if len(sorted_s) > 1 else 1.0

    arb_result = self.conflict_arb.update(
        candidate_scores=list(gated.values()),
        prediction_error=abs(self._last_chain_reward or 0.0),
        recent_failure_rate=self._recent_failure_rate(),
        wm_load=len(gated) / 14.0,   # нормализованная нагрузка (14 цепочек)
        task_complexity=len(gated) / 14.0,
        latency=self.chain_cooldown_s,
    )
    # arb_result.exploration_bias → передать в _build_candidate_chains
    # arb_result.decision_threshold_shift → передать в BG
```

---

## Задача 9 — Отладочная панель: визуализация слоёв NOWA

**Файл:** `pygame_engine.py`

Добавить метод `set_nowa_state()` и расширить debug overlay.

```python
def set_nowa_state(self, nowa_snapshot: dict) -> None:
    """Принимает полный снимок NOWA-состояния для HUD."""
    self._nowa_snapshot = nowa_snapshot

def _draw_nowa_hud(self) -> None:
    """Отрисовка NOWA-слоёв в debug-режиме."""
    if not self.show_debug or not hasattr(self, '_nowa_snapshot'):
        return
    s = self._nowa_snapshot
    x, y = 10, 60
    line_h = 14

    sections = [
        ("── NEUROMODULATORS ──", [
            f"DA  {s.get('dopamine',0):.2f}  | 5HT {s.get('serotonin',0):.2f}",
            f"NE  {s.get('norepinephrine',0):.2f}  | CORT {s.get('cortisol',0):.2f}",
            f"ACh {s.get('acetylcholine',0):.2f}",
        ]),
        ("── DRIVES ──", [
            f"energy_need  {s.get('energy_need',0):.2f}",
            f"curiosity    {s.get('curiosity',0):.2f}",
            f"exploration  {s.get('exploration',0):.2f}",
            f"social_drive {s.get('social_drive',0):.2f}",
            f"goal_tension {s.get('goal_tension',0):.2f}",
        ]),
        ("── AFFECT (8D) ──", [
            f"valence  {s.get('valence',0):+.2f}  arousal {s.get('arousal',0):.2f}",
            f"stress   {s.get('stress',0):.2f}   trust  {s.get('trust',0):.2f}",
            f"curiosity {s.get('curiosity_a',0):.2f}  stab {s.get('stability',0):.2f}",
        ]),
        ("── WAKEFULNESS ──", [
            f"wake  {s.get('wakefulness',0):.2f}  reliability {s.get('cognitive_reliability',0):.2f}",
        ]),
        ("── BG TOP-3 ──", [
            f"{i+1}. {chain:<22} {score:.3f}"
            for i, (chain, score) in enumerate(s.get('bg_top3', []))
        ]),
    ]

    for title, lines in sections:
        surf = self.font_dbg.render(title, True, (200, 180, 120))
        self.screen.blit(surf, (x, y)); y += line_h
        for line in lines:
            surf = self.font_dbg.render(line, True, (180, 200, 180))
            self.screen.blit(surf, (x + 6, y)); y += line_h
        y += 4
```

### Снимок NOWA в main.py

```python
# В sim_step(), после всех обновлений:
if self.pygame_engine and self.pygame_engine.show_debug:
    bg_top3 = sorted(
        self.bg_gate.last_gated.items(),
        key=lambda x: x[1], reverse=True
    )[:3]
    self.pygame_engine.set_nowa_state({
        # Neuromodulators
        "dopamine":        self.neuromod.dopamine,
        "serotonin":       self.neuromod.serotonin,
        "norepinephrine":  self.neuromod.norepinephrine,
        "cortisol":        self.neuromod.cortisol,
        "acetylcholine":   self.neuromod.acetylcholine,
        # Drives
        **self.drives.snapshot(),
        # Affect 8D
        **self.affect_space.legacy_axes_snapshot(),
        # Wakefulness
        "wakefulness":          self.wakefulness.wakefulness,
        "cognitive_reliability": self.wakefulness.get_cognitive_reliability(),
        # BG
        "bg_top3": bg_top3,
        # CER
        "cer_exploration": getattr(self.cer, 'exploration_bias', 0.0),
    })
```

---

## Задача 10 — Сохранение/загрузка NOWA-состояния

**Файл:** `main.py`

Заменить `memory_system.save_memory()` на полный снимок NOWA-состояния.

### save_nowa_state()

```python
def save_nowa_state(self) -> None:
    import json
    saves_dir = self.demo_dir / "saves"
    saves_dir.mkdir(exist_ok=True)

    state = {
        "neuromodulators": self.neuromod.to_dict(),
        "drives": self.drives.snapshot(),
        "wakefulness": self.wakefulness.get_statistics(),
        "bg_channels": {
            name: {
                "go_weight":      ch.go_weight,
                "nogo_weight":    ch.nogo_weight,
                "habit_strength": ch.habit_strength,
                "selection_count": ch.selection_count,
                "success_count":  ch.success_count,
            }
            for name, ch in self.bg_channels.items()
        },
        "cortex_patterns": len(self.cortex.patterns),
        "hippocampus_size": len(self.hippocampus._traces)
            if hasattr(self.hippocampus, '_traces') else 0,
        "total_sim_time": self.total_sim_time,
    }

    with open(saves_dir / "nowa_state.json", "w") as f:
        json.dump(state, f, indent=2)
    self.logger.info("[NOWA] State saved")
```

### load_nowa_state()

```python
def load_nowa_state(self) -> bool:
    import json
    path = self.demo_dir / "saves" / "nowa_state.json"
    if not path.exists():
        return False
    try:
        with open(path) as f:
            state = json.load(f)
        self.neuromod = NeuromodulatorState.from_dict(state["neuromodulators"])
        for name, vals in state.get("bg_channels", {}).items():
            if name in self.bg_channels:
                ch = self.bg_channels[name]
                ch.go_weight      = vals.get("go_weight", 0.5)
                ch.nogo_weight    = vals.get("nogo_weight", 0.5)
                ch.habit_strength = vals.get("habit_strength", 0.0)
                ch.selection_count = vals.get("selection_count", 0)
                ch.success_count  = vals.get("success_count", 0)
        self.logger.info("[NOWA] State loaded")
        return True
    except Exception as e:
        self.logger.error(f"[NOWA] Load failed: {e}")
        return False
```

### Вызовы

```python
# В __init__(), после инициализации всех компонентов:
self.load_nowa_state()

# В cleanup():
self.save_nowa_state()

# В sim_step(), периодически:
if self.total_sim_time - self._last_nowa_save >= 120.0:
    self.save_nowa_state()
    self._last_nowa_save = self.total_sim_time
```

---

## Порядок реализации

| # | Задача | Зависит от | Сложность |
|---|---|---|---|
| 3 | NeuromodulatorState | — | Низкая |
| 4 | WakefulnessState | — | Низкая |
| 2 | AffectiveSpace | 3 | Средняя |
| 1 | DriveSystem | 2 | Средняя |
| 5 | BasalGangliaGate | 1, 3, 4 | Средняя |
| 6 | EmotionalRegulationLayer | 2, 5 | Средняя |
| 8 | ConflictArbitrationLayer | 5 | Средняя |
| 7 | SleepManager | 4, 5 | Высокая |
| 9 | Debug HUD | 1–6 | Низкая |
| 10 | Save/Load | 1–7 | Низкая |

Задачи 3 и 4 первыми — они независимы и разблокируют всё остальное.
Задача 7 (Sleep) последней — самая сложная, требует работающего BG и Wakefulness.

