"""One provider output with native audio; publication media is never edited."""

import hashlib
import json
import shutil
from decimal import Decimal

from pydantic import Field
from sqlalchemy import select

from tsu.budget import BudgetBlocked
from tsu.media import inspect_final
from tsu.models import Concept, ProductionJob
from tsu.native_profile import (
    MAX_GENERATION_USD,
    MODEL,
    SECONDS,
    generation_parameters,
    native_profile,
)
from tsu.openrouter import usd
from tsu.pilot import MODELS
from tsu.workflow import JobProducer, ProductionBrief


class NativeProductionBrief(ProductionBrief):
    prompts: list[str] = Field(min_length=1, max_length=1)
    sound_plan: None = None


class NativeJobProducer(JobProducer):
    brief_schema = NativeProductionBrief
    expected_models = {**MODELS, "video_model": MODEL}

    def __init__(self, settings, engine, provider, job_id, interval=20, polls=60):
        super().__init__(settings, engine, provider, job_id, interval=interval, polls=polls)
        with self.sessions() as db:
            profile = db.get(ProductionJob, job_id).payload.get("production_profile", {})
        self.seconds = (
            profile.get("duration_seconds") if isinstance(profile, dict) else None
        ) or SECONDS
        self.max_generation_usd = (
            profile.get("maximum_generation_usd") if isinstance(profile, dict) else None
        ) or MAX_GENERATION_USD

    def generation_parameters(self):
        return generation_parameters(self.seconds)

    def verify_catalogue(self):
        self.provider.verify_key()
        videos, models = self.provider.catalogues()
        video = videos.get(MODEL, {})
        if not (
            self.seconds in video.get("supported_durations", [])
            and "1080p" in video.get("supported_resolutions", [])
            and "9:16" in video.get("supported_aspect_ratios", [])
            and video.get("generate_audio") is True
            and not video.get("expiration_date")
        ):
            raise RuntimeError("The single-generation native-audio plan is unavailable")
        price = video.get("pricing_skus", {}).get("duration_seconds_with_audio")
        if price is None:
            raise RuntimeError("No verified 1080p native-audio price; stop before spending")
        self.clip_quote = usd(price) * self.seconds
        if not 0 < self.clip_quote <= Decimal(self.max_generation_usd):
            raise RuntimeError("Native generation price exceeds its reviewed ceiling")
        self.verify_text_catalogue(models)

    def prepare(self):
        if (
            not self.settings.spending_authorized
            or min(self.settings.daily_budget_usd, self.settings.monthly_budget_usd) <= 0
        ):
            raise BudgetBlocked("Owner spending authorization and positive budgets are required")
        if (self.directory / "operator-brief.json").exists():
            raise RuntimeError("Native jobs require their own captured structured brief")
        self.verify_catalogue()
        with self.sessions.begin() as db:
            job = self.job(db)
            recent = list(
                db.scalars(select(Concept.name).order_by(Concept.created_at.desc()).limit(20))
            )
            self.creative_instruction = job.payload.get("creative_instruction") or (
                "NATIVE_SINGLE_GENERATION: Create one original TechnoInno satisfying macro video. "
                "Theme: "
                + self.theme
                + ". Avoid recent concepts: "
                + json.dumps(recent, ensure_ascii=False)
                + ". "
                f"Exactly ONE continuous {self.seconds}-second 9:16 1080p scene generated in a "
                "single request, "
                "including synchronized native AI-generated environmental sound. Write exactly one "
                "detailed English video prompt describing both the visuals and coherent "
                "action sounds. "
                "Simple realistic physics, fixed macro camera, gentle light, action in the "
                "first second, "
                "natural ending. No cuts, transitions, assembly, music, speech, text, logos "
                "or watermarks. "
                "Specify audible material-appropriate sounds, e.g. individual water drops on "
                "impact or "
                "continuous flowing water; do not request a generic repeating sound bed. No "
                "people. "
                "Set sound_plan to null. No separate soundtrack or later editing is permitted. "
                "Write natural titles/descriptions in en, fr, es, it, ru and zh-CN; English "
                "base fields "
                "must exactly match en. Keep TechnoInno and disclose AI-generated video AND "
                "audio in "
                "every description. Use a concise accurate title with the main subject early, and "
                "1-2 subject keywords in each title/first description line. Supply 1-2 "
                "relevant subject "
                "hashtags in hashtags; no #viral/#fyp and no hashtags inside the prose. No "
                "invented "
                "claims. Return only the strict JSON object."
            )
            job.payload = {
                **job.payload,
                "creative_instruction": self.creative_instruction,
                "production_profile": native_profile(),
                "quoted_generation_usd": str(self.clip_quote),
            }

    def inspect_master(self, final):
        return inspect_final(final, require_audio=True, native_seconds=self.seconds)

    def render(self, clips, final, brief):
        if len(clips) != 1:
            raise RuntimeError("Native output requires exactly one source; assembly is prohibited")
        source = clips[0]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copyfile(source, final)
        if hashlib.sha256(final.read_bytes()).hexdigest() != digest:
            raise RuntimeError("The native master must match the provider download exactly")
        return {**native_profile(), "source_sha256": digest, "master_sha256": digest}

    def final_decision(self, decision):
        return "manual_review" if decision == "local_edit" else decision
