"""Validation orchestration and correlation metrics for Warriner benchmarks."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from ._common import (
    compute_ccc_values,
    load_warriner_csv,
    mean,
    normalize_warriner_records,
    pearson_r,
    population_sd,
    row_word,
    spearman_rho,
    stratified_bins,
    stratified_sample,
)
from .nowa_colony import ARCHETYPES, ColonyResponse, NOWAColony
from .word_stimulus_encoder import WordStimulusEncoder


@dataclass
class ValidationResult:
    n_words: int
    encoder_mode: str
    spearman_rho_valence: float
    spearman_p_valence: float
    pearson_r_valence: float
    ccc_valence: float
    spearman_rho_arousal: float
    spearman_p_arousal: float
    archetype_correlations: Dict[str, float]
    archetype_n_agents: Dict[str, int]
    sd_nowa_valence: float
    sd_human_valence: float
    sd_ratio: float
    mean_activated_memories: float
    zero_activation_ratio: float
    words: List[str]
    warriner_valence_norm: List[float]
    nowa_valence_shifts: List[float]
    warriner_arousal_norm: List[float]
    nowa_arousal_shifts: List[float]
    colony_responses: List[ColonyResponse]
    spearman_rho_da_valence: float = 0.0
    spearman_rho_cortisol_valence: float = 0.0

    def summary(self) -> str:
        if self.spearman_rho_valence >= 0.6:
            status = "STRONG SIGNAL"
        elif self.spearman_rho_valence >= 0.4:
            status = "PROOF OF LIFE"
        elif self.spearman_rho_valence >= 0.2:
            status = "WEAK SIGNAL"
        else:
            status = "NO SIGNAL"
        collapse = "OK" if self.sd_ratio >= 0.1 else "COLLAPSE WARNING"
        return (
            "=== NOWA x Warriner Validation ===\n"
            f"Words tested: {self.n_words}\n"
            f"Encoder: {self.encoder_mode}\n\n"
            "VALENCE:\n"
            f"  Spearman rho = {self.spearman_rho_valence:.3f}  "
            f"(p = {self.spearman_p_valence:.3e})\n"
            f"  Pearson r    = {self.pearson_r_valence:.3f}\n"
            f"  CCC          = {self.ccc_valence:.3f}\n"
            f"  {status}\n\n"
            "AROUSAL:\n"
            f"  Spearman rho = {self.spearman_rho_arousal:.3f}  "
            f"(p = {self.spearman_p_arousal:.3e})\n\n"
            "VARIANCE CHECK:\n"
            f"  SD(human) = {self.sd_human_valence:.3f}\n"
            f"  SD(NOWA)  = {self.sd_nowa_valence:.3f}\n"
            f"  Ratio     = {self.sd_ratio:.3f}  [{collapse}]\n\n"
            "MEMORY DIAGNOSTICS:\n"
            f"  Mean activated memories per word: {self.mean_activated_memories:.2f}\n"
            f"  Zero-activation words: {self.zero_activation_ratio * 100.0:.1f}%\n\n"
            "NEUROMODULATOR CHECK:\n"
            f"  Spearman rho(DA, V)       = {self.spearman_rho_da_valence:.3f}\n"
            f"  Spearman rho(Cortisol, V) = {self.spearman_rho_cortisol_valence:.3f}"
        )


def compute_ccc(y_true: Any, y_pred: Any) -> float:
    return compute_ccc_values(list(y_true), list(y_pred))


class WarrinerValidator:
    """Load Warriner ratings, prepare train/test split, and run validation."""

    def __init__(
        self,
        warriner_csv_path: str,
        colony: NOWAColony,
        encoder: WordStimulusEncoder,
        n_words: int = 300,
        stratify_bins: bool = True,
        test_split_ratio: float = 0.2,
        validation_protocol: str = "heldout",
        seed: int = 42,
    ):
        self.warriner_csv_path = str(warriner_csv_path)
        self.colony = colony
        self.encoder = encoder
        self.n_words = max(1, int(n_words))
        self.stratify_bins = bool(stratify_bins)
        self.test_split_ratio = max(0.0, min(0.9, float(test_split_ratio)))
        self.validation_protocol = str(validation_protocol or "heldout")
        if self.validation_protocol not in {"heldout", "in_vocab"}:
            raise ValueError("validation_protocol must be heldout or in_vocab")
        self.seed = int(seed)
        self.rng = random.Random(seed)
        self._rows: Optional[List[dict]] = None
        self._calibration_rows: Optional[List[dict]] = None
        self._test_rows: Optional[List[dict]] = None

    def load_warriner(self) -> List[dict]:
        """Load and normalize Warriner rows from CSV."""
        self._rows = load_warriner_csv(self.warriner_csv_path)
        return [dict(row) for row in self._rows]

    def sample_words(self) -> Tuple[List[dict], List[dict]]:
        """Return disjoint calibration rows and sampled held-out test rows."""
        rows = self._rows if self._rows is not None else self.load_warriner()
        if not rows:
            raise ValueError("Warriner CSV contains no usable rows")

        calibration_rows: List[dict] = []
        heldout_pool: List[dict] = []
        buckets = stratified_bins(rows) if self.stratify_bins else {"all": [dict(row) for row in rows]}

        for bucket_rows in buckets.values():
            bucket = [dict(row) for row in bucket_rows]
            self.rng.shuffle(bucket)
            if len(bucket) <= 1:
                calibration_rows.extend(bucket)
                continue
            test_count = int(round(len(bucket) * self.test_split_ratio))
            test_count = max(1, min(len(bucket) - 1, test_count))
            heldout_pool.extend(bucket[:test_count])
            calibration_rows.extend(bucket[test_count:])

        if not heldout_pool:
            heldout_pool = [dict(row) for row in rows]

        test_rows = (
            stratified_sample(heldout_pool, self.n_words, self.rng)
            if self.stratify_bins
            else self._random_sample(heldout_pool, self.n_words)
        )

        calibration_words = {row_word(row) for row in calibration_rows}
        test_rows = [dict(row) for row in test_rows if row_word(row) not in calibration_words]
        if not test_rows:
            raise ValueError("train/test split produced no held-out test rows")

        self._calibration_rows = [dict(row) for row in calibration_rows]
        self._test_rows = [dict(row) for row in test_rows]
        return [dict(row) for row in calibration_rows], [dict(row) for row in test_rows]

    def run(
        self,
        seed_size: int = 500,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        agent_factory: Any = None,
    ) -> ValidationResult:
        """Run the full validation workflow."""
        rows = self.load_warriner()
        if self.validation_protocol == "in_vocab":
            calibration_rows = (
                stratified_sample(rows, seed_size, self.rng)
                if self.stratify_bins
                else self._random_sample(rows, seed_size)
            )
            test_rows = (
                stratified_sample(calibration_rows, self.n_words, self.rng)
                if self.stratify_bins
                else self._random_sample(calibration_rows, self.n_words)
            )
            self._calibration_rows = [dict(row) for row in calibration_rows]
            self._test_rows = [dict(row) for row in test_rows]
        else:
            calibration_rows, test_rows = self.sample_words()

        self.colony.initialize(
            calibration_rows,
            n_seed=min(max(0, int(seed_size)), len(calibration_rows)),
            agent_factory=agent_factory,
        )
        if self.encoder.mode == "sbert_neighbors":
            self.encoder.warriner_df = list(getattr(self.colony, "seed_corpus", []) or calibration_rows)
            self.encoder._records_cache = None
        elif self.encoder.warriner_df is None:
            self.encoder.warriner_df = calibration_rows
            self.encoder._records_cache = None

        colony_responses: List[ColonyResponse] = []
        words: List[str] = []
        human_v: List[float] = []
        human_a: List[float] = []
        nowa_v: List[float] = []
        nowa_a: List[float] = []

        total = len(test_rows)
        for index, row in enumerate(test_rows, start=1):
            word = row_word(row)
            if progress_callback is not None:
                progress_callback(index, total, word)
            events = self.encoder.encode(word, row)
            response = self.colony.run_stimulus(events)
            colony_responses.append(response)
            words.append(word)
            human_v.append(float(row["v"]))
            human_a.append(float(row["a"]))
            nowa_v.append(float(response.mean_valence_shift))
            nowa_a.append(float(response.mean_arousal_shift))

        rho_v, p_v = spearman_rho(human_v, nowa_v)
        rho_a, p_a = spearman_rho(human_a, nowa_a)
        da_deltas = [float(response.mean_da_delta) for response in colony_responses]
        cortisol_deltas = [float(response.mean_cortisol_delta) for response in colony_responses]
        rho_da_v, _ = spearman_rho(human_v, da_deltas)
        rho_cort_v, _ = spearman_rho(human_v, cortisol_deltas)
        sd_human = population_sd(human_v)
        sd_nowa = population_sd(nowa_v)
        sd_ratio = 0.0 if sd_human <= 0.0 else sd_nowa / sd_human

        archetype_corrs: Dict[str, float] = {}
        for archetype in ARCHETYPES:
            archetype_values = [
                float(response.per_archetype[archetype])
                for response in colony_responses
                if archetype in response.per_archetype
            ]
            if len(archetype_values) == len(human_v) and archetype_values:
                archetype_corrs[archetype] = spearman_rho(human_v, archetype_values)[0]

        archetype_counts: Dict[str, int] = {name: 0 for name in ARCHETYPES}
        if colony_responses:
            for response in colony_responses[0].agent_responses:
                if response.archetype in archetype_counts:
                    archetype_counts[response.archetype] += 1

        return ValidationResult(
            n_words=len(words),
            encoder_mode=self.encoder.mode,
            spearman_rho_valence=rho_v,
            spearman_p_valence=p_v,
            pearson_r_valence=pearson_r(human_v, nowa_v),
            ccc_valence=compute_ccc(human_v, nowa_v),
            spearman_rho_arousal=rho_a,
            spearman_p_arousal=p_a,
            archetype_correlations=archetype_corrs,
            archetype_n_agents=archetype_counts,
            sd_nowa_valence=sd_nowa,
            sd_human_valence=sd_human,
            sd_ratio=sd_ratio,
            mean_activated_memories=mean(response.mean_n_activated_memories for response in colony_responses),
            zero_activation_ratio=mean(
                1.0 if response.mean_n_activated_memories <= 0.0 else 0.0
                for response in colony_responses
            ),
            words=words,
            warriner_valence_norm=human_v,
            nowa_valence_shifts=nowa_v,
            warriner_arousal_norm=human_a,
            nowa_arousal_shifts=nowa_a,
            colony_responses=colony_responses,
            spearman_rho_da_valence=rho_da_v,
            spearman_rho_cortisol_valence=rho_cort_v,
        )

    def diagnose_zero_activations(
        self,
        result: ValidationResult,
        threshold: float = 0.3,
    ) -> dict:
        """Return a compact diagnostic report for zero or weak memory activation."""
        ranked = sorted(
            result.colony_responses,
            key=lambda response: response.mean_n_activated_memories,
        )
        if result.zero_activation_ratio > threshold:
            recommendation = (
                "Increase seed_size or use sbert_neighbors so held-out words can "
                "co-activate semantically related seed episodes."
            )
        else:
            recommendation = "Memory activation is within the configured threshold."
        return {
            "zero_activation_ratio": float(result.zero_activation_ratio),
            "worst_words": [response.word for response in ranked[:20]],
            "recommendation": recommendation,
        }

    def _random_sample(self, rows: List[dict], n_items: int) -> List[dict]:
        rows_copy = [dict(row) for row in rows]
        self.rng.shuffle(rows_copy)
        return rows_copy[: min(max(0, int(n_items)), len(rows_copy))]


__all__ = ["ValidationResult", "WarrinerValidator", "compute_ccc"]
