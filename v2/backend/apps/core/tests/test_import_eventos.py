"""
Testes para importacao de Eventos (Solicitacao + Participation).

Cobertura:
- Service: import_eventos_from_file()
- View: ImportEventosView
- RBAC: Permissoes HasPerm("import_spreadsheet")
- Idempotencia: Nao duplica registros
- Regras PA: Status baseado em projeto.fluxo
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false

import io
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation, Solicitacao
from apps.core.services.eventos_import import import_eventos_from_file
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

_TZ_FORTALEZA = ZoneInfo("America/Fortaleza")


def _aware_fortaleza(d: date, hh: int, mm: int = 0) -> datetime:
    """datetime timezone-aware em Fortaleza (mesmo fuso que o importer usa)."""
    return timezone.make_aware(datetime.combine(d, time(hh, mm)), _TZ_FORTALEZA)


def _write_csv(content: str) -> str:
    """Escreve um CSV temporario e devolve o caminho (cleanup no proprio teste/gc)."""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    return temp.name


# URL direta (evita problemas de cache de rotas no container)
IMPORT_EVENTOS_URL = "/api/solicitacoes/import/"


@pytest.fixture
def dat_import_user(db):
    """Usuario do grupo DAT (PR-A1 DAT-Imports: detentor de import_spreadsheet)."""
    return UsuarioFactory(
        username="dat_import_user",
        email="dat_imports@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="DAT",
        last_name="Imports",
        groups=["DAT"],
    )


@pytest.fixture
def formador_user(db):
    """Usuario do grupo Formador (sem permissao de import)."""
    return UsuarioFactory(
        username="formador_user",
        email="formador@test.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Formador",
        last_name="User",
        groups=["Formador"],
    )


@pytest.fixture
def coordenador_user(db):
    """Usuario que sera coordenador dos eventos."""
    return UsuarioFactory(
        username="coord_user",
        email="coord@test.com",
        password="testpass123",
        cpf="33333333333",
        first_name="Coordenador",
        last_name="Teste",
    )


@pytest.fixture
def formador1_user(db):
    """Usuario que sera formador 1."""
    return UsuarioFactory(
        username="formador1",
        email="formador1@test.com",
        password="testpass123",
        cpf="44444444444",
        first_name="Formador",
        last_name="Um",
    )


@pytest.fixture
def municipio(db):
    """Municipio para os eventos."""
    return MunicipioFactory(
        nome="Fortaleza",
        uf="CE",
    )


@pytest.fixture
def projeto_super(db):
    """Projeto com fluxo SUPER (requer aprovacao)."""
    return ProjetoFactory(
        nome="Projeto Super",
        fluxo="SUPER",
    )


@pytest.fixture
def projeto_nao_super(db):
    """Projeto com fluxo NAO_SUPER (auto-aprovado)."""
    return ProjetoFactory(
        nome="Projeto Nao Super",
        fluxo="NAO_SUPER",
    )


@pytest.fixture
def tipo_evento(db):
    """Tipo de evento para os eventos."""
    return TipoEventoFactory(
        nome="Formacao",
    )


@pytest.fixture
def api_client():
    """Cliente API."""
    return APIClient()


@pytest.fixture
def sample_csv(coordenador_user, municipio, projeto_super, tipo_evento):
    """Cria arquivo CSV de teste com cleanup automatico."""
    d1 = (date.today() + timedelta(days=30)).isoformat()
    d2 = (date.today() + timedelta(days=31)).isoformat()
    content = f"""municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,encontro,segmento,local
{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d1},08:00,12:00,{coordenador_user.email},EF1,Fundamental I,Escola Municipal
{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d2},14:00,18:00,{coordenador_user.first_name} {coordenador_user.last_name},EF2,Fundamental II,Escola Estadual
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    # Cleanup
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_same_slot_diff_segmento(coordenador_user, municipio, projeto_super, tipo_evento):
    """#1915: dois eventos no MESMO slot (municipio/projeto/tipo/data/hora), diferindo
    SO no segmento. Sao eventos DISTINTOS (turmas diferentes) e devem virar 2 Solicitacoes."""
    d1 = (date.today() + timedelta(days=45)).isoformat()
    content = f"""municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,segmento
{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d1},08:00,12:00,{coordenador_user.email},Fundamental I
{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d1},08:00,12:00,{coordenador_user.email},Fundamental II
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_with_formadores(coordenador_user, formador1_user, municipio, projeto_super, tipo_evento):
    """CSV com formadores."""
    d1 = (date.today() + timedelta(days=35)).isoformat()
    content = f"""municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,formador1
{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d1},09:00,13:00,{coordenador_user.email},{formador1_user.email}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_nao_super(coordenador_user, municipio, projeto_nao_super, tipo_evento):
    """CSV com projeto NAO_SUPER (deve ser auto-aprovado)."""
    d1 = (date.today() + timedelta(days=40)).isoformat()
    content = f"""municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador
{municipio.nome},{projeto_nao_super.nome},{tipo_evento.nome},{d1},10:00,14:00,{coordenador_user.email}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_super_passado(coordenador_user, municipio, projeto_super, tipo_evento):
    """CSV com projeto SUPER e data PASSADA (PA-01: deve permanecer pendente)."""
    d_passado = (date.today() - timedelta(days=30)).isoformat()
    content = f"""municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador
{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d_passado},08:00,12:00,{coordenador_user.email}
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_csv_invalid_municipio():
    """CSV com municipio inexistente."""
    content = """municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador
Municipio Inexistente,Projeto X,Formacao,2026-03-01,08:00,12:00,coord@test.com
"""
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


# =============================================================================
# TESTES DO SERVICE
# =============================================================================


@pytest.mark.django_db
class TestEventosImportService:
    """Testes do service import_eventos_from_file."""

    def test_dry_run_returns_stats(self, sample_csv, coordenador_user, municipio, projeto_super, tipo_evento):
        """dry_run=True retorna stats sem persistir."""
        result = import_eventos_from_file(path=sample_csv, dry_run=True)

        assert result["dry_run"] is True
        assert result["stats"]["solicitacoes"]["created"] == 2
        assert result["stats"]["solicitacoes"]["unchanged"] == 0

        # Nao deve ter criado no banco
        assert Solicitacao.objects.count() == 0

    def test_apply_creates_records(self, sample_csv, coordenador_user, municipio, projeto_super, tipo_evento):
        """dry_run=False persiste os registros."""
        result = import_eventos_from_file(path=sample_csv, dry_run=False)

        assert result["dry_run"] is False
        assert result["stats"]["solicitacoes"]["created"] == 2

        # Deve ter criado no banco
        assert Solicitacao.objects.count() == 2

        # Verificar dados
        solicitacoes = Solicitacao.objects.all().order_by("inicio")
        assert solicitacoes[0].municipio == municipio
        assert solicitacoes[0].projeto == projeto_super
        assert solicitacoes[0].coordenador == coordenador_user

    def test_idempotency_no_duplicates(self, sample_csv, coordenador_user, municipio, projeto_super, tipo_evento):
        """Rodar 2x nao duplica registros."""
        # Primeira execucao
        result1 = import_eventos_from_file(path=sample_csv, dry_run=False)
        assert result1["stats"]["solicitacoes"]["created"] == 2

        # Segunda execucao
        result2 = import_eventos_from_file(path=sample_csv, dry_run=False)
        assert result2["stats"]["solicitacoes"]["created"] == 0
        assert result2["stats"]["solicitacoes"]["unchanged"] == 2

        # Total no banco
        assert Solicitacao.objects.count() == 2

    def test_same_slot_different_segmento_creates_two(
        self, sample_csv_same_slot_diff_segmento, coordenador_user, municipio, projeto_super, tipo_evento
    ):
        """#1915: dois eventos no mesmo slot que so diferem no segmento NAO podem colapsar.

        Antes do fix o external_hash omitia o segmento -> hash identico -> update_or_create
        sobrescrevia o primeiro (perda silenciosa, contada como 'unchanged'). Cada segmento e
        uma turma distinta: devem coexistir como 2 Solicitacoes.
        """
        result = import_eventos_from_file(path=sample_csv_same_slot_diff_segmento, dry_run=False)

        assert result["stats"]["solicitacoes"]["created"] == 2
        assert Solicitacao.objects.count() == 2
        segmentos = set(Solicitacao.objects.values_list("segmento", flat=True))
        assert segmentos == {"Fundamental I", "Fundamental II"}

    def test_creates_participations(
        self, sample_csv_with_formadores, coordenador_user, formador1_user, municipio, projeto_super, tipo_evento
    ):
        """Cria Participations para coordenador e formadores."""
        result = import_eventos_from_file(path=sample_csv_with_formadores, dry_run=False)

        assert result["stats"]["participations"]["created"] >= 2  # Coord + Formador

        # Verificar participations
        solicitacao = Solicitacao.objects.first()
        participations = Participation.objects.filter(solicitacao=solicitacao)

        assert participations.filter(usuario=coordenador_user, role="COORDENADOR").exists()
        assert participations.filter(usuario=formador1_user, role="FORMADOR").exists()

    def test_projeto_super_status_pendente(self, sample_csv, coordenador_user, municipio, projeto_super, tipo_evento):
        """Projeto SUPER com data futura deve ter status pendente."""
        result = import_eventos_from_file(path=sample_csv, dry_run=False)

        assert result["stats"]["solicitacoes"]["created"] == 2

        # Verificar status
        solicitacoes = Solicitacao.objects.all()
        for sol in solicitacoes:
            assert sol.status == "pendente"

    def test_projeto_super_passado_status_pendente(
        self, sample_csv_super_passado, coordenador_user, municipio, projeto_super, tipo_evento
    ):
        """PA-01: projeto SUPER com data PASSADA NUNCA auto-aprova — deve ficar pendente.

        Regressao do bug latente: o importer decidia status por data (passado -> aprovado)
        ANTES de checar o fluxo, auto-aprovando eventos SUPER historicos. A regra correta
        (resolve_initial_status) ignora a data: SUPER sempre nasce pendente.
        """
        result = import_eventos_from_file(path=sample_csv_super_passado, dry_run=False)

        assert result["stats"]["solicitacoes"]["created"] == 1

        solicitacao = Solicitacao.objects.first()
        assert solicitacao is not None
        assert solicitacao.status == "pendente"

    def test_projeto_nao_super_status_aprovado(
        self, sample_csv_nao_super, coordenador_user, municipio, projeto_nao_super, tipo_evento
    ):
        """Projeto NAO_SUPER deve ter status aprovado."""
        result = import_eventos_from_file(path=sample_csv_nao_super, dry_run=False)

        assert result["stats"]["solicitacoes"]["created"] == 1

        # Verificar status
        solicitacao = Solicitacao.objects.first()
        assert solicitacao is not None
        assert solicitacao.status == "aprovado"

    def test_invalid_municipio_adds_pendencia(self, sample_csv_invalid_municipio):
        """Municipio inexistente adiciona pendencia."""
        result = import_eventos_from_file(path=sample_csv_invalid_municipio, dry_run=True)

        assert result["stats"]["skipped"]["municipio"] == 1
        assert len(result["pendencias"]["municipios"]) == 1
        assert result["pendencias"]["municipios"][0]["nome"] == "Municipio Inexistente"

    def test_invalid_dates_adds_pendencia(self, coordenador_user, municipio, projeto_super, tipo_evento):
        """Datas invalidas adicionam pendencia."""
        content = f"""municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador
{municipio.nome},{projeto_super.nome},{tipo_evento.nome},invalido,08:00,12:00,{coordenador_user.email}
"""
        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        temp.write(content)
        temp.close()

        result = import_eventos_from_file(path=temp.name, dry_run=True)

        assert result["stats"]["skipped"]["dates"] == 1
        assert len(result["pendencias"]["dates"]) == 1

        Path(temp.name).unlink()


# =============================================================================
# TESTES DA VIEW
# =============================================================================


@pytest.mark.django_db
class TestImportEventosView:
    """Testes da view ImportEventosView."""

    def test_permission_denied_for_formador(self, api_client, formador_user, sample_csv):
        """Formador nao tem permissao (403)."""
        api_client.force_authenticate(user=formador_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_EVENTOS_URL,
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dat_import_user_can_import(
        self, api_client, dat_import_user, sample_csv, coordenador_user, municipio, projeto_super, tipo_evento
    ):
        """Usuario Controle pode importar."""
        api_client.force_authenticate(user=dat_import_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_EVENTOS_URL + "?dry_run=true",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is True
        assert response.data["stats"]["solicitacoes"]["created"] == 2

    def test_apply_mode_persists(
        self, api_client, dat_import_user, sample_csv, coordenador_user, municipio, projeto_super, tipo_evento
    ):
        """dry_run=false persiste os dados."""
        api_client.force_authenticate(user=dat_import_user)

        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_EVENTOS_URL + "?dry_run=false",
                {"file": f},
                format="multipart",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["dry_run"] is False
        assert Solicitacao.objects.count() == 2

    def test_missing_file_returns_400(self, api_client, dat_import_user):
        """Arquivo ausente retorna 400."""
        api_client.force_authenticate(user=dat_import_user)

        response = api_client.post(
            IMPORT_EVENTOS_URL,
            {},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data["detail"].lower()

    def test_invalid_mime_type_returns_400(self, api_client, dat_import_user):
        """Tipo de arquivo invalido retorna 400."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        api_client.force_authenticate(user=dat_import_user)

        # Usar MIME type explicitamente inválido (não text/plain, pois CSVs podem ser text/plain)
        fake_file = SimpleUploadedFile("malicious.exe", b"MZ\x90\x00", content_type="application/x-msdownload")

        response = api_client.post(
            IMPORT_EVENTOS_URL,
            {"file": fake_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "tipo" in response.data["detail"].lower() or "permitido" in response.data["detail"].lower()

    def test_unauthenticated_returns_401(self, api_client, sample_csv):
        """Usuario nao autenticado retorna 401."""
        with open(sample_csv, "rb") as f:
            response = api_client.post(
                IMPORT_EVENTOS_URL,
                {"file": f},
                format="multipart",
            )

        # Pode ser 401 ou 403 dependendo da configuracao
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# =============================================================================
# MIGRACAO 0101 — re-hash com segmento (#1915)
# =============================================================================


@pytest.mark.django_db
class TestRehashMigration0101:
    """#1915: a migracao 0101 recomputa o external_hash das linhas ja persistidas para
    incluir o segmento. O ponto critico e o TIMEZONE TRAP: o hash usa data/hora LOCAIS de
    Fortaleza, mas o banco guarda inicio/fim em UTC — a migracao precisa converter de volta.
    """

    def test_rehash_reproduces_importer_hash(self, sample_csv_same_slot_diff_segmento):
        """Apos o re-hash, cada linha volta a ter EXATAMENTE o hash que o importer gera.

        Se a migracao extraisse a hora em UTC (em vez de Fortaleza), o hash recomputado
        divergiria do que um import futuro produz -> duplicacao. Este assert pega isso.
        """
        import importlib

        from django.apps import apps as global_apps

        import_eventos_from_file(path=sample_csv_same_slot_diff_segmento, dry_run=False)
        expected = {s.id: s.external_hash for s in Solicitacao.objects.all()}
        assert len(expected) == 2

        # Simula linhas pre-migracao: external_hash obsoleto (placeholder distinto, 64 chars).
        for i, sol in enumerate(Solicitacao.objects.all().order_by("id")):
            sol.external_hash = f"stale{i:059d}"
            sol.save(update_fields=["external_hash"])

        mig = importlib.import_module("apps.core.migrations.0101_rehash_eventos_external_hash_with_segmento")
        mig._rehash_forward(global_apps, None)

        got = {s.id: s.external_hash for s in Solicitacao.objects.all()}
        assert got == expected


# =============================================================================
# #1620 (gate de disponibilidade so p/ evento FUTURO) + #1628 (reimport nao reverte decisao)
# =============================================================================


@pytest.mark.django_db
class TestEventosImportAvailabilityAndReimport:
    """#1620/M08-12 (enforcement RD-01..08 no import, so p/ FUTURO) e #1628/M10-07
    (reimport nao sobrescreve decisao humana; relatorio real; orfao reportado)."""

    def _approved_event(self, *, municipio, projeto, tipo_evento, formador, inicio, fim):
        """Cria um evento APROVADO com o formador como participante (recurso alocado)."""
        sol = SolicitacaoFactory(
            municipio=municipio,
            projeto=projeto,
            tipo_evento=tipo_evento,
            inicio=inicio,
            fim=fim,
            status=Solicitacao.Status.APROVADO,
        )
        Participation.objects.create(solicitacao=sol, usuario=formador, role=Participation.Role.FORMADOR)
        return sol

    def test_future_conflict_goes_to_pendencia_not_created(
        self, coordenador_user, formador1_user, municipio, projeto_super, tipo_evento
    ):
        """#1620: evento FUTURO que conflita com evento aprovado do mesmo formador NAO e gravado."""
        d = date.today() + timedelta(days=60)
        self._approved_event(
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            formador=formador1_user,
            inicio=_aware_fortaleza(d, 8),
            fim=_aware_fortaleza(d, 12),
        )
        csv = _write_csv(
            "municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,formador1\n"
            f"{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d.isoformat()},"
            f"10:00,14:00,{coordenador_user.email},{formador1_user.email}\n"
        )
        result = import_eventos_from_file(path=csv, dry_run=False)
        Path(csv).unlink(missing_ok=True)

        # comportamento (RED no codigo antigo: o evento em conflito era gravado aprovado)
        assert result["stats"]["solicitacoes"]["created"] == 0
        assert Solicitacao.objects.count() == 1  # so o aprovado pre-existente
        # e reportado como pendencia de disponibilidade
        assert result["stats"]["skipped"]["availability"] == 1
        assert len(result["pendencias"]["availability"]) == 1

    def test_past_conflict_is_created_historical(
        self, coordenador_user, formador1_user, municipio, projeto_super, tipo_evento
    ):
        """#1620: evento PASSADO (historico) entra mesmo em conflito — nao passa pelo gate."""
        d = date.today() - timedelta(days=60)
        self._approved_event(
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            formador=formador1_user,
            inicio=_aware_fortaleza(d, 8),
            fim=_aware_fortaleza(d, 12),
        )
        csv = _write_csv(
            "municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,formador1\n"
            f"{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d.isoformat()},"
            f"10:00,14:00,{coordenador_user.email},{formador1_user.email}\n"
        )
        result = import_eventos_from_file(path=csv, dry_run=False)
        Path(csv).unlink(missing_ok=True)

        assert result["stats"]["solicitacoes"]["created"] == 1  # historico entra
        assert Solicitacao.objects.count() == 2

    def test_reimport_preserves_human_approved_status(self, coordenador_user, municipio, projeto_super, tipo_evento):
        """#1628: reimport NAO reverte a decisao humana (aprovado nao volta a pendente)."""
        d = date.today() + timedelta(days=70)
        content = (
            "municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador\n"
            f"{municipio.nome},{projeto_super.nome},{tipo_evento.nome},{d.isoformat()},"
            f"08:00,12:00,{coordenador_user.email}\n"
        )
        csv = _write_csv(content)
        import_eventos_from_file(path=csv, dry_run=False)
        sol = Solicitacao.objects.get()
        assert sol.status == "pendente"  # SUPER nasce pendente

        # decisao humana: aprova
        sol.status = Solicitacao.Status.APROVADO
        sol.save(update_fields=["status"])

        # reimport da MESMA linha
        result = import_eventos_from_file(path=csv, dry_run=False)
        Path(csv).unlink(missing_ok=True)

        sol.refresh_from_db()
        assert sol.status == "aprovado"  # RED: hoje o reimport reverte p/ pendente
        assert result["stats"]["skipped"]["protected"] == 1
        assert len(result["pendencias"]["protected"]) == 1

    def test_reimport_changed_nonprotected_field_counts_as_updated(
        self, coordenador_user, municipio, projeto_nao_super, tipo_evento
    ):
        """#1628 item 3: mudanca real (encontro) e contada como 'updated', nao 'unchanged'."""
        d = date.today() + timedelta(days=80)
        base = (
            "municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,encontro\n"
            f"{municipio.nome},{projeto_nao_super.nome},{tipo_evento.nome},{d.isoformat()},"
            "08:00,12:00,{coord},{enc}\n"
        )
        csv1 = _write_csv(base.format(coord=coordenador_user.email, enc="EF1"))
        import_eventos_from_file(path=csv1, dry_run=False)
        Path(csv1).unlink(missing_ok=True)

        csv2 = _write_csv(base.format(coord=coordenador_user.email, enc="EF9"))
        result = import_eventos_from_file(path=csv2, dry_run=False)
        Path(csv2).unlink(missing_ok=True)

        assert result["stats"]["solicitacoes"]["updated"] == 1  # RED: hoje conta 'unchanged'
        assert result["stats"]["solicitacoes"]["unchanged"] == 0
        sol = Solicitacao.objects.get()
        assert sol.encontro == "EF9"

    def test_reimport_orphan_formador_reported_not_removed(
        self, coordenador_user, formador1_user, municipio, projeto_nao_super, tipo_evento
    ):
        """#1628 item 4: formador retirado da planilha no reimport e REPORTADO, nao removido."""
        d = date.today() + timedelta(days=90)
        with_form = (
            "municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador,formador1\n"
            f"{municipio.nome},{projeto_nao_super.nome},{tipo_evento.nome},{d.isoformat()},"
            f"08:00,12:00,{coordenador_user.email},{formador1_user.email}\n"
        )
        csv1 = _write_csv(with_form)
        import_eventos_from_file(path=csv1, dry_run=False)
        Path(csv1).unlink(missing_ok=True)
        sol = Solicitacao.objects.get()
        assert Participation.objects.filter(solicitacao=sol, usuario=formador1_user).exists()

        # reimport SEM o formador1 (mesma chave natural = mesmo external_hash)
        without_form = (
            "municipio,projeto,tipo_evento,data,hora_inicio,hora_fim,coordenador\n"
            f"{municipio.nome},{projeto_nao_super.nome},{tipo_evento.nome},{d.isoformat()},"
            f"08:00,12:00,{coordenador_user.email}\n"
        )
        csv2 = _write_csv(without_form)
        result = import_eventos_from_file(path=csv2, dry_run=False)
        Path(csv2).unlink(missing_ok=True)

        # NAO removido, apenas reportado
        assert Participation.objects.filter(solicitacao=sol, usuario=formador1_user).exists()
        assert len(result["pendencias"]["orfaos"]) == 1
