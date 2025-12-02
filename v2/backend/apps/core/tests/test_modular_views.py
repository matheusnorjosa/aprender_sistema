"""
Test backwards compatibility for modular views package.

Ensures all views are importable from both:
- apps.core.views (new modular package)
- apps.core.views (legacy facade at views.py)
"""

import pytest


class TestViewsBackwardsCompatibility:
    """Test that all views.py exports remain accessible via legacy import."""

    def test_get_client_ip_importable_from_legacy(self):
        """_get_client_ip should be importable from views (facade)."""
        from apps.core.views import _get_client_ip
        assert callable(_get_client_ip)

    def test_api_root_importable_from_legacy(self):
        """api_root should be importable from views (facade)."""
        from apps.core.views import api_root
        assert callable(api_root)

    def test_solicitacao_viewset_importable_from_legacy(self):
        """SolicitacaoViewSet should be importable from views (facade)."""
        from apps.core.views import SolicitacaoViewSet
        assert SolicitacaoViewSet is not None

    def test_availability_block_viewset_importable_from_legacy(self):
        """AvailabilityBlockViewSet should be importable from views (facade)."""
        from apps.core.views import AvailabilityBlockViewSet
        assert AvailabilityBlockViewSet is not None

    def test_availability_check_view_importable_from_legacy(self):
        """AvailabilityCheckView should be importable from views (facade)."""
        from apps.core.views import AvailabilityCheckView
        assert AvailabilityCheckView is not None

    def test_availability_check_many_view_importable_from_legacy(self):
        """AvailabilityCheckManyView should be importable from views (facade)."""
        from apps.core.views import AvailabilityCheckManyView
        assert AvailabilityCheckManyView is not None

    def test_current_user_view_importable_from_legacy(self):
        """CurrentUserView should be importable from views (facade)."""
        from apps.core.views import CurrentUserView
        assert CurrentUserView is not None

    def test_municipio_viewset_importable_from_legacy(self):
        """MunicipioViewSet should be importable from views (facade)."""
        from apps.core.views import MunicipioViewSet
        assert MunicipioViewSet is not None

    def test_projeto_viewset_importable_from_legacy(self):
        """ProjetoViewSet should be importable from views (facade)."""
        from apps.core.views import ProjetoViewSet
        assert ProjetoViewSet is not None

    def test_produto_viewset_importable_from_legacy(self):
        """ProdutoViewSet should be importable from views (facade)."""
        from apps.core.views import ProdutoViewSet
        assert ProdutoViewSet is not None

    def test_gerencia_viewset_importable_from_legacy(self):
        """GerenciaViewSet should be importable from views (facade)."""
        from apps.core.views import GerenciaViewSet
        assert GerenciaViewSet is not None

    def test_compra_viewset_importable_from_legacy(self):
        """CompraViewSet should be importable from views (facade)."""
        from apps.core.views import CompraViewSet
        assert CompraViewSet is not None

    def test_usuario_admin_viewset_importable_from_legacy(self):
        """UsuarioAdminViewSet should be importable from views (facade)."""
        from apps.core.views import UsuarioAdminViewSet
        assert UsuarioAdminViewSet is not None

    def test_group_viewset_importable_from_legacy(self):
        """GroupViewSet should be importable from views (facade)."""
        from apps.core.views import GroupViewSet
        assert GroupViewSet is not None

    def test_audit_log_viewset_importable_from_legacy(self):
        """AuditLogViewSet should be importable from views (facade)."""
        from apps.core.views import AuditLogViewSet
        assert AuditLogViewSet is not None

    def test_municipio_option_viewset_importable_from_legacy(self):
        """MunicipioOptionViewSet should be importable from views (facade)."""
        from apps.core.views import MunicipioOptionViewSet
        assert MunicipioOptionViewSet is not None

    def test_projeto_option_viewset_importable_from_legacy(self):
        """ProjetoOptionViewSet should be importable from views (facade)."""
        from apps.core.views import ProjetoOptionViewSet
        assert ProjetoOptionViewSet is not None

    def test_coordenador_option_viewset_importable_from_legacy(self):
        """CoordenadorOptionViewSet should be importable from views (facade)."""
        from apps.core.views import CoordenadorOptionViewSet
        assert CoordenadorOptionViewSet is not None

    def test_formador_option_viewset_importable_from_legacy(self):
        """FormadorOptionViewSet should be importable from views (facade)."""
        from apps.core.views import FormadorOptionViewSet
        assert FormadorOptionViewSet is not None

    def test_tipo_evento_option_viewset_importable_from_legacy(self):
        """TipoEventoOptionViewSet should be importable from views (facade)."""
        from apps.core.views import TipoEventoOptionViewSet
        assert TipoEventoOptionViewSet is not None


class TestViewsPackageDirectImports:
    """Test that new modular package imports work correctly."""

    def test_utils_module_importable(self):
        """Utils module should be importable."""
        from apps.core.views.utils import _get_client_ip, api_root
        assert callable(_get_client_ip)
        assert callable(api_root)

    def test_solicitacao_module_importable(self):
        """Solicitacao module should be importable."""
        from apps.core.views.solicitacao import SolicitacaoViewSet
        assert SolicitacaoViewSet is not None

    def test_availability_module_importable(self):
        """Availability module should be importable."""
        from apps.core.views.availability import (
            AvailabilityBlockViewSet,
            AvailabilityCheckView,
            AvailabilityCheckManyView,
        )
        assert AvailabilityBlockViewSet is not None
        assert AvailabilityCheckView is not None
        assert AvailabilityCheckManyView is not None

    def test_user_module_importable(self):
        """User module should be importable."""
        from apps.core.views.user import CurrentUserView
        assert CurrentUserView is not None

    def test_admin_module_importable(self):
        """Admin module should be importable."""
        from apps.core.views.admin import (
            MunicipioViewSet,
            ProjetoViewSet,
            ProdutoViewSet,
            GerenciaViewSet,
            CompraViewSet,
            UsuarioAdminViewSet,
            GroupViewSet,
            AuditLogViewSet,
        )
        assert MunicipioViewSet is not None
        assert ProjetoViewSet is not None
        assert ProdutoViewSet is not None
        assert GerenciaViewSet is not None
        assert CompraViewSet is not None
        assert UsuarioAdminViewSet is not None
        assert GroupViewSet is not None
        assert AuditLogViewSet is not None

    def test_options_module_importable(self):
        """Options module should be importable."""
        from apps.core.views.options import (
            MunicipioOptionViewSet,
            ProjetoOptionViewSet,
            CoordenadorOptionViewSet,
            FormadorOptionViewSet,
            TipoEventoOptionViewSet,
        )
        assert MunicipioOptionViewSet is not None
        assert ProjetoOptionViewSet is not None
        assert CoordenadorOptionViewSet is not None
        assert FormadorOptionViewSet is not None
        assert TipoEventoOptionViewSet is not None


class TestViewsPackageStructure:
    """Test that views package has correct structure."""

    def test_package_has_all_attribute(self):
        """views package should have __all__ attribute."""
        from apps.core import views
        assert hasattr(views, '__all__')
        assert len(views.__all__) == 20  # All 20 exports

    def test_all_submodules_exist(self):
        """All submodules should be importable."""
        from apps.core.views import utils
        from apps.core.views import solicitacao
        from apps.core.views import availability
        from apps.core.views import user
        from apps.core.views import admin
        from apps.core.views import options

        assert utils is not None
        assert solicitacao is not None
        assert availability is not None
        assert user is not None
        assert admin is not None
        assert options is not None
