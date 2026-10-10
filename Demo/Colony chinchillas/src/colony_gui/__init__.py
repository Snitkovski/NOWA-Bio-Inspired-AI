"""Colony GUI package for rendering-oriented snapshot processing."""

from .agent_panel import AgentPanel
from .agent_inspector import (
    AgentInspectorOverlay,
    InspectorData,
    build_inspector_data_from_agent,
    build_inspector_data_from_memorial,
)
from .cage_view import get_zone_render_pos
from .colony_gui import ColonyGUI
from .config import (
    ACTION_ANIMATIONS,
    ACTION_SFX,
    AFFECT_BORDER_COLORS,
    DEFAULT_SPEED,
    GUI_CONTROLS,
    NAME_FORMAT_REGEX,
    SIM_SPEED_LEVELS,
    ZONE_RENDER_COORDS,
    ZONE_SLOT_OFFSETS,
    format_agent_name,
    is_formatted_name,
)
from .interaction_overlay import InteractionEntry
from .lineage_overlay import GENERATION_ROW_H, LineageOverlay
from .resource_bar import ResourceBar
from .swarm_analytics import (
    SwarmAnalytics,
    build_swarm_analytics,
)
from .swarm_analytics_overlay import SwarmAnalyticsOverlay
from .utils import format_sim_time

__all__ = [
    "ACTION_ANIMATIONS",
    "ACTION_SFX",
    "AFFECT_BORDER_COLORS",
    "AgentPanel",
    "AgentInspectorOverlay",
    "ColonyGUI",
    "DEFAULT_SPEED",
    "GENERATION_ROW_H",
    "GUI_CONTROLS",
    "InspectorData",
    "InteractionEntry",
    "LineageOverlay",
    "NAME_FORMAT_REGEX",
    "ResourceBar",
    "SIM_SPEED_LEVELS",
    "SwarmAnalytics",
    "SwarmAnalyticsOverlay",
    "ZONE_RENDER_COORDS",
    "ZONE_SLOT_OFFSETS",
    "format_agent_name",
    "format_sim_time",
    "get_zone_render_pos",
    "is_formatted_name",
    "build_inspector_data_from_agent",
    "build_inspector_data_from_memorial",
    "build_swarm_analytics",
]
