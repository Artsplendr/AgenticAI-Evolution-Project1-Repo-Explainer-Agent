"""Deterministic repository explainer (no LLM).

This module provides a minimal agent that:
 - picks search queries based on simple keyword heuristics
 - searches the repository for those queries
 - reads the top-ranked files
 - returns a structured `AgentAnswer` with evidence snippets

It also includes a small wrapper `AgentOrchestrator` to keep the CLI working
by generating a simple markdown report using the deterministic agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .evidence import EvidenceStore
from .models import AgentAnswer, ToolCall
from .tools import RepoTools, SearchHit


# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
@dataclass
class OrchestratorConfig:
    """Tuning parameters for deterministic repository exploration."""

    # Maximum number of files to read fully after ranking by search hits.
    max_files_to_read: int = 5
    # Minimum number of evidence snippets required to return a confident answer.
    min_evidence_snippets: int = 1


# --------------------------------------------------------------------------------------
# Deterministic agent
# --------------------------------------------------------------------------------------
class RepoExplainerAgent:
    """Keyword-driven repository explainer based on `RepoTools`."""

    def __init__(self, tools: RepoTools, config: OrchestratorConfig | None = None):
        self.tools = tools
        self.config = config or OrchestratorConfig()

    def _query_templates(self, question: str) -> List[str]:
        """Select regex templates based on very simple intent heuristics."""
        q = question.lower()

        # Heuristic: CLI / entry-point
        if "cli" in q or "command" in q or "entry" in q or "entrypoint" in q:
            # Put filename/entry-oriented tokens first so snippet matching picks them up
            return [
                r"\bcli\b|cli\.py|agent\.cli",
                r"__main__",
                r"argparse|typer|click",
                r"entry_points|console_scripts",
                r"main\(",
            ]

        # Heuristic: local run / getting started
        if "run" in q or "start" in q or "locally" in q:
            return [
                r"readme",
                r"docker",
                r"makefile",
                r"poetry|pyproject",
                r"npm|yarn|pnpm",
                r"how to run|getting started|install",
            ]

        # Heuristic: authentication
        if "auth" in q or "authentication" in q or "login" in q:
            return [
                r"auth",
                r"authentication",
                r"login",
                r"jwt",
                r"oauth",
                r"middleware",
            ]

        # Heuristic: logging
        if "logging" in q or "logger" in q:
            return [
                r"logging",
                r"logger",
                r"loglevel|log_level",
                r"structlog",
                r"loguru",
            ]

        # Fallback: generic entry/config terms
        return [r"main", r"config", r"setup", r"entry", r"app"]

    def answer(self, question: str) -> AgentAnswer:
        """Produce a deterministic answer with evidence snippets."""
        evidence = EvidenceStore()
        tool_calls: List[ToolCall] = []

        # 1) search_code with templates
        templates = self._query_templates(question)
        all_hits: List[SearchHit] = []
        for t in templates[:4]:
            hits = self.tools.search_code(t)
            tool_calls.append(
                ToolCall(name="search_code", args={"query": t}, result_preview=f"{len(hits)} hits")
            )
            all_hits.extend(hits)

        # Rank files by number of hits (descending), then by path for stability
        score: dict[str, int] = {}
        for h in all_hits:
            score[h.path] = score.get(h.path, 0) + 1
        ranked_files = sorted(score.keys(), key=lambda p: (-score[p], p))

        # Avoid reading our own agent heuristics file unless explicitly targeted;
        # it tends to contain the keywords as strings and can drown out real matches.
        ranked_files = [
            p for p in ranked_files
            if not p.endswith("src/agent/orchestrator.py")
        ][: self.config.max_files_to_read]

        # 2) read top files + add evidence snippets (first matching lines)
        for path in ranked_files:
            text, lines = self.tools.read_file(path)
            tool_calls.append(
                ToolCall(name="read_file", args={"path": path}, result_preview=f"{len(lines)} lines")
            )
            evidence.mark_inspected(path)

            # Grab up to 2 snippets around first matching line (for any template)
            for i, line in enumerate(lines, start=1):
                if any(t.lower().strip("r") in line.lower() for t in templates[:3]):  # simple heuristic
                    start = max(1, i - 2)
                    end = min(len(lines), i + 2)
                    snippet_text = "\n".join(lines[start - 1 : end])
                    evidence.add_snippet(path, start, end, snippet_text)
                    if len(evidence.snippets) >= 3:
                        break
            if len(evidence.snippets) >= 3:
                break

        # 3) produce answer
        if len(evidence.snippets) < self.config.min_evidence_snippets:
            return AgentAnswer(
                answer="I don’t have enough evidence yet from the repository to answer confidently.",
                evidence=[],
                inspected_files=evidence.inspected_files,
                tool_calls=tool_calls,
                needs_more_info=True,
                suggested_next_steps=[
                    "Try asking a more specific question (e.g., mention a framework/library name).",
                    "Point me to the entrypoint (e.g., main.py, app.py, server.py) or README and I’ll inspect it.",
                ],
            )

        # Lightweight synthesis (still deterministic)
        cited = ", ".join(sorted({s.path for s in evidence.snippets}))
        answer_text = (
            f"Based on what I inspected, the most relevant places are: {cited}.\n"
            f"I’m citing exact snippets below so you can verify quickly."
        )
        return AgentAnswer(
            answer=answer_text,
            evidence=evidence.snippets,
            inspected_files=evidence.inspected_files,
            tool_calls=tool_calls,
            needs_more_info=False,
            suggested_next_steps=[],
        )


# --------------------------------------------------------------------------------------
# Backwards-compatible wrapper used by the CLI
# --------------------------------------------------------------------------------------
class AgentOrchestrator:
    """Compatibility façade for the existing CLI entry-point.

    It builds a `RepoExplainerAgent` for the given repo path and returns a
    simple markdown report using a default question.
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None) -> None:
        self.config = config or OrchestratorConfig()

    def run(self, repo_path: str) -> str:
        repo = Path(repo_path).expanduser().resolve()
        if not repo.exists():
            return f"Repository not found: {repo}"

        tools = RepoTools(repo)
        agent = RepoExplainerAgent(tools, self.config)
        question = "How do I run this project locally?"
        ans = agent.answer(question)

        # Produce a concise markdown report from the structured answer
        lines = [
            "# Repo Explainer Report",
            "",
            f"- Path: {repo}",
            f"- Default question: {question}",
            f"- Files inspected: {len(ans.inspected_files)}",
            "",
            "## Answer",
            ans.answer,
            "",
            "## Evidence (snippets)",
        ]
        for snip in ans.evidence:
            lines.append(f"- {snip.path}:{snip.line_start}-{snip.line_end}")
        if not ans.evidence:
            lines.append("- <none>")

        return "\n".join(lines) + "\n"


