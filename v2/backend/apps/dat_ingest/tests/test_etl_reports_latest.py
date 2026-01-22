"""
Tests for ETL Observability - list_latest_reports and API endpoint

Fase 5 - Desligamento gradual de planilhas
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import time

import pytest
from pathlib import Path
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.dat_ingest.services.etl_observability import list_latest_reports, get_report_path

User = get_user_model()


# ============================================================================
# Service Layer Tests (list_latest_reports function)
# ============================================================================

class TestListLatestReportsService:
    """Tests for list_latest_reports service function"""

    def test_empty_directory_returns_empty_list(self, tmp_path):
        """Se diretório está vazio, deve retornar lista vazia"""
        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            reports = list_latest_reports(limit=20)
            assert reports == []

    def test_nonexistent_directory_returns_empty_list(self, tmp_path):
        """Se diretório não existe, deve retornar lista vazia (não erro)"""
        nonexistent = tmp_path / "does_not_exist"
        with override_settings(ETL_OUTPUT_DIR=str(nonexistent)):
            reports = list_latest_reports(limit=20)
            assert reports == []

    def test_lists_files_with_metadata(self, tmp_path):
        """Deve retornar metadados corretos para arquivos"""
        # Criar arquivos de teste
        (tmp_path / "report1.json").write_text('{"test": 1}')
        time.sleep(0.01)  # Garantir mtime diferente
        (tmp_path / "report2.csv").write_text('col1,col2\nval1,val2')

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            reports = list_latest_reports(limit=20)

            assert len(reports) == 2

            # Validar estrutura
            for report in reports:
                assert 'filename' in report
                assert 'size_bytes' in report
                assert 'mtime_iso' in report
                assert 'kind' in report
                assert 'path_rel' in report

            # Validar tipos de arquivo
            json_report = next(r for r in reports if r['filename'] == 'report1.json')
            assert json_report['kind'] == 'json'
            assert json_report['size_bytes'] > 0

            csv_report = next(r for r in reports if r['filename'] == 'report2.csv')
            assert csv_report['kind'] == 'csv'

    def test_orders_by_mtime_desc(self, tmp_path):
        """Deve ordenar por mtime (mais recente primeiro)"""
        # Criar 3 arquivos com mtimes diferentes
        file1 = tmp_path / "old.json"
        file1.write_text('{}')
        time.sleep(0.01)

        file2 = tmp_path / "middle.json"
        file2.write_text('{}')
        time.sleep(0.01)

        file3 = tmp_path / "new.json"
        file3.write_text('{}')

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            reports = list_latest_reports(limit=20)

            assert len(reports) == 3
            # Mais recente primeiro
            assert reports[0]['filename'] == 'new.json'
            assert reports[1]['filename'] == 'middle.json'
            assert reports[2]['filename'] == 'old.json'

            # Validar que mtimes estão em ordem decrescente
            mtimes = [r['mtime_iso'] for r in reports]
            assert mtimes == sorted(mtimes, reverse=True)

    def test_respects_limit_parameter(self, tmp_path):
        """Deve respeitar o parâmetro limit"""
        # Criar 10 arquivos
        for i in range(10):
            (tmp_path / f"report{i}.json").write_text('{}')
            time.sleep(0.001)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            # Testar limite de 5
            reports = list_latest_reports(limit=5)
            assert len(reports) == 5

            # Testar limite de 1
            reports = list_latest_reports(limit=1)
            assert len(reports) == 1

            # Testar limite maior que número de arquivos
            reports = list_latest_reports(limit=100)
            assert len(reports) == 10

    def test_validates_limit_range(self, tmp_path):
        """Deve validar que limit está entre 1 e 100"""
        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            # Limite muito baixo
            with pytest.raises(ValueError, match="entre 1 e 100"):
                list_latest_reports(limit=0)

            # Limite muito alto
            with pytest.raises(ValueError, match="entre 1 e 100"):
                list_latest_reports(limit=101)

            # Limites válidos não devem lançar erro
            list_latest_reports(limit=1)
            list_latest_reports(limit=100)

    def test_identifies_file_kinds(self, tmp_path):
        """Deve identificar corretamente os tipos de arquivo"""
        (tmp_path / "data.json").write_text('{}')
        (tmp_path / "data.csv").write_text('')
        (tmp_path / "log.txt").write_text('')
        (tmp_path / "log.log").write_text('')
        (tmp_path / "unknown.xyz").write_text('')

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            reports = list_latest_reports(limit=20)

            kinds_by_filename = {r['filename']: r['kind'] for r in reports}

            assert kinds_by_filename['data.json'] == 'json'
            assert kinds_by_filename['data.csv'] == 'csv'
            assert kinds_by_filename['log.txt'] == 'txt'
            assert kinds_by_filename['log.log'] == 'txt'
            assert kinds_by_filename['unknown.xyz'] == 'other'

    def test_ignores_hidden_files(self, tmp_path):
        """Deve ignorar arquivos ocultos (começando com .)"""
        (tmp_path / "visible.json").write_text('{}')
        (tmp_path / ".hidden.json").write_text('{}')

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            reports = list_latest_reports(limit=20)

            assert len(reports) == 1
            assert reports[0]['filename'] == 'visible.json'

    def test_ignores_subdirectories(self, tmp_path):
        """Deve ignorar subdiretórios (não recursivo)"""
        (tmp_path / "file.json").write_text('{}')
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.json").write_text('{}')

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            reports = list_latest_reports(limit=20)

            assert len(reports) == 1
            assert reports[0]['filename'] == 'file.json'


class TestGetReportPath:
    """Tests for get_report_path security function"""

    def test_returns_path_for_valid_file(self, tmp_path):
        """Deve retornar Path para arquivo válido"""
        (tmp_path / "report.json").write_text('{}')

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            path = get_report_path('report.json')

            assert path is not None
            assert path.exists()
            assert path.name == 'report.json'

    def test_returns_none_for_nonexistent_file(self, tmp_path):
        """Deve retornar None se arquivo não existe"""
        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            path = get_report_path('does_not_exist.json')
            assert path is None

    def test_blocks_path_traversal(self, tmp_path):
        """Deve bloquear tentativas de path traversal"""
        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            # Tentar acessar arquivo fora do diretório
            assert get_report_path('../etc/passwd') is None
            assert get_report_path('../../etc/passwd') is None
            assert get_report_path('subdir/../../../etc/passwd') is None

    def test_blocks_absolute_paths(self, tmp_path):
        """Deve bloquear paths absolutos"""
        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            assert get_report_path('/etc/passwd') is None
            assert get_report_path('C:\\Windows\\System32\\config\\sam') is None

    def test_blocks_directory_paths(self, tmp_path):
        """Deve retornar None para diretórios"""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            path = get_report_path('subdir')
            assert path is None


# ============================================================================
# API Endpoint Tests (EtlReportsLatestView)
# ============================================================================

@pytest.mark.django_db
class TestEtlReportsLatestEndpoint:
    """Tests for GET /api/etl/reports/latest/ endpoint"""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def usuario_controle(self):
        """Usuário com grupo Controle (tem permissão)"""
        group_controle, _ = Group.objects.get_or_create(name='Controle')
        user = User.objects.create_user(
            username='controle_test',
            email='controle@test.com',
            password='testpass123',
            cpf='11111111111',
        )
        user.groups.add(group_controle)
        return user

    @pytest.fixture
    def usuario_super(self):
        """Usuário com grupo Superintendência (tem permissão)"""
        group_super, _ = Group.objects.get_or_create(name='Superintendência')
        user = User.objects.create_user(
            username='super_test',
            email='super@test.com',
            password='testpass123',
            cpf='22222222222',
        )
        user.groups.add(group_super)
        return user

    @pytest.fixture
    def usuario_formador(self):
        """Usuário sem grupo privilegiado (sem permissão)"""
        user = User.objects.create_user(
            username='formador_test',
            email='formador@test.com',
            password='testpass123',
            cpf='33333333333',
        )
        return user

    def test_requires_authentication(self, api_client, tmp_path):
        """Deve exigir autenticação"""
        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/')
            assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_requires_controle_or_super_permission(self, api_client, usuario_formador, tmp_path):
        """Deve exigir grupo Controle ou Superintendência"""
        api_client.force_authenticate(user=usuario_formador)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/')
            assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_controle_can_access(self, api_client, usuario_controle, tmp_path):
        """Usuário Controle pode acessar"""
        api_client.force_authenticate(user=usuario_controle)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/')
            assert response.status_code == http_status.HTTP_200_OK

    def test_super_can_access(self, api_client, usuario_super, tmp_path):
        """Usuário Superintendência pode acessar"""
        api_client.force_authenticate(user=usuario_super)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/')
            assert response.status_code == http_status.HTTP_200_OK

    def test_returns_reports_list(self, api_client, usuario_controle, tmp_path):
        """Deve retornar lista de relatórios"""
        # Criar arquivos de teste
        (tmp_path / "report1.json").write_text('{}')
        (tmp_path / "report2.csv").write_text('')

        api_client.force_authenticate(user=usuario_controle)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/')

            assert response.status_code == http_status.HTTP_200_OK
            data = response.json()

            assert 'count' in data
            assert 'limit' in data
            assert 'reports' in data

            assert data['count'] == 2
            assert data['limit'] == 20
            assert len(data['reports']) == 2

    def test_accepts_limit_parameter(self, api_client, usuario_controle, tmp_path):
        """Deve aceitar parâmetro limit"""
        # Criar 5 arquivos
        for i in range(5):
            (tmp_path / f"report{i}.json").write_text('{}')
            time.sleep(0.001)

        api_client.force_authenticate(user=usuario_controle)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/?limit=3')

            assert response.status_code == http_status.HTTP_200_OK
            data = response.json()

            assert data['count'] == 3
            assert data['limit'] == 3
            assert len(data['reports']) == 3

    def test_validates_limit_parameter_type(self, api_client, usuario_controle, tmp_path):
        """Deve validar que limit é um número"""
        api_client.force_authenticate(user=usuario_controle)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/?limit=invalid')

            assert response.status_code == http_status.HTTP_400_BAD_REQUEST
            data = response.json()

            assert 'detail' in data
            assert 'número inteiro' in data['detail']

    def test_validates_limit_parameter_range(self, api_client, usuario_controle, tmp_path):
        """Deve validar que limit está entre 1 e 100"""
        api_client.force_authenticate(user=usuario_controle)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            # Limite muito baixo
            response = api_client.get('/api/etl/reports/latest/?limit=0')
            assert response.status_code == http_status.HTTP_400_BAD_REQUEST
            assert 'entre 1 e 100' in response.json()['detail']

            # Limite muito alto
            response = api_client.get('/api/etl/reports/latest/?limit=101')
            assert response.status_code == http_status.HTTP_400_BAD_REQUEST
            assert 'entre 1 e 100' in response.json()['detail']

    def test_handles_empty_directory_gracefully(self, api_client, usuario_controle, tmp_path):
        """Deve lidar com diretório vazio sem erro"""
        api_client.force_authenticate(user=usuario_controle)

        with override_settings(ETL_OUTPUT_DIR=str(tmp_path)):
            response = api_client.get('/api/etl/reports/latest/')

            assert response.status_code == http_status.HTTP_200_OK
            data = response.json()

            assert data['count'] == 0
            assert data['reports'] == []

    def test_handles_nonexistent_directory_gracefully(self, api_client, usuario_controle, tmp_path):
        """Deve lidar com diretório inexistente sem erro (degradação graciosa)"""
        nonexistent = tmp_path / "does_not_exist"

        api_client.force_authenticate(user=usuario_controle)

        with override_settings(ETL_OUTPUT_DIR=str(nonexistent)):
            response = api_client.get('/api/etl/reports/latest/')

            assert response.status_code == http_status.HTTP_200_OK
            data = response.json()

            assert data['count'] == 0
            assert data['reports'] == []
