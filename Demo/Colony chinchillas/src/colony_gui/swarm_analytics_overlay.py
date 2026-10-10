"""Pygame overlay for read-only colony swarm analytics."""

from __future__ import annotations

import math
from typing import Any

from .swarm_analytics import (
    BehaviorPattern,
    GenerationSummary,
    SwarmAnalytics,
    build_swarm_analytics,
    compare_first_last_third,
)


OVERLAY_WIDTH = 900
OVERLAY_HEIGHT = 680
TABS = ["Состояние", "Эволюция", "Геномы", "Поведение", "Прогноз"]

OVERLAY_BG = (242, 236, 225, 248)
OVERLAY_HEADER = (218, 208, 192)
OVERLAY_BORDER = (115, 100, 82)
SECTION_LINE = (195, 182, 165)
SECTION_TITLE_CLR = (108, 95, 78)
TAB_ACTIVE = (198, 185, 168)
TAB_INACTIVE = (228, 220, 208)
TAB_TEXT_ACTIVE = (35, 28, 20)
TAB_TEXT_INACTIVE = (100, 88, 70)
TEXT_COLOR = (35, 28, 20)
MUTED_TEXT = (104, 93, 78)
BAR_BG = (212, 202, 188)
GOOD = (92, 165, 105)
WARN = (190, 160, 70)
BAD = (200, 75, 62)
BLUE = (90, 145, 205)

GEN_COLORS: list[tuple[int, int, int]] = [
    (100, 155, 210),
    (90, 185, 125),
    (215, 145, 60),
    (185, 90, 175),
    (80, 175, 175),
    (210, 80, 80),
    (165, 160, 65),
    (130, 100, 195),
    (70, 140, 80),
    (200, 120, 90),
    (90, 130, 200),
    (170, 175, 75),
]


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _fmt_time(seconds: float) -> str:
    value = max(0, int(seconds))
    h = value // 3600
    m = (value % 3600) // 60
    s = value % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class SwarmAnalyticsOverlay:
    """Full-screen analytics overlay for colony-scale evolution."""

    def __init__(self) -> None:
        self._visible = False
        self._active_tab = 0
        self._scroll = 0
        self._data: SwarmAnalytics | None = None
        self._panel_rect: Any = None
        self._tab_rects: list[Any] = []
        self._needs_rebuild = True

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self) -> None:
        self._visible = not self._visible
        self._scroll = 0
        if self._visible:
            self.mark_dirty()

    def close(self) -> None:
        self._visible = False
        self._scroll = 0

    def mark_dirty(self) -> None:
        self._needs_rebuild = True

    def refresh(self, runner: Any, observer: Any = None, generation_index_map: dict[str, int] | None = None) -> None:
        self._data = build_swarm_analytics(runner, observer, generation_index_map=generation_index_map)
        self._needs_rebuild = False
        self._scroll = 0

    def handle_event(self, event: Any) -> bool:
        if not self._visible:
            return False
        try:
            import pygame  # type: ignore
        except Exception:
            return True

        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_a, pygame.K_TAB):
                self.close()
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self._active_tab = min(len(TABS) - 1, self._active_tab + 1)
                self._scroll = 0
                return True
            if event.key in (pygame.K_LEFT, pygame.K_q):
                self._active_tab = max(0, self._active_tab - 1)
                self._scroll = 0
                return True
            if event.key == pygame.K_r:
                self.mark_dirty()
                return True
            return True
        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, self._scroll - int(event.y) * 32)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = getattr(event, "pos", None)
            if pos is not None:
                for idx, rect in enumerate(self._tab_rects):
                    if rect.collidepoint(pos):
                        self._active_tab = idx
                        self._scroll = 0
                        break
            return True
        return True

    def _wrap_text(self, text: str, font: Any, max_width: int) -> list[str]:
        if not text:
            return [""]
        if font.size(text)[0] <= max_width:
            return [text]
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
        if current:
            lines.append(current)
        return lines or [text]

    def _fit_text(self, text: str, font: Any, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text
        trimmed = text
        while trimmed and font.size(f"{trimmed}...")[0] > max_width:
            trimmed = trimmed[:-1]
        return f"{trimmed}..." if trimmed else "..."

    def _section(self, surface: Any, font_small: Any, y: int, title: str) -> int:
        import pygame  # type: ignore

        rendered = font_small.render(title.upper(), True, SECTION_TITLE_CLR)
        surface.blit(rendered, (0, y))
        line_y = y + rendered.get_height() // 2
        pygame.draw.line(surface, SECTION_LINE, (rendered.get_width() + 10, line_y), (surface.get_width() - 2, line_y), 1)
        return y + rendered.get_height() + 8

    def _bar(
        self,
        surface: Any,
        x: int,
        y: int,
        width: int,
        value: float,
        color: tuple[int, int, int] = BLUE,
        *,
        height: int = 9,
    ) -> None:
        import pygame  # type: ignore

        clamped = _clamp(float(value))
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(surface, BAR_BG, rect, border_radius=3)
        if clamped > 0.0:
            pygame.draw.rect(surface, color, pygame.Rect(x, y, max(1, int(width * clamped)), height), border_radius=3)

    def _metric_row(
        self,
        surface: Any,
        font_small: Any,
        y: int,
        label: str,
        value: float,
        *,
        std: float | None = None,
        color: tuple[int, int, int] = BLUE,
        note: str = "",
    ) -> int:
        surface.blit(font_small.render(self._fit_text(label, font_small, 142), True, TEXT_COLOR), (0, y))
        self._bar(surface, 150, y + 4, 120, value, color)
        value_text = f"{value:.2f}"
        if std is not None:
            value_text += f"  ±{std:.2f}"
        surface.blit(font_small.render(value_text, True, TEXT_COLOR), (282, y))
        if note:
            surface.blit(font_small.render(self._fit_text(note, font_small, surface.get_width() - 392), True, MUTED_TEXT), (390, y))
        return y + 20

    def _draw_loading(self, surface: Any, font: Any, font_small: Any) -> int:
        surface.blit(font.render("Аналитика роя", True, TEXT_COLOR), (0, 6))
        text = "Данные ещё не собраны. Нажмите A заново или R для обновления."
        surface.blit(font_small.render(text, True, MUTED_TEXT), (0, 42))
        return 70

    def _draw_tab_state(self, surface: Any, font: Any, font_small: Any, _font_mono: Any) -> int:
        assert self._data is not None
        data = self._data
        metrics = data.current_metrics
        y = 6
        female = int(metrics.get("female_count", 0.0))
        male = int(metrics.get("male_count", 0.0))
        sleeping = int(metrics.get("sleeping_count", 0.0))
        title = "ТЕКУЩИЙ СРЕЗ КОЛОНИИ"
        surface.blit(font.render(title, True, TEXT_COLOR), (0, y))
        y += 28
        info = (
            f"sim_time: {_fmt_time(data.snapshot_time)}  |  живых: {data.living_count} "
            f"({female}F {male}M)  |  умерших: {data.dead_count}"
        )
        surface.blit(font_small.render(info, True, MUTED_TEXT), (0, y))
        y += 20
        gen_info = f"Поколения: G{data.generation_range[0]}-G{data.generation_range[1]}  |  средний возраст: {_fmt_time(metrics.get('mean_age', 0.0))}  |  спящих: {sleeping}"
        surface.blit(font_small.render(gen_info, True, MUTED_TEXT), (0, y))
        y += 30

        y = self._section(surface, font_small, y, "Аффективный срез")
        tone = "ХРОНИЧЕСКАЯ ТРЕВОГА" if metrics.get("mean_stress", 0.0) > 0.65 else "СТАБИЛЬНЫЙ ФОН"
        surface.blit(font_small.render(f"Итоговый аффективный тон роя: {tone}", True, TEXT_COLOR), (0, y))
        y += 24
        critical_stress = int(round(data.living_count * max(0.0, metrics.get("mean_stress", 0.0) - 0.65) / 0.35))
        y = self._metric_row(surface, font_small, y, "стресс", metrics.get("mean_stress", 0.0), std=metrics.get("std_stress", 0.0), color=BAD, note=f"критический у {critical_stress} из {data.living_count}")
        y = self._metric_row(surface, font_small, y, "кортизол", metrics.get("mean_cortisol", 0.0), std=metrics.get("std_cortisol", 0.0), color=BAD)
        y = self._metric_row(surface, font_small, y, "энергия", metrics.get("mean_energy", 0.0), std=metrics.get("std_energy", 0.0), color=GOOD)
        y = self._metric_row(surface, font_small, y, "социал. драйв", metrics.get("mean_social_drive", 0.0), color=BLUE)
        y = self._metric_row(surface, font_small, y, "любопытство", metrics.get("mean_curiosity", 0.0), color=(80, 170, 200))
        y += 10

        y = self._section(surface, font_small, y, "Нейрохимия популяции")
        y = self._metric_row(surface, font_small, y, "дофамин", metrics.get("mean_dopamine", 0.0), color=(100, 160, 220))
        y = self._metric_row(surface, font_small, y, "серотонин", metrics.get("mean_serotonin", 0.0), color=(90, 190, 130))
        y = self._metric_row(surface, font_small, y, "норадреналин", metrics.get("mean_norepinephrine", 0.0), color=(215, 140, 65))
        y = self._metric_row(surface, font_small, y, "кортизол", metrics.get("mean_cortisol", 0.0), color=BAD)
        y = self._metric_row(surface, font_small, y, "ацетилхолин", metrics.get("mean_acetylcholine", 0.0), color=(140, 110, 200))
        y += 10

        y = self._section(surface, font_small, y, "Ресурсы")
        x = 0
        for label, key, color in [("корм", "food_pellets", (190, 142, 82)), ("сено", "hay", (188, 170, 74)), ("вода", "water", (88, 156, 225))]:
            value = float(data.resources.get(key, 0.0))
            surface.blit(font_small.render(label, True, TEXT_COLOR), (x, y))
            self._bar(surface, x + 42, y + 4, 100, value, color)
            surface.blit(font_small.render(f"{value:.2f}", True, TEXT_COLOR), (x + 150, y))
            x += 245
        return y + 28

    def _draw_generation_series(
        self,
        surface: Any,
        font_small: Any,
        y: int,
        label: str,
        summaries: list[GenerationSummary],
        value_getter: Any,
        *,
        normalize: float = 1.0,
    ) -> int:
        selected = self._select_display_generations(summaries)
        surface.blit(font_small.render(label, True, TEXT_COLOR), (0, y))
        x = 170
        max_w = max(28, min(56, (surface.get_width() - x - 4) // max(1, len(selected))))
        values: list[float] = []
        for summary in selected:
            value = float(value_getter(summary))
            values.append(value)
            text = f"G{summary.generation}"
            surface.blit(font_small.render(text, True, MUTED_TEXT), (x, y))
            self._bar(surface, x, y + 18, max_w - 5, value / normalize, GEN_COLORS[summary.generation % len(GEN_COLORS)], height=10)
            surface.blit(font_small.render(f"{value:.2f}" if value < 10 else f"{value:.0f}", True, TEXT_COLOR), (x, y + 31))
            x += max_w
        trend, magnitude = compare_first_last_third(values, normalize)
        surface.blit(font_small.render(f"тренд: {trend}  Δ{magnitude:.2f}", True, MUTED_TEXT), (0, y + 34))
        return y + 58

    def _draw_tab_evolution(self, surface: Any, font: Any, font_small: Any, _font_mono: Any) -> int:
        assert self._data is not None
        data = self._data
        y = 6
        surface.blit(font.render("ЭВОЛЮЦИОННЫЕ ТРЕНДЫ ПО ПОКОЛЕНИЯМ", True, TEXT_COLOR), (0, y))
        y += 28
        info = f"{len(data.generation_summaries)} поколений  |  {data.dead_count} умерших агентов в базе"
        surface.blit(font_small.render(info, True, MUTED_TEXT), (0, y))
        y += 30
        if len(data.generation_summaries) < 2:
            surface.blit(font_small.render("Для эволюционных трендов нужно минимум два поколения.", True, MUTED_TEXT), (0, y))
            return y + 30
        y = self._section(surface, font_small, y, "Стресс и кортизол")
        y = self._draw_generation_series(surface, font_small, y, "стресс", data.generation_summaries, lambda s: s.mean_stress_at_death)
        y = self._draw_generation_series(surface, font_small, y, "кортизол", data.generation_summaries, lambda s: s.mean_cortisol_at_death)
        y = self._section(surface, font_small, y + 8, "Продолжительность жизни")
        lifespan_norm = max(1.0, max(summary.mean_lived_steps for summary in data.generation_summaries))
        y = self._draw_generation_series(surface, font_small, y, "ср. прожито шагов", data.generation_summaries, lambda s: s.mean_lived_steps, normalize=lifespan_norm)
        y = self._section(surface, font_small, y + 8, "Энергия при смерти")
        y = self._draw_generation_series(surface, font_small, y, "энергия", data.generation_summaries, lambda s: s.mean_energy_at_death)
        y = self._section(surface, font_small, y + 8, "Репродукция")
        return self._draw_generation_series(surface, font_small, y, "потомков/агента", data.generation_summaries, lambda s: s.mean_total_offspring, normalize=max(1.0, max(summary.mean_total_offspring for summary in data.generation_summaries)))

    def _draw_gene_track(self, surface: Any, font_small: Any, y: int, track: Any) -> int:
        first_gen = min(track.values_by_gen)
        last_gen = max(track.values_by_gen)
        first = track.values_by_gen[first_gen]
        last = track.values_by_gen[last_gen]
        marker = "●" if track.is_under_selection else "~"
        headline = f"{marker} {track.gene_key:<28} {track.trend_label:<12} Δ{track.trend_magnitude:.2f} ({first:.2f} → {last:.2f})"
        surface.blit(font_small.render(self._fit_text(headline, font_small, surface.get_width() - 4), True, TEXT_COLOR), (0, y))
        y += 18
        for line in self._wrap_text(f'"{track.interpretation}"', font_small, surface.get_width() - 12)[:2]:
            surface.blit(font_small.render(line, True, MUTED_TEXT), (12, y))
            y += 16
        gens = sorted(track.values_by_gen)
        step = max(1, math.ceil(len(gens) / 12))
        shown = gens[::step]
        if gens[-1] not in shown:
            shown.append(gens[-1])
        x = 12
        min_v = min(track.values_by_gen.values())
        max_v = max(track.values_by_gen.values())
        span = max(1e-6, max_v - min_v)
        for gen in shown[:12]:
            value = track.values_by_gen[gen]
            surface.blit(font_small.render(f"G{gen}", True, MUTED_TEXT), (x, y))
            self._bar(surface, x + 28, y + 4, 48, (value - min_v) / span if span > 0 else 0.5, GEN_COLORS[gen % len(GEN_COLORS)], height=8)
            x += 82
        return y + 22

    def _draw_tab_genomes(self, surface: Any, font: Any, font_small: Any, _font_mono: Any) -> int:
        assert self._data is not None
        data = self._data
        y = 6
        selected = [track for track in data.gene_tracks if track.is_under_selection]
        stable = [track for track in data.gene_tracks if not track.is_under_selection]
        surface.blit(font.render("ЭВОЛЮЦИЯ ГЕНОМА ПО ПОКОЛЕНИЯМ", True, TEXT_COLOR), (0, y))
        y += 28
        surface.blit(font_small.render(f"{len(data.gene_tracks)} отслеживаемых генов | под отбором: {len(selected)} | стабильных: {len(stable)}", True, MUTED_TEXT), (0, y))
        y += 28
        y = self._section(surface, font_small, y, "Гены под активным отбором")
        if not selected:
            surface.blit(font_small.render("Выраженного направленного отбора пока не видно.", True, MUTED_TEXT), (0, y))
            y += 22
        for track in selected[:5]:
            y = self._draw_gene_track(surface, font_small, y, track) + 8
        y = self._section(surface, font_small, y, "Стабильные гены")
        for track in stable[:10]:
            text = f"~ {track.gene_key:<28} {track.trend_label:<12} Δ±{track.trend_magnitude:.2f}"
            surface.blit(font_small.render(self._fit_text(text, font_small, surface.get_width() - 4), True, MUTED_TEXT), (0, y))
            y += 18
        y = self._section(surface, font_small, y + 8, "Генетическое разнообразие")
        diversity = data.health_index.components.get("diversity", 0.0)
        surface.blit(font_small.render(f"Текущий индекс: {diversity:.2f}", True, TEXT_COLOR), (0, y))
        self._bar(surface, 180, y + 4, 150, diversity, GOOD if diversity > 0.3 else WARN)
        return y + 28

    def _draw_pattern_list(self, surface: Any, font_small: Any, y: int, patterns: list[BehaviorPattern], total: int, *, width: int = 160) -> int:
        for pattern in patterns:
            label = self._fit_text(pattern.label_ru, font_small, 190)
            surface.blit(font_small.render(label, True, TEXT_COLOR), (0, y))
            self._bar(surface, 200, y + 4, width, pattern.fraction, BLUE)
            surface.blit(font_small.render(f"{pattern.count} ({pattern.fraction:.0%})", True, TEXT_COLOR), (200 + width + 12, y))
            y += 20
        if not patterns:
            surface.blit(font_small.render("Данных пока нет.", True, MUTED_TEXT), (0, y))
            y += 20
        return y

    def _draw_tab_behavior(self, surface: Any, font: Any, font_small: Any, _font_mono: Any) -> int:
        assert self._data is not None
        data = self._data
        y = 6
        surface.blit(font.render("ПОВЕДЕНЧЕСКИЙ ПРОФИЛЬ КОЛОНИИ", True, TEXT_COLOR), (0, y))
        y += 32
        y = self._section(surface, font_small, y, "Текущее распределение действий")
        y = self._draw_pattern_list(surface, font_small, y, data.current_action_distribution[:8], data.living_count)
        y += 8
        y = self._section(surface, font_small, y, "Социальная структура")
        social = data.current_social
        lines = [
            f"Всего известных пар: {social.total_known_pairs}",
            f"Bonded: {social.bonded_pairs}   Rival: {social.rival_pairs}   Kin: {social.kin_pairs}",
            f"Без связей: {social.isolation_count} агентов",
            f"Индекс сплочённости: {social.cohesion_index:.2f}",
        ]
        for line in lines:
            surface.blit(font_small.render(line, True, TEXT_COLOR), (0, y))
            y += 18
        y += 8
        y = self._section(surface, font_small, y, "Характеры роя")
        y = self._draw_pattern_list(surface, font_small, y, data.personality_distribution[:8], data.living_count)
        y += 8
        y = self._section(surface, font_small, y, "Гиппокамп и кортекс")
        memory_lines = [
            f"Средний размер гиппокампа: {data.mean_hippocampus_size:.0f} эпизодов (±{data.std_hippocampus_size:.0f})",
            f"Средний размер кортекса: {data.mean_cortex_patterns:.0f} паттернов (±{data.std_cortex_patterns:.0f})",
        ]
        for line in memory_lines:
            surface.blit(font_small.render(line, True, TEXT_COLOR), (0, y))
            y += 18
        surface.blit(font_small.render("Топ доминирующих привычек роя:", True, MUTED_TEXT), (0, y))
        y += 20
        return self._draw_pattern_list(surface, font_small, y, data.dominant_habits[:5], data.living_count)

    def _draw_tab_forecast(self, surface: Any, font: Any, font_small: Any, _font_mono: Any) -> int:
        assert self._data is not None
        data = self._data
        forecast = data.forecast
        y = 6
        surface.blit(font.render("ЭВОЛЮЦИОННЫЙ ПРОГНОЗ", True, TEXT_COLOR), (0, y))
        y += 32
        y = self._section(surface, font_small, y, "Индекс здоровья колонии")
        self._bar(surface, 0, y + 4, 180, data.health_index.overall, data.health_index.color, height=13)
        surface.blit(font_small.render(f"{data.health_index.overall:.2f}  {data.health_index.verdict.upper()}", True, TEXT_COLOR), (198, y))
        y += 28
        for key, value in data.health_index.components.items():
            y = self._metric_row(surface, font_small, y, key, value, color=data.health_index.color)
        y += 8
        y = self._section(surface, font_small, y, "Риски")
        for risk in forecast.key_risks[:8] or ["Критических рисков не выявлено"]:
            surface.blit(font_small.render(f"✗ {risk}", True, BAD), (0, y))
            y += 18
        y += 8
        y = self._section(surface, font_small, y, "Позитивные тренды")
        for item in forecast.key_opportunities[:8] or ["Позитивные тренды пока не выражены"]:
            surface.blit(font_small.render(f"✓ {item}", True, GOOD), (0, y))
            y += 18
        y += 8
        y = self._section(surface, font_small, y, "Давление отбора")
        surface.blit(font_small.render(f"Главный фактор: {forecast.dominant_pressure}", True, TEXT_COLOR), (0, y))
        y += 18
        surface.blit(font_small.render(self._fit_text(f"Адаптируется: {', '.join(forecast.adapting_traits) or '-'}", font_small, surface.get_width() - 4), True, MUTED_TEXT), (0, y))
        y += 18
        surface.blit(font_small.render(self._fit_text(f"Без отбора: {', '.join(forecast.stagnant_traits) or '-'}", font_small, surface.get_width() - 4), True, MUTED_TEXT), (0, y))
        y += 26
        y = self._section(surface, font_small, y, "Итоговый вывод")
        for line in self._wrap_text(f'"{forecast.summary}"', font_small, surface.get_width() - 4)[:5]:
            surface.blit(font_small.render(line, True, TEXT_COLOR), (0, y))
            y += 18
        return y + 8

    def _draw_active_tab(self, surface: Any, font: Any, font_small: Any, font_mono: Any) -> int:
        if self._data is None:
            return self._draw_loading(surface, font, font_small)
        if self._active_tab == 0:
            return self._draw_tab_state(surface, font, font_small, font_mono)
        if self._active_tab == 1:
            return self._draw_tab_evolution(surface, font, font_small, font_mono)
        if self._active_tab == 2:
            return self._draw_tab_genomes(surface, font, font_small, font_mono)
        if self._active_tab == 3:
            return self._draw_tab_behavior(surface, font, font_small, font_mono)
        return self._draw_tab_forecast(surface, font, font_small, font_mono)

    def _select_display_generations(self, summaries: list[GenerationSummary]) -> list[GenerationSummary]:
        if len(summaries) <= 12:
            return list(summaries)
        step = max(1, math.ceil(len(summaries) / 12))
        selected = list(summaries[::step])
        if summaries[0] not in selected:
            selected.insert(0, summaries[0])
        if summaries[-1] not in selected:
            selected.append(summaries[-1])
        while len(selected) > 12 and len(selected) > 2:
            selected.pop(-2)
        return selected

    def draw(self, screen: Any, font: Any, font_small: Any, font_mono: Any) -> None:
        if not self._visible:
            return
        import pygame  # type: ignore

        screen_w, screen_h = screen.get_size()
        panel_w = min(OVERLAY_WIDTH, screen_w - 24)
        panel_h = min(OVERLAY_HEIGHT, screen_h - 24)
        panel_x = max(12, (screen_w - panel_w) // 2)
        panel_y = max(12, (screen_h - panel_h) // 2)
        self._panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        veil = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 90))
        screen.blit(veil, (0, 0))

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill(OVERLAY_BG)
        pygame.draw.rect(panel, OVERLAY_BORDER, panel.get_rect(), 2, border_radius=8)
        pygame.draw.rect(panel, OVERLAY_HEADER, pygame.Rect(0, 0, panel_w, 60), border_radius=8)

        if self._data is not None:
            header = f"Аналитика роя  |  живых: {self._data.living_count}  умерших: {self._data.dead_count}  поколений: {len(self._data.generation_summaries)}"
        else:
            header = "Аналитика роя"
        panel.blit(font.render(header, True, TEXT_COLOR), (16, 12))
        panel.blit(font_small.render("ESC / A закрыть   ← → вкладки   R обновить", True, MUTED_TEXT), (16, 36))

        tabs_top = 66
        tab_h = 30
        tab_w = panel_w // len(TABS)
        self._tab_rects = []
        for idx, title in enumerate(TABS):
            rect = pygame.Rect(idx * tab_w, tabs_top, tab_w, tab_h)
            self._tab_rects.append(rect.move(panel_x, panel_y))
            active = idx == self._active_tab
            pygame.draw.rect(panel, TAB_ACTIVE if active else TAB_INACTIVE, rect, border_radius=4)
            rendered = font_small.render(title, True, TAB_TEXT_ACTIVE if active else TAB_TEXT_INACTIVE)
            panel.blit(rendered, rendered.get_rect(center=rect.center))

        content_rect = pygame.Rect(16, tabs_top + tab_h + 12, panel_w - 32, panel_h - tabs_top - tab_h - 24)
        content_h = max(content_rect.height, 1200)
        content = pygame.Surface((content_rect.width, content_h), pygame.SRCALPHA)
        content.fill((0, 0, 0, 0))
        full_h = self._draw_active_tab(content, font, font_small, font_mono)
        if full_h > content_h:
            content_h = full_h
            content = pygame.Surface((content_rect.width, content_h), pygame.SRCALPHA)
            content.fill((0, 0, 0, 0))
            full_h = self._draw_active_tab(content, font, font_small, font_mono)
        max_scroll = max(0, full_h - content_rect.height)
        self._scroll = max(0, min(self._scroll, max_scroll))
        panel.blit(content, content_rect.topleft, area=pygame.Rect(0, self._scroll, content_rect.width, content_rect.height))
        if max_scroll > 0:
            track = pygame.Rect(panel_w - 10, content_rect.y, 4, content_rect.height)
            pygame.draw.rect(panel, (210, 200, 186), track, border_radius=2)
            thumb_h = max(30, int(content_rect.height * (content_rect.height / float(max(full_h, 1)))))
            thumb_y = content_rect.y + int((content_rect.height - thumb_h) * (self._scroll / float(max_scroll)))
            pygame.draw.rect(panel, (145, 130, 108), pygame.Rect(track.x, thumb_y, track.width, thumb_h), border_radius=2)

        screen.blit(panel, (panel_x, panel_y))


__all__ = ["SwarmAnalyticsOverlay", "OVERLAY_WIDTH", "OVERLAY_HEIGHT", "TABS"]
