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


def run_once(config_path: Path, test_minutes: int | None = None, test_mode: bool = False) -> None:
    config = load_config(config_path)
    agent = VideoCreatorAgent(config)
    agent.run_once(test_minutes=test_minutes, test_mode=test_mode)


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
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (no upload, no repeat)",
    )
    parser.add_argument(
        "--test-minutes",
        type=int,
        default=None,
        help="Test mode duration in minutes (optional)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    schedule_enabled = config.get("schedule", {}).get("enabled", True)
    if args.once or not schedule_enabled:
        run_once(args.config, test_minutes=args.test_minutes, test_mode=args.test)
    else:
        run_scheduler(args.config)


if __name__ == "__main__":
    main()
