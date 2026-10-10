import pytest

from nowa_validation.word_stimulus_encoder import (
    WordStimulusEncoder,
    encode_direct_vad,
    encode_lexical,
)


ROWS = [
    {"word": "happy", "v": 0.8, "a": 0.7, "d": 0.7},
    {"word": "happen", "v": 0.1, "a": 0.4, "d": 0.5},
    {"word": "sad", "v": -0.7, "a": 0.6, "d": 0.3},
]


def test_lexical_encoder_never_leaks_vad_tokens():
    events = encode_lexical(" Happy ")

    assert events == ["word:happy"]
    assert not any(event.startswith(("valence:", "arousal:", "dominance:")) for event in events)


def test_direct_vad_encoder_includes_debug_vad_tokens():
    events = encode_direct_vad("happy", ROWS[0])

    assert "word:happy" in events
    assert "valence:very_positive" in events
    assert "arousal:high" in events


def test_batch_validates_row_count_for_direct_vad():
    encoder = WordStimulusEncoder(mode="direct_vad")

    with pytest.raises(ValueError):
        encoder.encode_batch(["happy", "sad"], warriner_rows=[ROWS[0]])


def test_sbert_neighbors_fallback_adds_only_word_tokens():
    encoder = WordStimulusEncoder(
        mode="sbert_neighbors",
        warriner_df=ROWS,
        k_neighbors=5,
    )
    encoder._sbert_load_failed = True

    events = encoder.encode("happy")

    assert events[:3] == ["word:happy", "word:happy", "word:happy"]
    assert len(events) == 5
    assert all(event.startswith("word:") for event in events)
    assert len(set(events[3:])) <= 2


def test_sbert_neighbors_zero_k_returns_single_primary_token():
    encoder = WordStimulusEncoder(
        mode="sbert_neighbors",
        warriner_df=ROWS,
        k_neighbors=0,
    )

    assert encoder.encode("happy") == ["word:happy"]


def test_encode_sentence_returns_deduplicated_word_tokens_without_vad():
    encoder = WordStimulusEncoder(mode="lexical")

    events = encoder.encode_sentence("I love this beautiful sunny day!")

    assert events == ["word:love", "word:beautiful", "word:sunny", "word:day"]
    assert not any(event.startswith(("valence:", "arousal:", "dominance:")) for event in events)
