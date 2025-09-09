"""
Django Management Command - TIER 3 Tools
=========================================

Command to test and manage TIER 3 specialized tools:
- System Prompts for AI interactions
- Google APIs integration
- Advanced automation features

Usage:
    python manage.py tier3_tools --test-prompts
    python manage.py tier3_tools --test-google-apis
    python manage.py tier3_tools --generate-prompt "analyze student performance"
    python manage.py tier3_tools --list-prompts --category education

Author: Claude Code
Date: Janeiro 2025
"""

import json
from django.core.management.base import BaseCommand, CommandError
from core.services.system_prompts import (
    system_prompts,
    educational_prompts,
    template_library,
    get_educational_prompt,
    list_available_prompts,
    register_custom_prompt
)
from core.services.google_apis_integration import (
    google_apis_manager,
    calendar_service,
    drive_service,
    gmail_service
)
from core.models import Formador, Projeto, Solicitacao


class Command(BaseCommand):
    help = "Test and manage TIER 3 specialized tools"

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-prompts',
            action='store_true',
            help='Test system prompts functionality'
        )
        
        parser.add_argument(
            '--test-google-apis',
            action='store_true',
            help='Test Google APIs integration'
        )
        
        parser.add_argument(
            '--list-prompts',
            action='store_true',
            help='List available system prompts'
        )
        
        parser.add_argument(
            '--category',
            type=str,
            help='Filter prompts by category'
        )
        
        parser.add_argument(
            '--generate-prompt',
            type=str,
            help='Generate specific prompt by name'
        )
        
        parser.add_argument(
            '--prompt-context',
            type=str,
            help='JSON context for prompt generation'
        )
        
        parser.add_argument(
            '--test-templates',
            action='store_true',
            help='Test prompt templates'
        )
        
        parser.add_argument(
            '--register-prompt',
            type=str,
            help='Register new custom prompt (provide template)'
        )
        
        parser.add_argument(
            '--prompt-name',
            type=str,
            help='Name for custom prompt registration'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all TIER 3 tests'
        )

    def handle(self, *args, **options):
        self.stdout.write("Testing TIER 3 Specialized Tools...")
        
        if options['all']:
            self.test_prompts()
            self.test_google_apis()
            self.test_templates()
        elif options['test_prompts']:
            self.test_prompts()
        elif options['test_google_apis']:
            self.test_google_apis()
        elif options['list_prompts']:
            self.list_prompts(options.get('category'))
        elif options['generate_prompt']:
            self.generate_prompt(options['generate_prompt'], options.get('prompt_context'))
        elif options['test_templates']:
            self.test_templates()
        elif options['register_prompt'] and options['prompt_name']:
            self.register_prompt(options['prompt_name'], options['register_prompt'])
        else:
            raise CommandError("Please specify a test to run. Use --help for options.")
    
    def test_prompts(self):
        """Test system prompts functionality"""
        self.stdout.write("=" * 60)
        self.stdout.write("TESTING SYSTEM PROMPTS")
        self.stdout.write("=" * 60)
        
        try:
            # Test prompt registration and retrieval
            self.stdout.write("Testing prompt registration...")
            
            test_prompt = """
            You are a test assistant. 
            Context: {{context}}
            Task: {{task}}
            Please provide a helpful response.
            """
            
            success = register_custom_prompt(
                "test_prompt",
                test_prompt,
                "testing",
                "Test prompt for validation"
            )
            
            if success:
                self.stdout.write("[OK] Custom prompt registered successfully")
            else:
                self.stdout.write("[ERROR] Failed to register custom prompt")
            
            # Test prompt retrieval
            self.stdout.write("\nTesting prompt retrieval...")
            retrieved_prompt = get_educational_prompt(
                "test_prompt",
                {"context": "Testing environment", "task": "Validate functionality"}
            )
            
            if retrieved_prompt:
                self.stdout.write("[OK] Prompt retrieved and rendered successfully")
                self.stdout.write(f"     Preview: {retrieved_prompt[:100]}...")
            else:
                self.stdout.write("[ERROR] Failed to retrieve prompt")
            
            # Test built-in prompts
            self.stdout.write("\nTesting built-in educational prompts...")
            
            # Test student performance analysis prompt
            perf_context = {
                'data': {'grades': [85, 90, 78, 92], 'attendance': 0.95},
                'course_name': 'Django Development',
                'time_period': 'January 2025',
                'student_count': 25
            }
            
            perf_prompt = get_educational_prompt("analyze_student_performance", perf_context)
            if perf_prompt:
                self.stdout.write("[OK] Student performance prompt generated")
            else:
                self.stdout.write("[ERROR] Failed to generate student performance prompt")
            
            # Test schedule optimization prompt
            schedule_context = {
                'constraints': {'max_hours_per_day': 8, 'min_break_time': 30},
                'formadores': ['João Silva', 'Maria Santos'],
                'time_slots': ['08:00-12:00', '14:00-18:00'],
                'locations': ['Fortaleza', 'Caucaia']
            }
            
            schedule_prompt = get_educational_prompt("optimize_class_schedule", schedule_context)
            if schedule_prompt:
                self.stdout.write("[OK] Schedule optimization prompt generated")
            else:
                self.stdout.write("[ERROR] Failed to generate schedule optimization prompt")
            
            # Test prompt categories
            self.stdout.write("\nTesting prompt categories...")
            categories = system_prompts.get_categories()
            self.stdout.write(f"[OK] Available categories: {', '.join(categories)}")
            
            # Test educational prompt generator
            self.stdout.write("\nTesting educational prompt generator...")
            
            # Get first formador for testing
            try:
                formador = Formador.objects.first()
                if formador:
                    formador_prompt = educational_prompts.generate_formador_analysis_prompt(formador)
                    if formador_prompt:
                        self.stdout.write("[OK] Formador analysis prompt generated")
                    else:
                        self.stdout.write("[WARNING] Formador prompt generation returned None")
                else:
                    self.stdout.write("[WARNING] No formador found for testing")
            except Exception as e:
                self.stdout.write(f"[ERROR] Formador prompt test failed: {e}")
            
            self.stdout.write("[OK] System prompts test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Prompts test failed: {e}")
    
    def test_google_apis(self):
        """Test Google APIs integration"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING GOOGLE APIS INTEGRATION")
        self.stdout.write("=" * 60)
        
        try:
            # Test APIs manager
            self.stdout.write("Testing Google APIs Manager...")
            
            if google_apis_manager.enabled:
                self.stdout.write("[OK] Google APIs manager is enabled")
                
                # Test credentials status
                if google_apis_manager.credentials:
                    self.stdout.write("[OK] Google credentials are loaded")
                    
                    # Test service initialization
                    calendar = google_apis_manager.get_service('calendar', 'v3')
                    drive = google_apis_manager.get_service('drive', 'v3')
                    gmail = google_apis_manager.get_service('gmail', 'v1')
                    
                    services_status = {
                        'calendar': "[OK]" if calendar else "[ERROR]",
                        'drive': "[OK]" if drive else "[ERROR]",
                        'gmail': "[OK]" if gmail else "[ERROR]"
                    }
                    
                    for service, status in services_status.items():
                        self.stdout.write(f"     {service.title()} service: {status}")
                        
                else:
                    self.stdout.write("[WARNING] Google credentials not available")
                    self.stdout.write("     Set up OAuth2 credentials for full functionality")
            else:
                self.stdout.write("[WARNING] Google APIs not available")
                self.stdout.write("     Install google-api-python-client for full functionality")
            
            # Test Calendar Service
            self.stdout.write("\nTesting Calendar Service...")
            
            if calendar_service.calendar_service:
                self.stdout.write("[OK] Calendar service initialized")
                
                # Test conflict checking (doesn't require auth for demonstration)
                from datetime import datetime, timedelta
                now = datetime.now()
                later = now + timedelta(hours=2)
                
                try:
                    # This will show the capability even if auth fails
                    conflicts = calendar_service.get_calendar_conflicts(now, later)
                    self.stdout.write(f"[OK] Conflict checking available (found {len(conflicts)} conflicts)")
                except Exception as e:
                    self.stdout.write(f"[INFO] Conflict checking needs authentication: {str(e)[:50]}...")
                
            else:
                self.stdout.write("[WARNING] Calendar service not available")
            
            # Test Drive Service
            self.stdout.write("\nTesting Drive Service...")
            
            if drive_service.drive_service:
                self.stdout.write("[OK] Drive service initialized")
                self.stdout.write("     Folder creation and permission management available")
            else:
                self.stdout.write("[WARNING] Drive service not available")
            
            # Test Gmail Service  
            self.stdout.write("\nTesting Gmail Service...")
            
            if gmail_service.gmail_service:
                self.stdout.write("[OK] Gmail service initialized")
                self.stdout.write("     Automated notifications available")
            else:
                self.stdout.write("[WARNING] Gmail service not available")
            
            # Test with actual solicitacao if available
            self.stdout.write("\nTesting event creation capability...")
            try:
                solicitacao = Solicitacao.objects.first()
                if solicitacao:
                    self.stdout.write(f"[OK] Found test solicitacao: {solicitacao.titulo_evento}")
                    
                    # Test event description building (doesn't require API call)
                    description = calendar_service._build_event_description(solicitacao)
                    if description:
                        self.stdout.write("[OK] Event description generation works")
                        self.stdout.write(f"     Preview: {description[:100]}...")
                    
                    # Test attendees list building
                    attendees = calendar_service._build_attendees_list(solicitacao)
                    self.stdout.write(f"[OK] Attendees list generation works ({len(attendees)} attendees)")
                    
                else:
                    self.stdout.write("[WARNING] No solicitacao found for testing")
                    
            except Exception as e:
                self.stdout.write(f"[ERROR] Event creation test failed: {e}")
            
            self.stdout.write("[OK] Google APIs integration test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Google APIs test failed: {e}")
    
    def test_templates(self):
        """Test prompt templates"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING PROMPT TEMPLATES")
        self.stdout.write("=" * 60)
        
        try:
            # List available templates
            self.stdout.write("Testing template library...")
            templates = template_library.list_templates()
            self.stdout.write(f"[OK] Available templates: {', '.join(templates)}")
            
            # Test template rendering
            self.stdout.write("\nTesting template rendering...")
            
            # Test lesson plan template
            lesson_context = {
                'subject': 'Python Programming',
                'duration': '4 hours',
                'audience': 'Beginner developers',
                'objectives': 'Learn basic Python syntax and concepts'
            }
            
            lesson_plan = template_library.render_template('lesson_plan', lesson_context)
            if lesson_plan:
                self.stdout.write("[OK] Lesson plan template rendered successfully")
                self.stdout.write(f"     Preview: {lesson_plan[:150]}...")
            else:
                self.stdout.write("[ERROR] Failed to render lesson plan template")
            
            # Test assessment rubric template
            rubric_context = {
                'activity': 'Python coding exercise',
                'criteria': 'Code quality, functionality, documentation',
                'levels': 'Excellent, Good, Satisfactory, Needs Improvement'
            }
            
            rubric = template_library.render_template('assessment_rubric', rubric_context)
            if rubric:
                self.stdout.write("[OK] Assessment rubric template rendered successfully")
            else:
                self.stdout.write("[ERROR] Failed to render assessment rubric template")
            
            # Test feedback analysis template
            feedback_context = {
                'feedback_data': 'Positive: 85%, Negative: 10%, Neutral: 5%',
                'course_name': 'Django Web Development',
                'instructor': 'João Silva'
            }
            
            feedback = template_library.render_template('feedback_analysis', feedback_context)
            if feedback:
                self.stdout.write("[OK] Feedback analysis template rendered successfully")
            else:
                self.stdout.write("[ERROR] Failed to render feedback analysis template")
            
            self.stdout.write("[OK] Template testing completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Template test failed: {e}")
    
    def list_prompts(self, category=None):
        """List available prompts"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("AVAILABLE SYSTEM PROMPTS")
        self.stdout.write("=" * 60)
        
        try:
            prompts = list_available_prompts(category)
            
            if category:
                self.stdout.write(f"Category: {category}")
                self.stdout.write("-" * 30)
            
            if prompts:
                for prompt in prompts:
                    self.stdout.write(f"Name: {prompt['name']}")
                    self.stdout.write(f"Category: {prompt['category']}")
                    self.stdout.write(f"Description: {prompt['description']}")
                    self.stdout.write(f"Created: {prompt['created_at']}")
                    self.stdout.write("-" * 40)
                
                self.stdout.write(f"\nTotal prompts: {len(prompts)}")
            else:
                filter_msg = f" in category '{category}'" if category else ""
                self.stdout.write(f"No prompts found{filter_msg}")
            
            # Show available categories
            categories = system_prompts.get_categories()
            self.stdout.write(f"\nAvailable categories: {', '.join(categories)}")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Failed to list prompts: {e}")
    
    def generate_prompt(self, prompt_name, context_json=None):
        """Generate specific prompt"""
        self.stdout.write(f"\nGenerating prompt: {prompt_name}")
        self.stdout.write("=" * 50)
        
        try:
            context = {}
            if context_json:
                try:
                    context = json.loads(context_json)
                except json.JSONDecodeError:
                    self.stdout.write("[WARNING] Invalid JSON context, using empty context")
            
            prompt = get_educational_prompt(prompt_name, context)
            
            if prompt:
                self.stdout.write("[OK] Prompt generated successfully:")
                self.stdout.write("-" * 50)
                self.stdout.write(prompt)
                self.stdout.write("-" * 50)
            else:
                self.stdout.write(f"[ERROR] Prompt '{prompt_name}' not found")
                
                # Suggest similar prompts
                available = [p['name'] for p in list_available_prompts()]
                self.stdout.write(f"Available prompts: {', '.join(available[:5])}...")
                
        except Exception as e:
            self.stdout.write(f"[ERROR] Failed to generate prompt: {e}")
    
    def register_prompt(self, name, template):
        """Register new custom prompt"""
        self.stdout.write(f"\nRegistering custom prompt: {name}")
        self.stdout.write("=" * 50)
        
        try:
            success = register_custom_prompt(
                name,
                template,
                "custom",
                f"Custom prompt registered via CLI: {name}"
            )
            
            if success:
                self.stdout.write("[OK] Custom prompt registered successfully")
                
                # Test the new prompt
                test_context = {'test': 'This is a test context'}
                rendered = get_educational_prompt(name, test_context)
                if rendered:
                    self.stdout.write("[OK] New prompt renders correctly")
                    self.stdout.write(f"Preview: {rendered[:200]}...")
                else:
                    self.stdout.write("[WARNING] New prompt failed to render")
            else:
                self.stdout.write("[ERROR] Failed to register custom prompt")
                
        except Exception as e:
            self.stdout.write(f"[ERROR] Prompt registration failed: {e}")