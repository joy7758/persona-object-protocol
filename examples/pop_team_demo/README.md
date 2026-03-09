# POP Team Demo

A tiny POP team demo showing 3 portable persona objects projected into 3 CrewAI-style runtime roles.

## What this demo shows

- `persona_ref -> persona object`
- `persona object -> CrewAI-style agent config`
- `3 roles -> 1 shared task brief`

## Dry Run (default)

```bash
python examples/pop_team_demo/demo.py
```

- no model required
- no CrewAI install required
- prints structured role projection output

## Live Run (optional)

```bash
pip install crewai
python examples/pop_team_demo/demo_live.py
```

- requires CrewAI
- may require model/provider configuration
- exits gracefully if dependencies are missing

## Demo roles

- Designer
- Engineer
- Marketing Manager

## Shared task brief

`Plan the first POP landing page and launch outline`
