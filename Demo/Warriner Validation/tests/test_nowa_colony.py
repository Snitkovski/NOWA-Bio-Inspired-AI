from nowa_validation.nowa_colony import NOWAColony
from nowa_validation._common import population_sd
from nowa_validation.word_stimulus_encoder import WordStimulusEncoder


class FakeAffectiveSpace:
    def __init__(self):
        self.axes = {
            "valence": 0.0,
            "arousal": 0.0,
            "dominance": 0.0,
            "stress": 0.0,
            "trust": 0.0,
            "curiosity": 0.0,
            "stability": 0.0,
            "attachment": 0.0,
        }
        self.last_axes = dict(self.axes)

    def step(self, inputs=None, **kwargs):
        del kwargs
        self.last_axes = dict(self.axes)
        for key, value in dict(inputs or {}).items():
            if key in self.axes:
                self.axes[key] += float(value)
        return dict(self.axes)

    def snapshot(self):
        return {"axes": dict(self.axes)}


class FakeNeuromodulators:
    def __init__(self):
        self.dopamine = 0.1
        self.norepinephrine = 0.1
        self.serotonin = 0.1
        self.cortisol = 0.05

    def snapshot(self):
        return {
            "dopamine": self.dopamine,
            "norepinephrine": self.norepinephrine,
            "serotonin": self.serotonin,
            "cortisol": self.cortisol,
        }


def _tokens(path):
    if hasattr(path, "signature"):
        return set(path.signature())
    return set(path)


class FakeHippocampus:
    def __init__(self):
        self.experiences = []

    def store(self, path, consequence=None, intensity=1.0, reward=0.0, encoding_strength=None):
        exp = type("FakeExperience", (), {})()
        exp.path = path
        exp.consequence = consequence
        exp.intensity = intensity
        exp.reward = reward
        exp.encoding_strength = encoding_strength
        exp.reinforcement_count = 1
        exp.activation_energy = 1.0
        self.experiences.append(exp)
        return exp

    def reinforce(self, path, consequence=None, intensity=1.0):
        del consequence, intensity
        wanted = _tokens(path)
        for exp in self.experiences:
            if _tokens(exp.path) == wanted:
                exp.reinforcement_count += 1
                return exp
        return self.store(path)

    def activate(self, context_events):
        query = set(context_events or [])
        return [
            exp
            for exp in self.experiences
            if query.intersection(_tokens(exp.path))
        ]


class FakeAgent:
    def __init__(self, agent_id, cort, curiosity):
        self.agent_id = agent_id
        self.hippocampus = FakeHippocampus()
        self.affective_space = FakeAffectiveSpace()
        self.neuromodulators = FakeNeuromodulators()
        self.genome = {"nm_acc_k_cort": cort, "dr_curiosity_baseline": curiosity}
        self.affect_state = type(
            "FakeAffectState",
            (),
            {"valence": 0.0, "arousal": 0.0, "threat": 0.0, "curiosity": 0.1},
        )()

    def step(self, context_events, reward=0.0, affective_inputs=None, **kwargs):
        del context_events, reward, kwargs
        self.affective_space.step(inputs=affective_inputs or {})
        valence = self.affective_space.axes["valence"]
        self.neuromodulators.dopamine = 0.1 + max(0.0, valence) * 0.1
        self.neuromodulators.cortisol = 0.05 + max(0.0, -valence) * 0.1
        self.neuromodulators.norepinephrine = 0.1 + abs(self.affective_space.axes["arousal"]) * 0.1
        return "observe"


def _factory(agent_id, rng, index):
    del rng
    traits = [
        (0.4, 0.30),
        (0.5, 0.10),
        (1.0, 0.35),
        (1.1, 0.05),
    ]
    cort, curiosity = traits[index]
    return FakeAgent(agent_id, cort, curiosity)


ROWS = [
    {"word": "happy", "v": 0.8, "a": 0.7, "d": 0.7},
    {"word": "sad", "v": -0.7, "a": 0.6, "d": 0.3},
    {"word": "table", "v": 0.0, "a": 0.4, "d": 0.5},
    {"word": "victory", "v": 0.9, "a": 0.8, "d": 0.8},
]


def test_colony_initializes_agents_seeds_memory_and_assigns_archetypes():
    colony = NOWAColony(n_agents=4, ticks_per_stimulus=1, seed=1)

    colony.initialize(ROWS, n_seed=4, agent_factory=_factory)

    assert len(colony.agents) == 4
    assert set(colony.agent_archetypes.values()) == {
        "explorer",
        "passive",
        "resource_pragmatist",
        "anxious_loner",
    }
    assert all(len(agent.hippocampus.experiences) == 4 for agent in colony.agents)
    assert len({id(agent.hippocampus) for agent in colony.agents}) == 4
    assert len({id(agent.affective_space) for agent in colony.agents}) == 4
    assert len({id(agent.neuromodulators) for agent in colony.agents}) == 4
    assert not any(hasattr(agent, "archetype") for agent in colony.agents)


def test_run_stimulus_uses_memory_signal_and_resets_affect_between_words():
    colony = NOWAColony(n_agents=4, ticks_per_stimulus=1, seed=1)
    colony.initialize(ROWS, n_seed=4, agent_factory=_factory)

    happy = colony.run_stimulus(["word:happy"])
    sad = colony.run_stimulus(["word:sad"])

    assert happy.word == "happy"
    assert happy.mean_n_activated_memories > 0
    assert happy.mean_valence_shift > 0
    assert sad.mean_valence_shift < 0
    assert all(response.valence_before == 0.0 for response in sad.agent_responses)
    assert set(happy.per_archetype) == {
        "explorer",
        "passive",
        "resource_pragmatist",
        "anxious_loner",
    }


def test_higher_affective_gain_increases_response_sd():
    encoder = WordStimulusEncoder(mode="direct_vad", warriner_df=ROWS)
    results_by_gain = {}

    for gain in [0.75, 1.8]:
        colony = NOWAColony(
            n_agents=4,
            ticks_per_stimulus=3,
            signal_ticks=3,
            affective_gain=gain,
            seed=1,
        )
        colony.initialize(ROWS, n_seed=4, agent_factory=_factory)
        shifts = []
        for row in ROWS:
            response = colony.run_stimulus(encoder.encode(row["word"], row))
            shifts.append(response.mean_valence_shift)
        results_by_gain[gain] = population_sd(shifts)

    assert results_by_gain[1.8] > results_by_gain[0.75]


def test_signal_ticks_accumulates_signal():
    encoder = WordStimulusEncoder(mode="direct_vad", warriner_df=ROWS)
    pos_row = next(row for row in ROWS if row["v"] > 0.8)
    shifts = {}

    for signal_ticks in [1, 3]:
        colony = NOWAColony(
            n_agents=4,
            ticks_per_stimulus=3,
            signal_ticks=signal_ticks,
            affective_gain=1.0,
            seed=1,
        )
        colony.initialize(ROWS, n_seed=4, agent_factory=_factory)
        response = colony.run_stimulus(encoder.encode(pos_row["word"], pos_row))
        shifts[signal_ticks] = response.mean_valence_shift

    assert shifts[3] > shifts[1]


def test_memory_top_k_filters_irrelevant():
    strong = type("Experience", (), {})()
    strong.warriner_valence_norm = 0.9
    strong.warriner_arousal_norm = 0.8
    strong.warriner_dominance_norm = 0.8
    strong.activation_energy = 1.0
    strong.reinforcement_count = 1

    weak = type("Experience", (), {})()
    weak.warriner_valence_norm = -0.9
    weak.warriner_arousal_norm = 0.6
    weak.warriner_dominance_norm = 0.4
    weak.activation_energy = 0.1
    weak.reinforcement_count = 1

    v, _, _, _ = NOWAColony._memory_signal(
        [weak, weak, weak, strong],
        top_k=1,
        min_activation=0.3,
    )

    assert v == 0.9
