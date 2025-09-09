"""
Advanced System Prompts Service for Aprender Sistema
=====================================================

Comprehensive prompt engineering system for AI interactions,
providing specialized prompts for educational management and automation.

Author: Claude Code
Date: Janeiro 2025
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from django.conf import settings
from django.template import Template, Context

try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None
    OpenAI = None

try:
    import anthropic
    from anthropic import Anthropic
except ImportError:
    anthropic = None
    Anthropic = None

from core.models import (
    Formador, Municipio, Projeto, TipoEvento,
    Solicitacao, SolicitacaoStatus
)

logger = logging.getLogger(__name__)


class SystemPromptEngine:
    """
    Advanced system prompt engineering for AI interactions
    """
    
    def __init__(self):
        self.prompts_registry = {}
        self._load_builtin_prompts()
        
        # Initialize AI clients if available
        self.openai_client = None
        self.anthropic_client = None
        self._setup_ai_clients()
    
    def _setup_ai_clients(self):
        """Setup AI service clients"""
        # OpenAI
        if OpenAI and hasattr(settings, 'OPENAI_API_KEY'):
            try:
                self.openai_client = OpenAI(
                    api_key=getattr(settings, 'OPENAI_API_KEY', None)
                )
            except Exception as e:
                logger.warning(f"OpenAI client setup failed: {e}")
        
        # Anthropic
        if Anthropic and hasattr(settings, 'ANTHROPIC_API_KEY'):
            try:
                self.anthropic_client = Anthropic(
                    api_key=getattr(settings, 'ANTHROPIC_API_KEY', None)
                )
            except Exception as e:
                logger.warning(f"Anthropic client setup failed: {e}")
    
    def _load_builtin_prompts(self):
        """Load built-in system prompts"""
        
        # Educational Analysis Prompts
        self.register_prompt(
            "analyze_student_performance",
            """
            You are an educational data analyst specializing in student performance evaluation.
            
            Your task is to analyze student performance data and provide actionable insights.
            
            Guidelines:
            - Focus on learning outcomes and engagement metrics
            - Identify patterns and trends in performance
            - Suggest evidence-based interventions
            - Consider diverse learning styles and needs
            - Provide specific, measurable recommendations
            
            Input Data: {{data}}
            
            Analysis Context:
            - Course: {{course_name}}
            - Time Period: {{time_period}}
            - Student Count: {{student_count}}
            
            Please provide:
            1. Performance Summary
            2. Key Insights
            3. Risk Factors
            4. Recommendations
            5. Action Items
            """,
            category="education",
            description="Analyze student performance data with educational insights"
        )
        
        # Schedule Optimization Prompts
        self.register_prompt(
            "optimize_class_schedule",
            """
            You are an expert educational scheduler with deep knowledge of:
            - Pedagogical best practices
            - Resource optimization
            - Conflict resolution
            - Accessibility requirements
            
            Your goal is to create optimal class schedules that maximize learning outcomes.
            
            Constraints:
            {{constraints}}
            
            Available Resources:
            - Formadores: {{formadores}}
            - Time Slots: {{time_slots}}  
            - Locations: {{locations}}
            
            Requirements:
            - No scheduling conflicts
            - Balanced workload distribution
            - Consider travel time between locations
            - Prioritize high-impact sessions
            - Maintain educational quality
            
            Please provide:
            1. Optimized schedule
            2. Conflict resolution strategies
            3. Resource utilization analysis
            4. Quality assurance measures
            """,
            category="scheduling",
            description="Optimize educational schedules with AI assistance"
        )
        
        # Content Generation Prompts
        self.register_prompt(
            "generate_course_content",
            """
            You are an instructional designer creating educational content for professional development.
            
            Subject: {{subject}}
            Target Audience: {{audience}}
            Duration: {{duration}}
            Learning Objectives: {{objectives}}
            
            Content Requirements:
            - Engaging and interactive
            - Practical applications
            - Assessment strategies
            - Diverse learning modalities
            - Accessibility compliance
            
            Please create:
            1. Course outline
            2. Learning activities
            3. Assessment rubrics
            4. Resource recommendations
            5. Implementation timeline
            
            Format: Structured educational content suitable for professional trainers.
            """,
            category="content",
            description="Generate structured educational content and curricula"
        )
        
        # Report Generation Prompts
        self.register_prompt(
            "generate_executive_report",
            """
            You are a senior educational consultant preparing executive reports for leadership.
            
            Your expertise includes:
            - Strategic planning in education
            - Performance metrics analysis
            - Resource allocation optimization
            - Risk management
            - Stakeholder communication
            
            Data Summary: {{data_summary}}
            Key Metrics: {{metrics}}
            Time Period: {{period}}
            
            Report Requirements:
            - Executive summary (max 300 words)
            - Key findings with data visualization suggestions
            - Strategic recommendations
            - Resource implications
            - Risk assessment
            - Next steps timeline
            
            Audience: Executive leadership, non-technical stakeholders
            Tone: Professional, data-driven, actionable
            """,
            category="reporting",
            description="Generate executive-level educational reports"
        )
        
        # Quality Assurance Prompts
        self.register_prompt(
            "review_educational_quality",
            """
            You are an educational quality assurance specialist conducting comprehensive reviews.
            
            Review Scope: {{scope}}
            Evaluation Criteria: {{criteria}}
            Stakeholder Feedback: {{feedback}}
            
            Quality Dimensions:
            - Learning effectiveness
            - Content accuracy and relevance
            - Delivery methodology
            - Student engagement
            - Resource utilization
            - Accessibility compliance
            
            Assessment Framework:
            1. Standards alignment
            2. Best practices adherence
            3. Outcome measurement
            4. Continuous improvement opportunities
            
            Please provide:
            1. Quality rating (1-10 scale)
            2. Strengths identification
            3. Improvement areas
            4. Action plan recommendations
            5. Success metrics
            """,
            category="quality",
            description="Conduct comprehensive educational quality reviews"
        )
        
        # Communication Prompts
        self.register_prompt(
            "draft_stakeholder_communication",
            """
            You are a professional communications specialist in educational settings.
            
            Communication Purpose: {{purpose}}
            Audience: {{audience}}
            Key Message: {{message}}
            Context: {{context}}
            
            Communication Guidelines:
            - Clear and concise language
            - Appropriate tone for audience
            - Action-oriented when applicable
            - Culturally sensitive
            - Professional formatting
            
            Please create:
            1. Primary message
            2. Supporting details
            3. Call to action (if applicable)
            4. Follow-up requirements
            5. Distribution recommendations
            
            Format: {{format}} (email, memo, presentation, etc.)
            """,
            category="communication", 
            description="Draft professional stakeholder communications"
        )
    
    def register_prompt(
        self, 
        name: str, 
        template: str, 
        category: str = "general",
        description: str = "",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Register a new system prompt
        
        Args:
            name: Unique prompt identifier
            template: Prompt template with Django template syntax
            category: Prompt category for organization
            description: Human-readable description
            metadata: Additional prompt metadata
            
        Returns:
            True if registration successful
        """
        try:
            self.prompts_registry[name] = {
                'template': template,
                'category': category,
                'description': description,
                'metadata': metadata or {},
                'created_at': datetime.now().isoformat()
            }
            logger.info(f"Registered prompt: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register prompt {name}: {e}")
            return False
    
    def get_prompt(
        self, 
        name: str, 
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Get rendered prompt by name
        
        Args:
            name: Prompt identifier
            context: Template context variables
            
        Returns:
            Rendered prompt string or None if not found
        """
        if name not in self.prompts_registry:
            logger.warning(f"Prompt not found: {name}")
            return None
        
        try:
            template_str = self.prompts_registry[name]['template']
            template = Template(template_str)
            context_obj = Context(context or {})
            rendered = template.render(context_obj)
            
            return rendered.strip()
        except Exception as e:
            logger.error(f"Failed to render prompt {name}: {e}")
            return None
    
    def list_prompts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available prompts, optionally filtered by category
        
        Args:
            category: Filter by category
            
        Returns:
            List of prompt metadata
        """
        prompts = []
        for name, config in self.prompts_registry.items():
            if category is None or config['category'] == category:
                prompts.append({
                    'name': name,
                    'category': config['category'],
                    'description': config['description'],
                    'created_at': config['created_at']
                })
        
        return sorted(prompts, key=lambda x: x['category'])
    
    def get_categories(self) -> List[str]:
        """Get all available prompt categories"""
        categories = set()
        for config in self.prompts_registry.values():
            categories.add(config['category'])
        return sorted(list(categories))
    
    async def execute_prompt_openai(
        self,
        prompt_name: str,
        context: Dict[str, Any] = None,
        model: str = "gpt-4",
        **kwargs
    ) -> Optional[str]:
        """
        Execute prompt using OpenAI API
        
        Args:
            prompt_name: Registered prompt name
            context: Template context
            model: OpenAI model to use
            **kwargs: Additional OpenAI parameters
            
        Returns:
            AI response or None if error
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available")
            return None
        
        prompt = self.get_prompt(prompt_name, context)
        if not prompt:
            return None
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": context.get("user_input", "Please analyze the provided data.")}
                ],
                **kwargs
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    async def execute_prompt_anthropic(
        self,
        prompt_name: str,
        context: Dict[str, Any] = None,
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1000,
        **kwargs
    ) -> Optional[str]:
        """
        Execute prompt using Anthropic Claude API
        
        Args:
            prompt_name: Registered prompt name
            context: Template context
            model: Claude model to use
            max_tokens: Maximum response tokens
            **kwargs: Additional Anthropic parameters
            
        Returns:
            AI response or None if error
        """
        if not self.anthropic_client:
            logger.warning("Anthropic client not available")
            return None
        
        prompt = self.get_prompt(prompt_name, context)
        if not prompt:
            return None
        
        try:
            response = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": f"{prompt}\n\nUser Input: {context.get('user_input', 'Please analyze the provided data.')}"}
                ],
                **kwargs
            )
            
            return response.content[0].text if response.content else None
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return None


class EducationalPromptGenerator:
    """
    Specialized prompt generator for educational contexts
    """
    
    def __init__(self):
        self.prompt_engine = SystemPromptEngine()
    
    def generate_formador_analysis_prompt(self, formador: Formador) -> str:
        """Generate analysis prompt for a specific formador"""
        context = {
            'formador_name': formador.usuario.get_full_name(),
            'formador_id': str(formador.id),
            'active_status': formador.ativo,
            'creation_date': formador.data_criacao.isoformat(),
        }
        
        return self.prompt_engine.get_prompt('analyze_formador_performance', context)
    
    def generate_schedule_optimization_prompt(
        self, 
        solicitacoes: List[Solicitacao],
        formadores: List[Formador],
        constraints: Dict[str, Any] = None
    ) -> str:
        """Generate schedule optimization prompt"""
        context = {
            'solicitacoes_count': len(solicitacoes),
            'formadores_count': len(formadores),
            'constraints': json.dumps(constraints or {}),
            'formadores': [f.usuario.get_full_name() for f in formadores],
            'time_period': 'Current planning period'
        }
        
        return self.prompt_engine.get_prompt('optimize_class_schedule', context)
    
    def generate_quality_review_prompt(
        self,
        projeto: Projeto,
        feedback_data: Dict[str, Any] = None
    ) -> str:
        """Generate quality review prompt for a project"""
        context = {
            'scope': f"Project: {projeto.nome}",
            'criteria': "Educational standards and best practices",
            'feedback': json.dumps(feedback_data or {}),
            'project_description': projeto.descricao or "No description available"
        }
        
        return self.prompt_engine.get_prompt('review_educational_quality', context)
    
    def generate_report_prompt(
        self,
        report_type: str,
        data_summary: Dict[str, Any],
        metrics: Dict[str, Any] = None,
        period: str = "Monthly"
    ) -> str:
        """Generate executive report prompt"""
        context = {
            'data_summary': json.dumps(data_summary),
            'metrics': json.dumps(metrics or {}),
            'period': period,
            'report_type': report_type
        }
        
        return self.prompt_engine.get_prompt('generate_executive_report', context)


class PromptTemplateLibrary:
    """
    Library of reusable prompt templates for common educational scenarios
    """
    
    TEMPLATES = {
        "lesson_plan": """
        Create a detailed lesson plan for:
        
        Subject: {{subject}}
        Duration: {{duration}}
        Audience: {{audience}}
        Learning Objectives: {{objectives}}
        
        Include:
        - Opening activities
        - Main content delivery
        - Interactive elements
        - Assessment methods
        - Closing activities
        - Required materials
        """,
        
        "assessment_rubric": """
        Design an assessment rubric for:
        
        Activity: {{activity}}
        Criteria: {{criteria}}
        Performance Levels: {{levels}}
        
        Provide clear descriptions for each performance level and specific indicators.
        """,
        
        "feedback_analysis": """
        Analyze participant feedback:
        
        Feedback Data: {{feedback_data}}
        Course: {{course_name}}
        Instructor: {{instructor}}
        
        Identify:
        - Key strengths
        - Areas for improvement
        - Actionable recommendations
        - Satisfaction trends
        """,
        
        "resource_recommendation": """
        Recommend educational resources for:
        
        Topic: {{topic}}
        Audience Level: {{level}}
        Format Preferences: {{formats}}
        Budget: {{budget}}
        
        Suggest diverse, high-quality resources with justification.
        """
    }
    
    @classmethod
    def get_template(cls, name: str) -> Optional[str]:
        """Get template by name"""
        return cls.TEMPLATES.get(name)
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """List available template names"""
        return list(cls.TEMPLATES.keys())
    
    @classmethod
    def render_template(cls, name: str, context: Dict[str, Any]) -> Optional[str]:
        """Render template with context"""
        template_str = cls.get_template(name)
        if not template_str:
            return None
        
        try:
            template = Template(template_str)
            context_obj = Context(context)
            return template.render(context_obj).strip()
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return None


# Global instances
system_prompts = SystemPromptEngine()
educational_prompts = EducationalPromptGenerator()
template_library = PromptTemplateLibrary()


# Convenience functions
def get_educational_prompt(name: str, context: Dict[str, Any] = None) -> Optional[str]:
    """Get educational prompt by name"""
    return system_prompts.get_prompt(name, context)


def list_available_prompts(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available system prompts"""
    return system_prompts.list_prompts(category)


def register_custom_prompt(
    name: str, 
    template: str, 
    category: str = "custom",
    description: str = ""
) -> bool:
    """Register a custom prompt"""
    return system_prompts.register_prompt(name, template, category, description)


async def execute_ai_prompt(
    prompt_name: str,
    context: Dict[str, Any] = None,
    provider: str = "anthropic",
    **kwargs
) -> Optional[str]:
    """Execute AI prompt with specified provider"""
    if provider.lower() == "openai":
        return await system_prompts.execute_prompt_openai(prompt_name, context, **kwargs)
    elif provider.lower() == "anthropic":
        return await system_prompts.execute_prompt_anthropic(prompt_name, context, **kwargs)
    else:
        logger.warning(f"Unknown AI provider: {provider}")
        return None