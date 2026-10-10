## Аннотация

English version: [NOWA_Procurement_Sandbox_Spec_v1.3_patch.en.md](NOWA_Procurement_Sandbox_Spec_v1.3_patch.en.md)

Патч v1.3 разбирает стоквартальный прогон стадии 1a (семя 1, методика базовой линии v1.2). Бюджетная дисциплина равна 1,000 во всех десяти декадах. Эффективность затрат по декадным средним растёт от 0,704 к 0,857, реакция на риск — от 0,711 к 0,754. Избежание дефицита по декадам составляет 0,444; 0,338; 0,405; 0,335; 0,528; 0,437; 0,255; 0,492; 0,562 и 0,487 и тренда не обнаруживает. Его межквартильный размах равен 0,8351 при размахе остальных критериев 0,000–0,205. Декада кварталов 31–40 не содержит ни одного выпуска, тогда как кварталы 21–30 содержат два, а 41–50 — четыре. Документ относит локальный провал к сложности мира, заданной зерном, и назначает первичным объектом правки параметры мира; вопрос о консолидации `sleep_cycle` остаётся вторичным и проверяется после сужения этих параметров.

Механизм структурно непроходимого квартала описан сочетанием верхних границ предшествующей инициализации: базовый спрос до 50 единиц в день, точка перезаказа в диапазоне около 5–12 дней спроса, начальный запас около 10–30 дней, срок поставки до 21 дня и волатильность спроса до 0,40. Заказ, размещённый при первом сигнале ниже точки перезаказа, может не успеть до исчерпания буфера, так что оптимальная стратегия квартал не спасает. Направление Q3b сужает конфигурацию: максимальный срок поставки 10 дней, максимальный базовый спрос 30, волатильность спроса не выше 0,30, нижняя надёжность поставщика 0,80, точка перезаказа 7–15 дней спроса, начальный запас 15–25 дней. Критерий нового тридцатиквартального прогона на семени, отличном от семени 1: межквартильный размах избежания дефицита ниже 0,50.

Направление Q3a вводит `WorldDifficultyEstimator` и необязательную нормировку сырого `stockout_avoidance` на теоретически достижимую в данном мире долю удовлетворимого спроса. По умолчанию нормировка выключена и включается как диагностика, если после Q3b размах остаётся выше 0,4. Диагностический скрипт сопоставляет кварталы с избежанием дефицита ниже заданного порога и кварталы с величиной не ниже 0,80 по полям сводки мира. Отдельно отмечено, что порог наклона 0,002 при скользящем среднем окна 10 не замечает зарегистрированный наклон эффективности затрат +0,00096, хотя декадные средние показывают рост 0,704 → 0,857; снижение порога до 0,0005 либо добавление разности первых и последних двадцати кварталов больше 0,05 отложено к версии 1.4.

---

# NOWA Procurement Sandbox — Патч v1.3

**Базовые документы:**
- NOWA_Procurement_Sandbox_Spec.md (v1.0)
- v1.1_patch.md — двухстадийный curriculum
- v1.1.1_patch.md — streak + non-regression в условии graduation
- v1.2_patch.md — median baseline + volatility-aware floor

**Статус:** Ready for implementation

---

## Эмпирическое обоснование

100-квартальный прогон Stage 1a (seed 1, v1.2) дал следующую картину:

| Критерий | Декадные средние | Диагноз |
|---|---|---|
| `budget_discipline` | 1.000 во всех 10 декадах | Ceiling — уже освоен полностью |
| `cost_efficiency` | 0.704 → 0.857 | Медленный реальный тренд обучения |
| `reaction_to_risk_events` | 0.711 → 0.754 | Стабильный, умеренный рост |
| `stockout_avoidance` | 0.444, 0.338, 0.405, **0.335**, 0.528, 0.437, **0.255**, 0.492, 0.562, 0.487 | Нет тренда, IQR=0.835 |

**`stockout_avoidance` — аномальная дисперсия.** IQR=0.8351 охватывает почти
весь теоретический диапазон [0, 1]. Три других критерия имеют IQR 0.000–0.205.
Это разрыв на порядок — указывает не на медленное обучение, а на структурно
разные классы задач, которые мир предъявляет агенту в разных кварталах.

**Декада Q31–40: 0 graduated кварталов** при Q21–30: 2 и Q41–50: 4. Провал
локализован в конкретном диапазоне, а не равномерно распределён по 100
кварталам — это признак seed-детерминированной сложности мира, а не
стохастического провала консолидации сна.

**Вывод:** первичный кандидат для v1.3 — Открытый вопрос 3 (параметры
мира создают непроходимые кварталы). Открытый вопрос 2 (sleep consolidation)
остаётся вторичным кандидатом для проверки после Q3.

---

## Анализ: почему `stockout_avoidance` так волатилен

### Механизм "идеально плохого квартала"

`VirtualProduct.reorder_point` и `base_demand_per_day` инициализируются
случайно для каждого нового `ProcurementWorld`. Возможна комбинация:

```
base_demand_per_day = 48 (верхняя граница диапазона [5, 50])
reorder_point = 48 × rng.uniform(5, 12) = ~432 единицы
current_stock  = 48 × rng.uniform(10, 30) = ~720 единицы
lead_time_days = rng.randint(3, 21) = 21 (максимум)
demand_volatility = 0.40 (максимум)
demand_shock_probability = 0.05 → в среднем 4–5 шоков за 90 дней
```

В таком квартале агент видит `below_reorder_point` впервые примерно
на день 4–6, размещает заказ у лучшего доступного поставщика, ждёт
21 день — а к этому моменту высокий спрос уже съел весь буфер. Это
**структурно непроходимый квартал**: оптимальная стратегия не спасает.

### Почему это проблема для curriculum

Stage 1a предполагает, что агент должен научиться управлять стоком —
но если 20–30% кварталов структурно непроходимы для `stockout_avoidance`
независимо от стратегии агента, то:

1. Агент не может отличить "я принял плохое решение" от "этот квартал
   был непроходимым" — нет правильного reward signal для обучения
2. Fitness-метрика смешивает компетентность агента с удачностью мира
3. `stage_1a_baseline` посчитанный на такой смеси — ненадёжен

---

## Два направления фикса (оба реализуются в этом патче)

### Направление Q3a — нормализация сложности квартала

Ввести `WorldDifficultyEstimator`, который для каждого нового мира
вычисляет априорную сложность на основе параметров конфигурации.
`stockout_avoidance` оценивается относительно "максимально достижимого
в этом мире", не абсолютного порога.

### Направление Q3b — ограничение диапазона параметров мира

Сузить диапазоны `ProcurementWorldConfig` так, чтобы "идеально плохих"
кварталов не было. Более консервативный подход, менее точный, но проще
в реализации и достаточен для первой итерации.

**Рекомендуемый порядок:** сначала Q3b (быстро, даёт данные), потом
Q3a (правильно, если Q3b не достаточно).

---

## Затронутые файлы

| Файл | Тип изменения |
|---|---|
| `procurement_world.py` | Сужение диапазонов `_init_products`, `_init_suppliers` (Q3b) |
| `procurement_fitness.py` | Опциональная difficulty-normalization для `stockout_avoidance` (Q3a) |
| `sandbox_config.py` | Новые параметры конфига для контроля диапазонов |
| `tools/world_volatility_diagnostic.py` | Новый инструмент (не часть основного пакета) |
| `tests/` | Тесты на новые диапазоны и normalization |

---

## Изменение 1 (Q3b): `ProcurementWorldConfig` — ограничение диапазонов

### Текущие диапазоны (проблемные)

```python
# В _init_products():
base_demand_per_day = rng.uniform(5, 50)    # диапазон 10x
reorder_point = base_demand * rng.uniform(5, 12)
current_stock  = base_demand * rng.uniform(10, 30)

# В _init_suppliers():
lead_time_days = rng.randint(3, 21)         # разброс 7x
reliability    = rng.uniform(0.70, 0.99)
price_volatility = rng.uniform(0.02, 0.15)
```

### Новые ограниченные диапазоны

```python
@dataclass
class ProcurementWorldConfig:
    # ... существующие поля ...

    # Q3b: difficulty bounding
    max_lead_time_days: int = 10
    """Upper bound for supplier lead time (was hardcoded 21).
    Reducing from 21 to 10 eliminates the 'structurally impossible quarter'
    where a 21-day lead time combined with high demand volatility makes
    stockout unavoidable regardless of agent strategy.
    Spec v1.3 open question Q3."""

    max_demand_per_day: float = 30.0
    """Upper bound for base_demand_per_day (was 50).
    Narrowing the range reduces variance in world difficulty without
    making the task trivially easy."""

    min_reorder_days: float = 7.0
    max_reorder_days: float = 15.0
    """Reorder point expressed in days of demand (was 5..12 days).
    Raising the floor ensures the agent always has an actionable signal
    before stockout becomes inevitable."""

    min_initial_stock_days: float = 15.0
    max_initial_stock_days: float = 25.0
    """Initial stock expressed in days of demand (was 10..30).
    Raising the floor prevents quarters that begin already in crisis."""
```

### Обновление `_init_products` и `_init_suppliers`

```python
def _init_products(self) -> Dict[str, VirtualProduct]:
    products = {}
    for i in range(self.config.n_products):
        pid = f"product_{i:03d}"
        base_demand = self.rng.uniform(5, self.config.max_demand_per_day)
        products[pid] = VirtualProduct(
            product_id=pid,
            base_demand_per_day=base_demand,
            demand_volatility=self.rng.uniform(0.1, 0.3),  # было 0.4
            holding_cost_per_unit=self.rng.uniform(0.5, 2.0),
            stockout_penalty_per_unit=self.rng.uniform(5, 20),
            current_stock=base_demand * self.rng.uniform(
                self.config.min_initial_stock_days,
                self.config.max_initial_stock_days,
            ),
            reorder_point=base_demand * self.rng.uniform(
                self.config.min_reorder_days,
                self.config.max_reorder_days,
            ),
        )
    return products

def _init_suppliers(self) -> Dict[str, VirtualSupplier]:
    suppliers = {}
    for i in range(self.config.n_suppliers):
        sid = f"supplier_{i:03d}"
        suppliers[sid] = VirtualSupplier(
            supplier_id=sid,
            reliability=self.rng.uniform(0.80, 0.99),  # было 0.70
            base_price_multiplier=self.rng.uniform(0.85, 1.15),
            price_volatility=self.rng.uniform(0.02, 0.10),  # было 0.15
            lead_time_days=self.rng.randint(
                3, self.config.max_lead_time_days
            ),
        )
    return suppliers
```

### Почему именно эти значения

| Параметр | Было | Стало | Обоснование |
|---|---|---|---|
| `lead_time_days` max | 21 | 10 | При 10 днях и `reorder_point` в 7+ дней спроса агент **успевает** сделать повторный заказ до stockout при любом разумном спросе |
| `demand_volatility` max | 0.40 | 0.30 | При 0.30 и базовом спросе 30/день, σ=9/день — это ±30%, что достаточно сложно, но не делает квартал непроходимым |
| `reliability` min | 0.70 | 0.80 | Исключает поставщиков, у которых >20% вероятность просрочки — этот класс создаёт цепные stockout через неожиданные задержки |
| `reorder_point` min | 5 дней | 7 дней | Даёт агенту минимум 7 дней на реакцию при любом lead time до 10 дней |
| `initial_stock` min | 10 дней | 15 дней | Квартал не начинается уже в критической ситуации |

---

## Изменение 2 (Q3a): difficulty-normalization для `stockout_avoidance`

Это более точный, но и более сложный подход. Реализуется **после** Q3b,
если после ограничения диапазонов IQR `stockout_avoidance` остаётся
выше 0.4.

### `WorldDifficultyEstimator`

```python
"""nowa_sandbox/world_difficulty.py"""

from dataclasses import dataclass
from typing import Any


@dataclass
class WorldDifficulty:
    """Estimates the inherent difficulty of a world for stockout_avoidance.

    Used to normalize fitness scores so the agent is judged on its
    decisions, not on the luck of world parameters.
    """
    max_lead_time: int
    mean_demand_volatility: float
    min_initial_stock_days: float
    mean_reorder_days: float
    expected_demand_shocks: float   # n_products * days * shock_prob

    def stockout_theoretical_max(self) -> float:
        """Estimate the best possible stockout_avoidance in this world
        for a perfect agent with full information.

        Formula: a perfect agent orders just-in-time at the exact
        reorder point, so the maximum exposed demand is:
        lead_time_days * base_demand * (1 + demand_volatility).
        If initial_stock > this, no stockout is structurally inevitable.

        Returns a value in [0, 1] representing the fraction of demand
        that is theoretically satisfiable by any strategy.
        """
        # Simplified heuristic — detailed implementation TBD
        lead_factor = 1.0 - (self.max_lead_time / 21.0) * 0.3
        volatility_factor = 1.0 - self.mean_demand_volatility * 0.5
        shock_factor = max(0.5, 1.0 - self.expected_demand_shocks * 0.05)
        return max(0.3, min(1.0, lead_factor * volatility_factor * shock_factor))


def estimate_difficulty(world: Any) -> WorldDifficulty:
    """Snapshot world difficulty from a ProcurementWorld instance."""
    products = list(world.products.values())
    suppliers = list(world.suppliers.values())
    n_days = world.config.days_per_quarter
    n_products = len(products)

    return WorldDifficulty(
        max_lead_time=max((s.lead_time_days for s in suppliers), default=10),
        mean_demand_volatility=(
            sum(p.demand_volatility for p in products) / n_products
            if n_products else 0.25
        ),
        min_initial_stock_days=(
            min(p.current_stock / max(p.base_demand_per_day, 0.01)
                for p in products)
            if n_products else 10.0
        ),
        mean_reorder_days=(
            sum(p.reorder_point / max(p.base_demand_per_day, 0.01)
                for p in products) / n_products
            if n_products else 7.0
        ),
        expected_demand_shocks=n_products * n_days * world.config.demand_shock_probability,
    )
```

### Интеграция в `ProcurementFitnessEvaluator`

```python
def _stockout_avoidance(
    self,
    world: Any,
    normalize_difficulty: bool = False,
) -> float:
    """
    normalize_difficulty=False (default, Q3b path): raw fraction,
    identical to v1.0-v1.2 behaviour.

    normalize_difficulty=True (Q3a path): score is divided by the
    world's theoretical maximum, so an agent doing the best possible
    in a hard world scores ~1.0, not 0.3.
    """
    total_demand = sum(
        p.base_demand_per_day * world.day for p in world.products.values()
    )
    total_stockout = sum(
        p.cumulative_stockout_units for p in world.products.values()
    )
    if total_demand <= 0:
        return 1.0
    stockout_ratio = total_stockout / total_demand
    raw_score = max(0.0, 1.0 - min(1.0, stockout_ratio * 5.0))

    if not normalize_difficulty:
        return raw_score

    from .world_difficulty import estimate_difficulty
    difficulty = estimate_difficulty(world)
    theoretical_max = difficulty.stockout_theoretical_max()
    if theoretical_max <= 0.0:
        return raw_score
    return min(1.0, raw_score / theoretical_max)
```

Добавить `normalize_stockout_difficulty: bool = False` в
`ProcurementFitnessEvaluator.__init__` и передавать в
`_stockout_avoidance`.

---

## Изменение 3: диагностический инструмент `world_volatility_diagnostic.py`

```python
"""tools/world_volatility_diagnostic.py

Analyse whether stockout_avoidance zeros correlate with world parameters
(high lead time, high demand volatility) rather than agent decisions.

This directly tests Open Question 3 from spec v1.2: are some quarters
structurally impossible for stockout_avoidance?
"""

import argparse
import json
import statistics
from pathlib import Path
from typing import List


def main():
    parser = argparse.ArgumentParser(
        description="Test if stockout zeros correlate with world difficulty."
    )
    parser.add_argument("results_json")
    parser.add_argument(
        "--zero-threshold", type=float, default=0.10,
        help="stockout_avoidance below this is treated as a 'zero quarter'."
    )
    args = parser.parse_args()

    quarters = json.loads(Path(args.results_json).read_text())

    zero_quarters = [
        q for q in quarters
        if q["fitness"]["stockout_avoidance"] < args.zero_threshold
    ]
    good_quarters = [
        q for q in quarters
        if q["fitness"]["stockout_avoidance"] >= 0.80
    ]

    print(f"Total quarters: {len(quarters)}")
    print(f"Zero quarters (sa < {args.zero_threshold}): {len(zero_quarters)}")
    print(f"Good quarters (sa >= 0.80): {len(good_quarters)}")
    print()

    # Extract world summary fields if available
    for label, group in [("ZERO quarters", zero_quarters),
                          ("GOOD quarters", good_quarters)]:
        if not group:
            continue
        print(f"=== {label} ===")
        ws_list = [q.get("world_summary", {}) for q in group]

        for field in [
            "n_orders_placed", "n_orders_delivered",
            "n_suppliers_defaulted", "total_stockout_units",
            "total_holding_cost", "spent_ratio",
        ]:
            vals = [safe_float(ws.get(field)) for ws in ws_list
                    if ws.get(field) is not None]
            if vals:
                print(f"  {field:28s} mean={statistics.mean(vals):.3f} "
                      f"std={statistics.pstdev(vals):.3f}")
        print()

    # Quarter indices
    print(f"Zero quarter indices: "
          f"{[q['quarter_index'] for q in zero_quarters]}")
    print(f"Good quarter indices: "
          f"{[q['quarter_index'] for q in good_quarters[:10]]}...")


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


if __name__ == "__main__":
    main()
```

### Использование

```bash
python tools/world_volatility_diagnostic.py \
  results/stage1a_seed1_extended.json \
  --zero-threshold 0.05
```

**Интерпретация:**
- Если `n_suppliers_defaulted` у zero-кварталов значимо выше, чем у
  good-кварталов → `supplier_default_probability` слишком высок
- Если `spent_ratio` у zero-кварталов близок к 1.0 → агент исчерпал
  бюджет, не имея возможности заказать достаточно товара (бюджетное
  сжатие вынуждало недозаказывать)
- Если нет разницы ни в одном поле → проблема в стратегии агента,
  не в параметрах мира

---

## Тест-кейсы

### `tests/test_world_difficulty_bounds.py` (новый файл)

```python
"""Tests ensuring Q3b parameter bounding eliminates impossible quarters."""

import random
import pytest
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig


class TestLeadTimeBound:

    def test_max_lead_time_respected(self):
        config = ProcurementWorldConfig(n_suppliers=5, seed=42, max_lead_time_days=10)
        world = ProcurementWorld(config)
        for supplier in world.suppliers.values():
            assert supplier.lead_time_days <= 10, (
                f"supplier {supplier.supplier_id} lead_time={supplier.lead_time_days} "
                f"exceeds max_lead_time_days=10"
            )

    def test_default_max_lead_time_is_10(self):
        """New default must be 10, not 21."""
        config = ProcurementWorldConfig()
        assert config.max_lead_time_days == 10

    def test_lead_time_always_gte_3(self):
        """Lower bound unchanged."""
        config = ProcurementWorldConfig(n_suppliers=20, seed=1, max_lead_time_days=10)
        world = ProcurementWorld(config)
        for supplier in world.suppliers.values():
            assert supplier.lead_time_days >= 3


class TestDemandVolatilityBound:

    def test_volatility_capped_at_0_3(self):
        config = ProcurementWorldConfig(n_products=20, seed=42)
        world = ProcurementWorld(config)
        for product in world.products.values():
            assert product.demand_volatility <= 0.30 + 1e-9, (
                f"product {product.product_id} volatility={product.demand_volatility} "
                f"exceeds 0.30"
            )


class TestInitialStockFloor:

    def test_initial_stock_at_least_min_days(self):
        config = ProcurementWorldConfig(
            n_products=10, seed=42, min_initial_stock_days=15.0
        )
        world = ProcurementWorld(config)
        for pid, product in world.products.items():
            days_of_stock = (product.current_stock /
                             max(product.base_demand_per_day, 0.01))
            assert days_of_stock >= 14.0, (  # -1 day tolerance for float
                f"product {pid} has only {days_of_stock:.1f} days of stock "
                f"(min expected: 15)"
            )


class TestReorderPointFloor:

    def test_reorder_point_covers_max_lead_time(self):
        """With min_reorder_days=7 and max_lead_time=10, there's always
        a 7-day buffer before hitting reorder_point from which the agent
        has time to order and receive before stockout."""
        config = ProcurementWorldConfig(
            n_products=10, seed=42,
            max_lead_time_days=10, min_reorder_days=7.0
        )
        world = ProcurementWorld(config)
        for pid, product in world.products.items():
            reorder_days = (product.reorder_point /
                            max(product.base_demand_per_day, 0.01))
            assert reorder_days >= 6.5, (  # -0.5 tolerance
                f"product {pid} reorder_point covers only {reorder_days:.1f} "
                f"days of demand (min expected: 7)"
            )


class TestBackwardCompatibility:

    def test_old_config_without_new_fields_still_works(self):
        """Code that constructs ProcurementWorldConfig without the new
        difficulty-bounding fields must continue to work unchanged."""
        config = ProcurementWorldConfig(
            initial_budget=50_000.0,
            n_products=5, n_suppliers=3,
            days_per_quarter=90, seed=1,
        )
        world = ProcurementWorld(config)
        assert world is not None
        world.tick()
```

---

## Definition of Done

- [ ] `ProcurementWorldConfig` содержит новые поля с документированными
      дефолтами: `max_lead_time_days=10`, `max_demand_per_day=30.0`,
      `min_reorder_days=7.0`, `max_reorder_days=15.0`,
      `min_initial_stock_days=15.0`, `max_initial_stock_days=25.0`
- [ ] `_init_products` и `_init_suppliers` используют новые поля вместо
      захардкоженных диапазонов
- [ ] Все тест-кейсы `test_world_difficulty_bounds.py` зелёные
- [ ] Прогон 30 кварталов Stage 1a с новыми параметрами (новый seed, не seed 1,
      чтобы не использовать "знакомые" данные): IQR `stockout_avoidance`
      снизился ниже 0.50 (было 0.835 на 100 кварталах)
- [ ] `world_volatility_diagnostic.py` запущен на новых результатах — разница
      между zero-кварталами и good-кварталами по `world_summary` полям либо
      сократилась, либо объяснена
- [ ] `normalize_stockout_difficulty` (`WorldDifficultyEstimator`) реализован
      как опция, но **не включён по умолчанию** — только для диагностики,
      до подтверждения что Q3b недостаточно

---

## Открытые вопросы (переходят в v1.4 если не закроются)

**Q2 (sleep consolidation)** — остаётся кандидатом, но приоритет снижен:
слабый позитивный тренд (`cost_efficiency` +0.704→0.857, graduation кластеры
в Q41–50, Q81–90, Q91–100) указывает на то, что консолидация работает,
просто медленно. Если после Q3b IQR `stockout_avoidance` снизится и агент
начнёт graduation чаще — Q2 закрывается без кода. Если нет — нужен
отдельный анализ hippocampus/cortex между конкретными кварталами.

**Порог `LEARNING_TREND` в `trend_diagnostic.py`** — slope > 0.002 при
MA10 оказался слишком строгим: слабый реальный тренд (slope +0.00096 у
`cost_efficiency`) он не детектирует, хотя декадные средние показывают
рост 0.704→0.857. Рассмотреть снижение порога до 0.0005 или добавление
второго критерия (first20/last20 разница > 0.05) в v1.4.

---

*Патч v1.3. Обоснован данными 100-квартального прогона. Первичный фикс —
Q3b (сужение параметров мира). Q3a (difficulty normalization) реализуется
как диагностическая опция, не как дефолт. Тест успешности: IQR
`stockout_avoidance` < 0.50 после нового прогона.*
