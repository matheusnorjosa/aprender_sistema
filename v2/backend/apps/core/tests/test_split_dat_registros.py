"""
Testes do split per-year de DATRegistro (serviço `split_dat_registros` + command
`split_dat_registros_por_ano`). Deriva um registro por ano de uso a partir das compras.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportOptionalMemberAccess=false

from __future__ import annotations

from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from apps.core.models import DATRegistro, ProjetoGeral
from apps.core.models.dat_compra import DATCompra
from apps.core.services.dat_registro_split import split_dat_registros
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory


class SplitDatRegistrosTest(TestCase):
    """`split_dat_registros` — fan-out de um registro flat em um por ano de uso das compras."""

    @classmethod
    def setUpTestData(cls):
        cls.municipio = MunicipioFactory(nome="Split City", uf="CE")
        cls.user = UsuarioFactory(username="split_user")
        cls.pg = ProjetoGeral.objects.create(
            nome="PG Split",
            usa_avaliar=False,
            tipo_calculo_codigos="por_professor",
            multiplicador_professor=Decimal("1.1"),
        )
        cls.projeto = ProjetoFactory(nome="SPLIT 1", codigo="SPL1", fluxo="NAO_SUPER", projeto_geral=cls.pg)

    def _flat(self, ano=None, aluno=None, prof=None):
        return DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.pg,
            projeto=self.projeto,
            ano=ano,
            aluno_qtde=aluno,
            professor_qtde=prof,
            created_by=self.user,
        )

    def _compra(self, qtde, ano, tipo="Professor", conta=True):
        return DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            tipo=tipo,
            quantidade=qtde,
            conta_para_codigos=conta,
            ano_uso=ano,
            created_by=self.user,
        )

    def _regs(self):
        return {r.ano: r for r in DATRegistro.objects.filter(municipio=self.municipio, projeto=self.projeto)}

    def test_cria_um_registro_por_ano(self):
        """Flat + compras 2026 e 2027 → dois registros, cada um com o nr_codigos do SEU ano."""
        self._flat(prof=40)
        self._compra(20, 2026)  # ceil(20×1.1)=22
        self._compra(100, 2027)  # ceil(100×1.1)=110
        split_dat_registros()
        regs = self._regs()
        self.assertEqual(set(regs), {2026, 2027})
        self.assertEqual(regs[2026].nr_codigos, 22)
        self.assertEqual(regs[2027].nr_codigos, 110)

    def test_bucket_pendente_para_nao_classificado(self):
        """Compras 2026 + NÃO_CLASSIFICADO (ano_uso=None) → registro 2026 + pendente(None)."""
        self._flat(prof=20)
        self._compra(20, 2026)  # 22
        self._compra(50, None)  # ceil(50×1.1)=55 no bucket pendente
        split_dat_registros()
        regs = self._regs()
        self.assertEqual(set(regs), {2026, None})
        self.assertEqual(regs[2026].nr_codigos, 22)
        self.assertEqual(regs[None].nr_codigos, 55)

    def test_idempotente(self):
        """Rodar duas vezes não duplica nem cria de novo."""
        self._flat(prof=20)
        self._compra(20, 2026)
        self._compra(20, 2027)
        split_dat_registros()
        n1 = DATRegistro.objects.filter(municipio=self.municipio, projeto=self.projeto).count()
        r2 = split_dat_registros()
        n2 = DATRegistro.objects.filter(municipio=self.municipio, projeto=self.projeto).count()
        self.assertEqual(n1, n2)
        self.assertEqual(r2["criados"], 0)

    def test_preserva_atributos_no_primario(self):
        """Os atributos do flat (aluno/professor) ficam no ano primário (2026); outros anos = None."""
        self._flat(aluno=100, prof=40)
        self._compra(20, 2026)
        self._compra(20, 2027)
        split_dat_registros()
        regs = self._regs()
        self.assertEqual((regs[2026].aluno_qtde, regs[2026].professor_qtde), (100, 40))
        self.assertEqual((regs[2027].aluno_qtde, regs[2027].professor_qtde), (None, None))

    def test_registro_sem_compras_intocado(self):
        """Registro sem nenhuma compra fica como está (não vira pendente nem some)."""
        reg = self._flat(ano=2026, prof=10)
        split_dat_registros()
        self.assertEqual(DATRegistro.objects.filter(municipio=self.municipio, projeto=self.projeto).count(), 1)
        reg.refresh_from_db()
        self.assertEqual(reg.ano, 2026)

    def test_compra_sem_registro_reportada(self):
        """Compra para um par SEM registro (anomalia de origem: planilha dat_registro não tem a
        linha) não é splitada nem inventada — é reportada em `compras_sem_registro`."""
        outro = ProjetoFactory(nome="SPLIT 2", codigo="SPL2", fluxo="NAO_SUPER", projeto_geral=self.pg)
        DATCompra.objects.create(
            municipio=self.municipio,
            projeto=outro,
            tipo="Professor",
            quantidade=20,
            conta_para_codigos=True,
            ano_uso=2026,
            created_by=self.user,
        )
        res = split_dat_registros()  # nenhum DATRegistro para (municipio, outro)
        self.assertEqual(res["compras_sem_registro"], 1)
        self.assertEqual(DATRegistro.objects.filter(municipio=self.municipio, projeto=outro).count(), 0)

    def test_dry_run_nao_grava(self):
        """--dry-run reporta o que faria mas não cria nada."""
        self._flat(prof=20)
        self._compra(20, 2026)
        self._compra(20, 2027)
        res = split_dat_registros(dry_run=True)
        self.assertEqual(res["criados"], 1)
        self.assertEqual(DATRegistro.objects.filter(municipio=self.municipio, projeto=self.projeto).count(), 1)

    def test_command_roda(self):
        """O command envelopa o serviço e grava (smoke de integração)."""
        self._flat(prof=20)
        self._compra(20, 2026)
        self._compra(20, 2027)
        call_command("split_dat_registros_por_ano")
        self.assertEqual(set(self._regs()), {2026, 2027})
