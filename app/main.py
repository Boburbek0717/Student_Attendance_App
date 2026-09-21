from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.database import engine, initialize_database
from app.security import authenticate, csrf_token, current_user, load_session_secret, verify_csrf


APP_DIRECTORY = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=APP_DIRECTORY / "templates")


def get_db(request: Request):
    with Session(request.app.state.database_engine) as db:
        yield db


def render(request: Request, name: str, status_code: int = 200, **context):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={"csrf_token": csrf_token(request), **context},
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


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
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret or load_session_secret(),
        session_cookie="attendance_session",
        max_age=8 * 60 * 60,
        same_site="lax",
        https_only=False,  # Local HTTP development only.
    )
    app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return render(request, "error.html", error.status_code, message=error.detail)

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
        user = authenticate(db, username, password)
        if user is None:
            return render(
                request, "login.html", 401,
                error="Incorrect username or password.", username=username[:100],
            )
        request.session.clear()
        request.session["user_id"] = user.id
        csrf_token(request)
        return RedirectResponse(f"/{user.role}", status_code=303)

    @app.post("/logout")
    def logout(request: Request, csrf: str = Form(default="")):
        verify_csrf(request, csrf)
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    def role_page(request: Request, db: Session, role: str):
        user = current_user(request, db)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        if user.role != role:
            raise HTTPException(status_code=403, detail="Your account cannot open this page.")
        return render(request, f"{role}.html", user=user)

    @app.get("/teacher", response_class=HTMLResponse)
    def teacher_page(request: Request, db: Session = Depends(get_db)):
        return role_page(request, db, "teacher")

    @app.get("/student", response_class=HTMLResponse)
    def student_page(request: Request, db: Session = Depends(get_db)):
        return role_page(request, db, "student")

    return app


app = create_app()
