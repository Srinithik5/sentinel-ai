from __future__ import annotations

from dataclasses import dataclass

from classification.attack_registry import ATTACK_REGISTRY


@dataclass(frozen=True)
class MitreEntry:
    """One row of the dashboard's MITRE ATT&CK reference panel. Derived
    directly from `classification.attack_registry.ATTACK_REGISTRY` — the
    project's single source of truth for attack descriptions, MITRE
    mappings, and typical severity — rather than a separate, hand-typed
    copy that could drift out of sync with the classifier it describes.
    """

    attack_type: str
    display_name: str
    tactic: str
    technique: str
    severity: str
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "attackType": self.attack_type,
            "displayName": self.display_name,
            "tactic": self.tactic,
            "technique": self.technique,
            "severity": self.severity,
            "description": self.description,
        }


def build_mitre_entries() -> tuple[MitreEntry, ...]:
    """Builds the dashboard's MITRE reference table straight from the real
    `ATTACK_REGISTRY` used by Phase 5's classifier — includes `unknown`,
    matching what Phase 5 can actually emit as an `attack_type`.
    """
    return tuple(
        MitreEntry(
            attack_type=definition.attack_type.value,
            display_name=definition.display_name,
            tactic=definition.mitre_tactic,
            technique=definition.mitre_technique,
            severity=definition.typical_severity.value,
            description=definition.description,
        )
        for definition in ATTACK_REGISTRY.values()
    )