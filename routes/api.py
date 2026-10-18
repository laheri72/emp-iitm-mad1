from flask import Blueprint, jsonify, request
from models import Course, Examination, ExaminationRubric, ExaminationSlot, Booking, User

api_bp = Blueprint('api', __name__)


# ── summary statistics ────────────────────────────────────────────────────────

@api_bp.route('/stats')
def get_stats():
    return jsonify({
        'status': 'success',
        'data': {
            'courses': Course.query.count(),
            'examinations': Examination.query.count(),
            'examiners': User.query.filter_by(role='examiner').count(),
            'students': User.query.filter_by(role='student').count(),
            'slots': ExaminationSlot.query.count(),
            'bookings': Booking.query.count(),
        }
    })


# ── examinations ──────────────────────────────────────────────────────────────

@api_bp.route('/exams')
def get_exams():
    status = request.args.get('status')
    query = Examination.query
    if status:
        query = query.filter_by(status=status)
    exams = query.order_by(Examination.created_at.desc()).all()

    result = []
    for e in exams:
        result.append({
            'id': e.id,
            'course_code': e.course.course_code,
            'course_name': e.course.course_name,
            'exam_name': e.exam_name,
            'exam_type': e.exam_type,
            'duration_minutes': e.duration,
            'max_marks': e.max_marks,
            'status': e.status,
            'is_slot_creation_open': e.is_slot_creation_open(),
            'is_booking_open': e.is_booking_open(),
            'slots_count': len(e.slots),
            'rubrics_count': len(e.rubrics),
            'slot_creation_start': e.slot_creation_start.isoformat() if e.slot_creation_start else None,
            'slot_creation_end': e.slot_creation_end.isoformat() if e.slot_creation_end else None,
            'booking_start': e.booking_start.isoformat() if e.booking_start else None,
            'booking_end': e.booking_end.isoformat() if e.booking_end else None,
        })
    return jsonify({'status': 'success', 'count': len(result), 'data': result})


@api_bp.route('/exams/<int:exam_id>')
def get_exam_detail(exam_id):
    e = Examination.query.get(exam_id)
    if not e:
        return jsonify({'status': 'error', 'message': 'Examination not found'}), 404

    rubrics = [{
        'id': r.id,
        'criterion_name': r.criterion_name,
        'max_marks': r.max_marks,
        'weightage': r.weightage,
        'description': r.description
    } for r in e.rubrics]

    slots = [{
        'id': s.id,
        'date': s.date.isoformat(),
        'start_time': s.start_time.strftime('%H:%M'),
        'end_time': s.end_time.strftime('%H:%M'),
        'examiner_name': s.examiner.name,
        'max_capacity': s.max_capacity,
        'available_seats': s.available_seats,
        'status': s.status
    } for s in e.slots]

    return jsonify({
        'status': 'success',
        'data': {
            'id': e.id,
            'course': {
                'id': e.course.id,
                'code': e.course.course_code,
                'name': e.course.course_name
            },
            'exam_name': e.exam_name,
            'exam_type': e.exam_type,
            'duration_minutes': e.duration,
            'max_marks': e.max_marks,
            'status': e.status,
            'rubrics': rubrics,
            'slots': slots
        }
    })


# ── examination slots ─────────────────────────────────────────────────────────

@api_bp.route('/slots')
def get_slots():
    exam_id = request.args.get('exam_id', type=int)
    query = ExaminationSlot.query
    if exam_id:
        query = query.filter_by(exam_id=exam_id)

    slots = query.order_by(ExaminationSlot.date.desc()).all()
    result = [{
        'id': s.id,
        'exam_id': s.exam_id,
        'exam_name': s.examination.exam_name,
        'date': s.date.isoformat(),
        'start_time': s.start_time.strftime('%H:%M'),
        'end_time': s.end_time.strftime('%H:%M'),
        'examiner_id': s.examiner_id,
        'examiner_name': s.examiner.name,
        'max_capacity': s.max_capacity,
        'available_seats': s.available_seats,
        'status': s.status
    } for s in slots]

    return jsonify({'status': 'success', 'count': len(result), 'data': result})


@api_bp.route('/slots/<int:slot_id>')
def get_slot_detail(slot_id):
    s = ExaminationSlot.query.get(slot_id)
    if not s:
        return jsonify({'status': 'error', 'message': 'Slot not found'}), 404

    return jsonify({
        'status': 'success',
        'data': {
            'id': s.id,
            'exam_id': s.exam_id,
            'exam_name': s.examination.exam_name,
            'course_code': s.examination.course.course_code,
            'date': s.date.isoformat(),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'examiner_id': s.examiner_id,
            'examiner_name': s.examiner.name,
            'max_capacity': s.max_capacity,
            'available_seats': s.available_seats,
            'status': s.status,
            'booked_count': len([b for b in s.bookings if b.status == 'Booked'])
        }
    })
