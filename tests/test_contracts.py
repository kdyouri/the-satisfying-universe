import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tsu.contracts import ClipRequest, QualityScores, VideoCapability


def test_technical_and_severe_defects_veto_high_score():
    score = QualityScores(
        visual_realism=25,
        motion_quality=20,
        aesthetic_quality=20,
        prompt_compliance=20,
        technical_quality=15,
        technical_pass=False,
    )
    assert score.total == 100
    assert not score.approved
    score.technical_pass = True
    score.severe_defects = ["persistent morphing"]
    assert not score.approved


def test_threshold_boundary():
    score = QualityScores(
        visual_realism=20,
        motion_quality=15,
        aesthetic_quality=15,
        prompt_compliance=15,
        technical_quality=15,
        technical_pass=True,
    )
    assert score.total == 80
    assert score.approved
    score.motion_quality = 14
    assert not score.approved
    with pytest.raises(ValidationError):
        QualityScores(**{**score.model_dump(), "visual_realism": 30})


def test_live_snapshot_rejects_marketing_duration_and_unsupported_resolution():
    path = (
        Path(__file__).resolve().parents[1]
        / "docs/evidence/openrouter-video-models-2026-11-04.json"
    )
    capabilities = {
        m["id"]: VideoCapability.model_validate(m) for m in json.loads(path.read_text())["data"]
    }
    request = ClipRequest(
        model="alibaba/wan-2.6",
        prompt="Macro liquid with natural gentle motion",
        duration=15,
        resolution="1080p",
    )
    with pytest.raises(ValueError, match="duration"):
        capabilities[request.model].validate_request(request)
    request.duration = 10
    capabilities[request.model].validate_request(request)
    request.resolution = "480p"
    with pytest.raises(ValueError, match="resolution"):
        capabilities[request.model].validate_request(request)
