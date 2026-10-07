# PDF-to-question workflow (zero AI tokens for supported files)

## Everyday use

1. Sign in as a teacher. Open Question library → Import PDF.
2. Upload the original text-based SQB answer PDF (10 MB / 100 pages maximum).
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
- The upload tool auto-detects these layouts per page.
- Difficulty is copied from explicit Easy/Medium/Hard metadata. Recognized image
  indicators must agree with it. Missing or unknown difficulty is not estimated.
- The correct answer comes from the answer key; the script does not solve questions.

Scans, other layouts, unfamiliar images/diagrams, missing metadata and ambiguous
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
