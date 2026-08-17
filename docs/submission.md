# Conform submission brief

## Reusable primitive

Conform is a standalone GenLayer Intelligent Contract for versioned, consensus-backed behavioural audits of agent or service endpoints. An owner registers an endpoint, specification, and bounded probe suite; any caller can request an audit and other contracts can consume the resulting version-pinned verdict.

## Why consensus is necessary

The observations are live web requests and, for semantic probes, natural-language interpretation. A deterministic contract cannot answer whether a response satisfies an arbitrary behavioural requirement. Conform uses GenLayer's leader/validator execution: the leader runs every enabled probe, while validators independently rerun the same probes and recompute the decisions.

The validator comparison is substantive. It requires each probe's semantic verdict and HTTP response class to agree; leader-provided evidence prose is bounded but not consensus-critical. Only after the equivalence check and consensus does the contract persist an `AuditReceipt`.

## Deterministic state and semantics

The contract stores `AgentProfile`, `Probe`, and append-only `AuditReceipt` records. Ownership controls profile and probe changes; GET-only auditing is permissionless after cooldown, while enabled POST probes make auditing owner-only because POST may have side effects. Specification, endpoint, and probe changes increment `spec_version`, so consumers can reject stale receipts. Aggregation is deterministic: critical failures force `BREACHED`, unavailable observations remain distinct from behavioural failures, and insufficient observations produce `INCONCLUSIVE`.

## Reuse

GET-only profiles are permissionless after cooldown; enabled POST profiles are owner-only because POST can have side effects. Consumers can pin an exact policy with `is_conformant_for(agent_id, expected_definition_hash)` and apply their own age limit to `audited_at`.

Consumers can call `latest_verdict(agent_id)` and require `has_audit`, `is_current_spec`, and `status_name == "CONFORMANT"` before allowing a workflow, release, marketplace listing, governance action, or other operation. The consumer does not need to reproduce HTTP access, prompts, validator comparison, or threshold arithmetic.

## Evidence

The fast checks are intentionally independent of external GenVM assets: `python scripts/test_deterministic.py` exercises the actual pure helpers extracted from the production contract, including endpoint safety, credential rejection, parsing, canonicalisation, aggregation, and exhaustive two-probe combinations. The current result is 144 exhaustive two-probe combinations plus edge cases; compilation also passes. Direct Mode tests are provided in `tests/test_conform.py`. In the Windows environment used for this checkout, the installed runner currently fails before contract execution while unlinking its stdin temporary file (`PermissionError [WinError 32]`), so that result is classified as an upstream/platform runner defect rather than Conform execution. No final-source Studionet deployment or audit receipt is claimed without verifiable network evidence.

## Security boundary

Only public HTTPS DNS origins are accepted. Credentials, explicit ports, localhost, loopback/private/link-local IPv4, raw/numeric IPs, `.local`/`.internal` names, and IPv6/colon hosts are rejected; paths are relative to the registered origin. These are conservative application-level checks, not a complete DNS firewall. Response bodies are untrusted prompt data, bounded before model interpretation, and never treated as instructions.

## Limitations

Conform evaluates observable HTTP behaviour at audit time. It does not prove hidden state, continuous compliance, or future behaviour. Endpoint checks are application-level SSRF hardening and deliberately fail closed for IPv6; runtime egress policy remains important. External endpoints and model responses can be unavailable or change between audits.
