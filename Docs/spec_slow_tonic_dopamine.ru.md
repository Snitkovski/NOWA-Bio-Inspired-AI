# Медленный тонический дофамин

English version: [spec_slow_tonic_dopamine.en.md](spec_slow_tonic_dopamine.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Проблема

Тонический DA обновляется слишком быстро. В мозге:

```
tonic DA  → медленная базовая линия
phasic DA → быстрые спайки
```

---

## Решение

Разделить фазический и тонический компоненты.

**Фазический:**

```
DA_phasic = reward_prediction_error
```

**Тонический:**

```
DA_tonic(t+1) = DA_tonic + k * (mean(DA_phasic) - DA_tonic)
```

Где `k ≈ 0.01`.

**Код:**

```python
tonic_DA += slow_rate * (mean_phasic - tonic_DA)
```

---

## Эффект

```
phasic → спайки
tonic  → дрейф базовой линии
```
