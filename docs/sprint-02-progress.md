# Next planned increment: class clarity and recovery

User authorized the next step after reviewing the sprint documents. Selected
SF-03 (3 provisional points): school-local dates and times. SF-04 and SF-05 remain
unselected; lifecycle and backup decisions still need refinement. Sprint 1 owner
review/retrospective is not claimed complete; no new calendar dates are assumed.

SF-03 implementation: Asia/Tashkent IANA conversion at rendering only. Lesson,
attendance, package-recorded dates and correction views show timezone and offset.
Storage, expiry, sorting and version comparisons stay UTC. tzdata is pinned for
Windows support. No database migration or recovery changes are required.

Verification: formatter tests cover naive UTC, aware UTC, another aware offset
and year rollover. Isolated route checks cover both roles, lesson detail/history,
renewals and correction preview with the same local date. Exact code expiry is
still rejected at the UTC boundary. All 122 tests passed in 33.965 seconds. A fictional teacher browser check
verified the expiry timezone and package dates at 390 x 844; Enter expanded the
package-date disclosure with visible focus. No balance changes were submitted.
SF-03: Done. Owner feedback is still welcome; SF-04 is next for refinement.
