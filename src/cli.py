#!/usr/bin/env python3
import argparse
from pathlib import Path

from agent.orchestrator import AgentOrchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repo Explainer Agent")
    parser.add_argument("repo", type=str, help="Path to repository to analyze")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="-",
        help="Output file path or '-' for stdout (default)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_path = Path(args.repo).expanduser().resolve()
    orchestrator = AgentOrchestrator()
    report = orchestrator.run(repo_path=str(repo_path))

    if args.output == "-" or args.output is None:
        print(report)
    else:
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()


