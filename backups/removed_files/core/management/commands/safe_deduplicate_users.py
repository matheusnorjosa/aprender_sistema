"""
Comando seguro para deduplicação de usuários
Usa apenas ORM Django para evitar conflitos de migração
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
    help = 'Remove usuários duplicados de forma segura usando apenas ORM'

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
            self.style.SUCCESS(f'\n{"="*70}')
        )
        self.stdout.write(
            self.style.SUCCESS('🧹 DEDUPLICAÇÃO SEGURA DE USUÁRIOS (ORM)')
        )
        self.stdout.write(
            self.style.SUCCESS(f'{"="*70}\n')
        )

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  MODO SIMULAÇÃO - Nenhuma alteração será feita\n')
            )

        # Estatísticas iniciais
        total_users_before = Usuario.objects.count()
        self.stdout.write(f'👥 Usuários antes da limpeza: {total_users_before}')

        # Executar limpeza por lotes menores para evitar problemas
        stats = self._perform_safe_deduplication()

        # Estatísticas finais
        total_users_after = Usuario.objects.count() if not self.dry_run else total_users_before

        self._print_final_stats(stats, total_users_before, total_users_after)

    def _perform_safe_deduplication(self):
        """Executa deduplicação segura por lotes"""
        stats = {
            'concatenated_removed': 0,
            'duplicates_merged': 0,
            'users_removed': 0,
            'groups_merged': 0,
            'operations': [],
            'errors': []
        }

        # ETAPA 1: Remover concatenações primeiro (são mais fáceis)
        stats['concatenated_removed'] = self._remove_concatenated_entries_safe(stats)

        # ETAPA 2: Processar duplicatas em lotes pequenos
        stats['duplicates_merged'] = self._merge_duplicates_in_batches(stats)

        return stats

    def _remove_concatenated_entries_safe(self, stats):
        """Remove entradas concatenadas usando ORM"""
        concatenated_users = Usuario.objects.filter(first_name__contains=' - ')
        count = concatenated_users.count()

        if self.verbose:
            self.stdout.write(f'\n🔍 Encontradas {count} entradas concatenadas para remoção:')

        removed_count = 0
        for user in concatenated_users:
            if self.verbose:
                self.stdout.write(f'  ❌ Removendo: "{user.first_name}" (ID: {user.id})')

            stats['operations'].append({
                'type': 'concatenated_removal',
                'user_id': str(user.id),
                'name': f'{user.first_name} {user.last_name}',
                'email': user.email
            })

            if not self.dry_run:
                try:
                    # Primeiro limpar grupos
                    user.groups.clear()
                    # Depois deletar
                    user.delete()
                    removed_count += 1
                except Exception as e:
                    error_msg = f'Erro ao remover usuário {user.id}: {e}'
                    stats['errors'].append(error_msg)
                    if self.verbose:
                        self.stdout.write(self.style.ERROR(f'    ⚠️ {error_msg}'))
            else:
                removed_count += 1

        return removed_count

    def _merge_duplicates_in_batches(self, stats):
        """Processa duplicatas em lotes pequenos"""
        # Recarregar usuários após remoção de concatenados
        users = Usuario.objects.exclude(first_name__contains=' - ')

        # Agrupar por nome
        name_groups = self._group_users_by_name(users)
        duplicate_groups = {key: users for key, users in name_groups.items() if len(users) > 1}

        if self.verbose:
            self.stdout.write(f'\n🔍 Encontrados {len(duplicate_groups)} grupos de duplicatas:')

        merged_count = 0
        batch_size = 5  # Processar apenas 5 grupos por vez

        # Processar em lotes pequenos
        items = list(duplicate_groups.items())
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]

            if self.verbose:
                self.stdout.write(f'\n📦 Processando lote {(i//batch_size)+1} ({len(batch)} grupos):')

            for group_key, user_list in batch:
                try:
                    merged_count += self._merge_user_group_safe(group_key, user_list, stats)
                except Exception as e:
                    error_msg = f'Erro ao processar grupo {group_key}: {e}'
                    stats['errors'].append(error_msg)
                    if self.verbose:
                        self.stdout.write(self.style.ERROR(f'    ⚠️ {error_msg}'))

        return merged_count

    def _group_users_by_name(self, users):
        """Agrupa usuários por similaridade de nome"""
        name_groups = defaultdict(list)

        for user in users:
            clean_name = self._normalize_name(user.first_name, user.last_name)
            name_groups[clean_name].append(user)

        return name_groups

    def _normalize_name(self, first_name, last_name):
        """Normaliza nomes para identificação de duplicatas"""
        full_name = f'{first_name} {last_name}'.strip().lower()
        clean_name = re.sub(r'[^\w\s]', '', full_name)
        words = clean_name.split()

        if len(words) >= 2:
            return f'{words[0]} {words[1]}'
        elif len(words) == 1:
            return words[0]
        else:
            return 'unnamed'

    def _merge_user_group_safe(self, group_key, users, stats):
        """Mescla um grupo de usuários de forma segura"""
        if len(users) <= 1:
            return 0

        # Ordenar por prioridade
        sorted_users = sorted(users, key=self._user_priority_score, reverse=True)
        primary_user = sorted_users[0]
        duplicate_users = sorted_users[1:]

        if self.verbose:
            self.stdout.write(f'  📝 Mesclando "{group_key}" ({len(users)} usuários):')
            self.stdout.write(f'    ✅ MANTENDO: {primary_user.first_name} {primary_user.last_name} '
                             f'(ID: {primary_user.id}) | Email: {primary_user.email}')

        # Mesclar dados primeiro
        if not self.dry_run:
            self._merge_user_data_safe(primary_user, duplicate_users, stats)

        # Remover duplicados um por vez
        for user in duplicate_users:
            if self.verbose:
                self.stdout.write(f'    ❌ REMOVENDO: {user.first_name} {user.last_name} '
                                 f'(ID: {user.id}) | Email: {user.email}')

            stats['operations'].append({
                'type': 'duplicate_merge',
                'primary_user_id': str(primary_user.id),
                'removed_user_id': str(user.id),
                'primary_name': f'{primary_user.first_name} {primary_user.last_name}',
                'removed_name': f'{user.first_name} {user.last_name}',
                'primary_email': primary_user.email,
                'removed_email': user.email
            })

            if not self.dry_run:
                try:
                    # Limpar relacionamentos primeiro
                    user.groups.clear()

                    # Tentar deletar o usuário
                    user.delete()
                    stats['users_removed'] += 1

                except Exception as e:
                    error_msg = f'Erro ao remover usuário {user.id}: {e}'
                    stats['errors'].append(error_msg)
                    if self.verbose:
                        self.stdout.write(self.style.ERROR(f'      ⚠️ {error_msg}'))
            else:
                stats['users_removed'] += 1

        return 1

    def _user_priority_score(self, user):
        """Calcula pontuação de prioridade"""
        score = 0

        # Email real vs gerado
        if user.email and '@planilha.' not in user.email and user.email != '':
            score += 100
        elif user.email and '@planilha.' in user.email:
            score += 50

        # CPF preenchido
        if user.cpf and user.cpf.strip():
            score += 20

        # Nome completo
        if user.last_name and user.last_name.strip():
            score += 10

        # Nome mais específico
        if user.first_name:
            score += len(user.first_name.strip())

        # Grupos
        score += user.groups.count() * 5

        return score

    def _merge_user_data_safe(self, primary_user, duplicate_users, stats):
        """Mescla dados de forma segura"""
        original_groups = set(primary_user.groups.all())

        for duplicate in duplicate_users:
            # Mesclar grupos
            for group in duplicate.groups.all():
                if group not in original_groups:
                    primary_user.groups.add(group)
                    stats['groups_merged'] += 1
                    original_groups.add(group)

            # Mesclar dados melhores
            if not primary_user.cpf and duplicate.cpf:
                primary_user.cpf = duplicate.cpf

            if not primary_user.telefone and duplicate.telefone:
                primary_user.telefone = duplicate.telefone

            if len(duplicate.last_name or '') > len(primary_user.last_name or ''):
                primary_user.last_name = duplicate.last_name

        primary_user.save()

    def _print_final_stats(self, stats, before_count, after_count):
        """Exibe estatísticas finais"""
        self.stdout.write(f'\n{"="*70}')
        self.stdout.write(self.style.SUCCESS('📊 RELATÓRIO FINAL - DEDUPLICAÇÃO SEGURA'))
        self.stdout.write(f'{"="*70}')

        self.stdout.write(f'👥 Usuários antes: {before_count}')
        self.stdout.write(f'👥 Usuários depois: {after_count}')
        self.stdout.write(f'🧹 Redução: {before_count - after_count} usuários removidos')
        self.stdout.write(f'📝 Entradas concatenadas removidas: {stats["concatenated_removed"]}')
        self.stdout.write(f'🔄 Grupos de duplicatas mesclados: {stats["duplicates_merged"]}')
        self.stdout.write(f'👤 Usuários individuais removidos: {stats["users_removed"]}')
        self.stdout.write(f'🏷️  Grupos de permissão mesclados: {stats["groups_merged"]}')
        self.stdout.write(f'⚠️  Erros encontrados: {len(stats["errors"])}')

        if stats['errors'] and self.verbose:
            self.stdout.write(f'\n❌ ERROS DETALHADOS:')
            for error in stats['errors'][:10]:  # Mostrar apenas os primeiros 10
                self.stdout.write(f'  - {error}')

        if self.dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  SIMULAÇÃO CONCLUÍDA - Nenhuma alteração foi feita'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ DEDUPLICAÇÃO SEGURA CONCLUÍDA!'))

        # Salvar relatório
        self._save_detailed_report(stats, before_count, after_count)

    def _save_detailed_report(self, stats, before_count, after_count):
        """Salva relatório detalhado"""
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
                'groups_merged': stats['groups_merged'],
                'errors_count': len(stats['errors'])
            },
            'operations': stats['operations'],
            'errors': stats['errors']
        }

        filename = f'relatorio_safe_deduplicacao_{"dry_run_" if self.dry_run else ""}{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f'📄 Relatório detalhado salvo: {filename}')