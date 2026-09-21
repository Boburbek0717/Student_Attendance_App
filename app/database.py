from pathlib import Path
from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


DATABASE_PATH = Path(__file__).resolve().parent.parent / "attendance.db"


def make_engine(database: str):
    engine = create_engine(
        URL.create("sqlite", database=database),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, connection_record):
        previous = connection.autocommit
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        connection.autocommit = previous

    return engine


engine = make_engine(str(DATABASE_PATH))


def initialize_database(database_engine: Engine = engine) -> None:
    # Import models so their tables are registered before creating the schema.
    from app import models

    Base.metadata.create_all(database_engine)
