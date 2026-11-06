from html import escape
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from tsu.security import (
    LOGIN_COOKIE,
    OWNER_COOKIE,
    OwnerIdentity,
    constant_equal,
    new_login_nonce,
    read_form,
    valid_login_nonce,
)
from tsu.youtube_auth import YouTubeConnectionError


def register_browser_routes(app, settings, access, youtube, require_admin):
    def login_page(message: str = "", status: int = 200):
        secret = settings.admin_token.get_secret_value()
        if not secret:
            raise HTTPException(503, "Administrative access is not configured")
        nonce = new_login_nonce(secret)
        template = Path(__file__).with_name("login.html").read_text()
        response = HTMLResponse(
            template.replace("{{csrf}}", escape(nonce)).replace("{{message}}", escape(message)),
            status_code=status,
        )
        response.set_cookie(
            LOGIN_COOKIE, nonce, max_age=600, secure=True, httponly=True, samesite="lax", path="/"
        )
        return response

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/login", status_code=303)

    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    async def login_get(request: Request):
        if request.cookies.get(OWNER_COOKIE):
            try:
                await access(request)
                return RedirectResponse("/admin", status_code=303)
            except HTTPException:
                pass
        return login_page()

    @app.post("/login", include_in_schema=False)
    async def login_post(request: Request):
        secret = settings.admin_token.get_secret_value()
        if not secret:
            raise HTTPException(503, "Administrative access is not configured")
        origin = request.headers.get("origin")
        if origin and origin != settings.public_origin:
            raise HTTPException(403, "Request origin is not allowed")
        fields = await read_form(request)
        nonce = fields.get("csrf", "")
        if (
            not nonce
            or not constant_equal(nonce, request.cookies.get(LOGIN_COOKIE, ""))
            or not valid_login_nonce(nonce, secret)
        ):
            raise HTTPException(403, "Login form expired; reload the login page")
        if not constant_equal(fields.get("password", ""), secret):
            return login_page("Incorrect owner password.", status=401)
        raw = access.create_session()
        response = RedirectResponse("/admin", status_code=303)
        response.set_cookie(
            OWNER_COOKIE,
            raw,
            max_age=8 * 3600,
            secure=True,
            httponly=True,
            samesite="lax",
            path="/",
        )
        response.delete_cookie(LOGIN_COOKIE, secure=True, httponly=True, samesite="lax")
        return response

    @app.post("/logout", include_in_schema=False)
    def logout(owner: Annotated[OwnerIdentity, Depends(require_admin)]):
        if owner.session_hash:
            access.delete_session(owner.session_hash)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(OWNER_COOKIE, secure=True, httponly=True, samesite="lax")
        return response

    @app.get("/api/youtube/status", dependencies=[Depends(require_admin)])
    def youtube_status():
        return youtube.status()

    @app.post("/auth/youtube/start", include_in_schema=False)
    def youtube_start(owner: Annotated[OwnerIdentity, Depends(require_admin)]):
        try:
            return RedirectResponse(youtube.start(owner.session_hash), status_code=303)
        except YouTubeConnectionError as error:
            raise HTTPException(400, str(error)) from None

    @app.get("/auth/youtube/callback", include_in_schema=False)
    def youtube_callback(request: Request, owner: Annotated[OwnerIdentity, Depends(require_admin)]):
        params = request.query_params
        if any(len(params.getlist(name)) > 1 for name in ("state", "code", "error")):
            raise HTTPException(400, "Duplicate OAuth parameters are not allowed")
        try:
            youtube.complete(
                owner.session_hash,
                params.get("state", ""),
                params.get("code"),
                denied="error" in params,
            )
        except YouTubeConnectionError as error:
            return HTMLResponse(
                "<!doctype html><html lang='en'><meta charset='utf-8'>"
                "<title>YouTube connection</title><h1>Connection not completed</h1>"
                f"<p>{escape(str(error))}</p>"
                "<p><a href='/admin'>Return to control room</a></p></html>",
                status_code=400,
            )
        return RedirectResponse("/admin", status_code=303)
