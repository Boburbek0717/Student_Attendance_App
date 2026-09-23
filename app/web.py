from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.security import csrf_token
from app.school_time import school_time


APP_DIRECTORY = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=APP_DIRECTORY / "templates")
templates.env.filters["school_time"] = school_time


def get_db(request: Request):
    with Session(request.app.state.database_engine) as db:
        yield db


def render(request: Request, name: str, status_code: int = 200, **context):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={"csrf_token": csrf_token(request), **context},
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
        },
    )
