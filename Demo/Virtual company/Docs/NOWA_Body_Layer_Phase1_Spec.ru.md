## Аннотация

English version: [NOWA_Body_Layer_Phase1_Spec.en.md](NOWA_Body_Layer_Phase1_Spec.en.md)

Спецификация фазы 1 переносит когнитивный порядок песочницы версии 2.0 в универсальный слой тела `nowa_body`, не привязанный к одной роли и к одной внешней системе. Три урока песочницы становятся обязательными. Путь `Path` иммутабелен и строится переприсваиванием результата `add_event`. Селектор формирует давление только по событиям типа `ACTION`, поэтому каждый затравочный эпизод содержит ровно одно такое событие; корпус из одних контекстных токенов лежит в гиппокампе и давления не создаёт. Вызов `agent.step` с `decision_only=True` проводит активацию, селектор, базальные ганглии и таламический шлюз и не пишет исход; эпизод записывает хозяин тела после того, как исход известен. Шлюз одобрения, которого в песочнице сознательно не было, становится границей записи во внешний мир.

Пайплайн фазы устроен так. Результат инструмента чтения кодируется в `context_events`. Шаг агента возвращает намерение. `MotorAdapter` строит ещё не исполненное `ProposedAction`. `ApprovalGate` исполняет чтение и явно разрешённую автономию сразу либо ставит прочую запись в очередь человека. После исполнения кодировщик исхода обновляет аффективное состояние и гиппокамп, и путь эпизода снова содержит событие `ACTION`. Периодически вызывается `sleep_cycle`. Запись `MCPCapability` получает список `action_types`, чтобы один инструмент мог обслуживать несколько стратегий селектора. `BusinessHippocampusSeeder` доменно-нейтрален: корпус передаётся снаружи, затрагивает только `store` и `reinforce` и не изменяет аффективное пространство, нейромодуляторы и слой ценности. `MockMCPClient` позволяет прогнать фазу без живого сервера.

Когнитивный шаг не получает объекта протокола: ядро не импортирует описание MCP. Реестр возможностей одного агента отделён от транспортного соединения, которое может быть общим. Высокая и необратимая запись требует одобрения, и это ограничение не снимается конфигурацией. Подключение реального сервера учёта отложено до переноса уже разобранного моторного пути закупок из песочницы. Открытыми на момент этой спецификации остаются момент вызова сна, частота шага относительно опроса сенсоров и формат краткого изложения намерения для человека.

---

# NOWA Body Layer — Фаза 1 Спецификация

**Версия:** 1.0
**Родительский документ:** NOWA_Virtual_Employees_Architecture_Spec.md (разделы 1–4)
**Предпосылка:** NOWA_Procurement_Sandbox_Spec v2.0 — рефакторинг подтвердил
рабочий когнитивный pipeline на симулированном мире
**Статус:** готово к реализации
**Цель:** Универсальный слой "тело" — превращает любой MCP-сервер в
сенсоры и мышцы NOWA-агента, без привязки к конкретной роли или системе.

---

## 0. Принципы (наследуются + уроки из песочницы)

Наследуется без изменений из архитектурной спецификации: агент —
суверенная единица; approval gate — снаружи когнитивного контура;
деньги — не валентность.

### Три конкретных урока из рефакторинга песочницы v2.0, обязательных здесь

**Урок 1 — `Path` иммутабелен.** `path.add_event(e)` возвращает новый
`Path`, не мутирует существующий. Любой код, строящий путь циклом с
переприсваиванием `path = path.add_event(e)`, а не просто вызовом.

**Урок 2 — Selector читает только `EventType.ACTION` события.**
`ActionSelector.compute_pressures()` формирует давление на actions на
основе того, какие `EventType.ACTION` токены исторически ассоциированы
с данным контекстом. Seed-эпизод из одних `EventType.CONTEXT` токенов
физически лежит в гиппокампе, но **не создаёт никакого давления** —
тихий no-op. Каждый seed-эпизод обязан содержать `action:<label>`
событие с `EventType.ACTION`.

**Урок 3 — Decision/Consolidation split через `decision_only=True`.**
`Agent.step(context_events, decision_only=True)` проходит весь pipeline
(`hippocampus.activate → selector → BG → Thalamic`) и возвращает action,
но не пишет в hippocampus/value_layer/affective regulation. Хост
(здесь — Body Layer runtime) сам записывает эпизод **после** того, как
узнал реальный исход действия — иначе эпизод помечается результатом,
которого ещё не произошло.

---

## 1. Архитектура пайплайна (обновлено под живой MCP)

```
MCP Server (READ_ONLY tool)
    ↓ tool result
BusinessEventEncoder.encode_tool_result()
    → context_events: List[str]
    ↓
agent.step(context_events, decision_only=True)
    (hippocampus.activate → selector.compute_pressures →
     BasalGangliaGate → ThalamicGate)
    → action_intent
    ↓
MotorAdapter.resolve(action_intent, observations)
    → ProposedAction (ещё не выполнено)
    ↓
ApprovalGate.route(proposed_action)
    ├── READ_ONLY / разрешённая автономия → выполнить немедленно
    └── иначе → очередь на approval человека
    ↓ (после исполнения, реальный или человеческий approve)
MCP Server (WRITE tool call)
    → result
    ↓
BusinessEventEncoder.encode_action_outcome(result)
    → affective_inputs + episode_tokens (с EventType.ACTION!)
    ↓
agent.affective_space.step(affective_inputs)
agent.hippocampus.store(path_with_action_event, consequence, reward)
    ↓ (периодически)
agent.sleep_manager.sleep_cycle()
```

Это прямое продолжение схемы из родительской спецификации (раздел 1),
уточнённое тремя уроками из раздела 0.

---

## 2. Структура проекта

```
nowa_body/
├── __init__.py
├── mcp_capability.py          # MCPCapability, CapabilityRisk
├── risk_classifier.py         # эвристики классификации риска тула
├── tool_registry.py           # MCPToolRegistry
├── business_event_encoder.py  # Sensory Adapter
├── business_hippocampus_seeder.py  # профессиональная интуиция (ACTION-aware)
├── motor_adapter.py           # generic MotorAdapter + ProposedAction
├── approval_gate.py           # ApprovalGate (внешний барьер)
├── hard_constraints.py        # инварианты, не обходимые конфигом
├── mock_mcp.py                # тестовый MCP без реального сервера
├── runtime.py                 # оркестратор полного pipeline
├── tests/
│   ├── conftest.py
│   ├── test_mcp_capability.py
│   ├── test_risk_classifier.py
│   ├── test_tool_registry.py
│   ├── test_business_event_encoder.py
│   ├── test_business_hippocampus_seeder.py
│   ├── test_motor_adapter.py
│   ├── test_approval_gate.py
│   ├── test_agent_pipeline_order.py   # аналог test_agent_pipeline.py из sandbox
│   └── test_integration.py
└── requirements.txt
```

---

## 3. `mcp_capability.py`

Реализация без изменений относительно родительской спецификации
(раздел 2.2) — контракт зафиксирован и уже проверен по смыслу. Одно
уточнение под уроки песочницы:

```python
@dataclass
class MCPCapability:
    tool_id: str
    server_name: str
    display_name: str
    description: str
    risk_level: CapabilityRisk
    domain_tags: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = True
    cost_impact_estimate: Optional[str] = None
    max_autonomous_value: Optional[float] = None

    # НОВОЕ: явная связь capability с action-стратегиями агента.
    # Аналог SUPPLIER_STRATEGIES из ProcurementMotorAdapter — MotorAdapter
    # должен знать, какие action_type от агента резолвятся в вызов ИМЕННО
    # этого тула. Без этой связи MotorAdapter не может сопоставить
    # ActionIntent → конкретный MCP-вызов при множестве write-тулов
    # в одном домене.
    action_types: List[str] = field(default_factory=list)
    """Action labels the agent's ActionSelector can choose that this
    capability fulfils. E.g. tool_id="mcp__email__send" might have
    action_types=["notify_supplier_urgent", "send_followup"]."""
```

---

## 4. `business_hippocampus_seeder.py` — с уроком 2 применённым

Прямая копия структуры `ProcurementHippocampusSeeder`, но домен-агностична —
корпус seed-эпизодов передаётся снаружи (не хардкодится в модуле), потому
что разные роли (закупщик, продажник, бухгалтер) будут иметь разные
профессиональные интуиции.

```python
@dataclass
class SeedEpisode:
    context_tokens: List[str]
    action: str              # ОБЯЗАТЕЛЬНО — станет EventType.ACTION
    consequence: str
    reward: float
    intensity: float = 0.5
    reinforce: bool = False


class BusinessHippocampusSeeder:
    """
    Domain-agnostic seeder. Same contract as ProcurementHippocampusSeeder
    (parent spec section 5.2, sandbox v2.0):
    - does NOT touch affective_space, neuromodulators, value_layer
    - only hippocampus.store() / hippocampus.reinforce()
    - each Path carries CONTEXT tokens + exactly one ACTION event
      (lesson 2 — without this the corpus is inert)
    - Path built via reassignment, never mutation (lesson 1)
    """

    def __init__(self, episodes: List[SeedEpisode]):
        self.episodes = episodes

    def seed_agent(self, agent: Any) -> int:
        """Returns count of successfully stored episodes."""
        hippocampus = getattr(agent, "hippocampus", None)
        if hippocampus is None or not hasattr(hippocampus, "store"):
            return 0
        added = 0
        for ep in self.episodes:
            try:
                path = self._build_path(ep.context_tokens, ep.action)
                consequence = self._build_consequence(ep.consequence)
                hippocampus.store(
                    path, consequence=consequence,
                    intensity=ep.intensity, reward=ep.reward,
                )
                added += 1
                if ep.reinforce and hasattr(hippocampus, "reinforce"):
                    hippocampus.reinforce(path, consequence=consequence,
                                          intensity=ep.intensity)
            except Exception:
                continue
        return added

    def _build_path(self, tokens: List[str], action: str) -> Any:
        """Reassignment-based (lesson 1); appends one ACTION event (lesson 2)."""
        from experience import Path, Event, EventType
        path = Path()
        for token in tokens:
            path = path.add_event(Event(str(token), EventType.CONTEXT))
        path = path.add_event(Event(f"action:{action}", EventType.ACTION))
        return path

    def _build_consequence(self, label: str) -> Any:
        from experience import Event, EventType
        return Event(str(label), EventType.CONSEQUENCE)
```

### Конструктор корпуса для конкретной роли

Роль-специфичный корпус — отдельный модуль, не часть `nowa_body`:

```
nowa_roles/procurement/seed_corpus.py    → List[SeedEpisode]
nowa_roles/sales/seed_corpus.py          → List[SeedEpisode] (будущее)
```

Это переиспользует `PROFESSIONAL_SEED_EPISODES` из sandbox напрямую —
достаточно обернуть существующие dict-эпизоды в `SeedEpisode`.

---

## 5. `business_event_encoder.py` — Sensory Adapter

Отличие от родительской спецификации (раздел 3.3): добавлен
`encode_action_outcome`, симметричный `encode_tool_result`, для
построения episode-токенов **после** исполнения действия — с тем же
уроком 2 (ACTION event обязателен для эпизода, который пойдёт в
`hippocampus.store()`).

```python
class BusinessEventEncoder:
    def __init__(self, affective_mapping: Dict[str, dict]):
        self.affective_mapping = affective_mapping

    def encode_tool_result(
        self, tool_id: str, result: Dict[str, Any],
        event_classifier: Optional[Callable] = None,
    ) -> List[str]:
        """READ observation → context_events. Same as parent spec 3.3."""
        ...

    def encode_action_outcome(
        self, action_type: str, tool_result: Dict[str, Any],
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Build (episode_tokens, affective_inputs) from a completed action's
        real outcome. episode_tokens is CONTEXT-only here — the caller
        (runtime.py) appends the ACTION event, because only the caller
        knows the exact action_type that was actually realized (the
        encoder should not need to re-derive it).

        Returns affective_inputs suitable for agent.affective_space.step().
        """
        status = str(tool_result.get("status", "unknown"))
        if status in ("accepted", "success", "ok"):
            tokens = ["result:success"]
            affective = {"valence": 0.4, "arousal": 0.2, "trust": 0.3}
        elif status in ("rejected", "failed", "error"):
            tokens = ["result:failure"]
            affective = {"valence": -0.4, "arousal": 0.5, "stress": 0.4}
        else:
            tokens = ["result:unknown"]
            affective = {}
        return tokens, affective
```

---

## 6. `motor_adapter.py` — generic MotorAdapter

Прямое обобщение `ProcurementMotorAdapter` (уже реализован и проверен
в песочнице). Ключевое отличие: вместо `SUPPLIER_STRATEGIES`
(захардкоженный маппинг procurement-стратегий) — маппинг строится из
`MCPCapability.action_types`, полученных от `MCPToolRegistry`.

```python
@dataclass
class ProposedAction:
    action_id: str
    agent_id: str
    tool_id: str
    tool_params: Dict[str, Any]
    risk_level: CapabilityRisk
    intent_summary: str
    affective_context: Dict[str, float]
    estimated_cost_impact: Optional[float] = None
    requires_approval: bool = True


class MotorAdapter:
    """
    Generic body: ActionIntent → ProposedAction.

    Same discipline as ProcurementMotorAdapter (sandbox v2.0, verified):
    - NEVER calls cognitive methods (hippocampus.activate, selector, step)
    - resolve() never raises — malformed observations yield None
    - reads hippocampus.experiences read-only, only for least_used-style
      resolution when several capabilities could serve one action_type
    """

    def __init__(self, tool_registry: MCPToolRegistry):
        self.tool_registry = tool_registry

    def resolve(
        self,
        action_type: str,
        observations: Dict[str, Any],
        hippocampus: Any = None,
    ) -> Optional[ProposedAction]:
        try:
            capability = self._capability_for_action(action_type)
            if capability is None:
                return None
            params = self._build_params(capability, action_type, observations)
            if params is None:
                return None
            return ProposedAction(
                action_id=self._new_id(),
                agent_id=str(observations.get("agent_id", "")),
                tool_id=capability.tool_id,
                tool_params=params,
                risk_level=capability.risk_level,
                intent_summary=self._summarize(action_type, params),
                affective_context=dict(observations.get("affect_snapshot", {})),
                estimated_cost_impact=self._estimate_cost(capability, params),
                requires_approval=capability.requires_approval,
            )
        except Exception:
            return None

    def _capability_for_action(self, action_type: str) -> Optional[MCPCapability]:
        matches = [
            c for c in self.tool_registry._capabilities.values()
            if action_type in c.action_types
        ]
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        # Несколько capability на один action_type — детерминированный
        # выбор по алфавиту tool_id, не случайный. Roles с несколькими
        # эквивалентными тулами должны явно приоритизировать через
        # порядок регистрации, не полагаться на этот tie-break.
        return sorted(matches, key=lambda c: c.tool_id)[0]

    def _build_params(
        self, capability: MCPCapability, action_type: str,
        observations: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Domain-specific parameter resolution. Generic MotorAdapter provides
        no default implementation — subclass per role (see
        ProcurementMotorAdapter as the reference: _select_priority_product,
        _select_most_reliable, _calculate_qty, _cap_qty_to_budget all live
        here for the procurement role specifically).
        """
        raise NotImplementedError(
            "Subclass MotorAdapter per role and implement _build_params; "
            "see ProcurementMotorAdapter (sandbox v2.0) as reference."
        )

    def _summarize(self, action_type: str, params: dict) -> str:
        return f"{action_type}({', '.join(f'{k}={v}' for k, v in params.items())})"

    def _estimate_cost(self, capability, params) -> Optional[float]:
        return None  # role-specific override

    def _new_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
```

**Важно:** `MotorAdapter` в этой фазе — абстрактный базовый класс.
`ProcurementMotorAdapter` из песочницы становится первой конкретной
реализацией `_build_params` — при переносе в Фазу 3 (реальный MCP)
переиспользуется структура, но `stock_obs`/`supplier_obs` заменяются
на `observations` из реальных MCP READ-тулов.

---

## 7. `approval_gate.py` + `hard_constraints.py`

Без существенных изменений относительно родительской спецификации
(разделы 6.2, 6.3) — этот код уже был специфицирован достаточно строго
и не имеет уроков из песочницы (approval gate — единственный компонент,
которого в песочнице сознательно не было, раздел 0 sandbox-спеки: "здесь
нет реальных денег — place_order исполняется немедленно").

Одно дополнение — `feedback_loop.py` (раздел 6.4 родительской спеки)
теперь должен строить эпизод через тот же паттерн, что и
`_store_order_experience` в песочнице:

```python
def apply_feedback_to_agent(agent: Any, record: ApprovalRecord,
                            encoder: BusinessEventEncoder) -> None:
    """
    Direct analogue of SandboxTrainer._store_order_experience (v2.0).
    Called AFTER the human's decision AND (if approved) the real MCP
    execution result — never before, per lesson 3 (decision_only split).
    """
    reward = approval_to_reward(record)
    tokens, affective_inputs = encoder.encode_action_outcome(
        record.proposed_action.intent_summary,
        record.execution_result or {"status": record.status.value},
    )

    affective_space = getattr(agent, "affective_space", None)
    if affective_space is not None and affective_inputs:
        step_fn = getattr(affective_space, "step", None)
        if callable(step_fn):
            step_fn(inputs=affective_inputs)

    hippocampus = getattr(agent, "hippocampus", None)
    if hippocampus is not None and hasattr(hippocampus, "store"):
        from experience import Path, Event, EventType
        path = Path()
        for t in tokens:
            path = path.add_event(Event(t, EventType.CONTEXT))
        # ACTION event — lesson 2 applies here too.
        path = path.add_event(Event(
            f"action:{record.proposed_action.tool_id}", EventType.ACTION
        ))
        consequence = Event(
            "approved" if reward > 0 else "rejected", EventType.CONSEQUENCE
        )
        hippocampus.store(path, consequence=consequence,
                          intensity=abs(reward), reward=reward)
```

---

## 8. `mock_mcp.py` — тестовый MCP без реального сервера

Раз реальных MCP-серверов пока нет (только запланировано подключение
к 1С), Фаза 1 должна быть полностью тестируема без них.

```python
class MockMCPTool:
    """One fake tool: deterministic responses for tests, keyed by input hash."""

    def __init__(self, tool_id: str, response_fn: Callable[[dict], dict]):
        self.tool_id = tool_id
        self.response_fn = response_fn
        self.call_log: List[dict] = []

    def __call__(self, params: dict) -> dict:
        self.call_log.append(dict(params))
        return self.response_fn(params)


class MockMCPClient:
    """
    Registers MockMCPTool instances and dispatches by tool_id — this is
    the `mcp_executor: Callable[[str, dict], Any]` that ApprovalGate expects.
    Never touches a network; safe for CI without real MCP servers.
    """

    def __init__(self):
        self.tools: Dict[str, MockMCPTool] = {}

    def register(self, tool: MockMCPTool) -> None:
        self.tools[tool.tool_id] = tool

    def execute(self, tool_id: str, params: dict) -> dict:
        tool = self.tools.get(tool_id)
        if tool is None:
            return {"status": "error", "reason": f"unknown_tool:{tool_id}"}
        return tool(params)
```

Ролевые тесты (procurement и далее) строят набор `MockMCPTool`,
имитирующих `get_stock_levels`, `create_purchase_order` и т.д., с
поведением, повторяющим `ProcurementWorld` из песочницы — это позволяет
переиспользовать уже накопленную интуицию о сценариях (stockout,
supplier_defaulted) без реального MCP.

---

## 9. `runtime.py` — оркестратор полного pipeline

Аналог `SandboxTrainer._run_single_quarter`, но для живого/полу-живого
режима: не квартал за 90 тиков, а один цикл на входящее событие
(например, ежедневный cron, или триггер на новое MCP-уведомление).

```python
class BusinessAgentRuntime:
    """
    Live/semi-live pipeline orchestrator. One call to run_cycle() =
    one full pass: observe → decide → resolve → gate → (execute) →
    feedback → store.

    Sleep is NOT triggered here automatically — a host process (cron,
    scheduler) calls agent.sleep_manager.sleep_cycle() on its own
    schedule, exactly as SandboxTrainer does on sleep_every_n_days,
    but decoupled from run_cycle() since live cadence is host-defined,
    not a fixed N-day sandbox quarter.
    """

    def __init__(
        self,
        agent: Any,
        tool_registry: MCPToolRegistry,
        motor_adapter: MotorAdapter,
        approval_gate: ApprovalGate,
        encoder: BusinessEventEncoder,
    ):
        self.agent = agent
        self.tool_registry = tool_registry
        self.motor_adapter = motor_adapter
        self.approval_gate = approval_gate
        self.encoder = encoder

    def run_cycle(self, observations: Dict[str, Any]) -> dict:
        """
        observations: pre-fetched results of READ_ONLY MCP calls, built
        by the host BEFORE calling run_cycle — this runtime does not
        itself decide which sensors to poll; that's a host/scheduling
        concern, same separation as ProcurementWorld.observe_* being
        called by SandboxTrainer, not by the agent.
        """
        context_events = self._build_context(observations)

        step_fn = getattr(self.agent, "step", None)
        action_intent = step_fn(context_events, decision_only=True) \
            if callable(step_fn) else "wait_and_monitor"
        action_type = self._intent_to_action_type(action_intent)

        proposed = self.motor_adapter.resolve(
            action_type, observations,
            hippocampus=getattr(self.agent, "hippocampus", None),
        )
        if proposed is None:
            return {"action_type": action_type, "proposed": None}

        record = self.approval_gate.route(proposed)
        if record.executed:
            self._apply_feedback(record)
        return {
            "action_type": action_type,
            "proposed": proposed,
            "approval_status": record.status.value,
        }

    def _build_context(self, observations: Dict[str, Any]) -> List[str]:
        tokens: List[str] = []
        for tool_id, result in observations.get("tool_results", {}).items():
            tokens.extend(self.encoder.encode_tool_result(tool_id, result))
        return tokens or ["quiet_period"]

    def _intent_to_action_type(self, action_intent: Any) -> str:
        # Identical logic to SandboxTrainer._intent_to_action_type (v2.0)
        if isinstance(action_intent, str):
            return action_intent
        if action_intent is None:
            return "wait_and_monitor"
        for attr in ("action_type", "action", "label", "name"):
            value = getattr(action_intent, attr, None)
            if isinstance(value, str):
                return value
        return "wait_and_monitor"

    def _apply_feedback(self, record: ApprovalRecord) -> None:
        from .feedback_loop import apply_feedback_to_agent
        apply_feedback_to_agent(self.agent, record, self.encoder)
```

---

## 10. Ограничения

| # | Ограничение | Наследие |
|---|---|---|
| **B1** | `MotorAdapter.resolve()` не вызывает `hippocampus.activate()`, `selector`, `agent.step()` | R2, подтверждено в sandbox v2.0 |
| **B2** | Каждый seed-эпизод обязан содержать ровно один `EventType.ACTION` токен | Урок 2 |
| **B3** | `Path` строится через переприсваивание, никогда не мутируется на месте | Урок 1 |
| **B4** | `agent.step(..., decision_only=True)` используется во всём runtime; полный `step()` без флага не вызывается в теле — обучение только в `sleep_cycle()` | Урок 3, R3/R4 |
| **B5** | `ApprovalGate` — единственная точка выполнения write-тулов; `MotorAdapter`/`runtime.py` никогда не вызывают MCP execute напрямую | Родительская спека, раздел 6.2 |
| **B6** | HIGH_WRITE/IRREVERSIBLE capability не может иметь `requires_approval=False` — `assert_stage2_invariant` вызывается в `ApprovalGate.route()` безусловно | Родительская спека, раздел 6.3 |
| **B7** | `apply_feedback_to_agent` вызывается только после реального исполнения (`record.executed`), никогда до | Урок 3 |

---

## 11. Тест-кейсы (ключевые, не исчерпывающий список — по образцу sandbox)

```python
# test_business_hippocampus_seeder.py

def test_seed_episode_without_action_raises_or_defaults():
    """SeedEpisode requires .action; a missing/empty action should not
    silently produce an inert (CONTEXT-only) path — lesson 2."""
    with pytest.raises(TypeError):
        SeedEpisode(context_tokens=["x"], consequence="y", reward=0.1)
        # action is a required positional/keyword field — dataclass enforces

def test_seeded_path_contains_action_event():
    seeder = BusinessHippocampusSeeder([
        SeedEpisode(["event:x"], action="do_thing", consequence="ok", reward=0.5)
    ])
    agent = make_test_agent()
    seeder.seed_agent(agent)
    stored_path = agent.hippocampus.experiences[0].path
    action_events = [e for e in stored_path.events if e.event_type == EventType.ACTION]
    assert len(action_events) == 1
    assert action_events[0].name == "action:do_thing"

def test_seeder_only_touches_hippocampus():
    # identical structure to sandbox test_seeder_only_touches_hippocampus
    ...


# test_motor_adapter.py

def test_resolve_never_raises_on_garbage_observations():
    adapter = SomeRoleMotorAdapter(registry)
    result = adapter.resolve("some_action", {"garbage": object()})
    assert result is None  # not an exception

def test_resolve_does_not_call_hippocampus_activate():
    mock_hippo = MagicMock()
    mock_hippo.experiences = []
    adapter.resolve("some_action", observations, hippocampus=mock_hippo)
    mock_hippo.activate.assert_not_called()


# test_approval_gate.py

def test_high_write_cannot_bypass_approval():
    cap = MCPCapability(
        tool_id="x", server_name="y", display_name="z", description="",
        risk_level=CapabilityRisk.HIGH_WRITE, requires_approval=False,
    )
    with pytest.raises(HardConstraintViolation):
        assert_stage2_invariant(cap)

def test_read_only_executes_immediately():
    gate = ApprovalGate(mcp_executor=mock_executor)
    proposed = ProposedAction(..., risk_level=CapabilityRisk.READ_ONLY,
                              requires_approval=False)
    record = gate.route(proposed)
    assert record.status == ApprovalStatus.APPROVED
    assert record.executed is True


# test_agent_pipeline_order.py — аналог sandbox test_agent_pipeline.py

def test_runtime_calls_step_before_motor_adapter():
    # same ordering assertion pattern as sandbox test_agent_step_called_before_motor_adapter
    ...

def test_feedback_applied_only_after_real_execution():
    """B7: apply_feedback_to_agent must not run before record.executed."""
    ...
```

---

## 12. Критерий готовности

- [ ] Все 9 модулей `nowa_body/` реализованы
- [ ] `MockMCPClient` покрывает минимум READ + одну WRITE-операцию для
      сквозного теста без реального MCP
- [ ] `BusinessHippocampusSeeder` — тест на ACTION event зелёный
- [ ] `MotorAdapter.resolve()` — тест на отсутствие вызовов
      `hippocampus.activate()` зелёный
- [ ] `ApprovalGate` — тест на невозможность обхода approval для
      HIGH_WRITE зелёный
- [ ] `BusinessAgentRuntime.run_cycle()` — интеграционный тест: полный
      цикл observe→decide→resolve→gate→feedback на MockMCP, без
      исключений
- [ ] Ни один компонент `nowa_body` не импортирует `nowa_sandbox` —
      это параллельный слой, не зависящий от песочницы (хотя
      переиспользует её как reference implementation для
      `ProcurementMotorAdapter._build_params`)

---

## 13. Перенос `ProcurementMotorAdapter` из песочницы (следующий шаг)

После завершения Фазы 1 (разделы 1–12) — `ProcurementMotorAdapter` из
`nowa_sandbox` рефакторится в `nowa_roles/procurement/motor_adapter.py`,
наследуясь от generic `nowa_body.MotorAdapter`:

```python
class ProcurementBodyMotorAdapter(MotorAdapter):
    def _build_params(self, capability, action_type, observations):
        # Переиспользует _select_priority_product, _select_most_reliable
        # и т.д. из sandbox ProcurementMotorAdapter почти дословно —
        # разница только в источнике observations: раньше
        # world.observe_stock_levels(), теперь результат READ_ONLY
        # MCP-вызова (например, 1С get_stock_levels), уже нормализованный
        # BusinessEventEncoder-ом к тому же словарному формату.
        ...
```

Это последний мост между песочницей и реальным телом — детали
переносятся в отдельный документ, когда появится тестовая база 1С
(Фаза 3 родительской спецификации).

---

*Спецификация Фазы 1 v1.0. Готова к передаче агенту-разработчику.*
*Уроки 1–3 из песочницы обязательны к соблюдению — они не гипотетические,
а найдены эмпирически при рефакторинге v2.0.*

---

## 14. Разграничение: реестр возможностей vs соединение с MCP

Важное уточнение, не проговорённое явно в родительской спецификации:
**`MCPToolRegistry` принадлежит агенту (суверенность), но соединение с
MCP-сервером — общая инфраструктура.**

```
Общая инфраструктура (может быть shared):
  MockMCPClient / реальный MCP transport
  ↓ (много агентов МОГУТ использовать одно соединение с 1С)

Per-agent (суверенность, никогда не shared):
  agent_A.tool_registry: MCPToolRegistry   → видит только свои capability
  agent_B.tool_registry: MCPToolRegistry   → видит только свои capability
```

Пример: закупщик и бухгалтер оба могут технически иметь доступ к одному
и тому же MCP-серверу 1С — но `tool_registry` закупщика зарегистрирует
только `get_stock_levels`, `create_purchase_order`, а `tool_registry`
бухгалтера — только `get_invoices`, `post_payment`. Это не два разных
MCP-сервера, это два разных **среза видимости** одного сервера,
определяемых на уровне `MCPToolRegistry.register()`, не на уровне
транспорта.

**Требование:** `BusinessAgentRuntime` никогда не хранит ссылку на
"глобальный" MCP client — только на `tool_registry`, который уже
отфильтрован под конкретного агента при инициализации. Это прямое
продолжение принципа суверенности (раздел 0, п.1 родительской
спецификации) на уровень интеграции с внешним миром.

---

## 15. Обновление `tool_registry.py` — индекс по `action_type`

`MotorAdapter._capability_for_action` из раздела 6 сканирует
`self.tool_registry._capabilities.values()` линейно при каждом вызове
`resolve()`. Для агента с малым числом capability (5–15 тулов) это не
проблема, но правильнее сразу построить индекс — особенно если позже
одна роль получит доступ к десяткам MCP-тулов.

```python
class MCPToolRegistry:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._capabilities: Dict[str, MCPCapability] = {}
        self._by_action_type: Dict[str, List[str]] = {}  # action_type → [tool_id, ...]

    def register(self, capability: MCPCapability) -> None:
        self._capabilities[capability.tool_id] = capability
        for action_type in capability.action_types:
            self._by_action_type.setdefault(action_type, []).append(capability.tool_id)

    def capabilities_for_action(self, action_type: str) -> List[MCPCapability]:
        """O(1) lookup instead of MotorAdapter scanning all capabilities."""
        tool_ids = self._by_action_type.get(action_type, [])
        return [self._capabilities[tid] for tid in tool_ids if tid in self._capabilities]

    # ... остальное без изменений (get, list_by_risk, list_by_domain,
    # sensory_capabilities, motor_capabilities — раздел 2.3 родительской
    # спецификации)
```

Соответствующее упрощение в `MotorAdapter._capability_for_action`:

```python
def _capability_for_action(self, action_type: str) -> Optional[MCPCapability]:
    matches = self.tool_registry.capabilities_for_action(action_type)
    if not matches:
        return None
    return sorted(matches, key=lambda c: c.tool_id)[0]
```

---

## 16. Порядок реализации

### День 1–2: capability layer (без MCP, без агента)
1. `mcp_capability.py`, `risk_classifier.py` (перенос из родительской
   спецификации разделов 2.2/2.4 без изменений)
2. `tool_registry.py` с индексом по action_type (раздел 15)
3. Тесты `test_mcp_capability.py`, `test_risk_classifier.py`,
   `test_tool_registry.py`

### День 3: sensory + seeding
4. `business_event_encoder.py`
5. `business_hippocampus_seeder.py` — **начать именно с теста на ACTION
   event** (раздел 11), прежде чем писать что-либо ещё — это единственный
   компонент, где молчаливый провал (Урок 2) незаметен без явного теста
6. `mock_mcp.py`

### День 4–5: motor + approval
7. `approval_gate.py`, `hard_constraints.py` (перенос из родительской
   спецификации 6.2/6.3, тесты обязательны — деньги/риск)
8. `motor_adapter.py` как абстрактный класс + первый конкретный
   `ProcurementBodyMotorAdapter` (раздел 13), используя `MockMCPClient`
   вместо `ProcurementWorld`
9. `feedback_loop.py`

### День 6: сборка
10. `runtime.py`
11. `test_agent_pipeline_order.py`, `test_integration.py` — полный
    цикл на MockMCP, сравнить поведение с эквивалентным днём в
    песочнице (одинаковый action_type на одинаковый context должен
    давать сопоставимое решение, если агент восстановлен из того же
    checkpoint)

### День 7: диагностика и документация
12. Прогнать `test_integration.py` многократно с разными MockMCP
    сценариями (успех, rejected, tool timeout) — убедиться, что
    `apply_feedback_to_agent` не падает ни на одном
13. Зафиксировать differences log: чем поведение `BusinessAgentRuntime`
    на MockMCP отличается от `SandboxTrainer` на `ProcurementWorld` —
    это будет чеклист для Фазы 3 (реальный MCP)

---

## 17. Открытые вопросы

### Q-Phase1-1: Кто вызывает `sleep_cycle()` в живом режиме

В песочнице `SandboxTrainer` сам решает, когда наступил
`sleep_every_n_days`. В живом режиме это должен быть внешний scheduler
(cron/Cowork task), не сам `runtime.py` — потому что "день" для реального
сотрудника не тождественен количеству вызовов `run_cycle()` (агент может
обрабатывать несколько событий в час или простаивать сутками). Нужно
решить: `sleep_cycle()` триггерится по календарному времени (раз в
сутки, ночью) или по числу накопленных эпизодов с момента последнего
сна. Рекомендация для Фазы 1 — календарный триггер снаружи `nowa_body`,
не внутри него; `nowa_body` только экспонирует `agent.sleep_manager`
для внешнего вызова.

### Q-Phase1-2: Что делать с несколькими `ProposedAction` за один цикл

Текущий `run_cycle()` производит максимум одно действие за вызов —
прямое наследование от одного тика в песочнице. В реальности за один
день закупщик может захотеть и заказать товар, и написать письмо
поставщику о задержке. Нужно решить: `agent.step()` должен вызываться
многократно за один `run_cycle()` (несколько последовательных решений
с обновлением контекста между ними) или `ActionSelector` должен уметь
возвращать несколько параллельных `ActionIntent`. Рекомендация — начать
с одного действия за цикл (как в песочнице), расширять только если
станет узким местом.

### Q-Phase1-3: Формат `intent_summary` для approval UI

`ProposedAction.intent_summary` сейчас — простая строка от `_summarize()`.
Для реального approval UI (Slack/email, раздел 6.2 родительской
спецификации) человеку нужно не "place_order_reliable_supplier(...)", а
человекочитаемое объяснение — это либо NLG-слой (раздел 4.1 родительской
спецификации), либо роль-специфичный шаблонизатор. Не блокирует Фазу 1
(MockMCP approval тестируется через сырые данные), но обязательно для
реального человеческого approval в Фазе 2.

---

## 18. Глоссарий (новые термины Фазы 1)

| Термин | Определение |
|---|---|
| **decision_only** | Флаг `agent.step()`, проходит когнитивный pipeline без записи в память/обучения |
| **ACTION event** | `EventType.ACTION` токен в `Path` — единственный тип событий, читаемый `ActionSelector.compute_pressures()` |
| **capability view** | Отфильтрованный per-agent срез `MCPToolRegistry` над общим MCP-соединением |
| **ProposedAction** | Результат `MotorAdapter.resolve()` — ещё не выполненное, но полностью параметризованное действие |
| **MockMCPClient** | Детерминированная замена реального MCP-транспорта для тестов без сети |
| **run_cycle** | Один полный проход `BusinessAgentRuntime`: observe → decide → resolve → gate → feedback |

---

## 19. Связь с изначальным запросом

Этот документ отвечает на вопрос "как сделать универсально" из самого
начала обсуждения (раздел 1 родительской спецификации, ответ на "1 конкретных
mcp серверов вот прям сейчас у меня нет, но… думаю надо бы это
универсально сделать как-то попробовать"): `MCPCapability`/`MCPToolRegistry`
не знают про 1С, email, CRM или что угодно ещё — они знают только про
абстрактный контракт "тул с риском и action_types". `MockMCPClient`
доказывает эту универсальность практически: весь `nowa_body` тестируется
и работает **до** появления первого реального MCP-соединения, и
единственное, что изменится в Фазе 3 — реализация транспорта под
`mcp_executor: Callable[[str, dict], Any]`, ожидаемого `ApprovalGate`.

---

*Спецификация Фазы 1 — финальная версия. Разделы 1–19.*
*Готова к передаче агенту-разработчику.*
