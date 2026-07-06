#!/usr/bin/env python3
"""
AI Study Planner - Database Cleaner
Safely wipes all data while preserving tables, schema, and constraints.
Run: python clean_database.py
"""
import sqlite3
import os

DB_PATH = 'study_planner.db'

def clean_database():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Disable FK checks temporarily
    cursor.execute("PRAGMA foreign_keys = OFF;")

    tables = [
        'activity_log',
        'announcement',
        'message',
        'notification',
        'study_plan',
        'submission',
        'question',
        'test_attempt',
        'test',
        'material',
        'assignment',
        'student_subjects',
        'teacher_departments',
        'subject',
        'department',
        'student_profile',
        'teacher_profile',
        'college',
        'user',
    ]

    print("=" * 50)
    print("  AI Study Planner - Database Cleaner")
    print("=" * 50)
    print()

    total_deleted = 0
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            cursor.execute(f"DELETE FROM {table}")
            print(f"  [OK] {table:25s} - {count:4d} rows deleted")
            total_deleted += count
        except sqlite3.Error as e:
            print(f"  [SKIP] {table:25s} - {e}")

    # Reset SQLite auto-increment sequences (may not exist, so wrap in try)
    try:
        cursor.execute("DELETE FROM sqlite_sequence;")
        print(f"  [OK] sqlite_sequence         - reset")
    except sqlite3.OperationalError:
        print(f"  [OK] sqlite_sequence         - not present (skipped)")

    # Re-enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    conn.commit()
    conn.close()

    print()
    print("=" * 50)
    print(f"  TOTAL: {total_deleted} rows wiped")
    print("  TABLES: Preserved (schema intact)")
    print("  CONSTRAINTS: Preserved")
    print("  AUTO-INCREMENT: Reset")
    print("=" * 50)
    print()
    print("  Database is clean and sales-ready!")
    print("  Default admin will be recreated on next startup.")

if __name__ == '__main__':
    confirm = input("This will DELETE ALL DATA. Type 'yes' to proceed: ")
    if confirm.lower().strip() == 'yes':
        clean_database()
    else:
        print("Cancelled.")