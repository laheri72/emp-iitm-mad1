from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# single table for all 3 roles, keeps auth simple
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    role = db.Column(db.String(20), nullable=False, default='student')  # admin / examiner / student
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # examiners need admin to flip this

    department = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    slots_created = db.relationship('ExaminationSlot', backref='examiner', lazy=True,
                                    foreign_keys='ExaminationSlot.examiner_id')
    bookings = db.relationship('Booking', backref='student', lazy=True,
                               foreign_keys='Booking.student_id')
    evaluations_done = db.relationship('Evaluation', backref='evaluator', lazy=True,
                                       foreign_keys='Evaluation.evaluated_by')

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_examiner(self):
        return self.role == 'examiner'

    @property
    def is_student(self):
        return self.role == 'student'

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    course_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    examinations = db.relationship('Examination', backref='course', lazy=True)

    def __repr__(self):
        return f'<Course {self.course_code}: {self.course_name}>'


class Examination(db.Model):
    __tablename__ = 'examinations'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    exam_name = db.Column(db.String(200), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False, default='Viva')
    duration = db.Column(db.Integer, nullable=False)  # minutes
    max_marks = db.Column(db.Integer, nullable=False)

    # these 4 dates define when examiners can create slots and when students can book
    slot_creation_start = db.Column(db.DateTime, nullable=True)
    slot_creation_end = db.Column(db.DateTime, nullable=True)
    booking_start = db.Column(db.DateTime, nullable=True)
    booking_end = db.Column(db.DateTime, nullable=True)

    # Draft -> Slot Creation -> Booking Open -> Closed -> Completed
    status = db.Column(db.String(30), default='Draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rubrics = db.relationship('ExaminationRubric', backref='examination', lazy=True,
                              cascade='all, delete-orphan')
    slots = db.relationship('ExaminationSlot', backref='examination', lazy=True)

    def is_slot_creation_open(self):
        now = datetime.utcnow()
        if self.status == 'Slot Creation' and self.slot_creation_start and self.slot_creation_end:
            return self.slot_creation_start <= now <= self.slot_creation_end
        return False

    def is_booking_open(self):
        now = datetime.utcnow()
        if self.status == 'Booking Open' and self.booking_start and self.booking_end:
            return self.booking_start <= now <= self.booking_end
        return False

    def __repr__(self):
        return f'<Examination {self.exam_name} [{self.status}]>'


class ExaminationRubric(db.Model):
    __tablename__ = 'examination_rubrics'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('examinations.id'), nullable=False)
    criterion_name = db.Column(db.String(150), nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    weightage = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)

    evaluations = db.relationship('Evaluation', backref='rubric', lazy=True)

    def __repr__(self):
        return f'<Rubric {self.criterion_name} ({self.max_marks} marks)>'


class ExaminationSlot(db.Model):
    __tablename__ = 'examination_slots'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('examinations.id'), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    max_capacity = db.Column(db.Integer, nullable=False, default=1)
    available_seats = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default='Available')  # Available / Full / Cancelled / Completed

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='slot', lazy=True)

    def has_seats(self):
        return self.available_seats > 0

    def __repr__(self):
        return f'<Slot {self.date} {self.start_time}-{self.end_time} [{self.status}]>'


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('examination_slots.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Booked')  # Booked / Cancelled / Completed

    evaluations = db.relationship('Evaluation', backref='booking', lazy=True,
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Booking student={self.student_id} slot={self.slot_id} [{self.status}]>'


class Evaluation(db.Model):
    __tablename__ = 'evaluations'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('examination_rubrics.id'), nullable=False)
    evaluated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    marks_awarded = db.Column(db.Integer, nullable=False, default=0)
    remarks = db.Column(db.Text, nullable=True)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Evaluation booking={self.booking_id} rubric={self.rubric_id} marks={self.marks_awarded}>'
