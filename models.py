"""
AI Study Planner - Database Models
Premium Multi-Tenant Education Management System
Developer: Mohammed Usman | GitHub: issu321
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import json

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

# Association tables
student_subjects = db.Table('student_subjects',
    db.Column('student_id', db.Integer, db.ForeignKey('student_profile.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subject.id'), primary_key=True)
)

teacher_departments = db.Table('teacher_departments',
    db.Column('teacher_id', db.Integer, db.ForeignKey('teacher_profile.id'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('department.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='student')  # super_admin, teacher, student
    avatar = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    teacher_profile = db.relationship('TeacherProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    study_plans = db.relationship('StudyPlan', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_student(self):
        return self.role == 'student'
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name(),
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'role': self.role,
            'avatar': self.avatar,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class College(db.Model):
    __tablename__ = 'college'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True, default='India')
    zip_code = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    established_year = db.Column(db.Integer, nullable=True)
    accreditation = db.Column(db.String(100), nullable=True)
    logo = db.Column(db.String(200), nullable=True)
    banner_image = db.Column(db.String(200), nullable=True)
    principal_name = db.Column(db.String(100), nullable=True)
    total_students = db.Column(db.Integer, default=0)
    total_teachers = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')  # active, inactive, suspended
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    departments = db.relationship('Department', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    teachers = db.relationship('TeacherProfile', backref='college', lazy='dynamic')
    students = db.relationship('StudentProfile', backref='college', lazy='dynamic')
    creator = db.relationship('User', foreign_keys=[created_by])
    announcements = db.relationship('Announcement', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_logo_url(self):
        if self.logo:
            return self.logo
        return '/static/images/default-college-logo.png'
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'established_year': self.established_year,
            'accreditation': self.accreditation,
            'logo': self.get_logo_url(),
            'banner_image': self.banner_image,
            'principal_name': self.principal_name,
            'total_students': self.total_students,
            'total_teachers': self.total_teachers,
            'status': self.status,
            'department_count': self.departments.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Department(db.Model):
    __tablename__ = 'department'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    head_name = db.Column(db.String(100), nullable=True)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subjects = db.relationship('Subject', backref='department', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'head_name': self.head_name,
            'college_id': self.college_id,
            'subject_count': self.subjects.count()
        }


class TeacherProfile(db.Model):
    __tablename__ = 'teacher_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    employee_id = db.Column(db.String(50), nullable=True)
    qualification = db.Column(db.String(200), nullable=True)
    specialization = db.Column(db.String(200), nullable=True)
    experience_years = db.Column(db.Integer, default=0)
    designation = db.Column(db.String(50), default='Assistant Professor')  # Professor, HOD, etc.
    bio = db.Column(db.Text, nullable=True)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    subjects = db.relationship('Subject', backref='teacher', lazy='dynamic')
    materials = db.relationship('Material', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')
    tests = db.relationship('Test', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'college_id': self.college_id,
            'employee_id': self.employee_id,
            'qualification': self.qualification,
            'specialization': self.specialization,
            'experience_years': self.experience_years,
            'designation': self.designation,
            'bio': self.bio,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'is_active': self.is_active,
            'user': self.user.to_dict() if self.user else None
        }


class StudentProfile(db.Model):
    __tablename__ = 'student_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    roll_number = db.Column(db.String(50), nullable=True)
    enrollment_number = db.Column(db.String(50), nullable=True)
    course = db.Column(db.String(100), nullable=True)
    semester = db.Column(db.Integer, default=1)
    batch_year = db.Column(db.Integer, nullable=True)
    guardian_name = db.Column(db.String(100), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=True)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    enrolled_subjects = db.relationship('Subject', secondary=student_subjects, backref='enrolled_students')
    submissions = db.relationship('Submission', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    test_attempts = db.relationship('TestAttempt', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'college_id': self.college_id,
            'roll_number': self.roll_number,
            'enrollment_number': self.enrollment_number,
            'course': self.course,
            'semester': self.semester,
            'batch_year': self.batch_year,
            'guardian_name': self.guardian_name,
            'guardian_phone': self.guardian_phone,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'is_active': self.is_active,
            'user': self.user.to_dict() if self.user else None
        }


class Subject(db.Model):
    __tablename__ = 'subject'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, nullable=True)
    credits = db.Column(db.Integer, default=3)
    semester = db.Column(db.Integer, default=1)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_profile.id'), nullable=True)
    syllabus = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    materials = db.relationship('Material', backref='subject', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='subject', lazy='dynamic', cascade='all, delete-orphan')
    tests = db.relationship('Test', backref='subject', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        teacher_name = None
        if self.teacher and self.teacher.user:
            teacher_name = self.teacher.user.full_name()
        return {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'credits': self.credits,
            'semester': self.semester,
            'department_id': self.department_id,
            'teacher_id': self.teacher_id,
            'teacher_name': teacher_name,
            'syllabus': self.syllabus,
            'status': self.status,
            'material_count': self.materials.count(),
            'assignment_count': self.assignments.count(),
            'test_count': self.tests.count(),
            'student_count': self.enrolled_students.count() if hasattr(self, 'enrolled_students') else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Material(db.Model):
    __tablename__ = 'material'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(300), nullable=True)
    file_type = db.Column(db.String(50), nullable=True)  # pdf, doc, ppt, etc.
    file_size = db.Column(db.Integer, default=0)  # in bytes
    content_type = db.Column(db.String(50), default='notes')  # notes, presentation, reference, video_link
    external_link = db.Column(db.String(500), nullable=True)  # for video links or external resources
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_profile.id'), nullable=False)
    download_count = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'description': self.description,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'external_link': self.external_link,
            'subject_id': self.subject_id,
            'teacher_id': self.teacher_id,
            'download_count': self.download_count,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Assignment(db.Model):
    __tablename__ = 'assignment'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instructions = db.Column(db.Text, nullable=True)
    total_marks = db.Column(db.Integer, default=100)
    passing_marks = db.Column(db.Integer, default=40)
    due_date = db.Column(db.DateTime, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_profile.id'), nullable=False)
    attachment_path = db.Column(db.String(300), nullable=True)
    allow_late_submission = db.Column(db.Boolean, default=False)
    late_submission_penalty = db.Column(db.Integer, default=10)  # percentage deduction
    status = db.Column(db.String(20), default='active')  # active, closed, graded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('Submission', backref='assignment', lazy='dynamic', cascade='all, delete-orphan')
    
    def is_overdue(self):
        return datetime.utcnow() > self.due_date
    
    def submission_count(self):
        return self.submissions.count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'description': self.description,
            'instructions': self.instructions,
            'total_marks': self.total_marks,
            'passing_marks': self.passing_marks,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'is_overdue': self.is_overdue(),
            'subject_id': self.subject_id,
            'teacher_id': self.teacher_id,
            'attachment_path': self.attachment_path,
            'allow_late_submission': self.allow_late_submission,
            'late_submission_penalty': self.late_submission_penalty,
            'status': self.status,
            'submission_count': self.submission_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Submission(db.Model):
    __tablename__ = 'submission'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    file_path = db.Column(db.String(300), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    marks_obtained = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='submitted')  # submitted, graded, returned
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    graded_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'assignment_id': self.assignment_id,
            'student_id': self.student_id,
            'file_path': self.file_path,
            'comments': self.comments,
            'marks_obtained': self.marks_obtained,
            'feedback': self.feedback,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'graded_at': self.graded_at.isoformat() if self.graded_at else None
        }


class Test(db.Model):
    __tablename__ = 'test'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instructions = db.Column(db.Text, nullable=True)
    total_marks = db.Column(db.Integer, default=100)
    passing_marks = db.Column(db.Integer, default=40)
    duration_minutes = db.Column(db.Integer, default=60)  # exam duration
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_profile.id'), nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, published, active, completed, cancelled
    shuffle_questions = db.Column(db.Boolean, default=True)
    show_result_immediately = db.Column(db.Boolean, default=True)
    max_attempts = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='test', lazy='dynamic', cascade='all, delete-orphan')
    attempts = db.relationship('TestAttempt', backref='test', lazy='dynamic', cascade='all, delete-orphan')
    
    def is_active_now(self):
        now = datetime.utcnow()
        if self.start_time and self.end_time:
            return self.start_time <= now <= self.end_time and self.status == 'published'
        return self.status == 'published'
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'description': self.description,
            'instructions': self.instructions,
            'total_marks': self.total_marks,
            'passing_marks': self.passing_marks,
            'duration_minutes': self.duration_minutes,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'is_active_now': self.is_active_now(),
            'subject_id': self.subject_id,
            'teacher_id': self.teacher_id,
            'status': self.status,
            'shuffle_questions': self.shuffle_questions,
            'show_result_immediately': self.show_result_immediately,
            'max_attempts': self.max_attempts,
            'question_count': self.questions.count(),
            'attempt_count': self.attempts.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Question(db.Model):
    __tablename__ = 'question'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='mcq')  # mcq, true_false, short_answer, essay
    options = db.Column(db.Text, nullable=True)  # JSON string for MCQ options
    correct_answer = db.Column(db.Text, nullable=True)
    marks = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text, nullable=True)  # explanation for correct answer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_options(self, options_list):
        self.options = json.dumps(options_list)
    
    def get_options(self):
        if self.options:
            return json.loads(self.options)
        return []
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'test_id': self.test_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'options': self.get_options(),
            'correct_answer': self.correct_answer,
            'marks': self.marks,
            'order': self.order,
            'explanation': self.explanation
        }


class TestAttempt(db.Model):
    __tablename__ = 'test_attempt'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    answers = db.Column(db.Text, nullable=True)  # JSON string of answers
    score = db.Column(db.Float, default=0)
    total_marks = db.Column(db.Float, default=0)
    percentage = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, timeout
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    time_taken_minutes = db.Column(db.Integer, nullable=True)
    
    def set_answers(self, answers_dict):
        self.answers = json.dumps(answers_dict)
    
    def get_answers(self):
        if self.answers:
            return json.loads(self.answers)
        return {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'test_id': self.test_id,
            'student_id': self.student_id,
            'score': self.score,
            'total_marks': self.total_marks,
            'percentage': self.percentage,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_taken_minutes': self.time_taken_minutes
        }


class StudyPlan(db.Model):
    __tablename__ = 'study_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    plan_data = db.Column(db.Text, nullable=True)  # JSON structured plan
    target_date = db.Column(db.DateTime, nullable=True)
    daily_hours = db.Column(db.Float, default=6)
    priority_subjects = db.Column(db.Text, nullable=True)  # JSON list of subject IDs
    status = db.Column(db.String(20), default='active')  # active, completed, archived
    progress_percentage = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_plan_data(self, data):
        self.plan_data = json.dumps(data)
    
    def get_plan_data(self):
        if self.plan_data:
            return json.loads(self.plan_data)
        return {}
    
    def set_priority_subjects(self, subjects):
        self.priority_subjects = json.dumps(subjects)
    
    def get_priority_subjects(self):
        if self.priority_subjects:
            return json.loads(self.priority_subjects)
        return []
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'plan_data': self.get_plan_data(),
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'daily_hours': self.daily_hours,
            'priority_subjects': self.get_priority_subjects(),
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    notification_type = db.Column(db.String(30), default='general')  # assignment, test, announcement, message
    reference_id = db.Column(db.String(50), nullable=True)  # ID of related object
    reference_type = db.Column(db.String(30), nullable=True)  # type of related object
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Message(db.Model):
    __tablename__ = 'message'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'subject': self.subject,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sender_name': self.sender.full_name() if self.sender else None,
            'receiver_name': self.receiver.full_name() if self.receiver else None
        }


class Announcement(db.Model):
    __tablename__ = 'announcement'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=generate_uuid)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'content': self.content,
            'priority': self.priority,
            'college_id': self.college_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)  # college, subject, assignment, etc.
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }