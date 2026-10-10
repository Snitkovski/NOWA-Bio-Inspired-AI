"""Simple tkinter Canvas line charts for sandbox fitness series."""

from __future__ import annotations

import tkinter as tk
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


CRITERION_COLORS = {
    "cost_efficiency": "#2563eb",
    "stockout_avoidance": "#dc2626",
    "budget_discipline": "#16a34a",
    "reaction_to_risk_events": "#9333ea",
    "supplier_diversification": "#ea580c",
    "decision_consistency": "#0891b2",
}

# Pixel radius for hover hit-testing against plotted points.
_HIT_RADIUS = 10


class FitnessChart(tk.Canvas):
    """Multi-series line chart; values expected in [0, 1].

    Legend is drawn below the plot. Hovering near a data point shows a
    tooltip with the criterion label and value.
    """

    def __init__(self, master, **kwargs):
        kwargs.setdefault("background", "#fafafa")
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", "#d4d4d4")
        super().__init__(master, **kwargs)
        self._series: Dict[str, List[float]] = {}
        self._categories: List[str] = []
        self._labels: Dict[str, str] = {}
        self._hit_points: List[Dict[str, object]] = []
        self._plot_box: Tuple[float, float, float, float] = (0, 0, 0, 0)
        self.empty_message: str = "No quarter data yet"
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    def set_labels(self, labels: Optional[Mapping[str, str]]) -> None:
        """Optional display names for series keys (legend / tooltip)."""
        self._labels = dict(labels or {})
        self.redraw()

    def set_data(
        self,
        categories: Sequence[str],
        series: Mapping[str, Sequence[float]],
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._categories = [str(c) for c in categories]
        self._series = {
            name: [float(v) for v in values] for name, values in series.items()
        }
        if labels is not None:
            self._labels = dict(labels)
        self.redraw()

    def clear(self) -> None:
        self._categories = []
        self._series = {}
        self._hit_points = []
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        self._hit_points = []
        width = max(int(self.winfo_width()), 40)
        height = max(int(self.winfo_height()), 40)

        pad_l, pad_r, pad_t = 44, 12, 14
        legend_h = self._legend_height(width - pad_l - pad_r)
        # X tick labels sit between plot and legend.
        pad_b = 22 + legend_h
        plot_w = max(width - pad_l - pad_r, 10)
        plot_h = max(height - pad_t - pad_b, 10)
        self._plot_box = (pad_l, pad_t, pad_l + plot_w, pad_t + plot_h)

        self.create_rectangle(
            pad_l, pad_t, pad_l + plot_w, pad_t + plot_h, outline="#a3a3a3"
        )
        for frac, label in ((0.0, "1.0"), (0.5, "0.5"), (1.0, "0.0")):
            y = pad_t + frac * plot_h
            self.create_line(pad_l - 4, y, pad_l, y, fill="#737373")
            self.create_text(
                pad_l - 8,
                y,
                text=label,
                anchor="e",
                fill="#525252",
                font=("Segoe UI", 8),
            )

        if not self._categories or not self._series:
            self.create_text(
                pad_l + plot_w / 2,
                pad_t + plot_h / 2,
                text=self.empty_message,
                fill="#a3a3a3",
                font=("Segoe UI", 10),
            )
            self._draw_legend(pad_l, pad_t + plot_h + 20, plot_w)
            return

        n = len(self._categories)
        for name, values in self._series.items():
            if not values:
                continue
            color = CRITERION_COLORS.get(name, "#404040")
            points: List[float] = []
            count = min(n, len(values))
            for i in range(count):
                x = pad_l + (i / max(count - 1, 1)) * plot_w
                clamped = max(0.0, min(1.0, values[i]))
                y = pad_t + (1.0 - clamped) * plot_h
                points.extend([x, y])
                self._hit_points.append(
                    {
                        "x": x,
                        "y": y,
                        "name": name,
                        "label": self._labels.get(name, name),
                        "value": float(values[i]),
                        "category": self._categories[i],
                        "color": color,
                    }
                )
            if count >= 2:
                self.create_line(
                    *points,
                    fill=color,
                    width=2,
                    tags=("series", f"series:{name}"),
                )
            elif count == 1:
                self.create_oval(
                    points[0] - 3,
                    points[1] - 3,
                    points[0] + 3,
                    points[1] + 3,
                    fill=color,
                    outline="",
                    tags=("series", f"series:{name}"),
                )

        step = max(1, n // 8)
        for i in range(0, n, step):
            x = pad_l + (i / max(n - 1, 1)) * plot_w
            self.create_text(
                x,
                pad_t + plot_h + 4,
                text=self._categories[i],
                anchor="n",
                fill="#525252",
                font=("Segoe UI", 8),
            )

        self._draw_legend(pad_l, pad_t + plot_h + 20, plot_w)

    def _legend_height(self, plot_w: float) -> int:
        names = list(self._series) if self._series else list(self._labels) or list(
            CRITERION_COLORS
        )
        if not names:
            return 28
        # Estimate columns from available width (~140 px per item).
        cols = max(1, min(len(names), int(max(plot_w, 80) // 140)))
        rows = (len(names) + cols - 1) // cols
        return 8 + rows * 16

    def _draw_legend(self, x0: float, y0: float, plot_w: float) -> None:
        names = list(self._series.keys()) if self._series else []
        if not names and self._labels:
            names = list(self._labels.keys())
        if not names:
            return
        cols = max(1, min(len(names), int(max(plot_w, 80) // 140)))
        col_w = plot_w / cols
        for idx, name in enumerate(names):
            row = idx // cols
            col = idx % cols
            lx = x0 + col * col_w
            ly = y0 + row * 16
            color = CRITERION_COLORS.get(name, "#404040")
            label = self._labels.get(name, name)
            self.create_rectangle(
                lx, ly, lx + 10, ly + 10, fill=color, outline="", tags=("legend",)
            )
            self.create_text(
                lx + 14,
                ly + 5,
                text=label,
                anchor="w",
                fill="#404040",
                font=("Segoe UI", 8),
                tags=("legend",),
            )

    def _on_motion(self, event: tk.Event) -> None:
        if not self._hit_points:
            self._hide_tooltip()
            return
        best = None
        best_dist = float(_HIT_RADIUS)
        for pt in self._hit_points:
            dx = float(pt["x"]) - event.x
            dy = float(pt["y"]) - event.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= best_dist:
                best_dist = dist
                best = pt
        if best is None:
            self._hide_tooltip()
            return
        label = str(best["label"])
        value = float(best["value"])
        category = str(best["category"])
        text = f"{label}\nQ{category}: {value:.3f}"
        self._show_tooltip(event.x, event.y, text, str(best["color"]))

    def _on_leave(self, _event: tk.Event) -> None:
        self._hide_tooltip()

    def _hide_tooltip(self) -> None:
        self.delete("tooltip")

    def _show_tooltip(
        self, x: float, y: float, text: str, color: str
    ) -> None:
        self._hide_tooltip()
        # Place tooltip near cursor, keep inside canvas.
        pad = 6
        tip = self.create_text(
            0,
            0,
            text=text,
            anchor="nw",
            fill="#1f2937",
            font=("Segoe UI", 9),
            tags=("tooltip",),
            justify="left",
        )
        bbox = self.bbox(tip)
        if not bbox:
            return
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        width = max(int(self.winfo_width()), 40)
        height = max(int(self.winfo_height()), 40)
        tx = x + 14
        ty = y - th - 10
        if tx + tw + pad > width:
            tx = x - tw - 14
        if ty < 2:
            ty = y + 14
        if ty + th + pad > height:
            ty = max(2, height - th - pad)
        self.coords(tip, tx, ty)
        self.create_rectangle(
            tx - pad,
            ty - pad,
            tx + tw + pad,
            ty + th + pad,
            fill="#fffbeb",
            outline=color or "#a3a3a3",
            width=2,
            tags=("tooltip",),
        )
        self.tag_raise(tip)


__all__ = ["CRITERION_COLORS", "FitnessChart"]
