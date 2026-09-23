import re
import secrets
import hashlib
from datetime import timedelta
from pathlib import Path
from time import time
from math import ceil

from fastapi import HTTPException, Request
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session

from app.models import AttendanceAttemptWindow, LoginAttemptWindow, LoginSession, User, utc_now
from app.database import write_transaction


password_hasher = PasswordHash.recommended()
# Unknown accounts still perform verification to reduce timing clues.
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))
SECRET_PATH = Path(__file__).resolve().parent.parent / ".session-secret"


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def limit_attendance_attempt(engine, user_id: int) -> None:
    """Persist at most ten timestamps per account across workers and restarts."""
    retry_after = 0
    with write_transaction(engine) as db:
        now = time()
        window = db.get(AttendanceAttemptWindow, user_id)
        recent = [stamp for stamp in window.timestamps if stamp > now - 60] if window else []
        if len(recent) >= 10:
            retry_after = max(1, ceil(min(recent) + 60 - now))
        else:
            recent.append(now)
            if window is None:
                db.add(AttendanceAttemptWindow(user_id=user_id, timestamps=recent))
            else:
                window.timestamps = recent
    # Commit the attempt before code validation, so failed check-ins consume it too.
    if retry_after:
        raise HTTPException(429, "Too many check-in attempts. Wait a minute and try again.",
                            headers={"Retry-After": str(retry_after)})


def start_session(request: Request, db: Session, user: User) -> None:
    revoke_session(request, db)
    token = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= utc_now()))
    db.add(LoginSession(
        token_hash=fingerprint(token), user_id=user.id,
        credential_fingerprint=fingerprint(user.password_hash),
        expires_at=utc_now() + timedelta(hours=8),
    ))
    db.commit()
    request.session.clear()
    request.session["session_id"] = token
    csrf_token(request)


def revoke_session(request: Request, db: Session) -> None:
    token = request.session.get("session_id")
    if isinstance(token, str):
        db.execute(delete(LoginSession).where(LoginSession.token_hash == fingerprint(token)))
        db.commit()


def load_session_secret() -> str:
    if not SECRET_PATH.exists():
        try:
            with SECRET_PATH.open("x", encoding="utf-8") as secret_file:
                secret_file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    secret = SECRET_PATH.read_text(encoding="utf-8").strip()
    if len(secret) < 64:
        raise RuntimeError("The local .session-secret file is invalid.")
    return secret


def normalize_username(username: str) -> str:
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,100}", username):
        raise ValueError("Use 3–100 letters, numbers, dots, underscores or hyphens for the username.")
    return username


def authenticate(db: Session, username: str, password: str) -> User | None:
    try:
        username = normalize_username(username)
    except ValueError:
        username = ""
    if not 1 <= len(password) <= 128:
        return None
    user = db.scalar(select(User).where(User.username == username))
    stored_hash = user.password_hash if user else DUMMY_HASH
    try:
        valid = password_hasher.verify(password, stored_hash)
    except (UnknownHashError, ValueError):
        # Stage 2 placeholders are not real credentials and cannot authenticate.
        valid = False
    return user if valid else None


def current_user(request: Request, db: Session) -> User | None:
    token = request.session.get("session_id")
    if not isinstance(token, str):
        return None
    login_session = db.get(LoginSession, fingerprint(token))
    if login_session is None or login_session.expires_at <= utc_now():
        request.session.clear()
        return None
    user = db.get(User, login_session.user_id)
    if user is None or not secrets.compare_digest(
        login_session.credential_fingerprint, fingerprint(user.password_hash)
    ):
        request.session.clear()
        return None
    return user


def csrf_token(request: Request) -> str:
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = secrets.token_urlsafe(32)
    return request.session["csrf_token"]


def verify_csrf(request: Request, submitted: str) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not secrets.compare_digest(expected.encode(), submitted.encode()):
        raise HTTPException(status_code=403, detail="This form has expired. Reload the page and try again.")


def limit_login_attempt(engine, username, address):
    # Count all attempts, not only failures: reservations precede expensive hashes.
    try:
        normalized = normalize_username(username)
    except ValueError:
        normalized = '<invalid>'
    account_key = 'a:' + fingerprint(normalized)
    connection_key = 'i:' + fingerprint(address)
    retry = 0
    with write_transaction(engine) as db:
        now = time()
        db.execute(delete(LoginAttemptWindow).where(LoginAttemptWindow.updated_at <= now - 60))
        windows = []
        for key, limit in ((connection_key, 120), (account_key, 10)):
            row = db.get(LoginAttemptWindow, key)
            recent = [stamp for stamp in row.timestamps if stamp > now - 60] if row else []
            windows.append((key, limit, row, recent))
        count = db.scalar(select(func.count()).select_from(LoginAttemptWindow))
        if count + sum(row is None for _, _, row, _ in windows) > 8192:
            retry = 60  # Fail closed; never evict an active limit to admit new keys.
        else:
            for key, limit, row, recent in windows:
                if len(recent) >= limit:
                    retry = max(retry, max(1, ceil(min(recent) + 60 - now)))
                    continue
                recent.append(now)
                if row is None:
                    db.add(LoginAttemptWindow(key=key, timestamps=recent, updated_at=now))
                else:
                    row.timestamps, row.updated_at = recent, now
    if retry:
        raise HTTPException(429, 'Too many login attempts. Please wait and try again.',
                            headers={'Retry-After': str(retry)})
