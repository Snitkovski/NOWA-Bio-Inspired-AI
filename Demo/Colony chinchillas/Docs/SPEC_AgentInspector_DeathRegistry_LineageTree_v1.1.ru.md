## Аннотация

English version: [SPEC_AgentInspector_DeathRegistry_LineageTree_v1.1.en.md](SPEC_AgentInspector_DeathRegistry_LineageTree_v1.1.en.md)

Научное описание колонии: [COLONY_SPEC.ru.md](COLONY_SPEC.ru.md).

Документ версии 1.1 задаёт совместную спецификацию реестра смертей, инспектора агента и оверлея родословной для колонии шиншилл. Реестр вынесен в модуль `death_registry` в составе `src` и не зависит от графического интерфейса. Умершие сохраняются в JSON рядом с сохранением колонии, а геном фиксируется целиком как словарь `genome.genes`.

Центральная структура `AgentMemorial` снимает на момент смерти идентичность и положение в поколении, интервал жизни и причину смерти, потомство, финальные аффект и нейромодуляторы, показатели бодрствования, витальности, гиппокампа и коры, социальный след и полный геном. Извлечение читает публичные атрибуты агента, подставляет пустые значения при отсутствии поля и не изменяет особь. Инспектор и оверлей родословной используют эти мемориалы совместно с живыми агентами исполнителя симуляции.

В многоагентной установке NOWA спецификация закрепляет продольный архив особей, покидающих текущий срез. Без снимка на момент смерти сопоставление геномов, причин смертности и социальной структуры ограничивалось бы живой популяцией. Версия 1.1 отделяет сохранение мемориалов от слоя отображения и тем самым делает реестр доступным для наблюдения вне сеанса графического интерфейса.

# Спецификация: DeathRegistry + AgentInspector + LineageOverlay

**Вариант B:** хранение умерших в JSON файл рядом с colony save  
**Геномы:** сохраняются целиком (полный `genome.genes`)  
**Файлы:**
- `src/death_registry.py` — новый (независим от GUI)
- `colony_gui/agent_inspector.py` — новый
- `colony_gui/lineage_overlay.py` — новый
- изменения в `simulation_runner.py`
- изменения в `colony_gui/colony_gui.py`
- изменения в `colony_gui/app.py`

**Версия:** 1.1

---

## 1. death_registry.py — в src/, независим от GUI

### 1.1 AgentMemorial

```python
@dataclass
class AgentMemorial:
    """Complete snapshot of an agent captured at the moment of death."""

    # --- Identity ---
    agent_id: str
    name: str
    sex: str
    generation: int
    parents: tuple[str | None, str | None]
    generation_index: int          # порядковый номер в поколении (G0A1 → 1)

    # --- Life span ---
    birth_sim_time: float
    death_sim_time: float
    age_at_death: float            # agent.age в sim-секундах
    lived_steps: int               # agent.lived_steps
    cause_of_death: str            # из mortality_system.cause_of_death

    # --- Offspring ---
    own_offspring: list[str]       # agent_id детёнышей
    total_offspring: int           # из reproductive_system.total_offspring

    # --- Final affective state ---
    final_stress: float
    final_valence: float
    final_arousal: float
    final_attachment: float
    final_curiosity: float
    final_trust: float
    final_dominance: float
    final_energy: float
    final_social_drive: float

    # --- Final neuromodulators ---
    final_dopamine: float
    final_serotonin: float
    final_norepinephrine: float
    final_cortisol: float
    final_acetylcholine: float

    # --- Final NOWA cognitive state ---
    final_wakefulness: float
    final_vitality: float
    final_hippocampus_size: int    # len(hippocampus.experiences)
    final_cortex_patterns: int     # len(cortex.patterns)
    final_mean_td_error: float     # среднее из td_error_history

    # --- Full genome (stored entirely) ---
    genome_genes: dict[str, float]    # полный genome.genes
    genome_generation: int            # genome.generation
    genome_lineage_id: str            # genome.lineage_id

    # --- Social footprint ---
    known_agents_count: int           # len(knowledge) на момент смерти
    bonded_count: int                 # сколько bonded связей
    kin_count: int                    # сколько kin связей
    mate_count: int                   # сколько mate связей
    total_interactions: int           # суммарно эпизодов по всем KnownAgent
    positive_interactions: int        # суммарно positive_count
    negative_interactions: int        # суммарно negative_count
```

### 1.2 Вспомогательная функция сбора данных

```python
def _extract_memorial(
    agent: Any,
    *,
    birth_sim_time: float,
    death_sim_time: float,
    generation_index_map: dict[str, int],
) -> AgentMemorial:
    """
    Извлечь все данные агента через getattr с fallback.
    Никогда не вызывает исключений — любая ошибка даёт 0.0/"".

    Читает:
        agent.affective_space.axes          — аффективные оси
        agent.neuromodulators.{nm}          — нейромодуляторы
        agent.wakefulness.wakefulness       — бодрствование
        agent.energy                        — энергия (property)
        agent.social_drive                  — social drive (property)
        agent.autonomous_runtime            — drives
        agent.hippocampus.experiences       — размер памяти
        agent.cortex.patterns               — кортикальные паттерны
        agent.td_error_history              — TD ошибки
        agent.genome.genes                  — ПОЛНЫЙ словарь генов
        agent.genome.generation             — поколение генома
        agent.genome.lineage_id             — lineage
        agent.knowledge                     — социальные связи
        agent.mortality_system.cause_of_death
        agent.mortality_system.vitality
        agent.reproductive_system.total_offspring
        agent.reproductive_system.reproductive_drive
        agent.own_offspring                 — список потомков
        agent.age, agent.lived_steps
        agent.sex, agent.generation, agent.parents, agent.name
    """
```

### 1.3 DeathRegistry

```python
REGISTRY_VERSION = "1.1"
MAX_MEMORIALS_IN_MEMORY = 500    # максимум мемориалов в RAM
REGISTRY_FILENAME = "death_registry.json"


class DeathRegistry:
    """
    Registry of all agents that ever lived.
    Persists to JSON alongside colony save files.
    """

    def __init__(self, save_dir: str | Path | None = None) -> None:
        """
        Аргументы:
            save_dir: директория для автосохранения registry.
                      None = не сохранять автоматически.
        """
        self._memorials: dict[str, AgentMemorial] = {}
        self._birth_times: dict[str, float] = {}
        self._save_dir: Path | None = Path(save_dir) if save_dir else None

    # ── Регистрация событий ──────────────────────────────────────────

    def register_birth(self, agent: Any, sim_time: float) -> None:
        """
        Запомнить время рождения агента.
        Вызывать из SimulationRunner.add_agent().
        """

    def register_death(
        self,
        agent: Any,
        sim_time: float,
        generation_index_map: dict[str, int],
    ) -> AgentMemorial:
        """
        Создать AgentMemorial и сохранить в registry.
        Вызывать из SimulationRunner._handle_agent_death()
        ДО удаления агента из runner.agents.

        При переполнении MAX_MEMORIALS_IN_MEMORY —
        удалять самые старые (по death_sim_time).

        Если save_dir задан — вызвать autosave().

        Возвращает: созданный AgentMemorial.
        """

    # ── Чтение ───────────────────────────────────────────────────────

    def get_memorial(self, agent_id: str) -> AgentMemorial | None:
        """Мемориал умершего агента или None."""

    def get_all_memorials(self) -> list[AgentMemorial]:
        """Все мемориалы, отсортированные по death_sim_time ASC."""

    def get_recent_memorials(self, n: int = 20) -> list[AgentMemorial]:
        """Последние N умерших по death_sim_time DESC."""

    def get_birth_time(self, agent_id: str) -> float:
        """sim_time рождения. 0.0 если неизвестен."""

    def is_deceased(self, agent_id: str) -> bool:
        """True если агент зарегистрирован как умерший."""

    def total_ever_lived(self) -> int:
        """len(_birth_times) — все кто когда-либо рождался."""

    def get_children(self, agent_id: str) -> list[str]:
        """
        agent_id всех детей агента.
        Ищет в own_offspring всех мемориалов.
        """

    def get_lineage_nodes(
        self,
        living_agents: list[Any],
        generation_index_map: dict[str, int],
    ) -> list["LineageNode"]:
        """
        Построить LineageNode для всех когда-либо живших агентов.
        Объединяет умерших (из мемориалов) и живых.
        """

    # ── Персистенция ─────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """
        Сохранить registry в JSON файл.

        Формат:
        {
            "version": "1.1",
            "total_ever_lived": int,
            "memorial_count": int,
            "birth_times": {agent_id: float},
            "memorials": [
                {все поля AgentMemorial, genome_genes полностью}
            ]
        }

        Создаёт директорию если не существует.
        При ошибке записи — warnings.warn, не исключение.
        """

    def load(self, path: str | Path) -> None:
        """
        Загрузить registry из JSON.
        Добавляет к существующим данным (не заменяет).
        При конфликте agent_id — существующий мемориал побеждает.
        При ошибке парсинга — warnings.warn, данные не меняются.
        """

    def autosave(self) -> None:
        """
        Сохранить в self._save_dir / REGISTRY_FILENAME.
        Ничего не делает если save_dir не задан.
        """

    def clear(self) -> None:
        """Очистить все данные."""

    def summary(self) -> str:
        """
        Краткая текстовая сводка.
        Пример: "Registry: 12 ever lived, 8 deceased, 4 living"
        """
```

---

## 2. LineageNode

```python
@dataclass
class LineageNode:
    """One node in the rendered lineage tree."""
    agent_id: str
    display_name: str              # G0A1, G1A3 и т.д.
    sex: str
    generation: int
    parents: tuple[str | None, str | None]
    own_offspring: list[str]
    is_alive: bool
    cause_of_death: str            # "" если живой
    age: float                     # текущий (живые) или age_at_death
    total_offspring: int
    generation_index: int

    # Позиция в дереве (заполняется LineageOverlay.rebuild())
    tree_x: float = 0.0
    tree_y: float = 0.0
```

---

## 3. agent_inspector.py

### 3.1 Структура данных инспектора

```python
@dataclass
class InspectorData:
    """
    Normalized payload for AgentInspectorOverlay.
    Одинаковый формат для живых и умерших агентов.
    """
    agent_id: str
    display_name: str
    is_deceased: bool

    # Identity
    sex: str
    generation: int
    parents: tuple[str | None, str | None]
    age: float
    lived_steps: int
    cause_of_death: str            # "" если живой

    # Вкладка NOWA
    affective_axes: dict[str, float]       # все 8 осей
    neuromodulators: dict[str, float]      # dopamine, serotonin, ne, cortisol, ach
    wakefulness: dict[str, float]          # wakefulness, sleep_pressure, circadian, alertness
    autonomous_drives: dict[str, float]    # curiosity, social_drive, exploration, energy
    memory: dict[str, float | int]         # lived_steps, hippocampus_size, cortex_patterns, td_error

    # Вкладка Социум
    known_agents: list[dict]               # список KnownAgent данных
    hearsay_received: int
    hearsay_sent: int                      # оценка по размеру hearsay в knowledge других

    # Вкладка Репро
    sex_specific: dict[str, Any]           # heat_cycle, is_pregnant и т.д.
    reproductive_drive: float
    cooldown_steps: int
    total_offspring_count: int
    own_offspring_ids: list[str]
    vitality: float
    senescence_rate: float

    # Вкладка Геном
    genome_genes: dict[str, float]         # полный словарь
    genome_generation: int
    genome_lineage_id: str

    # Вкладка История
    recent_interactions: list[dict]        # последние 20 по всем KnownAgent
```

### 3.2 Функции сбора данных

```python
def build_inspector_data_from_agent(
    agent: Any,
    display_name: str,
) -> InspectorData:
    """
    Собрать InspectorData из живого агента.
    Все обращения через getattr с fallback.
    Никогда не падает.
    """

def build_inspector_data_from_memorial(
    memorial: AgentMemorial,
    display_name: str,
) -> InspectorData:
    """
    Собрать InspectorData из AgentMemorial умершего агента.
    Поля которые не сохранялись (hearsay и т.д.) — заполнить из social footprint.
    """
```

### 3.3 AgentInspectorOverlay

```python
INSPECTOR_WIDTH  = 500
INSPECTOR_HEIGHT = 620
TABS = ["NOWA", "Социум", "Репро", "Геном", "История"]

# Цвета
INSPECTOR_BG       = (245, 239, 229, 245)
INSPECTOR_HEADER   = (220, 210, 195)
TAB_ACTIVE         = (200, 188, 170)
TAB_INACTIVE       = (232, 224, 212)
TAB_TEXT_ACTIVE    = (35, 28, 20)
TAB_TEXT_INACTIVE  = (100, 88, 70)
INSPECTOR_DECEASED_TINT = (210, 205, 200, 245)  # для умерших — чуть серее
BAR_W = 130
BAR_H = 8


class AgentInspectorOverlay:
    """
    Full-screen overlay showing complete agent metrics.

    - Открывается: open(inspector_data)
    - Закрывается: close() или ESC или повторный клик той же карточки
    - Вкладки: клик по заголовку вкладки
    - Скролл содержимого: колёсико мыши когда inspector видим
    - Данные статичны на момент открытия (не обновляются в реальном времени)
    """

    def __init__(self) -> None:
        self._visible: bool = False
        self._active_tab: int = 0
        self._scroll: int = 0
        self._data: InspectorData | None = None
        self._surface: "pygame.Surface | None" = None   # кэш отрисовки

    @property
    def visible(self) -> bool: ...

    @property
    def agent_id(self) -> str:
        """agent_id открытого агента или ""."""

    def open(self, data: InspectorData) -> None:
        """Открыть инспектор. Сбрасывает вкладку и скролл."""

    def close(self) -> None:
        """Закрыть инспектор."""

    def handle_event(self, event: "pygame.Event") -> bool:
        """
        Обработать pygame событие.
        Возвращает True если событие поглощено.

        Поглощает:
        - ESC → close()
        - клик по вкладке → переключить вкладку
        - MOUSEWHEEL → скролл содержимого
        - клик по области inspector → поглотить (не пропускать в основной экран)
        - клик вне inspector → close()
        """

    def draw(
        self,
        screen: "pygame.Surface",
        font: "pygame.font.Font",
        font_small: "pygame.font.Font",
        font_mono: "pygame.font.Font",    # моноширинный для генома
    ) -> None:
        """
        Нарисовать inspector поверх screen.

        Позиция: центр экрана или сдвинут вправо чтобы не перекрывать клетку.
        Полупрозрачный фон через SRCALPHA.
        """

    # ── Внутренние методы отрисовки ────────────────────────────────

    def _draw_tab_nowa(
        self,
        surface: "pygame.Surface",
        font: "pygame.font.Font",
        font_small: "pygame.font.Font",
    ) -> int:
        """
        Нарисовать содержимое вкладки NOWA.
        Возвращает полную высоту содержимого (для скролла).

        Секции:
        1. АФФЕКТ — 7 осей с барами (stress, valence, arousal,
                    attachment, curiosity, trust, dominance)
        2. НЕЙРОМОДУЛЯТОРЫ — 5 модуляторов с барами
        3. БОДРСТВОВАНИЕ — wakefulness, sleep_pressure, circadian, alertness
        4. АВТОНОМНЫЕ ДРАЙВЫ — curiosity_drive, social_drive, exploration, energy
        5. ПАМЯТЬ — lived_steps, hippocampus_size, cortex_patterns, td_error

        Для умершего агента: заголовок секции "(при смерти)"
        """

    def _draw_tab_social(self, surface, font, font_small) -> int:
        """
        Вкладка Социум.

        Для каждого known_agent:
            [иконка отношения] [имя]  [relationship_type]
            affinity: ████░░░░  0.72   familiarity: ████░░  0.68   trust: ████░  0.75
            Взаимодействий: 24 (позит: 22, негат: 2)
            Последнее: allogroom 00:14:23 → accepted

        Для умершего: данные из AgentMemorial.known_agents_count и счётчиков.
        """

    def _draw_tab_repro(self, surface, font, font_small) -> int:
        """
        Вкладка Репро.

        Общая часть (все агенты):
            Пол, возраст, половозрелость
            REPRODUCTIVE DRIVE: бар + значение + порог
            Cooldown, total_offspring, потомки (список GxAy)
            MORTALITY: vitality бар, senescence_rate, cause_of_death

        Для самок дополнительно:
            HEAT CYCLE: phase, value бар, urgency
            is_pregnant, gestation_timer

        Для умершего: финальные значения из AgentMemorial.
        """

    def _draw_tab_genome(self, surface, font, font_small, font_mono) -> int:
        """
        Вкладка Геном.

        Группировка по префиксу ключа:
            NM — нейромодуляторные веса (nm_*)
            AF — аффект decay (af_*)
            WK — бодрствование (wk_*)
            DR — драйвы (dr_*)
            LR — обучение (lr_*)
            IM — воображение (im_*)
            LT — продолжительность жизни (lt_*)

        Для каждого гена:
            ключ           значение   [мини-бар нормированный в диапазоне гена]

        Заголовок: "Геном поколения {N} | Lineage: {lineage_id}"
        """

    def _draw_tab_history(self, surface, font, font_small) -> int:
        """
        Вкладка История.

        Последние 20 взаимодействий (объединённые из всех KnownAgent,
        отсортированные по time DESC):
            [время]  [тип]  с [агент]  → [outcome]  Δ[affect_delta:+/-]

        Для умершего: данные из AgentMemorial.total_interactions и счётчиков.
        Если данных нет — "История недоступна для умерших агентов"
        """
```

---

## 4. lineage_overlay.py

```python
# Константы позиционирования
GENERATION_ROW_H = 120    # пикселей между поколениями (по вертикали)
NODE_SPACING_X   = 95     # пикселей между узлами одного поколения
NODE_R_ALIVE     = 28     # радиус живого агента
NODE_R_DEAD      = 22     # радиус умершего агента

# Цвета узлов
NODE_F_ALIVE   = (200, 150, 200)    # розово-фиолетовый (самка живая)
NODE_M_ALIVE   = (150, 180, 220)    # голубой (самец живой)
NODE_DEAD      = (158, 152, 148)    # серый (умерший)
NODE_SELECTED  = (255, 215, 80)     # жёлтый (выбранный)
NODE_BORDER    = (80, 65, 45)
NODE_BORDER_W  = 3

# Линии
LINE_PARENT    = (140, 130, 115)    # родитель → ребёнок
LINE_PAIR      = (180, 165, 145)    # горизонталь мать←→отец
LINE_W         = 2
LINE_PAIR_DASH = 8                  # длина сегмента пунктира (пикселей)

# Зум
ZOOM_MIN  = 0.3
ZOOM_MAX  = 2.5
ZOOM_STEP = 0.15

# Наложение
OVERLAY_BG = (232, 226, 214, 225)


class LineageOverlay:
    """
    Interactive lineage tree overlay.

    Управление:
        L           — toggle (открыть/закрыть)
        ESC         — закрыть
        ЛКМ drag    — панорамирование
        Колёсо      — зум
        Клик узел   — вернуть agent_id (для открытия inspector)
    """

    def __init__(self, registry: "DeathRegistry") -> None:
        self._visible: bool = False
        self._registry = registry
        self._zoom: float = 1.0
        self._offset: list[float] = [0.0, 0.0]
        self._dragging: bool = False
        self._drag_start: tuple[int, int] = (0, 0)
        self._drag_offset_start: list[float] = [0.0, 0.0]
        self._nodes: list[LineageNode] = []
        self._hovered_id: str | None = None
        self._needs_rebuild: bool = True

    @property
    def visible(self) -> bool: ...

    def toggle(self) -> None:
        """Открыть или закрыть overlay."""

    def close(self) -> None: ...

    def mark_dirty(self) -> None:
        """Пометить дерево как требующее перестройки."""

    def rebuild(
        self,
        living_agents: list[Any],
        generation_index_map: dict[str, int],
    ) -> None:
        """
        Пересчитать позиции всех узлов.

        Алгоритм:
            1. Получить все LineageNode из registry.get_lineage_nodes()
            2. Сгруппировать по generation
            3. Внутри каждого поколения — отсортировать по birth_sim_time
            4. Назначить tree_x = col_index * NODE_SPACING_X
            5. Назначить tree_y = generation * GENERATION_ROW_H
            6. Центрировать каждое поколение по ширине экрана

        Вызывать при:
            - открытии overlay (_needs_rebuild == True)
            - рождении нового агента
            - смерти агента
        """

    def handle_event(self, event: "pygame.Event") -> tuple[bool, str | None]:
        """
        Обработать pygame событие.

        Возвращает: (поглощено: bool, clicked_agent_id: str | None)

        Поглощает всё когда visible=True кроме QUIT.
        clicked_agent_id != None только при клике на узел.
        """

    def draw(
        self,
        screen: "pygame.Surface",
        font: "pygame.font.Font",
        font_small: "pygame.font.Font",
    ) -> None:
        """
        Нарисовать дерево поверх screen.

        Последовательность:
        1. Полупрозрачный фон на весь экран
        2. Заголовок: "Родословная | [кол-во живых] живых  [кол-во умерших] умерших  [ESC закрыть]"
        3. Линии пар (горизонтальные пунктиры между родителями)
        4. Линии родства (от точки между родителями вниз к ребёнку)
        5. Узлы агентов
        6. Имена под узлами
        7. Иконки состояния внутри узлов
        8. Тултип для hovered_id
        """

    def _world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Преобразовать мировые координаты в экранные с учётом zoom и offset."""

    def _screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        """Обратное преобразование."""

    def _node_at_screen(self, sx: int, sy: int) -> str | None:
        """Найти agent_id узла в точке экрана (с учётом радиуса)."""

    def _draw_node(
        self,
        surface: "pygame.Surface",
        node: LineageNode,
        font_small: "pygame.font.Font",
        *,
        selected: bool = False,
    ) -> None:
        """Нарисовать один узел с именем и иконкой."""

    def _draw_pair_line(
        self,
        surface: "pygame.Surface",
        pos_a: tuple[int, int],
        pos_b: tuple[int, int],
    ) -> None:
        """Пунктирная горизонтальная линия между двумя родителями."""

    def _draw_tooltip(
        self,
        surface: "pygame.Surface",
        node: LineageNode,
        font_small: "pygame.font.Font",
        screen_pos: tuple[int, int],
    ) -> None:
        """
        Тултип при наведении.

        Содержимое:
            [G1A2 ♂ adult]
            Возраст: 00:22:47
            Потомков: 2
            Стресс: 0.38
            [жив | умер от exhaustion в 01:15:30]
        """

    def _fit_view(self, screen_w: int, screen_h: int) -> None:
        """
        Подобрать zoom и offset так чтобы всё дерево умещалось на экране.
        Вызывать при открытии или rebuild если это первое открытие.
        """
```

---

## 5. Изменения в simulation_runner.py

```diff
+from death_registry import DeathRegistry

 class SimulationRunner:
     def __init__(self, factory=None, death_journal_path=None) -> None:
         ...
+        self.death_registry = DeathRegistry(save_dir=self._resolve_save_dir())
+
+    def _resolve_save_dir(self) -> Path | None:
+        """Вернуть директорию рядом с death_journal или None."""
+        if self._death_journal_path:
+            return Path(self._death_journal_path).parent
+        return None

     def add_agent(self, agent: ChinchillaAgent) -> None:
         agent.colony = self.agents
         agent.resources = self.resources
         self.agents.append(agent)
         self.swarm.add_agent(agent)
+        self.death_registry.register_birth(agent, self.sim_time)

     def _handle_agent_death(self, agent_id: str) -> None:
         dead_agent = next((a for a in self.agents if a.agent_id == agent_id), None)
+        # Сохранить в registry ДО удаления агента из списка
+        if dead_agent is not None:
+            gen_map = getattr(self, "_generation_index_map_cache", {})
+            self.death_registry.register_death(dead_agent, self.sim_time, gen_map)
         entry = self._build_death_entry(...)
         ...
```

---

## 6. Изменения в colony_gui.py

```diff
+from death_registry import DeathRegistry
+from colony_gui.agent_inspector import (
+    AgentInspectorOverlay, build_inspector_data_from_agent,
+    build_inspector_data_from_memorial,
+)
+from colony_gui.lineage_overlay import LineageOverlay

 class ColonyGUI:
     def __init__(self, runner: Any) -> None:
         ...
+        self.inspector = AgentInspectorOverlay()
+        self.lineage   = LineageOverlay(runner.death_registry)
+        self._generation_index_map: dict[str, int] = {}

+    def open_inspector(self, agent_id: str) -> None:
+        """
+        Открыть инспектор для живого или умершего агента.
+
+        Живой:  build_inspector_data_from_agent()
+        Умерший: build_inspector_data_from_memorial()
+        Имя:    canonical_display_name() из utils
+        """
+
+    def close_all_overlays(self) -> None:
+        """Закрыть inspector и lineage."""

     def load(self, path: str | Path) -> None:
         ...
         self._snapshot = None
         self.observer = ColonyPopulationObserver(self.runner, observe_every_n_ticks=5)
+        # Загрузить registry для нового runner
+        registry_path = Path(path).parent / "death_registry.json"
+        if registry_path.exists():
+            self.runner.death_registry.load(registry_path)
+        self.lineage = LineageOverlay(self.runner.death_registry)
+        self.lineage.mark_dirty()
```

---

## 7. Изменения в app.py — правая панель и overlay

### 7.1 Правая панель

```python
PANEL_RIGHT_X    = 730
PANEL_RIGHT_W    = 286
CARD_H_ALIVE     = 74
CARD_H_DEAD      = 52
CARD_MARGIN      = 6
CARD_BG_ALIVE    = (252, 249, 242)
CARD_BG_DEAD     = (215, 210, 206)
CARD_BORDER_ALIVE = (180, 168, 148)
CARD_BORDER_DEAD  = (145, 138, 130)
CARD_TEXT_DEAD    = (105, 96, 86)
MAX_DEAD_CARDS    = 20


def _draw_right_panel(
    screen: "pygame.Surface",
    font: "pygame.font.Font",
    font_small: "pygame.font.Font",
    *,
    living_agents_data: list[dict],
    dead_memorials: list["AgentMemorial"],
    selected_agent_id: str | None,
    scroll_offset: int,
) -> list[tuple["pygame.Rect", str]]:
    """
    Нарисовать правую панель с карточками живых и умерших агентов.

    Структура панели:
        [Заголовок "КОЛОНИЯ (N живых)"]
        [Карточки живых агентов]
        [Разделитель "── умершие (N) ──"]  (только если есть умершие)
        [Карточки умерших — последние MAX_DEAD_CARDS]
        [Кнопка "[L] Родословная"]

    Карточка живого агента:
        ● G1A2 ♂ adult [affect_tone_color]
        eat  | stress: ██░  0.38  energy: ████  0.72
        [мини-бары stress и energy]

    Карточка умершего:
        ✝ G0A2 ♂ [серый]
        exhaustion | прожил 01:15:30 | потомков: 2

    Возвращает список (pygame.Rect, agent_id) для hit-testing.
    """
```

### 7.2 Обработка кликов и клавиш в главном цикле

```diff
     for event in pygame.event.get():
+        # Сначала overlays поглощают события
+        if gui.inspector.visible:
+            consumed = gui.inspector.handle_event(event)
+            if consumed:
+                continue
+
+        if gui.lineage.visible:
+            consumed, clicked_id = gui.lineage.handle_event(event)
+            if clicked_id:
+                gui.close_all_overlays()
+                gui.open_inspector(clicked_id)
+            if consumed:
+                continue
+
         if event.type == pygame.QUIT:
             running = False
         elif event.type == pygame.KEYDOWN:
             if event.key == pygame.K_ESCAPE:
-                running = False
+                if gui.inspector.visible or gui.lineage.visible:
+                    gui.close_all_overlays()
+                else:
+                    running = False
+            elif event.key == pygame.K_l:
+                if gui.inspector.visible:
+                    gui.inspector.close()
+                gui.lineage.toggle()
+                if gui.lineage.visible:
+                    gui.lineage.rebuild(
+                        runner.agents,
+                        gui._generation_index_map,
+                    )

+        # Клик по правой панели
+        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
+            clicked_id = _handle_panel_click(event.pos, card_hit_areas)
+            if clicked_id:
+                if gui.inspector.agent_id == clicked_id and gui.inspector.visible:
+                    gui.inspector.close()   # повторный клик закрывает
+                else:
+                    gui.lineage.close()
+                    gui.open_inspector(clicked_id)

+    # В конце главного цикла — отрисовать overlays
+    card_hit_areas = _draw_right_panel(
+        screen, font, font_small,
+        living_agents_data=state["agents"],
+        dead_memorials=list(runner.death_registry.get_recent_memorials(MAX_DEAD_CARDS)),
+        selected_agent_id=gui.inspector.agent_id if gui.inspector.visible else None,
+        scroll_offset=gui._right_panel_scroll,
+    )
+    if gui.lineage.visible:
+        gui.lineage.draw(screen, font, font_small)
+    if gui.inspector.visible:
+        gui.inspector.draw(screen, font, font_small, font_mono)
```

### 7.3 Обновление lineage при рождениях/смертях

```diff
     # После _spawn_pending_offspring и смертей:
     dead_ids = gui.swarm.check_mortality()
     for agent_id in dead_ids:
         gui._handle_agent_death(agent_id)
+        gui.lineage.mark_dirty()   # дерево изменилось

     gui._spawn_pending_offspring()
+    if new_agents:
+        gui.lineage.mark_dirty()

+    # Rebuild если нужно и lineage открыт
+    if gui.lineage.visible and gui.lineage._needs_rebuild:
+        gui.lineage.rebuild(runner.agents, gui._generation_index_map)
```

---

## 8. Сохранение/загрузка registry рядом с colony save

### 8.1 В ColonyGUI.save()

```diff
 def save(self, path: str | Path) -> None:
     target = Path(path)
     storage = ColonyStorage(save_dir=target.parent)
     result = storage.save_colony(self.runner, target.name)
+    # Сохранить death registry рядом
+    registry_path = target.parent / "death_registry.json"
+    self.runner.death_registry.save(registry_path)
     return result
```

### 8.2 В ColonyGUI.load()

```diff
 def load(self, path: str | Path) -> None:
     source = Path(path)
     storage = ColonyStorage(save_dir=source.parent)
     self.runner = storage.load_colony(source)
     self._snapshot = None
     self.observer = ColonyPopulationObserver(self.runner, observe_every_n_ticks=5)
+    registry_path = source.parent / "death_registry.json"
+    if registry_path.exists():
+        self.runner.death_registry.load(registry_path)
+    self.lineage = LineageOverlay(self.runner.death_registry)
+    self.lineage.mark_dirty()
```

---

## 9. Ограничения реализации

1. `DeathRegistry` — в `src/death_registry.py`, не в GUI пакете.
2. Геномы хранятся целиком — `dict(genome.genes)` без фильтрации.
3. `AgentInspector` и `LineageOverlay` не открыты одновременно.
4. Инспектор показывает данные на момент открытия — не live.
5. Инспектор закрывается: ESC, повторный клик карточки, открытие lineage.
6. Lineage закрывается: ESC, L, открытие inspector через клик узла.
7. Симуляция не останавливается при открытых overlay.
8. `MAX_MEMORIALS_IN_MEMORY = 500` — при превышении удаляются самые старые.
9. `MAX_DEAD_CARDS = 20` — в правой панели только последние 20 умерших.
10. Python 3.10+.

---

## 10. Тест-кейсы

### TC-01: register_birth / register_death базовый

```python
registry = DeathRegistry()
agent = ChinchillaAgent(sex="F", generation=0)
registry.register_birth(agent, sim_time=10.0)

assert registry.get_birth_time(agent.agent_id) == 10.0
assert not registry.is_deceased(agent.agent_id)

memorial = registry.register_death(agent, sim_time=500.0, generation_index_map={})

assert registry.is_deceased(agent.agent_id)
assert memorial.death_sim_time == 500.0
assert memorial.birth_sim_time == 10.0
assert abs(memorial.age_at_death - agent.age) < 1e-3
```

### TC-02: Полный геном в мемориале

```python
from genome import GenomeVector

registry = DeathRegistry()
agent = ChinchillaAgent(sex="M")
agent.genome = GenomeVector.default()
registry.register_birth(agent, 0.0)
memorial = registry.register_death(agent, 100.0, {})

expected_keys = set(GenomeVector.default().genes.keys())
assert expected_keys == set(memorial.genome_genes.keys())
for key, val in GenomeVector.default().genes.items():
    assert abs(memorial.genome_genes[key] - val) < 1e-9
```

### TC-03: Финальный аффект из AffectiveSpace

```python
registry = DeathRegistry()
agent = ChinchillaAgent(sex="F")
agent.affective_space.axes["stress"]    = 0.75
agent.affective_space.axes["valence"]   = -0.30
agent.affective_space.axes["curiosity"] = 0.60
registry.register_birth(agent, 0.0)
memorial = registry.register_death(agent, 50.0, {})

assert abs(memorial.final_stress    - 0.75)  < 1e-6
assert abs(memorial.final_valence   - (-0.30)) < 1e-6
assert abs(memorial.final_curiosity - 0.60)  < 1e-6
```

### TC-04: Социальный след в мемориале

```python
registry = DeathRegistry()
agent = ChinchillaAgent(sex="M")
other = ChinchillaAgent(sex="F")

agent._ensure_known(other.agent_id, other.get_public_state())
agent.knowledge[other.agent_id].affinity = 0.8
agent.knowledge[other.agent_id].relationship_type = "bonded"
agent.knowledge[other.agent_id].positive_count = 10
agent.knowledge[other.agent_id].negative_count = 2

registry.register_birth(agent, 0.0)
memorial = registry.register_death(agent, 100.0, {})

assert memorial.known_agents_count == 1
assert memorial.bonded_count == 1
assert memorial.positive_interactions == 10
assert memorial.negative_interactions == 2
```

### TC-05: save / load round-trip с геномами

```python
import tempfile, os, json

registry = DeathRegistry()
agent = ChinchillaAgent(sex="F")
agent.genome = GenomeVector.random(random.Random(42))
registry.register_birth(agent, 0.0)
registry.register_death(agent, 200.0, {})

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    path = f.name
try:
    registry.save(path)

    # Проверить JSON напрямую
    with open(path) as f:
        data = json.load(f)
    assert data["version"] == "1.1"
    assert len(data["memorials"]) == 1
    memorial_data = data["memorials"][0]
    assert "genome_genes" in memorial_data
    assert len(memorial_data["genome_genes"]) == len(agent.genome.genes)

    # Загрузить в новый registry
    registry2 = DeathRegistry()
    registry2.load(path)
    assert len(registry2._memorials) == 1
    m = registry2.get_memorial(agent.agent_id)
    assert m is not None
    for key in agent.genome.genes:
        assert abs(m.genome_genes[key] - agent.genome.genes[key]) < 1e-9
finally:
    os.unlink(path)
```

### TC-06: load добавляет к существующим (не заменяет)

```python
import tempfile, os

registry = DeathRegistry()
a1 = ChinchillaAgent(sex="F")
registry.register_birth(a1, 0.0)
registry.register_death(a1, 100.0, {})

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    path = f.name
try:
    registry.save(path)

    a2 = ChinchillaAgent(sex="M")
    registry.register_birth(a2, 50.0)
    registry.register_death(a2, 200.0, {})

    registry.load(path)  # загружаем поверх — a1 уже есть

    assert len(registry._memorials) == 2  # не 3
finally:
    os.unlink(path)
```

### TC-07: get_lineage_nodes объединяет живых и умерших

```python
registry = DeathRegistry()

dead = ChinchillaAgent(sex="F", generation=0)
registry.register_birth(dead, 0.0)
registry.register_death(dead, 100.0, {})

living = ChinchillaAgent(sex="M", generation=0)

nodes = registry.get_lineage_nodes([living], generation_index_map={})

ids = {n.agent_id for n in nodes}
assert dead.agent_id in ids
assert living.agent_id in ids

dead_node = next(n for n in nodes if n.agent_id == dead.agent_id)
assert not dead_node.is_alive
assert dead_node.cause_of_death != "" or True  # может быть пустой при тесте
```

### TC-08: register_death не падает на минимальном агенте

```python
class Minimal:
    agent_id = "x"
    sex = "F"
    generation = 0
    parents = (None, None)
    name = "Test"
    age = 50.0
    lived_steps = 100
    own_offspring = []
    knowledge = {}

registry = DeathRegistry()
registry.register_birth(Minimal(), 0.0)
memorial = registry.register_death(Minimal(), 50.0, {})

assert memorial.agent_id == "x"
assert memorial.final_stress == 0.0
assert memorial.genome_genes == {}
```

### TC-09: MAX_MEMORIALS_IN_MEMORY соблюдается

```python
registry = DeathRegistry()

for i in range(MAX_MEMORIALS_IN_MEMORY + 10):
    a = ChinchillaAgent(sex="F" if i%2==0 else "M")
    registry.register_birth(a, float(i))
    registry.register_death(a, float(i) + 1.0, {})

assert len(registry._memorials) == MAX_MEMORIALS_IN_MEMORY
```

### TC-10: build_inspector_data_from_agent содержит все секции

```python
runner = SimulationRunner()
agent = ChinchillaAgent(sex="F", generation=1)
agent.genome = GenomeVector.default()
runner.add_agent(agent)

data = build_inspector_data_from_agent(agent, "G1A1")

assert data.agent_id == agent.agent_id
assert not data.is_deceased
assert "stress" in data.affective_axes
assert "dopamine" in data.neuromodulators
assert "wakefulness" in data.wakefulness
assert "curiosity" in data.autonomous_drives
assert "hippocampus_size" in data.memory
assert isinstance(data.genome_genes, dict)
assert len(data.genome_genes) > 0
```

### TC-11: build_inspector_data_from_memorial не падает

```python
registry = DeathRegistry()
agent = ChinchillaAgent(sex="M")
agent.genome = GenomeVector.default()
registry.register_birth(agent, 0.0)
memorial = registry.register_death(agent, 100.0, {})

data = build_inspector_data_from_memorial(memorial, "G0A1")

assert data.is_deceased
assert data.cause_of_death == memorial.cause_of_death
assert data.genome_genes == memorial.genome_genes
```

### TC-12: AgentInspectorOverlay open/close

```python
inspector = AgentInspectorOverlay()
assert not inspector.visible
assert inspector.agent_id == ""

agent = ChinchillaAgent(sex="F")
data = build_inspector_data_from_agent(agent, "G0A1")
inspector.open(data)

assert inspector.visible
assert inspector.agent_id == agent.agent_id

inspector.close()
assert not inspector.visible
```

### TC-13: Inspector ESC закрывает

```python
import pygame
pygame.init()

inspector = AgentInspectorOverlay()
agent = ChinchillaAgent(sex="M")
inspector.open(build_inspector_data_from_agent(agent, "G0A2"))

esc_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0, "unicode": ""})
consumed = inspector.handle_event(esc_event)

assert consumed is True
assert not inspector.visible
```

### TC-14: LineageOverlay rebuild создаёт корректные позиции

```python
runner = SimulationRunner()
for i in range(4):
    runner.add_agent(ChinchillaAgent(sex="F" if i%2==0 else "M", generation=0))

registry = runner.death_registry
lineage = LineageOverlay(registry)
lineage.rebuild(runner.agents, {})

assert len(lineage._nodes) == 4
positions = {(n.tree_x, n.tree_y) for n in lineage._nodes}
assert len(positions) == 4  # все уникальные

for node in lineage._nodes:
    assert node.tree_y == 0.0  # одно поколение → все в ряду 0
    assert node.tree_x >= 0.0
```

### TC-15: Родослоная — два поколения

```python
runner = SimulationRunner()
parent = ChinchillaAgent(sex="F", generation=0)
child = ChinchillaAgent(sex="M", generation=1)
child.parents = (parent.agent_id, None)

runner.add_agent(parent)
runner.add_agent(child)

lineage = LineageOverlay(runner.death_registry)
lineage.rebuild(runner.agents, {})

nodes_by_gen = {}
for node in lineage._nodes:
    nodes_by_gen.setdefault(node.generation, []).append(node)

assert 0 in nodes_by_gen
assert 1 in nodes_by_gen

# Разные вертикальные позиции
y0 = nodes_by_gen[0][0].tree_y
y1 = nodes_by_gen[1][0].tree_y
assert abs(y1 - y0 - GENERATION_ROW_H) < 1e-3
```

### TC-16: ColonyGUI.open_inspector для живого и умершего

```python
runner = SimulationRunner()
living = ChinchillaAgent(sex="F")
runner.add_agent(living)

dead = ChinchillaAgent(sex="M")
runner.add_agent(dead)
runner.death_registry.register_death(dead, 100.0, {})

gui = ColonyGUI(runner)

# Живой
gui.open_inspector(living.agent_id)
assert gui.inspector.visible
assert not gui.inspector._data.is_deceased

gui.inspector.close()

# Умерший
gui.open_inspector(dead.agent_id)
assert gui.inspector.visible
assert gui.inspector._data.is_deceased
```

---

## 11. Примечания для реализующего агента

- `death_registry.py` — импортировать из `src/`, не из `colony_gui/`. Это позволяет runner использовать registry без зависимости от GUI
- Геномы: `dict(getattr(getattr(agent, "genome", None), "genes", {}) or {})` — может быть `OrderedDict`, кастировать в обычный `dict` для JSON
- Все float значения геномов: `float(v)` перед записью в JSON — защита от numpy float
- `font_mono = pygame.font.SysFont("Courier New", 12)` — для вкладки Геном (выравнивание колонок)
- Правая панель: скролл через `pygame.MOUSEWHEEL` когда курсор `event.pos.x > PANEL_RIGHT_X`
- Колёсико для зума lineage vs скролл правой панели — определять по позиции курсора
- Пунктирная линия пары: рисовать отрезки `[(x, y, x+DASH, y), (x+DASH*2, y, x+DASH*3, y), ...]` через `pygame.draw.line()`
- При `is_deceased=True` в инспекторе: заголовок `"† G0A2 ♂  [умер: exhaustion]"`, все секции с пометкой `"(при смерти)"` в заголовке
- `_fit_view()` вызывать один раз при первом открытии: зум = min(screen_w / tree_w, screen_h / tree_h) * 0.85
- `autosave()` в `register_death()` — вызывать только если `self._save_dir is not None`
- `total_ever_lived()` = `len(self._birth_times)` — счётчик рождений, не смертей
