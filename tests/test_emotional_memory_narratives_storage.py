from affective_space import AffectiveSpace
from semantic_emotions import SemanticEmotionsLayer
from emotional_memory_narratives import EmotionalMemoryNarrativesLayer
from storage import AgentStorage
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector


def test_emotional_memory_save_load(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a"])

    space = AffectiveSpace(
        axes={"pleasure": 0.7, "arousal": 0.6, "pain": 0.0},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    sem = SemanticEmotionsLayer()
    memory = EmotionalMemoryNarrativesLayer()
    for t in (0.0, 10.0, 20.0):
        sem.update_from_space(space)
        memory.update_from_layers(semantic_emotions=sem, space=space, background={}, agent_lifetime=1000.0, timestamp=t)

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        emotional_memory=memory,
        filename="emotional_memory.pkl",
    )

    restored = EmotionalMemoryNarrativesLayer()
    storage.load_agent(
        hip,
        cortex,
        selector,
        path,
        emotional_memory=restored,
    )

    assert restored.snapshot()["patterns"]
    assert restored.snapshot()["narrative_fragments"]
