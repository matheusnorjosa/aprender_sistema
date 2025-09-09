"""
Django Management Command - Test Educational Algorithms
======================================================

Command to test and demonstrate educational algorithms implemented in the system.

Usage:
    python manage.py test_algorithms --test-recommendations
    python manage.py test_algorithms --test-scheduling
    python manage.py test_algorithms --test-performance

Author: Claude Code
Date: Janeiro 2025
"""

import json
from django.core.management.base import BaseCommand, CommandError
from core.services.educational_algorithms import (
    get_formador_recommendations,
    optimize_event_schedule,
    predict_student_performance,
    train_performance_model
)


class Command(BaseCommand):
    help = "Test educational algorithms and machine learning models"

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-recommendations',
            action='store_true',
            help='Test formador recommendation system'
        )
        
        parser.add_argument(
            '--test-scheduling',
            action='store_true',
            help='Test schedule optimization algorithm'
        )
        
        parser.add_argument(
            '--test-performance',
            action='store_true',
            help='Test student performance prediction'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all algorithm tests'
        )

    def handle(self, *args, **options):
        self.stdout.write("Testing Educational Algorithms...")
        
        if options['all']:
            self.test_recommendations()
            self.test_scheduling()
            self.test_performance()
        elif options['test_recommendations']:
            self.test_recommendations()
        elif options['test_scheduling']:
            self.test_scheduling()
        elif options['test_performance']:
            self.test_performance()
        else:
            raise CommandError("Please specify a test to run. Use --help for options.")
    
    def test_recommendations(self):
        """Test the formador recommendation system"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("TESTING FORMADOR RECOMMENDATION SYSTEM")
        self.stdout.write("="*60)
        
        # Sample student profile
        student_profile = {
            'learning_style_visual': 0.8,
            'learning_style_auditory': 0.3,
            'learning_style_kinesthetic': 0.6,
            'difficulty_preference': 4,  # 1-5 scale
            'interaction_preference': 3,
            'technical_level': 4,
        }
        
        # Sample available formadores
        available_formadores = [
            {
                'id': '1',
                'name': 'João Silva',
                'visual_teaching': 5,
                'auditory_teaching': 2,
                'practical_teaching': 3,
                'difficulty_level': 4,
                'interaction_style': 3,
                'technical_expertise': 5,
                'skills': ['python', 'machine_learning', 'data_science']
            },
            {
                'id': '2',
                'name': 'Maria Santos',
                'visual_teaching': 3,
                'auditory_teaching': 5,
                'practical_teaching': 4,
                'difficulty_level': 3,
                'interaction_style': 4,
                'technical_expertise': 3,
                'skills': ['web_development', 'javascript', 'react']
            },
            {
                'id': '3',
                'name': 'Pedro Costa',
                'visual_teaching': 4,
                'auditory_teaching': 3,
                'practical_teaching': 5,
                'difficulty_level': 4,
                'interaction_style': 3,
                'technical_expertise': 4,
                'skills': ['python', 'django', 'backend_development']
            }
        ]
        
        try:
            recommendations = get_formador_recommendations(student_profile, available_formadores)
            
            self.stdout.write(f"Student Profile: {json.dumps(student_profile, indent=2)}")
            self.stdout.write(f"\nAvailable Formadores: {len(available_formadores)}")
            self.stdout.write(f"\nRecommendations:")
            
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(f"\n{i}. {rec['name']}")
                self.stdout.write(f"   Similarity Score: {rec['similarity_score']:.3f}")
                self.stdout.write(f"   Recommendation Strength: {rec['recommendation_strength']}")
                self.stdout.write(f"   Skills: {', '.join(rec.get('skills', []))}")
            
            self.stdout.write(
                self.style.SUCCESS("\n[OK] Recommendation system test completed!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[ERROR] Recommendation test failed: {e}")
            )
    
    def test_scheduling(self):
        """Test the schedule optimization algorithm"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("TESTING SCHEDULE OPTIMIZATION ALGORITHM")
        self.stdout.write("="*60)
        
        # Sample events to schedule
        events = [
            {
                'id': 'event1',
                'title': 'Python Básico',
                'priority': 5,
                'duration_hours': 4,
                'required_formadores': 1,
                'required_skills': ['python', 'teaching'],
                'municipio': 'Fortaleza'
            },
            {
                'id': 'event2',
                'title': 'Django Avançado',
                'priority': 4,
                'duration_hours': 6,
                'required_formadores': 1,
                'required_skills': ['django', 'python', 'web_development'],
                'municipio': 'Fortaleza'
            },
            {
                'id': 'event3',
                'title': 'Machine Learning',
                'priority': 3,
                'duration_hours': 8,
                'required_formadores': 1,
                'required_skills': ['machine_learning', 'python'],
                'municipio': 'Caucaia'
            }
        ]
        
        # Sample formadores
        formadores = [
            {
                'id': 'form1',
                'name': 'João Silva',
                'skills': ['python', 'teaching', 'machine_learning'],
                'availability': 'full'
            },
            {
                'id': 'form2',
                'name': 'Maria Santos',
                'skills': ['django', 'python', 'web_development'],
                'availability': 'full'
            }
        ]
        
        # Sample time slots
        time_slots = [
            {
                'id': 'slot1',
                'start_time': '2025-01-15T08:00:00Z',
                'end_time': '2025-01-15T12:00:00Z',
                'duration_hours': 4,
                'municipio': 'Fortaleza'
            },
            {
                'id': 'slot2',
                'start_time': '2025-01-15T14:00:00Z',
                'end_time': '2025-01-15T20:00:00Z',
                'duration_hours': 6,
                'municipio': 'Fortaleza'
            },
            {
                'id': 'slot3',
                'start_time': '2025-01-16T08:00:00Z',
                'end_time': '2025-01-16T16:00:00Z',
                'duration_hours': 8,
                'municipio': 'Caucaia'
            }
        ]
        
        try:
            result = optimize_event_schedule(events, formadores, time_slots)
            
            if 'error' in result:
                self.stdout.write(
                    self.style.ERROR(f"[ERROR] {result['error']}")
                )
                return
            
            self.stdout.write(f"Events to Schedule: {len(events)}")
            self.stdout.write(f"Available Formadores: {len(formadores)}")
            self.stdout.write(f"Available Time Slots: {len(time_slots)}")
            
            self.stdout.write(f"\nOptimization Results:")
            self.stdout.write(f"Fitness Score: {result['fitness_score']:.2f}")
            self.stdout.write(f"Conflicts Detected: {len(result['conflicts'])}")
            
            self.stdout.write(f"\nOptimized Schedule:")
            for i, event in enumerate(result['schedule'], 1):
                self.stdout.write(f"\n{i}. {event['event_title']}")
                self.stdout.write(f"   Time: {event['start_time']} - {event['end_time']}")
                self.stdout.write(f"   Formadores: {', '.join(f['name'] for f in event['formadores'])}")
                self.stdout.write(f"   Score: {event['score']:.2f}")
            
            if result['conflicts']:
                self.stdout.write(f"\nConflicts:")
                for conflict in result['conflicts']:
                    self.stdout.write(f"- {conflict['type']}: {conflict}")
            
            self.stdout.write(
                self.style.SUCCESS("\n[OK] Schedule optimization test completed!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[ERROR] Schedule optimization test failed: {e}")
            )
    
    def test_performance(self):
        """Test the student performance prediction system"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("TESTING STUDENT PERFORMANCE PREDICTION")
        self.stdout.write("="*60)
        
        # Sample student data
        student_data = {
            'attendance_rate': 0.85,
            'assignment_completion_rate': 0.75,
            'average_quiz_score': 0.72,
            'participation_score': 0.6,
            'time_spent_studying': 0.8,
            'previous_course_average': 0.78,
            'age': 25,
            'has_prerequisites': True,
            'motivation_score': 0.7,
            'difficulty_rating': 0.6
        }
        
        try:
            prediction = predict_student_performance(student_data)
            
            if 'error' in prediction:
                self.stdout.write(
                    self.style.ERROR(f"[ERROR] {prediction['error']}")
                )
                return
            
            self.stdout.write(f"Student Data: {json.dumps(student_data, indent=2)}")
            
            self.stdout.write(f"\nPerformance Prediction Results:")
            self.stdout.write(f"Predicted Performance: {prediction['predicted_performance']:.3f}")
            self.stdout.write(f"Performance Category: {prediction['performance_category']}")
            self.stdout.write(f"Confidence Level: {prediction['confidence']:.1%}")
            
            if prediction.get('recommendations'):
                self.stdout.write(f"\nRecommendations:")
                for i, rec in enumerate(prediction['recommendations'], 1):
                    self.stdout.write(f"  {i}. {rec}")
            
            if prediction.get('risk_factors'):
                self.stdout.write(f"\nRisk Factors:")
                for i, risk in enumerate(prediction['risk_factors'], 1):
                    self.stdout.write(f"  {i}. {risk}")
            
            # Test with different student profiles
            self.stdout.write(f"\n--- Testing Additional Student Profiles ---")
            
            # High-performing student
            high_performer = {
                'attendance_rate': 0.95,
                'assignment_completion_rate': 0.9,
                'average_quiz_score': 0.88,
                'participation_score': 0.85,
                'time_spent_studying': 0.9,
                'previous_course_average': 0.87,
                'age': 22,
                'has_prerequisites': True,
                'motivation_score': 0.9,
                'difficulty_rating': 0.4
            }
            
            high_prediction = predict_student_performance(high_performer)
            self.stdout.write(f"\nHigh Performer Prediction: {high_prediction['performance_category']} "
                            f"({high_prediction['predicted_performance']:.3f})")
            
            # At-risk student
            at_risk_student = {
                'attendance_rate': 0.6,
                'assignment_completion_rate': 0.4,
                'average_quiz_score': 0.45,
                'participation_score': 0.3,
                'time_spent_studying': 0.4,
                'previous_course_average': 0.5,
                'age': 30,
                'has_prerequisites': False,
                'motivation_score': 0.4,
                'difficulty_rating': 0.8
            }
            
            risk_prediction = predict_student_performance(at_risk_student)
            self.stdout.write(f"At-Risk Student Prediction: {risk_prediction['performance_category']} "
                            f"({risk_prediction['predicted_performance']:.3f})")
            self.stdout.write(f"Risk Factors: {', '.join(risk_prediction.get('risk_factors', []))}")
            
            self.stdout.write(
                self.style.SUCCESS("\n[OK] Performance prediction test completed!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[ERROR] Performance prediction test failed: {e}")
            )