# Examination Management Portal (EMP)

**App Dev 1 Project | IIT Madras BS Data Science Program | September 2026 Term**

---

## What is this?

EMP is a role-based web application for managing viva and project examinations.
Three types of users interact with the system:

- **Admin** — controls everything (courses, exams, timelines, examiner approvals)
- **Examiner** — creates time slots and evaluates students using rubrics
- **Student** — books examination slots and views published results

## Tech Stack

| Layer | Tool |
|---|---|
| Backend | Flask 3.1 |
| ORM | Flask-SQLAlchemy 3.1 (SQLite) |
| Auth | Flask-Login 0.6 |
| Frontend | Jinja2 + Bootstrap 5.3 |
| Language | Python 3.12 |

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py
```

Open http://127.0.0.1:5000 in your browser.

The admin account is seeded automatically on first run:
- **Email:** admin@emp.iitm.ac.in
- **Password:** Admin@1234

## Project Structure

```
EMP/
├── app.py           ← entry point, app factory, admin seed
├── config.py        ← config (secret key, DB path)
├── models.py        ← all SQLAlchemy models
├── requirements.txt
├── instance/        ← auto-created, holds emp.db
├── routes/
│   ├── auth.py      ← login / register / logout
│   ├── admin.py     ← admin routes
│   ├── examiner.py  ← examiner routes
│   └── student.py   ← student routes
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── admin/
│   ├── examiner/
│   └── student/
└── static/
    └── css/style.css
```

## Key Design Decisions

1. **Single User table with a `role` column** — keeps auth logic simple and easy to explain
2. **Exam status as a state machine** — `Draft → Slot Creation → Booking Open → Closed → Completed`
3. **`available_seats` on ExaminationSlot** — decremented/incremented atomically to prevent overbooking
4. **Examiner approval flow** — examiners are created with `is_approved=False`, admin flips it
5. **Programmatic DB creation** — `db.create_all()` in `app.py`, no manual SQLite setup needed

## Development Log

See [DEVLOG.md](DEVLOG.md) for day-by-day build notes.
