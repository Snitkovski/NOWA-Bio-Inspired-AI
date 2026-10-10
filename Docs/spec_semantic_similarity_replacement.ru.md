# Замена семантическим сходством

English version: [spec_semantic_similarity_replacement.en.md](spec_semantic_similarity_replacement.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Проблема

`_hash_text_vector()` генерирует случайные векторы:

```
"eat"
"consume food"
```

→ никак не связаны.

---

## Минимальное решение

Тяжёлый эмбеддинг не нужен. Используем **детерминированное семантическое хеширование**.

---

## Алгоритм

**1. Токенизация:**

```
"eat_food" → ["eat", "food"]
```

**2. Стабильные векторы слов:**

```
vector(word) = hash(word) → unit vector
```

**3. Вектор предложения:**

```
v = mean(word_vectors)
```

**4. Сходство:**

```
cosine(v1, v2)
```

---

## Преимущества

- детерминированный
- дешёвый
- похожие строки → похожие вектора

---

## Код

```python
def semantic_vector(text):
    tokens  = tokenize(text)
    vectors = [word_vec(t) for t in tokens]
    return normalize(mean(vectors))
```
