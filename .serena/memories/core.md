Graph root. Read this first, then only the memories the task needs.

- Invariants, also inlined at project activation: `mem:critical_info`
- Language, dependencies, layout: `mem:tech_stack`
- Commands an agent will actually run: `mem:suggested_commands`
- Style and where new code goes: `mem:conventions`
- What to run before a change is done: `mem:task_completion`
- Cognitive core in `src/`: `mem:src/core`
- Demo hosts in `Demo/`: `mem:demos/core`

`src/` is not an installable package and has no third-party imports. Tests insert `src/` on `sys.path`. Each demo is a separate tree with its own `src/` and `tests/`.
