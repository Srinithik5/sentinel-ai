from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from detection.threshold_manager import SeverityLevel


class AttackType(str, Enum):
    BRUTE_FORCE = "brute_force"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    CREDENTIAL_STUFFING = "credential_stuffing"
    LATERAL_MOVEMENT = "lateral_movement"
    DEVICE_SPOOFING = "device_spoofing"
    LOW_AND_SLOW_EXFILTRATION = "low_and_slow_exfiltration"
    INSIDER_DRIFT = "insider_drift"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AttackDefinition:
    """The static, canonical description of one attack category — name,
    description, the indicators AttackClassifier looks for, its MITRE
    mapping, and its typical severity. This is the single source of truth
    every other classification module reads from, so a tactic/technique
    string or a severity rating is never duplicated across files.
    """

    attack_type: AttackType
    display_name: str
    description: str
    indicators: tuple[str, ...]
    mitre_tactic: str
    mitre_technique: str
    typical_severity: SeverityLevel

    def to_dict(self) -> dict[str, object]:
        return {
            "attack_type": self.attack_type.value,
            "display_name": self.display_name,
            "description": self.description,
            "indicators": list(self.indicators),
            "mitre_tactic": self.mitre_tactic,
            "mitre_technique": self.mitre_technique,
            "typical_severity": self.typical_severity.value,
        }


# MITRE tactic/technique strings are deliberately identical to the ones
# Phase 2B's attack modules already assign (attacks/*.py), so ground-truth
# labels and classifier output describe the same attack the same way.
ATTACK_REGISTRY: dict[AttackType, AttackDefinition] = {
    AttackType.BRUTE_FORCE: AttackDefinition(
        attack_type=AttackType.BRUTE_FORCE,
        display_name="Brute Force",
        description=(
            "Repeated authentication attempts against a single account until one succeeds, evidenced by a run "
            "of consecutive login failures concentrated in a short window from the entity's own known device."
        ),
        indicators=(
            "consecutive_failures >= 3 within the session",
            "elevated burst_access_score (many attempts in a short window)",
            "high authentication-dimension deviation from the entity's normal failure rate",
            "login_result is failure",
            "device identity consistent with the entity's known device (rules out spoofing/stuffing overlap)",
        ),
        mitre_tactic="Credential Access",
        mitre_technique="T1110 Brute Force",
        typical_severity=SeverityLevel.HIGH,
    ),
    AttackType.IMPOSSIBLE_TRAVEL: AttackDefinition(
        attack_type=AttackType.IMPOSSIBLE_TRAVEL,
        display_name="Impossible Travel",
        description=(
            "A login from a geographic location physically unreachable from the entity's previous session within "
            "the elapsed time, indicating a stolen or shared credential used from a second location."
        ),
        indicators=(
            "geo_velocity_kmh far exceeds plausible travel speed",
            "country_change is true",
            "geo_novelty (location never seen in the entity's profile)",
            "high geographic-dimension deviation",
            "login_result is success (the credential worked)",
        ),
        mitre_tactic="Initial Access",
        mitre_technique="T1078 Valid Accounts",
        typical_severity=SeverityLevel.CRITICAL,
    ),
    AttackType.CREDENTIAL_STUFFING: AttackDefinition(
        attack_type=AttackType.CREDENTIAL_STUFFING,
        display_name="Credential Stuffing",
        description=(
            "Automated login attempts using credential pairs leaked elsewhere, evidenced by a failed login paired "
            "with an unfamiliar device rather than the sustained single-device hammering of brute force."
        ),
        indicators=(
            "login_result is failure",
            "device_familiarity_score is low (device rarely or never used before)",
            "fingerprint_mismatch, os_novelty, or mac_novelty accompanies the failure",
            "a moderate, not extreme, run of consecutive_failures",
            "burst_access_score stays below the brute-force rapid-fire threshold",
        ),
        mitre_tactic="Credential Access",
        mitre_technique="T1110.004 Credential Stuffing",
        typical_severity=SeverityLevel.HIGH,
    ),
    AttackType.LATERAL_MOVEMENT: AttackDefinition(
        attack_type=AttackType.LATERAL_MOVEMENT,
        display_name="Lateral Movement",
        description=(
            "Access to a resource well outside the entity's normal and peer-department resource set, especially a "
            "sensitive resource reached via an improbable resource transition — a compromised account pivoting."
        ),
        indicators=(
            "resource_novelty (resource never seen in the entity's profile)",
            "sensitive_resource_access is true",
            "low resource_sharing_score against the entity's department peers",
            "low transition probability from the previous resource in this session",
            "high resource-dimension deviation",
        ),
        mitre_tactic="Lateral Movement",
        mitre_technique="T1021 Remote Services",
        typical_severity=SeverityLevel.HIGH,
    ),
    AttackType.DEVICE_SPOOFING: AttackDefinition(
        attack_type=AttackType.DEVICE_SPOOFING,
        display_name="Device Spoofing",
        description=(
            "A session presenting a device identity inconsistent with the entity's known devices — mismatched "
            "fingerprint, or an unfamiliar OS/MAC pairing — indicating identity masquerading."
        ),
        indicators=(
            "fingerprint_mismatch is true",
            "os_novelty or mac_novelty is true",
            "very low device_familiarity_score",
            "high device-dimension deviation",
            "login_result is success (the spoofed identity was accepted)",
        ),
        mitre_tactic="Defense Evasion",
        mitre_technique="T1036 Masquerading",
        typical_severity=SeverityLevel.MEDIUM,
    ),
    AttackType.LOW_AND_SLOW_EXFILTRATION: AttackDefinition(
        attack_type=AttackType.LOW_AND_SLOW_EXFILTRATION,
        display_name="Low-and-Slow Exfiltration",
        description=(
            "Sustained, deliberately unhurried access to sensitive or diverse resources — a long session and broad "
            "resource diversity without the burstiness of brute force, designed to stay under rate-based detection."
        ),
        indicators=(
            "sensitive_resource_access is true",
            "elevated resource_diversity across the entity's history",
            "session_duration well above the entity's historical percentile",
            "burst_access_score stays low despite elevated deviation (deliberately unhurried)",
            "elevated session-dimension deviation",
        ),
        mitre_tactic="Exfiltration",
        mitre_technique="T1030 Data Transfer Size Limits",
        typical_severity=SeverityLevel.MEDIUM,
    ),
    AttackType.INSIDER_DRIFT: AttackDefinition(
        attack_type=AttackType.INSIDER_DRIFT,
        display_name="Insider Drift",
        description=(
            "A gradual, multi-session broadening of a known entity's behaviour — rising privilege and resource "
            "footprint across successive profile versions rather than one sharp spike."
        ),
        indicators=(
            "privilege_change_indicator is true",
            "behaviour_drift_score elevated for this event",
            "the entity's own profile drift_score is elevated",
            "the entity is established, not cold-start (drift from a real baseline, not a first impression)",
            "drift_score is rising across the entity's recent profile-version history",
        ),
        mitre_tactic="Privilege Escalation",
        mitre_technique="T1078 Valid Accounts",
        typical_severity=SeverityLevel.MEDIUM,
    ),
    AttackType.UNKNOWN: AttackDefinition(
        attack_type=AttackType.UNKNOWN,
        display_name="Unknown",
        description=(
            "Flagged as anomalous by Phase 4, but no known attack signature scored above the minimum match "
            "threshold — warrants manual triage rather than an automated category."
        ),
        indicators=(),
        mitre_tactic="Unknown",
        mitre_technique="Unknown",
        typical_severity=SeverityLevel.LOW,
    ),
}


def get_attack_definition(attack_type: AttackType) -> AttackDefinition:
    return ATTACK_REGISTRY[attack_type]


KNOWN_ATTACK_TYPES: tuple[AttackType, ...] = tuple(
    attack_type for attack_type in ATTACK_REGISTRY if attack_type != AttackType.UNKNOWN
)