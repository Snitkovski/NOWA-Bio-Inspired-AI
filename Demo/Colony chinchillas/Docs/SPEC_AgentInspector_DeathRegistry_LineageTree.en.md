## Abstract

Russian version: [SPEC_AgentInspector_DeathRegistry_LineageTree.ru.md](SPEC_AgentInspector_DeathRegistry_LineageTree.ru.md)

Scientific account of the colony: [COLONY_SPEC.en.md](COLONY_SPEC.en.md).

Version 1.0 of this specification defines three components of the colony's graphical contour: the death registry `DeathRegistry`, the agent-inspector overlay, and the lineage-tree overlay. The registry is held in session memory and stores memorials of the dead together with birth records required to construct a kinship graph of living and dead individuals.

The record `AgentMemorial` captures at death the identity, life span, cause of death, offspring, final affect and neuromodulators, NOWA state measures, and the genome. The inspector opens from an agent card and distributes observation across tabs for cognitive state, sociality, reproduction, genome, and history. The lineage overlay draws the living and the dead in one graph and is invoked separately from the inspector.

The role of the document in the installation is to retain individuals who disappear from the current slice as units of kinship and of a completed life. Registration of birth and death is separate from action policy: the graphical layer reads public state and does not modify the agent. It thereby defines a read contract for later comparison of lines in the multi-agent NOWA simulation.

# Specification: Agent Inspector + Death Registry + Lineage Tree

**Files:**
- `colony_gui/agent_inspector.py` — new
- `colony_gui/death_registry.py` — new
- `colony_gui/lineage_overlay.py` — new
- changes in `colony_gui/colony_gui.py`
- changes in `colony_gui/app.py`
- changes in `simulation_runner.py`

**Version:** 1.0

---

## 1. Overall architecture of the three components

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

## 2. DeathRegistry — registry of deceased agents

### 2.1 AgentMemorial — a complete snapshot of the agent at the moment of death

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

## 3. LineageNode and LineageTree

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

### 3.2 Tree positioning algorithm

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

Positioning constants:

```python
GENERATION_ROW_HEIGHT = 110   # пикселей между поколениями
NODE_SPACING_X = 90           # пикселей между агентами одного поколения
NODE_RADIUS_ALIVE = 28        # радиус круга живого агента
NODE_RADIUS_DEAD = 22         # радиус круга умершего агента
```

---

## 4. AgentInspector — inspector of a living agent

### 4.1 Panel structure (overlay 480×600 px)

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

### 4.2 NOWA tab

The full cognitive state is shown:

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

### 4.3 Sociality tab

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

### 4.4 Reproduction tab

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

*(for females, in addition: the `heat_cycle` phase, value, urgency, and `is_pregnant`)*

### 4.5 Genome tab

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

### 4.6 History tab

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

## 5. LineageOverlay — the lineage tree

### 5.1 Controls

```
L — открыть/закрыть LineageOverlay
ESC — закрыть
Колёсико мыши — зум [0.4x ... 2.0x]
ЛКМ + drag — панорамирование
Клик на узел — показать AgentInspector для этого агента
```

### 5.2 Visual language of the nodes

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

### 5.3 Kinship lines

```python
# Линия от родителя к ребёнку
LINEAGE_LINE_COLOR       = (140, 130, 115)
LINEAGE_LINE_WIDTH       = 2

# Линия пары (мать←→отец) — горизонтальная
PAIR_LINE_COLOR          = (180, 160, 140)
PAIR_LINE_WIDTH          = 1
PAIR_LINE_STYLE          = "dashed"   # пунктир (pygame: чередование сегментов)
```

### 5.4 Contents of a node

Inside each node, the information is minimal:

```
    G1A2
     ♂
   [иконка состояния]
```

State icons (an emoji glyph when one is available, otherwise text):

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

### 5.5 Tooltip on hover

When the mouse hovers over a node, a small tooltip is shown beside it:

```
G1A2 ♂ adult
Возраст: 00:22:47
Потомков: 2
Стресс: 0.38
[жив / умер от exhaustion в 01:15:30]
```

### 5.6 Scrolling and zoom

```python
LINEAGE_ZOOM_MIN  = 0.3
LINEAGE_ZOOM_MAX  = 2.5
LINEAGE_ZOOM_STEP = 0.1

# Начальное положение: всё дерево центрировано
# Начальный зум: подобрать чтобы всё влезло по ширине
```

---

## 6. Right panel with agent cards

The existing right panel is extended. The following are added:

1. **Cards of living agents** (the existing code, with a click)
2. **The separator `── умершие ──`** (if any agents have died)
3. **Cards of the deceased** (grey, with the cause of death)

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

Cards of the deceased are clickable. They open the AgentInspector with data from `AgentMemorial` (every tab, other than data that exist only for the living, shows the final values).

---

## 7. Code structure

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

## 8. Changes in SimulationRunner

### 8.1 Addition of DeathRegistry

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

### 8.2 Passing generation_index_map

`register_death()` accepts `generation_index_map: dict[str, int]` so that `generation_index` in the memorial is correct. If the map is empty, `generation_index = 0` (the fallback).

---

## 9. Changes in ColonyGUI

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

## 10. Right panel with click handling

In `app.py`, add rendering of the right panel and handling of clicks:

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

## 11. Constants and colours

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

## 12. Implementation constraints

1. `DeathRegistry` is held only in memory. On restart it is empty.
2. `AgentInspector` opens by a click on a card in the right panel, not by a click on a sprite in the cage.
3. `LineageOverlay` and `AgentInspector` cannot be open at the same time: opening one closes the other.
4. While an overlay is open, the simulation **does not stop** (only the GUI blocks input to the main window).
5. The inspector of a living agent shows data **at the moment of opening**; it is not updated in real time.
6. The maximum number of deceased cards in the right panel is 20 (the most recent). The remainder are available through the tree.
7. `LineageOverlay` shows at most 8 generations vertically. With a larger number, the view scrolls downward.
8. A click on the node of a deceased agent in the tree opens the inspector with the memorial data.
9. `DeathRegistry` is not saved to a file; only the current session is retained.
10. Python 3.10+, pygame and the standard library only.

---

## 13. Test cases

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

### TC-02: AgentMemorial contains the final affect

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

### TC-03: AgentMemorial contains the genome genes

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

### TC-04: get_lineage_nodes includes the living and the dead

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

### TC-05: get_children returns the offspring

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

### TC-06: register_death does not fail on a minimal agent

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

### TC-07: _build_full_agent_data contains every section

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

### TC-08: the inspector opens for a living agent

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

### TC-09: the inspector opens for a deceased agent

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

### TC-11: Opening the lineage closes the inspector

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

### TC-12: lineage.rebuild creates the nodes

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

### TC-13: Positions of nodes within one generation do not coincide

```python
runner = SimulationRunner()
for _ in range(4):
    runner.add_agent(ChinchillaAgent(sex="F", generation=0))

gui = ColonyGUI(runner)
gui.lineage.rebuild(runner.agents)

positions = [(n.tree_x, n.tree_y) for n in gui.lineage._nodes]
assert len(set(positions)) == 4  # все разные
```

### TC-14: get_all_memorials is sorted by time of death

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

### TC-15: total_ever_lived counts the living and the dead

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

### TC-16: AgentInspector.handle_event consumes clicks inside the inspector

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

## 14. Notes for the implementing agent

- `death_registry` is added in `SimulationRunner.__init__()`. `DeathRegistry` is imported from `colony_gui.death_registry`, or moved to `src/death_registry.py` if independence from the GUI is required.
- It is preferable to place `DeathRegistry` in `src/death_registry.py`, so that the runner does not depend on the GUI package.
- `_build_full_agent_data()` reads `genome.genes` as `dict(getattr(agent.genome, "genes", {}) or {})`; the value may be an `OrderedDict`.
- For the display of genes in the inspector, group by key prefix: `nm_*`, `af_*`, `wk_*`, `dr_*`, `lr_*`, `im_*`, `lt_*`.
- `PANEL_RIGHT_X = 728`: the right panel begins after the cage (the cage extends to approximately x = 720, allowing for the bars).
- The right panel scrolls by `pygame.MOUSEWHEEL` when the cursor is over the panel.
- While `LineageOverlay` is open, the wheel controls the zoom of the tree, not the scroll of the right panel.
- For the dashed pair-line, draw segments `(0, 0, 8, 0), (12, 0, 20, 0)`, and so on, through `pygame.draw.line()`.
- The inspector is closed by the ESC key or by a repeated click on the same card.
- When `is_deceased=True`, the inspector header shows `†` and the cause of death, and the NOWA tab shows the final values with the annotation `(при смерти)`.
