---
version: 1
slug: "app-templates-results-html"
primary_target: "app/templates/results.html"
related_targets: []
---

# Results page

Scope: the public /results page (app/templates/results.html), exported to GitHub Pages as results.html. Visitor mode: Experience.

Audience: universities and employers reading the site as the owner's CV. Job: see what results his students reached and what kinds of result they are. Proof: the nine results in app/result_content.py; quotes stay behind a click (owner decision). Constraints: CSP default-src 'self', static-exportable, keep #result-<id> anchors that the homepage links to.

## Direction contract

THESIS: The page is the course's file of score reports, filed under the kind of result each proves; it refuses the uniform grid of identical testimonial cards.

OWN-WORLD: The homepage's stationery: navy ground #131f2a, paper #eeecea reports with notched corners, Big Shoulders 800 numerals, Public Sans text, a 400–1600 rail on every report, lime only on the primary action and the rail marker.

STORY: The reviewer reads one sentence of real figures (nine students, average 1347.8, best 1470 above the tutor's 1430), then four files: Top totals, Math highlights, Started from scratch, Persistence paid off. They open a quote if curious, then return to the portfolio.

FIRST VIEWPORT: Shared portfolio bar with Results marked current. Left, the h1 "My students' results" at display size; right (columns 8–12), the one sentence of real figures. The owner removed the file index ("Filed by results section is not needed", 2026-11-03), so the first file, Top totals, begins inside the first viewport.

FORM: Filed by story, position 5 on my ordered list (dealt lead). seed:549ec6b0f601ce2e

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
