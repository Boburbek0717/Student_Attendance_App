from contextlib import closing
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts.backup import backup, restore, load_bundle, inspect_database, copy_database, digest_file
from scripts.rehearse import rehearse, fields


class BackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture.cleanup)
        rehearse(cls.fixture.name)
        cls.source = Path(cls.fixture.name) / 'fictional.db'

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def bundle(self, source=None, keep=None):
        return Path(backup(source or self.source, self.root / 'backups', keep)['bundle'])

    def test_recovery_reconciles_history_and_rejects_old_cookie(self):
        from app.database import make_engine
        from app.main import create_app
        from app.security import password_hasher
        from app.models import User
        from sqlalchemy.orm import Session
        from fastapi.testclient import TestClient
        import secrets
        source = self.root / 'source.sqlite3'
        copy_database(self.source, source)
        engine = make_engine(str(source))
        secret, password = secrets.token_hex(32), secrets.token_urlsafe(24)
        with Session(engine) as db:
            db.get(User, 1).password_hash = password_hasher.hash(password); db.commit()
        with TestClient(create_app(engine, secret)) as client:
            data = fields(client.get('/login'))
            data.update(username='demo-teacher', password=password)
            self.assertEqual(client.post('/login', data=data, follow_redirects=False).status_code, 303)
            cookie = client.cookies.get('attendance_session')
            bundle = self.bundle(source)
        destination = self.root / 'restored.sqlite3'
        result = restore(bundle, destination)
        self.assertEqual(result['counts']['login_sessions'], 0)
        self.assertEqual(result['balances_reconciled'], 30)
        self.assertGreater(result['revoked_sessions'], 0)
        self.assertEqual(inspect_database(source)['fingerprints'], inspect_database(destination)['fingerprints'])
        restored_engine = make_engine(str(destination))
        with TestClient(create_app(restored_engine, secret)) as recovered:
            recovered.cookies.set('attendance_session', cookie)
            self.assertEqual(recovered.get('/teacher', follow_redirects=False).status_code, 303)

    def test_retention_keeps_only_configured_valid_versions(self):
        first = self.bundle(keep=2)
        second = self.bundle(keep=2)
        unrelated = second.parent / 'owner-notes.txt'; unrelated.write_text('keep me')
        third = self.bundle(keep=2)
        self.assertFalse(first.exists())
        self.assertTrue(second.exists() and third.exists() and unrelated.exists())
        with self.assertRaises(ValueError):
            self.bundle(keep=0)

    def test_retention_preserves_other_source_and_manifest_hides_balances(self):
        first = self.bundle(keep=1)
        other = self.root / 'other.sqlite3'; copy_database(self.source, other)
        self.bundle(other, keep=1)
        self.assertTrue(first.exists())
        manifest = json.loads((first / 'manifest.json').read_text(encoding='utf-8'))
        self.assertNotIn('balances', manifest)
        self.assertEqual(manifest['balance_count'], 30)

    def test_bad_timestamp_fails_before_publishing_restore(self):
        bundle = self.bundle()
        path = bundle / 'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        for stamp in ('not-a-time', '2020-01-01T00:00:00', None):
            manifest['snapshot_started_utc'] = stamp
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaises(ValueError): restore(bundle, self.root / 'restored.sqlite3')
            self.assertFalse((self.root / 'restored.sqlite3').exists())

    def test_restore_rejects_dangling_symlink_before_resolving(self):
        bundle = self.bundle()
        target = self.root / 'linked.sqlite3'
        # Windows may not grant symlink creation; mock only this boundary.
        with patch.object(Path, 'is_symlink', lambda p: p == target):
            with self.assertRaisesRegex(ValueError, 'symbolic link'): restore(bundle, target)
        self.assertFalse(target.exists())

    def test_existing_destination_and_sidecars_are_preserved(self):
        bundle = self.bundle()
        target = self.root / 'existing.sqlite3'; target.write_bytes(b'untouched')
        with self.assertRaises(ValueError): restore(bundle, target)
        self.assertEqual(target.read_bytes(), b'untouched')
        target = self.root / 'sidecar.sqlite3'
        Path(str(target)+'-wal').write_bytes(b'untouched')
        with self.assertRaises(ValueError): restore(bundle, target)
        self.assertFalse(target.exists())

    def test_corruption_or_manifest_mismatch_fails_without_destination(self):
        bundle = self.bundle()
        database = bundle / 'database.sqlite3'
        with database.open('ab') as stream: stream.write(b'changed')
        with self.assertRaises(ValueError): restore(bundle, self.root / 'restore.sqlite3')
        self.assertFalse((self.root / 'restore.sqlite3').exists())

    def test_foreign_key_corruption_is_rejected(self):
        bad = self.root / 'bad.sqlite3'; copy_database(self.source, bad)
        with closing(sqlite3.connect(bad)) as db:
            db.execute('UPDATE enrollments SET student_id=99999 WHERE id=1'); db.commit()
        with self.assertRaisesRegex(ValueError, 'Foreign key'): self.bundle(bad)
        self.assertEqual(list((self.root / 'backups').iterdir()), [])

    def test_active_wal_writer_snapshot_excludes_uncommitted_changes(self):
        source = self.root / 'wal.sqlite3'; copy_database(self.source, source)
        with closing(sqlite3.connect(source)) as writer:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute("UPDATE groups SET name='Committed fictional group' WHERE id=1"); writer.commit()
            writer.execute("UPDATE groups SET name='Uncommitted fictional group' WHERE id=1")
            bundle = self.bundle(source)
            with closing(sqlite3.connect(bundle / 'database.sqlite3')) as snapshot:
                self.assertEqual(snapshot.execute('SELECT name FROM groups WHERE id=1').fetchone()[0], 'Committed fictional group')
            writer.rollback()

    def test_copy_failure_publishes_no_bundle_and_preserves_source(self):
        before = digest_file(self.source)
        with patch('scripts.backup.copy_database', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError): self.bundle()
        self.assertEqual(list((self.root / 'backups').iterdir()), [])
        self.assertEqual(digest_file(self.source), before)

    def test_schema_mismatch_and_missing_source_fail_closed(self):
        with self.assertRaises(FileNotFoundError): self.bundle(self.root / 'missing.sqlite3')
        self.assertFalse((self.root / 'missing.sqlite3').exists())
        bad = self.root / 'old.sqlite3'; copy_database(self.source, bad)
        with closing(sqlite3.connect(bad)) as db:
            db.execute('DROP TABLE check_in_receipts'); db.commit()
        with self.assertRaisesRegex(ValueError, 'Schema'): self.bundle(bad)
