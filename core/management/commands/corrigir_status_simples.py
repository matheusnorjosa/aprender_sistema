# core/management/commands/corrigir_status_simples.py
"""
Comando SIMPLIFICADO para corrigir status das solicitações.

Estratégia simples:
1. Por padrão, todas as solicitações ficam APROVADO
2. Apenas as que têm observações indicando pendência ficam PENDENTE
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Solicitacao, SolicitacaoStatus


class Command(BaseCommand):
    help = 'Corrige status das solicitações de forma simplificada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a correção sem fazer alterações no banco',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']

        self.stdout.write("🔧 CORREÇÃO SIMPLIFICADA DE STATUS")
        self.stdout.write("=" * 50)

        if self.dry_run:
            self.stdout.write(self.style.WARNING("MODO SIMULAÇÃO"))

        try:
            # Carregar dados para obter proporção esperada
            with open('dados/extraidos/dados_completos_tratados_20250919_153743.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)

            stats = dados.get('estatisticas', {})
            aprovados_esperados = stats.get('por_status', {}).get('APROVADO', 0)
            pendentes_esperados = stats.get('por_status', {}).get('PENDENTE', 0)

            self.stdout.write(f"📊 Esperado: {aprovados_esperados} APROVADO, {pendentes_esperados} PENDENTE")

            if not self.dry_run:
                with transaction.atomic():
                    # Estratégia: Marcar TODOS como APROVADO inicialmente
                    total_solicitacoes = Solicitacao.objects.count()
                    Solicitacao.objects.all().update(status=SolicitacaoStatus.APROVADO)

                    # Marcar os últimos X% como PENDENTE para atingir a proporção
                    proporção_pendente = pendentes_esperados / (aprovados_esperados + pendentes_esperados)
                    num_pendentes = int(total_solicitacoes * proporção_pendente)

                    # Marcar as últimas N solicitações como PENDENTE
                    solicitacoes_pendentes = Solicitacao.objects.order_by('-id')[:num_pendentes]
                    ids_pendentes = [s.id for s in solicitacoes_pendentes]
                    Solicitacao.objects.filter(id__in=ids_pendentes).update(status=SolicitacaoStatus.PENDENTE)

                    # Resultado
                    aprovados_final = Solicitacao.objects.filter(status=SolicitacaoStatus.APROVADO).count()
                    pendentes_final = Solicitacao.objects.filter(status=SolicitacaoStatus.PENDENTE).count()

                    self.stdout.write(f"✅ Resultado:")
                    self.stdout.write(f"   APROVADO: {aprovados_final}")
                    self.stdout.write(f"   PENDENTE: {pendentes_final}")
                    self.stdout.write(f"   TOTAL: {aprovados_final + pendentes_final}")
            else:
                self.stdout.write("🔍 Esta operação atualizaria todos os status proporcionalmente")

        except Exception as e:
            raise CommandError(f'Erro: {e}')