# Single-generation native AI audio — current policy

Owner decisions, 2026-11-05: discard the turquoise-basin test, never upload it;
all future media must contain native AI-generated audio with no subsequent montage.
The owner selected 15–20 seconds in one generation. The implemented default is one
continuous 15-second 1080x1920 scene, environmental sounds appropriate to the action,
no music or speech by default. Six-language metadata and relevant hashtags remain.

## Model and price evidence

The public OpenRouter catalogue read on 2026-11-05 advertises
`google/gemini-omni-1.2-flash` with 15-second, 1080p, 9:16 native audio support.
Its `duration_seconds_with_audio` SKU is 0.104256 USD/second: 1.563840 USD/15 seconds.
This is a currently catalogued economical compatible candidate, not a claim of proven
subjective quality or an exhaustive lowest-price guarantee for variable-token models.

A fresh free catalogue check precedes spending. Missing duration/resolution/audio
support, an unknown applicable SKU, a retirement notice or a quote above 1.60 USD
blocks the plan. No automatic fallback to shorter clips, assembly, silence or another
model. Text preparation reserves up to 0.01 USD and quality review up to 0.05 USD.
The catalogue quote plus those stages is 1.623840 USD; the hard generation ceiling
plus those allowances is 1.66 USD. These limits are technical guards, not owner spend
permission. Earlier 1 USD trial permissions are consumed and do not cover this model.
No real generation with this model has been authorized or performed during setup.

Sources: https://openrouter.ai/api/v1/videos/models and
https://openrouter.ai/docs/guides/overview/multimodal/video-generation . Saved evidence:
`docs/evidence/native-audio-model-catalogue-2026-11-05.json`.
Postman Orbit discovery and integration results are saved beside it. The integration
brief was partial because its three selected resources omitted polling; the existing
known-ID GET poll/download implementation and official guide supply that part.

## Caller guarantees and boundaries

New reusable jobs capture `native_audio_v4`. Their structured brief has exactly one
prompt and no separate SoundPlan. A single paid video POST requests duration=15,
resolution=1080p, aspect_ratio=9:16, generate_audio=true, without continuity images.
Durable paid intents, known-ID polling, uncertain reservations and budget locks stay
in force. Ambiguous submissions are not repeated automatically.

The downloaded source is copied byte-for-byte as the publication master. No joining,
trim, normalization, fade, soundtrack insertion or re-encoding of that master occurs.
The original SHA-256 is recorded on VideoGeneration; publication rejects a changed
master or a mismatch with the approved video. A separate smaller analysis copy is
made for the quality model; it is never the publication file.

Read-only technical inspection requires a decodable MP4/H.264/yuv420p portrait master,
24–60 native fps, one audible AAC track, 15 seconds within 0.2 seconds and overall
15–20 seconds, with audio/video durations aligned. An unsupported output stops rather
than being converted. These are application acceptance limits, not provider guarantees.

Quality remains tolerant: score >=80, small imperfections accepted. Clearly visible
major defects, low score, unobservable/mismatched audio or uncertainty require human
review. A local_edit verdict is mapped to manual_review; no edit or paid retry follows.
The real model may still produce unsuitable sound; simulation cannot prove quality.

Historical completed uploads and captured profiles are preserved. The discarded test
job 8db44bfd-f1b1-4433-a6ab-f4be088fc6da is cancelled, never_publish and owner_discarded;
its private upload consent is withdrawn. Workflow, supervised trial and uploader guards
prevent revival/publication. Its files are retained only for accounting/test history.
Costs and uncertain holds are never erased by cancellation.

## Verification and launch

The existing local Postman production stand-in now returns a synthetic 15-second
24-fps AAC fixture. It is only a test asset, not a real AI sample or user output.
Real caller/PostgreSQL/FFmpeg tests verify one POST, exact source/master identity,
unchanged native frame rate, private six-language metadata and hashtags, price and
capability rejection before paid POSTs, silent output rejection, minor acceptance,
major-defect manual review, replay, post-generation tampering and cancellation guards.
See `docs/evidence/native-audio-final-tests-2026-11-05.xml` and tests/test_workflow.py.

Scheduling, global spending/publication flags and caps remain off/zero. The replacement
live cycle is unvalidated. A future private sample requires a fresh explicit budget.
Recurring times/budgets/publication, real alert delivery and an always-available offhost
backup destination still need completion before automatic production.

Installed verification: docs/evidence/native-audio-installed-2026-11-05.json and
studio-native-audio-2026-11-05.png confirm matching source hashes, the displayed policy,
the cancelled-job provider guard, 3 jobs/6 generations/2 publications/18 usages,
2.402445 USD cumulative actual and 0.30 USD held, with no new paid requests/uploads.
157 tests passed without skips. The real native-model output remains untested.
