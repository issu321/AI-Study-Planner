#!/usr/bin/env python3
"""
AI Study Planner - Quick Start Script
Run: python run.py
"""
from app import app, setup_database

if __name__ == '__main__':
    setup_database()
    print("\n" + "=" * 60)
    print("  AI STUDY PLANNER - Multi-Tenant Education System")
    print("  Developer: Mohammed Usman | GitHub: issu321")
    print("=" * 60)
    print("=" * 60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
