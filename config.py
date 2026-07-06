"""
AI Study Planner - Configuration
Premium Multi-Tenant Education Management System
Developer: Mohammed Usman | GitHub: issu321
"""
import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'AiStudyPlanner_SecretKey_2024_UltraProMax_by_MohammedUsman'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "study_planner.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # File upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    NOTES_FOLDER = os.path.join(UPLOAD_FOLDER, 'notes')
    ASSIGNMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'assignments')
    TESTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'tests')
    LOGOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'logos')
    PROFILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')
    
    # Allowed file extensions
    ALLOWED_NOTE_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'zip', 'rar'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
    ALLOWED_ASSIGNMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'zip', 'rar', 'py', 'java', 'cpp', 'c'}
    
    # Default admin credentials
    DEFAULT_ADMIN_USERNAME = 'usman'
    DEFAULT_ADMIN_PASSWORD = 'wsxcfty@9009'
    DEFAULT_ADMIN_EMAIL = 'jaafreeusman@gmail.com'
    DEFAULT_ADMIN_NAME = 'Mohammed Usman'
    DEFAULT_ADMIN_PHONE = '8884294749'
    
    # Developer info
    DEVELOPER_NAME = 'Mohammed Usman'
    DEVELOPER_GITHUB = 'https://github.com/issu321'
    DEVELOPER_EMAIL = 'jaafreeusman@gmail.com'
    DEVELOPER_PHONE = '8884294749'
    DEVELOPER_ROLE = 'Full Stack Developer & Software Architect'
    DEVELOPER_BIO = 'Building premium educational technology solutions. AI Study Planner is designed to revolutionize academic management with intelligent planning and seamless multi-tenant architecture.'
    
    # AI Study Planner settings
    AI_PLANNING_HORIZON_DAYS = 30
    MAX_STUDY_HOURS_PER_DAY = 12
    DEFAULT_STUDY_HOURS_PER_DAY = 6
