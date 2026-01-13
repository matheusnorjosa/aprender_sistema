"""
Testes para importação de Compras (CSV/XLSX).

Valida:
- Dry-run (preview sem persistir)
- Apply (persistência efetiva)
- Idempotência (reprocessar mesmos dados)
- Pendências (municípios/projetos não resolvidos)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
import tempfile
from pathlib import Path
from datetime import date
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.core.models import Compra, Municipio, Projeto, Usuario
from apps.core.services.controle_imports import import_compras_from_file


pytestmark = pytest.mark.django_db


@pytest.fixture
def user_controle():
    """Cria usuário com permissões de Controle."""
    user = Usuario.objects.create_user(
        username="controle",
        email="controle@test.com",
        password="testpass",
        cpf="11111111111",
    )
    group, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(group)
    return user


@pytest.fixture
def setup_data():
    """Cria municípios e projetos necessários para os testes."""
    # Municípios
    municipio_acarape, _ = Municipio.objects.get_or_create(
        nome="Acarape",
        defaults={"uf": "CE", "ativo": True},
    )
    municipio_pacajus, _ = Municipio.objects.get_or_create(
        nome="Pacajus",
        defaults={"uf": "CE", "ativo": True},
    )

    # Projetos (necessários para heurística)
    projeto_nl, _ = Projeto.objects.get_or_create(
        nome="Novo Lendo",
        defaults={"ativo": True},
    )
    projeto_ge, _ = Projeto.objects.get_or_create(
        nome="Gestão Escolar",
        defaults={"ativo": True},
    )

    return {
        "municipio_acarape": municipio_acarape,
        "municipio_pacajus": municipio_pacajus,
        "projeto_nl": projeto_nl,
        "projeto_ge": projeto_ge,
    }


@pytest.fixture
def csv_compras_temp(setup_data):
    """Cria arquivo CSV temporário com 2 linhas de compras."""
    content = """CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções
COMP-001,LIVRO NOVO LENDO,100,Acarape,CE,2025-01-15,Formação inicial
COMP-002,KIT GESTÃO ESCOLAR,50,Pacajus,CE,2025-02-20,Reposição estoque
"""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()
    yield tmp.name
    # Cleanup
    Path(tmp.name).unlink(missing_ok=True)


def test_import_compras_dry_run_csv(csv_compras_temp, setup_data):
    """
    Testa import em dry-run via CSV.

    - Deve simular created=2
    - Não deve persistir (Compra.count() == 0)
    """
    # Limpar compras existentes
    Compra.objects.all().delete()

    # Executar dry-run
    report = import_compras_from_file(path=csv_compras_temp, dry_run=True)

    # Validar relatório
    assert report["dry_run"] is True
    assert report["stats"]["created"] == 2
    assert report["stats"]["updated"] == 0
    assert report["stats"]["skipped"] == 0

    # Validar que não persistiu
    assert Compra.objects.count() == 0


def test_import_compras_apply_csv(csv_compras_temp, setup_data):
    """
    Testa import em apply via CSV.

    - Deve persistir created=2
    - Compra.count() == 2
    """
    # Limpar compras existentes
    Compra.objects.all().delete()

    # Executar apply
    report = import_compras_from_file(path=csv_compras_temp, dry_run=False)

    # Validar relatório
    assert report["dry_run"] is False
    assert report["stats"]["created"] == 2
    assert report["stats"]["updated"] == 0
    assert len(report["created_ids"]) == 2

    # Validar persistência
    assert Compra.objects.count() == 2

    # Validar dados
    compra1 = Compra.objects.get(codigo="COMP-001")
    assert compra1.municipio.nome == "Acarape"
    assert compra1.projeto.nome == "Novo Lendo"
    assert compra1.quantidade == 100
    assert compra1.data == date(2025, 1, 15)
    assert "formacao inicial" in compra1.uso.lower()

    compra2 = Compra.objects.get(codigo="COMP-002")
    assert compra2.municipio.nome == "Pacajus"
    assert compra2.projeto.nome == "Gestão Escolar"
    assert compra2.quantidade == 50


def test_import_compras_idempotence(csv_compras_temp, setup_data):
    """
    Testa idempotência: reprocessar mesmo CSV não duplica.

    - Primeira execução: created=2
    - Segunda execução: updated=0, skipped=2 (não mudou nada)
    """
    # Limpar compras existentes
    Compra.objects.all().delete()

    # Primeira execução
    report1 = import_compras_from_file(path=csv_compras_temp, dry_run=False)
    assert report1["stats"]["created"] == 2
    assert Compra.objects.count() == 2

    # Segunda execução (mesmos dados)
    report2 = import_compras_from_file(path=csv_compras_temp, dry_run=False)
    assert report2["stats"]["created"] == 0
    assert report2["stats"]["skipped"] == 2  # Não mudou nada
    assert Compra.objects.count() == 2  # Não duplicou


def test_import_compras_endpoint_dry_run(user_controle, csv_compras_temp, setup_data):
    """
    Testa endpoint POST /api/controle/import-compras/ com dry_run=true.

    - Deve retornar stats.created=2
    - Não deve persistir
    """
    # Limpar compras existentes
    Compra.objects.all().delete()

    client = APIClient()
    client.force_authenticate(user=user_controle)

    # Upload de arquivo
    with open(csv_compras_temp, "rb") as f:
        response = client.post(
            "/api/controle/import-compras/?dry_run=true",
            {"file": f},
            format="multipart",
        )

    # Validar resposta
    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["stats"]["created"] == 2
    assert data["stats"]["updated"] == 0

    # Validar que não persistiu
    assert Compra.objects.count() == 0


def test_import_compras_endpoint_apply(user_controle, csv_compras_temp, setup_data):
    """
    Testa endpoint POST /api/controle/import-compras/ com dry_run=false.

    - Deve retornar stats.created=2
    - Deve persistir (Compra.count() == 2)
    """
    # Limpar compras existentes
    Compra.objects.all().delete()

    client = APIClient()
    client.force_authenticate(user=user_controle)

    # Upload de arquivo
    with open(csv_compras_temp, "rb") as f:
        response = client.post(
            "/api/controle/import-compras/?dry_run=false",
            {"file": f},
            format="multipart",
        )

    # Validar resposta
    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is False
    assert data["stats"]["created"] == 2
    assert len(data["created_ids"]) == 2

    # Validar persistência
    assert Compra.objects.count() == 2


def test_import_compras_pendencias_municipio_invalido():
    """
    Testa que município inválido gera pendência.

    - Município "Inexistente" não resolve
    - Linha deve ser skipada
    - Pendência deve ser registrada
    """
    # Criar projeto para heurística
    Projeto.objects.get_or_create(
        nome="Novo Lendo",
        defaults={"ativo": True},
    )

    # CSV com município inválido
    content = """CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções
COMP-999,LIVRO NOVO LENDO,10,Inexistente,XX,2025-03-10,Teste
"""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()

    try:
        report = import_compras_from_file(path=tmp.name, dry_run=False)

        # Validar pendência
        assert report["stats"]["skipped"] == 1
        assert len(report["pendencias"]["municipios"]) == 1
        assert report["pendencias"]["municipios"][0]["municipio"] == "Inexistente"
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def test_import_compras_pendencias_projeto_nao_inferido():
    """
    Testa que produto sem heurística de projeto gera pendência.

    - Produto "DESCONHECIDO" não mapeia para projeto
    - Linha deve ser skipada
    - Pendência deve ser registrada
    """
    # Criar município válido
    Municipio.objects.get_or_create(
        nome="Acarape",
        defaults={"uf": "CE", "ativo": True},
    )

    # CSV com produto sem projeto inferível
    content = """CÓD,Produto,Quant.,Município,UF,Data,Uso das coleções
COMP-888,PRODUTO DESCONHECIDO,5,Acarape,CE,2025-04-01,Teste
"""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()

    try:
        report = import_compras_from_file(path=tmp.name, dry_run=False)

        # Validar pendência
        assert report["stats"]["skipped"] == 1
        assert len(report["pendencias"]["projetos"]) == 1
        assert "DESCONHECIDO" in report["pendencias"]["projetos"][0]["produto"]
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def test_import_compras_requires_controle_group():
    """
    Testa que endpoint exige grupo Controle ou Superintendência.

    - Usuário sem grupo → 403 Forbidden
    """
    # Criar usuário sem grupo Controle/Superintendência
    user = Usuario.objects.create_user(
        username="formador",
        email="formador@test.com",
        password="testpass",
        cpf="22222222222",
    )
    # Adicionar a um grupo diferente (Formador)
    group, _ = Group.objects.get_or_create(name="Formador")
    user.groups.add(group)

    client = APIClient()
    client.force_authenticate(user=user)

    # Tentar importar
    from pathlib import Path
    from django.conf import settings
    csv_path = str(Path(settings.BASE_DIR) / "data/csv-import/compras.csv")
    response = client.post(
        "/api/controle/import-compras/?dry_run=true",
        data={"path": csv_path}
    )

    # Deve retornar 403 Forbidden
    assert response.status_code == 403
    assert "Controle ou Superintendência" in str(response.data)


def test_import_compras_allowed_for_controle():
    """
    Testa que grupo Controle pode importar.

    - Usuário do grupo Controle → 200 ou 400 (não 403)
    """
    # Criar usuário do grupo Controle
    user = Usuario.objects.create_user(
        username="controle2",
        email="controle2@test.com",
        password="testpass",
        cpf="33333333333",
    )
    group, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(group)

    client = APIClient()
    client.force_authenticate(user=user)

    # Tentar importar (arquivo não existe, mas não deve dar 403)
    from pathlib import Path
    from django.conf import settings
    csv_path = str(Path(settings.BASE_DIR) / "data/csv-import/compras_nao_existe.csv")
    response = client.post(
        "/api/controle/import-compras/?dry_run=true",
        data={"path": csv_path}
    )

    # Deve retornar 400 (arquivo não encontrado) ou 200, mas NÃO 403
    assert response.status_code in (200, 400)


def test_import_compras_allowed_for_superintendencia():
    """
    Testa que grupo Superintendência pode importar.

    - Usuário do grupo Superintendência → 200 ou 400 (não 403)
    """
    # Criar usuário do grupo Superintendência
    user = Usuario.objects.create_user(
        username="super",
        email="super@test.com",
        password="testpass",
        cpf="44444444444",
    )
    group, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(group)

    client = APIClient()
    client.force_authenticate(user=user)

    # Tentar importar (arquivo não existe, mas não deve dar 403)
    from pathlib import Path
    from django.conf import settings
    csv_path = str(Path(settings.BASE_DIR) / "data/csv-import/compras_nao_existe.csv")
    response = client.post(
        "/api/controle/import-compras/?dry_run=true",
        data={"path": csv_path}
    )

    # Deve retornar 400 (arquivo não encontrado) ou 200, mas NÃO 403
    assert response.status_code in (200, 400)
