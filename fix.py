"""
One-time fix: Auto-enroll all existing students into their college's active subjects.
Run this in your project directory: python fix_existing_students.py
"""
from app import app
from models import db, StudentProfile, Subject, Department

with app.app_context():
    students = StudentProfile.query.all()
    fixed_count = 0

    for student in students:
        college_id = student.college_id
        # Get all active subjects in this college
        college_subjects = Subject.query.join(Department).filter(
            Department.college_id == college_id,
            Subject.status == 'active'
        ).all()

        enrolled = 0
        for subject in college_subjects:
            if subject not in student.enrolled_subjects:
                student.enrolled_subjects.append(subject)
                enrolled += 1

        if enrolled > 0:
            fixed_count += 1
            print(f"Enrolled {student.user.full_name()} in {enrolled} subjects")

    db.session.commit()
    print(f"\nDone! Fixed {fixed_count} student(s).")