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


## SF-09 delivery and interrupted-work review — 2026-09-25

Completed the previously uncommitted attendance feedback work. Teacher lesson
pages poll their canonical GET address, including when a rejected close/reopen
POST leaves the browser on an action URL. Offline, hidden and keyboard-focus
pauses preserve the existing view. Intentional aborts no longer overwrite the
paused message with a connection error. Without JavaScript the page accurately
instructs the teacher to refresh manually.

Receipts and attendance commit together. Repeated forms confirm the same record
without another charge, even after permanent finish. Ownership and current session
checks precede receipt access; reversed attendance cannot be restored by retry.
The form token must survive the retry; a fresh page has a new token, and history
remains the fallback for older closed codes. Polling is teacher-only and never
calls the student attempt limiter. Attempts themselves remain rate limited.

Verification: 142 isolated Python tests; five Node polling tests. Scenarios cover
simultaneous retries, lost response followed by finish, wrong student/session,
reversed attendance, readable throttling, atomic rollback and additive upgrade
with SQLite backup/restore. Polling checks cover the action-URL regression,
keyboard focus, offline/hidden pauses, reconnect, bounded backoff and expired
sessions. Earlier browser verification on fictional data demonstrated an automatic
Present 0 -> 1 / Absent 1 -> 0 update and the 390 x 844 layout. Keyboard pause and
network transitions are checked with a simulated DOM, not real-device network
emulation. Real classroom Wi-Fi testing and owner review remain pending.

No production data is used by tests. Startup adds only check_in_receipts; take a
SQLite-consistent backup before restarting an existing installation. No automated
backup schedule or public deployment is included. SF-09 is implemented; SF-05 is
next in the roadmap, subject to the owner's storage decision.
