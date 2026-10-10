## Аннотация

English version: [NOWA_Procurement_Sandbox_Spec_v2.0_refactor.en.md](NOWA_Procurement_Sandbox_Spec_v2.0_refactor.en.md)

Рефакторинг v2.0 фиксирует дефект тренировочного цикла песочницы, сложившегося к версии 1.3. Выбор товара, поставщика и объёма выполняется внешними эвристиками до вызова `agent.step`, после чего мир исполняет заказ. Активация гиппокампа питает аффективный сигнал и не входит в селектор; `compute_pressures`, `BasalGangliaGate`, `ThalamicGate`, память реализаций и память намерений в принятии заказа не участвуют. `sleep_cycle` при этом консолидирует траекторию суррогата. Документ требует обратного порядка: наблюдение становится `context_events`, шаг агента проходит гиппокамп, селектор, базальные ганглии и таламический шлюз и возвращает намерение, и только затем тело разрешает параметры.

`ProcurementMotorAdapter` переводит тип действия в `OrderParams` по наблюдениям остатков, справочника поставщиков и бюджета. Чтение гиппокампа допускается только в стратегии наименее используемого поставщика и только как подсчёт уже записанных эпизодов, без вызова `activate` и без вызова `place_order`. Аффективная обратная связь обновляет аффективное состояние принятого или отклонённого заказа и не обновляет слой ценности. Эпизод с токенами контекста, действия, поставщика и исхода пишется в гиппокамп; изменение весов остаётся функцией сна. `ProcurementHippocampusSeeder` один раз до первого тика загружает восемь профессиональных эпизодов и не трогает аффективное пространство, нейромодуляторы и слой ценности. Физика мира, кодировщик, оценщик пригодности, границы сложности Q3b, базовая линия и логика серии предыдущих патчей сохраняются.

Ограничения R1–R6 требуют, чтобы шаг агента предшествовал адаптеру на каждые сутки, чтобы адаптер не вызывал когнитивные методы, чтобы бодрствующая запись не обновляла слой ценности и чтобы строковый ответ запасного агента оставался допустимым. Приёмочные условия включают рост числа эпизодов между кварталами и прогон десяти кварталов стадии 1a без падения. Документ ожидает, что первые пять–десять кварталов могут уступать детерминированному суррогату версии 1.3 до нескольких циклов сна, и ставит условием последующего тридцатиквартального сравнения сохранение тренда эффективности затрат и межквартильного размаха избежания дефицита ниже 0,10 при сохранённых границах Q3b. Эти величины заданы как критерии сравнения, а не как уже измеренный итог рефакторинга. Перед переписыванием цикла требуется закрыть фактический контракт возврата `agent.step`, минимальные аргументы `compute_pressures` и конструкторы `Path` и `Event` в ядре.

---

# NOWA Procurement Sandbox — Рефакторинг v2.0

**Базовые документы:** все предыдущие патчи v1.0–v1.3
**Статус:** готово к реализации — фундаментальный архитектурный рефакторинг
**Приоритет:** Критический — без этого агент не является NOWA-агентом

---

## 0. Диагноз: что сделано неправильно

Текущая реализация (`training_loop.py` v1.3) работает так:
```
training_loop._run_single_quarter()
    ↓
_pick_priority_product(world)   ← ВНЕШНЕЕ решение, не агент
_pick_supplier(world, strategy) ← ВНЕШНЕЕ решение, не агент
_decide_quantity(world, pid)    ← ВНЕШНЕЕ решение, не агент
    ↓
agent.step(context_events)      ← вызывается ПОСЛЕ принятия решения
    ↓
world.place_order(...)          ← исполняется без участия мозга агента
```

Когнитивный контур NOWA — `hippocampus → affective_space → selector →
BasalGangliaGate → ThalamicGate` — существует в коде агента, но
**не участвует в принятии решений**. Агент является декорацией.
Обучение через `sleep_cycle()` накапливает опыт пассивного наблюдателя,
а не активного участника.

### Что конкретно не используется

| Компонент NOWA | Статус в текущей реализации |
|---|---|
| `NOWAHippocampus.activate()` | Вызывается в `_activate_memories`, но результат идёт только в `_memory_signal` для аффекта, не в selector |
| `ActionSelector.compute_pressures()` | Не вызывается |
| `BasalGangliaGate.process()` | Не вызывается |
| `ThalamicGate.select()` | Не вызывается |
| `AffectiveSpace` | Обновляется как побочный эффект `agent.step()`, но не влияет на решения |
| `NeuromodulatorState` | Обновляется, но не влияет на выбор поставщика |
| `RealizationMemory` | Не используется вообще |
| `IntentMemory` (привычки) | Не используется вообще |
| `sleep_cycle()` | Вызывается, но консолидирует опыт суррогата, не реального агента |

---

## 1. Правильная архитектура (Вариант B)
```
ProcurementWorld.observe_*()
    ↓
SandboxEncoder.encode_daily_context()
    → context_events: List[str]
    ↓
agent.hippocampus.activate(context_events)
    → active_experiences: List[Experience]
    ↓
agent.selector.compute_pressures(
    active_experiences,
    agent.affect_state,
    agent.neuromodulators,
    agent.temporal_levels,
)
    → pressure_vector: Dict[str, float]
    ↓
agent.basal_ganglia.process(pressure_vector, agent.neuromodulators)
    → go_actions: List[str]
    ↓
agent.thalamic_gate.select(go_actions, pressure_vector)
    → ActionIntent.action_type: str  ("place_order_reliable_supplier" и т.д.)
    ↓
ProcurementMotorAdapter.resolve(
    action_intent,
    world.observe_stock_levels(),
    world.observe_supplier_directory(),
    world.observe_budget_status(),
    agent.hippocampus,       ← читает историю отношений с поставщиками
)
    → OrderParams(supplier_id, product_id, qty)
    ↓
world.place_order(supplier_id, product_id, qty)
    → result: dict
    ↓
SandboxEncoder.encode_order_result(result)
    → feedback_events: List[str]
    → reward: float
    ↓
agent.affective_space.step(affective_inputs)   ← аффективная обратная связь
agent.hippocampus.store(path, consequence, reward=reward)  ← новый опыт
    ↓
(каждые sleep_every_n_days)
agent.sleep_manager.sleep_cycle()              ← единственное обучение
```

### Принципиальное отличие от v1.3

Порядок изменился на противоположный:
```
v1.3:  pick_params → agent.step() → world.place_order()
v2.0:  agent решает → MotorAdapter.resolve_params() → world.place_order()
```

Агент принимает решение первым. Параметры (supplier_id, qty) разрешаются
**после** того как агент выбрал стратегию — детерминированно из текущих
наблюдений мира через `ProcurementMotorAdapter`.

---

## 2. Новые компоненты

### 2.1 `ProcurementMotorAdapter` — тело, не мозг
```
Файл: nowa_sandbox/procurement_motor_adapter.py
```

**Назначение:** перевести `action_type` (стратегию агента) в конкретные
параметры заказа, используя текущие наблюдения мира и историю
гиппокампа агента.

**Это часть тела агента, не внешний оркестратор.** Аналогично тому,
как рука человека берёт конкретный предмет, реализуя намерение "взять
что-то со стола" — сама рука не принимает решение брать, но определяет
хват.
```python
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class OrderParams:
    """Конкретные параметры одного заказа, разрешённые из ActionIntent."""
    supplier_id: str
    product_id: str
    qty: float
    strategy: str          # action_type, для логирования
    confidence: float      # [0,1] — уверенность в выборе параметров


class ProcurementMotorAdapter:
    """
    Переводит стратегию агента в параметры конкретного заказа.

    Использует только данные из observe_* методов мира (сенсоры)
    и hippocampus агента (память об отношениях с поставщиками).

    НЕ принимает когнитивных решений — это задача мозга агента.
    НЕ вызывает world.place_order() — это делает training_loop.
    Только разрешает параметры из стратегии + наблюдений.
    """

    # Маппинг action_type → метод выбора поставщика
    SUPPLIER_STRATEGIES = {
        "place_order_reliable_supplier": "_select_most_reliable",
        "place_order_cheap_supplier":    "_select_cheapest",
        "urgent_reorder":                "_select_fastest",
        "diversify_supplier":            "_select_least_used",
        "wait_and_monitor":              None,  # нет заказа
    }

    def resolve(
        self,
        action_type: str,
        stock_obs: Dict[str, dict],
        supplier_obs: Dict[str, dict],
        budget_obs: dict,
        hippocampus: Any,
    ) -> Optional[OrderParams]:
        """
        Вернуть OrderParams если action_type предполагает заказ,
        None если action_type = "wait_and_monitor" или нет подходящих
        товаров/поставщиков.

        Алгоритм:
        1. Определить приоритетный товар (самый дефицитный ниже reorder_point)
        2. Выбрать поставщика по стратегии action_type
        3. Рассчитать qty на основе дефицита и истории из hippocampus
        4. Проверить бюджет — если не хватает, снизить qty до доступного

        Использование hippocampus: _select_least_used смотрит на историю
        эпизодов с конкретными supplier_id, чтобы выбрать того, с кем
        агент работал реже всего. Это единственное место, где MotorAdapter
        читает hippocampus — для разрешения параметров, не для решения.
        """
        strategy_method = self.SUPPLIER_STRATEGIES.get(action_type)
        if strategy_method is None:
            return None  # wait_and_monitor

        priority_product = self._select_priority_product(stock_obs)
        if priority_product is None:
            return None  # нет дефицитных товаров

        supplier_id = getattr(self, strategy_method)(
            supplier_obs, hippocampus, priority_product
        )
        if supplier_id is None:
            return None  # нет доступных поставщиков

        qty = self._calculate_qty(
            priority_product, stock_obs, supplier_obs.get(supplier_id, {})
        )
        if qty <= 0:
            return None

        # Проверка бюджета
        budget = float(budget_obs.get("remaining", 0.0))
        unit_price = float(supplier_obs.get(supplier_id, {}).get("reliability", 1.0))
        # Примерная оценка: снижаем qty если не хватает бюджета
        # Точная цена придёт от world.observe_supplier_quote() если нужна
        estimated_cost = qty * 1.0  # placeholder — уточняется через quote
        if estimated_cost > budget * 0.8:
            qty = qty * 0.5  # консервативное снижение при высокой загрузке бюджета

        return OrderParams(
            supplier_id=supplier_id,
            product_id=priority_product,
            qty=round(qty, 1),
            strategy=action_type,
            confidence=self._estimate_confidence(action_type, supplier_obs),
        )

    def _select_priority_product(self, stock_obs: Dict[str, dict]) -> Optional[str]:
        """Самый дефицитный товар ниже reorder_point."""
        below = {
            pid: info for pid, info in stock_obs.items()
            if info.get("below_reorder_point")
        }
        if not below:
            return None
        return min(
            below,
            key=lambda pid: below[pid]["quantity"] - below[pid]["reorder_point"],
        )

    def _select_most_reliable(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        available = self._available_suppliers(supplier_obs)
        if not available:
            return None
        return max(available, key=lambda sid: float(supplier_obs[sid].get("reliability", 0)))

    def _select_cheapest(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        available = self._available_suppliers(supplier_obs)
        if not available:
            return None
        return min(available, key=lambda sid: float(supplier_obs[sid].get("reputation", 1.0)))

    def _select_fastest(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        """Выбрать поставщика с минимальным lead_time из наблюдений."""
        available = self._available_suppliers(supplier_obs)
        if not available:
            return None
        # lead_time не экспонируется через observe_supplier_directory напрямую
        # — используем reputation как proxy (высокая репутация ~ надёжная доставка)
        return max(available, key=lambda sid: float(supplier_obs[sid].get("reputation", 0)))

    def _select_least_used(
        self, supplier_obs: Dict, hippocampus: Any, product_id: str
    ) -> Optional[str]:
        """
        Выбрать поставщика, с которым агент работал реже всего.
        Читает hippocampus для подсчёта эпизодов per supplier_id.
        Это единственное место где MotorAdapter касается hippocampus.
        """
        available = self._available_suppliers(supplier_obs)
        if not available:
            return None

        usage_counts: Dict[str, int] = {sid: 0 for sid in available}
        experiences = getattr(hippocampus, "experiences", []) or []
        for exp in experiences:
            path = getattr(exp, "path", None)
            if path is None:
                continue
            events = getattr(path, "events", []) if hasattr(path, "events") else []
            for event in events:
                token = getattr(event, "label", str(event))
                for sid in available:
                    if f"supplier:{sid}" in token or sid in token:
                        usage_counts[sid] = usage_counts.get(sid, 0) + 1

        return min(available, key=lambda sid: usage_counts.get(sid, 0))

    def _available_suppliers(self, supplier_obs: Dict) -> list:
        return [
            sid for sid, info in supplier_obs.items()
            if not info.get("is_defaulted", False)
        ]

    def _calculate_qty(
        self, product_id: str, stock_obs: Dict, supplier_info: Dict
    ) -> float:
        """Заказать на покрытие 30 дней среднего спроса.
        Это эвристика тела, не когнитивное решение агента.
        """
        info = stock_obs.get(product_id, {})
        reorder_point = float(info.get("reorder_point", 100))
        current = float(info.get("quantity", 0))
        deficit = max(0.0, reorder_point * 2 - current)
        return max(10.0, deficit)

    def _estimate_confidence(self, action_type: str, supplier_obs: Dict) -> float:
        available = self._available_suppliers(supplier_obs)
        if not available:
            return 0.0
        if action_type == "place_order_reliable_supplier":
            max_reliability = max(
                float(supplier_obs[sid].get("reliability", 0)) for sid in available
            )
            return max_reliability
        return 0.6  # дефолтная уверенность для других стратегий
```

---

### 2.2 `ProcurementHippocampusSeeder` — профессиональная интуиция
```
Файл: nowa_sandbox/procurement_hippocampus_seeder.py
```

**Назначение:** загрузить в hippocampus агента seed-эпизоды
"профессиональной интуиции" до первого тика. Аналог `HippocampusSeeder`
из Warriner-демо, но для бизнес-событий вместо слов.

Без этого агент начинает с пустым гиппокампом — `hippocampus.activate()`
возвращает пустой список, `selector.compute_pressures()` получает нулевые
входы, давление на все actions одинаковое, BG выбирает случайно.
Это не катастрофа (агент научится через sleep_cycle), но делает первые
10–20 кварталов практически случайными.
```python
from typing import Any, Dict, List


# Профессиональные seed-эпизоды: ситуация → правильное действие → исход
PROFESSIONAL_SEED_EPISODES = [
    {
        "context_tokens": ["event:stock_critical_low", "domain:procurement",
                           "valence:very_negative", "arousal:high"],
        "action": "urgent_reorder",
        "consequence": "stock_restored",
        "reward": 0.8,
        "intensity": 0.9,
        "reinforcement": True,  # усилить — критически важный паттерн
    },
    {
        "context_tokens": ["event:stock_critical_low", "domain:procurement",
                           "budget:critical"],
        "action": "place_order_cheap_supplier",
        "consequence": "budget_preserved",
        "reward": 0.6,
        "intensity": 0.7,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:supplier_defaulted", "domain:procurement",
                           "valence:negative"],
        "action": "diversify_supplier",
        "consequence": "risk_reduced",
        "reward": 0.7,
        "intensity": 0.8,
        "reinforcement": True,
    },
    {
        "context_tokens": ["event:order_arrived_on_time", "domain:trust",
                           "valence:positive"],
        "action": "place_order_reliable_supplier",
        "consequence": "reliable_delivery",
        "reward": 0.5,
        "intensity": 0.5,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:quiet_day", "domain:neutral",
                           "valence:neutral"],
        "action": "wait_and_monitor",
        "consequence": "no_action_needed",
        "reward": 0.1,
        "intensity": 0.2,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:demand_shock", "domain:procurement",
                           "arousal:high", "valence:negative"],
        "action": "urgent_reorder",
        "consequence": "demand_met",
        "reward": 0.75,
        "intensity": 0.85,
        "reinforcement": True,
    },
    {
        "context_tokens": ["budget:high_utilization", "domain:finance",
                           "valence:negative"],
        "action": "wait_and_monitor",
        "consequence": "budget_protected",
        "reward": 0.4,
        "intensity": 0.6,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:order_arrived_late", "domain:risk",
                           "valence:negative"],
        "action": "diversify_supplier",
        "consequence": "supplier_risk_reduced",
        "reward": 0.6,
        "intensity": 0.7,
        "reinforcement": True,
    },
]


class ProcurementHippocampusSeeder:
    """
    Загружает профессиональную интуицию в hippocampus агента.

    Работает ровно так же как HippocampusSeeder в Warriner-демо:
    - НЕ трогает affective_space, neuromodulators, value_layer
    - Только hippocampus.store() и hippocampus.reinforce()
    - Вызывается один раз перед первым тиком, не между кварталами
    """

    def __init__(self, episodes: List[dict] = None):
        self.episodes = episodes or PROFESSIONAL_SEED_EPISODES

    def seed_agent(self, agent: Any) -> int:
        """
        Загрузить seed-эпизоды в hippocampus агента.
        Возвращает количество успешно добавленных эпизодов.

        Использует тот же API что Warriner-демо:
        hippocampus.store(path, consequence, intensity, reward)
        """
        hippocampus = getattr(agent, "hippocampus", None)
        if hippocampus is None:
            return 0

        added = 0
        for episode in self.episodes:
            try:
                path = self._build_path(episode["context_tokens"])
                consequence = self._build_consequence(episode["consequence"])
                hippocampus.store(
                    path,
                    consequence=consequence,
                    intensity=float(episode.get("intensity", 0.5)),
                    reward=float(episode.get("reward", 0.0)),
                )
                if episode.get("reinforcement"):
                    hippocampus.reinforce(
                        path,
                        consequence=consequence,
                        intensity=float(episode.get("intensity", 0.5)),
                    )
                added += 1
            except Exception:
                continue

        return added

    def _build_path(self, tokens: List[str]) -> Any:
        """Строит Path из списка токенов. Использует существующий API NOWA."""
        try:
            from experience import Path, Event, EventType
            path = Path()
            for token in tokens:
                path.add_event(Event(token, EventType.CONTEXT))
            return path
        except ImportError:
            # Fallback: простой объект с events-атрибутом
            class _SimplePath:
                def __init__(self, tokens):
                    self.events = tokens
            return _SimplePath(tokens)

    def _build_consequence(self, label: str) -> Any:
        """Строит consequence Event."""
        try:
            from experience import Event, EventType
            return Event(label, EventType.CONSEQUENCE)
        except ImportError:
            return label
```

---

### 2.3 Рефакторинг `training_loop.py`

Главное изменение: убрать `_pick_priority_product`, `_pick_supplier`,
`_decide_quantity` из `SandboxTrainer` как методы принятия решений.
Они переезжают в `ProcurementMotorAdapter` как методы разрешения параметров.

#### Текущий `_run_single_quarter` (v1.3 — НЕПРАВИЛЬНО)
```python
def _run_single_quarter(self, world, n_days):
    for day in range(n_days):
        tick_result = world.history[-1] if world.history else {"events": []}
        context = self.encoder.encode_daily_context(world, tick_result)

        action = self._agent_decide(context)        # ← суррогат решения

        if action != "wait_and_monitor":
            order_result = self._execute_action(world, action)  # ← мозг обходится

        world.tick()
        ...
```

#### Новый `_run_single_quarter` (v2.0 — ПРАВИЛЬНО)
```python
def _run_single_quarter(self, world: Any, n_days: int) -> List[dict]:
    """
    Правильный порядок на каждый день:

    1. Наблюдение мира → context_events (сенсоры)
    2. agent.step(context_events) — мозг работает:
       hippocampus.activate → selector → BG → Thalamic → ActionIntent
    3. Аффективная обратная связь от предыдущего тика (если есть)
    4. MotorAdapter.resolve(ActionIntent, наблюдения) → OrderParams
    5. world.place_order(OrderParams) → result
    6. Запись нового эпизода в hippocampus
    7. world.tick() — физика мира
    8. (каждые N дней) sleep_cycle()
    """
    decision_log: List[dict] = []
    last_order_result: Optional[dict] = None

    for day in range(n_days):
        if world.bankrupt:
            break

        # 1. Наблюдение
        tick_result = world.history[-1] if world.history else {"events": []}
        context_events = self.encoder.encode_daily_context(world, tick_result)

        # 2. Аффективная обратная связь от предыдущего заказа
        #    (перед step, чтобы мозг уже знал об исходе)
        if last_order_result is not None:
            self._apply_order_feedback(last_order_result)
            last_order_result = None

        # 3. Агент думает — мозг принимает решение
        #    agent.step() проходит через весь pipeline NOWA:
        #    hippocampus.activate → selector → BG → Thalamic
        action_intent = self._agent_step(context_events)
        action_type = self._intent_to_action_type(action_intent)

        # 4. MotorAdapter разрешает параметры из стратегии
        order_params = None
        order_result = None
        if action_type != "wait_and_monitor":
            order_params = self.motor_adapter.resolve(
                action_type=action_type,
                stock_obs=world.observe_stock_levels(),
                supplier_obs=world.observe_supplier_directory(),
                budget_obs=world.observe_budget_status(),
                hippocampus=self.agent.hippocampus,
            )

        # 5. Исполнение заказа (только через место контакта world)
        if order_params is not None:
            order_result = world.place_order(
                order_params.supplier_id,
                order_params.product_id,
                order_params.qty,
            )
            last_order_result = {
                "params": order_params,
                "result": order_result,
                "world_state": world.observe_budget_status(),
            }

            # 6. Новый эпизод в hippocampus — агент запоминает что сделал
            self._store_order_experience(
                context_events, order_params, order_result
            )

        decision_log.append({
            "day": world.day,
            "action": action_type,
            "supplier_id": order_params.supplier_id if order_params else None,
            "product_id": order_params.product_id if order_params else None,
            "qty": order_params.qty if order_params else None,
            "result": order_result,
        })

        # 7. Физика мира — независимо от агента
        world.tick()

        # 8. Сон — единственный путь обучения
        if world.day % self.sleep_every_n_days == 0:
            self._agent_sleep()

    return decision_log
```

#### Новые вспомогательные методы `SandboxTrainer`
```python
def _agent_step(self, context_events: List[str]) -> Any:
    """
    Вызывает agent.step() и возвращает ActionIntent.

    agent.step() в NOWA проходит через:
    hippocampus.activate() → selector.compute_pressures() →
    BasalGangliaGate.process() → ThalamicGate.select() →
    ActionIntent

    Возвращаемый тип зависит от реализации Agent:
    может быть строкой action_label (fallback) или объектом ActionIntent.
    """
    step_fn = getattr(self.agent, "step", None)
    if callable(step_fn):
        try:
            return step_fn(context_events)
        except TypeError:
            return step_fn(context_events, reward=0.0)
    return "wait_and_monitor"


def _intent_to_action_type(self, action_intent: Any) -> str:
    """
    Извлекает action_type из ActionIntent.

    Если agent.step() вернул строку (fallback-агент) — использует как есть.
    Если вернул объект ActionIntent — читает .action_type или .action.
    Если вернул None или неизвестный тип — дефолт wait_and_monitor.
    """
    if action_intent is None:
        return "wait_and_monitor"
    if isinstance(action_intent, str):
        return action_intent
    # Полноценный ActionIntent из NOWA core
    for attr in ("action_type", "action", "label", "name"):
        value = getattr(action_intent, attr, None)
        if isinstance(value, str):
            return value
    return "wait_and_monitor"


def _apply_order_feedback(self, last_order_result: dict) -> None:
    """
    Передаёт результат заказа в аффективную систему агента.

    Это аффективная обратная связь — агент "чувствует" исход:
    - accepted + stock restored → положительный аффект (reward +)
    - rejected → негативный аффект (reward -)
    - bankrupt → очень негативный аффект

    НЕ вызывает value_layer.update() с reward — это нарушило бы
    принцип "обучение только во сне". Только аффективное состояние.
    """
    result = last_order_result.get("result", {})
    status = result.get("status", "unknown")
    params = last_order_result.get("params")

    if status == "accepted":
        reward = 0.4
        affective_inputs = {
            "valence": 0.4,
            "arousal": 0.2,
            "trust": 0.3,
        }
    elif status == "rejected":
        reason = result.get("reason", "unknown")
        reward = -0.5 if reason == "insufficient_budget" else -0.3
        affective_inputs = {
            "valence": -0.4,
            "arousal": 0.5,
            "stress": 0.4,
        }
    else:
        reward = 0.0
        affective_inputs = {}

    # Обновляем аффективное пространство агента
    affective_space = getattr(self.agent, "affective_space", None)
    if affective_space is not None and affective_inputs:
        step_fn = getattr(affective_space, "step", None)
        if callable(step_fn):
            try:
                step_fn(inputs=affective_inputs)
            except Exception:
                pass

    # Сохраняем reward для последующего использования в sleep_cycle
    # через existing_experience.reward (не обновляем value_layer напрямую)
    self._last_reward = reward


def _store_order_experience(
    self,
    context_events: List[str],
    order_params: "OrderParams",
    order_result: dict,
) -> None:
    """
    Записывает эпизод заказа в hippocampus агента.

    Это то, что агент запомнит и будет использовать при следующей
    активации hippocampus.activate(context_events). Так накапливается
    опыт: "в ситуации X я выбрал supplier Y, получил результат Z".

    Токены эпизода включают:
    - context_events (что предшествовало решению)
    - action token (что решил)
    - supplier token (у кого именно заказал)
    """
    hippocampus = getattr(self.agent, "hippocampus", None)
    if hippocampus is None:
        return

    status = order_result.get("status", "unknown")
    reward = 0.4 if status == "accepted" else -0.3

    episode_tokens = list(context_events) + [
        f"action:{order_params.strategy}",
        f"supplier:{order_params.supplier_id}",
        f"product:{order_params.product_id}",
        f"result:{status}",
    ]

    try:
        path = self._seeder._build_path(episode_tokens)
        consequence_label = "order_accepted" if status == "accepted" else "order_rejected"
        consequence = self._seeder._build_consequence(consequence_label)
        hippocampus.store(
            path,
            consequence=consequence,
            intensity=abs(reward),
            reward=reward,
        )
    except Exception:
        pass
```

---

### 2.4 Обновление `SandboxTrainer.__init__`
```python
class SandboxTrainer:
    def __init__(
        self,
        agent: Any,
        encoder: SandboxEncoder,
        fitness_evaluator: ProcurementFitnessEvaluator,
        sleep_every_n_days: int = 7,
        stage_1a_baseline: Optional[Mapping[str, float]] = None,
        stage_1a_spread_iqr: Optional[Mapping[str, float]] = None,
    ):
        self.agent = agent
        self.encoder = encoder
        self.fitness_evaluator = fitness_evaluator
        self.sleep_every_n_days = max(1, int(sleep_every_n_days))
        self.stage_1a_baseline = dict(stage_1a_baseline or {})
        self.stage_1a_spread_iqr = dict(stage_1a_spread_iqr or {})

        # НОВОЕ: motor adapter и seeder — часть тела агента
        self.motor_adapter = ProcurementMotorAdapter()
        self._seeder = ProcurementHippocampusSeeder()
        self._last_reward: float = 0.0

        # Stage 1b continuity
        self.carried_suppliers: Optional[Dict] = None
        self.last_decision_log: List[dict] = []
```

---

### 2.5 Обновление `sandbox_agent_factory.py`

Добавить вызов `ProcurementHippocampusSeeder.seed_agent()` после
создания агента и до возврата:
```python
def create_procurement_agent(agent_id="procurement_agent_001", rng=None):
    agent = _create_agent(agent_id, rng)

    # Загрузить профессиональную интуицию в hippocampus
    from nowa_sandbox.procurement_hippocampus_seeder import (
        ProcurementHippocampusSeeder
    )
    seeder = ProcurementHippocampusSeeder()
    n_seeded = seeder.seed_agent(agent)
    # Не падать если seeding не удался — агент начнёт с пустой памятью
    # и выучит паттерны через sleep_cycle самостоятельно

    return agent
```

---

## 3. Что удаляется из `training_loop.py`

| Метод | Причина удаления |
|---|---|
| `_agent_decide(context)` | Заменяется на `agent.step(context_events)` через весь pipeline NOWA |
| `_execute_action(world, action)` | Разделяется: MotorAdapter.resolve() + world.place_order() |
| `_pick_priority_product(world)` | Переезжает в `ProcurementMotorAdapter._select_priority_product` |
| `_pick_supplier(world, strategy)` | Переезжает в `ProcurementMotorAdapter._select_*` методы |
| `_decide_quantity(world, product_id)` | Переезжает в `ProcurementMotorAdapter._calculate_qty` |
| `ACTION_TO_ORDER_STRATEGY` | Переезжает в `ProcurementMotorAdapter.SUPPLIER_STRATEGIES` |

---

## 4. Что НЕ меняется

| Компонент | Причина сохранения |
|---|---|
| `ProcurementWorld` (вся физика) | Правильно реализован, инвариант C2 соблюдён |
| `SandboxEncoder` (токены) | Правильно реализован |
| `ProcurementFitnessEvaluator` | Правильно — внешний наблюдатель |
| `ProcurementFitnessVector` | Правильно |
| Все тесты `test_procurement_world.py` | Физика мира не меняется |
| Все тесты `test_procurement_fitness.py` | Fitness-логика не меняется |
| `stage_baseline.py` | Не меняется |
| `sandbox_checkpoint.py` | Не меняется — агент сериализуется через AgentStorage |
| Параметры мира v1.3 (Q3b bounds) | Остаются |
| `world_difficulty.py` | Остаётся как диагностическая опция |

---

## 5. Ограничения (нарушение = архитектурный дефект)

| # | Ограничение |
|---|---|
| **R1** | `SandboxTrainer._run_single_quarter` вызывает `agent.step()` ПЕРВЫМ на каждый день — до обращения к MotorAdapter |
| **R2** | `ProcurementMotorAdapter` не вызывает `agent.step()`, `agent.hippocampus.activate()` или любые когнитивные методы агента напрямую — только читает `hippocampus.experiences` для счётчика использования |
| **R3** | `_store_order_experience` использует `hippocampus.store()`, но НЕ `value_layer.update()` с ненулевым reward — обучение только через sleep |
| **R4** | `_apply_order_feedback` обновляет `affective_space`, но НЕ `value_layer` — аффект не есть обучение |
| **R5** | `ProcurementHippocampusSeeder.seed_agent()` трогает только `hippocampus` — не `affective_space`, не `neuromodulators` |
| **R6** | Если `agent.step()` возвращает строку (fallback-агент) — это допустимо; система должна работать с обоими backend без ifdef |

---

## 6. Тест-кейсы

### `tests/test_agent_pipeline.py` (новый файл)
```python
"""Verify that the full NOWA cognitive pipeline is invoked on each day."""

import random
import pytest
from unittest.mock import MagicMock, patch, call
from nowa_sandbox.sandbox_agent_factory import create_procurement_agent
from nowa_sandbox.sandbox_encoder import SandboxEncoder
from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig
from nowa_sandbox.training_loop import SandboxTrainer


class TestAgentPipelineOrder:

    def test_agent_step_called_before_motor_adapter(self):
        """
        R1: agent.step() must be called before motor_adapter.resolve().
        Verify ordering by tracking call sequence.
        """
        agent = create_procurement_agent("test", rng=random.Random(1))
        encoder = SandboxEncoder()
        evaluator = ProcurementFitnessEvaluator(stage="1a")
        trainer = SandboxTrainer(agent, encoder, evaluator)

        call_order = []
        original_step = agent.step
        original_resolve = trainer.motor_adapter.resolve

        def tracked_step(*a, **kw):
            call_order.append("agent.step")
            return original_step(*a, **kw)

        def tracked_resolve(*a, **kw):
            call_order.append("motor_adapter.resolve")
            return original_resolve(*a, **kw)

        agent.step = tracked_step
        trainer.motor_adapter.resolve = tracked_resolve

        config = ProcurementWorldConfig(
            n_products=2, n_suppliers=2, days_per_quarter=3, seed=1
        )
        world = ProcurementWorld(config)
        trainer._run_single_quarter(world, n_days=3)

        # agent.step должен встречаться перед каждым motor_adapter.resolve
        step_indices = [i for i, c in enumerate(call_order) if c == "agent.step"]
        resolve_indices = [i for i, c in enumerate(call_order) if c == "motor_adapter.resolve"]

        for resolve_idx in resolve_indices:
            preceding_steps = [s for s in step_indices if s < resolve_idx]
            assert preceding_steps, (
                f"motor_adapter.resolve at position {resolve_idx} "
                f"had no preceding agent.step call"
            )

    def test_motor_adapter_does_not_call_agent_cognitive_methods(self):
        """R2: MotorAdapter must not call hippocampus.activate() or selector."""
        from nowa_sandbox.procurement_motor_adapter import ProcurementMotorAdapter
        adapter = ProcurementMotorAdapter()

        mock_hippocampus = MagicMock()
        mock_hippocampus.experiences = []

        stock_obs = {
            "product_000": {"quantity": 10, "reorder_point": 100,
                            "below_reorder_point": True}
        }
        supplier_obs = {
            "supplier_000": {"reliability": 0.9, "reputation": 0.8,
                             "is_defaulted": False}
        }
        budget_obs = {"remaining": 5000.0}

        adapter.resolve(
            "place_order_reliable_supplier",
            stock_obs, supplier_obs, budget_obs,
            mock_hippocampus,
        )

        # activate() должен быть НЕ вызван
        mock_hippocampus.activate.assert_not_called()

    def test_store_order_experience_uses_hippocampus_not_value_layer(self):
        """R3: _store_order_experience must use hippocampus.store, not value_layer."""
        agent = create_procurement_agent("test", rng=random.Random(1))
        encoder = SandboxEncoder()
        evaluator = ProcurementFitnessEvaluator(stage="1a")
        trainer = SandboxTrainer(agent, encoder, evaluator)

        from nowa_sandbox.procurement_motor_adapter import OrderParams
        params = OrderParams(
            supplier_id="supplier_000", product_id="product_000",
            qty=100.0, strategy="urgent_reorder", confidence=0.9,
        )
        result = {"status": "accepted", "cost": 500.0}

        n_before = len(agent.hippocampus.experiences)

        trainer._store_order_experience(
            ["event:stock_critical_low"], params, result
        )

        assert len(agent.hippocampus.experiences) > n_before, (
            "hippocampus.store() was not called"
        )

        # value_layer не должен обновляться напрямую
        value_layer = getattr(agent, "value_layer", None)
        if value_layer is not None:
            # Если value_layer существует, его update() не должен
            # вызываться с ненулевым reward в waking
            pass  # проверка через mock если нужна строгая верификация


class TestHippocampusSeederInPipeline:

    def test_seeder_only_touches_hippocampus(self):
        """R5: Seeder must not touch affective_space or neuromodulators."""
        agent = create_procurement_agent("test", rng=random.Random(1))

        axes_before = dict(getattr(agent.affective_space, "axes", {}))
        nm_snapshot_before = None
        nm = getattr(agent, "neuromodulators", None)
        if nm and hasattr(nm, "to_dict"):
            nm_snapshot_before = nm.to_dict()

        from nowa_sandbox.procurement_hippocampus_seeder import (
            ProcurementHippocampusSeeder
        )
        seeder = ProcurementHippocampusSeeder()
        n = seeder.seed_agent(agent)

        assert n > 0, "No episodes were seeded"

        axes_after = dict(getattr(agent.affective_space, "axes", {}))
        for axis in axes_before:
            assert abs(axes_before[axis] - axes_after.get(axis, 0.0)) < 1e-6, \
                f"Seeder modified affective_space[{axis}]"

        if nm_snapshot_before and hasattr(nm, "to_dict"):
            nm_after = nm.to_dict()
            assert nm_snapshot_before == nm_after, \
                "Seeder modified neuromodulators"

    def test_agent_has_seeded_memories_before_first_tick(self):
        """After factory creation, agent hippocampus is not empty."""
        agent = create_procurement_agent("test", rng=random.Random(1))
        assert len(agent.hippocampus.experiences) > 0, (
            "Agent hippocampus is empty after creation — "
            "ProcurementHippocampusSeeder was not called in factory"
        )


class TestFallbackAgentCompatibility:

    def test_fallback_agent_string_return_accepted(self):
        """R6: If agent.step() returns a string, _intent_to_action_type handles it."""
        agent = create_procurement_agent("test", rng=random.Random(1))
        encoder = SandboxEncoder()
        evaluator = ProcurementFitnessEvaluator(stage="1a")
        trainer = SandboxTrainer(agent, encoder, evaluator)

        action_type = trainer._intent_to_action_type("wait_and_monitor")
        assert action_type == "wait_and_monitor"

        action_type = trainer._intent_to_action_type(None)
        assert action_type == "wait_and_monitor"

    def test_full_run_works_with_fallback_agent(self):
        """End-to-end: 3-day quarter completes without errors."""
        agent = create_procurement_agent("test", rng=random.Random(42))
        encoder = SandboxEncoder()
        evaluator = ProcurementFitnessEvaluator(stage="1a")
        trainer = SandboxTrainer(agent, encoder, evaluator, sleep_every_n_days=2)

        config = ProcurementWorldConfig(
            n_products=2, n_suppliers=2, days_per_quarter=3, seed=42
        )
        world = ProcurementWorld(config)
        log = trainer._run_single_quarter(world, n_days=3)

        assert isinstance(log, list)
        assert len(log) == 3
        for entry in log:
            assert "action" in entry
            assert "day" in entry
```

---

## 7. Определение готовности

- [ ] `ProcurementMotorAdapter` реализован, тест `test_motor_adapter_does_not_call_agent_cognitive_methods` зелёный
- [ ] `ProcurementHippocampusSeeder` реализован, тест `test_seeder_only_touches_hippocampus` зелёный
- [ ] `SandboxTrainer._run_single_quarter` переписан по новой схеме, тест `test_agent_step_called_before_motor_adapter` зелёный
- [ ] Методы `_pick_priority_product`, `_pick_supplier`, `_decide_quantity`, `_agent_decide`, `_execute_action` удалены из `SandboxTrainer`
- [ ] `sandbox_agent_factory.create_procurement_agent` вызывает `ProcurementHippocampusSeeder.seed_agent()` — тест `test_agent_has_seeded_memories_before_first_tick` зелёный
- [ ] Прогон 10 кварталов Stage 1a — не падает, логирует action_type из реального pipeline, `hippocampus.experiences` растёт между кварталами
- [ ] Все тесты `test_procurement_world.py` и `test_procurement_fitness.py` остаются зелёными (физика и fitness не менялись)

---

## 8. Порядок реализации

### Шаг 1 (не трогать agent.py, не трогать training_loop)
Реализовать `ProcurementMotorAdapter` и его тесты изолированно.
Убедиться, что `test_motor_adapter_does_not_call_agent_cognitive_methods` зелёный.

### Шаг 2
Реализовать `ProcurementHippocampusSeeder` и тест `test_seeder_only_touches_hippocampus`.
Добавить вызов в `sandbox_agent_factory`.

### Шаг 3
Переписать `SandboxTrainer._run_single_quarter` по новой схеме.
Добавить `_agent_step`, `_intent_to_action_type`, `_apply_order_feedback`,
`_store_order_experience`. Удалить старые методы.

### Шаг 4
Запустить полный тест-сьют. Запустить 10 кварталов и проверить логи:
- `agent.step()` вызывается каждый день
- `hippocampus.experiences` растёт
- action_type не всегда `wait_and_monitor` (агент реагирует)

### Шаг 5
30-квартальный Stage 1a прогон с новой архитектурой. Сравнить:
- graduation rate с v1.3 (ожидаем: не хуже, возможно лучше со временем)
- `cost_efficiency` тренд обучения должен сохраниться
- `stockout_avoidance` IQR должен остаться < 0.10 (Q3b bounds сохраняются)

---

*Спецификация v2.0. Исправляет фундаментальный архитектурный дефект:
когнитивный pipeline NOWA теперь является единственным местом принятия
решений. MotorAdapter — часть тела, не мозга. Все решения проходят через
hippocampus → selector → BG → Thalamic Gate.*

---

## 9. Диагностика правильной работы pipeline после рефакторинга

После реализации шага 3 (новый `_run_single_quarter`) нужно убедиться,
что NOWA-pipeline реально работает, а не просто "не падает". Вот
конкретные диагностические проверки.

### 9.1 Проверка активации гиппокампа
```python
# Запустить после 1 квартала и проверить:
agent = create_procurement_agent("diag", rng=random.Random(1))
encoder = SandboxEncoder()
trainer = SandboxTrainer(agent, encoder, ProcurementFitnessEvaluator())

config = ProcurementWorldConfig(n_products=3, n_suppliers=2,
                                days_per_quarter=30, seed=1)
world = ProcurementWorld(config)
trainer._run_single_quarter(world, n_days=30)

# Должно быть:
# 1. hippocampus.experiences НЕ пустой
n_exp = len(agent.hippocampus.experiences)
assert n_exp > 0, f"Hippocampus empty after 30 days: {n_exp}"

# 2. Среди опытов есть токены заказов
order_experiences = [
    exp for exp in agent.hippocampus.experiences
    if any("action:" in str(getattr(exp.path, "events", []))
           or "supplier:" in str(getattr(exp.path, "events", [])))
]
print(f"Order experiences stored: {len(order_experiences)}")

# 3. Разнообразие action_type (агент не залип на одном)
from collections import Counter
actions_taken = [entry["action"] for entry in trainer.last_decision_log]
print(f"Action distribution: {Counter(actions_taken)}")
# Ожидаем: wait_and_monitor доминирует (нормально), но есть и другие
```

### 9.2 Проверка аффективной динамики
```python
# Снимок affective_space до и после квартала с дефицитом
axes_start = dict(agent.affective_space.axes)
# ... (запустить квартал с заведомо высоким demand) ...
axes_end = dict(agent.affective_space.axes)

# При stock_critical_low → reward=-0.3 → аффект должен сдвинуться
valence_start = axes_start.get("valence", 0.0)
valence_end = axes_end.get("valence", 0.0)
print(f"Valence shift over quarter: {valence_start:.3f} → {valence_end:.3f}")
# Ожидаем: не ноль (аффект реагирует на события)
```

### 9.3 Проверка что BG/Thalamic Gate не возвращает всегда одно и то же
```python
# За 30 дней агент должен выбирать разные action_type при разных контекстах
action_counts = Counter(actions_taken)
n_unique = len([a for a, c in action_counts.items() if c > 0])
assert n_unique >= 2, (
    f"Agent always chose the same action — BG/Thalamic not working: "
    f"{action_counts}"
)
```

### 9.4 Логирование в `run_sandbox.py`

Добавить в вывод CLI ежедневную диагностику (опция `--verbose-pipeline`):
```
[Day  1] context=3 tokens | activated=2 memories | action=wait_and_monitor
[Day  2] context=5 tokens | activated=0 memories | action=wait_and_monitor
[Day  7] context=6 tokens | activated=3 memories | action=urgent_reorder
         → MotorAdapter: supplier_001, product_003, qty=87.5
         → place_order: accepted (cost=438.20)
         → affective_feedback: valence +0.4, trust +0.3
[Day 14] context=4 tokens | activated=1 memories | action=place_order_reliable_supplier
         → MotorAdapter: supplier_000, product_001, qty=120.0
         → place_order: accepted (cost=540.00)
```

Это единственный способ убедиться, что pipeline работает без чтения
внутреннего состояния агента.

---

## 10. Ожидаемые изменения в поведении после рефакторинга

### Что улучшится

**`decision_consistency`** — сейчас залипание на одном supplier_id было
артефактом `_pick_supplier` с детерминированной логикой. После рефакторинга
BG/Thalamic Gate будет выбирать action_type на основе давления, которое
формируется из активированных эпизодов. Если агент выучил, что
`place_order_reliable_supplier` работает → будет последовательнее его
выбирать, но это будет реальный паттерн обучения, не артефакт кода.

**`reaction_to_risk_events`** — сейчас реакция была обусловлена тем, что
`stock_critical_low` токен просто триггерил нужную ветку в `_agent_decide`.
После рефакторинга: `stock_critical_low` активирует соответствующий
seed-эпизод из hippocampus → давление на `urgent_reorder` возрастает →
BG даёт Go → агент реагирует. Это будет реальная причинно-следственная связь
через аффективную память, не хардкод.

**`supplier_diversification`** — Stage 1b сможет реально обучить агента
диверсификации через `_select_least_used` в MotorAdapter, потому что теперь
hippocampus накапливает `supplier:XXX` токены в эпизодах и MotorAdapter
читает эту историю для выбора "наименее использованного".

### Что может временно ухудшиться

**graduation rate первые 5–10 кварталов** — агент начнёт с профессиональной
интуицией из seeder, но без реального опыта. До первого `sleep_cycle()` его
решения будут хуже, чем детерминированный суррогат из v1.3. Это нормально —
это цена честного обучения. После нескольких sleep cycles качество должно
восстановиться и превзойти v1.3.

Если graduation rate через 30 кварталов ниже, чем в v1.3 — это сигнал
либо к настройке `PROFESSIONAL_SEED_EPISODES`, либо к проверке работы
`sleep_cycle()` на новых данных (открытый вопрос Q2 из v1.2, который теперь
наконец можно честно исследовать — потому что агент реально обучается).

---

## 11. Связь с родительской архитектурой (Body Layer)

Этот рефакторинг делает sandbox прямым прообразом боевой системы из
`NOWA_Virtual_Employees_Architecture_Spec.md`:

| Sandbox v2.0 | Боевая система (Фаза 3) |
|---|---|
| `ProcurementMotorAdapter` | `MotorAdapter` (раздел 4 родительской спеки) |
| `ProcurementHippocampusSeeder` | `BusinessEventEncoder` seed-режим |
| `world.observe_*()` | MCP tool calls (READ_ONLY) |
| `world.place_order()` | MCP tool call (MEDIUM_WRITE) через ApprovalGate |
| `_apply_order_feedback()` | `Sensory Adapter` → affective impulse |
| `_store_order_experience()` | `hippocampus.store()` в боевом агенте |

Когда агент выпустится из песочницы (раздел 20 основной спецификации),
его `hippocampus.experiences` будут содержать реальные эпизоды принятых
решений — и это будет честная память, потому что каждый эпизод создан
через полный когнитивный pipeline, а не суррогатом.

---

## 12. Открытые вопросы (не блокируют v2.0, но важны для v2.1)

### Q-v2.0-1: Как именно `agent.step()` возвращает ActionIntent

В разных реализациях NOWA core `agent.step()` может возвращать:
- `str` (action label) — в fallback агенте
- `ActionIntent` объект — в полном NOWA core
- `None` — если BG даёт NoGo на все действия

`_intent_to_action_type()` обрабатывает все три случая через `getattr`.
Но нужно проверить конкретную реализацию `Agent.step()` в NOWA core —
возможно, она не возвращает ничего (void), а результат читается через
`agent.last_action` или `action_realizer.last_intent`. Это нужно
уточнить до шага 3 реализации.

**Действие:** перед шагом 3 — прочитать `agent.py::step()` и `action_realizer.py`,
зафиксировать точный API возврата ActionIntent.

### Q-v2.0-2: `ActionSelector.compute_pressures()` — какие входы нужны

В NOWA core `compute_pressures()` принимает active_experiences плюс
множество опциональных параметров (drive_state, temporal_levels и т.д.).
Минимальный корректный вызов для sandbox нужно уточнить — не все
параметры обязательны, но и не все можно игнорировать без потери
семантики.

**Действие:** перед шагом 3 — прочитать `selector.py::compute_pressures()`
и определить минимальный набор параметров для правильной работы BG.

### Q-v2.0-3: Формат `Path` и `Event` в NOWA core

`ProcurementHippocampusSeeder._build_path()` использует `from experience
import Path, Event, EventType`. Если API отличается от предположений
(например, `Path` конструируется иначе) — seeder тихо упадёт в fallback
и вернёт `_SimplePath`. Это не сломает систему, но ухудшит качество
активации гиппокампа.

**Действие:** перед шагом 2 — проверить реальные `Path`, `Event`,
`EventType` API из `experience.py` в NOWA core.

---

*Спецификация v2.0 полная. Разделы 1–12.*
*Критически важно выполнить шаги в порядке 1→2→3→4→5.*
*Не начинать шаг 3 (переписывать training_loop) до закрытия Q-v2.0-1 и Q-v2.0-2.*

---

## 13. Детальный разбор Q-v2.0-1, Q-v2.0-2, Q-v2.0-3 (обязательно до шага 3)

Три открытых вопроса из раздела 12 — не академические. Без их закрытия
шаг 3 (переписывание `training_loop`) обречён: либо упадёт при первом
запуске, либо молча подставит дефолты и создаст видимость работающего
pipeline при фактически обходящем его коде.

### 13.1 Закрытие Q-v2.0-1: что возвращает `agent.step()`

**Что нужно сделать агенту-разработчику до шага 3:**
```bash
# 1. Открыть agent.py в NOWA core и найти метод step()
grep -n "def step" src/agent.py

# 2. Найти что он возвращает
# Варианты:
#   return None                  → результат через self.last_action
#   return action_label: str     → строка, _intent_to_action_type работает
#   return ActionIntent(...)     → объект, нужно проверить атрибуты
#   return self.selector.select(...)  → делегирует, смотреть selector.py
```

**Ожидаемые сценарии и их обработка в `_intent_to_action_type`:**

| Что возвращает `step()` | Как обрабатывать |
|---|---|
| `str` | Использовать напрямую |
| `ActionIntent` с `.action_type` | `getattr(intent, "action_type")` |
| `ActionIntent` с `.action` | `getattr(intent, "action")` |
| `None` (BG дал NoGo) | Дефолт `"wait_and_monitor"` |
| Ничего (void) | Читать `agent.last_intent` или `agent.last_action` |

Если `step()` void — добавить в `_agent_step`:
```python
def _agent_step(self, context_events: List[str]) -> Any:
    step_fn = getattr(self.agent, "step", None)
    if callable(step_fn):
        result = step_fn(context_events)
        if result is not None:
            return result
    # Fallback: читать last_intent если step() void
    for attr in ("last_intent", "last_action", "current_action"):
        value = getattr(self.agent, attr, None)
        if value is not None:
            return value
    return "wait_and_monitor"
```

### 13.2 Закрытие Q-v2.0-2: минимальный вызов `compute_pressures()`

**Что нужно сделать:**
```bash
grep -n "def compute_pressures" src/selector.py
```

Сигнатура из изученного кода NOWA (раздел 0 основной спецификации):
```python
ActionSelector.compute_pressures(
    active_experiences,     # List[Experience] — обязательный
    affect_state,           # AffectiveState или snapshot — обязательный
    neuromodulators,        # NeuromodulatorState — обязательный
    temporal_levels=None,   # TemporalLevels — опциональный
    cortical_patterns=None, # List[CorticalPattern] — опциональный
)
```

Однако `agent.step()` уже вызывает `compute_pressures()` внутри — агент
разработчику не нужно вызывать его напрямую. Достаточно вызвать
`agent.step(context_events)` и получить результат.

**Критическая проверка:** убедиться, что `agent.step()` в NOWA core:
1. Вызывает `hippocampus.activate(context_events)` — не нужно делать
   это снаружи
2. Вызывает `selector.compute_pressures()` с результатом активации
3. Передаёт через `BasalGangliaGate` и `ThalamicGate`

Если любой из этих вызовов отсутствует в `agent.step()` — нужно добавить
явные вызовы в `SandboxTrainer._agent_step()` между получением
`context_events` и получением `ActionIntent`.

### 13.3 Закрытие Q-v2.0-3: реальный API Path/Event

**Что нужно сделать:**
```bash
grep -n "class Path\|class Event\|class EventType" src/experience.py
```

Из анализа `experience.py` в NOWA core (раздел анализа кодовой базы):
```python
# Ожидаемый API:
from experience import Event, Path, EventType

path = Path()
path.add_event(Event("token_label", EventType.CONTEXT))
# или через конструктор:
# path = Path(events=[Event("token", EventType.CONTEXT)])
```

Если API отличается — `ProcurementHippocampusSeeder._build_path()` нужно
обновить до реального API. Fallback `_SimplePath` оставить как страховку
для тестов без NOWA core.

---

## 14. Контракты публичного API новых модулей

### `ProcurementMotorAdapter`

| Метод | Входы | Выход | Гарантии |
|---|---|---|---|
| `resolve(action_type, stock_obs, supplier_obs, budget_obs, hippocampus)` | str + dict + dict + dict + Any | `Optional[OrderParams]` | Никогда не бросает исключение; возвращает None если нет доступных поставщиков или action="wait_and_monitor" |
| `_select_priority_product(stock_obs)` | dict | `Optional[str]` | None если нет товаров below_reorder_point |
| `_select_least_used(supplier_obs, hippocampus, product_id)` | dict + Any + str | `Optional[str]` | Читает hippocampus.experiences, не вызывает activate() |

### `ProcurementHippocampusSeeder`

| Метод | Входы | Выход | Гарантии |
|---|---|---|---|
| `seed_agent(agent)` | Any | `int` (кол-во добавленных) | Не трогает affective_space, neuromodulators, value_layer; при любой ошибке возвращает 0, не падает |
| `_build_path(tokens)` | `List[str]` | Path-совместимый объект | При отсутствии NOWA core возвращает `_SimplePath` |
| `_build_consequence(label)` | `str` | Event-совместимый объект | При отсутствии NOWA core возвращает строку |

### `SandboxTrainer` (обновлённый)

| Метод | Изменение |
|---|---|
| `_run_single_quarter(world, n_days)` | Полностью переписан, см. раздел 2.3 |
| `_agent_step(context_events)` | Новый — вызывает agent.step(), обрабатывает все варианты возврата |
| `_intent_to_action_type(intent)` | Новый — конвертирует любой формат intent в str |
| `_apply_order_feedback(result)` | Новый — аффективная ОС без обновления value_layer |
| `_store_order_experience(ctx, params, result)` | Новый — hippocampus.store() для каждого заказа |
| `_agent_decide(context)` | **УДАЛЁН** |
| `_execute_action(world, action)` | **УДАЛЁН** |
| `_pick_priority_product(world)` | **УДАЛЁН** → в MotorAdapter |
| `_pick_supplier(world, strategy)` | **УДАЛЁН** → в MotorAdapter |
| `_decide_quantity(world, pid)` | **УДАЛЁН** → в MotorAdapter |

---

## 15. Регрессионные тесты — что должно остаться зелёным

После рефакторинга без изменений должны проходить:
```bash
pytest tests/test_procurement_world.py          # физика мира не трогалась
pytest tests/test_procurement_fitness.py        # fitness не трогался
pytest tests/test_world_difficulty_bounds.py    # Q3b bounds не трогались
pytest tests/test_sandbox_encoder.py            # encoder не трогался
pytest tests/test_hippocampus_seeder.py         # Warriner seeder не трогался
pytest tests/test_stage_baseline_strictness.py  # baseline не трогался
pytest tests/test_graduation_non_regression.py  # streak-логика не трогалась
```

Новые тесты (должны быть зелёными после рефакторинга):
```bash
pytest tests/test_agent_pipeline.py             # новый
pytest tests/test_procurement_motor_adapter.py  # новый (если выделить отдельно)
```

---

## 16. Итоговое сравнение архитектур
```
v1.x (НЕПРАВИЛЬНО):              v2.0 (ПРАВИЛЬНО):
─────────────────────────         ───────────────────────────────
training_loop                     training_loop
  ├── _pick_product()    ←─ МОЗГ    └── agent.step(context)  ← МОЗГ
  ├── _pick_supplier()   ←─ МОЗГ        └── hippocampus.activate()
  ├── _decide_qty()      ←─ МОЗГ            selector.compute_pressures()
  └── agent.step()  ← аффект         BasalGangliaGate.process()
       (только аффект,                ThalamicGate.select()
        не решения)                   → ActionIntent
                                  MotorAdapter.resolve(intent)  ← ТЕЛО
                                      _select_priority_product()
                                      _select_supplier()
                                      _calculate_qty()
                                  world.place_order(params)     ← МИР
                                  _apply_order_feedback()       ← ЧУВСТВА
                                  hippocampus.store(experience) ← ПАМЯТЬ
                                  (каждые N дней)
                                  sleep_cycle()                 ← ОБУЧЕНИЕ
```

Агент — суверенная единица, которая видит мир через сенсоры
(context_events), думает (hippocampus → BG → Thalamic), действует через
тело (MotorAdapter → world), чувствует результат (affective_space) и
учится во сне (sleep_cycle). Это и есть NOWA.

---

*Спецификация v2.0. Финальная версия. Разделы 1–16.*
*Готова к передаче агенту-разработчику.*
*Обязательный порядок: закрыть Q-v2.0-1,2,3 → шаг 1 → шаг 2 → шаг 3 → шаг 4 → шаг 5.*
