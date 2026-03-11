# POP vs Interaction Layer vs Governance Layer

| Layer | Primary question | Canonical object or decision surface | What it should not absorb |
| --- | --- | --- | --- |
| POP | Who is acting? | portable persona object | task intent, action exchange, result exchange |
| Interaction Layer | What is being requested or attempted? | intent, action, and result objects | identity issuance, policy enforcement, audit receipts |
| Governance Layer | What is allowed before execution? | policy, budget, fallback, and risk decision | persona definition, semantic identity, post-execution evidence packaging |

## Notes

- POP keeps identity portable across runtimes.
- The Interaction Layer keeps task semantics explicit without collapsing them into persona objects.
- The Governance Layer evaluates intent and action objects before execution.

Interaction-layer draft: [Agent Intent Protocol](https://github.com/joy7758/agent-intent-protocol)
