# PDF-to-question workflow (zero AI tokens for supported files)

## Everyday use

1. Sign in as a teacher. Open Question library → Import PDF.
2. Upload the original text-based SQB answer PDF (10 MB / 200 pages maximum).
3. Review the extracted question count, duplicate count and flagged pages.
   Expand questions to check passage, prompt, A–D choices, supplied answer,
   difficulty and explanation against the PDF.
4. Choose Import as drafts or Publish new questions. Publication is public.

No chat, API key, paid AI service or model call is involved. Routine use consumes
zero AI tokens; local CPU/memory are still used. The application creates the
supported category when needed. It records the teacher and source question ID,
page and file hash. Exact duplicates are skipped. Conflicting source IDs block the
import rather than replacing existing questions. One transaction prevents partial
imports. Repeating the same confirmation does not create another batch.

## What is supported

- SQB PSAT 8/9 Boundaries answer exports.
- SQB PSAT/NMSQT & PSAT 10 Transitions answer exports.
- Additional SQB-style exports with explicit assessment/section/domain/skill metadata,
  without hardcoded category names or prompt wording.
- Numbered text worksheets with `Question 1`, `Q1` or `1.` boundaries; A�D
  choices labelled `A.`, `A)` or `(A)` on separate lines; multiple questions per page.
- Inline `Answer: C` / `Correct Answer: C`, or separate `Answer Key` / `Answers`
  pages containing one numbered answer per line, such as `1. C`.
- Explicit colon-labelled Assessment, Section (or Test), Domain, Category (or
  Skill/Topic), Difficulty (or Question Difficulty). Page-level labels before the
  first question provide defaults; question-level labels override them.
- New category names are created automatically from these labels; exact existing
  category names in the same hierarchy are reused. No parser configuration needed.
- The upload tool tries exact SQB profiles first, then the labelled-text fallback.
  Known profiles retain stricter format checks.
- Difficulty is copied from explicit Easy/Medium/Hard metadata. Recognized image
  indicators must agree with it. Missing or unknown difficulty is not estimated.
- The correct answer comes from the answer key; the script does not solve questions.

Scans, unrecognized layouts, unfamiliar images/diagrams, missing metadata and ambiguous
pages are flagged. Any flagged page blocks that batch's import. No silent skipping.
Use manual entry or add a tested parser profile for a recurring new format. Layout
styling such as italics is not guaranteed; review is still necessary.

## Optional offline extraction

From the repository, with the project virtual environment:

```powershell
.venv\Scripts\python.exe scripts/extract_sqb_pdf.py --source "C:\path\questions.pdf" --output "C:\path\review.json"
```

Auto-detection is the default. An explicit --profile remains available. The output
file must be new; it will not overwrite an existing review. This command extracts
only and does not import or publish. Use the teacher upload workflow for database
writes. Avoid putting PDF text or extracted JSON into chat unless a parser failure
actually requires investigation.

## Efficient support for future formats

Keep the deterministic path first. For a new format, supply a representative
sample once, create a format-specific parser and regression fixtures, then reuse
it for future uploads without AI. Scanned PDFs would need an additional OCR path;
OCR and general math/diagram extraction are not implemented. An optional AI fallback
could later process only flagged pages, but would need explicit implementation and
cost/privacy choices. Do not send entire supported PDFs to a model each time.

## Operational limits

Reviews expire after 20 minutes or server restart; re-upload when expired. Original
uploads are removed after parsing. The parser has size/page/output/time bounds and
runs in a separate process. Public portfolio-demo hosting intentionally disables
teacher imports. Use the normal teacher application. Verify permission to distribute
the source material before public publication.


The fallback preserves line breaks and keeps unlabeled passage/prompt text together
in the question stem rather than guessing where to split it. Explicit Passage:
and Prompt: labels are separated. Explanation:/Rationale: is optional. Generated
source IDs hash the extracted prompt/passage/options; changing those creates a new
identity, while changing only answers/difficulty triggers a duplicate conflict.
Separate keys require unique question numbers throughout the document. Extra key
entries are flagged. Numbered worksheet questions spanning pages, columns with ambiguous reading
order, missing labels and image-based mathematics still require review. This is
broader automatic recognition, not a claim of universal PDF understanding.


## Command of Evidence reference standard (2026-10-07)

SQB question records now span up to four consecutive pages, grouped from each
Question ID header to the next. One metadata block is required and is normalized
from its extracted position (including before a continued answer). Matching source
IDs remain mandatory. The upload limit is 200 pages, with existing 10 MB, 25-second
worker and 2 MB output bounds retained. The review shows source page ranges.
Scientific initials such as O. vulgaris no longer count as extra SQB choices.

Measured on the supplied 101-page PSAT 10 Command of Evidence PDF: 70 records
accounted for, 35 text candidates and 35 graph/table-reference flags. The real
subprocess upload parser finished in 7.0 seconds locally. No questions imported.
Graph/table references are conservatively blocked because text cannot preserve the
visual information. This file remains blocked for batch publication: attached visual
storage, rendering, backup and access handling are not implemented in this slice.
Clear visual-content diagnostics replace the generic unsupported-format message.
This is multi-page SQB support, not complete visual-question support.

## Image attachments and visual PDF exclusions — 2026-10-08

Question authoring now accepts one validated PNG/JPEG/WebP raster, up to 4 MB,
8 million pixels and 6,000 pixels per side. A description is required. Image bytes
are re-encoded without metadata and stored in SQLite with immutable media records;
question revisions retain the original image when an attachment is replaced/removed.
Published question images are public, matching guest practice access; draft images
remain restricted. Assigned historical images remain accessible to active recipients.

PDF extraction lists detected visual questions as skipped instead of flattening
or silently importing their text. Supported text candidates still require teacher
review. Graph/table detection is conservative and does not constitute OCR or faithful
automatic visual extraction. Add skipped questions manually with the image field.

Schema v5 adds qb_media_content and media immutability triggers. Backups include
image bytes and verify their size/hash. Before a real upgrade, follow backup-recovery.md;
no existing live database was migrated for this repository checkpoint.
