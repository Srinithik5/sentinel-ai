from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config.simulation_config import SimulationConfig
from generators.simulator import SimulationResult


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path)


def write_json(data: dict | list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


EVENT_DATA_DICTIONARY: tuple[tuple[str, str, str, str], ...] = (
    ("event_id", "string", "Unique identifier for the access event.", "evt-3f9a1b2c4d5e6f70"),
    (
        "timestamp",
        "ISO 8601 datetime (UTC)",
        "Time the event occurred, normalized to UTC.",
        "2026-06-15T14:32:07+00:00",
    ),
    ("entity_id", "string", "Identifier of the entity that generated the event.", "USR-000042"),
    ("entity_type", "string", "One of: user, service_account, edge_device, iot_device.", "user"),
    ("source_ip", "string", "IPv4 address the event originated from.", "10.10.45.12"),
    ("geo_location", "string", "City, country the source IP is associated with.", "New York, USA"),
    ("resource_accessed", "string", "Name of the resource/system accessed.", "Git Repository"),
    ("auth_method", "string", "Authentication method used for the session.", "sso"),
    ("session_duration", "integer (seconds)", "Duration of the session in seconds.", "245"),
    (
        "command_sequence",
        "string (pipe-delimited)",
        "Ordered commands executed during the session.",
        "git_pull|run_tests|git_push",
    ),
    ("device_fingerprint", "string", "Stable hash identifying the device used.", "a1b2c3d4e5f6..."),
    ("login_result", "string", "One of: success, failure.", "success"),
    (
        "risk_context",
        "string (pipe-delimited)",
        "Deterministic contextual tags describing the event.",
        "in_hours|home_location|primary_device|expected_resource",
    ),
    (
        "label",
        "string",
        "Ground-truth label. Phase 2 output is 100% 'normal' — anomaly labels arrive in Phase 3.",
        "normal",
    ),
)


ENTITY_DATA_DICTIONARY: tuple[tuple[str, str, str, str], ...] = (
    ("entity_id", "string", "Unique identifier for the entity.", "USR-000042"),
    ("entity_type", "string", "One of: user, service_account, edge_device, iot_device.", "user"),
    ("display_name", "string", "Human-readable name.", "Jordan Reyes"),
    ("department", "string", "Owning department, or null for standalone devices.", "Engineering"),
    ("role", "string", "Organizational role, or null for devices.", "Employee"),
    ("privilege_level", "string", "One of: low, standard, elevated, admin.", "standard"),
    ("home_location", "string", "City, country of the entity's home office.", "New York, USA"),
    ("home_country", "string", "Country of the entity's home office.", "USA"),
    ("timezone", "string", "IANA timezone of the entity's home office.", "America/New_York"),
    ("working_hours_start", "integer (0-23)", "Local hour the entity's normal activity window begins.", "9"),
    ("working_hours_end", "integer (0-24)", "Local hour the entity's normal activity window ends.", "18"),
    (
        "active_days",
        "string (comma-delimited)",
        "Weekdays (0=Mon..6=Sun) the entity is normally active.",
        "0,1,2,3,4",
    ),
    (
        "normal_resources",
        "string (pipe-delimited)",
        "Resources this entity normally accesses.",
        "Git Repository|CI/CD Pipeline",
    ),
    ("trusted_device_count", "integer", "Number of devices this entity normally uses.", "2"),
    (
        "authentication_methods",
        "string (pipe-delimited)",
        "Authentication methods available to this entity.",
        "sso|mfa",
    ),
    ("normal_login_frequency", "float", "Configured mean events per active day (pre-scaling).", "6.2"),
    ("is_remote", "boolean", "Whether the entity is a remote worker.", "True"),
    ("network_cidr", "string", "Home network CIDR block for this entity.", "10.10.0.0/16"),
    ("schedule_type", "string", "Temporal generation pattern applied to this entity.", "business_hours"),
)


def write_data_dictionary(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# SentinelAI Synthetic Dataset — Data Dictionary", ""]

    lines.append("## events.csv / events.parquet")
    lines.append("")
    lines.append("| Column | Type | Description | Example |")
    lines.append("|---|---|---|---|")
    for name, dtype, description, example in EVENT_DATA_DICTIONARY:
        lines.append(f"| `{name}` | {dtype} | {description} | `{example}` |")

    lines.append("")
    lines.append("## entities.csv / entities.parquet")
    lines.append("")
    lines.append("| Column | Type | Description | Example |")
    lines.append("|---|---|---|---|")
    for name, dtype, description, example in ENTITY_DATA_DICTIONARY:
        lines.append(f"| `{name}` | {dtype} | {description} | `{example}` |")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_generation_report(
    path: Path,
    config: SimulationConfig,
    result: SimulationResult,
    file_sizes: dict[str, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entities_df = result.entities_df
    events_df = result.events_df

    entity_counts = entities_df["entity_type"].value_counts().to_dict()
    department_counts = entities_df["department"].value_counts(dropna=True).to_dict()
    label_counts = events_df["label"].value_counts().to_dict()
    login_result_counts = events_df["login_result"].value_counts().to_dict()

    lines = [
        "# SentinelAI Synthetic Dataset — Generation Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Generation time: {result.generation_seconds:.2f} seconds",
        "",
        "## Configuration",
        "",
        f"- Date range: {config.start_date} to {config.end_date} ({config.date_range_days} days)",
        f"- Target event count: {config.num_events:,}",
        f"- Noise level: {config.noise_level}",
        f"- Remote work percentage: {config.remote_work_percentage:.0%}",
        f"- Random seed: {config.random_seed}",
        "",
        "## Entity Counts",
        "",
        f"- Total entities: {len(entities_df):,}",
    ]
    for entity_type, count in entity_counts.items():
        lines.append(f"  - {entity_type}: {count:,}")

    lines.append("")
    lines.append("## Department Distribution")
    lines.append("")
    for department, count in department_counts.items():
        lines.append(f"- {department}: {count:,}")

    lines.append("")
    lines.append("## Event Summary")
    lines.append("")
    lines.append(f"- Total events generated: {len(events_df):,}")
    for label, count in label_counts.items():
        lines.append(f"  - label={label}: {count:,}")
    for result_type, count in login_result_counts.items():
        lines.append(f"  - login_result={result_type}: {count:,}")

    lines.append("")
    lines.append("## Output Files")
    lines.append("")
    for filename, size_bytes in file_sizes.items():
        size_mb = size_bytes / (1024 * 1024)
        lines.append(f"- {filename}: {size_mb:.2f} MB")

    path.write_text("\n".join(lines), encoding="utf-8")