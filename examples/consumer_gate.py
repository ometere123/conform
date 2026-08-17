# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

AUDIT_CONFORMANT = 1
AUDIT_DEGRADED = 2


@gl.contract_interface
class IConform:
    class View:
        def latest_verdict(self, agent_id: u256) -> dict: ...
        def is_conformant_for(self, agent_id: u256, expected_definition_hash: str) -> bool: ...

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
    expected_definition_hash: str

    def __init__(self, conform: Address, agent_id: u256, expected_definition_hash: str, require_fresh_spec: bool = True):
        self.conform = conform if isinstance(conform, Address) else Address(conform)
        self.agent_id = agent_id
        self.expected_definition_hash = str(expected_definition_hash)
        self.require_fresh_spec = require_fresh_spec

    @gl.public.view
    def can_use_agent(self) -> dict:
        verdict = IConform(self.conform).view().latest_verdict(self.agent_id)
        if not bool(verdict["has_audit"]):
            return {"allowed": False, "reason": "NO_AUDIT"}
        if self.require_fresh_spec and not bool(verdict["is_current_spec"]):
            return {"allowed": False, "reason": "STALE_AUDIT"}
        if not bool(verdict["agent_active"]) or not bool(verdict["reliable"]):
            return {"allowed": False, "reason": "UNRELIABLE"}
        if not IConform(self.conform).view().is_conformant_for(
            self.agent_id, self.expected_definition_hash
        ):
            return {"allowed": False, "reason": "DEFINITION_MISMATCH"}

        status = int(verdict["status"])
        allowed = status == AUDIT_CONFORMANT
        return {
            "allowed": allowed,
            "reason": str(verdict["status_name"]),
            "audit_id": int(verdict["audit_id"]),
            "pass_bps": int(verdict["pass_bps"]),
        }

    @gl.public.write
    def request_fresh_audit(self) -> None:
        IConform(self.conform).emit(on="accepted").audit(self.agent_id)
