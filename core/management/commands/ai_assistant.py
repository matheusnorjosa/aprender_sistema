"""
Django Management Command - AI Assistant
========================================

Command to interact with Claude Code SDK for AI-powered development assistance.

Usage:
    python manage.py ai_assistant --generate-model "Student performance tracker"
    python manage.py ai_assistant --generate-view "Solicitacao" --view-type "API"
    python manage.py ai_assistant --generate-tests "Authentication system"
    python manage.py ai_assistant --analyze-code path/to/file.py
    python manage.py ai_assistant --generate-docs core/models.py

Author: Claude Code
Date: Janeiro 2025
"""

import asyncio
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from core.services.claude_code_integration import (
    ai_generate_model,
    ai_generate_view,
    ai_generate_tests,
    ai_analyze_code,
    ai_generate_docs,
    claude_code_service
)


class Command(BaseCommand):
    help = "AI-powered development assistant using Claude Code SDK"

    def add_arguments(self, parser):
        parser.add_argument(
            '--generate-model',
            type=str,
            help='Generate Django model from description'
        )
        
        parser.add_argument(
            '--app-name',
            type=str,
            default='core',
            help='Django app name for generated model'
        )
        
        parser.add_argument(
            '--generate-view',
            type=str,
            help='Generate Django views for given model name'
        )
        
        parser.add_argument(
            '--view-type',
            type=str,
            default='CRUD',
            choices=['CRUD', 'API', 'ListView', 'DetailView', 'FormView'],
            help='Type of views to generate'
        )
        
        parser.add_argument(
            '--generate-tests',
            type=str,
            help='Generate tests for component description'
        )
        
        parser.add_argument(
            '--test-type',
            type=str,
            default='unit',
            choices=['unit', 'integration', 'functional'],
            help='Type of tests to generate'
        )
        
        parser.add_argument(
            '--analyze-code',
            type=str,
            help='Analyze code quality of given file path'
        )
        
        parser.add_argument(
            '--generate-docs',
            type=str,
            help='Generate documentation for given file path'
        )
        
        parser.add_argument(
            '--doc-type',
            type=str,
            default='api',
            choices=['api', 'user', 'technical'],
            help='Type of documentation to generate'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (optional, prints to console if not specified)'
        )
        
        parser.add_argument(
            '--test-sdk',
            action='store_true',
            help='Test if Claude Code SDK is working'
        )

    def handle(self, *args, **options):
        if not claude_code_service.enabled:
            raise CommandError(
                "Claude Code SDK not available. Install with: pip install claude-code-sdk"
            )
        
        if options['test_sdk']:
            self.test_sdk()
            return
        
        # Run async operations
        asyncio.run(self.handle_async(options))
    
    def test_sdk(self):
        """Test if Claude Code SDK is properly configured"""
        self.stdout.write("Testing Claude Code SDK...")
        
        if claude_code_service.enabled:
            self.stdout.write(
                self.style.SUCCESS("[OK] Claude Code SDK is available and ready!")
            )
            self.stdout.write(
                "Available commands:\n"
                "  --generate-model 'Description of model'\n"
                "  --generate-view 'ModelName' --view-type CRUD\n"
                "  --generate-tests 'Component description'\n"
                "  --analyze-code path/to/file.py\n"
                "  --generate-docs path/to/file.py"
            )
        else:
            self.stdout.write(
                self.style.ERROR("[ERROR] Claude Code SDK not available")
            )
    
    async def handle_async(self, options):
        """Handle async operations"""
        result = None
        
        if options['generate_model']:
            self.stdout.write("Generating Django model...")
            result = await ai_generate_model(
                options['generate_model'],
                options['app_name']
            )
            
        elif options['generate_view']:
            self.stdout.write("Generating Django views...")
            result = await ai_generate_view(
                options['generate_view'],
                options['view_type']
            )
            
        elif options['generate_tests']:
            self.stdout.write("Generating test cases...")
            result = await ai_generate_tests(
                options['generate_tests'],
                options['test_type']
            )
            
        elif options['analyze_code']:
            file_path = Path(options['analyze_code'])
            if not file_path.exists():
                raise CommandError(f"File not found: {file_path}")
            
            self.stdout.write(f"Analyzing code: {file_path}")
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code_content = f.read()
            except Exception as e:
                raise CommandError(f"Error reading file: {e}")
            
            analysis = await ai_analyze_code(code_content, "django")
            if analysis:
                result = json.dumps(analysis, indent=2)
            
        elif options['generate_docs']:
            file_path = Path(options['generate_docs'])
            if not file_path.exists():
                raise CommandError(f"File not found: {file_path}")
            
            self.stdout.write(f"Generating documentation for: {file_path}")
            result = await ai_generate_docs(
                str(file_path),
                options['doc_type']
            )
        
        else:
            raise CommandError(
                "Please specify an action. Use --help to see available options."
            )
        
        # Handle output
        if result:
            if options['output']:
                output_path = Path(options['output'])
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(result)
                    self.stdout.write(
                        self.style.SUCCESS(f"[OK] Output saved to: {output_path}")
                    )
                except Exception as e:
                    raise CommandError(f"Error saving output: {e}")
            else:
                self.stdout.write("\n" + "="*60)
                self.stdout.write("GENERATED RESULT:")
                self.stdout.write("="*60)
                self.stdout.write(result)
                self.stdout.write("="*60)
        else:
            self.stdout.write(
                self.style.WARNING("[WARNING] No result generated. Check logs for errors.")
            )