import pytest
from pydantic import ValidationError

from tsu.contracts import PracticalReview, ReviewIssue


def review(**changes):
    return PracticalReview(
        **{
            **dict(
                visual_realism=22,
                motion_quality=16,
                aesthetic_quality=17,
                prompt_compliance=17,
                technical_quality=10,
                technical_pass=True,
                audio_coherence="coherent",
            ),
            **changes,
        }
    )


def issue(**changes):
    return ReviewIssue(
        **{
            **dict(
                start_seconds=7.8,
                end_seconds=8.2,
                severity="minor",
                visibility="normal_playback",
                remedy="local_edit",
                description="Légère variation du reflet",
                evidence="Le reflet change légèrement de position au raccord.",
            ),
            **changes,
        }
    )


def decision(value, **changes):
    return value.decision(**{**dict(technical_pass=True, duration_seconds=15.8), **changes})


def test_minor_visible_defect_does_not_veto_82_points():
    value = review(issues=[issue()])
    assert value.total == 82 and decision(value) == "accepted" and value.approved


def test_defect_only_seen_under_inspection_is_tolerated():
    assert decision(review(issues=[issue(severity="major", visibility="inspection_only")])) == (
        "accepted"
    )


def test_visible_major_join_routes_to_local_edit_not_new_generation():
    assert decision(review(issues=[issue(severity="major")])) == "local_edit"


@pytest.mark.parametrize(
    "changes",
    [
        {"issues": [issue(severity="major", remedy="manual_review")]},
        {"issues": [issue(visibility="uncertain")]},
        {"issues": [issue(end_seconds=18)]},
        {"technical_pass": False},
        {"severe_defects": ["Unsupported subjective physics claim without timed evidence"]},
        {"audio_coherence": "not_observable"},
        {"audio_coherence": "problem"},
        {"motion_quality": 13},
    ],
)
def test_uncertain_unproven_or_low_score_requires_manual_review(changes):
    assert decision(review(**changes)) == "manual_review"


def test_actual_technical_failure_still_blocks():
    assert decision(review(), technical_pass=False) == "technical_failed"


def test_invalid_issue_evidence_is_rejected():
    with pytest.raises(ValidationError):
        issue(start_seconds=9, end_seconds=8)
    with pytest.raises(ValidationError):
        issue(evidence="bad")
