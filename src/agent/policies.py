from dataclasses import dataclass
from typing import List, Optional

from .evidence import EvidenceStore


@dataclass
class Policy:
    name: str
    description: str


class PolicyEngine:
    def __init__(self, policies: Optional[List[Policy]] = None) -> None:
        self.policies = policies or [
            Policy(name="basic", description="Collect basic repo stats"),
        ]

    def apply(self, evidence_store: EvidenceStore) -> List[Policy]:
        # Placeholder: inspect evidence and decide which policies were relevant
        return self.policies


