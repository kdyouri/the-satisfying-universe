"""Publish the existing owner-authorized video after verifying all six translations."""

import hashlib
import json

from sqlalchemy import select

from tsu.models import Publication, SocialAccount, SystemSetting, utcnow
from tsu.youtube_auth import YOUTUBE_EDIT_SCOPE
from tsu.youtube_metadata import (
    FIRST_VIDEO_LOCALIZATIONS,
    LANGUAGES,
    PUBLICATION_OPERATION,
    localized_metadata,
)
from tsu.youtube_upload import OPERATION, PrivateTestUpload, UploadError, upload_lock


class YouTubePublication(PrivateTestUpload):
    def binding(self):
        with self.sessions() as db:
            original = db.get(SystemSetting, OPERATION)
            pub = db.get(Publication, original.value["publication_id"]) if original else None
            if not pub or not pub.remote_id:
                raise UploadError("Upload the owner video before preparing its publication")
            return {
                "video_id": pub.remote_id,
                "publication_id": pub.id,
                "sha256": original.value["plan"]["sha256"],
            }

    def plan(self):
        binding = self.binding()
        with self.sessions() as db:
            account = db.scalar(
                select(SocialAccount).where(
                    SocialAccount.platform == "youtube",
                    SocialAccount.external_id == self.settings.youtube_channel_id,
                )
            )
            can_edit = bool(account and YOUTUBE_EDIT_SCOPE in account.scopes)
        return {
            **binding,
            "channel_id": self.settings.youtube_channel_id,
            "default_language": "en",
            "languages": LANGUAGES,
            "localizations": FIRST_VIDEO_LOCALIZATIONS,
            "target_privacy": "public",
            "edit_consent_granted": can_edit,
            "new_upload": False,
            "new_ai_calls": 0,
            "scheduler_enabled": False,
        }

    def read_remote(self):
        binding = self.binding()
        result = self.http.data(
            self.http.request(
                "GET",
                self.http.endpoints.api + "/videos",
                params={
                    "part": "snippet,localizations,status,contentDetails,processingDetails",
                    "id": binding["video_id"],
                },
            )
        )
        item = next(
            (x for x in result.get("items", []) if x.get("id") == binding["video_id"]), None
        )
        if not item or item.get("snippet", {}).get("channelId") != self.settings.youtube_channel_id:
            raise UploadError("The known video is missing or is not on the expected channel")
        return item

    @staticmethod
    def translations_match(item):
        snippet = item.get("snippet", {})
        english = FIRST_VIDEO_LOCALIZATIONS["en"]
        return (
            snippet.get("defaultLanguage") == "en"
            and all(snippet.get(k) == v for k, v in english.items())
            and all(
                all(
                    item.get("localizations", {}).get(code, {}).get(k) == v for k, v in text.items()
                )
                for code, text in FIRST_VIDEO_LOCALIZATIONS.items()
            )
        )

    def verify(self, item):
        match = self.translations_match(item)
        status = item.get("status", {})
        processing = item.get("processingDetails", {}).get("processingStatus")
        processed = status.get("uploadStatus") not in {"failed", "rejected", "deleted"} and (
            processing == "succeeded"
            or (status.get("uploadStatus") == "processed" and processing in (None, "terminated"))
        )
        restricted = bool(item.get("contentDetails", {}).get("regionRestriction"))
        return {
            **self.binding(),
            "channel_id": item["snippet"]["channelId"],
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "privacy": status.get("privacyStatus"),
            "default_language": item["snippet"].get("defaultLanguage"),
            "languages": sorted(item.get("localizations", {})),
            "localizations": item.get("localizations", {}),
            "translations_verified": match,
            "processing_succeeded": processed,
            "region_restriction": item.get("contentDetails", {}).get("regionRestriction"),
            "status": (
                "published_public"
                if status.get("privacyStatus") == "public"
                and match
                and processed
                and not restricted
                else "not_published_or_not_verified"
            ),
            "scheduler_enabled": False,
        }

    def save(self, **changes):
        with self.sessions.begin() as db:
            state = db.scalar(
                select(SystemSetting)
                .where(SystemSetting.key == PUBLICATION_OPERATION)
                .with_for_update()
            )
            state.value = {**state.value, **changes}

    def status(self):
        self.authorize()
        result = self.verify(self.read_remote())
        with self.sessions() as db:
            authorized = db.get(SystemSetting, PUBLICATION_OPERATION) is not None
        if authorized:
            self.save(verified=result)
            with self.sessions.begin() as db:
                pub = db.get(Publication, result["publication_id"])
                if result["status"] == "published_public":
                    pub.status = "processed_public"
                    # Observe public visibility before recording publication time.
                    pub.published_at = pub.published_at or utcnow()
                    pub.last_error = None
                else:
                    pub.status = (
                        "processed_private"
                        if result["privacy"] == "private" and result["processing_succeeded"]
                        else "publication_verification_required"
                    )
        return result

    def publish(self):
        with upload_lock(self.engine):
            plan = self.plan()
            if not plan["edit_consent_granted"]:
                raise UploadError(
                    "Authorize YouTube editing from the owner dashboard before publication"
                )
            self.authorize()
            item = self.read_remote()
            observed = self.verify(item)
            if not observed["processing_succeeded"] or observed["region_restriction"]:
                raise UploadError("Processing or regional restrictions need owner attention")
            if observed["privacy"] not in {"private", "public"}:
                raise UploadError("The video's visibility changed; review it before publication")
            desired_hash = hashlib.sha256(
                json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            with self.sessions.begin() as db:
                state = db.get(SystemSetting, PUBLICATION_OPERATION)
                if state and state.value["plan_hash"] != desired_hash:
                    raise UploadError("The publication plan changed; stop before any update")
                if state is None:
                    db.add(
                        SystemSetting(
                            key=PUBLICATION_OPERATION,
                            value={
                                "plan": plan,
                                "plan_hash": desired_hash,
                                "publication_id": plan["publication_id"],
                                "video_id": plan["video_id"],
                                "public_requested": True,
                                "owner_authorization": (
                                    "Explicit request to localize six languages "
                                    "and publish this video"
                                ),
                                "before": {
                                    "snippet": item.get("snippet"),
                                    "localizations": item.get("localizations", {}),
                                    "status": item.get("status"),
                                },
                                "stage": "prepared",
                            },
                        )
                    )
            if not observed["translations_verified"]:
                snippet = item["snippet"]
                if snippet.get("defaultAudioLanguage"):
                    raise UploadError("Review existing spoken-language metadata before changing it")
                metadata = localized_metadata(
                    FIRST_VIDEO_LOCALIZATIONS,
                    category_id=snippet["categoryId"],
                    tags=snippet.get("tags", []),
                )
                metadata["localizations"] = {
                    **item.get("localizations", {}),
                    **metadata["localizations"],
                }
                self.save(stage="updating_metadata")
                self.http.data(
                    self.http.request(
                        "PUT",
                        self.http.endpoints.api + "/videos",
                        params={"part": "snippet,localizations"},
                        json={"id": plan["video_id"], **metadata},
                    )
                )
                item = self.read_remote()
                if not self.translations_match(item):
                    raise UploadError(
                        "Google has not confirmed all translations; visibility unchanged"
                    )
                self.save(stage="translations_verified")
            if item["status"]["privacyStatus"] != "public":
                previous = item["status"]
                public_status = {
                    k: previous[k]
                    for k in ("license", "embeddable", "publicStatsViewable")
                    if k in previous
                }
                public_status.update(
                    privacyStatus="public",
                    selfDeclaredMadeForKids=False,
                    containsSyntheticMedia=True,
                )
                self.save(stage="making_public")
                self.http.data(
                    self.http.request(
                        "PUT",
                        self.http.endpoints.api + "/videos",
                        params={"part": "status"},
                        json={"id": plan["video_id"], "status": public_status},
                    )
                )
            result = self.status()
            if result["status"] != "published_public":
                raise UploadError("Google has not confirmed public visibility and all translations")
            self.save(stage="published_public")
            return result
