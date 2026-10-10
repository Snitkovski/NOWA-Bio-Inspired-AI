from pathlib import Path

from nowa_validation.nowa_colony import AgentResponse, ColonyResponse
from nowa_validation.warriner_validator import WarrinerValidator, compute_ccc
from nowa_validation.word_stimulus_encoder import WordStimulusEncoder


def _csv(path: Path) -> Path:
    lines = ["Word,V.Mean.Sum,A.Mean.Sum,D.Mean.Sum"]
    for index in range(30):
        v = 1.0 + (8.0 * index / 29.0)
        a = 1.0 + (8.0 * ((index * 7) % 30) / 29.0)
        d = 1.0 + (8.0 * ((index * 3) % 30) / 29.0)
        lines.append(f"w{index:02d},{v:.4f},{a:.4f},{d:.4f}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class FakeColony:
    def __init__(self):
        self.initialized_with = None

    def initialize(self, warriner_df, n_seed=500, agent_factory=None):
        del agent_factory
        self.initialized_with = (list(warriner_df), n_seed)

    def run_stimulus(self, context_events):
        word = next(token.split(":", 1)[1] for token in context_events if token.startswith("word:"))
        index = int(word[1:])
        shift = (index - 14.5) / 14.5
        arousal = (((index * 7) % 30) - 14.5) / 29.0
        responses = [
            AgentResponse(
                agent_id="a",
                archetype="explorer",
                valence_before=0.0,
                valence_after=shift,
                valence_shift=shift,
                arousal_shift=arousal,
                da_delta=max(0.0, shift) * 0.1,
                ne_delta=abs(arousal) * 0.1,
                cortisol_delta=max(0.0, -shift) * 0.1,
                serotonin_delta=0.0,
                n_activated_memories=1,
                stimulus_word=word,
                raw_axes_before={"valence": 0.0, "arousal": 0.0},
                raw_axes_after={"valence": shift, "arousal": arousal},
            )
        ]
        return ColonyResponse(
            word=word,
            n_agents=1,
            mean_valence_shift=shift,
            std_valence_shift=0.0,
            mean_arousal_shift=arousal,
            mean_da_delta=max(0.0, shift) * 0.1,
            mean_ne_delta=abs(arousal) * 0.1,
            mean_cortisol_delta=max(0.0, -shift) * 0.1,
            mean_n_activated_memories=1.0,
            per_archetype={"explorer": shift},
            agent_responses=responses,
            processing_time_s=0.0,
        )


def test_load_and_sample_are_normalized_and_disjoint(tmp_path):
    csv_path = _csv(tmp_path / "warriner.csv")
    validator = WarrinerValidator(
        warriner_csv_path=str(csv_path),
        colony=FakeColony(),
        encoder=WordStimulusEncoder(),
        n_words=8,
        seed=3,
    )

    rows = validator.load_warriner()
    calibration, test = validator.sample_words()

    assert rows[0]["v"] == -1.0
    assert rows[-1]["v"] == 1.0
    assert len(test) <= 8
    assert {row["word"] for row in calibration}.isdisjoint({row["word"] for row in test})


def test_run_returns_correlations_and_diagnostics(tmp_path):
    csv_path = _csv(tmp_path / "warriner.csv")
    colony = FakeColony()
    validator = WarrinerValidator(
        warriner_csv_path=str(csv_path),
        colony=colony,
        encoder=WordStimulusEncoder(mode="lexical"),
        n_words=8,
        seed=4,
    )

    result = validator.run(seed_size=10)
    diagnostics = validator.diagnose_zero_activations(result)

    assert result.n_words > 0
    assert result.spearman_rho_valence > 0.9
    assert result.pearson_r_valence > 0.9
    assert result.spearman_rho_da_valence > 0.5
    assert result.spearman_rho_cortisol_valence < -0.5
    assert result.zero_activation_ratio == 0.0
    assert colony.initialized_with[1] == 10
    assert {row["word"] for row in colony.initialized_with[0]}.isdisjoint(set(result.words))
    assert diagnostics["worst_words"]


def test_in_vocab_protocol_uses_seed_words_as_test_words(tmp_path):
    csv_path = _csv(tmp_path / "warriner.csv")
    colony = FakeColony()
    validator = WarrinerValidator(
        warriner_csv_path=str(csv_path),
        colony=colony,
        encoder=WordStimulusEncoder(mode="lexical"),
        n_words=8,
        validation_protocol="in_vocab",
        seed=4,
    )

    result = validator.run(seed_size=12)
    seed_words = {row["word"] for row in colony.initialized_with[0]}

    assert set(result.words).issubset(seed_words)
    assert result.spearman_rho_valence > 0.9


def test_compute_ccc_detects_perfect_concordance():
    assert compute_ccc([1, 2, 3], [1, 2, 3]) == 1.0
