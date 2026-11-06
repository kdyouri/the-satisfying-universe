"""Bounded OpenRouter HTTP adapter. Paid POSTs are deliberately never retried."""

import json
import re
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests


class ProviderError(RuntimeError):
    """Safe message only: no raw upstream body, signed URL or credential."""


class ProviderTerminalError(ProviderError):
    """Definitive parsed provider failure; stop instead of retrying free reads."""


def usd(value) -> Decimal:
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ProviderError("Invalid provider cost; retain the reservation")
    return number.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)


@dataclass
class ChatResult:
    content: str
    cost: Decimal
    request_id: str


def strict_schema(schema: dict) -> dict:
    schema = json.loads(json.dumps(schema))

    def visit(value):
        if isinstance(value, dict):
            value.pop("default", None)
            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(schema)
    return schema


def gemini_schema(schema: dict) -> dict:
    """Limit native schema complexity; the full Pydantic contract still validates output."""
    schema = json.loads(json.dumps(schema))

    def visit(value):
        if isinstance(value, dict):
            for key in (
                "minimum",
                "maximum",
                "minLength",
                "maxLength",
                "minItems",
                "maxItems",
                "title",
            ):
                value.pop(key, None)
            for key, child in value.items():
                if key in {"properties", "$defs", "definitions"} and isinstance(child, dict):
                    for definition in child.values():
                        visit(definition)
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    return schema


class OpenRouter:
    def __init__(self, key: str, base: str = "https://openrouter.ai/api/v1", timeout=(10, 90)):
        parsed = urlsplit(base)
        if base != "https://openrouter.ai/api/v1" and not (
            parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
        ):
            raise ValueError("Only the official API or an explicit loopback simulation is allowed")
        self.base, self.timeout = base.rstrip("/"), timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "TechnoInno Studio",
            }
        )

    def request_timeout(self, body: dict | None):
        # Requests retains the connect socket timeout while sending the body.
        # A base64 review can take longer to upload than our small catalogue calls.
        for message in (body or {}).get("messages", []):
            content = message.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                video = part.get("video_url", {}) if isinstance(part, dict) else {}
                url = video.get("url", "") if isinstance(video, dict) else ""
                if isinstance(url, str) and url.startswith("data:video/") and len(url) >= 1048576:
                    connect, read = self.timeout
                    return (max(connect, 120), read)
        return self.timeout

    def json(self, method: str, path: str, body: dict | None = None) -> dict:
        try:
            response = self.session.request(
                method,
                self.base + path,
                json=body,
                timeout=self.request_timeout(body),
                allow_redirects=False,
            )
        except requests.RequestException:
            raise ProviderError(
                "Provider connection failed; do not repeat a paid submission"
            ) from None
        if response.status_code not in (200, 202):
            raise ProviderError(f"Provider HTTP {response.status_code}; paid POST was not retried")
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError
            if "error" in result:
                # A parsed error body is a definitive answer, even beside HTTP 200.
                error = result["error"]
                if isinstance(error, dict):
                    detail = error.get("code") or error.get("message") or "provider error"
                else:
                    detail = error
                raise ProviderTerminalError(str(detail)[:200])
            return result
        except (ValueError, TypeError):
            raise ProviderError(
                "Invalid provider response; retain uncertain reservations"
            ) from None

    def catalogues(self) -> tuple[dict, dict]:
        videos = {m["id"]: m for m in self.json("GET", "/videos/models")["data"]}
        models = {m["id"]: m for m in self.json("GET", "/models")["data"]}
        return videos, models

    def verify_key(self):
        if not isinstance(self.json("GET", "/key").get("data"), dict):
            raise ProviderError("OpenRouter key could not be verified")

    def chat(
        self, model: str, content: list, schema: dict, prices: tuple[str, str], max_tokens=1200
    ) -> ChatResult:
        wire_schema = strict_schema(schema)
        if model.startswith("google/gemini-"):
            wire_schema = gemini_schema(wire_schema)
        body = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "reasoning": {"enabled": False},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "pilot_result",
                    "strict": True,
                    "schema": wire_schema,
                },
            },
            "provider": {
                "sort": "price",
                "allow_fallbacks": False,
                "require_parameters": True,
                "max_price": {"prompt": float(prices[0]), "completion": float(prices[1])},
            },
        }
        if model.startswith("google/gemini-"):
            # This standard endpoint accepted the practical review contract live.
            # Keep the same price caps and disable paid fallback/retries.
            body["provider"].update(
                only=["google-ai-studio"],
                ignore=["google-ai-studio/flex", "google-ai-studio/priority"],
            )
        response = self.json("POST", "/chat/completions", body)
        try:
            request_id = response["id"]
            cost = usd(response["usage"]["cost"])
            content = response["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not isinstance(request_id, str) or not request_id:
                raise ValueError
            return ChatResult(content=content, cost=cost, request_id=request_id)
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Incomplete chat/cost evidence; retain the reservation") from None

    @staticmethod
    def job_path(job_id: str) -> str:
        if not isinstance(job_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,249}", job_id
        ):
            raise ProviderError("Invalid remote job identifier")
        return "/videos/" + quote(job_id, safe="")

    def submit(self, body: dict) -> str:
        response = self.json("POST", "/videos", body)
        remote_id = response.get("id", "")
        self.job_path(remote_id)
        return remote_id

    def poll(self, remote_id: str) -> dict:
        return self.json("GET", self.job_path(remote_id))

    def download(self, remote_id: str, destination: Path, maximum=100 * 1024 * 1024):
        temporary = destination.with_suffix(".partial")
        try:
            with self.session.get(
                self.base + self.job_path(remote_id) + "/content?index=0",
                stream=True,
                timeout=(10, 120),
                allow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise ProviderError(
                        f"Video download HTTP {response.status_code}; no redirect followed"
                    )
                if "video/mp4" not in response.headers.get("Content-Type", ""):
                    raise ProviderError("Video download has an unexpected media type")
                size = 0
                with temporary.open("wb") as output:
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > maximum:
                            raise ProviderError("Video download exceeds the size limit")
                        output.write(chunk)
            if not size:
                raise ProviderError("Empty video download")
            temporary.replace(destination)
        except requests.RequestException:
            raise ProviderError(
                "Video download interrupted; the known job can be resumed"
            ) from None
        finally:
            temporary.unlink(missing_ok=True)
