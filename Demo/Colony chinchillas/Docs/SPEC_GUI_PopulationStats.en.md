## Abstract

Russian version: [SPEC_GUI_PopulationStats.ru.md](SPEC_GUI_PopulationStats.ru.md)

Scientific account of the colony: [COLONY_SPEC.en.md](COLONY_SPEC.en.md).

This specification defines the integration of the passive observer `ColonyPopulationObserver` into `ColonyGUI`. Its subject is the transfer of population metrics into the render-state dictionary and the display of a statistics panel in the pygame demonstration loop.

The observer is created when the interface is initialised and is called after the simulation step, with ticks skipped so that a slice is not read on every tick. Statistics assembly places into the render state the estimates of extinction risk and social cohesion, demography, births and deaths, mean affective and social measures, genetic diversity, and short trends. If the observer is unavailable or the history is empty, default values are returned and the render loop is not interrupted.

In the chinchilla-colony installation, the specification connects population measurement to the surface on which the colony is observed. The interface does not compute agent behaviour and does not become a source of simulation state. The panel is a derived view of slices already collected, so observation remains one-way in the multi-agent NOWA system.

# Specification: integration of ColonyPopulationObserver into ColonyGUI

**Files:** changes in `colony_gui/colony_gui.py`, `colony_gui/app.py`  
**Version:** 1.0

---

## 1. Purpose

Connect `ColonyPopulationObserver` to `ColonyGUI` so that:
- population metrics are available through `get_render_state()`
- a statistics panel is shown in the pygame demonstration
- the observer records automatically on every `_sim_tick()`

---

## 2. Changes in ColonyGUI

### 2.1 Initialisation of the observer

```python
# colony_gui/colony_gui.py

from colony_population_observer import ColonyPopulationObserver

class ColonyGUI:
    def __init__(self, runner: Any) -> None:
        ...  # существующие поля без изменений

        # НОВОЕ: observer создаётся при инициализации GUI
        self.observer = ColonyPopulationObserver(
            runner,
            observe_every_n_ticks=5,  # не каждый тик — экономия CPU
        )
```

### 2.2 `_sim_tick` — call to the observer

```python
def _sim_tick(self, real_dt: float) -> None:
    """Advance simulation when not paused."""
    if self.paused:
        return
    self.runner.tick(float(real_dt) * float(self.speed))
    self.observer.observe_tick()   # НОВОЕ: пассивное наблюдение после тика
```

### 2.3 `get_render_state` — new `population_stats` section

```python
def get_render_state(self) -> dict[str, Any]:
    ...  # существующий код без изменений
    
    # НОВОЕ: добавить секцию population_stats в конец словаря
    return {
        ...  # все существующие ключи
        "population_stats": self._build_population_stats(),
    }
```

### 2.4 `_build_population_stats` — new private method

```python
def _build_population_stats(self) -> dict[str, Any]:
    """
    Собрать метрики популяции из observer.
    
    Никогда не вызывает исключений — все обращения в try/except.
    Если observer недоступен или история пустая — возвращает defaults.
    
    Возвращает словарь:
    {
        # Риски и сплочённость
        "extinction_risk":   float,   # [0.0, 1.0]
        "social_cohesion":   float,   # [0.0, 1.0]
        
        # Демография
        "agent_count":       int,
        "female_count":      int,
        "male_count":        int,
        "juvenile_count":    int,
        "pregnant_count":    int,
        "sleeping_count":    int,
        
        # События (с последнего снапшота)
        "births_since_last": int,
        "deaths_since_last": int,
        "total_births":      int,
        "total_deaths":      int,
        
        # Средний аффект
        "mean_stress":       float,
        "mean_valence":      float,
        "mean_energy":       float,
        
        # Социальность
        "mean_affinity":     float,
        "bonded_pairs":      int,
        "total_known_pairs": int,
        
        # Генетика
        "mean_genome_diversity": float,
        
        # Тренды (последние 20 снапшотов)
        "stress_trend":      list[float],
        "energy_trend":      list[float],
        "population_trend":  list[int],
        
        # Текстовая сводка
        "summary":           str,
        
        # Флаг наличия данных
        "has_data":          bool,
    }
    """
    defaults = {
        "extinction_risk": 0.0,
        "social_cohesion": 0.0,
        "agent_count": 0,
        "female_count": 0,
        "male_count": 0,
        "juvenile_count": 0,
        "pregnant_count": 0,
        "sleeping_count": 0,
        "births_since_last": 0,
        "deaths_since_last": 0,
        "total_births": 0,
        "total_deaths": 0,
        "mean_stress": 0.0,
        "mean_valence": 0.0,
        "mean_energy": 0.0,
        "mean_affinity": 0.0,
        "bonded_pairs": 0,
        "total_known_pairs": 0,
        "mean_genome_diversity": 0.0,
        "stress_trend": [],
        "energy_trend": [],
        "population_trend": [],
        "summary": "",
        "has_data": False,
    }
    
    try:
        latest = self.observer.get_latest()
        if latest is None:
            return defaults
        
        return {
            "extinction_risk":       self.observer.get_extinction_risk(),
            "social_cohesion":       self.observer.get_social_cohesion(),
            "agent_count":           latest.agent_count,
            "female_count":          latest.female_count,
            "male_count":            latest.male_count,
            "juvenile_count":        latest.juvenile_count,
            "pregnant_count":        latest.pregnant_count,
            "sleeping_count":        latest.sleeping_count,
            "births_since_last":     latest.births_since_last,
            "deaths_since_last":     latest.deaths_since_last,
            "total_births":          latest.total_births,
            "total_deaths":          latest.total_deaths,
            "mean_stress":           latest.mean_stress,
            "mean_valence":          latest.mean_valence,
            "mean_energy":           latest.mean_energy,
            "mean_affinity":         latest.mean_affinity,
            "bonded_pairs":          latest.bonded_pairs,
            "total_known_pairs":     latest.total_known_pairs,
            "mean_genome_diversity": latest.mean_genome_diversity,
            "stress_trend":          self.observer.get_trend("mean_stress", last_n=20),
            "energy_trend":          self.observer.get_trend("mean_energy", last_n=20),
            "population_trend":      self.observer.get_trend("agent_count", last_n=20),
            "summary":               self.observer.summary_text(),
            "has_data":              True,
        }
    except Exception:
        return defaults
```

---

## 3. Changes in `app.py` — drawing the statistics panel

In `run_pygame_demo()`, add drawing of `population_stats` over the existing HUD.

### 3.1 Panel position

```
┌────────────────────────────────────────────────────────────┐
│  COLONY — Chinchilla Simulation                            │
│  [клетка с агентами — существующий код]                    │
│                                                            │
│  ┌─ HUD (левый верхний угол — существующий) ─────────┐    │
│  │  time: 00:14:32  agents: 4  speed: x1.0            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  ┌─ STATS PANEL (правый нижний угол — НОВОЕ) ─────────┐   │
│  │  ● Популяция: 4 (2♀ 2♂)  юных: 1  беременных: 0   │   │
│  │  ● Стресс: ████░░░░░░ 0.38  Энергия: ██████░░░░ 0.6│   │
│  │  ● Связей: 6  bonded: 2  Сплочённость: 0.41        │   │
│  │  ● Рождений: 2  Смертей: 0  Риск: ░░░░░░░░░░ 0.12 │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Panel parameters

```python
STATS_PANEL_RECT = pygame.Rect(
    gui.WIDTH - 340,   # x: правый край
    gui.HEIGHT - 130,  # y: нижний край
    330,               # width
    120,               # height
)
STATS_PANEL_BG_COLOR    = (245, 239, 229, 200)  # полупрозрачный
STATS_PANEL_BORDER_COLOR = (160, 148, 130)
STATS_TEXT_COLOR        = (35, 28, 20)
STATS_ACCENT_COLOR      = (140, 110, 72)

BAR_BG_COLOR   = (210, 198, 180)
BAR_FG_STRESS  = (220, 100, 80)
BAR_FG_ENERGY  = (80, 160, 220)
BAR_FG_RISK    = (200, 80, 80)
BAR_FG_COHESION = (100, 180, 120)
BAR_HEIGHT = 7
BAR_WIDTH  = 90
```

### 3.3 Panel drawing function

```python
def _draw_stats_panel(
    screen: pygame.Surface,
    font_small: pygame.font.Font,
    population_stats: dict[str, Any],
) -> None:
    """
    Нарисовать панель статистики популяции.
    
    Вызывается ПОСЛЕ отрисовки агентов, ПЕРЕД pygame.display.flip().
    Если population_stats["has_data"] == False — не рисовать ничего.
    
    Аргументы:
        screen: основная поверхность
        font_small: шрифт размер 12-13px
        population_stats: словарь из get_render_state()["population_stats"]
    
    Ограничения:
        - весь код в try/except — ошибка отрисовки не ломает главный цикл
        - не мутирует population_stats
        - не обращается к runner или observer напрямую
    """
```

### 3.4 Panel contents — lines

The panel displays 4 lines:

**Line 1 — Demography:**
```
Популяция: {agent_count} ({female_count}♀ {male_count}♂)
  юных: {juvenile_count}  беременных: {pregnant_count}
```

**Line 2 — Affect (with mini-bars):**
```
Стресс: [бар] {mean_stress:.2f}   Энергия: [бар] {mean_energy:.2f}
```

**Line 3 — Sociality:**
```
Связей: {total_known_pairs}  bonded: {bonded_pairs}
  Сплочённость: [бар] {social_cohesion:.2f}
```

**Line 4 — Dynamics:**
```
Рождений: {total_births}  Смертей: {total_deaths}
  Риск вымирания: [бар] {extinction_risk:.2f}
```

### 3.5 Colour of the `extinction_risk` bar

The `extinction_risk` bar changes colour according to its value:
```python
def _risk_bar_color(risk: float) -> tuple[int, int, int]:
    if risk < 0.3:
        return (100, 180, 120)   # зелёный — безопасно
    if risk < 0.6:
        return (220, 180, 80)    # жёлтый — внимание
    return (200, 80, 80)         # красный — опасность
```

---

## 4. Update of `load()` in ColonyGUI

When state is loaded, the observer must be recreated with the new runner:

```python
def load(self, path: str | Path) -> None:
    source = Path(path)
    storage = ColonyStorage(save_dir=source.parent)
    self.runner = storage.load_colony(source)
    self._snapshot = None
    # НОВОЕ: пересоздать observer для нового runner
    self.observer = ColonyPopulationObserver(
        self.runner,
        observe_every_n_ticks=5,
    )
```

---

## 5. Implementation constraints

1. `observer.observe_tick()` is called only from `_sim_tick()`, not from `_update_snapshot()`
2. `_build_population_stats()` only reads from the observer; it does not call `observe()`
3. `_draw_stats_panel()` does not access the runner or the observer directly, only the dictionary
4. If `has_data == False`, the panel is not drawn at all (not an empty rectangle)
5. `observe_every_n_ticks=5` is a fixed value in the GUI and is not configured by the user
6. The statistics panel is drawn over the cage; a translucent background is required via `pygame.SRCALPHA`
7. Python 3.10+

---

## 6. Test cases

### TC-01: `get_render_state` contains `population_stats`

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
gui = ColonyGUI(runner)
gui._sim_tick(0.5)
gui._update_snapshot()

state = gui.get_render_state()

assert "population_stats" in state
stats = state["population_stats"]
assert isinstance(stats, dict)
assert "extinction_risk" in stats
assert "social_cohesion" in stats
assert "has_data" in stats
```

### TC-02: `has_data` is False before the first tick

```python
runner = SimulationRunner()
gui = ColonyGUI(runner)
# НЕ вызываем _sim_tick — observer пустой

gui._update_snapshot()
state = gui.get_render_state()

stats = state["population_stats"]
assert stats["has_data"] is False
assert stats["extinction_risk"] == 0.0
```

### TC-03: `has_data` is True after a tick

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
gui = ColonyGUI(runner)
gui._sim_tick(0.1)

state = gui.get_render_state()
stats = state["population_stats"]

assert stats["has_data"] is True
assert stats["agent_count"] == 1
```

### TC-04: `_sim_tick` calls the observer

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="M"))
gui = ColonyGUI(runner)

assert len(gui.observer.history) == 0

for _ in range(10):
    gui._sim_tick(0.1)

# observe_every_n_ticks=5, 10 тиков → 2 снапшота
assert len(gui.observer.history) == 2
```

### TC-05: `population_stats` does not mutate the runner

```python
runner = SimulationRunner()
for _ in range(3):
    runner.add_agent(ChinchillaAgent(sex="F"))

gui = ColonyGUI(runner)
gui._sim_tick(0.5)
gui._update_snapshot()

original_count = len(runner.agents)
original_time = runner.sim_time

state = gui.get_render_state()
_ = state["population_stats"]

assert len(runner.agents) == original_count
assert runner.sim_time == original_time
```

### TC-06: `extinction_risk` is in [0, 1]

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))  # один агент — высокий риск
gui = ColonyGUI(runner)
gui._sim_tick(0.1)

state = gui.get_render_state()
risk = state["population_stats"]["extinction_risk"]

assert 0.0 <= risk <= 1.0
assert risk > 0.3  # low_population фактор активен
```

### TC-07: `social_cohesion` is in [0, 1]

```python
runner = SimulationRunner()
a = ChinchillaAgent(sex="F")
b = ChinchillaAgent(sex="M")
runner.add_agent(a)
runner.add_agent(b)

gui = ColonyGUI(runner)
gui._sim_tick(0.1)

state = gui.get_render_state()
cohesion = state["population_stats"]["social_cohesion"]

assert 0.0 <= cohesion <= 1.0
```

### TC-08: `stress_trend` and `population_trend` are lists

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
gui = ColonyGUI(runner)

for _ in range(20):
    gui._sim_tick(0.1)

state = gui.get_render_state()
stats = state["population_stats"]

assert isinstance(stats["stress_trend"], list)
assert isinstance(stats["population_trend"], list)
# Все элементы числовые
for v in stats["stress_trend"]:
    assert isinstance(v, float)
```

### TC-09: `summary` is non-empty when agents are present

```python
runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
runner.add_agent(ChinchillaAgent(sex="M"))
gui = ColonyGUI(runner)
gui._sim_tick(0.5)

state = gui.get_render_state()
summary = state["population_stats"]["summary"]

assert isinstance(summary, str)
assert len(summary) > 5
assert "2" in summary  # agent_count
```

### TC-10: `load` recreates the observer

```python
import tempfile, os

runner = SimulationRunner()
runner.add_agent(ChinchillaAgent(sex="F"))
gui = ColonyGUI(runner)
gui._sim_tick(1.0)

original_observer_id = id(gui.observer)

storage = ColonyStorage()
with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    path = f.name
try:
    storage.save_colony(runner, path)
    gui.load(path)

    assert id(gui.observer) != original_observer_id
    assert gui.observer.runner is gui.runner
finally:
    os.unlink(path)
```

### TC-11: `_build_population_stats` does not fail when the observer is empty

```python
runner = SimulationRunner()
gui = ColonyGUI(runner)

# Намеренно сломать observer
gui.observer = None

state = gui.get_render_state()
stats = state["population_stats"]

assert stats["has_data"] is False
assert stats["extinction_risk"] == 0.0
```

### TC-12: `population_stats` contains every expected key

```python
EXPECTED_KEYS = {
    "extinction_risk", "social_cohesion",
    "agent_count", "female_count", "male_count",
    "juvenile_count", "pregnant_count", "sleeping_count",
    "births_since_last", "deaths_since_last",
    "total_births", "total_deaths",
    "mean_stress", "mean_valence", "mean_energy",
    "mean_affinity", "bonded_pairs", "total_known_pairs",
    "mean_genome_diversity",
    "stress_trend", "energy_trend", "population_trend",
    "summary", "has_data",
}

runner = SimulationRunner()
gui = ColonyGUI(runner)
state = gui.get_render_state()

missing = EXPECTED_KEYS - set(state["population_stats"].keys())
assert not missing, f"Отсутствующие ключи: {missing}"
```

---

## 7. Notes for the implementing agent

- Importing `ColonyPopulationObserver` at the top of `colony_gui.py` by a relative path will not work: the module is in `src/`, not in `colony_gui/`. Use an absolute import, adding the path through `sys.path` or through the package `__init__.py`
- `STATS_PANEL_BG_COLOR` with an alpha channel requires `pygame.Surface((w, h), pygame.SRCALPHA)` followed by `screen.blit()`
- `population_trend`: the field `agent_count` is an `int`, and `get_trend()` returns `list[float]`. There is no need to cast back to `int` for display; a float is suitable for a graph
- `_draw_stats_panel()` should be a separate function in `app.py`, not inlined in the main loop
- Font for the panel: `pygame.font.SysFont("Arial", 12)`, separate from the main `font` (16px)
- Draw bars with two `pygame.draw.rect()` calls: the background (`BAR_BG_COLOR`) and the filled part (`value * BAR_WIDTH`)
- Call `_risk_bar_color()` every frame; do not cache it (the value changes)
