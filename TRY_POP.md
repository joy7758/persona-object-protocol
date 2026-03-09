# Try POP in 3 Minutes

POP is a lightweight protocol for treating persona as a portable object layer instead of prompt fragments.
Runtime configurations are derived projections, not the protocol core.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[crewai]'
```

## Run the dry-run demo

```bash
python examples/pop_team_demo/demo.py
```

## Expected output

You should see structured JSON showing:

- three persona refs
- three source paths
- three CrewAI-style runtime role projections
- one shared task brief

## Feedback

If you want to report friction or suggest changes, open a GitHub Issue in this repository.
