"""
Command para criar dados de exemplo para testar o sistema completo
"""

import random
from datetime import date, datetime, timedelta

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    Aprovacao,
    AprovacaoStatus,
    Deslocamento,
    DisponibilidadeFormadores,
    Formador,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


class Command(BaseCommand):
    help = "Cria dados de exemplo para testar o sistema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--quantidade",
            type=int,
            default=20,
            help="Quantidade de registros de exemplo a criar",
        )
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Limpar dados existentes antes de criar novos",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== CRIANDO DADOS DE EXEMPLO ==="))

        quantidade = options["quantidade"]
        limpar = options["limpar"]

        try:
            with transaction.atomic():
                if limpar:
                    self.limpar_dados()

                self.criar_dados_basicos()
                self.criar_solicitacoes(quantidade)
                self.criar_bloqueios(quantidade // 2)
                self.criar_deslocamentos(quantidade // 3)

                self.stdout.write(
                    self.style.SUCCESS("Dados de exemplo criados com sucesso!")
                )
                self.exibir_estatisticas()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao criar dados: {str(e)}"))

    def limpar_dados(self):
        """Limpa dados de exemplo existentes"""
        self.stdout.write("Limpando dados existentes...")

        # Limpar em ordem inversa das dependências
        Aprovacao.objects.all().delete()
        Solicitacao.objects.all().delete()
        DisponibilidadeFormadores.objects.all().delete()
        Deslocamento.objects.all().delete()

        self.stdout.write("Dados anteriores removidos.")

    def criar_dados_basicos(self):
        """Cria dados básicos se não existirem"""
        self.stdout.write("Verificando dados básicos...")

        # Criar municípios adicionais
        municipios_exemplo = [
            ("Fortaleza", "CE"),
            ("São Paulo", "SP"),
            ("Rio de Janeiro", "RJ"),
            ("Belo Horizonte", "MG"),
            ("Salvador", "BA"),
            ("Recife", "PE"),
            ("Brasília", "DF"),
            ("Curitiba", "PR"),
            ("Porto Alegre", "RS"),
            ("Manaus", "AM"),
        ]

        for nome, uf in municipios_exemplo:
            Municipio.objects.get_or_create(nome=nome, defaults={"uf": uf})

        # Criar projetos adicionais
        projetos_exemplo = [
            ("Projeto Alpha", "Formação em tecnologia"),
            ("Projeto Beta", "Desenvolvimento de liderança"),
            ("Projeto Gamma", "Capacitação técnica"),
            ("Projeto Delta", "Educação continuada"),
            ("Projeto Omega", "Inovação e criatividade"),
        ]

        for nome, desc in projetos_exemplo:
            Projeto.objects.get_or_create(nome=nome, defaults={"descricao": desc})

        # Criar tipos de evento adicionais
        tipos_exemplo = [
            ("Workshop", True),
            ("Palestra", True),
            ("Curso Intensivo", False),
            ("Seminário", True),
            ("Treinamento", False),
            ("Mesa Redonda", True),
        ]

        for nome, online in tipos_exemplo:
            TipoEvento.objects.get_or_create(
                nome=nome, defaults={"online": online, "ativo": True}
            )

    def criar_solicitacoes(self, quantidade):
        """Cria solicitações de exemplo"""
        self.stdout.write(f"Criando {quantidade} solicitações...")

        municipios = list(Municipio.objects.all())
        projetos = list(Projeto.objects.all())
        tipos_evento = list(TipoEvento.objects.all())
        coordenadores = list(Usuario.objects.filter(groups__name="coordenador"))

        if not coordenadores:
            # Criar um coordenador de exemplo
            coord_group = Group.objects.get(name="coordenador")
            coordenador = Usuario.objects.create_user(
                username="coord_exemplo",
                email="coordenador@exemplo.com",
                first_name="João",
                last_name="Coordenador",
            )
            coordenador.groups.add(coord_group)
            coordenadores = [coordenador]

        status_opcoes = [
            SolicitacaoStatus.PENDENTE,
            SolicitacaoStatus.APROVADO,
            SolicitacaoStatus.REPROVADO,
            SolicitacaoStatus.PRE_AGENDA,
        ]

        for i in range(quantidade):
            # Gerar data aleatória nos próximos 90 dias
            data_base = date.today()
            dias_futuros = random.randint(1, 90)
            data_evento = data_base + timedelta(days=dias_futuros)

            # Criar datetime completo com timezone
            from datetime import datetime, time

            horario_inicio = time(random.randint(8, 14), 0)
            horario_fim = time(random.randint(15, 18), 0)
            data_inicio = timezone.make_aware(
                datetime.combine(data_evento, horario_inicio)
            )
            data_fim = timezone.make_aware(datetime.combine(data_evento, horario_fim))

            solicitacao = Solicitacao.objects.create(
                titulo_evento=f"Evento de Exemplo {i+1:03d}",
                municipio=random.choice(municipios),
                projeto=random.choice(projetos),
                tipo_evento=random.choice(tipos_evento),
                data_inicio=data_inicio,
                data_fim=data_fim,
                observacoes=f"Solicitação de exemplo criada automaticamente - {i+1}",
                status=random.choice(status_opcoes),
                usuario_solicitante=random.choice(coordenadores),
            )

            # Criar aprovação se status não for pendente
            if solicitacao.status != SolicitacaoStatus.PENDENTE:
                superintendentes = Usuario.objects.filter(
                    groups__name="superintendencia"
                )
                if superintendentes.exists():
                    # Mapear status da solicitação para status de aprovação
                    status_aprovacao = (
                        AprovacaoStatus.APROVADO
                        if solicitacao.status == SolicitacaoStatus.APROVADO
                        else AprovacaoStatus.REPROVADO
                    )

                    Aprovacao.objects.create(
                        solicitacao=solicitacao,
                        status_decisao=status_aprovacao,
                        usuario_aprovador=superintendentes.first(),
                        justificativa=f"Decisão automática de exemplo para teste",
                    )

    def criar_bloqueios(self, quantidade):
        """Cria bloqueios de disponibilidade"""
        self.stdout.write(f"Criando {quantidade} bloqueios...")

        formadores = list(Formador.objects.all())
        if not formadores:
            self.stdout.write(
                "Nenhum formador encontrado, pulando criação de bloqueios."
            )
            return

        tipos_bloqueio = [
            "Férias",
            "Licença",
            "Compromisso pessoal",
            "Viagem",
            "Outros",
        ]

        for i in range(quantidade):
            # Gerar data aleatória
            data_base = date.today()
            dias_offset = random.randint(-30, 60)  # 30 dias atrás até 60 dias à frente
            data_bloqueio = data_base + timedelta(days=dias_offset)

            # Gerar horários
            hora_inicio_int = random.randint(8, 16)
            hora_fim_int = random.randint(hora_inicio_int + 1, 18)

            DisponibilidadeFormadores.objects.create(
                formador=random.choice(formadores),
                data_bloqueio=data_bloqueio,
                hora_inicio=f"{hora_inicio_int:02d}:00",
                hora_fim=f"{hora_fim_int:02d}:00",
                tipo_bloqueio=random.choice(tipos_bloqueio),
                motivo=f"Bloqueio de exemplo {i+1} - teste do sistema",
            )

    def criar_deslocamentos(self, quantidade):
        """Cria registros de deslocamento"""
        self.stdout.write(f"Criando {quantidade} deslocamentos...")

        usuarios = list(
            Usuario.objects.filter(groups__name__in=["formador", "coordenador"])
        )
        municipios = list(Municipio.objects.all())

        if len(municipios) < 2:
            self.stdout.write("Poucos municípios, pulando criação de deslocamentos.")
            return

        for i in range(quantidade):
            # Escolher origem e destino diferentes
            origem = random.choice(municipios)
            destino = random.choice([m for m in municipios if m != origem])

            # Gerar data aleatória
            data_base = date.today()
            dias_offset = random.randint(-15, 45)
            data_deslocamento = data_base + timedelta(days=dias_offset)

            # Criar deslocamento e associar formadores
            deslocamento = Deslocamento.objects.create(
                data=data_deslocamento, origem=origem.nome, destino=destino.nome
            )

            # Associar formadores ao deslocamento
            formadores_disponiveis = Formador.objects.all()
            if formadores_disponiveis.exists():
                # Selecionar 1-3 formadores aleatórios
                num_formadores = random.randint(
                    1, min(3, formadores_disponiveis.count())
                )
                formadores_selecionados = random.sample(
                    list(formadores_disponiveis), num_formadores
                )
                deslocamento.formadores.set(formadores_selecionados)

    def exibir_estatisticas(self):
        """Exibe estatísticas dos dados criados"""
        self.stdout.write("\n=== ESTATÍSTICAS FINAIS ===")
        self.stdout.write(f"Usuários: {Usuario.objects.count()}")
        self.stdout.write(f"Municípios: {Municipio.objects.count()}")
        self.stdout.write(f"Projetos: {Projeto.objects.count()}")
        self.stdout.write(f"Tipos de Evento: {TipoEvento.objects.count()}")
        self.stdout.write(f"Formadores: {Formador.objects.count()}")
        self.stdout.write(f"Solicitações: {Solicitacao.objects.count()}")
        self.stdout.write(f"Aprovações: {Aprovacao.objects.count()}")
        self.stdout.write(f"Bloqueios: {DisponibilidadeFormadores.objects.count()}")
        self.stdout.write(f"Deslocamentos: {Deslocamento.objects.count()}")

        # Status das solicitações
        self.stdout.write("\nSTATUS DAS SOLICITAÇÕES:")
        for status_choice in SolicitacaoStatus.choices:
            count = Solicitacao.objects.filter(status=status_choice[0]).count()
            self.stdout.write(f"- {status_choice[1]}: {count}")
