# POP Minimal Validation Tables

Table X. Schema conformance results for POP persona objects

| Case | Expected | Actual | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| caregiver.persona | valid | valid | pass | Repository example evaluated as a valid POP persona object. |
| companion.persona | valid | valid | pass | Repository example evaluated as a valid POP persona object. |
| mentor.persona | valid | valid | pass | Repository example evaluated as a valid POP persona object. |
| missing_required_field | invalid | invalid | pass | Removed required field `description`. First error: 'description' is a required property |
| wrong_field_type | invalid | invalid | pass | Changed `traits` from an array to a free-text string. First error: 'patient, structured, clear' is not of type 'array' |
| invalid_version | invalid | invalid | pass | Changed `schema_version` away from the allowed draft constant. First error: 'pop-0.1' was expected |
| unknown_field | invalid | invalid | pass | Added an undeclared operational policy block. First error: Additional properties are not allowed ('operator_policy' was unexpected) |
| free_text_profile | invalid | invalid | pass | Collapsed the persona into a vague free-text `profile` field. First error: Additional properties are not allowed ('profile' was unexpected) |

All 3 repository examples validated successfully, while all 5 intentionally malformed cases were rejected. This indicates that POP persona objects are machine-checkable at the schema boundary and that common structural deviations can be detected with a compact JSON Schema.

Summary: 8 of 8 cases matched the expected outcome.

Table Y. Cross-runtime projection fidelity for the same canonical persona object

| Projection | Identifier | Version | Role Label | Expressive Tendencies | Interaction Boundaries | Governance/Status Metadata | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| prompt_based | no | no | yes | weakened | weakened | lost | Flattened into a single prompt string with no stable slot for identity or governance metadata. |
| app_layer_role_model | yes | yes | yes | complete | complete | complete | Mapped into explicit app-layer slots that preserve identity, style, boundaries, and integration hints. |
| agent_runtime | yes | yes | yes | complete | complete | complete | Retained as a runtime contract with separate identity, behavior, boundary, and integration sections. |

For the canonical persona object `Structured Mentor`, prompt-based projection preserved the high-level role label but weakened expressive and boundary detail because structured fields were flattened into text. The app-layer role model and agent-runtime projections retained all tracked fields at the object level, showing that fidelity improves when downstream systems keep explicit persona slots instead of prompt-only injection.

Table Z. Comparison between separated persona objects and monolithic role configuration

| Mode | Update Steps | Unrelated Fields Affected | Portability | Boundary Clarity | Role Change Auditability | Accidental Drift Risk | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| monolithic | 10 | 6 | low | weak | low | higher | Role identity is duplicated across prompt, memory, tool, and UI fields, so changes spill into operational configuration. |
| separated | 4 | 0 | high | strong | high | lower | Role identity remains concentrated in the canonical POP object while runtime settings stay generic. |

Separated persona objects required fewer role-update edits and avoided spillover into memory, tool, and UI settings. The monolithic configuration showed lower portability and auditability because identity changes touched mixed operational fields, which increases the risk of accidental drift.
