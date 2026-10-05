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
