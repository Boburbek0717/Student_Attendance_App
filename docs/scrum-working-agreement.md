# SAT Factory — Scrum working agreement

Effective for future development from 2026-09-23.

Framework reference: [official Scrum Guide](https://scrumguides.org/scrum-guide.html).
Scrum uses a Product Goal, ordered Product Backlog, Sprint Goal and Sprint Backlog,
and a usable Increment meeting a Definition of Done. A Sprint includes Planning,
daily 15-minute inspection by Developers, Review and Retrospective. Product Owner
orders work; Developers plan delivery; Scrum Master supports an effective process.
Sprints are one month or less. Scope can adapt without endangering the Sprint Goal.

## Project choices

You are the proposed Product Owner: choose outcomes, order priorities and review
the product. Codex supports implementation, evidence gathering and facilitation;
it cannot replace human stakeholder feedback or a staffed team. Assign the human
Scrum Master accountability if a team forms. For now use a lightweight Scrum-based
working arrangement.

Start with two-week sprints; agree dates and actual capacity during Planning.
No velocity established. Points are relative estimates, not hours. Suggested
small-project sessions: 30–45 minute Planning, 30 minute Review, 15–20 minute
Retrospective. These durations are local choices, not official requirements.

Before future implementation consult product-backlog.md, identify the story and
acceptance criteria, and relate work to the selected Sprint Goal. Record completed
work, evidence and next obstacles. No scheduled reminders or background runs are
created by this agreement.

Board: Backlog → Selected → In progress → Review → Done. Mark genuine external
blockers with reason and owner. Prefer one implementation story in progress.
Update estimates/order when evidence changes and retain the rationale.

Triage urgent defects immediately, record them and discuss scope tradeoffs. Do
not discard authorized work or add repetitive approvals for routine fixes.
Before selection, clarify the problem, criteria, dependencies, required decisions
and a feasible slice. This checklist is our refinement aid, not an extra Scrum artifact.

## Definition of Done

- Acceptance criteria demonstrated; no unresolved critical regression introduced.
- Relevant tests pass. Balance/attendance writes exercise permissions, duplicate
  and stale requests, rollback and concurrency where appropriate.
- UI checked on mobile and keyboard, with clear errors and status feedback.
- Data changes have migration, backup and recovery checks on isolated data;
  existing records preserved.
- No secrets, private student records or fabricated result claims leak publicly.
- Documentation and backlog reflect actual behavior; reviewable changes committed.
- Increment runs locally. Public release has separate deployment prerequisites.

## Review and retrospective

Demonstrate agreed scenarios, record owner feedback, distinguish done from
incomplete work and reorder backlog. Definition of Done is not replaced by an
approval ceremony. Record one thing to keep, one problem and one process
improvement with an owner for the next sprint.

Track observed completion, carryover, escaped defects and scenario success.
Establish a baseline before promising delivery or usability targets.
