#!/usr/bin/env bash
# Idempotent Cloud Agent install: uv on the default PATH, then the Serena CLI.
# Serena's own docs prefer `uv tool install` over `uvx --from git+...`.
# The git form re-resolves upstream on every MCP start and can time out the client.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# The uv installer drops binaries in ~/.local/bin and records that path in
# shell rc files. Cloud Agent install/start are non-interactive login shells,
# which skip Ubuntu's ~/.bashrc, so expose the tools on the default PATH.
if [[ -x "${HOME}/.local/bin/uv" ]]; then
  sudo ln -sfn "${HOME}/.local/bin/uv" /usr/local/bin/uv
fi
if [[ -x "${HOME}/.local/bin/uvx" ]]; then
  sudo ln -sfn "${HOME}/.local/bin/uvx" /usr/local/bin/uvx
fi

# Serena asks for Python 3.13. uv downloads it if the image does not have it.
uv python install 3.13

if uv tool list | grep -q '^serena-agent '; then
  uv tool upgrade serena-agent --python 3.13
else
  uv tool install --python 3.13 serena-agent
fi

if [[ -x "${HOME}/.local/bin/serena" ]]; then
  sudo ln -sfn "${HOME}/.local/bin/serena" /usr/local/bin/serena
fi

# Language-server backend, non-interactive. Safe to repeat.
serena init --language-backend LSP

# Serena's Python language server is Pyright, launched later with uvx.
# Fetch the version Serena itself pins so the first symbol tool does not
# download it on the agent's clock.
SERENA_PY="${HOME}/.local/share/uv/tools/serena-agent/bin/python"
PYRIGHT_VERSION="$("$SERENA_PY" -c 'from solidlsp.language_servers.pyright_server import PYRIGHT_VERSION; print(PYRIGHT_VERSION)')"
uvx -p 3.13 --from "pyright==${PYRIGHT_VERSION}" pyright --version

serena --version
uv --version
