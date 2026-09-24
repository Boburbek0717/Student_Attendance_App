# Stage 1: class workflow — SF-04 delivered

Owner decision: Finish permanently; corrections only afterward. No finished or
cancelled lesson can reopen. Cancellation requires no original attendance, including
reversed entries. Actor, note and timestamp persist in lesson_closures. Writes are
serialized with check-in/corrections, checked for stale previews and atomic on failure.

Recent started lessons remain visible after code expiry/closure. Future lessons do
not become recent. Starting a new class is explicitly distinct from reopening an
unfinished one. Absence is provisional while code check-in is open. Finishing does
not debit absence or change balances. Legacy roster fallback freezes on finish.

Verification: full-suite result recorded below. New tests cover expired/recent
selection and group isolation; code/reopen rejection after finish; subsequent
corrections; cancellation and reversed history; stale previews; role/CSRF checks;
concurrent cancellation/check-in; rollback on closure audit failure; additive schema
upgrade and SQLite backup/restore integrity; legacy roster preservation. Browser
check on fictional data at 390 x 844 verified keyboard confirmation, readable
warning, permanent status, no reopen action and retained correction link.

SF-04 complete. SF-09 automatic refresh, connection feedback and retry clarity is
next; this does not mark all Stage 1 work complete. No public deployment performed.

Full suite: 134 tests passed in 35.717 seconds. Live SQLite backup verified before
restarting to apply the additive table. No real class was finished or cancelled.
