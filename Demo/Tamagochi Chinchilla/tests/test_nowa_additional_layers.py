import sys
from pathlib import Path


# Add src directory to path
SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def test_additional_nowa_layers_initialized():
    from main import ChinchillaAgent

    demo_dir = Path(__file__).parent.parent
    agent = ChinchillaAgent(demo_dir=str(demo_dir), use_pygame=False, use_gui=False)

    assert agent.temporal_levels is not None
    assert agent.affective_persistence is not None
    assert agent.affective_background is not None
    assert agent.semantic_emotions is not None
    assert agent.emotional_memory is not None
    assert agent.emotional_expectations is not None


def test_additional_nowa_layers_update():
    from main import ChinchillaAgent

    demo_dir = Path(__file__).parent.parent
    agent = ChinchillaAgent(demo_dir=str(demo_dir), use_pygame=False, use_gui=False)
    agent.running = True

    # Force a high-valence/high-arousal state to activate semantic emotions
    agent.affect_space.axes["valence"] = 0.9
    agent.affect_space.axes["arousal"] = 0.8
    agent.affect_space.axes["stress"] = 0.1
    agent.affect_space.axes["curiosity"] = 0.7

    # Update additional layers directly
    agent._update_additional_nowa_layers(0.2)

    # Temporal levels updated
    assert agent.temporal_levels.t1, "TemporalLevels should log snapshots"

    # Persistence + background snapshots are dict/list-like
    assert isinstance(agent.affective_persistence.snapshot(), list)
    assert isinstance(agent.affective_background.snapshot(), dict)

    # Semantic emotions should produce at least one active emotion
    semantic = agent.semantic_emotions.snapshot()
    assert isinstance(semantic, list)
    assert len(semantic) >= 1

    # Emotional memory and expectations snapshots should have keys
    mem = agent.emotional_memory.snapshot()
    assert "episodes" in mem
    exp = agent.emotional_expectations.snapshot()
    assert "expectations" in exp
