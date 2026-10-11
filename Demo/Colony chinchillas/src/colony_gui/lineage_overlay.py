"""Lineage tree overlay."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from death_registry import LineageNode

from .i18n import tr

GENERATION_ROW_H = 120
NODE_SPACING_X = 95
NODE_R_ALIVE = 28
NODE_R_DEAD = 22

NODE_F_ALIVE = (200, 150, 200)
NODE_M_ALIVE = (150, 180, 220)
NODE_DEAD = (158, 152, 148)
NODE_SELECTED = (255, 215, 80)
NODE_BORDER = (80, 65, 45)
NODE_BORDER_W = 3

LINE_PARENT = (140, 130, 115)
LINE_PAIR = (180, 165, 145)
LINE_W = 2
LINE_PAIR_DASH = 8

ZOOM_MIN = 0.3
ZOOM_MAX = 2.5
ZOOM_STEP = 0.15

OVERLAY_BG = (232, 226, 214, 225)
TITLE_COLOR = (35, 28, 20)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return float(default)
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return float(default)
    return parsed


class LineageOverlay:
    """Interactive lineage tree overlay."""

    def __init__(self, registry: Any, allow_nonadjacent_parents: bool = False) -> None:
        self._visible: bool = False
        self._registry = registry
        # If True, accept parents from any earlier generation. Default False
        # preserves legacy behaviour expected by tests; the GUI will enable
        # non-adjacent parents when desired.
        self._allow_nonadjacent_parents = bool(allow_nonadjacent_parents)
        self._zoom: float = 1.0
        self._offset: list[float] = [0.0, 0.0]
        self._dragging: bool = False
        self._drag_start: tuple[int, int] = (0, 0)
        self._drag_offset_start: list[float] = [0.0, 0.0]
        self._nodes: list[LineageNode] = []
        self._hovered_id: str | None = None
        self._selected_id: str | None = None
        self._needs_rebuild: bool = True
        self._fit_pending: bool = True

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self) -> None:
        self._visible = not self._visible
        if self._visible:
            self._fit_pending = True

    def close(self) -> None:
        self._visible = False
        self._dragging = False
        self._hovered_id = None

    def mark_dirty(self) -> None:
        self._needs_rebuild = True

    def rebuild(
        self,
        living_agents: list[Any],
        generation_index_map: dict[str, int],
    ) -> None:
        # Ensure we have a sensible generation index map for living agents.
        # If the caller passed an empty map or None (possible when GUI snapshot
        # wasn't refreshed), compute it locally to avoid layout corruption.
        if not generation_index_map:
            try:
                from .utils import build_generation_index_map

                generation_index_map = build_generation_index_map(living_agents)
            except Exception:
                generation_index_map = {}

        nodes = list(self._registry.get_lineage_nodes(living_agents, generation_index_map))
        # If a birth registry is attached to the death registry, prefer its
        # recorded human-readable names for display. This enforces the
        # requirement that human names come from a single authoritative source.
        try:
            birth_reg = getattr(self._registry, "birth_registry", None)
            if birth_reg is not None:
                for node in nodes:
                    try:
                        name = birth_reg.get_human_name(node.agent_id)
                        if name:
                            node.display_name = name
                        else:
                            node.display_name = str(node.agent_id)
                    except Exception:
                        # best-effort: leave existing display_name
                        continue
        except Exception:
            pass
        grouped: dict[int, list[LineageNode]] = defaultdict(list)
        for node in nodes:
            grouped[int(getattr(node, "generation", 0))].append(node)

        max_width = 0.0
        widths: dict[int, float] = {}
        for generation, items in grouped.items():
            ordered = sorted(
                items,
                key=lambda item: (
                    int(getattr(item, "generation_index", 0) or 0) if int(getattr(item, "generation_index", 0) or 0) > 0 else 10**9,
                    str(getattr(item, "agent_id", "")),
                ),
            )
            grouped[generation] = ordered
            width = max(0.0, (len(ordered) - 1) * NODE_SPACING_X)
            widths[generation] = width
            max_width = max(max_width, width)

        positioned: list[LineageNode] = []
        for generation in sorted(grouped.keys()):
            row = grouped[generation]
            row_width = widths[generation]
            row_offset = (max_width - row_width) * 0.5
            for idx, node in enumerate(row):
                node.tree_x = float(row_offset + (idx * NODE_SPACING_X))
                node.tree_y = float(generation * GENERATION_ROW_H)
                positioned.append(node)

        self._nodes = positioned
        self._needs_rebuild = False
        self._fit_pending = True

    def handle_event(self, event: Any) -> tuple[bool, str | None]:
        if not self._visible:
            return (False, None)
        try:
            import pygame  # type: ignore
        except Exception:
            return (False, None)

        event_type = getattr(event, "type", None)
        if event_type == pygame.QUIT:
            return (False, None)

        if event_type == pygame.KEYDOWN:
            key = getattr(event, "key", None)
            if key in (pygame.K_ESCAPE, pygame.K_l):
                self.close()
                return (True, None)
            return (True, None)

        if event_type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            old_world = self._screen_to_world(mouse_pos[0], mouse_pos[1])
            step = ZOOM_STEP if getattr(event, "y", 0) > 0 else -ZOOM_STEP
            self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom + step))
            new_screen_x = old_world[0] * self._zoom + self._offset[0]
            new_screen_y = old_world[1] * self._zoom + self._offset[1]
            self._offset[0] += mouse_pos[0] - new_screen_x
            self._offset[1] += mouse_pos[1] - new_screen_y
            return (True, None)

        if event_type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            pos = getattr(event, "pos", (0, 0))
            self._dragging = True
            self._drag_start = (int(pos[0]), int(pos[1]))
            self._drag_offset_start = [self._offset[0], self._offset[1]]
            clicked = self._node_at_screen(int(pos[0]), int(pos[1]))
            if clicked:
                self._selected_id = clicked
                return (True, clicked)
            return (True, None)

        if event_type == pygame.MOUSEBUTTONUP and getattr(event, "button", None) == 1:
            self._dragging = False
            return (True, None)

        if event_type == pygame.MOUSEMOTION:
            pos = getattr(event, "pos", (0, 0))
            if self._dragging and getattr(event, "buttons", (0, 0, 0))[0]:
                dx = int(pos[0]) - self._drag_start[0]
                dy = int(pos[1]) - self._drag_start[1]
                self._offset[0] = self._drag_offset_start[0] + dx
                self._offset[1] = self._drag_offset_start[1] + dy
            self._hovered_id = self._node_at_screen(int(pos[0]), int(pos[1]))
            return (True, None)

        return (True, None)

    def draw(self, screen: Any, font: Any, font_small: Any) -> None:
        if not self._visible:
            return
        try:
            import pygame  # type: ignore
        except Exception:
            return

        screen_w, screen_h = screen.get_size()
        if self._fit_pending:
            self._fit_view(screen_w, screen_h)
            self._fit_pending = False

        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill(OVERLAY_BG)

        living_count = sum(1 for node in self._nodes if node.is_alive)
        dead_count = len(self._nodes) - living_count
        title = tr("Родословная | {living} живых {dead} умерших | ESC закрыть").format(
            living=living_count,
            dead=dead_count,
        )
        overlay.blit(font.render(title, True, TITLE_COLOR), (16, 14))

        nodes_by_id = {node.agent_id: node for node in self._nodes}
        parent_edges = self._collect_parent_edges(nodes_by_id)
        valid_parents_by_child: dict[str, list[str]] = {
            node.agent_id: self._valid_parent_ids(node, nodes_by_id) for node in self._nodes
        }
        pair_drawn: set[frozenset[str]] = set()
        for node in self._nodes:
            parent_ids = valid_parents_by_child.get(node.agent_id, [])
            if len(parent_ids) != 2:
                continue
            pair_key = frozenset(parent_ids)
            if pair_key in pair_drawn:
                continue
            pair_drawn.add(pair_key)
            a = nodes_by_id[parent_ids[0]]
            b = nodes_by_id[parent_ids[1]]
            self._draw_pair_line(
                overlay,
                self._world_to_screen(a.tree_x, a.tree_y),
                self._world_to_screen(b.tree_x, b.tree_y),
            )

        for parent_id, child_id in parent_edges:
            parent = nodes_by_id.get(parent_id)
            child = nodes_by_id.get(child_id)
            if parent is None or child is None:
                continue
            start = self._world_to_screen(parent.tree_x, parent.tree_y)
            end = self._world_to_screen(child.tree_x, child.tree_y)
            pygame.draw.line(overlay, LINE_PARENT, start, end, LINE_W)

        for node in self._nodes:
            self._draw_node(
                overlay,
                node,
                font_small,
                selected=(node.agent_id == self._selected_id),
            )

        if self._hovered_id and self._hovered_id in nodes_by_id:
            node = nodes_by_id[self._hovered_id]
            self._draw_tooltip(
                overlay,
                node,
                font_small,
                self._world_to_screen(node.tree_x, node.tree_y),
            )

        screen.blit(overlay, (0, 0))

    def _world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        sx = int((_safe_float(x, 0.0) * self._zoom) + self._offset[0])
        sy = int((_safe_float(y, 0.0) * self._zoom) + self._offset[1])
        return (sx, sy)

    def _screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        world_x = (_safe_float(sx, 0.0) - self._offset[0]) / max(self._zoom, 1e-6)
        world_y = (_safe_float(sy, 0.0) - self._offset[1]) / max(self._zoom, 1e-6)
        return (world_x, world_y)

    def _node_at_screen(self, sx: int, sy: int) -> str | None:
        world_x, world_y = self._screen_to_world(sx, sy)
        for node in self._nodes:
            radius = NODE_R_ALIVE if node.is_alive else NODE_R_DEAD
            dx = world_x - node.tree_x
            dy = world_y - node.tree_y
            if (dx * dx + dy * dy) <= float(radius * radius):
                return node.agent_id
        return None

    def _valid_parent_ids(self, child: LineageNode, nodes_by_id: dict[str, LineageNode]) -> list[str]:
        child_generation = int(getattr(child, "generation", 0) or 0)
        out: list[str] = []
        seen: set[str] = set()
        # Parents are recorded as a 2-tuple (mother, father). We preserve order
        # but only include parents that we can resolve to nodes in the current
        # view. Accept parents from any earlier generation (not necessarily the
        # immediate previous generation) to support cross-generation parents.
        for raw_parent_id in tuple(getattr(child, "parents", (None, None)) or (None, None)):
            parent_id = str(raw_parent_id or "").strip()
            if not parent_id or parent_id in seen:
                continue
            seen.add(parent_id)
            parent = nodes_by_id.get(parent_id)
            if parent is None:
                # Parent missing from current node set (no memorial nor living)
                # — skip, we cannot draw a link.
                continue
            # Only accept a parent if it is from an earlier generation than the
            # child. Optionally allow parents from any earlier generation (not
            # necessarily the immediate previous) when enabled.
            try:
                parent_generation = int(getattr(parent, "generation", 0) or 0)
            except Exception:
                parent_generation = 0
            if child_generation <= 0:
                continue
            if self._allow_nonadjacent_parents:
                if parent_generation >= child_generation:
                    continue
            else:
                # Default conservative behaviour: only accept immediate
                # previous-generation parents.
                if parent_generation != (child_generation - 1):
                    continue
            out.append(parent_id)
        return out

    def _collect_parent_edges(self, nodes_by_id: dict[str, LineageNode]) -> list[tuple[str, str]]:
        edges: list[tuple[str, str]] = []
        for child in self._nodes:
            child_id = str(getattr(child, "agent_id", "") or "")
            if not child_id:
                continue
            parent_ids = self._valid_parent_ids(child, nodes_by_id)
            # Only create explicit parent->child edges when there are two
            # valid parents (a pair). Single-parent children are intentionally
            # left without direct parent edges to match inspector expectations.
            if not parent_ids or len(parent_ids) != 2:
                continue
            for parent_id in parent_ids:
                edges.append((parent_id, child_id))
        return edges

    def _draw_node(self, surface: Any, node: LineageNode, font_small: Any, *, selected: bool = False) -> None:
        import pygame  # type: ignore

        center = self._world_to_screen(node.tree_x, node.tree_y)
        radius = int((NODE_R_ALIVE if node.is_alive else NODE_R_DEAD) * self._zoom)
        radius = max(6, radius)

        if node.is_alive:
            color = NODE_F_ALIVE if str(node.sex).upper() == "F" else NODE_M_ALIVE
        else:
            color = NODE_DEAD
        pygame.draw.circle(surface, color, center, radius)
        pygame.draw.circle(surface, NODE_BORDER, center, radius, max(1, int(NODE_BORDER_W * self._zoom)))

        if selected:
            pygame.draw.circle(surface, NODE_SELECTED, center, radius + 4, max(1, int(2 * self._zoom)))

        if not node.is_alive:
            offset = int(radius * 0.45)
            pygame.draw.line(surface, NODE_BORDER, (center[0] - offset, center[1] - offset), (center[0] + offset, center[1] + offset), max(1, int(2 * self._zoom)))
            pygame.draw.line(surface, NODE_BORDER, (center[0] + offset, center[1] - offset), (center[0] - offset, center[1] + offset), max(1, int(2 * self._zoom)))

        label = font_small.render(str(node.display_name), True, TITLE_COLOR)
        label_rect = label.get_rect(center=(center[0], center[1] + radius + 12))
        surface.blit(label, label_rect.topleft)

    def _draw_pair_line(self, surface: Any, pos_a: tuple[int, int], pos_b: tuple[int, int]) -> None:
        import pygame  # type: ignore

        x1, y1 = pos_a
        x2, y2 = pos_b
        if y1 != y2:
            y = int((y1 + y2) * 0.5)
        else:
            y = y1
        left = min(x1, x2)
        right = max(x1, x2)
        cursor = left
        while cursor < right:
            end = min(right, cursor + LINE_PAIR_DASH)
            pygame.draw.line(surface, LINE_PAIR, (cursor, y), (end, y), LINE_W)
            cursor += LINE_PAIR_DASH * 2

    def _draw_tooltip(
        self,
        surface: Any,
        node: LineageNode,
        font_small: Any,
        screen_pos: tuple[int, int],
    ) -> None:
        import pygame  # type: ignore

        lines = [
            f"{node.display_name} {node.sex}",
            tr("Возраст: {age:.1f}s").format(age=node.age),
            tr("Потомков: {n}").format(n=node.total_offspring),
            (tr("Жив") if node.is_alive else tr("Умер: {cause}").format(cause=node.cause_of_death or tr("неизвестно"))),
        ]
        text_surfaces = [font_small.render(line, True, TITLE_COLOR) for line in lines]
        width = max(item.get_width() for item in text_surfaces) + 14
        height = sum(item.get_height() for item in text_surfaces) + 14
        x = min(surface.get_width() - width - 8, screen_pos[0] + 16)
        y = min(surface.get_height() - height - 8, screen_pos[1] + 12)
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(surface, (246, 241, 232), rect, border_radius=6)
        pygame.draw.rect(surface, NODE_BORDER, rect, 1, border_radius=6)
        cursor = y + 6
        for item in text_surfaces:
            surface.blit(item, (x + 7, cursor))
            cursor += item.get_height()

    def _fit_view(self, screen_w: int, screen_h: int) -> None:
        if not self._nodes:
            self._zoom = 1.0
            self._offset = [screen_w * 0.5, 120.0]
            return

        min_x = min(node.tree_x for node in self._nodes)
        max_x = max(node.tree_x for node in self._nodes)
        min_y = min(node.tree_y for node in self._nodes)
        max_y = max(node.tree_y for node in self._nodes)
        tree_w = max(1.0, max_x - min_x + (NODE_R_ALIVE * 2))
        tree_h = max(1.0, max_y - min_y + (NODE_R_ALIVE * 2))
        target_zoom = min((screen_w * 0.85) / tree_w, ((screen_h - 100) * 0.85) / tree_h)
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, target_zoom))
        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        self._offset[0] = (screen_w * 0.5) - (center_x * self._zoom)
        self._offset[1] = (screen_h * 0.5) - (center_y * self._zoom) + 24.0


__all__ = [
    "GENERATION_ROW_H",
    "LineageOverlay",
]
