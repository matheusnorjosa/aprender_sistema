"""
Testes para atualizações de contexto do Sistema APRENDER
"""
import pytest
import json
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Adicionar o diretório neural_system ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "neural_system"))

# Import das funções de update_context
try:
    from update_context import (
        calculate_file_hash,
        get_file_hashes,
        load_last_hashes,
        save_last_hashes,
        update_claude_context,
        restart_mcp_server
    )
except ImportError:
    pytest.skip("Update context module not available", allow_module_level=True)


class TestContextUpdates:
    """Test suite para funcionalidade de atualização de contexto."""

    def test_calculate_file_hash(self):
        """Testa cálculo de hash de arquivo."""
        # Criar arquivo temporário
        test_content = "Conteúdo de teste para hash"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            hash1 = calculate_file_hash(Path(temp_file))
            hash2 = calculate_file_hash(Path(temp_file))

            # Hash deve ser consistente
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 produz string hex de 64 caracteres

            # Conteúdo diferente deve produzir hash diferente
            with open(temp_file, 'w') as f:
                f.write("Conteúdo diferente")

            hash3 = calculate_file_hash(Path(temp_file))
            assert hash1 != hash3

        finally:
            os.unlink(temp_file)

    def test_get_file_hashes(self):
        """Testa obtenção de hashes de arquivos de documentação."""
        # Criar estrutura de documentação temporária
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)

            # Criar arquivos de teste
            (docs_dir / "ARQUITETURA_REFERENCIA.md").write_text("# Arquitetura")
            (docs_dir / "PADROES_CODIGO_PYTHON.md").write_text("# Padrões")
            (docs_dir / "CLAUDE_CONTEXT_PACKAGE.md").write_text("# Contexto")

            # Criar subdiretório docs
            docs_subdir = docs_dir / "docs"
            docs_subdir.mkdir()
            (docs_subdir / "fluxo_aprovacao.md").write_text("# Fluxo de Aprovação")

            # Mock DOCS_DIR
            with patch('update_context.DOCS_DIR', docs_dir):
                hashes = get_file_hashes()

                # Deve conter todos os arquivos de documentação
                assert "ARQUITETURA_REFERENCIA.md" in hashes
                assert "PADROES_CODIGO_PYTHON.md" in hashes
                assert "CLAUDE_CONTEXT_PACKAGE.md" in hashes
                assert "docs/fluxo_aprovacao.md" in hashes
                assert len(hashes) >= 4

    def test_load_last_hashes_no_file(self):
        """Testa carregamento de hashes quando arquivo não existe."""
        with patch('update_context.LAST_UPDATE_FILE', Path("/arquivo/inexistente.json")):
            hashes = load_last_hashes()
            assert hashes == {}

    def test_save_and_load_last_hashes(self):
        """Testa salvamento e carregamento de hashes."""
        # Criar diretório de contexto temporário
        with tempfile.TemporaryDirectory() as temp_dir:
            context_dir = Path(temp_dir)

            with patch('update_context.CONTEXT_DIR', context_dir):
                test_hashes = {
                    "arquivo1.md": "hash1",
                    "arquivo2.md": "hash2",
                    "docs/arquivo3.md": "hash3"
                }

                save_last_hashes(test_hashes)

                # Verificar se arquivo foi criado
                last_update_file = context_dir / "last_update.json"
                assert last_update_file.exists()

                # Carregar e verificar conteúdo
                with patch('update_context.LAST_UPDATE_FILE', last_update_file):
                    loaded_hashes = load_last_hashes()
                    assert loaded_hashes == test_hashes

                # Verificar estrutura do arquivo
                with open(last_update_file, 'r') as f:
                    data = json.load(f)
                    assert "timestamp" in data
                    assert "hashes" in data
                    assert "project" in data
                    assert data["project"] == "Sistema APRENDER"
                    assert data["hashes"] == test_hashes

    @patch('update_context.anthropic')
    def test_update_claude_context_success(self, mock_anthropic):
        """Testa atualização bem-sucedida do contexto do Claude."""
        # Mock do cliente Anthropic
        mock_client = Mock()
        mock_response = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        # Criar arquivo temporário para teste
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Documento de Teste\nConteúdo atualizado")
            temp_file = f.name

        try:
            with patch('update_context.CLAUDE_API_KEY', 'test_key'):
                with patch('update_context.DOCS_DIR', Path(temp_file).parent):
                    result = update_claude_context([Path(temp_file).name])
                    assert result is True

                    # Verificar se API foi chamada
                    mock_client.messages.create.assert_called_once()

                    # Verificar estrutura da requisição
                    call_args = mock_client.messages.create.call_args
                    assert call_args[1]['model'] == 'claude-3-sonnet-20240229'
                    assert 'messages' in call_args[1]

        finally:
            os.unlink(temp_file)

    def test_update_claude_context_no_api_key(self):
        """Testa atualização do contexto do Claude sem API key."""
        with patch('update_context.CLAUDE_API_KEY', None):
            result = update_claude_context(['teste.md'])
            assert result is False

    @patch('update_context.subprocess.run')
    def test_restart_mcp_server_success(self, mock_run):
        """Testa reinicialização bem-sucedida do servidor MCP."""
        # Mock do servidor MCP existente
        mock_server_path = Path("/caminho/para/mcp_server_aprender.py")

        with patch('update_context.Path') as mock_path:
            mock_path.return_value.parent / "mcp_server_aprender.py" = mock_server_path
            mock_server_path.exists.return_value = True

            result = restart_mcp_server()
            assert result is True

            # Verificar se subprocess foi chamado para parar o servidor
            mock_run.assert_called_once_with(
                ["pkill", "-f", "mcp_server_aprender.py"],
                check=False
            )

    @patch('update_context.subprocess.run')
    def test_restart_mcp_server_not_found(self, mock_run):
        """Testa reinicialização quando servidor MCP não existe."""
        with tempfile.TemporaryDirectory() as temp_dir:
            neural_dir = Path(temp_dir)

            with patch('update_context.Path') as mock_path:
                mock_instance = Mock()
                mock_instance.parent = neural_dir
                mock_path.return_value = mock_instance

                # O arquivo não existe
                mcp_server = neural_dir / "mcp_server_aprender.py"
                mock_instance.parent.__truediv__ = Mock(return_value=mcp_server)

                result = restart_mcp_server()
                assert result is False

    def test_integration_hash_detection(self):
        """Teste de integração: detecção de mudanças de hash."""
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            context_dir = docs_dir / "neural_system" / "context"
            context_dir.mkdir(parents=True)

            # Criar arquivo inicial
            doc_file = docs_dir / "TESTE.md"
            doc_file.write_text("Conteúdo inicial")

            # Simular primeira execução
            with patch('update_context.DOCS_DIR', docs_dir):
                with patch('update_context.CONTEXT_DIR', context_dir):
                    # Primeira execução - sem hashes anteriores
                    initial_hashes = {"TESTE.md": calculate_file_hash(doc_file)}
                    save_last_hashes(initial_hashes)

                    # Modificar arquivo
                    doc_file.write_text("Conteúdo modificado")

                    # Segunda execução - deve detectar mudança
                    current_hashes = {"TESTE.md": calculate_file_hash(doc_file)}
                    last_hashes = load_last_hashes()

                    assert current_hashes["TESTE.md"] != last_hashes["TESTE.md"]

    def test_context_directory_creation(self):
        """Testa criação automática do diretório de contexto."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = Path(temp_dir) / "context"
            assert not non_existent_dir.exists()

            with patch('update_context.CONTEXT_DIR', non_existent_dir):
                save_last_hashes({"teste.md": "hash123"})

                # Diretório deve ter sido criado
                assert non_existent_dir.exists()
                assert (non_existent_dir / "last_update.json").exists()

    def test_hash_stability(self):
        """Testa estabilidade dos hashes para mesmo conteúdo."""
        content = "Conteúdo de teste\nCom múltiplas linhas\nE caracteres especiais: áéíóú"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            # Calcular hash múltiplas vezes
            hashes = []
            for _ in range(5):
                hashes.append(calculate_file_hash(Path(temp_file)))

            # Todos os hashes devem ser idênticos
            assert len(set(hashes)) == 1
            assert all(len(h) == 64 for h in hashes)  # SHA256 length

        finally:
            os.unlink(temp_file)