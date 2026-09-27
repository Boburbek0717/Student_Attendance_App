# SAT Factory design refinement

Research checkpoint: 2026-09-26. Baseline: 0c2ad75. No application changes in this checkpoint.

## Priority and evidence

Owner selected visual refinement, UI/UX and coherent design quality for the next few sessions. Deployment preparation is deferred. Work in small increments: inspect, research, explain the proposed direction, implement, then review across pages. This supersedes the previous handover's SF-13 next action.

Inspected the shared layout, styles, motion, homepage, results, login/student guidance, teacher dashboard, lesson attendance, student management, renewal, completion and history templates. Reviewed existing fictional mobile lesson and public teacher-section screenshots. These are saved previews, not a fresh browser audit of every current page. No live database or account access. Browser interaction, contrast measurements, zoom and cross-page visual checks are required before accepting a redesign.

## Assessment

Retain the graphite, warm paper and lime identity, supplied logo, Score Tickets and portrait-free teacher section. Refine and extend the design system rather than replace the stack or visual identity.

The largest issues are hierarchy and accumulated inconsistency:

- The same public header serves working pages. A large logo and Results link take space without helping a teacher run a lesson.
- Teacher setup forms precede classes. Expanded student/package detail makes the dashboard grow with every enrollment.
- Narrow working-page containers, long combined headings and repeated full timestamps push actions down on phones. The saved fictional lesson screenshot demonstrates this; not every page has been newly measured.
- Typography names Inter but does not load it in the shared layout. Rendering depends on installed fonts. Spacing, colors and radii mix a small token set with many one-off values; earlier design-exploration selectors remain in the stylesheet. Verify usage before removing any.
- Plain roster lists mix names, timestamps and actions without clear columns. Student search results use a full card for very little information.
- Homepage content is focused, but the large dark portal banner competes with results and teacher credibility. Repeated Results links can be simplified.
- Useful foundations already exist: labelled inputs, skip link, focus outlines, server-rendered fallback, error/status roles, reduced-motion handling, confirmation previews and native disclosure controls. Preserve and extend them.

## Research and applicable patterns

Sources reviewed 2026-09-26; recommendations below are our interpretation for SAT Factory, not endorsements or usability-test results.

| Reference | Apply here | Avoid importing |
| --- | --- | --- |
| [Linear's March 2026 refresh](https://linear.app/now/behind-the-latest-design-refresh) | Predictable action placement; navigation visually quieter than the task; fewer competing borders/icons | Dark theme, tiny controls or an issue-tracker layout by default |
| [Atlassian spacing](https://atlassian.design/foundations/spacing/) and [typography](https://atlassian.design/foundations/typography/) | Named spacing/type roles reused across pages; proximity communicates relationships | A wholesale enterprise component framework |
| [Canvas dashboard guide](https://community.instructure.com/en/kb/articles/664620-how-do-i-use-the-dashboard) | Distinguish course overview from actionable daily tasks; make the next class action easy to find | Assignments, calendar or customizable widgets that our product does not need |
| [Moodle navigation overview](https://moodle.com/news/find-your-way-around-moodle-4-0/) | Searchable course navigation and secondary information disclosed when needed | Its full navigation structure; this is a historical design reference, not a current feature audit |
| [Carbon table guidance, v10](https://v10.carbondesignsystem.com/components/data-table/usage/) | Consistent row density, aligned data, table-level search and clear row actions | Importing the older component package; current Carbon URL was inaccessible during research |
| [GOV.UK error summary](https://design-system.service.gov.uk/components/error-summary/) | Multi-field forms need actionable linked errors as well as errors at inputs | Its visual brand; simple one-field check-in does not need an oversized summary |
| [W3C target-size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) | Review small inline actions as well as buttons; aim for comfortable 44px primary touch controls | Assuming every WCAG criterion is satisfied merely because buttons are large |

## Proposed shared foundations

- Color: graphite text, neutral white work surfaces, warm paper surrounding public content, restrained lime emphasis. Separate semantic success/warning/error colors with text labels. Measure combinations; lime is not body text on white.
- Typography: one consistent sans family. Body 16px equivalent; secondary 14px; working headings approximately 24–32px; larger editorial headings reserved for public pages. Use rem and fluid scales. Tabular numerals for scores, counts and balances. Avoid excessive uppercase labels and tight tracking on long names.
- Spacing: reusable 4/8/12/16/24/32/48/64 scale expressed in rem, with optical adjustments where demonstrated. Denser record rows, more space between distinct tasks.
- Shape: mostly 4–8px corners, thin intentional borders, minimal shadows. Score Ticket treatment stays distinctive; do not put every paragraph inside a card.
- Layout: shared brand and components, two appropriate page shells. Public pages are editorial; authenticated pages emphasize navigation and work. Start with compact labelled top navigation, not a large sidebar with few destinations. Keep mobile navigation visible and allow whole items to wrap.
- Components: page heading/action row, primary/secondary/destructive buttons, labelled form field with hint/error, status badge, notice, record row/table, empty state, confirmation summary and disclosure. Implement as CSS tokens and Jinja partials/macros where reuse warrants it.
- Motion: roughly 120–180ms feedback for genuine state changes. Preserve reduced-motion support. Reassess decorative entrances; attendance updates must not move focus or obscure a code. No artificial loading delays.

## Page-by-page direction

| Page/section | Main weakness | Proposed direction and benefit |
| --- | --- | --- |
| Homepage | Attention split between hero, results and strong portal banner | Bring proof close to the headline; align featured cards; make portal access a quieter utility. Keep teacher compact. Clearer visitor path without extra slogans. Contact action requires the owner's destination. |
| Results | Long names, different story lengths and repeated label treatments need consistent rhythm | Standardize ticket name/score/breakdown spacing and story disclosure; keep full names readable. No filtering UI until content volume justifies it. |
| Login | Generic shared header occupies limited phone space | Compact branded entry, clear form hierarchy, support guidance adjacent but secondary; strengthen inline errors while keeping generic authentication failures. |
| Student dashboard | Instructions, packages and history compete with check-in | Check-in first, clear success/duplicate state, per-group balance next, history afterward. Preserve single paste-friendly code input; avoid six separate input boxes. |
| Teacher dashboard (SF-10) | Setup dominates daily work; every member expands the overview | Current/recent lesson actions first, concise group rows/cards, setup via clearly labelled secondary destinations. Preserve error discoverability when forms move. Do not imply a timetable exists. |
| Lesson attendance | Long heading/status prose before roster; row actions hard to scan | Separate group name from lesson metadata; one clear lifecycle/code panel, visible counts and aligned roster rows. Keep Close check-in distinct from Finish permanently. Compact local time with timezone stated clearly; full audit detail remains available. |
| Student list/profile | Large low-information cards; many competing management forms | Search toolbar and compact rows; profile grouped into account, enrollments/balances and history. Password reset and balance correction retain explicit consequences and reasons. |
| Renewal/correction/finish | Related pages lack a common decision layout | Shared student/group context, before/after summary where applicable, one primary confirmation and clear return link. Permanent actions stay unmistakable. Never shorten away business consequences. |
| History | Wide tables and verbose repeated metadata | Clear headers, aligned numeric data and consistently formatted local dates. On mobile compare a labelled row layout with the existing scroll region; retain all information and semantic relationships. |
| Empty/error/loading states | Some plain messages lack a direct next action | Distinguish empty dataset from no search match; offer the relevant create/reset action. Preserve entered non-secret values on validation. Show pending, saved and reconnecting feedback only when real; preserve safe retry behavior. |

## Tools and dependency decision

Use existing CSS, Jinja and small JavaScript enhancements. A new frontend framework, component runtime or animation library does not solve the observed hierarchy problems and is not justified.

[Lucide documentation](https://lucide.dev/guide/) supports a consistent SVG icon approach; its [release feed](https://github.com/lucide-icons/lucide/releases) was reviewed as maintenance evidence. It is a candidate, not installed or version-selected. If icons are needed, verify the chosen release/license then vendor only a small reviewed SVG set with attribution. Use icons with labels, not as replacements for unclear wording. Avoid CDN/runtime dependency for a few icons.

Keep the system font for the first comparison. A self-hosted font may improve consistency, but first compare actual screenshots, license, file size and fallback behavior. No font purchase or external font request is currently warranted.

Figma is optional for side-by-side layout studies; browser prototypes are the final authority for this Jinja product. No additional plugin, external service or design subscription is needed for the first slice. Before any future dependency addition, record maintenance/release evidence, stack fit, license, payload and the problem it solves.

## Incremental sequence and acceptance

1. First implementation: public header and homepage hierarchy, backed by the minimum shared spacing/type/color tokens. Preserve content and Score Tickets. Compare isolated fictional/static previews at 320, 390, 768 and 1280px. Review related results/login pages for shared-style regressions. This is a proposal, not implemented here.
2. Results and login: apply the established components, refine forms and disclosure states.
3. Teacher dashboard and lesson roster: SF-10 with focused SF-17 checks. Separate functional navigation changes from purely visual changes when useful.
4. Student dashboard, profiles, history and confirmation flows: common patterns, same state language.

For each slice record before/after evidence, rationale, relevant regression checks and unresolved findings. Use fictional data: zero/one/30 students, long names, empty/error/success states, debt, expired/finished lessons and interrupted polling. Check keyboard order and focus, 200% text zoom/reflow, contrast, touch targets, reduced motion and no page-level horizontal overflow. Horizontal scrolling must be intentional and discoverable. Do not remove required warnings or alter authorization, CSRF, retry identities, immutable completion or balance calculations for layout convenience.

No real-device, assistive-technology or owner acceptance claim is made by this audit. No UI implementation or new test run occurred. Existing unrelated untracked artifacts remain untouched.

## Slice 1 implementation — 2026-09-26

Starting commit 555d739. Implemented public header/homepage hierarchy; ready for
owner review. Public header is a shared Jinja partial with labelled navigation and
Results current-page indication. Home/results share scoped foundation tokens and
a quieter page surface. Working-page layout and login remain unchanged.

Homepage removes duplicate hero actions and decorative eyebrow, retains supplied
headline/results/teacher content, aligns score cards and replaces the dominant
dark portal banner with a compact utility section. No dependency or backend changes.
Keyboard review found off-screen focus in the mobile card strip; focus now scrolls
the card into view immediately without animation. Reduced-motion handling remains.

Verification:
- `.venv/Scripts/python.exe scripts/verify.py --pattern test_auth.py`: 24 passed,
  7.030s, isolated session secret and live engine guard.
- `node --check app/static/motion.js`: passed.
- Static Jinja-only preview on loopback 8767, no app/database/security imports;
  owner-supplied public content and fictional signed-in context only.
- Homepage inspected at 320/390/768/1280px with no page-level horizontal overflow;
  mobile strip intentionally scrolls. Results/login/signed-in header also checked
  at responsive sizes, with a separate 768px Results visual review.
- 320px home with root text size doubled: reflows without page overflow. This is
  a controlled text-enlargement fixture, not a completed cross-browser zoom audit.
- Keyboard card focus visible after fix (third card x=51.6..284.6 at 320px),
  Enter on the second result opens `/results#result-9`. New nav targets 44px high.
- Contrast: graphite on public background 13.61:1; muted text 5.93:1 on background,
  6.21:1 on cards; existing focus color on white 5.40:1.

No real-phone or screen-reader acceptance claimed. No live server restarted or
database read. Next slice: Results card/story rhythm and Login form hierarchy,
using this foundation. SF-10 dashboard restructuring remains a later increment.

## Slice 2 — Results and Login, 2026-09-27

Completed the interrupted slice starting from 8d4f0e0. Results now uses consistent
name/score spacing, quieter ticket labels, readable story controls and a visible
outline for a card opened by its anchor. All nine supplied results and story text
are preserved. Login uses the shared public header and a focused form column;
credential issuance, recovery guidance, CSRF and error associations are retained.
No backend or dependency changes. Accessible story names include the visible label
and the student's name for keyboard, voice and assistive-technology context.

Verification: isolated `scripts/verify.py --pattern test_auth.py` passed 24 tests
in 6.967s; `scripts/verify.py --pattern test_onboarding.py` passed 2 in 1.829s,
both using `.venv/Scripts/python.exe`. Static Jinja-only browser preview: Login
390px and Results 320/1280px, keyboard Enter expansion for account help and student
story. Both pages at 320px with root text doubled remained within page width
(305px content width); this is a fixture, not real-device/browser zoom acceptance.
No real records or live server used. Owner visual review remains pending.
Next bounded slice: SF-10 teacher dashboard, classes before setup, compact group
information and explicit access to setup; preserve visible validation errors.
