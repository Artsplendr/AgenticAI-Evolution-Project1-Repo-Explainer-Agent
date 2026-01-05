Repo Explainer Agent
=====================

A minimal scaffold for an agent that explains a code repository: collects evidence, applies policies, uses tools, and produces human-friendly summaries.

Quick start
-----------
- Run the CLI locally:

```bash
python src/cli.py --help
```

Project layout
--------------
- `src/agent/`: core agent modules (orchestrator, policies, tools, evidence, models)
- `src/cli.py`: simple CLI entry to invoke the agent
- `tests/`: space for tests
- `docs/`: specifications, architecture, examples
- `sample_repo/`: optional tiny demo repo to test against
- `pyproject.toml`: project metadata

Notes
-----
- This is a scaffold. Implementations are intentionally light and ready for extension.
- You can rename or refactor modules as your design evolves.


