# Conform - Intelligent Contracts submission notes

## What is being submitted

A standalone, reusable GenLayer Intelligent Contract primitive for consensus-backed behavioural conformance audits of autonomous agents.

Conform is not a complete app and intentionally has no frontend.

## Purpose

Existing service checks can answer whether an endpoint is reachable. Conform answers a harder question: whether the endpoint's **observed behaviour** conforms to the natural-language restrictions and capabilities it committed to.

A registered profile contains a versioned specification and a bounded set of executable HTTP probes. Anyone can trigger an audit. The resulting receipt can be consumed by other Intelligent Contracts.

## Why GenLayer consensus is necessary

A deterministic smart contract can compare status codes or exact bytes, but cannot robustly decide questions such as:

> The request omitted explicit approval. Did the agent refuse the transfer, or did it behave as if the transfer was authorised?

Conform uses a custom leader/validator pattern for that semantic step.

The leader calls the live endpoint and classifies the observed response. A validator independently repeats the endpoint call and classification. The validator requires agreement on the bounded semantic verdict and HTTP class. It does not merely validate the leader's JSON shape.

## What remains deterministic

- input limits and endpoint safety checks;
- ownership and profile mutation;
- version increments;
- probe request construction;
- threshold arithmetic;
- critical-probe override;
- majority-inconclusive rule;
- breach streak updates;
- stale-receipt detection;
- audit receipt storage.

The model never chooses the aggregate contract status.

## State design

- `AgentProfile`: owner, endpoint, specification, version, thresholds, probes, latest result.
- `Probe`: bounded request + expectation + severity.
- `AuditReceipt`: append-only version-pinned aggregate and per-probe results.
- `ProbeResult`: bounded semantic verdict and evidence metadata.

## Equivalence design

Conform does not use exact equality over agent response text because generated output can legitimately vary. It compares stable decision fields that consumers care about:

1. semantic probe verdict;
2. HTTP response class.

Evidence prose is informational and not consensus-critical.

## Fail-closed behaviour

Conform distinguishes behavioural failure (`FAIL`), insufficient semantic evidence (`INCONCLUSIVE`), and inability to observe the service (`UNAVAILABLE`).

A service outage is not silently converted into a behavioural breach. Conversely, inconclusive/unavailable probes cannot inflate the passing ratio, and a majority of non-observations prevents a positive or negative aggregate claim.

## Reuse boundary

A consumer only needs `latest_verdict(agent_id)` or `get_audit(audit_id)`. It does not need to copy web access, prompts, validator logic, versioning, or aggregation rules.

`examples/consumer_gate.py` demonstrates this composition boundary.

## Tests included

The Direct Mode suite covers registration, owner-only mutation, private endpoint rejection, cross-origin probe rejection, invalid request-body rejection, specification versioning, no-probe and paused-agent guards, conformant results, critical behavioural breach, 5xx availability handling, explicit inconclusive outcomes, stale receipt detection, and independent validator disagreement.

The validator-disagreement test is the key consensus test: the leader sees a compliant refusal, the validator independently sees an unauthorised execution, and validation returns false.

The permanent deterministic check extracts and executes the actual pure helpers from `contracts/conform.py`; it currently passes 144 exhaustive two-probe combinations plus edge cases, including private/IPv6 and credential-bearing endpoint rejection. Contract compilation passes. The bundled Windows environment has `genlayer-test 0.29.2` and `genlayer-py 0.16.3`, but Direct Mode currently fails before contract import because the runner attempts to unlink its redirected stdin file immediately after `dup2`, producing `PermissionError [WinError 32]`. This is documented as an upstream/platform runner issue, not counted as Conform execution.

No final-source Studionet address, transaction hash, or accepted live `audit()` receipt is claimed in this checkout. Historical network evidence is deliberately not presented as proof for a different source commit.

## Repository entry points

- `contracts/conform.py` - primitive
- `tests/test_conform.py` - Direct Mode suite
- `examples/consumer_gate.py` - minimal reusable consumer
- `docs/CONSENSUS.md` - validator/equivalence rationale
- `docs/ARCHITECTURE.md` - state and flow
- `docs/SECURITY.md` - threat/failure model
