from affective_space import AffectiveSpace
from semantic_emotions import SemanticEmotionsLayer
from storage import AgentStorage
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector


def _map_by_name(items):
    return {item.get("emotion"): item for item in items}


def test_semantic_emotions_save_load(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a"])

    space = AffectiveSpace(
        axes={"pleasure": 0.4, "arousal": 0.3, "pain": 0.1},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        semantic_emotions=layer,
        filename="semantic_emotions.pkl",
    )

    restored = SemanticEmotionsLayer()
    storage.load_agent(
        hip,
        cortex,
        selector,
        path,
        semantic_emotions=restored,
    )

    src = _map_by_name(layer.snapshot())
    dst = _map_by_name(restored.snapshot())
    assert src.keys() == dst.keys()
    for name, item in src.items():
        assert abs(dst[name]["activation"] - item["activation"]) < 1e-6
        assert abs(dst[name]["stability"] - item["stability"]) < 1e-6
        assert dst[name]["obsessive"] == item["obsessive"]
