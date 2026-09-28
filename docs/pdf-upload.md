# Teacher PDF import — 2026-09-28

QB-07 bounded first release (and the review/duplicate portion of QB-06).
Teacher Question library and Create question now link to Import PDF. Upload, inspect
all extracted questions/answers, then explicitly Import as drafts or Publish.
No AI service, external upload or token usage occurs. File extraction uses pypdf
6.19.0 and Pillow 12.3.0 pinned in requirements.txt. The maintained upstream
[installation documentation](https://pypdf.readthedocs.io/en/stable/user/installation.html)
confirms Python support and the image dependency. `pip check` passed. This is a
compatibility check, not a claim of a complete dependency vulnerability audit.

## Supported scope

- Text-based SQB PSAT 8/9 Boundaries and PSAT/NMSQT & PSAT 10 Transitions answer
  exports, with the exact known structure and recognized difficulty icons.
- Up to 10 MB and 100 pages. Auto-detection tries these two profiles per page;
  uploaded content cannot select arbitrary commands or filesystem paths.
- Source assessment/domain/category, passage, A–D, key and rationale are preserved
  as text. Original typographic styling may be lost. Scans, unknown layouts/images,
  duplicate source IDs and incomplete pages are flagged. Any flag blocks the whole
  import; no silent partial batch. New PDF formats require a new verified profile.
- Categories are automatic. Source file name, PDF page, source ID and SHA-256 are
  recorded. Optional permission notes remain optional per the owner's decision.
- Exact matches to an existing source ID/content are skipped regardless of status.
  A duplicate draft/archived item is never republished by batch import. Different
  content for the same source ID blocks the batch for manual review.

## Safety and lifetime

Upload and confirmation require teacher authentication and CSRF. A review belongs
to the teacher's current login, is inaccessible to students/other logins, and holds
answers only in authenticated review pages. Confirmation reauthenticates under the
SQLite write lock; taxonomy/questions/publication audit are one atomic transaction.
Repeated confirmation returns the original outcome; re-upload detects stored source
IDs, including across restarts. Browser-submitted question content is never trusted:
confirmation accepts only the opaque review token and explicit action.

Only the exact POST /teacher/questions/import route gets a 10 MB + 64 KB multipart
body envelope. Question new/edit forms allow 192 KB for URL-encoded Unicode within their existing
field limits; other forms retain 16 KB. Multipart has one file/two-field bounds.
Parsing runs in a disposable child process with a 25-second timeout, no application
or database imports, suppressed parser output, a private random temporary directory,
and a 2 MB result limit. Files are removed after parsing, including failure/timeout.
This is process separation, not an OS security sandbox or a hard memory quota.

At most one parser and eight reviews exist per application process. Reviews are
kept in memory for 20 minutes, removed lazily on subsequent access, and lost at
restart. An expired/missing review requires re-upload and never causes publication.
Use the current single-process local launcher. Multi-worker hosting would need a
shared durable review store/sticky routing before enabling this feature there.
No background jobs, integrations, new schema version or automatic real-data import.

## Verification

- `.venv/Scripts/python.exe scripts/verify.py --pattern test_question_import.py`:
  nine passed (review-only upload, draft/publish, duplicates/conflicts, rollback,
  concurrent confirmations, role/CSRF/login isolation, expiry, escaping, narrow body
  limit, malformed PDF and parser timeout).
- `.venv/Scripts/python.exe scripts/verify.py`: 210 passed, 71.361 seconds.
- `.venv/Scripts/python.exe -m pip check`: no broken requirements.
- `git diff --check`: passed.
- Local disposable rehearsal `output/pdf-upload-check/rehearse.py`: actual supplied
  files uploaded through HTTP routes, 30 + 33 published in temporary DB, both repeated
  uploads recognized every duplicate. 63 total, working DB not read or modified.
- Browser inspection of the rendered isolated upload/review pages: desktop and
  390x844 viewport; keyboard Return expands a review; passage/options stack without
  clipping. This is simulated viewport testing, not a real-phone acceptance test.

No existing question bank records were reimported during development. Owner
acceptance remains pending. Next: try Import PDF from the teacher library; add more
format profiles only after representative sample verification.
