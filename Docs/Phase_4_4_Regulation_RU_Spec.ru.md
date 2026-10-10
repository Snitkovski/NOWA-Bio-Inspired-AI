# Phase 4.4 — Регуляция на основе эмоциональных ожиданий

English version: [Phase_4_4_Regulation_RU_Spec.en.md](Phase_4_4_Regulation_RU_Spec.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Статус документа

Фаза: 4.4  
Дата генерации: 2026-02-12T08:27:23.447697 UTC  
Зависимости: Phase 4.2 — Emotional Memory & Narratives; Phase 4.3 — Emotional Expectations

---

# 1. Назначение

Phase 4.4 вводит строго ограниченный регуляторный слой, использующий прогнозы Phase 4.3 для мягкой гомеостатической стабилизации фонового состояния.

Слой выполняет ТОЛЬКО стабилизацию.

ЗАПРЕЩЕНО:
- изменять semantic_emotions
- изменять affective space напрямую
- изменять память (4.2)
- изменять ожидания (4.3)
- влиять на action selection или planning (Phase 5)
- изменять utility / decision weights

РАЗРЕШЕНО:
- небольшая корректировка background-параметров
- небольшая корректировка нейромодуляторов

---

# 2. Архитектурные границы

| Слой | Может изменять |
| --- | --- |
| 4.2 | Только память |
| 4.3 | Ничего внешнего |
| 4.4 | Только фоновые параметры |
| 5.x | Поведение |

Phase 4.4 НЕ ПЕРЕСЕКАЕТСЯ с Phase 5.

---

# 3. Входы update()

- expectations_snapshot: Dict
- affective_background_snapshot: Dict[str, float]
- neuromodulators_snapshot: Dict[str, float]
- agent_lifetime: float
- timestamp: float

Все входы read-only.

---

# 4. Выход update()

```text
{
  "regulation_active": bool,
  "regulation_mode": "none" | "stabilizing" | "dampening" | "containment",
  "applied_adjustments": {
      "background_shift": "...",
      "neuromodulator_shift": "..."
  }
}
```

Ограничения:
- |delta| ≤ 0.1 за шаг
- L2-норма всех корректировок ≤ 0.15

---

# 5. Триггеры активации

Регуляция включается если:

1. probability ≥ 0.8 И confidence ≥ 0.6
2. risk_of_repetition == True
3. global_outlook == "escalating"

Иначе:
- regulation_active = False
- mode = "none"

---

# 6. Режимы

## 6.1 Stabilizing

Условия:
- escalating outlook
- рост активации

Эффект:
- arousal −≤0.05
- relaxation +≤0.05

Цель: мягкое гашение эскалации.

---

## 6.2 Dampening

Условия:
- obsessive pattern
- risk_of_repetition == True

Эффект:
- снижение emotional_gain ≤0.05
- уменьшение dominance bias

---

## 6.3 Containment

Условия:
- высокая вероятность
- increasing trend
- высокая уверенность

Эффект:
- ограничение усиления нейромодуляторов
- мягкое снижение амплификации

---

# 7. Критические ограничения

## 7.1 Запрет положительной обратной связи

Регуляция НЕ ДОЛЖНА увеличивать вероятность прогнозируемой эмоции.

## 7.2 Запрет изменения semantic_emotions

Прямые изменения запрещены.

## 7.3 Запрет изменения памяти

episodes/patterns/narratives не меняются.

## 7.4 Запрет влияния на поведение

Никакого изменения utility, ranking, planning.

## 7.5 Ограничение силы коррекции

Коррекции малы и ограничены нормой.

---

# 8. Anti-Patterns

1. Самоусиливающийся контур
2. Перерегуляция
3. Постоянно активная регуляция
4. Скрытое влияние на planning
5. Полное эмоциональное выравнивание

---

# 9. Тест-кейсы

## 9.1 Эскалация радости

Expected:
- mode = stabilizing
- arousal снижается
- вероятность joy не растет из-за регуляции

## 9.2 Навязчивый страх

Expected:
- mode = dampening
- emotional_gain уменьшается
- fear probability не увеличена регуляцией

## 9.3 Нейтральное состояние

Expected:
- regulation_active = False

## 9.4 Волатильность

Expected:
- минимальная регуляция

## 9.5 Комбинированный риск

Expected:
- mode = containment
- ограничения соблюдены

---

# 10. Критерии завершения

1. Нет self-reinforcing циклов за 1000 шагов.
2. Поведение идентично версии без 4.4.
3. Memory и Expectations не изменяются регуляцией.
4. Все anti-pattern тесты проходят.

---

Конец спецификации Phase 4.4.
