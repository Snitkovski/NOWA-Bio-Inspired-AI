## Аннотация

English version: [NOWA_Procurement_Sandbox_Spec_v1.1_patch.en.md](NOWA_Procurement_Sandbox_Spec_v1.1_patch.en.md)

Патч v1.1 отвечает на зарегистрированный прогон в тридцать кварталов, в котором `all_passed` наступил только в кварталах 17 и 19. Критерии `decision_consistency` и `supplier_diversification` считают выборы по строке `supplier_id`, тогда как `ProcurementWorld` каждый квартал заново разыгрывает надёжность, ценовой множитель и срок поставки под теми же идентификаторами. Гиппокамп агента между кварталами сохраняется, поэтому усвоенное о поставщике в квартале N указывает в квартале N+1 на другую случайную сущность. Наблюдаемый симптом: `supplier_diversification` пять кварталов подряд принимает значение 0,1333… синхронно с `decision_consistency`, стремящейся к 1,0.

Учебный план делится на две стадии одного контура, а не на два мира. Стадия 1a сохраняет сменяемых поставщиков и выпускает агента по четырём критериям, не зависящим от устойчивости идентификатора: эффективность затрат, избежание дефицита, бюджетная дисциплина и реакция на риск. Стадия 1b переносит атрибуты поставщиков между кварталами методами `export_supplier_state` и `carry_supplier_state`, сбрасывая только признак дефолта, и выпускает по согласованности решений и диверсификации. Четыре критерия стадии 1a остаются в отчёте; пол `check_non_regression` равен 0,9 от базовой линии стадии 1a, взятой как средние последних успешных кварталов. Бюджет между кварталами стадии 1b в первой реализации не переносится. Смешанное чередование персистентных и одноразовых миров отложено до отдельного подтверждения обеих стадий.

Порядок исполнения обязателен. Сначала уже собранный `results/sandbox_run_001.json` пересчитывается формулой стадии 1a без новой симуляции; затем следуют пять независимых прогонов стадии 1a; затем фиксируется базовая линия; только после этого пишется код персистентных поставщиков. Готовность стадии 1a требует выпуска не менее чем в трёх из пяти семян при разбросе кварталов до выпуска не более ±50 %. Готовность стадии 1b требует удержания выпуска не менее трёх кварталов подряд, прохождения пола во всех таких кварталах и успеха не менее чем в двух из пяти независимых прогонов стадии 1b при той же базовой линии.

---

# NOWA Procurement Sandbox — Патч v1.1

**Базовый документ:** NOWA_Procurement_Sandbox_Spec.md (v1.0, разделы 1–25)
**Статус:** Ready for implementation — точечное изменение поверх уже
реализованного и протестированного кода
**Контекст:** По итогам первого реального прогона (30 кварталов, один агент,
`results/sandbox_run_001.json`) обнаружена структурная проблема: два из
шести критериев fitness (`decision_consistency`, `supplier_diversification`)
измеряют постоянство конкретных `supplier_id` между кварталами, но физика
мира (`ProcurementWorld`) пересоздаёт атрибуты поставщиков под теми же ID
каждый квартал — из-за этого graduation срабатывает лишь случайно (2 из 30
кварталов), а не устойчиво.

**Что менять:** только модули, перечисленные в разделе "Затронутые файлы"
ниже. Весь остальной код v1.0 (`procurement_world.py` физика тика,
`sandbox_encoder.py`, `sandbox_agent_factory.py`, `sandbox_checkpoint.py`,
`sandbox_config.py`, `sandbox_observer.py`) остаётся без изменений в этой
ревизии.

---

## Затронутые файлы

| Файл | Тип изменения |
|---|---|
| `procurement_fitness.py` | Добавить параметр `stage`, разделить критерии на gating/monitored, добавить `check_non_regression` |
| `procurement_world.py` | Добавить `persistent_suppliers` в конфиг, методы `export_supplier_state`/`carry_supplier_state` |
| `training_loop.py` | Добавить метод `run_stage1b_persistent` |
| `run_sandbox.py` | Добавить CLI-флаги `--stage`, `--baseline-from` |
| `tests/` | Новые тест-файлы для staged graduation, persistent suppliers, non-regression guard |

---

## Обязательный порядок выполнения (не нарушать)

Это не только архитектурное, но и процессное требование — шаги строго
последовательны, не параллелить:

1. **Шаг 27.1** — пересчитать graduation по уже собранным данным
   `results/sandbox_run_001.json` новой 4-критериальной Stage 1a формулой
   БЕЗ повторной симуляции (скрипт ниже). Это подтверждает диагноз
   количественно за секунды, прежде чем менять код.
2. **Шаг 27.2** — только если диагноз подтверждён: внести изменения в
   `procurement_fitness.py`, прогнать 5 независимых Stage 1a прогонов
   с разными `--seed`.
3. **Шаг 27.3** — зафиксировать `stage_1a_baseline` из лучшего/медианного
   прогона.
4. **Шаг 27.4** — только после 27.3: реализовать `persistent_suppliers`
   (`procurement_world.py`, `training_loop.py`) и Stage 1b.

**Не писать код Stage 1b параллельно со сбором 5-seed sweep Stage 1a.**

---

## 26. Ревизия v1.1 — двухстадийный curriculum (Stage 1a / Stage 1b)

### 26.1 Диагноз, приведший к этой ревизии

Первый реальный прогон (30 кварталов, один агент) дал `all_passed=true`
только в кварталах 17 и 19 — не устойчивое graduation, а случайное попадание
в узкое окно. Разбор причины:

`ProcurementWorld._init_suppliers()` пересоздаёт поставщиков **каждый
квартал** с новыми случайными `reliability`/`base_price_multiplier`/
`lead_time_days`, но сохраняет прежние `supplier_id` (`supplier_000` и
т.д.). Гиппокамп агента не сбрасывается между кварталами (constraint V1
это разрешает). В результате: усвоенное в квартале N "supplier_002
надёжен" в квартале N+1 указывает на другую случайную сущность под тем
же ярлыком — агент либо переучивается заново каждый квартал, либо
залипает на одном ID вопреки экономическому смыслу.

Наблюдаемый симптом: `supplier_diversification` даёт точное значение
`0.1333...` (математический артефакт монополии на одного поставщика)
пять кварталов подряд, синхронно с `decision_consistency → 1.0`.

### 26.2 Разбор критериев по чувствительности к переносу ID

| Критерий | Зависит от постоянства `supplier_id` между периодами? |
|---|---|
| `cost_efficiency` | Нет — сравнивает наблюдаемую цену со статистической рыночной полосой |
| `stockout_avoidance` | Нет — считает штуки дефицита |
| `budget_discipline` | Нет — считает минимум бюджета за период |
| `reaction_to_risk_events` | Нет — сравнивает дни реакции, не выбор контрагента |
| `decision_consistency` | **Да** — `Counter` по конкретным `supplier_id` |
| `supplier_diversification` | **Да** — доля заказов у самого частого `supplier_id` |

Четыре критерия измеряют **общую профессиональную компетентность**
(узнавание сигналов "дёшево/дорого", "надёжно/рискованно" по наблюдаемым
атрибутам, а не по идентичности). Два критерия измеряют **устойчивость
отношений с конкретными, не меняющимися контрагентами** — и это осмысленно
только в мире, где контрагент действительно не меняется.

### 26.3 Новая модель: две стадии одной curriculum, не два разных мира

```
Stage 1a — "профшкола"           Stage 1b — "стажировка в фирме"
────────────────────────         ──────────────────────────────
Много независимых миров          Один персистентный мир
(текущее поведение,              (НОВЫЙ режим)
поставщики пересоздаются
каждый квартал)

Градация только по 4 критериям:  Градация только по 2 критериям:
  cost_efficiency                  decision_consistency
  stockout_avoidance                supplier_diversification
  budget_discipline               (плюс 4 предыдущих как
  reaction_to_risk_events          необходимый, но не
                                   достаточный минимум —
                                   не должны деградировать)

Цель: абстрактная стратегия,     Цель: устойчивая, но не
переносимая в cortex             монопольная связь с реальными
(не привязана к конкретным ID)   (для этого мира) партнёрами
```

**Обязательное условие последовательности:** Stage 1b запускается только
после того, как агент прошёл Stage 1a graduation. Смешанный режим (чередование
персистентных и одноразовых миров в одном прогоне) — предмет будущей ревизии
v1.2, реализуется только после того, как Stage 1a и Stage 1b по отдельности
подтверждены (раздел 26.7).

### 26.4 Изменения в `procurement_fitness.py`

```python
# Новая константа: два набора критериев вместо одного монолитного

STAGE_1A_CRITERIA = [
    "cost_efficiency",
    "stockout_avoidance",
    "budget_discipline",
    "reaction_to_risk_events",
]

STAGE_1B_CRITERIA = [
    "decision_consistency",
    "supplier_diversification",
]

# PROCUREMENT_CRITERIA остаётся как объединение обоих — используется
# для полного диагностического вывода (JSON по-прежнему содержит все 6),
# но graduation_report получает параметр stage.


class ProcurementFitnessEvaluator:
    def __init__(
        self,
        thresholds: Optional[Mapping[str, float]] = None,
        stage: Literal["1a", "1b"] = "1a",
    ):
        self.stage = stage
        merged = dict(GRADUATION_THRESHOLDS)
        for criterion, value in dict(thresholds or {}).items():
            if criterion in merged:
                merged[criterion] = clamp(safe_float(value, merged[criterion]), 0.0, 1.0)
        self.thresholds = merged

    def graduation_report(self, vector: ProcurementFitnessVector) -> dict:
        """
        Все 6 критериев по-прежнему вычисляются и попадают в отчёт
        (полная прозрачность), но all_passed зависит ТОЛЬКО от критериев
        текущей stage. Критерии другой stage помечаются как
        "monitored" (не блокируют graduation, но видны в отчёте —
        не должны катастрофически деградировать, см. раздел 26.5).
        """
        active_criteria = (
            STAGE_1A_CRITERIA if self.stage == "1a" else STAGE_1B_CRITERIA
        )
        criteria_results: Dict[str, dict] = {}
        for criterion, threshold in self.thresholds.items():
            value = safe_float(getattr(vector, criterion, 0.0), 0.0)
            criteria_results[criterion] = {
                "value": round(value, 4),
                "threshold": threshold,
                "passed": value >= threshold,
                "gating": criterion in active_criteria,
            }

        gating_results = {
            k: v for k, v in criteria_results.items() if v["gating"]
        }
        report: Dict[str, Any] = dict(criteria_results)
        report["stage"] = self.stage
        report["all_passed"] = all(r["passed"] for r in gating_results.values())
        report["n_days"] = vector.n_days
        report["n_orders"] = vector.n_orders
        return report
```

### 26.5 Non-regression guard для критериев вне текущей stage

Stage 1b не должна разрешать деградацию четырёх Stage 1a критериев ради
максимизации `decision_consistency`/`supplier_diversification` — иначе
агент "нарастит лояльность" ценой закупки у плохого поставщика по завышенной
цене, что не является целью.

```python
# Добавить в graduation_report:

NON_REGRESSION_FLOOR = 0.9  # доля от исходного Stage 1a порога

def check_non_regression(
    self, vector: ProcurementFitnessVector, stage_1a_baseline: Dict[str, float]
) -> Dict[str, bool]:
    """
    Вызывается только в Stage 1b. stage_1a_baseline — средние значения
    четырёх Stage 1a критериев за последние N кварталов Stage 1a
    (сохраняются в чекпоинте при переходе между стадиями).
    """
    result = {}
    for criterion in STAGE_1A_CRITERIA:
        current = safe_float(getattr(vector, criterion, 0.0), 0.0)
        baseline = stage_1a_baseline.get(criterion, 0.0)
        floor = baseline * NON_REGRESSION_FLOOR
        result[criterion] = current >= floor
    return result
```

### 26.6 Изменения в `procurement_world.py` — режим персистентного мира

Новый параметр в `ProcurementWorldConfig`:

```python
@dataclass
class ProcurementWorldConfig:
    # ... существующие поля без изменений ...
    persistent_suppliers: bool = False
    """
    False (по умолчанию, Stage 1a): supplier_id стабилен как строка,
    но VirtualSupplier-объект пересоздаётся с новыми случайными
    атрибутами при каждом ProcurementWorld.__init__.

    True (Stage 1b): при создании нового ProcurementWorld для следующего
    квартала атрибуты поставщиков (reliability, base_price_multiplier,
    lead_time_days, reputation, total_orders) переносятся из предыдущего
    квартала, а не генерируются заново. Только is_defaulted СБРАСЫВАЕТСЯ
    в False в начале нового квартала — иначе дефолт поставщика в
    Stage 1b был бы перманентным на весь прогон, что не даёт агенту
    возможности проверить восстановление доверия к ранее рискованному
    поставщику.
    """
```

Новый метод `training_loop.py::SandboxTrainer`:

```python
def run_stage1b_persistent(
    self,
    n_quarters: int,
    world_config: ProcurementWorldConfig,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> SandboxTrainingResult:
    """
    Отличие от run_quarters(): поставщики (кроме is_defaulted) переносятся
    между кварталами через carry_supplier_state. Мир по-прежнему
    пересоздаётся каждый квартал (для сброса дней/pending_orders/budget
    resetting остаётся под вопросом — см. 26.6.1), но идентичность
    поставщиков сохраняется.
    """
    config = replace(world_config, persistent_suppliers=True)
    result = SandboxTrainingResult()
    carried_suppliers: Optional[Dict[str, VirtualSupplier]] = None

    for q_idx in range(1, n_quarters + 1):
        if progress_callback:
            progress_callback(q_idx, n_quarters)

        world = ProcurementWorld(replace(config, seed=q_idx))
        if carried_suppliers is not None:
            world.carry_supplier_state(carried_suppliers)

        decision_log = self._run_single_quarter(world, config.days_per_quarter)
        carried_suppliers = world.export_supplier_state()

        fitness = self.fitness_evaluator.evaluate(world, decision_log)
        graduation = self.fitness_evaluator.graduation_report(fitness)
        result.quarters.append(QuarterResult(
            quarter_index=q_idx, fitness=fitness, graduation=graduation,
            world_summary=world.summary(), processing_time_s=0.0,
        ))
        if graduation["all_passed"]:
            result.graduated = True
            result.graduated_at_quarter = q_idx

    return result
```

Новые методы `ProcurementWorld`:

```python
def export_supplier_state(self) -> Dict[str, VirtualSupplier]:
    """Снимок поставщиков для переноса в следующий квартал (deep copy)."""
    import copy
    return {sid: copy.deepcopy(s) for sid, s in self.suppliers.items()}

def carry_supplier_state(self, carried: Dict[str, VirtualSupplier]) -> None:
    """
    Заменяет только что сгенерированных поставщиков перенесёнными,
    сбрасывая is_defaulted (26.6, обоснование восстановления доверия).
    Вызывается сразу после __init__, до первого tick().
    """
    for sid, supplier in carried.items():
        if sid in self.suppliers:
            supplier.is_defaulted = False
            self.suppliers[sid] = supplier
```

#### 26.6.1 Открытый вопрос: budget и demand между кварталами Stage 1b

Не решено окончательно — фиксирую как вопрос, не как готовое решение:

Если `persistent_suppliers=True`, должен ли **бюджет** тоже переноситься
между кварталами (агент реально управляет одним непрерывным P&L), или
каждый квартал по-прежнему стартует с `initial_budget` (изолированная
оценка per-quarter при персистентных партнёрах)?

Аргумент за перенос бюджета: это ближе к реальности "стажировки в одной
фирме" — деньги не появляются из воздуха каждые 90 дней.

Аргумент против: тогда один плохой квартал (например, дефолт поставщика
в день 85) обваливает весь оставшийся прогон, и `budget_discipline`
перестаёт быть per-quarter метрикой, усложняя сравнение кварталов между
собой.

**Рекомендация для первой реализации:** бюджет НЕ переносится (проще
диагностировать), только идентичность поставщиков. Если после внедрения
окажется, что это создаёт нереалистичную "перезагрузку" мотивации агента —
пересмотреть в v1.2.

### 26.7 Критерии перехода между стадиями (обновление раздела 20)

Раздел 20 родительской спецификации ("критерии готовности к Фазе 3")
теперь применяется в два подшага:

**Готовность Stage 1a → Stage 1b:**
- [ ] `all_passed` (по 4 критериям Stage 1a) в минимум 3 из 5 независимых
      прогонов с разными top-level seed
- [ ] Разброс кварталов до graduation не более ±50% между прогонами
- [ ] Сохранён snapshot средних значений 4 критериев за последние 5
      успешных кварталов — это `stage_1a_baseline` для non-regression guard

**Готовность Stage 1b → Фаза 3 (родительская спецификация):**
- [ ] `all_passed` (по 2 критериям Stage 1b) достигнут и **удержан**
      минимум 3 квартала подряд (не единичное попадание, как в
      диагностированном прогоне раздела 26.1)
- [ ] `check_non_regression` — все 4 Stage 1a критерия проходят floor
      во всех кварталах, где `all_passed=true`
- [ ] Минимум 2 из 5 независимых Stage 1b прогонов (разный top-level seed,
      но тот же `stage_1a_baseline`) достигают устойчивого graduation

### 26.8 Новые тест-кейсы

```python
class TestStagedGraduation:

    def test_stage_1a_ignores_diversification(self, small_world, fitness_evaluator):
        """
        Агент, залипший на одном поставщике (низкий diversification),
        всё равно должен пройти Stage 1a graduation, если остальные
        4 критерия хороши — diversification не gating в этой stage.
        """
        evaluator = ProcurementFitnessEvaluator(stage="1a")
        # decision_log с единственным supplier_id на всех заказах
        ...
        report = evaluator.graduation_report(vector)
        assert report["supplier_diversification"]["gating"] is False
        # all_passed зависит только от 4 других критериев

    def test_stage_1b_requires_diversification(self, fitness_evaluator):
        """Stage 1b: те же данные должны требовать diversification для all_passed."""
        evaluator = ProcurementFitnessEvaluator(stage="1b")
        report = evaluator.graduation_report(vector_with_monopoly)
        assert report["supplier_diversification"]["gating"] is True
        assert report["all_passed"] is False  # низкий diversification блокирует


class TestPersistentSuppliers:

    def test_carry_supplier_state_preserves_reliability(self):
        """После carry_supplier_state атрибуты (кроме is_defaulted) идентичны."""
        config = ProcurementWorldConfig(n_suppliers=3, seed=1)
        world1 = ProcurementWorld(config)
        exported = world1.export_supplier_state()

        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=3, seed=2))
        world2.carry_supplier_state(exported)

        for sid, supplier in world1.suppliers.items():
            assert world2.suppliers[sid].reliability == supplier.reliability
            assert world2.suppliers[sid].base_price_multiplier == supplier.base_price_multiplier

    def test_carry_supplier_state_resets_default_flag(self):
        """Дефолтнувший поставщик получает второй шанс в следующем квартале."""
        config = ProcurementWorldConfig(n_suppliers=1, seed=1)
        world1 = ProcurementWorld(config)
        list(world1.suppliers.values())[0].is_defaulted = True
        exported = world1.export_supplier_state()

        world2 = ProcurementWorld(ProcurementWorldConfig(n_suppliers=1, seed=2))
        world2.carry_supplier_state(exported)

        assert list(world2.suppliers.values())[0].is_defaulted is False

    def test_non_persistent_mode_unaffected(self, small_world_config):
        """persistent_suppliers=False (default) не меняет текущее поведение."""
        assert small_world_config.persistent_suppliers is False


class TestNonRegressionGuard:

    def test_regression_detected_when_cost_efficiency_drops(self, fitness_evaluator):
        baseline = {"cost_efficiency": 0.8, "stockout_avoidance": 0.9,
                     "budget_discipline": 1.0, "reaction_to_risk_events": 0.8}
        degraded_vector = ProcurementFitnessVector(
            cost_efficiency=0.5,  # ниже 0.9 * 0.8 = 0.72 floor
            stockout_avoidance=0.9, budget_discipline=1.0,
            supplier_diversification=0.9, decision_consistency=0.9,
            reaction_to_risk_events=0.8, n_days=90, n_orders=30,
        )
        result = fitness_evaluator.check_non_regression(degraded_vector, baseline)
        assert result["cost_efficiency"] is False
        assert result["stockout_avoidance"] is True
```

### 26.9 CLI: `--stage` флаг

```python
parser.add_argument(
    "--stage", choices=["1a", "1b"], default="1a",
    help="1a: rotating suppliers, general strategy. "
         "1b: persistent suppliers, relationship building. "
         "Requires prior 1a graduation baseline (see --baseline-from)."
)
parser.add_argument(
    "--baseline-from", default=None,
    help="path to a Stage 1a checkpoint/result, required when --stage=1b "
         "for the non-regression guard.",
)
```

### 26.10 Что НЕ входит в эту ревизию (явно отложено)

- Смешанный/чередующийся режим (то, что было предложено как "вариант 2") —
  реализуется только после подтверждения раздела 26.7 для обеих стадий
  по отдельности
- Перенос бюджета между кварталами Stage 1b (раздел 26.6.1) — открытый
  вопрос, дефолтное решение: не переносить
- Многоагентная конкуренция за одних и тех же персистентных поставщиков —
  вне объёма Stage 1/1b вообще, относится к разделу 8 родительской
  спецификации (multi-agent organization)

---

*Ревизия v1.1. Раздел 26 добавлен по итогам разбора первого реального
прогона (30 кварталов, graduation в 2 из 30, синхронная аномалия
diversification/consistency). Обосновывает и специфицирует двухстадийный
curriculum вместо единой градации по всем 6 критериям сразу.*

---

## 27. План исполнения — от текущего состояния к подтверждённому Stage 1a

### 27.1 Немедленный следующий шаг (не Stage 1b, а ревалидация Stage 1a)

Прежде чем писать код персистентных поставщиков (раздел 26.6), нужно
получить существующим кодом **правильную** оценку Stage 1a — то есть
прогнать `ProcurementFitnessEvaluator(stage="1a")` на **уже собранных**
30 кварталах из первого прогона, не гоняя симуляцию заново. Это дёшево
и сразу покажет, было ли дело только в разладе двух групп критериев.

```bash
python -c "
from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
import json

data = json.load(open('results/sandbox_run_001.json'))
evaluator = ProcurementFitnessEvaluator(stage='1a')

# Пересчитать graduation по сохранённым fitness-векторам без повторной симуляции
passed_count = 0
for q in data:
    f = q['fitness']
    gating = ['cost_efficiency', 'stockout_avoidance', 'budget_discipline', 'reaction_to_risk_events']
    thresholds = {'cost_efficiency': 0.60, 'stockout_avoidance': 0.85,
                  'budget_discipline': 0.95, 'reaction_to_risk_events': 0.50}
    passed = all(f[c] >= thresholds[c] for c in gating)
    passed_count += int(passed)
    print(f\"Q{q['quarter_index']:2d}: 1a_passed={passed}  \" +
          ' '.join(f'{c}={f[c]:.2f}' for c in gating))

print(f'
Stage 1a passed: {passed_count}/30 quarters')
"
```

**Ожидание:** число кварталов с `1a_passed=True` должно быть заметно
больше 2 (текущий результат при всех 6 критериях). Если это так —
диагноз раздела 26.1 подтверждён количественно, и можно двигаться дальше
по плану. Если число почти не изменилось — значит проблема глубже, чем
разлад критериев, и нужно возвращаться к анализу самого мира/энкодера
до внедрения двухстадийности.

### 27.2 Шаг 2 — обновить `procurement_fitness.py` и прогнать 5 независимых Stage 1a прогонов

После подтверждения диагноза — внести изменения раздела 26.4 и запустить
критерий готовности из раздела 26.7:

```bash
for SEED in 1 2 3 4 5; do
  python -m nowa_sandbox.run_sandbox \
    --stage 1a \
    --quarters 30 --seed $SEED \
    --output results/stage1a_seed${SEED}.json \
    --checkpoint checkpoints/stage1a_seed${SEED}.ckpt
done
```

Собрать сводную таблицу:

| seed | graduated | quarter | mean(4 criteria) последние 5 кварталов |
|---|---|---|---|
| 1 | ? | ? | ? |
| 2 | ? | ? | ? |
| 3 | ? | ? | ? |
| 4 | ? | ? | ? |
| 5 | ? | ? | ? |

Критерий перехода (раздел 26.7): ≥3 из 5 graduated, разброс кварталов
до graduation не более ±50%.

### 27.3 Шаг 3 — зафиксировать `stage_1a_baseline`

Из лучшего (или медианного) прогона взять средние значения 4 критериев
за последние 5 успешных кварталов — это войдёт в non-regression guard
для Stage 1b (раздел 26.5). Сохранить как отдельный JSON:

```json
{
  "stage_1a_baseline": {
    "cost_efficiency": 0.82,
    "stockout_avoidance": 0.91,
    "budget_discipline": 1.0,
    "reaction_to_risk_events": 0.85
  },
  "source_checkpoint": "checkpoints/stage1a_seed3.ckpt",
  "computed_from_quarters": [26, 27, 28, 29, 30]
}
```

### 27.4 Шаг 4 — только после 27.3: реализация Stage 1b

Раздел 26.6 (`export_supplier_state`/`carry_supplier_state`,
`run_stage1b_persistent`) реализуется этим шагом, не раньше. Открытый
вопрос 26.6.1 (перенос бюджета) решается эмпирически после первого
пробного Stage 1b прогона — если агент, начинающий Stage 1b сразу после
Stage 1a checkpoint, ведёт себя разумно с дефолтным "не переносить бюджет" —
вопрос закрывается без дальнейшей ревизии.

### 27.5 Не начинать одновременно

Явное ограничение процесса: не писать код Stage 1b (раздел 26.6) и не
собирать 5-seed sweep Stage 1a (27.2) параллельно одной сессией
разработки. Сначала 27.1 → 27.2 → 27.3, затем 27.4. Это прямое следствие
твоего решения "сначала отработать первый вариант, потом переходить ко
второму" — фиксирую это как процессное ограничение, а не только
архитектурное.

---

*Раздел 27 — конкретный план выполнения ревизии v1.1, последовательность
шагов 27.1→27.4 обязательна к соблюдению порядка.*
