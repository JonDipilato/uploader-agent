from __future__ import annotations

import argparse
import time
from pathlib import Path

import schedule
import yaml

from .pipeline import VideoCreatorAgent


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def run_once(config_path: Path) -> None:
    config = load_config(config_path)
    agent = VideoCreatorAgent(config)
    agent.run_once()


def run_scheduler(config_path: Path) -> None:
    config = load_config(config_path)
    schedule_cfg = config.get("schedule", {})
    daily_time = schedule_cfg.get("daily_time", "03:00")
    agent = VideoCreatorAgent(config)
    schedule.every().day.at(daily_time).do(agent.run_once)
    while True:
        schedule.run_pending()
        time.sleep(30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Video creator agent")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to YAML config",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the pipeline once and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    schedule_enabled = config.get("schedule", {}).get("enabled", True)
    if args.once or not schedule_enabled:
        run_once(args.config)
    else:
        run_scheduler(args.config)


if __name__ == "__main__":
    main()
