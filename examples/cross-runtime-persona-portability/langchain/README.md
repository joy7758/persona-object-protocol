# LangChain Projection of a POP Persona Object

This is not a native LangChain standard. It is an example of how a POP
persona object can be projected into a LangChain agent runtime.

The projection may use middleware, prompt transformation, or runtime
context shaping. The POP object remains canonical, while LangChain
bindings are treated as adapter-level constructs.

## Example Projection Fields

| POP persona field | LangChain runtime concept |
| --- | --- |
| `summary` | system framing |
| `communication_style` | prompt style guidance |
| `task_orientation` | response policy hints |
| `boundaries` | guardrail-oriented instructions |
| `preferred_outputs` | output format hints |

## Limitation

Projection does not guarantee identical runtime behavior. It only shows
how a canonical POP persona object may be expressed inside a LangChain
execution context.
