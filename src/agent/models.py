"""Core data models for the repo-explainer agent.

This module defines:
 - ToolName: a constrained set of valid tool identifiers used by the agent
 - ToolCall: a record of a single tool invocation and a short result preview
 - EvidenceSnippet: a slice of code/text gathered as supporting evidence
 - AgentAnswer: the agent's response bundle with evidence and bookkeeping
 - ModelConfig / ModelProvider: a minimal LLM-provider abstraction (stubbed)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


# A finite set of tool names that the agent can call.
# Using Literal narrows the allowed values at type-check time.
ToolName = Literal["list_files", "read_file", "search_code"]


@dataclass
class ToolCall:
    """Represents a single call to a tool during reasoning."""

    name: ToolName
    args: Dict
    result_preview: str = ""


@dataclass
class EvidenceSnippet:
    """A contiguous span of text captured from a file as evidence."""

    path: str
    line_start: int
    line_end: int
    text: str


@dataclass
class AgentAnswer:
    """The agent's answer along with traceable context and suggested follow-ups."""

    answer: str
    evidence: List[EvidenceSnippet] = field(default_factory=list)
    inspected_files: List[str] = field(default_factory=list)
    # The sequence of tool calls made while reasoning.
    tool_calls: List[ToolCall] = field(default_factory=list)
    # Whether the agent believes more input is required to proceed.
    needs_more_info: bool = False
    # Optional follow-up steps suggested for the user or agent.
    suggested_next_steps: List[str] = field(default_factory=list)


@dataclass
class ModelConfig:
    """Configuration for the model/provider used to generate text."""

    # Provider identifier (e.g., "openai", "anthropic"). "stub" for the demo.
    provider: str = "stub"
    # Concrete model name/version; interpretation depends on provider.
    model: str = "stub-model"


class ModelProvider:
    """Minimal provider wrapper used by the orchestrator.

    This is intentionally lightweight and stubbed to keep the scaffold simple.
    Replace with a real LLM client as your project evolves.
    """

    def __init__(self, config: ModelConfig) -> None:
        """Store configuration for later use."""
        self.config = config

    @staticmethod
    def from_env(config: Optional[ModelConfig] = None) -> "ModelProvider":
        """Factory that would normally read env vars and secrets.

        In this scaffold, we simply return a stubbed provider using the given
        config or a default ModelConfig if none is provided.
        """
        return ModelProvider(config or ModelConfig())

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        """Produce text from a prompt (stubbed).

        Replace this with a real call to your model provider. We return a short
        echo preview so downstream code has something deterministic to display.
        """
        preview = prompt[:80].replace("\n", " ")
        return f"(stub) Generated summary for prompt: {preview} ..."


