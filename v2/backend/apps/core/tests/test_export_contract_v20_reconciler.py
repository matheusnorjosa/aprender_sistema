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


RECONCILE_HEADER = [
    "classe",
    "entidade",
    "chave",
    "data",
    "municipio",
    "papel",
    "de",
    "para",
    "o_que_fazer",
    # colunas v24 (RELAY-43): identidade determinística. Vazias nas linhas v20 → fallback.
    "evento_id",
    "de_cpf",
    "para_cpf",
    "de_usuario_origem",
    # colunas v25 (RELAY-45/46): chave por e-mail + desambiguação de posto-em-sucessão.
    "para_email",
    "de_email",
    "email_desambigua",
]


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

    def test_v24_reassign_por_evento_id_e_cpf(self, tmp_path):
        """v24: casa por evento_id (external_hash) + de_cpf/para_cpf (não `chave`/`de`/`para`)."""
        de = UsuarioFactory(username="11111111111")
        para = UsuarioFactory(username="22222222222")
        sol = SolicitacaoFactory(external_hash="EV0777")
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.CONVIDADO)

        row = {
            "classe": "TROCA_DE_TITULAR",
            "entidade": "participation",
            "evento_id": "EV0777",
            "papel": "CONVIDADO",
            "de": "Fulano De Tal",
            "para": "Beltrano De Tal",
            "de_cpf": "11111111111",
            "para_cpf": "22222222222",
        }
        path = _write_reconcile(tmp_path / "r", [row])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_TITULAR",)).run()

        p.refresh_from_db()
        assert p.usuario_id == para.id
        assert rep["applied"]["TROCA_DE_TITULAR"] == 1

    def test_v24_caixa_por_guest_email(self, tmp_path):
        """v24: a caixa está gravada como guest_email; `de_usuario_origem` a localiza; vira usuario=para."""
        para = UsuarioFactory(username="22222222222")
        sol = SolicitacaoFactory(external_hash="EV0888")
        p = Participation.objects.create(
            solicitacao=sol, guest_email="coordenacao21@x.org", role=Participation.Role.CONVIDADO
        )

        row = {
            "classe": "TROCA_DE_TITULAR",
            "entidade": "participation",
            "evento_id": "EV0888",
            "papel": "CONVIDADO",
            "de": "Caixa Coordenacao",
            "para": "Beltrano De Tal",
            "para_cpf": "22222222222",
            "de_usuario_origem": "coordenacao21@x.org",
        }
        path = _write_reconcile(tmp_path / "r", [row])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_TITULAR",)).run()

        p.refresh_from_db()
        assert p.usuario_id == para.id
        assert p.guest_email in (None, "")
        assert rep["applied"]["TROCA_DE_TITULAR"] == 1

    def test_v25_para_por_cpf_quando_nao_mesma_caixa(self, tmp_path):
        """v25: email_desambigua=NAO_mesma_caixa (posto em sucessão, ex.: coordenacao21@ Elienai→Diogo)
        → resolve `para` por `para_cpf`, NUNCA por e-mail (o e-mail resolveria o posto = pessoa errada)."""
        de = UsuarioFactory(username="11111111111")
        diogo = UsuarioFactory(username="22222222222", email="")
        UsuarioFactory(username="99999999999", email="coordenacao21@x.org")  # decoy: o posto/e-mail
        sol = SolicitacaoFactory(external_hash="EV0999")
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.CONVIDADO)

        row = {
            "classe": "TROCA_DE_TITULAR",
            "entidade": "participation",
            "evento_id": "EV0999",
            "papel": "CONVIDADO",
            "de": "Elienai",
            "para": "Diogo",
            "de_cpf": "11111111111",
            "para_cpf": "22222222222",
            "para_email": "coordenacao21@x.org",
            "email_desambigua": "NAO_mesma_caixa",
        }
        path = _write_reconcile(tmp_path / "r", [row])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_TITULAR",)).run()

        p.refresh_from_db()
        assert p.usuario_id == diogo.id  # via para_cpf, NÃO o decoy do e-mail
        assert rep["applied"]["TROCA_DE_TITULAR"] == 1


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

    def test_v24_evento_id_desambigua(self, tmp_path):
        """v24: 2 eventos no MESMO município+data (ambíguo no lookup v20) — evento_id resolve
        exatamente-1, então aplica na participação certa e deixa a outra intacta."""
        de = UsuarioFactory(username="11111111111")
        para = UsuarioFactory(username="22222222222")
        mun = MunicipioFactory(nome="TAMANDARÉ", uf="PE")
        sol_a = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10), external_hash="EV-A")
        sol_b = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10), external_hash="EV-B")
        pa = Participation.objects.create(solicitacao=sol_a, usuario=de, role=Participation.Role.COORDENADOR)
        pb = Participation.objects.create(solicitacao=sol_b, usuario=de, role=Participation.Role.COORDENADOR)

        row = self._row(evento_id="EV-A", de_cpf="11111111111", para_cpf="22222222222")
        path = _write_reconcile(tmp_path / "r", [row])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_PESSOA",)).run()

        pa.refresh_from_db()
        pb.refresh_from_db()
        assert pa.usuario_id == para.id  # o evento apontado foi reatribuído
        assert pb.usuario_id == de.id  # o outro (mesmo município+data) ficou intacto
        assert rep["applied"]["TROCA_DE_PESSOA"] == 1
        assert rep["skipped_ambiguous"]["TROCA_DE_PESSOA"] == 0

    def test_v25_para_por_email_quando_sim(self, tmp_path):
        """v25: email_desambigua=sim → resolve `para` por para_email (o prod indexa coordenador por
        e-mail; o para_cpf 'correto' pode não bater com o username/cpf do prod). de por de_cpf."""
        de = UsuarioFactory(username="11111111111")
        para = UsuarioFactory(username="00000000000", email="novo.coord@x.org")  # username != para_cpf
        mun = MunicipioFactory(nome="TAMANDARÉ", uf="PE")
        sol = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10), external_hash="EVP01")
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.COORDENADOR)

        row = self._row(
            evento_id="EVP01",
            de_cpf="11111111111",
            para_cpf="22222222222",  # NÃO resolve (ninguém com esse cpf/username)
            para_email="novo.coord@x.org",
            email_desambigua="sim",
        )
        path = _write_reconcile(tmp_path / "r", [row])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_PESSOA",)).run()

        p.refresh_from_db()
        assert p.usuario_id == para.id  # resolvido por e-mail, não por cpf
        assert rep["applied"]["TROCA_DE_PESSOA"] == 1

    def test_v25_email_compartilhado_cai_no_cpf(self, tmp_path):
        """v25 guard: e-mail que resolve >1 Usuario (posto compartilhado) → _usuario_by_email=None
        (nunca chuta) → cai no para_cpf."""
        de = UsuarioFactory(username="11111111111")
        para = UsuarioFactory(username="22222222222", email="")
        UsuarioFactory(username="33333333333", email="posto@x.org")
        UsuarioFactory(username="44444444444", email="posto@x.org")  # 2 no mesmo e-mail
        mun = MunicipioFactory(nome="TAMANDARÉ", uf="PE")
        sol = SolicitacaoFactory(municipio=mun, inicio=_inicio(2026, 9, 10), external_hash="EVP02")
        p = Participation.objects.create(solicitacao=sol, usuario=de, role=Participation.Role.COORDENADOR)

        row = self._row(
            evento_id="EVP02",
            de_cpf="11111111111",
            para_cpf="22222222222",
            para_email="posto@x.org",
            email_desambigua="sim",
        )
        path = _write_reconcile(tmp_path / "r", [row])
        rep = ExportContractV20Reconciler(path=path, apply=True, allow=("TROCA_DE_PESSOA",)).run()

        p.refresh_from_db()
        assert p.usuario_id == para.id  # e-mail ambíguo → guard → para_cpf
        assert rep["applied"]["TROCA_DE_PESSOA"] == 1
