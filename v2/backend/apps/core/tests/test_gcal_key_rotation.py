"""
Rotação da chave dos tokens do Google sem parada (FER-59, M12-12 da auditoria de 17/07).

`GCAL_ENCRYPTION_KEY` é a chave principal (cifra e decifra); `GCAL_ENCRYPTION_KEY_FALLBACKS` lista,
separadas por vírgula, chaves antigas que só decifram (MultiFernet). A troca (GUIDE_GCAL.md, seção 8):
FALLBACKS = nova; depois principal = nova e FALLBACKS = antiga; `manage.py rotate_gcal_encryption_key`
recifra tudo com a principal, numa transação só; por fim tirar o FALLBACKS.

Este arquivo NÃO usa o patch de memoryview do `test_google_oauth.py`. Atenção ao driver: na CI e no
dev o Django usa o psycopg 3 (vem pelo pgcli do requirements-dev.txt), que devolve `bytes` para o
BinaryField; em produção só há psycopg2 (requirements-prod.txt), que devolve `memoryview`. O caso de
produção é simulado à parte em `_banco_devolve_memoryview` (o comando antigo quebrava nele).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

import pytest
from cryptography.fernet import Fernet, InvalidToken

from apps.core.models import AuditLog, GoogleOAuthCredential
from apps.core.services.google_oauth import decrypt_token, encrypt_token, rotate_encryption_key
from apps.core.tests.factories import UsuarioFactory

ACCESS = "fake_access_token_fer59"
REFRESH = "fake_refresh_token_fer59"


@pytest.fixture
def chaves(monkeypatch):
    """Chave antiga (a de hoje) e nova; começa só com a antiga configurada."""
    antiga = Fernet.generate_key().decode()
    nova = Fernet.generate_key().decode()
    monkeypatch.setenv("GCAL_ENCRYPTION_KEY", antiga)
    monkeypatch.delenv("GCAL_ENCRYPTION_KEY_FALLBACKS", raising=False)
    return {"antiga": antiga, "nova": nova}


def _trocar_para_nova(monkeypatch, chaves, fallbacks: str | None = None) -> None:
    monkeypatch.setenv("GCAL_ENCRYPTION_KEY", chaves["nova"])
    monkeypatch.setenv("GCAL_ENCRYPTION_KEY_FALLBACKS", chaves["antiga"] if fallbacks is None else fallbacks)


def _credencial(access: bytes, refresh: bytes) -> GoogleOAuthCredential:
    cred = GoogleOAuthCredential.objects.create(
        user=UsuarioFactory(),
        google_email="fer59@aprendereditora.com.br",
        access_token_encrypted=access,
        refresh_token_encrypted=refresh,
        token_expiry=timezone.now() + timedelta(hours=1),
    )
    # Lida de volta do banco (na CI vem `bytes`; o `memoryview` de produção é simulado à parte).
    return GoogleOAuthCredential.objects.get(pk=cred.pk)


@pytest.fixture
def _banco_devolve_memoryview(monkeypatch):
    """Simula o psycopg2 de produção: o BinaryField chega como `memoryview`."""
    original = GoogleOAuthCredential.from_db  # já ligado à classe

    def from_db(cls, db, field_names, values):
        values = [memoryview(v) if isinstance(v, bytes) else v for v in values]
        return original(db, field_names, values)

    monkeypatch.setattr(GoogleOAuthCredential, "from_db", classmethod(from_db))


def _abre_so_com(chave: str, token) -> str:
    return Fernet(chave.encode()).decrypt(bytes(token)).decode()


@pytest.mark.django_db
class TestLeituraComChaveAntiga:
    def test_token_da_chave_antiga_abre_quando_ela_esta_em_fallbacks(self, monkeypatch, chaves):
        cifrado_antigo = encrypt_token(ACCESS)
        _trocar_para_nova(monkeypatch, chaves)

        assert decrypt_token(cifrado_antigo) == ACCESS

    def test_sem_fallbacks_o_token_da_chave_antiga_nao_abre(self, monkeypatch, chaves):
        cifrado_antigo = encrypt_token(ACCESS)
        monkeypatch.setenv("GCAL_ENCRYPTION_KEY", chaves["nova"])

        with pytest.raises(InvalidToken):
            decrypt_token(cifrado_antigo)

    def test_cifrar_usa_sempre_a_principal(self, monkeypatch, chaves):
        _trocar_para_nova(monkeypatch, chaves)

        assert _abre_so_com(chaves["nova"], encrypt_token(ACCESS)) == ACCESS

    def test_le_o_que_vem_do_banco(self, monkeypatch, chaves):
        cred = _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        _trocar_para_nova(monkeypatch, chaves)

        assert decrypt_token(cred.refresh_token_encrypted) == REFRESH

    def test_aceita_memoryview(self, monkeypatch, chaves):
        cifrado_antigo = encrypt_token(ACCESS)
        _trocar_para_nova(monkeypatch, chaves)

        assert decrypt_token(memoryview(cifrado_antigo)) == ACCESS

    def test_entradas_vazias_e_espacos_sao_ignorados(self, monkeypatch, chaves):
        cifrado_antigo = encrypt_token(ACCESS)
        _trocar_para_nova(monkeypatch, chaves, fallbacks=f" , {chaves['antiga']} ,, ")

        assert decrypt_token(cifrado_antigo) == ACCESS

    def test_chave_malformada_em_fallbacks_falha_sem_mostrar_a_chave(self, monkeypatch, chaves):
        _trocar_para_nova(monkeypatch, chaves, fallbacks="nao-e-uma-chave-fernet-SEGREDO")

        with pytest.raises(ValueError) as erro:
            encrypt_token(ACCESS)
        assert "SEGREDO" not in str(erro.value)
        assert "GCAL_ENCRYPTION_KEY_FALLBACKS" in str(erro.value)


@pytest.mark.django_db
class TestRotacao:
    def test_recifra_tudo_com_a_principal(self, monkeypatch, chaves):
        c1 = _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        c2 = _credencial(encrypt_token(ACCESS + "2"), encrypt_token(REFRESH + "2"))
        _trocar_para_nova(monkeypatch, chaves)

        assert rotate_encryption_key().recifradas == 2

        for cred, sufixo in ((c1, ""), (c2, "2")):
            cred.refresh_from_db()
            assert _abre_so_com(chaves["nova"], cred.access_token_encrypted) == ACCESS + sufixo
            assert _abre_so_com(chaves["nova"], cred.refresh_token_encrypted) == REFRESH + sufixo

    def test_auditlog_sem_chave(self, monkeypatch, chaves):
        _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        _trocar_para_nova(monkeypatch, chaves)

        rotate_encryption_key()

        audit = AuditLog.objects.filter(action=AuditLog.Action.GCAL_ENCRYPTION_KEY_ROTATION).last()
        assert audit is not None
        assert audit.details["credentials_updated"] == 1
        assert audit.details["fallbacks_count"] == 1
        texto = str(audit.details)
        assert chaves["nova"] not in texto and chaves["antiga"] not in texto

    def test_falha_em_uma_desfaz_todas(self, monkeypatch, chaves):
        boa = _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        perdida = Fernet(Fernet.generate_key())  # chave que ninguém tem mais
        ruim = _credencial(perdida.encrypt(b"x"), perdida.encrypt(b"y"))
        antes = {c.pk: bytes(c.access_token_encrypted) for c in (boa, ruim)}
        _trocar_para_nova(monkeypatch, chaves)

        with pytest.raises(InvalidToken):
            rotate_encryption_key()

        for cred in (boa, ruim):
            cred.refresh_from_db()
            assert bytes(cred.access_token_encrypted) == antes[cred.pk]
        assert not AuditLog.objects.filter(action=AuditLog.Action.GCAL_ENCRYPTION_KEY_ROTATION).exists()

    def test_recifra_quando_o_banco_devolve_memoryview(self, monkeypatch, chaves, _banco_devolve_memoryview):
        cred = _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        assert isinstance(cred.access_token_encrypted, memoryview)  # a simulação pegou
        _trocar_para_nova(monkeypatch, chaves)

        assert rotate_encryption_key().recifradas == 1

        cred = GoogleOAuthCredential.objects.get(pk=cred.pk)
        assert _abre_so_com(chaves["nova"], cred.refresh_token_encrypted) == REFRESH

    def test_sem_credenciais_conta_zero(self, monkeypatch, chaves):
        _trocar_para_nova(monkeypatch, chaves)

        assert rotate_encryption_key().recifradas == 0


@pytest.mark.django_db
class TestComando:
    def test_nao_aceita_chave_na_linha_de_comando(self, chaves):
        # O comando antigo aceitava as duas e rodava; o novo recusa qualquer chave em argv.
        with pytest.raises(CommandError):
            call_command("rotate_gcal_encryption_key", "--old-key", chaves["antiga"], "--new-key", chaves["nova"])

    def test_roda_sem_argumentos_e_nao_imprime_chave(self, monkeypatch, chaves):
        cred = _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        _trocar_para_nova(monkeypatch, chaves)
        out = StringIO()

        call_command("rotate_gcal_encryption_key", stdout=out, stderr=out)

        saida = out.getvalue()
        assert "1" in saida
        assert chaves["nova"] not in saida and chaves["antiga"] not in saida
        cred.refresh_from_db()
        assert _abre_so_com(chaves["nova"], cred.access_token_encrypted) == ACCESS

    def test_sem_fallbacks_avisa_que_a_chave_nao_mudou(self, chaves):
        _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        out = StringIO()

        call_command("rotate_gcal_encryption_key", stdout=out, stderr=out)

        saida = out.getvalue()
        assert "nenhuma chave em GCAL_ENCRYPTION_KEY_FALLBACKS" in saida
        assert "Próximo passo" not in saida

    def test_principal_repetida_em_fallbacks_avisa_que_a_chave_nao_mudou(self, monkeypatch, chaves):
        _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        monkeypatch.setenv("GCAL_ENCRYPTION_KEY_FALLBACKS", chaves["antiga"])
        out = StringIO()

        call_command("rotate_gcal_encryption_key", stdout=out, stderr=out)

        saida = out.getvalue()
        assert "também está em GCAL_ENCRYPTION_KEY_FALLBACKS" in saida
        assert "Próximo passo" not in saida
        assert chaves["antiga"] not in saida

    def test_passo_3_esquecido_nao_manda_tirar_fallbacks(self, monkeypatch, chaves):
        # Estado do passo 2: principal ainda a antiga, nova só em FALLBACKS.
        _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        monkeypatch.setenv("GCAL_ENCRYPTION_KEY_FALLBACKS", chaves["nova"])
        out = StringIO()

        call_command("rotate_gcal_encryption_key", stdout=out, stderr=out)

        saida = out.getvalue()
        assert "nenhuma credencial estava cifrada" in saida
        assert "Próximo passo" not in saida
        assert chaves["nova"] not in saida and chaves["antiga"] not in saida

    def test_banco_vazio_nao_manda_tirar_fallbacks(self, monkeypatch, chaves):
        # Sem credenciais não há como conferir que a principal é a nova.
        monkeypatch.setenv("GCAL_ENCRYPTION_KEY_FALLBACKS", chaves["nova"])
        out = StringIO()

        call_command("rotate_gcal_encryption_key", stdout=out, stderr=out)

        saida = out.getvalue()
        assert "nenhuma credencial estava cifrada" in saida
        assert "Próximo passo" not in saida

    def test_rotacao_de_verdade_manda_tirar_fallbacks(self, monkeypatch, chaves):
        _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        _trocar_para_nova(monkeypatch, chaves)
        out = StringIO()

        call_command("rotate_gcal_encryption_key", stdout=out, stderr=out)

        assert "Próximo passo" in out.getvalue()

    def test_conta_as_que_so_abriam_com_fallback(self, monkeypatch, chaves):
        _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))
        _trocar_para_nova(monkeypatch, chaves)
        _credencial(encrypt_token(ACCESS), encrypt_token(REFRESH))  # já cifrada com a nova

        resultado = rotate_encryption_key()

        assert (resultado.recifradas, resultado.so_com_fallback) == (2, 1)
        audit = AuditLog.objects.filter(action=AuditLog.Action.GCAL_ENCRYPTION_KEY_ROTATION).last()
        assert audit is not None
        assert audit.details["credentials_from_fallback"] == 1

    def test_credencial_que_nao_abre_vira_command_error(self, monkeypatch, chaves):
        perdida = Fernet(Fernet.generate_key())
        _credencial(perdida.encrypt(b"x"), perdida.encrypt(b"y"))
        _trocar_para_nova(monkeypatch, chaves)

        with pytest.raises(CommandError):
            call_command("rotate_gcal_encryption_key", stdout=StringIO(), stderr=StringIO())
