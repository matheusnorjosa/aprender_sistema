# core/signals.py
"""
Signals for the Sistema Aprender
Role-based authorization is now handled through Django Groups
No automatic synchronization signals needed
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Usuario

# Future signals can be added here as needed
# Example:
# @receiver(post_save, sender=Usuario)
# def user_created_handler(sender, instance, created, **kwargs):
#     """Handle new user creation"""
#     if created:
#         # Add any default setup for new users
#         pass
