from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import User, Course, Examination, ExaminationSlot, Booking

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access only.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    stats = {
        'total_courses': Course.query.count(),
        'total_exams': Examination.query.count(),
        'total_examiners': User.query.filter_by(role='examiner').count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_slots': ExaminationSlot.query.count(),
        'total_bookings': Booking.query.count(),
        'pending_examiners': User.query.filter_by(role='examiner', is_approved=False).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)
