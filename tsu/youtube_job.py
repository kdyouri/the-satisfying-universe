"""Job-scoped upload/publication of approved media, using the tested resumable engine."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from sqlalchemy import select

from tsu.media import inspect_final
from tsu.models import (
    Concept,
    ProductionJob,
    Publication,
    QualityCheck,
    SocialAccount,
    SystemSetting,
    Video,
    VideoGeneration,
    utcnow,
)
from tsu.native_profile import SECONDS, is_native
from tsu.trial_policy import private_trial_authorized
from tsu.workflow import VERSION, ProductionBrief
from tsu.youtube_auth import YOUTUBE_EDIT_SCOPE
from tsu.youtube_metadata import discovery_metadata
from tsu.youtube_upload import PrivateTestUpload, UploadError, upload_lock


class YouTubeJob(PrivateTestUpload):
    def __init__(self, settings, engine, job_id, result, http=None):
        super().__init__(settings, engine, http=http)
        self.job_id, self.video_id = job_id, result["video_id"]
        self.operation_key = "youtube:job:" + job_id
        self.public_operation_key = "youtube:public:job:" + job_id
        self.asset_label = "approved_production_video"
        with self.sessions() as db:
            job = db.get(ProductionJob, job_id)
            video = db.get(Video, self.video_id)
            if not job or job.payload.get("workflow_version") != VERSION or not video:
                raise UploadError("Unknown production job/video")
            if video.concept_id != job.concept_id or video.sha256 != result["sha256"]:
                raise UploadError("The approved video does not belong to this production job")
            self.native = is_native(job.payload.get("production_profile"))
            self.native_seconds = None
            if self.native:
                profile = job.payload.get("production_profile", {})
                self.native_seconds = (
                    profile.get("duration_seconds") if isinstance(profile, dict) else None
                ) or SECONDS
            from tsu.native_production import NativeProductionBrief

            schema = NativeProductionBrief if self.native else ProductionBrief
            brief = schema.model_validate(db.get(Concept, video.concept_id).brief)
            self.brief = brief
            self.source_job_key = job.idempotency_key
            self.target = job.payload["visibility"]
            self.asset = Path(video.final_key)
            if not self.asset.resolve().is_relative_to(
                (settings.data_root / "jobs" / job_id).resolve()
            ):
                raise UploadError("Production media is outside its job directory")
            self.metadata = {
                **discovery_metadata(
                    brief.localizations.model_dump(by_alias=True),
                    brief.hashtags,
                    tags=["TechnoInno", "satisfying", "shorts"],
                ),
                "status": {
                    "privacyStatus": "private",
                    "selfDeclaredMadeForKids": False,
                    "containsSyntheticMedia": True,
                },
            }
            state = db.get(SystemSetting, self.operation_key)
            if state:
                # Saved upload metadata is part of its durable intent. A release must
                # not silently change an in-flight upload or a completed legacy video.
                pinned = state.value.get("metadata_override") or state.value["plan"].get("metadata")
                if pinned:
                    self.metadata = deepcopy(pinned)

    def update_discovery_metadata(self, *, authorized=False):
        """Explicit owner edit of an existing video; never uploads or changes visibility."""
        if not authorized:
            raise UploadError("Explicit owner authorization for metadata editing is required")
        with upload_lock(self.engine):
            self.authorize()
            with self.sessions() as db:
                account = db.get(SocialAccount, self.account_id)
                if YOUTUBE_EDIT_SCOPE not in account.scopes:
                    raise UploadError("YouTube edit consent is required")
            current = self.snapshot()
            if not current.get("video_id"):
                raise UploadError("Metadata editing requires a known existing upload")
            item = self.remote()
            privacy = item["status"]["privacyStatus"]
            if privacy not in {"private", "public"}:
                raise UploadError("Visibility changed; owner review required")
            with self.sessions() as db:
                previous = db.get(SystemSetting, self.operation_key).value.get("metadata_edit")
            if previous and previous["privacy"] != privacy:
                raise UploadError("Visibility changed since the saved metadata edit")
            target = discovery_metadata(
                self.brief.localizations.model_dump(by_alias=True),
                self.brief.hashtags,
                category_id=item["snippet"]["categoryId"],
                # Google can reorder tags on readback. Replay the captured intent,
                # rather than changing its fingerprint from a reordered response.
                tags=(
                    previous["desired"]["snippet"]["tags"]
                    if previous
                    else item["snippet"].get("tags", [])
                ),
            )
            fingerprint = hashlib.sha256(json.dumps(target, sort_keys=True).encode()).hexdigest()
            with self.sessions.begin() as db:
                state = db.get(SystemSetting, self.operation_key)
                previous = state.value.get("metadata_edit")
                if previous and previous["fingerprint"] != fingerprint:
                    raise UploadError("The requested metadata edit changed; inspect saved intent")
                if not previous:
                    state.value = {
                        **state.value,
                        "metadata_edit": {
                            "fingerprint": fingerprint,
                            "privacy": privacy,
                            "stage": "prepared",
                            "before": {
                                "snippet": item["snippet"],
                                "localizations": item.get("localizations", {}),
                            },
                            "desired": target,
                        },
                    }
                else:
                    privacy = previous["privacy"]
            self.metadata = {**target, "status": {"privacyStatus": privacy}}

            def matches(resource):
                try:
                    self.verify_metadata(resource)
                    return set(target["snippet"]["tags"]).issubset(
                        resource["snippet"].get("tags", [])
                    )
                except UploadError:
                    return False

            if not matches(item):
                if previous and previous["stage"] in {"submitted", "verified"}:
                    raise UploadError("Metadata edit already submitted; reconcile by reading")
                snippet = {
                    k: item["snippet"][k]
                    for k in (
                        "title",
                        "description",
                        "categoryId",
                        "tags",
                        "defaultLanguage",
                        "defaultAudioLanguage",
                    )
                    if k in item["snippet"]
                }
                snippet.update(target["snippet"])
                body = {
                    "id": current["video_id"],
                    "snippet": snippet,
                    "localizations": {**item.get("localizations", {}), **target["localizations"]},
                }
                headers = {"If-Match": item["etag"]} if item.get("etag") else {}
                with self.sessions.begin() as db:
                    state = db.get(SystemSetting, self.operation_key)
                    state.value = {
                        **state.value,
                        "metadata_edit": {**state.value["metadata_edit"], "stage": "submitted"},
                    }
                write_error = None
                try:
                    self.http.data(
                        self.http.request(
                            "PUT",
                            self.http.endpoints.api + "/videos",
                            params={"part": "snippet,localizations"},
                            json=body,
                            headers=headers,
                        )
                    )
                except UploadError as error:
                    write_error = error
                # A lost response may still mean Google accepted the update. Read first.
                item = self.remote()
                if not matches(item):
                    raise write_error or UploadError("Google has not confirmed the metadata edit")
            if item["status"]["privacyStatus"] != privacy:
                raise UploadError("Visibility changed during metadata verification")
            with self.sessions.begin() as db:
                state = db.get(SystemSetting, self.operation_key)
                state.value = {
                    **state.value,
                    "metadata_override": self.metadata,
                    "metadata_edit": {**state.value["metadata_edit"], "stage": "verified"},
                }
            return {
                "video_id": current["video_id"],
                "url": current["url"],
                "privacy": privacy,
                "translations_verified": True,
                "localizations": target["localizations"],
                "tags": target["snippet"]["tags"],
                "new_uploads": 0,
                "new_ai_calls": 0,
            }

    def approved(self):
        if not self.settings.publishing_authorized:
            raise UploadError("Automatic upload/publication is not authorized")
        with self.sessions() as db:
            source_job = db.get(ProductionJob, self.job_id)
            if (
                source_job.status == "cancelled"
                or source_job.payload.get("owner_discarded")
                or source_job.payload.get("never_publish")
            ):
                raise UploadError("The owner discarded this video; publication is prohibited")
            if self.native:
                video = db.get(Video, self.video_id)
                generation = db.get(VideoGeneration, video.generation_id)
                original_hash = generation.parameters.get("sha256")
                if (
                    not original_hash
                    or original_hash != video.sha256
                    or hashlib.sha256(self.asset.read_bytes()).hexdigest() != original_hash
                ):
                    raise UploadError(
                        "Native publication must preserve the provider output exactly"
                    )
            account = db.scalar(
                select(SocialAccount).where(
                    SocialAccount.platform == "youtube",
                    SocialAccount.external_id == self.settings.youtube_channel_id,
                )
            )
            check = db.scalar(
                select(QualityCheck).where(
                    QualityCheck.video_id == self.video_id,
                    QualityCheck.approved.is_(True),
                    QualityCheck.technical_pass.is_(True),
                )
            )
            scoped_private = private_trial_authorized(
                source_job, self.target, self.settings.youtube_channel_id
            )
            if not check or not account or not (account.approved_for_publication or scoped_private):
                raise UploadError(
                    "Approved quality and account publication authorization are required"
                )
            if self.target == "public" and YOUTUBE_EDIT_SCOPE not in account.scopes:
                raise UploadError("YouTube edit consent is required for public publication")

    def inspect_asset(self):
        return inspect_final(self.asset, require_audio=True, native_seconds=self.native_seconds)

    def video_record(self, db, source, plan):
        video = db.get(Video, self.video_id)
        if video.generation_id != source.id or video.sha256 != plan["sha256"]:
            raise UploadError("The approved media hash or generation changed")
        return video

    def remote(self):
        current = self.snapshot()
        response = self.http.data(
            self.http.request(
                "GET",
                self.http.endpoints.api + "/videos",
                params={
                    "part": "snippet,localizations,status,contentDetails,processingDetails",
                    "id": current["video_id"],
                },
            )
        )
        item = next(
            (v for v in response.get("items", []) if v.get("id") == current["video_id"]), None
        )
        if not item or item.get("snippet", {}).get("channelId") != self.settings.youtube_channel_id:
            raise UploadError("The job's uploaded video is missing or has the wrong channel")
        return item

    def verify_metadata(self, item):
        snippet = item["snippet"]
        english = self.metadata["localizations"]["en"]
        if snippet.get("defaultLanguage") != "en" or any(
            snippet.get(k) != v for k, v in english.items()
        ):
            raise UploadError("Google has not confirmed the English production metadata")
        if any(
            any(item.get("localizations", {}).get(code, {}).get(k) != v for k, v in text.items())
            for code, text in self.metadata["localizations"].items()
        ):
            raise UploadError("Google has not confirmed every localized title and description")
        if item.get("contentDetails", {}).get("regionRestriction"):
            raise UploadError("Regional restrictions need owner attention")

    def publish(self):
        self.approved()
        # The caller holds the global production lock. The original uploader acquires
        # its own lock for media transfer; status/public writes use it separately.
        if self.snapshot().get("video_id"):
            current = self.reconcile()
        else:
            current = self.upload()
        if current["status"] in {"processing_private", "uploaded_unverified"}:
            return current
        if current["status"] not in {"processed_private", "processed_public"}:
            raise UploadError("The uploaded video did not process successfully")
        with upload_lock(self.engine):
            self.authorize()
            item = self.remote()
            self.verify_metadata(item)
            if self.target == "public" and item["status"]["privacyStatus"] != "public":
                self.approved()
                with self.sessions.begin() as db:
                    existing = db.get(SystemSetting, self.public_operation_key)
                    intent = {
                        "public_requested": True,
                        "publication_id": current["publication_id"],
                        "video_id": current["video_id"],
                        "job_id": self.job_id,
                    }
                    if existing:
                        if existing.value != intent:
                            raise UploadError("Publication intent changed; owner review required")
                    else:
                        db.add(SystemSetting(key=self.public_operation_key, value=intent))
                status = {
                    k: item["status"][k]
                    for k in ("license", "embeddable", "publicStatsViewable")
                    if k in item["status"]
                }
                status.update(
                    privacyStatus="public",
                    selfDeclaredMadeForKids=False,
                    containsSyntheticMedia=True,
                )
                self.http.data(
                    self.http.request(
                        "PUT",
                        self.http.endpoints.api + "/videos",
                        params={"part": "status"},
                        json={"id": current["video_id"], "status": status},
                    )
                )
            current = self.reconcile()
            self.verify_metadata(self.remote())
            if current["privacy"] != self.target:
                raise UploadError("Google did not confirm the requested visibility")
            with self.sessions.begin() as db:
                publication = db.get(Publication, current["publication_id"])
                if self.target == "public":
                    publication.published_at = publication.published_at or utcnow()
                db.get(Video, self.video_id).status = (
                    "published" if self.target == "public" else "uploaded_private"
                )
            return {
                **current,
                "languages": list(self.metadata["localizations"]),
                "translations_verified": True,
            }
