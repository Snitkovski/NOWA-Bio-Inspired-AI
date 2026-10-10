# Phase 4.1 — семантические эмоции

English version: [phase_4_1_semantic_emotions_spec.en.md](phase_4_1_semantic_emotions_spec.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Назначение фазы

Phase 4.1 вводит **семантический слой эмоций**, который:

- НЕ генерирует аффект
- НЕ влияет напрямую на выбор действий
- НЕ регулирует другие подсистемы

Его единственная функция — **интерпретация непрерывного аффективного пространства (Phase 4)** в виде устойчивых, перекрывающихся **эмоциональных аттракторов**.

Это слой *осознания*, а не *реакции*.

---

## Входные данные

### Обязательные

- `AffectiveSpace.axes` — 8-мерный вектор:
  - pleasure
  - pain
  - arousal
  - relaxation
  - attachment
  - rejection
  - focus
  - vulnerability

- `AffectiveSpace.inertia`
- `AffectiveSpace.fall_rate`
- `AffectiveSpace.speed()`

### Опциональные

- `wakefulness`
- `agent_lifetime` (общее время существования агента)

---

## Выходные данные

Список активных семантических эмоций:

```json
{
  "emotion": "love",
  "activation": 0.73,
  "stability": 0.61,
  "obsessive": true
}
```

Выход НЕ используется селектором действий.

---

## Базовое определение: эмоциональный аттрактор

**Аттрактор** — это область в 8D-пространстве, задаваемая:

- центром (prototype vector)
- радиусами допусков по осям
- весами осей

### Формально

Активация эмоции E:

```
E = clamp( Σ w_i * f_i(A_i), 0..1 )
```

где `f_i` — нелинейные функции (ReLU, sigmoid, abs).

---

## Канонические эмоции (v1)

### Радость (joy)

- pleasure ↑
- arousal ↑
- pain ↓

```python
joy = pleasure*0.5 + arousal*0.4 - pain*0.4
```

---

### Грусть (sadness)

- pain ↑
- arousal ↓
- attachment ↑

```python
sadness = pain*0.5 + (1-arousal)*0.3 + attachment*0.3
```

---

### Любовь (love)

- attachment ↑↑
- pleasure ↑
- vulnerability ↑

```python
love = attachment*0.5 + pleasure*0.3 + vulnerability*0.3
```

---

### Ненависть (hate)

- rejection ↑
- arousal ↑
- focus ↑

```python
hate = rejection*0.5 + arousal*0.3 + focus*0.3
```

---

### Страх (fear)

- pain ↑
- arousal ↑
- vulnerability ↑

---

### Наслаждение (pleasure_rest)

- pleasure ↑
- relaxation ↑

---

## Навязчивость эмоций

Эмоция считается навязчивой, если:

```
obsessive = inertia_high AND fall_rate_low AND focus_high
```

Навязчивость — **не ошибка**, а характеристика личности.

---

## Устойчивость (stability)

```
stability = 1 - AffectiveSpace.speed()
```

Высокая устойчивость = эмоциональное «застревание».

---

## Свойства системы

- эмоции могут сосуществовать
- эмоции могут противоречить
- нет нормализации между эмоциями
- нет подавления

---

## Тест-кейсы

### TC-1: Любовь + боль

```
attachment=0.9
pleasure=0.7
pain=0.6
vulnerability=0.8
```

Ожидается:
- love > 0.6
- sadness > 0.3

---

### TC-2: Навязчивая ненависть

```
rejection=0.8
arousal=0.9
focus=1.0
inertia.high
fall_rate.low
```

Ожидается:
- hate.active
- hate.obsessive = true

---

### TC-3: Эмоциональный покой

```
pleasure=0.6
relaxation=0.7
arousal=0.1
pain=0.0
```

Ожидается:
- pleasure_rest > 0.6

---

## Анти-паттерны

Запрещено:

- Эмоции как переключатели
- Подавление конфликтных эмоций
- Нормализация суммы эмоций
- Использование эмоций напрямую в селекторе

---

## Философская ремарка

Phase 4.1 — это первый слой, где агент **может сказать себе**, а не миру:

> «Мне больно»
> «Я привязан»
> «Я хочу, но мне страшно»

Это не конец.
Это начало субъективности.

---

## Заметки о реализации (2026-02-10)

- Реализовано как `SemanticEmotionsLayer` с каноническими эмоциями (joy, sadness, love, hate, fear, pleasure_rest).
- Встроено в `Agent.step()` после обновления аффективного пространства.
- Сохраняется через save/load как `semantic_emotions`.
- GUI показывает краткое текстовое резюме и подробный список.
- Слой остаётся нерешающим: влияния на выбор действия нет.
