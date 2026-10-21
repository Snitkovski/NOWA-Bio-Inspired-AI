# Cloud agent notes

## Serena

Serena (`serena-agent`) is installed by `.cursor/install.sh` and registered in `.cursor/mcp.json` (`serena start-mcp-server --context ide --project ${workspaceFolder}`).

At the start of a task, read the project memories under `.serena/memories/`. Start with `critical_info` (also inlined when the project activates) and `core`, then the memories `core` points at.

Use Serena's symbolic tools for navigation and edits: `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, `replace_symbol_body`, and insert-before / insert-after symbol. Use a line edit only when the change has no symbol to address.

The launch is context `ide` and agent interface `tools` (Serena 2's default REPL would expose only `serena_repl`). File reads, directory listing, and shell stay on the cloud agent's own tools. `ide-assistant` is a retired Serena context name; do not use it.
