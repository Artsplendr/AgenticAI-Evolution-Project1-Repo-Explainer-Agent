### Architecture

- Orchestrator (`src/agent/orchestrator.py`)
  - Coordinates evidence collection, policy application, and model generation
- Evidence (`src/agent/evidence.py`)
  - Simple store for captured facts about the repository
- Policies (`src/agent/policies.py`)
  - Defines which signals/perspectives to apply over the evidence
- Tools (`src/agent/tools.py`)
  - Registry for operational helpers (e.g., readers, analyzers)
- Models (`src/agent/models.py`)
  - Config and provider abstraction for generation
- CLI (`src/cli.py`)
  - Thin wrapper to run the orchestrator

### Flow
1. CLI receives a `repo_path`
2. Orchestrator gathers basic evidence (stub)
3. Policies are applied (stub)
4. Model generates the summary (stub)
5. Report is returned/written


