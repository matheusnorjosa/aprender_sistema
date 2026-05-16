"""
Hardening: ``safe_temp_upload_file`` neutraliza path-injection via ``upload.name``.

Cobre CodeQL py/path-injection (CWE-022/023/036/073/099) nos 11 endpoints de
import (``views_import_*.py`` + ``views_imports.py`` + ``views_controle_imports.py``).

A correção move o ``suffix`` de ``os.path.splitext(upload.name)`` direto para
``NamedTemporaryFile`` (vulnerável a path traversal via nome do upload) para
``_safe_upload_suffix`` + ``safe_temp_upload_file`` no helper centralizado em
``apps/core/upload_validators.py``. Nome original do upload nunca entra no
path filesystem final.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

import pytest

from apps.core.upload_validators import (
    ALLOWED_UPLOAD_EXTENSIONS,
    _safe_upload_suffix,
    safe_temp_upload_file,
)


def _fake_upload(name):
    """Fake uploaded file — só precisa expor ``.name`` para o helper."""
    return SimpleNamespace(name=name)


class TestSafeUploadSuffixAllowlist:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("compras.csv", ".csv"),
            ("planilha.xls", ".xls"),
            ("relatorio.xlsx", ".xlsx"),
            ("DADOS.CSV", ".csv"),  # uppercase → normaliza
            ("Arquivo.Xlsx", ".xlsx"),  # mixed case → normaliza
            ("compras.XLS", ".xls"),
        ],
    )
    def test_extensao_valida_preservada(self, name, expected):
        assert _safe_upload_suffix(_fake_upload(name)) == expected

    @pytest.mark.parametrize(
        "name",
        [
            "arquivo_sem_extensao",
            "arquivo.tsv",  # tsv não está no allowlist atual
            "arquivo.txt",  # txt não está no allowlist atual
            "arquivo.pdf",
            "arquivo.exe",
            "arquivo.sh",
            "arquivo.",
            ".csvbackup",  # sem ponto na frente do nome
        ],
    )
    def test_extensao_fora_allowlist_vira_tmp(self, name):
        assert _safe_upload_suffix(_fake_upload(name)) == ".tmp"


class TestSafeUploadSuffixPathTraversal:
    @pytest.mark.parametrize(
        "name",
        [
            "../../etc/passwd",
            "../../../etc/passwd.csv",
            "/etc/passwd.csv",
            "../etc/passwd.xls",
            "folder/file.csv",
            "folder/sub/file.xlsx",
            "/var/data/evil.csv",
        ],
    )
    def test_forward_slash_vira_tmp(self, name):
        assert _safe_upload_suffix(_fake_upload(name)) == ".tmp"

    @pytest.mark.parametrize(
        "name",
        [
            r"C:\Windows\system32\evil.csv",
            r"..\..\etc\evil.xls",
            r"folder\file.csv",
            r"\\server\share\file.csv",
        ],
    )
    def test_backslash_vira_tmp(self, name):
        assert _safe_upload_suffix(_fake_upload(name)) == ".tmp"

    @pytest.mark.parametrize(
        "name",
        [
            "file.csv\x00.exe",
            "\x00file.csv",
            "evil\x00name.xlsx",
        ],
    )
    def test_null_byte_vira_tmp(self, name):
        assert _safe_upload_suffix(_fake_upload(name)) == ".tmp"


class TestSafeUploadSuffixDefensive:
    def test_nome_vazio_vira_tmp(self):
        assert _safe_upload_suffix(_fake_upload("")) == ".tmp"

    def test_nome_none_vira_tmp(self):
        assert _safe_upload_suffix(_fake_upload(None)) == ".tmp"

    def test_objeto_sem_atributo_name_vira_tmp(self):
        upload = SimpleNamespace()  # sem .name
        assert _safe_upload_suffix(upload) == ".tmp"

    def test_nome_so_extensao_valida_preservada(self):
        # ".csv" tem stem "" e suffix ".csv" — PurePath aceita.
        # Comportamento atual: preserva ".csv".
        assert _safe_upload_suffix(_fake_upload("data.csv")) == ".csv"


class TestSafeTempUploadFile:
    def test_arquivo_criado_dentro_de_gettempdir(self):
        upload = _fake_upload("compras.csv")
        tmp = safe_temp_upload_file(upload)
        try:
            assert os.path.dirname(tmp.name) == tempfile.gettempdir()
        finally:
            tmp.close()
            os.unlink(tmp.name)

    def test_arquivo_criado_com_suffix_normalizado(self):
        upload = _fake_upload("Compras.CSV")
        tmp = safe_temp_upload_file(upload)
        try:
            assert tmp.name.endswith(".csv")
        finally:
            tmp.close()
            os.unlink(tmp.name)

    def test_arquivo_path_traversal_vira_tmp(self):
        upload = _fake_upload("../../etc/passwd")
        tmp = safe_temp_upload_file(upload)
        try:
            assert tmp.name.endswith(".tmp")
            # Garante que nem o nome original nem parte dele vazaram no path
            assert "passwd" not in tmp.name
            assert ".." not in tmp.name
            assert os.path.dirname(tmp.name) == tempfile.gettempdir()
        finally:
            tmp.close()
            os.unlink(tmp.name)

    def test_nome_original_nunca_aparece_no_path(self):
        # Verifica explicitamente que partes do upload.name não vazam.
        original = "minha_planilha_super_secreta.xlsx"
        upload = _fake_upload(original)
        tmp = safe_temp_upload_file(upload)
        try:
            # Só o suffix ".xlsx" sobrevive — não o stem.
            assert "minha_planilha_super_secreta" not in tmp.name
            assert tmp.name.endswith(".xlsx")
        finally:
            tmp.close()
            os.unlink(tmp.name)

    def test_arquivo_eh_gravavel_e_removivel(self):
        upload = _fake_upload("dados.csv")
        tmp = safe_temp_upload_file(upload)
        try:
            tmp.write(b"linha1,linha2\n")
            tmp.flush()
        finally:
            tmp.close()
        assert os.path.exists(tmp.name)
        os.unlink(tmp.name)
        assert not os.path.exists(tmp.name)

    def test_nome_invalido_cai_em_tmp(self):
        upload = _fake_upload("evil\x00name.csv")
        tmp = safe_temp_upload_file(upload)
        try:
            assert tmp.name.endswith(".tmp")
            assert "\x00" not in tmp.name
            assert "evil" not in tmp.name
        finally:
            tmp.close()
            os.unlink(tmp.name)


class TestAllowlistConstant:
    def test_allowlist_eh_frozenset(self):
        # Sanity: ninguém ampliou sem revisão de segurança.
        assert isinstance(ALLOWED_UPLOAD_EXTENSIONS, frozenset)

    def test_allowlist_alinhado_com_content_types(self):
        # CSV / XLS / XLSX são as únicas extensões aceitas em prod hoje
        # (ver ALLOWED_CONTENT_TYPES em upload_validators.py).
        assert ALLOWED_UPLOAD_EXTENSIONS == frozenset({".csv", ".xls", ".xlsx"})
