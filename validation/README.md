# POP Minimal Validation

This directory contains a minimal, reproducible validation workflow for POP v0.1.

## Scope

The validation bundle covers three checks:

1. Schema conformance against `schema/persona.schema.json`
2. Cross-runtime projection fidelity for one canonical persona object
3. Comparison between separated persona objects and monolithic role configuration

## Layout

```text
validation/
├── README.md
├── requirements.txt
├── cases/
│   ├── invalid/
│   ├── monolithic/
│   ├── projection/
│   ├── separated/
│   └── valid/
├── results/
│   ├── comparison_results.json
│   ├── projection_results.json
│   ├── schema_results.json
│   └── tables.md
└── scripts/
    ├── compare_config_modes.py
    ├── project_runtime.py
    ├── render_tables.py
    └── validate_schema.py
```

## Reproduction

Run all commands from the repository root:

```bash
python3 -m pip install -r validation/requirements.txt
python3 validation/scripts/validate_schema.py
python3 validation/scripts/project_runtime.py
python3 validation/scripts/compare_config_modes.py
python3 validation/scripts/render_tables.py
```

## Notes

- Scripts resolve paths relative to the repository root and can be run directly.
- `validate_schema.py` copies repository examples into `validation/cases/valid/` and regenerates invalid cases on each run.
- `project_runtime.py` prefers `examples/mentor.persona.json` as the canonical object and falls back to the first available example if needed.
- `compare_config_modes.py` writes representative monolithic and separated configuration artifacts before computing comparison metrics.
- `render_tables.py` converts the JSON outputs into markdown tables suitable for direct insertion into a paper draft.
