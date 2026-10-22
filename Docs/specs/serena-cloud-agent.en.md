# Serena on Cursor Cloud Agents

Russian version: [serena-cloud-agent.ru.md](serena-cloud-agent.ru.md)

## Summary

Serena on Cloud Agents needs **two** dashboard-backed steps that committed repo files alone cannot satisfy:

1. **Environment Build** — run `bash .cursor/install.sh` via `.cursor/environment.json` (`install`).
2. **MCP server** — register a stdio server in the Cloud Agents MCP settings (repo `.cursor/mcp.json` is for the IDE/CLI, not Cloud Agents).

## Symptoms

- `get_mcp_tools: namespace "serena" not found`
- `serena: command not found` in the agent VM before manual install
- Build logs show only platform steps (`install-exec-daemon`, `install-cloud-agent-assets`, …) and **no** user `install` script

## Root cause (evidence)

| Check | Expected when working | Observed on failing runs |
| --- | --- | --- |
| `uv` / `serena` on PATH | `/usr/local/bin/serena` after Build | Missing until `bash .cursor/install.sh` is run manually |
| Environment Build `install` | Log line running repo install script | SYSTEM recurring Build with no `bash .cursor/install.sh` |
| Personal saved environment | `install` from repo or dashboard | Personal env wins over repo `environment.json`; `environmentJson` may be unset until linked |
| MCP namespaces | `serena` present | Only dashboard-configured MCPs (e.g. Slack, Gmail, `cursor-cloud`) |

After a successful manual install, `timeout 10 /usr/local/bin/serena start-mcp-server --context ide --agent-interface tools --project /workspace` starts and exposes tools.

## Owner checklist

### 1. Link the repo install script to the saved environment

In [Cloud Agents → Environments](https://cursor.com/dashboard/cloud-agents):

1. Open the environment used for `NOWA-Bio-Inspired-AI`.
2. Set **environment.json location** to this repository’s `.cursor/environment.json`, **or** set **Install** to `bash .cursor/install.sh` (same as the committed file).
3. If a **personal** saved environment overrides the team default, either update that personal env or remove the override so the repo file applies (resolution order: personal → team → repo file).

Trigger a **new Build** and confirm build logs include the user install finishing successfully (`serena --version` at the end of `.cursor/install.sh`).

### 2. Add Serena as a Cloud Agent stdio MCP

Cloud Agents load MCP from the dashboard ([Capabilities — MCP tools](https://cursor.com/docs/cloud-agent/capabilities)), not from `.cursor/mcp.json`.

Add a **stdio** server (team or personal, enabled for Cloud Agents):

| Field | Value |
| --- | --- |
| Name | `serena` |
| Type | `stdio` |
| Command | `/workspace/.cursor/serena-mcp.sh` |

Alternative after a successful Build:

| Field | Value |
| --- | --- |
| Command | `/usr/local/bin/serena` |
| Args | `start-mcp-server`, `--context`, `ide`, `--agent-interface`, `tools`, `--project`, `/workspace` |

Prefer the wrapper script so a missing Build fails with a clear message instead of `command not found`.

### 3. Verify in a fresh Cloud Agent

1. Start a **new** agent on `main` (or this branch after merge).
2. Ask the agent to list MCP namespaces or call `serena` / `get_symbols_overview`.
3. Optional shell checks in the agent VM: `which serena`, `serena --version`, `uv tool list | grep serena-agent`.

## Repo files (reference)

- `.cursor/environment.json` — `install`: `bash .cursor/install.sh`
- `.cursor/install.sh` — installs `uv`, `serena-agent` (Python 3.13), symlinks to `/usr/local/bin`
- `.cursor/mcp.json` — IDE/CLI MCP config (mirrors the wrapper for local dev)
- `.cursor/serena-mcp.sh` — absolute-path stdio entrypoint for dashboard MCP config
