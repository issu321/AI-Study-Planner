"""
AI Study Planner - Utility Functions
Premium Multi-Tenant Education Management System
Developer: Mohammed Usman | GitHub: issu321
"""
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for, abort, request, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
import humanize
import json


def role_required(*roles):
    """Decorator to restrict access by user role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to restrict access to super admins only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super_admin():
            flash('Super Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """Decorator to restrict access to teachers only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher():
            flash('Teacher access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator to restrict access to students only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student():
            flash('Student access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename, allowed_extensions):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_uploaded_file(file, folder, allowed_extensions=None):
    """Save an uploaded file with secure filename and return the path."""
    if file and allowed_file(file.filename, allowed_extensions or current_app.config['ALLOWED_NOTE_EXTENSIONS']):
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(folder, unique_name)
        file.save(filepath)
        return unique_name, os.path.getsize(filepath)
    return None, 0


def delete_file(filepath):
    """Delete a file if it exists."""
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except OSError:
            return False
    return False


def format_file_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    return humanize.naturalsize(size_bytes, binary=True)


def format_datetime(dt, format_str='%d %b %Y, %I:%M %p'):
    """Format datetime object to string."""
    if dt:
        return dt.strftime(format_str)
    return 'N/A'


def time_ago(dt):
    """Return human readable time ago string."""
    if not dt:
        return 'Never'
    return humanize.naturaltime(datetime.utcnow() - dt)


def truncate_text(text, length=100):
    """Truncate text to specified length."""
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + '...'


def generate_ref_id(prefix='REF'):
    """Generate a unique reference ID."""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{timestamp}-{unique}"


def get_file_icon(file_type):
    """Get Font Awesome icon class for file type."""
    icons = {
        'pdf': 'fa-file-pdf',
        'doc': 'fa-file-word',
        'docx': 'fa-file-word',
        'ppt': 'fa-file-powerpoint',
        'pptx': 'fa-file-powerpoint',
        'txt': 'fa-file-alt',
        'zip': 'fa-file-archive',
        'rar': 'fa-file-archive',
        'py': 'fa-file-code',
        'java': 'fa-file-code',
        'cpp': 'fa-file-code',
        'c': 'fa-file-code',
        'jpg': 'fa-file-image',
        'jpeg': 'fa-file-image',
        'png': 'fa-file-image',
        'gif': 'fa-file-image',
        'mp4': 'fa-file-video',
        'mp3': 'fa-file-audio',
    }
    return icons.get(file_type.lower(), 'fa-file')


def get_mime_type(file_type):
    """Get MIME type for file."""
    mime_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'txt': 'text/plain',
        'zip': 'application/zip',
        'rar': 'application/x-rar-compressed',
        'py': 'text/x-python',
        'java': 'text/x-java-source',
        'cpp': 'text/x-c++src',
        'c': 'text/x-csrc',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'mp4': 'video/mp4',
        'mp3': 'audio/mpeg',
    }
    return mime_types.get(file_type.lower(), 'application/octet-stream')


def log_activity(user_id, action, entity_type=None, entity_id=None, details=None):
    """Log user activity."""
    from models import ActivityLog, db
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def create_notification(user_id, title, message, notification_type='general', reference_id=None, reference_type=None):
    """Create a notification for a user."""
    from models import Notification, db
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            reference_id=str(reference_id) if reference_id else None,
            reference_type=reference_type
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception:
        db.session.rollback()
        return None


def get_dashboard_stats(user):
    """Get dashboard statistics based on user role."""
    from models import (College, Department, User, TeacherProfile, StudentProfile,
                       Subject, Material, Assignment, Test, Notification, Message,
                       ActivityLog, Submission, TestAttempt, db)
    
    stats = {}
    
    if user.is_super_admin():
        stats = {
            'total_colleges': College.query.count(),
            'total_departments': Department.query.count(),
            'total_teachers': User.query.filter_by(role='teacher').count(),
            'total_students': User.query.filter_by(role='student').count(),
            'total_subjects': Subject.query.count(),
            'total_materials': Material.query.count(),
            'total_assignments': Assignment.query.count(),
            'total_tests': Test.query.count(),
            'active_colleges': College.query.filter_by(status='active').count(),
            'recent_activities': ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
        }
    elif user.is_teacher():
        teacher = user.teacher_profile
        if teacher:
            subject_ids = [s.id for s in teacher.subjects]
            stats = {
                'my_subjects': teacher.subjects.count(),
                'my_students': sum(len(s.enrolled_students) for s in teacher.subjects),
                'my_materials': Material.query.filter_by(teacher_id=teacher.id).count(),
                'my_assignments': Assignment.query.filter_by(teacher_id=teacher.id).count(),
                'my_tests': Test.query.filter_by(teacher_id=teacher.id).count(),
                'pending_submissions': Submission.query.join(Assignment).filter(
                    Assignment.teacher_id == teacher.id,
                    Submission.status == 'submitted'
                ).count(),
                'recent_submissions': Submission.query.join(Assignment).filter(
                    Assignment.teacher_id == teacher.id
                ).order_by(Submission.submitted_at.desc()).limit(5).all()
            }
    elif user.is_student():
        student = user.student_profile
        if student:
            enrolled_subject_ids = [s.id for s in student.enrolled_subjects]
            stats = {
                'my_subjects': len(student.enrolled_subjects),
                'my_teachers': len(set(s.teacher_id for s in student.enrolled_subjects if s.teacher_id)),
                'pending_assignments': Assignment.query.filter(
                    Assignment.subject_id.in_(enrolled_subject_ids) if enrolled_subject_ids else False,
                    Assignment.status == 'active'
                ).count(),
                'my_submissions': Submission.query.filter_by(student_id=student.id).count(),
                'upcoming_tests': Test.query.filter(
                    Test.subject_id.in_(enrolled_subject_ids) if enrolled_subject_ids else False,
                    Test.status == 'published'
                ).count(),
                'my_test_attempts': TestAttempt.query.filter_by(student_id=student.id).count(),
                'avg_score': db.session.query(db.func.avg(TestAttempt.percentage)).filter_by(
                    student_id=student.id
                ).scalar() or 0
            }
    
    return stats


def get_unread_notifications_count(user_id):
    """Get count of unread notifications for user."""
    from models import Notification
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def get_unread_messages_count(user_id):
    """Get count of unread messages for user."""
    from models import Message
    return Message.query.filter_by(receiver_id=user_id, is_read=False).count()


def sanitize_filename(filename):
    """Sanitize a filename for safe storage."""
    filename = secure_filename(filename)
    name, ext = os.path.splitext(filename)
    return f"{uuid.uuid4().hex}{ext}"


def paginate(query, page=1, per_page=20):
    """Paginate a SQLAlchemy query."""
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'items': pagination.items,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'next_num': pagination.next_num,
        'prev_num': pagination.prev_num
    }


def get_days_remaining(due_date):
    """Get days remaining until due date."""
    if not due_date:
        return None
    now = datetime.utcnow()
    if due_date < now:
        return -1 * (now - due_date).days
    return (due_date - now).days


def calculate_progress(current, total):
    """Calculate percentage progress."""
    if total == 0:
        return 0
    return min(100, round((current / total) * 100, 1))


# Context processor for templates
def inject_globals():
    """Inject global variables into templates."""
    from models import Notification, Message
    
    context = {
        'current_year': datetime.utcnow().year,
        'developer_name': current_app.config.get('DEVELOPER_NAME', 'Mohammed Usman'),
        'developer_github': current_app.config.get('DEVELOPER_GITHUB', 'https://github.com/issu321'),
        'developer_email': current_app.config.get('DEVELOPER_EMAIL', 'jaafreeusman@gmail.com'),
        'developer_phone': current_app.config.get('DEVELOPER_PHONE', '8884294749'),
        'developer_role': current_app.config.get('DEVELOPER_ROLE', 'Full Stack Developer'),
        'developer_bio': current_app.config.get('DEVELOPER_BIO', ''),
        'app_name': 'AI Study Planner',
        'app_version': '1.0.0',
    }
    
    if current_user.is_authenticated:
        context['unread_notifications'] = get_unread_notifications_count(current_user.id)
        context['unread_messages'] = get_unread_messages_count(current_user.id)
        context['user_full_name'] = current_user.full_name()
        context['user_role'] = current_user.role
    
    return context