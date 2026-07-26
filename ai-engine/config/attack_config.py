from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from attacks.base import AttackConfig, AttackSeverity


@dataclass(frozen=True)
class AttackSimulationConfig:
    dataset_run_dir: Path
    output_dir: Path = field(default_factory=lambda: Path("data/attacks"))
    random_seed: int = 42
    max_attack_percentage: float = 0.15

    brute_force: AttackConfig = field(
        default_factory=lambda: AttackConfig(injection_percentage=0.015, severity=AttackSeverity.HIGH)
    )
    impossible_travel: AttackConfig = field(
        default_factory=lambda: AttackConfig(injection_percentage=0.01, severity=AttackSeverity.HIGH)
    )
    credential_stuffing: AttackConfig = field(
        default_factory=lambda: AttackConfig(injection_percentage=0.02, severity=AttackSeverity.MEDIUM)
    )
    lateral_movement: AttackConfig = field(
        default_factory=lambda: AttackConfig(injection_percentage=0.01, severity=AttackSeverity.CRITICAL)
    )
    device_spoofing: AttackConfig = field(
        default_factory=lambda: AttackConfig(injection_percentage=0.015, severity=AttackSeverity.MEDIUM)
    )
    low_and_slow_exfiltration: AttackConfig = field(
        default_factory=lambda: AttackConfig(injection_percentage=0.008, severity=AttackSeverity.CRITICAL)
    )
    insider_drift: AttackConfig = field(
        default_factory=lambda: AttackConfig(injection_percentage=0.008, severity=AttackSeverity.LOW)
    )

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_attack_percentage <= 1.0:
            raise ValueError("max_attack_percentage must be between 0.0 and 1.0")