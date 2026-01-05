### Tool Specifications

This project scaffolds a tool registry. Add concrete tools over time.

- File Reader
  - Input: path(s)
  - Output: file contents and metadata
  - Notes: honor ignore patterns (future)

- Language Detector
  - Input: repo path
  - Output: set of languages and file counts
  - Notes: rely on extensions or lightweight heuristics

- Dependency Extractor
  - Input: repo path
  - Output: top-level dependencies by ecosystem
  - Notes: parse common manifests (`package.json`, `pyproject.toml`, etc.)


