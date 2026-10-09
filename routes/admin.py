from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from models import db, User, Course, Examination, ExaminationRubric, ExaminationSlot, Booking

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access only.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── dashboard ─────────────────────────────────────────────────────────────────

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


# ── courses ───────────────────────────────────────────────────────────────────

@admin_bp.route('/courses')
@login_required
@admin_required
def courses():
    all_courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=all_courses)


@admin_bp.route('/courses/new', methods=['GET', 'POST'])
@login_required
@admin_required
def course_new():
    if request.method == 'POST':
        code = request.form.get('course_code', '').strip().upper()
        name = request.form.get('course_name', '').strip()
        desc = request.form.get('description', '').strip()

        if not code or not name:
            flash('Course code and name are required.', 'danger')
            return render_template('admin/course_form.html', course=None)

        if Course.query.filter_by(course_code=code).first():
            flash('A course with this code already exists.', 'danger')
            return render_template('admin/course_form.html', course=None)

        c = Course(course_code=code, course_name=name, description=desc)
        db.session.add(c)
        db.session.commit()
        flash(f'Course {code} created.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', course=None)


@admin_bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def course_edit(course_id):
    c = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        c.course_name = request.form.get('course_name', '').strip()
        c.description = request.form.get('description', '').strip()
        c.status = request.form.get('status', 'active')
        db.session.commit()
        flash('Course updated.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', course=c)


@admin_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@admin_required
def course_delete(course_id):
    c = Course.query.get_or_404(course_id)
    # only allow deleting if no exams are under it
    if c.examinations:
        flash('Cannot delete — this course has examinations linked to it.', 'warning')
        return redirect(url_for('admin.courses'))
    db.session.delete(c)
    db.session.commit()
    flash('Course deleted.', 'success')
    return redirect(url_for('admin.courses'))


# ── examinations ──────────────────────────────────────────────────────────────

@admin_bp.route('/exams')
@login_required
@admin_required
def exams():
    all_exams = Examination.query.order_by(Examination.created_at.desc()).all()
    return render_template('admin/exams.html', exams=all_exams)


@admin_bp.route('/exams/new', methods=['GET', 'POST'])
@login_required
@admin_required
def exam_new():
    courses = Course.query.filter_by(status='active').all()

    if request.method == 'POST':
        exam = Examination(
            course_id=request.form.get('course_id'),
            exam_name=request.form.get('exam_name', '').strip(),
            exam_type=request.form.get('exam_type', 'Viva'),
            duration=int(request.form.get('duration', 30)),
            max_marks=int(request.form.get('max_marks', 100)),
        )

        # parse the optional date/time fields
        def parse_dt(field):
            val = request.form.get(field, '').strip()
            return datetime.strptime(val, '%Y-%m-%dT%H:%M') if val else None

        exam.slot_creation_start = parse_dt('slot_creation_start')
        exam.slot_creation_end = parse_dt('slot_creation_end')
        exam.booking_start = parse_dt('booking_start')
        exam.booking_end = parse_dt('booking_end')

        if not exam.exam_name or not exam.course_id:
            flash('Exam name and course are required.', 'danger')
            return render_template('admin/exam_form.html', exam=None, courses=courses)

        db.session.add(exam)
        db.session.commit()
        flash('Examination created.', 'success')
        return redirect(url_for('admin.exams'))

    return render_template('admin/exam_form.html', exam=None, courses=courses)


@admin_bp.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def exam_edit(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    courses = Course.query.filter_by(status='active').all()

    if request.method == 'POST':
        exam.exam_name = request.form.get('exam_name', '').strip()
        exam.exam_type = request.form.get('exam_type', 'Viva')
        exam.course_id = request.form.get('course_id')
        exam.duration = int(request.form.get('duration', 30))
        exam.max_marks = int(request.form.get('max_marks', 100))

        def parse_dt(field):
            val = request.form.get(field, '').strip()
            return datetime.strptime(val, '%Y-%m-%dT%H:%M') if val else None

        exam.slot_creation_start = parse_dt('slot_creation_start')
        exam.slot_creation_end = parse_dt('slot_creation_end')
        exam.booking_start = parse_dt('booking_start')
        exam.booking_end = parse_dt('booking_end')

        db.session.commit()
        flash('Examination updated.', 'success')
        return redirect(url_for('admin.exam_detail', exam_id=exam.id))

    return render_template('admin/exam_form.html', exam=exam, courses=courses)


@admin_bp.route('/exams/<int:exam_id>')
@login_required
@admin_required
def exam_detail(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    return render_template('admin/exam_detail.html', exam=exam)


@admin_bp.route('/exams/<int:exam_id>/set-status', methods=['POST'])
@login_required
@admin_required
def exam_set_status(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    new_status = request.form.get('status', '').strip()

    allowed = ['Draft', 'Slot Creation', 'Booking Open', 'Closed', 'Completed']
    if new_status not in allowed:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin.exam_detail', exam_id=exam_id))

    exam.status = new_status
    db.session.commit()
    flash(f'Exam status changed to "{new_status}".', 'success')
    return redirect(url_for('admin.exam_detail', exam_id=exam_id))


@admin_bp.route('/exams/<int:exam_id>/delete', methods=['POST'])
@login_required
@admin_required
def exam_delete(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash('Examination deleted.', 'success')
    return redirect(url_for('admin.exams'))


# ── rubrics ───────────────────────────────────────────────────────────────────

@admin_bp.route('/exams/<int:exam_id>/rubrics/new', methods=['GET', 'POST'])
@login_required
@admin_required
def rubric_new(exam_id):
    exam = Examination.query.get_or_404(exam_id)

    if request.method == 'POST':
        r = ExaminationRubric(
            exam_id=exam_id,
            criterion_name=request.form.get('criterion_name', '').strip(),
            max_marks=int(request.form.get('max_marks', 10)),
            weightage=float(request.form.get('weightage', 0) or 0),
            description=request.form.get('description', '').strip()
        )
        if not r.criterion_name:
            flash('Criterion name is required.', 'danger')
            return render_template('admin/rubric_form.html', exam=exam, rubric=None)

        db.session.add(r)
        db.session.commit()
        flash('Rubric criterion added.', 'success')
        return redirect(url_for('admin.exam_detail', exam_id=exam_id))

    return render_template('admin/rubric_form.html', exam=exam, rubric=None)


@admin_bp.route('/rubrics/<int:rubric_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def rubric_edit(rubric_id):
    r = ExaminationRubric.query.get_or_404(rubric_id)
    exam = r.examination

    if request.method == 'POST':
        r.criterion_name = request.form.get('criterion_name', '').strip()
        r.max_marks = int(request.form.get('max_marks', 10))
        r.weightage = float(request.form.get('weightage', 0) or 0)
        r.description = request.form.get('description', '').strip()
        db.session.commit()
        flash('Rubric updated.', 'success')
        return redirect(url_for('admin.exam_detail', exam_id=exam.id))

    return render_template('admin/rubric_form.html', exam=exam, rubric=r)


@admin_bp.route('/rubrics/<int:rubric_id>/delete', methods=['POST'])
@login_required
@admin_required
def rubric_delete(rubric_id):
    r = ExaminationRubric.query.get_or_404(rubric_id)
    exam_id = r.exam_id
    db.session.delete(r)
    db.session.commit()
    flash('Rubric criterion removed.', 'success')
    return redirect(url_for('admin.exam_detail', exam_id=exam_id))


# ── examiners ─────────────────────────────────────────────────────────────────

@admin_bp.route('/examiners')
@login_required
@admin_required
def examiners():
    all_examiners = User.query.filter_by(role='examiner').order_by(User.created_at.desc()).all()
    return render_template('admin/examiners.html', examiners=all_examiners)


@admin_bp.route('/examiners/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def examiner_approve(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    user.is_active = True
    db.session.commit()
    flash(f'{user.name} approved.', 'success')
    return redirect(url_for('admin.examiners'))


@admin_bp.route('/examiners/<int:user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def examiner_deactivate(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    user.is_approved = False
    db.session.commit()
    flash(f'{user.name} deactivated.', 'warning')
    return redirect(url_for('admin.examiners'))


# ── students list ─────────────────────────────────────────────────────────────

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    q = request.args.get('q', '').strip()
    query = User.query.filter_by(role='student')
    if q:
        query = query.filter(User.name.ilike(f'%{q}%') | User.email.ilike(f'%{q}%'))
    all_students = query.order_by(User.created_at.desc()).all()
    return render_template('admin/students.html', students=all_students, q=q)
