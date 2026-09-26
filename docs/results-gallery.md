# Results gallery — 2026-09-26

Owner selected the recommended homepage/gallery split. This is a public layout
change, not completion of SF-06/SF-07 publishing tools. Public owner-supplied
content now lives in app/result_content.py; no private student database data is
exposed. Stable numeric IDs preserve featured-to-gallery links.

The homepage has three selected results (Javohir, Go'zal, Shukrona), their totals
and section scores. Desktop shows all three; mobile uses native horizontal scroll
and snap with a visible swipe hint and focusable card links. No autoplay or extra
JavaScript. The old /#results anchor remains a valid featured-results destination.
The dedicated /results page displays all nine tickets, two across on desktop and
one on phones. Original quotations use native expandable details; editorial
highlights remain clearly labeled. Existing order is retained without inventing
test dates. No enquiry destination has been provided, so no contact was invented.

Verification: public homepage and results route checks with temporary SQLite and
a disposable session secret; checked card counts, featured anchors, preserved
scores, escaped names and original quotation disclosures. All 142 existing tests
passed in 40.109 seconds with live database access blocked. Browser inspection
covered desktop cards, 390px mobile horizontal layout without page overflow,
keyboard card navigation and Enter expanding a story. Preview server restarted
using the owner's desktop launcher. No remote push or public deployment.

## Compact teacher introduction — 2026-09-26

Owner retained the original visual identity and requested a smaller teacher
section without a portrait. Removed the placeholder, repeated biography blocks
and duplicate results link. Name, teaching start year, university background,
SAT/IELTS credentials and one short teaching statement remain. Credentials sit
beside the introduction on wider screens and below it on phones.

Verification: direct Jinja rendering retained all teacher credentials and three
featured results with no portrait markup. Browser inspection covered the normal
viewport and a 390px phone viewport, with no page overflow. Diff whitespace check
passed. Backend behavior is unchanged; no live database was accessed by tests.
