# Dataset Loading Error — Fixed

Russian version: [DATASET_LOADING_FIX.ru.md](DATASET_LOADING_FIX.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Problem

When an attempt was made to load experiences from a dataset (a JSON file), the interface showed the error:

```text
'Path' object has no attribute 'add'
```

The interface prefixed that exception with a load-failure notice.

## Root Cause

The file `loader.py` was using the old API:

```python
exp_path.add(Event(event_name))  # former API
```

The refactored architecture uses:

```python
exp_path = exp_path.add_event(Event(event_name, EventType.CONTEXT))  # current API
```

The reasons are:
1. `Path` is now immutable (functional style)
2. `.add_event()` returns a **new Path** and does not modify the path in place
3. Events now require an `EventType` parameter (`CONTEXT`, `ACTION`, `CONSEQUENCE`)

## Solution

### Correction of `loader.py`

**Before:**

```python
exp_path.add(Event(event_name))
exp_path.add(Event(f"action:{action_name}"))
reward = float(row.get("reward", 0))
experience = Experience(exp_path, reward)
```

**After:**

```python
exp_path = exp_path.add_event(Event(event_name, EventType.CONTEXT))
exp_path = exp_path.add_event(Event(f"action:{action_name}", EventType.ACTION))
intensity = max(0, min(2, reward + 1))  # Map reward [-1,1] to intensity [0,2]
experience = Experience(exp_path, intensity=intensity)
```

Principal changes:
1. Use `.add_event()` in place of `.add()`
2. Capture the return value: `exp_path = exp_path.add_event(...)`
3. Pass `EventType.CONTEXT` and `EventType.ACTION`
4. Import `Event` and `EventType` at the top of the module
5. Convert `reward` to `intensity` (range 0–2)

### Correction of `gui.py`

`_add_experiences_to_agent()` was updated so that it creates consequence events correctly.

**Before:**

```python
self.hippocampus.store(experience.path, experience.intensity)
```

**After:**

```python
consequence = Event('success', EventType.CONSEQUENCE)
self.hippocampus.store(experience.path, consequence=consequence, intensity=intensity)
```

Principal changes:
1. Create a proper `consequence` event with `EventType.CONSEQUENCE`
2. Pass it as a keyword argument to `hippocampus.store()`
3. Extract `intensity` from the experience, with a fallback of 1.0

## Test Results

### Dataset Loading Test

```text
Loading experiences from datasets/test.json...
   Loaded 2 experiences

Storing in hippocampus...
   ['user:кто ты', 'action:ответить_кто_я']
   ['user:привет', 'action:сказать_привет']

Agent state:
   Experiences: 2
   Patterns: 0

Running sleep consolidation...
   Sleep completed

After sleep:
   Experiences: 2
   Sleep cycles: 1

FULL INTEGRATION TEST PASSED
```

### All Tests Still Pass

```text
Ran 81 tests in 0.137s
OK
```

## Files Modified

1. **src/loader.py**
   - Added imports: `Event`, `EventType`
   - Fixed `load_experience_from_dataset()` to use the new API
   - Maps reward values to the intensity range [0, 2]

2. **src/gui.py**
   - Fixed `_add_experiences_to_agent()` so that it creates consequence events
   - Calls `hippocampus.store()` with all required parameters

## How to Use

The interface control that loads a dataset now works correctly:

1. Activate the control that loads a dataset.
2. Choose a JSON file of the form:

   ```json
   [
     {
       "context": ["user:question"],
       "action": "action_name",
       "reward": 1
     }
   ]
   ```

3. The system loads the experiences into the hippocampus.
4. The interface reports that N experiences were loaded.
5. Activate sleep in order to consolidate.

## API Reference

### Former (broken) API

```python
path = Path()
path.add(Event("name"))  # modifies in place
exp = Experience(path, reward=1.0)  # uses reward, not intensity
```

### Current (corrected) API

```python
path = Path()
path = path.add_event(Event("name", EventType.CONTEXT))  # returns a new Path
exp = Experience(path, intensity=1.0)  # uses intensity in [0, 2]
```

## Status

The error is corrected. All tests pass. Dataset loading works. The interface is functional and ready for use.

---

*Corrected: 18 January 2026*
