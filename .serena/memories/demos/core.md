`Demo/` is in the Serena project on purpose. Four hosts. Each creature is its own `Agent` (a subclass or a dedicated instance), never one shared mind.

- Colony: `Demo/Colony chinchillas/`. `ChinchillaAgent` subclasses `Agent`. `SimulationRunner.tick(dt)` steps every living agent with the same simulated `dt`. GUI speed multiplies the frame: `tick(real_dt * speed)` in `colony_gui.py`. Speeds include 1 and 10 (`SIM_SPEED_LEVELS` in `Demo/Colony chinchillas/src/colony_gui/config.py`). The same simulated interval must produce the same state at 1x and at 10x.
- Tamagotchi, one creature: `Demo/Tamagochi Chinchilla/`.
- Virtual company, one employee mind: `Demo/Virtual company/`.
- Warriner lexical-norm bench: `Demo/Warriner Validation/`.

Run a demo by putting that demo's `src` on `PYTHONPATH`. Do not fold demo constants back into `src/`. See `mem:critical_info` and `mem:src/core`.

Serena indexes demo source and tests. Sprites, sfx, datasets, logs, saves, checkpoints, and results are ignored.
