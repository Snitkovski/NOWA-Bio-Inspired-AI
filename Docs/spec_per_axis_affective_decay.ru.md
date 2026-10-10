# Поосевое аффективное затухание

English version: [spec_per_axis_affective_decay.en.md](spec_per_axis_affective_decay.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Проблема

В `AffectiveSpace` уже используется 8 канонических осей:

```text
valence
arousal
dominance
stress
trust
curiosity
stability
attachment
```

Ранее инерционная часть была описана через единый `alpha`, что делало временную динамику осей слишком однородной.

---

## Биология

Оси имеют разные временные масштабы, поэтому нужен разный коэффициент затухания:

| Ось | Поведение |
| --- | --- |
| stress | быстро спадает |
| curiosity | быстро без подкрепления |
| arousal | быстро (подобно всплеску) |
| valence | средне |
| trust | медленно |
| dominance | очень медленно |

---

## Решение

Использовать поосевые коэффициенты `axis_decay` с алиасом `affective_decay`.

### Значения по умолчанию

```python
affective_decay = {
    "valence":   0.92,
    "arousal":   0.80,
    "dominance": 0.97,
    "stress":    0.75,
    "curiosity": 0.78,
    "trust":     0.95
}
```

Для остальных осей применяется запасной путь к `alpha` (прежнее поведение).

### Совместимость входов с прежними ключами

В `affective_decay` поддерживаются прежние ключи:

- `pleasure -> valence`
- `arousal -> arousal`
- `dominance -> dominance`

### Обновление состояния (инерционная часть)

```python
inertial_component = baseline[axis] + axis_decay[axis] * (current[axis] - baseline[axis])
```

---

## Эффект

Получается естественное поведение:

```text
arousal   → всплески
valence   → задерживается
stress    → быстрый спад
curiosity → угасает без подкрепления
trust     → инерционно
dominance → устойчиво
```
