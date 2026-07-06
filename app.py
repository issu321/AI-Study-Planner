"""
AI Study Planner - Main Application
Premium Multi-Tenant Education Management System
Developer: Mohammed Usman | GitHub: issu321
Contact: 8884294749 | jaafreeusman@gmail.com

A complete multi-user AI-powered study planning and college management system.
Run this file directly: python app.py
"""
import os
import sys
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func

# Import configuration
from config import Config

# Import models and database
from models import (
    db, User, College, Department, TeacherProfile, StudentProfile,
    Subject, Material, Assignment, Submission, Test, Question, TestAttempt,
    StudyPlan, Notification, Message, Announcement, ActivityLog
)

# Import utilities
from utils import (
    admin_required, teacher_required, student_required, role_required,
    allowed_file, save_uploaded_file, delete_file, format_file_size,
    format_datetime, time_ago, truncate_text, get_file_icon,
    log_activity, create_notification, get_dashboard_stats,
    paginate, get_days_remaining, calculate_progress, inject_globals
)

# Import AI engine
from ai_engine import AIStudyPlanner, generate_smart_schedule, get_subject_suggestions

# ============================================================
# APP INITIALIZATION
# ============================================================
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# Context processors
app.context_processor(inject_globals)

# Template globals (make utility functions available in all Jinja2 templates)
app.add_template_global(get_file_icon)
app.add_template_global(format_file_size)
app.add_template_global(format_datetime)
app.add_template_global(time_ago)
app.add_template_global(truncate_text)

# ============================================================
# ERROR HANDLERS
# ============================================================
@app.errorhandler(404)
def not_found_error(error):
    if request.is_json:
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('error.html', error_code=404, error_message='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.is_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('error.html', error_code=500, error_message='Something went wrong'), 500

@app.errorhandler(403)
def forbidden_error(error):
    if request.is_json:
        return jsonify({'error': 'Access forbidden'}), 403
    flash('You do not have permission to access this resource.', 'danger')
    return redirect(url_for('dashboard'))

# ============================================================
# LOGIN MANAGER
# ============================================================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================================
# APPLICATION SETUP (Create tables and default admin)
# ============================================================
def setup_database():
    """Create all tables and default admin user."""
    with app.app_context():
        db.create_all()
        
        # Create default super admin if not exists
        admin = User.query.filter_by(username=Config.DEFAULT_ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=Config.DEFAULT_ADMIN_USERNAME,
                email=Config.DEFAULT_ADMIN_EMAIL,
                first_name='Mohammed',
                last_name='Usman',
                phone=Config.DEFAULT_ADMIN_PHONE,
                role='super_admin',
                is_active=True,
                is_verified=True
            )
            admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f"[SETUP] Default super admin created: {Config.DEFAULT_ADMIN_USERNAME}")
        
        # Create upload directories
        upload_folders = [
            app.config['UPLOAD_FOLDER'],
            app.config['NOTES_FOLDER'],
            app.config['ASSIGNMENTS_FOLDER'],
            app.config['TESTS_FOLDER'],
            app.config['LOGOS_FOLDER'],
            app.config['PROFILES_FOLDER']
        ]
        for folder in upload_folders:
            os.makedirs(folder, exist_ok=True)
        
        print("[SETUP] Database initialized successfully!")

# ============================================================
# PUBLIC ROUTES
# ============================================================
@app.route('/')
def index():
    """Landing page."""
    stats = {
        'colleges': College.query.filter_by(status='active').count(),
        'teachers': User.query.filter_by(role='teacher', is_active=True).count(),
        'students': User.query.filter_by(role='student', is_active=True).count(),
        'subjects': Subject.query.filter_by(status='active').count()
    }
    recent_colleges = College.query.filter_by(status='active').order_by(College.created_at.desc()).limit(6).all()
    return render_template('index.html', stats=stats, recent_colleges=recent_colleges)

@app.route('/developer')
def developer():
    """Developer page."""
    return render_template('developer.html')

@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')

# ============================================================
# AUTHENTICATION ROUTES
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Please provide both username and password.', 'warning')
            return render_template('login.html')
        
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Contact admin.', 'danger')
                return render_template('login.html')
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_activity(user.id, 'login', 'user', user.id)
            flash(f'Welcome back, {user.full_name()}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration - Teachers and Students."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    colleges = College.query.filter_by(status='active').all()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'student')
        college_id = request.form.get('college_id', type=int)
        
        # Validation
        if not all([username, email, password, first_name, last_name]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('register.html', colleges=colleges)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return render_template('register.html', colleges=colleges)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('register.html', colleges=colleges)
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'warning')
            return render_template('register.html', colleges=colleges)
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return render_template('register.html', colleges=colleges)
        
        if role not in ['teacher', 'student']:
            flash('Invalid role selected.', 'warning')
            return render_template('register.html', colleges=colleges)
        
        if not college_id:
            flash('Please select a college.', 'warning')
            return render_template('register.html', colleges=colleges)
        
        college = College.query.get(college_id)
        if not college:
            flash('Selected college not found.', 'danger')
            return render_template('register.html', colleges=colleges)
        
        # Create user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Create role-specific profile
        if role == 'teacher':
            qualification = request.form.get('qualification', '')
            specialization = request.form.get('specialization', '')
            experience = request.form.get('experience_years', 0, type=int)
            designation = request.form.get('designation', 'Assistant Professor')
            bio = request.form.get('bio', '')
            employee_id = request.form.get('employee_id', '')
            
            profile = TeacherProfile(
                user_id=user.id,
                college_id=college_id,
                employee_id=employee_id,
                qualification=qualification,
                specialization=specialization,
                experience_years=experience,
                designation=designation,
                bio=bio
            )
            db.session.add(profile)
            college.total_teachers = TeacherProfile.query.filter_by(college_id=college.id).count()
        
        elif role == 'student':
            roll_number = request.form.get('roll_number', '')
            enrollment_number = request.form.get('enrollment_number', '')
            course = request.form.get('course', '')
            semester = request.form.get('semester', 1, type=int)
            batch_year = request.form.get('batch_year', datetime.utcnow().year, type=int)
            guardian_name = request.form.get('guardian_name', '')
            guardian_phone = request.form.get('guardian_phone', '')
            
            profile = StudentProfile(
                user_id=user.id,
                college_id=college_id,
                roll_number=roll_number,
                enrollment_number=enrollment_number,
                course=course,
                semester=semester,
                batch_year=batch_year,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone
            )
            db.session.add(profile)
            college.total_students = StudentProfile.query.filter_by(college_id=college.id).count()
        
        db.session.commit()
        log_activity(user.id, 'register', 'user', user.id, f'New {role} registered')
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', colleges=colleges)

@app.route('/logout')
@login_required
def logout():
    """User logout."""
    log_activity(current_user.id, 'logout', 'user', current_user.id)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', current_user.first_name)
        current_user.last_name = request.form.get('last_name', current_user.last_name)
        current_user.phone = request.form.get('phone', current_user.phone)
        
        # Handle avatar upload
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename, _ = save_uploaded_file(
                    file, app.config['PROFILES_FOLDER'], 
                    app.config['ALLOWED_IMAGE_EXTENSIONS']
                )
                if filename:
                    current_user.avatar = f'/static/uploads/profiles/{filename}'
        
        # Update password if provided
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        if current_password and new_password:
            if current_user.check_password(current_password):
                if len(new_password) >= 6:
                    current_user.set_password(new_password)
                    flash('Password updated successfully.', 'success')
                else:
                    flash('New password must be at least 6 characters.', 'warning')
            else:
                flash('Current password is incorrect.', 'danger')
        
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

# ============================================================
# DASHBOARD ROUTES
# ============================================================
@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - role-based redirect."""
    stats = get_dashboard_stats(current_user)
    
    if current_user.is_super_admin():
        return render_template('admin_dashboard.html', stats=stats)
    elif current_user.is_teacher():
        return render_template('teacher_dashboard.html', stats=stats)
    elif current_user.is_student():
        # Get AI study suggestions
        suggestions = []
        if current_user.student_profile:
            try:
                suggestions = get_subject_suggestions(current_user.student_profile)
            except Exception:
                pass
        return render_template('student_dashboard.html', stats=stats, suggestions=suggestions)
    
    return redirect(url_for('index'))

# ============================================================
# NOTIFICATIONS & MESSAGES
# ============================================================
@app.route('/notifications')
@login_required
def notifications():
    """View all notifications."""
    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/mark-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/notifications/mark-all-read')
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

@app.route('/messages')
@login_required
def messages():
    """View messages inbox."""
    page = request.args.get('page', 1, type=int)
    msgs = Message.query.filter_by(receiver_id=current_user.id).order_by(
        Message.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    return render_template('messages.html', messages=msgs)

@app.route('/messages/sent')
@login_required
def sent_messages():
    """View sent messages."""
    page = request.args.get('page', 1, type=int)
    msgs = Message.query.filter_by(sender_id=current_user.id).order_by(
        Message.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    return render_template('sent_messages.html', messages=msgs)

@app.route('/messages/compose', methods=['GET', 'POST'])
@login_required
def compose_message():
    """Compose and send a message."""
    if request.method == 'POST':
        receiver_id = request.form.get('receiver_id', type=int)
        subject = request.form.get('subject', '')
        content = request.form.get('content', '')
        
        if not receiver_id or not content:
            flash('Please fill in all required fields.', 'warning')
            return redirect(url_for('compose_message'))
        
        receiver = User.query.get(receiver_id)
        if not receiver:
            flash('Recipient not found.', 'danger')
            return redirect(url_for('compose_message'))
        
        msg = Message(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            subject=subject,
            content=content
        )
        db.session.add(msg)
        db.session.commit()
        
        # Create notification for receiver
        create_notification(
            user_id=receiver_id,
            title=f'New message from {current_user.full_name()}',
            message=subject or 'You have a new message',
            notification_type='message',
            reference_id=msg.id,
            reference_type='message'
        )
        
        flash('Message sent successfully.', 'success')
        return redirect(url_for('messages'))
    
    # Get possible recipients based on role
    recipients = []
    if current_user.is_teacher():
        # Students in teacher's subjects
        subject_ids = [s.id for s in current_user.teacher_profile.subjects]
        students = StudentProfile.query.filter(
            StudentProfile.enrolled_subjects.any(Subject.id.in_(subject_ids))
        ).all()
        recipients = [s.user for s in students]
    elif current_user.is_student():
        # Teachers of student's subjects
        teachers = TeacherProfile.query.filter(
            TeacherProfile.subjects.any(Subject.id.in_([s.id for s in current_user.student_profile.enrolled_subjects]))
        ).all()
        recipients = [t.user for t in teachers]
    elif current_user.is_super_admin():
        recipients = User.query.filter(User.id != current_user.id).all()
    
    return render_template('compose_message.html', recipients=recipients)

@app.route('/messages/view/<int:message_id>')
@login_required
def view_message(message_id):
    """View a specific message."""
    msg = Message.query.filter(
        (Message.id == message_id) & 
        ((Message.receiver_id == current_user.id) | (Message.sender_id == current_user.id))
    ).first_or_404()
    
    if msg.receiver_id == current_user.id and not msg.is_read:
        msg.is_read = True
        db.session.commit()
    
    return render_template('view_message.html', message=msg)

# ============================================================
# SUPER ADMIN ROUTES - COLLEGE MANAGEMENT
# ============================================================
@app.route('/admin/colleges')
@login_required
@admin_required
def admin_colleges():
    """Manage colleges."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    query = College.query
    if search:
        query = query.filter(
            College.name.contains(search) | College.code.contains(search)
        )
    if status:
        query = query.filter_by(status=status)
    
    colleges = query.order_by(College.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    return render_template('admin_colleges.html', colleges=colleges, search=search, status=status)

@app.route('/admin/colleges/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_college():
    """Create a new college."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '')
        address = request.form.get('address', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        country = request.form.get('country', 'India')
        zip_code = request.form.get('zip_code', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        website = request.form.get('website', '')
        established_year = request.form.get('established_year', type=int)
        accreditation = request.form.get('accreditation', '')
        principal_name = request.form.get('principal_name', '')
        
        if not name or not code:
            flash('College name and code are required.', 'warning')
            return render_template('college_form.html')
        
        if College.query.filter_by(code=code).first():
            flash('College code already exists.', 'warning')
            return render_template('college_form.html')
        
        college = College(
            name=name,
            code=code,
            description=description,
            address=address,
            city=city,
            state=state,
            country=country,
            zip_code=zip_code,
            phone=phone,
            email=email,
            website=website,
            established_year=established_year,
            accreditation=accreditation,
            principal_name=principal_name,
            status='active',
            created_by=current_user.id
        )
        
        # Handle logo upload
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                filename, _ = save_uploaded_file(
                    file, app.config['LOGOS_FOLDER'],
                    app.config['ALLOWED_IMAGE_EXTENSIONS']
                )
                if filename:
                    college.logo = f'/static/uploads/logos/{filename}'
        
        # Handle banner upload
        if 'banner' in request.files:
            file = request.files['banner']
            if file and file.filename:
                filename, _ = save_uploaded_file(
                    file, app.config['LOGOS_FOLDER'],
                    app.config['ALLOWED_IMAGE_EXTENSIONS']
                )
                if filename:
                    college.banner_image = f'/static/uploads/logos/{filename}'
        
        db.session.add(college)
        db.session.commit()
        
        log_activity(current_user.id, 'create_college', 'college', college.id, f'Created college: {name}')
        create_notification(
            current_user.id,
            'College Created',
            f'College "{name}" has been created successfully.',
            'announcement',
            college.id,
            'college'
        )
        
        flash(f'College "{name}" created successfully!', 'success')
        return redirect(url_for('admin_colleges'))
    
    return render_template('college_form.html')

@app.route('/admin/colleges/edit/<int:college_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_college(college_id):
    """Edit a college."""
    college = College.query.get_or_404(college_id)
    
    if request.method == 'POST':
        college.name = request.form.get('name', college.name)
        college.description = request.form.get('description', college.description)
        college.address = request.form.get('address', college.address)
        college.city = request.form.get('city', college.city)
        college.state = request.form.get('state', college.state)
        college.phone = request.form.get('phone', college.phone)
        college.email = request.form.get('email', college.email)
        college.website = request.form.get('website', college.website)
        college.established_year = request.form.get('established_year', type=int) or college.established_year
        college.accreditation = request.form.get('accreditation', college.accreditation)
        college.principal_name = request.form.get('principal_name', college.principal_name)
        college.status = request.form.get('status', college.status)
        
        # Handle logo upload
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                filename, _ = save_uploaded_file(
                    file, app.config['LOGOS_FOLDER'],
                    app.config['ALLOWED_IMAGE_EXTENSIONS']
                )
                if filename:
                    college.logo = f'/static/uploads/logos/{filename}'
        
        db.session.commit()
        log_activity(current_user.id, 'edit_college', 'college', college.id, f'Updated college: {college.name}')
        flash(f'College "{college.name}" updated successfully!', 'success')
        return redirect(url_for('admin_colleges'))
    
    return render_template('college_form.html', college=college, edit_mode=True)

@app.route('/admin/colleges/delete/<int:college_id>', methods=['POST'])
@login_required
@admin_required
def delete_college(college_id):
    """Delete a college."""
    college = College.query.get_or_404(college_id)
    name = college.name
    
    db.session.delete(college)
    db.session.commit()
    
    log_activity(current_user.id, 'delete_college', 'college', college_id, f'Deleted college: {name}')
    flash(f'College "{name}" deleted successfully.', 'success')
    return redirect(url_for('admin_colleges'))

@app.route('/admin/colleges/view/<int:college_id>')
@login_required
@admin_required
def view_college(college_id):
    """View college details."""
    college = College.query.get_or_404(college_id)
    departments = college.departments.all()
    teachers = college.teachers.all()
    students = college.students.all()
    return render_template('college_detail.html', college=college, 
                         departments=departments, teachers=teachers, students=students)

# ============================================================
# SUPER ADMIN - DEPARTMENT MANAGEMENT
# ============================================================
@app.route('/admin/colleges/<int:college_id>/departments', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_departments(college_id):
    """Manage departments for a college."""
    college = College.query.get_or_404(college_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '')
        head_name = request.form.get('head_name', '')
        
        if not name or not code:
            flash('Department name and code are required.', 'warning')
        elif Department.query.filter_by(code=code, college_id=college_id).first():
            flash('Department code already exists in this college.', 'warning')
        else:
            dept = Department(
                name=name, code=code, description=description,
                head_name=head_name, college_id=college_id
            )
            db.session.add(dept)
            db.session.commit()
            log_activity(current_user.id, 'create_department', 'department', dept.id, f'Created department: {name}')
            flash(f'Department "{name}" created successfully!', 'success')
            return redirect(url_for('manage_departments', college_id=college_id))
    
    departments = college.departments.all()
    return render_template('manage_departments.html', college=college, departments=departments)

@app.route('/admin/departments/delete/<int:dept_id>', methods=['POST'])
@login_required
@admin_required
def delete_department(dept_id):
    """Delete a department."""
    dept = Department.query.get_or_404(dept_id)
    college_id = dept.college_id
    db.session.delete(dept)
    db.session.commit()
    flash(f'Department "{dept.name}" deleted successfully.', 'success')
    return redirect(url_for('manage_departments', college_id=college_id))

# ============================================================
# SUPER ADMIN - USER MANAGEMENT
# ============================================================
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Manage all users."""
    page = request.args.get('page', 1, type=int)
    role = request.args.get('role', '')
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    query = User.query
    if role:
        query = query.filter_by(role=role)
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    if search:
        query = query.filter(
            (User.username.contains(search)) | 
            (User.email.contains(search)) |
            (User.first_name.contains(search)) |
            (User.last_name.contains(search))
        )
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin_users.html', users=users, role=role, search=search, status=status)

@app.route('/admin/users/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status."""
    user = User.query.get_or_404(user_id)
    if user.is_super_admin():
        flash('Cannot modify super admin status.', 'danger')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    log_activity(current_user.id, f'{status}_user', 'user', user.id, f'{status.title()} user: {user.username}')
    flash(f'User "{user.username}" {status}.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    if user.is_super_admin():
        flash('Cannot delete super admin.', 'danger')
        return redirect(url_for('admin_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_activity(current_user.id, 'delete_user', 'user', user_id, f'Deleted user: {username}')
    flash(f'User "{username}" deleted.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():
    """Admin analytics dashboard."""
    # Growth data (last 6 months)
    months = []
    for i in range(5, -1, -1):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
        months.append(month_start.strftime('%b %Y'))
    
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'users_by_role': {
            'super_admin': User.query.filter_by(role='super_admin').count(),
            'teachers': User.query.filter_by(role='teacher').count(),
            'students': User.query.filter_by(role='student').count()
        },
        'colleges_by_status': {
            'active': College.query.filter_by(status='active').count(),
            'inactive': College.query.filter_by(status='inactive').count(),
            'suspended': College.query.filter_by(status='suspended').count()
        },
        'total_materials': Material.query.count(),
        'total_assignments': Assignment.query.count(),
        'total_tests': Test.query.count(),
        'total_submissions': Submission.query.count(),
        'months': months
    }
    return render_template('admin_analytics.html', stats=stats)

# ============================================================
# TEACHER ROUTES
# ============================================================
@app.route('/teacher/subjects')
@login_required
@teacher_required
def teacher_subjects():
    """Teacher's subjects."""
    subjects = current_user.teacher_profile.subjects.all()
    college_departments = Department.query.filter_by(
        college_id=current_user.teacher_profile.college_id
    ).all()
    return render_template('teacher_subjects.html', subjects=subjects, departments=college_departments)

@app.route('/teacher/subjects/create', methods=['POST'])
@login_required
@teacher_required
def create_subject():
    """Create a new subject."""
    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip().upper()
    description = request.form.get('description', '')
    credits = request.form.get('credits', 3, type=int)
    semester = request.form.get('semester', 1, type=int)
    department_id = request.form.get('department_id', type=int)
    syllabus = request.form.get('syllabus', '')
    
    if not name or not code or not department_id:
        flash('Subject name, code and department are required.', 'warning')
        return redirect(url_for('teacher_subjects'))
    
    dept = Department.query.get(department_id)
    if not dept or dept.college_id != current_user.teacher_profile.college_id:
        flash('Invalid department selected.', 'danger')
        return redirect(url_for('teacher_subjects'))
    
    subject = Subject(
        name=name, code=code, description=description,
        credits=credits, semester=semester, department_id=department_id,
        teacher_id=current_user.teacher_profile.id, syllabus=syllabus
    )
    db.session.add(subject)
    db.session.commit()
    
    # Notify enrolled students
    college_students = StudentProfile.query.filter_by(college_id=current_user.teacher_profile.college_id).all()
    for student in college_students:
        create_notification(
            student.user_id,
            f'New Subject: {name}',
            f'{current_user.full_name()} has added a new subject: {name} ({code})',
            'announcement',
            subject.id,
            'subject'
        )
    
    log_activity(current_user.id, 'create_subject', 'subject', subject.id, f'Created subject: {name}')
    flash(f'Subject "{name}" created successfully!', 'success')
    return redirect(url_for('teacher_subjects'))

@app.route('/teacher/subjects/<int:subject_id>')
@login_required
@teacher_required
def view_teacher_subject(subject_id):
    """View subject details from teacher perspective."""
    subject = Subject.query.get_or_404(subject_id)
    if subject.teacher_id != current_user.teacher_profile.id:
        flash('You can only view your own subjects.', 'danger')
        return redirect(url_for('teacher_subjects'))
    
    materials = subject.materials.order_by(Material.created_at.desc()).all()
    assignments = subject.assignments.order_by(Assignment.created_at.desc()).all()
    tests = subject.tests.order_by(Test.created_at.desc()).all()
    students = subject.enrolled_students
    
    return render_template('teacher_subject_detail.html', subject=subject,
                         materials=materials, assignments=assignments, tests=tests, students=students)

@app.route('/teacher/materials')
@login_required
@teacher_required
def teacher_materials():
    """Teacher's study materials."""
    page = request.args.get('page', 1, type=int)
    subject_id = request.args.get('subject_id', type=int)
    
    query = Material.query.filter_by(teacher_id=current_user.teacher_profile.id)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    materials = query.order_by(Material.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    subjects = current_user.teacher_profile.subjects.all()
    return render_template('teacher_materials.html', materials=materials, subjects=subjects, current_subject_id=subject_id)

@app.route('/teacher/materials/upload', methods=['POST'])
@login_required
@teacher_required
def upload_material():
    """Upload study material."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '')
    content_type = request.form.get('content_type', 'notes')
    external_link = request.form.get('external_link', '')
    subject_id = request.form.get('subject_id', type=int)
    
    if not title or not subject_id:
        flash('Title and subject are required.', 'warning')
        return redirect(url_for('teacher_materials'))
    
    subject = Subject.query.get(subject_id)
    if not subject or subject.teacher_id != current_user.teacher_profile.id:
        flash('Invalid subject.', 'danger')
        return redirect(url_for('teacher_materials'))
    
    material = Material(
        title=title, description=description, content_type=content_type,
        external_link=external_link if external_link else None,
        subject_id=subject_id, teacher_id=current_user.teacher_profile.id
    )
    
    # Handle file upload
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            filename, filesize = save_uploaded_file(
                file, app.config['NOTES_FOLDER']
            )
            if filename:
                material.file_path = f'/static/uploads/notes/{filename}'
                material.file_type = file.filename.rsplit('.', 1)[1].lower()
                material.file_size = filesize
    
    if not material.file_path and not material.external_link:
        flash('Please upload a file or provide an external link.', 'warning')
        return redirect(url_for('teacher_materials'))
    
    db.session.add(material)
    db.session.commit()
    
    # Notify enrolled students
    for student in subject.enrolled_students:
        create_notification(
            student.user_id,
            f'New Material: {title}',
            f'New {content_type} uploaded for {subject.name}',
            'assignment',
            material.id,
            'material'
        )
    
    log_activity(current_user.id, 'upload_material', 'material', material.id, f'Uploaded: {title}')
    flash(f'Material "{title}" uploaded successfully!', 'success')
    return redirect(url_for('teacher_materials'))

@app.route('/teacher/materials/delete/<int:material_id>', methods=['POST'])
@login_required
@teacher_required
def delete_material(material_id):
    """Delete a study material."""
    material = Material.query.get_or_404(material_id)
    if material.teacher_id != current_user.teacher_profile.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('teacher_materials'))
    
    if material.file_path:
        delete_file(os.path.join(app.root_path, material.file_path.lstrip('/')))
    
    db.session.delete(material)
    db.session.commit()
    flash('Material deleted.', 'success')
    return redirect(url_for('teacher_materials'))

@app.route('/teacher/assignments')
@login_required
@teacher_required
def teacher_assignments():
    """Teacher's assignments."""
    page = request.args.get('page', 1, type=int)
    subject_id = request.args.get('subject_id', type=int)
    status = request.args.get('status', '')
    
    query = Assignment.query.filter_by(teacher_id=current_user.teacher_profile.id)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if status:
        query = query.filter_by(status=status)
    
    assignments = query.order_by(Assignment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    subjects = current_user.teacher_profile.subjects.all()
    return render_template('teacher_assignments.html', assignments=assignments, subjects=subjects)

@app.route('/teacher/assignments/create', methods=['POST'])
@login_required
@teacher_required
def create_assignment():
    """Create a new assignment."""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '')
    instructions = request.form.get('instructions', '')
    total_marks = request.form.get('total_marks', 100, type=int)
    passing_marks = request.form.get('passing_marks', 40, type=int)
    due_date_str = request.form.get('due_date', '')
    subject_id = request.form.get('subject_id', type=int)
    allow_late = request.form.get('allow_late_submission') == 'on'
    
    if not title or not due_date_str or not subject_id:
        flash('Title, due date and subject are required.', 'warning')
        return redirect(url_for('teacher_assignments'))
    
    subject = Subject.query.get(subject_id)
    if not subject or subject.teacher_id != current_user.teacher_profile.id:
        flash('Invalid subject.', 'danger')
        return redirect(url_for('teacher_assignments'))
    
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date format.', 'warning')
        return redirect(url_for('teacher_assignments'))
    
    assignment = Assignment(
        title=title, description=description, instructions=instructions,
        total_marks=total_marks, passing_marks=passing_marks,
        due_date=due_date, subject_id=subject_id,
        teacher_id=current_user.teacher_profile.id,
        allow_late_submission=allow_late
    )
    
    # Handle attachment
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            filename, _ = save_uploaded_file(file, app.config['ASSIGNMENTS_FOLDER'])
            if filename:
                assignment.attachment_path = f'/static/uploads/assignments/{filename}'
    
    db.session.add(assignment)
    db.session.commit()
    
    # Notify students
    for student in subject.enrolled_students:
        create_notification(
            student.user_id,
            f'New Assignment: {title}',
            f'New assignment in {subject.name}. Due: {due_date.strftime("%d %b %Y, %I:%M %p")}',
            'assignment',
            assignment.id,
            'assignment'
        )
    
    log_activity(current_user.id, 'create_assignment', 'assignment', assignment.id, f'Created: {title}')
    flash(f'Assignment "{title}" created!', 'success')
    return redirect(url_for('teacher_assignments'))

@app.route('/teacher/assignments/<int:assignment_id>/submissions')
@login_required
@teacher_required
def view_submissions(assignment_id):
    """View submissions for an assignment."""
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.teacher_id != current_user.teacher_profile.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('teacher_assignments'))
    
    submissions = assignment.submissions.order_by(Submission.submitted_at.desc()).all()
    return render_template('view_submissions.html', assignment=assignment, submissions=submissions)

@app.route('/teacher/submissions/grade/<int:submission_id>', methods=['POST'])
@login_required
@teacher_required
def grade_submission(submission_id):
    """Grade a submission."""
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    
    if assignment.teacher_id != current_user.teacher_profile.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('teacher_assignments'))
    
    marks = request.form.get('marks', type=float)
    feedback = request.form.get('feedback', '')
    
    if marks is None:
        flash('Please enter marks.', 'warning')
        return redirect(url_for('view_submissions', assignment_id=assignment.id))
    
    if marks > assignment.total_marks:
        flash(f'Marks cannot exceed {assignment.total_marks}.', 'warning')
        return redirect(url_for('view_submissions', assignment_id=assignment.id))
    
    submission.marks_obtained = marks
    submission.feedback = feedback
    submission.status = 'graded'
    submission.graded_at = datetime.utcnow()
    db.session.commit()
    
    # Notify student
    create_notification(
        submission.student.user_id,
        f'Assignment Graded: {assignment.title}',
        f'You scored {marks}/{assignment.total_marks}',
        'assignment',
        assignment.id,
        'assignment'
    )
    
    flash('Submission graded successfully.', 'success')
    return redirect(url_for('view_submissions', assignment_id=assignment.id))

@app.route('/teacher/tests')
@login_required
@teacher_required
def teacher_tests():
    """Teacher's tests."""
    page = request.args.get('page', 1, type=int)
    subject_id = request.args.get('subject_id', type=int)
    status = request.args.get('status', '')
    
    query = Test.query.filter_by(teacher_id=current_user.teacher_profile.id)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if status:
        query = query.filter_by(status=status)
    
    tests = query.order_by(Test.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    subjects = current_user.teacher_profile.subjects.all()
    return render_template('teacher_tests.html', tests=tests, subjects=subjects)

@app.route('/teacher/tests/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_test():
    """Create a new test."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '')
        instructions = request.form.get('instructions', '')
        total_marks = request.form.get('total_marks', 100, type=int)
        passing_marks = request.form.get('passing_marks', 40, type=int)
        duration = request.form.get('duration_minutes', 60, type=int)
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        subject_id = request.form.get('subject_id', type=int)
        shuffle = request.form.get('shuffle_questions') == 'on'
        show_result = request.form.get('show_result_immediately') == 'on'
        max_attempts = request.form.get('max_attempts', 1, type=int)
        
        if not title or not subject_id:
            flash('Title and subject are required.', 'warning')
            return redirect(url_for('create_test'))
        
        subject = Subject.query.get(subject_id)
        if not subject or subject.teacher_id != current_user.teacher_profile.id:
            flash('Invalid subject.', 'danger')
            return redirect(url_for('teacher_tests'))
        
        test = Test(
            title=title, description=description, instructions=instructions,
            total_marks=total_marks, passing_marks=passing_marks,
            duration_minutes=duration, subject_id=subject_id,
            teacher_id=current_user.teacher_profile.id,
            shuffle_questions=shuffle, show_result_immediately=show_result,
            max_attempts=max_attempts, status='draft'
        )
        
        if start_time_str:
            try:
                test.start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        if end_time_str:
            try:
                test.end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        db.session.add(test)
        db.session.commit()
        
        log_activity(current_user.id, 'create_test', 'test', test.id, f'Created test: {title}')
        flash(f'Test "{title}" created! Now add questions.', 'success')
        return redirect(url_for('edit_test_questions', test_id=test.id))
    
    subjects = current_user.teacher_profile.subjects.all()
    return render_template('create_test.html', subjects=subjects)

@app.route('/teacher/tests/<int:test_id>/questions', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_test_questions(test_id):
    """Add/edit questions for a test."""
    test = Test.query.get_or_404(test_id)
    if test.teacher_id != current_user.teacher_profile.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('teacher_tests'))
    
    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        question_type = request.form.get('question_type', 'mcq')
        correct_answer = request.form.get('correct_answer', '')
        marks = request.form.get('marks', 1, type=int)
        explanation = request.form.get('explanation', '')
        
        if not question_text:
            flash('Question text is required.', 'warning')
            return redirect(url_for('edit_test_questions', test_id=test_id))
        
        question = Question(
            test_id=test_id, question_text=question_text,
            question_type=question_type, correct_answer=correct_answer,
            marks=marks, explanation=explanation,
            order=test.questions.count() + 1
        )
        
        # Handle MCQ options
        if question_type == 'mcq':
            options = []
            for i in range(1, 5):
                opt = request.form.get(f'option_{i}', '').strip()
                if opt:
                    options.append(opt)
            if options:
                question.set_options(options)
        
        db.session.add(question)
        db.session.commit()
        flash('Question added!', 'success')
        return redirect(url_for('edit_test_questions', test_id=test_id))
    
    questions = test.questions.order_by(Question.order).all()
    return render_template('edit_test_questions.html', test=test, questions=questions)

@app.route('/teacher/tests/<int:test_id>/publish', methods=['POST'])
@login_required
@teacher_required
def publish_test(test_id):
    """Publish a test."""
    test = Test.query.get_or_404(test_id)
    if test.teacher_id != current_user.teacher_profile.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('teacher_tests'))
    
    if test.questions.count() == 0:
        flash('Cannot publish a test without questions.', 'warning')
        return redirect(url_for('edit_test_questions', test_id=test_id))
    
    test.status = 'published'
    db.session.commit()
    
    # Notify students
    subject = test.subject
    for student in subject.enrolled_students:
        create_notification(
            student.user_id,
            f'Test Published: {test.title}',
            f'New test in {subject.name}. Duration: {test.duration_minutes} mins',
            'test',
            test.id,
            'test'
        )
    
    flash(f'Test "{test.title}" published!', 'success')
    return redirect(url_for('teacher_tests'))

@app.route('/teacher/tests/<int:test_id>/results')
@login_required
@teacher_required
def view_test_results(test_id):
    """View test results."""
    test = Test.query.get_or_404(test_id)
    if test.teacher_id != current_user.teacher_profile.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('teacher_tests'))
    
    attempts = test.attempts.order_by(TestAttempt.percentage.desc()).all()
    
    # Calculate statistics
    stats = {}
    if attempts:
        scores = [a.percentage for a in attempts]
        stats = {
            'total_attempts': len(attempts),
            'average_score': round(sum(scores) / len(scores), 1),
            'highest_score': round(max(scores), 1),
            'lowest_score': round(min(scores), 1),
            'pass_count': len([s for s in scores if s >= 40])
        }
    
    return render_template('view_test_results.html', test=test, attempts=attempts, stats=stats)

@app.route('/teacher/students')
@login_required
@teacher_required
def teacher_students():
    """View students enrolled in teacher's subjects."""
    subject_ids = [s.id for s in current_user.teacher_profile.subjects]
    students = StudentProfile.query.filter(
        StudentProfile.enrolled_subjects.any(Subject.id.in_(subject_ids))
    ).all()
    
    subjects = current_user.teacher_profile.subjects.all()
    return render_template('teacher_students.html', students=students, subjects=subjects)

@app.route('/teacher/students/manage-enrollment', methods=['POST'])
@login_required
@teacher_required
def manage_enrollment():
    """Add/remove students from subjects."""
    student_id = request.form.get('student_id', type=int)
    subject_id = request.form.get('subject_id', type=int)
    action = request.form.get('action', 'enroll')
    
    student = StudentProfile.query.get_or_404(student_id)
    subject = Subject.query.get_or_404(subject_id)
    
    if subject.teacher_id != current_user.teacher_profile.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('teacher_students'))
    
    if action == 'enroll':
        if subject not in student.enrolled_subjects:
            student.enrolled_subjects.append(subject)
            db.session.commit()
            flash(f'{student.user.full_name()} enrolled in {subject.name}.', 'success')
    elif action == 'unenroll':
        if subject in student.enrolled_subjects:
            student.enrolled_subjects.remove(subject)
            db.session.commit()
            flash(f'{student.user.full_name()} removed from {subject.name}.', 'success')
    
    return redirect(url_for('teacher_students'))

# ============================================================
# STUDENT ROUTES
# ============================================================
@app.route('/student/colleges')
@login_required
@student_required
def student_colleges():
    """Browse available colleges."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = College.query.filter_by(status='active')
    if search:
        query = query.filter(
            College.name.contains(search) | College.city.contains(search)
        )
    
    colleges = query.order_by(College.name).paginate(
        page=page, per_page=12, error_out=False
    )
    return render_template('student_colleges.html', colleges=colleges, search=search)

@app.route('/student/college/<int:college_id>')
@login_required
@student_required
def view_college_detail(college_id):
    """View college details and teachers."""
    college = College.query.get_or_404(college_id)
    departments = college.departments.all()
    teachers = TeacherProfile.query.filter_by(college_id=college_id, is_active=True).all()
    
    # Get subjects for each teacher
    teacher_data = []
    for teacher in teachers:
        teacher_data.append({
            'teacher': teacher,
            'subjects': teacher.subjects.all(),
            'materials_count': sum(s.materials.count() for s in teacher.subjects)
        })
    
    return render_template('college_teachers.html', college=college, 
                         departments=departments, teacher_data=teacher_data)

@app.route('/student/my-teachers')
@login_required
@student_required
def student_teachers():
    """View my teachers."""
    student = current_user.student_profile
    teachers = []
    seen_ids = set()
    
    for subject in student.enrolled_subjects:
        if subject.teacher and subject.teacher.id not in seen_ids:
            teachers.append(subject.teacher)
            seen_ids.add(subject.teacher.id)
    
    return render_template('student_teachers.html', teachers=teachers)

@app.route('/student/subjects')
@login_required
@student_required
def student_subjects():
    """View enrolled and available subjects."""
    student = current_user.student_profile
    enrolled = student.enrolled_subjects

    # Get all active subjects from the same college that student is NOT enrolled in
    enrolled_ids = [s.id for s in enrolled]
    available = Subject.query.join(Department).filter(
        Department.college_id == student.college_id,
        Subject.status == 'active',
        ~Subject.id.in_(enrolled_ids) if enrolled_ids else True
    ).all()

    return render_template('student_subjects.html', subjects=enrolled, available_subjects=available)

@app.route('/student/enroll-subject/<int:subject_id>', methods=['POST'])
@login_required
@student_required
def enroll_subject(subject_id):
    """Enroll in a subject."""
    subject = Subject.query.get_or_404(subject_id)
    student = current_user.student_profile
    
    if subject in student.enrolled_subjects:
        flash('Already enrolled in this subject.', 'info')
    else:
        student.enrolled_subjects.append(subject)
        db.session.commit()
        
        # Notify teacher
        if subject.teacher:
            create_notification(
                subject.teacher.user_id,
                'New Enrollment',
                f'{current_user.full_name()} enrolled in {subject.name}',
                'general',
                student.id,
                'student'
            )
        
        flash(f'Enrolled in {subject.name} successfully!', 'success')
    
    return redirect(url_for('student_subjects'))

@app.route('/student/unenroll-subject/<int:subject_id>', methods=['POST'])
@login_required
@student_required
def unenroll_subject(subject_id):
    """Unenroll from a subject."""
    subject = Subject.query.get_or_404(subject_id)
    student = current_user.student_profile
    
    if subject in student.enrolled_subjects:
        student.enrolled_subjects.remove(subject)
        db.session.commit()
        flash(f'Unenrolled from {subject.name}.', 'success')
    
    return redirect(url_for('student_subjects'))

@app.route('/student/materials')
@login_required
@student_required
def student_materials():
    """View study materials for enrolled subjects."""
    page = request.args.get('page', 1, type=int)
    subject_id = request.args.get('subject_id', type=int)
    
    enrolled_ids = [s.id for s in current_user.student_profile.enrolled_subjects]
    
    query = Material.query.filter(Material.subject_id.in_(enrolled_ids) if enrolled_ids else False)
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    materials = query.order_by(Material.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    subjects = current_user.student_profile.enrolled_subjects
    return render_template('student_materials.html', materials=materials, subjects=subjects)

@app.route('/student/materials/download/<int:material_id>')
@login_required
@student_required
def download_material(material_id):
    """Download a study material."""
    material = Material.query.get_or_404(material_id)
    
    # Check if student is enrolled in this subject
    student = current_user.student_profile
    if material.subject not in student.enrolled_subjects:
        flash('You must be enrolled in this subject to download materials.', 'warning')
        return redirect(url_for('student_materials'))
    
    if material.file_path:
        material.download_count += 1
        db.session.commit()
        
        directory = os.path.join(app.root_path, 'static', 'uploads', 'notes')
        filename = os.path.basename(material.file_path)
        return send_from_directory(directory, filename, as_download=True)
    
    if material.external_link:
        return redirect(material.external_link)
    
    flash('File not available.', 'danger')
    return redirect(url_for('student_materials'))

@app.route('/student/assignments')
@login_required
@student_required
def student_assignments():
    """View assignments for enrolled subjects."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    enrolled_ids = [s.id for s in current_user.student_profile.enrolled_subjects]
    student_id = current_user.student_profile.id
    
    query = Assignment.query.filter(
        Assignment.subject_id.in_(enrolled_ids) if enrolled_ids else False,
        Assignment.status == 'active'
    )
    
    assignments_data = []
    for assignment in query.order_by(Assignment.due_date).all():
        submission = Submission.query.filter_by(
            assignment_id=assignment.id, student_id=student_id
        ).first()
        
        assignments_data.append({
            'assignment': assignment,
            'submission': submission,
            'days_left': get_days_remaining(assignment.due_date)
        })
    
    if status == 'pending':
        assignments_data = [a for a in assignments_data if not a['submission']]
    elif status == 'submitted':
        assignments_data = [a for a in assignments_data if a['submission']]
    
    return render_template('student_assignments.html', assignments_data=assignments_data, status=status)

@app.route('/student/assignments/submit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@student_required
def submit_assignment(assignment_id):
    """Submit an assignment."""
    assignment = Assignment.query.get_or_404(assignment_id)
    student = current_user.student_profile
    
    if assignment.subject not in student.enrolled_subjects:
        flash('You are not enrolled in this subject.', 'danger')
        return redirect(url_for('student_assignments'))
    
    # Check if already submitted
    existing = Submission.query.filter_by(assignment_id=assignment_id, student_id=student.id).first()
    if existing:
        flash('You have already submitted this assignment.', 'info')
        return redirect(url_for('student_assignments'))
    
    if request.method == 'POST':
        comments = request.form.get('comments', '')
        
        submission = Submission(
            assignment_id=assignment_id,
            student_id=student.id,
            comments=comments
        )
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                filename, _ = save_uploaded_file(file, app.config['ASSIGNMENTS_FOLDER'])
                if filename:
                    submission.file_path = f'/static/uploads/assignments/{filename}'
        
        db.session.add(submission)
        db.session.commit()
        
        # Notify teacher
        create_notification(
            assignment.teacher.user_id,
            'New Submission',
            f'{current_user.full_name()} submitted "{assignment.title}"',
            'assignment',
            assignment.id,
            'assignment'
        )
        
        flash('Assignment submitted successfully!', 'success')
        return redirect(url_for('student_assignments'))
    
    return render_template('submit_assignment.html', assignment=assignment)

@app.route('/student/tests')
@login_required
@student_required
def student_tests():
    """View available tests."""
    enrolled_ids = [s.id for s in current_user.student_profile.enrolled_subjects]
    student_id = current_user.student_profile.id
    
    tests_data = []
    if enrolled_ids:
        tests = Test.query.filter(
            Test.subject_id.in_(enrolled_ids),
            Test.status.in_(['published', 'active'])
        ).order_by(Test.start_time).all()
        
        for test in tests:
            attempts = TestAttempt.query.filter_by(test_id=test.id, student_id=student_id).count()
            tests_data.append({
                'test': test,
                'attempts': attempts,
                'can_attempt': attempts < test.max_attempts
            })
    
    return render_template('student_tests.html', tests_data=tests_data)

@app.route('/student/tests/take/<int:test_id>')
@login_required
@student_required
def take_test(test_id):
    """Start taking a test."""
    test = Test.query.get_or_404(test_id)
    student = current_user.student_profile
    
    if test.subject not in student.enrolled_subjects:
        flash('You are not enrolled in this subject.', 'danger')
        return redirect(url_for('student_tests'))
    
    # Check attempts
    attempts = TestAttempt.query.filter_by(test_id=test_id, student_id=student.id).count()
    if attempts >= test.max_attempts:
        flash('Maximum attempts reached for this test.', 'warning')
        return redirect(url_for('student_tests'))
    
    # Check if test is active
    if test.status != 'published' and test.status != 'active':
        flash('This test is not available.', 'warning')
        return redirect(url_for('student_tests'))
    
    # Create attempt
    attempt = TestAttempt(
        test_id=test_id,
        student_id=student.id,
        status='in_progress',
        started_at=datetime.utcnow()
    )
    db.session.add(attempt)
    db.session.commit()
    
    # Get questions
    questions = test.questions.order_by(Question.order).all()
    
    return render_template('take_test.html', test=test, questions=questions, attempt=attempt)

@app.route('/student/tests/submit/<int:attempt_id>', methods=['POST'])
@login_required
@student_required
def submit_test(attempt_id):
    """Submit test answers."""
    attempt = TestAttempt.query.get_or_404(attempt_id)
    student = current_user.student_profile
    
    if attempt.student_id != student.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('student_tests'))
    
    test = attempt.test
    questions = test.questions.all()
    
    answers = {}
    total_score = 0
    total_marks = sum(q.marks for q in questions)
    
    for question in questions:
        answer = request.form.get(f'question_{question.id}', '')
        answers[str(question.id)] = answer
        
        # Auto-grade
        if question.question_type in ['mcq', 'true_false']:
            if answer.strip().lower() == question.correct_answer.strip().lower():
                total_score += question.marks
    
    attempt.set_answers(answers)
    attempt.score = total_score
    attempt.total_marks = total_marks
    attempt.percentage = round((total_score / total_marks) * 100, 2) if total_marks > 0 else 0
    attempt.status = 'completed'
    attempt.completed_at = datetime.utcnow()
    
    if attempt.started_at:
        time_taken = attempt.completed_at - attempt.started_at
        attempt.time_taken_minutes = int(time_taken.total_seconds() / 60)
    
    db.session.commit()
    
    flash(f'Test submitted! Score: {total_score}/{total_marks} ({attempt.percentage}%)', 'success')
    
    if test.show_result_immediately:
        return redirect(url_for('test_result', attempt_id=attempt.id))
    return redirect(url_for('student_tests'))

@app.route('/student/tests/result/<int:attempt_id>')
@login_required
@student_required
def test_result(attempt_id):
    """View test result."""
    attempt = TestAttempt.query.get_or_404(attempt_id)
    student = current_user.student_profile
    
    if attempt.student_id != student.id:
        flash('Permission denied.', 'danger')
        return redirect(url_for('student_tests'))
    
    test = attempt.test
    questions = test.questions.all()
    answers = attempt.get_answers()
    
    return render_template('test_result.html', attempt=attempt, test=test, 
                         questions=questions, answers=answers)

@app.route('/student/tests/history')
@login_required
@student_required
def test_history():
    """View test history."""
    page = request.args.get('page', 1, type=int)
    attempts = TestAttempt.query.filter_by(
        student_id=current_user.student_profile.id,
        status='completed'
    ).order_by(TestAttempt.completed_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('test_history.html', attempts=attempts)

# ============================================================
# AI STUDY PLANNER ROUTES
# ============================================================
@app.route('/student/study-planner')
@login_required
@student_required
def study_planner():
    """AI Study Planner dashboard."""
    student = current_user.student_profile
    plans = StudyPlan.query.filter_by(user_id=current_user.id).order_by(
        StudyPlan.created_at.desc()
    ).all()
    
    # Get AI suggestions
    suggestions = get_subject_suggestions(student)
    
    # Get pattern analysis
    pattern_analysis = AIStudyPlanner.analyze_study_patterns(student.id)
    
    return render_template('study_planner.html', plans=plans, suggestions=suggestions,
                         pattern_analysis=pattern_analysis)

@app.route('/student/study-planner/generate', methods=['POST'])
@login_required
@student_required
def generate_study_plan():
    """Generate AI study plan."""
    title = request.form.get('title', '').strip()
    daily_hours = request.form.get('daily_hours', 6, type=float)
    target_date_str = request.form.get('target_date', '')
    description = request.form.get('description', '')
    
    if not title:
        flash('Plan title is required.', 'warning')
        return redirect(url_for('study_planner'))
    
    student = current_user.student_profile
    
    try:
        target_date = None
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        
        plan_data = generate_smart_schedule(student, daily_hours)
        
        study_plan = StudyPlan(
            user_id=current_user.id,
            title=title,
            description=description,
            target_date=target_date,
            daily_hours=daily_hours,
            status='active'
        )
        study_plan.set_plan_data(plan_data)
        study_plan.set_priority_subjects([s['subject_id'] for s in plan_data.get('subject_priorities', [])])
        
        db.session.add(study_plan)
        db.session.commit()
        
        flash('AI Study Plan generated successfully!', 'success')
        return redirect(url_for('view_study_plan', plan_id=study_plan.id))
    
    except Exception as e:
        flash(f'Error generating study plan: {str(e)}', 'danger')
        return redirect(url_for('study_planner'))

@app.route('/student/study-planner/<int:plan_id>')
@login_required
@student_required
def view_study_plan(plan_id):
    """View a study plan."""
    plan = StudyPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    plan_data = plan.get_plan_data()
    return render_template('view_study_plan.html', plan=plan, plan_data=plan_data)

@app.route('/student/study-planner/delete/<int:plan_id>', methods=['POST'])
@login_required
@student_required
def delete_study_plan(plan_id):
    """Delete a study plan."""
    plan = StudyPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    db.session.delete(plan)
    db.session.commit()
    flash('Study plan deleted.', 'success')
    return redirect(url_for('study_planner'))

@app.route('/student/study-planner/update-progress/<int:plan_id>', methods=['POST'])
@login_required
@student_required
def update_plan_progress(plan_id):
    """Update study plan progress."""
    plan = StudyPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    progress = request.form.get('progress', 0, type=float)
    plan.progress_percentage = min(100, max(0, progress))
    
    if plan.progress_percentage >= 100:
        plan.status = 'completed'
    
    db.session.commit()
    flash('Progress updated!', 'success')
    return redirect(url_for('view_study_plan', plan_id=plan_id))

# ============================================================
# API ROUTES (AJAX)
# ============================================================
@app.route('/api/notifications/unread-count')
@login_required
def api_unread_notifications():
    """Get unread notification count."""
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/search-students')
@login_required
def api_search_students():
    """Search students for enrollment."""
    query = request.args.get('q', '')
    college_id = request.args.get('college_id', type=int)
    
    if not query or not college_id:
        return jsonify({'students': []})
    
    students = StudentProfile.query.filter(
        StudentProfile.college_id == college_id,
        (User.first_name.contains(query)) | (User.last_name.contains(query)) | 
        (User.username.contains(query)) | (StudentProfile.roll_number.contains(query))
    ).join(User).limit(10).all()
    
    return jsonify({
        'students': [{
            'id': s.id,
            'name': s.user.full_name(),
            'roll_number': s.roll_number,
            'username': s.user.username
        } for s in students]
    })

@app.route('/api/college-stats/<int:college_id>')
@login_required
def api_college_stats(college_id):
    """Get college statistics."""
    college = College.query.get_or_404(college_id)
    return jsonify({
        'departments': college.departments.count(),
        'teachers': college.teachers.count(),
        'students': college.students.count(),
        'total_subjects': sum(d.subjects.count() for d in college.departments)
    })

# ============================================================
# FILE DOWNLOAD ROUTES
# ============================================================
@app.route('/uploads/<folder>/<filename>')
@login_required
def serve_upload(folder, filename):
    """Serve uploaded files securely."""
    allowed_folders = ['notes', 'assignments', 'tests', 'logos', 'profiles']
    if folder not in allowed_folders:
        abort(404)
    
    directory = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    return send_from_directory(directory, filename)

# ============================================================
# ANNOUNCEMENTS
# ============================================================
@app.route('/announcements')
@login_required
def announcements():
    """View announcements."""
    page = request.args.get('page', 1, type=int)
    
    if current_user.is_super_admin():
        announcements_list = Announcement.query.order_by(Announcement.created_at.desc())
    elif current_user.is_teacher():
        college_id = current_user.teacher_profile.college_id
        announcements_list = Announcement.query.filter_by(college_id=college_id).order_by(
            Announcement.created_at.desc()
        )
    else:
        college_id = current_user.student_profile.college_id
        announcements_list = Announcement.query.filter_by(college_id=college_id).order_by(
            Announcement.created_at.desc()
        )
    
    announcements = announcements_list.paginate(page=page, per_page=20, error_out=False)
    return render_template('announcements.html', announcements=announcements)

@app.route('/announcements/create', methods=['POST'])
@login_required
def create_announcement():
    """Create an announcement."""
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '')
    priority = request.form.get('priority', 'normal')
    
    if not title or not content:
        flash('Title and content are required.', 'warning')
        return redirect(url_for('announcements'))
    
    college_id = None
    if current_user.is_teacher():
        college_id = current_user.teacher_profile.college_id
    elif current_user.is_student():
        college_id = current_user.student_profile.college_id
    else:
        college_id = request.form.get('college_id', type=int)
    
    if not college_id:
        flash('College ID is required.', 'warning')
        return redirect(url_for('announcements'))
    
    announcement = Announcement(
        title=title, content=content, priority=priority,
        college_id=college_id, created_by=current_user.id
    )
    db.session.add(announcement)
    db.session.commit()
    
    flash('Announcement published!', 'success')
    return redirect(url_for('announcements'))

# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == '__main__':
    setup_database()
    print("=" * 60)
    print("  AI STUDY PLANNER - Multi-Tenant Education System")
    print("  Developer: Mohammed Usman | GitHub: issu321")
    print("  Contact: 8884294749 | jaafreeusman@gmail.com")
    print("=" * 60)
    print(f"  Default Admin: username={Config.DEFAULT_ADMIN_USERNAME}")
    print(f"  Default Pass:  {Config.DEFAULT_ADMIN_PASSWORD}")
    print("=" * 60)
    print("  Starting server at http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)