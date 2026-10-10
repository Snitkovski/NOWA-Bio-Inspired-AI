import logging
from pathlib import Path
import sys
ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hippocampus import NOWAHippocampus
from sleep import SleepManager, CortexMemory
from neuromodulators import NeuromodulatorState

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def run_test():
    hip = NOWAHippocampus(max_experiences=200)
    cortex = CortexMemory()
    sm = SleepManager(hippocampus=hip, cortex=cortex)

    # Store some experiences
    for i in range(8):
        path = [f"action:demo_{i}", f"object:toy_{i%3}"]
        hip.store(path=path, consequence=None, reward=0.2 * (i%3), intensity=0.5)
    log.info(f"Stored experiences: {len(hip.experiences)}")

    # Set neuromodulators to a sample state
    nm = NeuromodulatorState()
    nm.dopamine = 0.08
    nm.cortisol = 0.05
    nm.norepinephrine = 0.1
    sm.neuromodulators = nm

    before = len(hip.experiences)
    stats = sm.deep_sleep(cycles=2)
    after = len(hip.experiences)
    log.info(f"SleepManager.deep_sleep stats: {stats}")
    log.info(f"Hippocampus before={before} after={after}")
    log.info(f"Cortex stats: {cortex.get_statistics()}")

    # Try again with relaxed consolidation thresholds to demonstrate successful consolidation
    sm.min_reinforcement_for_consolidation = 0
    sm.td_threshold = 0.0
    stats2 = sm.deep_sleep(cycles=2)
    log.info(f"After relaxation, deep_sleep stats: {stats2}")
    log.info(f"Cortex stats after relaxation: {cortex.get_statistics()}")

if __name__ == '__main__':
    run_test()
