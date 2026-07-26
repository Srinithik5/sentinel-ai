from __future__ import annotations

from dataclasses import dataclass

from classification.attack_registry import AttackType, get_attack_definition


@dataclass(frozen=True)
class MitreMapping:
    tactic: str
    technique: str

    def to_dict(self) -> dict[str, object]:
        return {"mitre_tactic": self.tactic, "mitre_technique": self.technique}


def map_attack(attack_type: AttackType) -> MitreMapping:
    """Looks up the canonical MITRE ATT&CK tactic/technique for an attack
    type. A pure, deterministic read of AttackRegistry — the single source
    of truth for every tactic/technique string in the project — so no
    classification component ever hardcodes its own MITRE mapping.
    """
    definition = get_attack_definition(attack_type)
    return MitreMapping(tactic=definition.mitre_tactic, technique=definition.mitre_technique)