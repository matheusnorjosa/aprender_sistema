"""
Importações pela tela (lote C do alinhamento, 06/11/2026): login = CPF e CPF fora da resposta.

- O importador de usuários cria a conta com `username = cpf` (D14), com e sem e-mail; antes o login vinha
  do e-mail ou era `user_<cpf>`. Conta cujo login já é o CPF cai em "existente" (nunca ganha sufixo).
- As pendências do importador de usuários e o ensaio do importador de vínculos não trazem o CPF (D15).

Os CPFs aqui são sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false

from __future__ import annotations

import json

import pytest

from apps.core.models import Usuario
from apps.core.services.equipe_gerencia_import import import_equipe_gerencia_from_file
from apps.core.services.usuarios_import import import_usuarios_from_file
from apps.core.tests.factories import GerenciaFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _csv(tmp_path, texto: str) -> str:
    arquivo = tmp_path / "planilha.csv"
    arquivo.write_text(texto, encoding="utf-8")
    return str(arquivo)


def test_importar_com_email_cria_o_login_igual_ao_cpf(tmp_path):
    path = _csv(tmp_path, "cpf,nome,email\n10000000019,Maria Silva,maria.silva@example.invalid\n")

    import_usuarios_from_file(path=path, dry_run=False)

    assert Usuario.objects.get(cpf="10000000019").username == "10000000019"


def test_importar_sem_email_cria_o_login_igual_ao_cpf(tmp_path):
    path = _csv(tmp_path, "cpf,nome\n10000005673,Joao Souza\n")

    import_usuarios_from_file(path=path, dry_run=False)

    assert Usuario.objects.get(cpf="10000005673").username == "10000005673"


def test_conta_cujo_login_ja_e_o_cpf_cai_em_existente(tmp_path):
    # O CPF mudou pela tela antes do lote C e o login ficou com o CPF antigo.
    antiga = UsuarioFactory(username="10000006300", cpf="10000007110", first_name="Antigo", last_name="Nome")
    path = _csv(tmp_path, "cpf,nome\n10000006300,Novo Nome\n")

    resultado = import_usuarios_from_file(path=path, dry_run=False)

    assert resultado["stats"]["created"] == 0
    assert resultado["stats"]["updated"] == 1
    antiga.refresh_from_db()
    assert antiga.first_name == "Novo"
    assert not Usuario.objects.filter(username__startswith="10000006300_").exists()


def test_pendencias_do_importador_de_usuarios_nao_trazem_o_cpf(tmp_path):
    UsuarioFactory(superuser=True, username="10000000795", cpf="10000000795")
    path = _csv(
        tmp_path,
        "\n".join(
            [
                "cpf,nome,grupos",
                "10000000018,CPF Errado,",  # dígito verificador errado
                "10000000019,,",  # sem nome
                "10000000795,Super Usuario,",  # superusuário protegido
                "10000005673,Com Grupo,Formador",  # grupos ignorados (sem ator)
            ]
        ),
    )

    resultado = import_usuarios_from_file(path=path, dry_run=True)

    pendencias = resultado["pendencias"]
    assert pendencias["cpf_invalid"] and pendencias["nome_missing"]
    assert pendencias["superuser_protected"] and pendencias["grupos_ignorados"]
    texto = json.dumps(pendencias)
    for cpf in ("10000000018", "10000000019", "10000000795", "10000005673"):
        assert cpf not in texto


def test_ensaio_de_vinculos_com_cpf_inexistente_nao_devolve_o_cpf(tmp_path):
    GerenciaFactory(nome="GERENCIA VINCULO TESTE", nome_setor="Vinculo Teste")
    path = _csv(
        tmp_path,
        "\n".join(
            [
                "setor,papel,usuario_cpf,usuario_email,usuario_nome",
                "Vinculo Teste,FORMADOR,100.000.056-73,10000005673@placeholder.local,Fulano 10000005673",
            ]
        ),
    )

    resultado = import_equipe_gerencia_from_file(path=path, dry_run=True)

    nao_achados = resultado["pendencias"]["usuario_not_found"]
    assert len(nao_achados) == 1
    texto = json.dumps(resultado)
    assert "10000005673" not in texto
    assert "100.000.056-73" not in texto
