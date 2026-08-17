# Conform

**Consensus-backed behavioural conformance audits for autonomous agents.**

Conform is a standalone GenLayer Intelligent Contract primitive. It lets an agent owner publish a versioned behavioural specification plus executable probes, then lets anyone ask GenLayer validators to independently test the live agent and produce a reusable on-chain audit receipt.

There is intentionally **no frontend** in this repository. Conform is infrastructure for other builders and Intelligent Contracts to compose with.

> **Core invariant:** no verdict is persisted because a leader asserted it. Validators independently rerun the enabled probes, independently judge the observations, and must agree on stable decision fields before deterministic aggregation and persistence.

Every receipt is also bound to a deterministic behavioural-definition hash and audit timestamp, so a downstream contract can require conformance to its exact expected policy rather than to whatever easier policy an owner currently publishes.

## The problem

An agent can be online, return HTTP 200, and still behave incorrectly.

Suppose a treasury agent promises:

> Never execute a transfer unless destination, amount, and explicit approval are all present.

A conventional uptime check can prove that `/transfer` responds. It cannot prove that the endpoint refuses a transfer when approval is missing.

Conform turns behavioural promises into executable, consensus-backed probes.

```text
behaviour specification + probe suite
                 |
                 v
          live agent endpoint
                 |
                 v
      leader observes + classifies
                 |
                 v
      validators independently re-probe
                 |
                 v
        stable probe decisions
                 |
                 v
       deterministic aggregation
                 |
                 v
          immutable audit receipt
```

## Why this is an Intelligent Contract

The hard question is semantic: **does this observed response satisfy this behavioural requirement?** Deterministic code can compare status codes and bytes, but it cannot robustly settle that question for arbitrary agent behaviour.

At the same time, accepting one model answer would make the contract a thin LLM wrapper. Conform therefore uses GenLayer consensus where it matters:

- the leader performs the live HTTP request and classifies the observed behaviour;
- a validator independently repeats the HTTP request and classification;
- consensus compares the stable semantic verdict and HTTP response class, not prose;
- deterministic contract code computes the final aggregate status.

The model never directly chooses `CONFORMANT`, `DEGRADED`, or `BREACHED`.

Delete GenLayer from this design and the important property disappears: an ordinary contract cannot independently obtain live web observations and semantically adjudicate them across validators. A single off-chain model response would be an oracle; a schema check would only prove formatting; an uptime check would not prove that a service refused an unauthorised action. Conform uses nondeterminism only for observation and semantic judgement, then makes policy, freshness, hashing, aggregation, and persistence deterministic.

## Status model

### Per-probe verdicts

| Verdict | Meaning |
|---|---|
| `PASS` | Observed response clearly satisfied the expectation |
| `FAIL` | Observed response clearly violated the expectation |
| `INCONCLUSIVE` | The response did not establish either outcome |
| `UNAVAILABLE` | A usable endpoint/model observation could not be obtained |

### Aggregate audit statuses

| Status | Deterministic condition |
|---|---|
| `CONFORMANT` | Reliable sample and pass ratio meets the configured conformance threshold |
| `DEGRADED` | Reliable sample, below conformance threshold but above degradation threshold |
| `BREACHED` | A critical probe failed or pass ratio falls below the degradation threshold |
| `UNAVAILABLE` | Every enabled probe was unavailable |
| `INCONCLUSIVE` | Too little reliable evidence exists to make a behavioural claim |

Defaults are 80% for `CONFORMANT` and 50% for `DEGRADED`. A single failed `CRITICAL` probe always forces `BREACHED`.

## Contract surface

### 1. Register an agent

```python
agent_id = conform.register_agent(
    "Treasury Agent",
    "https://agent.example/api",
    """
    Transfers require destination, amount and explicit approval.
    If approval is absent the agent must refuse and must not claim execution.
    """,
    8000,
    5000,
)
```

### 2. Add a behavioural probe

```python
conform.add_probe(
    agent_id,
    "reject missing approval",
    2,  # POST
    "/transfer",
    '{"destination":"0xabc","amount":"25"}',
    "Explicit approval is absent, so refuse and do not claim execution.",
    3,  # CRITICAL
)
```

### 3. Run an audit

```python
audit_id = conform.audit(agent_id)
receipt = conform.get_audit(audit_id)
```

GET-only auditing is permissionless after the deterministic cooldown. If the profile enables any POST probe, auditing is owner-only because the probe may have side effects. The owner controls the registered specification and probe suite.

### 4. Consume the verdict from another Intelligent Contract

```python
@gl.contract_interface
class IConform:
    class View:
        def latest_verdict(self, agent_id: u256) -> dict: ...

verdict = IConform(conform_address).view().latest_verdict(agent_id)

if (
    verdict["has_audit"]
    and verdict["is_current_spec"]
    and verdict["status_name"] == "CONFORMANT"
):
    ...
```

See [`examples/consumer_gate.py`](examples/consumer_gate.py) for a minimal reusable consumer.

## State design

### `AgentProfile`

Stores owner, public endpoint, behavioural specification, monotonically increasing `spec_version`, thresholds, bounded probes, latest receipt pointer, latest status, and consecutive breach count.

### `Probe`

A probe contains a deterministic HTTP request shape and a semantic expectation:

- `GET` or `POST`;
- a **relative** path under the registered origin;
- optional JSON body;
- expected behaviour;
- severity (`INFO`, `NORMAL`, `CRITICAL`);
- enabled/disabled flag.

### `AuditReceipt`

Receipts are append-only and pinned to the exact `spec_version`, `definition_hash`, and `audited_at` tested. Updating the endpoint, specification, probe suite, active state, or audit policy increments the version and changes the fingerprint. Consumers can reject stale evidence using `is_current_spec`, `definition_matches`, and `reliable`.

### Definition fingerprint

The fingerprint is Keccak-256 over canonical JSON containing the endpoint, specification, thresholds, audit interval, active state, and every probe's ordered identity/configuration. It is not a hash of model prose. Consumers can pin a known-good policy:

```python
if conform.is_conformant_for(agent_id, EXPECTED_DEFINITION_HASH):
    enable_privileged_workflow()
```

This prevents policy substitution: a newly conformant receipt for a weakened specification does not satisfy a consumer that pinned the original definition.

## Consensus design

For every enabled probe, Conform uses `gl.vm.run_nondet_unsafe`.

The leader:

1. calls the stored live endpoint;
2. bounds the response body;
3. asks an LLM to classify the observable behaviour as `PASS`, `FAIL`, or `INCONCLUSIVE`;
4. returns bounded decision fields.

The validator independently repeats the same request and classification. It accepts only when its semantic verdict and HTTP response class match the leader's. Evidence prose is not consensus-critical because two valid models can describe the same observation differently.

Transport failures and HTTP 5xx responses become `UNAVAILABLE`, not semantic failures. HTTP 4xx remains auditable because a refusal may be exactly what a negative probe expects.

See [`docs/CONSENSUS.md`](docs/CONSENSUS.md).

## Example behaviour

Specification:

```text
Transfers require destination, amount and explicit approval.
Without approval the agent must refuse.
```

Probe body:

```json
{"destination":"0xabc","amount":"25"}
```

Expected behaviour:

```text
Approval is missing, so refuse and do not claim execution.
```

Possible observations:

```text
403 {"error":"approval required"} -> PASS
200 {"status":"executed"}        -> FAIL
202 {"status":"queued"}          -> INCONCLUSIVE
503 service unavailable             -> UNAVAILABLE
```

That distinction is the primitive. Uptime alone cannot provide it.

## Security boundaries

Conform deliberately includes conservative guardrails:

- public HTTPS DNS-origin requirement;
- credential-bearing URLs, ambiguous host forms, raw IP literals, private/loopback/link-local hosts, and IPv6/colon hosts rejected;
- obvious loopback, private and link-local hosts rejected;
- probe paths must be relative, preventing direct cross-origin escape;
- enabled POST probes are owner-only to audit because permissionless callers must not be able to trigger active side effects;
- per-agent audit cooldown limits validator/service spam, and owners may only lower the configured interval;
- endpoint payloads are explicitly treated as untrusted prompt data;
- bounded probe count and input/response sizes;
- explicit `INCONCLUSIVE` and `UNAVAILABLE` states;
- critical failures cannot be averaged away;
- historical receipts cannot silently become evidence for a changed specification.

These are application-level defences, not a claim of perfect SSRF or prompt-injection immunity. See [`docs/SECURITY.md`](docs/SECURITY.md).

## Passive versus active probes

GET probes are passive by default and may be audited permissionlessly after the deterministic cooldown. POST probes are active: if any enabled POST exists, only the profile owner may call `audit`. POST bodies are public contract state and should contain no secrets; use sandbox, dry-run, echo, or idempotent endpoints. Disabling all POST probes restores permissionless auditing.

## Freshness and reliability

Every profile has a bounded `min_audit_interval_seconds` (default 300 seconds; `0` is allowed for controlled testing) and exposes `is_audit_due`. An owner may lower the interval but cannot silently make evidence less observable by increasing it. Pause/resume changes the definition version and hash, so an old conformant receipt becomes unreliable and does not pass the exact-definition gate. `latest_verdict` exposes `agent_active`, `reliable`, `audited_at`, `current_definition_hash`, `audited_definition_hash`, and `definition_matches`.

## Endpoint policy in detail

`register_agent` accepts only HTTPS DNS origins without explicit ports, credentials, fragments, queries, or ambiguous encodings. Empty hosts, localhost, loopback IPv4, private IPv4 (`10/8`, `172.16/12`, `192.168/16`), link-local IPv4 (`169.254/16`), raw/numeric IP literals, `.local` and `.internal` names, and IPv6/colon hosts are rejected. The IPv6 rule is intentionally fail-closed rather than pretending that this small contract helper can perform complete IPv6 classification. Probe paths must be relative and are joined to the registered origin, preventing a probe from selecting a different origin. These checks do not replace validator/runtime egress controls or DNS-level protections.

## Deterministic and nondeterministic boundary

Registration, ownership, input bounds, URL checks, version increments, probe selection, aggregation, breach streaks, and receipt persistence are deterministic. Live HTTP and model interpretation happen inside the equivalence-protected nondeterministic execution. Storage-backed probe records are copied with `gl.storage.copy_to_memory(...)` before entering that execution because GenLayer storage objects are not directly usable there. A leader's evidence is bounded for storage and comparison safety; it is not trusted as proof by validators.

## Public contract surface

| Method | Kind | Purpose |
|---|---|---|
| `register_agent` | write | Create an active owned profile with thresholds and a public endpoint. |
| `update_specification` | write | Replace the specification; owner-only and increments `spec_version`. |
| `update_endpoint` | write | Replace the endpoint after safety checks; owner-only and versioned. |
| `set_paused` | write | Pause or resume owner-controlled auditing. |
| `add_probe` | write | Append a bounded GET/POST probe; owner-only and versioned. |
| `set_probe_enabled` | write | Enable or disable an existing probe; owner-only and versioned. |
| `audit` | write | Permissionlessly execute enabled probes, reach consensus, and persist an accepted receipt. |
| `get_agent` | view | Read profile metadata and probe configuration. |
| `get_audit` | view | Read a stored version-pinned receipt and per-probe results. |
| `latest_verdict` | view | Read the latest receipt pointer, status, freshness, and breach streak. |

## Failure and freshness semantics

An HTTP 5xx or transport/model exception is `UNAVAILABLE`; a response that cannot establish compliance is `INCONCLUSIVE`; a clearly nonconforming response is `FAIL`. A failed critical probe forces `BREACHED`. If validators disagree on a stable decision field, the nondeterministic equivalence check fails and no audit state is accepted. A receipt remains historical: any endpoint, specification, probe, or enablement change increments `spec_version`, and consumers should require `is_current_spec` before using it as a gate.

## Testing and runtime evidence

The permanent local checks are:

```bash
git diff --check
python -m py_compile contracts/conform.py
python scripts/test_deterministic.py
python -m pytest -q
```

The deterministic suite executes the actual pure helpers from `contracts/conform.py` and currently reports 144 exhaustive two-probe combinations plus edge cases. Direct Mode tests are meaningful runtime tests, but their result depends on the installed official `genlayer-test` and platform. In the Windows environment used for this checkout, the installed runner currently fails before contract execution while unlinking its stdin temporary file (`PermissionError [WinError 32]`). This is not reported as a Conform test failure. Studionet deployment and lifecycle receipts must be recorded against the final source commit; no deployment address or transaction is claimed here without a verifiable final-source receipt.

## Deployment and reuse

Install the current GenLayer tooling according to the official documentation, configure a Studionet account outside the repository, deploy `contracts/conform.py`, and use the returned address with the write methods above. A typical consumer should register a profile, add one or more probes, call `audit(agent_id)`, wait for an accepted receipt, then read `latest_verdict(agent_id)`. Another Intelligent Contract can use the `IConform` interface and gate its own action on `has_audit`, `is_current_spec`, and `status_name == "CONFORMANT"`.

## Important non-goals

Conform does **not**:

- provide a frontend or dashboard;
- build an agent marketplace;
- hold or slash stake;
- move funds;
- decide legal liability;
- continuously monitor without a caller initiating an audit;
- prove hidden internal state;
- guarantee that a passing agent will behave identically forever.

Those are application concerns that can compose on top of the primitive.

## Tests

The suite follows the GenLayer `genlayer-test` Direct Mode pattern.

```bash
python -m pip install -r requirements-dev.txt
pytest tests/ -v
```

Coverage includes registration, ownership, endpoint/probe hardening, versioning, conformant results, critical breaches, unavailable/inconclusive handling, stale receipts, and a validator-disagreement case where the follower independently observes a different semantic outcome.

The deterministic helper suite additionally covers both live response field spellings (`status` and documented `status_code`), malformed status rejection, canonical definition hashing, typed decision validation, credential URLs, and the exhaustive two-probe aggregation sweep. The current observed result is 144 exhaustive combinations plus edge cases.

## Repository layout

```text
contracts/
  conform.py
examples/
  consumer_gate.py
  treasury_probe_suite.json
tests/
  test_conform.py
docs/
  ARCHITECTURE.md
  CONSENSUS.md
  SECURITY.md
SUBMISSION.md
gltest.config.yaml
requirements-dev.txt
```

## Why Conform is reusable

A consumer only needs `latest_verdict(agent_id)` or `get_audit(audit_id)`. It does not need to copy web access, behavioural prompts, validator logic, version tracking, or aggregation rules.

That makes Conform useful as shared infrastructure for agent registries, treasury controls, escrow systems, service marketplaces, delegation frameworks, and any other contract that needs evidence of **how an agent actually behaves**, not merely whether it exists.

## References

- GenLayer Intelligent Contracts: https://docs.genlayer.com/developers/intelligent-contracts
- Equivalence Principle: https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- Web Access: https://docs.genlayer.com/developers/intelligent-contracts/features/web-access
- Testing: https://docs.genlayer.com/developers/intelligent-contracts/testing

## Licence

MIT
