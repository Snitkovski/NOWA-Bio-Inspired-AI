"""Executable app entrypoints for Colony GUI."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path
from typing import Any

from colony_agent import ChinchillaAgent
from genome import GenomeVector
from simulation_runner import SimulationRunner

from .cage_view import get_zone_render_pos
from .colony_gui import ColonyGUI
from .config import ACTION_ANIMATIONS, ACTION_SFX, CAGE_RECT, ZONE_RENDER_COORDS
from .i18n import cause_label, get_language, label, set_language, sex_label, toggle_language, tr
from .utils import format_sim_time

try:
    import pygame  # type: ignore

    PYGAME_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    pygame = None  # type: ignore
    PYGAME_AVAILABLE = False

_LANG_BUTTONS: dict[str, Any] = {}


def _confirm_quit() -> bool:
    """Show a native confirmation dialog asking whether to quit.

    Falls back to allowing quit if a dialog cannot be shown.
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        return True

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        answer = messagebox.askyesno(
            tr("Закрыть симуляцию"),
            tr("Вы действительно хотите закрыть окно симуляции? Несохранённые данные будут потеряны."),
        )
        return bool(answer)
    except Exception:
        return True
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
MAX_FRAME_DT_S = 0.05
SIM_BASE_STEP_S = 1.0 / 12.0
SIM_MAX_STEP_S = 0.25
SIM_MAX_CATCHUP_STEPS = 2
VISUAL_ZONE_TTL_MIN_S = 2.5
VISUAL_ZONE_TTL_MAX_S = 5.5
POSITION_SMOOTHING_RATE = 10.0
AGENT_MAX_SPEED_PX_S = 150.0
AGENT_MIN_SPEED_PX_S = 35.0
SIM_STEP_COST_TARGET_S = 0.012
SIM_STEP_COST_MAX_SCALE = 4.0
SFX_MIN_INTERVAL_S = 0.20
SFX_GLOBAL_DEDUP_S = 0.10
HIGH_POPULATION_THRESHOLD = 50
VERY_HIGH_POPULATION_THRESHOLD = 90
HIGH_POP_LABEL_BUDGET = 24
HIGH_POP_SIM_BATCH_STEPS = 2.5
SIM_ACCUMULATOR_MAX_STEPS = 3.0
MOUNT_OVERLAY_MAX_AGENTS = 80
DIAGNOSTICS_REFRESH_PERIOD_S = 0.25
HIGH_POP_RENDER_FPS = 45
VERY_HIGH_POP_RENDER_FPS = 30
HIGH_POP_LAYOUT_REFRESH_PERIOD_S = 0.10
VERY_HIGH_POP_LAYOUT_REFRESH_PERIOD_S = 0.16
HIGH_POP_PANEL_REFRESH_PERIOD_S = 0.35
VERY_HIGH_POP_PANEL_REFRESH_PERIOD_S = 0.50
NO_NAME_LABELS_THRESHOLD = 90
WINDOW_EXTRA_UI_HEIGHT = 130
STATS_PANEL_HEIGHT = 112
STATS_PANEL_MARGIN_TOP = 4
STATS_PANEL_MARGIN_BOTTOM = 8
STATS_PANEL_BG_COLOR = (245, 239, 229, 225)
STATS_PANEL_BORDER_COLOR = (160, 148, 130)
STATS_TEXT_COLOR = (35, 28, 20)
BAR_BG_COLOR = (210, 198, 180)
BAR_FG_STRESS = (220, 100, 80)
BAR_FG_ENERGY = (80, 160, 220)
BAR_FG_COHESION = (100, 180, 120)
BAR_FG_FOOD = (190, 142, 82)
BAR_FG_HAY = (188, 170, 74)
BAR_FG_WATER = (88, 156, 225)
BAR_WIDTH = 90
BAR_HEIGHT = 8
PANEL_RIGHT_X = CAGE_RECT[0] + CAGE_RECT[2] + 12
PANEL_RIGHT_W = 286
CARD_H_ALIVE = 74
CARD_H_DEAD = 52
CARD_MARGIN = 6
CARD_BG_ALIVE = (252, 249, 242)
CARD_BG_DEAD = (215, 210, 206)
CARD_BORDER_ALIVE = (180, 168, 148)
CARD_BORDER_DEAD = (145, 138, 130)
CARD_TEXT_DEAD = (105, 96, 86)
MAX_DEAD_CARDS = 20

def _draw_small_bar(
    panel: "pygame.Surface",
    *,
    x: int,
    y: int,
    value: float,
    fg: tuple[int, int, int],
    width: int = 42,
) -> None:
    import pygame  # type: ignore

    safe_width = max(10, int(width))
    bg_rect = pygame.Rect(x, y, safe_width, 6)
    pygame.draw.rect(panel, BAR_BG_COLOR, bg_rect, border_radius=2)
    fill = int(safe_width * _clamp01(value))
    if fill > 0:
        pygame.draw.rect(panel, fg, pygame.Rect(x, y, fill, 6), border_radius=2)


def _draw_card_metric(
    panel: "pygame.Surface",
    font_small: "pygame.font.Font",
    *,
    x: int,
    y: int,
    width: int,
    label: str,
    value: float,
    text_color: tuple[int, int, int],
    bar_color: tuple[int, int, int],
) -> None:
    safe_value = _clamp01(value)
    label_surface = font_small.render(label, True, text_color)
    value_surface = font_small.render(f"{safe_value:.2f}", True, text_color)
    panel.blit(label_surface, (x, y))

    gap = 4
    bar_x = x + label_surface.get_width() + gap
    bar_width = max(16, int(width) - label_surface.get_width() - value_surface.get_width() - (gap * 2))
    _draw_small_bar(
        panel,
        x=bar_x,
        y=y + 4,
        value=safe_value,
        fg=bar_color,
        width=bar_width,
    )

    value_x = bar_x + bar_width + gap
    panel.blit(value_surface, (value_x, y))


_AGE_CATEGORY_RU = {
    "juvenile": "детёныш",
    "adult": "взрослый",
}

_ACTION_LABELS_RU = {
    "explore": "исследует",
    "eat": "ест",
    "drink": "пьёт",
    "sleep": "спит",
    "groom_self": "ухаживает за собой",
    "run_wheel": "бежит в колесе",
    "hide": "прячется",
    "socialize": "общается",
    "play": "играет",
    "allogroom": "взаимный груминг",
    "play_invite": "приглашает играть",
    "share_knowledge": "делится знанием",
    "chase": "преследует",
    "sleep_together": "спят вместе",
    "mount_display": "брачное поведение",
    "nurse": "ухаживает за детёнышем",
    "rest": "отдыхает",
    "idle": "бездействует",
}


def _ru_age_category(value: Any) -> str:
    key = str(value or "").strip().lower()
    if key in ("juvenile", "adult"):
        return label("age", key, str(value or ""))
    return str(value or "")


def _ru_action(value: Any) -> str:
    key = str(value or "").strip().lower()
    if key:
        return label("action", key, str(value or ""))
    return str(value or "")


def _draw_right_panel(
    screen: "pygame.Surface",
    font: "pygame.font.Font",
    font_small: "pygame.font.Font",
    *,
    living_agents_data: list[dict[str, Any]],
    dead_memorials: list[Any],
    name_registry: Any | None = None,
    selected_agent_id: str | None,
    scroll_offset: int,
) -> list[tuple["pygame.Rect", str]]:
    """
    Draw right-side cards for living and deceased agents.

    Returns list[(rect, agent_id)] for click hit-testing.
    """
    import pygame  # type: ignore

    panel_rect = pygame.Rect(PANEL_RIGHT_X, 0, PANEL_RIGHT_W, screen.get_height())
    panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    panel.fill((244, 237, 226, 240))
    pygame.draw.rect(panel, (166, 152, 132), panel.get_rect(), 2)

    card_hit_areas: list[tuple[pygame.Rect, str]] = []

    global _LANG_BUTTONS
    living_count = len(living_agents_data)
    title = tr("КОЛОНИЯ ({n} живых)").format(n=living_count)
    panel.blit(font.render(title, True, (35, 28, 20)), (10, 10))
    panel.blit(font_small.render(tr("[L] Родословная"), True, (90, 78, 62)), (10, 30))
    active_lang = get_language()
    placed: dict[str, Any] = {}
    button_x = panel_rect.width - 92
    for code in ("en", "ru"):
        lang_btn = pygame.Rect(button_x, 8, 40, 22)
        button_x += 44
        if code == active_lang:
            pygame.draw.rect(panel, (219, 234, 254), lang_btn, border_radius=4)
            pygame.draw.rect(panel, (37, 99, 168), lang_btn, 2, border_radius=4)
        else:
            pygame.draw.rect(panel, (226, 214, 196), lang_btn, border_radius=4)
            pygame.draw.rect(panel, (120, 104, 84), lang_btn, 1, border_radius=4)
        lang_mark = font_small.render(code.upper(), True, (35, 28, 20))
        panel.blit(lang_mark, lang_mark.get_rect(center=lang_btn.center))
        placed[code] = lang_btn.move(panel_rect.x, panel_rect.y)
    _LANG_BUTTONS = placed

    y = 52 - int(scroll_offset)
    for item in living_agents_data:
        agent_id = str(item.get("agent_id", ""))
        if not agent_id:
            continue
        card_rect = pygame.Rect(8, y, panel_rect.width - 16, CARD_H_ALIVE)
        y += CARD_H_ALIVE + CARD_MARGIN
        if card_rect.bottom < 0 or card_rect.top > panel_rect.height:
            continue

        bg = CARD_BG_ALIVE
        border = CARD_BORDER_ALIVE
        if selected_agent_id and selected_agent_id == agent_id:
            bg = (255, 247, 220)
            border = (208, 170, 86)
        pygame.draw.rect(panel, bg, card_rect, border_radius=6)
        pygame.draw.rect(panel, border, card_rect, 2, border_radius=6)

        sex = sex_label(item.get("sex", ""))
        age_category = _ru_age_category(item.get("age_category", "adult"))
        # Prefer authoritative birth registry name when provided.
        if name_registry is not None:
            try:
                rn = name_registry.get_human_name(agent_id) or agent_id
            except Exception:
                rn = item.get("name", agent_id)
        else:
            rn = item.get("name", agent_id)
        line1 = f"● {rn} {sex} {age_category}"
        panel.blit(font_small.render(line1, True, (35, 28, 20)), (card_rect.x + 8, card_rect.y + 6))

        action = _ru_action(item.get("action", "idle"))
        panel.blit(font_small.render(action, True, (90, 78, 62)), (card_rect.x + 8, card_rect.y + 24))

        stress = _clamp01(item.get("stress", 0.0))
        energy = _clamp01(item.get("energy", 1.0))
        metric_y = card_rect.y + 43
        metric_x = card_rect.x + 8
        metric_width = max(80, (card_rect.width - 16) // 2)
        _draw_card_metric(
            panel,
            font_small,
            x=metric_x,
            y=metric_y,
            width=metric_width,
            label=tr("стресс"),
            value=stress,
            text_color=(80, 60, 55),
            bar_color=BAR_FG_STRESS,
        )
        _draw_card_metric(
            panel,
            font_small,
            x=metric_x + metric_width,
            y=metric_y,
            width=metric_width,
            label=tr("энергия"),
            value=energy,
            text_color=(60, 80, 95),
            bar_color=BAR_FG_ENERGY,
        )

        card_hit_areas.append((card_rect.move(panel_rect.x, panel_rect.y), agent_id))

    dead_cards = list(dead_memorials)[:MAX_DEAD_CARDS]
    if dead_cards:
        y += 4
        panel.blit(font_small.render(tr("── умершие ({n}) ──").format(n=len(dead_cards)), True, (110, 100, 90)), (10, y))
        y += 20
        for memorial in dead_cards:
            agent_id = str(getattr(memorial, "agent_id", ""))
            if not agent_id:
                continue
            card_rect = pygame.Rect(8, y, panel_rect.width - 16, CARD_H_DEAD)
            y += CARD_H_DEAD + CARD_MARGIN
            if card_rect.bottom < 0 or card_rect.top > panel_rect.height:
                continue
            bg = CARD_BG_DEAD
            border = CARD_BORDER_DEAD
            if selected_agent_id and selected_agent_id == agent_id:
                bg = (235, 226, 210)
                border = (175, 145, 92)
            pygame.draw.rect(panel, bg, card_rect, border_radius=6)
            pygame.draw.rect(panel, border, card_rect, 2, border_radius=6)

            if name_registry is not None:
                try:
                    name = str(name_registry.get_human_name(agent_id) or agent_id)
                except Exception:
                    name = str(getattr(memorial, "name", "") or agent_id)
            else:
                name = str(getattr(memorial, "name", "") or agent_id)
            sex = sex_label(getattr(memorial, "sex", ""))
            panel.blit(font_small.render(f"✝ {name} {sex}".rstrip(), True, CARD_TEXT_DEAD), (card_rect.x + 8, card_rect.y + 6))
            cause = cause_label(getattr(memorial, "cause_of_death", "")) or tr("неизвестно")
            lived = format_sim_time(float(getattr(memorial, "age_at_death", 0.0) or 0.0))
            offspring = int(getattr(memorial, "total_offspring", 0) or 0)
            line2 = (
                f"{cause} | {tr('прожил {lived}').format(lived=lived)} | "
                f"{tr('потомков {n}').format(n=offspring)}"
            )
            panel.blit(font_small.render(line2, True, CARD_TEXT_DEAD), (card_rect.x + 8, card_rect.y + 24))

            card_hit_areas.append((card_rect.move(panel_rect.x, panel_rect.y), agent_id))

    screen.blit(panel, panel_rect.topleft)
    return card_hit_areas


def _handle_panel_click(
    mouse_pos: tuple[int, int],
    card_hit_areas: list[tuple["pygame.Rect", str]],
) -> str | None:
    for rect, agent_id in reversed(card_hit_areas):
        if rect.collidepoint(mouse_pos):
            return agent_id
    return None


def build_demo_runner(agent_count: int = 4) -> SimulationRunner:
    """Create a demo runner with a small starter colony."""
    safe_count = max(1, int(agent_count))
    runner = SimulationRunner()
    rng = random.Random()
    for idx in range(safe_count):
        sex = "F" if idx % 2 == 0 else "M"
        runner.add_agent(
            ChinchillaAgent(
                sex=sex,
                generation=0,
                genome=GenomeVector.random(rng),
            )
        )
    return runner


def run_headless_ticks(agent_count: int = 4, duration_s: float = 2.0, dt: float = 0.1) -> dict[str, Any]:
    """Run simulation and GUI read-model without pygame window."""
    runner = build_demo_runner(agent_count=agent_count)
    gui = ColonyGUI(runner)
    remaining = max(0.0, float(duration_s))
    step = max(0.01, float(dt))
    while remaining > 0.0:
        gui._sim_tick(min(step, remaining))
        gui._update_snapshot()
        remaining -= step
    return gui.get_render_state()


def _load_sprite_clip(
    sprite_manifest: dict[str, Any],
    animation_id: str,
    sprites_dir: Path,
    cache: dict[str, tuple[list["pygame.Surface"], float]],
) -> "tuple[list[pygame.Surface], float] | None":
    if animation_id in cache:
        return cache[animation_id]
    entry = sprite_manifest.get(animation_id)
    if not isinstance(entry, dict):
        return None
    file_name = str(entry.get("file", ""))
    if not file_name:
        return None
    frame_w = int(entry.get("frame_w", 96) or 96)
    frame_h = int(entry.get("frame_h", 96) or 96)
    image_path = sprites_dir / file_name
    if not image_path.exists():
        return None
    try:
        image = pygame.image.load(str(image_path)).convert_alpha()
        frames_count = max(1, int(entry.get("frames", 1) or 1))
        fps = max(1.0, float(entry.get("fps", 8.0) or 8.0))
        sheet_w = image.get_width()
        step_w = max(1, sheet_w // frames_count)
        clips: list[pygame.Surface] = []
        for i in range(frames_count):
            src_x = i * step_w
            surface = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
            surface.blit(image, (0, 0), (src_x, 0, frame_w, frame_h))
            clips.append(surface)
        cache[animation_id] = (clips, fps)
        return cache[animation_id]
    except Exception:
        return None


def _load_sfx_clip(
    sfx_manifest: dict[str, Any],
    sfx_id: str,
    sfx_dir: Path,
    cache: dict[str, "pygame.mixer.Sound"],
) -> "pygame.mixer.Sound | None":
    if not sfx_id:
        return None
    if sfx_id in cache:
        return cache[sfx_id]
    entry = sfx_manifest.get(sfx_id)
    if not isinstance(entry, dict):
        return None
    file_name = str(entry.get("file", ""))
    if not file_name:
        return None
    sound_path = sfx_dir / file_name
    if not sound_path.exists():
        return None
    try:
        clip = pygame.mixer.Sound(str(sound_path))
        cache[sfx_id] = clip
        return clip
    except Exception:
        return None


def _compute_sfx_interval_s(sfx_manifest: dict[str, Any], sfx_id: str) -> float:
    entry = sfx_manifest.get(str(sfx_id))
    if not isinstance(entry, dict):
        return SFX_MIN_INTERVAL_S
    duration_s = float(entry.get("duration_s", SFX_MIN_INTERVAL_S) or SFX_MIN_INTERVAL_S)
    return max(SFX_MIN_INTERVAL_S, min(2.2, duration_s * 0.9))


def _play_action_sfx(
    *,
    action: str,
    sfx_id: str | None,
    sfx_manifest: dict[str, Any],
    sfx_dir: Path,
    sfx_cache: dict[str, "pygame.mixer.Sound"],
    action_by_agent: dict[str, str],
    played_by_agent: dict[str, float],
    played_by_sfx: dict[str, float],
    agent_id: str,
    now_s: float,
) -> None:
    sound_id = str(sfx_id or "").strip()
    if not sound_id:
        action_by_agent[agent_id] = str(action)
        return

    previous_action = action_by_agent.get(agent_id)
    interval_s = _compute_sfx_interval_s(sfx_manifest, sound_id)
    last_agent_play = float(played_by_agent.get(agent_id, -1e9))
    last_global_play = float(played_by_sfx.get(sound_id, -1e9))

    due_to_action_change = previous_action != str(action)
    due_to_loop_interval = (now_s - last_agent_play) >= interval_s
    if (not due_to_action_change) and (not due_to_loop_interval):
        return
    if (now_s - last_global_play) < min(SFX_GLOBAL_DEDUP_S, interval_s * 0.25):
        return

    clip = _load_sfx_clip(
        sfx_manifest=sfx_manifest,
        sfx_id=sound_id,
        sfx_dir=sfx_dir,
        cache=sfx_cache,
    )
    if clip is None:
        return
    try:
        clip.play()
    except Exception:
        return

    action_by_agent[agent_id] = str(action)
    played_by_agent[agent_id] = now_s
    played_by_sfx[sound_id] = now_s


ACTION_VISUAL_ZONE_HINTS: dict[str, list[str]] = {
    "eat": ["bowl_pellets", "bowl_hay"],
    "drink": ["waterer"],
    "sleep": ["house", "shelf_lower", "shelf_mid"],
    "groom_self": ["floor", "house"],
    "run_wheel": ["wheel"],
    "hide": ["house"],
    "socialize": ["floor", "toy", "corner"],
    "play": ["toy", "floor", "dustbath", "object"],
    "allogroom": ["house", "floor", "shelf_lower"],
    "play_invite": ["toy", "floor", "corner"],
    "share_knowledge": ["floor", "shelf_lower", "house"],
    "sleep_together": ["house", "shelf_lower"],
    "chase": ["floor", "corner", "shelf_lower"],
    "mount_display": ["house", "floor", "corner"],
    "nurse": ["house"],
    "rest": ["floor", "house", "shelf_lower"],
    "explore": ["floor", "shelf_lower", "shelf_mid", "shelf_upper", "corner", "object", "dustbath", "bars"],
    "idle": ["floor", "house", "toy"],
}

EXCLUSIVE_VISUAL_ZONE_CAPACITY: dict[str, int] = {
    "wheel": 1,
    "dustbath": 1,
}


VALID_RENDER_ZONES = {
    zone_name
    for zone_name, coords in ZONE_RENDER_COORDS.items()
    if coords is not None
}


def _normalize_visual_zone(zone: Any) -> str:
    zone_name = str(zone)
    if zone_name in VALID_RENDER_ZONES:
        return zone_name
    return "floor"


def _resolve_visual_animation_id(
    *,
    action: str,
    visual_zone: str,
    preferred_animation_id: str,
) -> str:
    # Wheel-running sprite must only appear when the agent is in the wheel zone.
    if action == "run_wheel" and visual_zone != "wheel":
        return ACTION_ANIMATIONS.get("explore", "walk_loop")
    return preferred_animation_id


def _smooth_position_step(
    *,
    current_x: float,
    current_y: float,
    target_x: float,
    target_y: float,
    dt: float,
) -> tuple[float, float]:
    safe_dt = max(0.0, min(float(dt), MAX_FRAME_DT_S))
    if safe_dt <= 0.0:
        return (current_x, current_y)

    dx = target_x - current_x
    dy = target_y - current_y
    dist = math.hypot(dx, dy)
    if dist <= 1e-6:
        return (target_x, target_y)

    alpha = 1.0 - math.exp(-POSITION_SMOOTHING_RATE * safe_dt)
    eased_step = max(AGENT_MIN_SPEED_PX_S * safe_dt, dist * alpha)
    max_step = AGENT_MAX_SPEED_PX_S * safe_dt
    step = min(dist, max_step, eased_step)
    step_ratio = step / dist
    next_x = current_x + dx * step_ratio
    next_y = current_y + dy * step_ratio
    if abs(target_x - next_x) < 0.2:
        next_x = target_x
    if abs(target_y - next_y) < 0.2:
        next_y = target_y
    return (next_x, next_y)


def _adaptive_sim_step_s(agent_count: int) -> float:
    safe_count = max(1, int(agent_count))
    extra_agents = max(0, safe_count - 4)
    adaptive = SIM_BASE_STEP_S + extra_agents * 0.004
    return min(SIM_MAX_STEP_S, adaptive)


def _apply_sim_load_adaptation(base_step_s: float, step_cost_ema_s: float) -> float:
    base = max(0.001, float(base_step_s))
    cost = max(0.0, float(step_cost_ema_s))
    if cost <= SIM_STEP_COST_TARGET_S:
        return base
    scale = min(SIM_STEP_COST_MAX_SCALE, cost / SIM_STEP_COST_TARGET_S)
    return min(SIM_MAX_STEP_S, base * scale)


def _prune_agent_caches(active_agent_ids: set[str], *caches: dict[str, Any]) -> None:
    if not caches:
        return
    for cache in caches:
        stale_keys = [agent_id for agent_id in list(cache.keys()) if agent_id not in active_agent_ids]
        for agent_id in stale_keys:
            cache.pop(agent_id, None)


def _clamp01(value: Any) -> float:
    try:
        parsed = float(value)
    except Exception:
        return 0.0
    if parsed != parsed:
        return 0.0
    return max(0.0, min(1.0, parsed))


def _risk_bar_color(risk: float) -> tuple[int, int, int]:
    safe_risk = _clamp01(risk)
    if safe_risk < 0.3:
        return (100, 180, 120)
    if safe_risk < 0.6:
        return (220, 180, 80)
    return (200, 80, 80)


def _draw_metric_bar(
    panel: "pygame.Surface",
    font_small: "pygame.font.Font",
    text_surface_cache: dict[tuple[str, tuple[int, int, int]], "pygame.Surface"],
    *,
    x: int,
    y: int,
    label: str,
    value: float,
    color: tuple[int, int, int],
) -> int:
    safe_value = _clamp01(value)
    label_surface = _get_cached_text_surface(
        text_surface_cache,
        font_small,
        label,
        STATS_TEXT_COLOR,
    )
    panel.blit(label_surface, (x, y))

    bar_x = x + label_surface.get_width() + 5
    bar_y = y + 4
    bar_rect = pygame.Rect(bar_x, bar_y, BAR_WIDTH, BAR_HEIGHT)
    pygame.draw.rect(panel, BAR_BG_COLOR, bar_rect, border_radius=3)
    fill_width = int(round(BAR_WIDTH * safe_value))
    if fill_width > 0:
        pygame.draw.rect(
            panel,
            color,
            pygame.Rect(bar_x, bar_y, fill_width, BAR_HEIGHT),
            border_radius=3,
        )

    value_surface = _get_cached_text_surface(
        text_surface_cache,
        font_small,
        f"{safe_value:.2f}",
        STATS_TEXT_COLOR,
    )
    value_x = bar_x + BAR_WIDTH + 6
    panel.blit(value_surface, (value_x, y))
    return value_x + value_surface.get_width() + 16


def _draw_stats_panel(
    screen: "pygame.Surface",
    font_small: "pygame.font.Font",
    text_surface_cache: dict[tuple[str, tuple[int, int, int]], "pygame.Surface"],
    *,
    sim_time_text: str,
    speed: float,
    paused: bool,
    audio_enabled: bool,
    diagnostics: dict[str, int | float],
    population_stats: dict[str, Any],
    resources: dict[str, Any],
) -> None:
    """Draw one consolidated status panel below cage with readable metrics."""
    try:
        if len(text_surface_cache) > 2048:
            text_surface_cache.clear()

        cage_x, cage_y, cage_w, cage_h = CAGE_RECT
        panel_x = int(cage_x)
        panel_y = int(cage_y + cage_h + STATS_PANEL_MARGIN_TOP)
        available_height = max(18, screen.get_height() - panel_y - STATS_PANEL_MARGIN_BOTTOM)
        panel_h = min(STATS_PANEL_HEIGHT, available_height)
        panel_w = min(cage_w, screen.get_width() - panel_x - 8)

        panel_rect = pygame.Rect(
            panel_x,
            panel_y,
            panel_w,
            panel_h,
        )
        panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel.fill(STATS_PANEL_BG_COLOR)
        pygame.draw.rect(panel, STATS_PANEL_BORDER_COLOR, panel.get_rect(), 1, border_radius=4)

        has_stats = isinstance(population_stats, dict) and bool(population_stats.get("has_data", False))
        if has_stats:
            agent_count = int(population_stats.get("agent_count", 0) or 0)
            female_count = int(population_stats.get("female_count", 0) or 0)
            male_count = int(population_stats.get("male_count", 0) or 0)
            juvenile_count = int(population_stats.get("juvenile_count", 0) or 0)
            pregnant_count = int(population_stats.get("pregnant_count", 0) or 0)
            mean_stress = _clamp01(population_stats.get("mean_stress", 0.0))
            mean_energy = _clamp01(population_stats.get("mean_energy", 0.0))
            social_cohesion = _clamp01(population_stats.get("social_cohesion", 0.0))
            extinction_risk = _clamp01(population_stats.get("extinction_risk", 0.0))
            total_births = int(population_stats.get("total_births", 0) or 0)
            total_deaths = int(population_stats.get("total_deaths", 0) or 0)
            total_known_pairs = int(population_stats.get("total_known_pairs", 0) or 0)
            bonded_pairs = int(population_stats.get("bonded_pairs", 0) or 0)
        else:
            agent_count = 0
            female_count = 0
            male_count = 0
            juvenile_count = 0
            pregnant_count = int(diagnostics.get("pregnant", 0) or 0)
            mean_stress = 0.0
            mean_energy = 0.0
            social_cohesion = 0.0
            extinction_risk = 0.0
            total_births = 0
            total_deaths = 0
            total_known_pairs = 0
            bonded_pairs = 0

        mature_f = int(diagnostics.get("mature_f", 0) or 0)
        mature_m = int(diagnostics.get("mature_m", 0) or 0)
        estrus_f = int(diagnostics.get("estrus_f", 0) or 0)
        avg_age_s = float(diagnostics.get("avg_age_s", 0.0) or 0.0)
        food_level = _clamp01(resources.get("food_pellets", 0.0))
        hay_level = _clamp01(resources.get("hay", 0.0))
        water_level = _clamp01(resources.get("water", 0.0))

        line1 = tr(
            "Время: {time}   Агентов: {n} (самок: {f}, самцов: {m})   Средний возраст: {age}"
        ).format(
            time=sim_time_text,
            n=agent_count,
            f=female_count,
            m=male_count,
            age=format_sim_time(avg_age_s),
        )
        line2 = tr(
            "Половозрелые: самки {f}, самцы {m}   Эструс (самки): {estrus}   "
            "Беременные: {preg}   Рождений/смертей: {births}/{deaths}   "
            "Связи/крепкие пары: {pairs}/{bonded}"
        ).format(
            f=mature_f,
            m=mature_m,
            estrus=estrus_f,
            preg=pregnant_count,
            births=total_births,
            deaths=total_deaths,
            pairs=total_known_pairs,
            bonded=bonded_pairs,
        )
        line3 = tr(
            "Скорость: x{speed:.1f}   Пауза: {paused}   Звук: {sound}   "
            "Управление: SPACE пауза, +/- скорость, M звук, L родословная, A анализ роя, G язык, ESC выход"
        ).format(
            speed=speed,
            paused=tr("да") if paused else tr("нет"),
            sound=tr("вкл") if audio_enabled else tr("выкл"),
        )

        panel.blit(
            _get_cached_text_surface(text_surface_cache, font_small, line1, STATS_TEXT_COLOR),
            (8, 6),
        )
        panel.blit(
            _get_cached_text_surface(text_surface_cache, font_small, line2, STATS_TEXT_COLOR),
            (8, 24),
        )

        bar_y = 44
        next_x = _draw_metric_bar(
            panel,
            font_small,
            text_surface_cache,
            x=8,
            y=bar_y,
            label=tr("Стресс"),
            value=mean_stress,
            color=BAR_FG_STRESS,
        )
        next_x = _draw_metric_bar(
            panel,
            font_small,
            text_surface_cache,
            x=next_x,
            y=bar_y,
            label=tr("Энергия"),
            value=mean_energy,
            color=BAR_FG_ENERGY,
        )
        next_x = _draw_metric_bar(
            panel,
            font_small,
            text_surface_cache,
            x=next_x,
            y=bar_y,
            label=tr("Сплоченность"),
            value=social_cohesion,
            color=BAR_FG_COHESION,
        )
        _draw_metric_bar(
            panel,
            font_small,
            text_surface_cache,
            x=next_x,
            y=bar_y,
            label=tr("Риск вымирания"),
            value=extinction_risk,
            color=_risk_bar_color(extinction_risk),
        )

        resource_bar_y = 64
        resource_next_x = _draw_metric_bar(
            panel,
            font_small,
            text_surface_cache,
            x=8,
            y=resource_bar_y,
            label=tr("Корм"),
            value=food_level,
            color=BAR_FG_FOOD,
        )
        resource_next_x = _draw_metric_bar(
            panel,
            font_small,
            text_surface_cache,
            x=resource_next_x,
            y=resource_bar_y,
            label=tr("Сено"),
            value=hay_level,
            color=BAR_FG_HAY,
        )
        _draw_metric_bar(
            panel,
            font_small,
            text_surface_cache,
            x=resource_next_x,
            y=resource_bar_y,
            label=tr("Вода"),
            value=water_level,
            color=BAR_FG_WATER,
        )

        panel.blit(
            _get_cached_text_surface(text_surface_cache, font_small, line3, STATS_TEXT_COLOR),
            (8, 86),
        )

        screen.blit(panel, panel_rect.topleft)
    except Exception:
        return


def _collect_reproduction_diagnostics(runner: Any) -> dict[str, int | float]:
    agents = list(getattr(runner, "agents", []) or [])
    mature_f = 0
    mature_m = 0
    estrus_f = 0
    pregnant = 0
    age_total_s = 0.0

    for agent in agents:
        sex = str(getattr(agent, "sex", "")).upper()
        is_mature = bool(getattr(agent, "is_mature", False))
        try:
            age_total_s += max(0.0, float(getattr(agent, "age", 0.0) or 0.0))
        except Exception:
            age_total_s += 0.0
        if is_mature and sex == "F":
            mature_f += 1
        elif is_mature and sex == "M":
            mature_m += 1

        if bool(getattr(agent, "is_pregnant", False)):
            pregnant += 1

        heat_cycle = getattr(agent, "heat_cycle", None)
        if sex == "F" and heat_cycle is not None:
            phase = str(getattr(heat_cycle, "phase", ""))
            if phase == "estrus":
                estrus_f += 1

    return {
        "mature_f": mature_f,
        "mature_m": mature_m,
        "estrus_f": estrus_f,
        "pregnant": pregnant,
        "avg_age_s": (age_total_s / len(agents)) if agents else 0.0,
    }


def _get_cached_text_surface(
    cache: dict[tuple[str, tuple[int, int, int]], "pygame.Surface"],
    font: "pygame.font.Font",
    text: str,
    color: tuple[int, int, int],
) -> "pygame.Surface":
    key = (text, color)
    surface = cache.get(key)
    if surface is not None:
        return surface
    surface = font.render(text, True, color)
    cache[key] = surface
    return surface


def _pick_local_zone(
    *,
    sanitized_hints: list[str],
    previous_zone: str | None,
    rng: random.Random,
) -> str:
    if not sanitized_hints:
        return "floor"
    unique_hints = list(dict.fromkeys(sanitized_hints))
    if len(unique_hints) <= 1:
        return unique_hints[0]

    previous = _normalize_visual_zone(previous_zone or "floor")
    previous_pos = ZONE_RENDER_COORDS.get(previous)
    if previous_pos is None:
        return rng.choice(unique_hints)

    ranked = sorted(
        unique_hints,
        key=lambda zone: math.hypot(
            float((ZONE_RENDER_COORDS.get(zone) or previous_pos)[0] - previous_pos[0]),
            float((ZONE_RENDER_COORDS.get(zone) or previous_pos)[1] - previous_pos[1]),
        ),
    )
    shortlist = ranked[: min(3, len(ranked))]
    return rng.choice(shortlist)


def _resolve_visual_zone(
    *,
    agent: dict[str, Any],
    dt: float,
    rng: random.Random,
    state_by_agent: dict[str, dict[str, Any]],
    wheel_lock_owner: str | None = None,
) -> str:
    agent_id = str(agent["agent_id"])
    action = str(agent.get("action", "idle"))
    fallback_zone = _normalize_visual_zone(agent.get("position", "floor"))
    if action == "run_wheel":
        # Show wheel only for the lock owner, otherwise keep fallback.
        if wheel_lock_owner and wheel_lock_owner == agent_id:
            return "wheel"
        if wheel_lock_owner and wheel_lock_owner != agent_id:
            return fallback_zone if fallback_zone != "wheel" else "floor"
        # Without lock info, wheel is shown only when agent is at wheel.
        if fallback_zone == "wheel":
            return "wheel"
        return fallback_zone if fallback_zone != "wheel" else "floor"

    # Keep visual placement aligned with simulation position so GUI does not
    # fight NOWA movement decisions.
    state_by_agent[agent_id] = {
        "action": action,
        "zone": fallback_zone,
        "ttl": rng.uniform(VISUAL_ZONE_TTL_MIN_S, VISUAL_ZONE_TTL_MAX_S),
    }

    hints = ACTION_VISUAL_ZONE_HINTS.get(action)
    if not hints:
        return fallback_zone

    sanitized_hints = [_normalize_visual_zone(zone) for zone in hints]
    if fallback_zone in sanitized_hints:
        return fallback_zone

    item = state_by_agent.get(agent_id)
    needs_new_zone = (
        item is None
        or str(item.get("action")) != action
        or float(item.get("ttl", 0.0)) <= 0.0
    )
    if needs_new_zone:
        previous_zone = None if item is None else str(item.get("zone", "floor"))
        zone = _pick_local_zone(
            sanitized_hints=sanitized_hints,
            previous_zone=previous_zone,
            rng=rng,
        )
        state_by_agent[agent_id] = {
            "action": action,
            "zone": zone,
            "ttl": rng.uniform(VISUAL_ZONE_TTL_MIN_S, VISUAL_ZONE_TTL_MAX_S),
        }
        return zone

    item["ttl"] = float(item["ttl"]) - float(dt)
    return _normalize_visual_zone(item["zone"])


def _pick_capacity_fallback(
    *,
    action: str,
    fallback_zone: str,
    zone_counts: dict[str, int],
    rng: random.Random,
) -> str:
    normalized_fallback = _normalize_visual_zone(fallback_zone)
    candidates: list[str]
    if action == "run_wheel":
        candidates = [normalized_fallback, "floor", "shelf_lower", "toy", "house", "corner"]
    else:
        candidates = [normalized_fallback, "floor", "house", "toy", "corner"]

    seen: set[str] = set()
    deduped_candidates: list[str] = []
    for zone in candidates:
        zone_name = _normalize_visual_zone(zone)
        if zone_name in seen:
            continue
        seen.add(zone_name)
        deduped_candidates.append(zone_name)

    for zone in deduped_candidates:
        cap = EXCLUSIVE_VISUAL_ZONE_CAPACITY.get(zone)
        if cap is None or zone_counts.get(zone, 0) < cap:
            return zone

    relaxed = [zone for zone in deduped_candidates if zone not in EXCLUSIVE_VISUAL_ZONE_CAPACITY]
    if relaxed:
        return rng.choice(relaxed)
    return "floor"


def _draw_furniture(screen: "pygame.Surface", font_dbg: "pygame.font.Font") -> None:
    """Draw full cage furniture layout compatible with Tamagochi scene."""
    s = screen

    # Floor baseline
    pygame.draw.line(s, (160, 148, 130), (60, 630), (964, 630), 3)

    # Right-side bars
    for bx in range(900, 975, 14):
        pygame.draw.line(s, (130, 120, 110), (bx, 60), (bx, 630), 2)
    for by in (60, 200, 400, 630):
        pygame.draw.line(s, (110, 100, 90), (900, by), (974, by), 3)

    # Door
    door_rect = pygame.Rect(910, 490, 55, 140)
    pygame.draw.rect(s, (95, 80, 60), door_rect, 0)
    pygame.draw.rect(s, (70, 58, 40), door_rect, 3)
    for hy in (510, 560, 610):
        pygame.draw.circle(s, (140, 120, 90), (918, hy), 3)
    s.blit(font_dbg.render(tr("дверь"), True, (30, 20, 10)), (912, 635))

    # Left wall/corner
    pygame.draw.line(s, (150, 140, 128), (60, 60), (60, 630), 3)
    pygame.draw.arc(s, (140, 130, 118), pygame.Rect(62, 610, 36, 24), 0, math.pi / 2, 2)

    # House
    pygame.draw.rect(s, (185, 158, 118), (72, 468, 120, 110))
    pygame.draw.polygon(s, (158, 128, 88), [(66, 470), (132, 390), (198, 470)])
    pygame.draw.rect(s, (60, 45, 30), (110, 510, 42, 68))
    pygame.draw.line(s, (138, 110, 72), (66, 470), (132, 390), 2)
    pygame.draw.line(s, (138, 110, 72), (132, 390), (198, 470), 2)
    s.blit(font_dbg.render(tr("домик"), True, (30, 20, 10)), (92, 620))

    # Dustbath
    pygame.draw.rect(s, (160, 145, 125), (210, 574, 100, 44), border_radius=6)
    pygame.draw.rect(s, (130, 115, 95), (210, 574, 100, 44), 2, border_radius=6)
    pygame.draw.rect(s, (210, 195, 168), (214, 578, 92, 36), border_radius=4)
    for i in range(18):
        gx = 218 + (i * 37) % 84
        gy = 582 + (i * 13) % 28
        pygame.draw.circle(s, (195, 178, 148), (gx, gy), 2)
    s.blit(font_dbg.render(tr("купалка"), True, (30, 20, 10)), (218, 620))

    # Water bottle
    pygame.draw.rect(s, (190, 215, 235), (330, 540, 30, 55), border_radius=5)
    pygame.draw.rect(s, (150, 178, 200), (330, 540, 30, 55), 2, border_radius=5)
    pygame.draw.rect(s, (130, 175, 220, 160), (333, 565, 24, 27), border_radius=3)
    pygame.draw.rect(s, (160, 148, 130), (341, 595, 8, 14))
    pygame.draw.circle(s, (140, 128, 110), (345, 610), 4)
    pygame.draw.rect(s, (130, 120, 110), (326, 548, 6, 20))
    pygame.draw.rect(s, (130, 120, 110), (326, 572, 6, 16))
    s.blit(font_dbg.render(tr("поилка"), True, (30, 20, 10)), (326, 620))

    # Pellets bowl
    pygame.draw.ellipse(s, (155, 138, 115), (390, 600, 80, 28))
    pygame.draw.ellipse(s, (130, 115, 92), (390, 600, 80, 28), 2)
    for px, py in [(404, 605), (418, 603), (432, 606), (446, 604), (412, 610), (428, 610), (442, 609)]:
        pygame.draw.ellipse(s, (180, 148, 95), (px, py, 8, 5))
    s.blit(font_dbg.render(tr("корм"), True, (30, 20, 10)), (414, 630))

    # Hay rack
    pygame.draw.rect(s, (148, 125, 80), (472, 580, 76, 44), 2)
    for rx in range(478, 544, 10):
        pygame.draw.line(s, (148, 125, 80), (rx, 580), (rx, 624), 1)
    for hx, hy, ang in [
        (478, 572, -15),
        (486, 568, -5),
        (495, 570, 8),
        (504, 567, 0),
        (513, 570, -10),
        (522, 568, 5),
        (532, 572, 12),
        (540, 570, -3),
    ]:
        ex = hx + int(18 * math.cos(math.radians(ang - 80)))
        ey = hy + int(18 * math.sin(math.radians(ang - 80)))
        pygame.draw.line(s, (195, 172, 65), (hx, hy), (ex, ey), 2)
    s.blit(font_dbg.render(tr("сено"), True, (30, 20, 10)), (494, 630))

    # Mineral
    pts = [(596, 596), (610, 590), (628, 592), (638, 600), (634, 614), (618, 618), (602, 612)]
    pygame.draw.polygon(s, (210, 205, 195), pts)
    pygame.draw.polygon(s, (170, 163, 150), pts, 2)
    for gx, gy in [(606, 600), (618, 596), (626, 604), (612, 610)]:
        pygame.draw.circle(s, (240, 238, 232), (gx, gy), 2)
    s.blit(font_dbg.render(tr("минерал"), True, (30, 20, 10)), (596, 630))

    # Litter
    pygame.draw.rect(s, (155, 140, 120), (828, 568, 88, 52), border_radius=4)
    pygame.draw.rect(s, (120, 108, 88), (828, 568, 88, 52), 2, border_radius=4)
    pygame.draw.rect(s, (185, 172, 148), (832, 572, 80, 44), border_radius=3)
    for i in range(20):
        lx = 836 + (i * 31) % 72
        ly = 576 + (i * 17) % 36
        pygame.draw.circle(s, (170, 156, 132), (lx, ly), 2)
    pygame.draw.rect(s, (128, 114, 90), (828, 568, 88, 12), border_radius=4)
    s.blit(font_dbg.render(tr("лоток"), True, (30, 20, 10)), (846, 630))

    # Wheel
    wh_cx, wh_cy = 730, 418
    pygame.draw.rect(s, (150, 138, 122), (718, 468, 24, 40))
    pygame.draw.rect(s, (150, 138, 122), (704, 504, 52, 8))
    pygame.draw.circle(s, (165, 152, 135), (wh_cx, wh_cy), 50, 5)
    pygame.draw.circle(s, (165, 152, 135), (wh_cx, wh_cy), 36, 2)
    for i in range(8):
        ang = math.radians(i * 45)
        x1 = int(wh_cx + 10 * math.cos(ang))
        y1 = int(wh_cy + 10 * math.sin(ang))
        x2 = int(wh_cx + 48 * math.cos(ang))
        y2 = int(wh_cy + 48 * math.sin(ang))
        pygame.draw.line(s, (150, 138, 122), (x1, y1), (x2, y2), 2)
    pygame.draw.circle(s, (140, 128, 110), (wh_cx, wh_cy), 8)
    s.blit(font_dbg.render(tr("колесо"), True, (30, 20, 10)), (690, 530))

    # Toy
    toy_x, toy_y = 760, 510
    pygame.draw.line(s, (160, 138, 100), (toy_x, 420), (toy_x, toy_y - 20), 1)
    for ry in (toy_y - 18, toy_y, toy_y + 18):
        pygame.draw.ellipse(s, (185, 155, 100), (toy_x - 14, ry - 8, 28, 16), 3)
    pygame.draw.circle(s, (195, 175, 110), (toy_x, toy_y + 22), 7, 2)
    s.blit(font_dbg.render(tr("игрушка"), True, (30, 20, 10)), (toy_x - 24, toy_y + 36))

    # Object (cardboard box)
    pygame.draw.rect(s, (195, 168, 118), (768, 510, 64, 50))
    pygame.draw.rect(s, (165, 140, 90), (768, 510, 64, 50), 2)
    pygame.draw.line(s, (165, 140, 90), (768, 510), (784, 492), 2)
    pygame.draw.line(s, (165, 140, 90), (816, 492), (832, 510), 2)
    pygame.draw.line(s, (165, 140, 90), (832, 510), (816, 492), 2)
    pygame.draw.ellipse(s, (80, 65, 45), (786, 524, 28, 22))
    s.blit(font_dbg.render(tr("объект"), True, (30, 20, 10)), (772, 565))

    # Shelves
    shelf_c = (178, 152, 116)
    shelf_e = (148, 124, 88)
    pygame.draw.rect(s, shelf_c, (500, 424, 160, 14))
    pygame.draw.rect(s, shelf_e, (500, 424, 160, 14), 1)
    pygame.draw.line(s, shelf_e, (510, 438), (496, 480), 2)
    pygame.draw.line(s, shelf_e, (650, 438), (664, 480), 2)

    pygame.draw.rect(s, shelf_c, (400, 304, 160, 12))
    pygame.draw.rect(s, shelf_e, (400, 304, 160, 12), 1)
    pygame.draw.line(s, shelf_e, (410, 316), (396, 358), 2)
    pygame.draw.line(s, shelf_e, (550, 316), (564, 358), 2)

    pygame.draw.rect(s, shelf_c, (300, 190, 160, 12))
    pygame.draw.rect(s, shelf_e, (300, 190, 160, 12), 1)
    pygame.draw.line(s, shelf_e, (310, 202), (296, 244), 2)
    pygame.draw.line(s, shelf_e, (450, 202), (464, 244), 2)

    shadow = pygame.Surface((904, 18), pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 22))
    s.blit(shadow, (60, 630))


def _draw_heart_icon(
    screen: "pygame.Surface",
    *,
    center_x: int,
    center_y: int,
    size: int,
    color: tuple[int, int, int],
) -> None:
    radius = max(2, int(size // 3))
    left = (int(center_x - radius), int(center_y - radius))
    right = (int(center_x + radius), int(center_y - radius))
    tip = (int(center_x), int(center_y + size))
    pygame.draw.circle(screen, color, left, radius)
    pygame.draw.circle(screen, color, right, radius)
    pygame.draw.polygon(
        screen,
        color,
        [
            (int(center_x - (2 * radius)), int(center_y - radius)),
            (int(center_x + (2 * radius)), int(center_y - radius)),
            tip,
        ],
    )


def _draw_mount_display_overlays(
    screen: "pygame.Surface",
    *,
    center_by_agent: dict[str, tuple[int, int]],
    runner: Any,
    now_s: float,
) -> None:
    agents = list(getattr(runner, "agents", []) or [])
    by_id = {str(agent.agent_id): agent for agent in agents if str(getattr(agent, "agent_id", ""))}
    painted_pairs: set[frozenset[str]] = set()

    for agent in agents:
        agent_id = str(getattr(agent, "agent_id", ""))
        if not agent_id:
            continue
        if str(getattr(agent, "current_action", "")) != "mount_display":
            continue
        mate_id = str(getattr(agent, "_current_mate_id", "") or "")
        if not mate_id:
            continue
        pair_key = frozenset({agent_id, mate_id})
        if pair_key in painted_pairs:
            continue
        mate = by_id.get(mate_id)
        if mate is None:
            continue
        if str(getattr(mate, "current_action", "")) != "mount_display":
            continue
        center_a = center_by_agent.get(agent_id)
        center_b = center_by_agent.get(mate_id)
        if center_a is None or center_b is None:
            continue

        mid_x = int((center_a[0] + center_b[0]) * 0.5)
        mid_y = int((center_a[1] + center_b[1]) * 0.5) - 48
        pulse = 0.5 + (0.5 * math.sin(now_s * 6.0))
        color = (
            int(210 + 35 * pulse),
            int(90 + 20 * pulse),
            int(120 + 20 * pulse),
        )
        size = 10 + int(3 * pulse)
        _draw_heart_icon(screen, center_x=mid_x, center_y=mid_y, size=size, color=color)
        _draw_heart_icon(
            screen,
            center_x=mid_x + 16,
            center_y=mid_y + 6,
            size=max(6, size - 3),
            color=(255, 185, 195),
        )
        painted_pairs.add(pair_key)


def _paint_static_scene(static_scene: "pygame.Surface", font: "pygame.font.Font") -> None:
    static_scene.fill((235, 228, 215))
    cage_x, cage_y, cage_w, cage_h = CAGE_RECT
    pygame.draw.rect(static_scene, (200, 190, 175), pygame.Rect(cage_x, cage_y, cage_w, cage_h))
    pygame.draw.rect(static_scene, (100, 85, 70), pygame.Rect(cage_x, cage_y, cage_w, cage_h), 3)
    _draw_furniture(static_scene, font)


def _apply_language_chrome(gui: Any, static_scene: "pygame.Surface", font: "pygame.font.Font") -> None:
    gui.swarm_analytics.mark_dirty()
    _paint_static_scene(static_scene, font)
    try:
        pygame.display.set_caption(tr("Colony GUI — симуляция шиншилл"))
    except Exception:
        pass


def _set_demo_language(
    lang: str,
    gui: Any,
    static_scene: "pygame.Surface",
    font: "pygame.font.Font",
) -> None:
    if get_language() == lang:
        return
    set_language(lang)
    _apply_language_chrome(gui, static_scene, font)


def _switch_language(gui: Any, static_scene: "pygame.Surface", font: "pygame.font.Font") -> None:
    toggle_language()
    _apply_language_chrome(gui, static_scene, font)


def run_pygame_demo(
    agent_count: int = 4,
    *,
    max_frames: int | None = None,
    frame_dt_s: float | None = None,
    on_frame: Any | None = None,
) -> int:
    """Start interactive pygame demo loop.

    ``max_frames``, ``frame_dt_s`` and ``on_frame`` are for headless capture.
    Leave them unset for the interactive window.
    """
    if not PYGAME_AVAILABLE:
        raise RuntimeError(
            "pygame is not installed. Install it first: pip install pygame"
        )

    runner = build_demo_runner(agent_count=agent_count)
    gui = ColonyGUI(runner)

    pygame.init()
    audio_available = False
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        audio_available = pygame.mixer.get_init() is not None
        if audio_available:
            pygame.mixer.set_num_channels(16)
    except Exception:
        audio_available = False

    screen_width = max(gui.WIDTH, PANEL_RIGHT_X + PANEL_RIGHT_W + 8)
    screen_height = gui.HEIGHT + WINDOW_EXTRA_UI_HEIGHT
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption(tr("Colony GUI — симуляция шиншилл"))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans, Liberation Sans, Arial", 16)
    font_small = pygame.font.SysFont("DejaVu Sans, Liberation Sans, Arial", 13)
    font_mono = pygame.font.SysFont("DejaVu Sans Mono, Liberation Mono, Courier New", 12)
    static_scene = pygame.Surface((screen_width, screen_height)).convert()
    _paint_static_scene(static_scene, font)
    cage_x, cage_y, cage_w, cage_h = CAGE_RECT

    sprite_manifest = {}
    try:
        with Path(gui.sprite_manifest_path).open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        if isinstance(payload, dict):
            sprite_manifest = payload
    except Exception:
        sprite_manifest = {}
    sfx_manifest: dict[str, Any] = {}
    try:
        with Path(gui.sfx_manifest_path).open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        if isinstance(payload, dict):
            sfx_manifest = payload
    except Exception:
        sfx_manifest = {}
    sprite_cache: dict[str, tuple[list[pygame.Surface], float]] = {}
    sfx_cache: dict[str, pygame.mixer.Sound] = {}
    sprites_dir_path = Path(gui.sprites_dir)
    sfx_dir_path = Path(gui.sfx_dir)
    smoothed_positions: dict[str, list[float]] = {}
    visual_zone_state: dict[str, dict[str, Any]] = {}
    visual_rngs: dict[str, random.Random] = {}
    animation_time: dict[str, float] = {}
    rendered_animation: dict[str, str] = {}
    name_surface_cache: dict[tuple[str, tuple[int, int, int]], pygame.Surface] = {}
    panel_text_surface_cache: dict[tuple[str, tuple[int, int, int]], pygame.Surface] = {}
    audio_action_by_agent: dict[str, str] = {}
    audio_played_by_agent: dict[str, float] = {}
    audio_played_by_sfx: dict[str, float] = {}
    audio_enabled = audio_available
    sim_accumulator = 0.0
    sim_step_cost_ema_s = 0.0
    layout_elapsed_s = 0.0
    snapshot_elapsed_s = 0.0
    gui._update_snapshot()
    state = gui.get_render_state()
    ordered_agents = list(state["agents"])
    visual_targets: dict[str, tuple[int, int]] = {}
    visual_zones: dict[str, str] = {}
    diagnostics_cache = _collect_reproduction_diagnostics(getattr(gui, "runner", None))
    diagnostics_elapsed_s = 0.0
    card_hit_areas: list[tuple[pygame.Rect, str]] = []
    lineage_births_seen = int(getattr(runner, "total_births", 0))
    lineage_deaths_seen = int(getattr(runner, "total_deaths", 0))

    running = True
    frame_i = 0
    while running:
        current_agent_count = len(ordered_agents)
        target_fps = gui.FPS
        if current_agent_count >= VERY_HIGH_POPULATION_THRESHOLD:
            target_fps = VERY_HIGH_POP_RENDER_FPS
        elif current_agent_count >= HIGH_POPULATION_THRESHOLD:
            target_fps = HIGH_POP_RENDER_FPS

        if frame_dt_s is not None:
            clock.tick()
            frame_dt = max(0.0, float(frame_dt_s))
        else:
            frame_dt = min(clock.tick(target_fps) / 1000.0, MAX_FRAME_DT_S)
        layout_elapsed_s += frame_dt
        snapshot_elapsed_s += frame_dt
        for event in pygame.event.get():
            if gui.swarm_analytics.visible:
                consumed = gui.swarm_analytics.handle_event(event)
                if gui.swarm_analytics.visible and gui.swarm_analytics._needs_rebuild:
                    gui.swarm_analytics.refresh(runner, gui.observer, gui._generation_index_map)
                if consumed:
                    continue

            if gui.inspector.visible:
                consumed = gui.inspector.handle_event(event)
                if consumed:
                    continue

            if gui.lineage.visible:
                consumed, clicked_id = gui.lineage.handle_event(event)
                if clicked_id:
                    gui.close_all_overlays()
                    gui.open_inspector(clicked_id)
                if consumed:
                    continue

            if event.type == pygame.QUIT:
                if _confirm_quit():
                    running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if gui.inspector.visible or gui.lineage.visible:
                        gui.close_all_overlays()
                    else:
                        if _confirm_quit():
                            running = False
                elif event.key == pygame.K_SPACE:
                    gui.pause_resume()
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    gui.speed_up()
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    gui.speed_down()
                elif event.key == pygame.K_l:
                    if gui.inspector.visible:
                        gui.inspector.close()
                    gui.lineage.toggle()
                    if gui.lineage.visible and gui.lineage._needs_rebuild:
                        gui.lineage.rebuild(runner.agents, gui._generation_index_map)
                elif event.key == pygame.K_a:
                    if gui.inspector.visible:
                        gui.inspector.close()
                    gui.swarm_analytics.toggle()
                    if gui.swarm_analytics.visible and gui.swarm_analytics._needs_rebuild:
                        gui.swarm_analytics.refresh(runner, gui.observer, gui._generation_index_map)
                elif event.key == pygame.K_m and audio_available:
                    audio_enabled = not audio_enabled
                elif event.key == pygame.K_g:
                    _switch_language(gui, static_scene, font)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked_lang = next(
                    (code for code, rect in _LANG_BUTTONS.items() if rect.collidepoint(event.pos)),
                    None,
                )
                if clicked_lang is not None:
                    _set_demo_language(clicked_lang, gui, static_scene, font)
                    continue
                clicked_id = _handle_panel_click(event.pos, card_hit_areas)
                if clicked_id:
                    if gui.inspector.visible and gui.inspector.agent_id == clicked_id:
                        gui.inspector.close()
                    else:
                        gui.lineage.close()
                        gui.open_inspector(clicked_id)
            elif event.type == pygame.MOUSEWHEEL:
                mouse_x, _ = pygame.mouse.get_pos()
                if mouse_x >= PANEL_RIGHT_X:
                    gui._right_panel_scroll = max(0, int(gui._right_panel_scroll - event.y * 24))

        sim_accumulator += frame_dt
        base_sim_step = _adaptive_sim_step_s(len(state["agents"]))
        sim_step = _apply_sim_load_adaptation(base_sim_step, sim_step_cost_ema_s)
        high_population_mode = len(ordered_agents) >= HIGH_POPULATION_THRESHOLD
        step_count = 0
        if high_population_mode and sim_accumulator >= sim_step:
            # In dense colonies one runner tick is the expensive part.
            # Batch catch-up into one larger sim tick to keep render cadence stable.
            batched_dt = min(sim_accumulator, sim_step * HIGH_POP_SIM_BATCH_STEPS)
            tick_started = time.perf_counter()
            gui._sim_tick(batched_dt)
            tick_cost_s = time.perf_counter() - tick_started
            if sim_step_cost_ema_s <= 0.0:
                sim_step_cost_ema_s = tick_cost_s
            else:
                sim_step_cost_ema_s = (sim_step_cost_ema_s * 0.9) + (tick_cost_s * 0.1)
            sim_accumulator -= batched_dt
            step_count = 1
        else:
            while sim_accumulator >= sim_step and step_count < SIM_MAX_CATCHUP_STEPS:
                tick_started = time.perf_counter()
                gui._sim_tick(sim_step)
                tick_cost_s = time.perf_counter() - tick_started
                if sim_step_cost_ema_s <= 0.0:
                    sim_step_cost_ema_s = tick_cost_s
                else:
                    sim_step_cost_ema_s = (sim_step_cost_ema_s * 0.9) + (tick_cost_s * 0.1)
                sim_accumulator -= sim_step
                step_count += 1
            if step_count >= SIM_MAX_CATCHUP_STEPS:
                sim_accumulator = min(sim_accumulator, sim_step)

        # Prevent long-stall spiral when frame budget is exceeded.
        sim_accumulator = min(sim_accumulator, sim_step * SIM_ACCUMULATOR_MAX_STEPS)

        layout_refresh_required = False
        if step_count > 0:
            refresh_due = True
            if high_population_mode:
                refresh_period_s = HIGH_POP_LAYOUT_REFRESH_PERIOD_S
                if len(ordered_agents) >= VERY_HIGH_POPULATION_THRESHOLD:
                    refresh_period_s = VERY_HIGH_POP_LAYOUT_REFRESH_PERIOD_S
                refresh_due = snapshot_elapsed_s >= refresh_period_s
            if refresh_due:
                gui._update_snapshot()
                state = gui.get_render_state()
                ordered_agents = list(state["agents"])
                layout_refresh_required = True
                snapshot_elapsed_s = 0.0

        current_births = int(getattr(runner, "total_births", lineage_births_seen))
        current_deaths = int(getattr(runner, "total_deaths", lineage_deaths_seen))
        if current_births != lineage_births_seen or current_deaths != lineage_deaths_seen:
            gui.lineage.mark_dirty()
            gui.swarm_analytics.mark_dirty()
            lineage_births_seen = current_births
            lineage_deaths_seen = current_deaths
        if gui.lineage.visible and gui.lineage._needs_rebuild:
            gui.lineage.rebuild(runner.agents, gui._generation_index_map)

        screen.blit(static_scene, (0, 0))

        if layout_refresh_required:
            active_agent_ids = {
                str(item.get("agent_id", ""))
                for item in ordered_agents
                if str(item.get("agent_id", ""))
            }
            active_names = {
                str(item.get("name", ""))
                for item in ordered_agents
                if str(item.get("name", ""))
            }
            _prune_agent_caches(
                active_agent_ids,
                smoothed_positions,
                visual_zone_state,
                visual_rngs,
                animation_time,
                rendered_animation,
                audio_action_by_agent,
                audio_played_by_agent,
            )
            stale_name_keys = [key for key in list(name_surface_cache.keys()) if key[0] not in active_names]
            for key in stale_name_keys:
                name_surface_cache.pop(key, None)
        if layout_refresh_required:
            zone_counts: dict[str, int] = {}
            next_visual_targets: dict[str, tuple[int, int]] = {}
            next_visual_zones: dict[str, str] = {}
            wheel_lock_owner = getattr(getattr(gui, "runner", None), "resources", None)
            wheel_lock_owner = str(getattr(wheel_lock_owner, "wheel_lock", "") or "")
            wheel_lock_owner = wheel_lock_owner or None

            for agent in ordered_agents:
                agent_id = str(agent["agent_id"])
                if agent_id not in visual_rngs:
                    visual_rngs[agent_id] = random.Random(f"visual:{agent_id}")
                visual_zone = _resolve_visual_zone(
                    agent=agent,
                    dt=layout_elapsed_s,
                    rng=visual_rngs[agent_id],
                    state_by_agent=visual_zone_state,
                    wheel_lock_owner=wheel_lock_owner,
                )
                cap = EXCLUSIVE_VISUAL_ZONE_CAPACITY.get(visual_zone)
                if cap is not None and zone_counts.get(visual_zone, 0) >= cap:
                    visual_zone = _pick_capacity_fallback(
                        action=str(agent.get("action", "idle")),
                        fallback_zone=str(agent.get("position", "floor")),
                        zone_counts=zone_counts,
                        rng=visual_rngs[agent_id],
                    )
                slot_index = zone_counts.get(visual_zone, 0)
                zone_counts[visual_zone] = slot_index + 1
                next_visual_zones[agent_id] = visual_zone
                next_visual_targets[agent_id] = get_zone_render_pos(
                    visual_zone,
                    agent_index=slot_index,
                    agent_id=agent_id,
                )
            visual_targets = next_visual_targets
            visual_zones = next_visual_zones
            layout_elapsed_s = 0.0

        render_agent_count = len(ordered_agents)
        diagnostics_elapsed_s += frame_dt
        diagnostics_refresh_period_s = DIAGNOSTICS_REFRESH_PERIOD_S
        if render_agent_count >= VERY_HIGH_POPULATION_THRESHOLD:
            diagnostics_refresh_period_s = VERY_HIGH_POP_PANEL_REFRESH_PERIOD_S
        elif render_agent_count >= HIGH_POPULATION_THRESHOLD:
            diagnostics_refresh_period_s = HIGH_POP_PANEL_REFRESH_PERIOD_S
        if layout_refresh_required or diagnostics_elapsed_s >= diagnostics_refresh_period_s:
            diagnostics_cache = _collect_reproduction_diagnostics(getattr(gui, "runner", None))
            diagnostics_elapsed_s = 0.0

        center_by_agent: dict[str, tuple[int, int]] = {}
        frame_now_s = time.perf_counter()
        show_names = render_agent_count < NO_NAME_LABELS_THRESHOLD
        name_stride = 1
        if show_names and render_agent_count >= HIGH_POPULATION_THRESHOLD:
            name_stride = max(1, math.ceil(render_agent_count / HIGH_POP_LABEL_BUDGET))

        for agent_idx, agent in enumerate(ordered_agents):
            agent_id = str(agent["agent_id"])
            target_x, target_y = visual_targets.get(agent_id, agent["render_pos"])
            if agent_id not in smoothed_positions:
                smoothed_positions[agent_id] = [float(target_x), float(target_y)]
            current_x, current_y = smoothed_positions[agent_id]
            current_x, current_y = _smooth_position_step(
                current_x=current_x,
                current_y=current_y,
                target_x=float(target_x),
                target_y=float(target_y),
                dt=frame_dt,
            )
            smoothed_positions[agent_id] = [current_x, current_y]

            center_x, center_y = int(current_x), int(current_y)
            center_by_agent[agent_id] = (center_x, center_y)
            action = str(agent.get("action", "idle"))
            visual_zone = visual_zones.get(agent_id, _normalize_visual_zone(agent.get("position", "floor")))
            animation_id = _resolve_visual_animation_id(
                action=action,
                visual_zone=visual_zone,
                preferred_animation_id=str(agent.get("animation_id", "loaf_idle")),
            )
            if rendered_animation.get(agent_id) != animation_id:
                rendered_animation[agent_id] = animation_id
                animation_time[agent_id] = 0.0
            animation_time[agent_id] = float(animation_time.get(agent_id, 0.0)) + frame_dt

            clip = _load_sprite_clip(
                sprite_manifest=sprite_manifest,
                animation_id=animation_id,
                sprites_dir=sprites_dir_path,
                cache=sprite_cache,
            )
            if clip is None:
                pygame.draw.circle(screen, (80, 90, 120), (center_x, center_y), 16)
            else:
                frames, fps = clip
                frame_idx = int(animation_time[agent_id] * fps) % len(frames)
                frame = frames[frame_idx]
                rect = frame.get_rect(center=(center_x, center_y))
                screen.blit(frame, rect.topleft)

            if show_names and (name_stride <= 1 or (agent_idx % name_stride) == 0):
                name_surface = _get_cached_text_surface(
                    name_surface_cache,
                    font,
                    str(agent["name"]),
                    (35, 28, 20),
                )
                name_rect = name_surface.get_rect(center=(int(center_x), int(center_y) - 58))
                screen.blit(name_surface, name_rect.topleft)

            if audio_enabled and (not gui.paused):
                sfx_id = agent.get("sfx_id") or ACTION_SFX.get(action)
                _play_action_sfx(
                    action=action,
                    sfx_id=str(sfx_id) if sfx_id is not None else None,
                    sfx_manifest=sfx_manifest,
                    sfx_dir=sfx_dir_path,
                    sfx_cache=sfx_cache,
                    action_by_agent=audio_action_by_agent,
                    played_by_agent=audio_played_by_agent,
                    played_by_sfx=audio_played_by_sfx,
                    agent_id=agent_id,
                    now_s=frame_now_s,
                )

        if render_agent_count <= MOUNT_OVERLAY_MAX_AGENTS:
            _draw_mount_display_overlays(
                screen,
                center_by_agent=center_by_agent,
                runner=getattr(gui, "runner", None),
                now_s=frame_now_s,
            )

        _draw_stats_panel(
            screen=screen,
            font_small=font_small,
            text_surface_cache=panel_text_surface_cache,
            sim_time_text=str(state.get("sim_time_text", "00:00:00")),
            speed=float(gui.speed),
            paused=bool(gui.paused),
            audio_enabled=bool(audio_enabled),
            diagnostics=diagnostics_cache,
            population_stats=dict(state.get("population_stats", {})),
            resources=dict(state.get("resources", {})),
        )

        registry = getattr(runner, "death_registry", None)
        if registry is not None:
            dead_memorials = list(registry.get_recent_memorials(MAX_DEAD_CARDS))
        else:
            dead_memorials = []
        name_registry = getattr(runner, "birth_registry", None)
        card_hit_areas = _draw_right_panel(
            screen,
            font,
            font_small,
            living_agents_data=list(state.get("agents", [])),
            dead_memorials=dead_memorials,
            name_registry=name_registry,
            selected_agent_id=gui.inspector.agent_id if gui.inspector.visible else None,
            scroll_offset=int(gui._right_panel_scroll),
        )
        if gui.lineage.visible:
            gui.lineage.draw(screen, font, font_small)
        if gui.inspector.visible:
            gui.inspector.draw(screen, font, font_small, font_mono)
        if gui.swarm_analytics.visible:
            if gui.swarm_analytics._needs_rebuild:
                gui.swarm_analytics.refresh(runner, gui.observer, gui._generation_index_map)
            gui.swarm_analytics.draw(screen, font, font_small, font_mono)

        pygame.display.flip()
        if on_frame is not None:
            on_frame(screen)
        if max_frames is not None:
            frame_i += 1
            if frame_i >= max_frames:
                running = False

    try:
        if audio_available and pygame.mixer.get_init() is not None:
            pygame.mixer.stop()
    except Exception:
        pass
    pygame.quit()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Colony GUI")
    parser.add_argument("--agents", type=int, default=4, help="Number of starter agents")
    parser.add_argument(
        "--lang",
        choices=("en", "ru"),
        default=None,
        help="UI language. Overrides NOWA_LANG. Default is English.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without pygame window and print one summary snapshot",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="Headless simulation duration in seconds",
    )
    args = parser.parse_args(argv)
    if args.lang:
        set_language(args.lang)

    if args.headless:
        state = run_headless_ticks(agent_count=args.agents, duration_s=args.duration)
        print(
            f"ok: sim_time={state['sim_time_text']} agents={len(state['agents'])} "
            f"sprite_manifest={state['sprite_manifest_path']} sfx_manifest={state['sfx_manifest_path']}"
        )
        return 0

    return run_pygame_demo(agent_count=args.agents)
