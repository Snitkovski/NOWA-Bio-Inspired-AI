"""Seed NOWA hippocampal memory with affective Warriner episodes."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Literal, Optional, Sequence

from ._common import (
    clamp,
    ensure_core_src_on_path,
    normalize_warriner_records,
    normalize_word,
    row_vad,
    row_word,
    stratified_sample,
)


def _word_to_events(word: str, v: float, a: float, d: float) -> List[str]:
    """Convert a Warriner word plus normalized VAD into NOWA event tokens."""
    token_word = normalize_word(word)
    events = [f"word:{token_word}"]

    if v > 0.6:
        events.append("valence:very_positive")
    elif v > 0.2:
        events.append("valence:positive")
    elif v >= -0.2:
        events.append("valence:neutral")
    elif v >= -0.6:
        events.append("valence:negative")
    else:
        events.append("valence:very_negative")

    if a > 0.6:
        events.append("arousal:high")
    elif a >= 0.4:
        events.append("arousal:medium")
    else:
        events.append("arousal:low")

    if d > 0.6:
        events.append("dominance:high")
    elif d < 0.4:
        events.append("dominance:low")

    return events


def _consequence_name(v: float) -> str:
    if v > 0.1:
        return "positive_valence_outcome"
    if v < -0.1:
        return "negative_valence_outcome"
    return "neutral_outcome"


def _path_from_events(events: Sequence[str]) -> Any:
    ensure_core_src_on_path()
    try:
        from experience import Event, EventType, Path
    except Exception:
        return list(events)

    path = Path()
    for event_name in events:
        path = path.add_event(Event(str(event_name), EventType.CONTEXT))
    return path


def _consequence_event(v: float) -> Any:
    ensure_core_src_on_path()
    name = _consequence_name(v)
    try:
        from experience import Event, EventType
    except Exception:
        return name
    return Event(name, EventType.CONSEQUENCE)


class HippocampusSeeder:
    """Build and store affectively-labeled seed episodes in agent hippocampi."""

    def __init__(
        self,
        warriner_df: Any,
        n_seed: int = 500,
        seed_strategy: Literal["stratified", "random", "full"] = "stratified",
        rng: Optional[random.Random] = None,
    ):
        self.warriner_df = warriner_df
        self.n_seed = max(0, int(n_seed))
        self.seed_strategy = str(seed_strategy or "stratified")
        if self.seed_strategy not in {"stratified", "random", "full"}:
            raise ValueError("seed_strategy must be stratified, random, or full")
        self.rng = rng if rng is not None else random.Random()
        self._seed_corpus_cache: Optional[List[Dict[str, Any]]] = None

    def build_seed_corpus(self) -> List[dict]:
        """Return seed records with normalized keys: word, v, a, d."""
        if self._seed_corpus_cache is not None:
            return [dict(row) for row in self._seed_corpus_cache]

        records = normalize_warriner_records(self.warriner_df)
        if self.seed_strategy == "full":
            corpus = list(records)
        elif self.seed_strategy == "random":
            corpus = [dict(row) for row in records]
            self.rng.shuffle(corpus)
            corpus = corpus[: min(self.n_seed, len(corpus))]
        else:
            corpus = stratified_sample(records, self.n_seed, self.rng)

        self._seed_corpus_cache = [dict(row) for row in corpus]
        return [dict(row) for row in corpus]

    def seed_agent(self, agent: Any) -> int:
        """Populate one agent's hippocampus and return the episode count."""
        return self._seed_agent_with_corpus(agent, self.build_seed_corpus())

    def seed_colony(self, agents: List[Any]) -> Dict[str, int]:
        """Populate all agents with the same seed corpus in varied order."""
        base_corpus = self.build_seed_corpus()
        counts: Dict[str, int] = {}
        for index, agent in enumerate(list(agents or [])):
            agent_corpus = [dict(row) for row in base_corpus]
            self.rng.shuffle(agent_corpus)
            agent_id = str(getattr(agent, "agent_id", "") or f"agent_{index}")
            counts[agent_id] = self._seed_agent_with_corpus(agent, agent_corpus)
        return counts

    def _seed_agent_with_corpus(self, agent: Any, corpus: Sequence[dict]) -> int:
        hippocampus = getattr(agent, "hippocampus", None)
        if hippocampus is None or not hasattr(hippocampus, "store"):
            raise AttributeError("agent must expose a hippocampus.store API")

        added = 0
        for row in corpus:
            word = row_word(row)
            v, a, d = row_vad(row)
            events = _word_to_events(word, v, a, d)
            path = _path_from_events(events)
            consequence = _consequence_event(v)
            intensity = abs(v)
            reward = clamp(v, -1.0, 1.0)
            encoding_strength = clamp((abs(v) * 0.8) + 0.2, 0.0, 1.0)

            stored = self._store(
                hippocampus,
                path,
                consequence,
                intensity=intensity,
                reward=reward,
                encoding_strength=encoding_strength,
            )
            self._attach_warriner_metadata(stored, word, v, a, d, events)
            added += 1

            if abs(v) > 0.7 and hasattr(hippocampus, "reinforce"):
                reinforced = self._reinforce(hippocampus, path, consequence, intensity=intensity)
                self._attach_warriner_metadata(reinforced, word, v, a, d, events)

        return added

    @staticmethod
    def _store(
        hippocampus: Any,
        path: Any,
        consequence: Any,
        intensity: float,
        reward: float,
        encoding_strength: float,
    ) -> Any:
        try:
            return hippocampus.store(
                path,
                consequence=consequence,
                intensity=intensity,
                reward=reward,
                encoding_strength=encoding_strength,
            )
        except TypeError:
            try:
                return hippocampus.store(
                    path,
                    consequence=consequence,
                    intensity=intensity,
                    reward=reward,
                )
            except TypeError:
                return hippocampus.store(path, consequence=consequence, intensity=intensity)

    @staticmethod
    def _reinforce(hippocampus: Any, path: Any, consequence: Any, intensity: float) -> Any:
        try:
            return hippocampus.reinforce(path, consequence=consequence, intensity=intensity)
        except TypeError:
            try:
                return hippocampus.reinforce(path, consequence=consequence)
            except TypeError:
                return hippocampus.reinforce(path)

    @staticmethod
    def _attach_warriner_metadata(
        experience: Any,
        word: str,
        v: float,
        a: float,
        d: float,
        events: Sequence[str],
    ) -> None:
        if experience is None:
            return
        for key, value in {
            "warriner_word": word,
            "warriner_valence_norm": float(v),
            "warriner_arousal_norm": float(a),
            "warriner_dominance_norm": float(d),
            "warriner_seed_events": list(events),
        }.items():
            try:
                setattr(experience, key, value)
            except Exception:
                pass


__all__ = ["HippocampusSeeder", "_word_to_events"]
