"""
MCP Toolset for Core Models - Aprender Sistema

This toolset exposes core Django models to MCP clients for AI-assisted queries and operations.
"""

from django_mcp_server.toolsets import ModelQueryToolset

from core.models import Formador, Municipio, Projeto, TipoEvento, Usuario


class CoreModelToolset(ModelQueryToolset):
    """
    MCP toolset for core models: Usuario, Formador, Municipio, Projeto, TipoEvento
    """

    name = "core_models"
    description = "Query and manage core models of the Aprender Sistema"

    # Define which models are accessible
    models = [
        Usuario,
        Formador,
        Municipio,
        Projeto,
        TipoEvento,
    ]

    # Define which fields are accessible for each model
    accessible_fields = {
        "Usuario": [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "groups",
            "primary_role",
        ],
        "Formador": ["id", "nome", "email", "ativo", "area_atuacao", "usuario"],
        "Municipio": ["id", "nome", "uf", "ativo"],
        "Projeto": ["id", "nome", "descricao", "ativo", "vinculado_superintendencia"],
        "TipoEvento": ["id", "nome", "online", "ativo"],
    }

    # Define read-only fields (for security)
    readonly_fields = {
        "Usuario": ["id", "date_joined", "password", "last_login"],
        "Formador": ["id"],
        "Municipio": ["id"],
        "Projeto": ["id"],
        "TipoEvento": ["id"],
    }

    def get_queryset(self, model):
        """
        Customize querysets for each model
        """
        if model == Usuario:
            # Only return active users, exclude sensitive data
            return model.objects.filter(is_active=True).select_related()
        elif model == Formador:
            # Include related user data
            return model.objects.filter(ativo=True).select_related(
                "usuario", "area_atuacao"
            )
        else:
            # Default: return active records
            return (
                model.objects.filter(ativo=True)
                if hasattr(model, "ativo")
                else model.objects.all()
            )

    def can_query(self, model, user=None):
        """
        Permission check for querying models
        """
        # Allow queries for authenticated users or in development
        from django.conf import settings

        if getattr(settings, "DEBUG", False):
            return True
        return user and user.is_authenticated

    def can_create(self, model, user=None):
        """
        Permission check for creating objects
        """
        # More restrictive for creation
        if not user or not user.is_authenticated:
            return False

        # Check specific permissions based on model
        if model == Usuario:
            return user.has_perm("auth.add_user") or user.is_superuser
        elif model == Formador:
            return (
                user.has_perm("core.add_formador")
                or user.groups.filter(name__in=["admin", "superintendencia"]).exists()
            )
        else:
            return user.has_perm(f"core.add_{model._meta.model_name}")

    def can_update(self, model, obj, user=None):
        """
        Permission check for updating objects
        """
        if not user or not user.is_authenticated:
            return False

        # Users can update their own profile
        if model == Usuario and obj == user:
            return True

        # Formadores can update their own profile
        if (
            model == Formador
            and hasattr(user, "formador_profile")
            and obj == user.formador_profile
        ):
            return True

        # Admin and superintendencia can update most things
        if (
            user.is_superuser
            or user.groups.filter(name__in=["admin", "superintendencia"]).exists()
        ):
            return True

        return False

    def can_delete(self, model, obj, user=None):
        """
        Permission check for deleting objects - very restrictive
        """
        if not user or not user.is_authenticated:
            return False

        # Only superusers can delete core data
        return user.is_superuser
