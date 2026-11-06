"""Manual first-video runner; never starts workers, a scheduler or a publisher."""

import argparse
import base64
import hashlib
import json
import subprocess
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import Field
from sqlalchemy import select, text

from tsu.budget import reserve, settle
from tsu.config import Settings
from tsu.contracts import PracticalReview, StrictModel
from tsu.db import make_engine, make_sessions
from tsu.jobs import create_job
from tsu.media import inspect_final
from tsu.models import (
    Concept,
    ModelUsage,
    ProductionJob,
    Prompt,
    QualityCheck,
    Video,
    VideoGeneration,
)
from tsu.openrouter import OpenRouter, ProviderError, ProviderTerminalError, usd
from tsu.production import production_profile, render_final, review_instruction, review_proxy

KEY = "owner:first-video:v1"
MODELS = {
    "creative_model": "google/gemma-4-26b-a4b-it",
    "quality_model": "google/gemini-3.1-flash-lite",
    "video_model": "google/veo-3.1-lite",
}
CREATIVE = """Create the first TechnoInno satisfying macro video: golden viscous liquid
forming a slow spiral in a matte black ceramic bowl. Original, physically plausible,
warm studio lighting, fixed macro camera, no people, no hands, no text, no logos.
Two complementary 8-second shots, 9:16 portrait. Shot 2 starts from a frame of shot 1;
maintain the same bowl, liquid, camera and lighting. End with calm settling motion.
Write concept, title, description in French, hashtags without invented brand claims,
and exactly two detailed English video prompts. Generate silent source clips;
the final montage adds a quiet original ambient soundtrack. Do not describe it as silent.
Prefer a simple believable movement to a complicated spectacular transformation.
Return only the requested JSON object."""


class PilotBrief(StrictModel):
    concept: str = Field(min_length=3, max_length=300)
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    hashtags: list[str] = Field(max_length=12)
    prompts: list[str] = Field(min_length=2, max_length=2)


def now():
    return datetime.now(UTC)


def ffmpeg(*arguments):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, arguments)],
        check=True,
        capture_output=True,
        timeout=240,
    )


@contextmanager
def first_video_lock(engine):
    if engine.dialect.name != "postgresql":
        raise RuntimeError("The manual paid runner requires PostgreSQL")
    with engine.connect() as connection:
        acquired = connection.scalar(text("SELECT pg_try_advisory_lock(865190041)"))
        if not acquired:
            raise RuntimeError("The first-video run is already active")
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(865190041)"))


class FirstVideo:
    key = KEY
    models = MODELS
    creative_instruction = CREATIVE
    brief_schema = PilotBrief
    price_limits = {"creative_model": ("0.027", "0.08"), "quality_model": ("0.25", "1.50")}
    chat_tokens = 1200

    def __init__(self, settings, engine, provider, directory=None, interval=20, polls=60):
        if settings.enable_daily_scheduler or settings.publishing_authorized:
            raise RuntimeError("Keep scheduling and publishing disabled for the first video")
        if any(getattr(settings, field) != model for field, model in self.models.items()):
            raise RuntimeError("This first-video plan is limited to the quoted economic models")
        self.settings = settings.model_copy(
            update={
                "spending_authorized": True,
                "daily_budget_usd": Decimal("1"),
                "monthly_budget_usd": Decimal("1"),
            }
        )
        self.engine, self.sessions, self.provider = engine, make_sessions(engine), provider
        self.directory = directory or settings.data_root / "pilot/first-video"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.interval, self.polls = interval, polls

    def job(self, session, locked=False):
        query = select(ProductionJob).where(ProductionJob.idempotency_key == self.key)
        return session.scalar(query.with_for_update() if locked else query)

    def verify_catalogue(self):
        if not production_profile()["audio_ready"]:
            raise RuntimeError("Soundtrack missing; stop before any paid submission")
        self.provider.verify_key()
        videos, models = self.provider.catalogues()
        video = videos[self.models["video_model"]]
        if not (
            8 in video["supported_durations"]
            and "1080p" in video["supported_resolutions"]
            and "9:16" in video["supported_aspect_ratios"]
            and video["generate_audio"] is True
            and "first_frame" in video["supported_frame_images"]
        ):
            raise RuntimeError("The provider no longer supports the quoted video plan")
        self.clip_quote = usd(video["pricing_skus"]["duration_seconds_without_audio"]) * 8
        if self.clip_quote > Decimal("0.40"):
            raise RuntimeError("The video price increased; stop before spending")
        self.verify_text_catalogue(models)

    def verify_text_catalogue(self, models):
        for role, limits in self.price_limits.items():
            if role == "creative_model" and (self.directory / "operator-brief.json").exists():
                # No creative-model API request is made for an operator-prepared brief.
                continue
            model = models[self.models[role]]
            if model.get("expiration_date"):
                raise RuntimeError("Selected model has a retirement notice; review before spending")
            if "structured_outputs" not in model.get("supported_parameters", []):
                raise RuntimeError("Selected model no longer advertises structured outputs")
            if role == "quality_model" and "video" not in model["architecture"]["input_modalities"]:
                raise RuntimeError("The review model no longer supports video input")
            if any(
                Decimal(model["pricing"][field]) * 1000000 > Decimal(limit)
                for field, limit in zip(("prompt", "completion"), limits, strict=True)
            ):
                raise RuntimeError("Selected text model price increased; stop before spending")

    def prepare(self):
        self.verify_catalogue()
        quote = {
            "scope": "One first video requested by the owner; not recurring production",
            "owner_request": (
                "Peut-on produire notre première vidéo maintenant ? "
                "On laisse la production programmée désactivée pour l'instant."
            ),
            "limit_usd": "1.00",
            "generation_quote_usd": str(self.clip_quote * 2),
            "models": self.models,
            "resolution": "1080p",
            "aspect_ratio": "9:16",
            "clip_seconds": 8,
            "clip_count": 2,
            "generate_audio": False,
            "production_profile": production_profile(),
            "automatic_regeneration": False,
            "publish": False,
            "scheduler_enabled": False,
        }
        with self.sessions.begin() as session:
            job, _ = create_job(session, self.key, quote)
            self.job_id = job.id
            if job.status == "queued":
                job.status = "manual_pilot"
        (self.directory / "plan.json").write_text(json.dumps(quote, indent=2) + "\n")
        print("Plan checked: one 16-second video, two clips, <= 1 USD, no publication.", flush=True)

    def chat(self, stage, content, schema, allowance, model, prices):
        request_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
        operation = f"{self.key}:{stage}"
        with self.sessions.begin() as session:
            job = self.job(session, locked=True)
            previous = job.payload.get("calls", {}).get(stage)
            if previous:
                if previous["state"] != "done" or previous["input_hash"] != request_hash:
                    raise ProviderError(
                        "A previous paid chat is uncertain or its input changed; do not repeat"
                    )
                return previous["content"]
            reserve(session, self.settings, operation, model, stage, Decimal(allowance), now())
            job.payload = {
                **job.payload,
                "calls": {
                    **job.payload.get("calls", {}),
                    stage: {
                        "state": "submitting",
                        "input_hash": request_hash,
                    },
                },
            }
        result = self.provider.chat(model, content, schema, prices, max_tokens=self.chat_tokens)
        with self.sessions.begin() as session:
            job = self.job(session, locked=True)
            settle(session, operation, result.cost, result.request_id, now())
            job.payload = {
                **job.payload,
                "calls": {
                    **job.payload["calls"],
                    stage: {
                        "state": "done",
                        "input_hash": request_hash,
                        "content": result.content,
                        "cost_usd": str(result.cost),
                        "request_id": result.request_id,
                    },
                },
            }
        if result.cost > Decimal(allowance):
            raise ProviderError("Provider cost exceeded its reservation; spending frozen")
        return result.content

    def creative(self):
        operator_brief = self.directory / "operator-brief.json"
        if operator_brief.exists():
            # Explicit local operator preparation for this supervised first sample.
            # Preserve any earlier uncertain paid call and its reservation verbatim.
            raw = operator_brief.read_text()
            source = "operator-prepared; no replacement creative API call"
        else:
            raw = self.chat(
                "creative",
                [{"type": "text", "text": self.creative_instruction}],
                self.brief_schema.model_json_schema(),
                "0.01",
                self.models["creative_model"],
                self.price_limits["creative_model"],
            )
            source = self.models["creative_model"]
        brief = self.brief_schema.model_validate_json(raw)
        if any(len(prompt) < 30 or len(prompt) > 12000 for prompt in brief.prompts):
            raise RuntimeError("Creative prompt does not satisfy the plan")
        with self.sessions.begin() as session:
            job = self.job(session)
            job.payload = {**job.payload, "brief_source": source}
            if not job.concept_id:
                concept = Concept(
                    name=brief.concept,
                    category="liquid macro",
                    fingerprint=self.concept_fingerprint(brief),
                    brief=brief.model_dump(by_alias=True),
                )
                session.add(concept)
                session.flush()
                job.concept_id = concept.id
                for index, prompt_text in enumerate(brief.prompts):
                    prompt = Prompt(concept_id=concept.id, version=index + 1, text=prompt_text)
                    session.add(prompt)
                    session.flush()
                    session.add(
                        VideoGeneration(
                            concept_id=concept.id,
                            prompt_id=prompt.id,
                            job_id=job.id,
                            attempt=1,
                            clip_index=index,
                            provider="openrouter",
                            model=self.models["video_model"],
                            parameters=self.generation_parameters(),
                            status="planned",
                        )
                    )
        (self.directory / "brief.json").write_text(
            brief.model_dump_json(indent=2, by_alias=True) + "\n"
        )
        return brief

    def concept_fingerprint(self, brief):
        return hashlib.sha256(self.key.encode()).hexdigest()

    def generation(self, session, index, locked=False):
        query = select(VideoGeneration).where(
            VideoGeneration.job_id == self.job_id,
            VideoGeneration.clip_index == index,
        )
        return session.scalar(query.with_for_update() if locked else query)

    def clip(self, index, prompt):
        operation = f"{self.key}:clip:{index}"
        destination = self.directory / f"clip-{index + 1}.mp4"
        with self.sessions.begin() as session:
            generation = self.generation(session, index, locked=True)
            remote_id = generation.remote_job_id
            if generation.status == "submitting" and not remote_id:
                raise ProviderError(
                    "An earlier video submission is ambiguous; do not submit it again"
                )
            if not remote_id:
                reserve(
                    session,
                    self.settings,
                    operation,
                    self.models["video_model"],
                    "video",
                    self.clip_quote,
                    now(),
                )
                generation.status = "submitting"
        if not remote_id:
            body = {
                "model": self.models["video_model"],
                "prompt": prompt,
                **self.generation_parameters(),
            }
            if index:
                frame = self.directory / "continuity.jpg"
                ffmpeg(
                    "-sseof",
                    "-0.1",
                    "-i",
                    self.directory / "clip-1.mp4",
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    frame,
                )
                body["frame_images"] = [
                    {
                        "type": "image_url",
                        "frame_type": "first_frame",
                        "image_url": {
                            "url": "data:image/jpeg;base64,"
                            + base64.b64encode(frame.read_bytes()).decode()
                        },
                    }
                ]
            remote_id = self.provider.submit(body)
            with self.sessions.begin() as session:
                generation = self.generation(session, index, locked=True)
                generation.remote_job_id, generation.status = remote_id, "pending"
        for _ in range(self.polls):
            try:
                result = self.provider.poll(remote_id)
            except ProviderTerminalError:
                # A definitive provider failure is terminal; do not poll or retry.
                raise
            except ProviderError:
                # GET is safe to retry; the known paid POST is never repeated.
                time.sleep(self.interval)
                continue
            status = result.get("status")
            print(f"Clip {index + 1}: {status}", flush=True)
            if status in ("completed", "failed", "cancelled", "expired"):
                if result.get("usage", {}).get("cost") is None:
                    raise ProviderError("Terminal video has no cost evidence; retain reservation")
                cost = usd(result["usage"]["cost"])
                with self.sessions.begin() as session:
                    generation = self.generation(session, index, locked=True)
                    settle(
                        session, operation, cost, result.get("generation_id") or remote_id, now()
                    )
                    generation.status, generation.cost_usd = status, cost
                if cost > self.clip_quote:
                    raise ProviderError("Video cost exceeded its reservation; spending frozen")
                if status != "completed":
                    raise ProviderError("Video generation terminated without a finished clip")
                break
            if status not in ("pending", "in_progress"):
                raise ProviderError("Unknown provider status; retain the known job")
            time.sleep(self.interval)
        else:
            raise ProviderError("Polling deadline reached; resume the known job, do not resubmit")
        if not destination.exists():
            self.provider.download(remote_id, destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        with self.sessions.begin() as session:
            generation = self.generation(session, index, locked=True)
            old_hash = generation.parameters.get("sha256")
            if old_hash and old_hash != digest:
                raise RuntimeError("Downloaded clip changed; review before continuing")
            generation.parameters = {
                **generation.parameters,
                "sha256": digest,
                "local_key": str(destination),
            }
        return destination

    def run(self):
        with first_video_lock(self.engine):
            # Completed legacy samples are immutable and never rerendered/rebilled by resume.
            with self.sessions() as session:
                saved = self.job(session)
                if saved and (
                    saved.status == "cancelled"
                    or saved.payload.get("owner_discarded")
                    or saved.payload.get("never_publish")
                ):
                    raise RuntimeError("The owner discarded this video; execution is prohibited")
                existing = saved.payload.get("result") if saved else None
                if existing and Path(existing["file"]).exists():
                    self.job_id = saved.id
                    return existing
                if saved and "production_profile" not in saved.payload:
                    raise RuntimeError("Unfinished legacy job requires explicit operator migration")
            self.prepare()
            brief = self.creative()
            clips = [self.clip(index, prompt) for index, prompt in enumerate(brief.prompts)]
            final = self.directory / "first-video.mp4"
            editing = self.render(clips, final, brief)
            technical = self.inspect_master(final)
            if not technical["technical_pass"]:
                raise RuntimeError("The first video failed technical inspection")
            digest = hashlib.sha256(final.read_bytes()).hexdigest()
            self.validate_final(digest)
            # Bound the multimodal request size while preserving the native 1080p master.
            review = self.directory / "review.mp4"
            review_proxy(final, review)
            review_prompt = review_instruction(
                brief.concept, editing["duration_seconds"], editing.get("audio_mode")
            )
            raw = self.chat(
                "quality_" + editing["version"],
                [
                    {"type": "text", "text": review_prompt},
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": "data:video/mp4;base64,"
                            + base64.b64encode(review.read_bytes()).decode()
                        },
                    },
                ],
                PracticalReview.model_json_schema(),
                "0.05",
                self.models["quality_model"],
                self.price_limits["quality_model"],
            )
            quality = PracticalReview.model_validate_json(raw)
            decision = quality.decision(
                technical_pass=technical["technical_pass"],
                duration_seconds=editing["duration_seconds"],
            )
            decision = self.final_decision(decision)
            approved = decision == "accepted"
            with self.sessions.begin() as session:
                job = self.job(session)
                generation = self.generation(session, 0)
                video = session.scalar(select(Video).where(Video.generation_id == generation.id))
                if video is None:
                    video = Video(
                        concept_id=job.concept_id,
                        generation_id=generation.id,
                        original_key=str(clips[0]),
                        final_key=str(final),
                        sha256=digest,
                        technical_metadata={
                            **technical,
                            "source_clips": list(map(str, clips)),
                            "editing": editing,
                        },
                        status="awaiting_owner_review",
                    )
                    session.add(video)
                    session.flush()
                    session.add(
                        QualityCheck(
                            video_id=video.id,
                            model=self.models["quality_model"],
                            score=quality.total,
                            technical_pass=True,
                            approved=approved,
                            details=quality.model_dump(),
                            rejection_reason=None if approved else decision,
                        )
                    )
                charges = session.scalars(
                    select(ModelUsage).where(ModelUsage.operation_key.startswith(self.key + ":"))
                ).all()
                result = {
                    "job_id": job.id,
                    "video_id": video.id,
                    "file": str(final),
                    "title": brief.title,
                    "sha256": digest,
                    "technical_pass": True,
                    "quality_score": quality.total,
                    "quality_pass": approved,
                    "quality_decision": decision,
                    "production_profile": editing,
                    "issues": [issue.model_dump() for issue in quality.issues],
                    "severe_defects": quality.severe_defects,
                    "actual_cost_usd": str(sum(c.actual_usd or Decimal(0) for c in charges)),
                    "unsettled_reservations": sum(c.actual_usd is None for c in charges),
                    "published": False,
                    "scheduler_enabled": False,
                    "automatic_regeneration": False,
                }
                job.payload = {**job.payload, "result": result}
                job.status = self.completion_status(decision)
                video.status = job.status
            (self.directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            return result

    def render(self, clips, final, brief):
        return render_final(clips, final)

    def generation_parameters(self):
        return {
            "duration": 8,
            "resolution": "1080p",
            "aspect_ratio": "9:16",
            "generate_audio": False,
        }

    def inspect_master(self, final):
        return inspect_final(final, require_audio=True)

    def final_decision(self, decision):
        return decision

    def completion_status(self, decision):
        return (
            "awaiting_local_edit"
            if decision == "local_edit"
            else "rejected"
            if decision == "technical_failed"
            else "awaiting_owner_review"
        )

    def validate_final(self, digest):
        """Legacy samples keep their original behavior; reusable jobs add deduplication."""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-first-video", action="store_true", required=True)
    args = parser.parse_args()
    assert args.run_first_video
    settings = Settings()
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        runner = FirstVideo(
            settings, engine, OpenRouter(settings.openrouter_api_key.get_secret_value())
        )
        result = runner.run()
        print(json.dumps(result, indent=2), flush=True)
    except Exception as error:
        # Do not print upstream bodies, signed URLs, media data or request headers.
        safe_reason = str(error) if isinstance(error, ProviderError) else type(error).__name__
        with make_sessions(engine).begin() as session:
            job = session.scalar(select(ProductionJob).where(ProductionJob.idempotency_key == KEY))
            if job and job.status not in ("awaiting_owner_review", "rejected"):
                job.status = "owner_attention"
                job.payload = {**job.payload, "safe_error": safe_reason}
        print(
            json.dumps(
                {
                    "stopped": True,
                    "safe_error_type": type(error).__name__,
                    "safe_reason": safe_reason,
                    "action": "Inspect saved state before repeating any paid submission",
                }
            ),
            flush=True,
        )
        raise SystemExit(1) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
