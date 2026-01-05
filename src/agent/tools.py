"""Repository access utilities and a minimal tool registry.

This module provides:
 - ToolRegistry: a tiny container for registering/invoking function tools
 - RepoTools: deterministic, dependency-light access to a repository via
   three operations: list_files, read_file, and search_code
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

Tool = Callable[..., Any]


class ToolRegistry:
    """Lightweight registry for callable tools keyed by string name.

    This is useful when you want to expose a limited set of operations to a
    reasoning loop while maintaining explicit control over what functions are
    callable.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, tool: Tool) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]

    def list(self) -> Dict[str, Tool]:
        return dict(self._tools)

# --------------------------------------------------------------------------------------
# Deterministic repo access via only 3 tools
# --------------------------------------------------------------------------------------

# Directories frequently ignored in developer repositories. The caller can extend/override.
DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
}


@dataclass(frozen=True)
class SearchHit:
    """A single match from a code search."""

    path: str
    line_number: int
    line_text: str


class RepoTools:
    """Safe, deterministic filesystem helpers scoped to a repository root.

    Exposes three methods:
      - list_files: enumerate files and directories under a path
      - read_file: read a file (optionally truncated)
      - search_code: regex search across text files
    """

    def __init__(self, repo_root: str | Path, ignore_dirs: set[str] | None = None):
        self.repo_root = Path(repo_root).resolve()
        self.ignore_dirs = ignore_dirs or set(DEFAULT_IGNORE_DIRS)

    # Internal helper to ensure paths never escape the configured repo root.
    def _safe_path(self, rel_path: str | Path) -> Path:
        p = (self.repo_root / rel_path).resolve()
        if not str(p).startswith(str(self.repo_root)):
            raise ValueError("Path escapes repo root.")
        return p

    def list_files(self, path: str = ".") -> List[str]:
        """Recursively list repo entries under path, returning relative paths.

        Ignores directories in `self.ignore_dirs`. The result is de-duplicated
        and sorted for stability.
        """
        base = self._safe_path(path)
        if not base.exists():
            return []
        results: List[str] = []

        for root, dirs, files in os.walk(base):
            # Prune ignored directories deterministically
            dirs[:] = sorted([d for d in dirs if d not in self.ignore_dirs])

            root_path = Path(root)
            # Collect child directories and files relative to the repo root
            for d in dirs:
                results.append(str((root_path / d).relative_to(self.repo_root)))
            for f in sorted(files):
                results.append(str((root_path / f).relative_to(self.repo_root)))

        # Return a stable, unique list
        return sorted(set(results))

    def read_file(self, path: str, max_bytes: int = 200_000) -> Tuple[str, List[str]]:
        """Read a file safely and return both full text and split lines.

        Reads up to `max_bytes` to avoid huge files. Non-UTF-8 bytes are replaced.
        """
        p = self._safe_path(path)
        if not p.exists() or not p.is_file():
            return "", []

        data = p.read_bytes()[:max_bytes]
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return text, lines

    def search_code(self, query: str, max_hits: int = 60) -> List[SearchHit]:
        """Regex search across files under the repo root.

        Uses a simple case-insensitive regex; skips likely binary/large formats
        by extension heuristic. Returns at most `max_hits` matches.
        """
        pattern = re.compile(query, re.IGNORECASE)
        hits: List[SearchHit] = []

        for rel in self.list_files("."):
            full = self._safe_path(rel)
            if full.is_dir():
                continue

            # Skip large/binary-like artifacts using a conservative heuristic
            if full.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
                continue

            # Count filename/path matches as signal as well (helps locate cli.py, __main__.py, etc.)
            if pattern.search(rel):
                hits.append(SearchHit(path=rel, line_number=0, line_text="(filename match)"))
                if len(hits) >= max_hits:
                    return hits

            _, lines = self.read_file(rel)
            for i, line in enumerate(lines, start=1):
                if pattern.search(line):
                    hits.append(SearchHit(path=rel, line_number=i, line_text=line.strip()))
                    if len(hits) >= max_hits:
                        return hits

        return hits

