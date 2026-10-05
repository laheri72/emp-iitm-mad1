from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from models import db, Examination, Booking, ExaminationSlot

student_bp = Blueprint('student', __name__)


# ── access control ────────────────────────────────────────────────────────────
def student_required(f):
    """Only registered students get access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student:
            flash('Student access only.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── dashboard ─────────────────────────────────────────────────────────────────
@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    # exams currently open for booking
    open_exams = Examination.query.filter_by(status='Booking Open').all()

    # this student's active bookings
    my_bookings = Booking.query.filter_by(
        student_id=current_user.id,
        status='Booked'
    ).all()

    # completed bookings where results might be published
    past_bookings = Booking.query.filter_by(
        student_id=current_user.id,
        status='Completed'
    ).all()

    return render_template('student/dashboard.html',
                           open_exams=open_exams,
                           my_bookings=my_bookings,
                           past_bookings=past_bookings)
