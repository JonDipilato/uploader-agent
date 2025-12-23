from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OpenAIImageConfig:
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-image-1"
    size: str = "1792x1024"
    quality: str | None = None
    style: str | None = None
    base_url: str = "https://api.openai.com/v1/images/generations"


class OpenAIImageClient:
    def __init__(self, config: OpenAIImageConfig) -> None:
        self.config = config

    def generate_image(self, prompt: str, output_path: Path) -> None:
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{self.config.api_key_env} is not set. "
                "Set the environment variable before generating images."
            )

        payload: dict[str, object] = {
            "model": self.config.model,
            "prompt": prompt,
            "size": self.config.size,
            "n": 1,
            "response_format": "b64_json",
        }
        if self.config.quality:
            payload["quality"] = self.config.quality
        if self.config.style:
            payload["style"] = self.config.style

        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.config.base_url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI image request failed: {details}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI image request failed: {exc}") from exc

        data = json.loads(response_body)
        images = data.get("data", [])
        if not images:
            raise RuntimeError("OpenAI image response did not include any images.")
        image_data = images[0].get("b64_json")
        if not image_data:
            raise RuntimeError("OpenAI image response missing b64_json data.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(image_data))
