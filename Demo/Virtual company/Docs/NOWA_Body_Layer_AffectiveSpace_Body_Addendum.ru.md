## Аннотация

English version: [NOWA_Body_Layer_AffectiveSpace_Body_Addendum.en.md](NOWA_Body_Layer_AffectiveSpace_Body_Addendum.en.md)

Дополнение от 24 августа 2026 года меняет путь мышцы протокольного тела и оставляет в силе контракт фазы 1 на формат `tool_id`, конверт поля `status`, `ApprovalGate` и `MockMCP`. Агент выбирает идентификатор инструмента записи либо действие `wait_and_monitor`. Параметры собирает `SchemaBinder` из JSON Schema, состояния мира, лексикона и весов `rank_weights()` канонического аффективного состояния A(t). Обязательная в YAML ссылка на класс моторного адаптера снимается: у роли нет отдельного класса мышцы на Python. Обратная связь записывает событие `action:{tool_id}`.

Платформенный пакет расположен в `src/mcp_body/`; демонстрационный хозяин `nowa_body` его реэкспортирует. `MotorAdapter` сохраняется как устаревшая прокладка, чтобы прежние импорты не обрывались. Контур `nowa_sandbox` этим дополнением не изменяется и остаётся отдельным от протокольного тела. Последующий сервер учётной системы спецификация определяет как ещё один `MCPTransport`: ядро, связыватель схемы и форма YAML при смене транспорта не меняются.

---

# Дополнение: канон AffectiveSpace и тело без MotorAdapter

**Дата:** 2026-08-24  
**Спецификация:** `Docs/spec_affective_space_platform_body.md` (v1.1)  
**Замещает:** MotorAdapter фазы 1 как точку расширения (`ProcurementBodyMotorAdapter`, обязательное `motor_adapter:` в YAML).

Фаза 1 (`NOWA_Body_Layer_Phase1_AsBuilt_MCP_API.md`) остаётся контрактом на
формат `tool_id`, конверт `status`, ApprovalGate и MockMCP. Путь мышцы
изменён:

| Фаза 1 | Настоящее дополнение |
|---|---|
| Агент выбирает `action_type` | Агент выбирает WRITE `tool_id` (либо `wait_and_monitor`) |
| `MotorAdapter._build_params` | `SchemaBinder` (JSON Schema + WorldState + лексикон + `rank_weights()`) |
| Обязательный YAML `motor_adapter: pkg:Class` | Отдельный класс мышцы роли на Python отсутствует |
| Обратная связь `action:{strategy}` | Обратная связь `action:{tool_id}` |

Платформенный пакет: `src/mcp_body/`. Демонстрационный хозяин (`nowa_body`) реэкспортирует его.
`MotorAdapter` сохраняется лишь как устаревшая прокладка, чтобы прежние импорты не завершались сбоем.
Песочница (`nowa_sandbox`) не изменяется.

Будущий MCP-сервер 1C является ещё одним `MCPTransport`. Ядро, связыватель и форма YAML
не изменяются.
