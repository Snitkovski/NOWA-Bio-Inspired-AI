"""
Epigenome snapshot for package B (inherited consolidated memory).

This module is intentionally self-contained and does not import NOWA runtime
modules. It accepts and emits plain dictionaries for extraction/injection.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import time
import warnings
from typing import Dict, List, Tuple

EPIGENOME_VERSION = "1.0"

MAX_PATTERNS = 32
MAX_ACTIONS = 16
MAX_VALUES = 24

PATTERN_STRENGTH_RANGE = (0.0, 1.0)
ACTION_CONFIDENCE_RANGE = (0.0, 1.0)
ACTION_STABILITY_RANGE = (0.0, 1.0)
ACTION_SUCCESS_RANGE = (0.0, 1.0)
VALUE_RANGE = (-1.0, 1.0)
VALUE_CONFIDENCE_RANGE = (0.0, 1.0)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _safe_float(value, default: float = 0.0) -> float:
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(casted) or math.isinf(casted):
        return default
    return casted


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float_strict(value) -> Tuple[bool, float]:
    try:
        casted = float(value)
    except (TypeError, ValueError):
        return False, 0.0
    if math.isnan(casted) or math.isinf(casted):
        return False, 0.0
    return True, casted


def _parse_int_strict(value) -> Tuple[bool, int]:
    try:
        casted = int(value)
    except (TypeError, ValueError):
        return False, 0
    return True, casted


def _clamp_limit(value: int, fallback: int) -> int:
    numeric = _safe_int(value, fallback)
    return max(1, min(256, numeric))


@dataclass(frozen=True)
class InheritedPattern:
    context_signature: str
    action: str
    strength: float
    reinforcement_count: int


@dataclass(frozen=True)
class InheritedAction:
    action_id: str
    predicted_effect: Dict[str, float]
    semantic_confidence: float
    stability_score: float
    success_rate: float


@dataclass(frozen=True)
class InheritedValue:
    state_key: str
    value: float
    confidence: float
    confirmation_count: float


@dataclass(frozen=True)
class EpigenomeSnapshot:
    patterns: Tuple[InheritedPattern, ...]
    actions: Tuple[InheritedAction, ...]
    values: Tuple[InheritedValue, ...]
    source_generation: int = 0
    source_lineage_id: str = ""
    extraction_timestamp: float = 0.0

    def __post_init__(self):
        object.__setattr__(
            self,
            "patterns",
            tuple(item for item in self.patterns if isinstance(item, InheritedPattern))[:MAX_PATTERNS],
        )
        object.__setattr__(
            self,
            "actions",
            tuple(item for item in self.actions if isinstance(item, InheritedAction))[:MAX_ACTIONS],
        )
        object.__setattr__(
            self,
            "values",
            tuple(item for item in self.values if isinstance(item, InheritedValue))[:MAX_VALUES],
        )
        object.__setattr__(self, "source_generation", max(0, _safe_int(self.source_generation, 0)))
        object.__setattr__(self, "source_lineage_id", str(self.source_lineage_id))
        object.__setattr__(self, "extraction_timestamp", _safe_float(self.extraction_timestamp, 0.0))

    @classmethod
    def extract(
        cls,
        cortex_patterns: List[dict],
        action_metadata: Dict[str, dict],
        value_profiles: Dict[str, dict],
        source_generation: int = 0,
        source_lineage_id: str = "",
        max_patterns: int = 32,
        max_actions: int = 16,
        max_values: int = 24,
        min_reinforcement: int = 2,
        min_stability: float = 0.5,
        min_confirmation: float = 1.0,
    ) -> "EpigenomeSnapshot":
        capped_patterns = _clamp_limit(max_patterns, MAX_PATTERNS)
        capped_actions = _clamp_limit(max_actions, MAX_ACTIONS)
        capped_values = _clamp_limit(max_values, MAX_VALUES)

        min_reinf = _safe_int(min_reinforcement, 2)
        min_stab = _safe_float(min_stability, 0.5)
        min_confirm = _safe_float(min_confirmation, 1.0)

        extracted_patterns: List[InheritedPattern] = []
        pattern_source = cortex_patterns if isinstance(cortex_patterns, list) else []
        for row in pattern_source:
            if not isinstance(row, dict):
                continue

            context_signature = row.get("context_signature")
            action = row.get("action")
            if not isinstance(context_signature, str) or not isinstance(action, str):
                continue

            ok_strength, strength_raw = _parse_float_strict(row.get("strength"))
            ok_reinf, reinforcement = _parse_int_strict(row.get("reinforcement_count"))
            if not ok_strength or not ok_reinf:
                continue

            if reinforcement < min_reinf:
                continue

            extracted_patterns.append(
                InheritedPattern(
                    context_signature=context_signature,
                    action=action,
                    strength=_clamp(strength_raw, *PATTERN_STRENGTH_RANGE),
                    reinforcement_count=reinforcement,
                )
            )

        extracted_patterns.sort(
            key=lambda item: (
                item.reinforcement_count,
                item.strength,
                item.context_signature,
                item.action,
            ),
            reverse=True,
        )
        extracted_patterns = extracted_patterns[:capped_patterns]

        extracted_actions: List[InheritedAction] = []
        if isinstance(action_metadata, dict):
            for action_id, metadata in action_metadata.items():
                if not isinstance(action_id, str) or not isinstance(metadata, dict):
                    continue
                if metadata.get("consolidated") is not True:
                    continue

                ok_sem, semantic_raw = _parse_float_strict(metadata.get("semantic_confidence"))
                ok_stab, stability_raw = _parse_float_strict(metadata.get("stability_score"))
                ok_succ, success_raw = _parse_float_strict(metadata.get("success_rate"))
                if not ok_sem or not ok_stab or not ok_succ:
                    continue

                stability = _clamp(stability_raw, *ACTION_STABILITY_RANGE)
                if stability < min_stab:
                    continue

                predicted_effect_raw = metadata.get("predicted_effect", {})
                predicted_effect: Dict[str, float] = {}
                if isinstance(predicted_effect_raw, dict):
                    for key, value in predicted_effect_raw.items():
                        if not isinstance(key, str):
                            continue
                        ok_effect, effect_val = _parse_float_strict(value)
                        if not ok_effect:
                            continue
                        predicted_effect[key] = effect_val

                extracted_actions.append(
                    InheritedAction(
                        action_id=action_id,
                        predicted_effect=predicted_effect,
                        semantic_confidence=_clamp(semantic_raw, *ACTION_CONFIDENCE_RANGE),
                        stability_score=stability,
                        success_rate=_clamp(success_raw, *ACTION_SUCCESS_RANGE),
                    )
                )

        extracted_actions.sort(
            key=lambda item: (item.stability_score, item.semantic_confidence, item.action_id),
            reverse=True,
        )
        extracted_actions = extracted_actions[:capped_actions]

        extracted_values: List[InheritedValue] = []
        if isinstance(value_profiles, dict):
            for state_key, profile in value_profiles.items():
                if not isinstance(state_key, str) or not isinstance(profile, dict):
                    continue

                ok_value, value_raw = _parse_float_strict(profile.get("value"))
                ok_conf, confidence_raw = _parse_float_strict(profile.get("confidence"))
                ok_count, confirmation_raw = _parse_float_strict(profile.get("confirmation_count"))
                if not ok_value or not ok_conf or not ok_count:
                    continue

                if confirmation_raw < min_confirm:
                    continue

                extracted_values.append(
                    InheritedValue(
                        state_key=state_key,
                        value=_clamp(value_raw, *VALUE_RANGE),
                        confidence=_clamp(confidence_raw, *VALUE_CONFIDENCE_RANGE),
                        confirmation_count=confirmation_raw,
                    )
                )

        extracted_values.sort(
            key=lambda item: (item.confirmation_count, item.confidence, item.state_key),
            reverse=True,
        )
        extracted_values = extracted_values[:capped_values]

        return cls(
            patterns=tuple(extracted_patterns),
            actions=tuple(extracted_actions),
            values=tuple(extracted_values),
            source_generation=max(0, _safe_int(source_generation, 0)),
            source_lineage_id=str(source_lineage_id),
            extraction_timestamp=time.time(),
        )

    def inject(
        self,
        target_cortex_patterns: list,
        target_action_metadata: dict,
        target_value_profiles: dict,
        noise_level: float = 0.1,
        rng: random.Random = None,
    ) -> dict:
        noise = _clamp(_safe_float(noise_level, 0.1), 0.0, 1.0)
        generator = rng if rng is not None else random.Random()

        stats = {
            "patterns_injected": 0,
            "patterns_skipped": 0,
            "actions_injected": 0,
            "actions_skipped": 0,
            "values_injected": 0,
            "values_skipped": 0,
            "noise_level": noise,
        }

        if isinstance(target_cortex_patterns, list):
            existing_indices: Dict[str, int] = {}
            for idx, row in enumerate(target_cortex_patterns):
                if not isinstance(row, dict):
                    continue
                context_signature = row.get("context_signature")
                if isinstance(context_signature, str) and context_signature not in existing_indices:
                    existing_indices[context_signature] = idx

            for pattern in self.patterns:
                strength = pattern.strength
                if noise > 0.0:
                    strength += generator.gauss(0.0, noise * 0.1)
                noisy_strength = _clamp(strength, *PATTERN_STRENGTH_RANGE)

                inherited = {
                    "context_signature": pattern.context_signature,
                    "action": pattern.action,
                    "strength": noisy_strength,
                    "reinforcement_count": int(pattern.reinforcement_count),
                }

                existing_idx = existing_indices.get(pattern.context_signature)
                if existing_idx is None:
                    target_cortex_patterns.append(inherited)
                    existing_indices[pattern.context_signature] = len(target_cortex_patterns) - 1
                    stats["patterns_injected"] += 1
                    continue

                existing = target_cortex_patterns[existing_idx]
                if not isinstance(existing, dict):
                    target_cortex_patterns[existing_idx] = inherited
                    stats["patterns_injected"] += 1
                    continue

                existing_strength = _safe_float(existing.get("strength"), -1.0)
                if noisy_strength > existing_strength:
                    target_cortex_patterns[existing_idx] = inherited
                    stats["patterns_injected"] += 1
                else:
                    stats["patterns_skipped"] += 1

        if isinstance(target_action_metadata, dict):
            for action in self.actions:
                if action.action_id in target_action_metadata:
                    stats["actions_skipped"] += 1
                    continue

                semantic_confidence = action.semantic_confidence
                if noise > 0.0:
                    semantic_confidence *= 1.0 - (noise * generator.uniform(0.0, 0.5))
                semantic_confidence = _clamp(semantic_confidence, *ACTION_CONFIDENCE_RANGE)

                target_action_metadata[action.action_id] = {
                    "predicted_effect": dict(action.predicted_effect),
                    "semantic_confidence": semantic_confidence,
                    "stability_score": _clamp(action.stability_score, *ACTION_STABILITY_RANGE),
                    "success_rate": _clamp(action.success_rate, *ACTION_SUCCESS_RANGE),
                    "consolidated": True,
                }
                stats["actions_injected"] += 1

        if isinstance(target_value_profiles, dict):
            for profile in self.values:
                if profile.state_key in target_value_profiles:
                    stats["values_skipped"] += 1
                    continue

                value = profile.value
                confidence = profile.confidence
                if noise > 0.0:
                    value += generator.gauss(0.0, noise * 0.2)
                    confidence *= 1.0 - (noise * generator.uniform(0.0, 0.5))

                target_value_profiles[profile.state_key] = {
                    "value": _clamp(value, *VALUE_RANGE),
                    "confidence": _clamp(confidence, *VALUE_CONFIDENCE_RANGE),
                    "confirmation_count": _safe_float(profile.confirmation_count, 0.0),
                }
                stats["values_injected"] += 1

        return stats

    def blend(
        self,
        other: "EpigenomeSnapshot",
        alpha: float = 0.5,
        rng: random.Random = None,
    ) -> "EpigenomeSnapshot":
        del rng  # Reserved for future modes in spec.

        if not isinstance(other, EpigenomeSnapshot):
            other = EpigenomeSnapshot.empty()

        blend_alpha = _clamp(_safe_float(alpha, 0.5), 0.0, 1.0)

        def _normalized_pattern(item: InheritedPattern) -> InheritedPattern:
            return InheritedPattern(
                context_signature=str(item.context_signature),
                action=str(item.action),
                strength=_clamp(_safe_float(item.strength, 0.0), *PATTERN_STRENGTH_RANGE),
                reinforcement_count=max(0, _safe_int(item.reinforcement_count, 0)),
            )

        def _normalized_action(item: InheritedAction) -> InheritedAction:
            normalized_effect: Dict[str, float] = {}
            if isinstance(item.predicted_effect, dict):
                for key, value in item.predicted_effect.items():
                    if not isinstance(key, str):
                        continue
                    ok_value, parsed_value = _parse_float_strict(value)
                    if not ok_value:
                        continue
                    normalized_effect[key] = parsed_value
            return InheritedAction(
                action_id=str(item.action_id),
                predicted_effect=normalized_effect,
                semantic_confidence=_clamp(
                    _safe_float(item.semantic_confidence, 0.0),
                    *ACTION_CONFIDENCE_RANGE,
                ),
                stability_score=_clamp(
                    _safe_float(item.stability_score, 0.0),
                    *ACTION_STABILITY_RANGE,
                ),
                success_rate=_clamp(
                    _safe_float(item.success_rate, 0.0),
                    *ACTION_SUCCESS_RANGE,
                ),
            )

        def _normalized_value(item: InheritedValue) -> InheritedValue:
            return InheritedValue(
                state_key=str(item.state_key),
                value=_clamp(_safe_float(item.value, 0.0), *VALUE_RANGE),
                confidence=_clamp(_safe_float(item.confidence, 0.0), *VALUE_CONFIDENCE_RANGE),
                confirmation_count=max(0.0, _safe_float(item.confirmation_count, 0.0)),
            )

        pattern_map: Dict[str, InheritedPattern] = {}
        for item in list(self.patterns) + list(other.patterns):
            normalized = _normalized_pattern(item)
            existing = pattern_map.get(normalized.context_signature)
            if existing is None or normalized.strength > existing.strength:
                pattern_map[normalized.context_signature] = normalized

        blended_patterns = sorted(
            pattern_map.values(),
            key=lambda item: (item.strength, item.reinforcement_count, item.context_signature),
            reverse=True,
        )[:MAX_PATTERNS]

        action_map: Dict[str, InheritedAction] = {}
        for item in list(self.actions) + list(other.actions):
            normalized = _normalized_action(item)
            existing = action_map.get(normalized.action_id)
            if existing is None or normalized.stability_score > existing.stability_score:
                action_map[normalized.action_id] = normalized

        blended_actions = sorted(
            action_map.values(),
            key=lambda item: (item.stability_score, item.semantic_confidence, item.action_id),
            reverse=True,
        )[:MAX_ACTIONS]

        value_map: Dict[str, InheritedValue] = {}
        for item in self.values:
            normalized = _normalized_value(item)
            value_map[normalized.state_key] = normalized
        for incoming in other.values:
            normalized_incoming = _normalized_value(incoming)
            existing = value_map.get(normalized_incoming.state_key)
            if existing is None:
                value_map[normalized_incoming.state_key] = normalized_incoming
                continue

            mixed_value = _clamp(
                (blend_alpha * existing.value) + ((1.0 - blend_alpha) * normalized_incoming.value),
                *VALUE_RANGE,
            )
            mixed_confidence = _clamp(
                min(existing.confidence, normalized_incoming.confidence),
                *VALUE_CONFIDENCE_RANGE,
            )
            value_map[normalized_incoming.state_key] = InheritedValue(
                state_key=normalized_incoming.state_key,
                value=mixed_value,
                confidence=mixed_confidence,
                confirmation_count=max(existing.confirmation_count, normalized_incoming.confirmation_count),
            )

        blended_values = sorted(
            value_map.values(),
            key=lambda item: (item.confirmation_count, item.confidence, item.state_key),
            reverse=True,
        )[:MAX_VALUES]

        lineage = f"{self.source_lineage_id}+{other.source_lineage_id}"[:64]

        return EpigenomeSnapshot(
            patterns=tuple(blended_patterns),
            actions=tuple(blended_actions),
            values=tuple(blended_values),
            source_generation=max(self.source_generation, other.source_generation),
            source_lineage_id=lineage,
            extraction_timestamp=time.time(),
        )

    def to_dict(self) -> dict:
        ordered_patterns = sorted(
            self.patterns,
            key=lambda item: (item.strength, item.reinforcement_count, item.context_signature),
            reverse=True,
        )
        ordered_actions = sorted(
            self.actions,
            key=lambda item: (item.stability_score, item.semantic_confidence, item.action_id),
            reverse=True,
        )
        ordered_values = sorted(
            self.values,
            key=lambda item: (item.confirmation_count, item.confidence, item.state_key),
            reverse=True,
        )

        return {
            "version": EPIGENOME_VERSION,
            "source_generation": int(self.source_generation),
            "source_lineage_id": self.source_lineage_id,
            "extraction_timestamp": _safe_float(self.extraction_timestamp, 0.0),
            "patterns": [
                {
                    "context_signature": item.context_signature,
                    "action": item.action,
                    "strength": item.strength,
                    "reinforcement_count": int(item.reinforcement_count),
                }
                for item in ordered_patterns
            ],
            "actions": [
                {
                    "action_id": item.action_id,
                    "predicted_effect": dict(item.predicted_effect),
                    "semantic_confidence": item.semantic_confidence,
                    "stability_score": item.stability_score,
                    "success_rate": item.success_rate,
                }
                for item in ordered_actions
            ],
            "values": [
                {
                    "state_key": item.state_key,
                    "value": item.value,
                    "confidence": item.confidence,
                    "confirmation_count": item.confirmation_count,
                }
                for item in ordered_values
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EpigenomeSnapshot":
        raw = data if isinstance(data, dict) else {}

        generation = _safe_int(raw.get("source_generation", 0), 0)
        if generation < 0:
            generation = 0
        source_lineage_id = str(raw.get("source_lineage_id", ""))
        extraction_timestamp = _safe_float(raw.get("extraction_timestamp", 0.0), 0.0)

        parsed_patterns: List[InheritedPattern] = []
        for row in raw.get("patterns", []) or []:
            if not isinstance(row, dict):
                warnings.warn("Skipping non-dict pattern record in epigenome.", RuntimeWarning, stacklevel=2)
                continue

            context_signature = row.get("context_signature", "")
            action = row.get("action", "")
            if not isinstance(context_signature, str) or not isinstance(action, str):
                warnings.warn("Skipping malformed pattern record in epigenome.", RuntimeWarning, stacklevel=2)
                continue

            if "strength" in row:
                ok_strength, strength = _parse_float_strict(row.get("strength"))
            else:
                ok_strength, strength = True, 0.0

            if "reinforcement_count" in row:
                ok_reinf, reinforcement_count = _parse_int_strict(row.get("reinforcement_count"))
            else:
                ok_reinf, reinforcement_count = True, 0

            if not ok_strength or not ok_reinf:
                warnings.warn("Skipping malformed pattern numeric fields.", RuntimeWarning, stacklevel=2)
                continue

            parsed_patterns.append(
                InheritedPattern(
                    context_signature=context_signature,
                    action=action,
                    strength=strength,
                    reinforcement_count=reinforcement_count,
                )
            )

        parsed_actions: List[InheritedAction] = []
        for row in raw.get("actions", []) or []:
            if not isinstance(row, dict):
                warnings.warn("Skipping non-dict action record in epigenome.", RuntimeWarning, stacklevel=2)
                continue

            action_id = row.get("action_id", "")
            if not isinstance(action_id, str):
                warnings.warn("Skipping malformed action record in epigenome.", RuntimeWarning, stacklevel=2)
                continue

            predicted_effect: Dict[str, float] = {}
            predicted_effect_raw = row.get("predicted_effect", {})
            if isinstance(predicted_effect_raw, dict):
                for key, value in predicted_effect_raw.items():
                    if not isinstance(key, str):
                        continue
                    ok_effect, effect_value = _parse_float_strict(value)
                    if not ok_effect:
                        continue
                    predicted_effect[key] = effect_value

            if "semantic_confidence" in row:
                ok_sem, semantic_confidence = _parse_float_strict(row.get("semantic_confidence"))
            else:
                ok_sem, semantic_confidence = True, 0.0

            if "stability_score" in row:
                ok_stab, stability_score = _parse_float_strict(row.get("stability_score"))
            else:
                ok_stab, stability_score = True, 0.0

            if "success_rate" in row:
                ok_succ, success_rate = _parse_float_strict(row.get("success_rate"))
            else:
                ok_succ, success_rate = True, 0.0

            if not (ok_sem and ok_stab and ok_succ):
                warnings.warn("Skipping malformed action numeric fields.", RuntimeWarning, stacklevel=2)
                continue

            parsed_actions.append(
                InheritedAction(
                    action_id=action_id,
                    predicted_effect=predicted_effect,
                    semantic_confidence=semantic_confidence,
                    stability_score=stability_score,
                    success_rate=success_rate,
                )
            )

        parsed_values: List[InheritedValue] = []
        for row in raw.get("values", []) or []:
            if not isinstance(row, dict):
                warnings.warn("Skipping non-dict value record in epigenome.", RuntimeWarning, stacklevel=2)
                continue

            state_key = row.get("state_key", "")
            if not isinstance(state_key, str):
                warnings.warn("Skipping malformed value record in epigenome.", RuntimeWarning, stacklevel=2)
                continue

            if "value" in row:
                ok_val, value = _parse_float_strict(row.get("value"))
            else:
                ok_val, value = True, 0.0

            if "confidence" in row:
                ok_conf, confidence = _parse_float_strict(row.get("confidence"))
            else:
                ok_conf, confidence = True, 0.0

            if "confirmation_count" in row:
                ok_count, confirmation_count = _parse_float_strict(row.get("confirmation_count"))
            else:
                ok_count, confirmation_count = True, 0.0

            if not (ok_val and ok_conf and ok_count):
                warnings.warn("Skipping malformed value numeric fields.", RuntimeWarning, stacklevel=2)
                continue

            parsed_values.append(
                InheritedValue(
                    state_key=state_key,
                    value=value,
                    confidence=confidence,
                    confirmation_count=confirmation_count,
                )
            )

        return cls(
            patterns=tuple(parsed_patterns[:MAX_PATTERNS]),
            actions=tuple(parsed_actions[:MAX_ACTIONS]),
            values=tuple(parsed_values[:MAX_VALUES]),
            source_generation=generation,
            source_lineage_id=source_lineage_id,
            extraction_timestamp=extraction_timestamp,
        )

    @classmethod
    def empty(cls) -> "EpigenomeSnapshot":
        return cls(
            patterns=(),
            actions=(),
            values=(),
            source_generation=0,
            source_lineage_id="",
            extraction_timestamp=0.0,
        )

    def is_empty(self) -> bool:
        return not self.patterns and not self.actions and not self.values

    def size(self) -> dict:
        return {
            "patterns": len(self.patterns),
            "actions": len(self.actions),
            "values": len(self.values),
            "total": len(self.patterns) + len(self.actions) + len(self.values),
        }

    def validate(self) -> List[str]:
        issues: List[str] = []

        if self.source_generation < 0:
            issues.append("source_generation must be non-negative")

        if len(self.patterns) > MAX_PATTERNS:
            issues.append(f"patterns exceed MAX_PATTERNS={MAX_PATTERNS}")
        if len(self.actions) > MAX_ACTIONS:
            issues.append(f"actions exceed MAX_ACTIONS={MAX_ACTIONS}")
        if len(self.values) > MAX_VALUES:
            issues.append(f"values exceed MAX_VALUES={MAX_VALUES}")

        seen_pattern_keys = set()
        for pattern in self.patterns:
            if pattern.context_signature in seen_pattern_keys:
                issues.append(f"Duplicate pattern key: {pattern.context_signature}")
            seen_pattern_keys.add(pattern.context_signature)

            if not math.isfinite(pattern.strength):
                issues.append(f"Pattern '{pattern.context_signature}' has non-finite strength")
            elif pattern.strength < PATTERN_STRENGTH_RANGE[0] or pattern.strength > PATTERN_STRENGTH_RANGE[1]:
                issues.append(
                    f"Pattern '{pattern.context_signature}' strength out of range: {pattern.strength}"
                )
            if pattern.reinforcement_count < 0:
                issues.append(
                    f"Pattern '{pattern.context_signature}' has negative reinforcement_count"
                )

        seen_action_keys = set()
        for action in self.actions:
            if action.action_id in seen_action_keys:
                issues.append(f"Duplicate action key: {action.action_id}")
            seen_action_keys.add(action.action_id)

            for field_name, value, value_range in [
                ("semantic_confidence", action.semantic_confidence, ACTION_CONFIDENCE_RANGE),
                ("stability_score", action.stability_score, ACTION_STABILITY_RANGE),
                ("success_rate", action.success_rate, ACTION_SUCCESS_RANGE),
            ]:
                if not math.isfinite(value):
                    issues.append(f"Action '{action.action_id}' has non-finite {field_name}")
                    continue
                if value < value_range[0] or value > value_range[1]:
                    issues.append(f"Action '{action.action_id}' {field_name} out of range: {value}")

        seen_value_keys = set()
        for value_item in self.values:
            if value_item.state_key in seen_value_keys:
                issues.append(f"Duplicate value key: {value_item.state_key}")
            seen_value_keys.add(value_item.state_key)

            if not math.isfinite(value_item.value):
                issues.append(f"Value '{value_item.state_key}' has non-finite value")
            elif value_item.value < VALUE_RANGE[0] or value_item.value > VALUE_RANGE[1]:
                issues.append(f"Value '{value_item.state_key}' out of range: {value_item.value}")

            if not math.isfinite(value_item.confidence):
                issues.append(f"Value '{value_item.state_key}' has non-finite confidence")
            elif (
                value_item.confidence < VALUE_CONFIDENCE_RANGE[0]
                or value_item.confidence > VALUE_CONFIDENCE_RANGE[1]
            ):
                issues.append(
                    f"Value '{value_item.state_key}' confidence out of range: {value_item.confidence}"
                )

            if not math.isfinite(value_item.confirmation_count):
                issues.append(
                    f"Value '{value_item.state_key}' has non-finite confirmation_count"
                )
            elif value_item.confirmation_count < 0.0:
                issues.append(
                    f"Value '{value_item.state_key}' confirmation_count is negative"
                )

        return issues

    def summary(self) -> dict:
        pattern_mean = (
            sum(item.strength for item in self.patterns) / len(self.patterns)
            if self.patterns
            else 0.0
        )
        action_mean = (
            sum(item.stability_score for item in self.actions) / len(self.actions)
            if self.actions
            else 0.0
        )
        value_mean = (
            sum(item.confidence for item in self.values) / len(self.values)
            if self.values
            else 0.0
        )

        return {
            "patterns_count": len(self.patterns),
            "actions_count": len(self.actions),
            "values_count": len(self.values),
            "mean_pattern_strength": pattern_mean,
            "mean_action_stability": action_mean,
            "mean_value_confidence": value_mean,
            "source_generation": int(self.source_generation),
        }
