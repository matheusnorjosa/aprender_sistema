"""
Testes para o servidor MCP do Sistema APRENDER
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Adicionar o diretório neural_system ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "neural_system"))

# Import do servidor MCP
try:
    from mcp_server_aprender import (
        _extract_section_from_content,
        _read_documentation_file,
        server,
    )
except ImportError:
    pytest.skip("MCP server module not available", allow_module_level=True)


class TestMCPServer:
    """Test suite para funcionalidade do servidor MCP."""

    def test_list_tools(self):
        """Testa se as ferramentas são listadas corretamente."""
        tools = asyncio.run(server.list_tools())

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Verificar se ferramentas essenciais estão presentes
        tool_names = [tool["name"] for tool in tools]
        essential_tools = [
            "get_architecture_patterns",
            "get_python_patterns",
            "get_security_guidelines",
            "get_business_rules",
            "validate_code_pattern",
            "check_security_vulnerabilities",
            "get_system_context",
            "get_project_structure",
        ]

        for tool in essential_tools:
            assert tool in tool_names, f"Ferramenta {tool} não encontrada"

    def test_read_documentation_file_success(self):
        """Testa leitura bem-sucedida de arquivos de documentação."""
        # Criar arquivo de teste temporário
        test_content = "# Documento de Teste\nEste é um teste."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            # Testar leitura do arquivo
            content = _read_documentation_file(temp_file)
            assert content == test_content
        finally:
            os.unlink(temp_file)

    def test_read_documentation_file_not_found(self):
        """Testa leitura de arquivo de documentação inexistente."""
        content = _read_documentation_file("/arquivo/inexistente.md")
        assert content is None

    def test_extract_section_from_content(self):
        """Testa extração de seções do conteúdo."""
        test_content = """
# Documento Principal

## Seção de Aprovação
Conteúdo da seção de aprovação.
Mais detalhes aqui.

## Outra Seção
Conteúdo diferente.
"""

        section = _extract_section_from_content(test_content, "aprovação")
        assert "Seção de Aprovação" in section
        assert "Conteúdo da seção de aprovação" in section
        assert "Outra Seção" not in section

    @pytest.mark.asyncio
    async def test_get_architecture_patterns(self):
        """Testa obtenção de padrões de arquitetura."""
        mock_content = "# Padrões de Arquitetura\nConteúdo de teste"

        with patch(
            "mcp_server_aprender._read_documentation_file", return_value=mock_content
        ):
            result = await server.call_tool("get_architecture_patterns", {})

            assert len(result) == 1
            assert result[0]["type"] == "text"
            assert result[0]["text"] == mock_content

    @pytest.mark.asyncio
    async def test_validate_code_pattern_good_django_code(self):
        """Testa validação de código Django com bom padrão."""
        good_code = '''
@login_required
def evento_detail_view(request, evento_id: int) -> HttpResponse:
    """View para detalhar evento específico."""
    evento = get_object_or_404(Evento, pk=evento_id)
    return render(request, 'core/evento_detail.html', {'evento': evento})
'''

        result = await server.call_tool(
            "validate_code_pattern", {"code": good_code, "context": "view"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "✅ Código segue os padrões" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_validate_code_pattern_bad_django_code(self):
        """Testa validação de código Django com problemas."""
        bad_code = """
def bad_view(request):
    print(f"User accessed view")
    user_id = request.GET['user_id']
    return HttpResponse("Done")
"""

        result = await server.call_tool(
            "validate_code_pattern", {"code": bad_code, "context": "view"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "ERRO" in result[0]["text"]
        assert "print(" in result[0]["text"] or "permissão" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_validate_django_model_pattern(self):
        """Testa validação específica para models Django."""
        model_code = """
class Evento(models.Model):
    nome = models.CharField(max_length=200)
    data_inicio = models.DateTimeField()

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
"""

        result = await server.call_tool(
            "validate_code_pattern", {"code": model_code, "context": "model"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        # Deve avisar sobre timezone-aware
        assert "timezone" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_check_security_vulnerabilities_safe_code(self):
        """Testa verificação de segurança com código seguro."""
        safe_code = """
@login_required
@permission_required('core.view_evento')
def evento_list(request):
    form = EventoForm(request.POST)
    if form.is_valid():
        evento = form.save()
        return redirect('evento_detail', evento.pk)
    return render(request, 'core/evento_form.html', {'form': form})
"""

        result = await server.call_tool(
            "check_security_vulnerabilities", {"code": safe_code}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "✅ Nenhuma vulnerabilidade óbvia detectada" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_check_security_vulnerabilities_unsafe_code(self):
        """Testa verificação de segurança com código vulnerável."""
        unsafe_code = """
def unsafe_view(request):
    user_id = request.GET['user_id']
    query = "SELECT * FROM auth_user WHERE id = %s" % user_id
    api_key = "hardcoded-secret-key-123"
    return execute_query(query)
"""

        result = await server.call_tool(
            "check_security_vulnerabilities", {"code": unsafe_code}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "RISCO" in result[0]["text"]
        # Deve detectar SQL injection e hardcoded secret
        assert (
            "injection" in result[0]["text"].lower()
            or "segredo" in result[0]["text"].lower()
        )

    @pytest.mark.asyncio
    async def test_get_business_rules_availability(self):
        """Testa obtenção de regras de negócio de disponibilidade."""
        result = await server.call_tool(
            "get_business_rules", {"rule_category": "availability"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        content = result[0]["text"]
        assert "Códigos de Disponibilidade" in content
        assert "America/Fortaleza" in content

    @pytest.mark.asyncio
    async def test_get_business_rules_calendar(self):
        """Testa obtenção de regras de integração com Google Calendar."""
        result = await server.call_tool(
            "get_business_rules", {"rule_category": "calendar"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        content = result[0]["text"]
        assert "Google Calendar" in content
        assert "aprovação manual" in content.lower()

    @pytest.mark.asyncio
    async def test_get_project_structure(self):
        """Testa obtenção da estrutura do projeto."""
        result = await server.call_tool("get_project_structure", {})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        content = result[0]["text"]
        assert "aprender_sistema/" in content
        assert "core/" in content
        assert "neural_system/" in content

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Testa manipulação de ferramentas desconhecidas."""
        result = await server.call_tool("ferramenta_inexistente", {})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Ferramenta desconhecida" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_validate_django_command_pattern(self):
        """Testa validação específica para Django management commands."""
        command_code = """
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Importa dados de teste"

    def handle(self, *args, **options):
        self.stdout.write("Importando dados...")
"""

        result = await server.call_tool(
            "validate_code_pattern", {"code": command_code, "context": "command"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        # Não deve haver erros para um command bem formado
        assert "✅" in result[0]["text"] or "ERRO" not in result[0]["text"]

    @pytest.mark.asyncio
    async def test_validate_django_form_pattern(self):
        """Testa validação específica para Django forms."""
        form_code = """
from django import forms
from django.core.exceptions import ValidationError

class EventoForm(forms.ModelForm):
    def clean_data_inicio(self):
        data = self.cleaned_data['data_inicio']
        if data < timezone.now():
            raise ValidationError("Data deve ser no futuro")
        return data
"""

        result = await server.call_tool(
            "validate_code_pattern", {"code": form_code, "context": "form"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"
        # Form bem estruturado não deve ter erros significativos
        content = result[0]["text"]
        assert "ModelForm" not in content or "ERRO" not in content
