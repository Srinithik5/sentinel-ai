from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from attacks.base import AttackConfig, AttackInjectionResult, AttackModule
from attacks.brute_force import BruteForceAttack
from attacks.credential_stuffing import CredentialStuffingAttack
from attacks.dataset_loader import load_dataset
from attacks.device_spoofing import DeviceSpoofingAttack
from attacks.impossible_travel import ImpossibleTravelAttack
from attacks.insider_drift import InsiderDriftAttack
from attacks.lateral_movement import LateralMovementAttack
from attacks.low_and_slow_exfiltration import LowAndSlowExfiltrationAttack
from config.attack_config import AttackSimulationConfig
from ground_truth.ground_truth_builder import build_ground_truth
from outputs.attack_writers import (
    merge_events,
    write_attack_summary_report,
    write_injected_dataset,
    write_injection_statistics,
)
from outputs.writers import write_csv
from validators.injection_validators import run_all_validations


class AttackOrchestrator:
    """Coordinates every independent attack module against one loaded
    dataset: runs each enabled module, merges the results into the base
    event log, validates the outcome, builds ground truth, and writes every
    required output artifact. Depends only on the AttackModule abstraction
    (DIP) — adding an eighth attack means adding one module here, nothing
    else in this class changes.
    """

    def __init__(self, config: AttackSimulationConfig) -> None:
        self.config = config
        self._modules: list[AttackModule] = self._build_modules()

    def _build_modules(self) -> list[AttackModule]:
        seed = self.config.random_seed
        return [
            BruteForceAttack(replace(self.config.brute_force, random_seed=seed + 1)),
            ImpossibleTravelAttack(replace(self.config.impossible_travel, random_seed=seed + 2)),
            CredentialStuffingAttack(replace(self.config.credential_stuffing, random_seed=seed + 3)),
            LateralMovementAttack(replace(self.config.lateral_movement, random_seed=seed + 4)),
            DeviceSpoofingAttack(replace(self.config.device_spoofing, random_seed=seed + 5)),
            LowAndSlowExfiltrationAttack(replace(self.config.low_and_slow_exfiltration, random_seed=seed + 6)),
            InsiderDriftAttack(replace(self.config.insider_drift, random_seed=seed + 7)),
        ]

    def run(self) -> Path:
        dataset = load_dataset(self.config.dataset_run_dir)

        results: list[AttackInjectionResult] = []
        for module in self._modules:
            result = module.inject(dataset.profiles, dataset.events_df)
            results.append(result)
            status = "enabled" if module.config.enabled else "disabled"
            print(f"  [{status}] {module.attack_type}: {result.incident_count} incidents, {result.event_count} events")

        all_injected_events = [event for result in results for event in result.events]

        merged_df = merge_events(dataset.events_df, all_injected_events)

        start_date = dataset.events_df["timestamp"].min().date()
        end_date = dataset.events_df["timestamp"].max().date()

        validation_report = run_all_validations(
            entities_df=dataset.entities_df,
            merged_df=merged_df,
            injected_event_count=len(all_injected_events),
            start_date=start_date,
            end_date=end_date,
            max_attack_percentage=self.config.max_attack_percentage,
        )

        ground_truth_df = build_ground_truth(dataset.events_df, all_injected_events)

        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = self.config.output_dir / run_id

        write_injected_dataset(merged_df, run_dir / "events_injected.csv", run_dir / "events_injected.parquet")
        write_csv(ground_truth_df, run_dir / "ground_truth.csv")
        write_attack_summary_report(
            run_dir / "attack_summary_report.md", results, validation_report, len(dataset.events_df)
        )
        write_injection_statistics(run_dir / "injection_statistics.csv", results, merged_df)

        print()
        print(f"Total injected events: {len(all_injected_events):,}")
        print(
            f"Validation: {'PASSED' if validation_report.passed else 'FAILED'} "
            f"({validation_report.error_count} errors, {validation_report.warning_count} warnings)"
        )
        print(f"Output written to: {run_dir.resolve()}")

        if not validation_report.passed:
            raise RuntimeError(
                f"Attack injection validation failed with {validation_report.error_count} error(s). "
                f"See {run_dir / 'attack_summary_report.md'} for details."
            )

        return run_dir


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inject synthetic attacks into a SentinelAI Phase 2 dataset.")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        required=True,
        help="Path to a Phase 2 generate_dataset.py run directory (containing entities.csv and events.csv).",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/attacks"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-attack-percentage", type=float, default=0.15)
    parser.add_argument(
        "--disable",
        type=str,
        default="",
        help="Comma-separated attack types to disable, e.g. 'device_spoofing,insider_drift'.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    disabled = {name.strip() for name in args.disable.split(",") if name.strip()}

    def maybe_disable(name: str, config: AttackConfig) -> AttackConfig:
        return replace(config, enabled=name not in disabled)

    base_config = AttackSimulationConfig(
        dataset_run_dir=args.dataset_dir,
        output_dir=args.output_dir,
        random_seed=args.seed,
        max_attack_percentage=args.max_attack_percentage,
    )
    config = replace(
        base_config,
        brute_force=maybe_disable("brute_force", base_config.brute_force),
        impossible_travel=maybe_disable("impossible_travel", base_config.impossible_travel),
        credential_stuffing=maybe_disable("credential_stuffing", base_config.credential_stuffing),
        lateral_movement=maybe_disable("lateral_movement", base_config.lateral_movement),
        device_spoofing=maybe_disable("device_spoofing", base_config.device_spoofing),
        low_and_slow_exfiltration=maybe_disable("low_and_slow_exfiltration", base_config.low_and_slow_exfiltration),
        insider_drift=maybe_disable("insider_drift", base_config.insider_drift),
    )

    print(f"Loading dataset from: {config.dataset_run_dir}")
    print("Injecting attacks:")
    AttackOrchestrator(config).run()


if __name__ == "__main__":
    main()