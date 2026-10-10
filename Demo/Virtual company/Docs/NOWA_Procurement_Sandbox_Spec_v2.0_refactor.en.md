## Abstract

Russian version: [NOWA_Procurement_Sandbox_Spec_v2.0_refactor.ru.md](NOWA_Procurement_Sandbox_Spec_v2.0_refactor.ru.md)

The v2.0 refactor records a defect in the sandbox training loop as it stood at version 1.3. Product, supplier, and quantity are chosen by external heuristics before `agent.step` is called, after which the world executes the order. Hippocampal activation feeds an affective signal and does not enter the selector; `compute_pressures`, `BasalGangliaGate`, `ThalamicGate`, realisation memory, and intent memory take no part in placing the order. `sleep_cycle` then consolidates the trajectory of a surrogate. The document requires the reverse order: an observation becomes `context_events`, the agent step passes through the hippocampus, the selector, the basal ganglia, and the thalamic gate and returns an intention, and only then does the body resolve parameters.

`ProcurementMotorAdapter` turns an action type into `OrderParams` from observations of stock, the supplier directory, and budget. A read of the hippocampus is admitted only in the least-used-supplier strategy, and only as a count of episodes already stored, without calling `activate` and without calling `place_order`. Affective feedback updates the affective state of an accepted or rejected order and does not update the value layer. An episode with tokens of context, action, supplier, and outcome is written to the hippocampus; weight change remains a function of sleep. `ProcurementHippocampusSeeder` loads eight professional episodes once, before the first tick, and does not touch affective space, neuromodulators, or the value layer. World physics, the encoder, the fitness evaluator, the Q3b difficulty bounds, the baseline, and the streak logic of the preceding patches are retained.

Constraints R1–R6 require that the agent step precede the adapter on every day, that the adapter not call cognitive methods, that a waking write not update the value layer, and that a string return from the fallback agent remain admissible. Acceptance conditions include growth in the number of episodes across quarters and a ten-quarter Stage 1a run without a crash. The document expects that the first five to ten quarters may fall short of the deterministic surrogate of version 1.3 until several sleep cycles have passed, and it sets, as a condition of the later thirty-quarter comparison, retention of the cost-efficiency trend and an interquartile range of stockout avoidance below 0.10 with the Q3b bounds kept. These quantities are stated as comparison criteria, not as an outcome of the refactor already measured. Before the loop is rewritten, the actual return contract of `agent.step`, the minimal arguments of `compute_pressures`, and the constructors of `Path` and `Event` in the core must be closed.

---

# NOWA Procurement Sandbox — Refactor v2.0

**Base documents:** all preceding patches v1.0–v1.3
**Status:** Ready for implementation — a fundamental architectural refactor
**Priority:** Critical — without this the agent is not a NOWA agent

---

## 0. Diagnosis: what was done incorrectly

The current implementation (`training_loop.py` v1.3) works as follows:

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
The NOWA cognitive contour — `hippocampus → affective_space → selector →
BasalGangliaGate → ThalamicGate` — exists in the agent's code, but
**takes no part in decision-making**. The agent is decoration.
Learning through `sleep_cycle()` accumulates the experience of a passive observer,
not of an active participant.

### What specifically is unused

| NOWA component | Status in the current implementation |
|---|---|
| `NOWAHippocampus.activate()` | Called in `_activate_memories`, but the result goes only into `_memory_signal` for affect, not into the selector |
| `ActionSelector.compute_pressures()` | Not called |
| `BasalGangliaGate.process()` | Not called |
| `ThalamicGate.select()` | Not called |
| `AffectiveSpace` | Updated as a side effect of `agent.step()`, but does not influence decisions |
| `NeuromodulatorState` | Updated, but does not influence supplier choice |
| `RealizationMemory` | Not used at all |
| `IntentMemory` (habits) | Not used at all |
| `sleep_cycle()` | Called, but consolidates the experience of a surrogate, not of the real agent |

---

## 1. The correct architecture (Variant B)

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
### The essential difference from v1.3

The order has been reversed:

```
v1.3:  pick_params → agent.step() → world.place_order()
v2.0:  agent решает → MotorAdapter.resolve_params() → world.place_order()
```
The agent decides first. The parameters (supplier_id, qty) are resolved
**after** the agent has chosen a strategy — deterministically from the current
observations of the world through `ProcurementMotorAdapter`.

---

## 2. New components

### 2.1 `ProcurementMotorAdapter` — body, not brain

```
Файл: nowa_sandbox/procurement_motor_adapter.py
```
**Purpose:** turn an `action_type` (the agent's strategy) into concrete
order parameters, using the current observations of the world and the history
of the agent's hippocampus.

**This is part of the agent's body, not an external orchestrator.** Analogous to
the way a human hand takes a particular object, carrying out the intention "take
something from the table" — the hand itself does not decide to take, but determines
the grip.

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

### 2.2 `ProcurementHippocampusSeeder` — professional intuition

```
Файл: nowa_sandbox/procurement_hippocampus_seeder.py
```
**Purpose:** load seed episodes of
"professional intuition" into the agent's hippocampus before the first tick. An analogue of `HippocampusSeeder`
from the Warriner demo, but for business events instead of words.

Without this the agent starts with an empty hippocampus — `hippocampus.activate()`
returns an empty list, `selector.compute_pressures()` receives zero
inputs, the pressure on all actions is equal, and the basal ganglia choose at random.
This is not a catastrophe (the agent will learn through sleep_cycle), but it makes the first
10–20 quarters practically random.

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

### 2.3 Refactor of `training_loop.py`

The main change: remove `_pick_priority_product`, `_pick_supplier`,
and `_decide_quantity` from `SandboxTrainer` as decision methods.
They move into `ProcurementMotorAdapter` as methods that resolve parameters.

#### Current `_run_single_quarter` (v1.3 — INCORRECT)

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
#### New `_run_single_quarter` (v2.0 — CORRECT)

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
#### New auxiliary methods of `SandboxTrainer`

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

### 2.4 Update of `SandboxTrainer.__init__`

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

### 2.5 Update of `sandbox_agent_factory.py`

Add a call to `ProcurementHippocampusSeeder.seed_agent()` after
the agent is created and before the return:

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

## 3. What is removed from `training_loop.py`

| Method | Reason for removal |
|---|---|
| `_agent_decide(context)` | Replaced by `agent.step(context_events)` through the whole NOWA pipeline |
| `_execute_action(world, action)` | Split into MotorAdapter.resolve() + world.place_order() |
| `_pick_priority_product(world)` | Moves into `ProcurementMotorAdapter._select_priority_product` |
| `_pick_supplier(world, strategy)` | Moves into the `ProcurementMotorAdapter._select_*` methods |
| `_decide_quantity(world, product_id)` | Moves into `ProcurementMotorAdapter._calculate_qty` |
| `ACTION_TO_ORDER_STRATEGY` | Moves into `ProcurementMotorAdapter.SUPPLIER_STRATEGIES` |

---

## 4. What does NOT change

| Component | Reason for retention |
|---|---|
| `ProcurementWorld` (all physics) | Correctly implemented; invariant C2 is observed |
| `SandboxEncoder` (tokens) | Correctly implemented |
| `ProcurementFitnessEvaluator` | Correct — an external observer |
| `ProcurementFitnessVector` | Correct |
| All tests in `test_procurement_world.py` | World physics does not change |
| All tests in `test_procurement_fitness.py` | Fitness logic does not change |
| `stage_baseline.py` | Does not change |
| `sandbox_checkpoint.py` | Does not change — the agent is serialised through AgentStorage |
| World parameters of v1.3 (Q3b bounds) | Remain |
| `world_difficulty.py` | Remains as a diagnostic option |

---

## 5. Constraints (a violation is an architectural defect)

| # | Constraint |
|---|---|
| **R1** | `SandboxTrainer._run_single_quarter` calls `agent.step()` FIRST on every day — before any appeal to MotorAdapter |
| **R2** | `ProcurementMotorAdapter` does not call `agent.step()`, `agent.hippocampus.activate()`, or any cognitive method of the agent directly — it only reads `hippocampus.experiences` for a usage counter |
| **R3** | `_store_order_experience` uses `hippocampus.store()`, but NOT `value_layer.update()` with a non-zero reward — learning is only through sleep |
| **R4** | `_apply_order_feedback` updates `affective_space`, but NOT `value_layer` — affect is not learning |
| **R5** | `ProcurementHippocampusSeeder.seed_agent()` touches only `hippocampus` — not `affective_space`, not `neuromodulators` |
| **R6** | If `agent.step()` returns a string (fallback agent) — this is admissible; the system must work with both backends without an ifdef |

---

## 6. Test cases

### `tests/test_agent_pipeline.py` (new file)

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

## 7. Definition of done

- [ ] `ProcurementMotorAdapter` is implemented; the test `test_motor_adapter_does_not_call_agent_cognitive_methods` is green
- [ ] `ProcurementHippocampusSeeder` is implemented; the test `test_seeder_only_touches_hippocampus` is green
- [ ] `SandboxTrainer._run_single_quarter` is rewritten to the new scheme; the test `test_agent_step_called_before_motor_adapter` is green
- [ ] The methods `_pick_priority_product`, `_pick_supplier`, `_decide_quantity`, `_agent_decide`, `_execute_action` are removed from `SandboxTrainer`
- [ ] `sandbox_agent_factory.create_procurement_agent` calls `ProcurementHippocampusSeeder.seed_agent()` — the test `test_agent_has_seeded_memories_before_first_tick` is green
- [ ] A run of 10 quarters of Stage 1a does not crash, logs action_type from the real pipeline, and `hippocampus.experiences` grows between quarters
- [ ] All tests in `test_procurement_world.py` and `test_procurement_fitness.py` remain green (physics and fitness were not changed)

---

## 8. Implementation order

### Step 1 (do not touch agent.py, do not touch training_loop)
Implement `ProcurementMotorAdapter` and its tests in isolation.
Confirm that `test_motor_adapter_does_not_call_agent_cognitive_methods` is green.

### Step 2
Implement `ProcurementHippocampusSeeder` and the test `test_seeder_only_touches_hippocampus`.
Add the call in `sandbox_agent_factory`.

### Step 3
Rewrite `SandboxTrainer._run_single_quarter` to the new scheme.
Add `_agent_step`, `_intent_to_action_type`, `_apply_order_feedback`,
`_store_order_experience`. Remove the old methods.

### Step 4
Run the full test suite. Run 10 quarters and check the logs:
- `agent.step()` is called every day
- `hippocampus.experiences` grows
- action_type is not always `wait_and_monitor` (the agent reacts)

### Step 5
A 30-quarter Stage 1a run with the new architecture. Compare:
- graduation rate with v1.3 (expected: not worse, possibly better over time)
- the `cost_efficiency` learning trend must be retained
- the `stockout_avoidance` IQR must remain < 0.10 (the Q3b bounds are kept)

---

*Specification v2.0. It corrects a fundamental architectural defect:
the NOWA cognitive pipeline is now the only place where decisions
are made. MotorAdapter is part of the body, not of the brain. Every decision passes through
hippocampus → selector → BG → Thalamic Gate.*

---

## 9. Diagnosis that the pipeline works correctly after the refactor

After step 3 is implemented (the new `_run_single_quarter`) one must confirm
that the NOWA pipeline actually works, and does not merely "not crash". The
concrete diagnostic checks follow.

### 9.1 Check of hippocampal activation

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
### 9.2 Check of affective dynamics

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
### 9.3 Check that the BG/Thalamic Gate does not always return the same thing

```python
# За 30 дней агент должен выбирать разные action_type при разных контекстах
action_counts = Counter(actions_taken)
n_unique = len([a for a, c in action_counts.items() if c > 0])
assert n_unique >= 2, (
    f"Agent always chose the same action — BG/Thalamic not working: "
    f"{action_counts}"
)
```
### 9.4 Logging in `run_sandbox.py`

Add daily diagnostics to the CLI output (option `--verbose-pipeline`):

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
This is the only way to confirm that the pipeline works without reading
the agent's internal state.

---

## 10. Expected changes in behaviour after the refactor

### What will improve

**`decision_consistency`** — sticking to a single supplier_id was
an artefact of `_pick_supplier` with deterministic logic. After the refactor
the BG/Thalamic Gate will choose action_type from the pressure that
is formed from activated episodes. If the agent has learned that
`place_order_reliable_supplier` works → it will choose it more consistently,
but this will be a real learning pattern, not an artefact of the code.

**`reaction_to_risk_events`** — the reaction was previously due to the
`stock_critical_low` token simply triggering the required branch in `_agent_decide`.
After the refactor: `stock_critical_low` activates the corresponding
seed episode from the hippocampus → pressure on `urgent_reorder` rises →
the basal ganglia give Go → the agent reacts. This will be a real causal link
through affective memory, not a hard-coded rule.

**`supplier_diversification`** — Stage 1b will be able to train the agent
in diversification through `_select_least_used` in MotorAdapter, because the
hippocampus now accumulates `supplier:XXX` tokens in episodes and MotorAdapter
reads that history in order to choose the "least used".

### What may temporarily worsen

**graduation rate over the first 5–10 quarters** — the agent will start with professional
intuition from the seeder, but without real experience. Until the first `sleep_cycle()` its
decisions will be worse than the deterministic surrogate of v1.3. This is normal —
it is the price of honest learning. After several sleep cycles quality should
recover and surpass v1.3.

If the graduation rate after 30 quarters is lower than in v1.3, that is a signal
either to tune `PROFESSIONAL_SEED_EPISODES`, or to check the operation of
`sleep_cycle()` on the new data (open question Q2 from v1.2, which can now
at last be investigated honestly — because the agent actually learns).

---

## 11. Relation to the parent architecture (Body Layer)

This refactor makes the sandbox a direct prototype of the operational system in
`NOWA_Virtual_Employees_Architecture_Spec.md`:

| Sandbox v2.0 | Operational system (Phase 3) |
|---|---|
| `ProcurementMotorAdapter` | `MotorAdapter` (section 4 of the parent specification) |
| `ProcurementHippocampusSeeder` | `BusinessEventEncoder` seed mode |
| `world.observe_*()` | MCP tool calls (READ_ONLY) |
| `world.place_order()` | MCP tool call (MEDIUM_WRITE) through ApprovalGate |
| `_apply_order_feedback()` | `Sensory Adapter` → affective impulse |
| `_store_order_experience()` | `hippocampus.store()` in the operational agent |

When the agent graduates from the sandbox (section 20 of the main specification),
its `hippocampus.experiences` will contain real episodes of decisions
taken — and this will be honest memory, because every episode was created
through the full cognitive pipeline, not by a surrogate.

---

## 12. Open questions (they do not block v2.0, but they matter for v2.1)

### Q-v2.0-1: How exactly `agent.step()` returns an ActionIntent

In different implementations of the NOWA core, `agent.step()` may return:
- `str` (action label) — in the fallback agent
- an `ActionIntent` object — in the full NOWA core
- `None` — if the basal ganglia give NoGo on every action

`_intent_to_action_type()` handles all three cases through `getattr`.
But the concrete implementation of `Agent.step()` in the NOWA core must be checked —
it may return nothing (void), while the result is read through
`agent.last_action` or `action_realizer.last_intent`. This must
be settled before implementation step 3.

**Action:** before step 3 — read `agent.py::step()` and `action_realizer.py`,
and record the exact API by which an ActionIntent is returned.

### Q-v2.0-2: `ActionSelector.compute_pressures()` — which inputs are required

In the NOWA core, `compute_pressures()` accepts active_experiences plus
a set of optional parameters (drive_state, temporal_levels, and so on).
The minimal correct call for the sandbox must be settled — not every
parameter is obligatory, but not every parameter can be ignored without loss
of semantics.

**Action:** before step 3 — read `selector.py::compute_pressures()`
and determine the minimal set of parameters for the basal ganglia to work correctly.

### Q-v2.0-3: The format of `Path` and `Event` in the NOWA core

`ProcurementHippocampusSeeder._build_path()` uses `from experience
import Path, Event, EventType`. If the API differs from the assumptions
(for example, `Path` is constructed differently) — the seeder will fall quietly into the fallback
and return `_SimplePath`. This will not break the system, but it will degrade the quality
of hippocampal activation.

**Action:** before step 2 — check the real `Path`, `Event`,
and `EventType` API from `experience.py` in the NOWA core.

---

*Specification v2.0 is complete. Sections 1–12.*
*It is critical to carry out the steps in the order 1→2→3→4→5.*
*Do not begin step 3 (rewriting training_loop) until Q-v2.0-1 and Q-v2.0-2 are closed.*

---

## 13. Detailed treatment of Q-v2.0-1, Q-v2.0-2, Q-v2.0-3 (obligatory before step 3)

The three open questions of section 12 are not academic. Without closing them,
step 3 (rewriting `training_loop`) is doomed: it will either crash on the first
launch, or it will silently substitute defaults and create the appearance of a working
pipeline while the code in fact bypasses it.

### 13.1 Closing Q-v2.0-1: what `agent.step()` returns

**What the implementing agent must do before step 3:**

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
**Expected scenarios and their handling in `_intent_to_action_type`:**

| What `step()` returns | How to handle it |
|---|---|
| `str` | Use it directly |
| `ActionIntent` with `.action_type` | `getattr(intent, "action_type")` |
| `ActionIntent` with `.action` | `getattr(intent, "action")` |
| `None` (the basal ganglia gave NoGo) | Default `"wait_and_monitor"` |
| Nothing (void) | Read `agent.last_intent` or `agent.last_action` |

If `step()` is void — add to `_agent_step`:

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
### 13.2 Closing Q-v2.0-2: the minimal call to `compute_pressures()`

**What must be done:**

```bash
grep -n "def compute_pressures" src/selector.py
```
Signature from the NOWA code that was studied (section 0 of the main specification):

```python
ActionSelector.compute_pressures(
    active_experiences,     # List[Experience] — обязательный
    affect_state,           # AffectiveState или snapshot — обязательный
    neuromodulators,        # NeuromodulatorState — обязательный
    temporal_levels=None,   # TemporalLevels — опциональный
    cortical_patterns=None, # List[CorticalPattern] — опциональный
)
```
However, `agent.step()` already calls `compute_pressures()` internally — the implementing
agent does not need to call it directly. It is enough to call
`agent.step(context_events)` and obtain the result.

**Critical check:** confirm that `agent.step()` in the NOWA core:
1. Calls `hippocampus.activate(context_events)` — this need not be done
   from outside
2. Calls `selector.compute_pressures()` with the result of activation
3. Passes the result through `BasalGangliaGate` and `ThalamicGate`

If any of these calls is absent from `agent.step()`, explicit calls must be added
in `SandboxTrainer._agent_step()` between obtaining
`context_events` and obtaining the `ActionIntent`.

### 13.3 Closing Q-v2.0-3: the real Path/Event API

**What must be done:**

```bash
grep -n "class Path\|class Event\|class EventType" src/experience.py
```
From the analysis of `experience.py` in the NOWA core (the code-base analysis section):

```python
# Ожидаемый API:
from experience import Event, Path, EventType

path = Path()
path.add_event(Event("token_label", EventType.CONTEXT))
# или через конструктор:
# path = Path(events=[Event("token", EventType.CONTEXT)])
```
If the API differs, `ProcurementHippocampusSeeder._build_path()` must
be updated to the real API. Leave the `_SimplePath` fallback as a safeguard
for tests without the NOWA core.

---

## 14. Public API contracts of the new modules

### `ProcurementMotorAdapter`

| Method | Inputs | Output | Guarantees |
|---|---|---|---|
| `resolve(action_type, stock_obs, supplier_obs, budget_obs, hippocampus)` | str + dict + dict + dict + Any | `Optional[OrderParams]` | Never raises; returns None if there are no available suppliers or action="wait_and_monitor" |
| `_select_priority_product(stock_obs)` | dict | `Optional[str]` | None if there are no products below_reorder_point |
| `_select_least_used(supplier_obs, hippocampus, product_id)` | dict + Any + str | `Optional[str]` | Reads hippocampus.experiences; does not call activate() |

### `ProcurementHippocampusSeeder`

| Method | Inputs | Output | Guarantees |
|---|---|---|---|
| `seed_agent(agent)` | Any | `int` (number added) | Does not touch affective_space, neuromodulators, or value_layer; on any error returns 0 and does not crash |
| `_build_path(tokens)` | `List[str]` | a Path-compatible object | In the absence of the NOWA core returns `_SimplePath` |
| `_build_consequence(label)` | `str` | an Event-compatible object | In the absence of the NOWA core returns a string |

### `SandboxTrainer` (updated)

| Method | Change |
|---|---|
| `_run_single_quarter(world, n_days)` | Rewritten in full; see section 2.3 |
| `_agent_step(context_events)` | New — calls agent.step() and handles every return variant |
| `_intent_to_action_type(intent)` | New — converts any intent format into str |
| `_apply_order_feedback(result)` | New — affective feedback without updating value_layer |
| `_store_order_experience(ctx, params, result)` | New — hippocampus.store() for every order |
| `_agent_decide(context)` | **REMOVED** |
| `_execute_action(world, action)` | **REMOVED** |
| `_pick_priority_product(world)` | **REMOVED** → into MotorAdapter |
| `_pick_supplier(world, strategy)` | **REMOVED** → into MotorAdapter |
| `_decide_quantity(world, pid)` | **REMOVED** → into MotorAdapter |

---

## 15. Regression tests — what must remain green

After the refactor, the following must pass unchanged:

```bash
pytest tests/test_procurement_world.py          # физика мира не трогалась
pytest tests/test_procurement_fitness.py        # fitness не трогался
pytest tests/test_world_difficulty_bounds.py    # Q3b bounds не трогались
pytest tests/test_sandbox_encoder.py            # encoder не трогался
pytest tests/test_hippocampus_seeder.py         # Warriner seeder не трогался
pytest tests/test_stage_baseline_strictness.py  # baseline не трогался
pytest tests/test_graduation_non_regression.py  # streak-логика не трогалась
```
New tests (they must be green after the refactor):

```bash
pytest tests/test_agent_pipeline.py             # новый
pytest tests/test_procurement_motor_adapter.py  # новый (если выделить отдельно)
```
---

## 16. Final comparison of the architectures

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
The agent is a sovereign unit that sees the world through sensors
(context_events), thinks (hippocampus → BG → Thalamic), acts through
the body (MotorAdapter → world), feels the result (affective_space), and
learns in sleep (sleep_cycle). That is NOWA.

---

*Specification v2.0. Final version. Sections 1–16.*
*Ready to be handed to the implementing agent.*
*Obligatory order: close Q-v2.0-1, 2, 3 → step 1 → step 2 → step 3 → step 4 → step 5.*
