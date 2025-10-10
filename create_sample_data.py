#!/usr/bin/env python3
"""
Script para criar dados de exemplo para testar os gráficos do dashboard.
"""

import os
import sys
from datetime import datetime, timedelta
from random import choice, randint

import django

# Configuração do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.utils import timezone

from core.models import (
    Formador,
    FormadoresSolicitacao,
    Municipio,
    Projeto,
    Setor,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


def create_sample_data():
    """Cria dados de exemplo para testar gráficos"""

    print("=== Criando dados de exemplo ===")

    # Verificar se já existem dados
    if Solicitacao.objects.count() > 0:
        print("Ja existem solicitacoes no banco. Limpando...")
        Solicitacao.objects.all().delete()
        FormadoresSolicitacao.objects.all().delete()

    # Pegar dados existentes
    formadores = list(Formador.objects.filter(ativo=True)[:20])  # Apenas 20 para teste
    municipios = list(Municipio.objects.filter(ativo=True))
    projetos = list(Projeto.objects.filter(ativo=True))
    tipos_evento = list(TipoEvento.objects.all())
    usuarios = list(Usuario.objects.all()[:5])  # Poucos usuários para teste

    print(f"Formadores disponiveis: {len(formadores)}")
    print(f"Municipios disponiveis: {len(municipios)}")
    print(f"Projetos disponiveis: {len(projetos)}")
    print(f"Tipos evento disponiveis: {len(tipos_evento)}")

    if not all([formadores, municipios, projetos, tipos_evento, usuarios]):
        print("ERRO: Dados basicos nao encontrados!")
        return False

    # Criar solicitações dos últimos 12 meses
    today = timezone.now().date()
    solicitacoes_criadas = 0

    for mes_offset in range(12):  # 12 meses atrás até hoje
        # Data do mês
        data_mes = today - timedelta(days=30 * mes_offset)

        # Quantidade de eventos por mês (variação realista)
        num_eventos = randint(5, 25)  # Entre 5 e 25 eventos por mês

        print(f"\nCriando {num_eventos} eventos para {data_mes.strftime('%B %Y')}")

        for i in range(num_eventos):
            # Criar solicitação
            inicio_dia = timezone.make_aware(
                datetime.combine(data_mes, datetime.min.time())
            ) + timedelta(
                days=randint(0, 25),  # Dia do mês
                hours=randint(8, 17),  # Hora do evento
                minutes=choice([0, 30]),  # 0 ou 30 minutos
            )

            fim_evento = inicio_dia + timedelta(hours=randint(2, 6))  # Duração 2-6h

            solicitacao = Solicitacao.objects.create(
                usuario_solicitante=choice(usuarios),
                projeto=choice(projetos),
                municipio=choice(municipios),
                tipo_evento=choice(tipos_evento),
                titulo_evento=f"Evento Teste {i+1} - {data_mes.strftime('%b/%Y')}",
                observacoes=f"Observacoes do evento de teste para {data_mes.strftime('%B %Y')}",
                data_inicio=inicio_dia,
                data_fim=fim_evento,
                status=choice(
                    [
                        SolicitacaoStatus.APROVADO,  # 70%
                        SolicitacaoStatus.APROVADO,
                        SolicitacaoStatus.APROVADO,
                        SolicitacaoStatus.PENDENTE,  # 20%
                        SolicitacaoStatus.REPROVADO,  # 10%
                    ]
                ),
            )

            # Atualizar data_solicitacao manualmente (já que é auto_now_add)
            solicitacao.data_solicitacao = inicio_dia - timedelta(days=randint(1, 7))
            solicitacao.save()

            # Adicionar formadores à solicitação (1-3 formadores por evento)
            num_formadores = randint(1, 3)
            formadores_selecionados = (
                choice(formadores)
                if num_formadores == 1
                else list(set([choice(formadores) for _ in range(num_formadores)]))
            )

            if not isinstance(formadores_selecionados, list):
                formadores_selecionados = [formadores_selecionados]

            for formador in formadores_selecionados:
                FormadoresSolicitacao.objects.create(
                    solicitacao=solicitacao, formador=formador
                )

            solicitacoes_criadas += 1

    print(f"\n=== Dados criados com sucesso! ===")
    print(f"Total de solicitacoes: {solicitacoes_criadas}")
    print(
        f"Solicitacoes aprovadas: {Solicitacao.objects.filter(status=SolicitacaoStatus.APROVADO).count()}"
    )
    print(
        f"Solicitacoes pendentes: {Solicitacao.objects.filter(status=SolicitacaoStatus.PENDENTE).count()}"
    )
    print(
        f"Solicitacoes reprovadas: {Solicitacao.objects.filter(status=SolicitacaoStatus.REPROVADO).count()}"
    )

    return True


if __name__ == "__main__":
    print("=== Criacao de Dados de Exemplo para Dashboard ===")
    success = create_sample_data()
    if success:
        print("\nDados criados com sucesso! Os graficos devem funcionar agora.")
    else:
        print("\nErro ao criar dados!")
        sys.exit(1)
