from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, date, time
from models import db, Examination, ExaminationSlot, Booking

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


# ── dashboard ─────────────────────────────────────────────────────────────────

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


# ── slots ─────────────────────────────────────────────────────────────────────

@examiner_bp.route('/slots')
@login_required
@examiner_required
def my_slots():
    slots = ExaminationSlot.query.filter_by(
        examiner_id=current_user.id
    ).order_by(ExaminationSlot.date.desc()).all()
    return render_template('examiner/slots.html', slots=slots)


@examiner_bp.route('/slots/new', methods=['GET', 'POST'])
@login_required
@examiner_required
def slot_new():
    # show exams in slot creation window (even if booking is already open if dates overlap)
    open_exams = [e for e in Examination.query.filter(
        Examination.status.in_(['Slot Creation', 'Booking Open'])
    ).all() if e.is_slot_creation_open()]

    if request.method == 'POST':
        exam_id = request.form.get('exam_id')
        slot_date = request.form.get('date')
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')
        capacity = int(request.form.get('max_capacity', 1))

        if not exam_id or not slot_date or not start_str or not end_str:
            flash('All fields are required.', 'danger')
            return render_template('examiner/slot_form.html', slot=None, open_exams=open_exams)

        exam = Examination.query.get(exam_id)
        if not exam or not exam.is_slot_creation_open():
            flash('Slot creation is not open for this exam.', 'danger')
            return render_template('examiner/slot_form.html', slot=None, open_exams=open_exams)

        start_t = datetime.strptime(start_str, '%H:%M').time()
        end_t = datetime.strptime(end_str, '%H:%M').time()

        if end_t <= start_t:
            flash('End time must be after start time.', 'danger')
            return render_template('examiner/slot_form.html', slot=None, open_exams=open_exams)

        slot = ExaminationSlot(
            exam_id=exam_id,
            examiner_id=current_user.id,
            date=date.fromisoformat(slot_date),
            start_time=start_t,
            end_time=end_t,
            max_capacity=capacity,
            available_seats=capacity
        )
        db.session.add(slot)
        db.session.commit()
        flash('Slot created.', 'success')
        return redirect(url_for('examiner.my_slots'))

    return render_template('examiner/slot_form.html', slot=None, open_exams=open_exams)


@examiner_bp.route('/slots/<int:slot_id>/edit', methods=['GET', 'POST'])
@login_required
@examiner_required
def slot_edit(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)

    if slot.examiner_id != current_user.id:
        flash('Not your slot.', 'danger')
        return redirect(url_for('examiner.my_slots'))

    # don't allow editing if students have already booked in
    active_bookings = Booking.query.filter_by(slot_id=slot.id, status='Booked').count()
    if active_bookings > 0:
        flash('Cannot edit — students have already booked this slot.', 'warning')
        return redirect(url_for('examiner.my_slots'))

    if request.method == 'POST':
        slot_date = request.form.get('date')
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')
        capacity = int(request.form.get('max_capacity', 1))

        start_t = datetime.strptime(start_str, '%H:%M').time()
        end_t = datetime.strptime(end_str, '%H:%M').time()

        if end_t <= start_t:
            flash('End time must be after start time.', 'danger')
            return render_template('examiner/slot_form.html', slot=slot, open_exams=[])

        slot.date = date.fromisoformat(slot_date)
        slot.start_time = start_t
        slot.end_time = end_t
        slot.max_capacity = capacity
        slot.available_seats = capacity  # reset since no bookings exist
        db.session.commit()
        flash('Slot updated.', 'success')
        return redirect(url_for('examiner.my_slots'))

    return render_template('examiner/slot_form.html', slot=slot, open_exams=[])


@examiner_bp.route('/slots/<int:slot_id>/cancel', methods=['POST'])
@login_required
@examiner_required
def slot_cancel(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)

    if slot.examiner_id != current_user.id:
        flash('Not your slot.', 'danger')
        return redirect(url_for('examiner.my_slots'))

    # cancel all active bookings on this slot too
    for booking in slot.bookings:
        if booking.status == 'Booked':
            booking.status = 'Cancelled'

    slot.status = 'Cancelled'
    db.session.commit()
    flash('Slot cancelled. Any bookings on it were also cancelled.', 'warning')
    return redirect(url_for('examiner.my_slots'))


@examiner_bp.route('/slots/<int:slot_id>/bookings')
@login_required
@examiner_required
def slot_bookings(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)

    if slot.examiner_id != current_user.id:
        flash('Not your slot.', 'danger')
        return redirect(url_for('examiner.my_slots'))

    return render_template('examiner/slot_bookings.html', slot=slot)
