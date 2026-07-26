from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileFieldDefinition:
    name: str
    profile_type: str
    dtype: str
    description: str
    purpose: str


PROFILE_FIELD_REGISTRY: tuple[ProfileFieldDefinition, ...] = (
    # ---- Statistical ----
    ProfileFieldDefinition(
        "sample_count", "statistical", "int",
        "Number of normal events this profile was learned from.",
        "Denominator for every ratio in the profile; also the basis for confidence scoring.",
    ),
    ProfileFieldDefinition(
        "avg_login_hour", "statistical", "float",
        "Mean local login hour (0-23) across all learned events.",
        "The entity's typical time-of-day baseline.",
    ),
    ProfileFieldDefinition(
        "login_hour_std", "statistical", "float",
        "Standard deviation of local login hour across learned events.",
        "How tightly clustered the entity's activity is around its typical hour.",
    ),
    ProfileFieldDefinition(
        "avg_session_duration", "statistical", "float",
        "Mean session_duration (seconds) across learned events.",
        "Baseline session length for anomaly comparison.",
    ),
    ProfileFieldDefinition(
        "session_duration_std", "statistical", "float",
        "Standard deviation of session_duration across learned events.",
        "Dispersion term paired with avg_session_duration.",
    ),
    ProfileFieldDefinition(
        "authentication_frequency_per_day", "statistical", "float",
        "Mean number of events per active day.",
        "Baseline cadence — a sudden spike or drop is itself a signal.",
    ),
    ProfileFieldDefinition(
        "failure_rate", "statistical", "float",
        "Fraction of learned events that were failed logins.",
        "Baseline reliability; downstream scoring compares live failure rate against this.",
    ),
    ProfileFieldDefinition(
        "resource_frequency", "statistical", "dict[str, float]",
        "Resource name -> fraction of learned events accessing it.",
        "The entity's normal resource-access distribution, for novelty/drift comparison.",
    ),
    ProfileFieldDefinition(
        "device_frequency", "statistical", "dict[str, float]",
        "Device fingerprint -> fraction of learned events using it.",
        "The entity's normal device mix.",
    ),
    ProfileFieldDefinition(
        "geo_frequency", "statistical", "dict[str, float]",
        "Location -> fraction of learned events originating there.",
        "The entity's normal location mix.",
    ),
    ProfileFieldDefinition(
        "working_hour_ratio", "statistical", "float",
        "Fraction of learned events that fell within the entity's configured working hours.",
        "Summarizes the working-hour pattern into one comparable number.",
    ),
    # ---- Sequence ----
    ProfileFieldDefinition(
        "command_transition_matrix", "sequence", "dict[str, dict[str, float]]",
        "First-order Markov transition probabilities between commands within a session.",
        "Explainable representation of typical command order — feeds sequence-anomaly scoring.",
    ),
    ProfileFieldDefinition(
        "resource_transition_matrix", "sequence", "dict[str, dict[str, float]]",
        "First-order Markov transition probabilities between consecutively accessed resources.",
        "Captures typical resource-traversal order (e.g. login gateway -> primary system).",
    ),
    ProfileFieldDefinition(
        "common_resource_sequences", "sequence", "tuple[tuple[str, ...], ...]",
        "The entity's most frequent length-3 resource access sequences.",
        "Human-readable summary of typical multi-step workflows.",
    ),
    # ---- Relationship ----
    ProfileFieldDefinition(
        "associated_devices", "relationship", "tuple[str, ...]",
        "Distinct device fingerprints observed for this entity.",
        "Reusable lookup for device-familiarity scoring.",
    ),
    ProfileFieldDefinition(
        "associated_resources", "relationship", "tuple[str, ...]",
        "Distinct resources observed for this entity.",
        "Reusable lookup for resource-novelty scoring.",
    ),
    ProfileFieldDefinition(
        "associated_locations", "relationship", "tuple[str, ...]",
        "Distinct locations observed for this entity.",
        "Reusable lookup for geo-novelty scoring.",
    ),
    ProfileFieldDefinition(
        "department_common_resources", "relationship", "tuple[str, ...]",
        "The most common resources across all entities sharing this entity's department.",
        "Peer-group baseline — lets scoring distinguish 'unusual for this person' from 'unusual for anyone in this role'.",
    ),
    ProfileFieldDefinition(
        "resource_sharing_score", "relationship", "float",
        "Jaccard similarity between this entity's resource set and its department peers'.",
        "A low score flags an entity whose access pattern diverges from its peer group even if individually plausible.",
    ),
    # ---- Drift ----
    ProfileFieldDefinition(
        "drift_score", "drift", "float",
        "Composite distance (0.0-1.0) between the historical and current statistical profile.",
        "Quantifies how much an entity's baseline has moved since the last profiling run.",
    ),
    ProfileFieldDefinition(
        "is_significant_drift", "drift", "bool",
        "Whether drift_score exceeds the configured significance threshold.",
        "A coarse flag for the Drift Report without hard-gating the (always current) active profile.",
    ),
    ProfileFieldDefinition(
        "profile_version", "drift", "int",
        "Monotonically increasing version number for this entity's profile.",
        "Full version history lets downstream systems audit how a baseline evolved.",
    ),
    # ---- Cold Start ----
    ProfileFieldDefinition(
        "history_length", "cold_start", "int",
        "Number of normal events backing this profile (same value as statistical.sample_count).",
        "The raw evidence count behind the confidence score.",
    ),
    ProfileFieldDefinition(
        "is_new_entity", "cold_start", "bool",
        "Whether this entity had zero learned events in this run.",
        "Distinguishes true cold-start entities from ones merely still warming up.",
    ),
    ProfileFieldDefinition(
        "confidence_score", "cold_start", "float",
        "0.0-1.0 score reflecting how much history backs this profile.",
        "Lets downstream scoring discount profiles built from too little data.",
    ),
    ProfileFieldDefinition(
        "warmup_strategy", "cold_start", "str",
        "insufficient_data | warming_up | established.",
        "A categorical summary of confidence_score for reporting and simple gating logic.",
    ),
)


def get_fields_for(profile_type: str) -> tuple[ProfileFieldDefinition, ...]:
    return tuple(field for field in PROFILE_FIELD_REGISTRY if field.profile_type == profile_type)