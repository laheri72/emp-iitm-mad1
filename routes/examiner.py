from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import ExaminationSlot, Booking

examiner_bp = Blueprint('examiner', __name__)


def examiner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_examiner:
            flash('Examiner access only.', 'danger')
            return redirect(url_for('auth.login'))
        if not current_user.is_approved:
            flash('Account is pending admin approval.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@examiner_bp.route('/dashboard')
@login_required
@examiner_required
def dashboard():
    my_slots = ExaminationSlot.query.filter_by(examiner_id=current_user.id).all()

    my_slot_ids = [s.id for s in my_slots]
    booked_count = Booking.query.filter(
        Booking.slot_id.in_(my_slot_ids),
        Booking.status == 'Booked'
    ).count() if my_slot_ids else 0

    # will calculate properly once evaluation is built
    pending_evals = 0

    return render_template('examiner/dashboard.html',
                           my_slots=my_slots,
                           booked_count=booked_count,
                           pending_evals=pending_evals)
