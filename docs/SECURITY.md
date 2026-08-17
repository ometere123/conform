# Security and failure model

Conform is an observation primitive, not an enforcement system. A consumer decides what to do with an audit receipt.

## Threats considered

### Leader fabrication

A malicious or faulty leader cannot simply invent `PASS`. Validators independently re-run the endpoint request and classification and reject a materially different verdict.

### Shape-only validation

Conform does not accept a result merely because it contains valid JSON or an allowed enum. The validator produces independent evidence.

### Prompt injection in endpoint responses

The response body is explicitly treated as untrusted evidence. Instructions inside it are not contract instructions.

### Validator-side SSRF

Registrations require HTTPS DNS origins and reject credentials, fragments, backslashes, raw/numeric IP literals, malformed DNS labels, loopback, link-local, private IPv4, localhost variants, `.local`, `.internal`, and IPv6/colon hosts. Probe paths must be non-empty, relative, free of control characters/backslashes, and cannot use protocol-relative or absolute URLs.

This is a conservative application-level barrier, not a substitute for validator/runtime egress controls. DNS rebinding, redirects, and resolver behavior remain infrastructure-level concerns.

### Active POST probes

Enabled POST probes are owner-only to audit. This prevents a permissionless stranger from repeatedly causing an endpoint side effect. POST configuration is public and should never contain secrets; sandbox, dry-run, echo, or idempotent endpoints are the intended use.

### Cadence and suppression

Each profile has a deterministic audit cooldown. The first audit is immediate; subsequent audits are rejected until due. Owners may lower, but not increase, the interval. This bounds external-service and validator pressure without allowing an owner to silently suppress observation.

### Policy substitution and temporal freshness

Every accepted receipt stores the canonical definition hash and transaction timestamp. Configuration changes increment the version and change the hash; pause/resume also invalidates reliability. Consumers can require `is_conformant_for(agent_id, expected_hash)` and impose their own maximum age policy.

### Unbounded resource consumption

The contract caps probe count, specification length, endpoint/path length, request body length, response bytes presented to the model, expectation length, and evidence length.

### Endpoint flapping

A leader and validator can legitimately hit different service states. Conform compares semantic verdict and HTTP response class. Material disagreement prevents a clean consensus result rather than pretending the observation was stable.

### Stale audits

Every receipt stores the tested `spec_version`. Endpoint, specification, probe-suite, or enablement changes increment the version. Consumers can require `is_current_spec == true`.

### Owner gaming the suite

An owner can publish weak probes. Conform proves conformance to the **registered specification and probe suite**, not universal safety. High-stakes consumers should inspect, standardise, or independently require acceptable probe suites.

### External side effects

A probe may trigger a real external side effect if the endpoint performs one. Probe authors should prefer dry-run, simulation, sandbox, or deliberately idempotent endpoints. Conform cannot undo an HTTP side effect.

## Non-goals

Conform does not:

- hold or slash stake;
- decide legal liability;
- prove hidden internal state;
- guarantee future behaviour;
- authenticate endpoint ownership beyond the registered URL;
- continuously monitor without a caller initiating an audit.

## Consumer guidance

For high-stakes use, consumers should normally require a current specification version, `CONFORMANT` rather than `DEGRADED`, zero critical failures, application-layer freshness appropriate to the use case, and a probe suite whose expectations the consumer recognises.
