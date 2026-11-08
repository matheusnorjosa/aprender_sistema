"""
#1658 (partes A e B) — a lotação da carga não escolhe gerência nem pessoa por chute.

(A) Gerência: a cadeia de 4 degraus de `_resolve_gerencia` para no primeiro degrau em que alguma gerência casa,
ativa ou inativa, como o `.first()` antigo. Só vale a ativa sozinha no degrau; duas ou mais no degrau = ambígua:
nenhuma é escolhida e a linha sai com `gerencia_ambigua`; só inativas = `gerencia_inativa`. A ativa de um degrau
posterior nunca vence a inativa de um degrau anterior (a regra antiga parava na inativa).
(B) Pessoa: CPF válido sem cadastro deixa a pessoa de fora, sem cair para e-mail nem nome (decisão do dono de
07/11/2026, a mesma do #2035 na participação). No export_contract o motivo é `cpf_sem_cadastro` (o resto da
pessoa não resolvida segue `usuario_nao_resolvido`), e a conta que o e-mail ou o nome ligaria pela regra antiga sai
em `lotacao_perdida_contas` (só `u<id>`); no upload pela tela, `usuario_not_found`.

Lotação dá poder (`RBAC_FONTE=lotacao`): a regra só tira vínculo da carga, nunca liga outra pessoa ou gerência.
Fixtures sintéticas: CPFs de teste com DV válido, sem dado real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command

from apps.core.models import EquipeGerencia, Gerencia
from apps.core.services.equipe_gerencia_import import (
    _resolve_gerencia,
    _resolve_usuario,
    import_equipe_gerencia_from_file,
)
from apps.core.services.export_contract_importer import ExportContractImporter, _gerencia_da_linha
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_CPF_A = "11144477735"  # cadastrado
_CPF_B = "52998224725"  # válido, sem cadastro
_CPF_C = "12345678909"  # válido, sem cadastro
_EMAIL_A = "pessoa.a@example.invalid"


def _export(tmp_path: Path, files: dict[str, str]) -> str:
    d = tmp_path / "export"
    d.mkdir()
    manifest: dict[str, Any] = {"entities": {}}
    for name, content in files.items():
        (d / f"{name}.csv").write_text(content, encoding="utf-8")
        manifest["entities"][name] = {"file_csv": f"{name}.csv"}
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return str(d)


def _upload(tmp_path: Path, content: str) -> str:
    p = tmp_path / "equipe.csv"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _duas_vidas_ativas() -> tuple[Gerencia, Gerencia]:
    return (
        Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas"),
        Gerencia.objects.create(nome="GERENCIA 9", nome_setor="Vidas"),
    )


def _pessoa_a():
    return UsuarioFactory(cpf=_CPF_A, email=_EMAIL_A, first_name="Ana Maria", last_name="Souza")


# --- (A) gerência ---------------------------------------------------------------------------------------------


def test_nome_setor_repetido_entre_ativas_nao_escolhe():
    _duas_vidas_ativas()

    assert _resolve_gerencia("Vidas") is None
    assert _gerencia_da_linha("Vidas") == (None, "gerencia_ambigua")


def test_ativa_e_inativa_no_mesmo_degrau_nao_escolhem():
    """`nome_setor` repetido não escolhe, mesmo quando uma das duas está inativa: a regra antiga podia lotar na
    inativa, e a nova não pode trocar isso por um vínculo na ativa."""
    Gerencia.objects.create(nome="GERENCIA 1", nome_setor="Vidas", ativo=False)
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")

    assert _resolve_gerencia("Vidas") is None
    assert _gerencia_da_linha("Vidas") == (None, "gerencia_ambigua")


def test_duas_inativas_e_uma_ativa_no_mesmo_degrau_sao_ambiguas():
    Gerencia.objects.create(nome="GERENCIA 1", nome_setor="Vidas", ativo=False)
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas", ativo=False)
    Gerencia.objects.create(nome="GERENCIA 3", nome_setor="Vidas")

    assert _gerencia_da_linha("Vidas") == (None, "gerencia_ambigua")


def test_inativa_no_degrau_1_para_a_cadeia_antes_da_ativa_do_degrau_3():
    """A regra antiga parava na inativa do degrau 1 (`gerencia_inativa`); a ativa do degrau 3 (nome gerado) não
    pode passar a vencer, senão a carga liga uma lotação que antes não ligava."""
    inativa = Gerencia.objects.create(nome="GERENCIA 1", nome_setor="Vidas", ativo=False)
    Gerencia.objects.create(nome="GERENCIA VIDAS", nome_setor="Outro rótulo")

    assert _resolve_gerencia("Vidas") == inativa
    assert _gerencia_da_linha("Vidas") == (None, "gerencia_inativa")


def test_inativa_no_degrau_1_para_a_cadeia_antes_da_ativa_do_degrau_4():
    """Degrau 4 = `nome_setor` igual ao rótulo cru ("Brincando"), que o de-para leva a "Brincando e Aprendendo"."""
    inativa = Gerencia.objects.create(nome="GERENCIA 1", nome_setor="Brincando e Aprendendo", ativo=False)
    Gerencia.objects.create(nome="GERENCIA 7", nome_setor="Brincando")

    assert _resolve_gerencia("Brincando") == inativa
    assert _gerencia_da_linha("Brincando") == (None, "gerencia_inativa")


def test_export_contract_inativa_no_degrau_1_nao_lota_na_ativa_do_degrau_3(tmp_path):
    Gerencia.objects.create(nome="GERENCIA 1", nome_setor="Vidas", ativo=False)
    Gerencia.objects.create(nome="GERENCIA VIDAS", nome_setor="Outro rótulo")
    _pessoa_a()
    path = _export(tmp_path, {"equipe_gerencia": f"gerencia,usuario_cpf,papel\nVidas,{_CPF_A},COORDENADOR\n"})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert pe["would_reject"] == 1
    assert pe["reject_reasons"]["gerencia_inativa"] == 1

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()
    assert report["applied"]["equipe_gerencia"] == 0
    assert EquipeGerencia.objects.count() == 0


def test_upload_inativa_no_degrau_1_nao_lota_na_ativa_do_degrau_3(tmp_path):
    """O upload segue como antes (lota na inativa do degrau 1, que não dá direito); só não passa para a ativa."""
    inativa = Gerencia.objects.create(nome="GERENCIA 1", nome_setor="Vidas", ativo=False)
    ativa = Gerencia.objects.create(nome="GERENCIA VIDAS", nome_setor="Outro rótulo")
    _pessoa_a()
    path = _upload(tmp_path, f"setor,papel,usuario_cpf\nVidas,COORDENADOR,{_CPF_A}\n")

    import_equipe_gerencia_from_file(path=path, dry_run=False)

    assert not EquipeGerencia.objects.filter(gerencia=ativa).exists()
    assert list(EquipeGerencia.objects.values_list("gerencia_id", flat=True)) == [inativa.pk]


def test_ambiguidade_no_degrau_1_nao_cai_para_os_seguintes():
    _duas_vidas_ativas()
    Gerencia.objects.create(nome="GERENCIA VIDAS", nome_setor="Outro rótulo")

    assert _resolve_gerencia("Vidas") is None
    assert _gerencia_da_linha("Vidas") == (None, "gerencia_ambigua")


def test_so_inativa_continua_reportando_inativa():
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas", ativo=False)

    assert _gerencia_da_linha("Vidas") == (None, "gerencia_inativa")


def test_duas_inativas_reportam_inativa_sem_escolher():
    Gerencia.objects.create(nome="GERENCIA 1", nome_setor="Vidas", ativo=False)
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas", ativo=False)

    assert _resolve_gerencia("Vidas") is None
    assert _gerencia_da_linha("Vidas") == (None, "gerencia_inativa")


def test_classify_gerencia_com_setor_ambiguo_nao_quebra(tmp_path):
    _duas_vidas_ativas()
    path = _export(tmp_path, {"gerencia": "nome,nome_setor\nVidas,Vidas\n"})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["gerencia"]

    assert pe["would_reject"] == 1
    assert pe["reject_reasons"]["gerencia_ambigua"] == 1


def test_export_contract_setor_ambiguo_nao_grava_vinculo(tmp_path):
    _duas_vidas_ativas()
    _pessoa_a()
    path = _export(tmp_path, {"equipe_gerencia": f"gerencia,usuario_cpf,papel\nVidas,{_CPF_A},FORMADOR\n"})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert pe["would_reject"] == 1
    assert pe["reject_reasons"]["gerencia_ambigua"] == 1

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()
    assert report["applied"]["equipe_gerencia"] == 0
    assert EquipeGerencia.objects.count() == 0


def test_upload_setor_ambiguo_vira_pendencia(tmp_path):
    _duas_vidas_ativas()
    _pessoa_a()
    path = _upload(tmp_path, f"setor,papel,usuario_cpf\nVidas,FORMADOR,{_CPF_A}\n")

    result = import_equipe_gerencia_from_file(path=path, dry_run=False)

    assert len(result["pendencias"]["setor_missing"]) == 1
    assert EquipeGerencia.objects.count() == 0


# --- (B) pessoa -----------------------------------------------------------------------------------------------


def test_cpf_informado_sem_match_nao_cai_para_nome():
    _pessoa_a()

    assert _resolve_usuario(_CPF_B, "", "Ana Souza") is None


def test_cpf_informado_sem_match_nao_cai_para_email():
    _pessoa_a()

    assert _resolve_usuario(_CPF_B, _EMAIL_A, "") is None


def test_sem_cpf_continua_resolvendo_por_email_e_nome():
    a = _pessoa_a()

    assert _resolve_usuario("", _EMAIL_A, "") == a
    assert _resolve_usuario("", "", "Ana Souza") == a
    assert _resolve_usuario(_CPF_A, "", "") == a


def test_cpf_invalido_continua_caindo_para_email():
    """Só o CPF válido sem cadastro tira a pessoa (mesma regra do #2035): o dígito errado é erro de digitação."""
    a = _pessoa_a()

    assert _resolve_usuario("11144477700", _EMAIL_A, "") == a


def test_export_contract_cpf_sem_match_nao_lota_homonimo(tmp_path):
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
    _pessoa_a()
    path = _export(
        tmp_path,
        {"equipe_gerencia": f"gerencia,usuario_cpf,usuario_nome,papel\nVidas,{_CPF_B},Ana Souza,COORDENADOR\n"},
    )

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert pe["would_reject"] == 1
    assert pe["reject_reasons"]["cpf_sem_cadastro"] == 1
    assert pe["reject_reasons"]["usuario_nao_resolvido"] == 0

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()
    assert report["applied"]["equipe_gerencia"] == 0
    assert EquipeGerencia.objects.count() == 0


def test_export_contract_cpf_sem_cadastro_lista_a_conta_que_a_regra_antiga_lotaria(tmp_path):
    """CPF válido sem cadastro + e-mail (ou nome) de uma conta existente: a regra antiga lotava essa conta. A linha
    sai com `cpf_sem_cadastro` e a conta vai em `lotacao_perdida_contas` uma vez só, só como `u<id>` (o "quem
    perde" que o dono vê no ensaio), no dry-run e no relatório do apply."""
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
    a = _pessoa_a()
    path = _export(
        tmp_path,
        {
            "equipe_gerencia": (
                "gerencia,usuario_cpf,usuario_email,usuario_nome,papel\n"
                f"Vidas,{_CPF_B},{_EMAIL_A},,COORDENADOR\n"
                f"Vidas,{_CPF_C},,Ana Souza,FORMADOR\n"
            )
        },
    )

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert pe["would_reject"] == 2
    assert pe["reject_reasons"]["cpf_sem_cadastro"] == 2
    assert pe["reject_reasons"]["usuario_nao_resolvido"] == 0
    assert pe["lotacao_perdida_contas"] == [f"u{a.pk}"]

    report = ExportContractImporter(path=path, apply=True, allow=("equipe_gerencia",)).run()
    assert report["por_entidade"]["equipe_gerencia"]["lotacao_perdida_contas"] == [f"u{a.pk}"]
    assert report["applied"]["equipe_gerencia"] == 0
    assert EquipeGerencia.objects.count() == 0

    out = io.StringIO()
    call_command("import_export_contract", "--path", path, stdout=out)
    assert f"lotacao_perdida_contas=['u{a.pk}']" in out.getvalue()


def test_export_contract_cpf_sem_cadastro_sem_conta_pela_regra_antiga_nao_lista(tmp_path):
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
    _pessoa_a()
    path = _export(tmp_path, {"equipe_gerencia": f"gerencia,usuario_cpf,papel\nVidas,{_CPF_B},COORDENADOR\n"})

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert pe["reject_reasons"]["cpf_sem_cadastro"] == 1
    assert pe["lotacao_perdida_contas"] == []


def test_export_contract_sem_cpf_que_nao_casa_segue_usuario_nao_resolvido(tmp_path):
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
    _pessoa_a()
    path = _export(
        tmp_path,
        {
            "equipe_gerencia": (
                "gerencia,usuario_cpf,usuario_email,usuario_nome,papel\n"
                "Vidas,,ninguem@example.invalid,Fulano Inexistente,COORDENADOR\n"
            )
        },
    )

    pe = ExportContractImporter(path=path).run()["por_entidade"]["equipe_gerencia"]
    assert pe["would_reject"] == 1
    assert pe["reject_reasons"]["usuario_nao_resolvido"] == 1
    assert pe["reject_reasons"]["cpf_sem_cadastro"] == 0
    assert pe["lotacao_perdida_contas"] == []


def test_upload_cpf_sem_match_vira_usuario_not_found(tmp_path):
    Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")
    _pessoa_a()
    path = _upload(tmp_path, f"setor,papel,usuario_cpf,usuario_nome\nVidas,FORMADOR,{_CPF_B},Ana Souza\n")

    result = import_equipe_gerencia_from_file(path=path, dry_run=False)

    assert len(result["pendencias"]["usuario_not_found"]) == 1
    assert EquipeGerencia.objects.count() == 0
