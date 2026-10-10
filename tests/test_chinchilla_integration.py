import types
import pytest
import importlib.util
from pathlib import Path

# Load Demo/Tamagochi Chinchilla/src/main.py module by path (handles spaces)
demo_main_path = Path(__file__).parent.parent / "Demo" / "Tamagochi Chinchilla" / "src" / "main.py"
spec = importlib.util.spec_from_file_location("chinchilla_main", str(demo_main_path))
ch_main = importlib.util.module_from_spec(spec)
import sys
# ensure the demo src dir is on sys.path so local imports (config, behavioral_chains) resolve
sys.path.insert(0, str(demo_main_path.parent))
spec.loader.exec_module(ch_main)
ChinchillaAgent = ch_main.ChinchillaAgent
Event = ch_main.Event
EventType = ch_main.EventType


class DummyCER:
    def __init__(self):
        self.last_kwargs = None
    def update(self, **kwargs):
        # record kwargs shape
        self.last_kwargs = dict(kwargs)
        return {
            "modulation_factors": {
                "exploration_bias": 0.42,
                "decision_threshold_shift": 0.1,
                "habit_gain_scale": 1.5,
            },
            "valence": 0.25,
        }


class DummySleepManager:
    def __init__(self):
        self.deep_sleep_called = 0
        self.neuromodulators = None
    def deep_sleep(self, cycles=1):
        assert hasattr(self, 'neuromodulators')
        self.deep_sleep_called += cycles
        return {"status": "ok", "cycles": cycles}


class DummyHippocampus:
    def __init__(self):
        self.stored = None
        self.experiences = []
        self.signatures = []

    def store(self, path=None, consequence=None, intensity=None, reward=None):
        self.stored = (path, consequence, intensity, reward)

    def recall_recent(self, limit=10):
        return list(self.experiences)[-max(1, int(limit)) :]


class DummyChainExecutor:
    def __init__(self):
        self._current_chain = None
        self._can_continue = True
    @property
    def current_chain(self):
        return self._current_chain
    def can_continue_chain(self):
        return self._can_continue
    def get_chain_stats(self):
        return {"total_chains_completed": 0}
    def start_chain(self, name):
        return None
    def get_next_action_in_chain(self):
        return None


@pytest.fixture
def agent(tmp_path):
    # instantiate and then patch heavy components
    demo_dir = tmp_path
    # create minimal required dirs
    (demo_dir / "Datasets").mkdir()
    a = ChinchillaAgent(demo_dir=str(demo_dir), use_pygame=False, use_gui=False)
    return a


def test_sleep_manager_deep_sleep_called(agent):
    sm = DummySleepManager()
    agent.sleep_manager = sm
    # set neuromodulator stub
    class NM:
        def __init__(self):
            self.dopamine = 0.1
            self.cortisol = 0.1
            self.serotonin = 0.1
            self.acetylcholine = 0.0

        def get_learning_rate_modifier(self):
            return 1.0

        def get_forgetting_rate(self):
            return 0.1

        def get_consolidation_strength(self):
            return 1.0
    nm = NM()
    agent.neuromod = nm

    agent._run_sleep_consolidation()
    assert sm.deep_sleep_called >= 1
    assert getattr(agent.sleep_manager, 'neuromodulators', None) is nm


def test_event_without_features(agent):
    # patch hippocampus and bg_channels to simulate chain finish
    hip = DummyHippocampus()
    agent.hippocampus = hip
    agent.last_chain_name = 'dummy_chain'
    agent.chain_executor = DummyChainExecutor()
    agent.chain_executor._can_continue = False
    agent._last_chain_reward = 0.2
    # ensure bg_channels contains the chain
    class DummyChannel:
        def __init__(self):
            self.last_outcome = 0.1
            self.habit_strength = 0.0
        def record_outcome(self, outcome):
            self.last_outcome = outcome
    agent.bg_channels = {'dummy_chain': DummyChannel()}

    # Call the part of sim_step that stores hippocampus traces
    # We simulate by calling sim_step with conditions that trigger chain_just_finished
    agent.running = True
    agent.paused = False
    # set action so that action_remaining_s == 0
    agent.action_remaining_s = 0.0
    # ensure no active chain
    agent.chain_executor._current_chain = None

    # run one sim step
    agent.sim_step(0.1)

    # hippocampus.store should have been called
    assert hip.stored is not None
    path, consequence, intensity, reward = hip.stored
    # path should have events and event should be of correct type
    events = getattr(path, 'events', None)
    assert events and len(events) > 0
    ev = events[0]
    assert isinstance(ev, Event)
    assert ev.name == 'dummy_chain'
    assert ev.event_type == EventType.ACTION


def test_cer_update_kwargs_and_result_handling(agent):
    cer = DummyCER()
    agent.cer = cer
    agent.running = True
    agent.paused = False
    agent.action_remaining_s = 0.0
    agent.chain_executor = DummyChainExecutor()
    agent.chain_executor._can_continue = True

    # call sim step; cer.update should be invoked with new kwarg names
    agent.sim_step(0.1)
    assert 'reward_signal' in cer.last_kwargs
    assert 'novelty_score' in cer.last_kwargs
    # agent fields should be updated from modulation_factors
    assert abs(agent._cer_exploration_bias - 0.42) < 1e-6
    assert abs(agent._cer_decision_threshold_shift - 0.1) < 1e-6
    assert abs(agent._cer_habit_gain_scale - 1.5) < 1e-6
