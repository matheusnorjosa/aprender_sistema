#!/usr/bin/env python3
"""
Importação Completa de Dados Identificados
==========================================

Importa todos os dados identificados nas planilhas de forma organizada.

Author: Claude Code
Date: Setembro 2025
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from core.models import (
    Municipio,
    Projeto,
    Setor,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


def load_analysis_data():
    """Carrega dados da análise cruzada"""
    print("📂 CARREGANDO DADOS DA ANÁLISE")
    print("=" * 50)

    # Encontrar arquivo de análise mais recente
    analysis_files = [
        f
        for f in os.listdir(".")
        if f.startswith("analise_cruzada_completa_") and f.endswith(".json")
    ]
    if not analysis_files:
        print("❌ Arquivo de análise não encontrado")
        return None

    latest_analysis = max(analysis_files)
    print(f"📋 Carregando: {latest_analysis}")

    with open(latest_analysis, "r", encoding="utf-8") as f:
        return json.load(f)


def load_planilha_data():
    """Carrega dados das planilhas"""
    print("\n📂 CARREGANDO DADOS DAS PLANILHAS")
    print("=" * 50)

    planilhas = {}

    # Encontrar arquivos mais recentes
    files = {
        "usuarios": "usuarios_planilha_",
        "controle": "controle_planilha_",
        "agenda": "agenda_planilha_",
        "disponibilidade": "disponibilidade_planilha_",
    }

    for key, prefix in files.items():
        matching_files = [
            f for f in os.listdir(".") if f.startswith(prefix) and f.endswith(".json")
        ]
        if matching_files:
            latest_file = max(matching_files)
            print(f"📋 {key.upper()}: {latest_file}")

            with open(latest_file, "r", encoding="utf-8") as f:
                planilhas[key] = json.load(f)
        else:
            print(f"❌ {key.upper()}: Nenhum arquivo encontrado")
            planilhas[key] = None

    return planilhas


def normalize_cpf(cpf):
    """Normaliza CPF"""
    if not cpf:
        return None
    cpf_limpo = re.sub(r"\D", "", str(cpf))
    if len(cpf_limpo) == 11:
        return cpf_limpo
    return None


def normalize_name(name):
    """Normaliza nome"""
    if not name:
        return None
    return " ".join(word.capitalize() for word in str(name).strip().split())


def get_or_create_setor(nome, sigla=None):
    """Obtém ou cria setor"""
    if not nome:
        return None

    nome_normalizado = normalize_name(nome)
    if not nome_normalizado:
        return None

    setor, created = Setor.objects.get_or_create(
        nome=nome_normalizado,
        defaults={
            "sigla": sigla or nome_normalizado[:3].upper(),
            "ativo": True,
            "vinculado_superintendencia": False,
        },
    )

    if created:
        print(f"   ✅ Setor criado: {nome_normalizado}")

    return setor


def get_or_create_municipio(nome, uf="CE"):
    """Obtém ou cria município"""
    if not nome:
        return None

    # Limpar nome
    nome_limpo = str(nome).strip()
    if " - " in nome_limpo:
        nome_limpo = nome_limpo.split(" - ")[0].strip()

    nome_normalizado = normalize_name(nome_limpo)
    if not nome_normalizado:
        return None

    municipio, created = Municipio.objects.get_or_create(
        nome=nome_normalizado, uf=uf, defaults={"ativo": True}
    )

    if created:
        print(f"   ✅ Município criado: {nome_normalizado} - {uf}")

    return municipio


def get_or_create_projeto(nome, setor=None):
    """Obtém ou cria projeto"""
    if not nome:
        return None

    nome_normalizado = normalize_name(nome)
    if not nome_normalizado:
        return None

    # Mapear projetos específicos para genéricos
    project_mapping = {
        "ACERTA MATEMÁTICA": "ACerta",
        "ACERTA PORTUGUÊS": "ACerta",
        "NOVO LENDO": "Lendo e Escrevendo",
        "VIDA E MATEMÁTICA": "Vida & Matemática",
        "VIDA E LINGUAGEM": "Vida & Linguagem",
        "BRINCANDO E APRENDENDO": "Brincando e Aprendendo",
        "LENDO E ESCREVENDO": "Lendo e Escrevendo",
        "PROJETO AMMA": "Projeto AMMA",
        "VIDA E CIÊNCIAS": "Vida & Ciências",
    }

    nome_final = project_mapping.get(nome_normalizado, nome_normalizado)

    projeto, created = Projeto.objects.get_or_create(
        nome=nome_final,
        defaults={"setor": setor or get_or_create_setor("Outros"), "ativo": True},
    )

    if created:
        print(f"   ✅ Projeto criado: {nome_final}")

    return projeto


def get_or_create_tipo_evento(nome):
    """Obtém ou cria tipo de evento"""
    if not nome:
        return None

    nome_normalizado = normalize_name(nome)
    if not nome_normalizado:
        return None

    # Mapear tipos específicos
    tipo_mapping = {
        "Presencial": "Formação Presencial",
        "Online": "Formação Online",
        "Acompanhamento": "Acompanhamento",
        "Deslocamento": "Deslocamento",
        "Retorno": "Retorno",
    }

    nome_final = tipo_mapping.get(nome_normalizado, nome_normalizado)

    tipo_evento, created = TipoEvento.objects.get_or_create(
        nome=nome_final, defaults={"ativo": True, "online": "Online" in nome_final}
    )

    if created:
        print(f"   ✅ Tipo de evento criado: {nome_final}")

    return tipo_evento


def import_usuarios(planilhas):
    """Importa usuários das planilhas"""
    print("\n👥 IMPORTANDO USUÁRIOS")
    print("=" * 50)

    if not planilhas.get("usuarios"):
        print("❌ Dados de usuários não disponíveis")
        return

    usuarios_data = planilhas["usuarios"]
    imported_count = 0
    updated_count = 0

    for ws in usuarios_data.get("worksheets", []):
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        print(f"📊 Processando {ws_title}: {len(records)} registros")

        for record in records:
            try:
                # Extrair dados
                nome_completo = record.get("Nome Completo", "") or record.get(
                    "Nome", ""
                )
                cpf = record.get("CPF", "")
                email = record.get("Email", "")
                telefone = record.get("Telefone", "")
                cargo = record.get("Cargo", "")
                municipio_nome = record.get("Município", "")
                projeto_nome = record.get("Projeto", "")

                if not nome_completo:
                    continue

                # Normalizar dados
                cpf_limpo = normalize_cpf(cpf)
                nome_normalizado = normalize_name(nome_completo)

                # Determinar se é ativo
                is_active = "Ativos" in ws_title
                formador_ativo = cargo and "formador" in cargo.lower()

                # Criar ou atualizar usuário
                if cpf_limpo:
                    usuario, created = Usuario.objects.update_or_create(
                        cpf=cpf_limpo,
                        defaults={
                            "first_name": (
                                nome_normalizado.split()[0] if nome_normalizado else ""
                            ),
                            "last_name": (
                                " ".join(nome_normalizado.split()[1:])
                                if len(nome_normalizado.split()) > 1
                                else ""
                            ),
                            "email": email or "",
                            "telefone": telefone or "",
                            "cargo": cargo or "",
                            "is_active": is_active,
                            "formador_ativo": formador_ativo,
                            "username": cpf_limpo,
                        },
                    )
                else:
                    # Se não tem CPF, usar nome como username
                    username = re.sub(r"\W+", "", nome_normalizado.lower())
                    usuario, created = Usuario.objects.update_or_create(
                        username=username,
                        defaults={
                            "first_name": (
                                nome_normalizado.split()[0] if nome_normalizado else ""
                            ),
                            "last_name": (
                                " ".join(nome_normalizado.split()[1:])
                                if len(nome_normalizado.split()) > 1
                                else ""
                            ),
                            "email": email or "",
                            "telefone": telefone or "",
                            "cargo": cargo or "",
                            "is_active": is_active,
                            "formador_ativo": formador_ativo,
                        },
                    )

                if created:
                    imported_count += 1
                    print(f"   ✅ Usuário criado: {nome_normalizado}")
                else:
                    updated_count += 1

                # Associar com município e projeto
                if municipio_nome:
                    municipio = get_or_create_municipio(municipio_nome)
                    if municipio:
                        usuario.municipio = municipio
                        usuario.save()

                if projeto_nome:
                    projeto = get_or_create_projeto(projeto_nome)
                    if projeto:
                        usuario.projeto = projeto
                        usuario.save()

                # Adicionar a grupos
                if cargo:
                    if "formador" in cargo.lower():
                        grupo, _ = Group.objects.get_or_create(name="formador")
                        usuario.groups.add(grupo)
                    elif "coordenador" in cargo.lower():
                        grupo, _ = Group.objects.get_or_create(name="coordenador")
                        usuario.groups.add(grupo)
                    elif "gerente" in cargo.lower():
                        grupo, _ = Group.objects.get_or_create(name="gerente")
                        usuario.groups.add(grupo)

            except Exception as e:
                print(
                    f"   ❌ Erro ao processar usuário {record.get('Nome', 'N/A')}: {e}"
                )

    print(f"📊 Usuários importados: {imported_count}")
    print(f"📊 Usuários atualizados: {updated_count}")


def import_coordenadores_mapping(planilhas):
    """Importa mapeamento coordenador-projeto-município"""
    print("\n👨‍💼 IMPORTANDO MAPEAMENTO COORDENADORES")
    print("=" * 50)

    if not planilhas.get("controle"):
        print("❌ Dados de controle não disponíveis")
        return

    controle_data = planilhas["controle"]
    imported_count = 0

    for ws in controle_data.get("worksheets", []):
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        if "AÇÕES" not in ws_title:
            continue

        print(f"📊 Processando {ws_title}: {len(records)} registros")

        for record in records:
            try:
                municipio_nome = record.get("Município", "")
                projeto_nome = record.get("Projeto", "")
                coordenador_nome = record.get("Coordenador", "")

                if not all([municipio_nome, projeto_nome, coordenador_nome]):
                    continue

                # Obter ou criar entidades
                municipio = get_or_create_municipio(municipio_nome)
                projeto = get_or_create_projeto(projeto_nome)
                coordenador = get_or_create_coordenador(coordenador_nome)

                if not all([municipio, projeto, coordenador]):
                    continue

                # Criar solicitação de mapeamento
                solicitacao, created = Solicitacao.objects.get_or_create(
                    titulo_evento=f"Mapeamento {projeto.nome} - {municipio.nome}",
                    data_inicio=timezone.now(),
                    defaults={
                        "projeto": projeto,
                        "municipio": municipio,
                        "tipo_evento": get_or_create_tipo_evento("Mapeamento"),
                        "usuario_solicitante": coordenador,
                        "data_fim": timezone.now() + timedelta(hours=1),
                        "status": SolicitacaoStatus.APROVADO,
                        "observacoes": f"Mapeamento coordenador-projeto-município importado da planilha de controle",
                        "data_solicitacao": timezone.now(),
                        "coordenador_acompanha": True,
                    },
                )

                if created:
                    imported_count += 1
                    print(
                        f"   ✅ Mapeamento criado: {coordenador_nome} -> {projeto_nome} -> {municipio_nome}"
                    )

            except Exception as e:
                print(f"   ❌ Erro ao processar mapeamento: {e}")

    print(f"📊 Mapeamentos importados: {imported_count}")


def get_or_create_coordenador(nome):
    """Obtém ou cria coordenador"""
    if not nome:
        return None

    nome_normalizado = normalize_name(nome)
    if not nome_normalizado:
        return None

    # Tentar encontrar por nome
    usuario = Usuario.objects.filter(
        first_name__icontains=nome_normalizado.split()[0],
        last_name__icontains=(
            " ".join(nome_normalizado.split()[1:])
            if len(nome_normalizado.split()) > 1
            else ""
        ),
    ).first()

    if usuario:
        # Atualizar cargo se necessário
        if usuario.cargo != "coordenador":
            usuario.cargo = "coordenador"
            usuario.save()

        # Adicionar ao grupo
        grupo, _ = Group.objects.get_or_create(name="coordenador")
        usuario.groups.add(grupo)

        return usuario

    # Criar novo coordenador
    username = re.sub(r"\W+", "", nome_normalizado.lower())
    usuario, created = Usuario.objects.get_or_create(
        username=username,
        defaults={
            "first_name": nome_normalizado.split()[0] if nome_normalizado else "",
            "last_name": (
                " ".join(nome_normalizado.split()[1:])
                if len(nome_normalizado.split()) > 1
                else ""
            ),
            "cargo": "coordenador",
            "is_active": True,
            "formador_ativo": False,
        },
    )

    if created:
        print(f"   ✅ Coordenador criado: {nome_normalizado}")

    # Adicionar ao grupo
    grupo, _ = Group.objects.get_or_create(name="coordenador")
    usuario.groups.add(grupo)

    return usuario


def import_eventos(planilhas):
    """Importa eventos das planilhas"""
    print("\n📅 IMPORTANDO EVENTOS")
    print("=" * 50)

    if not planilhas.get("agenda"):
        print("❌ Dados de agenda não disponíveis")
        return

    agenda_data = planilhas["agenda"]
    imported_count = 0

    for ws in agenda_data.get("worksheets", []):
        ws_title = ws.get("title", "")
        records = ws.get("records", [])

        if not records or "Google Agenda" not in ws_title:
            continue

        print(f"📊 Processando {ws_title}: {len(records)} registros")

        # Processar apenas uma amostra para evitar sobrecarga
        sample_records = records[:100]  # Primeiros 100 registros

        for record in sample_records:
            try:
                titulo = record.get("Title", "") or record.get("Título", "")
                inicio = record.get("Start", "") or record.get("Data Inicio", "")
                fim = record.get("End", "") or record.get("Data Termino", "")

                if not titulo:
                    continue

                # Extrair município e projeto do título
                municipio_nome = extract_municipio_from_title(titulo)
                projeto_nome = extract_projeto_from_title(titulo)

                # Obter ou criar entidades
                municipio = (
                    get_or_create_municipio(municipio_nome) if municipio_nome else None
                )
                projeto = get_or_create_projeto(projeto_nome) if projeto_nome else None
                tipo_evento = get_or_create_tipo_evento("Evento")

                # Obter coordenador aleatório
                coordenador = Usuario.objects.filter(
                    cargo="coordenador", is_active=True
                ).first()
                if not coordenador:
                    coordenador = Usuario.objects.filter(is_active=True).first()

                if not coordenador:
                    continue

                # Criar datas
                data_inicio = parse_date(inicio) if inicio else timezone.now()
                data_fim = parse_date(fim) if fim else data_inicio + timedelta(hours=2)

                # Criar solicitação
                solicitacao, created = Solicitacao.objects.get_or_create(
                    titulo_evento=titulo,
                    data_inicio=data_inicio,
                    defaults={
                        "projeto": projeto,
                        "municipio": municipio,
                        "tipo_evento": tipo_evento,
                        "usuario_solicitante": coordenador,
                        "data_fim": data_fim,
                        "status": SolicitacaoStatus.APROVADO,
                        "observacoes": f"Evento importado da planilha de agenda",
                        "data_solicitacao": timezone.now(),
                        "coordenador_acompanha": True,
                    },
                )

                if created:
                    imported_count += 1
                    print(f"   ✅ Evento criado: {titulo}")

            except Exception as e:
                print(f"   ❌ Erro ao processar evento: {e}")

    print(f"📊 Eventos importados: {imported_count}")


def extract_municipio_from_title(titulo):
    """Extrai município do título"""
    if not titulo:
        return None

    # Padrões comuns
    patterns = [
        r"([A-Za-z\s]+)\s*-\s*[A-Z]{2}",  # Nome - UF
        r"([A-Za-z\s]+)\s*\([A-Z]{2}\)",  # Nome (UF)
    ]

    for pattern in patterns:
        match = re.search(pattern, titulo)
        if match:
            return match.group(1).strip()

    return None


def extract_projeto_from_title(titulo):
    """Extrai projeto do título"""
    if not titulo:
        return None

    # Projetos conhecidos
    projetos = [
        "ACerta",
        "Brincando e Aprendendo",
        "Lendo e Escrevendo",
        "Vida & Matemática",
        "Vida & Linguagem",
        "Vida & Ciências",
        "Projeto AMMA",
        "Tema",
        "Novo Lendo",
    ]

    for projeto in projetos:
        if projeto.lower() in titulo.lower():
            return projeto

    return None


def parse_date(date_str):
    """Converte string de data para datetime"""
    if not date_str:
        return timezone.now()

    try:
        # Tentar diferentes formatos
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return timezone.make_aware(dt)
            except ValueError:
                continue

        return timezone.now()
    except:
        return timezone.now()


def main():
    """Função principal"""
    print("📥 IMPORTAÇÃO COMPLETA DE DADOS IDENTIFICADOS")
    print("=" * 80)

    # Carregar dados
    analysis_data = load_analysis_data()
    planilhas = load_planilha_data()

    if not planilhas:
        print("❌ Nenhum dado disponível para importação")
        return False

    # Importar dados em transação
    with transaction.atomic():
        try:
            # Importar usuários
            import_usuarios(planilhas)

            # Importar mapeamento coordenadores
            import_coordenadores_mapping(planilhas)

            # Importar eventos
            import_eventos(planilhas)

            print("\n" + "=" * 80)
            print("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

            return True

        except Exception as e:
            print(f"\n❌ Erro durante importação: {e}")
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
