"""
Claude Code SDK Integration for Aprender Sistema
===============================================

This module integrates the official Claude Code SDK with our Django educational system,
providing AI-powered development assistance and automated code generation capabilities.

Author: Claude Code
Date: Janeiro 2025
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings

try:
    from claude_code_sdk import query, ClaudeCodeOptions
except ImportError:
    query = None
    ClaudeCodeOptions = None

logger = logging.getLogger(__name__)


class ClaudeCodeService:
    """
    Service class for integrating Claude Code SDK with Django
    
    Provides AI-powered assistance for:
    - Model generation
    - View automation
    - Test creation
    - Documentation generation
    - Code analysis and optimization
    """
    
    def __init__(self):
        self.enabled = query is not None and ClaudeCodeOptions is not None
        if not self.enabled:
            logger.warning("Claude Code SDK not available - install with: pip install claude-code-sdk")
    
    async def generate_django_model(self, description: str, app_name: str = "core") -> Optional[str]:
        """
        Generate Django model code based on description
        
        Args:
            description: Natural language description of the model
            app_name: Django app name for the model
            
        Returns:
            Generated model code or None if SDK not available
        """
        if not self.enabled:
            return None
            
        prompt = f"""
        Generate a Django model for the {app_name} app with the following requirements:
        
        {description}
        
        Requirements:
        - Use proper Django field types
        - Include appropriate Meta class options
        - Add __str__ method
        - Include proper imports
        - Follow Django best practices
        - Use UUID as primary key where appropriate
        - Include created_at and updated_at timestamps
        """
        
        options = ClaudeCodeOptions(
            system_prompt="You are a Django expert generating production-ready model code."
        )
        
        try:
            generated_code = ""
            async for message in query(prompt=prompt, options=options):
                generated_code += message
            
            logger.info(f"Generated Django model for: {description}")
            return generated_code.strip()
            
        except Exception as e:
            logger.error(f"Error generating Django model: {e}")
            return None
    
    async def generate_django_view(self, model_name: str, view_type: str = "CRUD") -> Optional[str]:
        """
        Generate Django views for a given model
        
        Args:
            model_name: Name of the Django model
            view_type: Type of views to generate (CRUD, API, etc.)
            
        Returns:
            Generated view code or None if SDK not available
        """
        if not self.enabled:
            return None
            
        prompt = f"""
        Generate Django {view_type} views for the {model_name} model.
        
        Requirements:
        - Use class-based views (CBV)
        - Include proper permissions and authentication
        - Add error handling
        - Include success messages
        - Use proper HTTP status codes
        - Follow RESTful principles
        - Include proper imports
        - Add docstrings
        """
        
        options = ClaudeCodeOptions(
            system_prompt="You are a Django expert creating secure, production-ready views."
        )
        
        try:
            generated_code = ""
            async for message in query(prompt=prompt, options=options):
                generated_code += message
            
            logger.info(f"Generated Django views for model: {model_name}")
            return generated_code.strip()
            
        except Exception as e:
            logger.error(f"Error generating Django views: {e}")
            return None
    
    async def generate_tests(self, component_description: str, test_type: str = "unit") -> Optional[str]:
        """
        Generate test cases for Django components
        
        Args:
            component_description: Description of the component to test
            test_type: Type of tests (unit, integration, functional)
            
        Returns:
            Generated test code or None if SDK not available
        """
        if not self.enabled:
            return None
            
        prompt = f"""
        Generate Django {test_type} tests for: {component_description}
        
        Requirements:
        - Use Django TestCase or appropriate test classes
        - Include setUp and tearDown methods
        - Test both success and error cases
        - Use factory_boy for test data if complex
        - Include proper assertions
        - Test edge cases
        - Follow Django testing best practices
        - Include docstrings
        """
        
        options = ClaudeCodeOptions(
            system_prompt="You are a Django testing expert creating comprehensive test suites."
        )
        
        try:
            generated_code = ""
            async for message in query(prompt=prompt, options=options):
                generated_code += message
            
            logger.info(f"Generated tests for: {component_description}")
            return generated_code.strip()
            
        except Exception as e:
            logger.error(f"Error generating tests: {e}")
            return None
    
    async def analyze_code_quality(self, code: str, code_type: str = "django") -> Optional[Dict[str, Any]]:
        """
        Analyze code quality and suggest improvements
        
        Args:
            code: Code to analyze
            code_type: Type of code (django, python, javascript)
            
        Returns:
            Analysis results with suggestions or None if SDK not available
        """
        if not self.enabled:
            return None
            
        prompt = f"""
        Analyze the following {code_type} code for:
        - Security vulnerabilities
        - Performance issues
        - Code style violations
        - Best practice violations
        - Potential bugs
        - Optimization opportunities
        
        Code to analyze:
        ```
        {code}
        ```
        
        Return analysis as JSON with:
        - issues: list of problems found
        - suggestions: list of improvements
        - score: overall quality score (1-10)
        - security_rating: security assessment
        """
        
        options = ClaudeCodeOptions(
            system_prompt="You are a senior code reviewer providing detailed analysis."
        )
        
        try:
            analysis_result = ""
            async for message in query(prompt=prompt, options=options):
                analysis_result += message
            
            logger.info("Completed code quality analysis")
            
            # Try to parse as JSON
            import json
            try:
                return json.loads(analysis_result.strip())
            except json.JSONDecodeError:
                return {"raw_analysis": analysis_result.strip()}
                
        except Exception as e:
            logger.error(f"Error analyzing code quality: {e}")
            return None
    
    async def generate_documentation(self, component_path: str, doc_type: str = "api") -> Optional[str]:
        """
        Generate documentation for Django components
        
        Args:
            component_path: Path to the component file
            doc_type: Type of documentation (api, user, technical)
            
        Returns:
            Generated documentation or None if SDK not available
        """
        if not self.enabled:
            return None
            
        try:
            # Read the component file
            with open(component_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        except FileNotFoundError:
            logger.error(f"Component file not found: {component_path}")
            return None
            
        prompt = f"""
        Generate {doc_type} documentation for the following Django component:
        
        File: {component_path}
        ```
        {code_content}
        ```
        
        Requirements:
        - Use Markdown format
        - Include clear descriptions
        - Add usage examples
        - Document all parameters and return values
        - Include error handling information
        - Add related components links
        - Follow documentation best practices
        """
        
        options = ClaudeCodeOptions(
            system_prompt="You are a technical writer creating comprehensive documentation."
        )
        
        try:
            documentation = ""
            async for message in query(prompt=prompt, options=options):
                documentation += message
            
            logger.info(f"Generated documentation for: {component_path}")
            return documentation.strip()
            
        except Exception as e:
            logger.error(f"Error generating documentation: {e}")
            return None


# Global service instance
claude_code_service = ClaudeCodeService()


# Convenience functions for use in Django management commands and views
async def ai_generate_model(description: str, app_name: str = "core") -> Optional[str]:
    """Convenience function to generate Django models"""
    return await claude_code_service.generate_django_model(description, app_name)


async def ai_generate_view(model_name: str, view_type: str = "CRUD") -> Optional[str]:
    """Convenience function to generate Django views"""
    return await claude_code_service.generate_django_view(model_name, view_type)


async def ai_generate_tests(description: str, test_type: str = "unit") -> Optional[str]:
    """Convenience function to generate test cases"""
    return await claude_code_service.generate_tests(description, test_type)


async def ai_analyze_code(code: str, code_type: str = "django") -> Optional[Dict[str, Any]]:
    """Convenience function to analyze code quality"""
    return await claude_code_service.analyze_code_quality(code, code_type)


async def ai_generate_docs(component_path: str, doc_type: str = "api") -> Optional[str]:
    """Convenience function to generate documentation"""
    return await claude_code_service.generate_documentation(component_path, doc_type)