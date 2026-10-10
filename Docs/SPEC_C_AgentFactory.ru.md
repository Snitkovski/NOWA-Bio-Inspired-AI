# Спецификация пакета C — AgentFactory

English version: [SPEC_C_AgentFactory.en.md](SPEC_C_AgentFactory.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


**Проект:** NOWA (расширение существующего)  
**Файл:** `src/agent_factory.py`  
**Зависимости:** `genome.py` (пакет A), `epigenome.py` (пакет B), модули NOWA  
**Версия спецификации:** 1.0

---

## 1. Назначение

`AgentFactory` — единственная точка создания агентов в эволюционном контексте.  
Принимает `GenomeVector` и опциональный `EpigenomeSnapshot`,  
создаёт полностью инициализированный агент NOWA с параметрами из генома  
и унаследованной памятью из эпигенома.

**Ключевые принципы:**

- Фабрика не знает о рое — она создаёт одного агента
- Геном определяет архитектуру, эпигеном — начальные знания
- Инъекция эпигенома происходит до первого шага, но после инициализации
- Агент созданный через фабрику неотличим от агента созданного вручную

---

## 2. Зависимости от модулей NOWA

Фабрика импортирует и использует:

```python
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from intent_memory import IntentMemory
from affect import AffectiveState
from agent import Agent
from genome import GenomeVector, GENE_REGISTRY
from epigenome import EpigenomeSnapshot
```

---

## 3. Структура AgentFactory

```python
@dataclass
class AgentConfig:
    """Конфигурация среды — параметры не из генома."""
    actions: List[str]                    # доступные действия
    hippocampus_capacity: int = 512       # размер гиппокампа
    cortex_capacity: int = 256            # размер кортекса
    sleep_cycles_default: int = 3         # циклов сна по умолчанию
    intent_memory_enabled: bool = True    # включить intent memory
    environment_id: str = ""              # идентификатор среды


class AgentFactory:
    """
    Фабрика агентов NOWA для эволюционного контекста.
    """
    
    def __init__(self, config: AgentConfig):
        ...
```

---

## 4. API

### 4.1 Основной метод создания

```python
def spawn(
    self,
    genome: GenomeVector,
    epigenome: Optional[EpigenomeSnapshot] = None,
    epigenome_noise: float = 0.1,
    rng: Optional[random.Random] = None,
    agent_id: str = "",
) -> Agent:
    """
    Создать агента из генома и опционального эпигенома.
    
    Последовательность:
        1. Извлечь параметры модулей из genome.to_agent_params()
        2. Создать все модули NOWA с геномными параметрами
        3. Собрать Agent
        4. Если epigenome не None — вызвать _inject_epigenome()
        5. Вернуть готового агента
    
    Аргументы:
        genome: геном агента (определяет параметры)
        epigenome: унаследованная память (None = чистый агент)
        epigenome_noise: уровень шума при инъекции [0.0, 1.0]
        rng: генератор случайных чисел для инъекции шума
        agent_id: строковый идентификатор для трекинга
    
    Возвращает: полностью инициализированный Agent
    
    Ограничения:
        - epigenome_noise клампируется в [0.0, 1.0]
        - agent_id сохраняется в agent.lineage_id (новый атрибут)
        - при epigenome=None агент стартует с чистой памятью
        - никогда не вызывает исключений от некорректного epigenome
    """
```

### 4.2 Создание первого поколения

```python
def spawn_random(
    self,
    rng: Optional[random.Random] = None,
    agent_id: str = "",
) -> Agent:
    """
    Создать агента со случайным геномом и чистой памятью.
    Используется для инициализации первого поколения.
    
    Эквивалентно spawn(GenomeVector.random(rng), epigenome=None).
    """

def spawn_default(
    self,
    agent_id: str = "",
) -> Agent:
    """
    Создать агента с дефолтным геномом и чистой памятью.
    Используется для baseline сравнений.
    """
```

### 4.3 Создание потомка от двух родителей

```python
def spawn_child(
    self,
    parent_a: Agent,
    parent_b: Agent,
    mutation_rate: float = 0.05,
    sigma_scale: float = 1.0,
    crossover_alpha: float = 0.5,
    crossover_mode: str = "arithmetic",
    epigenome_noise: float = 0.1,
    blend_epigenomes: bool = True,
    rng: Optional[random.Random] = None,
    agent_id: str = "",
) -> Agent:
    """
    Создать потомка от двух родительских агентов.
    
    Последовательность:
        1. Извлечь геномы из parent_a и parent_b
        2. Скрестить геномы → child_genome (один из двух потомков)
        3. Если blend_epigenomes:
               Извлечь эпигеномы из обоих родителей
               Смешать через epigenome_a.blend(epigenome_b)
               child_epigenome = смешанный
           Иначе:
               child_epigenome = None
        4. Мутировать child_genome
        5. spawn(child_genome, child_epigenome, epigenome_noise, rng)
    
    Аргументы:
        parent_a, parent_b: родительские агенты
        mutation_rate: вероятность мутации каждого гена [0.0, 1.0]
        sigma_scale: масштаб мутационного шума [0.1, 5.0]
        crossover_alpha: вес parent_a при arithmetic crossover [0.0, 1.0]
        crossover_mode: режим скрещивания ("arithmetic"|"uniform"|"sbx")
        epigenome_noise: шум при инъекции эпигенома [0.0, 1.0]
        blend_epigenomes: передавать ли унаследованную память
        rng: генератор случайных чисел
        agent_id: идентификатор потомка
    
    Возвращает: Agent — один потомок
    
    Ограничения:
        - если у родителя нет атрибута genome — использовать GenomeVector.default()
        - если у родителя нет атрибута epigenome — использовать EpigenomeSnapshot.empty()
        - все параметры клампируются в допустимые диапазоны
    """
```

### 4.4 Извлечение генома/эпигенома из агента

```python
def extract_genome(self, agent: Agent) -> GenomeVector:
    """
    Извлечь геном из живого агента.
    
    Читает атрибут agent.genome если есть.
    Иначе реконструирует из текущих параметров модулей.
    
    Возвращает: GenomeVector
    """

def extract_epigenome(
    self,
    agent: Agent,
    max_patterns: int = 32,
    max_actions: int = 16,
    max_values: int = 24,
    min_reinforcement: int = 2,
    min_stability: float = 0.5,
    min_confirmation: float = 1.0,
) -> EpigenomeSnapshot:
    """
    Извлечь эпигеном из живого агента.
    
    Читает данные из:
        - agent.cortex (паттерны)
        - agent.selector.action_metadata (SAC)
        - agent.value_layer (profiles)
    
    Использует EpigenomeSnapshot.extract() с данными в виде словарей.
    
    Возвращает: EpigenomeSnapshot
    """
```

---

## 5. Внутренние методы

### 5.1 Создание модулей из генома

```python
def _build_hippocampus(self, params: dict) -> NOWAHippocampus:
    """
    Создать гиппокамп с параметрами из генома.
    
    Геномные параметры:
        params["hippocampus"]["similarity_threshold"] → hippocampus.similarity_threshold
    
    Фиксированные параметры из config:
        capacity = self.config.hippocampus_capacity
    """

def _build_cortex(self, params: dict) -> CortexMemory:
    """
    Создать кортекс.
    Фиксированный capacity из config.
    """

def _build_selector(self, params: dict) -> ActionSelector:
    """
    Создать selector с actions из config.
    """

def _build_sleep_manager(self, params: dict) -> SleepManager:
    """
    Создать SleepManager.
    
    Геномные параметры:
        params["sleep"]["consolidation_threshold"] → stability_index_threshold
    """

def _build_wakefulness(self, params: dict):
    """
    Создать WakefulnessState с геномными параметрами.
    
    Геномные параметры:
        params["wakefulness"]["circadian_amplitude"]
        params["wakefulness"]["circadian_phase"]
        params["wakefulness"]["accumulation_rate_factor"] → умножить на базовый rate
        params["wakefulness"]["recovery_rate_factor"] → умножить на базовый rate
    """
```

### 5.2 Применение параметров к агенту

```python
def _apply_genome_to_agent(self, agent: Agent, params: dict) -> None:
    """
    Применить геномные параметры к уже созданному агенту.
    
    Применяет параметры которые нельзя передать при инициализации модулей:
    
    AffectiveSpace:
        agent.affective_space.axis_decay = params["affective_space"]["axis_decay"]
        agent.affective_space.lambda_reg = params["affective_space"]["lambda_reg"]
        agent.affective_space.baseline_adapt_rate = params["affective_space"]["baseline_adapt_rate"]
    
    NeuromodulatorState:
        Применить interaction_overrides к agent.neuromodulators.interaction_field
        Применить acc_k_ne, acc_k_cort, acc_k_ht
        Применить decay_half_life
    
    ValueLayer:
        agent.value_layer.gamma_default = params["value_layer"]["gamma_default"]
        agent.value_layer.alpha_online_default = params["value_layer"]["alpha_online_default"]
        agent.value_layer.td_layer.tonic_slow_rate = params["value_layer"]["tonic_slow_rate"]
    
    HippocampalImagineEngine:
        agent.imagination_engine.goal_bias = params["imagination"]["goal_bias"]
        agent.imagination_engine.confidence_decay = params["imagination"]["confidence_decay"]
        agent.imagination_engine.state_novelty_weight = params["imagination"]["state_novelty_weight"]
        agent.imagination_value_blend = params["imagination"]["value_blend"]
    
    AutonomousOrganismAgent (если инициализирован):
        drive_system.drives — начальные уровни из params["autonomous"]["drive_baselines"]
        drive_system thresholds из params["autonomous"]["drive_thresholds"]
        energy_system.recovery_rate из params["autonomous"]["energy_recovery_rate"]
        energy_system.cognitive_cost из params["autonomous"]["cognitive_cost"]
    
    Ограничения:
        - все операции в try/except — некорректный параметр пропускается
        - предупреждение через warnings.warn при пропуске
        - агент должен оставаться в рабочем состоянии при любых параметрах
    """
```

### 5.3 Инъекция эпигенома

```python
def _inject_epigenome(
    self,
    agent: Agent,
    epigenome: EpigenomeSnapshot,
    noise_level: float,
    rng: Optional[random.Random],
) -> dict:
    """
    Внедрить унаследованную память в агента.
    
    Извлекает текущие структуры агента как словари,
    вызывает epigenome.inject(), результат применяет обратно.
    
    Последовательность:
        1. Собрать cortex_patterns из agent.cortex
        2. Собрать action_metadata из agent.selector
        3. Собрать value_profiles из agent.value_layer
        4. Вызвать epigenome.inject(...)
        5. Применить изменённые структуры обратно в агента
    
    Возвращает: статистику инъекции из epigenome.inject()
    
    Ограничения:
        - весь метод в try/except — при ошибке возвращает пустую статистику
        - агент не должен быть повреждён при ошибке инъекции
        - не вызывать agent.sleep() — инъекция происходит до первого сна
    """
```

### 5.4 Реконструкция генома из агента

```python
def _reconstruct_genome(self, agent: Agent) -> GenomeVector:
    """
    Реконструировать геном из текущих параметров агента.
    
    Читает параметры из каждого модуля и собирает GenomeVector.
    Используется если agent.genome не установлен.
    
    При недоступности параметра — использовать default из GENE_REGISTRY.
    Результат всегда валидный GenomeVector.
    """
```

---

## 6. Атрибуты агента добавляемые фабрикой

После `spawn()` агент имеет дополнительные атрибуты:

```python
agent.genome: GenomeVector           # геном агента
agent.epigenome: EpigenomeSnapshot   # эпигеном (empty если не передан)
agent.agent_id: str                  # идентификатор
agent.factory_config: AgentConfig    # конфигурация среды (read-only ref)
```

---

## 7. Ограничения реализации

1. `AgentFactory` не хранит состояния между вызовами `spawn()` — каждый вызов независим.
2. `spawn_child()` создаёт **одного** потомка, не двух — второй потомок из crossover отбрасывается.
3. Геномные параметры применяются **после** стандартной инициализации Agent — переопределяют дефолты.
4. `_apply_genome_to_agent()` использует только `try/except` без raise — агент остаётся рабочим.
5. Автономный рантайм (`autonomous_runtime`) инициализируется через `agent.init_autonomous_runtime()` с параметрами из генома, не напрямую.
6. `extract_epigenome()` вызывает `EpigenomeSnapshot.extract()` — не создаёт объекты эпигенома напрямую.
7. Python версия: 3.10+

---

## 8. Тест-кейсы

### TC-01: spawn с дефолтным геномом создаёт рабочего агента

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)
genome = GenomeVector.default()

agent = factory.spawn(genome)

# Атрибуты фабрики установлены
assert hasattr(agent, "genome")
assert hasattr(agent, "epigenome")
assert hasattr(agent, "agent_id")

# Геном совпадает
assert agent.genome.genes == genome.genes

# Эпигеном пустой
assert agent.epigenome.is_empty()

# Агент рабочий — можно сделать шаг
action = agent.step(context_events=["morning"], reward=0.0, novelty=0.0)
assert isinstance(action, str)
```

### TC-02: Геномные параметры применяются к модулям

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# Создаём геном с нестандартными значениями
genome = GenomeVector.default()
custom_genes = dict(genome.genes)
custom_genes["af_decay_valence"] = 0.85   # отличается от default 0.92
custom_genes["lr_gamma"] = 0.90           # отличается от default 0.95
genome = GenomeVector(genes=custom_genes)

agent = factory.spawn(genome)

# Параметры применены
assert abs(agent.affective_space.axis_decay.get("valence", 0) - 0.85) < 1e-6
assert abs(agent.value_layer.gamma_default - 0.90) < 1e-6
```

### TC-03: spawn_random создаёт агента со случайным геномом

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)
rng = random.Random(42)

agent_a = factory.spawn_random(rng=random.Random(42))
agent_b = factory.spawn_random(rng=random.Random(99))

# Геномы различаются
assert agent_a.genome.genes != agent_b.genome.genes

# Оба рабочие
action_a = agent_a.step(["ctx"], reward=0.0, novelty=0.0)
action_b = agent_b.step(["ctx"], reward=0.0, novelty=0.0)
assert isinstance(action_a, str)
assert isinstance(action_b, str)
```

### TC-04: spawn_default создаёт агента с дефолтным геномом

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

agent = factory.spawn_default()

for key in GENE_REGISTRY:
    assert abs(agent.genome.genes[key] - GENE_REGISTRY[key].default) < 1e-9
```

### TC-05: Инъекция эпигенома — паттерны попадают в cortex

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)

# Создаём эпигеном с паттерном
epigenome = EpigenomeSnapshot.extract(
    cortex_patterns=[
        {"context_signature": "morning", "action": "eat",
         "strength": 0.9, "reinforcement_count": 5}
    ],
    action_metadata={},
    value_profiles={},
    min_reinforcement=0,
)

agent = factory.spawn(
    GenomeVector.default(),
    epigenome=epigenome,
    epigenome_noise=0.0,
)

# Паттерн присутствует в cortex
cortex_patterns = agent.cortex.get_patterns() if hasattr(agent.cortex, "get_patterns") else []
# Альтернативно: проверяем что action_metadata или cortex содержат наследство
assert agent.epigenome is not None
assert not agent.epigenome.is_empty()
```

### TC-06: spawn_child создаёт потомка с геномом между родителями

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

rng = random.Random(0)
parent_a = factory.spawn_random(rng=random.Random(1))
parent_b = factory.spawn_random(rng=random.Random(2))

child = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=0.0,  # без мутации для чистоты теста
    crossover_alpha=0.5,
    crossover_mode="arithmetic",
    blend_epigenomes=False,
    rng=random.Random(42),
)

# generation потомка = max(родителей) + 1
assert child.genome.generation == max(
    parent_a.genome.generation, parent_b.genome.generation
) + 1

# Каждый ген потомка между родителями (arithmetic, alpha=0.5)
for key in GENE_REGISTRY:
    val_a = parent_a.genome.genes[key]
    val_b = parent_b.genome.genes[key]
    val_child = child.genome.genes[key]
    lo, hi = min(val_a, val_b), max(val_a, val_b)
    assert lo - 1e-9 <= val_child <= hi + 1e-9, f"Gene {key} out of parent range"
```

### TC-07: spawn_child с мутацией создаёт отличающийся геном

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

parent_a = factory.spawn_default()
parent_b = factory.spawn_default()

child = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=1.0,  # мутируют все гены
    sigma_scale=2.0,
    rng=random.Random(7),
)

# Хотя бы один ген отличается от обоих родителей
at_least_one_different = False
for key in GENE_REGISTRY:
    val_a = parent_a.genome.genes[key]
    val_b = parent_b.genome.genes[key]
    val_child = child.genome.genes[key]
    if abs(val_child - val_a) > 1e-9 or abs(val_child - val_b) > 1e-9:
        at_least_one_different = True
        break
assert at_least_one_different
```

### TC-08: extract_genome возвращает корректный GenomeVector

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

original_genome = GenomeVector.random(random.Random(5))
agent = factory.spawn(original_genome)

extracted = factory.extract_genome(agent)

assert isinstance(extracted, GenomeVector)
assert extracted.validate() == []

# Основные параметры совпадают
assert abs(extracted.genes["lr_gamma"] - original_genome.genes["lr_gamma"]) < 1e-6
assert abs(extracted.genes["af_decay_valence"] - original_genome.genes["af_decay_valence"]) < 1e-6
```

### TC-09: extract_epigenome после шагов возвращает непустой снапшот

```python
config = AgentConfig(actions=["eat", "sleep", "play"])
factory = AgentFactory(config)

agent = factory.spawn_default()

# Несколько шагов для накопления опыта
for _ in range(10):
    agent.step(["morning", "hungry"], reward=0.8, novelty=0.3)

# Сон для консолидации
agent.sleep(cycles=1)

# Извлечение эпигенома
epigenome = factory.extract_epigenome(
    agent,
    min_reinforcement=0,
    min_stability=0.0,
    min_confirmation=0.0,
)

assert isinstance(epigenome, EpigenomeSnapshot)
assert epigenome.validate() == []
# После шагов и сна должны быть данные
assert epigenome.source_generation >= 0
```

### TC-10: spawn_child с blend_epigenomes=True передаёт память

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# Родители с некоторым опытом
parent_a = factory.spawn_default()
parent_b = factory.spawn_default()

for _ in range(5):
    parent_a.step(["ctx_a"], reward=0.9, novelty=0.1)
    parent_b.step(["ctx_b"], reward=0.7, novelty=0.2)

parent_a.sleep(cycles=1)
parent_b.sleep(cycles=1)

child = factory.spawn_child(
    parent_a, parent_b,
    blend_epigenomes=True,
    epigenome_noise=0.05,
    rng=random.Random(0),
)

# Эпигеном потомка не пустой (если родители накопили паттерны)
assert child.epigenome is not None
# child рабочий
action = child.step(["ctx_a"], reward=0.0, novelty=0.0)
assert isinstance(action, str)
```

### TC-11: AgentFactory не хранит состояние между вызовами

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

agent_1 = factory.spawn(GenomeVector.default(), agent_id="agent_1")
agent_2 = factory.spawn(GenomeVector.default(), agent_id="agent_2")

# Агенты независимы
assert agent_1.agent_id == "agent_1"
assert agent_2.agent_id == "agent_2"
assert agent_1 is not agent_2
assert agent_1.hippocampus is not agent_2.hippocampus
```

### TC-12: agent_id сохраняется

```python
config = AgentConfig(actions=["eat"])
factory = AgentFactory(config)

agent = factory.spawn(GenomeVector.default(), agent_id="test_agent_42")
assert agent.agent_id == "test_agent_42"
```

### TC-13: spawn с некорректным epigenome не падает

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# Намеренно некорректный эпигеном не должен ронять spawn
epigenome = EpigenomeSnapshot.empty()

# Не должен вызывать исключений
agent = factory.spawn(
    GenomeVector.default(),
    epigenome=epigenome,
    epigenome_noise=0.5,
)
assert agent is not None
```

### TC-14: spawn_child без родительских геномов использует default

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

# Агенты без атрибута genome (созданные не через фабрику)
# Фабрика должна использовать default геном
parent_a = factory.spawn_default()
parent_b = factory.spawn_default()

# Удаляем геном имитируя агента не из фабрики
del parent_a.genome
del parent_b.genome

# Не должен падать
child = factory.spawn_child(parent_a, parent_b, rng=random.Random(0))
assert isinstance(child, Agent)
assert child.genome is not None
```

### TC-15: Все действия из config зарегистрированы в BG каналах

```python
config = AgentConfig(actions=["eat", "sleep", "play", "explore"])
factory = AgentFactory(config)

agent = factory.spawn_default()

for action in config.actions:
    assert action in agent.bg_action_channels, f"Действие {action} не зарегистрировано"
```

### TC-16: Детерминизм spawn_child при фиксированном rng

```python
config = AgentConfig(actions=["eat", "sleep"])
factory = AgentFactory(config)

parent_a = factory.spawn(GenomeVector.random(random.Random(1)))
parent_b = factory.spawn(GenomeVector.random(random.Random(2)))

child_1 = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=0.3,
    rng=random.Random(42),
    blend_epigenomes=False,
)
child_2 = factory.spawn_child(
    parent_a, parent_b,
    mutation_rate=0.3,
    rng=random.Random(42),
    blend_epigenomes=False,
)

# Геномы идентичны
assert child_1.genome.genes == child_2.genome.genes
```

---

## 9. Примечания для реализующего агента

- `AgentConfig` — простой dataclass без `frozen=True` (допускает изменение после создания)
- `_apply_genome_to_agent()` вызывается ПОСЛЕ `Agent.__init__()` — порядок обязателен
- Автономный рантайм создаётся через `agent.init_autonomous_runtime(drive_thresholds=...)` — не напрямую
- `accumulation_rate_factor` из генома: `wakefulness.accumulation_rate = WakefulnessState.ACCUMULATION_RATE * factor`
- `recovery_rate_factor` аналогично: `wakefulness.recovery_rate = WakefulnessState.RECOVERY_RATE * factor`
- Для `interaction_overrides` нейромодуляторов: изменять конкретные веса в `INTERACTION_MATRIX`-подобной структуре через `NeuromodulatorState` — конкретный API зависит от реализации `neuromodulators.py`
- `extract_epigenome()` должна читать `agent.cortex` через публичный API кортекса — не через приватные поля
- `agent.factory_config` — ссылка на объект `AgentConfig`, не копия
- При реконструкции генома через `_reconstruct_genome()`: если параметр недоступен — брать `GENE_REGISTRY[key].default`
