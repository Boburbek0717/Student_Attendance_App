from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import initialize_database, engine


APP_DIRECTORY = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="Student Attendance Tracker", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIRECTORY / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Student Attendance Tracker"},
    )
