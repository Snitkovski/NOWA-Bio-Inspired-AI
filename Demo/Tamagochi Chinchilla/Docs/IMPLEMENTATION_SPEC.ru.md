# Агент «шиншилла» — спецификация реализации

English version: [IMPLEMENTATION_SPEC.en.md](IMPLEMENTATION_SPEC.en.md)

## Аннотация

Научное описание установки: [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md).

Документ задаёт нормативный протокол доработки демонстрационного организма «шиншилла», предназначенный для агентной реализации. Десять задач упорядочены по приоритету и объявлены атомарными и взаимно независимыми. Начальные задачи относятся к локальной подсистеме памяти и к выбору поведенческих цепочек: согласование ключей функции оценки награды со словарём аффективного состояния, вызов сохранения памяти при завершении сеанса и с заданным периодом внутри шага симуляции, а также передача предложений локального планировщика в процедуру выбора цепочки.

Дальнейшие задачи касаются временной устойчивости и выразительности цикла pygame. Протокол требует ограничить приращение времени в проигрывателе анимации, включить в цепочки восемнадцать действий библиотеки, которые текст спецификации квалифицирует как не входящие ни в одну цепочку, заполнять постуральный слой по осям аффекта и микрослой в интервалах между действиями, а также допустить вероятностный пропуск шагов цепочки. Отдельными пунктами задаются циркадная окраска фона и индикатор благополучия.

Спецификация фиксирует причину каждого расхождения и ожидаемый вид правки в локальных модулях памяти, планировщика, конфигурации цепочек и графического движка. Она представляет собой протокол подлежащих выполнению изменений.

---

Спецификация для агентной реализации. Задачи упорядочены по приоритету.
Каждая задача атомарна и независима от остальных.

---

## Задача 1 — Исправить `_calculate_reward()` в `memory_system.py`

**Файл:** `memory_system.py`  
**Метод:** `_calculate_reward(affect_before, affect_after, chain_name)`  
**Статус:** Метод возвращает `0.0` при любых входных данных → обучение не работает.

### Причина

Метод обращается к ключам `'hunger'`, `'happiness'`, `'fear'`, `'calmness'`, `'sadness'`.
В `affect.state` этих ключей нет. Используется другой словарь:

| Ключ в `_calculate_reward()` | Правильный ключ в `affect.state` |
|---|---|
| `'hunger'` | `'hunger'` ✓ (есть, добавлен scheduling-ом) |
| `'tiredness'` | `'tiredness'` ✓ |
| `'boredom'` | `'boredom'` ✓ |
| `'happiness'` | `'valence'` |
| `'fear'` | `'stress'` |
| `'calmness'` | `1.0 - affect.state['stress']` |
| `'sadness'` | `max(0.0, -affect.state['valence'])` |

### Что нужно сделать

Переписать тело `_calculate_reward()`. Логика оценки остаётся прежней, меняются только ключи:

```python
def _calculate_reward(self, affect_before, affect_after, chain_name):
    reward = 0.0

    # Вычислить производные значения из правильных ключей
    hunger_before   = affect_before.get('hunger', 0.0)
    hunger_after    = affect_after.get('hunger', 0.0)
    tiredness_before = affect_before.get('tiredness', 0.0)
    tiredness_after  = affect_after.get('tiredness', 0.0)
    boredom_before  = affect_before.get('boredom', 0.0)
    boredom_after   = affect_after.get('boredom', 0.0)

    valence_before  = affect_before.get('valence', 0.0)
    valence_after   = affect_after.get('valence', 0.0)
    stress_before   = affect_before.get('stress', 0.0)
    stress_after    = affect_after.get('stress', 0.0)

    # Chain-specific rewards
    if chain_name in ('eating', 'eating_and_grooming'):
        if hunger_after < hunger_before:
            reward += 0.3

    elif chain_name in ('bedtime_routine', 'sleeping'):
        if tiredness_after < tiredness_before:
            reward += 0.3

    elif chain_name in ('play', 'activity_burst', 'exploration', 'hyperactivity'):
        if boredom_after < boredom_before:
            reward += 0.25
        if valence_after > valence_before:
            reward += 0.15

    elif chain_name in ('full_grooming', 'dust_bathing'):
        if stress_after < stress_before:
            reward += 0.2

    # Общее: снижение стресса всегда хорошо
    if stress_after < stress_before:
        reward += (stress_before - stress_after) * 0.1

    # Общее: рост позитивного настроения
    if valence_after > 0.3:
        reward += valence_after * 0.05

    # Патологические цепочки — штраф
    if chain_name == 'chronic_stress':
        reward -= 0.4

    return max(-1.0, min(1.0, reward))
```

---

## Задача 2 — Вызвать `save_memory()` при выходе

**Файл:** `main.py`  
**Метод:** `cleanup()`

### Причина

`MemorySystem.save_memory()` полностью реализован и пишет в `saves/memory.json`.
Нигде не вызывается → весь прогресс обучения теряется при закрытии окна.

### Что нужно сделать

**Шаг 1.** Добавить вызов в `cleanup()`:

```python
def cleanup(self) -> None:
    self.memory.save_memory()          # ← добавить первой строкой
    self.audio.cleanup()
    if self.pygame_engine:
        self.pygame_engine.cleanup()
    self.logger.info("Cleanup complete")
```

**Шаг 2.** Добавить периодическое сохранение в `sim_step()`.
Добавить атрибут в `__init__`: `self._last_memory_save: float = 0.0`

```python
# В конце sim_step(), после блока memory consolidation:
if self.total_sim_time - self._last_memory_save >= 60.0:
    self.memory.save_memory()
    self._last_memory_save = self.total_sim_time
```

---

## Задача 3 — Подключить `_build_candidate_chains()` к выбору цепочки

**Файл:** `main.py`  
**Метод:** `_try_start_chain()`

### Причина

`SchedulingSystem.get_drive_suggestions()` возвращает веса для цепочек на основе hunger/tiredness/boredom.
`_build_candidate_chains()` принимает эти веса и правильно сортирует кандидатов.
Но `_try_start_chain()` вызывает `chain_executor.select_chain()`, который drive_suggestions не видит.
Результат: шиншилла с `hunger=0.95` выбирает `exploration` так же часто, как `eating_and_grooming`.

### Что нужно сделать

Заменить вызов `select_chain()` на `_build_candidate_chains()` в `_try_start_chain()`:

```python
def _try_start_chain(self) -> None:
    drive_suggest = self.scheduler.get_drive_suggestions()

    # Было:
    # affect_ctx = self.affect.get_chain_context()
    # chain = self.chain_executor.select_chain(affect_ctx)

    # Стало:
    candidates = self._build_candidate_chains(drive_suggest)
    chain = candidates[0] if candidates else None

    if chain:
        cmd = self.chain_executor.start_chain(chain)
        if cmd:
            self._send_command(cmd)
            self.chain_cooldown_s = random.uniform(
                self.CHAIN_COOLDOWN_MIN_S, self.CHAIN_COOLDOWN_MAX_S
            )
            self.last_chain_name    = chain
            self.chain_start_affect = self.affect.get_state()
            return

    self._dispatch_idle_action()
    self.chain_cooldown_s = random.uniform(
        self.CHAIN_COOLDOWN_MIN_S, self.CHAIN_COOLDOWN_MAX_S
    )
```

> `_build_candidate_chains()` уже реализован в `main.py` (строка 539) — изменений в нём не требуется.

---

## Задача 4 — Добавить кэп `dt` в `AnimationPlayer`

**Файл:** `pygame_engine.py`  
**Класс:** `AnimationPlayer`, метод `update()`

### Причина

При сворачивании/разворачивании окна `wall_dt` скачет до 2–5 с.
`SpriteMovement` защищён кэпом в главном цикле (`wall_dt = min(wall_dt, 0.2)`).
`AnimationPlayer` накапливает `time_in_frame += dt` без ограничений → анимация прыгает на несколько секунд вперёд.

### Что нужно сделать

Одна строка в начале `AnimationPlayer.update()`:

```python
def update(self, dt: float) -> None:
    dt = min(dt, 0.1)   # не прыгать больше одного кадра за раз
    if self.finished:
        return
    self.time_in_frame += dt
    # ... остальное без изменений
```

---

## Задача 5 — Включить 18 «мёртвых» действий в цепочки

**Файл:** `config.py`  
**Константа:** `BEHAVIORAL_CHAINS`

### Причина

18 действий определены в `ACTION_LIBRARY`, но не входят ни в одну цепочку:

```
eat_treat, gnaw_mineral, toilet_main, explore_corner, play_toy, gnaw_wood,
problem_solve, overgroom_other, vocalize_squeak, vocalize_alarm,
vocalize_teeth, avoid_hand, follow_finger, thump_hind, fur_slip,
wall_jump, tail_raise, nose_twitch
```

### Что нужно сделать

Внести изменения в `BEHAVIORAL_CHAINS` согласно таблице:

| Действие | Добавить в цепочку | Позиция |
|---|---|---|
| `eat_treat` | `eating_and_grooming` | после `eat_hay` |
| `gnaw_mineral` | `territorial_patrol` | после `toilet_mark` |
| `toilet_main` | `bedtime_routine` | перед `rearrange_bedding` |
| `explore_corner` | `exploration` | заменить второй `sniff_air` |
| `play_toy` | `activity_burst` | между `toss_toy` и `chase_toy` |
| `gnaw_wood` | `nesting` | после первого `rearrange_bedding` |
| `problem_solve` | `exploration` | перед `rearrange_bedding` |
| `thump_hind` | `mild_fear` | между `freeze` и `ear_flat` |
| `fur_slip` | `extreme_fear` | после `flee_corner` |
| `wall_jump` | `extreme_fear` | перед `freeze` |
| `vocalize_squeak` | `mild_fear` | в начало |
| `vocalize_alarm` | `extreme_fear` | в начало (уже есть `alarm_call`, вставить следом) |
| `vocalize_teeth` | `chronic_stress` | между `bar_chewing` и `stereotypy_pacing` |
| `avoid_hand` | `social_contact` | альтернатива `take_treat` при низком `trust` |
| `follow_finger` | `social_contact` | после `watch_owner` |
| `tail_raise` | `territorial_patrol` | после `stand_upright` |
| `nose_twitch` | `exploration` | в начало |
| `overgroom_other` | `chronic_stress` | после `overgroom_fur` |

Конечный вид изменённых цепочек:

```python
BEHAVIORAL_CHAINS = {
    "eating_and_grooming": [
        "eat_pellets", "eat_hay", "eat_treat",       # ← eat_treat добавлен
        "drink_water", "groom_face", "groom_body", "rest_loaf"
    ],
    "exploration": [
        "nose_twitch",                                # ← добавлен
        "sniff_air", "stand_upright", "explore_corner",  # ← explore_corner вместо approach_door
        "inspect_new_obj", "problem_solve",           # ← problem_solve добавлен
        "sniff_hand", "gnaw_toy", "gnaw_wood",        # ← gnaw_wood добавлен
        "carry_object", "rearrange_bedding"
    ],
    "activity_burst": [
        "stand_upright", "sniff_air", "run_wheel",
        "jump_hop_play", "play_toy", "toss_toy",      # ← play_toy добавлен
        "chase_toy", "jump_shelf_up", "observe_room", "drink_water"
    ],
    "mild_fear": [
        "vocalize_squeak",                            # ← добавлен
        "ear_forward", "whisker_twitch",
        "thump_hind",                                 # ← добавлен
        "freeze", "ear_flat", "press_flat",
        "sniff_air", "stand_upright", "patrol_floor"
    ],
    "extreme_fear": [
        "vocalize_alarm", "alarm_call",               # ← vocalize_alarm добавлен
        "wall_jump",                                  # ← добавлен
        "flee_corner", "fur_slip",                    # ← fur_slip добавлен
        "freeze", "hide_house", "press_flat", "eye_half_close", "doze_shelf"
    ],
    "chronic_stress": [
        "observe_room", "bar_chewing",
        "vocalize_teeth",                             # ← добавлен
        "stereotypy_pacing", "overgroom_fur",
        "overgroom_other",                            # ← добавлен
        "hide_house", "vocalize_bark"
    ],
    "territorial_patrol": [
        "stretch_body", "patrol_floor", "sniff_corners",
        "toilet_mark", "gnaw_mineral",               # ← gnaw_mineral добавлен
        "stand_upright", "tail_raise",               # ← tail_raise добавлен
        "climb_bars", "observe_room"
    ],
    "nesting": [
        "rearrange_bedding", "dig_bedding",
        "gnaw_wood",                                  # ← добавлен
        "carry_object", "cache_food", "rearrange_bedding"
    ],
    "bedtime_routine": [
        "eat_hay", "drink_water", "groom_body",
        "toilet_main",                                # ← добавлен
        "rearrange_bedding", "cache_food", "hide_house", "sleep_house"
    ],
    "social_contact": [
        "watch_owner", "follow_finger",              # ← follow_finger добавлен
        "approach_door", "vocalize_chirp",
        "sniff_hand", "take_treat", "allow_pet",
        "avoid_hand",                                 # ← добавлен (конец — если не понравилось)
        "solicit_pet"
    ],
    # Остальные цепочки без изменений:
    # morning_awakening, full_grooming, dust_bathing, hyperactivity
}
```

---

## Задача 6 — Постуральный слой: уши и поза по affect

**Файлы:** `main.py`  
**Слой:** `postural` в `pygame_engine.py` (уже поддерживается, не используется)

### Причина

Движок рендерит три слоя: `action`, `postural`, `micro`. Слои `postural` и `micro` никогда не заполняются — многослойная система простаивает. Шиншилла не выражает эмоциональное состояние позой.

Доступные спрайты постурального слоя (из `manifest.json`):

- `ears_forward_hold` — интерес, настороженность
- `ears_flat_hold` — страх, стресс
- `tail_up_hold` — возбуждение
- `press_flat_hold` — подавленность
- `eyes_droop_hold` — усталость

### Что нужно сделать

Добавить метод `_update_postural_layer()` в `ChinchillaAgent` и вызывать его в `sim_step()` один раз в секунду (не каждый тик).

Добавить атрибут в `__init__`: `self._postural_timer: float = 0.0`

```python
def _update_postural_layer(self) -> None:
    """Отправляет постуральную анимацию на основе текущего affect.state."""
    s = self.affect.state
    stress    = s.get('stress', 0.0)
    curiosity = s.get('curiosity', 0.5)
    arousal   = s.get('arousal', 0.5)
    tiredness = s.get('tiredness', 0.0)

    if stress > 0.6:
        anim = 'ears_flat_hold'
    elif tiredness > 0.7:
        anim = 'eyes_droop_hold'
    elif curiosity > 0.65:
        anim = 'ears_forward_hold'
    elif arousal > 0.75:
        anim = 'tail_up_hold'
    else:
        return  # нейтральная поза — не перекрывать action

    if self.pygame_engine:
        self.pygame_engine.queue_action({
            'action_id': f'postural_{anim}',
            'anim':      anim,
            'sfx':       None,
            'position':  'current',
            'duration':  [8, 20],
            'subtitle':  '',
            'loop':      True,
            'layer':     'postural',
        })
```

В `sim_step()`, после обновления affect:

```python
self._postural_timer -= dt
if self._postural_timer <= 0:
    self._update_postural_layer()
    self._postural_timer = 1.0   # обновлять раз в секунду
```

---

## Задача 7 — Микро-анимации в паузах (idle не замирает)

**Файл:** `main.py`

### Причина

Между цепочками шиншилла стоит полностью неподвижно (`loaf_idle`, 2 кадра).
Реальные шиншиллы непрерывно шевелят усами, подёргивают носом, поворачивают уши.

Доступные спрайты микро-слоя:

- `whisker_loop` (6 кадров, 8 fps)
- `nose_twitch_loop` (4 кадра, 8 fps)
- `head_track_loop` (6 кадров, 8 fps)

### Что нужно сделать

Добавить атрибут в `__init__`: `self._micro_timer: float = random.uniform(2.0, 5.0)`

Добавить метод:

```python
def _dispatch_micro_action(self) -> None:
    """Проигрывает короткую микро-анимацию на micro-слое, не прерывая action."""
    micro_pool = ['whisker_loop', 'nose_twitch_loop', 'head_track_loop']
    anim = random.choice(micro_pool)
    if self.pygame_engine and hasattr(self.pygame_engine, 'clips'):
        if anim not in self.pygame_engine.clips:
            return
    if self.pygame_engine:
        self.pygame_engine.queue_action({
            'action_id': f'micro_{anim}',
            'anim':      anim,
            'sfx':       None,
            'position':  'current',
            'duration':  [2, 4],
            'subtitle':  '',
            'loop':      False,
            'layer':     'micro',
        })
```

В `sim_step()`, каждый тик:

```python
self._micro_timer -= dt
if self._micro_timer <= 0:
    self._dispatch_micro_action()
    self._micro_timer = random.uniform(3.0, 8.0)
```

---

## Задача 8 — Вариативные шаги в цепочках (вероятности)

**Файлы:** `config.py`, `behavioral_chains.py`

### Причина

`drink_water` встречается в 5 цепочках, `groom_body` в 4, `stand_upright` в 4.
Каждый запуск цепочки всегда идентичен — нет вариативности.

### Что нужно сделать

**Шаг 1.** Изменить формат цепочек в `config.py`:
каждый элемент теперь кортеж `(action_id, probability)`. Обратная совместимость: строки без вероятности интерпретируются как 1.0.

```python
BEHAVIORAL_CHAINS = {
    "morning_awakening": [
        ("sleep_house",   1.0),
        ("stretch_body",  1.0),
        ("yawn",          0.8),
        ("groom_face",    0.9),
        ("drink_water",   0.6),   # не каждое утро
        ("eat_pellets",   1.0),
        ("patrol_floor",  0.7),
        ("run_wheel",     0.5),
    ],
    "eating_and_grooming": [
        ("eat_pellets",   1.0),
        ("eat_hay",       0.8),
        ("eat_treat",     0.3),   # редкое угощение
        ("drink_water",   0.7),
        ("groom_face",    1.0),
        ("groom_body",    0.8),
        ("rest_loaf",     0.9),
    ],
    # Для остальных цепочек оставить вероятность 1.0 везде,
    # кроме drink_water (0.5–0.7) и rest_loaf (0.8–0.9)
}
```

**Шаг 2.** Обновить `BehavioralChainExecutor.get_next_action_in_chain()` в `behavioral_chains.py`:

```python
def get_next_action_in_chain(self):
    if not self.current_chain:
        return None

    chain_actions = BEHAVIORAL_CHAINS[self.current_chain]

    while self.chain_progress < len(chain_actions):
        step = chain_actions[self.chain_progress]
        self.chain_progress += 1

        # Поддержка обоих форматов: строка или (action_id, probability)
        if isinstance(step, tuple):
            action_id, probability = step
        else:
            action_id, probability = step, 1.0

        # Пропустить шаг с заданной вероятностью
        if random.random() > probability:
            self.logger.debug(f"Skipped step {action_id} (p={probability:.1f})")
            continue

        # Реализовать действие
        command = self.action_realizer.realize_action(
            action_id,
            pressure=0.9,
            context={"chain_context": self.current_chain}
        )
        if command:
            self.logger.debug(
                f"Chain step {self.chain_progress}/{len(chain_actions)}: {action_id}"
            )
            return command

    # Цепочка завершена
    self.chain_history.append(self.current_chain)
    if len(self.chain_history) > 50:
        self.chain_history.pop(0)
    self.logger.info(f"Chain '{self.current_chain}' completed")
    self.current_chain = None
    self.chain_progress = 0
    return None
```

---

## Задача 9 — Циркадная окраска фона

**Файл:** `pygame_engine.py`  
**Метод:** `render()`

### Причина

`SchedulingSystem` считает `circadian_phase` (0.0 = полночь, 0.5 = полдень), но визуально клетка не меняется.

### Что нужно сделать

**Шаг 1.** Добавить метод в `PygameEngine`:

```python
def set_circadian_phase(self, phase: float) -> None:
    """Обновить фазу циркадного ритма для окраски фона (0.0–1.0)."""
    self._circadian_phase = max(0.0, min(1.0, phase))
```

Добавить атрибут в `__init__`: `self._circadian_phase: float = 0.5`

**Шаг 2.** В `render()` заменить статичный `screen.fill()`:

```python
# Было:
self.screen.fill((235, 228, 215))

# Стало:
import math
day_t = max(0.0, math.sin(self._circadian_phase * math.pi))  # 0.0 ночь → 1.0 день
r = int(100 + 135 * day_t)
g = int( 90 + 138 * day_t)
b = int( 80 + 135 * day_t)
self.screen.fill((r, g, b))
```

Цвета: ночь `(100, 90, 80)` → день `(235, 228, 215)`.

**Шаг 3.** В `main.py`, в `sim_step()` после обновления scheduler:

```python
if self.pygame_engine and hasattr(self.pygame_engine, 'set_circadian_phase'):
    circadian = self.scheduler.get_circadian_state()
    self.pygame_engine.set_circadian_phase(circadian['phase'])
```

---

## Задача 10 — Индикатор wellbeing

**Файл:** `pygame_engine.py`

### Причина

Нет быстрого способа оценить состояние шиншиллы без открытия debug-оверлея.

### Что нужно сделать

Добавить метод `set_wellbeing()` и вызов в `render()`.

В `__init__`: `self._wellbeing: float = 1.0` — значение 0.0–1.0.

```python
def set_wellbeing(self, stress: float, valence: float, arousal: float,
                  pathological_chain: bool = False) -> None:
    """Обновить индикатор самочувствия. Вызывать раз в секунду."""
    if pathological_chain:
        self._wellbeing = 0.0       # красный
    elif stress > 0.6:
        self._wellbeing = 0.2
    elif stress > 0.3:
        self._wellbeing = 0.5       # жёлтый
    elif arousal < 0.2:
        self._wellbeing = -1.0      # синий (спит)
    else:
        self._wellbeing = 1.0       # зелёный
```

В `render()`, после `_draw_furniture()`:

```python
self._draw_wellbeing_bar()
```

```python
def _draw_wellbeing_bar(self) -> None:
    """Цветная полоска 12×80 px в правом верхнем углу клетки."""
    wb = self._wellbeing
    if wb < 0:
        color = (70, 130, 200)    # синий — спит
    elif wb < 0.3:
        color = (192, 40, 40)     # красный — стресс/патология
    elif wb < 0.6:
        color = (200, 160, 30)    # жёлтый — беспокойство
    else:
        color = (60, 160, 70)     # зелёный — норма

    bar_rect = pygame.Rect(self.width - 100, 60, 12, 80)
    pygame.draw.rect(self.screen, (50, 50, 50), bar_rect.inflate(2, 2))  # рамка
    pygame.draw.rect(self.screen, color, bar_rect)

    lbl = self.font_dbg.render("wellbeing", True, (160, 150, 140))
    self.screen.blit(lbl, (self.width - 118, 145))
```

В `main.py`, добавить атрибут `self._wellbeing_timer: float = 0.0`, в `sim_step()`:

```python
self._wellbeing_timer -= dt
if self._wellbeing_timer <= 0 and self.pygame_engine:
    s = self.affect.state
    pathological = self.chain_executor.current_chain == 'chronic_stress'
    self.pygame_engine.set_wellbeing(
        stress=s.get('stress', 0.0),
        valence=s.get('valence', 0.0),
        arousal=s.get('arousal', 0.5),
        pathological_chain=pathological,
    )
    self._wellbeing_timer = 1.0
```

---

## Порядок реализации

| # | Задача | Файлы | Сложность | Важность |
|---|---|---|---|---|
| 1 | Исправить `_calculate_reward()` | `memory_system.py` | Низкая | Критично |
| 2 | Вызвать `save_memory()` | `main.py` | Минимальная | Критично |
| 3 | Подключить `_build_candidate_chains()` | `main.py` | Низкая | Критично |
| 4 | Кэп `dt` в `AnimationPlayer` | `pygame_engine.py` | Минимальная | Важно |
| 5 | Включить мёртвые действия в цепочки | `config.py` | Низкая | Важно |
| 6 | Постуральный слой | `main.py` | Средняя | Улучшение |
| 7 | Микро-анимации в паузах | `main.py` | Средняя | Улучшение |
| 8 | Вариативные шаги (вероятности) | `config.py`, `behavioral_chains.py` | Средняя | Улучшение |
| 9 | Циркадная окраска фона | `pygame_engine.py`, `main.py` | Низкая | Идея |
| 10 | Индикатор wellbeing | `pygame_engine.py`, `main.py` | Средняя | Идея |

Задачи 1–3 можно делать в любом порядке — они независимы.
Задача 8 зависит от задачи 5 (изменения в цепочках лучше вносить за один проход).
