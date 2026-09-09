"""
Reconcile v16→v20 (RELAY-40/41): corrige o que o create-only não conserta.

Este teste cobre os handlers DETERMINÍSTICOS de FAMÍLIA (catálogo):
- FAMILIA_CORRIGIDA: repontar Projeto.projeto_geral para a família declarada.
- FAMILIA_INEXISTENTE: deletar ProjetoGeral fantasma (guard: sem refs).

Disciplina: dry-run por padrão; --apply exige allowlist por classe; idempotente;
nunca chuta (skip+report quando ambíguo/não-encontrado).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportUnusedVariable=false

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from apps.core.models import Participation, Projeto, ProjetoGeral
from apps.core.services.export_contract_v20_reconciler import ExportContractV20Reconciler
from apps.core.tests.factories import MunicipioFactory, SolicitacaoFactory, UsuarioFactory

_FORTALEZA = ZoneInfo("America/Fortaleza")


def _inicio(y: int, m: int, d: int) -> datetime:
    """Datetime ao meio-dia Fortaleza (longe da fronteira de fuso) na data dada."""
    return datetime(y, m, d, 12, 0, tzinfo=_FORTALEZA)


RECONCILE_HEADER = ["classe", "entidade", "chave", "data", "municipio", "papel", "de", "para", "o_que_fazer"]


def _write_reconcile(base: Path, rows: list[dict[str, str]]) -> str:
    base.mkdir(parents=True, exist_ok=True)
    fp = base / "reconcile__v16_para_v20.csv"
    with open(fp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RECONCILE_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in RECONCILE_HEADER})
    return str(base)


@pytest.mark.django_db
class TestFamiliaCorrigida:
    """FAMILIA_CORRIGIDA: seta Projeto.projeto_geral para a família declarada (`para`)."""

    def test_apply_repoints_projeto_geral(self, tmp_path):
        pg_certo = ProjetoGeral.objects.create(nome="ED FINANCEIRA")
        pg_fantasma = ProjetoGeral.objects.create(nome="EDUCAÇÃO FINANCEIRA")
        proj = Projeto.objects.create(nome="EDUCAÇÃO FINANCEIRA LIVRO 1", projeto_geral=pg_fantasma)

        path = _write_reconcile(
            tmp_path / "recon",
            [
                {
                    "classe": "FAMILIA_CORRIGIDA",
                    "entidade": "projeto",
                    "chave": "EDUCAÇÃO FINANCEIRA LIVRO 1",
                    "de": "EDUCAÇÃO FINANCEIRA",
                    "para": "ED FINANCEIRA",
                    "o_que_fazer": "repontar a variante para a família que a DAT declara",
                }
            ],
        )

        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("FAMILIA_CORRIGIDA",)).run()

        proj.refresh_from_db()
        assert proj.projeto_geral_id == pg_certo.id
        assert rep["applied"]["FAMILIA_CORRIGIDA"] == 1

    def test_dry_run_does_not_write(self, tmp_path):
        pg_certo = ProjetoGeral.objects.create(nome="ED FINANCEIRA")
        pg_fantasma = ProjetoGeral.objects.create(nome="EDUCAÇÃO FINANCEIRA")
        proj = Projeto.objects.create(nome="EDUCAÇÃO FINANCEIRA LIVRO 1", projeto_geral=pg_fantasma)

        path = _write_reconcile(
            tmp_path / "recon",
            [
                {
                    "classe": "FAMILIA_CORRIGIDA",
                    "entidade": "projeto",
                    "chave": "EDUCAÇÃO FINANCEIRA LIVRO 1",
                    "para": "ED FINANCEIRA",
                }
            ],
        )

        rep = ExportContractV20Reconciler(path=path, apply=False).run()

        proj.refresh_from_db()
        assert proj.projeto_geral_id == pg_fantasma.id  # inalterado
        assert rep["would_apply"]["FAMILIA_CORRIGIDA"] == 1
        assert rep["applied"]["FAMILIA_CORRIGIDA"] == 0

    def test_sem_familia_seta_null(self, tmp_path):
        pg = ProjetoGeral.objects.create(nome="ESCREVER COMUNICAR E SER")
        proj = Projeto.objects.create(nome="ESCREVER, COMUNICAR E SER", projeto_geral=pg)

        path = _write_reconcile(
            tmp_path / "recon",
            [
                {
                    "classe": "FAMILIA_CORRIGIDA",
                    "entidade": "projeto",
                    "chave": "ESCREVER, COMUNICAR E SER",
                    "para": "(sem família)",
                }
            ],
        )

        ExportContractV20Reconciler(path=path, apply=True, allow=("FAMILIA_CORRIGIDA",)).run()

        proj.refresh_from_db()
        assert proj.projeto_geral_id is None

    def test_idempotente_noop_se_ja_certo(self, tmp_path):
        pg_certo = ProjetoGeral.objects.create(nome="ED FINANCEIRA")
        Projeto.objects.create(nome="EDUCAÇÃO FINANCEIRA LIVRO 1", projeto_geral=pg_certo)

        path = _write_reconcile(
            tmp_path / "recon",
            [
                {
                    "classe": "FAMILIA_CORRIGIDA",
                    "entidade": "projeto",
                    "chave": "EDUCAÇÃO FINANCEIRA LIVRO 1",
                    "para": "ED FINANCEIRA",
                }
            ],
        )

        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("FAMILIA_CORRIGIDA",)).run()
        assert rep["applied"]["FAMILIA_CORRIGIDA"] == 0
        assert rep["noop"]["FAMILIA_CORRIGIDA"] == 1

    def test_allowlist_gate_bloqueia_sem_permissao(self, tmp_path):
        pg_certo = ProjetoGeral.objects.create(nome="ED FINANCEIRA")
        pg_fantasma = ProjetoGeral.objects.create(nome="EDUCAÇÃO FINANCEIRA")
        proj = Projeto.objects.create(nome="EDUCAÇÃO FINANCEIRA LIVRO 1", projeto_geral=pg_fantasma)

        path = _write_reconcile(
            tmp_path / "recon",
            [
                {
                    "classe": "FAMILIA_CORRIGIDA",
                    "entidade": "projeto",
                    "chave": "EDUCAÇÃO FINANCEIRA LIVRO 1",
                    "para": "ED FINANCEIRA",
                }
            ],
        )

        # apply=True mas classe NÃO está no allow → não escreve (would_apply).
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=()).run()
        proj.refresh_from_db()
        assert proj.projeto_geral_id == pg_fantasma.id
        assert rep["would_apply"]["FAMILIA_CORRIGIDA"] == 1


@pytest.mark.django_db
class TestFamiliaInexistente:
    """FAMILIA_INEXISTENTE: deleta ProjetoGeral fantasma; guard: só se não houver refs."""

    def test_apply_deleta_pg_sem_filhos(self, tmp_path):
        ProjetoGeral.objects.create(nome="EDUCAÇÃO FINANCEIRA")

        path = _write_reconcile(
            tmp_path / "recon",
            [
                {
                    "classe": "FAMILIA_INEXISTENTE",
                    "entidade": "projeto_geral",
                    "chave": "EDUCAÇÃO FINANCEIRA",
                    "o_que_fazer": "família que eu inventei",
                }
            ],
        )

        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("FAMILIA_INEXISTENTE",)).run()
        assert not ProjetoGeral.objects.filter(nome="EDUCAÇÃO FINANCEIRA").exists()
        assert rep["applied"]["FAMILIA_INEXISTENTE"] == 1

    def test_guard_nao_deleta_pg_com_filho(self, tmp_path):
        pg = ProjetoGeral.objects.create(nome="EDUCAÇÃO FINANCEIRA")
        Projeto.objects.create(nome="ALGUM PROJETO", projeto_geral=pg)

        path = _write_reconcile(
            tmp_path / "recon",
            [{"classe": "FAMILIA_INEXISTENTE", "entidade": "projeto_geral", "chave": "EDUCAÇÃO FINANCEIRA"}],
        )

        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("FAMILIA_INEXISTENTE",)).run()
        assert ProjetoGeral.objects.filter(nome="EDUCAÇÃO FINANCEIRA").exists()  # NÃO deletado
        assert rep["skipped_has_refs"]["FAMILIA_INEXISTENTE"] == 1


@pytest.mark.django_db
class TestTrocaDeTitular:
    """TROCA_DE_TITULAR: reatribui Participation (caixa) de→para por external_hash. Determinístico."""

    def _row(self) -> dict[str, str]:
        return {
            "classe": "TROCA_DE_TITULAR",
            "entidade": "participation",
            "chave": "hash-abc",
            "papel": "CONVIDADO",
            "de": "11111111111",
            "para": "22222222222",
        }

    def test_reassign_por_hash(self, tmp_path):
        de = UsuarioFactory(username="11111111111")
        para = UsuarioFactory(username="22222222222")
        sol = SolicitacaoFactory(external_hash="hash-abc")
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.CONVIDADO)

        path = _write_reconcile(tmp_path / "r", [self._row()])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_TITULAR",)).run()

        p.refresh_from_db()
        assert p.usuario_id == para.id
        assert rep["applied"]["TROCA_DE_TITULAR"] == 1

    def test_idempotente_ja_no_para(self, tmp_path):
        UsuarioFactory(username="11111111111")
        para = UsuarioFactory(username="22222222222")
        sol = SolicitacaoFactory(external_hash="hash-abc")
        Participation.objects.create(solicitacao=sol, usuario=para, role=Participation.Role.CONVIDADO)

        path = _write_reconcile(tmp_path / "r", [self._row()])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_TITULAR",)).run()
        assert rep["noop"]["TROCA_DE_TITULAR"] == 1
        assert rep["applied"]["TROCA_DE_TITULAR"] == 0

    def test_hash_inexistente_skip(self, tmp_path):
        UsuarioFactory(username="11111111111")
        UsuarioFactory(username="22222222222")
        row = self._row()
        row["chave"] = "nao-existe"
        path = _write_reconcile(tmp_path / "r", [row])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_TITULAR",)).run()
        assert rep["skipped_not_found"]["TROCA_DE_TITULAR"] == 1

    def test_dry_run_nao_escreve(self, tmp_path):
        de = UsuarioFactory(username="11111111111")
        UsuarioFactory(username="22222222222")
        sol = SolicitacaoFactory(external_hash="hash-abc")
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.CONVIDADO)

        path = _write_reconcile(tmp_path / "r", [self._row()])
        rep = ExportContractV20Reconciler(path=path, apply=False).run()

        p.refresh_from_db()
        assert p.usuario_id == de.id
        assert rep["would_apply"]["TROCA_DE_TITULAR"] == 1


@pytest.mark.django_db
class TestTrocaDePessoa:
    """TROCA_DE_PESSOA: guarda estrita — casa por município+data+papel+de-CPF, exatamente-1."""

    def _row(self, **kw: str) -> dict[str, str]:
        base = {
            "classe": "TROCA_DE_PESSOA",
            "entidade": "solicitacao + participation",
            "municipio": "TAMANDARÉ - PE",
            "data": "2026-09-10",
            "papel": "coordenador",
            "de": "11111111111",
            "para": "22222222222",
            "o_que_fazer": "assumiu a coordenação",
        }
        base.update(kw)
        return base

    def test_reassign_coordenador(self, tmp_path):
        de = UsuarioFactory(username="11111111111")
        para = UsuarioFactory(username="22222222222")
        mun = MunicipioFactory(nome="TAMANDARÉ", uf="PE")
        sol = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10))
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.COORDENADOR)

        path = _write_reconcile(tmp_path / "r", [self._row()])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_PESSOA",)).run()

        p.refresh_from_db()
        assert p.usuario_id == para.id
        assert rep["applied"]["TROCA_DE_PESSOA"] == 1

    def test_vaga_formador_esvaziada_remove(self, tmp_path):
        de = UsuarioFactory(username="11111111111")
        mun = MunicipioFactory(nome="TAMANDARÉ", uf="PE")
        sol = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10))
        Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.FORMADOR)

        path = _write_reconcile(
            tmp_path / "r",
            [self._row(papel="formador", para="", o_que_fazer="vaga de formador esvaziada")],
        )
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_PESSOA",)).run()

        assert not Participation.objects.filter(solicitacao=sol, usuario=de, role=Participation.Role.FORMADOR).exists()
        assert rep["applied"]["TROCA_DE_PESSOA"] == 1

    def test_ambiguo_skip(self, tmp_path):
        de = UsuarioFactory(username="11111111111")
        UsuarioFactory(username="22222222222")
        mun = MunicipioFactory(nome="TAMANDARÉ", uf="PE")
        for _ in range(2):
            sol = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10))
            Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.COORDENADOR)

        path = _write_reconcile(tmp_path / "r", [self._row()])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_PESSOA",)).run()

        assert rep["skipped_ambiguous"]["TROCA_DE_PESSOA"] == 1
        assert rep["applied"]["TROCA_DE_PESSOA"] == 0

    def test_nao_encontrado_skip(self, tmp_path):
        UsuarioFactory(username="11111111111")
        UsuarioFactory(username="22222222222")
        MunicipioFactory(nome="TAMANDARÉ", uf="PE")  # sem solicitacao correspondente

        path = _write_reconcile(tmp_path / "r", [self._row()])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_PESSOA",)).run()

        assert rep["skipped_not_found"]["TROCA_DE_PESSOA"] == 1

    def test_dry_run_nao_escreve(self, tmp_path):
        de = UsuarioFactory(username="11111111111")
        UsuarioFactory(username="22222222222")
        mun = MunicipioFactory(nome="TAMANDARÉ", uf="PE")
        sol = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10))
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.COORDENADOR)

        path = _write_reconcile(tmp_path / "r", [self._row()])
        rep = ExportContractV20Reconciler(path=path, apply=False).run()

        p.refresh_from_db()
        assert p.usuario_id == de.id
        assert rep["would_apply"]["TROCA_DE_PESSOA"] == 1
