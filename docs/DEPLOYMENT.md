# Deployment evidence

## Canonical Studionet evidence

The final source was deployed and exercised on Studionet with real consensus. The generated signer was `0x4AF2A182Ca45865a5c6885142B1d4C80541224C5`, and the contract address is `0xd56726Db2eb3E707Dfd9A27A1F1b5D90301DC658`.

Deployment transaction: `0xaddbef505c1419f9de03e940d0983bdac60bfd8198f4b83c546a995dddfdc466`.

The transaction summaries reported status `5`, consensus data containing leader receipt, validators, and votes, and leader execution `SUCCESS`. The live run completed with `1 passed` in 235.61 seconds. The deployable source was unchanged after this evidence run except for test/documentation cleanup; source parity is checked before merge.

The intended network is Studionet, chain ID `61999`, through the current official GenLayer tooling. The deployment account must be an unlocked/funded account or an officially supported generated test account; private keys must never enter the repository.

## Historical diagnostic evidence

An earlier diagnostic deployment reached `ACCEPTED / MAJORITY_AGREE` at `0x8F15395e4332ceCd076001F4bdb2ABC0455e9491` with deployment transaction `0x498820732b73e2f99b6b58817de92a5b24e34d6802a037a09a44bf92d04c43d6`. That run used a temporary `response.status` compatibility change and is not proof for the final source. It is retained here only to explain the runtime discrepancy and why a fresh final-source deployment is required.

## Lifecycle evidence

| Operation | Transaction | Execution | Consensus | Result |
|---|---|---|---|---|
| Deploy final source | `0xaddbef505c1419f9de03e940d0983bdac60bfd8198f4b83c546a995dddfdc466` | `SUCCESS` | validators/votes exposed; status `5` | deployed |
| Register GET-only profile | `0x3cf5f3baf71e79352026e8febab56917aaf1f3e1392442cfc8a717fdc06538a8` | `SUCCESS` | validators/votes exposed; status `5` | accepted |
| Add passive GET probe | `0x359cbdfeec68710c8b40106d5f926407d7dae8612087d6d4171ea9de6a3d8cc6` | `SUCCESS` | validators/votes exposed; status `5` | accepted |
| Permissionless GET audit | `0xe94f3195f3a02059bc280c6b5f44ec95a1936852ab216f5dfb49b1e195ddd5d9` | `SUCCESS` | validators/votes exposed; status `5` | `CONFORMANT` |
| Update specification | `0x083ff805719dca265c3366ed80ab0588889e6d29e1b68bcfdd5ec022689427d5` | `SUCCESS` | validators/votes exposed; status `5` | old receipt stale |
| Add harmless POST probe | `0x50979062e0d28215d298201424195329ecec49022243998aa45089d53362288` | `SUCCESS` | validators/votes exposed; status `5` | accepted |
| Owner POST audit | `0xb468dfb7978f5d390f259a24e97453a82d6710d81ee83c2d5a60229beb219f5d` | `SUCCESS` | validators/votes exposed; status `5` | accepted |

The passive probe used `https://test-server.genlayer.com/static/genvm/hello.html`. Its receipt was `CONFORMANT`, with `audited_at = 1786986132`, audited definition hash `8ad35103f97da6d0cf52629819ff701157e679721eaa6962b2081880873a46f8`, and `latest_verdict` reporting `definition_matches = true`, `is_current_spec = true`, and `reliable = true`. After changing the specification, the current hash became `489287f929a73174a62df45cc2cdf9c4a40059b55e57befd4c79da8d4d97aff5`; the old receipt became stale and the exact-definition gate returned false.

Studionet is rate-limited. Final evidence should use slow receipt polling and capture execution output separately from consensus status.
