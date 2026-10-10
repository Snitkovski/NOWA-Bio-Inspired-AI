# TODO — Phase 5.A.2

Russian version: [Phase_5A2_Online_Sleep_Plasticity_Harmonization.ru.md](Phase_5A2_Online_Sleep_Plasticity_Harmonization.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Online + Sleep Plasticity Harmonization

---

## 1. Separate online and sleep updates in ValueLayer

### Problem
At present `update_count` is shared.

### Required
In `ValueLayer`:

**Add:**
```python
self.online_update_count = 0
self.sleep_update_count = 0
```

**Change:**
- Online update → increments `online_update_count`
- Sleep replay → increments `sleep_update_count`

**Add to the snapshot:**
```python
"online_update_count": ...,
"sleep_update_count": ...
```

---

## 2. Add an update-mode flag

**Change the signature:**
```python
update(..., mode: str = "online")
```

**Inside:**
```python
if mode == "online":
    self.online_update_count += 1
elif mode == "sleep":
    self.sleep_update_count += 1
```

`SleepManager` must call:
```python
value_layer.update(..., mode="sleep")
```

---

## 3. Separate alpha for online and sleep

Add parameters in `ValueLayer`:
```python
self.alpha_online_default = 0.03
self.alpha_sleep_default = 0.08
```

**Online:**
```python
alpha = self.alpha_online_default
```

**Sleep:**
```python
alpha = self.alpha_sleep_default
```

**Aim:**  
Sleep must be an amplifying phase, but not a runaway.

---

## 4. Stability modulation of sleep alpha

In `SleepManager`, before the call to `update`:
```python
alpha_sleep_effective = alpha_sleep_default * clamp(stability_index, 0.3, 1.0)
```

If `stability_index` is low → replay is weakened.

**This links:**
- Phase 4.5 Stability
- Phase 5 Replay plasticity

---

## 5. Bound the online TD amplitude

Add clipping for the online TD error:
```python
td_error = clamp(td_error, -td_clip_online, td_clip_online)
```

**For example:**
```python
td_clip_online = 1.0
```

**So that:**  
a strong reward does not break the value space.

---

## 6. Add replay temperature decay

In `SleepManager`:

**At the start of sleep:**
```python
replay_temperature = 1.0
```

**After each replay:**
```python
replay_temperature *= 0.95
```

**Replay priority:**
```python
effective_priority = priority * replay_temperature
```

**This makes replay:**
- strong at first
- then decaying
- biologically plausible.

---

## 7. Introduce dopamine_sleep_scaling

At present dopamine is modulated only online.

**Add in `SleepManager`:**

After the replay TD update:
```python
dopamine_delta_sleep = k_sleep * td_error
```

**But:**
```python
dopamine_delta_sleep *= 0.3
```

(sleep is weaker than wakefulness)

**Apply through:**
```python
neuromodulators.apply_dopamine_delta(...)
```

---

## 8. Add a sleep learning summary

After sleep, add to the sleep statistics:
```python
{
    "total_value_delta_sleep": ...,
    "total_bg_delta_sleep": ...,
    "sleep_update_count": ...,
    "replay_blocked": ...
}
```

This is required for stability analysis.

---

## 9. Add a runaway safeguard

If during sleep:
```python
abs(total_value_delta) > value_total_cap
```

→ **stop replay immediately.**

Even if the budget is not exhausted.

---

## 10. Add a diagnostic hook

In `Agent.snapshot()`:

**Add:**
```python
"value_drift_ratio": sleep_update_count / (online_update_count + 1)
```

If `> 3.0` → a warning.

---

## Behavioural logic (what should result)

After the changes:

### Online:
- small TD updates
- dopamine reflects prediction error

### Sleep:
- replay amplifies important episodes
- plasticity depends on stability
- decay and caps are present
- there is no runaway

---

## What to verify after implementation

- A reward spike does not break value.
- Instability weakens replay.
- Many repeated rewards do not drive weights into saturation.
- Without reward, value is gradually forgotten (decay).
