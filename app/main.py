from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.database import engine, initialize_database
from app.security import authenticate, current_user, load_session_secret, verify_csrf
from app.security import LoginLimiter, start_session, revoke_session
from app.middleware import RequestBodyLimit
from app.teacher import router as teacher_router
from app.web import APP_DIRECTORY, get_db, render


def create_app(database_engine: Engine = engine, session_secret: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_database(database_engine)
        try:
            yield
        finally:
            database_engine.dispose()

    app = FastAPI(title="Student Attendance Tracker", lifespan=lifespan)
    app.state.database_engine = database_engine
    app.state.login_limiter = LoginLimiter()
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret or load_session_secret(),
        session_cookie="attendance_session",
        max_age=8 * 60 * 60,
        same_site="lax",
        https_only=False,  # Local HTTP development only.
    )
    app.add_middleware(RequestBodyLimit)
    app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")
    app.include_router(teacher_router)

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
        if user:
            return RedirectResponse(f"/{user.role}", status_code=303)
        return render(request, "index.html")

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
        app.state.login_limiter.check(request.client.host if request.client else "unknown")
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

    def role_page(request: Request, db: Session, role: str):
        user = current_user(request, db)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if user.role != role:
            raise HTTPException(status_code=403, detail="Your account cannot open this page.")
        return render(request, f"{role}.html", user=user)

    @app.get("/student", response_class=HTMLResponse)
    def student_page(request: Request, db: Session = Depends(get_db)):
        return role_page(request, db, "student")

    return app


app = create_app()
