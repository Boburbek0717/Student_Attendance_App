# Backup and recovery — SF-05 local tooling

This chunk implements and tests mechanisms using fictional data only. It does
not activate real-data backups, external access, or scheduling. Owner delegated
storage selection; proposed local operational location is
`%LOCALAPPDATA%\SAT Factory\backups`, outside the repository. A protected copy
outside the laptop and its access controls remain a release prerequisite.

## Safe rehearsal

From the repository, run:

```powershell
.\.venv\Scripts\python.exe scripts/recovery_drill.py
.\.venv\Scripts\python.exe scripts/verify.py --pattern test_backup.py
```

The drill creates a temporary fictional class, runs its workflows, backs it up,
restores to a different file, verifies it, and deletes only its temporary data.
It never opens the working database or the local session secret.
`docs/recovery-evidence.json` records measured local recovery and snapshot age.
Snapshot age is the age of the backup used by this drill, not a promise about
future data loss. The previous full suite passed 151 tests in 44.223s; three
additional backup review regressions then passed in the focused 11-test suite.

## Explicit operator commands

These examples name fictional paths. Replace them only after authorizing the
actual source, destination, permissions and operation. No command has a default
source database.

```powershell
.\.venv\Scripts\python.exe scripts/backup.py backup --source C:\SAT-Demo\fictional.sqlite3 --destination C:\SAT-Demo\backups --keep 14
.\.venv\Scripts\python.exe scripts/backup.py validate --bundle C:\SAT-Demo\backups\BUNDLE-NAME
.\.venv\Scripts\python.exe scripts/backup.py restore --bundle C:\SAT-Demo\backups\BUNDLE-NAME --destination C:\SAT-Demo\recovered.sqlite3
```

Success is JSON with status, counts and destination. Failure returns exit code 1
and a generic operator message without SQL, codes, names or credentials. Treat
any failure as requiring investigation; an unsuccessful retention cleanup can
leave a successful backup present. Inspect/validate it before retrying. The
backup is a directory containing database.sqlite3 and manifest.json; keep both.
It uses SQLite's backup API, not a raw copy of an actively written database.
Copies are validated before publication. Restore requires a new destination,
rejects existing files/sidecars and destination symlinks, and explicitly refuses
the checkout's attendance.db. Publication uses an atomic no-clobber hard link;
the destination filesystem must support it (verified on this laptop).

Retention counts successful versions, not calendar days. `--keep 14` retains
14 validated versions **per source path identity**; omit it to retain everything.
It only prunes recognized tool-created bundles, preserving unrelated files,
incomplete/corrupt bundles and backups from other source paths. If daily and
pre-upgrade backups share one folder, they both count toward the limit. Use
separate destinations for daily and pre-upgrade archives if 14 daily versions
must always remain. No daily scheduler is installed or enabled.

## What is checked

SQLite integrity and foreign keys; expected table/column layout; attendance,
enrollment, teacher and roster relationships; row counts and content digests;
independent SQL versus application balance calculation. Restore preserves all
non-session table content, including packages, original attendance, correction
history, lesson closure and retry receipts. All login_sessions are deleted before
the recovered database is published. A test uses the same signing secret and a
copied old cookie to prove restored access is rejected.

Manifests contain counts and hashes, not individual balances. Both files remain
private: the database contains account password hashes and course records.
Checksums detect damage, not malicious replacement of both files. Use restricted
OS access and encrypted storage/off-device transport chosen by the owner. This
tool does not create encryption keys, choose cloud recipients or apply ACLs.

Eleven tests cover realistic recovery, copied-cookie revocation, retention and
source isolation, existing targets/sidecars, checksum damage, foreign-key damage,
active WAL/uncommitted writes, simulated copy failure, missing sources/schema,
malformed timestamps, and a mocked Windows symlink boundary. Real symlink creation
permissions, disk-full hardware failure and off-device loss have not been tested.

## Upgrade and rollback

1. Pause attendance writes and announce maintenance. Make and validate a
   pre-upgrade bundle; retain its matching Git commit and dependency lock list.
2. Restore into a separate staging destination using the backup's matching code.
   Review the new release's migration instructions before starting new code on it.
   Current schema changes are additive; never assume arbitrary downgrades are safe.
3. Verify the new release against that staging copy, including accounts, permanent
   closures, history and balances. This chunk has no schema migration.
4. On a failed release, stop its process. Restore the pre-upgrade bundle to another
   new destination with the matching old code; verify and switch the configured
   database path only in the later deployment procedure. Do not overwrite files
   in place. Data entered after that snapshot will not be in the rollback copy;
   owner must reconcile it before reopening attendance.
5. Require fresh logins. Never copy old session secrets from production into a
   rehearsal. Do not run pre-SF-04 code on a database containing finished lessons.

Deployment-specific switching, service restart and external recovery will be
prepared in a later chunk. Local drill success does not establish a production
recovery SLA or complete the operational portion of SF-05.

Implementation references: Python sqlite3 Connection.backup
(https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup) and
SQLAlchemy SQLite pooling
(https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#disabling-connection-pooling-for-file-databases).
