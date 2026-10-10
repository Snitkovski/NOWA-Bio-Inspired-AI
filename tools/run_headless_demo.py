import logging
from pathlib import Path
import time

# Ensure src path resolution matches demo expectations
import sys
ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import importlib.util

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

def load_chinchilla_agent_module(path: Path):
    spec = importlib.util.spec_from_file_location("chinchilla_main", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run(duration_s: float = 20.0):
    demo_src = ROOT / "Demo" / "Tamagochi Chinchilla" / "src"
    # Ensure demo src dir is on sys.path so local imports (config, dataset_loader) resolve
    if str(demo_src) not in sys.path:
        sys.path.insert(0, str(demo_src))
    demo_main = load_chinchilla_agent_module(demo_src / "main.py")
    ChinchillaAgent = getattr(demo_main, "ChinchillaAgent")
    demo_dir = ROOT / "Demo" / "Tamagochi Chinchilla"
    # Create agent with pygame enabled, but replace engine with stub to avoid display
    agent = ChinchillaAgent(demo_dir=str(demo_dir), use_pygame=True, use_gui=False)
    StubEngine = getattr(demo_main, "StubPygameEngine", None)
    if StubEngine:
        agent.pygame_engine = StubEngine()
    agent.run(max_duration=duration_s)

if __name__ == '__main__':
    run(20.0)
