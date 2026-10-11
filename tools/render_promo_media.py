#!/usr/bin/env python3
"""Render short promo clips of the colony, tamagotchi, and lineage tree.

Headless: SDL_VIDEODRIVER=dummy. Requires pygame and pillow
(pip install -r requirements-demo.txt && pip install pillow).

    python tools/render_promo_media.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "media"
COLONY_SRC = REPO / "Demo" / "Colony chinchillas" / "src"
TAMAGOTCHI_SRC = REPO / "Demo" / "Tamagochi Chinchilla" / "src"


def _image_from_surface(surface, max_width: int = 760):
    import pygame
    from PIL import Image

    width, height = surface.get_size()
    if width > max_width:
        height = max(1, int(height * max_width / width))
        width = max_width
        surface = pygame.transform.smoothscale(surface, (width, height))
    raw = pygame.image.tobytes(surface, "RGB")
    return Image.frombytes("RGB", (width, height), raw)


def _save_gif(frames, path: Path, fps: int = 8) -> None:
    if not frames:
        raise RuntimeError(f"no frames for {path}")
    # Quantize each frame on its own, then hand Pillow a fresh RGB sequence.
    # Sharing one palette across frames collapsed the colony clip to a single frame.
    rgb = [frame.convert("RGB") for frame in frames]
    rgb[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=rgb[1:],
        duration=int(1000 / fps),
        loop=0,
        optimize=True,
    )


def _report(path: Path) -> None:
    size = path.stat().st_size
    print(f"{path.relative_to(REPO)}  {size / 1_048_576:.2f} MB")
    if size > 5 * 1_048_576:
        raise RuntimeError(f"{path} exceeds 5 MB")


def _activate(lang: str) -> None:
    os.environ["NOWA_LANG"] = lang
    for src in (COLONY_SRC, TAMAGOTCHI_SRC):
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
    from colony_gui.i18n import set_language as set_colony_language
    from tama_i18n import set_language as set_tama_language

    set_colony_language(lang)
    set_tama_language(lang)


def render_colony(out: Path) -> None:
    import pygame

    if str(COLONY_SRC) not in sys.path:
        sys.path.insert(0, str(COLONY_SRC))
    from colony_gui.app import run_pygame_demo

    frames = []

    def on_frame(screen) -> None:
        frames.append(_image_from_surface(screen))

    run_pygame_demo(
        agent_count=6,
        max_frames=24,
        frame_dt_s=0.12,
        on_frame=on_frame,
    )
    pygame.quit()
    gif = out / "colony.gif"
    png = out / "colony.png"
    _save_gif(frames, gif, fps=8)
    frames[len(frames) // 2].save(png, optimize=True)
    _report(gif)
    _report(png)


def render_tamagotchi(out: Path) -> None:
    import pygame

    if str(TAMAGOTCHI_SRC) not in sys.path:
        sys.path.insert(0, str(TAMAGOTCHI_SRC))
    from pygame_engine import PygameEngine

    engine = PygameEngine(width=960, height=640, fps=30)
    engine.audio_enabled = False
    font_name = "DejaVu Sans, Liberation Sans, Arial"
    engine.font_sub = pygame.font.SysFont(font_name, 22)
    engine.font_ui = pygame.font.SysFont(font_name, 16)
    engine.font_ui_title = pygame.font.SysFont(font_name, 20, bold=True)
    sprites = REPO / "Demo" / "Tamagochi Chinchilla" / "sprites"
    for sprite in sorted(sprites.glob("*.png")):
        engine.load_animation(sprite.stem, sprite)

    script = (
        ("walk_loop", "bowl_pellets", "ест гранулы", 10),
        ("eat_hay_loop", "bowl_hay", "ест сено", 12),
        ("run_wheel_loop", "wheel", "на колесе", 12),
        ("dustbath_loop", "dustbath", "купается в пыли", 10),
        ("sleep_loop", "house", "спит в домике", 10),
    )
    frames = []
    for anim, position, subtitle, steps in script:
        engine.queue_action(
            {
                "action_id": anim,
                "anim": anim,
                "sfx": None,
                "position": position,
                "duration": [2, 4],
                "subtitle": subtitle,
                "loop": True,
                "layer": "action",
            }
        )
        engine.process_actions()
        # The engine will not replace an action younger than one second.
        engine._action_layer_age = 2.0
        for _ in range(steps):
            engine.update(0.12)
            engine.render()
            frames.append(_image_from_surface(engine.screen, max_width=720))
    pygame.quit()
    gif = out / "tamagotchi.gif"
    png = out / "tamagotchi.png"
    _save_gif(frames, gif, fps=8)
    frames[len(frames) // 3].save(png, optimize=True)
    _report(gif)
    _report(png)


def render_lineage(out: Path) -> None:
    import pygame

    if str(COLONY_SRC) not in sys.path:
        sys.path.insert(0, str(COLONY_SRC))
    from colony_gui.lineage_overlay import LineageOverlay
    from death_registry import LineageNode

    def node(agent_id, name, sex, generation, parents, alive, offspring, index):
        return LineageNode(
            agent_id=agent_id,
            display_name=name,
            sex=sex,
            generation=generation,
            parents=parents,
            own_offspring=list(offspring),
            is_alive=alive,
            cause_of_death="" if alive else "old_age",
            age=400.0 if alive else 1800.0,
            total_offspring=len(offspring),
            generation_index=index,
        )

    nodes = [
        node("g0a", "Luna", "F", 0, (None, None), False, ["g1a", "g1b"], 1),
        node("g0b", "Moss", "M", 0, (None, None), False, ["g1a", "g1b"], 2),
        node("g0c", "Pebble", "F", 0, (None, None), True, ["g1c"], 3),
        node("g0d", "Birch", "M", 0, (None, None), True, ["g1c"], 4),
        node("g1a", "Nimbus", "F", 1, ("g0a", "g0b"), True, ["g2a", "g2b"], 1),
        node("g1b", "Cinder", "M", 1, ("g0a", "g0b"), False, [], 2),
        node("g1c", "Thistle", "M", 1, ("g0c", "g0d"), True, ["g2a", "g2b"], 3),
        node("g2a", "Pip", "F", 2, ("g1a", "g1c"), True, [], 1),
        node("g2b", "Sable", "M", 2, ("g1a", "g1c"), True, [], 2),
    ]

    class _Registry:
        birth_registry = None

        def get_lineage_nodes(self, living_agents, generation_index_map):
            return list(nodes)

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((960, 640))
    font = pygame.font.SysFont("DejaVu Sans, Liberation Sans, Arial", 18)
    font_small = pygame.font.SysFont("DejaVu Sans, Liberation Sans, Arial", 14)
    overlay = LineageOverlay(_Registry(), allow_nonadjacent_parents=False)
    overlay._visible = True
    overlay.rebuild([], {})
    overlay._selected_id = "g2a"
    overlay._hovered_id = "g1a"

    focus = ["g0a", "g1a", "g2a", "g1c", "g2b", "g0d", "g1b", "g2a"]
    frames = []
    fitted_offset = None
    for step in range(16):
        screen.fill((235, 228, 215))
        overlay._fit_pending = step == 0
        overlay._selected_id = focus[step % len(focus)]
        overlay._hovered_id = focus[(step + 2) % len(focus)]
        if fitted_offset is not None:
            overlay._offset[0] = fitted_offset[0] + (step - 8) * 6
        overlay.draw(screen, font, font_small)
        if fitted_offset is None:
            fitted_offset = list(overlay._offset)
        pygame.display.flip()
        frames.append(_image_from_surface(screen, max_width=760))
    pygame.quit()
    gif = out / "lineage.gif"
    png = out / "lineage.png"
    _save_gif(frames, gif, fps=6)
    frames[-1].save(png, optimize=True)
    _report(gif)
    _report(png)


def main() -> int:
    import shutil

    OUT.mkdir(parents=True, exist_ok=True)
    names = (
        "colony.gif",
        "colony.png",
        "tamagotchi.gif",
        "tamagotchi.png",
        "lineage.gif",
        "lineage.png",
    )
    for lang in ("en", "ru"):
        dest = OUT / lang
        dest.mkdir(parents=True, exist_ok=True)
        _activate(lang)
        render_colony(dest)
        render_tamagotchi(dest)
        render_lineage(dest)
    for name in names:
        shutil.copyfile(OUT / "en" / name, OUT / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
