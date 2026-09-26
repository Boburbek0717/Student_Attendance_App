"""Explicit SQLite backup/recovery. No default source and no live app import."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FORMAT = 1


def read_only(path):
    path = Path(path).resolve(strict=True)
    return sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)


def copy_database(source, destination):
    deadline = time.monotonic() + 30
    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError('Database snapshot timed out; retry when storage is available.')
    with closing(read_only(source)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst, pages=256, progress=progress, sleep=0.05)


def digest_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_database(path):
    """Validate physical/FK/schema/business integrity without printing records."""
    from app.database import Base, make_engine
    from app import models
    from app.packages import enrollment_balance
    from sqlalchemy.orm import Session
    with closing(read_only(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('SQLite integrity validation failed.')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign key validation failed.')
        actual = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if actual != set(Base.metadata.tables):
            raise ValueError('Schema differs from this release; restore using matching code.')
        counts, fingerprints = {}, {}
        for name, table in sorted(Base.metadata.tables.items()):
            columns = {row[1] for row in db.execute(f'PRAGMA table_info("{name}")')}
            if columns != set(table.columns.keys()):
                raise ValueError('Schema columns differ from this release.')
            rows = db.execute(f'SELECT * FROM "{name}" ORDER BY ' + ','.join('"'+c.name+'"' for c in table.primary_key.columns)).fetchall()
            counts[name] = len(rows)
            if name != 'login_sessions':
                fingerprints[name] = hashlib.sha256(json.dumps(rows, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
        violations = [
            "SELECT 1 FROM attendance a JOIN lessons l ON l.id=a.lesson_id JOIN enrollments e ON e.id=a.enrollment_id WHERE l.group_id != e.group_id LIMIT 1",
            "SELECT 1 FROM enrollments e JOIN users u ON u.id=e.student_id WHERE u.role != 'student' LIMIT 1",
            "SELECT 1 FROM attendance_corrections c JOIN users u ON u.id=c.teacher_id WHERE u.role != 'teacher' LIMIT 1",
            "SELECT 1 FROM balance_adjustments c JOIN users u ON u.id=c.teacher_id WHERE u.role != 'teacher' LIMIT 1",
            "SELECT 1 FROM lesson_closures c JOIN users u ON u.id=c.teacher_id WHERE u.role != 'teacher' LIMIT 1",
            "SELECT 1 FROM lesson_roster r JOIN lessons l ON l.id=r.lesson_id JOIN enrollments e ON e.id=r.enrollment_id WHERE l.group_id != e.group_id LIMIT 1",
        ]
        if any(db.execute(query).fetchone() for query in violations):
            raise ValueError('Business relationship validation failed.')
        ids = [row[0] for row in db.execute('SELECT id FROM enrollments ORDER BY id')]
        expected = dict(db.execute('''SELECT e.id,
            COALESCE((SELECT SUM(p.lesson_limit) FROM lesson_packages p WHERE p.enrollment_id=e.id),0)
            + COALESCE((SELECT SUM(b.delta) FROM balance_adjustments b WHERE b.enrollment_id=e.id),0)
            - (SELECT COUNT(*) FROM attendance a WHERE a.enrollment_id=e.id AND
              COALESCE((SELECT c.action FROM attendance_corrections c WHERE c.attendance_id=a.id ORDER BY c.id DESC LIMIT 1),'code') != 'reverse')
            FROM enrollments e'''))
    engine = make_engine(str(Path(path).resolve()))
    try:
        with Session(engine) as session:
            balances = {key: enrollment_balance(session, key)['balance'] for key in ids}
        if expected != balances:
            raise ValueError('Balance reconciliation failed.')
    finally:
        engine.dispose()
    return dict(counts=counts, fingerprints=fingerprints, balance_count=len(balances), balance_digest=hashlib.sha256(json.dumps(balances, sort_keys=True).encode()).hexdigest())


def backup(source, destination, keep=None):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if keep is not None and keep < 1:
        raise ValueError('Retention must keep at least one successful backup.')
    destination.mkdir(parents=True, exist_ok=True)
    # Unpublished staging directory; only complete, validated bundles get a managed name.
    stage = Path(tempfile.mkdtemp(prefix='.incomplete-', dir=destination))
    try:
        started = datetime.now(timezone.utc)
        copy_database(source, stage / 'database.sqlite3')
        summary = inspect_database(stage / 'database.sqlite3')
        source_id = hashlib.sha256(os.path.normcase(str(source)).encode()).hexdigest()
        manifest = dict(format=FORMAT, source_id=source_id, snapshot_started_utc=started.isoformat(), completed_utc=datetime.now(timezone.utc).isoformat(),
                        sha256=digest_file(stage / 'database.sqlite3'), **summary)
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        final = destination / ('sat-backup-' + started.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex)
        stage.rename(final)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    removed = prune(destination, keep, source_id) if keep is not None else 0
    return dict(bundle=str(final), retained_policy=keep, removed=removed, counts=summary['counts'])


def load_bundle(bundle):
    bundle = Path(bundle).resolve(strict=True)
    if (bundle / 'manifest.json').is_symlink() or (bundle / 'database.sqlite3').is_symlink():
        raise ValueError('Linked backup files are not supported.')
    data = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Invalid backup manifest.')
    try:
        started = datetime.fromisoformat(data['snapshot_started_utc'])
        completed = datetime.fromisoformat(data['completed_utc'])
        if started.utcoffset() is None or completed.utcoffset() is None or completed < started:
            raise ValueError('Invalid backup times.')
        if started > datetime.now(timezone.utc):
            raise ValueError('Backup time is in the future; verify the system clock.')
        if not isinstance(data['source_id'], str) or len(data['source_id']) != 64:
            raise ValueError('Invalid source identity.')
    except (KeyError, TypeError) as error:
        raise ValueError('Incomplete backup manifest.') from error
    if data.get('format') != FORMAT or data.get('sha256') != digest_file(bundle / 'database.sqlite3'):
        raise ValueError('Backup format or checksum validation failed.')
    summary = inspect_database(bundle / 'database.sqlite3')
    if any(data.get(key) != summary[key] for key in ('counts', 'fingerprints', 'balance_count', 'balance_digest')):
        raise ValueError('Backup record reconciliation failed.')
    return data


def prune(destination, keep, source_id):
    """Only delete valid tool-owned bundles; unrelated/incomplete files are untouched."""
    import re
    root = Path(destination).resolve()
    candidates = []
    for item in root.iterdir():
        if item.is_symlink() or not re.fullmatch(r'sat-backup-\d{8}T\d{6}-[a-f0-9]{32}', item.name):
            continue
        if not item.is_dir() or item.resolve().parent != root:
            continue
        if {p.name for p in item.iterdir()} != {'database.sqlite3', 'manifest.json'}:
            continue
        try:
            info = load_bundle(item)
            if info['source_id'] == source_id:
                candidates.append((info['snapshot_started_utc'], item.name, item))
        except (ValueError, OSError, sqlite3.Error, KeyError):
            continue
    obsolete = sorted(candidates, reverse=True)[keep:]
    for _, _, item in obsolete:
        # Resolved targets are checked immediately before recursive deletion.
        if item.is_symlink() or item.resolve().parent != root:
            raise ValueError('Retention path changed; nothing further removed.')
        shutil.rmtree(item)
    return len(obsolete)


def restore(bundle, destination):
    begin = time.perf_counter()
    info = load_bundle(bundle)
    requested = Path(destination).absolute()
    if requested.is_symlink():
        raise ValueError('Restore destination cannot be a symbolic link.')
    target = requested.resolve()
    if target == ROOT / 'attendance.db':
        raise ValueError('Restore must use a separate destination, never the working database.')
    if any(Path(str(target)+suffix).exists() for suffix in ('', '-wal', '-shm', '-journal')):
        raise ValueError('Restore destination or sidecar already exists; choose a new path.')
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix='.restore-', suffix='.sqlite3', dir=target.parent)
    os.close(descriptor)
    temporary = Path(filename)
    try:
        copy_database(Path(bundle) / 'database.sqlite3', temporary)
        with closing(sqlite3.connect(temporary)) as db:
            db.execute('DELETE FROM login_sessions')
            db.commit()
        result = inspect_database(temporary)
        if result['fingerprints'] != info['fingerprints'] or result['balance_digest'] != info['balance_digest']:
            raise ValueError('Restored records or balances differ.')
        if result['counts']['login_sessions'] != 0:
            raise ValueError('Restored session revocation failed.')
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(info['snapshot_started_utc'])).total_seconds()
        report = dict(destination=str(target), recovery_seconds=round(time.perf_counter()-begin, 3),
                      snapshot_age_seconds=round(age, 3), revoked_sessions=info['counts']['login_sessions'],
                      counts=result['counts'], balances_reconciled=result['balance_count'])
        # Atomic no-clobber publication on the destination filesystem.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    b = commands.add_parser('backup')
    b.add_argument('--source', type=Path, required=True)
    b.add_argument('--destination', type=Path, required=True)
    b.add_argument('--keep', type=int, help='Keep N validated versions; omitted means never prune')
    r = commands.add_parser('restore')
    r.add_argument('--bundle', type=Path, required=True)
    r.add_argument('--destination', type=Path, required=True)
    v = commands.add_parser('validate')
    v.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'backup':
            result = backup(args.source, args.destination, args.keep)
        elif args.command == 'restore':
            result = restore(args.bundle, args.destination)
        else:
            result = {'counts': load_bundle(args.bundle)['counts']}
        print(json.dumps({'status':'success', **result}, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error, TimeoutError) as error:
        # Do not echo SQL, rows, passwords, codes or tracebacks in operator output.
        print(json.dumps({'status':'failed', 'error':type(error).__name__,
                          'message':'Operation failed. Check paths, free space, matching release and backup integrity. No existing restore destination was overwritten.'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
