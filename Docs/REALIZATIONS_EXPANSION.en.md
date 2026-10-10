# Expansion of Realization Datasets

Russian version: [REALIZATIONS_EXPANSION.ru.md](REALIZATIONS_EXPANSION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Results

### Before
- 20 realizations (10 basic + 10 advanced)
- limited diversity of replies
- many repetitions

### After
- **91 realizations** (26 basic + 30 advanced + 35 extended)
- **4.5 times more variants**
- substantially better diversity and adequacy

## Distribution by Intent Type

| Type | Number of variants |
| --- | --- |
| acknowledge | 16 |
| ask_question | 11 |
| express_confusion | 11 |
| greet_user | 13 |
| help_user | 14 |
| refuse | 12 |
| respond_about_self | 14 |
| **Total** | **91** |

## What Changed

### 1. `realizations_basic.json` (was 10, became 26)

Variants were added for:
- **respond_about_self**: 4 variants (different levels of detail)
- **greet_user**: 4 variants (different contexts)
- **help_user**: 4 variants (different phrases)
- **ask_question**: 3 variants
- **express_confusion**: 3 variants
- **refuse**: 3 variants
- **acknowledge**: 5 variants

### 2. `realizations_advanced.json` (was 10, became 30)

Stylistic variants were extended:
- **respond_about_self**: 4 variants (minimal, verbose, technical, straightforward)
- **greet_user**: 5 variants (with a mark, time of day, different styles)
- **help_user**: 4 variants (different urgency)
- **ask_question**: 4 variants (different question types)
- **express_confusion**: 4 variants (different levels of confusion)
- **refuse**: 4 variants (different reasons for refusal)
- **acknowledge**: 5 variants (with a mark, different intensity)

### 3. `realizations_extended.json` (a new file with 35 realizations)

Entirely new contexts:
- **respond_about_self**: 6 variants (abilities, knowledge, origin)
- **greet_user**: 4 variants (how one is, news, time of day)
- **help_user**: 5 variants (different task types)
- **ask_question**: 4 variants (different kinds of clarification)
- **express_confusion**: 4 variants (loss, errors, a beginning)
- **refuse**: 5 variants (prohibitions, incorrectness, stop)
- **acknowledge**: 7 variants (gratitude, agreement, continuation)

## The Test Confirms

```text
Loaded 91 realizations
  - respond_about_self: 14 realizations
  - greet_user: 13 realizations
  - help_user: 14 realizations
  [and the others]

All tests passed (7/7)
```

## Example: Diversity of Replies to a Greeting

The agent may now say:
1. “Hello. Glad to meet you.” (basic)
2. “Hello. How may I help you?” (with an offer)
3. “Hello. Glad to see you.” (friendly)
4. “Hello. Nice to meet you.” (an English phrasing)
5. A greeting that asks how one is, with a mark
6. “Good morning. How does your day begin?” (time of day)
7. “Good evening. How did your day go?” (evening)
8. “Glad to meet you. What is new?” (warm)
9. “Good day. I am glad to see you.” (formal)
10. “I see you for the first time. Welcome.” (for a new interlocutor)
11. “I am well. And you?” (in reply to “how are you”)
12. “Thank you for asking. I am ready to work.” (in reply to “how are you”)
13. “Nothing particular. I am ready to hear your news.” (in reply to news)

This replaces the constant repetition of two or three variants.

## What Improved

- **Variability** — the agent replies differently
- **Adequacy** — replies match the context
- **Realism** — the phrases are more natural
- **Coverage** — all intent types are well covered
- **Context** — different contexts are taken into account

## How the System Sees It

```text
User input: a greeting
    ↓
Agent selects: the greet action
    ↓
ActionRealizer looks for: GREET_USER realizations
    ↓
Available: 13 different greetings
    ↓
Selects one based on activation pressure
    ↓
Result: “Good morning. How does your day begin?”
    ↓ (the next time may differ)
Result: “Glad to meet you. What is new?”
    ↓
Result: a greeting that asks how one is
```

## Running the Tests

```bash
python test_adaptive_mouth.py
```

**Result:** all 7 tests pass

---

The realization datasets are now genuinely extensible and diverse.
