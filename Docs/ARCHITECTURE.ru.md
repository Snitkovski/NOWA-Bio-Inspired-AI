# 🏗️ Архитектура NOWA Cognitive

English version: [ARCHITECTURE.en.md](ARCHITECTURE.en.md)


**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


## Обзор системы

NOWA — универсальное когнитивное ядро, которое:

- **Пишет стабильные параметры только во сне** (`Agent.sleep()` под `learning_guard.learning_allowed()`)
- **Пишет ограниченный лабильный слой днём** (быстрые добавки Q/Go/NoGo с затуханием)
- **Использует память** (гиппокамп и кора) с эффективными стабильными + лабильными значениями
- **Регулируется аффектом** и нейромодуляторами (быстрое состояние; медленная аффективная статистика — во сне)
- **Выбирает действия** через selector и затвор базальных ганглиев
- **Консолидирует опыт** во сне (replay Q, capture меток канала, EMA привычек, кора, SHY)

См. [Docs/architecture/two-tier-plasticity.ru.md](../Docs/architecture/two-tier-plasticity.ru.md) и [SLEEP.ru.md](SLEEP.ru.md).

---

## 🧠 Компоненты Системы

### 1. Многоуровневая Память

```
┌─────────────────────────────────┐
│      Memory System              │
├─────────────────────────────────┤
│                                 │
│  Hippocampus (Episodic)        │
│  ├─ Stores recent experiences  │
│  ├─ Fast learning surface       │
│  └─ Immutable records           │
│                                 │
│  Cortex (Semantic)             │
│  ├─ Consolidated patterns       │
│  ├─ Abstract knowledge          │
│  └─ Modified only in sleep      │
│                                 │
└─────────────────────────────────┘
```

### 2. Нейромодуляторная Система (Phase 2) ⭐

**Глобальные регуляторы поведения:**

```
┌────────────────────────────────────────────┐
│   Neuromodulators (Phase 2 - NEW!)        │
├────────────────────────────────────────────┤
│                                            │
│  DOPAMINE (DA)                            │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.1   │
│  ├─ Function: Reward prediction error    │
│  ├─ Effects:                             │
│  │  └─ Learning rate ↑                   │
│  │  └─ Consolidation strength ↑          │
│  └─ Update: reward > 0 → DA += 0.25*R   │
│                                            │
│  SEROTONIN (HT)                           │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.1   │
│  ├─ Function: Stability & temporal depth │
│  ├─ Effects:                             │
│  │  └─ Temporal horizon ↑                │
│  │  └─ Habit formation ↑                 │
│  └─ Update: reward > 0, conflict==0      │
│            → HT += 0.05*reward           │
│                                            │
│  NOREPINEPHRINE (NE)                      │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.1   │
│  ├─ Function: Uncertainty & arousal      │
│  ├─ Effects:                             │
│  │  └─ Exploration level ↑               │
│  │  └─ Chain generation ↑                │
│  └─ Update: NE += 0.30*novelty           │
│            NE += 0.15*conflict           │
│                                            │
│  CORTISOL (CORT)                          │
│  ├─ Range: [0.0 - 1.0], Baseline: 0.05  │
│  ├─ Function: Stress & threat response   │
│  ├─ Effects:                             │
│  │  └─ Forgetting rate ↑                 │
│  │  └─ Consolidation threshold ↑         │
│  └─ Update: reward < 0 → CORT += 0.2*|R|│
│            CORT += 0.25*conflict         │
│                                            │
│  Decay: Exponential toward baseline      │
│  Half-life: ~90 seconds                  │
│                                            │
└────────────────────────────────────────────┘
```

### 3. Аффективная система

```
┌──────────────────────────────┐
│   AffectiveState            │
├──────────────────────────────┤
│                              │
│ Valence [-1.0 to +1.0]      │
│ Arousal [0.0 to 2.0]        │
│ Threat [0.0 to 1.0]         │
│ Curiosity [0.0 to 1.0]      │
│ Entity associations (dict)   │
│                              │
│ Effects:                     │
│ └─ Modifies action pressure  │
│ └─ Influences habit strength │
│                              │
└──────────────────────────────┘
```

### 3.5. Аффективная персистентность (фаза 3.5)

```
┌──────────────────────────────┐
│  AffectivePersistenceLayer  │
├──────────────────────────────┤
│  Durable affective traces   │
│  ├─ anxiety / tension       │
│  ├─ satisfaction / interest │
│  ├─ slow decay              │
│  ├─ accumulation            │
│  └─ age tracking            │
│                              │
│ Reads: affect, neuromods,   │
│       temporal T1/T2        │
│                              │
│ ⚠️ Does NOT select actions  │
│ ⚠️ No direct selector input │
└──────────────────────────────┘
```

### 3.75. Аффективное фоновое поле (фаза 3.75)

```
┌──────────────────────────────┐
│  AffectiveBackgroundField    │
├──────────────────────────────┤
│  Inertial background field   │
│  from affective traces       │
│  + lifetime modulation       │
│  + wakefulness noise only    │
│                              │
│ Reads: traces + lifetime     │
│ Writes: background_*         │
│                              │
│ ⚠ No direct action input     │
│ ⚠ No neuromodulator control  │
└──────────────────────────────┘
```

### 4. Система выбора действий

```
┌─────────────────────────────────────┐
│      Action Selection               │
├─────────────────────────────────────┤
│                                     │
│  Inputs:                            │
│  ├─ Hippocampal activations        │
│  ├─ Cortical patterns              │
│  ├─ Intent memory (habits)          │
│  ├─ Affective modifier              │
│  └─ Prediction layer (advisory)    │
│                                     │
│  Selector                           │
│  ├─ Confidence-based stochastic    │
│  ├─ NOT learnable                   │
│  └─ Deterministic at high conf.     │
│                                     │
│  Output: action_name                │
│                                     │
│  ⚠️ ONLY selector chooses actions  │
│  ⚠️ Nothing else can override      │
│                                     │
└─────────────────────────────────────┘
```

### 5. Система привычек (Intent Memory)

```
┌──────────────────────────────┐
│    Intent Memory (Habits)    │
├──────────────────────────────┤
│                              │
│ context → action mapping     │
│ strength: how often used     │
│ affective valence: quality   │
│                              │
│ Днём: только note_selection  │
│   (следы силы 0)             │
│ Во сне:                      │
│ ├─ EMA по исходу             │
│ ├─ degrade_unused (сон)      │
│ └─ replay медленного аффекта │
│                              │
└──────────────────────────────┘
```

### 6. Сон и Консолидация

```
┌────────────────────────────────────┐
│   Sleep Manager                    │
├────────────────────────────────────┤
│                                    │
│ Единственный писатель стабильного │
│                                    │
│ Двухуровневый проход (раз за сон): │
│  1. Capture κ лабильного Go/NoGo  │
│  2. Компенсированный шаг η_eff    │
│  3. EMA привычек + визиты         │
│  4. Медленный аффект + внешние хуки│
│                                    │
│ Затем циклы: replay стабильного Q, │
│  кора, SHY, цепочки, SAC, …       │
│                                    │
│ Днём: только лабильные метки       │
│                                    │
└────────────────────────────────────┘
```

### 7. Слой Предсказания (Plan C)

```
┌─────────────────────────────────┐
│  Prediction Layer               │
├─────────────────────────────────┤
│                                 │
│ Role: ADVISORY only             │
│ ├─ Creates pressure, not choice │
│ ├─ Selector still decides       │
│ └─ Can be ignored               │
│                                 │
│ Updates:                        │
│ ├─ Positive prediction → ↑ P   │
│ ├─ Negative prediction → ↓ P   │
│ └─ Noisy predictions ignored    │
│                                 │
│ No feedback from selector       │
│                                 │
└─────────────────────────────────┘
```

---

## 📊 Полный Процесс в Действии

### Фаза 1: Бодрствование (Waking)

```
1. Receive context events
                  ↓
2. Activate memories (hippocampus + cortex)
                  ↓
3. Get intent habits (from intent_memory)
                  ↓
4. Get affective state & neuromodulators
                  ↓
5. Compute action pressures
                  ↓
6. Selector chooses action (confidence-based)
                  ↓
7. Store experience (immutable in hippocampus)
                  ↓
8. Update affect & neuromodulators
                  ↓
9. Известный исход → только лабильный Q/Go/NoGo
   (хосту нужен dt для затухания)
```

### Фаза 2: Сон (Sleep)

```
1. Get consolidation candidates
                  ↓
2. Cluster similar experiences
                  ↓
3. Abstract into patterns
                  ↓
4. Store in cortex (semantic memory)
                  ↓
5. Apply neuromodulator effects:
   ├─ DA: boost consolidation
   ├─ HT: stabilize
   ├─ NE: form chains
   └─ CORT: increase forgetting
                  ↓
6. Degrade unused habits
                  ↓
7. Обновление стабильного слоя (replay Q,
   capture, привычки, кора, …)
```

---

## 🔄 Цикл взаимовлияния модулей

```
Environment
    ↓
    │ reward, novelty, conflict signals
    ↓
AffectiveState ←→ Neuromodulators
    ↓              ↓
    │              │ modifies learning params
    │              ↓
    └────→ Selector (confidence-based)
              ↓
              Action
              ↓
          Experience (stored)
              ↓
           Sleep ← Стабильное обучение + capture
              ↓
         Consolidation (modified by neuromodulators)
              ↓
        Cortex patterns updated
```

---

## ⚙️ 8 Методов-модификаторов нейромодуляторов

| Метод | Эффект | Диапазон |
|-------|--------|----------|
| `get_learning_rate_modifier()` | Скорость обучения | 0.5 - 1.5 |
| `get_consolidation_strength()` | Усиление консолидации | 0.5 - 1.5 |
| `get_temporal_discount()` | Временной горизонт | 0.5 - 1.5 |
| `get_exploration_level()` | Исследовательское поведение | 0.0 - 1.0 |
| `get_temporal_chain_generation()` | Формирование цепочек | 0.0 - 1.0 |
| `get_forgetting_rate()` | Скорость забывания | 0.1 - 0.9 |
| `get_consolidation_threshold()` | Порог консолидации | 0.1 - 0.9 |
| `get_affective_arousal_modifier()` | Модификация возбуждения | 0.5 - 1.5 |

---

## 🚫 Жесткие Ограничения (Anti-abuse)

**Нельзя:**
- ❌ Выбирать action на основе DA
- ❌ Делать `if DA > X then action`
- ❌ Хранить предпочтения в нейромодуляторах
- ❌ Изменять нейромодуляторы извне (кроме update_from_signals)

**Можно:**
- ✅ Менять коэффициенты (методы-модификаторы)
- ✅ Влиять на скорость забывания
- ✅ Менять вес prediction layer
- ✅ Читать состояние (snapshot)

---

## 📈 Типичная эволюция нейромодуляторов

```
Scenario: Agent meets success

Time 0:     DA=0.1, HT=0.1, NE=0.1, CORT=0.05 (baseline)
            ↓
Step 1:     reward=+0.8 (success!)
            ↓
Immediate:  DA: 0.1 → 0.30 (↑200%)
            HT: 0.1 → 0.14 (↑40%)
            
During Sleep:
            consolidation ↑ from DA
            habit strengthened from HT
            
At Rest:    DA → 0.1 (decay over ~90s)
            HT → 0.1 (slow decay)
```

---

## 🔬 Биологическое обоснование

| Модулятор | Биологический коррелят | Функция |
|-----------|----------------------|---------|
| Dopamine | Вентральный покрышка | Награда и мотивация |
| Serotonin | Дорзальные ядра шва | Настроение и устойчивость |
| Norepinephrine | Locus coeruleus | Возбуждение и внимание |
| Cortisol | HPA axis | Реакция на стресс |

---

## 📚 Ключевые Документы

- [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.ru.md) - краткий обзор Phase 2
- [FINAL_REPORT_NEUROMODULATORS_PHASE2.md](FINAL_REPORT_NEUROMODULATORS_PHASE2.ru.md) - полный отчет
- [LEARNING.md](LEARNING.ru.md) - принципы обучения
- [README_AFFECTIVE_SYSTEM.md](README_AFFECTIVE_SYSTEM.ru.md) - аффективная система

---

**Построено на основе спецификации Phase 2 - Нейромодулятор**

✅ Все требования спецификации соблюдены
✅ 219/219 тестов пройдено
✅ Код готов к промышленной эксплуатации
