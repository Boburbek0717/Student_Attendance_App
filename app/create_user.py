import argparse
import getpass
import warnings

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import engine, initialize_database
from app.models import User
from app.security import normalize_username, password_hasher


def create_user(db: Session, username: str, display_name: str, password: str, role: str) -> User:
    username = normalize_username(username)
    display_name = display_name.strip()
    if not 1 <= len(display_name) <= 100:
        raise ValueError("The display name must contain 1–100 characters.")
    if not 12 <= len(password) <= 128:
        raise ValueError("Use a password containing 12–128 characters.")
    if role not in {"teacher", "student"}:
        raise ValueError("The role must be teacher or student.")
    user = User(
        username=username,
        display_name=display_name,
        password_hash=password_hasher.hash(password),
        role=role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError("That username is already in use.") from error
    db.refresh(user)
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local teacher or student account.")
    parser.add_argument("username")
    parser.add_argument("--name", required=True, help="Name shown on the welcome page")
    parser.add_argument("--role", choices=("teacher", "student"), default="student")
    args = parser.parse_args()
    try:
        # Refuse a terminal that would echo the password onto the screen.
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Password (12–128 characters): ")
            confirmation = getpass.getpass("Repeat password: ")
        if password != confirmation:
            raise ValueError("The passwords do not match.")
        initialize_database()
        with Session(engine) as db:
            user = create_user(db, args.username, args.name, password, args.role)
            print(f"Created {user.role} account: {user.username}")
    except (ValueError, getpass.GetPassWarning) as error:
        parser.exit(1, f"Account not created: {error}\n")
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nAccount creation cancelled.\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
