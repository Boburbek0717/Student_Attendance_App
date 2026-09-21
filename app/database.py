from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import URL, Engine, create_engine, event, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Session


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


@contextmanager
def write_transaction(engine: Engine):
    """Serialize balance checks and writes in one SQLite transaction."""
    with Session(engine) as db:
        try:
            db.execute(text("BEGIN IMMEDIATE"))
            yield db
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError("The record could not be saved. Refresh and check your history before retrying.") from error
        except OperationalError as error:
            db.rollback()
            if (getattr(error.orig, "sqlite_errorcode", 0) & 255) in (5, 6):
                raise ValueError("The database is busy. Please try again in a moment.") from error
            raise


def initialize_database(database_engine: Engine = engine) -> None:
    # Import models so their tables are registered before creating the schema.
    from app import models

    Base.metadata.create_all(database_engine)
