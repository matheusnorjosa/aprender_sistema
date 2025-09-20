"""
Comando Django para deduplicação inteligente de usuários
Remove duplicatas priorizando emails reais, CPFs válidos e dados mais completos.
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from core.models import Usuario

class Command(BaseCommand):
    help = 'Remove usuários duplicados priorizando dados mais completos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula a execução sem fazer alterações no banco'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Exibe logs detalhados das operações'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']

        self.stdout.write(
            self.style.SUCCESS(f'\n{"="*60}')
        )
        self.stdout.write(
            self.style.SUCCESS('🧹 DEDUPLICAÇÃO INTELIGENTE DE USUÁRIOS')
        )
        self.stdout.write(
            self.style.SUCCESS(f'{"="*60}\n')
        )

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  MODO SIMULAÇÃO - Nenhuma alteração será feita\n')
            )

        # Estatísticas iniciais
        total_users_before = Usuario.objects.count()
        self.stdout.write(f'👥 Usuários antes da limpeza: {total_users_before}')

        # Executar limpeza
        with transaction.atomic():
            stats = self._perform_deduplication()

            if self.dry_run:
                # Reverter transação no modo dry-run
                transaction.set_rollback(True)

        # Estatísticas finais
        total_users_after = Usuario.objects.count() if not self.dry_run else total_users_before

        self._print_final_stats(stats, total_users_before, total_users_after)

    def _perform_deduplication(self):
        """Executa o processo completo de deduplicação"""
        stats = {
            'concatenated_removed': 0,
            'duplicates_merged': 0,
            'users_removed': 0,
            'groups_merged': 0,
            'operations': []
        }

        # ETAPA 1: Remover concatenações
        stats['concatenated_removed'] = self._remove_concatenated_entries(stats)

        # ETAPA 2: Identificar e mesclar duplicatas
        stats['duplicates_merged'] = self._merge_duplicate_users(stats)

        return stats

    def _remove_concatenated_entries(self, stats):
        """Remove entradas com nomes concatenados (ex: 'Nome1 - Nome2 - Nome3')"""
        concatenated_users = Usuario.objects.filter(first_name__contains=' - ')
        count = concatenated_users.count()

        if self.verbose:
            self.stdout.write(f'\n🔍 Encontradas {count} entradas concatenadas para remoção:')

        for user in concatenated_users:
            if self.verbose:
                self.stdout.write(f'  ❌ Removendo: "{user.first_name}" (ID: {user.id})')

            stats['operations'].append({
                'type': 'concatenated_removal',
                'user_id': user.id,
                'name': f'{user.first_name} {user.last_name}',
                'email': user.email
            })

            if not self.dry_run:
                user.delete()

        return count

    def _merge_duplicate_users(self, stats):
        """Identifica e mescla usuários duplicados"""
        # Agrupar usuários por similaridade de nome
        name_groups = self._group_users_by_name()

        duplicate_groups = {key: users for key, users in name_groups.items() if len(users) > 1}

        if self.verbose:
            self.stdout.write(f'\n🔍 Encontrados {len(duplicate_groups)} grupos de potenciais duplicatas:')

        merged_count = 0
        for group_key, users in duplicate_groups.items():
            if len(users) > 1:
                merged_count += self._merge_user_group(group_key, users, stats)

        return merged_count

    def _group_users_by_name(self):
        """Agrupa usuários por similaridade de nome"""
        name_groups = defaultdict(list)

        # Excluir usuários concatenados (já serão removidos)
        users = Usuario.objects.exclude(first_name__contains=' - ')

        for user in users:
            # Normalizar nome para comparação
            clean_name = self._normalize_name(user.first_name, user.last_name)
            name_groups[clean_name].append(user)

        return name_groups

    def _normalize_name(self, first_name, last_name):
        """Normaliza nomes para identificação de duplicatas"""
        full_name = f'{first_name} {last_name}'.strip().lower()

        # Remover acentos e caracteres especiais
        clean_name = re.sub(r'[^\w\s]', '', full_name)

        # Usar as primeiras 2 palavras como chave
        words = clean_name.split()
        if len(words) >= 2:
            return f'{words[0]} {words[1]}'
        elif len(words) == 1:
            return words[0]
        else:
            return 'unnamed'

    def _merge_user_group(self, group_key, users, stats):
        """Mescla um grupo de usuários duplicados"""
        if len(users) <= 1:
            return 0

        # Ordenar usuários por prioridade (melhor primeiro)
        sorted_users = sorted(users, key=self._user_priority_score, reverse=True)

        primary_user = sorted_users[0]  # Usuário que será mantido
        duplicate_users = sorted_users[1:]  # Usuários que serão removidos

        if self.verbose:
            self.stdout.write(f'\n📝 Mesclando grupo "{group_key}" ({len(users)} usuários):')
            self.stdout.write(f'  ✅ MANTENDO: {primary_user.first_name} {primary_user.last_name} '
                             f'(ID: {primary_user.id}) | Email: {primary_user.email} | CPF: {primary_user.cpf or "None"}')

        # Mesclar dados dos duplicados no usuário principal
        self._merge_user_data(primary_user, duplicate_users, stats)

        # Remover usuários duplicados
        for user in duplicate_users:
            if self.verbose:
                self.stdout.write(f'  ❌ REMOVENDO: {user.first_name} {user.last_name} '
                                 f'(ID: {user.id}) | Email: {user.email} | CPF: {user.cpf or "None"}')

            stats['operations'].append({
                'type': 'duplicate_merge',
                'primary_user_id': primary_user.id,
                'removed_user_id': user.id,
                'primary_name': f'{primary_user.first_name} {primary_user.last_name}',
                'removed_name': f'{user.first_name} {user.last_name}',
                'primary_email': primary_user.email,
                'removed_email': user.email
            })

            if not self.dry_run:
                user.delete()

            stats['users_removed'] += 1

        return 1  # 1 grupo mesclado

    def _user_priority_score(self, user):
        """Calcula pontuação de prioridade para um usuário (maior = melhor)"""
        score = 0

        # Prioridade 1: Email real (não @planilha.x)
        if user.email and '@planilha.' not in user.email and user.email != '':
            score += 100
        elif user.email and '@planilha.' in user.email:
            score += 50

        # Prioridade 2: CPF preenchido
        if user.cpf and user.cpf.strip():
            score += 20

        # Prioridade 3: Nome completo (last_name preenchido)
        if user.last_name and user.last_name.strip():
            score += 10

        # Prioridade 4: Primeiro nome mais longo (mais específico)
        if user.first_name:
            score += len(user.first_name.strip())

        # Prioridade 5: Grupos atribuídos
        score += user.groups.count() * 5

        return score

    def _merge_user_data(self, primary_user, duplicate_users, stats):
        """Mescla dados dos usuários duplicados no usuário principal"""
        original_groups = set(primary_user.groups.all())

        for duplicate in duplicate_users:
            # Mesclar grupos
            for group in duplicate.groups.all():
                if group not in original_groups:
                    if not self.dry_run:
                        primary_user.groups.add(group)
                    stats['groups_merged'] += 1
                    original_groups.add(group)

            # Atualizar dados se o duplicado tiver informações melhores
            if not primary_user.cpf and duplicate.cpf:
                if not self.dry_run:
                    primary_user.cpf = duplicate.cpf

            if not primary_user.telefone and duplicate.telefone:
                if not self.dry_run:
                    primary_user.telefone = duplicate.telefone

            # Manter o nome mais completo
            if len(duplicate.last_name or '') > len(primary_user.last_name or ''):
                if not self.dry_run:
                    primary_user.last_name = duplicate.last_name

        if not self.dry_run:
            primary_user.save()

    def _print_final_stats(self, stats, before_count, after_count):
        """Exibe estatísticas finais da operação"""
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('📊 RELATÓRIO FINAL DE DEDUPLICAÇÃO'))
        self.stdout.write(f'{"="*60}')

        self.stdout.write(f'👥 Usuários antes: {before_count}')
        self.stdout.write(f'👥 Usuários depois: {after_count}')
        self.stdout.write(f'🧹 Redução: {before_count - after_count} usuários removidos')
        self.stdout.write(f'📝 Entradas concatenadas removidas: {stats["concatenated_removed"]}')
        self.stdout.write(f'🔄 Grupos de duplicatas mesclados: {stats["duplicates_merged"]}')
        self.stdout.write(f'👤 Usuários individuais removidos: {stats["users_removed"]}')
        self.stdout.write(f'🏷️  Grupos de permissão mesclados: {stats["groups_merged"]}')

        if self.dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  SIMULAÇÃO CONCLUÍDA - Nenhuma alteração foi feita'))
            self.stdout.write('Execute sem --dry-run para aplicar as mudanças')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ DEDUPLICAÇÃO CONCLUÍDA COM SUCESSO!'))

        # Salvar relatório detalhado
        self._save_detailed_report(stats, before_count, after_count)

    def _save_detailed_report(self, stats, before_count, after_count):
        """Salva relatório detalhado em JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'dry_run' if self.dry_run else 'execution',
            'summary': {
                'users_before': before_count,
                'users_after': after_count,
                'users_removed': before_count - after_count,
                'concatenated_removed': stats['concatenated_removed'],
                'duplicates_merged': stats['duplicates_merged'],
                'individual_users_removed': stats['users_removed'],
                'groups_merged': stats['groups_merged']
            },
            'operations': stats['operations']
        }

        filename = f'relatorio_deduplicacao_{"dry_run_" if self.dry_run else ""}{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f'📄 Relatório detalhado salvo: {filename}')