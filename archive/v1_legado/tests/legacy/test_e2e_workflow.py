#!/usr/bin/env python
"""
Teste E2E: Coordenador -> Superintendencia -> Controle
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.models import (
    Aprovacao,
    AprovacaoStatus,
    Formador,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
)


def test_e2e_workflow():
    print("=== TESTE E2E: FLUXO COORDENADOR -> SUPERINTENDENCIA -> CONTROLE ===")

    # 1. AUTENTICAÇÃO DO COORDENADOR
    print("\n1. Testando autenticacao coordenador...")
    coord_user = authenticate(username="coordenador_teste", password="senha123")
    if coord_user:
        print(f"OK Coordenador autenticado: {coord_user.username}")
        print(f'OK Grupos: {list(coord_user.groups.values_list("name", flat=True))}')
    else:
        print("X Falha na autenticacao do coordenador")
        return False

    # 2. VERIFICAR DADOS NECESSÁRIOS
    print("\n2. Verificando dados necessarios...")
    formadores = Formador.objects.filter(ativo=True)[:2]
    municipio = Municipio.objects.first()
    projeto = Projeto.objects.first()
    tipo_evento = TipoEvento.objects.first()

    print(f"OK Formadores disponiveis: {[f.nome for f in formadores]}")
    print(f'OK Municipio: {municipio.nome if municipio else "Nenhum"}')
    print(f'OK Projeto: {projeto.nome if projeto else "Nenhum"}')
    print(f'OK Tipo Evento: {tipo_evento.nome if tipo_evento else "Nenhum"}')

    if not all([formadores.exists(), municipio, projeto, tipo_evento]):
        print("X Dados necessarios nao encontrados")
        return False

    # 3. COORDENADOR CRIA SOLICITAÇÃO
    print("\n3. Coordenador cria solicitacao...")

    data_inicio = timezone.now() + timedelta(days=7, hours=9)  # Próxima semana, 9h
    data_fim = data_inicio + timedelta(hours=4)  # 4 horas de duração

    try:
        with transaction.atomic():
            solicitacao = Solicitacao.objects.create(
                usuario_solicitante=coord_user,
                projeto=projeto,
                municipio=municipio,
                tipo_evento=tipo_evento,
                titulo_evento="Workshop Teste E2E",
                data_inicio=data_inicio,
                data_fim=data_fim,
                numero_encontro_formativo="1º Encontro",
                coordenador_acompanha=True,
                observacoes="Teste automatizado do fluxo E2E",
            )
            solicitacao.formadores.set(formadores)
            print(f"OK Solicitacao criada: ID {solicitacao.id}")
            print(f"OK Status inicial: {solicitacao.get_status_display()}")
    except Exception as e:
        print(f"X Erro ao criar solicitacao: {e}")
        return False

    # 4. SUPERINTENDÊNCIA APROVA
    print("\n4. Superintendencia aprova...")
    super_user = authenticate(username="super_teste", password="senha123")
    if not super_user:
        print("X Falha na autenticacao da superintendencia")
        return False

    print(f"OK Superintendencia autenticada: {super_user.username}")

    try:
        with transaction.atomic():
            aprovacao = Aprovacao.objects.create(
                solicitacao=solicitacao,
                usuario_aprovador=super_user,
                status_decisao=AprovacaoStatus.APROVADO,
                justificativa="Aprovado via teste E2E automatizado",
            )
            print(f"OK Aprovacao criada: ID {aprovacao.id}")
            print(f"OK Status: {aprovacao.get_status_decisao_display()}")
            print(f"OK Data aprovacao: {aprovacao.data_aprovacao}")
    except Exception as e:
        print(f"X Erro ao aprovar: {e}")
        return False

    # 5. CONTROLE MONITORA
    print("\n5. Controle monitora...")
    controle_user = authenticate(username="controle_teste", password="senha123")
    if not controle_user:
        print("X Falha na autenticacao do controle")
        return False

    print(f"OK Controle autenticado: {controle_user.username}")

    # Verificar solicitações aprovadas
    aprovadas = Solicitacao.objects.filter(
        aprovacoes__status_decisao=AprovacaoStatus.APROVADO
    ).distinct()

    print(f"OK Solicitacoes aprovadas encontradas: {aprovadas.count()}")
    for sol in aprovadas:
        print(
            f'  - ID {sol.id}: {sol.titulo_evento} ({sol.data_inicio.strftime("%d/%m %H:%M")})'
        )

    # 6. VERIFICAÇÃO FINAL
    print("\n6. Verificacao final...")
    sol_final = Solicitacao.objects.get(id=solicitacao.id)
    aprov_final = sol_final.aprovacoes.first()

    print(f"OK Solicitacao final - Status: {sol_final.get_status_display()}")
    print(f"OK Aprovacao final - Status: {aprov_final.get_status_decisao_display()}")
    print(f"OK Aprovado por: {aprov_final.usuario_aprovador.username}")
    print(f"OK Data aprovacao: {aprov_final.data_aprovacao}")

    print("\n=== TESTE E2E CONCLUÍDO COM SUCESSO ===")
    return True


if __name__ == "__main__":
    test_e2e_workflow()
