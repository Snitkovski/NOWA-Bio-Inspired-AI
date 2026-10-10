# Audit of the Agent's Autonomous Physiology

Russian version: [agent_physiology_audit.ru.md](agent_physiology_audit.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

> Energy, fatigue, internal cycles, speech, dynamic stability

---

## I. Critical problem: accelerated growth of energetic fatigue

### 1. Constant `cognitive_load = 1.0`

**Symptom:**

The agent tires even in the absence of external activity.

**Probable cause:**

`organism_step()` invokes:

```python
energy_system.update(dt, cognitive_load=1.0)
```

This imposes 100% cognitive load on every tick, independently of actual activity.

**Consequences:**

- Linear decline of energy
- Monotonic growth of fatigue
- Absence of a rest regime
- Rapid saturation of `fatigue = 1.0`

**Required check:**

Log `cognitive_load` on every tick. Determine whether it depends on:

- the internal cycle
- speech
- reasoning
- external action

**Recommended architecture:**

```python
cognitive_load = 0.0   # idle
cognitive_load = 0.3   # passive monitoring
cognitive_load = 0.7   # internal simulation
cognitive_load = 1.0   # active reasoning
```

---

## II. Check of the time scale (dt)

### 2. Incorrect time scale

**Risk:**

If `dt > 1.0` (or is unstable), energy and fatigue are scaled incorrectly.

**Check:**

- The log of `dt`
- The minimum tick interval
- Whether `last_tick` is updated correctly

**Symptom of the anomaly:**

- Energy falls faster than expected
- Fatigue reaches `1.0` within tens of seconds

---

## III. Error in the fatigue model

### 3. Fatigue lacks a complete recovery mechanism

**Check the formula:**

```python
fatigue += load * dt
fatigue -= recovery_rate * dt
```

If `recovery_rate` is too small or is absent, fatigue grows monotonically.

**Correctness criterion:**

In the idle regime, fatigue must decrease.

### 4. Possible error: fatigue depends directly on energy

If a formula of the following type is used:

```python
fatigue = 1 - energy
```

or an analogous derivative, fatigue becomes a secondary reflection of energy and loses dynamic autonomy. This produces sticking.

---

## IV. Double or triple energy expenditure

### 5. Base expenditure + cognitive load + internal cycle

**Check:**

- Base decay
- Cognitive cost
- `consume_internal_cycle()`
- Speech cost

If these are summed without normalisation, energy is expended too quickly.

### 6. No distinction between idle and active regime

The system at present likely treats:

> the mere fact of existence = 100% activity

This is methodologically incorrect. **Idle must be a cheap state.**

---

## V. Nonlinear feedback affect → drive → cycle

### 7. Possible positive feedback loop

**Circuit:**

```
affect → drive ↑
drive → internal cycle
cycle → affect impulse
affect ↑
```

If the coefficients are not balanced, saturation of drives occurs.

**Check:**

- The amplitude of affect impulses
- The weight affect → drive
- The frequency of the internal cycle

---

## VI. DriveSystem

### 8. `energy_need` coupling can induce oscillations

```python
raw = (1 - coupling) * raw + coupling * target
```

If `energy` oscillates about the threshold, the drive switches continually.

This can provoke:

- Frequent internal cycles
- Additional energy expenditure

---

## VII. InternalSimulationLoop

### 9. `threshold` is used only through DriveSystem

The loop is not autonomous: it depends on an external selector. This is not an error, but an architectural dependency.

### 10. Silent failure in `_apply_impulses`

If `affect_core` fails, the internal loop continues to run, but affect does not change. This creates a hidden degradation of behaviour.

> Failure must be logged.

---

## VIII. SpeechGovernor

### 11. `social_drive` is not discharged after speech

If speech does not reduce the drive, there is constant pressure on speech. The governor limits frequency, but the drive remains high.

**Recommended:**

```python
apply_discharge("social_drive", X)
```

---

## IX. Deadlock detection

### 12. Deadlock is almost impossible under the current logic

If recovery is invoked when `!triggered`, energy recovers and `deadlock_ticks` does not accumulate.

> Check whether deadlock is reachable at all.

---

## X. Invariants

### 13. There is no check of:

- `idle → fatigue ↓`
- `no internal cycle → cognitive_load < 0.3`
- `no speech → no speech cost`

---

## XI. Behavioural diagnostics

### 14. The agent has no metric of "physiological regime"

**Add a state log:**

```
mode:
  - idle
  - passive
  - internal_processing
  - speaking
  - low_energy
```

Without this it is impossible to determine why energy falls.

---

## XII. Principal systemic hypothesis

The most probable cause of the present problem:

1. `cognitive_load = 1.0` — always
2. `recovery_rate` — too low
3. Idle regime — absent
4. Aggregate expenditure — too large
5. Fatigue — lacks an adequate negative term

---

## XIII. Diagnostic tests

### Test 1

Set `cognitive_load = 0.0`
→ Check: does fatigue fall?

### Test 2

Disable the internal cycle
→ Check the dynamics of energy.

### Test 3

Fix `dt = 1.0`
→ Compare the dynamics.

### Test 4

Idle for 60 seconds
→ Expected: `fatigue ↓`

> If `fatigue` increases, the model is incorrect.

---

## XIV. Architectural requirement

The system must satisfy the following conditions:

| Condition | Description |
|---|---|
| Idle stability | At rest the system is stable |
| Activity induces fatigue | Load → growth of fatigue |
| Recovery at rest | Idle → decrease of fatigue |
| Impossibility of saturation without activity | Fatigue does not grow at rest |
| Bounded feedback affect→drive | No uncontrolled loops |
