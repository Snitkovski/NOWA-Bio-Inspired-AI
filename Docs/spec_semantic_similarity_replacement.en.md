# Semantic Similarity Replacement

Russian version: [spec_semantic_similarity_replacement.ru.md](spec_semantic_similarity_replacement.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

## Problem

`_hash_text_vector()` generates random vectors:

```
"eat"
"consume food"
```

→ they are not related in any way.

---

## Minimal solution

A heavy embedding is not required. **Deterministic semantic hashing** is used.

---

## Algorithm

**1. Tokenize:**

```
"eat_food" → ["eat", "food"]
```

**2. Stable word vectors:**

```
vector(word) = hash(word) → unit vector
```

**3. Sentence vector:**

```
v = mean(word_vectors)
```

**4. Similarity:**

```
cosine(v1, v2)
```

---

## Advantages

- deterministic
- cheap
- similar strings → similar vectors

---

## Code

```python
def semantic_vector(text):
    tokens  = tokenize(text)
    vectors = [word_vec(t) for t in tokens]
    return normalize(mean(vectors))
```
