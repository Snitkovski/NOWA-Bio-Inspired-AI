# NOWA Role Configurator — GUI Specification

Russian version: [NOWA_Role_Configurator_GUI_Spec.ru.md](NOWA_Role_Configurator_GUI_Spec.ru.md)

## Abstract

This specification describes the graphical role configurator as a thin visual layer over the already implemented `role_config.py`. The interface introduces no validation of its own: the fitness badge, errors, and warnings are computed by calls to `load_role_config` and `validate_role_config`. The technological assumption is Tkinter and the view/controller split already adopted in the sandbox graphics, together with the ready RU/EN language pair. If the library changes, the screens and flows stay, and the rendering layer changes. The intended user edits structured data and risk classes and does not edit YAML or Python by hand.

The information architecture consists of a role list, a five-step wizard, and an editor of six tabs: tools, action vocabulary, affective reactions, professional intuition, validation, and a dry run. The list reads the directory `nowa_roles/*/config.yaml` and stores no separate registry. Tool discovery pre-fills risk from the heuristic and requires explicit confirmation; until a live client exists, the button works against `MockMCPClient` or allows a tool to be added by hand. For a read, the approval toggle is off and disabled. For `HIGH_WRITE` and `IRREVERSIBLE` it is on and locked, which repeats `assert_stage2_invariant` at the level of the widget. Lowering risk beneath the heuristic requires a non-empty textual justification. The affect tab in this version works on the shortened valence/arousal pair; the extended axis block is hidden until a separate patch. Seed lessons are assembled by a four-step wizard and, in the main mode, do not show raw context tokens, reward, and intensity.

Constraints G1–G7 forbid constructing `MCPCapability` and `SeedEpisode` by bypassing the `role_config` parsers, block saving while `validate_role_config` raises `RoleConfigError`, and do not treat warnings as a reason to block a write. Edits live in memory until an explicit save on the validation tab; a diff is shown before the first write, and every save creates a backup of the previous version. The dry run embeds a `BodyLabSession` on the role's current unsaved state. The editor describes a role as data and does not introduce the entity of a started employee.

---

**Version:** 1.0
**Parent documents:**
- NOWA_Body_Layer_Phase1_Spec.md
- NOWA_Body_Layer_RoleConfig_Spec.md (v1.0, implemented)
**Status:** Ready for implementation
**Intended user:** an advanced user, who understands structured data, dropdowns, and the basic notions of risk, but does not write Python and does not edit YAML by hand.
**Principle:** the GUI is a thin visual layer over `role_config.py`. It contains no validation logic of its own. Every check goes through the already written `load_role_config` / `validate_role_config`. The GUI does not reinvent what already works and is covered by tests.

---

## 0. Technological decision

**Tkinter**, consistently with the sandbox infrastructure that already exists (`nowa_sandbox/gui_app.py`, `gui_controller.py`, `gui_world_tab.py`, `gui_i18n.py`, including the ready RU/EN internationalisation). This is an assumption, not a hard requirement. If another decision is taken, the screens and flows below transfer without change, and only the rendering layer changes.

New module: `nowa_body/gui_configurator.py` + `gui_configurator_controller.py` (the same view/controller split as in the sandbox GUI).

---

## 1. Information architecture

```
Главный экран (список ролей)
    │
    ├── [Новая роль] → Мастер создания роли (шаги 1–5)
    │
    └── [Открыть роль] → Редактор роли (вкладки)
            ├── Вкладка 1: Инструменты (Tools)
            ├── Вкладка 2: Словарь решений (Action Vocabulary)
            ├── Вкладка 3: Эмоциональные реакции (Affective Mapping)
            ├── Вкладка 4: Профессиональная интуиция (Seed Corpus)
            ├── Вкладка 5: Проверка (Validation & Preview)
            └── Вкладка 6: Тестовый прогон (Dry Run в песочнице)
```

The wizard that creates a new role leads the user through the same five tabs in sequence on the first filling. After creation, the role opens at once in tab mode (free navigation, not a wizard).

---

## 2. Main screen — the list of roles

```
┌─────────────────────────────────────────────────────────┐
│  NOWA Role Configurator                                   │
├─────────────────────────────────────────────────────────┤
│                                                             │
│  Роли компании:                                            │
│                                                             │
│  ┌───────────────────────────────────────────────────┐   │
│  │ 📦 Менеджер по закупкам          ✓ валиден          │   │
│  │    procurement · 4 тула · 8 уроков · изменено 2д назад │
│  └───────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────┐   │
│  │ 📦 Продажник                    ⚠ 2 предупреждения │   │
│  │    sales · 6 тулов · 3 урока · изменено вчера       │   │
│  └───────────────────────────────────────────────────┘   │
│                                                             │
│  [+ Новая роль]                                            │
│                                                             │
└─────────────────────────────────────────────────────────┘
```

The status badge (✓/⚠/✗) is computed by a call to `load_role_config` on every `config.yaml` when the list is opened. `RoleConfigError` yields ✗ with the error text in a tooltip; `warnings.warn` (unseeded action_types) yields ⚠; a clean config yields ✓. The list reads the file system at `nowa_roles/*/config.yaml` and stores no separate state.

---

## 3. Tab 1 — Tools

### Purpose

Overview and classification of the MCP tools available to the role. This corresponds to `mcp_capabilities` in the config.

### The flow “Discover tools”

```
┌─────────────────────────────────────────────────────────┐
│  Инструменты                          [🔍 Обнаружить тулы] │
├─────────────────────────────────────────────────────────┤
│  Сервер: [1c_erp ▾]                                        │
│                                                             │
│  ┌──────────────────────────────────────────────────┐    │
│  │ ☑ mcp__1c__get_stock_levels                        │    │
│  │   "Get stock levels"                               │    │
│  │   Риск: [READ_ONLY ▾]  Approval: (авто, выкл.)     │    │
│  │   Теги: [procurement ×] [+ тег]                     │    │
│  ├──────────────────────────────────────────────────┤    │
│  │ ☑ mcp__1c__create_purchase_order                   │    │
│  │   "Create purchase order"                           │    │
│  │   Риск: [MEDIUM_WRITE ▾] 💡 предложено эвристикой   │    │
│  │   Approval: ☑ Требуется одобрение (нельзя выключить*)│   │
│  │   Решения: [урочный дозаказ ×][надёжный поставщик ×]│    │
│  │             [дешёвый поставщик ×][диверсификация ×] │    │
│  │             [+ добавить решение]                    │    │
│  │   Теги: [procurement ×]                              │    │
│  ├──────────────────────────────────────────────────┤    │
│  │ ☐ mcp__1c__delete_supplier          🔴 IRREVERSIBLE │    │
│  │   "Delete supplier record"                          │    │
│  │   ⚠ Не включена в роль — тул с необратимым риском   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                             │
│  * HIGH_WRITE/IRREVERSIBLE не могут работать без            │
│    одобрения человека — это архитектурное ограничение       │
│    (assert_stage2_invariant), не настройка.                 │
└─────────────────────────────────────────────────────────┘
```

### Key UX rules

**“Discover tools”** calls `MCPToolRegistry.register_from_mcp_discovery` (Phase 3 is the real MCP client SDK; until it appears, the button works against `MockMCPClient` with a predetermined set of tools for demonstration, or allows a tool to be added by hand with the button `[+ Add a tool by hand]`).

**Risk class** is pre-filled through `classify_risk_heuristic`, but it is **never accepted automatically**. The dropdown shows the proposed value with the mark “suggested by the heuristic” and requires an explicit click from the user in order to confirm or change it. That is the same requirement already stated in the docstring of `risk_classifier.py` ("An administrator MUST confirm... never rely on the heuristic for HIGH_WRITE / IRREVERSIBLE without human review").

**The “Approval” toggle.** For READ_ONLY it is off and disabled (approval has no meaning). For HIGH_WRITE and IRREVERSIBLE it is **on and locked** (it cannot be turned off through the UI at all; this is not merely a warning). This is the UI mirror of `hard_constraints.py::assert_stage2_invariant`. The protection must be physically visible to the user, not only as an error after an attempt to save.

**Lowering risk beneath the heuristic** (for example, the user changes `delete_supplier` from IRREVERSIBLE to LOW_WRITE) requires a confirming dialogue with a mandatory text field, “why is it safe to lower this”:

```
┌─────────────────────────────────────────┐
│  ⚠ Понижение уровня риска                 │
│                                             │
│  Эвристика определила этот тул как         │
│  IRREVERSIBLE. Вы понижаете до LOW_WRITE.  │
│                                             │
│  Почему это безопасно? (обязательно)       │
│  ┌───────────────────────────────────┐   │
│  │                                     │   │
│  └───────────────────────────────────┘   │
│                                             │
│         [Отмена]      [Подтвердить]       │
└─────────────────────────────────────────┘
```

The reason is stored in the `description` field of the capability as an annotation (`"[risk downgrade justified: <text>] " + original_description`). It is not a separate field of the `MCPCapability` schema (the data contract is not made more complicated for the sake of a UI audit), and it is not lost.

**“Decisions” (`action_types`)** is a multiselect drawn from the action vocabulary already defined (tab 2). If tab 2 is still empty, a direct link to it is offered inside the same dialogue, not as a separate blocking step.

---

## 4. Tab 2 — Action vocabulary

### Purpose

Until this tab, in the earlier specifications the action vocabulary (`PROCUREMENT_ACTION_TYPES`) lived only in the code of a `MotorAdapter` subclass and of `ActionSelector`. The GUI makes it visible and editable by the user for the first time, but it **does not recreate the logic that selects parameters** (that remains the code of `MotorAdapter`, section 0 of the parent specification). This screen defines only the *names* and the *human-readable descriptions* of the decisions an employee may take. The composition of the vocabulary must match what the concrete `MotorAdapter` subclass implements.

```
┌─────────────────────────────────────────────────────────┐
│  Словарь решений                                           │
├─────────────────────────────────────────────────────────┤
│  Какие решения может принимать этот сотрудник?             │
│                                                             │
│  ┌──────────────────────────────────────────────────┐    │
│  │ urgent_reorder                                      │    │
│  │ "Срочный дозаказ" — заказать у самого быстрого       │    │
│  │  поставщика, не глядя на цену                        │    │
│  │ Используется в тулах: create_purchase_order          │    │
│  ├──────────────────────────────────────────────────┤    │
│  │ diversify_supplier                                   │    │
│  │ "Диверсификация" — заказать у наименее               │    │
│  │  используемого поставщика                             │    │
│  │ Используется в тулах: create_purchase_order          │    │
│  └──────────────────────────────────────────────────┘    │
│                                                             │
│  ⚠ wait_and_monitor всегда доступно неявно —               │
│    не требует тула, означает "ничего не делать"             │
│                                                             │
│  [+ Добавить решение]                                       │
└─────────────────────────────────────────────────────────┘
```

**An important constraint of the UI:** this screen **does not allow** an `action_type` to be created for which no `MotorAdapter` exists that can resolve it into parameters, because the GUI does not write code. A new `action_type` added here is automatically marked “requires an implementation in MotorAdapter” until a developer adds the corresponding `_select_*` method to the role’s code. That is an explicit, visible boundary between what an advanced user configures and what remains a developer’s task. The GUI does not try to hide the boundary. It shows it plainly.

---

## 5. Tab 3 — Affective reactions

### Purpose

This corresponds to `affective_mapping` in the config. The central UX difficulty is not to force the user to enter raw numbers on the axes of `AffectiveSpace`. Most users should not have to know what an axis named “AXIS_PLACEHOLDER_N” is (the section on the full set of axes is patch v1.1, the stage that follows this specification).

```
┌─────────────────────────────────────────────────────────┐
│  Эмоциональные реакции                                      │
├─────────────────────────────────────────────────────────┤
│  Что происходит?  [stock_critical_low            ▾ ]      │
│  [+ Новое событие]                                          │
│                                                             │
│  Насколько это плохо или хорошо?                            │
│  Очень плохо  ●───────○───────○  Очень хорошо              │
│               (−0.7)                                        │
│                                                             │
│  Насколько это тревожно или спокойно?                       │
│  Спокойно  ○───────○───────●  Тревожно                     │
│                            (0.8)                             │
│                                                             │
│  ┌─ Пресеты ────────────────────────────────────┐         │
│  │ [🔥 Кризис] [✓ Успех] [💔 Разрыв доверия] [😐 Рутина] │  │
│  └────────────────────────────────────────────────┘         │
│                                                             │
│  Теги: [procurement ×] [urgency ×] [risk ×] [+ тег]         │
│                                                             │
│  ▸ Продвинутая настройка (отдельные оси AffectiveSpace)     │
│                                                             │
└─────────────────────────────────────────────────────────┘
```

### Key UX rules

**Two sliders equal valence and arousal**, exactly what `_parse_affective_mapping` already supports (the shorthand form). Slider values are written directly into the `valence` and `arousal` fields of the YAML.

**Presets** are not a separate entity in the schema. They only pre-fill the sliders with sensible values (“Crisis” → valence=-0.8, arousal=0.7; “Routine” → valence=0.0, arousal=0.1, and so on), which the user may then move. This is UX convenience laid over the same shorthand schema.

**“Advanced settings”** is a block collapsed by default (progressive disclosure). It reveals explicit entry on the separate axes of `AffectiveSpace` and is the UI equivalent of the `explicit axes:` form from patch v1.1. **This block is not active until patch v1.1 is closed.** Until that moment tab 3 works only in shorthand mode, and the button “Advanced settings” is hidden entirely. It is not shown in a disabled state. Functionality that does not yet physically exist behind the control is not shown to the user.

**Automatic suggestions of events.** When the user switches to tab 3 after tools have been defined on tab 1, the GUI may propose typical events on the basis of the role’s `event_classifier` (if that classifier is already implemented in code). Static analysis is impossible for an arbitrary function, so the suggestion works only through a list of “frequently classified events” declared in advance inside `event_classifier.py`, the optional attribute `KNOWN_EVENT_NAMES: List[str]`. This is not a required part of the definition of done of this specification. It is a convenience, not a requirement.

---

## 6. Tab 4 — Professional intuition (Seed Corpus)

### Purpose — the hardest UX task of this specification

The user must not see `context_tokens`, `EventType.ACTION`, or the raw numbers of reward and intensity. The task is to turn a “lesson” into narrative form: **“When X happens → the right action is Y → because Z”**.

### The wizard “Teach a decision”

```
┌─────────────────────────────────────────────────────────┐
│  Новый урок                                    Шаг 1 из 4  │
├─────────────────────────────────────────────────────────┤
│  Когда это происходит...                                    │
│                                                             │
│  ☑ Критически низкий остаток на складе                     │
│  ☐ Поставщик подвёл (дефолт)                                │
│  ☐ Бюджет почти исчерпан                                    │
│  ☐ Заказ пришёл вовремя                                     │
│                                                             │
│  (список = события из вкладки 3 "Эмоциональные реакции")   │
│                                                             │
│                                    [Отмена]   [Далее →]     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Новый урок                                    Шаг 2 из 4  │
├─────────────────────────────────────────────────────────┤
│  ...правильное решение —                                    │
│                                                             │
│  ○ Срочный дозаказ (urgent_reorder)                         │
│  ○ Заказ у надёжного поставщика                             │
│  ○ Заказ у дешёвого поставщика                               │
│  ○ Диверсификация поставщиков                                │
│  ○ Ничего не делать, просто наблюдать                        │
│                                                             │
│  (список = "Словарь решений", вкладка 2)                    │
│                                                             │
│                              [← Назад]   [Далее →]          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Новый урок                                    Шаг 3 из 4  │
├─────────────────────────────────────────────────────────┤
│  ...потому что —                                             │
│                                                             │
│  Результат: [Остаток восстановлен          ▾]              │
│             [+ новый результат]                              │
│                                                             │
│                              [← Назад]   [Далее →]          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Новый урок                                    Шаг 4 из 4  │
├─────────────────────────────────────────────────────────┤
│  Насколько важен этот урок?                                 │
│                                                             │
│  Незначительный  ○──────●──────○  Критически важный        │
│                                                             │
│  ☑ Это критически важный урок — запомнить особенно крепко   │
│    (усиленное закрепление в памяти)                          │
│                                                             │
│  ┌─ Предпросмотр ────────────────────────────────────┐    │
│  │ Когда критически низкий остаток на складе —          │    │
│  │ правильно сделать срочный дозаказ,                    │    │
│  │ потому что это восстанавливает остаток.                │    │
│  │ Важность: высокая. Запомнить крепко: да.               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│                        [← Назад]   [Сохранить урок]          │
└─────────────────────────────────────────────────────────┘
```

### Mapping of the wizard onto `SeedEpisode`

| Wizard screen | Field of `SeedEpisode` |
|---|---|
| Step 1 (events) | `context_tokens` — each selected event is expanded into its tokens through a mapping of the kind already present in `_event_to_tokens` (event → `["event:X", "valence:...", "arousal:...", "domain:..."]`) |
| Step 2 (decision) | `action` |
| Step 3 (outcome) | `consequence` |
| Step 4, the importance slider | `reward` / `intensity` (a slider from 0 to 10 maps linearly onto 0.0–1.0 for both; they can later be split into two sliders if independent control is required) |
| Step 4, the checkbox | `reinforce` |

**The list of lessons that already exist** on tab 4 shows every `SeedEpisode` in the same narrative form as the preview of step 4, not as a raw dict or as YAML. Editing an existing lesson opens the same four-step wizard, pre-filled with the current values.

**Compatibility with `seed_corpus_module`.** If the role config uses `seed_corpus_module` (as procurement does now, section 4.2 of the parent specification), tab 4 shows the corpus in **read-only** mode, with this banner:

```
ℹ Этот словарь интуиции определён в коде (seed_corpus.py),
  не в этом конфиге. Чтобы редактировать через интерфейс,
  сначала перенесите его в inline-формат — [Перенести в конфиг →]
```

The button “Move into the config” is a one-time action. It rewrites `config.yaml` so that `seed_corpus_module` is replaced by `seed_corpus:` with the same data inline, using the existing Python list as the source and losing no lesson. After that, editing through the wizard becomes available.

---

## 7. Tab 5 — Validation and preview

### Purpose

A live call to `validate_role_config` on every change on any tab. There is no separate button “Validate”. There is a persistent status bar at the bottom of the window, and a detailed report on this tab.

```
┌─────────────────────────────────────────────────────────┐
│  Проверка конфигурации                                      │
├─────────────────────────────────────────────────────────┤
│  ✗ Найдены проблемы, требующие исправления:                │
│                                                             │
│  ┌──────────────────────────────────────────────────┐    │
│  │ ✗ Урок "срочный дозаказ" ссылается на решение       │    │
│  │   "экстренная эскалация", которого нет ни в одном    │    │
│  │   инструменте. Этот урок никогда не сработает.        │    │
│  │   → [Перейти к уроку]  [Перейти к словарю решений]   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                             │
│  ⚠ Предупреждения (не блокируют сохранение):                │
│                                                             │
│  ┌──────────────────────────────────────────────────┐    │
│  │ ⚠ Решение "диверсификация поставщиков" не имеет     │    │
│  │   ни одного урока — сотрудник начнёт без опыта        │    │
│  │   по этому решению.                                    │    │
│  │   → [Научить решению]                                 │    │
│  └──────────────────────────────────────────────────┘    │
│                                                             │
│  ✓ Проверено: 4 инструмента, 4 решения, 8 уроков            │
│                                                             │
│                              [Сохранить]  (заблокировано*)  │
│  * пока не исправлены ✗-ошибки                               │
└─────────────────────────────────────────────────────────┘
```

**Direct display of exceptions and warnings** from `role_config.py`. `RoleConfigError` becomes a red card that blocks saving. `warnings.warn(...)` (unseeded action_types) becomes a yellow card, which does not block. The error text **is restated** in the language of the domain (“decision”, “lesson”, “tool”) and is not shown as a raw Python exception. A click on “Show the technical detail” makes the original text of `RoleConfigError` available to a developer, if debugging is required.

**The button “Save”** is the only place where the GUI writes `config.yaml`. Before the write, a diff preview is shown (section 9).

---

## 8. Tab 6 — Dry run

### Purpose

The tab reuses the already written `BodyLabSession`. The GUI does not create a new test infrastructure. Tab 6 literally embeds the sandbox and the body lab in the role editor.

```
┌─────────────────────────────────────────────────────────┐
│  Тестовый прогон                                             │
├─────────────────────────────────────────────────────────┤
│  Сценарий: [Критический дефицит на складе  ▾]               │
│  [▶ Прогнать 20 тактов]                                      │
│                                                             │
│  Тик 14: действие = urgent_reorder                          │
│    → Мотор: supplier_002, sku_a, qty=45.0                    │
│    → place_order: accepted (стоимость=360.00)                │
│    → эмоциональный отклик: доверие +0.3, тревога −0.2         │
│                                                             │
│  Тик 15: действие = wait_and_monitor                        │
│                                                             │
│  [Показать полный лог]  [Показать содержимое памяти]         │
│                                                             │
│  📊 За 20 тактов: 3 заказа, 0 отклонено, накоплено 3 урока   │
└─────────────────────────────────────────────────────────┘
```

**Implementation.** A `BodyLabSession` is constructed from the current, unsaved state of the config in memory. A write to `config.yaml` is not required before the test. The session uses the `MockMCPClient` scenarios already defined in `lab_session.py` (`SCENARIO_QUIET`, `SCENARIO_STOCK_CRITICAL`, `SCENARIO_SUPPLIER_DEFAULTED`). The user can therefore “run what is there”, as the task statement put it, directly from the editing process, before saving and, still more, before a real MCP connection.

---

## 9. Saving — a diff preview

Given how many iterations of configuration edits are likely to be required, by analogy with how many patches the sandbox itself required, saving must show an explicit diff before the write:

```
┌─────────────────────────────────────────────────────────┐
│  Сохранить изменения?                                        │
├─────────────────────────────────────────────────────────┤
│  + добавлен инструмент: mcp__1c__cancel_order                │
│  ~ изменено: create_purchase_order, риск LOW_WRITE → MEDIUM │
│  + добавлен урок: "при дефолте поставщика — диверсификация"  │
│                                                             │
│              [Отмена]        [Сохранить]                    │
└─────────────────────────────────────────────────────────┘
```

**Versioning.** Every save copies the previous version of `config.yaml` to `nowa_roles/procurement/.history/config_<timestamp>.yaml` before overwriting. This is a simple file backup and does not require a git integration for the first version. The button “Change history” on the role’s main screen shows the list of versions, with a view of the diff and with rollback.

---

## 10. Constraints (obligatory)

| # | Constraint |
|---|---|
| **G1** | The GUI never calls the `MCPCapability` or `SeedEpisode` constructors directly, bypassing `role_config.py`. Every object is built through `load_role_config` or through the parsers of that same module, so that validation does not diverge |
| **G2** | The approval toggle for HIGH_WRITE and IRREVERSIBLE is physically locked in the UI (a disabled widget), not merely discouraged visually. It mirrors `assert_stage2_invariant` at the level of the interface |
| **G3** | The button “Save” is unavailable while `validate_role_config` raises `RoleConfigError`. Warnings do not block |
| **G4** | Lowering risk beneath the heuristic requires a non-empty textual justification. The form does not accept an empty string |
| **G5** | Tab 4 (Seed Corpus) never shows the user the raw `context_tokens`, `reward`, or `intensity` in the main mode. They appear only in an optional “technical” view, on an explicit request |
| **G6** | Changes on any tab are not written to the file until “Save” is pressed explicitly on tab 5. The editor works on an in-memory `RoleConfig`, and the diff is shown before the first write |
| **G7** | Every save creates a backup of the previous version before overwriting |

---

## 11. Definition of done

- [ ] A main screen with the list of roles. Status is computed through a real `load_role_config` on every config
- [ ] Tab 1 (tools): CRUD over `mcp_capabilities`. The approval toggle is locked for HIGH_WRITE and IRREVERSIBLE (test: an attempt to set `requires_approval=False` programmatically through the UI code for such a risk must be unreachable, not merely rejected)
- [ ] Tab 2 (action vocabulary): CRUD over the list of action_types, with human-readable descriptions
- [ ] Tab 3 (affect): the shorthand slider mode works. The block “advanced settings” is hidden until patch v1.1 is ready
- [ ] Tab 4 (lessons): the four-step wizard produces a valid `SeedEpisode`. Read-only mode for configs that use `seed_corpus_module`, with a button that migrates them to inline form
- [ ] Tab 5 (validation): a live call to `validate_role_config`, restated error messages, and a jump to the source of the problem
- [ ] Tab 6 (dry run): embeds `BodyLabSession` with the current unsaved state. At least one run finishes without an exception on the default scenario
- [ ] A diff preview before saving, and a backup of the previous version

---

## 12. Open questions

**Q-GUI-1: real MCP tool discovery.** The button “Discover tools” (section 3) depends on `register_from_mcp_discovery`, which in Phase 1 is left as `NotImplementedError` until a concrete MCP client SDK exists (Phase 3). Until then the button works only against `MockMCPClient` with a demonstration set. The open question is how acceptable that limitation is for the first version of the GUI, or whether Phase 3 should be brought forward in parallel at least for reading a tool schema (not for real execution).

**Q-GUI-2: migration `seed_corpus_module → inline`, and atomicity.** The button “Move into the config” (section 6) rewrites the file. It must be decided whether that button should also offer to delete the source Python module (`seed_corpus.py`) or leave it as dead code for the record. The recommendation is to leave it, and not to delete it automatically. The GUI must not touch files outside `config.yaml` and `.history/`.

**Q-GUI-3: localisation.** `gui_i18n.py` in the sandbox already supports RU/EN. It must be decided whether the new configurator uses that same infrastructure (recommended, for consistency) or a separate i18n layer.

---

*GUI configurator specification v1.0. It rests entirely on the already implemented and tested `role_config.py`. It adds no new business logic. It only visualises what already exists.*
