"""Configuration constants for colony GUI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

WINDOW_SIZE: Final[tuple[int, int]] = (1024, 768)
CAGE_RECT: Final[tuple[int, int, int, int]] = (40, 40, 944, 688)

FPS: Final[int] = 60
UPDATE_INTERVAL_MS: Final[int] = 100
INTERACTION_DISPLAY_DURATION: Final[float] = 3.0

NAME_FORMAT_REGEX: Final[str] = r"^G[0-9]+A[0-9]+S[MFU]$"
_NAME_FORMAT_PATTERN = re.compile(NAME_FORMAT_REGEX)


def format_agent_name(generation: int, index_in_generation: int, sex: str) -> str:
    """Return canonical colony GUI name."""
    if generation < 0:
        raise ValueError("generation must be >= 0")
    if index_in_generation < 1:
        raise ValueError("index_in_generation must be >= 1")
    normalized_sex = str(sex).upper()
    if normalized_sex not in {"M", "F", "U"}:
        raise ValueError("sex must be one of M/F/U")
    return f"G{generation}A{index_in_generation}S{normalized_sex}"


def is_formatted_name(name: str) -> bool:
    """Check whether name matches canonical format G<gen>A<index>S<sex>."""
    return bool(_NAME_FORMAT_PATTERN.match(str(name)))


ZONE_RENDER_COORDS: Final[dict[str, tuple[int, int] | None]] = {
    "floor": (490, 580),
    "corner": (110, 575),
    "litter": (872, 572),
    "toy": (720, 510),
    "object": (800, 528),
    "house": (132, 510),
    "dustbath": (260, 590),
    "waterer": (345, 590),
    "bowl_pellets": (430, 600),
    "bowl_hay": (510, 598),
    "mineral": (618, 598),
    "wheel": (730, 406),
    "shelf_lower": (580, 374),
    "shelf_mid": (480, 254),
    "shelf_upper": (380, 140),
    "bars": (920, 450),
    "bars_top": (920, 120),
    "door": (920, 540),
    "current": None,
}

ZONE_LABEL_NAMES: Final[dict[str, str]] = {
    "floor": "пол",
    "corner": "угол",
    "litter": "лоток",
    "toy": "игрушка",
    "object": "объект",
    "house": "домик",
    "dustbath": "купалка",
    "waterer": "поилка",
    "bowl_pellets": "еда",
    "bowl_hay": "сено",
    "mineral": "минерал",
    "wheel": "колесо",
    "shelf_lower": "полка↓",
    "shelf_mid": "полка",
    "shelf_upper": "полка↑",
    "bars": "прутья",
    "bars_top": "верх прутьев",
    "door": "дверь",
}

ZONE_SLOT_OFFSETS: Final[list[tuple[int, int]]] = [
    (0, 0),
    (112, 0),
    (79, -79),
    (0, -112),
    (-79, -79),
    (-112, 0),
    (-79, 79),
    (0, 112),
    (79, 79),
]

# Zone-specific overrides for zones where generic offsets look unnatural.
ZONE_SLOT_OFFSETS_BY_ZONE: Final[dict[str, list[tuple[int, int]]]] = {
    # Keep house occupants visually around/inside the house footprint.
    "house": [
        (0, 0),
        (24, -8),
        (-24, -8),
        (16, 14),
        (-16, 14),
        (0, -18),
        (30, 12),
        (-30, 12),
        (0, 20),
    ],
}

ACTION_ANIMATIONS: Final[dict[str, str]] = {
    "explore": "walk_loop",
    "eat": "eat_loop",
    "drink": "drink_loop",
    "sleep": "sleep_loop",
    "groom_self": "groom_body_loop",
    "run_wheel": "run_wheel_loop",
    "hide": "hide_loop",
    "socialize": "chirp_anim",
    "play": "play_loop",
    "allogroom": "allogroom_loop",
    "play_invite": "play_invite_anim",
    "share_knowledge": "share_knowledge_anim",
    "chase": "chase_rival_loop",
    "sleep_together": "pair_bond_rest_loop",
    "mount_display": "mating_pair_loop",
    "nurse": "retrieve_pup_anim",
    "rest": "loaf_idle",
    "idle": "loaf_idle",
    "dead": "freeze_hold",
}

ACTION_SFX: Final[dict[str, str | None]] = {
    "explore": "steps_soft",
    "eat": "chewing",
    "drink": "drinking",
    "sleep": None,
    "groom_self": "fur_rustle",
    "run_wheel": "wheel_spin",
    "hide": None,
    "socialize": "chirp",
    "play": "toy_rattle",
    "allogroom": "groom_social",
    "play_invite": "social_chirp",
    "share_knowledge": "queue_murmur",
    "chase": "scuffle",
    "sleep_together": "bonding_coo",
    "mount_display": "mating_coo",
    "nurse": "maternal_hum",
    "rest": None,
    "idle": None,
    "dead": None,
}

AFFECT_BORDER_COLORS: Final[dict[str, tuple[int, int, int]]] = {
    "calm": (180, 220, 180),
    "excited": (220, 200, 100),
    "fearful": (220, 120, 80),
    "aggressive": (200, 80, 80),
    "sleeping": (120, 150, 200),
}

GUI_CONTROLS: Final[list[dict[str, str]]] = [
    {"key": "SPACE", "label": "⏸/▶", "action": "pause_resume"},
    {"key": "S", "label": "💾", "action": "save"},
    {"key": "L", "label": "📂", "action": "load"},
    {"key": "F", "label": "⚡x", "action": "toggle_fast_mode"},
    {"key": "ESC", "label": "✕", "action": "quit"},
    {"key": "+", "label": "+spd", "action": "speed_up"},
    {"key": "-", "label": "-spd", "action": "speed_down"},
]

SIM_SPEED_LEVELS: Final[list[float]] = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
DEFAULT_SPEED: Final[float] = 1.0


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _demo_root() -> Path:
    return _project_root().parent


def resolve_assets_dir(kind: str) -> Path:
    """Resolve asset directory with graceful fallback to legacy layout."""
    kind = str(kind)
    if kind not in {"sprites", "sfx"}:
        raise ValueError(f"Unsupported asset kind: {kind}")

    project_root = _project_root()
    demo_root = _demo_root()
    candidates = [
        project_root / "assets" / kind,
        project_root / kind,
        demo_root / "Tamagochi Chinchilla" / kind,
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def resolve_manifest_path(kind: str) -> Path:
    kind = str(kind)
    filename = "manifest.json" if kind == "sprites" else "sfx_manifest.json"
    return resolve_assets_dir(kind) / filename
