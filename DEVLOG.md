# EMP Dev Log

just keeping track of what i did and why, useful for the report too

---

## 05 Oct 2026

started the project today. set up the basic structure first — app.py, config.py, models.py.

decided to keep all 3 roles (admin, examiner, student) in one User table with a role column.
thought about having separate tables but that would mean writing 3 different login flows which
is unnecessary. role column + property check is cleaner.

wrote all the models: User, Course, Examination, Rubric, Slot, Booking, Evaluation.
the Examination has 4 date fields to control when examiners can create slots and when students
can book — these work together with the status field. status is like a state machine,
dates are a secondary check.

for slots i kept `available_seats` as a real column instead of counting bookings each time.
makes more sense — just decrement when someone books, increment on cancel.

flask-login handles sessions. put login_required and role decorators on all routes.
examiners need is_approved=True before they can log in — admin flips that.

admin gets seeded automatically when app starts (only once, checks first).

built login, register, logout and basic dashboards for all 3 roles.
register page has a small JS toggle to show/hide the department/phone fields for examiners —
only UI stuff, all real validation is in the route.

base template has navbar with role-based links, flash messages, footer.
made a custom CSS file — navy and amber color theme (wanted something different from the
default bootstrap blue).

next: admin CRUD for courses, exams, rubrics, examiner approval

---

## 09 Oct 2026

built out all the admin functionality today.

courses — basic CRUD, can't delete a course if it has exams under it (would break FK refs).
course code is readonly on edit because changing it after exams are linked would be messy.

examinations — CRUD with the 4 timeline date fields (slot_creation_start/end, booking_start/end).
kept a `set-status` route separate from edit, so admin explicitly moves the exam through stages
rather than just setting status in the edit form. feels cleaner and prevents accidents.

rubrics — added per-exam rubric criteria management. the exam detail page shows a running
total of max_marks across all criteria which is handy.

examiner approval — list shows pending/approved/deactivated with inline approve and
deactivate buttons. deactivate also sets is_approved=False so they can't log back in.

student list has a basic name/email search filter using ilike.

updated the navbar to have dropdowns for admin — Courses, Exams, Users. looks cleaner
than cramming everything into one level.

also added stub /slots and /bookings routes for examiner and student so the navbar links
don't 404 — those get built properly in Phase 3.

next: examiner slot creation + student slot booking (the core of the app)

---

## 11 Oct 2026

built the slot creation and booking system today — this is the main part of the whole project.

examiner side:
- `/examiner/slots` — lists all slots the examiner created, shows live booking count per slot
- `/examiner/slots/new` — create a slot, only shows exams currently in slot creation window
  (uses `is_slot_creation_open()` to filter, not just the status field)
- edit slot — only allowed if no students have booked yet. didn't want to let examiners
  change the date after students have committed to it.
- cancel slot — cancels all active bookings on that slot too, keeps data consistent

student side:
- `/student/exams` — shows only exams where booking is actually open (status + datetime check)
- `/student/exams/<id>/slots` — shows available slots for an exam
  checks if student already has a booking for this exam before showing the book button
- booking logic has 3 guards:
  1. is_booking_open() — time window check
  2. has_seats() — available_seats > 0
  3. duplicate check — JOIN query to see if student already booked same exam
  then: decrement available_seats, set status='Full' if it hits 0
- cancellation: restore available_seats, set slot back to 'Available' if it was 'Full'

also wired up all the placeholder href="#" buttons in student dashboard, and added
Browse Exams to the student navbar.

hit a weird bug while testing with overlapping dates:
when slot creation and booking dates overlapped, student wasn't seeing the exam under open exams
even though admin set status to 'Booking Open'.
dug into it and found two reasons:
1. was using `datetime.utcnow()` in is_booking_open() and is_slot_creation_open() — but the
   form sends local time (IST). UTC is 5.5 hours behind local time so python was comparing
   1:01 PM against 9:25 AM and thinking booking hadn't started yet! changed all utcnow calls
   to `datetime.now()` to stay consistent with local naive datetimes.
2. during overlap periods when admin flips status to 'Booking Open', examiners should still
   be able to add slots until slot_creation_end. updated `is_slot_creation_open()` to allow
   status in ('Slot Creation', 'Booking Open') as long as the slot creation end time hasn't passed.

next: evaluation (examiner marks students per rubric criterion)

---

## 15 Oct 2026

built the evaluation system today.

examiner side:
- `/examiner/evaluate` — shows all my slots that have bookings, grouped, with pending/completed status
- `/examiner/bookings/<id>/evaluate` — the actual evaluation form
  one row per rubric criterion, marks input with max shown inline, optional remarks field
  validates marks are within 0–max_marks range for each criterion
  if evaluation already exists for a criterion, it pre-fills (allows re-evaluation)
  on submit: creates one Evaluation row per rubric, marks booking as 'Completed',
  marks slot as 'Completed' (using slot.status = 'Completed')
- added Evaluate link to examiner navbar

student side:
- `/student/results/<booking_id>` — shows score breakdown per criterion with total and percentage
  only accessible once booking.status == 'Completed'
  shows eval_map dict to look up each rubric's evaluation quickly
- added View button in past bookings table (shows 'Pending' if not evaluated yet)

admin side:
- `/admin/exams/<id>/results` — all bookings for an exam in one table with marks and score %
- `/admin/bookings` — all bookings system-wide with student search
- added All Bookings to Users dropdown in navbar
- added View Results button on exam detail page

next: Phase 5 — admin power features (reschedule, change examiner, search across everything)

---

## 16 Oct 2026

phase 5 done today — admin management features.

two bugs i noticed and fixed first:
- examiner dashboard had `href="#"` on both the "create slot" and "view" buttons, so they did nothing.
  wired them to the actual routes (`examiner.slot_new` and `examiner.slot_bookings`). silly oversight.

main things added:

search on exams and examiners list:
- `/admin/exams?q=` filters by exam name using ilike
- `/admin/examiners?q=` filters by name or email — same pattern as students already had

all slots page:
- `/admin/slots` — see every slot across all exams in one table
- can filter by exam (dropdown) or search by examiner name
- "change examiner" button on each row takes you to the reassign form

reschedule booking:
- `/admin/bookings/<id>/reschedule` — shows current booking info + radio list of other available
  slots from the same exam
- on submit: old slot gets its seat back (and flips back to Available if it was Full),
  new slot loses a seat (flips to Full if needed)
- only shows slots that are 'Available' and have seats — keeps it clean

change slot examiner:
- `/admin/slots/<id>/change-examiner` — dropdown of approved+active examiners
- simple reassign, no complex logic needed

nav:
- added "All Slots" to the Users dropdown in navbar, right above All Bookings

---
