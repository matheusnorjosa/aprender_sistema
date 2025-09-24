"""
Comando Django para importar eventos usando dados já extraídos do Google Sheets

Este comando importa os eventos/solicitações usando os dados já extraídos
do arquivo mapeamento_completo_google_sheets_20250923_220315.json
"""

import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import (
    Municipio, Projeto, TipoEvento, Solicitacao,
    SolicitacaoStatus, Setor
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Importa eventos usando dados já extraídos do Google Sheets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='Limite de registros por aba (padrão: 500)'
        )
        parser.add_argument(
            '--aba',
            type=str,
            help='Importar apenas uma aba específica',
            choices=['Super', 'ACerta', 'Outros', 'Brincando', 'Vidas']
        )

    def normalizar_data(self, data_str, hora_str="08:00"):
        """Converter data DD/MM/YYYY + hora HH:MM para datetime"""
        if not data_str or data_str.strip() == "":
            return None

        try:
            # Remover espaços e processar data
            data_str = data_str.strip()
            if "/" in data_str:
                dia, mes, ano = data_str.split("/")
                dia, mes, ano = int(dia), int(mes), int(ano)
            else:
                return None

            # Processar hora
            if hora_str and ":" in hora_str:
                hora, minuto = hora_str.split(":")[:2]
                hora, minuto = int(hora), int(minuto)
            else:
                hora, minuto = 8, 0

            # Criar datetime timezone-aware
            dt = datetime(ano, mes, dia, hora, minuto)
            return timezone.make_aware(dt)
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"❌ Erro ao processar data '{data_str}' + hora '{hora_str}': {e}")
            )
            return None

    def obter_ou_criar_municipio(self, nome):
        """Obter ou criar município"""
        if not nome or nome.strip() == "":
            return None

        nome = nome.strip()

        # Buscar por nome exato
        municipio = Municipio.objects.filter(nome__iexact=nome).first()
        if municipio:
            return municipio

        # Criar novo município (assumir CE como padrão)
        municipio = Municipio.objects.create(
            nome=nome,
            uf="CE",  # Padrão baseado nos dados existentes
            ativo=True
        )
        self.stdout.write(f"✅ Município criado: {nome}/CE")
        return municipio

    def obter_ou_criar_projeto(self, nome):
        """Obter ou criar projeto"""
        if not nome or nome.strip() == "":
            nome = "Outros"

        nome = nome.strip()

        # Buscar por nome exato
        projeto = Projeto.objects.filter(nome__iexact=nome).first()
        if projeto:
            return projeto

        # Obter setor padrão "Outros"
        from core.models import Setor
        setor_outros = Setor.objects.filter(nome="Outros").first()
        if not setor_outros:
            setor_outros = Setor.objects.create(
                nome="Outros",
                sigla="OUTROS",
                vinculado_superintendencia=False,
                ativo=True
            )

        # Criar novo projeto
        projeto = Projeto.objects.create(
            nome=nome,
            setor=setor_outros,
            ativo=True
        )
        self.stdout.write(f"✅ Projeto criado: {nome}")
        return projeto

    def obter_ou_criar_tipo_evento(self, nome):
        """Obter ou criar tipo de evento"""
        if not nome or nome.strip() == "":
            nome = "Formação"

        nome = nome.strip()

        # Mapear abreviações comuns
        mapeamento = {
            "LP": "Língua Portuguesa",
            "MAT": "Matemática",
            "FORM": "Formação",
            "Presencial": "Presencial",
            "Online": "Online"
        }
        nome = mapeamento.get(nome, nome)

        tipo = TipoEvento.objects.filter(nome__iexact=nome).first()
        if tipo:
            return tipo

        tipo = TipoEvento.objects.create(
            nome=nome,
            online=(nome.lower() == "online"),
            ativo=True
        )
        self.stdout.write(f"✅ Tipo evento criado: {nome}")
        return tipo

    def buscar_formador(self, nome):
        """Buscar formador por nome"""
        if not nome or nome.strip() == "":
            return None

        nome = nome.strip()

        # Buscar por nome completo ou parcial
        user = User.objects.filter(
            first_name__icontains=nome.split()[0],
            formador_ativo=True
        ).first()

        return user

    def importar_aba(self, dados_aba, nome_aba, limit):
        """Importar uma aba específica"""
        self.stdout.write(f"\n🚀 Importando aba: {nome_aba}")
        self.stdout.write(f"📊 Registros válidos: {dados_aba.get('registros_validos', 0)}")

        registros = dados_aba.get('amostra_dados', [])
        cabecalhos = dados_aba.get('cabecalhos', [])

        if not registros:
            self.stdout.write(self.style.ERROR("❌ Nenhum registro encontrado"))
            return 0

        contador = 0
        erros = 0

        # Obter projeto padrão para esta aba
        projeto_padrao = self.obter_ou_criar_projeto(nome_aba)

        for i, registro in enumerate(registros[1:limit+1]):  # Pular cabeçalho (primeira linha)
            try:
                if len(registro) < 10:  # Validação básica
                    continue

                # Extrair campos (baseado no mapeamento correto da aba Super)
                # Índices corretos: Municípios=4, data=7, hora início=8, hora fim=9, projeto=10, segmento=11, Formador 1=14
                municipio_nome = registro[4] if len(registro) > 4 else ""
                data_str = registro[7] if len(registro) > 7 else ""
                hora_inicio = registro[8] if len(registro) > 8 else "08:00"
                hora_fim = registro[9] if len(registro) > 9 else "17:00"
                projeto_nome = registro[10] if len(registro) > 10 else nome_aba
                tipo_evento_nome = registro[6] if len(registro) > 6 else "Presencial"  # campo "tipo"
                formador_nome = registro[14] if len(registro) > 14 else ""  # Formador 1

                # Verificar se está aprovado (campo "Aprovação" = índice 1)
                aprovacao = registro[1] if len(registro) > 1 else ""
                if aprovacao.upper() != "SIM":
                    continue

                # Validações básicas
                if not municipio_nome or not data_str:
                    continue

                # Processar dados
                municipio = self.obter_ou_criar_municipio(municipio_nome)
                if not municipio:
                    continue

                data_inicio = self.normalizar_data(data_str, hora_inicio)
                data_fim = self.normalizar_data(data_str, hora_fim)

                if not data_inicio or not data_fim:
                    continue

                projeto = self.obter_ou_criar_projeto(projeto_nome)
                tipo_evento = self.obter_ou_criar_tipo_evento(tipo_evento_nome)

                # Debug - verificar objetos antes de criar solicitação
                if not projeto or not projeto.setor:
                    self.stdout.write(f"❌ Projeto inválido: {projeto}")
                    continue

                # Obter usuário admin como solicitante padrão para dados históricos
                admin_user = User.objects.filter(is_superuser=True).first()
                if not admin_user:
                    admin_user = User.objects.first()

                # Verificar se já existe (para evitar duplicatas)
                titulo_evento = f"{projeto.nome} - {municipio.nome} - {registro[5] if len(registro) > 5 else '1'}"

                if Solicitacao.objects.filter(
                    titulo_evento=titulo_evento,
                    data_inicio=data_inicio
                ).exists():
                    continue  # Pular duplicata

                # Criar solicitação
                try:
                    solicitacao = Solicitacao.objects.create(
                        titulo_evento=titulo_evento,
                        projeto=projeto,
                        municipio=municipio,
                        tipo_evento=tipo_evento,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        numero_encontro_formativo=registro[5] if len(registro) > 5 else "1",
                        coordenador_acompanha=True,
                        observacoes=f"Importado da aba {nome_aba}",
                        status=SolicitacaoStatus.APROVADO,  # Dados históricos já aprovados
                        usuario_solicitante=admin_user
                    )
                except Exception as e:
                    self.stdout.write(f"❌ Erro ao criar solicitação: {e}")
                    self.stdout.write(f"   Projeto: {projeto.nome}, Setor: {projeto.setor}")
                    continue

                # Tentar associar formador se encontrado
                if formador_nome:
                    formador = self.buscar_formador(formador_nome)
                    if formador:
                        solicitacao.formadores.add(formador)

                contador += 1

                if contador % 100 == 0:
                    self.stdout.write(f"  📈 Processados: {contador}")

            except Exception as e:
                erros += 1
                if erros < 10:  # Mostrar apenas os primeiros erros
                    self.stdout.write(
                        self.style.WARNING(f"❌ Erro no registro {i}: {e}")
                    )

        self.stdout.write(
            self.style.SUCCESS(f"✅ Aba {nome_aba}: {contador} solicitações importadas, {erros} erros")
        )
        return contador

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 INICIANDO IMPORTAÇÃO DE EVENTOS DOS DADOS EXTRAÍDOS"))

        # Carregar dados extraídos
        arquivo_dados = "mapeamento_completo_google_sheets_20250923_220315.json"

        if not os.path.exists(arquivo_dados):
            raise CommandError(f"❌ Arquivo não encontrado: {arquivo_dados}")

        self.stdout.write(f"📂 Carregando dados de: {arquivo_dados}")

        with open(arquivo_dados, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        # Encontrar planilha de agenda
        planilha_agenda = None
        for nome, planilha in dados.get('planilhas', {}).items():
            if 'Acompanhamento' in nome and 'Agenda' in nome:
                planilha_agenda = planilha
                break

        if not planilha_agenda:
            raise CommandError("❌ Planilha de agenda não encontrada")

        self.stdout.write(f"📊 Planilha encontrada: {planilha_agenda.get('nome')}")
        self.stdout.write(f"📋 Total de abas: {planilha_agenda.get('total_abas', 0)}")

        # Importar abas específicas ou todas
        if options['aba']:
            abas_importar = [options['aba']]
        else:
            abas_importar = ['Super', 'ACerta']  # Começar com as principais

        total_importado = 0

        for aba_config in planilha_agenda.get('abas', []):
            nome_aba = aba_config.get('nome')

            if nome_aba in abas_importar:
                total_importado += self.importar_aba(
                    aba_config, nome_aba, options['limit']
                )

        self.stdout.write(self.style.SUCCESS(f"\n🎉 IMPORTAÇÃO CONCLUÍDA!"))
        self.stdout.write(f"📊 Total importado: {total_importado} solicitações")

        # Verificar resultado
        self.stdout.write(f"\n📈 ESTATÍSTICAS FINAIS:")
        self.stdout.write(f"👥 Usuários: {User.objects.count()}")
        self.stdout.write(f"🏙️ Municípios: {Municipio.objects.count()}")
        self.stdout.write(f"🏛️ Projetos: {Projeto.objects.count()}")
        self.stdout.write(f"⭐ Tipos Evento: {TipoEvento.objects.count()}")
        self.stdout.write(f"📋 Solicitações: {Solicitacao.objects.count()}")