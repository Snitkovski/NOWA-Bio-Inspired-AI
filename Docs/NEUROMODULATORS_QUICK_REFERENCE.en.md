# Neuromodulators — Quick Reference

Russian version: [NEUROMODULATORS_QUICK_REFERENCE.ru.md](NEUROMODULATORS_QUICK_REFERENCE.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

**Placement:** Right sidebar of the GUI  
**Implementation file:** `src/neuromodulators.py`  
**Tests:** `tests/test_neuromodulators.py`, `tests/test_neuromodulators_phase2.py`, `tests/test_neuromodulator_integration.py`, `tests/test_neuromodulator_interaction_layer.py`

---

## Coupled Interaction Layer (DA/5HT/NE/ACh)

`NeuromodulatorState` contains a `NeuromodulatorField` with a matrix of inter-modulator couplings.

The dynamics in use:

```text
dM/dt = base_signal + W * (M - baseline) - decay * (M - baseline)
```

Where:
- `M = [DA, 5HT, NE, ACh]`
- `base_signal` is assembled from reward/novelty/conflict plus ACh novelty/repetition
- the baseline-centered variant holds a stable resting state

---

## Four Neuromodulators

### DA — Dopamine
**Reinforcement and value**

| Parameter | Value |
|----------|----------|
| Increases when | Positive reward (reward > 0) |
| Affects | Strengthening of cortical patterns during sleep |
| Range | 0.0 – 1.0 |
| Growth coefficient | +0.25 when reward > 0; −0.10×\|reward\| when reward < 0 |
| Decay | Exponential toward 0.1 |

**Effect during sleep:**
```
pattern.strength *= (1.0 + dopamine * 0.05)
```

---

### NE — Norepinephrine
**Mobilization and surprise**

| Parameter | Value |
|----------|----------|
| Increases when | Novelty > 0 or Conflict > 0 |
| Affects | Formation of additional chains, exploration |
| Range | 0.0 – 1.0 |
| Growth coefficient | +0.3 per unit of novelty |
| Decay | Exponential toward 0.1 |

**Effect during sleep (when NE > 0.4):**
```
_form_chains_from_recent(max_len=9)  # вместо обычных 7
```

---

### 5-HT — Serotonin
**Stability and satiation**

| Parameter | Value |
|----------|----------|
| Increases when | Positive reward without conflict, and stable repetition |
| Affects | Stabilization of patterns and experiences |
| Range | 0.0 – 1.0 |
| Growth coefficient | +0.05×reward (when conflict=0) +0.01 per stable repetition |
| Decay | Exponential toward 0.1 |

**Effect during sleep (when 5-HT > 0.1):**
```
for exp in hippocampus.experiences[-50:]:
    exp.stability += serotonin * 0.01
```

---

### CORT — Cortisol
**Stress and overload**

| Parameter | Value |
|----------|----------|
| Increases when | Negative reward (reward < 0) or Conflict > 0 |
| Affects | Aggressive forgetting of unstable traces |
| Range | 0.0 – 1.0 |
| Growth coefficient | +0.20×\|reward\| +0.25×conflict |
| Decay | Exponential toward 0.05 |

**Effect during sleep (when CORT > 0.4):**
```
threshold = forget_threshold + (cortisol * 0.2)
kept = [exp for exp in hippocampus if exp.stability >= threshold ...]
```

---

## Use in Code

### Initialization

```python
from neuromodulators import NeuromodulatorState

agent = Agent(...)
# agent.neuromodulators уже инициализирован
print(agent.neuromodulators.dopamine)  # 0.1 (базовый уровень)
```

### Update during a step

```python
action = agent.step(
    context=["user:hello"],
    reward=+0.5,     # → DA растёт
    novelty=0.2,     # → NE растёт
    conflict=0.0     # → CORT не растёт
)

# Нейромодуляторы обновились автоматически
print(agent.neuromodulators.dopamine)  # ~0.23
print(agent.neuromodulators.norepinephrine)  # ~0.16
```

### Application during sleep

```python
stats = agent.sleep(cycles=1)

# Во время сна:
# - DA усилит паттерны
# - NE создаст больше цепочек
# - CORT забудет нестабильные трассы
# - 5-HT стабилизирует опыты
```

### Save and load

```python
from storage import AgentStorage

storage = AgentStorage()

# Сохранить вместе с нейромодуляторами
filepath = storage.save_agent(
    hippocampus, cortex, selector,
    neuromodulators=agent.neuromodulators  # ← добавить
)

# Загрузить
storage.load_agent(
    hippocampus, cortex, selector,
    filepath,
    neuromodulators_data=saved_nm_data
)
```

---

## Example Scenarios

### Scenario 1: Successful learning

```
Step 1: reward=+1.0 → DA=0.3, 5-HT=0.15
Step 2: reward=+0.8 → DA=0.4, 5-HT=0.20
Step 3: reward=+0.9 → DA=0.5, 5-HT=0.25

During sleep:
Strong strengthening of patterns (DA effect)
Stabilization of experiences (5-HT effect)
Minimal forgetting (low CORT)
```

### Scenario 2: An unexpected event

```
Step 1: novelty=0.9 → NE=0.37
Step 2: novelty=0.7 → NE=0.44

During sleep:
More chains are formed (NE > 0.4)
Longer sequences are remembered
The system is prepared for a repetition of the unexpected
```

### Scenario 3: Stress and recovery

```
Step 1: reward=-1.0, conflict=0.8 → CORT=0.35, DA=0.05
Step 2: reward=-0.9, conflict=0.7 → CORT=0.50, DA=0.04

During sleep:
Aggressive forgetting of unsuccessful traces (CORT > 0.4)
Simplification of strategies
Retention of only the most stable traces

Recovery:
Step 3: reward=+0.5 → DA rises, CORT decays
→ The system returns to a normal state
```

---

## Test Cases

### TC-1: Repeated success

```python
for i in range(5):
    agent.step([f"context{i}"], reward=+0.8)

# Ожидание:
assert agent.neuromodulators.dopamine > 0.5
assert agent.neuromodulators.serotonin > 0.3
# ✓ Цепочки стабилизируются
# ✓ Паттерны усиливаются
```

### TC-2: A sharp surprise

```python
agent.step(["context"], novelty=0.9, conflict=0.3)

# Ожидание:
assert agent.neuromodulators.norepinephrine > 0.4
assert agent.neuromodulators.cortisol > 0.15
# ✓ NE скачок → больше исследования
# ✓ CORT растёт → немного стресса
```

### TC-3: Prolonged negativity

```python
for i in range(6):
    agent.step(["context"], reward=-0.7, conflict=0.5)

before_count = len(agent.hippocampus.experiences)
agent.sleep(cycles=1)
after_count = len(agent.hippocampus.experiences)

# Ожидание:
assert agent.neuromodulators.cortisol > 0.4
assert after_count < before_count  # забывание активировано
# ✓ CORT высокий
# ✓ Нестабильные трассы удалены
```

### TC-4: Stability

```python
for i in range(8):
    agent.step(["context"], reward=0.0, novelty=0.0, conflict=0.0)

# Ожидание:
assert agent.neuromodulators.serotonin > 0.05
assert agent.neuromodulators.dopamine == 0.1  # на базовом уровне
# ✓ 5-HT растёт (стабильность)
# ✓ DA не меняется (нет подкрепления)
```

---

## GUI Visualization

### Diagnostic block

```
Neuromodulators:
  DA: 0.42        ← dopamine (strengthening)
  NE: 0.31        ← norepinephrine (mobilization)
  5-HT: 0.58      ← serotonin (stability)
  CORT: 0.12      ← cortisol (stress)
```

**Interpretation:**
- **DA high** — successful learning, consolidation
- **NE high** — exploration, adaptation
- **5-HT high** — stability, fewer changes
- **CORT high** — stress, forgetting is active

---

## API Reference

### NeuromodulatorState

```python
class NeuromodulatorState:
    def __init__(
        self,
        dopamine: float = None,
        norepinephrine: float = None,
        serotonin: float = None,
        cortisol: float = None,
        acetylcholine: float = None,
    ):
        ...

    # Coupled dynamics entrypoint
    def update_from_signals(
        self,
        reward: float = 0.0,
        novelty: float = 0.0,
        conflict: float = 0.0,
        stable_repetition: bool = False,
        use_reward_for_dopamine: bool = True,
    ):
        ...

    # ACh helper update
    def update_acetylcholine(self, novelty: float = 0.0, stable_repetition: bool = False):
        ...

    # Temporal decay
    def decay_over_time(self, elapsed: float):
        ...

    # Serialization / persistence
    def to_dict(self) -> dict:
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "NeuromodulatorState":
        ...

    # Immutable snapshot
    def snapshot(self) -> dict:
        ...
```

---

## Frequently Asked Questions

**Q: Can I turn neuromodulators off?**  
A: Yes. Simply do not pass them to `SleepManager`:
```python
sleep_manager = SleepManager(hip, cortex)  # без neuromodulators
```

**Q: Which coefficients can I change?**  
A: The principal coefficients are set on the class `NeuromodulatorState` and on the interaction-layer parameters:
```python
NeuromodulatorState.DA_REWARD_POSITIVE
NeuromodulatorState.NE_NOVELTY
NeuromodulatorState.ACH_NOVELTY_GAIN
NeuromodulatorState.INTERACTION_DECAY
NeuromodulatorState.INTERACTION_DT
```

**Q: Why is the baseline 0.1?**  
A: It balances the absence of stimulation against complete neutrality.

**Q: When are the effects applied?**  
A: Some effects are applied already in `step()` (through `update_from_signals` and the interaction layer), and some in `sleep()` through the downstream consolidation mechanisms.

---

**Version:** 1.1  
**Updated:** March 2026
