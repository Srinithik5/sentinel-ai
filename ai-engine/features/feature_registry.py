from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    category: str
    dtype: str
    description: str
    calculation: str
    purpose: str


FEATURE_REGISTRY: tuple[FeatureDefinition, ...] = (
    # ---- Temporal ----
    FeatureDefinition(
        name="login_hour",
        category="temporal",
        dtype="int",
        description="Hour of day (0-23) the event occurred, in the entity's own local timezone.",
        calculation="timestamp converted to the entity's IANA timezone via zoneinfo; local_dt.hour.",
        purpose="Baseline temporal signal — off-pattern hours are one of the strongest simple anomaly cues.",
    ),
    FeatureDefinition(
        name="day_of_week",
        category="temporal",
        dtype="int",
        description="Day of week (0=Monday..6=Sunday) the event occurred, local time.",
        calculation="local_dt.weekday().",
        purpose="Lets models learn weekday-specific behavioral baselines per entity.",
    ),
    FeatureDefinition(
        name="is_weekend",
        category="temporal",
        dtype="bool",
        description="Whether the event occurred on a Saturday or Sunday, local time.",
        calculation="day_of_week >= 5.",
        purpose="Cheap, high-signal flag — most entities have near-zero legitimate weekend activity.",
    ),
    FeatureDefinition(
        name="working_hours_deviation",
        category="temporal",
        dtype="float",
        description="Hours between login_hour and the entity's configured working-hours window; 0 if inside it.",
        calculation="0.0 if start<=hour<end, else min(distance to start, distance to end) on a 24h clock.",
        purpose="A graded (not just boolean) measure of how far outside normal hours an event falls.",
    ),
    FeatureDefinition(
        name="time_since_previous_login_seconds",
        category="temporal",
        dtype="float",
        description="Seconds since this entity's previous event; -1.0 if this is their first observed event.",
        calculation="current timestamp minus the tracker's last_timestamp (state strictly before this event).",
        purpose="Core input to burst detection and session-cadence anomalies (e.g. brute force).",
    ),
    FeatureDefinition(
        name="session_duration_zscore",
        category="temporal",
        dtype="float",
        description="How many standard deviations this event's session_duration is from the entity's own historical mean.",
        calculation="(duration - rolling_mean) / rolling_std, using Welford's online algorithm over prior history; 0.0 with <2 prior events.",
        purpose="Personalized (per-entity) outlier signal for session length, robust to different roles having very different normal durations.",
    ),
    # ---- Geographic ----
    FeatureDefinition(
        name="geo_novelty",
        category="geographic",
        dtype="bool",
        description="Whether this event's location has never been seen before for this entity.",
        calculation="geo_location not in the entity's cumulative set of previously observed locations.",
        purpose="First-seen-location is a classic precursor signal to impossible-travel and account-takeover detection.",
    ),
    FeatureDefinition(
        name="geo_velocity_kmh",
        category="geographic",
        dtype="float",
        description="Implied travel speed (km/h) between the entity's previous known office location and this event's location.",
        calculation="haversine distance / elapsed hours since the previous event; 0.0 if either location is unmapped or elapsed time is non-positive.",
        purpose="Direct numeric feature for impossible-travel detection — no threshold baked in, left to the downstream model.",
    ),
    FeatureDefinition(
        name="country_change",
        category="geographic",
        dtype="bool",
        description="Whether this event's country differs from the entity's immediately preceding event's country.",
        calculation="tracker.last_country is not None and last_country != current country.",
        purpose="Coarser, cheaper companion to geo_velocity — flags cross-border movement even when exact timing math is inconclusive.",
    ),
    FeatureDefinition(
        name="city_change_frequency",
        category="geographic",
        dtype="float",
        description="Fraction of this entity's prior events where the city differed from the one immediately before it.",
        calculation="cumulative city-change count / history_length.",
        purpose="Distinguishes entities with naturally itinerant behavior (frequent travelers) from stable ones, contextualizing geo_novelty.",
    ),
    # ---- Device ----
    FeatureDefinition(
        name="device_familiarity_score",
        category="device",
        dtype="float",
        description="Fraction of this entity's prior events that used this exact device fingerprint.",
        calculation="prior occurrence count of this fingerprint / history_length; 0.0 with no prior history.",
        purpose="Graded trust signal for the device — a device used 1% of the time is riskier than one used 90% of the time, even if both are 'known'.",
    ),
    FeatureDefinition(
        name="fingerprint_mismatch",
        category="device",
        dtype="bool",
        description="Whether this device fingerprint has never been seen before for this entity.",
        calculation="device_fingerprint not in the entity's cumulative set of previously observed fingerprints.",
        purpose="Primary signal for device-spoofing and new-device account access.",
    ),
    FeatureDefinition(
        name="os_novelty",
        category="device",
        dtype="bool",
        description="Whether this event's OS signature has never been seen before for this entity.",
        calculation="device_os not in the entity's cumulative known-OS set; False when device_os is absent (most events carry no OS telemetry).",
        purpose="Detects OS-level inconsistency even when the fingerprint string alone might look plausible.",
    ),
    FeatureDefinition(
        name="mac_novelty",
        category="device",
        dtype="bool",
        description="Whether this event's MAC address has never been seen before for this entity.",
        calculation="device_mac not in the entity's cumulative known-MAC set; False when device_mac is absent.",
        purpose="Complements os_novelty as a second independent hardware-identity signal for device spoofing.",
    ),
    # ---- Authentication ----
    FeatureDefinition(
        name="success_ratio",
        category="authentication",
        dtype="float",
        description="Fraction of this entity's prior events that were successful logins.",
        calculation="prior success_count / history_length; 0.0 with no prior history.",
        purpose="Baseline reliability signal — a sudden drop for a normally high-success entity is itself informative.",
    ),
    FeatureDefinition(
        name="failure_ratio",
        category="authentication",
        dtype="float",
        description="Fraction of this entity's prior events that were failed logins.",
        calculation="prior failure_count / history_length; 0.0 with no prior history.",
        purpose="Direct complement of success_ratio, kept as its own feature since models often weight the two asymmetrically.",
    ),
    FeatureDefinition(
        name="consecutive_failures",
        category="authentication",
        dtype="int",
        description="The entity's current run of consecutive failed logins immediately preceding this event.",
        calculation="a streak counter reset to 0 on every success, incremented on every failure, read before this event's own outcome is applied.",
        purpose="The single strongest brute-force signal in the feature set.",
    ),
    FeatureDefinition(
        name="mfa_usage_frequency",
        category="authentication",
        dtype="float",
        description="Fraction of this entity's prior events authenticated via MFA.",
        calculation="prior mfa_count / history_length; 0.0 with no prior history.",
        purpose="An entity whose auth_method suddenly drops MFA usage may indicate a downgraded or compromised session.",
    ),
    # ---- Behaviour ----
    FeatureDefinition(
        name="resource_novelty",
        category="behaviour",
        dtype="bool",
        description="Whether this resource has never been accessed by this entity before.",
        calculation="resource_accessed not in the entity's cumulative set of previously accessed resources.",
        purpose="Core lateral-movement and privilege-escalation signal.",
    ),
    FeatureDefinition(
        name="resource_diversity",
        category="behaviour",
        dtype="float",
        description="Ratio of distinct resources this entity has accessed, relative to its total prior event count.",
        calculation="count(distinct prior resources) / history_length.",
        purpose="A high ratio flags entities whose access pattern is unusually scattered rather than routine.",
    ),
    FeatureDefinition(
        name="command_sequence_complexity",
        category="behaviour",
        dtype="float",
        description="Lexical diversity of this single event's command sequence.",
        calculation="count(distinct commands in this event) / count(commands in this event); 0.0 if empty.",
        purpose="A session that repeats one command many times behaves differently from one that runs many distinct commands.",
    ),
    FeatureDefinition(
        name="session_entropy",
        category="behaviour",
        dtype="float",
        description="Shannon entropy (bits) of the command distribution within this single event's command sequence.",
        calculation="-sum(p * log2(p)) over each distinct command's probability within the sequence.",
        purpose="A more information-theoretic companion to command_sequence_complexity, sensitive to *how* skewed the repetition is, not just whether any exists.",
    ),
    FeatureDefinition(
        name="burst_access_score",
        category="behaviour",
        dtype="float",
        description="Count of this entity's prior events in the trailing 5-minute window before this event.",
        calculation="prior event timestamps within [current_timestamp - 5min, current_timestamp), a pruned sliding window.",
        purpose="Directly targets brute-force- and credential-stuffing-style rapid-fire activity.",
    ),
    FeatureDefinition(
        name="behaviour_drift_score",
        category="behaviour",
        dtype="float",
        description="Fraction of the entity's last N resource accesses that are absent from its established (pre-window) baseline.",
        calculation="|recent_window_resources - baseline_resources| / |recent_window_resources|, where baseline is resources that have aged out of the rolling window.",
        purpose="The core longitudinal signal for insider drift — no single event needs to look anomalous for this to rise.",
    ),
    # ---- Privilege ----
    FeatureDefinition(
        name="privilege_change_indicator",
        category="privilege",
        dtype="bool",
        description="Whether this event accessed a resource owned by a department more sensitive than the entity's own.",
        calculation="resource's owning department's sensitivity tier > the entity's own department's tier (from a fixed 3-tier ordering).",
        purpose="Flags accesses that represent a jump toward more sensitive systems, independent of whether the resource itself is brand new.",
    ),
    FeatureDefinition(
        name="sensitive_resource_access",
        category="privilege",
        dtype="bool",
        description="Whether the accessed resource belongs to the fixed set of high-sensitivity Security/Finance/IT primary resources.",
        calculation="resource_accessed membership in a static set derived from Phase 2's own department/resource catalog.",
        purpose="A context-free severity multiplier — any anomaly against a sensitive resource deserves more attention than the same anomaly elsewhere.",
    ),
    # ---- Statistical ----
    FeatureDefinition(
        name="rolling_mean_session_duration",
        category="statistical",
        dtype="float",
        description="Expanding mean of session_duration across this entity's entire prior history.",
        calculation="Welford's online mean, updated incrementally after every event; 0.0 with no prior history.",
        purpose="The per-entity baseline session_duration_zscore is computed against.",
    ),
    FeatureDefinition(
        name="rolling_std_session_duration",
        category="statistical",
        dtype="float",
        description="Expanding (sample) standard deviation of session_duration across this entity's entire prior history.",
        calculation="Welford's online variance (M2/(n-1)), square-rooted; 0.0 with fewer than 2 prior events.",
        purpose="The dispersion term for session_duration_zscore, and a standalone volatility indicator.",
    ),
    FeatureDefinition(
        name="moving_avg_session_duration",
        category="statistical",
        dtype="float",
        description="Simple moving average of session_duration over the entity's most recent N prior events (default N=5).",
        calculation="mean of a fixed-size trailing deque of prior session_duration values.",
        purpose="Reacts faster to recent behavior change than the all-history rolling mean — the two together separate long-term vs. short-term drift.",
    ),
    FeatureDefinition(
        name="historical_percentile_session_duration",
        category="statistical",
        dtype="float",
        description="This event's session_duration expressed as a percentile (0-100) rank within the entity's prior duration distribution.",
        calculation="rank of current_duration via binary search against a maintained sorted list of prior durations, as a percentage.",
        purpose="A distribution-shape-agnostic alternative to the z-score, robust to the skewed distributions session durations often have.",
    ),
    # ---- Cold Start ----
    FeatureDefinition(
        name="history_length",
        category="cold_start",
        dtype="int",
        description="Count of this entity's events strictly before the current one.",
        calculation="a running counter incremented once per processed event, read before incrementing.",
        purpose="The denominator behind nearly every other ratio feature, and a direct cold-start signal on its own.",
    ),
    FeatureDefinition(
        name="new_entity_flag",
        category="cold_start",
        dtype="bool",
        description="Whether this is the very first observed event for this entity.",
        calculation="history_length == 0.",
        purpose="Every ratio-based feature is meaningless (defaulted to 0.0) on an entity's first event — this flag lets downstream models handle that case explicitly rather than silently.",
    ),
    FeatureDefinition(
        name="confidence_score",
        category="cold_start",
        dtype="float",
        description="How much historical evidence backs this event's behavioral features, saturating to 1.0 once enough history exists.",
        calculation="min(1.0, history_length / confidence_saturation), default saturation point of 30 prior events.",
        purpose="Lets downstream models discount behavioral-anomaly features for entities they barely know anything about yet.",
    ),
)

FEATURE_NAMES: tuple[str, ...] = tuple(feature.name for feature in FEATURE_REGISTRY)
FEATURE_CATEGORIES: tuple[str, ...] = tuple(sorted({feature.category for feature in FEATURE_REGISTRY}))


def get_feature(name: str) -> FeatureDefinition:
    for feature in FEATURE_REGISTRY:
        if feature.name == name:
            return feature
    raise KeyError(f"Unknown feature: {name}")