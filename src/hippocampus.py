"""Hippocampus 2.0: fuzzy episodic memory with novelty signaling."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import time
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from experience import Event, EventType, Experience, Path


@dataclass
class SignatureTrace:
    feature_set: Set[str]
    drive_vector: Tuple[float, float, float]
    context_vector: Tuple[float, float, float]
    timestamp: float
    context_tokens: Tuple[str, ...] = ()
    activation_weight: float = 1.0
    repetition_count: int = 1
    reward_signal: float = 0.0
    source_experience: Optional[Experience] = None
    last_decay_ts: float = field(default_factory=time.time)


class NOWAHippocampus:
    """Hippocampal episodic memory with spec 2.0 extensions."""

    def __init__(
        self,
        max_experiences: int = 1000,
        activation_decay_half_life: float = 3600.0,
        decay_rate: float = 0.015,
        activation_threshold: float = 0.03,
        max_features: int = 12,
        top_k_recall: int = 5,
        novelty_window: int = 25,
        cycle_length: int = 24,
        context_history_size: int = 12,
        activation_similarity_threshold: float = 0.20,
        reinforce_similarity_threshold: float = 0.85,
        consolidation_min_probability: float = 0.0,
        novelty_capacity_bias: float = 0.55,
    ):
        self.experiences: List[Experience] = []
        self.signatures: List[SignatureTrace] = []

        self.max_experiences = max(1, int(max_experiences))
        self.activation_decay_half_life = max(1e-6, float(activation_decay_half_life))
        self.decay_rate = max(0.0, min(0.99, float(decay_rate)))
        self.activation_threshold = max(0.0, min(1.0, float(activation_threshold)))
        self.max_features = max(1, int(max_features))
        self.top_k_recall = max(1, int(top_k_recall))
        self.novelty_window = max(1, int(novelty_window))
        self.cycle_length = max(1, int(cycle_length))
        self.context_history_size = max(1, int(context_history_size))
        self.activation_similarity_threshold = max(0.0, min(1.0, float(activation_similarity_threshold)))
        self.reinforce_similarity_threshold = max(0.0, min(1.0, float(reinforce_similarity_threshold)))
        self.consolidation_min_probability = max(0.0, min(1.0, float(consolidation_min_probability)))
        self.novelty_capacity_bias = max(0.0, min(1.0, float(novelty_capacity_bias)))
        self.novelty_sensitivity_scale = 1.0

        self._recent_event_window: List[str] = []
        self._novelty_history: List[float] = []
        self._episode_seq = 0
        self._episodes_by_id: Dict[str, Experience] = {}

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, float(value)))

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def set_novelty_sensitivity_scale(self, scale: float) -> float:
        """Set external novelty scaling factor (CER integration)."""
        self.novelty_sensitivity_scale = self._clamp(self._safe_float(scale, 1.0), 0.5, 2.0)
        return self.novelty_sensitivity_scale

    def get_novelty_sensitivity_scale(self) -> float:
        return self._clamp(self._safe_float(self.novelty_sensitivity_scale, 1.0), 0.5, 2.0)

    def _to_path(self, path_like) -> Path:
        if isinstance(path_like, Path):
            return path_like

        if isinstance(path_like, (set, tuple, list)):
            path = Path()
            for token in path_like:
                if token is None:
                    continue
                path = path.add_event(Event(str(token), EventType.CONTEXT))
            return path

        if isinstance(path_like, str):
            path = Path()
            return path.add_event(Event(path_like, EventType.CONTEXT))

        if hasattr(path_like, "signature"):
            try:
                signature_items = list(path_like.signature())
            except Exception:
                signature_items = []
            path = Path()
            for token in signature_items:
                path = path.add_event(Event(str(token), EventType.CONTEXT))
            return path

        raise TypeError("path must be Path, iterable of feature strings, or signature-like object")

    def _sanitize_features(self, features: Iterable[str]) -> Set[str]:
        out: Set[str] = set()
        for feature in features or []:
            token = str(feature).strip()
            if token:
                out.add(token)
        return out

    def _extract_features_from_path(self, path: Path, consequence=None) -> Set[str]:
        features = self._sanitize_features(path.signature())
        if consequence is not None and getattr(consequence, "name", None):
            features.add(f"consequence:{consequence.name}")
        return features

    def _feature_frequency(self, feature: str) -> int:
        count = 0
        for sig in self.signatures:
            if feature in sig.feature_set:
                count += 1
        return count

    def _salience_score(self, feature: str) -> float:
        freq = self._feature_frequency(feature)
        rarity = 1.0 / (1.0 + float(freq))
        structural = 0.05
        if ":" in feature:
            structural += 0.15
        if feature.startswith("action:"):
            structural += 0.20
        if feature.startswith("consequence:"):
            structural += 0.12
        return rarity + structural

    def _sparsify_features(self, feature_set: Set[str]) -> Set[str]:
        features = self._sanitize_features(feature_set)
        if len(features) <= self.max_features:
            return features
        ranked = sorted(features, key=lambda f: (-self._salience_score(f), f))
        return set(ranked[: self.max_features])

    def _build_drive_vector(
        self,
        intensity: float,
        reward: float = 0.0,
        encoding_strength: Optional[float] = None,
        drive_state=None,
    ) -> Tuple[float, float, float]:
        if isinstance(drive_state, dict):
            ordered = sorted((str(k), self._safe_float(v)) for k, v in drive_state.items())
            vals = [v for _, v in ordered[:3]]
            while len(vals) < 3:
                vals.append(0.0)
            return tuple(vals[:3])

        if isinstance(drive_state, (tuple, list)):
            vals = [self._safe_float(v) for v in list(drive_state)[:3]]
            while len(vals) < 3:
                vals.append(0.0)
            return tuple(vals)

        enc = self._safe_float(
            encoding_strength if encoding_strength is not None else intensity,
            default=self._safe_float(intensity, 0.0),
        )
        return (
            self._safe_float(intensity, 0.0),
            self._safe_float(reward, 0.0),
            enc,
        )

    def _rolling_hash(self, tokens: Sequence[str]) -> int:
        payload = "|".join(str(t) for t in list(tokens or [])[-self.context_history_size :])
        digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()
        return int(digest, 16)

    def _build_context_tokens(self, features: Set[str]) -> Tuple[str, ...]:
        tokens = list(self._recent_event_window[-self.context_history_size :]) + sorted(list(features))
        if len(tokens) > self.context_history_size:
            tokens = tokens[-self.context_history_size :]
        return tuple(tokens)

    def _discretize_drive(self, drive_vector: Tuple[float, float, float]) -> float:
        mean_drive = sum(abs(self._safe_float(v, 0.0)) for v in drive_vector) / 3.0
        return float(min(9, max(0, int(round(mean_drive * 3.0)))))

    def _encode_context_vector(
        self,
        features: Set[str],
        drive_vector: Tuple[float, float, float],
        timestamp: float,
        context_tokens: Optional[Sequence[str]] = None,
    ) -> Tuple[float, float, float]:
        time_bucket = float(int(timestamp) % self.cycle_length)
        tokens = list(context_tokens or self._build_context_tokens(features))
        rolling_hash = self._rolling_hash(tokens)
        drive_bucket = self._discretize_drive(drive_vector)
        return (time_bucket, float(rolling_hash), drive_bucket)

    def _vector_similarity(
        self, left: Tuple[float, float, float], right: Tuple[float, float, float]
    ) -> float:
        distance = math.sqrt(sum((self._safe_float(a) - self._safe_float(b)) ** 2 for a, b in zip(left, right)))
        return self._clamp(1.0 / (1.0 + distance))

    @staticmethod
    def _jaccard_similarity(left: Set[str], right: Set[str]) -> float:
        if not left and not right:
            return 1.0
        union = left | right
        if not union:
            return 0.0
        return float(len(left & right)) / float(len(union))

    def _context_window_similarity(
        self,
        query_tokens: Sequence[str],
        stored_tokens: Sequence[str],
    ) -> float:
        left = [str(x) for x in list(query_tokens or [])]
        right = [str(x) for x in list(stored_tokens or [])]
        if not left or not right:
            return 0.0

        left_set = set(left)
        right_set = set(right)
        set_sim = self._jaccard_similarity(left_set, right_set)
        max_len = max(len(left), len(right), 1)
        positional = 0.0
        for idx in range(min(len(left), len(right))):
            if left[idx] == right[idx]:
                positional += 1.0
        positional_sim = positional / float(max_len)
        return self._clamp(0.75 * set_sim + 0.25 * positional_sim)

    def _context_similarity(
        self,
        q_ctx: Tuple[float, float, float],
        s_ctx: Tuple[float, float, float],
        q_tokens: Sequence[str],
        s_tokens: Sequence[str],
    ) -> float:
        if q_ctx is None or s_ctx is None:
            return 0.0
        time_delta = abs(self._safe_float(q_ctx[0]) - self._safe_float(s_ctx[0]))
        cyc = float(max(1, self.cycle_length))
        time_sim = self._clamp(1.0 - min(time_delta, cyc) / cyc)
        max_hash = float((1 << 64) - 1)
        hash_delta = abs(self._safe_float(q_ctx[1]) - self._safe_float(s_ctx[1])) / max_hash
        hash_sim = self._clamp(1.0 - hash_delta)
        drive_delta = abs(self._safe_float(q_ctx[2]) - self._safe_float(s_ctx[2]))
        drive_sim = self._clamp(1.0 - (drive_delta / 9.0))
        window_sim = self._context_window_similarity(q_tokens, s_tokens)
        return 0.30 * time_sim + 0.15 * hash_sim + 0.20 * drive_sim + 0.35 * window_sim

    def _composite_similarity(
        self,
        query_features: Set[str],
        query_drive: Tuple[float, float, float],
        query_context: Tuple[float, float, float],
        query_context_tokens: Sequence[str],
        stored: SignatureTrace,
    ) -> float:
        feature_sim = self._jaccard_similarity(query_features, stored.feature_set)
        drive_sim = self._vector_similarity(query_drive, stored.drive_vector)
        context_sim = self._context_similarity(
            query_context,
            stored.context_vector,
            query_context_tokens,
            getattr(stored, "context_tokens", ()),
        )
        return self._clamp(0.80 * feature_sim + 0.15 * drive_sim + 0.05 * context_sim)
    def _append_recent_events(self, ordered_tokens: Sequence[str]) -> None:
        for token in ordered_tokens or []:
            txt = str(token).strip()
            if not txt:
                continue
            self._recent_event_window.append(txt)
            if len(self._recent_event_window) > self.context_history_size:
                self._recent_event_window = self._recent_event_window[-self.context_history_size :]

    def _ensure_signature_store(self) -> None:
        if not self.experiences:
            self.signatures = []
            return

        existing_by_experience = {}
        for sig in self.signatures:
            if sig.source_experience is not None:
                existing_by_experience[id(sig.source_experience)] = sig

        rebuilt: List[SignatureTrace] = []
        for exp in self.experiences:
            found = existing_by_experience.get(id(exp))
            if found is None:
                features = self._sparsify_features(self._extract_features_from_path(exp.path, exp.consequence))
                drive_vector = self._build_drive_vector(
                    intensity=getattr(exp, "intensity", 0.0),
                    reward=getattr(exp, "reward", 0.0),
                    encoding_strength=getattr(exp, "encoding_strength", None),
                )
                timestamp = self._safe_float(getattr(exp, "timestamp", time.time()), time.time())
                context_tokens = self._build_context_tokens(features)
                context_vector = self._encode_context_vector(
                    features,
                    drive_vector,
                    timestamp,
                    context_tokens=context_tokens,
                )
                found = SignatureTrace(
                    feature_set=features,
                    drive_vector=drive_vector,
                    context_vector=context_vector,
                    context_tokens=context_tokens,
                    timestamp=timestamp,
                    activation_weight=self._clamp(self._safe_float(getattr(exp, "activation_energy", 1.0), 1.0)),
                    repetition_count=max(1, int(getattr(exp, "reinforcement_count", 1))),
                    reward_signal=self._safe_float(getattr(exp, "reward", 0.0), 0.0),
                    source_experience=exp,
                    last_decay_ts=self._safe_float(getattr(exp, "last_activated", time.time()), time.time()),
                )
            else:
                found.repetition_count = max(1, int(getattr(exp, "reinforcement_count", found.repetition_count)))
                found.activation_weight = self._clamp(
                    self._safe_float(getattr(exp, "activation_energy", found.activation_weight), found.activation_weight)
                )
                found.source_experience = exp
                if not found.feature_set:
                    found.feature_set = self._sparsify_features(
                        self._extract_features_from_path(exp.path, getattr(exp, "consequence", None))
                    )
                if not getattr(found, "context_tokens", None):
                    found.context_tokens = self._build_context_tokens(found.feature_set)
            rebuilt.append(found)
        self.signatures = rebuilt

    def _apply_decay(self) -> None:
        if not self.signatures:
            return

        now = time.time()
        for sig in self.signatures:
            elapsed = max(0.0, now - self._safe_float(sig.last_decay_ts, now))
            if elapsed <= 0.0:
                continue
            decay_steps = elapsed / self.activation_decay_half_life
            half_life_factor = 0.5 ** decay_steps
            # Half-life remains the primary decay dynamic.
            # decay_rate is used as a soft regularizer to avoid overly aggressive collapse.
            if self.decay_rate > 0.0:
                retention_bias = (1.0 - self.decay_rate) ** decay_steps
                decay_factor = self._clamp((0.90 * half_life_factor) + (0.10 * retention_bias), 0.0, 1.0)
            else:
                decay_factor = self._clamp(half_life_factor, 0.0, 1.0)
            sig.activation_weight = self._clamp(sig.activation_weight * decay_factor)

            exp = sig.source_experience
            if exp is not None:
                exp.activation_energy = self._clamp(
                    self._safe_float(getattr(exp, "activation_energy", 1.0), 1.0) * decay_factor
                )
            sig.last_decay_ts = now

        keep_exps: List[Experience] = []
        keep_sigs: List[SignatureTrace] = []
        for exp, sig in zip(self.experiences, self.signatures):
            strong_enough = sig.activation_weight >= self.activation_threshold
            repeated = int(getattr(exp, "reinforcement_count", 1)) >= 2
            stable = self._safe_float(getattr(exp, "stability", 0.0), 0.0) >= 1.0
            if strong_enough or repeated or stable:
                keep_exps.append(exp)
                keep_sigs.append(sig)

        self.experiences = keep_exps
        self.signatures = keep_sigs
        self._sync_episode_index()

    def _assign_episode_id(self, exp: Experience) -> str:
        """Give an experience a stable id that does not depend on list order."""
        existing = getattr(exp, "episode_id", None)
        if existing:
            episode_id = str(existing)
        else:
            self._episode_seq += 1
            episode_id = f"ep-{self._episode_seq}"
            exp.episode_id = episode_id
        self._episodes_by_id[episode_id] = exp
        return episode_id

    def _sync_episode_index(self) -> None:
        """Rebuild the id index from the episodes that are still stored."""
        index: Dict[str, Experience] = {}
        for exp in self.experiences:
            episode_id = getattr(exp, "episode_id", None)
            if not episode_id:
                continue
            index[str(episode_id)] = exp
        self._episodes_by_id = index

    def get_experience(self, episode_id: str):
        """Return the stored episode with this id, regardless of list position."""
        if episode_id is None:
            return None
        key = str(episode_id)
        resident = self._episodes_by_id.get(key)
        if resident is not None and any(item is resident for item in self.experiences):
            return resident
        self._sync_episode_index()
        return self._episodes_by_id.get(key)

    def _enforce_capacity(self, protect_id: Optional[str] = None) -> None:
        if len(self.experiences) <= self.max_experiences:
            return

        scored = []
        for exp, sig in zip(self.experiences, self.signatures):
            novelty = self._novelty_from_recent(sig.feature_set, exclude_signature=sig)
            novelty_blend = (
                (1.0 - self.novelty_capacity_bias) * self._safe_float(sig.activation_weight, 0.0)
            ) + (self.novelty_capacity_bias * novelty)
            score = (
                novelty_blend,
                novelty,
                int(getattr(exp, "reinforcement_count", 1)),
                self._safe_float(getattr(exp, "last_activated", 0.0), 0.0),
            )
            scored.append((score, exp, sig))

        scored.sort(key=lambda item: item[0], reverse=True)
        protected = str(protect_id) if protect_id else ""
        kept = []
        overflow = []
        if protected:
            for item in scored:
                if str(getattr(item[1], "episode_id", "")) == protected:
                    kept.append(item)
                else:
                    overflow.append(item)
            room = max(0, self.max_experiences - len(kept))
            kept.extend(overflow[:room])
        else:
            kept = scored[: self.max_experiences]
        self.experiences = [item[1] for item in kept]
        self.signatures = [item[2] for item in kept]
        self._sync_episode_index()

    def _build_query_signature(
        self, current_signature, consequence=None, intensity: float = 1.0
    ) -> Tuple[Set[str], Tuple[float, float, float], Tuple[float, float, float], float, Tuple[str, ...]]:
        now = time.time()

        if isinstance(current_signature, dict):
            raw_features = current_signature.get("features", current_signature.get("feature_set", []))
            features = self._sparsify_features(self._sanitize_features(raw_features))
            drive_vector = self._build_drive_vector(
                intensity=current_signature.get("intensity", intensity),
                reward=current_signature.get("reward", 0.0),
                encoding_strength=current_signature.get("encoding_strength", current_signature.get("drive_state", None)),
                drive_state=current_signature.get("drive_vector", current_signature.get("drive_state", None)),
            )
            timestamp = self._safe_float(current_signature.get("timestamp", now), now)
            supplied_context = current_signature.get("context_vector")
            supplied_tokens = current_signature.get("context_tokens")
            if isinstance(supplied_tokens, (tuple, list)):
                context_tokens = tuple(str(x) for x in list(supplied_tokens)[-self.context_history_size :])
            else:
                context_tokens = self._build_context_tokens(features)
            if isinstance(supplied_context, (list, tuple)) and len(supplied_context) >= 3:
                context_vector = (
                    self._safe_float(supplied_context[0]),
                    self._safe_float(supplied_context[1]),
                    self._safe_float(supplied_context[2]),
                )
            else:
                context_vector = self._encode_context_vector(
                    features,
                    drive_vector,
                    timestamp,
                    context_tokens=context_tokens,
                )
            return features, drive_vector, context_vector, timestamp, context_tokens

        path = self._to_path(current_signature)
        features = self._sparsify_features(self._extract_features_from_path(path, consequence))
        drive_vector = self._build_drive_vector(intensity=intensity)
        context_tokens = self._build_context_tokens(features)
        context_vector = self._encode_context_vector(
            features,
            drive_vector,
            now,
            context_tokens=context_tokens,
        )
        return features, drive_vector, context_vector, now, context_tokens

    def store(
        self,
        path,
        consequence=None,
        intensity: float = 1.0,
        reward: float = 0.0,
        encoding_strength: float = None,
    ) -> Experience:
        self._ensure_signature_store()
        self._apply_decay()

        signature_input = path if isinstance(path, dict) else None
        if signature_input is not None and ("features" in signature_input or "feature_set" in signature_input):
            features, drive_vector, context_vector, timestamp, context_tokens = self._build_query_signature(
                signature_input, consequence=consequence, intensity=intensity
            )
            path_obj = self._to_path(sorted(features))
        else:
            path_obj = self._to_path(path)
            features = self._sparsify_features(self._extract_features_from_path(path_obj, consequence))
            drive_vector = self._build_drive_vector(
                intensity=intensity,
                reward=reward,
                encoding_strength=encoding_strength,
            )
            timestamp = time.time()
            context_tokens = self._build_context_tokens(features)
            context_vector = self._encode_context_vector(
                features,
                drive_vector,
                timestamp,
                context_tokens=context_tokens,
            )

        exp = Experience(
            path_obj,
            consequence=consequence,
            intensity=intensity,
            reward=reward,
            encoding_strength=encoding_strength,
        )
        if signature_input is not None and "timestamp" in signature_input:
            ts = self._safe_float(signature_input.get("timestamp", time.time()), time.time())
            exp.timestamp = ts
            exp.first_seen = ts
            exp.last_activated = ts

        self._assign_episode_id(exp)
        self.experiences.append(exp)
        sig = SignatureTrace(
            feature_set=features,
            drive_vector=drive_vector,
            context_vector=context_vector,
            context_tokens=context_tokens,
            timestamp=self._safe_float(getattr(exp, "timestamp", timestamp), timestamp),
            activation_weight=self._safe_float(getattr(exp, "activation_energy", 1.0), 1.0),
            repetition_count=max(1, int(getattr(exp, "reinforcement_count", 1))),
            reward_signal=self._safe_float(reward, 0.0),
            source_experience=exp,
            last_decay_ts=time.time(),
        )
        self.signatures.append(sig)
        self._append_recent_events(path_obj.signature())
        self._enforce_capacity(protect_id=str(getattr(exp, "episode_id", "") or ""))
        return exp
    def reinforce(self, path, consequence=None, intensity: float = 1.0):
        self._ensure_signature_store()
        self._apply_decay()

        query_features, query_drive, query_context, _, query_tokens = self._build_query_signature(
            path, consequence=consequence, intensity=intensity
        )

        best_similarity = -1.0
        best_sig: Optional[SignatureTrace] = None
        for sig in self.signatures:
            sim = self._composite_similarity(query_features, query_drive, query_context, query_tokens, sig)
            if sim > best_similarity:
                best_similarity = sim
                best_sig = sig

        if best_sig is not None and best_similarity >= self.reinforce_similarity_threshold:
            exp = best_sig.source_experience
            if exp is None:
                return self.store(path, consequence=consequence, intensity=intensity)

            exp.reinforcement_count += 1
            exp.last_activated = time.time()
            exp.activation_energy = self._clamp(
                max(self._safe_float(getattr(exp, "activation_energy", 1.0), 1.0), best_similarity)
            )
            exp.intensity = max(self._safe_float(getattr(exp, "intensity", 0.0), 0.0), float(intensity))

            best_sig.feature_set = self._sparsify_features(set(best_sig.feature_set) | set(query_features))
            best_sig.repetition_count = int(getattr(exp, "reinforcement_count", best_sig.repetition_count))
            best_sig.activation_weight = self._safe_float(getattr(exp, "activation_energy", best_sig.activation_weight))
            blend_n = max(1.0, float(best_sig.repetition_count))
            best_sig.drive_vector = tuple(
                ((a * (blend_n - 1.0)) + b) / blend_n for a, b in zip(best_sig.drive_vector, query_drive)
            )
            best_sig.context_vector = self._encode_context_vector(best_sig.feature_set, best_sig.drive_vector, time.time())
            best_sig.context_tokens = self._build_context_tokens(best_sig.feature_set)
            self._append_recent_events(list(query_features))
            return exp

        return self.store(path, consequence=consequence, intensity=intensity)

    def activate(self, context_events: list) -> list:
        self._ensure_signature_store()
        self._apply_decay()

        if not self.experiences:
            return []

        context_features = self._sanitize_features(context_events or [])
        now = time.time()

        if not context_features:
            activated_all = []
            for exp, sig in zip(self.experiences, self.signatures):
                exp.last_activated = now
                exp.activation_energy = self._clamp(max(self._safe_float(exp.activation_energy, 0.0), sig.activation_weight))
                sig.activation_weight = self._safe_float(exp.activation_energy, sig.activation_weight)
                activated_all.append(exp)
            return activated_all

        query_drive = self._build_drive_vector(intensity=1.0)
        query_tokens = self._build_context_tokens(context_features)
        query_context = self._encode_context_vector(
            context_features,
            query_drive,
            now,
            context_tokens=query_tokens,
        )

        matches = []
        for exp, sig in zip(self.experiences, self.signatures):
            similarity = self._composite_similarity(context_features, query_drive, query_context, query_tokens, sig)
            if similarity >= self.activation_similarity_threshold:
                exp.last_activated = now
                exp.activation_energy = self._clamp(max(self._safe_float(exp.activation_energy, 0.0), similarity))
                sig.activation_weight = self._safe_float(exp.activation_energy, sig.activation_weight)
                matches.append((similarity, exp))

        if not matches:
            for exp, sig in sorted(
                zip(self.experiences, self.signatures),
                key=lambda item: self._jaccard_similarity(context_features, item[1].feature_set),
                reverse=True,
            ):
                similarity = self._jaccard_similarity(context_features, sig.feature_set)
                if similarity <= 0.0:
                    continue
                exp.last_activated = now
                exp.activation_energy = self._clamp(max(self._safe_float(exp.activation_energy, 0.0), similarity))
                sig.activation_weight = self._safe_float(exp.activation_energy, sig.activation_weight)
                matches.append((similarity, exp))
                if len(matches) >= self.top_k_recall:
                    break

        matches.sort(key=lambda item: item[0], reverse=True)
        return [exp for _, exp in matches]

    def _novelty_from_recent(
        self,
        query_features: Set[str],
        exclude_signature: Optional[SignatureTrace] = None,
    ) -> float:
        recent = self.signatures[-self.novelty_window :]
        if not recent:
            return 1.0
        max_similarity = 0.0
        any_compared = False
        for sig in recent:
            if exclude_signature is not None and sig is exclude_signature:
                continue
            any_compared = True
            max_similarity = max(max_similarity, self._jaccard_similarity(query_features, sig.feature_set))
        if not any_compared:
            base = 1.0
        else:
            base = self._clamp(1.0 - max_similarity)
        scaled = base * self.get_novelty_sensitivity_scale()
        return self._clamp(scaled)

    def _reconstruct_features(self, top_k_entries: List[Tuple[float, SignatureTrace]]) -> Set[str]:
        if not top_k_entries:
            return set()

        total = sum(max(0.0, sim) for sim, _ in top_k_entries)
        if total <= 0.0:
            return set()

        weighted_scores: Dict[str, float] = {}
        for similarity, sig in top_k_entries:
            weight = max(0.0, similarity) / total
            for feature in sig.feature_set:
                weighted_scores[feature] = weighted_scores.get(feature, 0.0) + weight

        if not weighted_scores:
            return set()

        max_score = max(weighted_scores.values())
        adaptive_threshold = self._clamp(0.50 * max_score, 0.05, 0.45)
        reconstructed = {feature for feature, score in weighted_scores.items() if score >= adaptive_threshold}
        if reconstructed:
            return reconstructed

        best_feature = max(weighted_scores.items(), key=lambda item: item[1])[0]
        return {best_feature}

    def classify_novelty(self, novelty_score: float) -> str:
        score = self._clamp(novelty_score)
        if score < 0.2:
            return "familiar"
        if score <= 0.6:
            return "partial_match"
        if score <= 0.85:
            return "novel"
        return "high_novelty"

    def recall_signature(self, current_signature) -> dict:
        self._ensure_signature_store()
        self._apply_decay()

        query_features, query_drive, query_context, _, query_tokens = self._build_query_signature(current_signature)
        similarity_entries: List[Tuple[float, SignatureTrace]] = []
        for sig in self.signatures:
            sim = self._composite_similarity(query_features, query_drive, query_context, query_tokens, sig)
            if sim > 0.0:
                similarity_entries.append((sim, sig))

        similarity_entries.sort(key=lambda item: item[0], reverse=True)
        top_k = similarity_entries[: self.top_k_recall]
        reconstructed = self._reconstruct_features(top_k)
        novelty = self._novelty_from_recent(query_features)

        self._novelty_history.append(novelty)
        if len(self._novelty_history) > 500:
            self._novelty_history = self._novelty_history[-500:]

        similarity_payload = []
        for similarity, sig in top_k:
            similarity_payload.append(
                {
                    "similarity": float(similarity),
                    "features": set(sig.feature_set),
                    "timestamp": float(sig.timestamp),
                    "repetition_count": int(sig.repetition_count),
                }
            )

        return {
            "reconstructed_features": reconstructed,
            "novelty_score": float(novelty),
            "novelty_class": self.classify_novelty(novelty),
            "similarity_top_k": similarity_payload,
        }

    def recall_recent(self, limit: Optional[int] = None) -> list:
        self._ensure_signature_store()
        self._apply_decay()
        k = max(1, int(limit or self.top_k_recall))
        return list(self.experiences)[-k:]

    def recall(self, current_signature=None, *, active_drive=None, limit: Optional[int] = None):
        """
        Backward-compatible dispatcher.

        Preferred explicit APIs:
        - recall_signature(signature_query)
        - recall_recent(limit)
        - recall_by_drive(active_drive, limit)
        """
        if isinstance(current_signature, int) and active_drive is None and limit is None:
            return self.recall_recent(limit=int(current_signature))

        if active_drive is not None and current_signature is None:
            return self.recall_by_drive(active_drive=active_drive, limit=int(limit or self.top_k_recall))

        if current_signature is None:
            return self.recall_recent(limit=limit)

        return self.recall_signature(current_signature)

    def recall_by_drive(self, active_drive: str, limit: int = 6) -> list:
        self._ensure_signature_store()
        self._apply_decay()

        token = str(active_drive or "").strip()
        k = max(1, int(limit))
        if not token:
            return list(self.experiences)[-k:]

        scored = []
        for exp, sig in zip(self.experiences, self.signatures):
            score = 1.0 if any(token in feature for feature in sig.feature_set) else 0.0
            if score <= 0.0:
                score = self._jaccard_similarity({token}, sig.feature_set)
            if score > 0.0:
                scored.append((score, exp))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [exp for _, exp in scored[:k]]

    def consolidation_probability(
        self, novelty_score: float, repetition_count: int, reward_signal: float = 0.0
    ) -> float:
        novelty = self._clamp(novelty_score)
        repetition_factor = self._clamp(float(max(0, int(repetition_count))) / 5.0)
        reward_norm = self._clamp((self._safe_float(reward_signal, 0.0) + 1.0) / 2.0)
        reward_weight = 0.4 + (0.6 * reward_norm)
        probability = (novelty * reward_weight) + (0.35 * repetition_factor)
        return self._clamp(probability)

    def get_candidates_for_sleep(self, min_reinforcement: int = 2) -> list:
        self._ensure_signature_store()
        self._apply_decay()

        candidates = []
        for exp, sig in zip(self.experiences, self.signatures):
            reinforcement = int(getattr(exp, "reinforcement_count", 1))
            activation = self._safe_float(getattr(exp, "activation_energy", 0.0), 0.0)
            stability = self._safe_float(getattr(exp, "stability", 0.0), 0.0)
            novelty = self._novelty_from_recent(sig.feature_set, exclude_signature=sig)
            probability = self.consolidation_probability(
                novelty_score=novelty,
                repetition_count=reinforcement,
                reward_signal=self._safe_float(getattr(exp, "reward", 0.0), 0.0),
            )
            exp.novelty_score = novelty
            exp.consolidation_probability = probability

            if (
                reinforcement >= int(min_reinforcement)
                and activation > 0.5
                and stability < 1.0
                and probability >= self.consolidation_min_probability
            ):
                candidates.append((reinforcement, activation, probability, exp))

        candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [item[3] for item in candidates]

    def get_statistics(self) -> dict:
        self._ensure_signature_store()
        self._apply_decay()

        if not self.experiences:
            return {
                "total_experiences": 0,
                "avg_reinforcement": 0,
                "avg_activation": 0,
                "avg_stability": 0,
                "total_signatures": 0,
                "avg_novelty_recent": 0,
                "familiar_ratio": 0,
                "partial_match_ratio": 0,
                "novel_ratio": 0,
                "high_novelty_ratio": 0,
            }

        total = len(self.experiences)
        novelties = [
            self._novelty_from_recent(sig.feature_set, exclude_signature=sig)
            for sig in self.signatures[-self.novelty_window :]
        ]
        if not novelties:
            novelties = [0.0]

        familiar = 0
        partial = 0
        novel = 0
        high_novel = 0
        for score in novelties:
            label = self.classify_novelty(score)
            if label == "familiar":
                familiar += 1
            elif label == "partial_match":
                partial += 1
            elif label == "novel":
                novel += 1
            else:
                high_novel += 1

        denom = float(len(novelties))
        return {
            "total_experiences": total,
            "avg_reinforcement": sum(e.reinforcement_count for e in self.experiences) / total,
            "avg_activation": sum(self._safe_float(e.activation_energy, 0.0) for e in self.experiences) / total,
            "avg_stability": sum(self._safe_float(e.stability, 0.0) for e in self.experiences) / total,
            "total_signatures": len(self.signatures),
            "avg_novelty_recent": sum(novelties) / denom,
            "familiar_ratio": familiar / denom,
            "partial_match_ratio": partial / denom,
            "novel_ratio": novel / denom,
            "high_novelty_ratio": high_novel / denom,
        }
