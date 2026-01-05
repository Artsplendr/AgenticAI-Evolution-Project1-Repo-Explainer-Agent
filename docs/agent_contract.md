### Agent Contract

- Purpose: Explain a repository's structure, intent, and key components.
- Inputs:
  - repo_path: absolute or relative path to a target repository
  - config: model/policy knobs (optional)
- Outputs:
  - A markdown report summarizing the repository
  - Optional structured metadata (future)

### Responsibilities
- Collect evidence (files count, structure, notable files)
- Apply policies to determine what to highlight
- Use tools (future) to parse, lint, or extract metadata
- Produce a concise, human-friendly summary

### Non-Goals
- Full static analysis or security audit
- Language-specific deep refactoring advice


