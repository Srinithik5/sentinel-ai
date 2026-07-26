from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from classification.attack_registry import AttackType
from explainability.evidence_aggregator import ExplainabilityEvidence

_PRIORITY_ORDER: dict[str, int] = {"immediate": 0, "high": 1, "standard": 2}
_ESCALATION_SEVERITIES: frozenset[str] = frozenset({"high", "critical"})


class ActionPriority(str, Enum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    STANDARD = "standard"


@dataclass(frozen=True)
class RecommendedAction:
    action: str
    priority: str
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return {"action": self.action, "priority": self.priority, "rationale": self.rationale}


_ATTACK_RECOMMENDATIONS: dict[AttackType, tuple[RecommendedAction, ...]] = {
    AttackType.BRUTE_FORCE: (
        RecommendedAction(
            "Lock or temporarily disable the targeted account",
            "immediate",
            "A sustained run of consecutive login failures indicates an active credential-guessing attempt.",
        ),
        RecommendedAction(
            "Reset credentials for the affected account",
            "high",
            "Even a failed brute-force attempt exposes the account as a target; rotating credentials removes the risk.",
        ),
        RecommendedAction(
            "Review authentication logs for the source network",
            "standard",
            "Establishes whether the same source targeted other accounts.",
        ),
    ),
    AttackType.IMPOSSIBLE_TRAVEL: (
        RecommendedAction(
            "Verify the entity's actual location with the account owner",
            "immediate",
            "Geographic velocity implies travel that is not physically possible in the elapsed time.",
        ),
        RecommendedAction(
            "Force re-authentication with multi-factor verification",
            "immediate",
            "Confirms the session belongs to the legitimate account owner before any further access is trusted.",
        ),
        RecommendedAction(
            "Reset credentials if travel cannot be confirmed",
            "high",
            "An unconfirmed impossible-travel event is treated as a likely account compromise.",
        ),
    ),
    AttackType.CREDENTIAL_STUFFING: (
        RecommendedAction(
            "Reset credentials for the affected account",
            "immediate",
            "A failed login from an unfamiliar device is consistent with a leaked-credential attempt.",
        ),
        RecommendedAction(
            "Enforce multi-factor authentication for this account if not already required",
            "high",
            "Removes password-only reuse as a viable attack path going forward.",
        ),
        RecommendedAction(
            "Check whether the same source device or network targeted other accounts",
            "standard",
            "Credential stuffing is typically automated against many accounts, not just this one.",
        ),
    ),
    AttackType.LATERAL_MOVEMENT: (
        RecommendedAction(
            "Investigate the account's access to the newly reached resource",
            "immediate",
            "Access to a resource well outside this entity's normal footprint suggests a pivot from a compromised foothold.",
        ),
        RecommendedAction(
            "Review privileged sessions for this entity",
            "high",
            "Lateral movement frequently precedes or follows privilege escalation.",
        ),
        RecommendedAction(
            "Isolate the endpoint if compromise is confirmed",
            "high",
            "Limits further pivoting while the investigation continues.",
        ),
    ),
    AttackType.DEVICE_SPOOFING: (
        RecommendedAction(
            "Isolate the endpoint presenting the mismatched device identity",
            "immediate",
            "A device fingerprint inconsistent with the entity's known devices may itself be compromised or spoofed.",
        ),
        RecommendedAction(
            "Verify the device with the account owner",
            "high",
            "Distinguishes a genuine new device from an actual masquerading attempt.",
        ),
        RecommendedAction(
            "Reset credentials if the device cannot be confirmed as legitimate",
            "high",
            "Assumes compromise until the device is verified.",
        ),
    ),
    AttackType.LOW_AND_SLOW_EXFILTRATION: (
        RecommendedAction(
            "Review the entity's resource access history for signs of data exposure",
            "immediate",
            "Sustained access to sensitive or diverse resources over time is the defining signature of this attack.",
        ),
        RecommendedAction(
            "Review privileged sessions for this entity",
            "high",
            "Establishes whether the broadened access was itself a privilege escalation.",
        ),
        RecommendedAction(
            "Escalate to SOC for data-loss-prevention review",
            "high",
            "Slow exfiltration is designed to stay under simple rate-based detection and warrants specialist review.",
        ),
    ),
    AttackType.INSIDER_DRIFT: (
        RecommendedAction(
            "Review privileged sessions for this entity",
            "immediate",
            "A gradually broadening resource and privilege footprint is the defining signature of insider drift.",
        ),
        RecommendedAction(
            "Discuss the account's recent behavioural change with the entity's manager or department",
            "high",
            "Confirms whether the change in access pattern reflects a legitimate role change.",
        ),
        RecommendedAction(
            "Re-baseline the entity's behaviour profile once reviewed",
            "standard",
            "Ensures the profile reflects the entity's confirmed, current legitimate behaviour going forward.",
        ),
    ),
    AttackType.UNKNOWN: (
        RecommendedAction(
            "Investigate the account activity manually",
            "standard",
            "No known attack signature matched strongly enough for an automated category — analyst judgment is required.",
        ),
        RecommendedAction(
            "Monitor the entity for recurrence",
            "standard",
            "A repeated or escalating pattern from the same entity would strengthen the case for a specific attack type.",
        ),
    ),
}

_ESCALATION_ACTION = RecommendedAction(
    "Escalate to SOC immediately",
    "immediate",
    "Severity is High or Critical, exceeding the threshold for individual analyst handling alone.",
)


class RecommendationEngine:
    """Generates analyst actions for an already-classified event. Actions
    are keyed by the Phase 5 attack type (never re-derived here) plus a
    universal severity-based escalation rule, ordered by priority.
    """

    def recommend(self, evidence: ExplainabilityEvidence) -> tuple[RecommendedAction, ...]:
        attack_type = AttackType(evidence.classification.attack_type)
        actions = list(_ATTACK_RECOMMENDATIONS[attack_type])

        severity = evidence.detection.severity.lower()
        if severity in _ESCALATION_SEVERITIES:
            actions = [_ESCALATION_ACTION] + actions

        return tuple(sorted(actions, key=lambda action: _PRIORITY_ORDER.get(action.priority, 99)))