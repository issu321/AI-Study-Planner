"""
AI Study Planner - AI Engine
Premium Multi-Tenant Education Management System
Developer: Mohammed Usman | GitHub: issu321

This module provides intelligent study planning capabilities including:
- Personalized study schedule generation
- Subject priority analysis
- Performance-based recommendations
- Smart deadline management
- Study pattern analysis
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict
import random


class AIStudyPlanner:
    """AI-powered study planning engine."""
    
    def __init__(self, user_id, daily_hours=6, planning_days=30):
        self.user_id = user_id
        self.daily_hours = daily_hours
        self.planning_days = planning_days
        self.subjects_data = []
        self.assignments_data = []
        self.tests_data = []
        self.historical_performance = {}
    
    def load_user_data(self, student_profile):
        """Load all relevant user data for planning."""
        from models import Subject, Assignment, Test, TestAttempt, StudyPlan
        
        # Get enrolled subjects
        subjects = student_profile.enrolled_subjects
        self.subjects_data = []
        for subject in subjects:
            self.subjects_data.append({
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'credits': subject.credits,
                'teacher': subject.teacher.user.full_name() if subject.teacher else 'Unassigned',
                'material_count': subject.materials.count(),
                'assignment_count': subject.assignments.count(),
                'test_count': subject.tests.count()
            })
        
        # Get pending assignments
        now = datetime.utcnow()
        enrolled_ids = [s.id for s in subjects]
        if enrolled_ids:
            assignments = Assignment.query.filter(
                Assignment.subject_id.in_(enrolled_ids),
                Assignment.status == 'active'
            ).all()
            self.assignments_data = []
            for a in assignments:
                days_left = (a.due_date - now).days if a.due_date else 30
                self.assignments_data.append({
                    'id': a.id,
                    'title': a.title,
                    'subject_id': a.subject_id,
                    'subject_name': a.subject.name if a.subject else 'Unknown',
                    'due_date': a.due_date.isoformat() if a.due_date else None,
                    'days_left': days_left,
                    'total_marks': a.total_marks,
                    'priority': 'urgent' if days_left < 3 else 'high' if days_left < 7 else 'normal'
                })
        
        # Get upcoming tests
        if enrolled_ids:
            tests = Test.query.filter(
                Test.subject_id.in_(enrolled_ids),
                Test.status.in_(['published', 'active'])
            ).all()
            self.tests_data = []
            for t in tests:
                days_left = (t.start_time - now).days if t.start_time else 30
                self.tests_data.append({
                    'id': t.id,
                    'title': t.title,
                    'subject_id': t.subject_id,
                    'subject_name': t.subject.name if t.subject else 'Unknown',
                    'start_time': t.start_time.isoformat() if t.start_time else None,
                    'days_left': days_left,
                    'duration': t.duration_minutes,
                    'total_marks': t.total_marks,
                    'priority': 'urgent' if days_left < 3 else 'high' if days_left < 7 else 'normal'
                })
        
        # Get historical performance
        attempts = TestAttempt.query.filter_by(student_id=student_profile.id).all()
        if attempts:
            subject_scores = defaultdict(list)
            for attempt in attempts:
                test = attempt.test
                if test and test.subject_id:
                    subject_scores[test.subject_id].append(attempt.percentage)
            
            for subj_id, scores in subject_scores.items():
                self.historical_performance[subj_id] = sum(scores) / len(scores)
    
    def calculate_subject_priority(self):
        """Calculate priority score for each subject based on multiple factors."""
        priorities = []
        
        for subject in self.subjects_data:
            score = 50  # Base priority
            
            # Factor 1: Number of upcoming assignments (higher = more priority)
            subject_assignments = [a for a in self.assignments_data if a['subject_id'] == subject['id']]
            urgent_assignments = [a for a in subject_assignments if a['priority'] == 'urgent']
            high_assignments = [a for a in subject_assignments if a['priority'] == 'high']
            score += len(urgent_assignments) * 15
            score += len(high_assignments) * 8
            
            # Factor 2: Upcoming tests
            subject_tests = [t for t in self.tests_data if t['subject_id'] == subject['id']]
            urgent_tests = [t for t in subject_tests if t['priority'] == 'urgent']
            high_tests = [t for t in subject_tests if t['priority'] == 'high']
            score += len(urgent_tests) * 15
            score += len(high_tests) * 8
            
            # Factor 3: Historical performance (lower performance = higher priority)
            hist_score = self.historical_performance.get(subject['id'], 50)
            if hist_score < 50:
                score += 20
            elif hist_score < 70:
                score += 10
            
            # Factor 4: Credits (higher credits = more study time needed)
            score += subject['credits'] * 3
            
            # Factor 5: Material availability (more materials = more to study)
            score += min(subject['material_count'] * 2, 10)
            
            priorities.append({
                'subject_id': subject['id'],
                'subject_name': subject['name'],
                'priority_score': min(score, 100),
                'urgent_assignments': len(urgent_assignments),
                'upcoming_tests': len(subject_tests),
                'historical_score': hist_score,
                'recommended_hours': 0  # Will be calculated
            })
        
        # Sort by priority score descending
        priorities.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Calculate recommended hours per subject
        total_score = sum(p['priority_score'] for p in priorities)
        if total_score > 0:
            for p in priorities:
                p['recommended_hours'] = round(
                    (p['priority_score'] / total_score) * self.daily_hours, 1
                )
        
        return priorities
    
    def generate_daily_schedule(self, date, priorities):
        """Generate a daily study schedule."""
        schedule = {
            'date': date.isoformat(),
            'day_name': date.strftime('%A'),
            'total_hours': self.daily_hours,
            'sessions': [],
            'assignments_due': [],
            'tests_upcoming': []
        }
        
        # Check assignments due on this date
        date_str = date.strftime('%Y-%m-%d')
        for a in self.assignments_data:
            if a['due_date'] and a['due_date'].startswith(date_str):
                schedule['assignments_due'].append(a)
        
        # Check tests on this date
        for t in self.tests_data:
            if t['start_time'] and t['start_time'].startswith(date_str):
                schedule['tests_upcoming'].append(t)
        
        # Create study sessions based on priorities
        current_hour = 9  # Start at 9 AM
        for priority in priorities:
            hours = priority['recommended_hours']
            if hours < 0.5:
                continue
            
            end_hour = current_hour + hours
            if end_hour > 21:  # Don't study past 9 PM
                break
            
            # Get relevant assignments for this subject
            subject_assignments = [
                a for a in self.assignments_data 
                if a['subject_id'] == priority['subject_id'] and a['days_left'] > 0
            ]
            
            # Get relevant tests
            subject_tests = [
                t for t in self.tests_data
                if t['subject_id'] == priority['subject_id'] and t['days_left'] > 0
            ]
            
            session = {
                'subject_id': priority['subject_id'],
                'subject_name': priority['subject_name'],
                'start_time': f"{int(current_hour):02d}:00",
                'end_time': f"{int(end_hour):02d}:00",
                'duration_hours': round(hours, 1),
                'focus_areas': [],
                'tasks': []
            }
            
            # Add focus areas based on urgency
            if subject_assignments:
                most_urgent = min(subject_assignments, key=lambda x: x['days_left'])
                session['focus_areas'].append(f"Assignment: {most_urgent['title']} ({most_urgent['days_left']} days left)")
                session['tasks'].append({
                    'type': 'assignment',
                    'id': most_urgent['id'],
                    'title': most_urgent['title'],
                    'priority': most_urgent['priority']
                })
            
            if subject_tests:
                most_urgent_test = min(subject_tests, key=lambda x: x['days_left'])
                session['focus_areas'].append(f"Test prep: {most_urgent_test['title']} ({most_urgent_test['days_left']} days left)")
                session['tasks'].append({
                    'type': 'test_prep',
                    'id': most_urgent_test['id'],
                    'title': most_urgent_test['title'],
                    'priority': most_urgent_test['priority']
                })
            
            if not session['focus_areas']:
                session['focus_areas'].append(f"Review {priority['subject_name']} materials and notes")
                session['tasks'].append({
                    'type': 'review',
                    'title': f"Review {priority['subject_name']}",
                    'priority': 'normal'
                })
            
            schedule['sessions'].append(session)
            current_hour = end_hour
        
        return schedule
    
    def generate_weekly_schedule(self):
        """Generate a full week study schedule."""
        priorities = self.calculate_subject_priority()
        today = datetime.utcnow().date()
        
        weekly_schedule = []
        for day_offset in range(7):
            date = today + timedelta(days=day_offset)
            daily = self.generate_daily_schedule(date, priorities)
            weekly_schedule.append(daily)
        
        return weekly_schedule
    
    def generate_study_plan(self, title, description=None, target_date=None):
        """Generate a comprehensive AI study plan."""
        priorities = self.calculate_subject_priority()
        weekly_schedule = self.generate_weekly_schedule()
        
        # Calculate planning horizon
        if target_date:
            end_date = target_date
        else:
            end_date = datetime.utcnow() + timedelta(days=self.planning_days)
        
        plan_data = {
            'title': title,
            'description': description or 'AI-generated personalized study plan',
            'generated_at': datetime.utcnow().isoformat(),
            'target_date': end_date.isoformat() if target_date else None,
            'daily_hours': self.daily_hours,
            'planning_days': self.planning_days,
            'subject_priorities': priorities,
            'weekly_schedule': weekly_schedule,
            'recommendations': self._generate_recommendations(priorities),
            'deadlines_summary': {
                'urgent_assignments': len([a for a in self.assignments_data if a['priority'] == 'urgent']),
                'high_priority_assignments': len([a for a in self.assignments_data if a['priority'] == 'high']),
                'upcoming_tests_urgent': len([t for t in self.tests_data if t['priority'] == 'urgent']),
                'upcoming_tests_high': len([t for t in self.tests_data if t['priority'] == 'high'])
            },
            'performance_insights': self._generate_performance_insights()
        }
        
        return plan_data
    
    def _generate_recommendations(self, priorities):
        """Generate personalized study recommendations."""
        recommendations = []
        
        # Check for subjects needing attention
        low_performing = [p for p in priorities if p.get('historical_score', 50) < 50]
        if low_performing:
            subj_names = ', '.join([p['subject_name'] for p in low_performing[:3]])
            recommendations.append({
                'type': 'warning',
                'category': 'performance',
                'message': f"Focus extra attention on: {subj_names}. Your scores indicate these need improvement."
            })
        
        # Check for urgent deadlines
        urgent = [a for a in self.assignments_data if a['priority'] == 'urgent']
        if urgent:
            recommendations.append({
                'type': 'urgent',
                'category': 'deadline',
                'message': f"You have {len(urgent)} assignment(s) due within 3 days. Prioritize these immediately."
            })
        
        # Balance recommendation
        if len(priorities) > 4:
            recommendations.append({
                'type': 'info',
                'category': 'balance',
                'message': f"You're enrolled in {len(priorities)} subjects. Ensure balanced study time across all subjects."
            })
        
        # Study technique recommendations based on performance
        avg_score = sum(p.get('historical_score', 50) for p in priorities) / len(priorities) if priorities else 50
        if avg_score < 60:
            recommendations.append({
                'type': 'tip',
                'category': 'technique',
                'message': "Consider using active recall and spaced repetition techniques to improve retention."
            })
        
        # High performer encouragement
        if avg_score > 80:
            recommendations.append({
                'type': 'success',
                'category': 'motivation',
                'message': "Excellent performance! Maintain your momentum by helping peers and exploring advanced topics."
            })
        
        return recommendations
    
    def _generate_performance_insights(self):
        """Generate performance insights based on historical data."""
        insights = {
            'overall_average': 0,
            'strongest_subject': None,
            'weakest_subject': None,
            'trend': 'stable',
            'study_streak_days': 0
        }
        
        if self.historical_performance:
            scores = list(self.historical_performance.values())
            insights['overall_average'] = round(sum(scores) / len(scores), 1)
            
            # Find strongest and weakest
            if scores:
                max_subj = max(self.historical_performance.items(), key=lambda x: x[1])
                min_subj = min(self.historical_performance.items(), key=lambda x: x[1])
                
                # Find subject names
                for subj in self.subjects_data:
                    if subj['id'] == max_subj[0]:
                        insights['strongest_subject'] = {
                            'name': subj['name'],
                            'score': round(max_subj[1], 1)
                        }
                    if subj['id'] == min_subj[0]:
                        insights['weakest_subject'] = {
                            'name': subj['name'],
                            'score': round(min_subj[1], 1)
                        }
        
        return insights
    
    @staticmethod
    def analyze_study_patterns(user_id):
        """Analyze user's study patterns and provide insights."""
        from models import TestAttempt, StudyPlan
        
        # Get all test attempts
        attempts = TestAttempt.query.filter_by(student_id=user_id).all()
        
        if not attempts:
            return {
                'message': 'Not enough data to analyze patterns. Complete more tests to get insights.',
                'patterns': []
            }
        
        # Analyze time of day performance
        morning_scores = []
        afternoon_scores = []
        evening_scores = []
        
        for attempt in attempts:
            hour = attempt.started_at.hour if attempt.started_at else 12
            if 5 <= hour < 12:
                morning_scores.append(attempt.percentage)
            elif 12 <= hour < 17:
                afternoon_scores.append(attempt.percentage)
            else:
                evening_scores.append(attempt.percentage)
        
        best_time = 'morning'
        best_avg = 0
        
        patterns = []
        
        if morning_scores:
            avg = sum(morning_scores) / len(morning_scores)
            patterns.append({'time': 'Morning (5AM-12PM)', 'average_score': round(avg, 1), 'attempts': len(morning_scores)})
            if avg > best_avg:
                best_avg = avg
                best_time = 'morning'
        
        if afternoon_scores:
            avg = sum(afternoon_scores) / len(afternoon_scores)
            patterns.append({'time': 'Afternoon (12PM-5PM)', 'average_score': round(avg, 1), 'attempts': len(afternoon_scores)})
            if avg > best_avg:
                best_avg = avg
                best_time = 'afternoon'
        
        if evening_scores:
            avg = sum(evening_scores) / len(evening_scores)
            patterns.append({'time': 'Evening (5PM+)', 'average_score': round(avg, 1), 'attempts': len(evening_scores)})
            if avg > best_avg:
                best_avg = avg
                best_time = 'evening'
        
        # Consistency analysis
        if len(attempts) >= 5:
            recent_scores = [a.percentage for a in sorted(attempts, key=lambda x: x.started_at, reverse=True)[:5]]
            score_variance = max(recent_scores) - min(recent_scores)
            consistency = 'consistent' if score_variance < 15 else 'variable' if score_variance < 30 else 'inconsistent'
        else:
            consistency = 'insufficient_data'
        
        return {
            'best_study_time': best_time,
            'patterns': patterns,
            'consistency': consistency,
            'total_attempts': len(attempts),
            'average_score': round(sum(a.percentage for a in attempts) / len(attempts), 1) if attempts else 0,
            'recommendation': f"Based on your data, you perform best during {best_time} hours. Schedule important subjects during this time."
        }


def generate_smart_schedule(student_profile, daily_hours=6):
    """Generate a smart study schedule for a student."""
    planner = AIStudyPlanner(student_profile.user_id, daily_hours)
    planner.load_user_data(student_profile)
    return planner.generate_study_plan(
        title=f"Study Plan - {datetime.utcnow().strftime('%B %Y')}",
        target_date=datetime.utcnow() + timedelta(days=30)
    )


def get_subject_suggestions(student_profile, limit=3):
    """Get subject improvement suggestions based on performance."""
    planner = AIStudyPlanner(student_profile.user_id)
    planner.load_user_data(student_profile)
    priorities = planner.calculate_subject_priority()
    
    # Return subjects that need most attention
    suggestions = []
    for p in priorities[:limit]:
        if p['priority_score'] > 60 or p.get('historical_score', 50) < 60:
            suggestions.append({
                'subject_name': p['subject_name'],
                'priority_score': p['priority_score'],
                'recommended_hours': p['recommended_hours'],
                'reason': 'Low performance' if p.get('historical_score', 50) < 60 else 'High workload'
            })
    
    return suggestions
