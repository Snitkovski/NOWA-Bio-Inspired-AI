# Двухуровневая пластичность ядра: спецификация

База: `main` @ `cbce2fb`. Номера строк — по этому коммиту.
Scope: **ядро** NOWA (`src/`) как универсальный движок, независимо от хост-приложения. Демо рассматриваются только в приложении и в критерии приёмки ядра не входят.
Заменяет ранние черновики (строгий вариант «только сон» и смешанный вариант ядро+демо), обсуждавшиеся в issue #13.

## 1. Цель / Принцип

В ядре два уровня пластичности плюс самая медленная система привычек.

- **Стабильный слой** (долговременные параметры): таблица V/Q, веса Go/NoGo/habit BG, следы привычек, счётчики визитов, веса стратегий, медленная аффективная статистика. **Пишется только во сне.**
- **Лабильный слой** (синаптические метки / eligibility traces): малые, ограниченные, затухающие во времени добавки к Q/V и к Go/NoGo каналов BG. **Пишется днём**, затухает по прошедшему времени хоста, теряется, если не консолидирован.
- **Привычки** (аналог дорсолатерального стриатума): самый медленный слой. Одиночные дневные исходы их не меняют; максимум создаётся пустой след (сила 0). Обновляются только во сне.

**Инвариант W (стабильный слой днём только читается).** Между двумя вызовами `Agent.sleep()` каждый стабильный параметр (§4.2 A) не меняется бит-в-бит, что бы ни вызывал хост: `step()` с `reward` и без, `step(decision_only=True)`, `commit_executed_transition()`, `apply_feedback_to_last_experience()`, внешний feedback (`execute_external_action`, `resolve_external_feedback`). Дневные изменения разрешены только в лабильном слое (§4.2 B), в пределах clamp.

**Инвариант S (сон — единственный писатель стабильного слоя).** Запись в стабильный слой — только внутри API консолидации, вызываемого из `Agent.sleep()`. Каждый эпизод консолидируется ровно один раз.

**Поведение днём:** выбор использует эффективные значения = стабильное + лабильное, поэтому недавние исходы влияют на поведение ещё до следующего сна.

**Контракт с хостом.** Ядро не решает, когда спать и с какой скоростью идёт время. Хост передаёт (а) `dt` (прошедшее время на дневной вызов, в секундах хоста) и (б) вызывает `sleep()`. Хост объявляет ожидаемый интервал между снами `expected_wake_interval_s` в `PlasticityConfig`; временные дефолты выводятся из него (§6).

## 2. Нейронаучное обоснование (механизм мозга → компонент ядра)
Только общеизвестные соответствия уровня учебника; числа из литературы не берутся.

| Механизм мозга | Компонент ядра |
|---|---|
| Фазический дофамин кодирует ошибку предсказания награды (Шульц и коллеги) | δ = r + γ·V(s') − V(s) по эффективным значениям; уровень фазического DA (состояние) задаётся δ |
| Трёхфакторное правило: совпадение пре/пост оставляет eligibility trace, нейромодулятор превращает его в изменение веса | Метки лабильного слоя пишутся DA-знаковой δ; метки затухают во времени |
| Пути стриатума D1 (прямой, Go) и D2 (непрямой, NoGo); при положительной RPE DA усиливает D1 и ослабляет D2, при отрицательной — наоборот | Веса Go/NoGo канала: положительный исход → Go↑ NoGo↓, отрицательный → Go↓ NoGo↑ |
| Synaptic tagging and capture (Фрей и Моррис): ранняя LTP временна, если не захвачена в позднюю | Лабильные добавки затухают, если во сне не захвачены в стабильный слой с коэффициентом κ |
| Быстрое (с одного предъявления) эпизодическое кодирование в гиппокампе | `hippocampus.store` записывает каждый эпизод с `episode_id`, наградой, исполненным действием, `overridden` |
| Replay в sharp-wave ripples во сне, смещённый к наградным/значимым/новым эпизодам | Приоритетный replay во сне по |δ|, |r|, новизне, эмоциональной значимости |
| Комплементарные системы обучения (McClelland, McNaughton, O'Reilly): быстрое обучение гиппокампа, медленное корковое/стриатное через replay | Быстрый лабильный слой + эпизодическая память днём; медленный стабильный слой через replay во сне |
| Гипотеза синаптического гомеостаза, SHY (Тонони и Чирелли): сон понижает синапсы, усиленные за день | Понижение весов BG к prior во сне (уже есть: `_apply_bg_decay`, PR #35) |
| Привычки зависят от дорсолатерального стриатума и формируются медленно через повторение | Следы привычек: днём не меняются; ограниченная EMA только во сне |
| Есть гипотеза, что REM-сон снижает аффективную окраску воспоминаний | Опциональный REM-шаг (решение ядра 10); сейчас не реализован (§3.4) |

## 3. Текущее состояние ядра (проверено на `cbce2fb`)

### 3.1 Дневные записи в стабильные параметры — должны уйти в лабильный слой или в сон
`src/agent.py`:
| Место | Что пишет сейчас | Куда |
|---|---|---|
| docstring модуля, строки 11–13: *«While awake, a known reward updates the value of the transition, the outcome-gated habit, and that action's Go/NoGo channel. Sleep consolidates episodes; it is not the only learning step.»* | — | переписать |
| docstring `step()` ~293–299: *«When `reward` is known, this step also applies one TD backup and the outcome updates for the habit and the basal-ganglia channel.»* | — | переписать |
| `step()` ~1173 `value_layer.update(..., mode="online")` при известном исходе; поля эпизода `td_committed_reward`, `td_prior_value`, `td_applied_delta` (~1205–1212) | стабильная Q/V | лабильная метка Q |
| `step()` ~1216 `_record_known_outcome(...)` | привычки, Go/NoGo, `bg_sleep_memories` | привычки → сон; Go/NoGo → лабильная метка канала; журнал → эпизод |
| `step()` ~1045–1052 `intent_memory.note_selection(...)`, fallback `record_trace(...)` | след силы 0; fallback увеличивает силу | `note_selection` оставить; fallback с увеличением силы убрать |
| `commit_executed_transition()`, строка 935, docstring 952: *«Store and learn the action that was actually executed … applies the same TD / habit / channel update as a waking step whose reward is already known»* | то же, что `step(reward=)` | только эпизод + лабильный слой |
| `apply_feedback_to_last_experience()`, строка 3112, docstring: *«A new rating commits one TD backup and the shared outcome update … A changed rating revises that one backup inside the current Q»*; ~3162 `_record_known_outcome`; ~3626 `value_layer.update` | стабильные Q, привычки, Go/NoGo | исход эпизода + идемпотентный лабильный вклад |
| `_record_known_outcome()` 2997 | диспетчер | разделить на лабильного писателя (день) и стабильных (сон) |
| `_apply_outcome_to_channel()` 3015 → `channel.update_weights(go ±0.08·r, nogo ∓0.04·r)` 3030/3036 | стабильные Go/NoGo | днём лабильно, во сне стабильно |
| `_apply_outcome_to_habits()` 3041 → `intent_memory.apply_outcome` 3054/3061 (EMA, rate 0.20·gain, gain ∈ [0.25, 1.5]) | стабильные привычки | только сон |
| `record_action_outcome()` 2975 → `bg_sleep_memories` | журнал для сна | заменяется записью в эпизоде (решение ядра 5) |
| `step()` ~1442 `emotional_expectations.update`, ~1418 `semantic_emotions.update_from_space`, ~1429 `emotional_memory.update_from_layers`, ~1377 `affective_background.update_from_traces`, ~1536 `conflict_arbitration.register_outcome` | медленная аффективная статистика и статистика ожиданий («expectation profiles» в #13) | серая зона → решение ядра 3 |
| `_apply_external_feedback_learning()` 4164 → `external_interaction_layer.apply_learning_hooks(alpha=0.1, learning_rate=0.05)` (`src/external_interaction_layer.py:516`) | веса стратегий, связь стратегия–драйв, `selector.action_metadata` | сон (решение ядра 8) |
| `step()` ~346–348: прошедшее время из `time.time()` (настенные часы) | — | лабильное затухание по `dt` от хоста (§4.1) |
| `sleep()` 3343: *«This is THE ONLY mechanism for learning/adaptation.»* | — | переформулировать: единственный механизм стабильного обучения |

`src/intent_memory.py`: `record_trace` 149 (увеличивает силу через `IntentTrace.strengthen` 78), `strengthen_trace` 251 (legacy), `note_selection` 271 (сила 0, разрешено), `apply_outcome` 296 (→ только сон), `degrade_unused` 234 (уже только во сне).
`src/basal_ganglia.py`: `ActionChannel.update_weights` (стабильный писатель → только сон); `prior_go/prior_nogo/prior_habit` (PR #35, константы); `BasalGangliaGate.process` (читатель, должен читать эффективные веса).
`src/value_layer.py`: путь `update(..., mode="online")` и `alpha_online_default` (512) — режим online удаляется.

### 3.2 Сонная сторона сейчас (`src/sleep.py`)
`SleepManager` 118 (docstring *«Sleep consolidation - THE ONLY learning mechanism.»*). `sleep_cycle()` 254: кандидаты → фильтрованная консолидация, `_select_replay_sample` 1295, `_compute_replay_priority` 1366, `_apply_replay_td_bg` 1404 (δ пересчитывается при replay, #9 / PR #35), семантическая консолидация действий 1809 → `_apply_bg_decay` 2500 (к prior) + `_normalize_bg_weights` 2521 → кластеризация → кора, временные цепочки, `_forget_unstable` 2691 → `intent_memory.degrade_unused(0.8)` → `_apply_neuromodulators_during_sleep` 615. `_consolidate_bg_outcome_cache` 2548 применяет `bg_sleep_memories` один раз; `Agent.sleep()` его очищает (agent.py 3399).

### 3.3 История
До PR #33 бодрствование уже писало V(s) в режиме online и усиливало привычки без учёта исхода. PR #33 добавил дневной Q(s,a), привычки по исходу (`b68ac53`), Go/NoGo канала (`3cad48d`), `step(reward=)` (`c72e808`); PR #36 добавил `commit_executed_transition`. #13 оставался открытым.

### 3.4 REM в коде
`sleep.py` 229–245 и `_classify_sleep_phase` 1143 классифицируют пачки replay как SWS / REM / TRANSITIONAL для настройки семантической консолидации действий (`sac_*_sws`). Шага, снижающего аффективную окраску эпизодов, нет.

## 4. Требуемое поведение

### 4.1 Бодрствование
1. **Кодирование:** каждый исполненный переход сохраняет один эпизод: `episode_id`, контекст, снимок состояния, `decided_action`, `executed_action`, `overridden`, `override_source`, `reward` (None = неизвестен), `terminal`, следующий контекст, снимок нейромодуляторов при кодировании, novelty / conflict / intensity, аффективный gain при кодировании, `outcome_revision`, `labile_contribution`, `encoded_at` (время хоста), `consolidated = False`.
2. **Эффективные значения:** `Q_eff(s,a) = Q_stable(s,a) + L_Q(s,a)` (и `V_eff`, если V используется); `go_eff = clamp01(go_stable + L_go)`, `nogo_eff = clamp01(nogo_stable + L_nogo)`. Вклад привычки в выбор = стабильная сила привычки.
3. **Трёхфакторное лабильное обновление**, когда исход становится известен (`step(reward=r)`, `commit_executed_transition(reward=r)`, feedback):
   - `δ = r + γ·(0 если terminal иначе max_a' Q_eff(s',a')) − Q_eff(s,a)`;
   - `ΔL_Q = clamp(η_L·g_DA·δ, −a_step, +a_step)`; `L_Q(s,a) = clamp(L_Q + ΔL_Q, −A_Q, +A_Q)`; `g_DA` — ограниченный gain фазического DA (состояние), по умолчанию 1;
   - канал: r>0 → `ΔL_go = +η_Lc·r`, `ΔL_nogo = −½η_Lc·r`; r<0 → `ΔL_go = −½η_Lc·|r|`, `ΔL_nogo = +η_Lc·|r|`; каждая L зажимается в `[−A_c, +A_c]`;
   - эпизод хранит свой фактически применённый вклад (после clamp), чтобы его можно было заменить.
4. **Идемпотентный feedback:** та же оценка → no-op (метки, эпизод, журналы, счётчик ревизий не меняются). Изменённая оценка → убрать сохранённый вклад эпизода (с тем же коэффициентом затухания, что у меток), применить новый, сохранить его; никакого накопления. Неизвестный/вытесненный `episode_id` → `updated=False`, без изменений. NaN = неизвестно; ±inf → ±1. Ключи результата не меняются (`updated`, `reward_signal`, `td_error`, `salience`, `importance`); `td_error` считается по эффективным значениям.
5. **Затухание по времени:** `L ← L·exp(−Δt/τ_L)`, в замкнутой форме, лениво для каждой записи от её времени последнего обновления по часам хоста в агенте. Часы хоста продвигаются на `dt`, переданный в `step(..., dt=...)` / `commit_executed_transition(..., dt=...)` (новый необязательный аргумент), или явным `agent.advance_time(dt)`. Если `dt` никогда не передаётся, часы берутся из текущего источника прошедшего времени (настенные часы) и один раз пишется предупреждение. Один вызов с dt=T и N вызовов с dt=T/N дают одинаковый результат. Записи с |L| < 1e-6 удаляются.
6. **Привычки:** дневные исходы их не меняют; `note_selection` может создать след силы 0.
7. **Счётчики визитов:** стабильные заморожены; опционально лабильный счётчик для дневного бонуса исследования (решение ядра 6).
8. **Состояние** (уровни нейромодуляторов, аффект, бодрость, энергия) меняется как сейчас.

### 4.2 Категории
**A. Стабильные параметры (пишутся только во сне; днём заморожены бит-в-бит):** (1) V/Q `value_layer`, среднее/дисперсия ожидаемой награды, счётчики подтверждений, дисперсия по состоянию; (2) стабильные счётчики визитов; (3) силы следов `intent_memory` (следы с силой > 0); (4) `go_weight`, `nogo_weight`, `habit_strength` BG, параметры `bg_learning`; (5) паттерны коры, временные цепочки; (6) внешние `strategy_weights`, связь стратегия–драйв, обучаемые поля `selector.action_metadata`; (7) медленная аффективная статистика и статистика ожиданий (по умолчанию, решение ядра 3); (8) уставки/базовые линии нейромодуляторов.
Константы: priors каналов `prior_go/prior_nogo/prior_habit`; значения `PlasticityConfig`.

**B. Лабильный слой (днём писать можно, с clamp, затухает):** `L_Q(s,a)`, `L_V(s)` (если используется), `L_go[a]`, `L_nogo[a]`, опциональный лабильный счётчик визитов, время последнего обновления записи, вклады эпизодов.

**C. Состояние:** уровни нейромодуляторов, включая фазический DA, положение в аффективном пространстве, valence/arousal, выход регуляции, бодрость, энергия, рабочий контекст, состояние RNG, счётчики, последовательность `episode_id`, часы хоста, эпизоды гиппокампа и записи feedback, показания монитора стабильности.

### 4.3 Сон (порядок за один `Agent.sleep()`)
1. Применить отложенное лабильное затухание до момента засыпания (по часам хоста).
2. Выбрать неконсолидированные эпизоды с известным исходом (+ ревизованные после консолидации — по решению ядра 1).
3. **Приоритетный replay:** `priority = w_δ·|δ_now| + w_r·|r| + w_n·novelty + w_e·emotional_salience`, δ_now — по текущим стабильным значениям; детерминированное разрешение ничьих по `episode_id`. Расширяет `_compute_replay_priority`.
4. **TD replay** стабильного Q (как #9): δ пересчитывается в момент replay по текущим стабильным значениям; eligibility по порядку траектории; гейт по дисперсии состояния (как сейчас).
5. **Capture:** для каждого эпизода, консолидируемого в этом сне, κ × его оставшийся (после затухания) вклад канала переносится в стабильные Go/NoGo; вклад удаляется из L. Для Q по умолчанию лабильный Q не захватывается (Q учится через replay, шаг 4) и очищается для консолидированных эпизодов, чтобы не считать дважды (решение ядра 13).
6. **Консолидация привычек** (ограниченная EMA из #8): на эпизод `strength += rate·(target − strength)`, target 1 при r>0, 0 при r<0, без изменений при r=0; `rate = 0.20·clamp(affect_gain_при_кодировании, 0.25, 1.5)`.
7. **Стабильное обучение Go/NoGo** (D1/D2-подобно) по эпизоду, скорость `η_c_sleep` (§6), масштабируется снимком нейромодуляторов при кодировании (с ограничением). При включённом capture `η_c_sleep_eff = η_c_sleep − κ·η_Lc`, чтобы суммарный шаг на исход оставался `η_c_sleep`.
8. Внешние стратегии / медленная статистика по записанному feedback (решения ядра 3, 8).
9. Стабильные счётчики визитов += консолидированные эпизоды.
10. **Понижение по SHY:** существующие `_apply_bg_decay` + `_normalize_bg_weights`, формулы не меняются.
11. Существующие шаги: кластеризация → кора, временные цепочки, `_forget_unstable`, `degrade_unused`, сонная динамика нейромодуляторов.
12. Опциональный REM-шаг (решение ядра 10; по умолчанию выключен).
13. Пометить эпизоды `consolidated = True`, `consolidated_reward`, `consolidated_revision`; очистить их лабильные вклады. Лабильные записи неконсолидированных эпизодов продолжают затухать (решение ядра 14).
При нескольких циклах за сон шаги 5–7 выполняются один раз на эпизод за сон; replay (шаг 4) может возвращаться к переходам.
Нет сна → стабильный слой не меняется; лабильный затухает с τ_L; неконсолидированные исходы остаются в гиппокампе до вытеснения (статистика `lost_unconsolidated`).

### 4.4 Ровно один раз
Каждый эпизод вносит вклад в capture, привычки и Go/NoGo один раз. Ревизия до сна: только финальное значение. Ревизия после консолидации: решение ядра 1.

## 5. Структурное принуждение
1. `src/labile_layer.py` — `LabileLayer` (`effective_q`, `effective_channel`, `apply_outcome`, `replace_contribution`, `decay_to`, `pop_contribution`, `to_dict/from_dict`). Стабильные объекты лабильных значений не хранят.
2. `src/learning_guard.py` — `learning_allowed()` (в него входит `Agent.sleep()`), `initializing()` (создание, загрузка, `register_action_channel`, явный посев хостом), `assert_learning_allowed()` в каждом стабильном писателе: `ValueLayer.update`, методы `IntentMemory`, меняющие силу, `ActionChannel.update_weights`, `apply_learning_hooks`, обновления медленной статистики (по решению ядра 3). Строгий режим (`NOWA_STRICT_LEARNING=1`, включён в `conftest.py` ядра) бросает `WakingLearningError`; продакшен — по решению ядра 2.
3. `stable_fingerprint(agent)` (sha256 канонической сериализации категории A) и `labile_snapshot(agent)`.
4. Удалить `mode="online"` из `ValueLayer`; разделить `_record_known_outcome`.
5. `PlasticityConfig` (один блок, §6); сохраняется в save/load. Продуктового флага нет.

Документы ядра к исправлению:
- Docstrings: `src/agent.py` 11–13, `step()` ~293–299, `commit_executed_transition()` 952–958, `apply_feedback_to_last_experience()` 3119–3124, `sleep()` 3347; `src/sleep.py` 120.
- `Docs/qa/PR-33-reward-learning-qa*.ru.md`, `Docs/qa/PR-35-sleep-learning-qa.ru.md`: пометка «заменено двухуровневой моделью #13», где относится.
- Одна уточняющая фраза (стабильный vs лабильный) в: `Docs/ARCHITECTURE.en/ru.md` (11, 204/206, 268/270, 312/314), `Docs/ARCHITECTURE_UPDATED.en.md` 671, 861 / `.ru.md` 925, `Docs/00_INDEX(.NEW).en.md` 104/100, `Docs/DELIVERY_SUMMARY.*`, `Docs/GUI_COMPLETE.*`, `Docs/GUI_QUICK_REFERENCE.en.md` 12, `Docs/arxiv_NOWA_en.md` 24 и `Docs/arxiv_NOWA_ru.md`. `Docs/API.*`: описать `dt`, `advance_time`, `PlasticityConfig`, контракт с хостом.
- README / quick start: утверждений о дневном обучении нет; контракт с хостом — только в документации API.

## 6. Параметры ядра (`PlasticityConfig`)
| Параметр | По умолчанию | Обоснование (свойства ядра / нейронаука) | Зависит от хоста |
|---|---|---|---|
| `expected_wake_interval_s` (T_w) | **задаёт хост**; fallback 3600 с с предупреждением | Ядро не может знать, как часто хост вызывает сон | да, задаёт масштаб времени |
| `tau_labile_s` (τ_L) | **= T_w** (`tau_labile_ratio = 1.0`) | Метки, подобные ранней LTP, должны частично дожить до следующего сна: исход в начале периода бодрствования сохраняет e⁻¹ ≈ 37 % к засыпанию, исход в конце — почти всё; недавний опыт преобладает, старое неконсолидированное затухает, как в tagging-and-capture. Ratio < 0.3 теряет большую часть дня; ratio > 3 делает лабильный слой почти постоянным между снами | да, через T_w и единицы `dt` |
| `eta_labile_q` (η_L) | 0.1 × стабильный α replay (`alpha_default`) | Лабильный слой быстрый, но не должен доминировать над стабильными значениями; шаг в 10 раз меньше делает дневную адаптацию мягкой | нет |
| `labile_step_clamp_q` (a_step) | 0.05 (шкала награды ±1) | Ограничивает эффект одного исхода | масштаб награды |
| `labile_amp_clamp_q` (A_Q) | 0.2 | Максимальный суммарный лабильный сдвиг; меньше типичного разделения выученных значений на шкале ±1 | масштаб награды |
| `eta_labile_channel` (η_Lc) | 0.02 | ¼ стабильной скорости канала | нет |
| `labile_amp_clamp_channel` (A_c) | 0.1 | Веса лежат в [0,1]; днём сдвиг ≤10 % | нет |
| `capture_kappa` (κ) | 0.5 | Частичный захват: не все метки превращаются в стабильные, остальное теряется | нет |
| `eta_channel_sleep` | 0.08 | Равна нынешнему шагу Go на исход (PR #33), сохраняет существующие пороги | нет |
| `replay_priority_weights` (w_δ, w_r, w_n, w_e) | 1.0, 0.5, 0.25, 0.25 | Приоритетный replay в основном по неожиданности (|RPE|), затем величина награды, новизна, эмоция | нет |
| `labile_epsilon` | 1e-6 | очистка хранилища | нет |
Обязанности хоста: передавать `dt` в согласованных единицах; задать `expected_wake_interval_s`; вызывать `sleep()`. Если хост никогда не вызывает сон, стабильный слой никогда не меняется — так задумано.

## 7. Тесты ядра
Правило: существующие ассерты не ослабляются; переписываются в эквивалентную форму «лабильно днём» или «после сна» с теми же порогами/seeds. Все тесты ядра создают `Agent` напрямую; импорта из `Demo/` нет.

Переписать (ядро): `tests/test_reward_bandit.py`, `tests/test_td_transition.py`, `tests/test_qa_issue32_reward_learning.py`, `tests/test_episode_feedback_addressing.py`, `tests/test_k02_decide_act_learn.py` (decide/act/learn ядра через `commit_executed_transition`), `tests/test_k03_habit_signature.py`, `tests/test_intent_memory_integration.py`, `tests/test_intent_memory.py`, `tests/test_basal_ganglia.py`, `tests/test_basal_ganglia_integration_spec.py`, `tests/test_selector.py`, `tests/test_affect_integration.py`, `tests/test_affective_persistence.py`, `tests/test_agent.py`.
Аудит (переписывать, только если проверяют дневное изменение стабильного слоя): `test_value_layer_integration.py`, `test_value_layer.py`, `test_dopaminergic_td_layer.py`, `test_deliberative_planning_spec_011.py`, `test_neuromodulator_integration.py`, `test_external_interaction_layer.py`, `test_hie_002.py`, `test_hie_003.py`, `test_imagination_engine_spec_001.py`, `test_affective_space_integration.py`, `test_acc_conflict_modulation.py`, `test_conflict_arbitration_integration.py`, `test_phase_5_edpc.py`, `test_agent_factory.py`, `test_neuromodulators*.py`, `test_semantic_action_consolidation.py`, `test_phase_6_*`, `test_sleep_replay_td_bg.py`, `test_issue9/10/12_*.py`, `test_qa_pr35_sleep_learning.py`.
Тесты в `tests/`, импортирующие код демо (`test_k01_*`, `test_qa_pr36_colony_core.py`), переходят в доработку демо (Приложение).

Новый `tests/test_issue13_two_tier.py` (контекстный бандит на `Agent`, 2 контекста × 3 действия, ±1, фиксированный seed, `expected_wake_interval_s = 1000`, dt = 1):
1. Guard стабильного слоя: 200 дневных вызовов (step с наградами, decision_only + commit с `overridden`, feedback с ревизиями, внешний feedback) → `stable_fingerprint` идентичен; строгий guard бросает исключение на любом стабильном писателе вне сна.
2. Лабильный слой меняет поведение: P(вознаграждённого действия) после 100 вознаграждённых шагов без сна > исходной; |L| всё время ≤ clamp.
3. Привычки днём не меняются (могут появиться только следы силы 0).
4. Затухание без сна: через 5·τ_L времени хоста |L| < 1 % от начального; policy совпадает с policy только по стабильному слою.
5. Независимость от dt: dt=T один раз против N×T/N → одинаковые лабильные значения (1e-12) и отпечатки.
6. Направление консолидации: после сна Q_stable↑, habit↑, go_stable↑, nogo_stable↓ для вознаграждённой (c,a); наоборот для наказанной; консолидированные вклады = 0.
7. Ровно один раз: второй сон без новых эпизодов = контрольный агент, спящий без эпизодов (только понижение SHY).
8. Идемпотентность: r×3 ≡ r×1 (лабильно и стабильно после сна); r1→r2 ≡ r2.
9. Не консолидировано — потеряно: вытесненный эпизод → стабильного эффекта нет.
10. Детерминизм при PYTHONHASHSEED 0/1/7.
11. Save/load: лабильный слой, часы хоста, неконсолидированные эпизоды, `PlasticityConfig` восстанавливаются; затухание продолжается.
12. Порядок приоритетного replay детерминирован и следует заданным весам.
13. τ_L следует конфигурации: удвоение `expected_wake_interval_s` удваивает τ_L (при дефолтном ratio).

## 8. Вне scope
Как/когда хост вызывает сон; масштаб времени хоста; производительность сна и размеры выборки; формулы PR #33/#35 для сигнала NoGo, затухания/нормализации SHY, неподвижных точек нейромодуляторов; аффективная обработка в REM, если решение ядра 10 ≠ да; любой код и тесты демо (Приложение, PR D).

## 9. Критерии приёмки ядра
1. Стабильный отпечаток бит-в-бит неизменен при любой последовательности дневных вызовов; строгий guard включён во всех тестах ядра; набор тестов ядра проходит.
2. Всё дневное обучение идёт в `LabileLayer`, в пределах clamp; дневных изменений силы привычек нет.
3. Выбор использует стабильное + лабильное для Q/V и Go/NoGo.
4. Лабильное затухание экспоненциально по времени хоста, не зависит от dt; τ_L выводится из `PlasticityConfig`.
5. Feedback идемпотентен; изменённая оценка заменяет вклад эпизода.
6. Сон выполняет §4.3 по порядку; каждый эпизод консолидируется один раз.
7. `mode="online"` удалён; стабильные писатели — только внутри `learning_allowed()` / `initializing()`.
8. Новые тесты 1–13 зелёные; переписанные тесты сохраняют пороги; ни один тест ядра не импортирует `Demo/`.
9. Docstrings ядра и `Docs/` обновлены; документация API описывает контракт с хостом.
10. Save/load покрывает лабильный слой, часы хоста, метки консолидации, конфигурацию.

## 10. Решения по ядру (открытые вопросы, с дефолтами)
1. Оценка изменена после консолидации → по умолчанию: коррекция в следующем сне (свежее наблюдение; replay берёт новую награду). Альтернатива: игнорировать.
2. Guard в продакшене → по умолчанию: исключение в тестах/отладке, лог и пропуск в продакшене.
3. Медленная аффективная статистика / статистика ожиданий → по умолчанию: стабильная, только сон.
4. Посев привычек/каналов хостом → по умолчанию: разрешён внутри `initializing()`.
5. `bg_sleep_memories` → по умолчанию: убрать, брать из эпизодов.
6. Счётчики визитов → по умолчанию: стабильные заморожены + лабильный счётчик для дневного исследования.
7. Стабильная скорость Go/NoGo во сне → по умолчанию: 0.08 (не 0.05 из `bg_learning`).
8. Внешние `apply_learning_hooks` → по умолчанию: перенести в сон.
9. Скорость/clamp лабильного слоя → по умолчанию: η_L = 0.1·α, a_step 0.05, A_Q 0.2, η_Lc 0.02, A_c 0.1.
10. REM-шаг снижения аффекта → по умолчанию: выключен.
11. τ_L → по умолчанию: `tau_labile_ratio = 1.0 × expected_wake_interval_s`; интервал обязан задать хост (fallback 3600 с + предупреждение).
12. κ → по умолчанию: 0.5.
13. Capture против replay для Q → по умолчанию: Q только через replay, лабильный Q очищается; capture для Go/NoGo с компенсированной скоростью во сне.
14. Лабильные записи неконсолидированных эпизодов после сна → по умолчанию: продолжают затухать.
15. Веса приоритета replay → по умолчанию: 1.0 / 0.5 / 0.25 / 0.25.
16. `dt` не передан → по умолчанию: настенные часы с однократным предупреждением (альтернатива: исключение).

## 11. Объём и разбиение на PR
Ядро ≈ L (~2 недели, ~2–3 тыс. строк с тестами).
- **PR A — лабильный слой + guard:** `LabileLayer`, `PlasticityConfig`, часы хоста и `dt`, эффективные значения, guard + отпечатки, дневные писатели → лабильный слой, привычки днём выключены, переписанные тесты ядра, новые тесты 1–5, 8, 10, 11, 13.
- **PR B — консолидация во сне:** приоритетный replay, capture, EMA привычек, Go/NoGo по эпизодам, метки, ровно-один-раз, ревизии после консолидации, медленная статистика/внешние хуки в сон; тесты 6, 7, 9, 12.
- **PR C — docstrings/Docs ядра:** список из §5, контракт с хостом в API, пометки QA.
- **PR D — адаптация демо** (после A+B): см. Приложение.
Порядок: A → B → C (C можно параллельно с B); D после B.

## Приложение: влияние на демо колонии (вне критериев приёмки ядра)
Из этого приложения никаких требований к ядру не следует.
- `Demo/Colony chinchillas/src/colony_agent.py`: `sim_step(dt)` (419) вызывает `step(reward=None, decision_only=True)` (~452) и `commit_executed_transition(reward=...)` (~470) — оба API остаются; демо должно передавать `dt=dt` и задавать `expected_wake_interval_s` при создании агента. `_apply_sleep_recovery` (867) вызывает `self.sleep(cycles, sleep_duration_seconds=0.0)` — без изменений. `_seed_habit_bootstrap` (901) пишет следы напрямую — должен выполняться внутри `initializing()`.
- Константы демо и `PHYSIOLOGY_AS_POLICY` работой над ядром не меняются.
- Тесты для адаптации в PR D: `tests/test_k01_colony_ablation.py` (абляция #19), `tests/test_k01_need_consumption.py`, `tests/test_qa_pr36_colony_core.py`, `Demo/Colony chinchillas/tests/test_nowa_agent.py`, `test_knowledge.py`, `test_death_registry_inspector_lineage.py`. Если преимущество ядра в абляции держалось на дневном стабильном обучении — добавить в тест явные `sleep()` между блоками; ассерты сохранить.
- Документы демо, где говорится об обучении только во сне (`Demo/Tamagochi Chinchilla/Docs/*`, `Demo/Virtual company/Docs/*`, `Demo/Warriner Validation/Docs/*`): по желанию, пометка.

**Вопросы по доработке демо (дефолты):**
1. `expected_wake_interval_s` демо → по умолчанию: измеренная средняя длительность бодрствования между снами в демо.
2. Абляция #19, если упадёт → по умолчанию: явные `sleep()` в тесте, константы демо не трогать.
3. `_seed_habit_bootstrap` → по умолчанию: обернуть в `initializing()`, без изменения поведения.
4. Документы демо → по умолчанию: однострочная пометка, отдельно от PR документации ядра.


---
**Owner decision (2026-10-19):** all default answers to the open questions (Core decisions 1–16, Demo follow-up 1–4) are accepted. Implementation order: PR A → B → C (core), then D (demo).

**Решение владельца (2026-10-19):** все варианты по умолчанию в открытых вопросах (решения по ядру 1–16, демо 1–4) приняты. Порядок: PR A → B → C (ядро), затем D (демо).

---
**Owner decisions after PR A (2026-10-19), scope of PR B:**
1. Slow affective statistics are stable parameters: they change only during sleep (decision 3), included in the stable fingerprint.
2. Phasic dopamine gain `g_DA` stays 1 (no dependence on dopamine level for now; possible separate feature later).
3. Labile visit counters do not decay during waking; during sleep they are transferred into stable visit counts and reset (decision 6).
4. Guard bypasses are closed: direct `go_weight` assignment, `register_action_channel`, `ValueLayer._set_value` outside sleep, `consolidate_habits` without guard; `apply_sleep_learning` must not open the guard when called during waking.
5. Demo adaptation (former PR D) is split into a separate stage and PR per demo: Colony chinchillas, Tamagochi Chinchilla, Virtual company, Warriner Validation — each adapted and fully checked independently, without tuning the core.

**Решения владельца после PR A (2026-10-19), объём PR B:**
1. Медленная аффективная статистика — стабильный параметр: меняется только во сне (решение 3), входит в отпечаток стабильного слоя.
2. Фазический коэффициент дофамина `g_DA` остаётся 1 (без зависимости от уровня дофамина; возможна отдельная фича позже).
3. Лабильные счётчики визитов днём не затухают; во сне переносятся в стабильные визиты и обнуляются (решение 6).
4. Обходы guard закрываются: прямая запись `go_weight`, `register_action_channel`, `ValueLayer._set_value` вне сна, `consolidate_habits` без guard; `apply_sleep_learning` не должен открывать guard при вызове днём.
5. Адаптация демо (бывший PR D) разбита на отдельные этапы и PR по каждому демо: Colony chinchillas, Tamagochi Chinchilla, Virtual company, Warriner Validation — каждое адаптируется и полностью проверяется отдельно, без подстройки ядра.

---
**Owner decisions after PR B (2026-10-19):**
1. The sleep Go/NoGo step is not scaled by the encoding neuromodulator snapshot. `g_DA` stays 1.
2. A rating changed after consolidation is a new observation. The previous stable write is not rolled back (reconsolidation-like: the new reward is applied again).
3. `register_action_channel` enters `initializing()` itself. Host seeding stays a scoped write.
4. Slow affective statistics are inside `stable_fingerprint` and change only in sleep. Fast per-step affect (space position, valence/arousal, regulation output, the arbitration mode of the current step) stays outside the fingerprint.
5. The four-term replay priority orders only the single consolidation pass. It is not added inside the bounded EDPC replay score.
6. Replay caps from PR #35 stay. `Q > 0.8` after `sleep(cycles=3)` is not a requirement.
7. Replay learns only stable Q. Go/NoGo and habit-channel weights change only via tag capture plus the compensated sleep step (an undecayed +1 totals +0.08 on Go).
8. Only the sleep path opens the learning guard. `SleepManager._apply_replay_td_bg` does not open it; a direct daytime call raises in strict mode and skips the write in production.

**Решения владельца после PR B (2026-10-19):**
1. Сонный шаг Go/NoGo не масштабируется снимком нейромодуляторов при кодировании. `g_DA` остаётся 1.
2. Оценка, изменённая после консолидации, — новое наблюдение. Прежняя запись в стабильный слой не откатывается (как реконсолидация: новая награда применяется ещё раз).
3. `register_action_channel` сам входит в `initializing()`. Посев хоста остаётся записью внутри явной области.
4. Медленная аффективная статистика входит в `stable_fingerprint` и меняется только во сне. Быстрый аффект шага (положение в пространстве, valence/arousal, выход регуляции, режим арбитража текущего шага) в отпечаток не входит.
5. Четырёхчленный приоритет replay задаёт порядок только однократного прохода консолидации. В ограниченный счёт EDPC он не прибавляется.
6. Потолки replay из PR #35 остаются. `Q > 0.8` после `sleep(cycles=3)` не требуется.
7. Replay учит только стабильный Q. Веса Go/NoGo и habit канала меняются только захватом метки плюс компенсированным сонным шагом (незатухший +1 даёт +0.08 на Go).
8. Guard обучения открывает только сонный путь. `SleepManager._apply_replay_td_bg` его не открывает: прямой дневной вызов в строгом режиме бросает исключение, в проде запись пропускается.

