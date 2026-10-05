from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from models import db, ExaminationSlot, Booking, Examination

examiner_bp = Blueprint('examiner', __name__)


# ── access control ────────────────────────────────────────────────────────────
def examiner_required(f):
    """Only approved examiners can get through."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_examiner:
            flash('Examiner access only.', 'danger')
            return redirect(url_for('auth.login'))
        if not current_user.is_approved:
            flash('Your account is still pending admin approval.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── dashboard ─────────────────────────────────────────────────────────────────
@examiner_bp.route('/dashboard')
@login_required
@examiner_required
def dashboard():
    # fetch slots this examiner has created
    my_slots = ExaminationSlot.query.filter_by(examiner_id=current_user.id).all()

    # count how many students are booked into my slots
    my_slot_ids = [s.id for s in my_slots]
    booked_count = Booking.query.filter(
        Booking.slot_id.in_(my_slot_ids),
        Booking.status == 'Booked'
    ).count() if my_slot_ids else 0

    # pending evaluations = bookings in my completed slots not yet evaluated
    # (we'll wire this up properly in Phase 4)
    pending_evals = 0

    return render_template('examiner/dashboard.html',
                           my_slots=my_slots,
                           booked_count=booked_count,
                           pending_evals=pending_evals)
