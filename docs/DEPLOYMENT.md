# Deployment evidence

## Canonical status

There is no canonical final-source Studionet deployment recorded in this repository yet. A final deployment must use the exact committed `contracts/conform.py` source after the compatibility, security, cooldown, freshness, and definition-hash changes in this branch. The repository does not invent an address, transaction hash, receipt, validator vote, or audit result.

The intended network is Studionet, chain ID `61999`, through the current official GenLayer tooling. The deployment account must be an unlocked/funded account or an officially supported generated test account; private keys must never enter the repository.

## Historical diagnostic evidence

An earlier diagnostic deployment reached `ACCEPTED / MAJORITY_AGREE` at `0x8F15395e4332ceCd076001F4bdb2ABC0455e9491` with deployment transaction `0x498820732b73e2f99b6b58817de92a5b24e34d6802a037a09a44bf92d04c43d6`. That run used a temporary `response.status` compatibility change and is not proof for the final source. It is retained here only to explain the runtime discrepancy and why a fresh final-source deployment is required.

## Required final evidence table

| Operation | Transaction | Execution | Consensus | Result |
|---|---|---|---|---|
| Deploy final source | pending | pending | pending | pending |
| Register GET-only profile | pending | pending | pending | pending |
| Add passive GET probe | pending | pending | pending | pending |
| Permissionless GET audit | pending | pending | pending | pending |
| Read `get_audit` / `latest_verdict` | — | — | — | pending |
| Exact-definition gate | — | — | — | pending |
| Active POST stranger attempt | pending | pending | pending | expected deterministic refusal |

Studionet is rate-limited. Final evidence should use slow receipt polling and capture execution output separately from consensus status.
