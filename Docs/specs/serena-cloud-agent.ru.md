# Serena в Cursor Cloud Agents

English version: [serena-cloud-agent.en.md](serena-cloud-agent.en.md)

## Кратко

Для Serena в Cloud Agents нужны **два** шага через дашборд; одних файлов в репозитории недостаточно:

1. **Environment Build** — выполнить `bash .cursor/install.sh` через `.cursor/environment.json` (`install`).
2. **MCP-сервер** — зарегистрировать stdio-сервер в настройках MCP Cloud Agents (`.cursor/mcp.json` в репо — для IDE/CLI, не для Cloud Agents).

## Симптомы

- `get_mcp_tools: namespace "serena" not found`
- `serena: command not found` в VM агента до ручного install
- В логах Build только платформенные шаги (`install-exec-daemon`, `install-cloud-agent-assets`, …), **без** пользовательского `install`

## Корневая причина (доказательства)

| Проверка | При рабочей конфигурации | На падающих прогонах |
| --- | --- | --- |
| `uv` / `serena` в PATH | `/usr/local/bin/serena` после Build | Нет до ручного `bash .cursor/install.sh` |
| `install` в Build | В логе запуск install из репо | SYSTEM recurring Build без `bash .cursor/install.sh` |
| Personal saved environment | `install` из репо или дашборда | Personal env перекрывает `environment.json` репо; `environmentJson` может быть не привязан |
| MCP namespaces | есть `serena` | Только MCP из дашборда (Slack, Gmail, `cursor-cloud`, …) |

После успешного ручного install команда `timeout 10 /usr/local/bin/serena start-mcp-server --context ide --agent-interface tools --project /workspace` стартует и отдаёт инструменты.

## Чеклист владельца

### 1. Привязать install-скрипт репозитория к saved environment

В [Cloud Agents → Environments](https://cursor.com/dashboard/cloud-agents):

1. Откройте environment для `NOWA-Bio-Inspired-AI`.
2. Укажите **environment.json location** на `.cursor/environment.json` этого репозитория **или** задайте **Install**: `bash .cursor/install.sh` (как в закоммиченном файле).
3. Если **personal** saved environment перекрывает team default — обновите personal env или снимите override, чтобы применился файл репо (порядок: personal → team → файл репо).

Запустите **новый Build** и убедитесь, что в логе install завершился успешно (в конце `.cursor/install.sh` — `serena --version`).

### 2. Добавить Serena как stdio MCP для Cloud Agent

Cloud Agents подхватывают MCP из дашборда ([Capabilities — MCP tools](https://cursor.com/docs/cloud-agent/capabilities)), не из `.cursor/mcp.json`.

Добавьте **stdio**-сервер (team или personal, включён для Cloud Agents):

| Поле | Значение |
| --- | --- |
| Name | `serena` |
| Type | `stdio` |
| Command | `/workspace/.cursor/serena-mcp.sh` |

Альтернатива после успешного Build:

| Поле | Значение |
| --- | --- |
| Command | `/usr/local/bin/serena` |
| Args | `start-mcp-server`, `--context`, `ide`, `--agent-interface`, `tools`, `--project`, `/workspace` |

Предпочтительнее wrapper: при отсутствии Build будет явная ошибка, а не `command not found`.

### 3. Проверка в новом Cloud Agent

1. Запустите **нового** агента на `main` (или на ветке после merge).
2. Попросите перечислить MCP namespaces или вызвать `get_symbols_overview`.
3. Опционально в shell VM: `which serena`, `serena --version`, `uv tool list | grep serena-agent`.

## Файлы в репозитории (справка)

- `.cursor/environment.json` — `install`: `bash .cursor/install.sh`
- `.cursor/install.sh` — `uv`, `serena-agent` (Python 3.13), symlink в `/usr/local/bin`
- `.cursor/mcp.json` — MCP для IDE/CLI (тот же wrapper для локальной разработки)
- `.cursor/serena-mcp.sh` — stdio entrypoint с абсолютными путями для MCP в дашборде
