## Abstract

Russian version: [NOWA_Role_Configurator_Affective_Mapping_Spec.ru.md](NOWA_Role_Configurator_Affective_Mapping_Spec.ru.md)

Specification version 1.1 closes the deferred block of the affective-reactions tab and brings the role map to the canon of affective state. The vector A(t) contains eight axes, each on the interval [−1, 1]: valence, arousal, dominance, stress, trust, curiosity, stability, and attachment. YAML describes an impulse toward a named event, not a second vector of feeling. The host, the interface, the encoder, and the dry run do not assign axes; what is admitted is an `EmotionalImpulse` and `step`. Money and urgency are not axes and remain tags. The labels `joy`, `sadness`, `love`, `hate`, `fear`, and `pleasure_rest` are computed from the axes by the semantic-emotion layer and do not enter the selector or `SchemaBinder`. The readouts `decision_bias()` — risk, response speed, word choice, empathy, and goal priority — and `rank_weights()` — caution, cost aversion, speed seeking, reliability, novelty seeking, and assertiveness — are not set in YAML. The source of an impulse from a world event is always `external`. The employee host does not add new axes.

The implementation record of 31 August 2026 diverges from this canon. The parser `_parse_affective_mapping` keeps only valence, arousal, and tags and discards the other axes. The flag `ADVANCED_AFFECT_AXES_ENABLED` is off, and the advanced-settings button is hidden. On a matching event name, `GenericEncoder` emits context tokens and almost does not build an impulse from the map: heuristic impulses are limited to error or timeout, a rise in cost, a fall in quantity, and novelty. Role comparison on merge looks at valence, arousal, and tags, so an identical valence/arousal pair with a different stress merges without a conflict. The shortened arousal slider writes the interval [0, 1], whereas the canonical axis is [−1, 1]. Four presets are hard-wired in the controller and contain only that pair; there is no user catalogue.

Phase A, in one implementation cycle, extends parsing and round-trip writing to all eight axes and to intensity, rejects an unknown key with a `RoleConfigError` that carries the path to the field and does not drop the key silently, and makes a map that has fired emit an `EmotionalImpulse`. An omitted axis does not mean zero and is not written into the file on save. Intensity defaults to 0.35, lies in [0, 1], and on a read overlay is additionally capped at 0.4. Presets move to a separate YAML catalogue of delivered and user entries; a click fills the full canonical vector. Merge compares the full entry. Phase B, which does not block acceptance of Phase A, shows on the card of a running employee a snapshot of the eight axes, the top three semantic labels, and the numerical readouts of decision bias and ranking weights from the `EmployeeSession` that already exists, without a second state and without recreating widgets on every tick. A role dry run does not start an employee session. The specification does not admit new axes, pleasure and pain fields on the role, or a rewrite of `affective_space.py`. Outcome vectors by MCP status remain those of the platform.

---

# NOWA Role Configurator — the full canon of feelings and emotions

**Version:** 1.1  
**Status:** Ready for implementation — there are no open questions  
**Date:** 2026-08-31  
**1.1:** presets are a separate YAML catalogue (delivery + user entries),
not a dictionary in Python.  
**Target user:** the same person as for the role configurator — they describe
how an employee *reacts* to events of the world, without knowing Python and without touching
`AffectiveSpace` by hand.  
**This specification closes** the deferred block of GUI spec §5,
"Advanced settings are hidden until the v1.1 patch is closed".

**Parent documents (do not rewrite them; only keep them consistent):**

- `Docs/spec_affective_space_platform_body.md` v1.1 — P1–P11, the canon of `AXES`,
  `EmotionalImpulse`, `outcome_impulse`, `rank_weights`
- `src/affective_space.py` — the only source of truth for axes and step
- `src/semantic_emotions.py` — an interpretation of A(t), not a second state
- `NOWA_Role_Configurator_GUI_Spec.md` §5 — shorthand valence/arousal, presets
- `NOWA_Body_Layer_RoleConfig_Spec.md` — role YAML, `affective_mapping`
- `NOWA_Body_Layer_AffectiveSpace_Body_Addendum.md` — SchemaBinder reads
  `rank_weights()`, not MotorAdapter
- `NOWA_Role_Configurator_Agent_Host_Spec.md` — H9: the host does not add axes

**Principle:** the GUI remains a thin visual layer over `role_config.py`.
New logic lives in the YAML parser, in `GenericEncoder` (impulses from
the mapping), and in the preview, which *reads* `AffectiveSpace` /
`SemanticEmotionsLayer`. Nobody outside writes `axes["stress"] = …`.

Tab name in the UI: **Affective mapping** / **Эмоциональные реакции**.
Technical name of the YAML block: `affective_mapping`.

---

## 0. Why this specification

The tab now looks like a "full affect", but behind it stands a **cut-down
shorthand**. The user moves valence/arousal, whereas the NOWA canon is eight
axes, impulses, bias, ranking, and semantic labels. Without this delivery
a role cannot express what an employee can already use in the core.

| What the user sees / expects | What exists as-built (2026-08-31) |
|---|---|
| A world event → the employee's feeling | Only `valence` + `arousal` + `tags` in YAML |
| The eight axes of AffectiveSpace | The parser `_parse_affective_mapping` **discards** any other axes |
| An "Advanced settings" button | `ADVANCED_AFFECT_AXES_ENABLED = False`, the button is hidden |
| An event really *shifts* A(t) | `GenericEncoder` almost does not emit an impulse from the mapping: the overlay yields **tokens**; heuristic impulses are only error / cost↑ / quantity↓ / novelty |
| "How far this will change the decision" | There is no preview of `decision_bias()` / `rank_weights()` |
| The words "fear / joy" | There are none; and they **must not** become a control signal (P9) |
| A live A(t) of a running employee | The employee card does not show the axes |
| One's own "crisis" presets | `AFFECT_PRESETS` — four ids in Python, VA only; a user catalogue is absent |

This specification closes the gap **without rewriting the core**. There are no new axes.
There are no new emotion-controllers. MCP status outcome vectors remain
those of the platform (`AffectiveSpace.outcome_impulse`).

---

## 1. The canon that must not be broken

A copy of the rules from `spec_affective_space_platform_body.md`, worded
for this tab:

| ID | Rule | Consequence for the configurator |
|---|---|---|
| **P1** | One affect: `AffectiveSpace.axes` | YAML describes an *impulse toward an event*, not a second vector of feeling |
| **P2** | Only `EmotionalImpulse` + `step` | The host, the GUI, the encoder, and Dry Run do **not** assign axes |
| **P8** | Money / urgency are not axes. The canon of 8 names is closed | Tags `procurement, urgency, risk` remain tags. An axis `urgency` or `budget` must not be introduced |
| **P9** | No projection of feelings as control | The captions "fear", "joy" are a read-only interpretation |
| **P11** | SchemaBinder assembles params from `rank_weights()` | The tab may *show* ranking; it cannot override it in YAML |
| **H9** | The host does not add axes | `ADVANCED_AFFECT_AXES_ENABLED` opens the UI; it does not extend `AXES` |

Frozen axes, each in `[-1.0, 1.0]`:

```
valence, arousal, dominance, stress, trust, curiosity, stability, attachment
```

Readout (not YAML fields):

- `decision_bias()` → `{risk, response_speed, word_choice, empathy, goal_priority}` in `[-1, 1]`
- `rank_weights()` → `{caution, cost_aversion, speed_seek, reliability, novelty_seek, assertiveness}` in `[0, 1]`

Semantics (`src/semantic_emotions.py`): `joy`, `sadness`, `love`, `hate`,
`fear`, `pleasure_rest`. Computed from the axes. Not written to YAML. Does not go into
the selector / SchemaBinder.

`source` of an impulse from a world event: always `"external"`. The user does not
choose this. Memory/internal is the business of the core (recall, TD, conflict), not of the role.

---

## 2. Scope and phases

### Phase A — the role tab + YAML + encoder (this delivery)

Obligatory in one PR / one implementation cycle:

1. Parser and YAML round-trip: all 8 axes, `intensity`; unknown keys are an error.
2. Encoder: when the mapping *fires*, an `EmotionalImpulse` is emitted, not tokens alone.
3. Tab GUI: shorthand as now + an expandable block of 8 axes + a readout preview + semantic labels.
4. Presets — a YAML catalogue (§4.4): four factory presets in the delivery, one's own
   through the GUI; a click on a preset fills the full canonical vector.
5. Role compose compares the full entry, not only valence/arousal/tags.
6. i18n EN/RU, help, tests.
7. The flag `ADVANCED_AFFECT_AXES_ENABLED = True`.

### Phase B — a live A(t) on the employee card

The same document, a separate implementation step *after* Phase A:

- On the card of a running employee: the current 8 axes, the top-3 semantic
  labels, `decision_bias` / `rank_weights` as numbers.
- Source: `AffectiveSpace.snapshot()` of the `EmployeeSession` that already exists.
  No second state.
- Update in place (do not recreate widgets on every tick — the same
  invariant as the tick log).
- A role Dry Run still does **not** start an `EmployeeSession`.

Phase B does not block acceptance of Phase A.

### Out of scope (explicitly)

- New axes, legacy pleasure/pain as role fields, a parallel VAD.
- A YAML override of `decision_bias`, `rank_weights`,
  `_OUTCOME_STATUS_VECTORS`, `DEFAULT_DECISION_MATRIX`.
- An editor of `token_rules` / the lexicon on this tab.
- A condition language "when quantity < 10" (that is WorldState + classifier /
  lexicon, not affect).
- A rewrite of `semantic_emotions.py` / `affective_space.py`.
- An import of `nowa_sandbox` from `nowa_body`.
- Presets inside the role's `config.yaml` (that is a catalogue of the configurator, not
  role data). The encoder and compose do not read presets.

---

## 3. As-built: what is broken relative to the canon

Recorded so that the implementation fixes precisely this, and does not "add UI".

### 3.1 The parser throws axes away

`nowa_body/role_config.py` `_parse_affective_mapping` keeps only
`valence`, `arousal`, `tags`. A hand-written YAML with `stress:` / `trust:` is lost after
Save from the GUI or `load_role_config`. This violates P1: a role cannot
set a canonical impulse.

### 3.2 The encoder almost does not feed A(t) from the mapping

The live path: `GenericEncoder.encode(world_state)`
(`src/mcp_body/generic_encoder.py`).

- The overlay `_overlay_tokens`, when an event name matches in the haystack
  of results, emits `event:…`, `valence:…`, `arousal:…`, `domain:…`.
- `_impulses_for_tool` does **not** look at `affective_mapping`. Impulses:
  `outcome_impulse` on error/timeout, heuristic cost/quantity, novelty.
- `BusinessEventEncoder.encode_tool_result`, when a classifier is present, returns
  **tokens only**, `_tokens_for_mapped_event`, without an impulse.

The result: the tab configures "how to feel", and the employee at start
receives these numbers mainly as **memory/seed context**, not as an
external impulse. Phase A must close this gap.

### 3.3 The GUI and the controller know only two numbers

- The arousal slider: `from_=0.0, to=1.0` (a convenient shorthand "calm →
  alarmed"); the canon of the axis is `[-1, 1]`.
- `upsert_affective_event(name, valence, arousal, tags)` wipes
  the other axes if they are not carried through the draft.
- The presets `AFFECT_PRESETS` are hard-wired in `gui_configurator_controller.py`
  (four ids, valence/arousal only). One's own presets cannot be made;
  changing the numbers requires a code release.
- The advanced button is created and immediately hidden.

### 3.4 Compose compares an incomplete entry

`role_compose._merge_affective` conflicts if valence,
arousal, or tags differ. Two roles with the same VA but a different `stress` now
merge silently. After Phase A this is a compose conflict.

---

## 4. YAML: the `affective_mapping` schema v1.1

Backward compatibility: existing roles (valence/arousal/tags only)
are valid without edits. An omitted axis does **not** mean `0.0` — it is absent from the impulse
vector.

```yaml
affective_mapping:
  stock_critical_low:
    # shorthand (the obligatory minimum, as now)
    valence: -0.70          # [-1, 1]
    arousal: 0.80           # the shorthand slider writes [0, 1];
                            # advanced may write [-1, 1]
    tags: [procurement, urgency, risk]

    # canon (every key is optional; unknown keys are a load error)
    dominance: -0.20
    stress: 0.70
    trust: -0.10
    curiosity: 0.15
    stability: -0.40
    attachment: 0.00

    intensity: 0.35         # [0, 1], default 0.35
                            # the encoder for a READ overlay clamps ≤ 0.4 (canon §6.5)
```

### 4.1 Entry fields

| Field | Type | Default if the key is absent | Rule |
|---|---|---|---|
| `valence` | float | `0.0` | Always in YAML after Save from the GUI (shorthand is always written) |
| `arousal` | float | `0.5` | The same |
| `tags` | list[str] | `[]` | Domain labels, not axes. `urgency` / `risk` are lawful here |
| `dominance` `stress` `trust` `curiosity` `stability` `attachment` | float | *omit* | Canonical names only. Clamp `[-1, 1]` on parse |
| `intensity` | float | `0.35` | Clamp `[0, 1]` on parse. The encoder overlay additionally applies `min(value, MAX_IMPULSE_INTENSITY)` where `MAX_IMPULSE_INTENSITY = 0.4` |

Forbidden in an entry:

- any name not in `{valence, arousal, dominance, stress, trust, curiosity, stability, attachment, tags, intensity}`;
- legacy `pleasure` / `pain` / `relaxation` / … (the core still maps them inside
  `EmotionalImpulse`; the role does not: we keep YAML on the canon);
- `source`, `decision_bias`, `rank_weights`, `emotion`, `label`;
- a nested `axes:` block as a second dictionary (a flat form, as in the shorthand).

Error: `RoleConfigError` with the path
`{path}: affective_mapping['{event}'] unknown key '{key}'` — without a
silent drop. This is the same principle as for capabilities: a silently
dropped field is a class of bug the project has already caught.

Event name: a non-empty string. UI recommendation: Latin `snake_case` for
stable ids (`stock_critical_low`); the display name may be Russian
through the existing hint dictionary, **not** a separate YAML field in this
version (event id = mapping key = the token `event:{name}`).

### 4.2 What the parser must return

```python
{
  "valence": float,
  "arousal": float,
  "tags": list[str],
  # only the axes that were in the YAML:
  "stress": float,          # optional
  ...
  "intensity": float,       # always after parse (substitute the default)
}
```

Round-trip Save: do not write into the file axes that the author did not set.
If the GUI opened advanced and the user did not touch `trust`, the key
`trust` is absent from the YAML. An explicit `trust: 0.0` after the slider moved is written.

The controller `upsert_affective_event` is extended:

```text
upsert_affective_event(name, valence, arousal, tags=None, axes=None, intensity=None)
```

`axes` is a dict of a subset of the six non-VA axes (and optionally an override of
valence/arousal from advanced). Axes that were not passed are **kept** in the draft,
not zeroed. To erase an axis: `axes={"stress": None}` or a separate
`clear_affect_axis(name, axis)` — a GUI button "reset axis".

### 4.3 Compose

`_merge_affective`: two entries with the same event key are compatible if
all present canonical axes, `intensity`, and `tags` (as lists) are equal
(with a float tolerance of `1e-9`). Otherwise a `RoleConfigError` compose
conflict, as now for VA.

### 4.4 Preset catalogue (not a role)

A preset is a named impulse template. A click substitutes the numbers into
the **current event** of the role. This is UX sugar over the same entry schema as in
§4.1. The catalogue is **not** part of `affective_mapping`, does **not** travel into
the encoder, and is **not** composed across roles. The catalogue is **global**:
set it once and it is available for any role, regardless of which one
is open now. Switching roles does not change the preset strip and does not
reload the user file from the role directory.

`AFFECT_PRESETS` in Python after Phase A is **not** the source of
truth. The dictionary in code either disappears or remains a thin wrapper
`{id: vector}` over the loaded YAML — without hard-wired numbers.

#### 4.4.1 Two files

The same device as for employees: delivery in the package, the user file
beside `nowa_roles/`, and the GUI writes only there.

| Layer | Path | Who writes |
|---|---|---|
| Delivery | `nowa_body/data/affect_presets.defaults.yaml` (beside the package, in git) | The product developer. The GUI **never** writes this file |
| User | a sibling of `nowa_roles/`, by the same rule as `default_employees_root`: if `roles_root.name == "nowa_roles"`, then `roles_root.parent / "nowa_affect_presets.yaml"`, otherwise `roles_root / "nowa_affect_presets.yaml"` | The catalogue GUI. The file appears on the first save of one's own preset / overlay / hide |

If the delivery file is missing, that is a packaging bug. The GUI shows an error and
an empty button strip; the user can still create their own presets
in the user file. There is no emergency dictionary of numbers in `.py`: otherwise
there would again be two sources of truth.

If the user file is missing, the strip contains only the delivery (four
factory presets). That is a normal first launch.

Tests place `roles_root` in tmp: the user path moves into tmp,
and the delivery is read from the package (or from an explicitly passed `defaults_path`).

#### 4.4.2 YAML schema

The same for both files. Unknown keys on a preset entry are a load
error (the same 8 axes + `intensity` + captions + the service fields below).
A preset has no tags: tags belong to the role event, and a preset click does not
touch them.

```yaml
schema_version: 1
hidden: []          # user file only: ids of factory presets to
                    # hide from the strip (the delivery data themselves are not deleted)
order: []           # optional; if non-empty — the order of buttons
                    # (known ids; unknown ones are skipped; whoever is not
                    # listed goes to the tail in order of appearance)
presets:
  - id: crisis                    # ^[a-z][a-z0-9_]{1,47}$
    label_en: Crisis              # at least one of label_en / label_ru
    label_ru: Кризис
    valence: -0.80
    arousal: 0.70
    dominance: -0.25
    stress: 0.75
    trust: -0.15
    curiosity: 0.20
    stability: -0.45
    attachment: 0.00
    intensity: 0.35
```

Fields of a preset entry:

| Field | Obligation | Rule |
|---|---|---|
| `id` | yes | Unique within the file. In the user file the same `id` as in the delivery is an **overlay** (a replacement of numbers/captions), not a second button |
| `label_en` / `label_ru` | at least one | The GUI takes the caption of the current language; if it is empty, the other language; if both are empty, `id` |
| 8 axes | as in §4.1 | omit = do not substitute this axis on click (do not write 0 into the event) |
| `intensity` | no | default `0.35` |
| `hidden` on the preset itself | no | do not use it; hiding is only the top-level `hidden` list |

The delivery file has **no** `hidden` and no user ids. Four
factory ids are reserved as builtin: `crisis`, `success`,
`trust_break`, `routine`. Their vectors are the delivery contract (the §6.1 table
is the contents of `affect_presets.defaults.yaml`; a divergence is a bug).

Do not store a service flag `builtin` in YAML: it is computed at merge
(`id` is present in the delivery).

A duplicate `id` in one file → a load error.

#### 4.4.3 Merge

The module `nowa_body/affect_presets.py` (a thin layer, like `employee_config`):

1. Load the delivery. Every id → `builtin=True`.
2. If a user file exists, load it.
3. For each user preset: if the id is already in the delivery,
   replace vector/labels (it remains `builtin=True`); otherwise add it
   (`builtin=False`).
4. Subtract `hidden` from the **button strip**. A hidden factory preset remains in
   the catalogue with the action "return to the strip / reset to the delivery".
5. Order: the `order` of the user file, otherwise the delivery in its
   order, then user ids in file order.

The result of the merge is what the strip draws and what
`apply_affect_preset(event_name, preset_id)` resolves.

Writing: the user file **only**. An overlay of a factory id is written
there in full (every field the user left after editing).
Resetting a factory preset to the delivery = delete that id from `presets` and from
`hidden` in the user file. Deleting one's own preset = remove the id from
the user file. "Restore the whole delivery" = delete
the user file (with confirmation: one's own presets will disappear too —
then two buttons are better: "reset factory overlays" versus "delete all
of one's own"). The Phase A minimum: reset **one** id at a time and delete one's own;
a full wipe of the user file is a separate confirmation.

Save of a role and Save of the catalogue are **independent**. A preset click dirties the role
draft (`dirty=True`). An edit of the catalogue writes the catalogue
YAML at once (or on OK of the dialogue) and does not require Save of the role.

#### 4.4.4 Application to an event

`apply_affect_preset` copies into the current event:

- every axis that is present in the preset (including an explicit `0.0`);
- `intensity`;
- it does **not** copy tags;
- axes that are absent from the preset are **not** wiped in the event (as with upsert
  of extra axes).

If what is needed is "as in the preset, without tails from the past", the catalogue
dialogue has an option "replace all axes" (first `clear` the extras, then
the copy). The default click on the strip is the soft substitution of the section above, as now
the sliders move while tags live a life of their own.

There is no `preset_id` in the event YAML: after a click the event does not remember the template.
This is intentional (the event is the truth of the role; the catalogue may be changed tomorrow).

---

## 5. Encoder: mapping → impulse

### 5.1 Impulse contract

When an event `E` from `affective_mapping` has **fired** on this tick:

```python
impulse = {
    "vector": {axis: value, ...},  # only the axes set in the entry
                                   # valence/arousal always, if they are in the entry
                                   # (after parse they always are)
    "intensity": min(entry.intensity, MAX_IMPULSE_INTENSITY),
    "source": "external",
}
```

Then the existing `apply_impulses(..., source="external")` →
`AffectiveSpace.step(external_impulses=...)`. No assignments.

Do not substitute omitted axes as zeros in `vector`: a zero in the vector is an
impulse "stay near zero on this axis"; omit is "do not touch".

### 5.2 When an event counts as having fired

Do not introduce a new condition language. Three existing channels, all of which must
emit **both tokens and an impulse**:

1. **Classifier (preferred).**
   `event_classifier(tool_id, payload)` returned the name `E`, and `E` is in
   the mapping. Today `BusinessEventEncoder.encode_tool_result` returns
   tokens only — Phase A adds an impulse on the path that the runtime actually
   uses (`encode` / encode+classifier), and does not leave the
   impulse only on a dead branch.

2. **Overlay haystack (as-built GenericEncoder).**
   The name `E` or `event:E` occurs in the serialised READ results
   of the tick. Do not change token behaviour. Add a parallel
   `_impulses_for_mapped_event(E)`.

3. **WRITE outcome.**
   Do not duplicate the event mapping. Status → only
   `AffectiveSpace.outcome_impulse(status, magnitude)`. The role does not
   override the table of §6.6. On the tab there is a read-only note
   (see §6.4).

One event on one tick is one overlay impulse (not twice, from
classifier and haystack). Deduplicate by the name `E` inside `encode()`.

Canon §6.5: READ impulses are weak, `intensity ≤ 0.4`. Heuristic
cost/quantity/novelty **remain**. The mapping is an overlay *addition*, not
a replacement of the heuristics. If both a heuristic and a mapping fired on a tick, both
go into `step` (the sum of impulses is the ordinary behaviour of the core).

### 5.3 Tokens

Compatibility of seed / memory:

- as now: `event:{E}`, `valence:{bucket}`, `arousal:{bucket}`,
  `domain:{tag}`;
- do **not** proliferate `emotion:fear` as a control token (P9);
- additional axes **need not** become tokens in Phase A
  (the impulse carries the numbers). Optionally, if search over memory is needed:
  `axis:{name}:{low|mid|high}` with the same thresholds as valence
  (`|x|≤0.15` mid, otherwise the sign). Not a blocker of acceptance.

`event_to_tokens` (the seed wizard) remains on valence/arousal/tags, so as
not to break the existing corpus. Extra axes are not required in a lesson: the lesson
remembers the *event*; A(t) will be shifted by the encoder at runtime.

### 5.4 Preview ≠ live A(t)

Preview on the tab (Phase A):

1. A new `AffectiveSpace()` (all axes 0, except the core's internal baselines).
2. One `step(external_impulses=[impulse_from_entry])`.
3. Show `axes`, `decision_bias()`, `rank_weights()`.
4. `SemanticEmotionsLayer().update_from_space(space)` → top-3 by
   `activation`, caption "interpretation, not a command".

Caption in the UI: this answers the question "if the employee was at rest and only
this event happened, where the decision will shift". This is **not** the current feeling
of a live employee (Phase B).

The preview implementation is a function in `gui_configurator_controller` (or a thin
helper beside the encoder) that imports `AffectiveSpace` /
`SemanticEmotionsLayer` from the core. The GUI does not compute bias formulae itself.

---

## 6. GUI of the "Affective mapping" tab

The target user is not obliged to know the names of the axes. Therefore **two layers**,
as GUI spec §5 promised, but advanced is no longer hidden.

```
┌─────────────────────────────────────────────────────────────┐
│  What is happening?  [stock_critical_low               ▾]   │
│  [+ New event]  [Delete event]                              │
│                                                             │
│  How bad or how good is this?                               │
│  Very bad     ●────────────○  Very good        (−0.70)     │
│                                                             │
│  How alarming or how calm is this?                          │
│  Calm         ○────────────●  Alarming          (0.80)     │
│                                                             │
│  ┌ Presets ───────────────────────────────────────────────┐ │
│  │ [Crisis] [Success] [Trust break] [Routine]             │ │
│  │ [+ Save as preset]  [Catalogue…]                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Tags: procurement, urgency, risk                  [+ tag]  │
│                                                             │
│  ▾ Advanced settings (AffectiveSpace axes)                  │
│     dominance   [────●────]  −0.20                          │
│     stress      [───────●─]   0.70   [reset]                │
│     trust       [────●────]  −0.10                          │
│     curiosity   [──●──────]   0.15                          │
│     stability   [───●─────]  −0.40                          │
│     attachment  [────●────]   0.00                          │
│     arousal*    [────────●]   0.80   (*full range −1…1)     │
│     Impulse strength, intensity  [──●──────]  0.35          │
│                                                             │
│  ┌ If only this happens (preview) ────────────────────────┐ │
│  │ Interpretation: fear 0.62 · sadness 0.41               │ │
│  │ decision_bias: risk −0.41 · response_speed +0.52 · …   │ │
│  │ rank_weights:  caution 0.71 · speed_seek 0.64 · …      │ │
│  │ hint: labels do not command the employee               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌ Action outcome (platform, not editable) ───────────────┐ │
│  │ success → valence+ stress− trust+ …                    │ │
│  │ error   → valence− stress+ trust− …                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 6.1 Shorthand (the top, always visible)

Without a change of meaning from GUI spec §5:

- Valence slider `[-1, 1]`, step `0.05`.
- Arousal shorthand slider **`[0, 1]`**, step `0.05` — "calm /
  alarmed". It writes the field `arousal`. This is a deliberate narrowing of the UX: typical
  working events lie in non-negative arousal.
- If YAML has `arousal < 0` (set in advanced), the shorthand shows
  `0.00`, the advanced block is **expanded**, and under the slider the text: "a full
  arousal below zero is set — see advanced settings". Moving
  the shorthand slider overwrites `arousal` with a non-negative value
  (the user explicitly chose the simplified scale).

Presets on this tab are buttons from the **catalogue of §4.4**, not literals in
code. The strip is rebuilt when the catalogue changes, not on every poll
of an employee.

- A click on a button = `apply_affect_preset` on the current event (the full
  vector from the catalogue YAML; tags are not touched).
- There are as many buttons as there are visible presets after the merge. If there are more
  than ~8, the strip wraps to a second row; beyond ~16 the remainder is only in
  the "Catalogue" dialogue (on the strip, those visible by `order`).
- **Save as preset** — a dialogue: id, RU caption, EN caption.
  The vector is taken from the current sliders of the event. It writes the user
  YAML. If the id coincides with a factory one, this is an overlay (a warning:
  "it will replace the delivered Crisis until you reset"). If the id is one's own and already
  exists — confirmation of overwrite.
- **Catalogue…** — a separate window (not a role tab):

```
┌─ Catalogue of affective presets ────────────────────────────┐
│  [Crisis] builtin · overlay / as in the delivery            │
│  [Success]  builtin                                         │
│  [Month close] own                                          │
│                                                             │
│  id: month_close                                            │
│  RU: Закрытие месяца    EN: Month close                     │
│  (the same axis sliders + intensity as on the tab)         │
│                                                             │
│  [Apply to event] [Save] [Hide from the strip]              │
│  [Reset to delivery]       — builtin only                   │
│  [Delete]                  — own only                       │
│  [Restore the user file…]  (confirmation)                   │
└─────────────────────────────────────────────────────────────┘
```

The four factory presets cannot be deleted from the delivery through the GUI. They can be hidden
from the strip, overridden by numbers, and reset to the delivery file.

The table below is the **contract of the delivery file**
`affect_presets.defaults.yaml`. The implementation copies these numbers into YAML,
not into Python.

| Preset (id) | RU / EN | valence | arousal | dominance | stress | trust | curiosity | stability | attachment | intensity |
|---|---|---|---|---|---|---|---|---|---|---|
| `crisis` | Кризис / Crisis | −0.80 | 0.70 | −0.25 | 0.75 | −0.15 | 0.20 | −0.45 | 0.00 | 0.35 |
| `success` | Успех / Success | +0.80 | 0.60 | +0.20 | −0.35 | +0.40 | 0.15 | +0.25 | +0.10 | 0.30 |
| `trust_break` | Разрыв доверия / Trust break | −0.70 | 0.65 | −0.10 | 0.55 | −0.80 | 0.10 | −0.35 | −0.25 | 0.35 |
| `routine` | Рутина / Routine | 0.00 | 0.10 | 0.00 | 0.00 | 0.10 | 0.00 | +0.20 | 0.00 | 0.20 |

The numbers are recommended starting impulses, not a "scientific norm". Signs and
which axes are touched are changed in the delivery only deliberately (crisis hits
stress/stability, a break of trust hits trust, success raises trust and
lowers stress). RU/EN captions live in the catalogue YAML, not in
`gui_configurator_i18n.py` (i18n keys remain on the buttons "Catalogue",
"Save as preset", and help).

The user may move anything after a click — those are already fields
of the role event, until they press Save of the role.

The button **Delete event** (it exists in the controller now, and is absent from the UI):
confirmation, then `remove_affective_event`. Seed lessons that refer to
`event:{name}` are caught after deletion by the role validation that already exists
(not silently). This is not deletion of a preset.

### 6.2 Advanced settings

- Progressive disclosure: collapsed by default if the entry has no
  extra axis and `intensity` equals the default `0.35`. Expanded if
  extra axes are set, `arousal < 0`, or `intensity ≠ 0.35`.
- Six sliders `[-1, 1]` + an optional full arousal `[-1, 1]`
  (synchronised with the shorthand when arousal ≥ 0).
- On each extra axis: "reset" → the key disappears from YAML.
- Unsigned axes are not shown to the user as a list of
  zeros while collapsed.
- Short axis captions (i18n), not a lecture. The help button of the tab explains
  "this is a shift of feeling, not an order for the employee to be sad".

Synchronisation of shorthand ↔ advanced: an edit of valence/arousal anywhere
writes the same two fields. Extra axes are not derived from the shorthand automatically
(do not invent `stress = −valence`). If the author wants stress, they move
stress. A preset from the catalogue is the place where extra axes are filled as a package;
the author creates their own templates there, not in code.

### 6.3 Preview block

Read-only, recomputed on any movement of a slider / a preset / a change of
event (in the draft memory, before Save — like the other fields of the tab).

Do not show raw JSON. Show:

- up to three semantic labels with `activation` ≥ the layer threshold (as in
  `SemanticEmotionsLayer`; if there are none — "neutral / no label");
- the five numbers of `decision_bias`;
- the six numbers of `rank_weights`.

The wording of P9 in help and in one line under the preview: labels describe
a state; the employee does **not** branch on them.

### 6.4 Outcome note (read-only)

A compact table from canon §6.6 (`accepted/success/ok`,
`rejected/failed/error`, `timeout/unknown`). Without editing.
Why: so that the role author does not try on this tab to "draw" the success
of an order as an event `deal_closed_favorable` *instead of* the platform
outcome — both channels are lawful and **add**, if they fire together.

### 6.5 Help and i18n

Update `help.affect.body` in EN and RU:

- two sliders = a quick entry;
- advanced settings = the other axes of the canon;
- the preview = a hypothetical shift of the decision;
- presets = a catalogue; four factory presets are delivered, and one's own can be
  saved from the current sliders;
- tags are not axes;
- Save of the role and saving the catalogue are different actions;

New keys (names are indicative, in the style of the existing
`gui_configurator_i18n.py`): `affect.advanced`, `affect.reset_axis`,
`affect.intensity`, `affect.preview`, `affect.preview_hint`,
`affect.outcome_help`, `affect.delete_event`, `affect.save_preset`,
`affect.preset_catalog`, `affect.preset_builtin`, `affect.preset_overlay`,
`affect.preset_hide`, `affect.preset_restore`, plus captions of the eight axes and
of the six rank keys / five bias keys. Captions of the factory presets live in the delivery
YAML, not in i18n. EN/RU parity is obligatory for UI keys.

The flag `ADVANCED_AFFECT_AXES_ENABLED` equals `True` after Phase A. The flag itself
may be left as a switch in case of a rollback, but the default is on.
Hiding the block entirely is no longer allowed: otherwise the specification is again "not
closed".

---

## 7. Employee card (Phase B)

When `EmployeeSession` is alive:

- a "State" block on the card: the 8 axes from the current `snapshot()`, without
  sliders (this is not an editor);
- the same semantic top-3 and `rank_weights` as the preview, but from the **live**
  space;
- do not show "the employee is sad, therefore we do not write to Drive" — stress
  does not bypass ApprovalGate (P6); the UI may caption caution/speed_seek
  as an influence on choice, not as a prohibition of WRITE.

Until Phase B is done, it is enough that the card does not lie: do not show
the two sliders of the role as "the current feeling".

---

## 8. Implementation invariants

**A1.** The GUI does not validate role YAML itself. Save of a role → `load_role_config` /
`validate_role_config`. The preset catalogue is validated by
`affect_presets.py` (the same principle: an error with a path, not a silent drop).
Tk does not parse YAML by hand.

**A2.** No `axes[k] = v` in `nowa_body`, the encoder, or the employee host.

**A3.** `GenericEncoder` does not import role classes. The mapping is data.

**A4.** Dry Run does not create an `EmployeeSession` (a host invariant). The tab
preview is a separate one-shot `AffectiveSpace`, not an employee session.

**A5.** Do not import `nowa_sandbox` from `nowa_body`.

**A6.** Existing YAML without extra axes loads, encodes,
passes compose and the GUI without a migration.

**A7.** `MAX_IMPULSE_INTENSITY` (0.4) is applied to the overlay mapping on
READ. Do not apply it to a WRITE `outcome_impulse` (there the magnitude is as in
the core).

**A8.** A semantic label is not written into the `context_tokens` of a lesson and does not
become a SchemaBinder key.

**A9.** Numbers and captions of presets live in the catalogue YAML. The GUI does not
contain literals `crisis: {valence: -0.8, …}`. The button strip is built
from the merge of the delivery and the user file. The GUI does not write the delivery file.
A preset does not enter `load_role_config` / the encoder.

**A10.** The catalogue parser is the same domain module (`affect_presets.py`),
not Tk. An unknown axis in a preset is an error, as in a role.

---

## 9. Tests (DoD of Phase A)

The minimum. File names belong to the existing suites; do not spawn a third runner.

| # | What | Where |
|---|---|---|
| T1 | Parse YAML with 8 axes + intensity; omitted axes are absent from the dict | role `tests` / `test_role_config.py` |
| T2 | YAML with only VA+tags — as now, intensity default 0.35 | the same |
| T3 | An unknown key / legacy `pain:` → `RoleConfigError` | the same |
| T4 | Round-trip Save of the GUI/controller does not lose `stress` | `test_gui_configurator_controller` or the role draft |
| T5 | `upsert` of valence does not wipe a previously set `trust` | controller |
| T6 | A click on `trust_break` from the catalogue writes a low trust, not only VA | controller + `affect_presets` |
| T7 | Compose conflict if two roles have a different `stress` on the same event | `test_role_compose` |
| T8 | `GenericEncoder.encode`: on a haystack match there is an impulse with `source=external` and intensity clamped ≤ 0.4 | `tests/test_mcp_body_generic_encoder.py` (or a neighbour) |
| T9 | The classifier path emits an impulse, not tokens only; dedup of a double fire | encoder + BusinessEventEncoder |
| T10 | Heuristic cost/quantity is still emitted alongside the mapping | encoder |
| T11 | WRITE `encode_outcome` is still `outcome_impulse`; the mapping does not replace it | encoder |
| T12 | Preview helper: after the crisis preset, `rank_weights()["caution"]` is noticeably higher than for `routine` | a unit test without GUI |
| T13 | The semantic preview is non-empty for crisis, empty/neutral for a near-zero routine | unit |
| T14 | GUI: the advanced pack when the flag is True; i18n keys EN and RU exist | `test_gui_configurator_app`, if possible without a flaky Tk |
| T15 | Seed `event_to_tokens` on an old entry without extra axes — the same token set as now | controller |
| T16 | The delivery file contains exactly four ids `crisis` / `success` / `trust_break` / `routine` with the numbers of the §6.1 table | `test_affect_presets.py` |
| T17 | Without a user file, merge = delivery; the strip is in the same order | the same |
| T18 | A user overlay of `crisis` changes the vector; `builtin` remains; reset returns the delivery | the same |
| T19 | One's own preset `month_close` appears on the strip; deletion removes it; the factory presets stay | the same |
| T20 | `hidden: [routine]` removes the button without deleting the delivery; "return" clears hidden | the same |
| T21 | An unknown axis / a broken id in the catalogue → a load error, not a silent drop | the same |
| T22 | Applying a preset does not change the event's tags; Save of the role does not write `nowa_affect_presets.yaml` | controller |

Phase B (a separate DoD): in-place update of the axes on the card; the value
matches `session.affective_space` (or an equivalent accessor);
widgets are not destroy/rebuild on every poll.

Phase B (a separate DoD): in-place update of the axes on the card; the value
matches `session.affective_space` (or an equivalent accessor);
widgets are not destroy/rebuild on every poll.

---

## 10. Implementation order

1. Role parser + compose + tests T1–T3, T7 (without GUI).
2. `affect_presets.py` + delivery YAML + T16–T21.
3. Encoder impulses + dedup + T8–T11.
4. Controller: extended upsert, apply/save/hide of presets, the preview helper,
   T4–T6, T12–T13, T15, T22.
5. GUI: a strip from the merge, the catalogue dialogue, i18n, the flag True, T14.
6. Help. The procurement YAML (`nowa_roles/procurement/config.yaml`) is **not
   obliged** to grow extra axes at once — shorthand remains a valid
   demo. One may, in a single commit, enrich `stock_critical_low` to the full
   vector as a sample, without breaking seed tokens.

Do not commit until the user has asked.

---

## 11. Definition of Done (Phase A)

- The tab allows any canonical impulse toward an event to be set and
  saved in YAML so that `load_role_config` does not bite it off.
- The live encoder shifts A(t) through `EmotionalImpulse` when the event
  has fired.
- The role author sees how this will strike `decision_bias` / `rank_weights`,
  and sees semantic labels as a caption, not as a control handle.
- Four factory presets are delivered as YAML and are visible on the strip without
  a user file. The user can save their own preset,
  override a factory one, hide it, reset it, and delete their own — without editing
  Python.
- `AFFECT_PRESETS` with hard-wired numbers in code is no longer the source of truth.
- The MCP outcome remains that of the platform.
- Old roles and the seed corpus are green.
- EN/RU parity of help and of axis captions.
- Tests T1–T22 are green.

Phase B is not part of this DoD.

---

## 12. Alignment with what is already written

| Document | What changes in meaning |
|---|---|
| GUI spec §5 | The prohibition "hide advanced until v1.1" is lifted. Shorthand remains. Presets are no longer "four buttons from code", but the catalogue of §4.4 |
| RoleConfig spec §2 `affective_mapping` | Extended by axis fields and `intensity`; VA+tags are not removed. Presets do not enter the role |
| Platform body §6.5 | The overlay mapping receives an impulse, as was promised by the phrase "a YAML overlay may remain" — at present the overlay has no impulse |
| Agent Host H9 | Observed: we do not add axes |
| Body addendum | SchemaBinder still reads `rank_weights()` of the live A(t); the tab only configures *where* external impulses will come from |

End of the specification.
