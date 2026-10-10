# Руководство по реализации FitnessEvaluator (пакет D)

English version: [FITNESS_EVALUATOR.en.md](FITNESS_EVALUATOR.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

Последняя проверка: 25 марта 2026 г.

---

## Область

`src/fitness.py` реализует автономный многокритериальный оценщик приспособленности для агентов NOWA. Модуль использует только стандартную библиотеку Python и читает состояние агента через открытые атрибуты.

Основные цели:
1. вычислять ограниченные векторы приспособленности по 7 критериям
2. сохранять оценку свободной от побочных эффектов (только чтение)
3. поддерживать детерминированное ранжирование Парето (фронты в стиле NSGA-II и расстояние скученности)
4. предоставлять скалярную запасную оценку с настраиваемыми нормализованными весами
5. поддерживать сериализацию для эволюционных процедур

---

## Реализованные объекты

### `FitnessVector` (`frozen=True`)

Поля:
- `longevity`
- `affective_range`
- `prediction_skill`
- `stress_resilience`
- `behavioral_diversity`
- `learning_efficiency`
- `memory_quality`
- `agent_id`
- `generation`
- `evaluation_step`

Поведение:
1. все критерии ограничиваются диапазоном `[0.0, 1.0]` в `__post_init__`
2. `generation` и `evaluation_step` нормализуются к неотрицательным целым
3. `agent_id` всегда нормализуется к строке

### `ParetoRank` (`frozen=True`)

Поля:
- `agent_id`
- `rank`
- `crowding_distance`
- `fitness`

### `FitnessEvaluator`

Открытый интерфейс:
- `evaluate(agent) -> FitnessVector`
- `evaluate_population(agents) -> List[FitnessVector]`
- `pareto_rank(fitness_vectors) -> List[ParetoRank]`
- `scalar_score(fitness) -> float`
- `dominates(a, b) -> bool`
- `criteria_names() -> List[str]`
- `fitness_to_dict(fitness) -> dict`
- `fitness_from_dict(data) -> FitnessVector`

---

## Контракты критериев

Реализованные критерии из `Docs/SPEC_D_FitnessEvaluator.md`:
1. `longevity`: `min(1.0, lived_steps / expected_lifetime_steps)`
2. `affective_range`: среднее по осям `std(affective_history)`, нормализованное на `0.5`
3. `prediction_skill`: `1.0 - mean(abs(td_error_history))` с запасом к `value_layer.snapshot()["last_td_error"]`
4. `stress_resilience`: `1.0 - mean(cortisol_history)` с запасом к `neuromodulators.cortisol`
5. `behavioral_diversity`: нормализованная энтропия по `bg_action_channels[*].selection_count`
6. `learning_efficiency`: `(sleep_update_count / (online_update_count + 1)) / 3.0`, с ограничением
7. `memory_quality`: среднее `consolidation_weight` по последним 128 опытам hippocampus

Правила устойчивости:
1. некорректные или отсутствующие поля снижают критерий до `0.0`
2. оценщик не возбуждает исключение на пути оценки
3. оценщик никогда не изменяет состояние агента

---

## Поддержка времени выполнения агента

`Agent` теперь ведёт скользящие истории, используемые пакетом D:
- `agent.affective_history: List[dict]`
- `agent.td_error_history: List[float]`
- `agent.cortisol_history: List[float]`

Поведение времени выполнения в `Agent.step()`:
1. добавить текущий снимок осей аффекта
2. добавить текущую ошибку TD (из текущего `value_update` или `value_layer.snapshot`)
3. добавить текущее значение cortisol
4. хранить только последние `256` записей (`agent._fitness_history_limit`)

Эта поддержка реализована в:
- `src/agent.py`

---

## Поведение ранжирования Парето

`FitnessEvaluator.pareto_rank(...)` реализует детерминированное ранжирование в стиле NSGA-II:
1. построить недоминируемый фронт (`rank=1`)
2. итеративно снимать фронты и назначать возрастающие ранги
3. вычислить расстояние скученности внутри каждого фронта
4. назначить `float("inf")` в качестве расстояния скученности крайним точкам минимума и максимума по каждому критерию
5. вернуть список, отсортированный по `(rank по возрастанию, crowding_distance по убыванию)` со стабильным разрешением равенства по индексу

---

## Покрытие тестами

Основные наборы:
- `tests/test_fitness.py`
- `tests/test_fitness_agent_integration.py`

Покрытие включает:
1. TC-01..TC-18 из `Docs/SPEC_D_FitnessEvaluator.md`
2. круговой проход словаря и обработку значений по умолчанию
3. детерминированное упорядочение Парето
4. накопление истории на уровне агента и поведение предела скользящего окна

Последний локальный прогон:

```text
python -m pytest tests/test_fitness.py tests/test_fitness_agent_integration.py -q
21 passed in 0.22s
```

Регрессия по проекту (без Demo):

```text
python -m pytest tests -q
681 passed, 3 skipped
```
