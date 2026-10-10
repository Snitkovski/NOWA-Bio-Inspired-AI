# NOWA Body Layer — Патч v1.2

English version: [NOWA_Body_Layer_Phase1_Patch_v1.2.en.md](NOWA_Body_Layer_Phase1_Patch_v1.2.en.md)

## Аннотация

Патч v1.2 устраняет разрыв, подтверждённый построчным чтением реализации фаз 1.0 и 1.1, на границе моторного адаптера и петли обратной связи. `ProcurementBodyMotorAdapter._build_params` записывает выбранную агентом стратегию в поле `strategy` параметров действия. `apply_feedback_to_agent` строил событие `ACTION` из `tool_id`. Инструмент заказа лабораторной сессии обслуживает все четыре закупочные стратегии одним идентификатором, поэтому любой исполненный заказ сохранялся с токеном `action:mcp__1c__create_purchase_order`. Этого токена нет в словаре `ActionSelector`, где присутствуют четыре стратегии и `wait_and_monitor`. Селектор читает только известные события типа `ACTION`, так что эпизод остаётся в гиппокампе и не меняет давление ни на одну стратегию. Затравочный корпус по-прежнему задаёт начальное давление; опыт после реального исполнения его не корректирует. Затравщик при той же ревизии признан реализованным верно, и дефект локализован именно в петле обратной связи.

Исправление вводит `_resolve_action_label`. Если в `tool_params` есть непустая строка `strategy`, событие строится как `action:` этой строки. Иначе сохраняется прежний `tool_id`, что остаётся верным для роли, у которой один инструмент соответствует одной стратегии. Добавление поля `action_type` в универсальный `ProposedAction` отклонено: не у каждой роли есть внутренняя стратегия внутри одного инструмента, и пустое поле стало бы мёртвым грузом общего контракта. Смысл метки остаётся у роли. Аффективный шаг и вызов `store` в остальном не меняются; путь по-прежнему строится переприсваиванием и содержит ровно одно событие `ACTION`.

Регрессионный тест строится на этом сценарии: после исполнения в гиппокампе должна лежать стратегия агента, а не идентификатор инструмента, обслуживающего несколько стратегий. Роль без ключа `strategy` обязана сохранить прежнее поведение с `tool_id`. Патч не меняет физику песочницы и не меняет планировщик сна.

**Базовые документы:**
- NOWA_Body_Layer_Phase1_Spec.md (v1.0)
- NOWA_Body_Layer_Phase1_Patch_v1.1.md (планировщик сна и модель тика)

**Статус:** готово к реализации — единственный блокирующий дефект,
найденный при построчной ревизии реализации v1.0/v1.1

---

## Диагноз (подтверждён построчным чтением кода, не гипотеза)

`ProcurementBodyMotorAdapter._build_params` корректно кладёт выбранную
агентом стратегию в параметры действия:

```python
return {
    "supplier_id": str(supplier_id),
    "product_id": str(priority_product),
    "qty": qty,
    "strategy": str(action_type),   # ← "urgent_reorder" и т.п.
    "confidence": self._estimate_confidence(action_type, supplier_obs),
}
```

Но `feedback_loop.py::apply_feedback_to_agent` строит ACTION-событие
эпизода не из этого поля, а из `tool_id`:

```python
path = path.add_event(
    event_cls(f"action:{record.proposed_action.tool_id}", event_type.ACTION)
)
```

`ORDER_TOOL` в реестре (`BodyLabSession`) обслуживает все четыре
procurement-стратегии сразу:

```python
MCPCapability(
    tool_id=ORDER_TOOL,
    action_types=list(PROCUREMENT_ACTION_TYPES),  # все 4 → один tool_id
)
```

**Следствие:** любой реально исполненный заказ — вне зависимости от
того, была ли это `urgent_reorder`, `diversify_supplier` или
`place_order_cheap_supplier` — сохраняется в hippocampus с одним и тем
же ACTION-токеном `"action:mcp__1c__create_purchase_order"`. Этого
токена нет в словаре `ActionSelector` (там только четыре procurement-
стратегии + `wait_and_monitor`). По Уроку 2 (родительская спецификация,
раздел 0), `ActionSelector.compute_pressures()` читает только
`EventType.ACTION` события, ассоциированные с известными actions —
эпизод с неизвестным ACTION-токеном физически лежит в памяти, но не
корректирует давление ни на одну реальную стратегию.

**Практический эффект:** seed-корпус (`PROCUREMENT_SEED_EPISODES`)
создаёт правильное начальное давление на все четыре стратегии — это
работает. Но живой опыт после реального исполнения **никогда не
подкрепляет и не корректирует** это давление. Агент может успешно
стартовать на seed-интуиции, но не способен обучаться на собственных
результатах — второй Урок-2-провал, теперь на стыке `MotorAdapter →
feedback_loop`, а не в самом seeder (где, как подтверждено ревизией,
всё реализовано верно).

---

## Затронутые файлы

| Файл | Тип изменения |
|---|---|
| `feedback_loop.py` | Читать `action_type` из `tool_params["strategy"]`, откатываясь на `tool_id`, если поля нет |
| `tests/` | Регрессионный тест на точном сценарии этого разрыва |

---

## Изменение: `feedback_loop.py`

```python
def apply_feedback_to_agent(
    agent: Any,
    record: "ApprovalRecord",
    encoder: "BusinessEventEncoder",
) -> None:
    """..."""
    reward = approval_to_reward(record)
    execution_result = record.execution_result
    if not isinstance(execution_result, dict):
        execution_result = {"status": record.status.value}
    tokens, affective_inputs = encoder.encode_action_outcome(
        record.proposed_action.intent_summary,
        execution_result,
    )

    # ... affective_space.step(...) unchanged ...

    hippocampus = getattr(agent, "hippocampus", None)
    store_fn = getattr(hippocampus, "store", None)
    if not callable(store_fn):
        return
    path_cls, event_cls, event_type = load_experience_types()
    path = path_cls()
    for token in tokens or []:
        path = path.add_event(event_cls(str(token), event_type.CONTEXT))

    # ИЗМЕНЕНО: action_type берётся из tool_params, если роль его туда
    # положила (procurement кладёт под ключом "strategy" — см.
    # ProcurementBodyMotorAdapter._build_params). Роли, не использующие
    # это соглашение, откатываются на tool_id — прежнее поведение,
    # без регрессии для тех, у кого один tool_id == одна стратегия.
    action_label = _resolve_action_label(record.proposed_action)
    path = path.add_event(
        event_cls(f"action:{action_label}", event_type.ACTION)
    )

    consequence = event_cls(
        "approved" if reward > 0 else "rejected",
        event_type.CONSEQUENCE,
    )
    # ... store_fn(...) unchanged ...


def _resolve_action_label(proposed_action: "ProposedAction") -> str:
    """
    Recover the agent's actual chosen action_type for the ACTION event,
    not the MCP tool_id that happened to fulfil it. A single tool_id may
    serve several action_types (e.g. one 'create_purchase_order' tool
    fulfils all four procurement strategies) — falling back to tool_id
    there would store every outcome under one token the ActionSelector
    does not recognise, silently breaking learning from real outcomes
    (lesson 2, applied a second time at the MotorAdapter -> feedback_loop
    boundary; see patch v1.2 diagnosis).

    Convention: roles that need per-strategy feedback put the label under
    tool_params["strategy"] (see ProcurementBodyMotorAdapter). Roles with
    a 1:1 tool_id<->action_type mapping need not set it — tool_id already
    is the correct label there, and this falls back to it unchanged.
    """
    params = proposed_action.tool_params or {}
    strategy = params.get("strategy")
    if isinstance(strategy, str) and strategy.strip():
        return strategy.strip()
    return proposed_action.tool_id
```

### Почему не добавлять `action_type` полем в `ProposedAction`

Рассматривался альтернативный фикс — добавить `action_type: str` прямо
в dataclass `ProposedAction` в `motor_adapter.py`. Отклонён в пользу
конвенции через `tool_params["strategy"]`:

- `ProposedAction` — универсальный контракт для любой роли (раздел 6
  базовой спецификации). Не у каждой роли обязательно есть понятие
  "стратегии" внутри одного action_type — например, роль с 1:1
  соответствием tool_id↔action_type никогда не заполнила бы это поле,
  оно было бы всегда пустым мёртвым грузом в generic dataclass.
- `tool_params["strategy"]` уже существует и используется
  `ProcurementBodyMotorAdapter` для собственных целей (диагностика,
  возможно UI). Читать его в `feedback_loop.py` — не новая связь между
  компонентами, а использование уже существующей.
- Это сохраняет `MotorAdapter`/`ProposedAction` максимально тонкими —
  ответственность за то, что значит "action_type" для конкретной роли,
  остаётся у роли, а не протекает в generic-слой.

---

## Тест-кейсы

### `tests/test_feedback_action_label.py` (новый файл)

```python
"""Regression test for patch v1.2: the ACTION event stored after a real
MCP execution must reflect the agent's chosen strategy, not the tool_id
that happened to fulfil it — otherwise the ActionSelector never learns
from real outcomes for any tool_id that serves multiple action_types."""

import pytest
from nowa_body.approval_gate import ApprovalRecord, ApprovalStatus
from nowa_body.motor_adapter import ProposedAction
from nowa_body.mcp_capability import CapabilityRisk
from nowa_body.business_event_encoder import BusinessEventEncoder
from nowa_body.feedback_loop import apply_feedback_to_agent, _resolve_action_label


def _make_record(strategy_in_params: bool) -> ApprovalRecord:
    params = {"supplier_id": "acme", "product_id": "sku_a", "qty": 30.0}
    if strategy_in_params:
        params["strategy"] = "urgent_reorder"
    proposed = ProposedAction(
        action_id="test-1",
        agent_id="buyer",
        tool_id="mcp__1c__create_purchase_order",
        tool_params=params,
        risk_level=CapabilityRisk.MEDIUM_WRITE,
        intent_summary="urgent_reorder(supplier_id=acme, ...)",
        requires_approval=False,
    )
    return ApprovalRecord(
        proposed_action=proposed,
        status=ApprovalStatus.APPROVED,
        submitted_at=0.0,
        decided_at=0.0,
        decided_by="test",
        executed=True,
        execution_result={"status": "accepted"},
    )


class TestResolveActionLabel:

    def test_uses_strategy_when_present(self):
        record = _make_record(strategy_in_params=True)
        label = _resolve_action_label(record.proposed_action)
        assert label == "urgent_reorder"

    def test_falls_back_to_tool_id_when_absent(self):
        record = _make_record(strategy_in_params=False)
        label = _resolve_action_label(record.proposed_action)
        assert label == "mcp__1c__create_purchase_order"


class TestFeedbackStoresCorrectActionEvent:

    def test_stored_path_has_strategy_as_action_event(self, make_test_agent):
        """The exact bug: without the fix, this ACTION token would be
        'action:mcp__1c__create_purchase_order' for every strategy,
        which ActionSelector does not recognise."""
        agent = make_test_agent()
        encoder = BusinessEventEncoder({})
        record = _make_record(strategy_in_params=True)

        apply_feedback_to_agent(agent, record, encoder)

        stored = agent.hippocampus.experiences[-1]
        action_names = [
            e.name for e in stored.path.events
            if e.event_type.value == "action"
        ]
        assert action_names == ["action:urgent_reorder"]
        assert "action:mcp__1c__create_purchase_order" not in action_names

    def test_two_different_strategies_produce_different_action_events(
        self, make_test_agent
    ):
        """Two orders through the SAME tool_id but different strategies
        must be distinguishable in the hippocampus afterward — this is
        what makes per-strategy learning from real outcomes possible."""
        agent = make_test_agent()
        encoder = BusinessEventEncoder({})

        record_a = _make_record(strategy_in_params=True)
        apply_feedback_to_agent(agent, record_a, encoder)

        record_b = _make_record(strategy_in_params=True)
        record_b.proposed_action.tool_params["strategy"] = "diversify_supplier"
        apply_feedback_to_agent(agent, record_b, encoder)

        stored_actions = []
        for exp in agent.hippocampus.experiences[-2:]:
            names = [
                e.name for e in exp.path.events if e.event_type.value == "action"
            ]
            stored_actions.append(names[0] if names else None)

        assert stored_actions == ["action:urgent_reorder", "action:diversify_supplier"]

    def test_role_without_strategy_convention_unaffected(self, make_test_agent):
        """B4/backward-compat: a role that never sets tool_params['strategy']
        (1:1 tool_id<->action_type) must behave exactly as before this patch."""
        agent = make_test_agent()
        encoder = BusinessEventEncoder({})
        record = _make_record(strategy_in_params=False)

        apply_feedback_to_agent(agent, record, encoder)

        stored = agent.hippocampus.experiences[-1]
        action_names = [
            e.name for e in stored.path.events if e.event_type.value == "action"
        ]
        assert action_names == ["action:mcp__1c__create_purchase_order"]
```

---

## Ограничения

| # | Ограничение |
|---|---|
| **F1** | `_resolve_action_label` — чистая функция, без побочных эффектов, не мутирует `proposed_action` |
| **F2** | Конвенция ключа `"strategy"` в `tool_params` — не обязательна для всех ролей; отсутствие ключа не является ошибкой, только откатом к `tool_id` |
| **F3** | Фикс не меняет `ProcurementBodyMotorAdapter` — тот код уже был корректен, разрыв был только в `feedback_loop.py` |

---

## Критерий готовности

- [ ] `_resolve_action_label` реализована в `feedback_loop.py`
- [ ] `apply_feedback_to_agent` использует `_resolve_action_label` вместо
      прямого `record.proposed_action.tool_id`
- [ ] `test_stored_path_has_strategy_as_action_event` зелёный
- [ ] `test_two_different_strategies_produce_different_action_events` зелёный
      — это главный тест, доказывающий, что разрыв закрыт
- [ ] `test_role_without_strategy_convention_unaffected` зелёный —
      подтверждает отсутствие регрессии для ролей без конвенции
- [ ] Повторный прогон `BodyLabSession` с несколькими тиками, где агент
      реально исполняет разные стратегии (`urgent_reorder`,
      `diversify_supplier` и т.д.) — проверить вручную по
      `episode_rows()`, что ACTION-токены в сохранённых эпизодах
      действительно различаются между стратегиями, не совпадают все на
      `tool_id`

---

*Патч v1.2. Единственный блокирующий дефект Фазы 1, найденный при
построчной ревизии. Обоснован тем же классом ошибки (Урок 2), что уже
проявлялся дважды в этом проекте — на границе компонентов, не внутри
них по отдельности.*
