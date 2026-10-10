from nowa_validation.hippocampus_seeder import HippocampusSeeder, _word_to_events


class FakeHippocampus:
    def __init__(self):
        self.stored = []
        self.reinforced = []

    def store(self, path, consequence=None, intensity=1.0, reward=0.0, encoding_strength=None):
        exp = type("FakeExperience", (), {})()
        exp.path = path
        exp.consequence = consequence
        exp.intensity = intensity
        exp.reward = reward
        exp.encoding_strength = encoding_strength
        exp.reinforcement_count = 1
        exp.activation_energy = 1.0
        self.stored.append(exp)
        return exp

    def reinforce(self, path, consequence=None, intensity=1.0):
        self.reinforced.append((path, consequence, intensity))
        return self.stored[-1]


class FakeAgent:
    def __init__(self):
        self.agent_id = "fake"
        self.hippocampus = FakeHippocampus()


def _rows():
    return [
        {"Word": "murder", "V.Mean.Sum": 1.4, "A.Mean.Sum": 7.0, "D.Mean.Sum": 2.0},
        {"Word": "dull", "V.Mean.Sum": 3.8, "A.Mean.Sum": 2.0, "D.Mean.Sum": 3.0},
        {"Word": "table", "V.Mean.Sum": 5.0, "A.Mean.Sum": 3.0, "D.Mean.Sum": 5.0},
        {"Word": "window", "V.Mean.Sum": 5.4, "A.Mean.Sum": 4.0, "D.Mean.Sum": 5.0},
        {"Word": "smile", "V.Mean.Sum": 7.1, "A.Mean.Sum": 5.0, "D.Mean.Sum": 6.0},
        {"Word": "happy", "V.Mean.Sum": 8.6, "A.Mean.Sum": 6.5, "D.Mean.Sum": 7.0},
    ]


def _signature(path):
    if hasattr(path, "signature"):
        return list(path.signature())
    return list(path)


def test_word_to_events_uses_expected_threshold_tokens():
    assert _word_to_events(" Happy ", 0.8, 0.7, 0.7) == [
        "word:happy",
        "valence:very_positive",
        "arousal:high",
        "dominance:high",
    ]
    assert _word_to_events("Murder", -0.8, 0.2, 0.2) == [
        "word:murder",
        "valence:very_negative",
        "arousal:low",
        "dominance:low",
    ]


def test_build_seed_corpus_normalizes_and_stratifies():
    seeder = HippocampusSeeder(_rows(), n_seed=6)
    corpus = seeder.build_seed_corpus()

    assert len(corpus) == 6
    assert all(-1.0 <= row["v"] <= 1.0 for row in corpus)
    assert all(0.0 <= row["a"] <= 1.0 for row in corpus)
    assert any(row["v"] < -0.5 for row in corpus)
    assert any(row["v"] > 0.5 for row in corpus)


def test_seed_agent_stores_metadata_and_reinforces_strong_valence():
    agent = FakeAgent()
    seeder = HippocampusSeeder(_rows(), n_seed=6)

    added = seeder.seed_agent(agent)

    assert added == 6
    assert len(agent.hippocampus.stored) == 6
    assert agent.hippocampus.reinforced
    stored_words = {
        getattr(exp, "warriner_word")
        for exp in agent.hippocampus.stored
    }
    assert {"happy", "murder"}.issubset(stored_words)
    happy_exp = next(exp for exp in agent.hippocampus.stored if exp.warriner_word == "happy")
    assert "word:happy" in _signature(happy_exp.path)
    assert happy_exp.reward > 0
    assert happy_exp.encoding_strength >= 0.2


def test_seed_colony_uses_same_corpus_for_all_agents():
    agents = [FakeAgent(), FakeAgent()]
    agents[0].agent_id = "a"
    agents[1].agent_id = "b"
    seeder = HippocampusSeeder(_rows(), n_seed=4)

    counts = seeder.seed_colony(agents)

    assert counts == {"a": 4, "b": 4}
    words_a = {exp.warriner_word for exp in agents[0].hippocampus.stored}
    words_b = {exp.warriner_word for exp in agents[1].hippocampus.stored}
    assert words_a == words_b
