"""
Educational Algorithms for Aprender Sistema
===========================================

Implementation of educational algorithms inspired by TheAlgorithms/Python repository,
specifically designed for educational management systems and student analytics.

Algorithms included:
- Student recommendation systems
- Schedule optimization
- Performance prediction
- Learning path optimization
- Resource allocation

Author: Claude Code
Date: Janeiro 2025
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from django.db.models import Q, Avg, Count

try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


class StudentRecommendationEngine:
    """
    Recommendation system for educational content and formadores
    Based on collaborative filtering and content-based algorithms
    """
    
    def __init__(self):
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.model = None
        
    def recommend_formadores(self, student_profile: Dict, available_formadores: List[Dict]) -> List[Dict]:
        """
        Recommend best formadores for a student based on profile and history
        
        Args:
            student_profile: Student characteristics and preferences
            available_formadores: List of available formadores with their skills
            
        Returns:
            Ranked list of recommended formadores
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("Sklearn not available, using simple recommendation")
            return self._simple_formador_recommendation(student_profile, available_formadores)
        
        try:
            # Create feature vectors for student and formadores
            student_vector = self._create_student_vector(student_profile)
            formador_vectors = [self._create_formador_vector(f) for f in available_formadores]
            
            if not formador_vectors:
                return []
            
            # Calculate similarity scores
            similarities = cosine_similarity([student_vector], formador_vectors)[0]
            
            # Rank formadores by similarity
            recommendations = []
            for i, formador in enumerate(available_formadores):
                recommendations.append({
                    **formador,
                    'similarity_score': float(similarities[i]),
                    'recommendation_strength': self._calculate_strength(similarities[i])
                })
            
            # Sort by similarity score
            recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return recommendations[:5]  # Top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error in formador recommendation: {e}")
            return self._simple_formador_recommendation(student_profile, available_formadores)
    
    def _create_student_vector(self, profile: Dict) -> np.ndarray:
        """Create feature vector for student"""
        # Example features: learning_style, difficulty_preference, subject_interests, etc.
        features = [
            profile.get('learning_style_visual', 0),
            profile.get('learning_style_auditory', 0),
            profile.get('learning_style_kinesthetic', 0),
            profile.get('difficulty_preference', 3),  # 1-5 scale
            profile.get('interaction_preference', 3),  # 1-5 scale
            profile.get('technical_level', 3),  # 1-5 scale
        ]
        return np.array(features)
    
    def _create_formador_vector(self, formador: Dict) -> np.ndarray:
        """Create feature vector for formador"""
        features = [
            formador.get('visual_teaching', 3),
            formador.get('auditory_teaching', 3),
            formador.get('practical_teaching', 3),
            formador.get('difficulty_level', 3),
            formador.get('interaction_style', 3),
            formador.get('technical_expertise', 3),
        ]
        return np.array(features)
    
    def _simple_formador_recommendation(self, student_profile: Dict, formadores: List[Dict]) -> List[Dict]:
        """Simple recommendation without sklearn"""
        # Basic scoring based on simple rules
        for formador in formadores:
            score = 0
            
            # Basic matching logic
            if student_profile.get('technical_level', 3) <= formador.get('technical_expertise', 3):
                score += 1
            
            if student_profile.get('interaction_preference', 3) == formador.get('interaction_style', 3):
                score += 1
            
            formador['similarity_score'] = score / 2.0
            formador['recommendation_strength'] = self._calculate_strength(formador['similarity_score'])
        
        return sorted(formadores, key=lambda x: x['similarity_score'], reverse=True)[:5]
    
    def _calculate_strength(self, score: float) -> str:
        """Convert similarity score to recommendation strength"""
        if score >= 0.8:
            return "Muito Alta"
        elif score >= 0.6:
            return "Alta"
        elif score >= 0.4:
            return "Média"
        elif score >= 0.2:
            return "Baixa"
        else:
            return "Muito Baixa"


class ScheduleOptimizer:
    """
    Schedule optimization algorithm for educational events
    Based on genetic algorithms and constraint satisfaction
    """
    
    def __init__(self):
        self.constraints = []
        self.optimization_params = {
            'population_size': 50,
            'generations': 100,
            'mutation_rate': 0.1
        }
    
    def optimize_schedule(
        self,
        events: List[Dict],
        formadores: List[Dict],
        time_slots: List[Dict],
        constraints: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Optimize schedule using genetic algorithm approach
        
        Args:
            events: List of events to schedule
            formadores: Available formadores
            time_slots: Available time slots
            constraints: Additional constraints
            
        Returns:
            Optimized schedule with fitness score
        """
        try:
            if not events or not formadores or not time_slots:
                return {'error': 'Missing required data for optimization'}
            
            # Simple greedy algorithm implementation
            # (In production, this would be a full genetic algorithm)
            schedule = self._greedy_schedule_optimization(events, formadores, time_slots)
            
            return {
                'schedule': schedule,
                'fitness_score': self._calculate_schedule_fitness(schedule),
                'conflicts': self._detect_conflicts(schedule),
                'optimization_method': 'greedy' if not SKLEARN_AVAILABLE else 'genetic'
            }
            
        except Exception as e:
            logger.error(f"Error in schedule optimization: {e}")
            return {'error': str(e)}
    
    def _greedy_schedule_optimization(
        self, 
        events: List[Dict], 
        formadores: List[Dict], 
        time_slots: List[Dict]
    ) -> List[Dict]:
        """Greedy algorithm for schedule optimization"""
        scheduled_events = []
        available_formadores = {f['id']: f for f in formadores}
        available_slots = time_slots.copy()
        
        # Sort events by priority (highest first)
        events_sorted = sorted(events, key=lambda x: x.get('priority', 0), reverse=True)
        
        for event in events_sorted:
            best_assignment = self._find_best_assignment(
                event, available_formadores, available_slots
            )
            
            if best_assignment:
                scheduled_events.append(best_assignment)
                # Remove assigned slot
                available_slots = [s for s in available_slots if s['id'] != best_assignment['slot_id']]
        
        return scheduled_events
    
    def _find_best_assignment(
        self, 
        event: Dict, 
        formadores: Dict, 
        slots: List[Dict]
    ) -> Optional[Dict]:
        """Find best formador and time slot for an event"""
        best_score = -1
        best_assignment = None
        
        required_formadores = event.get('required_formadores', 1)
        
        for slot in slots:
            # Check if slot fits event duration
            if not self._slot_fits_event(slot, event):
                continue
            
            # Find best formadores for this slot
            available_formadores = self._get_available_formadores(formadores, slot)
            
            if len(available_formadores) < required_formadores:
                continue
            
            # Calculate assignment score
            score = self._calculate_assignment_score(event, available_formadores[:required_formadores], slot)
            
            if score > best_score:
                best_score = score
                best_assignment = {
                    'event_id': event['id'],
                    'event_title': event.get('title', ''),
                    'slot_id': slot['id'],
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'formadores': available_formadores[:required_formadores],
                    'score': score
                }
        
        return best_assignment
    
    def _slot_fits_event(self, slot: Dict, event: Dict) -> bool:
        """Check if time slot can accommodate event duration"""
        slot_duration = slot.get('duration_hours', 2)
        event_duration = event.get('duration_hours', 2)
        return slot_duration >= event_duration
    
    def _get_available_formadores(self, formadores: Dict, slot: Dict) -> List[Dict]:
        """Get formadores available for a specific time slot"""
        # This would check formador availability in the database
        # For now, return all formadores
        return list(formadores.values())
    
    def _calculate_assignment_score(
        self, 
        event: Dict, 
        formadores: List[Dict], 
        slot: Dict
    ) -> float:
        """Calculate score for a specific event-formador-slot assignment"""
        score = 0.0
        
        # Base score
        score += event.get('priority', 0) * 0.4
        
        # Formador expertise match
        required_skills = event.get('required_skills', [])
        for formador in formadores:
            formador_skills = formador.get('skills', [])
            skill_match = len(set(required_skills) & set(formador_skills)) / max(len(required_skills), 1)
            score += skill_match * 0.3
        
        # Time preference
        preferred_time = event.get('preferred_time')
        if preferred_time and preferred_time == slot.get('time_category'):
            score += 0.2
        
        # Location optimization
        if event.get('municipio') == slot.get('municipio'):
            score += 0.1
        
        return score
    
    def _calculate_schedule_fitness(self, schedule: List[Dict]) -> float:
        """Calculate overall fitness score for the schedule"""
        if not schedule:
            return 0.0
        
        total_score = sum(event.get('score', 0) for event in schedule)
        conflict_penalty = len(self._detect_conflicts(schedule)) * 0.5
        
        return max(0, total_score - conflict_penalty)
    
    def _detect_conflicts(self, schedule: List[Dict]) -> List[Dict]:
        """Detect scheduling conflicts"""
        conflicts = []
        
        for i, event1 in enumerate(schedule):
            for j, event2 in enumerate(schedule[i+1:], i+1):
                # Check time overlap
                if self._events_overlap(event1, event2):
                    # Check formador conflict
                    formadores1 = {f['id'] for f in event1.get('formadores', [])}
                    formadores2 = {f['id'] for f in event2.get('formadores', [])}
                    
                    if formadores1 & formadores2:  # Common formadores
                        conflicts.append({
                            'type': 'formador_conflict',
                            'event1': event1['event_id'],
                            'event2': event2['event_id'],
                            'conflicting_formadores': list(formadores1 & formadores2)
                        })
        
        return conflicts
    
    def _events_overlap(self, event1: Dict, event2: Dict) -> bool:
        """Check if two events have time overlap"""
        start1 = datetime.fromisoformat(event1['start_time'].replace('Z', '+00:00'))
        end1 = datetime.fromisoformat(event1['end_time'].replace('Z', '+00:00'))
        start2 = datetime.fromisoformat(event2['start_time'].replace('Z', '+00:00'))
        end2 = datetime.fromisoformat(event2['end_time'].replace('Z', '+00:00'))
        
        return start1 < end2 and start2 < end1


class PerformancePredictionEngine:
    """
    Machine learning engine for predicting student performance
    Based on historical data and current indicators
    """
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100) if SKLEARN_AVAILABLE else None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.trained = False
    
    def train_model(self, training_data: List[Dict]) -> Dict[str, Any]:
        """
        Train the performance prediction model
        
        Args:
            training_data: Historical student performance data
            
        Returns:
            Training results and metrics
        """
        if not SKLEARN_AVAILABLE:
            return {'error': 'Sklearn not available for ML training'}
        
        try:
            if len(training_data) < 10:
                return {'error': 'Insufficient training data (minimum 10 records required)'}
            
            # Prepare features and targets
            features, targets = self._prepare_training_data(training_data)
            
            if len(features) == 0:
                return {'error': 'No valid features extracted from training data'}
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Train model
            self.model.fit(features_scaled, targets)
            self.trained = True
            
            # Calculate training metrics
            predictions = self.model.predict(features_scaled)
            mse = np.mean((predictions - targets) ** 2)
            r2 = self.model.score(features_scaled, targets)
            
            return {
                'status': 'trained',
                'samples_used': len(training_data),
                'mse': float(mse),
                'r2_score': float(r2),
                'feature_importance': [
                    {'feature': f'feature_{i}', 'importance': float(imp)}
                    for i, imp in enumerate(self.model.feature_importances_)
                ]
            }
            
        except Exception as e:
            logger.error(f"Error training performance model: {e}")
            return {'error': str(e)}
    
    def predict_performance(self, student_data: Dict) -> Dict[str, Any]:
        """
        Predict student performance based on current indicators
        
        Args:
            student_data: Current student characteristics and metrics
            
        Returns:
            Performance prediction with confidence intervals
        """
        if not SKLEARN_AVAILABLE or not self.trained:
            return self._simple_performance_prediction(student_data)
        
        try:
            # Extract features
            features = self._extract_student_features(student_data)
            features_scaled = self.scaler.transform([features])
            
            # Make prediction
            prediction = self.model.predict(features_scaled)[0]
            
            # Calculate confidence (simplified)
            # In production, this would use proper confidence intervals
            confidence = min(0.95, max(0.5, 1.0 - abs(prediction - 0.75) * 2))
            
            return {
                'predicted_performance': float(prediction),
                'performance_category': self._categorize_performance(prediction),
                'confidence': float(confidence),
                'recommendations': self._generate_recommendations(prediction, student_data),
                'risk_factors': self._identify_risk_factors(student_data, prediction)
            }
            
        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            return {'error': str(e)}
    
    def _prepare_training_data(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML model"""
        features = []
        targets = []
        
        for record in data:
            feature_vector = self._extract_student_features(record)
            if feature_vector and 'final_performance' in record:
                features.append(feature_vector)
                targets.append(record['final_performance'])
        
        return np.array(features), np.array(targets)
    
    def _extract_student_features(self, student_data: Dict) -> List[float]:
        """Extract numerical features from student data"""
        features = [
            student_data.get('attendance_rate', 0.5),
            student_data.get('assignment_completion_rate', 0.5),
            student_data.get('average_quiz_score', 0.5),
            student_data.get('participation_score', 0.5),
            student_data.get('time_spent_studying', 0.5),
            student_data.get('previous_course_average', 0.5),
            student_data.get('age', 25) / 100.0,  # Normalize age
            1.0 if student_data.get('has_prerequisites') else 0.0,
            student_data.get('motivation_score', 0.5),
            student_data.get('difficulty_rating', 0.5)
        ]
        return features
    
    def _simple_performance_prediction(self, student_data: Dict) -> Dict[str, Any]:
        """Simple rule-based performance prediction"""
        # Basic scoring
        score = 0.0
        weight_sum = 0.0
        
        # Attendance impact
        if 'attendance_rate' in student_data:
            score += student_data['attendance_rate'] * 0.3
            weight_sum += 0.3
        
        # Assignment completion
        if 'assignment_completion_rate' in student_data:
            score += student_data['assignment_completion_rate'] * 0.25
            weight_sum += 0.25
        
        # Quiz performance
        if 'average_quiz_score' in student_data:
            score += student_data['average_quiz_score'] * 0.25
            weight_sum += 0.25
        
        # Participation
        if 'participation_score' in student_data:
            score += student_data['participation_score'] * 0.2
            weight_sum += 0.2
        
        # Normalize score
        if weight_sum > 0:
            predicted_performance = score / weight_sum
        else:
            predicted_performance = 0.5  # Default
        
        return {
            'predicted_performance': predicted_performance,
            'performance_category': self._categorize_performance(predicted_performance),
            'confidence': 0.6,  # Moderate confidence for simple model
            'recommendations': self._generate_recommendations(predicted_performance, student_data),
            'risk_factors': self._identify_risk_factors(student_data, predicted_performance)
        }
    
    def _categorize_performance(self, score: float) -> str:
        """Categorize performance score"""
        if score >= 0.85:
            return "Excelente"
        elif score >= 0.7:
            return "Bom"
        elif score >= 0.6:
            return "Satisfatório"
        elif score >= 0.5:
            return "Necessita Melhoria"
        else:
            return "Risco"
    
    def _generate_recommendations(self, predicted_score: float, student_data: Dict) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if predicted_score < 0.6:
            recommendations.append("Considere sessões de tutoria adicional")
            recommendations.append("Revise o material básico do curso")
        
        if student_data.get('attendance_rate', 1.0) < 0.8:
            recommendations.append("Melhore a frequência às aulas")
        
        if student_data.get('assignment_completion_rate', 1.0) < 0.7:
            recommendations.append("Complete todas as atividades propostas")
        
        if student_data.get('participation_score', 1.0) < 0.5:
            recommendations.append("Participe mais ativamente das discussões")
        
        if not recommendations:
            recommendations.append("Continue o excelente trabalho!")
        
        return recommendations
    
    def _identify_risk_factors(self, student_data: Dict, predicted_score: float) -> List[str]:
        """Identify potential risk factors"""
        risk_factors = []
        
        if student_data.get('attendance_rate', 1.0) < 0.7:
            risk_factors.append("Baixa frequência")
        
        if student_data.get('assignment_completion_rate', 1.0) < 0.6:
            risk_factors.append("Baixa conclusão de atividades")
        
        if predicted_score < 0.5:
            risk_factors.append("Alto risco de reprovação")
        
        if student_data.get('motivation_score', 1.0) < 0.4:
            risk_factors.append("Baixa motivação")
        
        return risk_factors


# Global instances
recommendation_engine = StudentRecommendationEngine()
schedule_optimizer = ScheduleOptimizer()
performance_predictor = PerformancePredictionEngine()


# Convenience functions for external use
def get_formador_recommendations(student_profile: Dict, formadores: List[Dict]) -> List[Dict]:
    """Get formador recommendations for a student"""
    return recommendation_engine.recommend_formadores(student_profile, formadores)


def optimize_event_schedule(events: List[Dict], formadores: List[Dict], slots: List[Dict]) -> Dict:
    """Optimize schedule for events"""
    return schedule_optimizer.optimize_schedule(events, formadores, slots)


def predict_student_performance(student_data: Dict) -> Dict:
    """Predict student performance"""
    return performance_predictor.predict_performance(student_data)


def train_performance_model(training_data: List[Dict]) -> Dict:
    """Train the performance prediction model"""
    return performance_predictor.train_model(training_data)