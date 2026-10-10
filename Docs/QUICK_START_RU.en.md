# Quick Reference: Launch and Use (v2.1)

Russian version: [QUICK_START_RU.ru.md](QUICK_START_RU.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Launching the GUI with Affective Indicators and Sleep Control

```bash
cd e:\git\NOWA-Cognitive
python src/gui.py
```

## What to See on the Screen

### Left Panel: Chat
- Dialogue with the agent
- Message history

### Right Panel: Agent State

#### Wakefulness State (v2.1 — NEW)
```
[████░░░░░░░░░░░░] 0.35
Fatigue / Wakefulness

Parameters:
- Fatigue level: 0.35 (35% exhausted)
- Reliability of cognitive functions: 0.65 (65% normal)
- Time since last sleep: 3.5 hours ago
- Time until mandatory sleep: 2.5 hours
```

**What it means:**
- **0.00-0.20** (green): Rested, alert, ready to work
- **0.20-0.50** (yellow): Slightly tired, but functioning
- **0.50-0.75** (orange): Heavily tired; capacities decline
- **0.75-1.00** (red): Critically exhausted; urgent sleep is required

**Neuromodulator modification under fatigue:**
- Cortisol: rises (stress increases)
- Norepinephrine: rises (an attempt to stay awake)
- Serotonin: falls (stability decreases)

**Effect on the PFC (prefrontal cortex):**
- Signal strength degrades with fatigue
- Noise level increases (less precision)
- Reliability of cognitive decisions declines

#### Sleep Control (v2.1 — NEW)
The side panel "Sleep control" contains three buttons:

```
Short sleep (30 min)  →  Recovery: ~10%-15%
Ordinary sleep (1 h)  →  Recovery: ~25%-35%
Long sleep (3 h)      →  Recovery: ~75%-90%
```

Pressing a button opens the consolidation dialog:
- The required number of cycles is selected automatically (1, 2, or 6)
- Additional cycles may be selected
- After sleep, all wakefulness indicators are updated

#### Affective Indicators

##### 1. Valence (Mood)
```
[████░░░░░░] 0.24
Red ← → Green
Sad       Happy
```

##### 2. Arousal (Energy)
```
[██░░░░░░░░] 0.60
Blue ← → Orange
Calm      Hyperactive
```

##### 3. Threat (Stress)
```
[████░░░░░░] 0.36
Green ← → Red
Safe        Dangerous
```

##### 4. Curiosity (Interest)
```
[██░░░░░░░░] 0.23
Grey ← → Violet
Bored     Interesting
```

##### 5. Readiness (Learnability)
```
Readiness: 0.50 (Processing)
```

## Use

### Step 1: Talk to the Agent
1. Write a message
2. Press "Send"
3. Watch the indicators update

### Step 2: Control the Agent's Sleep (NEW in v2.1)
1. **Monitor fatigue** — watch the "Wakefulness state" indicator
2. **When the level warrants it**, press a sleep button:
   - **Short sleep (30 min)** — if slightly tired (0.20-0.40)
   - **Ordinary sleep (1 h)** — if tired (0.40-0.70)
   - **Long sleep (3 h)** — if critically exhausted (0.70-1.00)
3. **The sleep-consolidation window** opens with a proposed number of cycles
4. **Confirm** — the agent sleeps and recovers
5. **The indicators update** — fatigue falls and capacities recover

**Effect of sleep on modulators:**
- Cortisol normalizes (stress falls)
- Norepinephrine is restored for wakefulness
- Serotonin restores stability

### Step 3: Rate the Reply
1. Choose a rating: (+2), (+1), (0), (-1), (-2)
2. Press "Save feedback"
3. Valence changes in response

### Step 4: Read the Analysis
1. Open the "Affective state" tab in the Inspector
2. Read what limits and what supports the agent
3. Understand why it acts as it does

## Interpreting the Indicators

### Valence
- **+0.5 to +1.0** (green): Happy, positively disposed
- **-0.3 to +0.3** (yellow): Neutral, calm
- **-1.0 to -0.3** (red): Dissatisfied, negative

### Arousal
- **0.0 to 0.5** (blue): Calm, relaxed
- **0.5 to 1.5** (yellow): Active, engaged
- **1.5 to 2.0** (orange): Hyperactive, over-aroused

### Threat
- **0.0 to 0.3** (green): Safe, stable
- **0.3 to 0.6** (yellow): Cautious, unstable
- **0.6 to 1.0** (red): Critical, in danger

### Curiosity
- **0.0 to 0.3** (black): Indifferent, uninterested
- **0.3 to 0.7** (white): Interested, exploring
- **0.7 to 1.0** (violet): Highly curious, exploring intensely

### Readiness
- **0.0-0.2** (red): Limited, under stress
- **0.2-0.7** (yellow): Processing, in progress
- **0.7-1.0** (green): Ready, stable

## Examples of Behaviour

### When a Positive Rating Is Given (+2)
```
Before: Valence: 0.00
↓
After:  Valence: 0.40 (green)
Readiness: 0.50 → 0.60
```

### When the Agent Encounters Novelty
```
Before: Curiosity: 0.00, Arousal: 0.30
↓
After:  Curiosity: 0.45 (violet), Arousal: 0.80 (orange)
```

### When a Conflict Is Detected
```
Before: Threat: 0.00, Valence: 0.30
↓
After:  Threat: 0.55 (red), Valence: -0.10 (red)
Readiness: 0.50 → 0.25 (warning)
```

## Usage Advice

- **Look at the indicators often** — they show how the agent responds
- **Give positive ratings** — help the agent acquire useful behaviour
- **Use the Inspector** — it shows the deeper causes of behaviour
- **Watch patterns** — which questions raise curiosity?
- **Monitor threat** — if it is red, the agent is under stress

## Shortcuts

| Action | Control |
|----------|--------|
| Send a message | `Enter` or the "Send" button |
| Save a rating | "Save" button |
| View memory | "Memory" tab |
| **Short sleep (30 min)** | Short-sleep button (side panel) |
| **Ordinary sleep (1 h)** | Ordinary-sleep button (side panel) |
| **Long sleep (3 h)** | Long-sleep button (side panel) |
| Affect analysis | Affective-state tab |
| Wakefulness analysis | Wakefulness tab (new in v2.1) |

## Important Files

- **Wakefulness System specification** (new in v2.1): `Phase2_Wakefulness_PFC_Extension.md`
- **Wakefulness implementation report**: `IMPLEMENTATION_REPORT_WAKEFULNESS.md`
- **Full report**: `COMPLETE_PROJECT_REPORT.en.md`
- **Russian summary**: `FINAL_SUMMARY_RU.md`
- **GUI report**: `GUI_AFFECTIVE_VISUALIZATION_REPORT.md`
- **Wakefulness source** (new): `src/wakefulness.py`
- **Affect source**: `src/affect.py`, `src/self_model.py`, `src/gui.py`
- **Wakefulness tests** (new): `tests/test_wakefulness.py`
- **Demonstration**: `wakefulness_demo.py` (new in v2.1)

## Troubleshooting

**Indicators do not update**
- Confirm that "Send" was pressed
- Check the console for errors

**The values look strange**
- This is expected. Parameters update dynamically
- See "Affective state" for the explanation

**Sleep buttons do not work** (new in v2.1)
- Confirm that they are visible in the "Sleep control" side panel
- Press a button; the sleep-consolidation console should open
- Success should appear as an update of the fatigue indicator

**The agent is too tired**
- If the indicator is red (0.75+), the agent requires urgent sleep
- Press "Long sleep (3 h)" for full recovery
- After sleep, capacities recover

**I want to see the Wakefulness source** (new in v2.1)
- `src/wakefulness.py` — the WakefulnessState class (350+ lines)
- `src/agent.py` — integration into Agent
- `src/gui.py` — visualization and sleep buttons
- `tests/test_wakefulness.py` — 31 tests for Wakefulness

**I want to run the demonstration**
- `python wakefulness_demo.py` — shows a 24-hour sleep/wake cycle
- Demonstrates neuromodulator modulation
- Shows the effect of the PFC on cognitive reliability

**I want to see the earlier systems**
- `src/affect.py` — affective state (valence, arousal, threat, curiosity)
- `src/self_model.py` — self-model (readiness)
- `src/gui.py` — interface with visualization

---

**Everything is ready. Launch the GUI and observe how the agent responds and sleeps.**

**Further reading.** See `INDEX.md` for the full documentation, or `Phase2_Wakefulness_PFC_Extension.md` for the detailed Wakefulness System specification.
