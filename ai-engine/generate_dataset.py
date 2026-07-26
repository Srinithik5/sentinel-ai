from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from config.simulation_config import SimulationConfig
from generators.simulator import EnterpriseSimulator
from outputs.writers import write_csv, write_data_dictionary, write_generation_report, write_parquet
from profiles.behavior_profiles import build_behavior_profile_summary


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a synthetic SentinelAI enterprise dataset.")
    parser.add_argument("--num-users", type=int, default=2000)
    parser.add_argument("--num-service-accounts", type=int, default=150)
    parser.add_argument("--num-edge-devices", type=int, default=100)
    parser.add_argument("--num-iot-devices", type=int, default=250)
    parser.add_argument("--num-events", type=int, default=250_000)
    parser.add_argument("--start-date", type=_parse_date, default=None)
    parser.add_argument("--end-date", type=_parse_date, default=None)
    parser.add_argument("--days", type=int, default=30, help="Used when --start-date is not provided.")
    parser.add_argument("--noise-level", type=float, default=0.08)
    parser.add_argument("--remote-work-percentage", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("data/generated"))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    end_date = args.end_date or date.today()
    start_date = args.start_date or (end_date - timedelta(days=args.days))

    config = SimulationConfig(
        num_users=args.num_users,
        num_service_accounts=args.num_service_accounts,
        num_edge_devices=args.num_edge_devices,
        num_iot_devices=args.num_iot_devices,
        start_date=start_date,
        end_date=end_date,
        num_events=args.num_events,
        noise_level=args.noise_level,
        remote_work_percentage=args.remote_work_percentage,
        random_seed=args.seed,
        output_dir=args.output_dir,
    )

    print(
        f"Generating dataset: {config.total_entities:,} entities, target {config.num_events:,} events, "
        f"{config.date_range_days} days ({config.start_date} to {config.end_date})"
    )

    result = EnterpriseSimulator(config).run()

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.output_dir / run_id

    entities_csv = run_dir / "entities.csv"
    entities_parquet = run_dir / "entities.parquet"
    events_csv = run_dir / "events.csv"
    events_parquet = run_dir / "events.parquet"
    behavior_summary_csv = run_dir / "behavior_profile_summary.csv"
    data_dictionary_path = run_dir / "data_dictionary.md"
    report_path = run_dir / "generation_report.md"

    write_csv(result.entities_df, entities_csv)
    write_parquet(result.entities_df, entities_parquet)
    write_csv(result.events_df, events_csv)
    write_parquet(result.events_df, events_parquet)

    behavior_summary = build_behavior_profile_summary(result.entities_df, result.events_df)
    write_csv(behavior_summary, behavior_summary_csv)

    write_data_dictionary(data_dictionary_path)

    file_sizes = {
        path.name: path.stat().st_size
        for path in (
            entities_csv,
            entities_parquet,
            events_csv,
            events_parquet,
            behavior_summary_csv,
            data_dictionary_path,
        )
    }
    write_generation_report(report_path, config, result, file_sizes)

    print(
        f"Generated {len(result.entities_df):,} entities and {len(result.events_df):,} events "
        f"in {result.generation_seconds:.2f}s"
    )
    print(f"Output written to: {run_dir.resolve()}")


if __name__ == "__main__":
    main()