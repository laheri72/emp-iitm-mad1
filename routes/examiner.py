from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, date, time
from models import db, Examination, ExaminationSlot, Booking, Evaluation, ExaminationRubric

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

    # pending evals = booked students in my slots who haven't been evaluated yet
    pending_evals = Booking.query.filter(
        Booking.slot_id.in_(my_slot_ids),
        Booking.status == 'Booked'
    ).count() if my_slot_ids else 0

    # exams where slot creation is currently open
    open_exams = [e for e in Examination.query.filter(
        Examination.status.in_(['Slot Creation', 'Booking Open'])
    ).all() if e.is_slot_creation_open()]

    return render_template('examiner/dashboard.html',
                           my_slots=my_slots,
                           booked_count=booked_count,
                           pending_evals=pending_evals,
                           open_exams=open_exams)


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
        slot.available_seats = capacity
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


# ── evaluation ────────────────────────────────────────────────────────────────

@examiner_bp.route('/evaluate')
@login_required
@examiner_required
def evaluate_list():
    # show all my slots that have booked students (pending or completed evals)
    my_slots = ExaminationSlot.query.filter_by(
        examiner_id=current_user.id
    ).order_by(ExaminationSlot.date.desc()).all()

    # only slots with at least one booking
    slots_with_bookings = [s for s in my_slots if s.bookings]
    return render_template('examiner/evaluate_list.html', slots=slots_with_bookings)


@examiner_bp.route('/bookings/<int:booking_id>/evaluate', methods=['GET', 'POST'])
@login_required
@examiner_required
def evaluate_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    slot = booking.slot

    if slot.examiner_id != current_user.id:
        flash('Not your booking to evaluate.', 'danger')
        return redirect(url_for('examiner.evaluate_list'))

    if booking.status == 'Cancelled':
        flash('This booking was cancelled.', 'warning')
        return redirect(url_for('examiner.evaluate_list'))

    exam = slot.examination
    rubrics = exam.rubrics

    if not rubrics:
        flash('No rubric criteria defined for this exam. Ask admin to add them first.', 'warning')
        return redirect(url_for('examiner.slot_bookings', slot_id=slot.id))

    # load any existing evaluations for this booking (to pre-fill if re-editing)
    existing = {e.rubric_id: e for e in booking.evaluations}

    if request.method == 'POST':
        total_awarded = 0
        errors = []

        for rubric in rubrics:
            marks_key = f'marks_{rubric.id}'
            remarks_key = f'remarks_{rubric.id}'
            marks_str = request.form.get(marks_key, '0').strip()

            try:
                marks = int(marks_str)
            except ValueError:
                errors.append(f'Invalid marks for "{rubric.criterion_name}".')
                continue

            if marks < 0 or marks > rubric.max_marks:
                errors.append(f'Marks for "{rubric.criterion_name}" must be 0–{rubric.max_marks}.')
                continue

            remarks = request.form.get(remarks_key, '').strip()
            total_awarded += marks

            if rubric.id in existing:
                # update existing
                existing[rubric.id].marks_awarded = marks
                existing[rubric.id].remarks = remarks
                existing[rubric.id].evaluated_at = datetime.now()
            else:
                ev = Evaluation(
                    booking_id=booking.id,
                    rubric_id=rubric.id,
                    evaluated_by=current_user.id,
                    marks_awarded=marks,
                    remarks=remarks
                )
                db.session.add(ev)

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('examiner/evaluation_form.html',
                                   booking=booking, rubrics=rubrics, existing=existing)

        # mark booking as completed once evaluation is submitted
        booking.status = 'Completed'
        slot.status = 'Completed'
        db.session.commit()

        flash(f'Evaluation submitted. Total: {total_awarded}/{exam.max_marks}', 'success')
        return redirect(url_for('examiner.slot_bookings', slot_id=slot.id))

    return render_template('examiner/evaluation_form.html',
                           booking=booking, rubrics=rubrics, existing=existing)


# ── profile ───────────────────────────────────────────────────────────────────

@examiner_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@examiner_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()
        new_pw = request.form.get('new_password', '').strip()
        confirm_pw = request.form.get('confirm_password', '').strip()

        if not name:
            flash('Name is required.', 'danger')
            return render_template('examiner/profile.html')

        current_user.name = name
        current_user.department = department
        current_user.phone = phone

        if new_pw:
            if len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'danger')
                return render_template('examiner/profile.html')
            if new_pw != confirm_pw:
                flash('Passwords do not match.', 'danger')
                return render_template('examiner/profile.html')
            current_user.set_password(new_pw)

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('examiner.profile'))

    return render_template('examiner/profile.html')
