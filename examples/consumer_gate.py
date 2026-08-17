# v0.1.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

AUDIT_CONFORMANT = 1
AUDIT_DEGRADED = 2


@gl.contract_interface
class IConform:
    class View:
        def latest_verdict(self, agent_id: u256) -> dict: ...

    class Write:
        def audit(self, agent_id: u256) -> u256: ...


class AgentGate(gl.Contract):
    """Minimal example showing how another contract consumes Conform.

    This consumer contains no LLM call, web request, behavioural prompt, or
    equivalence rule. It relies on the shared Conform deployment's receipt.
    """

    conform: Address
    agent_id: u256
    require_fresh_spec: bool

    def __init__(self, conform: Address, agent_id: u256, require_fresh_spec: bool = True):
        self.conform = conform if isinstance(conform, Address) else Address(conform)
        self.agent_id = agent_id
        self.require_fresh_spec = require_fresh_spec

    @gl.public.view
    def can_use_agent(self) -> dict:
        verdict = IConform(self.conform).view().latest_verdict(self.agent_id)
        if not bool(verdict["has_audit"]):
            return {"allowed": False, "reason": "NO_AUDIT"}
        if self.require_fresh_spec and not bool(verdict["is_current_spec"]):
            return {"allowed": False, "reason": "STALE_AUDIT"}

        status = int(verdict["status"])
        allowed = status in (AUDIT_CONFORMANT, AUDIT_DEGRADED)
        return {
            "allowed": allowed,
            "reason": str(verdict["status_name"]),
            "audit_id": int(verdict["audit_id"]),
            "pass_bps": int(verdict["pass_bps"]),
        }

    @gl.public.write
    def request_fresh_audit(self) -> None:
        IConform(self.conform).emit(on="accepted").audit(self.agent_id)
