## Abstract

Russian version: [NOWA_Body_Layer_AffectiveSpace_Body_Addendum.ru.md](NOWA_Body_Layer_AffectiveSpace_Body_Addendum.ru.md)

The addendum of 24 August 2026 changes the muscle path of the protocol body and leaves in force the Phase 1 contract for the `tool_id` format, the `status` envelope, `ApprovalGate`, and `MockMCP`. The agent chooses a write-tool identifier or the action `wait_and_monitor`. Parameters are assembled by `SchemaBinder` from a JSON Schema, world state, a lexicon, and the `rank_weights()` of the canonical affective state A(t). The YAML reference to a motor-adapter class, previously required, is removed: a role has no separate Python muscle class. Feedback records the event `action:{tool_id}`.

The platform package is located in `src/mcp_body/`; the demonstration host `nowa_body` re-exports it. `MotorAdapter` is retained as a deprecated shim so that former imports do not break. The `nowa_sandbox` contour is not changed by this addendum and remains separate from the protocol body. A later accounting-system server is defined as another `MCPTransport`: the core, the schema binder, and the YAML shape do not change when the transport changes.

---

# Addendum: AffectiveSpace canon + body without MotorAdapter

**Date:** 2026-08-24  
**Spec:** `Docs/spec_affective_space_platform_body.md` (v1.1)  
**Supersedes:** Phase 1 MotorAdapter as the extension point (`ProcurementBodyMotorAdapter`, required `motor_adapter:` in YAML).

Phase 1 (`NOWA_Body_Layer_Phase1_AsBuilt_MCP_API.md`) remains the contract for
`tool_id` format, the status envelope, ApprovalGate, and MockMCP. The muscle
path changed:

| Phase 1 | This addendum |
|---|---|
| Agent chooses an `action_type` | Agent chooses a WRITE `tool_id` (or `wait_and_monitor`) |
| `MotorAdapter._build_params` | `SchemaBinder` (JSON Schema + WorldState + lexicon + `rank_weights()`) |
| Required YAML `motor_adapter: pkg:Class` | No role Python muscle class |
| Feedback `action:{strategy}` | Feedback `action:{tool_id}` |

Platform package: `src/mcp_body/`. Demo host (`nowa_body`) re-exports it.
`MotorAdapter` remains only as a deprecated shim so old imports do not crash.
Sandbox (`nowa_sandbox`) is unchanged.

A future 1C MCP server is another `MCPTransport`. Core, binder, and YAML shape
do not change.
