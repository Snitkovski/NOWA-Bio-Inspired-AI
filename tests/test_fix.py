"""Regression marker: legacy trainer module has been removed from src/."""

from pathlib import Path


def test_trainer_module_removed():
    assert not Path("src/trainer.py").exists()
