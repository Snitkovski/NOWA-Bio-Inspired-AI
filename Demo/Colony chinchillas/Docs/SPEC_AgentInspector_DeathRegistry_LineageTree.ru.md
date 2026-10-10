## Аннотация

English version: [SPEC_AgentInspector_DeathRegistry_LineageTree.en.md](SPEC_AgentInspector_DeathRegistry_LineageTree.en.md)

Научное описание колонии: [COLONY_SPEC.ru.md](COLONY_SPEC.ru.md).

Настоящая спецификация версии 1.0 определяет три компонента графического контура колонии: реестр умерших `DeathRegistry`, оверлей инспектора агента и оверлей родословного дерева. Реестр ведётся в памяти сеанса и хранит мемориалы умерших вместе со сведениями о рождениях, необходимыми для построения графа родства живых и умерших особей.

Структура `AgentMemorial` фиксирует на момент смерти идентичность, сроки жизни, причину смерти, потомство, финальные аффект и нейромодуляторы, показатели состояния NOWA и геном. Инспектор открывается с карточки агента и распределяет наблюдение по вкладкам когнитивного состояния, социальности, репродукции, генома и истории. Оверлей родословной изображает живых и умерших в одном графе и вызывается отдельно от инспектора.

Роль документа в установке состоит в том, чтобы сохранить особей, исчезающих из текущего среза, как единицы родства и жизненного итога. Регистрация рождения и смерти отделена от политики действия: графический слой снимает публичное состояние и не изменяет агента. Тем самым задаётся контракт чтения для последующего сопоставления линий в многоагентной симуляции NOWA.

# Спецификация: Agent Inspector + Death Registry + Lineage Tree

**Файлы:**
- `colony_gui/agent_inspector.py` — новый
- `colony_gui/death_registry.py` — новый  
- `colony_gui/lineage_overlay.py` — новый
- изменения в `colony_gui/colony_gui.py`
- изменения в `colony_gui/app.py`
- изменения в `simulation_runner.py`

**Версия:** 1.0

---

## 1. Общая архитектура трёх компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│  Основной экран (существующий)                                  │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐ │
│  │  Клетка          │  │  Правая панель (карточки агентов)    │ │
│  │                  │  │  [● G0A1 ♀ adult calm]  ← клик →   │ │
│  │  [спрайты]       │  │  [● G0A2 ♂ adult excit] ← клик →   │ │
│  │                  │  │  [○ G1A1 ♀ juv  calm]  ← клик →   │ │
│  └──────────────────┘  └──────────────────────────────────────┘ │
│  ┌────────────────────── stats panel ──────────────────────────┐ │
└──┴─────────────────────────────────────────────────────────────┘─┘
         ↓ клик на карточку              ↓ клавиша L (Lineage)
┌─────────────────────────┐   ┌──────────────────────────────────┐
│  AgentInspector overlay │   │  LineageTree overlay             │
│  (поверх основного)     │   │  (поверх основного)              │
│  Вкладки:               │   │  Граф родословной                │
│  [NOWA][Социум][Репро]  │   │  Живые: круги                   │
│  [Геном][История]       │   │  Умершие: серые кресты           │
└─────────────────────────┘   └──────────────────────────────────┘
```

---

## 2. DeathRegistry — реестр умерших агентов

### 2.1 AgentMemorial — полный снапшот агента на момент смерти

```python
@dataclass(frozen=True)
class AgentMemorial:
    # Идентичность
    agent_id: str
    name: str
    sex: str
    generation: int
    parents: tuple[str | None, str | None]

    # Жизнь
    birth_sim_time: float        # sim_time при создании (age=0)
    death_sim_time: float        # sim_time на момент смерти
    age_at_death: float          # agent.age в sim-секундах
    lived_steps: int             # agent.lived_steps
    cause_of_death: str          # из mortality_system.cause_of_death

    # Потомки
    own_offspring: list[str]     # agent_id детёнышей
    total_offspring: int         # из reproductive_system.total_offspring

    # Финальный аффект (на момент смерти)
    final_stress: float
    final_valence: float
    final_arousal: float
    final_energy: float
    final_social_drive: float

    # Финальные нейромодуляторы
    final_dopamine: float
    final_serotonin: float
    final_norepinephrine: float
    final_cortisol: float

    # Финальный NOWA
    final_wakefulness: float
    final_vitality: float
    final_lived_steps: int
    final_hippocampus_size: int
    final_cortex_patterns: int

    # Финальный геном (ключевые гены)
    genome_genes: dict[str, float]   # полный dict из genome.genes

    # Социальный след
    known_agents_count: int      # len(knowledge) на момент смерти
    bonded_count: int            # сколько bonded связей
    interactions_total: int      # суммарно эпизодов во всех KnownAgent

    # Поколение
    generation_index: int        # порядковый номер в своём поколении (G0A1 → 1)
```

### 2.2 DeathRegistry

```python
class DeathRegistry:
    """
    In-memory registry of all agents that ever lived in this session.
    
    Хранит как умерших (AgentMemorial), так и сводку живых агентов
    для построения родословного дерева.
    """
    
    def __init__(self) -> None:
        self._memorials: dict[str, AgentMemorial] = {}  # agent_id → memorial
        self._birth_times: dict[str, float] = {}        # agent_id → sim_time рождения
    
    def register_birth(self, agent: Any, sim_time: float) -> None:
        """
        Зарегистрировать рождение агента.
        Вызывается при add_agent() в SimulationRunner.
        Сохраняет sim_time рождения для вычисления возраста при смерти.
        Не мутирует агента.
        """
    
    def register_death(
        self,
        agent: Any,
        sim_time: float,
        generation_index_map: dict[str, int],
    ) -> AgentMemorial:
        """
        Создать AgentMemorial из текущего состояния агента.
        Вызывается из _handle_agent_death() ДО удаления агента из runner.
        
        Читает все атрибуты через getattr с fallback.
        Никогда не вызывает исключений.
        
        Возвращает: созданный AgentMemorial.
        """
    
    def get_memorial(self, agent_id: str) -> AgentMemorial | None:
        """Получить memorial умершего агента."""
    
    def get_all_memorials(self) -> list[AgentMemorial]:
        """Все умершие, отсортированные по death_sim_time ASC."""
    
    def get_birth_time(self, agent_id: str) -> float:
        """sim_time рождения агента (0.0 если неизвестен)."""
    
    def is_deceased(self, agent_id: str) -> bool:
        """Умер ли агент в этой сессии."""
    
    def total_ever_lived(self) -> int:
        """Сколько агентов всего жило (живые + умершие)."""
    
    def get_children(self, agent_id: str) -> list[str]:
        """agent_id всех известных детей (из own_offspring мемориалов)."""
    
    def get_lineage_nodes(
        self,
        living_agents: list[Any],
    ) -> list["LineageNode"]:
        """
        Построить список LineageNode для всех агентов когда-либо живших.
        
        Объединяет:
        - умерших из _memorials
        - живых из living_agents
        
        Возвращает список для LineageTree.
        """
```

---

## 3. LineageNode и LineageTree

### 3.1 LineageNode

```python
@dataclass(frozen=True)
class LineageNode:
    agent_id: str
    display_name: str           # G0A1, G1A3 и т.д.
    sex: str
    generation: int
    parents: tuple[str | None, str | None]
    own_offspring: list[str]
    is_alive: bool
    cause_of_death: str         # "" если живой
    age: float                  # текущий возраст (живые) или age_at_death
    total_offspring: int
    generation_index: int
    
    # Для позиционирования в дереве
    tree_x: float = 0.0
    tree_y: float = 0.0
```

### 3.2 Алгоритм позиционирования дерева

```
Поколение 0 (основатели) — верхний ряд
Поколение 1 — следующий ряд ниже
...

Внутри поколения — агенты расположены по горизонтали
слева направо в порядке рождения (birth_sim_time ASC).

tree_y = generation * GENERATION_ROW_HEIGHT
tree_x = index_within_generation * NODE_SPACING_X + centering_offset

Линии родства: от центра узла родителя к центру узла ребёнка.
Если оба родителя известны — линия от точки между ними.
```

Константы позиционирования:
```python
GENERATION_ROW_HEIGHT = 110   # пикселей между поколениями
NODE_SPACING_X = 90           # пикселей между агентами одного поколения
NODE_RADIUS_ALIVE = 28        # радиус круга живого агента
NODE_RADIUS_DEAD = 22         # радиус круга умершего агента
```

---

## 4. AgentInspector — инспектор живого агента

### 4.1 Структура панели (overlay 480×600px)

```
┌────────────────────────────────────────────────────┐
│  G1A2  ♂  adult  поколение 1    [родители: G0A1×G0A2] [✕]│
├──────────┬──────────┬──────────┬──────────┬────────┤
│  NOWA    │  Социум  │  Репро   │  Геном   │История │
├──────────┴──────────┴──────────┴──────────┴────────┤
│  [содержимое активной вкладки]                     │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 4.2 Вкладка NOWA

Показывает полное когнитивное состояние:

```
АФФЕКТ                          НЕЙРОМОДУЛЯТОРЫ
stress    ████░░░░░░  0.38      dopamine     ██████░░░░  0.61
valence   ████████░░  0.72      serotonin    ████░░░░░░  0.42
arousal   ██████░░░░  0.57      norepinephrine ████░░░░ 0.39
attachment██████░░░░  0.55      cortisol     ██░░░░░░░░  0.18
curiosity ███████░░░  0.68      acetylcholine ████░░░░  0.44
trust     ████████░░  0.73      dopamine_tonic  ░░░░░░  0.12
dominance ████░░░░░░  0.40

БОДРСТВОВАНИЕ                   АВТОНОМНЫЕ ДРАЙВЫ
wakefulness  ████████░░  0.76   curiosity    0.62
sleep_pressure ████░░░░  0.41   social_drive 0.45
circadian    ████████░░  0.74   exploration  0.58
alertness    ████░░░░░░  0.38   energy       0.71

ПАМЯТЬ (NOWA)
lived_steps:        1247
hippocampus:        43 эпизодов
cortex_patterns:    12 паттернов
td_error (mean):    0.14
```

### 4.3 Вкладка Социум

```
Знает агентов: 3

♥ G0A1  мать     affinity: 0.90  familiarity: 0.95  trust: 0.88
  Последнее: allogroom 00:14:23 → accepted
  Взаимодействий: 24 (позитивных: 22, негативных: 2)

★ G0A2  отец     affinity: 0.72  familiarity: 0.80  trust: 0.75
  Последнее: sniff_greet 00:08:11 → accepted
  Взаимодействий: 8

? G1A1  незнакомец→знакомый  affinity: 0.31  familiarity: 0.45
  Последнее: play_invite 00:12:00 → accepted
  Взаимодействий: 3

Слухи: 2 записи
  - G0A2 (источник: G0A1): seen_at_wheel|affect_calm
  - G1A1 (источник: G0A1): seen_at_floor|affect_excited
```

### 4.4 Вкладка Репро

```
Пол: ♂ (самец)
Половозрелость: да
Возраст: 00:22:47 (из 1h 23m максимум)

REPRODUCTIVE DRIVE
drive:      ████████░░  0.78  ← порог 0.70 ПРЕВЫШЕН
cooldown:   0 шагов
потомков:   2 (G2A1, G2A3)

MORTALITY
vitality:   ████████░░  0.82
senescence: 0.00  (старение не началось)
Причина смерти: — (жив)
```

*(для самок дополнительно: heat_cycle фаза, value, urgency, is_pregnant)*

### 4.5 Вкладка Геном

```
ГРУППА NM (нейромодуляторы)
nm_da_ne_weight:    0.24  ██░░░░░░
nm_ne_da_weight:    0.18  █░░░░░░░
nm_da_ach_weight:  -0.28  ░░░██░░░  (отриц.)
nm_acc_k_ne:        0.45  ████░░░░

ГРУППА AF (аффект)
af_decay_valence:   0.92  █████████░
af_decay_stress:    0.75  ███████░░░
af_lambda_reg:      0.03  ░░░░░░░░░░

ГРУППА WK (бодрствование)
wk_circadian_amplitude: 0.25  ██░░░░░░
wk_accumulation_factor: 1.10  ██████░░░░

ГРУППА DR (драйвы)
dr_curiosity_baseline:     0.42  ████░░░░
dr_social_drive_baseline:  0.51  █████░░░
dr_perception_radius_factor: 1.3  █████████░░
lt_max_lifespan_factor:    1.15  ████████░░░░

[... остальные группы LR, IM ...]

Поколение генома: 1
Lineage ID: gen0_agent_0
```

### 4.6 Вкладка История

```
Взаимодействий всего: 35

Последние 10:
  00:22:10  allogroom     с G0A1 → accepted   Δvalence +0.05
  00:21:45  play_invite   с G1A1 → accepted   Δvalence +0.03
  00:20:30  sniff_greet   с G1A1 → accepted   Δvalence +0.02
  00:19:15  allogroom     с G0A1 → accepted   Δvalence +0.05
  00:18:00  mount_display с G1A1 → rejected   Δvalence -0.05
  ...

Слухи полученных: 4
Слухов передано:  7
```

---

## 5. LineageOverlay — родословное дерево

### 5.1 Управление

```
L — открыть/закрыть LineageOverlay
ESC — закрыть
Колёсико мыши — зум [0.4x ... 2.0x]
ЛКМ + drag — панорамирование
Клик на узел — показать AgentInspector для этого агента
```

### 5.2 Визуальный язык узлов

```python
# Живой агент
ALIVE_FEMALE_COLOR  = (200, 150, 200)   # розово-фиолетовый
ALIVE_MALE_COLOR    = (150, 180, 220)   # голубой
ALIVE_BORDER_COLOR  = (80, 60, 40)
ALIVE_BORDER_WIDTH  = 3

# Умерший агент
DEAD_COLOR          = (160, 155, 150)   # серый
DEAD_BORDER_COLOR   = (100, 95, 90)
DEAD_BORDER_WIDTH   = 1
DEAD_CROSS_COLOR    = (120, 115, 110)   # маленький крест внутри

# Размеры
NODE_RADIUS_ALIVE = 28
NODE_RADIUS_DEAD  = 22
```

### 5.3 Линии родства

```python
# Линия от родителя к ребёнку
LINEAGE_LINE_COLOR       = (140, 130, 115)
LINEAGE_LINE_WIDTH       = 2

# Линия пары (мать←→отец) — горизонтальная
PAIR_LINE_COLOR          = (180, 160, 140)
PAIR_LINE_WIDTH          = 1
PAIR_LINE_STYLE          = "dashed"   # пунктир (pygame: чередование сегментов)
```

### 5.4 Содержимое узла

Внутри каждого узла — минимальная информация:
```
    G1A2
     ♂
   [иконка состояния]
```

Иконки состояния (emoji если доступно, иначе текст):
```python
NODE_ICONS = {
    "sleeping":   "💤",
    "eating":     "🌿",
    "pregnant":   "◎",
    "dead":       "†",
    "estrus":     "♡",
    "young":      "○",
}
```

### 5.5 Тултип при наведении

При наведении мыши на узел — маленький тултип рядом:
```
G1A2 ♂ adult
Возраст: 00:22:47
Потомков: 2
Стресс: 0.38
[жив / умер от exhaustion в 01:15:30]
```

### 5.6 Скроллинг и зум

```python
LINEAGE_ZOOM_MIN  = 0.3
LINEAGE_ZOOM_MAX  = 2.5
LINEAGE_ZOOM_STEP = 0.1

# Начальное положение: всё дерево центрировано
# Начальный зум: подобрать чтобы всё влезло по ширине
```

---

## 6. Правая панель с карточками агентов

Существующая правая панель расширяется — добавляется:

1. **Карточки живых агентов** (существующий код, с кликом)
2. **Разделитель "── умершие ──"** (если есть умершие)
3. **Карточки умерших** (серые, с причиной смерти)

```
┌─────────────────────────────────────┐
│ КОЛОНИЯ (3 живых)                   │
│ ┌──────────────────────────────┐    │
│ │● G0A1 ♀ adult calm          │ ←клик│
│ │  eat  stress:0.2 energy:0.8  │    │
│ └──────────────────────────────┘    │
│ ┌──────────────────────────────┐    │
│ │● G1A2 ♂ adult excited       │ ←клик│
│ │  run_wheel  stress:0.4       │    │
│ └──────────────────────────────┘    │
│                                     │
│ ── умершие (1) ──                   │
│ ┌──────────────────────────────┐    │
│ │✝ G0A2 ♂  exhaustion         │ ←клик│
│ │  прожил 01:15:30  потомков:2 │    │
│ └──────────────────────────────┘    │
│                                     │
│ [L] Родословная                     │
└─────────────────────────────────────┘
```

Карточки умерших кликабельны — открывают AgentInspector с данными из AgentMemorial (все вкладки кроме живых данных — показываются финальные значения).

---

## 7. Структура кода

```
colony_gui/
├── agent_inspector.py     # НОВЫЙ: AgentInspectorOverlay
├── death_registry.py      # НОВЫЙ: DeathRegistry + AgentMemorial + LineageNode
├── lineage_overlay.py     # НОВЫЙ: LineageOverlay
├── agent_panel.py         # ИЗМЕНЕНИЕ: добавить умерших + клик
├── colony_gui.py          # ИЗМЕНЕНИЕ: registry, inspector, lineage
└── app.py                 # ИЗМЕНЕНИЕ: правая панель, overlay рендер, клавиши
```

### 7.1 AgentInspectorOverlay

```python
class AgentInspectorOverlay:
    """
    Полноэкранный overlay с детальной информацией об агенте.
    Read-only. Данные получает при открытии и не обновляет автоматически.
    """
    
    WIDTH  = 480
    HEIGHT = 600
    TABS   = ["NOWA", "Социум", "Репро", "Геном", "История"]
    
    def __init__(self) -> None:
        self._visible: bool = False
        self._active_tab: int = 0
        self._scroll_offset: int = 0
        self._data: dict[str, Any] = {}   # данные агента
        self._agent_id: str = ""
        self._is_deceased: bool = False
    
    def open(self, agent_data: dict[str, Any], is_deceased: bool = False) -> None:
        """Открыть инспектор с данными агента."""
    
    def close(self) -> None:
        """Закрыть инспектор."""
    
    @property
    def visible(self) -> bool: ...
    
    def handle_event(self, event: "pygame.Event") -> bool:
        """
        Обработать pygame событие.
        Возвращает True если событие поглощено (не передавать дальше).
        """
    
    def draw(self, screen: "pygame.Surface", font: "pygame.font.Font", font_small: "pygame.font.Font") -> None:
        """Нарисовать overlay поверх screen."""
```

### 7.2 LineageOverlay

```python
class LineageOverlay:
    """
    Интерактивный overlay с родословным деревом.
    Поддерживает зум, панорамирование и клик по узлам.
    """
    
    def __init__(self, registry: "DeathRegistry") -> None:
        self._visible: bool = False
        self._registry = registry
        self._zoom: float = 1.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._dragging: bool = False
        self._drag_start: tuple[int, int] = (0, 0)
        self._nodes: list[LineageNode] = []
        self._hovered_id: str | None = None
        self._needs_rebuild: bool = True
    
    def toggle(self) -> None:
        """Открыть/закрыть overlay."""
    
    def rebuild(self, living_agents: list[Any]) -> None:
        """Пересчитать позиции узлов дерева."""
    
    def handle_event(self, event: "pygame.Event") -> tuple[bool, str | None]:
        """
        Обработать событие.
        Возвращает (поглощено, agent_id если клик по узлу).
        """
    
    def draw(
        self,
        screen: "pygame.Surface",
        font: "pygame.font.Font",
        font_small: "pygame.font.Font",
    ) -> None:
        """Нарисовать дерево поверх screen."""
```

---

## 8. Изменения в SimulationRunner

### 8.1 Добавить DeathRegistry

```python
class SimulationRunner:
    def __init__(self, factory=None, death_journal_path=None) -> None:
        ...  # существующий код
        self.death_registry = DeathRegistry()   # НОВОЕ
    
    def add_agent(self, agent: ChinchillaAgent) -> None:
        agent.colony = self.agents
        agent.resources = self.resources
        self.agents.append(agent)
        self.swarm.add_agent(agent)
        self.death_registry.register_birth(agent, self.sim_time)   # НОВОЕ
    
    def _handle_agent_death(self, agent_id: str) -> None:
        dead_agent = next((a for a in self.agents if a.agent_id == agent_id), None)
        # НОВОЕ: сохранить в registry ДО удаления
        if dead_agent is not None:
            gen_map = {}   # будет передан из GUI если доступен
            self.death_registry.register_death(dead_agent, self.sim_time, gen_map)
        # ... существующий код удаления
```

### 8.2 Проброс generation_index_map

`register_death()` принимает `generation_index_map: dict[str, int]` для корректного `generation_index` в мемориале. Если map пустой — `generation_index = 0` (fallback).

---

## 9. Изменения в ColonyGUI

```python
class ColonyGUI:
    def __init__(self, runner: Any) -> None:
        ...  # существующий код
        
        # НОВОЕ: inspector и lineage
        self.inspector = AgentInspectorOverlay()
        self.lineage = LineageOverlay(runner.death_registry)
        self._right_panel_scroll: int = 0   # скролл правой панели
    
    def open_inspector(self, agent_id: str) -> None:
        """
        Открыть инспектор для агента (живого или умершего).
        
        Живой: собрать данные из runner.agents
        Умерший: взять из runner.death_registry.get_memorial()
        """
    
    def _build_full_agent_data(self, agent: Any) -> dict[str, Any]:
        """
        Собрать полные данные живого агента для инспектора.
        Читает все атрибуты через getattr с fallback.
        
        Возвращает словарь с секциями:
        {
            "identity": {...},
            "nowa": {
                "affective_axes": {...},    # все 8 осей
                "neuromodulators": {...},   # все 5 модуляторов + tonic
                "wakefulness": {...},       # wakefulness, pressure, circadian, alertness
                "autonomous_drives": {...}, # все drives
                "memory": {...},            # lived_steps, hippocampus_size, etc.
            },
            "social": {
                "known_agents": [...],      # список KnownAgent данных
                "hearsay_received": int,
                "hearsay_sent": int,
            },
            "reproduction": {...},
            "genome": {
                "generation": int,
                "lineage_id": str,
                "genes": dict[str, float],  # полный genome.genes
            },
            "history": {
                "recent_interactions": [...],  # последние 10 по всем KnownAgent
            },
        }
        """
    
    def _build_memorial_data(self, memorial: AgentMemorial) -> dict[str, Any]:
        """Преобразовать AgentMemorial в формат для инспектора."""
```

---

## 10. Правая панель с кликом

В `app.py` добавить рендер правой панели и обработку кликов:

```python
PANEL_RIGHT_X    = 728    # начало правой панели (1024 - 296)
PANEL_RIGHT_W    = 288    # ширина панели
CARD_HEIGHT      = 72     # высота карточки живого агента
CARD_DEAD_HEIGHT = 52     # высота карточки умершего
CARD_MARGIN      = 6
CARD_BG_ALIVE    = (252, 249, 242)
CARD_BG_DEAD     = (220, 215, 210)
CARD_BORDER_ALIVE = (180, 168, 148)
CARD_BORDER_DEAD  = (150, 142, 130)
CARD_TEXT_DEAD    = (110, 100, 90)

def _draw_right_panel(
    screen: pygame.Surface,
    font: pygame.font.Font,
    font_small: pygame.font.Font,
    *,
    living_agents_data: list[dict],    # из get_render_state()["agents"]
    dead_memorials: list[AgentMemorial],
    selected_agent_id: str | None,
    scroll_offset: int,
) -> list[tuple[pygame.Rect, str]]:    # [(card_rect, agent_id)] для обработки кликов
    """
    Нарисовать правую панель.
    Возвращает список (rect, agent_id) для hit-testing кликов.
    """

def _handle_panel_click(
    mouse_pos: tuple[int, int],
    card_hit_areas: list[tuple[pygame.Rect, str]],
) -> str | None:
    """Вернуть agent_id если клик попал в карточку."""
```

---

## 11. Константы и цвета

```python
# agent_inspector.py
INSPECTOR_BG_COLOR     = (245, 239, 229, 240)
INSPECTOR_HEADER_COLOR = (220, 210, 195)
INSPECTOR_TAB_ACTIVE   = (200, 188, 170)
INSPECTOR_TAB_INACTIVE = (230, 222, 210)
INSPECTOR_SEPARATOR    = (185, 170, 150)

BAR_WIDTH_INSPECTOR = 120
BAR_HEIGHT_INSPECTOR = 8

# lineage_overlay.py
LINEAGE_BG_COLOR      = (235, 228, 215, 230)
LINEAGE_TITLE_COLOR   = (35, 28, 20)

# Цвета узлов
NODE_ALIVE_F  = (200, 150, 200)
NODE_ALIVE_M  = (150, 180, 220)
NODE_DEAD     = (160, 155, 150)
NODE_SELECTED = (255, 220, 100)   # жёлтый для выбранного
```

---

## 12. Ограничения реализации

1. `DeathRegistry` — только в памяти. При перезапуске пустой.
2. `AgentInspector` открывается кликом по карточке в правой панели — не по спрайту в клетке.
3. `LineageOverlay` и `AgentInspector` не могут быть открыты одновременно — открытие одного закрывает другое.
4. При открытом overlay симуляция **не останавливается** (только GUI блокирует ввод в основное окно).
5. Инспектор для живого агента показывает данные **на момент открытия** — не обновляется в реальном времени.
6. Максимальное число карточек умерших в правой панели: 20 (самые свежие). Остальные доступны через дерево.
7. `LineageOverlay` — максимум 8 поколений вертикально. При большем числе — скролл вниз.
8. Клик по узлу умершего агента в дереве открывает инспектор с данными мемориала.
9. Нет сохранения DeathRegistry в файл — только текущая сессия.
10. Python 3.10+, только pygame + стандартная библиотека.

---

## 13. Тест-кейсы

### TC-01: DeathRegistry.register_birth / register_death

```python
registry = DeathRegistry()
agent = ChinchillaAgent(sex="F", generation=0)
registry.register_birth(agent, sim_time=10.0)

assert registry.get_birth_time(agent.agent_id) == 10.0
assert not registry.is_deceased(agent.agent_id)

memorial = registry.register_death(agent, sim_time=500.0, generation_index_map={})
assert registry.is_deceased(agent.agent_id)
assert memorial.agent_id == agent.agent_id
assert memorial.death_sim_time == 500.0
assert memorial.sex == "F"
assert memorial.generation == 0
```

### TC-02: AgentMemorial содержит финальный аффект

```python
registry = DeathRegistry()
agent = ChinchillaAgent(sex="M")
agent.affective_space.axes["stress"] = 0.75
agent.affective_space.axes["valence"] = -0.3
registry.register_birth(agent, 0.0)

memorial = registry.register_death(agent, 100.0, {})

assert abs(memorial.final_stress - 0.75) < 1e-6
assert abs(memorial.final_valence - (-0.3)) < 1e-6
```

### TC-03: AgentMemorial содержит genome genes

```python
from genome import GenomeVector

registry = DeathRegistry()
agent = ChinchillaAgent(sex="F")
agent.genome = GenomeVector.default()
registry.register_birth(agent, 0.0)

memorial = registry.register_death(agent, 100.0, {})

assert isinstance(memorial.genome_genes, dict)
assert "af_decay_stress" in memorial.genome_genes
assert "lt_max_lifespan_factor" in memorial.genome_genes
```

### TC-04: get_lineage_nodes включает живых и умерших

```python
registry = DeathRegistry()

dead_agent = ChinchillaAgent(sex="F", generation=0)
registry.register_birth(dead_agent, 0.0)
registry.register_death(dead_agent, 100.0, {})

living_agent = ChinchillaAgent(sex="M", generation=0)

nodes = registry.get_lineage_nodes([living_agent])

node_ids = {n.agent_id for n in nodes}
assert dead_agent.agent_id in node_ids
assert living_agent.agent_id in node_ids

dead_node = next(n for n in nodes if n.agent_id == dead_agent.agent_id)
alive_node = next(n for n in nodes if n.agent_id == living_agent.agent_id)
assert not dead_node.is_alive
assert alive_node.is_alive
```

### TC-05: get_children возвращает потомков

```python
registry = DeathRegistry()

mother = ChinchillaAgent(sex="F", generation=0)
child1 = ChinchillaAgent(sex="M", generation=1)
child1.parents = (mother.agent_id, None)
mother.own_offspring = [child1.agent_id]

registry.register_birth(mother, 0.0)
memorial = registry.register_death(mother, 200.0, {})

children = registry.get_children(mother.agent_id)
assert child1.agent_id in children
```

### TC-06: register_death не падает на минимальном агенте

```python
class MinAgent:
    agent_id = "min"
    sex = "F"
    generation = 0
    parents = (None, None)
    age = 100.0
    lived_steps = 500
    own_offspring = []
    knowledge = {}

registry = DeathRegistry()
registry.register_birth(MinAgent(), 0.0)
memorial = registry.register_death(MinAgent(), 100.0, {})

assert memorial.agent_id == "min"
assert memorial.final_stress == 0.0
assert memorial.genome_genes == {}
```

### TC-07: _build_full_agent_data содержит все секции

```python
runner = SimulationRunner()
agent = ChinchillaAgent(sex="F", generation=1)
runner.add_agent(agent)

gui = ColonyGUI(runner)
data = gui._build_full_agent_data(agent)

assert "identity" in data
assert "nowa" in data
assert "social" in data
assert "reproduction" in data
assert "genome" in data
assert "history" in data

assert "affective_axes" in data["nowa"]
assert "neuromodulators" in data["nowa"]
assert "wakefulness" in data["nowa"]
assert "autonomous_drives" in data["nowa"]
assert "memory" in data["nowa"]
```

### TC-08: inspector открывается для живого агента

```python
runner = SimulationRunner()
agent = ChinchillaAgent(sex="M")
runner.add_agent(agent)

gui = ColonyGUI(runner)
assert not gui.inspector.visible

gui.open_inspector(agent.agent_id)
assert gui.inspector.visible
assert gui.inspector._agent_id == agent.agent_id
assert not gui.inspector._is_deceased
```

### TC-09: inspector открывается для умершего агента

```python
runner = SimulationRunner()
agent = ChinchillaAgent(sex="F")
runner.add_agent(agent)
runner.death_registry.register_death(agent, 100.0, {})

gui = ColonyGUI(runner)
gui.open_inspector(agent.agent_id)

assert gui.inspector.visible
assert gui.inspector._is_deceased
```

### TC-10: LineageOverlay toggle

```python
runner = SimulationRunner()
gui = ColonyGUI(runner)

assert not gui.lineage.visible
gui.lineage.toggle()
assert gui.lineage.visible
gui.lineage.toggle()
assert not gui.lineage.visible
```

### TC-11: Открытие lineage закрывает inspector

```python
runner = SimulationRunner()
agent = ChinchillaAgent(sex="F")
runner.add_agent(agent)

gui = ColonyGUI(runner)
gui.open_inspector(agent.agent_id)
assert gui.inspector.visible

# Нажатие L должно закрыть inspector
gui.inspector.close()
gui.lineage.toggle()
assert gui.lineage.visible
assert not gui.inspector.visible
```

### TC-12: lineage.rebuild создаёт узлы

```python
runner = SimulationRunner()
for i in range(3):
    runner.add_agent(ChinchillaAgent(sex="F" if i%2==0 else "M", generation=0))

gui = ColonyGUI(runner)
gui.lineage.rebuild(runner.agents)

assert len(gui.lineage._nodes) == 3
for node in gui.lineage._nodes:
    assert isinstance(node.tree_x, float)
    assert isinstance(node.tree_y, float)
    assert node.generation == 0
```

### TC-13: Позиции узлов одного поколения не совпадают

```python
runner = SimulationRunner()
for _ in range(4):
    runner.add_agent(ChinchillaAgent(sex="F", generation=0))

gui = ColonyGUI(runner)
gui.lineage.rebuild(runner.agents)

positions = [(n.tree_x, n.tree_y) for n in gui.lineage._nodes]
assert len(set(positions)) == 4  # все разные
```

### TC-14: get_all_memorials сортирован по времени смерти

```python
registry = DeathRegistry()
for i in range(3):
    a = ChinchillaAgent(sex="F")
    registry.register_birth(a, float(i * 10))
    registry.register_death(a, float(i * 100 + 50), {})

memorials = registry.get_all_memorials()
times = [m.death_sim_time for m in memorials]
assert times == sorted(times)
```

### TC-15: total_ever_lived учитывает живых и умерших

```python
registry = DeathRegistry()

living = ChinchillaAgent(sex="F")
registry.register_birth(living, 0.0)

dead = ChinchillaAgent(sex="M")
registry.register_birth(dead, 0.0)
registry.register_death(dead, 100.0, {})

# 2 агента всего жили в этой сессии
assert registry.total_ever_lived() == 2
```

### TC-16: AgentInspector.handle_event поглощает клики внутри

```python
import pygame
pygame.init()

inspector = AgentInspectorOverlay()
inspector.open({"identity": {"agent_id": "test", "name": "G0A1", "sex": "F",
                              "generation": 0, "parents": (None, None)}}, False)

# Клик внутри инспектора
click_inside = pygame.event.Event(
    pygame.MOUSEBUTTONDOWN,
    {"pos": (512, 384), "button": 1}
)
consumed = inspector.handle_event(click_inside)
assert consumed is True
```

---

## 14. Примечания для реализующего агента

- `death_registry` добавляется в `SimulationRunner.__init__()` — `DeathRegistry` импортируется из `colony_gui.death_registry` или выносится в `src/death_registry.py` если нужна независимость от GUI
- Лучше вынести `DeathRegistry` в `src/death_registry.py` — тогда runner не зависит от GUI пакета
- `_build_full_agent_data()` читает `genome.genes` как `dict(getattr(agent.genome, "genes", {}) or {})` — может быть OrderedDict
- Для отображения генов в инспекторе группировать по префиксу ключа: `nm_*`, `af_*`, `wk_*`, `dr_*`, `lr_*`, `im_*`, `lt_*`
- `PANEL_RIGHT_X = 728` — правая панель начинается после клетки (клетка занимает до x≈720 с учётом прутьев)
- Скролл правой панели через `pygame.MOUSEWHEEL` когда курсор над панелью
- При `LineageOverlay` открытом — скролл колёсиком управляет зумом дерева, не скроллом правой панели
- Для пунктирной линии пары: рисовать сегменты `(0, 0, 8, 0), (12, 0, 20, 0)` и т.д. через `pygame.draw.line()`
- Инспектор закрывается клавишей ESC или повторным кликом на ту же карточку
- При `is_deceased=True` заголовок инспектора показывает `†` и причину смерти, вкладка "NOWA" показывает финальные значения с пометкой "(при смерти)"
