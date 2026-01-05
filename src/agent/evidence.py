"""Evidence collection primitives for the repo-explainer agent.

This module defines:
 - EvidenceStore: tracks inspected files and extracted `EvidenceSnippet`s
 - Evidence (deprecated): legacy key/value evidence item kept for compatibility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .models import EvidenceSnippet


# --------------------------------------------------------------------------------------
# Deprecated legacy item kept only to avoid breaking older orchestrator code.
# Prefer adding snippet-based evidence to `EvidenceStore` instead.
# --------------------------------------------------------------------------------------
@dataclass
class Evidence:
    """Legacy key/value evidence item (deprecated)."""

    kind: str
    key: str
    value: str


@dataclass
class EvidenceStore:
    """In-memory store for files inspected and evidence snippets.

    Chunk-level responsibilities:
      - maintain an ordered list of files inspected by the agent
      - collect code/text snippets with positions for later citation
    """

    # Paths the agent looked at while reasoning (relative or absolute).
    inspected_files: List[str] = field(default_factory=list)
    # Snippets cited as supporting evidence.
    snippets: List[EvidenceSnippet] = field(default_factory=list)

    def mark_inspected(self, path: str) -> None:
        """Record that a file path was inspected (deduplicated, order-preserving)."""
        if path not in self.inspected_files:
            self.inspected_files.append(path)

    def add_snippet(self, path: str, line_start: int, line_end: int, text: str) -> None:
        """Append a new snippet of text gathered from a file."""
        self.snippets.append(
            EvidenceSnippet(
                path=path,
                line_start=line_start,
                line_end=line_end,
                text=text,
            )
        )

    # Convenience bridge for legacy call sites that added key/value evidence.
    # This allows older code to continue working while the project transitions
    # toward snippet-first evidence.
    def add(self, evidence: Evidence) -> None:  # type: ignore[override]
        """Compatibility method: map legacy Evidence into store metadata."""
        if evidence.kind == "meta" and evidence.key == "inspected_file":
            self.mark_inspected(evidence.value)
        else:
            # Store as a plain snippet-like item without line positions.
            self.add_snippet(path=evidence.key or "<meta>", line_start=0, line_end=0, text=evidence.value)

