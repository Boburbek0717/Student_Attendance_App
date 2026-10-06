from contextlib import asynccontextmanager
import os
import re

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.result_content import RESULTS, FEATURED_RESULTS, SPOTLIGHT_RESULTS
from app.database import engine, initialize_database
from app.security import authenticate, current_user, load_session_secret, verify_csrf
from app.security import limit_login_attempt, start_session, revoke_session
from app.middleware import RequestBodyLimit, SecurityHeaders
from app.teacher import router as teacher_router
from app.student import router as student_router
from app.student_management import router as management_router
from app.lesson_management import router as lesson_router
from app.attendance_corrections import router as correction_router
from app.web import APP_DIRECTORY, get_db, render
from app.question_bank.routes import router as question_router
from app.question_bank.practice import router as practice_router
from app.question_bank.public_practice import router as public_practice_router, GuestLimiter
from app.question_bank.import_routes import router as import_router
from app.question_bank.pdf_import import ReviewStore
from app.question_bank.assignments import router as assignment_router


def create_app(database_engine: Engine = engine, session_secret: str | None = None, code_minutes: int | None = None,
               production: bool | None = None, allowed_hosts: list[str] | None = None) -> FastAPI:
    if production is None:
        environment = os.environ.get('SAT_FACTORY_ENV', 'development')
        if environment not in ('development', 'production'):
            raise ValueError('SAT_FACTORY_ENV must be development or production.')
        production = environment == 'production'
    if production:
        session_secret = session_secret or os.environ.get('SAT_FACTORY_SESSION_SECRET')
        if not session_secret or len(session_secret) < 64:
            raise ValueError('Production requires an external session secret of at least 64 characters.')
        allowed_hosts = allowed_hosts or [h.strip() for h in os.environ.get('SAT_FACTORY_ALLOWED_HOSTS', '').split(',') if h.strip()]
        if not allowed_hosts or any(not re.fullmatch(r'[a-zA-Z0-9]+(?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', h) for h in allowed_hosts):
            raise ValueError('Production requires explicit hostnames without wildcards, schemes or ports.')
    if code_minutes is None:
        code_minutes = int(os.environ.get("ATTENDANCE_CODE_MINUTES", "15"))
    if not 1 <= code_minutes <= 60:
        raise ValueError("ATTENDANCE_CODE_MINUTES must be between 1 and 60.")
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_database(database_engine)
        try:
            yield
        finally:
            database_engine.dispose()

    app = FastAPI(title="SAT Factory", lifespan=lifespan,
                  docs_url=None if production else '/docs',
                  redoc_url=None if production else '/redoc',
                  openapi_url=None if production else '/openapi.json')
    app.state.database_engine = database_engine
    app.state.code_minutes = code_minutes
    app.state.pdf_reviews = ReviewStore()
    app.state.guest_limiter = GuestLimiter()
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret or load_session_secret(),
        session_cookie="attendance_session",
        max_age=8 * 60 * 60,
        same_site="lax",
        https_only=production,
    )
    app.add_middleware(RequestBodyLimit)
    if production:
        app.add_middleware(HTTPSRedirectMiddleware)
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts, www_redirect=False)
    app.add_middleware(SecurityHeaders, hsts=production)
    app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")
    app.include_router(teacher_router)
    app.include_router(student_router)
    app.include_router(management_router)
    app.include_router(lesson_router)
    app.include_router(correction_router)
    app.include_router(import_router)
    app.include_router(question_router)
    app.include_router(practice_router)
    app.include_router(public_practice_router)
    app.include_router(assignment_router)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        # FastAPI's default payload includes raw submitted input; do not echo it.
        return render(request, 'error.html', 422,
                      message='Some submitted values are invalid. Return to the form, check the fields and try again.')

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        if error.status_code == 303:
            return RedirectResponse(error.headers["Location"], status_code=303)
        response = render(request, "error.html", error.status_code, message=error.detail)
        response.headers.update(error.headers or {})
        return response

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        return render(request, "index.html", user=user, featured=FEATURED_RESULTS, spotlights=SPOTLIGHT_RESULTS, result_count=len(RESULTS))

    @app.get("/results", response_class=HTMLResponse)
    def results_page(request: Request, db: Session = Depends(get_db)):
        return render(request, "results.html", user=current_user(request, db), results=RESULTS)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if user:
            return RedirectResponse(f"/{user.role}", status_code=303)
        return render(request, "login.html", error=None, username="")

    @app.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        username: str = Form(default=""),
        password: str = Form(default=""),
        csrf: str = Form(default=""),
        db: Session = Depends(get_db),
    ):
        verify_csrf(request, csrf)
        try:
            limit_login_attempt(database_engine, username, request.client.host if request.client else "unknown")
        except ValueError as error:
            return render(request, "login.html", 503, error=str(error), username=username[:100])
        user = authenticate(db, username, password)
        if user is None:
            return render(
                request, "login.html", 401,
                error="Incorrect username or password.", username=username[:100],
            )
        start_session(request, db, user)
        return RedirectResponse(f"/{user.role}", status_code=303)

    @app.post("/logout")
    def logout(request: Request, csrf: str = Form(default=""), db: Session = Depends(get_db)):
        verify_csrf(request, csrf)
        revoke_session(request, db)
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    return app


app = create_app()
