"""Platform body: MCP organs, WorldState, SchemaBinder, ApprovalGate.

The mind never imports this package. Hosts (Demo lab, a future 1C transport)
register WRITE ``tool_id``s as basal-ganglia channels and call
``BusinessAgentRuntime``.
"""

from .approval_gate import ApprovalGate, ApprovalRecord, ApprovalStatus
from .feedback import apply_feedback_to_agent, approval_to_reward
from .field_lexicon import classify_field, merge_aliases
from .generic_encoder import GenericEncoder, mapped_event_tokens
from .hard_constraints import HardConstraintViolation, assert_stage2_invariant
from .mcp_capability import CapabilityRisk, MCPCapability, parse_risk
from .mcp_client import (
    MCPToolDescriptor,
    MCPTransport,
    list_tool_descriptors,
    make_tool_id,
    normalize_envelope,
    sanitize_tool_name,
)
from .mcp_http import (
    HttpMCPClient,
    HttpMCPError,
    basic_authorization_header,
    mcp_transport_from_server,
)
from .organ_registry import MCPToolRegistry, OrganRegistry
from .proposed_action import ProposedAction, new_action_id, summarize_call
from .risk_classifier import RISK_KEYWORDS, classify_risk_heuristic
from .runtime import WAIT_AND_MONITOR, BusinessAgentRuntime
from .schema_binder import SchemaBinder
from .seeder import BusinessHippocampusSeeder, SeedEpisode
from .world_state import WorldState

__all__ = [
    "ApprovalGate",
    "ApprovalRecord",
    "ApprovalStatus",
    "BusinessAgentRuntime",
    "BusinessHippocampusSeeder",
    "CapabilityRisk",
    "GenericEncoder",
    "mapped_event_tokens",
    "HardConstraintViolation",
    "HttpMCPClient",
    "HttpMCPError",
    "MCPCapability",
    "MCPToolDescriptor",
    "MCPToolRegistry",
    "MCPTransport",
    "OrganRegistry",
    "ProposedAction",
    "RISK_KEYWORDS",
    "SchemaBinder",
    "SeedEpisode",
    "WAIT_AND_MONITOR",
    "WorldState",
    "apply_feedback_to_agent",
    "approval_to_reward",
    "assert_stage2_invariant",
    "basic_authorization_header",
    "classify_field",
    "classify_risk_heuristic",
    "list_tool_descriptors",
    "make_tool_id",
    "mcp_transport_from_server",
    "merge_aliases",
    "new_action_id",
    "normalize_envelope",
    "parse_risk",
    "sanitize_tool_name",
    "summarize_call",
]
