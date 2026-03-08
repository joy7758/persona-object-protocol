# CrewAI Projection of a POP Persona Object

This example shows how a canonical POP persona object can be projected
into CrewAI-style agent definitions. The mapping is an adapter
projection, not a replacement for CrewAI abstractions.

Role, goal, and backstory are treated as runtime-facing expressions
derived from the POP core, not as the POP core itself.

## Example Projection Fields

| POP persona field | CrewAI runtime concept |
| --- | --- |
| `summary` | role framing |
| `task_orientation` | goal framing |
| `traits` and `communication_style` | backstory hints |
| `boundaries` | behavioral constraints |
| `preferred_outputs` | task and result style expectations |

## Portability Note

The same POP object should remain reusable across multiple runtimes even
when the runtime-facing projection is expressed differently.
