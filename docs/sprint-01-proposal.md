# Sprint 1 — Proposed, not started

Goal: a teacher can record a real class accurately even when students share Wi-Fi
or cannot use their phone.

Suggested duration: two weeks; dates and capacity to be chosen during Planning.
No velocity established. Selection is a forecast, not a delivery promise.

| Candidate | Scope | Provisional points |
| --- | --- | --- |
| SF-01 | Classroom-safe login protection | 5 |
| SF-02 | Audited manual attendance and reversal | 8 |

Total 13 relative points. Split SF-02 during Planning if it does not fit capacity;
do not sacrifice audit history or duplicate protection. SF-03 is next in order,
not an implied stretch commitment. All candidates remain Backlog until selected.

## Implementation plan for refinement

SF-01: reproduce shared-IP burst; agree thresholds and storage bounds; implement
account-aware and connection-abuse protection; test 30 valid accounts, guessing,
restart and parallel workers; demonstrate recovery and document behavior.

SF-02: agree historical/inactive-membership rules and balance semantics; design
audit records and migration; rehearse recovery; add teacher preview/confirmation;
update history/status/accounting readers; test correction after renewal, debt,
duplicates, unauthorized requests and simultaneous code/manual submissions.

## Review demonstration

- Thirty fictional students can sign in from one simulated classroom address.
- Code attendance and retry produce exactly one debit.
- Teacher marks a student present with reason; history and balance agree. A later
  code submission by the same student cannot double-charge.
- Teacher reverses a mistake, restoring the correct credit with retained evidence;
  repeated reversal does not credit twice.
- Unauthorized/stale requests cannot alter history or balances.

## Later goals, subject to reprioritization

Sprint 2 theme: class clarity and recovery (SF-03, SF-04, SF-05 as capacity allows).
Sprint 3 theme: first approved anonymous results and enquiry route (SF-06–08,
dependent on owner-supplied content). These are not fixed scope or dates.
Public deployment requires SF-13 readiness and an explicit release decision.
