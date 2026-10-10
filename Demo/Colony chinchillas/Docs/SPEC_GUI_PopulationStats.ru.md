## Аннотация

English version: [SPEC_GUI_PopulationStats.en.md](SPEC_GUI_PopulationStats.en.md)

Научное описание колонии: [COLONY_SPEC.ru.md](COLONY_SPEC.ru.md).

Спецификация определяет включение пассивного наблюдателя `ColonyPopulationObserver` в `ColonyGUI`. Предмет документа — передача популяционных метрик в словарь состояния отрисовки и вывод панели статистики в демонстрационном цикле pygame.

Наблюдатель создаётся при инициализации интерфейса и вызывается после шага симуляции с прореживанием по тикам, чтобы чтение среза не выполнялось на каждом такте. Сборка статистики переносит в состояние отрисовки оценки риска вымирания и социальной сплочённости, демографию, рождения и смерти, средние аффективные и социальные показатели, генетическое разнообразие и короткие тренды. При недоступности наблюдателя или пустой истории возвращаются значения по умолчанию, и цикл отрисовки не прерывается.

В установке колонии шиншилл спецификация связывает измерительный контур популяции с поверхностью наблюдения. Интерфейс не вычисляет поведение агентов и не становится источником состояния симуляции. Панель является производным представлением уже собранных срезов и тем самым сохраняет односторонность наблюдения в многоагентной системе NOWA.

# Спецификация: интеграция ColonyPopulationObserver в ColonyGUI

**Файлы:** изменения в `colony_gui/colony_gui.py`, `colony_gui/app.py`  
**Версия:** 1.0

---

## 1. Назначение

Подключить `ColonyPopulationObserver` к `ColonyGUI` так чтобы:
- метрики популяции были доступны через `get_render_state()`
- в pygame демо отображалась панель статистики
- observer автоматически наблюдал при каждом `_sim_tick()`

---

## 2. Изменения в ColonyGUI

### 2.1 Инициализация observer

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

### 2.2 _sim_tick — вызов observer

```python
def _sim_tick(self, real_dt: float) -> None:
    """Advance simulation when not paused."""
    if self.paused:
        return
    self.runner.tick(float(real_dt) * float(self.speed))
    self.observer.observe_tick()   # НОВОЕ: пассивное наблюдение после тика
```

### 2.3 get_render_state — новая секция population_stats

```python
def get_render_state(self) -> dict[str, Any]:
    ...  # существующий код без изменений
    
    # НОВОЕ: добавить секцию population_stats в конец словаря
    return {
        ...  # все существующие ключи
        "population_stats": self._build_population_stats(),
    }
```

### 2.4 _build_population_stats — новый приватный метод

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

## 3. Изменения в app.py — отрисовка панели статистики

В `run_pygame_demo()` добавить отрисовку `population_stats` поверх существующего HUD.

### 3.1 Позиция панели

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

### 3.2 Параметры панели

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

### 3.3 Функция отрисовки панели

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

### 3.4 Содержимое панели — строки

Панель отображает 4 строки:

**Строка 1 — Демография:**
```
Популяция: {agent_count} ({female_count}♀ {male_count}♂)
  юных: {juvenile_count}  беременных: {pregnant_count}
```

**Строка 2 — Аффект (с mini-барами):**
```
Стресс: [бар] {mean_stress:.2f}   Энергия: [бар] {mean_energy:.2f}
```

**Строка 3 — Социальность:**
```
Связей: {total_known_pairs}  bonded: {bonded_pairs}
  Сплочённость: [бар] {social_cohesion:.2f}
```

**Строка 4 — Динамика:**
```
Рождений: {total_births}  Смертей: {total_deaths}
  Риск вымирания: [бар] {extinction_risk:.2f}
```

### 3.5 Цвет бара extinction_risk

Бар `extinction_risk` меняет цвет в зависимости от значения:
```python
def _risk_bar_color(risk: float) -> tuple[int, int, int]:
    if risk < 0.3:
        return (100, 180, 120)   # зелёный — безопасно
    if risk < 0.6:
        return (220, 180, 80)    # жёлтый — внимание
    return (200, 80, 80)         # красный — опасность
```

---

## 4. Обновление load() в ColonyGUI

При загрузке состояния observer нужно пересоздать с новым runner:

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

## 5. Ограничения реализации

1. `observer.observe_tick()` вызывается только из `_sim_tick()` — не из `_update_snapshot()`
2. `_build_population_stats()` — только чтение из observer, никаких вызовов `observe()`
3. `_draw_stats_panel()` — не обращается к runner или observer напрямую, только к словарю
4. Если `has_data == False` — панель не отрисовывается совсем (не пустой прямоугольник)
5. `observe_every_n_ticks=5` — фиксированное значение в GUI, не конфигурируется пользователем
6. Панель статистики рисуется поверх клетки — нужен полупрозрачный фон через `pygame.SRCALPHA`
7. Python 3.10+

---

## 6. Тест-кейсы

### TC-01: get_render_state содержит population_stats

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

### TC-02: has_data False до первого тика

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

### TC-03: has_data True после тика

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

### TC-04: _sim_tick вызывает observer

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

### TC-05: population_stats не мутирует runner

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

### TC-06: extinction_risk в [0, 1]

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

### TC-07: social_cohesion в [0, 1]

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

### TC-08: stress_trend и population_trend — списки

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

### TC-09: summary непустой при наличии агентов

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

### TC-10: load пересоздаёт observer

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

### TC-11: _build_population_stats не падает при пустом observer

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

### TC-12: population_stats содержит все ожидаемые ключи

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

## 7. Примечания для реализующего агента

- `import` ColonyPopulationObserver в начало `colony_gui.py` через относительный путь не получится — модуль в `src/`, а не в `colony_gui/`. Использовать абсолютный импорт с добавлением пути через `sys.path` или через `__init__.py` пакета
- `STATS_PANEL_BG_COLOR` с альфа-каналом требует `pygame.Surface((w, h), pygame.SRCALPHA)` с последующим `screen.blit()`
- `population_trend` — поле `agent_count` является `int`, `get_trend()` возвращает `list[float]`. При отображении кастовать обратно в `int` не нужно — для графика float подходит
- `_draw_stats_panel()` рекомендуется вынести в отдельную функцию в `app.py`, не встраивать инлайн в главный цикл
- Шрифт для панели: `pygame.font.SysFont("Arial", 12)` — отдельный от основного `font` (16px)
- Бары рисовать через два `pygame.draw.rect()`: фон (`BAR_BG_COLOR`) и заполненная часть (`value * BAR_WIDTH`)
- `_risk_bar_color()` вызывать каждый кадр — не кэшировать (значение меняется)
