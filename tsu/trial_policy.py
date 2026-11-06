"""Fixed one-video scope, separate from global recurring authorization."""

import hashlib

from tsu.native_profile import is_native

NATIVE_KEY = "owner:native-audio-private-trial:v1"
NATIVE_LIMIT = "1.70"
NATIVE_THEME = (
    "Individual clear water droplets fall slowly into a shallow dark-blue ceramic dish. "
    "One continuous fixed macro view with simple realistic ripples and soft studio light. "
    "Generate synchronized subtle water-drop sounds natively with the video; no music, "
    "speech, people, cuts or transitions."
)
NATIVE_DURABLE_KEY = "production:" + hashlib.sha256(NATIVE_KEY.encode()).hexdigest()

NATIVE2_KEY = "owner:native-audio-private-trial:v2"
NATIVE2_LIMIT = "2.00"
NATIVE2_THEME = (
    "One NEW original satisfying macro subject chosen freely by the creative model, "
    "avoiding every recently used concept. One continuous fixed macro view with simple "
    "realistic physics and soft studio light. Generate synchronized material-appropriate "
    "environmental sounds natively with the video; no music, speech, people, cuts or "
    "transitions."
)
NATIVE2_DURABLE_KEY = "production:" + hashlib.sha256(NATIVE2_KEY.encode()).hexdigest()

NATIVE3_KEY = "owner:native-audio-private-trial:v3"
NATIVE3_LIMIT = "1.00"
NATIVE3_THEME = NATIVE2_THEME
NATIVE3_DURABLE_KEY = "production:" + hashlib.sha256(NATIVE3_KEY.encode()).hexdigest()
NATIVE_LIMITS = {
    NATIVE_DURABLE_KEY: NATIVE_LIMIT,
    NATIVE2_DURABLE_KEY: NATIVE2_LIMIT,
    NATIVE3_DURABLE_KEY: NATIVE3_LIMIT,
}


def private_trial_authorized(job, target, channel_id):
    grant = job.payload.get("private_trial_authorization", {})
    native = is_native(job.payload.get("production_profile"))
    common = (
        target == "private"
        and job.payload.get("visibility") == "private"
        and not job.payload.get("owner_discarded")
        and not job.payload.get("never_publish")
        and job.status != "cancelled"
        and grant.get("job_id") == job.id
        and grant.get("channel_id") == channel_id
        and grant.get("confirmed") is True
        and not grant.get("withdrawn_by_owner")
    )
    if not common:
        return False
    if not native:
        return grant.get("maximum_usd") == "1.00"
    expected = NATIVE_LIMITS.get(job.idempotency_key)
    return expected is not None and grant.get("maximum_usd") == expected
