import sys
from pathlib import Path

import pytest


DEMO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_ROOT.parents[1]

sys.path.insert(0, str(DEMO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from nowa_validation._common import normalize_warriner_records


MINI_WARRINER = [
    {"word": "love", "V.Mean.Sum": 8.5, "A.Mean.Sum": 6.0, "D.Mean.Sum": 7.0},
    {"word": "murder", "V.Mean.Sum": 1.5, "A.Mean.Sum": 7.5, "D.Mean.Sum": 3.0},
    {"word": "table", "V.Mean.Sum": 5.2, "A.Mean.Sum": 3.0, "D.Mean.Sum": 5.5},
    {"word": "happy", "V.Mean.Sum": 8.2, "A.Mean.Sum": 6.5, "D.Mean.Sum": 7.2},
    {"word": "cancer", "V.Mean.Sum": 1.8, "A.Mean.Sum": 6.8, "D.Mean.Sum": 2.5},
    {"word": "tree", "V.Mean.Sum": 6.8, "A.Mean.Sum": 3.5, "D.Mean.Sum": 5.8},
    {"word": "fear", "V.Mean.Sum": 2.1, "A.Mean.Sum": 7.2, "D.Mean.Sum": 2.8},
    {"word": "joy", "V.Mean.Sum": 8.7, "A.Mean.Sum": 7.0, "D.Mean.Sum": 7.5},
    {"word": "death", "V.Mean.Sum": 1.6, "A.Mean.Sum": 5.5, "D.Mean.Sum": 2.0},
    {"word": "peace", "V.Mean.Sum": 8.0, "A.Mean.Sum": 3.2, "D.Mean.Sum": 7.8},
    {"word": "war", "V.Mean.Sum": 1.9, "A.Mean.Sum": 7.8, "D.Mean.Sum": 4.5},
    {"word": "smile", "V.Mean.Sum": 8.3, "A.Mean.Sum": 6.2, "D.Mean.Sum": 7.0},
    {"word": "pain", "V.Mean.Sum": 2.0, "A.Mean.Sum": 6.9, "D.Mean.Sum": 2.3},
    {"word": "garden", "V.Mean.Sum": 7.5, "A.Mean.Sum": 4.0, "D.Mean.Sum": 6.5},
    {"word": "anger", "V.Mean.Sum": 1.7, "A.Mean.Sum": 8.0, "D.Mean.Sum": 3.5},
    {"word": "music", "V.Mean.Sum": 8.1, "A.Mean.Sum": 6.8, "D.Mean.Sum": 7.1},
    {"word": "disease", "V.Mean.Sum": 1.4, "A.Mean.Sum": 5.8, "D.Mean.Sum": 2.0},
    {"word": "sunset", "V.Mean.Sum": 8.4, "A.Mean.Sum": 5.2, "D.Mean.Sum": 6.8},
    {"word": "grief", "V.Mean.Sum": 1.9, "A.Mean.Sum": 6.0, "D.Mean.Sum": 2.2},
    {"word": "hope", "V.Mean.Sum": 8.6, "A.Mean.Sum": 5.8, "D.Mean.Sum": 7.4},
]


@pytest.fixture
def mini_warriner():
    return list(MINI_WARRINER)


@pytest.fixture
def mini_warriner_norm():
    return normalize_warriner_records(MINI_WARRINER)
