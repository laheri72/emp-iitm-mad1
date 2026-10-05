# EMP — Development Log

Day-by-day notes on what was built and why.
This is a personal record of the project's progress.

---

## Day 1 — 05 Oct 2026

**What I set up today:**
- Created the project folder structure
- Wrote `config.py` — kept it minimal, just the DB URI and secret key
- Wrote `models.py` — decided to go with a single `User` table for all three roles
  (admin, examiner, student) using a `role` column. This is simpler than three
  separate tables and still gives me the access control I need with just a property check.
- Added helper methods like `set_password()`, `check_password()`, `is_slot_creation_open()`
  directly on the model — keeps the route logic clean
- Wrote `app.py` with an app factory pattern and `seed_admin()` — the admin gets
  created only once, on first run
- Set up Flask-Login and registered all four blueprints
- Built auth routes: login (with role-based redirect), register (student/examiner only),
  logout
- Made base template with responsive navbar and flash message area
- Made login and register templates (register has JS toggle for examiner fields — UI only,
  not core logic, so allowed per spec)
- Made placeholder dashboards for all three roles
- Wrote custom CSS with a navy+amber color theme

**Design decisions:**
- Examination status is a proper state machine string. I check it explicitly in
  `is_slot_creation_open()` and `is_booking_open()` instead of just checking dates.
  This way the admin has explicit control, and dates are a secondary guard.
- `available_seats` lives directly on the slot row — decrement on booking,
  increment on cancel. Simple and fast.

**Next up:**
- Admin: Course CRUD, Examination CRUD, Rubric management, Examiner approval

---
