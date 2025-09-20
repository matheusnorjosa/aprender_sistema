#!/usr/bin/env python3
"""
Comando Django para limpar usuários duplicados e centralizar tudo no Docker
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Usuario, Formador, FormadoresSolicitacao
from django.contrib.auth.models import Group
from collections import defaultdict
import re

class Command(BaseCommand):
    help = 'Limpa usuários duplicados mantendo apenas emails reais e centralizando no Docker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa simulação sem salvar alterações'
        )
        parser.add_argument(
            '--confirmar-limpeza',
            action='store_true',
            help='Confirma que quer executar a limpeza (obrigatório para execução real)'
        )

    def handle(self, *args, **options):
        if not options['dry_run'] and not options['confirmar_limpeza']:
            raise CommandError(
                "Para executar a limpeza real, use: --confirmar-limpeza\n"
                "Para simular, use: --dry-run"
            )

        self.dry_run = options['dry_run']

        if self.dry_run:
            self.stdout.write("=== MODO SIMULAÇÃO - NENHUMA ALTERAÇÃO SERÁ SALVA ===")
        else:
            self.stdout.write("=== EXECUTANDO LIMPEZA REAL DOS USUÁRIOS DUPLICADOS ===")

        # Verificar ambiente
        from django.db import connection
        db_engine = connection.settings_dict['ENGINE']
        if 'postgresql' not in db_engine:
            raise CommandError("Este comando deve ser executado APENAS com PostgreSQL Docker!")

        self.stdout.write(f"Banco em uso: {db_engine}")
        self.stdout.write(f"Host: {connection.settings_dict.get('HOST', 'localhost')}")
        self.stdout.write(f"Database: {connection.settings_dict.get('NAME', 'N/A')}")

        with transaction.atomic():
            # Executar limpeza
            self.analisar_situacao_atual()
            self.identificar_duplicacoes()
            self.limpar_emails_genericos()
            self.consolidar_usuarios_reais()
            self.relatorio_final()

            if self.dry_run:
                # Rollback em modo simulação
                transaction.set_rollback(True)
                self.stdout.write("\n=== SIMULAÇÃO CONCLUÍDA - NENHUMA ALTERAÇÃO SALVA ===")
            else:
                self.stdout.write("\n=== LIMPEZA CONCLUÍDA COM SUCESSO ===")

    def analisar_situacao_atual(self):
        """Analisa situação atual dos usuários"""
        self.stdout.write("\nANALISE DA SITUACAO ATUAL:")
        self.stdout.write("=" * 50)

        total = Usuario.objects.count()
        emails_planilha = Usuario.objects.filter(email__contains='planilha.').count()
        emails_sistema = Usuario.objects.filter(email__contains='sistema.local').count()
        emails_reais = Usuario.objects.exclude(
            email__contains='planilha.'
        ).exclude(
            email__contains='sistema.local'
        ).count()

        self.stdout.write(f"Total de usuários: {total}")
        self.stdout.write(f"Emails @planilha.*: {emails_planilha}")
        self.stdout.write(f"Emails @sistema.local: {emails_sistema}")
        self.stdout.write(f"Emails reais: {emails_reais}")

        # Verificar relacionamentos
        formadores_count = Formador.objects.count()
        self.stdout.write(f"Formadores: {formadores_count}")

    def identificar_duplicacoes(self):
        """Identifica grupos de usuários duplicados por nome"""
        self.stdout.write("\nIDENTIFICANDO DUPLICACOES POR NOME:")
        self.stdout.write("=" * 50)

        # Agrupar por primeiro nome (case-insensitive)
        grupos_nome = defaultdict(list)

        for usuario in Usuario.objects.all():
            nome_normalizado = self.normalizar_nome(usuario.first_name)
            if nome_normalizado:
                grupos_nome[nome_normalizado].append(usuario)

        # Identificar duplicações
        self.duplicados = {}
        for nome, usuarios in grupos_nome.items():
            if len(usuarios) > 1:
                self.duplicados[nome] = usuarios

        self.stdout.write(f"Nomes com duplicações: {len(self.duplicados)}")
        self.stdout.write(f"Usuários afetados: {sum(len(usuarios) for usuarios in self.duplicados.values())}")

        # Mostrar alguns exemplos
        count = 0
        for nome, usuarios in sorted(self.duplicados.items()):
            if count >= 10:  # Mostrar apenas 10 exemplos
                break
            count += 1

            self.stdout.write(f"\n{count}. Nome: '{nome}' ({len(usuarios)} usuários):")
            for u in usuarios:
                tipo_email = self.classificar_email(u.email)
                self.stdout.write(f"   - {u.username:20} | {u.email:30} | {tipo_email}")

        if len(self.duplicados) > 10:
            self.stdout.write(f"\n... e mais {len(self.duplicados) - 10} grupos")

    def normalizar_nome(self, nome):
        """Normaliza nome para comparação"""
        if not nome:
            return ""
        # Remove acentos e converte para minúsculo
        nome = nome.lower().strip()
        # Remove caracteres especiais
        nome = re.sub(r'[^\w\s]', '', nome)
        return nome

    def classificar_email(self, email):
        """Classifica tipo de email"""
        email = email.lower()
        if 'planilha.' in email:
            return 'PLANILHA'
        elif 'sistema.local' in email:
            return 'SISTEMA'
        elif '@gmail.com' in email or '@aprendereditora.com.br' in email:
            return 'REAL'
        else:
            return 'OUTRO'

    def limpar_emails_genericos(self):
        """Remove usuários com emails genéricos que têm equivalente real"""
        self.stdout.write("\nLIMPANDO EMAILS GENERICOS:")
        self.stdout.write("=" * 50)

        removidos = 0
        preservados = 0

        for nome, usuarios in self.duplicados.items():
            # Separar por tipo de email
            usuarios_reais = [u for u in usuarios if self.classificar_email(u.email) == 'REAL']
            usuarios_genericos = [u for u in usuarios if self.classificar_email(u.email) in ['PLANILHA', 'SISTEMA']]

            if usuarios_reais and usuarios_genericos:
                # Tem tanto real quanto genérico - remover genéricos
                for u in usuarios_genericos:
                    self.stdout.write(f"Removendo: {u.username} ({u.email}) - tem equivalente real")

                    # Transferir relacionamentos antes de remover
                    self.transferir_relacionamentos(u, usuarios_reais[0])

                    if not self.dry_run:
                        u.delete()
                    removidos += 1

            elif usuarios_genericos and not usuarios_reais:
                # Só tem genéricos - preservar um, remover outros
                principal = usuarios_genericos[0]
                outros = usuarios_genericos[1:]

                self.stdout.write(f"Preservando: {principal.username} (único disponível)")
                preservados += 1

                for u in outros:
                    self.stdout.write(f"Removendo duplicata: {u.username}")
                    self.transferir_relacionamentos(u, principal)

                    if not self.dry_run:
                        u.delete()
                    removidos += 1

        self.stdout.write(f"\nUsuários removidos: {removidos}")
        self.stdout.write(f"Usuários preservados: {preservados}")

    def transferir_relacionamentos(self, usuario_origem, usuario_destino):
        """Transfere relacionamentos antes de deletar usuário"""

        # Transferir FormadoresSolicitacao
        if not self.dry_run:
            FormadoresSolicitacao.objects.filter(usuario=usuario_origem).update(usuario=usuario_destino)

        # Transferir formadores
        try:
            formador_origem = Formador.objects.get(usuario=usuario_origem)
            try:
                formador_destino = Formador.objects.get(usuario=usuario_destino)
                # Já existe formador para destino
                # Transferir dados importantes se necessário
                if not self.dry_run:
                    # Manter dados mais completos
                    if not formador_destino.nome and formador_origem.nome:
                        formador_destino.nome = formador_origem.nome
                    if not formador_destino.email and formador_origem.email:
                        formador_destino.email = formador_origem.email
                    formador_destino.save()
                    formador_origem.delete()
            except Formador.DoesNotExist:
                # Transferir formador para usuário destino
                if not self.dry_run:
                    formador_origem.usuario = usuario_destino
                    formador_origem.save()
        except Formador.DoesNotExist:
            pass

        # Transferir outros relacionamentos se existirem
        # Verificar outros modelos que referenciam Usuario

    def consolidar_usuarios_reais(self):
        """Consolida usuários com emails reais similares"""
        self.stdout.write("\nCONSOLIDANDO USUARIOS REAIS SIMILARES:")
        self.stdout.write("=" * 50)

        consolidados = 0

        for nome, usuarios in self.duplicados.items():
            usuarios_reais = [u for u in usuarios if self.classificar_email(u.email) == 'REAL']

            if len(usuarios_reais) > 1:
                # Múltiplos usuários reais com mesmo nome
                principal = self.escolher_usuario_principal(usuarios_reais)
                outros = [u for u in usuarios_reais if u.id != principal.id]

                self.stdout.write(f"\nConsolidando '{nome}':")
                self.stdout.write(f"  Principal: {principal.username} ({principal.email})")

                for u in outros:
                    self.stdout.write(f"  Mesclando: {u.username} ({u.email})")
                    self.transferir_relacionamentos(u, principal)

                    if not self.dry_run:
                        u.delete()
                    consolidados += 1

        self.stdout.write(f"\nUsuários consolidados: {consolidados}")

    def escolher_usuario_principal(self, usuarios):
        """Escolhe usuário principal baseado em critérios"""
        # Prioridade: @aprendereditora.com.br > @gmail.com > outros
        # Depois: mais relacionamentos > criado primeiro

        def score(usuario):
            score = 0

            # Email corporativo tem prioridade
            if '@aprendereditora.com.br' in usuario.email:
                score += 100
            elif '@gmail.com' in usuario.email:
                score += 50

            # Usuário com formador tem prioridade
            if hasattr(usuario, 'formador'):
                score += 20

            # Mais antigo tem prioridade
            score += (10000 - usuario.id)  # IDs menores = mais antigos

            return score

        return max(usuarios, key=score)

    def relatorio_final(self):
        """Gera relatório final da limpeza"""
        self.stdout.write("\nRELATORIO FINAL:")
        self.stdout.write("=" * 50)

        total = Usuario.objects.count()
        emails_planilha = Usuario.objects.filter(email__contains='planilha.').count()
        emails_sistema = Usuario.objects.filter(email__contains='sistema.local').count()
        emails_reais = Usuario.objects.exclude(
            email__contains='planilha.'
        ).exclude(
            email__contains='sistema.local'
        ).count()

        self.stdout.write(f"Total de usuários após limpeza: {total}")
        self.stdout.write(f"Emails @planilha.*: {emails_planilha}")
        self.stdout.write(f"Emails @sistema.local: {emails_sistema}")
        self.stdout.write(f"Emails reais: {emails_reais}")

        # Verificar duplicações restantes
        grupos_nome = defaultdict(list)
        for usuario in Usuario.objects.all():
            nome_normalizado = self.normalizar_nome(usuario.first_name)
            if nome_normalizado:
                grupos_nome[nome_normalizado].append(usuario)

        duplicados_restantes = {nome: usuarios for nome, usuarios in grupos_nome.items() if len(usuarios) > 1}

        self.stdout.write(f"Duplicações restantes: {len(duplicados_restantes)}")

        if duplicados_restantes:
            self.stdout.write("\nDuplicações que ainda precisam de atenção manual:")
            for nome, usuarios in list(duplicados_restantes.items())[:5]:
                self.stdout.write(f"  {nome}: {len(usuarios)} usuários")