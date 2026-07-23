from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import SECRET_KEY, SESSION_COOKIE_NAME
from app.core.deps import Forbidden, NotAuthenticated, get_current_user_optional
from app.core.templates import templates
from app.db.session import Base, SessionLocal, engine
from app.routers import auth, clubs, head, reports, settings, vrsp, vrsp_requests

app = FastAPI(title="DSG Digital")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie=SESSION_COOKIE_NAME)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/logo", StaticFiles(directory="logo"), name="logo")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(engine)


@app.exception_handler(NotAuthenticated)
def handle_not_authenticated(request: Request, exc: NotAuthenticated):
    return RedirectResponse(f"/login?next={request.url.path}", status_code=303)


@app.exception_handler(Forbidden)
def handle_forbidden(request: Request, exc: Forbidden):
    return templates.TemplateResponse(request, "pages/403.html", {"user": None}, status_code=403)


@app.get("/")
def root(request: Request):
    db = SessionLocal()
    try:
        user = get_current_user_optional(request, db)
    finally:
        db.close()
    return templates.TemplateResponse(request, "pages/landing.html", {"user": user})


app.include_router(auth.router)
app.include_router(clubs.router)
app.include_router(head.router)
app.include_router(vrsp.router)
app.include_router(vrsp_requests.router)
app.include_router(settings.router)
app.include_router(reports.router)
