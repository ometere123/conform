# Conform architecture

Conform is a reusable behavioural conformance primitive for autonomous agents and HTTP-accessible services. It deliberately stops before product concerns such as dashboards, alerts, payments, slashing, marketplaces, or reputation scoring.

## Design goals

1. **Reusable**: one deployed Conform contract can be consumed by many Intelligent Contracts.
2. **Behavioural, not availability-only**: a successful HTTP response does not prove that an agent respected its policy.
3. **Consensus-backed**: validators independently call the live endpoint and independently classify the observable behaviour.
4. **Fail closed**: unavailable or ambiguous observations never become passing observations.
5. **Version/hash/time-aware**: every receipt is pinned to the exact definition version, canonical fingerprint, and audit timestamp it tested.
6. **Deterministic settlement surface**: the model produces probe-level observations only; deterministic code computes the final status.

## State model

### AgentProfile

An agent registration stores owner address, name, public endpoint, behavioural specification, monotonically increasing `spec_version`, thresholds, bounded probe suite, audit cooldown, latest audit reference/time/status, definition fingerprint, and consecutive breach count. Pause/resume and policy changes are versioned configuration changes.

Only the owner can mutate the profile. GET-only auditing is permissionless after cooldown; enabled POST probes make auditing owner-only because POST may have side effects.

### Probe

A probe is a concrete executable question against the behavioural specification:

- GET or POST;
- relative path under the registered origin;
- optional JSON body;
- natural-language expected behaviour;
- severity (`INFO`, `NORMAL`, `CRITICAL`);
- enabled/disabled flag.

The HTTP request shape is deterministic. Only interpretation of the live response is non-deterministic.

### AuditReceipt

An audit is append-only. It records the agent id, tested specification version, aggregate verdict, pass basis points, pass/fail/inconclusive/unavailable counts, critical-failure count, summary, and one `ProbeResult` for every enabled probe.

Old receipts remain historical evidence after an owner updates the profile. `latest_verdict()` exposes version, hash, timestamp, active, and reliable fields; `is_conformant_for()` lets a consumer pin an exact expected definition.

## Flow

```text
register_agent
     |
     +--> add_probe x N
              |
              v
          audit(agent_id)
              |
              +--> deterministic cooldown + permission gate
              +--> snapshot current definition hash/time
              |
              +--> probe 1: HTTP -> classify -> validator re-probe
              +--> probe 2: HTTP -> classify -> validator re-probe
              +--> ...
              |
              v
        deterministic aggregation
              |
              v
        version/hash/time-pinned AuditReceipt
              |
              v
       consumer reads latest_verdict()
```

The contract boundary is deliberately split:

```text
DETERMINISTIC: admission, ownership, cooldown, permissions, hashing,
               freshness, aggregation, receipt persistence
NONDETERMINISTIC: live HTTP observation and semantic judgement only
```

## Deterministic aggregation

Each consensus probe produces one bounded observation: `PASS`, `FAIL`, `INCONCLUSIVE`, or `UNAVAILABLE`.

Ordinary deterministic code then applies:

1. all unavailable -> `UNAVAILABLE`;
2. any critical failure -> `BREACHED`;
3. no evaluated probes -> `INCONCLUSIVE`;
4. majority inconclusive/unavailable -> `INCONCLUSIVE`;
5. pass ratio >= conformant threshold -> `CONFORMANT`;
6. pass ratio >= degraded threshold -> `DEGRADED`;
7. otherwise -> `BREACHED`.

The LLM is never asked what aggregate contract status should be.

## Composition boundary

A marketplace can hide agents with stale or breached audits. A DAO can require a current conformant receipt before delegating treasury authority. An escrow can refuse to use an agent whose current specification has not passed.

None of those consumers needs to reimplement live HTTP probing, prompts, validator equivalence, versioning, or aggregation. That is the purpose of the primitive boundary.
