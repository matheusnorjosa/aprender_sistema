"""
Testes do cálculo de nr_codigos por linha de compra (contrato v5).

Ver serviço `apps/core/services/dat_codigos.py` e o plano do redesign.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

from django.test import TestCase

from apps.core.models import DATRegistro, ProjetoGeral
from apps.core.models.dat_compra import DATCompra
from apps.core.services.dat_codigos import calcular_nr_codigos, codigos_da_compra, recompute_registros
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory


def _compra(tipo, qtde, conta=True):
    """DATCompra NÃO salva — só o necessário para o cálculo puro."""
    return DATCompra(tipo=tipo, quantidade=qtde, conta_para_codigos=conta)


def _pg(tipo_calc, divisor=20, mult=Decimal("1.1")):
    return ProjetoGeral(tipo_calculo_codigos=tipo_calc, divisor_aluno=divisor, multiplicador_professor=mult)


class CodigosDaCompraTest(TestCase):
    """Função pura `codigos_da_compra` (objetos não-salvos; TestCase p/ o conftest RBAC)."""

    def test_conta_para_codigos_false_contribui_zero(self):
        """Invariante MARINGÁ: compra não-contável dá 0 mesmo com tipo/qtde que contariam."""
        pg = _pg("por_professor")
        self.assertEqual(codigos_da_compra(_compra("Professor", 100, conta=False), pg), 0)
        pg_a = _pg("por_aluno")
        self.assertEqual(codigos_da_compra(_compra("Aluno", 500, conta=False), pg_a), 0)

    def test_por_professor_decimal_sem_overshoot_de_float(self):
        """
        Adversarial: varre valores de quantidade — inclusive os que expõem o artefato
        IEEE-754 (`float(1.1)` faz `q*mult` cair acima do inteiro → ceil ingênuo +1).
        Propriedade: codigos == ceil(quantidade × Decimal(mult)).
        """
        pg = _pg("por_professor", mult=Decimal("1.1"))
        sujos = [50, 90, 100, 110, 170, 200, 340, 410, 450]  # float overshoot
        limpos = [10, 20, 30, 500]  # controle
        for q in sujos + limpos:
            with self.subTest(quantidade=q):
                esperado = int((Decimal(q) * Decimal("1.1")).to_integral_value(rounding=ROUND_CEILING))
                self.assertEqual(codigos_da_compra(_compra("Professor", q), pg), esperado)

    def test_por_aluno_ceil_nas_fronteiras(self):
        """por_aluno = ceil(quantidade / divisor). Fronteiras do divisor 20."""
        pg = _pg("por_aluno", divisor=20)
        casos = {19: 1, 20: 1, 21: 2, 39: 2, 40: 2, 41: 3, 735: 37}
        for q, esperado in casos.items():
            with self.subTest(quantidade=q):
                self.assertEqual(codigos_da_compra(_compra("Aluno", q), pg), esperado)

    def test_tipo_diferente_do_metodo_contribui_zero(self):
        """por_professor só conta Professor; por_aluno só conta Aluno."""
        self.assertEqual(codigos_da_compra(_compra("Aluno", 100), _pg("por_professor")), 0)
        self.assertEqual(codigos_da_compra(_compra("Professor", 100), _pg("por_aluno")), 0)

    def test_nao_aplicavel_contribui_zero(self):
        self.assertEqual(codigos_da_compra(_compra("Professor", 100), _pg("nao_aplicavel")), 0)

    def test_tipo_none_contribui_zero(self):
        """Compra sem tipo (linha seed antiga) não casa nenhum ramo."""
        self.assertEqual(codigos_da_compra(_compra(None, 100), _pg("por_professor")), 0)


class CalcularNrCodigosTest(TestCase):
    """`calcular_nr_codigos(registro)` — soma por compra, com DB."""

    @classmethod
    def setUpTestData(cls):
        cls.municipio = MunicipioFactory(nome="Test City", uf="CE")
        cls.user = UsuarioFactory(username="calc_user")
        cls.pg_prof = ProjetoGeral.objects.create(
            nome="PG Prof",
            usa_avaliar=False,
            tipo_calculo_codigos="por_professor",
            multiplicador_professor=Decimal("1.1"),
        )
        cls.pg_na = ProjetoGeral.objects.create(
            nome="PG NA",
            usa_avaliar=False,
            tipo_calculo_codigos="nao_aplicavel",
        )
        cls.projeto = ProjetoFactory(nome="NOVO LENDO 1", codigo="NL1", fluxo="NAO_SUPER", projeto_geral=cls.pg_prof)

    def _registro(self, projeto, pg, aluno=None, prof=None, ano=None):
        return DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=pg,
            projeto=projeto,
            aluno_qtde=aluno,
            professor_qtde=prof,
            ano=ano,
            created_by=self.user,
        )

    def _compra_db(self, projeto, tipo, qtde, conta=True, ano=2026):
        return DATCompra.objects.create(
            municipio=self.municipio,
            projeto=projeto,
            tipo=tipo,
            quantidade=qtde,
            conta_para_codigos=conta,
            ano_uso=ano,
            created_by=self.user,
        )

    def test_conta_so_o_ano_do_registro(self):
        """Cohort anual: registro de 2026 conta só as compras ano_uso=2026, não as de 2027."""
        reg = self._registro(self.projeto, self.pg_prof, prof=20, ano=2026)
        self._compra_db(self.projeto, "Professor", 20, ano=2026)  # ceil(22.0) = 22
        self._compra_db(self.projeto, "Professor", 100, ano=2027)  # outro ano → não conta
        self.assertEqual(calcular_nr_codigos(reg), 22)

    def test_ano_nulo_soma_todos_os_anos(self):
        """Transição (ano=NULL): mantém o comportamento antigo, somando todos os anos."""
        reg = self._registro(self.projeto, self.pg_prof, prof=20, ano=None)
        self._compra_db(self.projeto, "Professor", 20, ano=2026)  # 22
        self._compra_db(self.projeto, "Professor", 20, ano=2027)  # 22
        self.assertEqual(calcular_nr_codigos(reg), 44)

    def test_soma_arredonda_cada_compra_nao_o_agregado(self):
        """O caso 41+11 do REGRA-10: per-compra = 46+13 = 59 (NÃO ceil(52×1.1)=58)."""
        reg = self._registro(self.projeto, self.pg_prof, prof=52)
        self._compra_db(self.projeto, "Professor", 41)
        self._compra_db(self.projeto, "Professor", 11)
        self.assertEqual(calcular_nr_codigos(reg), 59)
        self.assertNotEqual(calcular_nr_codigos(reg), 58)

    def test_conta_para_codigos_false_excluida(self):
        """Compra não-contável não entra na soma (cenário GESTÃO ESCOLAR/MARINGÁ)."""
        reg = self._registro(self.projeto, self.pg_prof, prof=10)
        self._compra_db(self.projeto, "Professor", 10, conta=True)  # ceil(11.0)=11
        self._compra_db(self.projeto, "Professor", 500, conta=False)  # excluída
        self.assertEqual(calcular_nr_codigos(reg), 11)

    def test_registro_sem_compras_da_zero(self):
        reg = self._registro(self.projeto, self.pg_prof, prof=10)
        self.assertEqual(calcular_nr_codigos(reg), 0)

    def test_nao_aplicavel_da_none(self):
        proj_na = ProjetoFactory(nome="NA proj", codigo="NAP", fluxo="NAO_SUPER", projeto_geral=self.pg_na)
        reg = self._registro(proj_na, self.pg_na)
        self.assertIsNone(calcular_nr_codigos(reg))

    def test_compra_inativa_nao_conta(self):
        reg = self._registro(self.projeto, self.pg_prof, prof=10)
        c = self._compra_db(self.projeto, "Professor", 10)
        c.ativo = False
        c.save()
        self.assertEqual(calcular_nr_codigos(reg), 0)


class RecomputeRegistrosTest(TestCase):
    """`recompute_registros` — usado pelo importer, viewset e command."""

    @classmethod
    def setUpTestData(cls):
        cls.municipio = MunicipioFactory(nome="Recompute City", uf="CE")
        cls.user = UsuarioFactory(username="recompute_user")
        cls.pg = ProjetoGeral.objects.create(
            nome="PG Recompute",
            usa_avaliar=False,
            tipo_calculo_codigos="por_professor",
            multiplicador_professor=Decimal("1.1"),
        )
        cls.projeto = ProjetoFactory(nome="REC 1", codigo="REC1", fluxo="NAO_SUPER", projeto_geral=cls.pg)

    def test_recompute_atualiza_apos_compra(self):
        """Registro criado sem compras (nr_codigos 0); ao surgir compra, recompute atualiza."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.pg,
            projeto=self.projeto,
            professor_qtde=100,
            created_by=self.user,
        )
        self.assertEqual(reg.nr_codigos, 0)
        DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            tipo="Professor",
            quantidade=100,
            ano_uso=2026,
            created_by=self.user,
        )
        n = recompute_registros(self.municipio.id, self.projeto.id)
        reg.refresh_from_db()
        self.assertEqual(n, 1)
        self.assertEqual(reg.nr_codigos, 110)  # ceil(100 × 1.1) Decimal
