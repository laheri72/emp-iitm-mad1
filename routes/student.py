from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from models import db, Examination, ExaminationSlot, Booking

student_bp = Blueprint('student', __name__)


def student_required(f):
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
    open_exams = [e for e in Examination.query.filter_by(status='Booking Open').all()
                  if e.is_booking_open()]

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


# ── exam browsing + booking ───────────────────────────────────────────────────

@student_bp.route('/exams')
@login_required
@student_required
def browse_exams():
    q = request.args.get('q', '').strip()
    # only show exams where booking is actually open right now
    open_exams = [e for e in Examination.query.filter_by(status='Booking Open').all()
                  if e.is_booking_open()]
    if q:
        open_exams = [
            e for e in open_exams
            if q.lower() in e.exam_name.lower() or q.lower() in e.course.course_code.lower()
        ]
    return render_template('student/exams.html', exams=open_exams, q=q)


@student_bp.route('/exams/<int:exam_id>/slots')
@login_required
@student_required
def exam_slots(exam_id):
    exam = Examination.query.get_or_404(exam_id)

    if not exam.is_booking_open():
        flash('Booking is not open for this exam.', 'warning')
        return redirect(url_for('student.browse_exams'))

    # check if already booked for this exam
    already_booked = Booking.query.join(ExaminationSlot).filter(
        ExaminationSlot.exam_id == exam_id,
        Booking.student_id == current_user.id,
        Booking.status == 'Booked'
    ).first()

    available_slots = ExaminationSlot.query.filter_by(
        exam_id=exam_id,
        status='Available'
    ).order_by(ExaminationSlot.date, ExaminationSlot.start_time).all()

    return render_template('student/exam_slots.html',
                           exam=exam,
                           slots=available_slots,
                           already_booked=already_booked)


@student_bp.route('/slots/<int:slot_id>/book', methods=['POST'])
@login_required
@student_required
def book_slot(slot_id):
    slot = ExaminationSlot.query.get_or_404(slot_id)
    exam = slot.examination

    # gate checks
    if not exam.is_booking_open():
        flash('Booking window has closed.', 'danger')
        return redirect(url_for('student.browse_exams'))

    if slot.status != 'Available' or not slot.has_seats():
        flash('This slot is full or unavailable.', 'danger')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # prevent duplicate booking for the same exam
    existing = Booking.query.join(ExaminationSlot).filter(
        ExaminationSlot.exam_id == exam.id,
        Booking.student_id == current_user.id,
        Booking.status == 'Booked'
    ).first()

    if existing:
        flash('You already have a booking for this exam.', 'warning')
        return redirect(url_for('student.exam_slots', exam_id=exam.id))

    # create booking and decrement seat count
    booking = Booking(student_id=current_user.id, slot_id=slot_id)
    db.session.add(booking)

    slot.available_seats -= 1
    if slot.available_seats == 0:
        slot.status = 'Full'

    db.session.commit()
    flash('Slot booked successfully!', 'success')
    return redirect(url_for('student.my_bookings'))


# ── bookings ──────────────────────────────────────────────────────────────────

@student_bp.route('/bookings')
@login_required
@student_required
def my_bookings():
    active = Booking.query.filter_by(student_id=current_user.id, status='Booked').all()
    past = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.status.in_(['Completed', 'Cancelled'])
    ).order_by(Booking.booking_date.desc()).all()

    return render_template('student/bookings.html', active=active, past=past)


@student_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
@student_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.student_id != current_user.id:
        flash('Not your booking.', 'danger')
        return redirect(url_for('student.my_bookings'))

    if booking.status != 'Booked':
        flash('This booking cannot be cancelled.', 'warning')
        return redirect(url_for('student.my_bookings'))

    # deadline check: student cannot cancel after booking deadline
    exam = booking.slot.examination
    if exam.booking_end and datetime.now() > exam.booking_end:
        flash('Cannot cancel — the booking deadline has passed.', 'warning')
        return redirect(url_for('student.my_bookings'))

    booking.status = 'Cancelled'

    # give the seat back
    slot = booking.slot
    slot.available_seats += 1
    if slot.status == 'Full':
        slot.status = 'Available'

    db.session.commit()
    flash('Booking cancelled.', 'info')
    return redirect(url_for('student.my_bookings'))


@student_bp.route('/results/<int:booking_id>')
@login_required
@student_required
def result_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.student_id != current_user.id:
        flash('Not your result.', 'danger')
        return redirect(url_for('student.my_bookings'))

    if booking.status != 'Completed':
        flash('Results are not available yet.', 'info')
        return redirect(url_for('student.my_bookings'))

    exam = booking.slot.examination
    rubrics = exam.rubrics
    eval_map = {e.rubric_id: e for e in booking.evaluations}
    total = sum(e.marks_awarded for e in booking.evaluations)

    return render_template('student/result_detail.html',
                           booking=booking,
                           exam=exam,
                           rubrics=rubrics,
                           eval_map=eval_map,
                           total=total)


# ── profile ───────────────────────────────────────────────────────────────────

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@student_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        new_pw = request.form.get('new_password', '').strip()
        confirm_pw = request.form.get('confirm_password', '').strip()

        if not name:
            flash('Name is required.', 'danger')
            return render_template('student/profile.html')

        current_user.name = name
        current_user.phone = phone

        if new_pw:
            if len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'danger')
                return render_template('student/profile.html')
            if new_pw != confirm_pw:
                flash('Passwords do not match.', 'danger')
                return render_template('student/profile.html')
            current_user.set_password(new_pw)

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student.profile'))

    return render_template('student/profile.html')

