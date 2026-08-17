# Consensus design

## What requires GenLayer consensus

The difficult fact is not whether an endpoint responded. It is whether the endpoint's observed response satisfied a behavioural expectation expressed in natural language.

For every enabled probe, Conform executes a custom `gl.vm.run_nondet_unsafe` leader/validator pair.

## Leader

The leader:

1. sends the stored HTTP request to the registered public endpoint;
2. records the HTTP status and a bounded response body;
3. asks an LLM to classify that response against the frozen behavioural specification and probe expectation;
4. canonicalises the result into stable fields.

## Validator

A validator does **not** validate JSON shape alone and does not trust the leader's reasoning.

It independently repeats the HTTP request and LLM classification. It then compares material fields:

- semantic probe verdict (`PASS`, `FAIL`, `INCONCLUSIVE`, `UNAVAILABLE`);
- HTTP response class.

Evidence prose and reason wording are intentionally not consensus-critical.

## Why not strict equality

Autonomous-agent responses can legitimately vary in wording, request ids, timestamps, generated text, or other details. Exact response bytes are therefore the wrong equivalence target.

The stable semantic question is narrower:

> Did the behaviour pass, fail, remain inconclusive, or become unavailable under this exact probe?

Two nodes may observe different prose and still agree on that outcome.

## Why compare HTTP class

Semantic agreement alone is insufficient if nodes observed fundamentally different endpoint conditions. A leader seeing HTTP 200 and a validator seeing HTTP 403 did not observe the same response class. Conform therefore requires the class to match as well as the semantic verdict.

This makes endpoint transitions more likely to fail consensus instead of being silently flattened into a misleading receipt.

## Availability is not failure

A 5xx response or transport failure becomes `UNAVAILABLE`, not `FAIL`. Conform does not claim that an agent violated a behavioural policy merely because its server could not answer.

A 4xx response remains semantically auditable because negative probes often expect refusal. A 403 can be evidence of correct behaviour when an unauthorised action should be rejected.

## Abstention

`INCONCLUSIVE` is a first-class outcome. If the observable response does not establish whether a hidden action occurred, the prompt requires abstention. Aggregate logic also refuses to produce a positive or negative status when a majority of probes are unavailable or inconclusive.

## Prompt-injection boundary

The agent response is wrapped as explicitly untrusted data. The evaluation prompt instructs the model to ignore instructions inside the payload and judge only the frozen expectation.

This is defence in depth, not a claim of perfect prompt-injection immunity. Independent validator re-execution and bounded decision fields are the stronger consensus controls.
