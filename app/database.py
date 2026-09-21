from pathlib import Path

from sqlalchemy import URL, create_engine, text


DATABASE_PATH = Path(__file__).resolve().parent.parent / "attendance.db"
engine = create_engine(
    URL.create("sqlite", database=str(DATABASE_PATH)),
    connect_args={"check_same_thread": False},
)


def check_database() -> None:
    """Open the SQLite file and verify that it can answer a query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
