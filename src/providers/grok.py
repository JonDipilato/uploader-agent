from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class GrokConfig:
    mode: str
    command: str | Sequence[str] | None
    api_key_env: str | None
    model: str | None


class GrokClient:
    def __init__(self, config: GrokConfig) -> None:
        self.config = config

    def generate_loop_video(
        self,
        image_path: Path,
        output_path: Path,
        prompt: str,
        duration_seconds: int,
        fps: int,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.config.mode != "command":
            raise NotImplementedError(
                "Grok API mode is not implemented. Use mode=command with a CLI template."
            )
        if not self.config.command:
            raise ValueError("Grok command template is required when mode=command")
        if self.config.api_key_env and not os.getenv(self.config.api_key_env):
            raise ValueError(f"Missing {self.config.api_key_env} for Grok")
        mapping = {
            "prompt": prompt,
            "image_path": str(image_path),
            "output_path": str(output_path),
            "duration": str(duration_seconds),
            "fps": str(fps),
            "model": self.config.model or "",
        }
        command = _format_command(self.config.command, mapping)
        _run_command(command)


def _format_command(template: str | Sequence[str], mapping: dict[str, str]) -> list[str]:
    if isinstance(template, str):
        return shlex.split(template.format(**mapping))
    return [str(part).format(**mapping) for part in template]


def _run_command(command: list[str]) -> None:
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError("Grok command failed")
