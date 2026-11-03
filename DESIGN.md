---
name: SAT Factory Portfolio
description: The tutor's CV and his students' results, printed as SAT Factory score-report stationery on a navy ground.
colors:
  ground: "#131f2a"
  ground-ink: "#eef1ec"
  ground-muted: "#b4bec4"
  paper: "#eeecea"
  surface: "#e1ded9"
  field: "#cdc3b6"
  ink: "#18212a"
  ink-hover: "#2c3a46"
  muted: "#575d5c"
  accent: "#c4f65d"
  accent-hover: "#d6ff86"
  accent-ink: "#131f2a"
typography:
  display:
    fontFamily: "Big Shoulders, Arial Narrow, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(4.25rem, 1rem + 7.4vw, 7.5rem)"
    fontWeight: 800
    lineHeight: 0.86
    letterSpacing: "-0.005em"
  headline:
    fontFamily: "Big Shoulders, Arial Narrow, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(2.5rem, 1.2rem + 5vw, 5.5rem)"
    fontWeight: 800
    lineHeight: 0.88
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Big Shoulders, Arial Narrow, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.7vw, 1.625rem)"
    fontWeight: 800
    lineHeight: 1
    fontFeature: "tnum"
  lead:
    fontFamily: "Public Sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.7vw, 1.625rem)"
    fontWeight: 400
    lineHeight: 1.35
  body:
    fontFamily: "Public Sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.0625rem, 1rem + 0.25vw, 1.1875rem)"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Public Sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(0.8125rem, 0.79rem + 0.1vw, 0.875rem)"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  none: "0px"
  round: "50%"
spacing:
  gutter: "clamp(16px, 2.2vw, 32px)"
  column: "24px"
  block: "clamp(72px, 9vw, 140px)"
  section: "clamp(96px, 12vw, 200px)"
  report: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0 22px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.accent-ink}"
  button-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "0 22px"
    height: "48px"
  button-ink-hover:
    backgroundColor: "{colors.ink-hover}"
  cell:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 22px"
    height: "72px"
  cell-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "0 22px"
    height: "72px"
  report:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "32px 32px 28px"
  report-section:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    padding: "12px 14px 14px"
  nav-link:
    textColor: "{colors.ground-ink}"
    typography: "{typography.body}"
---

# Design System: SAT Factory Portfolio

## Overview

**Creative North Star: "The Score Report Stationery"**

The public pages are printed as SAT Factory's own stationery: a score report, its ledger, torn quote slips, a letter with a tear-off stub, the back of the card. Every paper piece sits on one deep navy ground, and the figures on it are set the way an official report sets them, large condensed numerals over small plain captions. The page is a CV for universities and employers, so the stationery carries real numbers and nothing decorative stands in for them.

Density is low and deliberate. Paper pieces are large, separated by generous navy, and laid on a 12-column grid that lets headings and figures sit on opposite sides of the page. Depth comes from paper on ground, overlap and slight rotation, never from shadows. The one lime accent is a signal colour: the primary action, the marker on a score rail, keyboard focus and the current page.

This world covers the public portfolio pages only: the homepage (`app/templates/index.html`) and the results page (`app/templates/results.html`), sharing `app/static/portfolio.css`, `portfolio.js` and the portfolio bar and head partials, and exported as static files to GitHub Pages. The course portal (login, teacher and student dashboards, question practice) still uses the older `app/static/style.css` and its own stylesheets and is not part of this system.

**Key Characteristics:**
- Paper reports on a navy ground; ground, paper and one lime accent.
- Condensed 800-weight uppercase display over a plain humanist-grotesque text face.
- Every score sits on a 400 to 1600 rail with the tutor's 1430 marked on it.
- Square corners everywhere; edges are notched, torn or perforated like paper.
- Flat: no shadows, no radius, no gradients.
- Motion lifts paper into place and fills rails; the finished state is the reduced-motion state.

## Colors

One navy ground, warm off-white paper, one acid lime used as a signal.

### Primary
- **Score Lime** (accent): the primary action button in the bar and visit card, the marker dot at the end of every score rail, the target slider thumb, keyboard focus outlines on the ground, text selection, the underline of the current and hovered navigation link, and the letter's highlighted phrase. Its hover is **Bright Lime** (accent-hover). Text on lime is always the navy ground colour (accent-ink).

### Neutral
- **Report Navy** (ground): the page ground behind every paper piece, the perforation dots on the ledger and stub, and the footer behind the back card.
- **Ground Ink** (ground-ink): text set directly on the navy ground (bar links, the results intro, file headings).
- **Ground Slate** (ground-muted): secondary text on the ground, such as the one-sentence intro under each results file heading.
- **Report Paper** (paper): every paper piece: hero card, ledger, results table panel, reports, slips, letter, visit card, back card.
- **Paper Shade** (surface): recessed panels on paper: score boxes, section-score cells, empty rail tracks, secondary cells.
- **Desk Kraft** (field): the warmer field behind the fanned quote slips, the only band that is neither navy nor paper.
- **Report Ink** (ink): text and filled rails on paper, the ink button, the Math cell on the Math highlights file. Its hover is **Ink Lift** (ink-hover).
- **Caption Grey** (muted): captions, scale ends, labels and below-target rows on paper.

### Named Rules
**The Signal Lime Rule.** Lime marks something you can act on or a position on a scale: the primary action, a rail marker, focus, the current page. It is never a fill for panels, headings or body text, and never sits on paper as a background larger than a button.

**The Paper On Ground Rule.** Content lives on paper, paper lives on navy. Ink text never sits directly on the ground, and ground-ink text never sits on paper.

## Typography

**Display Font:** Big Shoulders 800 (with Arial Narrow, Helvetica Neue, Arial)
**Body Font:** Public Sans 400 and 600, plus 400 italic (with Helvetica Neue, Arial)

**Character:** A tall condensed poster numeral, the kind printed on score reports and scoreboards, paired with a plain public-service grotesque that reads like the fine print under the figure. Both are self-hosted woff2 files in `app/static/fonts/`.

### Hierarchy
- **Display** (800, uppercase): the page's name block: the tutor's name on the homepage card, "My students' results" on the results page. Set as two masked lines that rise in on load.
- **Headline** (800, uppercase, balanced): section and file headings ("My scores and theirs", "Top totals") and every large score figure (hero scores, report totals, slip scores, target output).
- **Title** (800, tabular numerals): secondary figures: section scores inside reports, totals in the results table.
- **Lead** (400): the one-sentence intros and panel copy, held to 26 to 40ch.
- **Body** (400, 600 for names and actions): running text, held to about 60ch in the letter and 62ch in quotes.
- **Label** (400): captions, scale ends, "out of 1600" units, table column heads, imprint.

### Named Rules
**The Numerals Speak Rule.** Every score is set in Big Shoulders 800 with tabular numerals and sits beside a small Public Sans caption that says what it is out of. A figure is never set in the text face, and a caption is never set in the display face.

**The Two Faces Rule.** Big Shoulders is for names, headings and numbers; Public Sans is for everything read as a sentence. Italic appears only on the letter's signature.

## Layout

A 12-column grid (24px column gap) inside a fluid gutter (16 to 32px). Headings take columns 1 to 5 or 1 to 6 and the matching sentence or figures take columns 7 or 8 to 12, so the page reads across rather than down. Results files lay reports in an auto-fit grid of 340px minimum tracks with a 24px gap; a file with a single report puts the heading left and the report right.

Bands are separated by block spacing (72 to 140px) and section spacing (96 to 200px). The portfolio bar is absolute over the first band: logo seal, centred navigation, action on the right.

Breakpoints: at 1023px the two-sided layouts collapse to one column and reports go two-up (an odd last report spans both); at 719px the phone gets its own composition (navigation moves to a second row, reports go one-up, the table drops its section columns for an inline split line, slips stack and alternate sides); at 379px the bar navigation drops to label size.

**The Real Positions Rule.** A rail fill, marker or dot is placed at its true position on the 400 to 1600 scale ((score - 400) / 12 percent). Because the Content Security Policy forbids inline style attributes, these per-element positions are set from `portfolio.js`, never written into the markup.

## Elevation & Depth

Flat. There are no shadows anywhere in the world; the stylesheet actively clears the portal shell's shadows. Depth is tonal and physical: paper on navy, recessed Paper Shade panels on paper, the hero card cropped by the bottom of the screen, slips fanned with small rotations (-4 to 5 degrees) and overlapping, the back card uncovered as the page lifts.

**The No Shadow Rule.** Separation is paper against ground or shade against paper. A drop shadow, glow or blur never stands in for it.

## Shapes

Corners are square (0px) on every paper piece, button, cell and panel. Round (50%) is reserved for the SF logo seals, rail markers and target dots. Paper edges carry the stationery: a 45-degree notch on the top corners of report cards (28px on the hero card, 20px on reports and the results back card), a zigzag tear on both edges of quote slips, a perforated dotted rule (10px on the ledger, 7px on the letter stub) in ground navy, a scalloped stub bottom, and a scalloped top on the homepage back card.

**The Paper Edge Rule.** A paper piece is shaped by how paper is cut, notched, torn or perforated, never by rounding its corners.

## Components

### Buttons
Blunt rectangles that read as stamped labels.
- **Shape:** square (0px), 48px tall (44px on phones), 22px side padding, 600 weight.
- **Primary:** Score Lime with navy text; one per view, in the bar or a card's foot.
- **Hover / Focus:** Bright Lime on hover (pointer devices only); press scales to 0.97 over 140ms; focus is a 3px lime outline offset 4px on the ground, ink on paper.
- **Ink:** Report Ink with paper text, used where lime would sit on paper (the letter stub); hover to Ink Lift.

### Cells
Full-bleed action tiles at the foot of the platform panel: 72px tall (60px on phones), Paper Shade or Report Ink, 600-weight label; hover darkens the tile (Ink Lift on the ink cell) and press scales to 0.98.

### Links and Tabs
- **Text links:** underlined at 35% of current colour (0.07em thick, 0.22em offset), full colour on hover.
- **Tabs:** plain muted text with a 3px underline that becomes ink when selected; 44px minimum height.

### Navigation
The portfolio bar: logo seal (56px, 44px on phones) on a paper disc, then links in body size with an invisible underline that turns lime on hover and stays lime on the current page (`aria-current`), then the primary button. Shared by both pages through `portfolio_header.html`.

### Score Report (signature)
The results page's unit and the homepage hero's sibling. A notched paper card (32px padding, 26px/22px on phones) holding, in order: the student's name (lead, 600), the total in headline numerals with a small "total" caption, the 400 to 1600 rail (8px Paper Shade track, ink fill ending in a lime dot ringed in ink, a thin muted tick at the tutor's 1430 labelled "my 1430"), two section cells in Paper Shade, an optional one-line proof, and an optional quote behind a "Read the story" disclosure with a rotating chevron. The Math cell turns Report Ink in the Math highlights file. Rails fill on scroll; without JavaScript the scale is hidden rather than shown empty.

### Results Table and Target Slider
The homepage ranks every total in a right-aligned tabular table with a 6px ink bar per row; rows below the visitor's chosen target fade to Caption Grey. The target slider is a transparent range input over a Paper Shade track of dots, with a lime thumb ringed in ink.

## Do's and Don'ts

### Do:
- **Do** put every new public surface on Report Navy with its content on Report Paper pieces, and keep the tokens on `:root` in `portfolio.css`.
- **Do** set every score in Big Shoulders 800 with tabular numerals, beside a Public Sans caption saying what it is out of.
- **Do** place any score on the 400 to 1600 rail at its true position, with the tutor's 1430 marked.
- **Do** keep lime to actions, rail markers, focus, selection and the current page.
- **Do** shape paper by notching, tearing or perforating it, with square corners.
- **Do** self-host every font, image and script and set per-element positions from JavaScript: the Content Security Policy is `default-src 'self'`, with no inline style attributes and no inline scripts.
- **Do** make the reduced-motion state the finished state: entrances, fills and rolls only run under `prefers-reduced-motion: no-preference`.

### Don't:
- **Don't** round the corners of paper pieces, buttons or cells.
- **Don't** add drop shadows, glows or blurs for depth.
- **Don't** fill panels, headings or body text with lime, or put lime on paper larger than a button.
- **Don't** set figures in the text face or sentences in the display face.
- **Don't** apply this system to the course portal pages, which still run on `app/static/style.css`.
