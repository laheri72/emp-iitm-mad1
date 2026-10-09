from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import Examination, Booking

student_bp = Blueprint('student', __name__)


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student:
            flash('Student access only.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    open_exams = Examination.query.filter_by(status='Booking Open').all()

    my_bookings = Booking.query.filter_by(
        student_id=current_user.id,
        status='Booked'
    ).all()

    past_bookings = Booking.query.filter_by(
        student_id=current_user.id,
        status='Completed'
    ).all()

    return render_template('student/dashboard.html',
                           open_exams=open_exams,
                           my_bookings=my_bookings,
                           past_bookings=past_bookings)


@student_bp.route('/bookings')
@login_required
@student_required
def my_bookings():
    # full booking page comes in Phase 3
    return redirect(url_for('student.dashboard'))
