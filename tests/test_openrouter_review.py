import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
import requests
from pydantic import ValidationError

from tsu.contracts import PracticalReview
from tsu.openrouter import OpenRouter, ProviderError, gemini_schema


def test_gemini_projection_preserves_properties_named_like_schema_keywords():
    original = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "maxLength": 100},
            "maximum": {"type": "integer", "maximum": 3},
        },
        "required": ["title", "maximum"],
    }
    wire = gemini_schema(original)
    assert wire["properties"] == {"title": {"type": "string"}, "maximum": {"type": "integer"}}
    assert wire["required"] == ["title", "maximum"]
    assert original["properties"]["title"]["maxLength"] == 100


def test_compact_gemini_review_keeps_full_application_validation(monkeypatch):
    provider = OpenRouter("synthetic-key", "http://127.0.0.1:4999")
    observed = []
    valid = {
        "visual_realism": 22,
        "motion_quality": 18,
        "aesthetic_quality": 18,
        "prompt_compliance": 18,
        "technical_quality": 15,
        "technical_pass": True,
        "severe_defects": [],
        "issues": [],
        "audio_coherence": "coherent",
    }

    def respond(*args, **kwargs):
        observed.append(kwargs["json"])
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "id": "synthetic-review",
                "usage": {"cost": 0.000001},
                "choices": [{"message": {"content": json.dumps(valid)}}],
            },
        )

    monkeypatch.setattr(provider.session, "request", respond)
    original = PracticalReview.model_json_schema()
    result = provider.chat("google/gemini-3.1-flash-lite", [], original, ("0.25", "1.50"))
    assert PracticalReview.model_validate_json(result.content).approved
    wire = observed[0]
    assert (
        "maximum"
        not in wire["response_format"]["json_schema"]["schema"]["properties"]["visual_realism"]
    )
    assert original["properties"]["visual_realism"]["maximum"] == 25
    assert wire["provider"]["max_price"] == {"prompt": 0.25, "completion": 1.5}
    assert wire["provider"]["only"] == ["google-ai-studio"]
    assert not wire["provider"]["allow_fallbacks"]
    assert wire["provider"]["require_parameters"]
    with pytest.raises(ValidationError):
        PracticalReview.model_validate({**valid, "visual_realism": 26})
    assert not PracticalReview.model_validate(
        {**valid, "audio_coherence": "not_observable"}
    ).approved


def test_non_gemini_models_keep_the_existing_schema_and_routing(monkeypatch):
    provider = OpenRouter("synthetic-key", "http://127.0.0.1:4999")
    observed = []

    def respond(*args, **kwargs):
        observed.append(kwargs["json"])
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "id": "synthetic-creative",
                "usage": {"cost": 0.000001},
                "choices": [{"message": {"content": "{}"}}],
            },
        )

    monkeypatch.setattr(provider.session, "request", respond)
    provider.chat(
        "google/gemma-4-26b-a4b-it", [], PracticalReview.model_json_schema(), ("0.1", "0.4")
    )
    wire = observed[0]
    assert (
        wire["response_format"]["json_schema"]["schema"]["properties"]["visual_realism"]["maximum"]
        == 25
    )
    assert "only" not in wire["provider"] and "ignore" not in wire["provider"]


def test_uncertain_review_post_is_never_automatically_repeated(monkeypatch):
    provider = OpenRouter("synthetic-key", "http://127.0.0.1:4999")
    calls = []

    def timeout(*args, **kwargs):
        calls.append(args)
        raise requests.ReadTimeout("synthetic timeout")

    monkeypatch.setattr(provider.session, "request", timeout)
    with pytest.raises(ProviderError, match="do not repeat"):
        provider.chat(
            "google/gemini-3.1-flash-lite", [], PracticalReview.model_json_schema(), ("0.25", "1.5")
        )
    assert len(calls) == 1


def test_only_large_inline_video_gets_a_bounded_send_budget():
    provider = OpenRouter("synthetic-key", timeout=(10, 300))
    assert provider.request_timeout(None) == (10, 300)
    for content in ("text", [{"type": "text", "text": "A" * 1048576}]):
        assert provider.request_timeout({"messages": [{"content": content}]}) == (10, 300)
    for url in ("https://example.invalid/video.mp4", "data:video/mp4;base64,AAAA"):
        body = {"messages": [{"content": [{"type": "video_url", "video_url": {"url": url}}]}]}
        assert provider.request_timeout(body) == (10, 300)
    large = {
        "messages": [
            {
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": "data:video/mp4;base64," + "A" * 1048576},
                    }
                ]
            }
        ]
    }
    assert provider.request_timeout(large) == (120, 300)
    assert provider.timeout == (10, 300)


def test_large_review_upload_survives_a_slow_receiver_without_retry():
    events = []

    class Receiver(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            time.sleep(0.15)
            size = int(self.headers["Content-Length"])
            received = self.rfile.read(size)
            complete = len(received) == size
            events.append(complete)
            body = json.dumps({"received": len(received), "complete": complete}).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    provider = OpenRouter(
        "synthetic-key", f"http://127.0.0.1:{server.server_port}", timeout=(0.02, 3)
    )
    body = {
        "messages": [
            {
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": "data:video/mp4;base64," + "A" * (16 * 1024 * 1024)},
                    }
                ]
            }
        ]
    }
    try:
        with pytest.raises(requests.RequestException):
            provider.session.post(provider.base + "/baseline", json=body, timeout=(0.02, 3))
        result = provider.json("POST", "/chat/completions", body)
        assert result["complete"]
        assert sum(events) == 1
        assert len(events) == 2
    finally:
        provider.session.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
