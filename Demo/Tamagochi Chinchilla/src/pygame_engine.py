"""
Pygame rendering engine for Chinchilla Agent.
Handles sprite rendering, animation, SFX playback, and UI.

FIXES:
- load_animation() now reads manifest.json to get correct frame count
- AnimationState.advance() uses real-time seconds, not integer ticks
- Sprite is rendered at correct position (centered, not top-left)
- Smooth lerp movement between positions
- Action layer is properly NOT overwritten while animation is still playing
"""

import logging
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import random

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from tama_i18n import get_language, toggle_language, tr

# ============================================================================
# POSITION MAPPING
# ============================================================================

POSITION_COORDINATES: Dict[str, Tuple[int, int]] = {
    # Floor level
    "floor":        (490, 580),   # open floor centre
    "corner":       (110, 575),   # back-left corner

    # Right side
    "litter":       (872, 572),   # litter box
    "toy":          (720, 510),   # hanging toy
    "object":       (800, 528),   # cardboard box

    # Left cluster: house + dustbath
    "house":        (132, 510),   # inside/at wooden house door
    "dustbath":     (260, 590),   # sand bath tray centre

    # Feeding station (left-centre)
    "waterer":      (345, 590),   # water bottle spout
    "bowl_pellets": (430, 600),   # food bowl centre
    "bowl_hay":     (510, 598),   # hay rack
    "mineral":      (618, 598),   # mineral block

    # Wheel (right-centre)
    "wheel":        (730, 406),   # inside wheel running surface (wh_cy=418 + inner_r=36 - half_sprite=48)

    # Shelves (staggered right-to-left going up)
    # Important: coordinates are sprite-center targets.
    # Shelf boards are y=424 / y=304 / y=190, so centres are lifted
    # by ~50px to place paws on top of shelves (not intersecting boards).
    "shelf_lower":  (580, 374),   # stands on lower shelf
    "shelf_mid":    (480, 254),   # stands on mid shelf
    "shelf_upper":  (380, 140),   # stands on upper shelf

    # Bars (right wall)
    "bars":         (920, 450),   # mid-height bars
    "bars_top":     (920, 120),   # top of bars

    # Door (right wall, below bars)
    "door":         (920, 540),   # in front of cage door

    # Stay in place
    "current":      None,
}

# ============================================================================
# ANIMATION
# ============================================================================

FRAME_SIZE = 96   # px — matches our sprite sheets


@dataclass
class AnimationClip:
    """
    A loaded animation clip: list of surfaces + per-frame duration in seconds.
    fps is stored so we can compute frame duration = 1/fps.
    """
    animation_id: str
    frames: List['pygame.Surface']
    fps: float = 8.0       # frames per second for this clip
    loop: bool = True

    @property
    def frame_duration(self) -> float:
        """Duration of one frame in seconds."""
        return 1.0 / max(self.fps, 1.0)


class AnimationPlayer:
    """
    Plays an AnimationClip, advancing based on real elapsed time.
    Completely separate from simulation ticks.
    """

    def __init__(self, clip: AnimationClip, loop: bool = True):
        self.clip = clip
        self.loop = loop
        self.current_frame: int = 0
        self.time_in_frame: float = 0.0   # seconds spent on current frame
        self.finished: bool = False

    def update(self, dt: float) -> None:
        """Advance animation by dt real seconds."""
        dt = min(dt, 0.1)   # не прыгать больше одного кадра за раз
        if self.finished:
            return

        self.time_in_frame += dt
        fd = self.clip.frame_duration

        while self.time_in_frame >= fd:
            self.time_in_frame -= fd
            self.current_frame += 1
            if self.current_frame >= len(self.clip.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.clip.frames) - 1
                    self.finished = True
                    break

    def get_surface(self) -> Optional['pygame.Surface']:
        if not self.clip.frames:
            return None
        return self.clip.frames[self.current_frame]


# ============================================================================
# MOVEMENT LERP
# ============================================================================

class SpriteMovement:
    """Smooth lerp movement between positions."""

    SPEED = 300.0   # pixels per second

    def __init__(self, start: Tuple[int, int]):
        self.pos: List[float] = [float(start[0]), float(start[1])]
        self.target: Tuple[float, float] = (float(start[0]), float(start[1]))
        self.moving: bool = False

    def set_target(self, target: Tuple[int, int]) -> None:
        self.target = (float(target[0]), float(target[1]))
        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        self.moving = (abs(dx) > 2 or abs(dy) > 2)

    def update(self, dt: float) -> None:
        if not self.moving:
            return
        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        step = self.SPEED * dt
        if step >= dist:
            self.pos[0] = self.target[0]
            self.pos[1] = self.target[1]
            self.moving = False
        else:
            ratio = step / dist
            self.pos[0] += dx * ratio
            self.pos[1] += dy * ratio

    @property
    def screen_pos(self) -> Tuple[int, int]:
        """Top-left for blitting a 96px sprite, centred on logical pos."""
        return (int(self.pos[0]) - FRAME_SIZE // 2,
                int(self.pos[1]) - FRAME_SIZE // 2)


# ============================================================================
# PYGAME ENGINE
# ============================================================================

class PygameEngine:
    """Pygame-based rendering engine for Chinchilla."""

    # Minimum seconds an action layer animation plays before it can be replaced.
    # Prevents the "flickering" caused by main.py queueing actions every tick.
    # NOTE: the first action always bypasses this check.
    MIN_ACTION_DURATION = 1.0   # seconds

    def __init__(self, width: int = 1024, height: int = 768, fps: int = 60):
        if not PYGAME_AVAILABLE:
            raise ImportError("Pygame not available. Install with: pip install pygame")

        self.width = width
        self.height = height
        self.target_fps = fps
        self.logger = logging.getLogger(__name__)

        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Chinchilla Agent — Cognitive Tamagotchi")
        self.clock = pygame.time.Clock()

        # Animation clips keyed by animation_id
        self.clips: Dict[str, AnimationClip] = {}

        # Active players per layer  (layer -> AnimationPlayer)
        self.players: Dict[str, AnimationPlayer] = {}

        # How long the current action-layer animation has been playing
        self._action_layer_age: float = 0.0

        # Sprite movement
        start_pos = POSITION_COORDINATES.get("floor", (400, 500))
        self.movement = SpriteMovement(start_pos)

        # UI
        self.subtitle: str = ""
        self.subtitle_timer: float = 0.0
        self.show_debug: bool = False
        self.debug_lines: List[str] = []
        self.show_state_window: bool = False
        self.state_snapshot: Dict[str, Any] = {}
        self.audio_enabled: bool = True
        self._nowa_snapshot: Dict[str, Any] = {}

        # Fonts
        pygame.font.init()
        _ui_font = "DejaVu Sans, Liberation Sans, Arial"
        self.font_sub  = pygame.font.SysFont(_ui_font, 22)
        self.font_dbg  = pygame.font.SysFont(_ui_font, 14)
        self.font_ui   = pygame.font.SysFont(_ui_font, 16)
        self.font_ui_title = pygame.font.SysFont(_ui_font, 20, bold=True)
        self.lang_button_rect = pygame.Rect(self.width - 58, 8, 46, 22)

        # Bottom UI row is below cage border (cage bottom is y = height - 40)
        self.state_button_rect = pygame.Rect((self.width - 360) // 2, self.height - 34, 360, 24)
        self.sound_button_rect = pygame.Rect(self.state_button_rect.right + 12, self.height - 34, 220, 24)

        # ── Training rating buttons ───────────────────────────────────
        # Layout (left-anchored): [Оценить:] [1][2][3][4][5]  ··· [state_btn]
        # state_button starts at x=332; buttons must end before that with margin.
        _rb_y   = self.height - 34
        _rb_h   = 24
        _rb_w   = 36          # narrower → 5×(36+4)−4 = 196px total for buttons
        _rb_gap = 4
        _rb_x0  = 90          # label "Оценить:" ~74px wide at x=14 → 14+74+2=90
        self.rating_label_pos   = (14, _rb_y + 4)
        self.rating_button_rects: List['pygame.Rect'] = [
            pygame.Rect(_rb_x0 + i * (_rb_w + _rb_gap), _rb_y, _rb_w, _rb_h)
            for i in range(5)
        ]
        self._last_rating: Optional[int] = None   # 1-5, None = not set

        # Action queue — engine processes these on process_actions()
        self.action_queue: List[Dict[str, Any]] = []

        # Flag: first action should always go through regardless of age
        self._first_action = True

        # Circadian phase for background coloring
        self._circadian_phase: float = 0.5

        # Wellbeing indicator
        self._wellbeing: float = 1.0
        self._state_scroll: int = 0     # scroll offset for state window (lines)

        self.logger.info(f"PygameEngine ready: {width}×{height}@{fps}fps")

    def set_circadian_phase(self, phase: float) -> None:
        """Обновить фазу циркадного ритма для окраски фона (0.0–1.0)."""
        self._circadian_phase = max(0.0, min(1.0, phase))

    def set_wellbeing(self, stress: float, valence: float, arousal: float,
                      pathological_chain: bool = False,
                      is_sleeping: bool = False) -> None:
        """Обновить индикатор самочувствия. Вызывать раз в секунду."""
        if pathological_chain:
            self._wellbeing = 0.0       # красный — патологическая цепочка
        elif stress > 0.6:
            self._wellbeing = 0.2       # красный
        elif stress > 0.3:
            self._wellbeing = 0.5       # жёлтый — тревога
        elif is_sleeping:
            # FIX: was using arousal < 0.2 as proxy for sleep, but arousal can go
            # negative after the sleep-suppression fix — giving false "sleep" blue
            # even during fear/activity chains. Use explicit is_sleeping flag instead.
            self._wellbeing = -1.0      # синий (спит)
        else:
            self._wellbeing = 1.0       # зелёный — нормальное самочувствие

    # ------------------------------------------------------------------
    # LOADING
    # ------------------------------------------------------------------

    def load_animation(self, animation_id: str, sprite_path: Path,
                       num_frames: int = 0, fps: float = 0.0) -> bool:
        """
        Load animation from sprite sheet PNG.

        If manifest.json exists in the same directory, its metadata is used
        (num_frames, fps).  Otherwise num_frames / fps arguments are used.
        Falls back to treating the whole image as 1 frame at 8 fps.
        """
        try:
            if not sprite_path.exists():
                self.logger.warning(f"Sprite not found: {sprite_path}")
                return False

            # Try to read manifest for this sprite
            manifest_path = sprite_path.parent / "manifest.json"
            if manifest_path.exists() and num_frames == 0:
                try:
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    entry = manifest.get(animation_id, {})
                    num_frames = entry.get("frames", 0)
                    fps = fps or entry.get("fps", 8.0)
                except Exception:
                    pass

            image = pygame.image.load(str(sprite_path)).convert_alpha()
            img_w = image.get_width()
            img_h = image.get_height()

            # Auto-detect from image width if still unknown
            if num_frames <= 0:
                num_frames = max(1, img_w // FRAME_SIZE)
            if fps <= 0:
                fps = 8.0

            # Extract frames from horizontal sprite sheet
            frame_w = img_w // num_frames
            surfaces = []
            for i in range(num_frames):
                rect = pygame.Rect(i * frame_w, 0, frame_w, img_h)
                surfaces.append(image.subsurface(rect).copy())

            self.clips[animation_id] = AnimationClip(
                animation_id=animation_id,
                frames=surfaces,
                fps=fps,
            )
            self.logger.debug(
                f"Loaded {animation_id}: {num_frames} frames @ {fps}fps"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to load {animation_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # ACTION QUEUE
    # ------------------------------------------------------------------

    def queue_action(self, action_data: Dict[str, Any]) -> None:
        """Queue an action command for processing on next process_actions()."""
        self.logger.debug(f"Queueing action: {action_data}")
        self.action_queue.append(action_data)

    def process_actions(self) -> None:
        """
        Process queued actions.

        Key rule: the action layer is NOT replaced if its current animation
        has been playing for less than MIN_ACTION_DURATION seconds.
        This prevents the main loop from flickering by queuing a new action
        every simulation tick.

        Queue is deduplicated per layer before processing — last command wins.
        This prevents stale postural/micro overlays when multiple sim ticks
        fire between render frames.
        """
        if not self.action_queue:
            return

        # Deduplicate: keep only the last command per layer.
        seen: Dict[str, Dict] = {}
        for action in self.action_queue:
            layer = action.get("layer", "action")
            seen[layer] = action   # last wins
        self.action_queue.clear()

        # Always process action layer first so pop(postural/micro) fires
        # before any postural/micro in the same batch.
        ordered = []
        if "action" in seen:
            ordered.append(seen.pop("action"))
        ordered.extend(seen.values())

        for action in ordered:
            layer  = action.get("layer", "action")
            anim_id = action.get("anim", "")
            loop   = action.get("loop", True)

            # Guard: don't interrupt a recently-started action layer
            if layer == "action":
                if (not self._first_action
                        and "action" in self.players
                        and self._action_layer_age < self.MIN_ACTION_DURATION):
                    # Too fresh — skip, and also drop postural/micro from same batch
                    self.players.pop("postural", None)
                    self.players.pop("micro", None)
                    continue
                self._action_layer_age = 0.0
                self._first_action = False
                # Clear looping postural/micro overlays
                self.players.pop("postural", None)
                self.players.pop("micro", None)

            # Update position (only if specified and not "current")
            pos_name = action.get("position", "current")
            target = POSITION_COORDINATES.get(pos_name)
            if target is not None:
                pad = FRAME_SIZE // 2
                left = 40 + pad
                right = self.width - 40 - pad
                top = 40 + pad
                bottom = self.height - 40 - pad
                tx = max(left, min(target[0], right))
                ty = max(top, min(target[1], bottom))
                self.logger.info(f"Action sets movement target: action_id={action.get('action_id')} pos={pos_name} -> ({tx},{ty})")
                self.movement.set_target((tx, ty))

            # Subtitle
            subtitle = action.get("subtitle", "")
            if subtitle:
                self.subtitle = subtitle
                self.subtitle_timer = 4.0

            # Start animation
            if anim_id and anim_id in self.clips:
                clip = self.clips[anim_id]
                player = AnimationPlayer(clip, loop=loop)
                self.players[layer] = player
            elif anim_id:
                self.logger.warning(f"Animation not loaded: {anim_id}")
                player = self.players.get(layer)
                if player:
                    player.loop = True

    # ------------------------------------------------------------------
    # UPDATE / RENDER
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance animation players and movement by dt real seconds."""
        # Advance all animation players
        for layer, player in list(self.players.items()):
            player.update(dt)
            if player.finished and not player.loop:
                del self.players[layer]
                # When action player finishes, reset guard so next command loads immediately.
                # Without this: _action_layer_age resets to 0 → guard blocks next command → sprite vanishes.
                if layer == "action":
                    self._first_action = True

        # Track how long current action layer has been playing
        if "action" in self.players:
            self._action_layer_age += dt
        else:
            self._action_layer_age = 0.0

        # Move sprite
        self.movement.update(dt)

        # Countdown subtitle
        if self.subtitle_timer > 0:
            self.subtitle_timer -= dt

    def render(self) -> None:
        """Render the current frame."""
        # Static background — circadian not implemented in NOWA
        self.screen.fill((235, 228, 215))

        # Enclosure border
        cage_rect = pygame.Rect(40, 40, self.width - 80, self.height - 80)
        pygame.draw.rect(self.screen, (200, 190, 175), cage_rect)
        pygame.draw.rect(self.screen, (100, 85, 70),   cage_rect, 3)

        # Simple furniture hints
        self._draw_furniture()

        # Wellbeing bar
        self._draw_wellbeing_bar()

        # Draw position markers in debug mode
        if self.show_debug:
            self._draw_debug_positions()

        # Render only the action layer.
        # postural/micro share the same sprite sheets as action — blitting them
        # on top always produces double-sprite overlap. They stay in players{}
        # for logic/timing purposes but are not drawn separately.
        blit_x, blit_y = self.movement.screen_pos
        player = self.players.get("action")
        if player:
            surf = player.get_surface()
            if surf:
                self.screen.blit(surf, (blit_x, blit_y))

        # Subtitle
        if self.subtitle and self.subtitle_timer > 0:
            self._draw_subtitle()

        # Debug overlay
        if self.show_debug:
            self._draw_debug_overlay()
            self._draw_nowa_hud()

        # UI
        self._draw_rating_buttons()
        self._draw_state_button()
        self._draw_audio_button()
        self._draw_lang_button()
        if self.show_state_window:
            self._draw_state_window()

        pygame.display.flip()

    # ------------------------------------------------------------------
    # UI HELPERS
    # ------------------------------------------------------------------

    def _draw_furniture(self) -> None:
        """
        Draw all cage furniture matching all 18 position zones from spec.
        Positions match POSITION_COORDINATES exactly so the sprite lands on objects.

        Zones: floor, corner, litter, toy, object, house, dustbath,
               bowl_pellets, bowl_hay, waterer, mineral, wheel,
               shelf_lower, shelf_mid, shelf_upper, bars, bars_top, door
        """
        s = self.screen

        # ── Cage structure ─────────────────────────────────────────────────
        # Floor line
        pygame.draw.line(s, (160, 148, 130), (60, 630), (964, 630), 3)

        # Right-wall cage bars  (bars / bars_top zone: x≈950)
        bar_color   = (130, 120, 110)
        bar_color2  = (110, 100,  90)
        for bx in range(900, 975, 14):
            pygame.draw.line(s, bar_color, (bx, 60), (bx, 630), 2)
        # Horizontal bar rails
        for by in (60, 200, 400, 630):
            pygame.draw.line(s, bar_color2, (900, by), (974, by), 3)

        # Door frame cut-out in bars (zone "door": cx≈960, cy≈570)
        door_rect = pygame.Rect(910, 490, 55, 140)
        pygame.draw.rect(s, (95, 80, 60),  door_rect, 0)   # door bg
        pygame.draw.rect(s, (70, 58, 40),  door_rect, 3)   # door frame
        # Door hinge dots
        for hy in (510, 560, 610):
            pygame.draw.circle(s, (140, 120, 90), (918, hy), 3)
        # Door label (tiny)
        lbl = self.font_dbg.render(tr("дверь"), True, (30, 20, 10))
        s.blit(lbl, (912, 635))

        # Left back-corner wall mark (zone "corner": cx≈80)
        pygame.draw.line(s, (150, 140, 128), (60, 60), (60, 630), 3)
        # Small corner mark on floor
        pygame.draw.arc(s, (140, 130, 118),
                        pygame.Rect(62, 610, 36, 24), 0, math.pi/2, 2)

        # ── House (zone "house": cx≈130, cy≈520) ──────────────────────────
        # Body
        pygame.draw.rect(s, (185, 158, 118), (72, 468, 120, 110))
        # Roof
        pygame.draw.polygon(s, (158, 128, 88),
                            [(66, 470), (132, 390), (198, 470)])
        # Door hole
        pygame.draw.rect(s, (60, 45, 30), (110, 510, 42, 68))
        # Roof ridge line
        pygame.draw.line(s, (138, 110, 72), (66, 470), (132, 390), 2)
        pygame.draw.line(s, (138, 110, 72), (132, 390), (198, 470), 2)

        # ── Dust-bath container (zone "dustbath": cx≈260, cy≈600) ─────────
        # Outer tray
        pygame.draw.rect(s, (160, 145, 125), (210, 574, 100, 44), border_radius=6)
        pygame.draw.rect(s, (130, 115,  95), (210, 574, 100, 44), 2, border_radius=6)
        # Sand fill (grainy dots)
        sand_c = (210, 195, 168)
        pygame.draw.rect(s, sand_c, (214, 578, 92, 36), border_radius=4)
        for i in range(18):
            gx = 218 + (i * 37) % 84
            gy = 582 + (i * 13) % 28
            pygame.draw.circle(s, (195, 178, 148), (gx, gy), 2)
        lbl = self.font_dbg.render(tr("купалка"), True, (30, 20, 10))
        s.blit(lbl, (218, 620))

        # ── Water bottle (zone "waterer": cx≈350, cy≈595) ─────────────────
        # Bottle body mounted on wall
        pygame.draw.rect(s, (190, 215, 235), (330, 540, 30, 55), border_radius=5)
        pygame.draw.rect(s, (150, 178, 200), (330, 540, 30, 55), 2, border_radius=5)
        # Water level inside
        pygame.draw.rect(s, (130, 175, 220, 160), (333, 565, 24, 27), border_radius=3)
        # Nozzle / spout
        pygame.draw.rect(s, (160, 148, 130), (341, 595, 8, 14))
        pygame.draw.circle(s, (140, 128, 110), (345, 610), 4)
        # Wall mount clip
        pygame.draw.rect(s, (130, 120, 110), (326, 548, 6, 20))
        pygame.draw.rect(s, (130, 120, 110), (326, 572, 6, 16))
        lbl = self.font_dbg.render(tr("поилка"), True, (30, 20, 10))
        s.blit(lbl, (326, 620))

        # ── Food bowl / pellets (zone "bowl_pellets": cx≈430, cy≈610) ─────
        pygame.draw.ellipse(s, (155, 138, 115), (390, 600, 80, 28))
        pygame.draw.ellipse(s, (130, 115,  92), (390, 600, 80, 28), 2)
        # Pellets inside (small rounded rects)
        for px, py in [(404,605),(418,603),(432,606),(446,604),(412,610),(428,610),(442,609)]:
            pygame.draw.ellipse(s, (180, 148, 95), (px, py, 8, 5))
        lbl = self.font_dbg.render(tr("корм"), True, (30, 20, 10))
        s.blit(lbl, (414, 630))

        # ── Hay rack (zone "bowl_hay": cx≈510, cy≈610) ─────────────────────
        # Rack frame
        pygame.draw.rect(s, (148, 125, 80), (472, 580, 76, 44), 2)
        # Vertical bars of rack
        for rx in range(478, 544, 10):
            pygame.draw.line(s, (148, 125, 80), (rx, 580), (rx, 624), 1)
        # Hay strands sticking out
        hay_c = (195, 172, 65)
        for i, (hx, hy, ang) in enumerate([
            (478,572,-15),(486,568,-5),(495,570,8),(504,567,0),
            (513,570,-10),(522,568,5),(532,572,12),(540,570,-3)
        ]):
            ex = hx + int(18 * math.cos(math.radians(ang - 80)))
            ey = hy + int(18 * math.sin(math.radians(ang - 80)))
            pygame.draw.line(s, hay_c, (hx, hy), (ex, ey), 2)
        lbl = self.font_dbg.render(tr("сено"), True, (30, 20, 10))
        s.blit(lbl, (494, 630))

        # ── Mineral stone (zone "mineral": cx≈620, cy≈610) ─────────────────
        # Irregular polygon — mineral block
        pts = [(596,596),(610,590),(628,592),(638,600),(634,614),(618,618),(602,612)]
        pygame.draw.polygon(s, (210, 205, 195), pts)
        pygame.draw.polygon(s, (170, 163, 150), pts, 2)
        # Salt crystal glints
        for gx, gy in [(606,600),(618,596),(626,604),(612,610)]:
            pygame.draw.circle(s, (240, 238, 232), (gx, gy), 2)
        lbl = self.font_dbg.render(tr("минерал"), True, (30, 20, 10))
        s.blit(lbl, (596, 630))

        # ── Litter box (zone "litter": cx≈870, cy≈590) ────────────────────
        pygame.draw.rect(s, (155, 140, 120), (828, 568, 88, 52), border_radius=4)
        pygame.draw.rect(s, (120, 108,  88), (828, 568, 88, 52), 2, border_radius=4)
        # Litter fill
        litter_c = (185, 172, 148)
        pygame.draw.rect(s, litter_c, (832, 572, 80, 44), border_radius=3)
        # Granules
        for i in range(20):
            lx = 836 + (i * 31) % 72
            ly = 576 + (i * 17) % 36
            pygame.draw.circle(s, (170, 156, 132), (lx, ly), 2)
        # Rim
        pygame.draw.rect(s, (128, 114, 90), (828, 568, 88, 12), border_radius=4)
        lbl = self.font_dbg.render(tr("лоток"), True, (30, 20, 10))
        s.blit(lbl, (846, 630))

        # ── Exercise wheel (zone "wheel": cx≈730, cy≈420) ─────────────────
        wh_c  = pygame.Rect(680, 368, 100, 100)
        wh_cx, wh_cy = 730, 418
        # Stand
        pygame.draw.rect(s, (150, 138, 122), (718, 468, 24, 40))
        pygame.draw.rect(s, (150, 138, 122), (704, 504, 52,  8))
        # Outer ring
        pygame.draw.circle(s, (165, 152, 135), (wh_cx, wh_cy), 50, 5)
        # Inner ring
        pygame.draw.circle(s, (165, 152, 135), (wh_cx, wh_cy), 36, 2)
        # Spokes (8)
        for i in range(8):
            ang = math.radians(i * 45)
            x1 = int(wh_cx + 10 * math.cos(ang))
            y1 = int(wh_cy + 10 * math.sin(ang))
            x2 = int(wh_cx + 48 * math.cos(ang))
            y2 = int(wh_cy + 48 * math.sin(ang))
            pygame.draw.line(s, (150, 138, 122), (x1, y1), (x2, y2), 2)
        # Hub
        pygame.draw.circle(s, (140, 128, 110), (wh_cx, wh_cy), 8)
        lbl = self.font_dbg.render(tr("колесо"), True, (30, 20, 10))
        s.blit(lbl, (690, 530))

        # ── Toy (zone "toy": cx≈720, cy≈510) ──────────────────────────────
        # Hanging wooden toy — rings on a string; draw to right of wheel so it's not hidden
        toy_x, toy_y = 760, 510
        # string from ceiling
        pygame.draw.line(s, (160, 138, 100), (toy_x, 420), (toy_x, toy_y - 20), 1)
        # rings
        for ry in (toy_y - 18, toy_y, toy_y + 18):
            pygame.draw.ellipse(s, (185, 155, 100), (toy_x-14, ry-8, 28, 16), 3)
        # Small bell at bottom
        pygame.draw.circle(s, (195, 175, 110), (toy_x, toy_y + 22), 7, 2)
        lbl = self.font_dbg.render(tr("игрушка"), True, (30, 20, 10))
        s.blit(lbl, (toy_x - 24, toy_y + 36))

        # ── Mystery object (zone "object": cx≈800, cy≈540) ─────────────────
        # Cardboard box (common enrichment toy)
        pygame.draw.rect(s, (195, 168, 118), (768, 510, 64, 50))
        pygame.draw.rect(s, (165, 140,  90), (768, 510, 64, 50), 2)
        # Open flaps
        pygame.draw.line(s, (165, 140, 90), (768, 510), (784, 492), 2)
        pygame.draw.line(s, (165, 140, 90), (816, 492), (832, 510), 2)
        pygame.draw.line(s, (165, 140, 90), (832, 510), (816, 492), 2)
        # Hole in box
        pygame.draw.ellipse(s, (80, 65, 45), (786, 524, 28, 22))

        # ── Shelves (tops at y=424/304/190; stand points are in POSITION_COORDINATES) ──
        shelf_c  = (178, 152, 116)
        shelf_e  = (148, 124,  88)
        # Lower shelf — wider, sturdier
        pygame.draw.rect(s, shelf_c,  (500, 424, 160, 14))
        pygame.draw.rect(s, shelf_e,  (500, 424, 160, 14), 1)
        # Support brackets
        pygame.draw.line(s, shelf_e, (510, 438), (496, 480), 2)
        pygame.draw.line(s, shelf_e, (650, 438), (664, 480), 2)

        # Mid shelf
        pygame.draw.rect(s, shelf_c,  (400, 304, 160, 12))
        pygame.draw.rect(s, shelf_e,  (400, 304, 160, 12), 1)
        pygame.draw.line(s, shelf_e, (410, 316), (396, 358), 2)
        pygame.draw.line(s, shelf_e, (550, 316), (564, 358), 2)

        # Upper shelf
        pygame.draw.rect(s, shelf_c,  (300, 190, 160, 12))
        pygame.draw.rect(s, shelf_e,  (300, 190, 160, 12), 1)
        pygame.draw.line(s, shelf_e, (310, 202), (296, 244), 2)
        pygame.draw.line(s, shelf_e, (450, 202), (464, 244), 2)

        # ── Subtle floor shadow under everything ───────────────────────────
        shadow_surf = pygame.Surface((904, 18), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 22))
        s.blit(shadow_surf, (60, 630))

    def _draw_wellbeing_bar(self) -> None:
        """Цветная полоска 12×80 px в правом верхнем углу клетки."""
        s = self.screen
        wb = self._wellbeing
        if wb < 0:
            color = (70, 130, 200)    # синий — спит
        elif wb < 0.3:
            color = (192, 40, 40)     # красный — стресс/патология
        elif wb < 0.6:
            color = (200, 160, 30)    # жёлтый — беспокойство
        else:
            color = (60, 160, 70)     # зелёный — норма

        # place bar outside cage to the right
        bar_rect = pygame.Rect(self.width - 40, 60, 12, 80)
        pygame.draw.rect(s, (50, 50, 50), bar_rect.inflate(2, 2))  # рамка
        pygame.draw.rect(s, color, bar_rect)

        lbl = self.font_dbg.render(tr("Самочувствие"), True, (30, 20, 10))
        s.blit(lbl, (self.width - 58, 145))

    def _draw_subtitle(self) -> None:
        # Fade out in last second
        alpha = min(255, int(self.subtitle_timer * 180))
        surf = self.font_sub.render(tr(self.subtitle), True, (20, 10, 5))
        surf.set_alpha(alpha)
        rect = surf.get_rect(center=(self.width // 2, self.height - 70))
        self.screen.blit(surf, rect)

    def _draw_debug_positions(self) -> None:
        for name, coord in POSITION_COORDINATES.items():
            if coord is None:
                continue
            pygame.draw.circle(self.screen, (180, 180, 255), coord, 6)
            lbl = self.font_dbg.render(name, True, (80, 80, 120))
            self.screen.blit(lbl, (coord[0] + 8, coord[1] - 8))

    def _draw_debug_overlay(self) -> None:
        y = 10
        for line in self.debug_lines:
            surf = self.font_dbg.render(line, True, (30, 30, 30))
            self.screen.blit(surf, (10, y))
            y += 18

    def set_nowa_state(self, nowa_snapshot: dict) -> None:
        """Принимает полный снимок NOWA-состояния для HUD."""
        self._nowa_snapshot = dict(nowa_snapshot or {})

    def _draw_nowa_hud(self) -> None:
        """Отрисовка NOWA-слоёв в debug-режиме."""
        if not self.show_debug or not self._nowa_snapshot:
            return
        s = self._nowa_snapshot
        x, y = 50, 55
        line_h = 14

        top3 = s.get("bg_top3") or []
        sections = [
            ("── NEUROMODULATORS ──", [
                f"DA  {s.get('dopamine',0):.2f}  | 5HT {s.get('serotonin',0):.2f}",
                f"NE  {s.get('norepinephrine',0):.2f}  | CORT {s.get('cortisol',0):.2f}",
                f"ACh {s.get('acetylcholine',0):.2f}",
            ]),
            ("── DRIVES ──", [
                f"energy_need  {s.get('energy_need',0):.2f}",
                f"curiosity    {s.get('curiosity',0):.2f}",
                f"exploration  {s.get('exploration',0):.2f}",
                f"social_drive {s.get('social_drive',0):.2f}",
                f"goal_tension {s.get('goal_tension',0):.2f}",
            ]),
            ("── AFFECT (8D) ──", [
                f"valence  {s.get('valence',0):+.2f}  arousal {s.get('arousal',0):.2f}",
                f"stress   {s.get('stress',0):.2f}   trust  {s.get('trust',0):.2f}",
                f"curiosity {s.get('curiosity',0):.2f}  stab {s.get('stability',0):.2f}",
            ]),
            ("── WAKEFULNESS ──", [
                f"wake  {s.get('wakefulness',0):.2f}  reliability {s.get('cognitive_reliability',0):.2f}",
            ]),
            ("── BG TOP-3 ──", [
                f"{i+1}. {chain:<22} {float(score):.3f}"
                for i, (chain, score) in enumerate(top3)
            ]),
        ]

        for title, lines in sections:
            surf = self.font_dbg.render(title, True, (200, 180, 120))
            self.screen.blit(surf, (x, y))
            y += line_h
            for line in lines:
                surf = self.font_dbg.render(line, True, (180, 200, 180))
                self.screen.blit(surf, (x + 6, y))
                y += line_h
            y += 4

    def _get_state_window_rect(self) -> 'pygame.Rect':
        # Keep state window above bottom controls and inside cage area.
        return pygame.Rect(100, 80, self.width - 200, self.height - 170)

    def _get_state_close_rect(self) -> 'pygame.Rect':
        panel = self._get_state_window_rect()
        return pygame.Rect(panel.right - 34, panel.top + 10, 24, 24)

    def _fmt_metric(self, value: Any) -> str:
        try:
            return f"{float(value):+.2f}"
        except Exception:
            return "n/a"

    def _build_state_lines(self) -> List[str]:
        snap = self.state_snapshot or {}
        current_action = snap.get("current_action") or {}
        stats = snap.get("stats") or {}
        chain_stats = snap.get("chain_stats") or {}
        affect = snap.get("affect") or {}
        # NOWA snapshot fields
        nowa = snap.get("nowa") or {}
        drives = snap.get("drives") or {}
        mind = snap.get("mind") or {}
        memory_summary = snap.get("memory_summary") or {}

        wakefulness = float(nowa.get("wakefulness", 0.0))
        cognitive_rel = float(nowa.get("cognitive_reliability", 1.0))
        bg_top3 = nowa.get("bg_top3") or []

        drive_labels = {
            "energy_need": tr("голод/энергия"),
            "exploration": tr("исследование"),
            "social_drive": tr("соц. контакт"),
            "curiosity": tr("любопытство"),
            "goal_tension": tr("целенаправленность"),
        }
        drive_items = sorted(drives.items(), key=lambda kv: kv[1], reverse=True)[:4]
        drive_lines = (
            [f"  {drive_labels.get(k, k)}={float(v):.2f}" for k, v in drive_items]
            if drive_items else ["  " + tr("нет данных")]
        )

        next_actions_ru = mind.get("next_actions_ru") or []
        next_actions_line = ", ".join(tr(item) for item in next_actions_ru[:3]) if next_actions_ru else tr("нет")

        candidate_chains_ru = mind.get("candidate_chains_ru") or []
        candidate_line = ", ".join(candidate_chains_ru[:3]) if candidate_chains_ru else "нет"

        top_chains = memory_summary.get("top_chains") or []
        if top_chains:
            top_mem_line = ", ".join(
                f"{item.get('chain','-').replace('_', ' ')} ({float(item.get('weight', 0.0)):.2f})"
                for item in top_chains[:3]
            )
        else:
            top_mem_line = tr("нет")

        # circadian rhythm not implemented in NOWA; remove related lines

        # --- Interpret affect (human-friendly summary) ---
        affect_interp = []
        try:
            v = float(affect.get('valence', 0.0) or 0.0)
            a = float(affect.get('arousal', 0.0) or 0.0)
            s_ = float(affect.get('stress', 0.0) or 0.0)
            cur = float(affect.get('curiosity', 0.0) or 0.0)
            trust = float(affect.get('trust', 0.0) or 0.0)
            if v > 0.3:
                affect_interp.append(tr("настроение позитивное"))
            elif v < -0.3:
                affect_interp.append(tr("настроение негативное"))
            else:
                affect_interp.append(tr("настроение нейтральное"))
            if a > 0.6:
                affect_interp.append(tr("высокая активация"))
            elif a < 0.3:
                affect_interp.append(tr("низкая активность"))
            if s_ > 0.6:
                affect_interp.append(tr("стресс"))
            if cur > 0.6:
                affect_interp.append(tr("любопытство"))
            if trust > 0.6:
                affect_interp.append(tr("доверие"))
        except Exception:
            affect_interp = []
        affect_interp_line = ", ".join(affect_interp) or "—"

        # --- Interpret drives (human-friendly) ---
        drives_interp = []
        for k, v in drive_items:
            label = drive_labels.get(k, k)
            val = float(v or 0.0)
            if val > 0.7:
                drives_interp.append("  " + tr("сильная потребность: {label}").format(label=label))
            elif val > 0.4:
                drives_interp.append("  " + tr("умеренная потребность: {label}").format(label=label))
        drives_interp_lines = drives_interp if drives_interp else ["  " + tr("нет сильных желаний")]

        action_remaining = float(snap.get("action_remaining_s", 0.0))
        chain_cooldown = float(snap.get("chain_cooldown_s", 0.0))

        action_label = mind.get("current_action_ru") or current_action.get("action_id") or "-"
        return [
            tr("Симуляция: {time:.1f}с   тик: {tick}").format(
                time=float(snap.get("time", 0.0)),
                tick=int(snap.get("tick", 0)),
            ),
            tr("Режим: {mode}").format(mode=tr("пауза") if snap.get("paused") else tr("активен")),
            "",
            tr("Мысли и намерения:"),
            "  " + tr("Сценарий: {chain} ({progress}/{length})").format(
                chain=mind.get("current_chain_ru") or "-",
                progress=int(mind.get("chain_progress", 0)),
                length=int(mind.get("chain_length", 0)),
            ),
            "  " + tr("Следующие шаги: {steps}").format(steps=next_actions_line),
            "",
            tr("Чувства:"),
            "  " + tr("Валентность={valence}  Возбуждение={arousal}").format(
                valence=self._fmt_metric(affect.get("valence")),
                arousal=self._fmt_metric(affect.get("arousal")),
            ),
            "  " + tr("Стресс={stress}  Любопытство={curiosity}").format(
                stress=self._fmt_metric(affect.get("stress")),
                curiosity=self._fmt_metric(affect.get("curiosity")),
            ),
            "  " + tr("Доверие={trust}  Стабильность={stability}").format(
                trust=self._fmt_metric(affect.get("trust")),
                stability=self._fmt_metric(affect.get("stability")),
            ),
            "  " + tr("Привязанность={attachment}").format(attachment=self._fmt_metric(affect.get("attachment"))),
            "  " + tr("Интерпретация: {text}").format(text=affect_interp_line),
            "",
            tr("Желания и потребности:"),
            "  " + tr("Драйвы:"),
            *drive_lines,
            "  " + tr("Бодрость={wake:.2f}   Надёжность когниций={cog:.2f}").format(
                wake=wakefulness,
                cog=cognitive_rel,
            ),
            "  " + tr("Желания:"),
            *drives_interp_lines,
            "",
            tr("Поведение сейчас:"),
            "  " + tr("Действие: {action}").format(action=tr(str(action_label))),
            "  " + tr("Анимация: {anim}   Позиция: {position}").format(
                anim=current_action.get("anim") or "-",
                position=current_action.get("position") or "-",
            ),
            "  " + tr("До конца действия: {remain:.1f}с   кулдаун цепочки: {cool:.1f}с").format(
                remain=action_remaining,
                cool=chain_cooldown,
            ),
            "  " + tr("Выполнено действий: {actions}   цепочек: {chains}").format(
                actions=int(stats.get("actions_executed", 0)),
                chains=int(stats.get("chains_completed", 0)),
            ),
            "",
            tr("Память и обучение:"),
            "  " + tr("Записей памяти: {entries}   успехов: {success:.0f}%   ср. награда: {reward:+.2f}").format(
                entries=int(memory_summary.get("total_entries", 0)),
                success=float(memory_summary.get("success_rate", 0.0)) * 100,
                reward=float(memory_summary.get("average_reward", 0.0)),
            ),
            "  " + tr("Предпочитаемые цепочки: {chains}").format(chains=top_mem_line),
        ]

    def _draw_rating_buttons(self) -> None:
        """Пять кнопок оценки (1–5) в левой части нижней панели."""
        s = self.screen

        # Label
        lbl = self.font_ui.render(tr("Оценить:"), True, (80, 68, 55))
        s.blit(lbl, self.rating_label_pos)

        # Color ramp: 1=красный … 5=зелёный
        colors_normal = [
            (180,  55,  50),   # 1 — плохо
            (195, 125,  40),   # 2
            (155, 145,  60),   # 3 — нейтрально
            ( 70, 148,  75),   # 4
            ( 40, 135,  60),   # 5 — отлично
        ]
        colors_active = [
            (220,  80,  70),
            (225, 155,  60),
            (185, 175,  80),
            ( 95, 180,  95),
            ( 60, 170,  80),
        ]
        # ASCII-safe text labels (avoid Unicode glyphs that may not render)
        labels = ["1", "2", "3", "4", "5"]
        border_col  = (70, 58, 48)
        text_col    = (252, 248, 240)

        for i, rect in enumerate(self.rating_button_rects):
            rating = i + 1
            active = self._last_rating == rating
            bg     = colors_active[i] if active else colors_normal[i]

            pygame.draw.rect(s, bg,         rect, border_radius=4)
            pygame.draw.rect(s, border_col, rect, 1 if active else 2, border_radius=4)

            if active:
                inner = rect.inflate(-4, -4)
                glow  = tuple(min(255, c + 30) for c in bg)
                pygame.draw.rect(s, glow, inner, border_radius=2)

            surf = self.font_ui.render(labels[i], True, text_col)
            s.blit(surf, surf.get_rect(center=rect.center))

    def _draw_state_button(self) -> None:
        rect = self.state_button_rect
        bg = (132, 120, 104) if self.show_state_window else (154, 140, 122)
        border = (96, 82, 68)
        pygame.draw.rect(self.screen, bg, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=6)
        label = tr("Скрыть состояние питомца") if self.show_state_window else tr("Показать состояние питомца")
        surf = self.font_ui.render(label, True, (245, 239, 231))
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_audio_button(self) -> None:
        rect = self.sound_button_rect
        bg = (108, 142, 118) if self.audio_enabled else (154, 112, 112)
        border = (82, 68, 58)
        pygame.draw.rect(self.screen, bg, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=6)
        label = tr("Выключить звук") if self.audio_enabled else tr("Включить звук")
        surf = self.font_ui.render(label, True, (248, 244, 238))
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_state_window(self) -> None:
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 96))
        self.screen.blit(overlay, (0, 0))

        panel = self._get_state_window_rect()
        pygame.draw.rect(self.screen, (241, 234, 223), panel, border_radius=10)
        pygame.draw.rect(self.screen, (114, 100, 84), panel, 2, border_radius=10)

        title = self.font_ui_title.render(tr("Текущее состояние персонажа"), True, (48, 38, 28))
        self.screen.blit(title, (panel.left + 16, panel.top + 12))

        close_rect = self._get_state_close_rect()
        pygame.draw.rect(self.screen, (182, 110, 100), close_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 70, 64), close_rect, 2, border_radius=4)
        close_lbl = self.font_dbg.render("X", True, (255, 244, 240))
        self.screen.blit(close_lbl, close_lbl.get_rect(center=close_rect.center))

        line_h = 18
        content_top = panel.top + 48
        content_bottom = panel.bottom - 24
        visible_lines = max(1, (content_bottom - content_top) // line_h)

        all_lines = self._build_state_lines()
        total_lines = len(all_lines)

        # Clamp scroll offset
        max_scroll = max(0, total_lines - visible_lines)
        self._state_scroll = max(0, min(self._state_scroll, max_scroll))

        # Render visible slice
        y = content_top
        for line in all_lines[self._state_scroll: self._state_scroll + visible_lines]:
            surf = self.font_ui.render(line, True, (44, 36, 28))
            self.screen.blit(surf, (panel.left + 16, y))
            y += line_h

        # Scroll indicator
        if total_lines > visible_lines:
            bar_h = content_bottom - content_top
            thumb_h = max(20, int(bar_h * visible_lines / total_lines))
            thumb_y = content_top + int((bar_h - thumb_h) * self._state_scroll / max(1, max_scroll))
            track_rect = pygame.Rect(panel.right - 16, content_top, 10, bar_h)
            thumb_rect = pygame.Rect(panel.right - 16, thumb_y, 10, thumb_h)
            pygame.draw.rect(self.screen, (210, 200, 188), track_rect, border_radius=5)
            pygame.draw.rect(self.screen, (100, 86, 70), thumb_rect, border_radius=5)
            hint = self.font_dbg.render("scroll", True, (130, 115, 95))
            self.screen.blit(hint, (panel.right - 58, panel.bottom - 20))

    def _draw_lang_button(self) -> None:
        rect = self.lang_button_rect
        pygame.draw.rect(self.screen, (226, 214, 196), rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 104, 84), rect, 1, border_radius=4)
        mark = self.font_ui.render(get_language().upper(), True, (35, 28, 20))
        self.screen.blit(mark, mark.get_rect(center=rect.center))

    def handle_mouse_click(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.lang_button_rect.collidepoint(pos):
            toggle_language()
            try:
                pygame.display.set_caption(tr("Тамагочи — шиншилла"))
            except Exception:
                pass
            return "toggle_language"
        if self.show_state_window and self._get_state_close_rect().collidepoint(pos):
            self.show_state_window = False
            self._state_scroll = 0
            return "close_state_window"
        # Scrollbar click: click on track above/below thumb scrolls by page
        if self.show_state_window:
            panel = self._get_state_window_rect()
            content_top = panel.top + 48
            content_bottom = panel.bottom - 24
            track_rect = pygame.Rect(panel.right - 14, content_top, 16, content_bottom - content_top)
            if track_rect.collidepoint(pos):
                all_lines = self._build_state_lines()
                total = len(all_lines)
                visible = max(1, (content_bottom - content_top) // 18)
                max_scroll = max(0, total - visible)
                # Map click y to scroll position
                rel = (pos[1] - content_top) / max(1, content_bottom - content_top)
                self._state_scroll = max(0, min(max_scroll, int(rel * total)))
                return None
        if self.state_button_rect.collidepoint(pos):
            self.show_state_window = not self.show_state_window
            self._state_scroll = 0
            return "toggle_state_window"
        if self.sound_button_rect.collidepoint(pos):
            return "toggle_audio"
        # ── Training rating buttons ───────────────────────────────────
        for i, rect in enumerate(self.rating_button_rects):
            if rect.collidepoint(pos):
                rating = i + 1
                self._last_rating = rating
                return f"training:{rating}"
        return None

    def set_state_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.state_snapshot = snapshot or {}
        self.audio_enabled = bool(snapshot.get("audio_enabled", self.audio_enabled))

    def set_audio_enabled(self, enabled: bool) -> None:
        self.audio_enabled = bool(enabled)

    def set_debug_lines(self, lines: List[str]) -> None:
        self.debug_lines = lines

    def toggle_debug(self) -> None:
        self.show_debug = not self.show_debug

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------

    def start_loop(self) -> None:
        self.running = True

    def stop_loop(self) -> None:
        self.running = False

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_d:
                    self.toggle_debug()
                if event.key == pygame.K_g:
                    toggle_language()
                # Scroll state window with arrow keys
                if self.show_state_window:
                    if event.key == pygame.K_UP:
                        self._state_scroll = max(0, self._state_scroll - 1)
                    elif event.key == pygame.K_DOWN:
                        self._state_scroll += 1
            # Mouse wheel scrolls state window when it's open
            if event.type == pygame.MOUSEWHEEL and self.show_state_window:
                self._state_scroll = max(0, self._state_scroll - event.y)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_mouse_click(event.pos)
        return True

    def cleanup(self) -> None:
        pygame.quit()
        self.logger.info("Pygame cleanup complete")

    def is_running(self) -> bool:
        return getattr(self, "running", False)


# ============================================================================
# STUB
# ============================================================================

class StubPygameEngine:
    """Stub engine for when pygame is not available."""

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.screen = None
        self.clock = None
        self._last_rating: Optional[int] = None

    def load_animation(self, *args, **kwargs): return True
    def queue_action(self, action_data): self.logger.info(f"ACTION: {action_data}")
    def process_actions(self): pass
    def update(self, dt=0.016): pass
    def render(self): pass
    def handle_events(self): return True
    def start_loop(self): pass
    def stop_loop(self): pass
    def cleanup(self): pass
    def is_running(self): return False
    def toggle_debug(self): pass
    def set_debug_lines(self, lines): pass
    def handle_mouse_click(self, pos): return None
    def set_state_snapshot(self, snapshot): pass
    def set_audio_enabled(self, enabled): pass
    def set_wellbeing(self, stress=0, valence=0, arousal=0.5, pathological_chain=False): pass
    def set_circadian_phase(self, phase): pass


# ============================================================================
# FACTORY
# ============================================================================

def create_pygame_engine(*args, **kwargs) -> PygameEngine:
    if not PYGAME_AVAILABLE:
        return StubPygameEngine(*args, **kwargs)
    try:
        return PygameEngine(*args, **kwargs)
    except Exception as exc:
        logging.getLogger(__name__).warning(f"Pygame init failed, falling back to stub: {exc}")
        return StubPygameEngine(*args, **kwargs)