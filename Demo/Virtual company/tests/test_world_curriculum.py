"""Tests for authored world curriculum."""

from pathlib import Path

import pytest

from nowa_sandbox.world_curriculum import (
    CurriculumValidationError,
    WorldCurriculum,
    default_template_quarter,
    validate_quarter,
)


def test_template_quarter_validates():
    assert validate_quarter(default_template_quarter()) == []


def test_round_trip_json(tmp_path: Path):
    cur = WorldCurriculum.from_template(n_quarters=2)
    q2 = cur.get_quarter(2)
    q2["offers"][0]["unit_price"] = 2.5
    cur.set_quarter(2, q2)
    path = tmp_path / "plan.json"
    cur.save_json(path)
    loaded = WorldCurriculum.load_json(path)
    assert loaded.n_quarters == 2
    assert loaded.get_quarter(2)["offers"][0]["unit_price"] == 2.5
    loaded.ensure_valid()


def test_curriculum_step_mapping():
    cur = WorldCurriculum.from_template(n_quarters=2)
    assert cur.curriculum_quarter_for_step(1) == (1, 1)
    assert cur.curriculum_quarter_for_step(2) == (2, 1)
    assert cur.curriculum_quarter_for_step(3) == (1, 2)
    assert cur.curriculum_quarter_for_step(4) == (2, 2)


def test_duplicate_and_remove():
    cur = WorldCurriculum.from_template(n_quarters=1)
    cur.duplicate_quarter(1)
    assert cur.n_quarters == 2
    cur.remove_quarter(1)
    assert cur.n_quarters == 1


def test_invalid_offer_refs():
    bad = default_template_quarter()
    bad["offers"][0]["product_id"] = "missing"
    errs = validate_quarter(bad)
    assert any("unknown product" in e for e in errs)


def test_ensure_valid_raises():
    cur = WorldCurriculum()
    with pytest.raises(CurriculumValidationError):
        cur.ensure_valid()


def test_build_world_from_curriculum():
    cur = WorldCurriculum.from_template(n_quarters=1)
    world = cur.build_world(1, days_per_quarter=10, seed=7)
    assert "product_001" in world.products
    assert "supplier_001" in world.suppliers
    assert len(world.offers) == 1
    quote = world.observe_supplier_quote("supplier_001", "product_001", 10)
    assert quote["status"] == "ok"
