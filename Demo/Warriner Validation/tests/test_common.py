"""Tests for shared validation helpers."""

import random

from nowa_validation._common import (
    compute_ccc_values,
    mean,
    normalize_warriner_records,
    pearson_r,
    population_sd,
    spearman_rho,
    stratified_sample,
)


def test_normalize_warriner_converts_raw_scale_and_lowercases():
    rows = [{"Word": "HAPPY", "V.Mean.Sum": 9.0, "A.Mean.Sum": 1.0, "D.Mean.Sum": 5.0}]

    result = normalize_warriner_records(rows)

    assert result == [
        {
            "word": "happy",
            "v": 1.0,
            "a": 0.0,
            "d": 0.5,
            "V.Mean.Sum": 9.0,
            "A.Mean.Sum": 1.0,
            "D.Mean.Sum": 5.0,
        }
    ]


def test_normalize_warriner_accepts_normalized_rows_and_clamps():
    rows = [{"word": "x", "v": 2.0, "a": -0.5, "d": 1.5}]

    result = normalize_warriner_records(rows)

    assert result[0]["v"] == 1.0
    assert result[0]["a"] == 0.0
    assert result[0]["d"] == 1.0


def test_normalize_warriner_skips_missing_values():
    rows = [
        {"Word": "good", "V.Mean.Sum": 7.0, "A.Mean.Sum": 5.0, "D.Mean.Sum": 5.0},
        {"Word": "bad", "V.Mean.Sum": "", "A.Mean.Sum": 5.0, "D.Mean.Sum": 5.0},
    ]

    result = normalize_warriner_records(rows)

    assert [row["word"] for row in result] == ["good"]


def test_correlations_and_ccc_cover_expected_extremes():
    x = [1.0, 2.0, 3.0, 4.0]
    y = [4.0, 3.0, 2.0, 1.0]

    rho_pos, p_pos = spearman_rho(x, x)
    rho_neg, _ = spearman_rho(x, y)

    assert abs(rho_pos - 1.0) < 1e-12
    assert p_pos == 0.0
    assert abs(rho_neg + 1.0) < 1e-12
    assert abs(pearson_r(x, x) - 1.0) < 1e-12
    assert compute_ccc_values(x, x) == 1.0
    assert compute_ccc_values(x, [value + 10.0 for value in x]) < 0.2


def test_mean_population_sd_and_stratified_sample(mini_warriner_norm):
    sample = stratified_sample(mini_warriner_norm, 12, random.Random(0))
    v_values = [row["v"] for row in sample]

    assert mean([1.0, 2.0, 3.0]) == 2.0
    assert round(population_sd([1.0, 2.0, 3.0]), 6) == 0.816497
    assert len(sample) == 12
    assert min(v_values) < -0.2
    assert max(v_values) > 0.2
