# Слой взаимодействия нейромодуляторов

English version: [spec_neuromodulator_interaction_layer.en.md](spec_neuromodulator_interaction_layer.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Проблема

Сейчас нейромодуляторы — просто скаляры без взаимодействий:

```text
DA
5HT
NE
ACh
```

В мозге существуют попарные взаимодействия:

```text
DA  ↔ ACh
NE  ↔ ACh
5HT ↔ DA
```

а также важна топография (локальность).

---

## Минимальное улучшение

Полноценные карты не нужны. Добавляются **матрица взаимодействия и медленная динамика**.

**Было:**

```text
DA_t+1 = f(signal)
```

**Станет:**

```text
M = [DA, 5HT, NE, ACh]

dM/dt = base_signal
      + W * M
      - decay * M
```

Где `W` — матрица взаимодействия.

---

## Матрица взаимодействия

```text
       DA    5HT   NE    ACh
DA   [  0   -0.2   0.1  -0.3 ]
5HT  [  0.1   0   -0.1   0   ]
NE   [  0.2  -0.1   0    0.2 ]
ACh  [ -0.3   0    0.2   0   ]
```

---

## Кодовая структура

**Новый класс:** `NeuromodulatorField`

```python
def update(signals):

    M = self.levels

    interaction = W @ M

    dM = signals + interaction - decay * M

    M += dt * dM
```

---

## Почему это важно

Появляются биологически правдоподобные эффекты:

```text
high NE  → suppress ACh
high DA  → suppress ACh
high 5HT → damp DA
```
