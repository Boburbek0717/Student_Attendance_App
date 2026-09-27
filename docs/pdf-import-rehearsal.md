# PDF import rehearsal — 2026-09-27

Owner requested a test using `SQB PSAT 8 and 9 Boundaries (excluded) ANSWERS.pdf`.
This is a bounded QB-07 investigation layered on the QB-02 draft editor, not a
general production PDF uploader or completion of QB-06/QB-07.

## Outcome

- Source: 30 pages, SHA-256
  `e386ca968c399da4df30a404ce3318126558ab2f0aa28921deba728524028aec`.
- 30 unique question IDs extracted; zero rejected pages after the reviewed
  difficulty-icon handling was added. 4 easy, 9 medium, 17 hard.
- Assessment is **PSAT 8/9**, Reading and Writing, Standard English Conventions,
  Boundaries. A separate PSAT bank/skill was created only in the temporary database.
  The editor/preview now display assessment context instead of labelling all skills SAT.
- All 30 candidates were saved through the real authenticated teacher HTTP route,
  as drafts with no published revision. Stored passage, stem, explanation, all
  120 choices, correct-answer choice IDs, difficulty, classification and provenance
  reconciled to the candidates. Required source IDs and PDF page numbers preserved.
- Independent pdfplumber extraction cross-checked all 30 pages against pypdf's
  candidates: all 120 choice strings and 30 correct-answer letters matched after
  whitespace/ligature normalization. No mismatch pages. This supplements the
  rendered-page spot checks; it does not claim a full human content review.
- SQLite backup and separate restore preserved fingerprints of all imported data.
  Recovery took 0.035 seconds in this local run; one test login session revoked.
  This is not a production recovery-time commitment.
- Temporary databases and credentials were removed on completion. Working database,
  existing accounts and original PDF untouched. No operational import or publication.

## Extraction and visual checks

`scripts/extract_sqb_pdf.py` uses pypdf in the existing bundled PDF runtime; no
application dependency was added. The profile accepts only this SQB answer-page
structure. It matches repeated question IDs, four labelled choices, a known answer
letter, explicit difficulty and the expected assessment/skill. Unsupported pages,
duplicate IDs and unknown images are quarantined rather than guessed.

Initial conservative extraction rejected all pages because each has a difficulty
indicator image. Rendered pages 1, 2, 15 and 30 were visually inspected. The three
46×15 difficulty indicators are recognized by exact image-content hashes and
checked against textual difficulty; arbitrary diagrams are not discarded.

PDF line wraps and typographic ligatures (`ﬁ`, `ﬃ`, etc.) are normalized. Punctuation,
capitalization, em dashes, accents and blank markers are preserved. Original italics
and page typography are not retained by this plain-text slice. Review against the
source remains necessary before publication; no owner approval has been claimed.

Local artifacts (not committed): `output/pdf-import-test/review-candidates.json`,
`output/pdf-import-test/review-1/report.json` and `review.html`. The review HTML
contains all 30 passages/choices with expandable keys/rationales, a split desktop
layout and stacked mobile layout. Browser check counted 30 questions and 120
choices; no horizontal overflow in the inspected desktop viewport. The browser
review page is an artifact, not a live teacher dashboard or student exercise.

## Reproduce without live access

Run extraction with the bundled Python interpreter containing pypdf:

```powershell
& 'C:\Users\noral\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/extract_sqb_pdf.py --source '<explicit PDF path>' --output '<new candidate JSON path>'
```

Then use the project's interpreter; the runner installs the default-engine and
secret-path isolation guards before importing the app:

```powershell
.\.venv\Scripts\python.exe scripts/rehearse_question_import.py --candidates output/pdf-import-test/review-candidates.json --output '<new review directory>'
.\.venv\Scripts\python.exe scripts/verify.py --pattern test_sqb_pdf_extract.py
.\.venv\Scripts\python.exe scripts/verify.py --pattern test_question_authoring.py
```

Extractor refuses an existing output file; rehearsal refuses an existing output
directory and never accepts a database destination. It creates a fictional teacher,
tests draft insertion, reconciles recovery and removes its temporary database.
Use a new output name to repeat a run; keep previous evidence intact.
Source content and review artifacts remain local and should not be committed.

Latest focused checks: four PDF/rehearsal tests passed (0.580s) and ten authoring
tests passed (5.277s). Before this PDF slice, the full isolated suite passed all
179 tests (58.240s). No claim of a new full-suite run after this slice.

## Remaining work

Human review and publication rights remain pending. This profile does not handle
scanned PDFs, OCR, diagrams, arbitrary multi-column exports, cross-page questions,
math layout or upload resource isolation. Do not expose this development CLI as
an unrestricted web upload service. A production import needs staged jobs,
review/approval, transactional batches, persistent duplicate identity across
imports, upload limits and audited publication. Current duplicate rejection is
within the candidate document; no real import has occurred.
