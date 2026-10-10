## Аннотация

English version: [chinchilla_agent_spec.en.md](chinchilla_agent_spec.en.md)

Научное описание установки: [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md).

Документ задаёт техническую спецификацию версии 1.0 целевого когнитивного агента «шиншилла», построенного на архитектуре NOWA. Фиксируются репертуар из семидесяти четырёх действий с этологической группировкой, четырнадцать типов поведенческих цепочек, восемнадцать именованных зон клетки и трёхслойная команда визуализации, различающая действие, позу и микродвижение. Динамика организма выводится из пяти накопительных драйвов и системы энергии, восьмимерного аффективного вектора с заданными антагонистическими парами осей, пяти нейромодуляторов и конкуренции каналов базальных ганглиев с итоговым выбором через таламический вентиль, температура которого зависит от норадреналина.

Спецификация отдельно определяет эпизодическую память гиппокампа, образование корковых паттернов и обновление памяти цепочек исключительно в фазе сна, а также изолированное обучение временных различий по правилу TD(0), читающее скалярную награду и слепок состояния. Заданы жёсткие инварианты с отказом при нарушении, мягкие ограничения, регистрируемые в журнале отказов, и количественные пределы доли мнемического импульса, числа внутренних циклов и речевых событий. Минимальный снимок для восстановления включает драйвы, энергию, аффект, нейромодуляторы, гиппокамп, кору, память цепочек, слой ценности и каналы базальных ганглиев.

Сценарии TC-01–TC-35 сформулированы как ожидаемые реакции на заданные начальные условия: рефлексы потребностей, развёртывание цепочек, аффективные переходы, соблюдение ограничений, патологии благополучия, научение и контракт вывода pygame. Эти сценарии задают приёмочные условия спецификации. Документ описывает целевую архитектуру организма. Точка входа демонстрации импортирует соответствующие модули ядра и одновременно сохраняет локальные SchedulingSystem и MemorySystem.

---

# Chinchilla Agent — Техническая спецификация
**Когнитивный ИИ-тамагочи · Python / pygame · Версия 1.0**

---

## 1. Обзор системы

Chinchilla Agent — автономный когнитивный агент поверх NOWA-архитектуры (нейроморфный организм с аффектом). Реализует этологически достоверное поведение виртуальной чинчиллы: драйвы потребностей, 8-мерный аффект, подкрепляющее обучение TD(0), консолидацию памяти во сне.

### 1.1 Роли компонентов

| Модуль | Ответственность |
|---|---|
| `autonomous_organism.py` | Главный цикл: DriveSystem → InternalSimulationLoop → EnergySystem → вывод тика |
| `basal_ganglia.py` | Go/NoGo конкуренция каналов; финальный выбор через ThalamicGate (softmax) |
| `affective_space.py` | 8-мерный аффект A(t) ∈ [-1,1]^8 |
| `neuromodulators.py` | 5 нейромодуляторов (DA, 5HT, NE, CORT, ACh) — регуляторы обучения |
| `hippocampus.py` | Эпизодическая память, fuzzy-recall, сигнал новизны |
| `value_layer.py` | TD(0): V(s), δ = r + γV(s') − V(s); изолирован от аффекта |
| `sleep.py` | Консолидация — единственный механизм обобщения, только вне бодрствования |
| `temporal_chains.py` | ChainMemory: цепочки событий → смещение давления при выборе |
| Наборы данных (JSON) | Инициализация BG-каналов (`habits.json`) и пул реализаций (`realizations_*.json`) |
| движок pygame | Рендер спрайтов; получает `{anim, sfx, position, duration, subtitle, loop, layer}` |

### 1.2 Поток данных за один тик

```
organism_step(dt=1s)
  → update_affect → update_memory_decay → update_baseline
  → regulate_affect → drive_system.update → evaluate_drive_thresholds
  → InternalSimulationLoop.run_cycle → BG pipeline → ActionRealizer.realize
  → pygame output: {anim, sfx, position, duration, subtitle, loop, layer}
```

---

## 2. Архитектура действий

### 2.1 Репертуар (74 действия)

| Категория | N | Примеры |
|---|---|---|
| Базовые потребности | 10 | eat_pellets, eat_hay, eat_treat, drink_water, gnaw_mineral, sleep_house, doze_shelf, rest_loaf, toilet_main, toilet_mark |
| Локомоция | 9 | run_wheel, jump_shelf_up/down, jump_hop_play, patrol_floor, sniff_corners, sniff_air, stand_upright, climb_bars, hang_bars |
| Исследование / игра | 14 | explore_corner, observe_room, play_toy, toss_toy, chase_toy, gnaw_toy, gnaw_wood, rearrange_bedding, dig_bedding, cache_food, carry_object, inspect_new_obj, problem_solve, dust_bath |
| Груминг | 10 | groom_face, groom_body, groom_tail, groom_paws, scratch_head, stretch_body, yawn, body_shake, overgroom_fur, overgroom_other |
| Социальное | 12 | approach_door, vocalize_chirp/squeak/bark/alarm/teeth, sniff_hand, take_treat, allow_pet, solicit_pet, avoid_hand, watch_owner, follow_finger |
| Стресс / защита | 9 | freeze, hide_house, flee_corner, alarm_call, thump_hind, fur_slip, bar_chewing, stereotypy_pacing, wall_jump |
| Постуральные / микро | 7 | ear_forward, ear_flat, whisker_twitch, tail_raise, press_flat, eye_half_close, nose_twitch |

### 2.2 Структура output (pygame-команда)

```json
{
  "anim":     "eat_loop",       
  "sfx":      "chewing",        
  "position": "bowl_pellets",   
  "duration": [10, 30],         
  "subtitle": "ест корм",       
  "loop":     true,             
  "layer":    "action"          
}
```

### 2.3 Слои рендера

| Слой | Поведение | Примеры |
|---|---|---|
| `action` | Главное действие; двигает спрайт; занимает основной канал | run_wheel, eat_pellets, hide_house |
| `postural` | Накладывается поверх action, не прерывает его | ear_flat, press_flat, tail_raise |
| `micro` | Короткие рефлексы, `loop=false`, не блокируют action | yawn, whisker_twitch, groom_face |

### 2.4 Позиции (18 зон клетки)

```
floor  house  bowl_pellets  bowl_hay  waterer  mineral  litter  wheel
shelf_lower  shelf_mid  shelf_upper  bars  bars_top  corner  door
toy  dustbath  object  current
```

`current` — анимация без перемещения спрайта.

---

## 3. Поведенческие цепочки (14 типов)

| Цепочка | Последовательность |
|---|---|
| Утреннее пробуждение | sleep_house → stretch_body → yawn → groom_face → drink_water → eat_pellets → patrol_floor → run_wheel |
| Еда + груминг | eat_pellets → eat_hay → drink_water → groom_face → groom_body → rest_loaf |
| Всплеск активности | stand_upright → sniff_air → run_wheel → jump_hop_play → toss_toy → chase_toy → jump_shelf_up → observe_room → drink_water |
| Исследование новинки | sniff_air → stand_upright → approach_door → inspect_new_obj → sniff_object → gnaw_toy → carry_object → rearrange_bedding |
| Полный груминг | groom_face → groom_body → groom_paws → groom_tail → scratch_head → body_shake → rest_loaf |
| Купалка | inspect_new_obj → dust_bath → body_shake → groom_body → groom_tail → rest_loaf |
| Социальный контакт | watch_owner → approach_door → vocalize_chirp → sniff_hand → take_treat → allow_pet → solicit_pet |
| Лёгкий испуг | ear_forward → whisker_twitch → freeze → ear_flat → press_flat → sniff_air → stand_upright → patrol_floor |
| Сильный испуг | alarm_call → flee_corner → freeze → hide_house → press_flat → [пауза] → eye_half_close → doze_shelf |
| Хронический стресс | observe_room → bar_chewing → stereotypy_pacing → overgroom_fur → hide_house → vocalize_bark → [цикл] |
| Отход ко сну | eat_hay → drink_water → groom_body → rearrange_bedding → cache_food → hide_house → sleep_house |
| Территориальный обход | stretch_body → patrol_floor → sniff_corners → toilet_mark → stand_upright → climb_bars → observe_room |
| Гнездование | rearrange_bedding → dig_bedding → carry_object → cache_food → rearrange_bedding [цикл] |
| Гиперактивность | jump_hop_play → run_wheel → climb_bars → hang_bars → jump_shelf_up → jump_shelf_down → toss_toy → chase_toy → drink_water |

---

## 4. Система драйвов и энергии

### 4.1 Драйвы (5 переменных, ∈ [0,1])

| Драйв | Накоп./с | Разряд/с | Порог | Аффект-веса |
|---|---|---|---|---|
| curiosity | 0.020 | 0.001 | 0.35 | curiosity +0.025, stress −0.005, stability +0.004 |
| social_drive | 0.010 | 0.0015 | 0.35 | trust +0.020, attachment +0.014, stress −0.010 |
| goal_tension | 0.012 | 0.0010 | 0.35 | dominance +0.018, stability +0.006, stress +0.010 |
| exploration | 0.011 | 0.0012 | 0.35 | curiosity +0.020, dominance +0.008, stress −0.005 |
| energy_need | 0.004 | 0.0010 | 0.35 | stress +0.008, arousal +0.004 |

Разряд при выборе: активный драйв `−0.18·dt`; social_drive при речевом событии `−0.22·dt`.

### 4.2 EnergySystem

| Параметр | Значение |
|---|---|
| Базовый расход (idle) | 0.06 · dt |
| Расход при internal_cycle | +0.28 (составляющая cognitive_load) |
| Расход при речевом событии | +0.18 |
| Скорость восстановления | 0.050 · rest_time |
| Порог подавления цикла | energy < 0.25 → suppress_internal_cycles = True |
| Аварийный пол | energy < 0.05 → energy_deadlock после 8 тиков подряд |

---

## 5. Аффективное пространство

8-мерный вектор A(t) ∈ [-1, 1]^8. Обновляется импульсами: `external`, `memory`, `internal`.

| Ось | Семантика | Влияние на поведение |
|---|---|---|
| valence | Позитивный/негативный тон | risk↑, word_choice↑ при высоком |
| arousal | Возбуждение/заторможенность | response_speed↑ |
| dominance | Уверенность/подчинённость | risk↑, goal_priority↑ |
| stress | Напряжение/угроза | все decision-измерения↓; антагонист valence/trust/dominance |
| trust | Доверие к среде/хозяину | empathy↑; снижается при stranger_near |
| curiosity | Интерес/скука | goal_priority↑; антагонист stability |
| stability | Устойчивость | goal_priority↑; снижается при новизне |
| attachment | Привязанность | empathy↑; накапливается при bonding |

**Противоположные пары:** (valence, stress), (trust, stress), (dominance, stress), (curiosity, stability).

**Регуляция перегрузки:** если `state_norm / norm_cap > 0.80` → stress `−0.45r`, arousal `−0.35r`, stability `+0.30r`.

---

## 6. Нейромодуляторы

Базовый уровень ≈ 0.1, период полураспада ≈ 90 с. Не принимают решений — только модулируют.

| Нейромодулятор | Базовый | Что регулирует |
|---|---|---|
| Дофамин (DA) | 0.10 | Скорость TD-обучения; Go+ при +reward (+0.25); ThalamicGate temperature↓ |
| Серотонин (5HT) | 0.10 | Долгосрочное настроение; +0.01/цикл при стабильных повторениях |
| Норадреналин (NE) | 0.10 | ThalamicGate temperature↑ (→ exploration); новизна (+0.30), конфликт (+0.15) |
| Кортизол (CORT) | 0.05 | Тормоз обучения; neg.reward (+0.20), конфликт (+0.25); антагонист DA |
| Ацетилхолин (ACh) | 0.10 | Пластичность vs стабильность; +0.25 при новизне, −0.05 при повторении |

---

## 7. Базальные ганглии и выбор действия

### 7.1 Пайплайн выбора

1. Cortex вычисляет вектор давлений: `{action_id → float}`
2. `BG.process()`: Go/NoGo с DA, CORT, NE, habit_strength, aversive_signal
3. `ThalamicGate.select()`: softmax с `T = base_T · (1 + NE_gain · NE)`
4. `ActionRealizer.realize()`: реализация из пула по activation_pressure + context_match
5. Pygame получает `{anim, sfx, position, duration, subtitle, loop, layer}`

### 7.2 Сила привычек — инициализация из habits.json

| strength | Тип | Примеры |
|---|---|---|
| 3.0 | Рефлексы / выживание | hunger_high→eat_pellets, fear_extreme→alarm_call, prev:sleep_house→stretch_body |
| 2.5 | Сильные инстинкты | energy_high→run_wheel, grooming_need→groom_body, fear_acute→flee_corner |
| 2.0 | Устойчивые паттерны | owner_present→approach_door, alarmed→vocalize_bark |
| 1.5 | Умеренные привычки | hand_near→sniff_hand, fear_acute→ear_flat, rearrange_bedding→dig_bedding |
| 1.0 | Слабые, нарабатываемые | nighttime→run_wheel, explore_corner, eye_half_close при спокойствии |
| 0.1–0.3 | Подавленные патологические | stress_high→bar_chewing (0.3), stress_chronic→stereotypy_pacing (0.2), stress_extreme→overgroom_other (0.1) |

---

## 8. Система памяти

### 8.1 Гиппокамп (эпизодическая)

| Параметр | Значение |
|---|---|
| max_experiences | 1000 |
| top_k_recall | 5 |
| novelty_window | 25 последних |
| activation_decay_half_life | 3600 с |
| decay_rate | 0.015 |
| reinforce_similarity_threshold | 0.85 |

**Сигнал новизны:** если experience уникален для последних 25 → DA +0.30, NE +0.20, ACh +0.25.

### 8.2 Консолидация сна (CortexMemory)

1. Кластеризация эпизодов гиппокампа → CorticalPattern (сигнатура + strength)
2. net_affect < 0 → NoGo+; net_affect > 0 → Go+
3. Нестабильные опыты деградируют
4. ChainMemory обновляется цепочками с net_affect ≠ 0

> **Правило:** CortexMemory и ChainMemory изменяются **исключительно** в фазе сна. Вне сна — только для чтения.

---

## 9. TD-обучение и ValueLayer

`δ = r + γ·V(s') − V(s)`. Изолирован от аффекта и памяти — читает только скалярную награду и слепки состояния.

### 9.1 Параметры

| Параметр | Значение |
|---|---|
| γ (discount) | 0.95 |
| α (скорость) | 0.05 · (1 + DA) |
| Кеш состояний | 10 000 (LRU) |
| Кодирование | context_signature, action, intensity, novelty, conflict |

### 9.2 Сигналы награды

| Событие | r | Аффект |
|---|---|---|
| Удовлетворение потребности (еда/вода/сон) | +1.0 | valence +0.5, stress −0.4 |
| Купание в пыли | +0.8 | valence +0.7, arousal +0.3 |
| Лакомство от хозяина | +0.9 | valence +0.8, trust +0.3 |
| Поглаживание (allow_pet) | +0.6 | valence +0.5, attachment +0.4 |
| Успешное исследование (problem_solve) | +0.5 | curiosity +0.5, dominance +0.2 |
| Игра (jump_hop_play, chase_toy) | +0.4 | valence +0.4, arousal +0.5 |
| Патологическое (bar_chewing, stereotypy) | −0.8 | stress +0.6, stability −0.5 |
| Стресс-событие (freeze из-за угрозы) | −0.5 | stress +0.7, trust −0.3 |
| Срыв меха | −1.0 | stress +1.0, trust −0.5 |

---

## 10. Система ограничений

### 10.1 Жёсткие инварианты — OrganismInvariantError при нарушении

| ID | Инвариант | Условие нарушения |
|---|---|---|
| INV-01 | Аффект изменяется только через интерфейс | affective_core не имеет `.step()` или `.apply_impulse()` |
| INV-02 | Все драйвы ∈ [0, 1] | drive < 0 или > 1 после update() |
| INV-03 | Нет устаревших мета-драйвов | `self_reflection` или `emotional_discharge` в drive_system.drives |
| INV-04 | agent_mode ∈ {IDLE, ACTIVE, REFLECTION} | любое другое значение |
| INV-05 | Энергия и усталость ∈ [0, 1] | energy или fatigue вне диапазона |
| INV-06 | Активный драйв требует internal_cycle | active_drive ≠ None AND triggered=False AND limit_reached=False |
| INV-07 | speech_load только при речевом событии | load_components.speech > 0 при speech_event=False |
| INV-08 | Когнитивная нагрузка простоя < 0.3 | cognitive_load ≥ 0.3 без cycle и speech |
| INV-09 | Пауза между речевыми событиями | events[-1] − events[-2] < cooldown_seconds |

### 10.2 Мягкие ограничения (failure_log, без исключения)

| Код | Условие | Следствие |
|---|---|---|
| dt_anomaly | dt ≤ 0, < 0.05, > 1.0 или не finite | Заменяется на dt_min=0.05 |
| drive_runaway_growth | drive до clamp < 0 или > 1 | Ограничение применено |
| speech_spam | Превышен лимит речи | Речь подавлена |
| infinite_internal_cycle_loop | limit_reached=True | Цикл пропущен |
| idle_fatigue_non_recovering | Усталость растёт в idle/low_energy | Предупреждение |
| energy_deadlock | energy < 0.05 ≥ 8 тиков подряд | Критическое предупреждение |
| affect_regulation_failed | Исключение при apply_impulse(regulation) | Регуляция пропущена |

### 10.3 Ограничения путей данных

| Ограничение | Правило |
|---|---|
| Обучение только во сне | Cortex и ChainMemory изменяются исключительно в sleep-фазе |
| ValueLayer изолирован | TD-обновление не читает/не пишет в affective_space, hippocampus, cortex |
| Только 3 типа импульсов | external, memory, internal — иные источники → отказ |
| recall_share ≤ 0.4 | Импульс памяти не превышает 40% суммарной импульсной энергии тика |
| Internal cycles ≤ 8 за 60 с | InternalSimulationLoop.max_internal_cycles_per_window |
| Speech events ≤ 5 за 30 с | SpeechGovernor.max_speech_events_per_interval |
| Recalls ≤ 6 за цикл | InternalSimulationLoop.max_active_memory_recalls |
| Патологические действия | bar_chewing/stereotypy/overgroom: r=−0.8; wellbeing_flag=True в parameters |

---

## 11. Тест-кейсы

### TC-01…TC-05: Базовые рефлексы

| ID | Начальное состояние | Ожид. действие | Проверка |
|---|---|---|---|
| TC-01 | hunger_high=1.0, прочие < 0.35 | eat_pellets / eat_hay | position ∈ {bowl_pellets, bowl_hay}; groom_face в течение 3 тиков после |
| TC-02 | thirst_high=1.0 | drink_water | position=waterer; sfx=drinking; после → groom_face |
| TC-03 | fatigue_high=1.0, energy < 0.25 | sleep_house | position=house; suppress_internal_cycles=True во время сна |
| TC-04 | toilet_need=1.0 | toilet_main | position=litter; duration ∈ [2,6]; возврат к прежней позиции |
| TC-05 | dustbath_available=True + grooming_need=0.7 | dust_bath | position=dustbath; sfx=rustling; следом body_shake → groom_body |

### TC-06…TC-10: Поведенческие цепочки

| ID | Триггер | Ожид. цепочка | Проверка |
|---|---|---|---|
| TC-06 | prev:sleep_house; energy восстановлена | stretch_body → yawn → groom_face | Все 3 за ≤ 10 тиков; layer=micro для groom_face |
| TC-07 | prev:run_wheel; hunger_low, thirst_mod | eat_pellets → drink_water → groom_face | bowl_pellets → waterer; prev:-токены сработали |
| TC-08 | dustbath_available + grooming_need | dust_bath → body_shake → groom_body → rest_loaf | body_shake.loop=false; groom_body.layer=action |
| TC-09 | new_object; state:calm; curiosity_high | sniff_object → inspect_new_obj → gnaw_toy | object → object → toy; без flee_corner |
| TC-10 | owner_present + trust>0.7 + treat_offered | approach_door → sniff_hand → take_treat → allow_pet | solicit_pet возможна если trust > 0.75 |

### TC-11…TC-15: Аффективные переходы

| ID | Триггер | Аффект | Проверка действий |
|---|---|---|---|
| TC-11 | fear_extreme (sudden_loud_sound) | stress→max; trust↓ | alarm_call; ear_flat (postural); flee_corner; hide_house за ≤ 5 тиков |
| TC-12 | state:stress_high + hand_near | trust↓; stress↑ | vocalize_teeth → vocalize_bark → avoid_hand (3 уровня предупреждения) |
| TC-13 | state:trusting + allow_pet ≥ 5 тиков | attachment +0.4; valence +0.5 | solicit_pet с вер. > 0.5; eye_half_close следом |
| TC-14 | state_norm/norm_cap > 0.80 | regulation_active=True | stress −0.45r; arousal −0.35r; stability +0.30r; affect_applied=True |
| TC-15 | fur_slip | stress→1.0; trust→min | r=−1.0 в ValueLayer; CORT +0.20; DA резко снижается |

### TC-16…TC-20: Ограничения и инварианты

| ID | Сценарий | Ожидаемый результат |
|---|---|---|
| TC-16 | Подать dt=0 | failure_log ← dt_anomaly; dt_used=0.05; тик выполнен штатно |
| TC-17 | Форсировать drive=1.5 через set_drive() | OrganismInvariantError INV-02; значение зажато на 1.0 |
| TC-18 | Запустить 9 internal_cycle за 60 с | 9-й → limit_reached=True; failure_log ← infinite_internal_cycle_loop |
| TC-19 | energy < 0.05 в течение 10 тиков | energy_deadlock в failure_log после 8-го тика |
| TC-20 | Внедрить 'self_reflection' в drives напрямую | OrganismInvariantError INV-03 |

### TC-21…TC-25: Патологии и благополучие

| ID | Условие | Ожидаемое поведение |
|---|---|---|
| TC-21 | boredom_high + understimulated ≥ 120 с | bar_chewing появляется; wellbeing_flag=True; r=−0.8; CORT растёт |
| TC-22 | stress_chronic + prev:bar_chewing | stereotypy_pacing следует; DA снижается; nogo_weight bar_chewing растёт |
| TC-23 | Нормализация после TC-22 (игрушка, хозяин) | bar_chewing/pacing снижаются за ≤ 60 тиков; valence восстанавливается |
| TC-24 | overgroom_other при stress_extreme | r=−0.8; habit_strength НЕ растёт (nogo усиливается); wellbeing_flag=True |
| TC-25 | wall_jump при panic | position=bars; sfx=thump_soft; после → freeze или hide_house; r=−0.5 |

### TC-26…TC-30: TD-обучение и память

| ID | Сценарий | Проверка |
|---|---|---|
| TC-26 | 10 повторений: take_treat → r=+0.9 | go_weight take_treat↑; V(s_treat)↑; DA↑; activation_count +10 |
| TC-27 | Фаза сна после TC-26 | ChainMemory: (sniff_hand, take_treat) net_affect > 0; CorticalPattern создан |
| TC-28 | После TC-27: owner_present + hand_near | Смещение ChainMemory → take_treat получает +pressure; выбирается быстрее |
| TC-29 | 5 повторений: bar_chewing → r=−0.8 | nogo_weight bar_chewing↑; V(s_bored)↓; CORT↑; habit_strength НЕ растёт |
| TC-30 | recall_impulse_share > 0.4 | Зафиксировано на ≤ 0.4; предупреждение в failure_log |

### TC-31…TC-35: Pygame-движок

| ID | Действие | Ожидаемый вывод |
|---|---|---|
| TC-31 | run_wheel (action layer) | Спрайт → zone=wheel; anim=run_wheel_loop; sfx=wheel_spin; loop=True |
| TC-32 | ear_flat (postural) + freeze (action) одновременно | Оба слоя рендерятся: freeze_hold на current И ears_flat_hold наложен поверх |
| TC-33 | yawn (micro) во время run_wheel | yawn_anim один раз (loop=False) поверх; после — run_wheel продолжается |
| TC-34 | sleep_house; duration=[240,960] | Спрайт в house 240–960 тиков; sfx=null; прерывается при hunger_high |
| TC-35 | Неизвестный action_id от ActionRealizer | pygame: запасной idle_loop на current; без аварийного останова; событие логируется |

---

## 12. Временная шкала

| Параметр | Значение |
|---|---|
| 1 тик | 1 секунда реального времени |
| LifeLoopController.min_interval | 0.05 с (20 fps max) |
| dt clamp | [0.05, 1.0] с |
| Рефлекс (yawn, freeze) | duration [2, 2] тиков |
| Короткое действие (take_treat) | duration [4, 10] тиков |
| Среднее действие (eat_pellets) | duration [10, 30] тиков |
| Долгое действие (run_wheel) | duration [10, 80] тиков |
| Сон (sleep_house) | duration [240, 960] тиков (4–16 мин) |
| Окно internal_cycles | 60 тиков → max 8 циклов |
| Пауза речи | 5 тиков |
| Период полураспада нейромод. | 90 тиков |
| decay_half_life гиппокампа | 3600 тиков |

---

## 13. Хранение состояния (snapshot)

Минимальный набор для полного восстановления:

```
drives | energy | affect | neuromodulators | hippocampus
cortex | chain_memory | value_layer | bg_channels | realization_memory
```

> **Важно:** CortexMemory и ChainMemory изменяются только в sleep-фазе. При загрузке без прошедшего сна — восстанавливаются как есть, без повторной консолидации.

---

## 14. Глоссарий

| Термин | Определение |
|---|---|
| ActionChannel | Канал BG: go_weight, nogo_weight, habit_strength, selection_count, last_outcome |
| ActionRealizer | Выбирает реализацию из пула по activation_pressure + context_match |
| affective_space | 8-мерный вектор A(t) ∈ [-1,1]^8 — каноническое аффективное состояние |
| ChainMemory | Хранилище TemporalChain; обновляется во сне; смещение давления при выборе |
| CortexMemory | Медленная память; изменяется только во сне |
| DriveSystem | 5 накопительных переменных; выбирает активный драйв по порогу и весам |
| EnergySystem | Энергия + усталость; подавляет internal_cycles при energy < 0.25 |
| habit_strength | Начальный go_weight из habits.json — инициализация BG-каналов |
| InternalSimulationLoop | Генерирует гипотезы, симулирует эффект, оценивает утилиту; max 8 за 60 с |
| intent_type | ID действия (74 штуки); связывает реализацию с BG-каналом и pygame-командой |
| layer | Слой рендера: action / postural / micro |
| OrganismHardLimits | Жёсткие числовые ограничения; нарушение → OrganismInvariantError |
| position | Целевая зона в клетке; 18 именованных зон |
| SpeechGovernor | Управляет частотой речевых событий и аффективной регуляцией перегрузки |
| TD(0) | δ = r + γV(s') − V(s); изолировано от аффекта |
| ThalamicGate | Финальный softmax-выбор; температура растёт с NE |
| tick | Один шаг organism_step(dt=1с) |
| wellbeing_flag | Маркер патологии в parameters; сигнал для UI-индикатора стресса |
