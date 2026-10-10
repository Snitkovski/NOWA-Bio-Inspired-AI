"""Encode validation words into NOWA context event tokens."""

from __future__ import annotations

import difflib
import math
from typing import Any, Dict, List, Literal, Optional, Sequence

from ._common import normalize_warriner_records, normalize_word, row_vad, row_word
from .hippocampus_seeder import _word_to_events


def encode_lexical(word: str) -> List[str]:
    """Return only lexical identity, with no VAD leakage."""
    return [f"word:{normalize_word(word)}"]


def encode_direct_vad(word: str, warriner_row: dict) -> List[str]:
    """Debug baseline that deliberately reveals VAD tokens."""
    if warriner_row is None:
        raise ValueError("direct_vad mode requires warriner_row")
    v, a, d = row_vad(warriner_row)
    return _word_to_events(word, v, a, d)


class WordStimulusEncoder:
    """Main word-to-context encoder for validation stimuli."""

    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "he",
        "her",
        "him",
        "his",
        "i",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "our",
        "she",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "we",
        "were",
        "with",
        "you",
        "your",
    }

    def __init__(
        self,
        mode: Literal["lexical", "sbert_neighbors", "direct_vad"] = "lexical",
        warriner_df: Optional[Any] = None,
        sbert_model: Any = None,
        k_neighbors: int = 2,
    ):
        self.mode = str(mode or "lexical")
        if self.mode not in {"lexical", "sbert_neighbors", "direct_vad"}:
            raise ValueError("mode must be lexical, sbert_neighbors, or direct_vad")
        self.warriner_df = warriner_df
        self.sbert_model = sbert_model
        self.k_neighbors = max(0, int(k_neighbors))
        self._records_cache: Optional[List[Dict[str, Any]]] = None
        self._embedding_cache: Dict[str, Any] = {}
        self._sbert_load_failed = False

    def encode(self, word: str, warriner_row: Optional[dict] = None) -> List[str]:
        """Return context_events for one word."""
        normalized = normalize_word(word)
        if self.mode == "lexical":
            return encode_lexical(normalized)
        if self.mode == "direct_vad":
            return encode_direct_vad(normalized, warriner_row)
        return self.encode_sbert_neighbors(normalized)

    def encode_batch(
        self,
        words: List[str],
        warriner_rows: Optional[List[dict]] = None,
    ) -> List[List[str]]:
        """Batch encoding for convenience and tests."""
        if warriner_rows is not None and len(words) != len(warriner_rows):
            raise ValueError("warriner_rows must have the same length as words")
        rows = warriner_rows or [None] * len(words)
        return [self.encode(word, row) for word, row in zip(words, rows)]

    def encode_sbert_neighbors(self, word: str) -> List[str]:
        """Return primary word token x3 plus up to two semantic-neighbor tokens."""
        base_token = f"word:{normalize_word(word)}"
        if self.k_neighbors <= 0:
            return [base_token]

        records = self._records()
        words = [row_word(row) for row in records if row_word(row)]
        if not words:
            return [base_token]

        neighbors = self._semantic_neighbors(word, words, min(self.k_neighbors, 2))
        tokens = [base_token, base_token, base_token]
        seen = {base_token}
        for neighbor in neighbors:
            token = f"word:{normalize_word(neighbor)}"
            if token not in seen:
                tokens.append(token)
                seen.add(token)
        return tokens

    def encode_sentence(
        self,
        sentence: str,
        max_content_words: int = 5,
        k_neighbors: int = 3,
    ) -> List[str]:
        """Encode a sentence into deduplicated context events without VAD leakage."""
        original_k = self.k_neighbors
        self.k_neighbors = max(0, int(k_neighbors))
        try:
            words = self._extract_content_words(sentence)[: max(1, int(max_content_words))]
            tokens: List[str] = []
            seen = set()
            for word in words:
                encoded = encode_lexical(word) if self.mode == "direct_vad" else self.encode(word)
                for token in encoded:
                    if token not in seen:
                        tokens.append(token)
                        seen.add(token)
            if tokens:
                return tokens
            fallback = normalize_word(str(sentence or "")[:20])
            return [f"word:{fallback}"] if fallback else ["word:neutral"]
        finally:
            self.k_neighbors = original_k

    def _extract_content_words(self, sentence: str) -> List[str]:
        words: List[str] = []
        current: List[str] = []
        for char in str(sentence or "").lower():
            if char.isalpha() or char == "'":
                current.append(char)
            else:
                if current:
                    self._append_content_word(words, "".join(current))
                    current = []
        if current:
            self._append_content_word(words, "".join(current))
        return words

    def _append_content_word(self, words: List[str], raw_word: str) -> None:
        word = normalize_word(raw_word.strip("'"))
        if len(word) <= 2 or word in self.STOP_WORDS:
            return
        if word not in words:
            words.append(word)

    def _records(self) -> List[Dict[str, Any]]:
        if self._records_cache is None:
            self._records_cache = normalize_warriner_records(self.warriner_df or [])
        return [dict(row) for row in self._records_cache]

    def _semantic_neighbors(self, word: str, candidates: Sequence[str], k: int) -> List[str]:
        usable = [normalize_word(candidate) for candidate in candidates if normalize_word(candidate) != word]
        if not usable:
            return []
        self._ensure_sbert_model()
        if self.sbert_model is not None:
            try:
                return self._model_neighbors(word, usable, k)
            except Exception:
                pass
        return self._lexical_fallback_neighbors(word, usable, k)

    def _ensure_sbert_model(self) -> None:
        if self.sbert_model is not None or self._sbert_load_failed:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self.sbert_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception:
            self._sbert_load_failed = True

    def _model_neighbors(self, word: str, candidates: Sequence[str], k: int) -> List[str]:
        word_vec = self._embedding(word)
        self._precache_embeddings(candidates)
        scored = []
        for candidate in candidates:
            cand_vec = self._embedding(candidate)
            score = self._cosine(word_vec, cand_vec)
            scored.append((score, candidate))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [candidate for _, candidate in scored[:k]]

    def _precache_embeddings(self, texts: Sequence[str]) -> None:
        missing = [normalize_word(text) for text in texts if normalize_word(text) not in self._embedding_cache]
        if not missing:
            return
        encoded = self.sbert_model.encode(missing, show_progress_bar=False)
        for text, vector in zip(missing, encoded):
            self._embedding_cache[text] = vector

    def _embedding(self, text: str) -> Any:
        key = normalize_word(text)
        if key not in self._embedding_cache:
            encoded = self.sbert_model.encode([key], show_progress_bar=False)
            if isinstance(encoded, list):
                self._embedding_cache[key] = encoded[0]
            else:
                self._embedding_cache[key] = encoded[0]
        return self._embedding_cache[key]

    @staticmethod
    def _cosine(left: Any, right: Any) -> float:
        left_values = [float(x) for x in list(left)]
        right_values = [float(x) for x in list(right)]
        num = sum(a * b for a, b in zip(left_values, right_values))
        den_l = math.sqrt(sum(a * a for a in left_values))
        den_r = math.sqrt(sum(b * b for b in right_values))
        denom = den_l * den_r
        return 0.0 if denom <= 0.0 else num / denom

    @staticmethod
    def _lexical_fallback_neighbors(word: str, candidates: Sequence[str], k: int) -> List[str]:
        scored = [
            (difflib.SequenceMatcher(a=word, b=candidate).ratio(), candidate)
            for candidate in candidates
        ]
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [candidate for _, candidate in scored[:k]]


def encode_sbert_neighbors(word: str, warriner_df: Any, k: int = 2) -> List[str]:
    encoder = WordStimulusEncoder(
        mode="sbert_neighbors",
        warriner_df=warriner_df,
        k_neighbors=k,
    )
    return encoder.encode(word)


__all__ = [
    "WordStimulusEncoder",
    "encode_lexical",
    "encode_sbert_neighbors",
    "encode_direct_vad",
]
