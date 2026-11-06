from contextlib import asynccontextmanager
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from tsu.browser_auth import register_browser_routes
from tsu.budget import exposure
from tsu.config import Settings
from tsu.contracts import StrictModel
from tsu.db import make_engine, make_sessions
from tsu.jobs import IdempotencyConflict, create_job
from tsu.models import Alert, BudgetGuard, ProductionJob
from tsu.native_profile import native_profile
from tsu.security import OwnerAccess, OwnerIdentity
from tsu.workflow import ProductionInput, enqueue, readiness
from tsu.youtube_auth import YouTubeConnections
from tsu.youtube_metadata import FIRST_VIDEO_LOCALIZATIONS, LANGUAGES, PUBLICATION_OPERATION
from tsu.youtube_publication import YouTubePublication
from tsu.youtube_upload import OPERATION, PrivateTestUpload, UploadError


class JobInput(StrictModel):
    concept: str = Field(min_length=3, max_length=2000)


class PrivateUploadInput(StrictModel):
    confirm_private_test: Literal[True]


class PublicationInput(StrictModel):
    confirm_publication: Literal[True]


def job_view(job: ProductionJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "payload": job.payload,
        "attempts": job.attempts,
        "reason": job.reason,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def create_app(
    settings: Settings | None = None,
    engine=None,
    google_client=None,
    youtube_upload_factory=None,
    youtube_publication_factory=None,
) -> FastAPI:
    settings = settings or Settings()
    engine = engine if engine is not None else make_engine(settings.database_url.get_secret_value())
    sessions = make_sessions(engine)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(
        title="The Satisfying Universe",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.sessions = sessions
    auth = HTTPBearer(auto_error=False)
    access = OwnerAccess(settings, sessions)
    youtube = YouTubeConnections(settings, sessions, google_client)

    @app.exception_handler(HTTPException)
    async def owner_access_error(request: Request, error: HTTPException):
        if (
            request.method == "GET"
            and request.url.path == "/admin"
            and error.status_code == 401
            and not request.headers.get("authorization")
            and "text/html" in request.headers.get("accept", "").lower()
        ):
            return RedirectResponse("/login", status_code=303)
        return await http_exception_handler(request, error)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        # no-referrer makes browsers send Origin: null on native HTML form POSTs.
        # Keep callback URLs private while preserving genuine origins on our forms.
        response.headers["Referrer-Policy"] = (
            "no-referrer" if request.url.path == "/auth/youtube/callback" else "strict-origin"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "form-action 'self' https://accounts.google.com; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    async def require_admin(
        request: Request,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(auth),
        ],
    ):
        return await access(request)

    protected = [Depends(require_admin)]
    register_browser_routes(app, settings, access, youtube, require_admin)
    from tsu.public_information import register as register_public_information

    register_public_information(app, settings, access)

    def upload_service():
        if youtube_upload_factory:
            return youtube_upload_factory()
        return PrivateTestUpload(settings, engine)

    def upload_call(method):
        service = upload_service()
        try:
            return getattr(service, method)()
        except UploadError as error:
            from tsu.models import Publication, SystemSetting

            with sessions.begin() as session:
                state = session.get(SystemSetting, OPERATION)
                if state:
                    publication = session.get(Publication, state.value["publication_id"])
                    publication.last_error = str(error)
            raise HTTPException(409, str(error)) from None
        finally:
            service.close()

    @app.get("/api/youtube/test-upload/plan", dependencies=protected)
    def private_upload_plan():
        return upload_call("plan")

    @app.get("/api/youtube/test-upload", dependencies=protected)
    def private_upload_status():
        return upload_call("reconcile")

    @app.post("/api/youtube/test-upload", dependencies=protected)
    def private_upload(body: PrivateUploadInput, response: Response):
        assert body.confirm_private_test
        result = upload_call("upload")
        response.status_code = 202 if result["status"] == "processing_private" else 200
        return result

    def publication_call(method):
        service = (
            youtube_publication_factory()
            if youtube_publication_factory
            else YouTubePublication(settings, engine)
        )
        try:
            return getattr(service, method)()
        except UploadError as error:
            from tsu.models import Publication, SystemSetting

            with sessions.begin() as session:
                state = session.get(SystemSetting, PUBLICATION_OPERATION)
                if state:
                    publication = session.get(Publication, state.value["publication_id"])
                    publication.last_error = str(error)
            raise HTTPException(409, str(error)) from None
        finally:
            service.close()

    @app.get("/api/youtube/publication/plan", dependencies=protected)
    def publication_plan():
        return publication_call("plan")

    @app.get("/api/youtube/publication", dependencies=protected)
    def publication_status():
        return publication_call("status")

    @app.post("/api/youtube/publication", dependencies=protected)
    def publication_publish(body: PublicationInput):
        assert body.confirm_publication
        return publication_call("publish")

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/api/production/status", dependencies=protected)
    def production_status():
        from tsu.models import SocialAccount

        state = readiness(settings)
        with sessions() as session:
            account = session.scalar(
                select(SocialAccount).where(
                    SocialAccount.platform == "youtube",
                    SocialAccount.external_id == settings.youtube_channel_id,
                )
            )
            approved = bool(account and account.approved_for_publication)
        state["account_publication_approved"] = approved
        state["languages"] = list(LANGUAGES)
        if not approved:
            state["blockers"].append("account_publication_not_authorized")
        return state

    @app.post("/api/production/jobs", dependencies=protected)
    def production_job(
        body: ProductionInput,
        response: Response,
        idempotency_key: Annotated[str, Header(min_length=1, max_length=120)],
    ):
        try:
            with sessions.begin() as session:
                job, created = enqueue(session, idempotency_key, body)
                result = job_view(job)
            response.status_code = 201 if created else 200
            return result
        except IdempotencyConflict as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/health/ready", dependencies=protected)
    def ready():
        try:
            with sessions() as session:
                session.execute(text("SELECT 1"))
                if session.get(BudgetGuard, 1) is None:
                    raise HTTPException(503, "Database migrations are required")
        except SQLAlchemyError:
            raise HTTPException(503, "Database unavailable or not migrated") from None
        return {"status": "ready", "milestone": "foundation"}

    def overview_data():
        from tsu.notifications import readiness as email_readiness

        with sessions() as session:
            states = dict(
                session.execute(
                    select(ProductionJob.status, func.count()).group_by(ProductionJob.status)
                ).all()
            )
            costs = exposure(session, datetime.now(UTC), settings.tz)
            guard = session.get(BudgetGuard, 1)
            alerts = session.scalar(
                select(func.count()).select_from(Alert).where(Alert.resolved.is_(False))
            )
        return {
            "jobs": states,
            "costs_usd": {k: str(v) for k, v in costs.items()},
            "daily_cap_usd": str(settings.daily_budget_usd),
            "monthly_cap_usd": str(settings.monthly_budget_usd),
            "spending_frozen": guard.frozen if guard else True,
            "unresolved_alerts": alerts,
            "capabilities": settings.gates(),
            "email_alerts": email_readiness(settings),
        }

    @app.get("/api/overview", dependencies=protected)
    def overview():
        return overview_data()

    @app.get("/api/capabilities", dependencies=protected)
    def capabilities():
        return settings.gates()

    @app.post("/api/jobs", dependencies=protected, status_code=201)
    def queue_job(
        body: JobInput,
        response: Response,
        idempotency_key: Annotated[str, Header(min_length=1, max_length=160)],
    ):
        try:
            with sessions.begin() as session:
                job, created = create_job(session, idempotency_key, body.model_dump())
                result = job_view(job)
        except IdempotencyConflict:
            raise HTTPException(409, "Idempotency key has different input") from None
        response.status_code = 201 if created else 200
        return result

    @app.get("/api/jobs", dependencies=protected)
    def list_jobs(limit: Annotated[int, Query(ge=1, le=100)] = 30):
        with sessions() as session:
            jobs = session.scalars(
                select(ProductionJob)
                .order_by(ProductionJob.created_at.desc(), ProductionJob.id)
                .limit(limit)
            ).all()
            return [job_view(j) for j in jobs]

    @app.get("/api/jobs/{job_id}", dependencies=protected)
    def get_job(job_id: str):
        with sessions() as session:
            job = session.get(ProductionJob, job_id)
            if job is None:
                raise HTTPException(404, "Job not found")
            return job_view(job)

    @app.get("/api/alerts", dependencies=protected)
    def list_alerts():
        with sessions() as session:
            alerts = session.scalars(
                select(Alert)
                .where(Alert.resolved.is_(False))
                .order_by(Alert.created_at.desc())
                .limit(100)
            ).all()
            return [
                {"id": a.id, "kind": a.kind, "message": a.message, "created_at": a.created_at}
                for a in alerts
            ]

    @app.get("/api/openapi.json", dependencies=protected, include_in_schema=False)
    def openapi():
        return app.openapi()

    @app.get("/admin", dependencies=protected, response_class=HTMLResponse)
    def admin(owner: Annotated[OwnerIdentity, Depends(require_admin)]):
        data = overview_data()
        template = Path(__file__).with_name("admin.html").read_text()
        jobs = "".join(f"<li>{escape(k)}: {v}</li>" for k, v in data["jobs"].items())
        connection = youtube.status()
        channel = escape(connection["handle"] or connection["expected_handle"])
        status = f"Connected: {channel}" if connection["connected"] else f"Not connected: {channel}"
        actions = (
            (
                '<form action="/auth/youtube/start" method="post">'
                f'<input type="hidden" name="csrf" value="{escape(owner.csrf)}">'
                '<button type="submit">Connect YouTube</button></form>'
                '<form action="/logout" method="post">'
                f'<input type="hidden" name="csrf" value="{escape(owner.csrf)}">'
                '<button type="submit">Sign out</button></form>'
            )
            if owner.session_hash
            else '<p><a href="/login">Owner sign in</a> to connect YouTube.</p>'
        )
        upload_message = "Test de téléversement privé : pas encore effectué."
        from tsu.models import Publication, SystemSetting

        with sessions() as session:
            stored = session.get(SystemSetting, OPERATION)
            publication = (
                session.get(Publication, stored.value["publication_id"]) if stored else None
            )
            if publication:
                upload_message = (
                    "Vidéo publique : traitement terminé."
                    if publication.status == "processed_public"
                    else "Test privé : " + escape(publication.status)
                )
                if publication.remote_id:
                    url = "https://www.youtube.com/watch?v=" + publication.remote_id
                    upload_message += (
                        f' · <a href="{escape(url)}" target="_blank" rel="noreferrer">'
                        "Ouvrir la vidéo sur YouTube</a>"
                    )
        translations = "".join(
            f"<tr><td>{escape(label)}</td><td>{escape(FIRST_VIDEO_LOCALIZATIONS[code]['title'])}"
            "</td></tr>"
            for code, label in LANGUAGES.items()
        )
        edit_status = (
            "Autorisation de mise à jour accordée."
            if connection["metadata_edit_authorized"]
            else "Pour appliquer les traductions, clique sur Connect YouTube et accorde "
            "le droit de mise à jour demandé par Google. La connexion actuelle est conservée."
        )
        production = production_status()
        scheduled = (
            "Production programmée active : " + ", ".join(settings.production_times)
            if settings.enable_daily_scheduler and not production["blockers"]
            else "Production programmée désactivée. Le parcours est relié ; "
            "l’essai réel complet et les réglages de lancement restent à valider."
        )
        return HTMLResponse(
            template.replace("{{jobs}}", jobs or "<li>No jobs yet</li>")
            .replace(
                "{{native_duration_seconds}}",
                escape(str(native_profile()["duration_seconds"])),
            )
            .replace("{{daily}}", data["daily_cap_usd"])
            .replace("{{monthly}}", data["monthly_cap_usd"])
            .replace("{{alerts}}", str(data["unresolved_alerts"]))
            .replace("{{youtube_status}}", status)
            .replace("{{youtube_upload_status}}", upload_message)
            .replace("{{youtube_languages}}", translations)
            .replace("{{youtube_edit_status}}", edit_status)
            .replace("{{production_status}}", escape(scheduled))
            .replace(
                "{{email_alert_status}}",
                (
                    "Alertes par courriel actives."
                    if data["email_alerts"]["ready"]
                    else "Alertes par courriel préparées ; accès d’envoi à configurer."
                ),
            )
            .replace("{{owner_actions}}", actions),
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
            },
        )

    return app


app = create_app()
