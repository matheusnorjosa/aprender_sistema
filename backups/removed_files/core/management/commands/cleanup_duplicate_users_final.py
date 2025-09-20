"""
Comando final para limpeza de usuários duplicados
Remove apenas usuários sem relacionamentos críticos
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from core.models import Usuario

class Command(BaseCommand):
    help = 'Remove usuários duplicados finais sem relacionamentos críticos'

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
            self.style.SUCCESS('🧹 LIMPEZA FINAL DE USUÁRIOS DUPLICADOS')
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

        # Executar limpeza seletiva
        stats = self._perform_selective_cleanup()

        # Estatísticas finais
        total_users_after = Usuario.objects.count() if not self.dry_run else total_users_before

        self._print_final_stats(stats, total_users_before, total_users_after)

    def _perform_selective_cleanup(self):
        """Remove apenas usuários seguros de serem removidos"""
        stats = {
            'duplicates_found': 0,
            'users_removed': 0,
            'users_skipped': 0,
            'operations': [],
            'errors': []
        }

        # Identificar duplicatas
        name_groups = self._group_users_by_name()
        duplicate_groups = {key: users for key, users in name_groups.items() if len(users) > 1}

        if self.verbose:
            self.stdout.write(f'\n🔍 Encontrados {len(duplicate_groups)} grupos de duplicatas')

        stats['duplicates_found'] = len(duplicate_groups)

        for group_key, user_list in duplicate_groups.items():
            if len(user_list) > 1:
                self._process_duplicate_group_selective(group_key, user_list, stats)

        return stats

    def _group_users_by_name(self):
        """Agrupa usuários por nome"""
        name_groups = defaultdict(list)
        users = Usuario.objects.all()

        for user in users:
            clean_name = self._normalize_name(user.first_name, user.last_name)
            name_groups[clean_name].append(user)

        return name_groups

    def _normalize_name(self, first_name, last_name):
        """Normaliza nomes"""
        full_name = f'{first_name} {last_name}'.strip().lower()
        clean_name = re.sub(r'[^\w\s]', '', full_name)
        words = clean_name.split()

        if len(words) >= 2:
            return f'{words[0]} {words[1]}'
        elif len(words) == 1:
            return words[0]
        else:
            return 'unnamed'

    def _process_duplicate_group_selective(self, group_key, users, stats):
        """Processa grupo de duplicatas de forma seletiva"""
        if len(users) <= 1:
            return

        # Ordenar por prioridade
        sorted_users = sorted(users, key=self._user_priority_score, reverse=True)
        primary_user = sorted_users[0]
        duplicate_users = sorted_users[1:]

        if self.verbose:
            self.stdout.write(f'\n📝 Processando "{group_key}" ({len(users)} usuários):')
            self.stdout.write(f'  ✅ MANTENDO: {primary_user.first_name} {primary_user.last_name} '
                             f'(ID: {primary_user.id}) | Email: {primary_user.email}')

        # Tentar remover duplicados de forma seletiva
        for user in duplicate_users:
            can_remove = self._can_safely_remove_user(user)

            if can_remove:
                if self.verbose:
                    self.stdout.write(f'  ❌ REMOVENDO: {user.first_name} {user.last_name} '
                                     f'(ID: {user.id}) | Email: {user.email}')

                stats['operations'].append({
                    'type': 'safe_removal',
                    'removed_user_id': str(user.id),
                    'removed_name': f'{user.first_name} {user.last_name}',
                    'removed_email': user.email,
                    'primary_user_id': str(primary_user.id),
                    'primary_name': f'{primary_user.first_name} {primary_user.last_name}'
                })

                if not self.dry_run:
                    try:
                        # Limpar grupos primeiro
                        user.groups.clear()
                        # Deletar usuário
                        user.delete()
                        stats['users_removed'] += 1
                    except Exception as e:
                        error_msg = f'Erro ao remover usuário {user.id}: {e}'
                        stats['errors'].append(error_msg)
                        if self.verbose:
                            self.stdout.write(self.style.ERROR(f'    ⚠️ {error_msg}'))
                else:
                    stats['users_removed'] += 1
            else:
                if self.verbose:
                    self.stdout.write(f'  ⚠️ PULANDO: {user.first_name} {user.last_name} '
                                     f'(ID: {user.id}) - Tem relacionamentos críticos')
                stats['users_skipped'] += 1

    def _can_safely_remove_user(self, user):
        """Verifica se um usuário pode ser removido com segurança"""
        with connection.cursor() as cursor:
            # Verificar se há relacionamentos críticos

            # 1. Verificar core_formadoressolicitacao (problema conhecido)
            try:
                cursor.execute("SELECT COUNT(*) FROM core_formadoressolicitacao WHERE formador_id = %s", [str(user.id)])
                if cursor.fetchone()[0] > 0:
                    return False
            except:
                # Se der erro (campo não existe), é seguro continuar
                pass

            # 2. Verificar core_formador
            try:
                cursor.execute("SELECT COUNT(*) FROM core_formador WHERE usuario_id = %s", [str(user.id)])
                if cursor.fetchone()[0] > 0:
                    return False
            except:
                pass

            # 3. Verificar core_disponibilidadeformadores
            try:
                cursor.execute("SELECT COUNT(*) FROM core_disponibilidadeformadores WHERE formador_id = %s", [str(user.id)])
                if cursor.fetchone()[0] > 0:
                    return False
            except:
                pass

            # 4. Verificar se tem grupos importantes (coordenação, superintendência)
            important_groups = user.groups.filter(name__in=['coordenador', 'superintendencia', 'admin']).count()
            if important_groups > 0:
                return False

            # 5. Verificar se tem email real (não deve ser removido se for o único com email real)
            if user.email and '@planilha.' not in user.email and user.email != '':
                # Este usuário tem email real, verificar se há outro com mesmo nome e email real
                same_name_users = Usuario.objects.filter(
                    first_name__icontains=user.first_name.split()[0],
                    last_name__icontains=user.last_name.split()[-1] if user.last_name else ''
                ).exclude(id=user.id)

                real_email_alternatives = same_name_users.exclude(email__contains='@planilha.').exclude(email='')
                if real_email_alternatives.count() == 0:
                    return False  # Não remover se for o único com email real

        return True  # Seguro para remover

    def _user_priority_score(self, user):
        """Calcula pontuação de prioridade"""
        score = 0

        # Email real
        if user.email and '@planilha.' not in user.email and user.email != '':
            score += 100
        elif user.email and '@planilha.' in user.email:
            score += 50

        # CPF
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

    def _print_final_stats(self, stats, before_count, after_count):
        """Exibe estatísticas finais"""
        self.stdout.write(f'\n{"="*70}')
        self.stdout.write(self.style.SUCCESS('📊 RELATÓRIO FINAL - LIMPEZA SELETIVA'))
        self.stdout.write(f'{"="*70}')

        self.stdout.write(f'👥 Usuários antes: {before_count}')
        self.stdout.write(f'👥 Usuários depois: {after_count}')
        self.stdout.write(f'🔍 Grupos de duplicatas encontrados: {stats["duplicates_found"]}')
        self.stdout.write(f'✅ Usuários removidos com segurança: {stats["users_removed"]}')
        self.stdout.write(f'⚠️ Usuários pulados (relacionamentos): {stats["users_skipped"]}')
        self.stdout.write(f'❌ Erros encontrados: {len(stats["errors"])}')

        if stats['errors'] and self.verbose:
            self.stdout.write(f'\n❌ ERROS DETALHADOS:')
            for error in stats['errors'][:5]:
                self.stdout.write(f'  - {error}')

        if self.dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  SIMULAÇÃO CONCLUÍDA - Nenhuma alteração foi feita'))
        else:
            if stats['users_removed'] > 0:
                self.stdout.write(self.style.SUCCESS(f'\n✅ LIMPEZA PARCIAL CONCLUÍDA! Removidos {stats["users_removed"]} usuários seguros'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠️ NENHUM USUÁRIO REMOVIDO - Todos têm relacionamentos críticos'))

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
                'duplicates_found': stats['duplicates_found'],
                'users_removed': stats['users_removed'],
                'users_skipped': stats['users_skipped'],
                'errors_count': len(stats['errors'])
            },
            'operations': stats['operations'],
            'errors': stats['errors']
        }

        filename = f'relatorio_cleanup_final_{"dry_run_" if self.dry_run else ""}{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f'📄 Relatório detalhado salvo: {filename}')