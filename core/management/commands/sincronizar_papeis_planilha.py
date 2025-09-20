"""
Comando Django para sincronizar papéis/grupos dos usuários baseado na planilha "Usuários".
Corrige discrepâncias entre os cargos definidos na planilha e os grupos no sistema.
"""

import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction
from core.models import Usuario


class Command(BaseCommand):
    help = 'Sincroniza papéis/grupos dos usuários baseado na planilha Usuários oficial'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa em modo simulação sem fazer alterações'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra informações detalhadas do processo'
        )
        parser.add_argument(
            '--planilha-file',
            type=str,
            default='archive/temp_data/extracted_usuarios.json',
            help='Caminho para arquivo JSON da planilha de usuários'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        planilha_file = options['planilha_file']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO SIMULACAO - Nenhuma alteracao sera feita')
            )

        # Carregar dados da planilha
        try:
            with open(planilha_file, 'r', encoding='utf-8') as f:
                planilha_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'Arquivo da planilha nao encontrado: {planilha_file}')
            )
            return
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR(f'Erro ao ler arquivo JSON: {planilha_file}')
            )
            return

        # Garantir que todos os grupos existem
        grupos_necessarios = ['coordenador', 'superintendencia', 'controle', 'formador', 'diretoria', 'admin']
        for grupo_nome in grupos_necessarios:
            grupo, created = Group.objects.get_or_create(name=grupo_nome)
            if created and verbose:
                self.stdout.write(f"Grupo '{grupo_nome}' criado")

        # Mapeamento de cargos da planilha para grupos do sistema
        cargo_para_grupo = {
            'Coordenadores': 'coordenador',
            'Superintendência': 'superintendencia',
            'Gerentes': 'superintendencia',
            'Controle': 'controle',
            'Formadores': 'formador',
            'Diretoria': 'diretoria',
            'Admin': 'admin'
        }

        estatisticas = {
            'usuarios_atualizados': 0,
            'usuarios_nao_encontrados': 0,
            'erros': 0,
            'cargos_nao_mapeados': set(),
            'alteracoes': []
        }

        with transaction.atomic():
            if dry_run:
                sid = transaction.savepoint()

            # Processar dados da planilha
            if 'worksheets' in planilha_data and 'Ativos' in planilha_data['worksheets']:
                dados_ativos = planilha_data['worksheets']['Ativos']['data']
                headers = planilha_data['worksheets']['Ativos']['headers']

                # Mapear índices das colunas
                try:
                    idx_nome = headers.index('Nome')
                    idx_cpf = headers.index('CPF')
                    idx_cargo = headers.index('Cargo')
                    idx_email = headers.index('Email')
                except ValueError as e:
                    self.stdout.write(
                        self.style.ERROR(f'Coluna nao encontrada no header: {str(e)}')
                    )
                    return

                for linha in dados_ativos:
                    if len(linha) <= max(idx_nome, idx_cpf, idx_cargo, idx_email):
                        continue

                    nome = linha[idx_nome].strip()
                    cpf = linha[idx_cpf].strip() if linha[idx_cpf] else ''
                    cargo_planilha = linha[idx_cargo].strip()
                    email = linha[idx_email].strip() if linha[idx_email] else ''

                    # Limpar CPF (apenas números)
                    cpf_limpo = ''.join(filter(str.isdigit, cpf)) if cpf else ''

                    if not nome:
                        continue

                    # Mapear cargo da planilha para grupo do sistema
                    grupo_alvo = cargo_para_grupo.get(cargo_planilha)
                    if not grupo_alvo:
                        estatisticas['cargos_nao_mapeados'].add(cargo_planilha)
                        continue

                    try:
                        # Buscar usuário no sistema
                        usuario = None

                        # 1. Tentar por CPF (mais confiável)
                        if cpf_limpo and len(cpf_limpo) == 11:
                            try:
                                usuario = Usuario.objects.get(cpf=cpf_limpo)
                                if verbose:
                                    self.stdout.write(f"Usuario encontrado por CPF: {nome}")
                            except Usuario.DoesNotExist:
                                pass

                        # 2. Tentar por email
                        if not usuario and email:
                            try:
                                usuario = Usuario.objects.get(email=email)
                                if verbose:
                                    self.stdout.write(f"Usuario encontrado por email: {nome}")
                            except Usuario.DoesNotExist:
                                pass

                        # 3. Tentar por nome (busca flexível)
                        if not usuario:
                            nome_parts = nome.split()
                            if len(nome_parts) >= 2:
                                # Buscar por primeiro e último nome
                                primeiro_nome = nome_parts[0]
                                ultimo_nome = nome_parts[-1]

                                usuarios_similares = Usuario.objects.filter(
                                    first_name__icontains=primeiro_nome,
                                    last_name__icontains=ultimo_nome
                                )

                                if usuarios_similares.count() == 1:
                                    usuario = usuarios_similares.first()
                                    if verbose:
                                        self.stdout.write(f"Usuario encontrado por nome: {nome}")

                        if not usuario:
                            estatisticas['usuarios_nao_encontrados'] += 1
                            if verbose:
                                self.stdout.write(f"AVISO: Usuario nao encontrado: {nome} (CPF: {cpf_limpo}, Email: {email})")
                            continue

                        # Verificar se já está no grupo correto
                        grupo_atual = list(usuario.groups.all().values_list('name', flat=True))

                        if grupo_alvo not in grupo_atual:
                            alteracao = {
                                'usuario': usuario.nome_completo,
                                'cargo_planilha': cargo_planilha,
                                'grupo_anterior': grupo_atual,
                                'grupo_novo': grupo_alvo
                            }
                            estatisticas['alteracoes'].append(alteracao)

                            if verbose:
                                self.stdout.write(
                                    f"ALTERANDO: {usuario.nome_completo} "
                                    f"({grupo_atual} -> {grupo_alvo})"
                                )

                            if not dry_run:
                                # Limpar grupos relacionados a cargos (manter outros como formador se aplicável)
                                grupos_cargo = ['coordenador', 'superintendencia', 'controle', 'diretoria']
                                for grupo_cargo in grupos_cargo:
                                    try:
                                        grupo_obj = Group.objects.get(name=grupo_cargo)
                                        usuario.groups.remove(grupo_obj)
                                    except Group.DoesNotExist:
                                        pass

                                # Adicionar ao grupo correto
                                grupo_obj = Group.objects.get(name=grupo_alvo)
                                usuario.groups.add(grupo_obj)

                                # Atualizar campo cargo
                                if grupo_alvo == 'coordenador':
                                    usuario.cargo = 'coordenador'
                                elif grupo_alvo == 'superintendencia':
                                    usuario.cargo = 'gerente'
                                elif grupo_alvo == 'controle':
                                    usuario.cargo = 'controle'
                                elif grupo_alvo == 'diretoria':
                                    usuario.cargo = 'outros'
                                # Manter formador_ativo=True se aplicável
                                elif grupo_alvo == 'formador':
                                    usuario.cargo = 'formador'
                                    usuario.formador_ativo = True

                                usuario.save()

                            estatisticas['usuarios_atualizados'] += 1

                        elif verbose:
                            self.stdout.write(f"OK: {usuario.nome_completo} ja esta no grupo correto ({grupo_alvo})")

                    except Exception as e:
                        estatisticas['erros'] += 1
                        self.stdout.write(
                            self.style.ERROR(f"Erro ao processar {nome}: {str(e)}")
                        )

            if dry_run:
                transaction.savepoint_rollback(sid)

        # Relatório final
        self.stdout.write(f"\nRELATORIO DE SINCRONIZACAO:")
        self.stdout.write(f"   Usuarios atualizados: {estatisticas['usuarios_atualizados']}")
        self.stdout.write(f"   Usuarios nao encontrados: {estatisticas['usuarios_nao_encontrados']}")
        self.stdout.write(f"   Erros: {estatisticas['erros']}")

        if estatisticas['cargos_nao_mapeados']:
            self.stdout.write(f"\nCargos nao mapeados encontrados:")
            for cargo in estatisticas['cargos_nao_mapeados']:
                self.stdout.write(f"   - {cargo}")

        if verbose and estatisticas['alteracoes']:
            self.stdout.write(f"\nAlteracoes realizadas:")
            for alt in estatisticas['alteracoes'][:10]:  # Primeiras 10
                self.stdout.write(
                    f"   {alt['usuario']}: {alt['cargo_planilha']} "
                    f"({alt['grupo_anterior']} -> {alt['grupo_novo']})"
                )
            if len(estatisticas['alteracoes']) > 10:
                self.stdout.write(f"   ... e mais {len(estatisticas['alteracoes']) - 10} alteracoes")

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nSimulacao concluida - Execute sem --dry-run para aplicar as alteracoes')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nSincronizacao concluida com sucesso!')
            )

            # Mostrar estatísticas finais por grupo
            self.stdout.write(f"\nESTATISTICAS FINAIS POR GRUPO:")
            for grupo_nome in grupos_necessarios:
                try:
                    grupo = Group.objects.get(name=grupo_nome)
                    count = grupo.user_set.count()
                    self.stdout.write(f"   {grupo_nome}: {count} usuarios")
                except Group.DoesNotExist:
                    self.stdout.write(f"   {grupo_nome}: grupo nao existe")