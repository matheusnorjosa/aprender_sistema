"""
Management command: seed_frontend_contract_data

Seed deterministico para testes de contrato funcional frontend-backend
(matriz critica usada no checklist Playwright).

Tambem semeia textos longos (80+ caracteres) em todo campo que aparece em tabela,
para o spec `e2e/checklist/sem-rolagem-horizontal.spec.ts` (Programa C): tabela
vazia nunca estoura largura e daria falso verde. E cria `admin_matrix@test.com`
(superusuario), o unico perfil que abre as rotas cuja policy nao tem grupo no seed.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import Group
from django.core.management import BaseCommand, call_command
from django.utils import timezone

from apps.core.models import (
    AcaoInstancia,
    AcaoTemplate,
    AvailabilityBlock,
    CicloAcoes,
    Compra,
    DATAcao,
    DATCadastro,
    DATCompra,
    DATCoordenador,
    DATRegistro,
    Deslocamento,
    Gerencia,
    Municipio,
    NotificacaoInterna,
    Participation,
    PermissaoFuncional,
    PlanoFormacoes,
    Produto,
    Projeto,
    ProjetoGeral,
    Solicitacao,
    TipoEvento,
    Usuario,
)

SENHA_E2E = "testpass123"

# Textos longos (Programa C, C0). Todos com 80+ caracteres e dentro do max_length do campo.
# O prefixo "Aaa" põe a linha na 1a página das listas paginadas por nome ou username.
MUNICIPIO_LONGO = "Aaa São Sebastião dos Campos Gerais do Alto Sertão da Serra da Borborema do Norte"
PROJETO_LONGO = (
    "Aaa Alfabetização e Letramento: Formação Continuada em Linguagens, Matemática "
    "e Ciências da Natureza nos Anos Iniciais"
)
PROJETO_GERAL_LONGO = "Aaa Alfabetização na Idade Certa com Acompanhamento Pedagógico e Avaliação Anual"
PRODUTO_LONGO = (
    "Aaa Kit Pedagógico de Alfabetização com Livro do Estudante, Caderno de Atividades "
    "e Guia do Professor para o 1º Ano"
)
TIPO_EVENTO_LONGO = "Aaa Formação Presencial com Oficina Prática, Estudo de Caso e Devolutiva Individual"
GERENCIA_SETOR_LONGO = "Aaa Gerência de Formação Continuada, Acompanhamento Pedagógico e Avaliação das Redes"
GRUPO_LONGO = "Aaa Grupo de Teste de Largura com Nome Muito Longo para Conferir a Quebra de Linha nas Tabelas"
NOME_LONGO = "Aaa Maria Aparecida da Conceição"
SOBRENOME_LONGO = "dos Santos Albuquerque Cavalcanti de Vasconcelos Figueiredo"
CARGO_LONGO = "Coordenadora Pedagógica de Formação Continuada e Acompanhamento das Redes Municipais"
ENCONTRO_LONGO = "Encontro de Formação Continuada com Oficinas Práticas de Leitura, Escrita e Oralidade"
SEGMENTO_LONGO = "Professores Alfabetizadores do 1º ao 3º Ano e Coordenadores Pedagógicos das Escolas"
LOCAL_LONGO = (
    "Auditório Municipal Professora Maria das Graças Nascimento, Avenida Governador Luiz Viana Filho, "
    "Centro Administrativo, Sala de Formação 2"
)
TEXTO_OBSERVACAO_LONGO = (
    "Observação longa de teste: confirmar com a secretaria municipal a lista de presença, "
    "o transporte dos formadores e a entrega do material pedagógico antes do encontro."
)
MOTIVO_BLOQUEIO_LONGO = (
    "Participação no seminário estadual de alfabetização e letramento, com apresentação "
    "de relato de experiência sobre a rede municipal"
)
ORIGEM_LONGA = "Aaa São Sebastião dos Campos Gerais do Alto Sertão da Serra da Borborema do Norte (BA)"
DESTINO_LONGO = "Santa Maria da Vitória do Sertão Baiano, Distrito de São José do Rio Grande, Zona Rural (BA)"
COORDENADOR_DAT_LONGO = "Aaa Coordenadora Regional Josefa Aparecida Nascimento de Albuquerque Cavalcanti Lins"
AREA_DAT_LONGA = "Formação Continuada e Acompanhamento Pedagógico das Redes Municipais de Ensino (BA)"
ACAO_TEMPLATE_LONGA = (
    "Aaa Enviar à secretaria municipal o ofício de confirmação da formação com a lista de escolas "
    "participantes e o cronograma"
)
NOTIFICACAO_LONGA = (
    "Prazo da ação se aproxima: enviar o ofício de confirmação da formação à secretaria municipal "
    "com a lista de escolas"
)
ANO_TEXTOS_LONGOS = 2026
ORDEM_ACAO_TEMPLATE_LONGA = 900


class Command(BaseCommand):
    help = "Cria dados deterministicos para a matriz funcional critica do frontend"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("=" * 80)
        self.stdout.write("SEED FRONTEND CONTRACT DATA")
        self.stdout.write("=" * 80)

        # Reusa seed de usuarios/projeto base de E2E.
        call_command("seed_e2e_users")

        dat_group, _ = Group.objects.get_or_create(name="DAT")
        dashboard_perm = PermissaoFuncional.objects.filter(codename="view_compras_dashboard").first()
        if dashboard_perm is not None:
            dashboard_perm.groups.add(dat_group)

        dat_user, created = Usuario.objects.update_or_create(
            username="dat_matrix@test.com",
            defaults={
                "email": "dat_matrix@test.com",
                "first_name": "DAT",
                "last_name": "Matrix",
                "cpf": "00000000005",
                "is_superuser": False,
            },
        )
        if created or not dat_user.check_password("testpass123"):
            dat_user.set_password("testpass123")
            dat_user.save(update_fields=["password"])
        dat_user.groups.set([dat_group])

        projeto, _ = Projeto.objects.get_or_create(
            codigo="E2E",
            defaults={"nome": "TESTE E2E", "fluxo": "SUPER", "ativo": True},
        )

        municipio, _ = Municipio.objects.get_or_create(
            nome="Matrizopolis",
            uf="BA",
            defaults={"ativo": True},
        )
        if not municipio.ativo:
            municipio.ativo = True
            municipio.save(update_fields=["ativo"])

        # Garante que esse par municipio+projeto fique pendente no dashboard
        # (sem solicitacao ativa).
        Solicitacao.objects.filter(
            municipio=municipio,
            projeto=projeto,
            status__in=["pendente", "aprovado"],
        ).delete()

        Compra.objects.update_or_create(
            external_hash="9" * 64,
            defaults={
                "codigo": "MATRIX-PEND-001",
                "projeto": projeto,
                "municipio": municipio,
                "quantidade": 15,
                "data": date(2026, 3, 3),
                "uso": "Matriz funcional frontend",
            },
        )

        DATCompra.objects.update_or_create(
            municipio=municipio,
            projeto=projeto,
            descricao_produto="KIT MATRIX CONTRACT",
            ano_uso=2026,
            defaults={
                "quantidade": 77,
                "quantidade_utilizada": 0,
                "valor_unitario": Decimal("19.90"),
                "created_by": dat_user,
                "updated_by": dat_user,
                "ativo": True,
            },
        )

        self._semear_textos_longos(projeto_e2e=projeto)

        self.stdout.write(self.style.SUCCESS("✅ Seed funcional da matriz concluido"))
        self.stdout.write("Usuarios:")
        self.stdout.write("  - controle_e2e@test.com / testpass123 (Controle)")
        self.stdout.write("  - dat_matrix@test.com / testpass123 (DAT)")
        self.stdout.write("Dados-chave:")
        self.stdout.write("  - core_compra codigo=MATRIX-PEND-001 municipio=Matrizopolis projeto=TESTE E2E")
        self.stdout.write("  - core_dat_compra descricao=KIT MATRIX CONTRACT municipio=Matrizopolis projeto=TESTE E2E")
        self.stdout.write("  - admin_matrix@test.com / testpass123 (superusuario)")
        self.stdout.write("  - textos longos (80+) nas tabelas, prefixo 'Aaa' (spec sem-rolagem-horizontal)")

    def _usuario(self, username: str, **defaults: Any) -> Usuario:
        usuario, created = Usuario.objects.update_or_create(username=username, defaults={"email": username, **defaults})
        if created or not usuario.check_password(SENHA_E2E):
            usuario.set_password(SENHA_E2E)
            usuario.save(update_fields=["password"])
        return usuario

    def _semear_textos_longos(self, *, projeto_e2e: Projeto) -> None:
        """Uma linha com texto longo em cada tabela, visível ao perfil que o spec usa na rota.

        Nenhuma linha aponta para Matrizopolis, `dat_matrix` ou `controle_e2e`: o teste do seed
        apaga esses três na limpeza, e FK PROTECT travaria o teardown.
        """
        coord_vidas = Usuario.objects.get(username="coord_vidas@test.com")
        dat_e2e = Usuario.objects.get(username="dat_e2e@test.com")

        admin = self._usuario(
            "admin_matrix@test.com",
            first_name="Admin",
            last_name="Matrix",
            cpf="00000000007",
            is_superuser=True,
            is_staff=True,
        )
        pessoa_longa = self._usuario(
            "aaa.largura@test.com",
            first_name=NOME_LONGO,
            last_name=SOBRENOME_LONGO,
            cargo=CARGO_LONGO,
            cpf="00000000006",
            is_superuser=False,
        )
        pessoa_longa.groups.set(Group.objects.filter(name="Formador"))
        Group.objects.get_or_create(name=GRUPO_LONGO)
        Gerencia.objects.update_or_create(
            nome="AAA LARGURA E2E",
            defaults={"nome_setor": GERENCIA_SETOR_LONGO, "ativo": False, "descricao": TEXTO_OBSERVACAO_LONGO},
        )

        # Com coordenadas: o Mapa (vista Lista) só mostra município com latitude e longitude.
        municipio, _ = Municipio.objects.update_or_create(
            nome=MUNICIPIO_LONGO,
            uf="BA",
            defaults={"ativo": True, "latitude": Decimal("-12.971400"), "longitude": Decimal("-38.501400")},
        )
        projeto_geral, _ = ProjetoGeral.objects.get_or_create(nome=PROJETO_GERAL_LONGO)
        # Com a família: a coluna "Família" da tela Projetos é medida com texto longo.
        projeto, _ = Projeto.objects.update_or_create(
            codigo="E2E_LARGURA",
            defaults={
                "nome": PROJETO_LONGO,
                "fluxo": "SUPER",
                "ativo": True,
                "descricao": TEXTO_OBSERVACAO_LONGO,
                "projeto_geral": projeto_geral,
            },
        )
        tipo_evento, _ = TipoEvento.objects.get_or_create(nome=TIPO_EVENTO_LONGO, defaults={"cor": "#1890ff"})

        # Pendências do dashboard de compras: Compra sem solicitação ativa no par (município, projeto).
        # Ordena antes de Matrizopolis, que continua na 1a página (10 por página).
        Compra.objects.update_or_create(
            external_hash=hashlib.sha256(b"sem-rolagem-horizontal:compra").hexdigest(),
            defaults={
                "codigo": "LARGURA-PEND-001",
                "projeto": projeto_e2e,
                "municipio": municipio,
                "quantidade": 3,
                "data": date(2026, 3, 3),
                "uso": TEXTO_OBSERVACAO_LONGO,
            },
        )
        produto, _ = Produto.objects.update_or_create(
            codigo="AAA-LARGURA-01",
            defaults={"nome": PRODUTO_LONGO, "projeto": projeto, "descricao": TEXTO_OBSERVACAO_LONGO},
        )
        # Quantidade baixa: o Top Produtos (top 10 por quantidade) segue mostrando o KIT MATRIX (77).
        DATCompra.objects.update_or_create(
            municipio=municipio,
            projeto=projeto,
            descricao_produto=PRODUTO_LONGO,
            ano_uso=ANO_TEXTOS_LONGOS,
            defaults={
                "produto": produto,
                "quantidade": 5,
                "quantidade_utilizada": 0,
                "valor_unitario": Decimal("12.50"),
                "observacoes": TEXTO_OBSERVACAO_LONGO,
                "created_by": dat_e2e,
                "updated_by": dat_e2e,
                "ativo": True,
            },
        )

        hoje = timezone.localdate()

        def _em(dias: int, hora: int) -> datetime:
            return timezone.make_aware(datetime.combine(hoje + timedelta(days=dias), time(hora)))

        comum: dict[str, Any] = {
            "municipio": municipio,
            "projeto": projeto,
            "tipo_evento": tipo_evento,
            "local": LOCAL_LONGO,
            "tipo": "Formação presencial",
            "encontro": ENCONTRO_LONGO,
            "segmento": SEGMENTO_LONGO,
            "observacoes": TEXTO_OBSERVACAO_LONGO,
            "coordenador": coord_vidas,
            # created_at recente: o dashboard de equipe só olha os últimos 7 dias.
            "created_at": timezone.now(),
        }
        # Pendente de coord_vidas: Minhas, Aprovações (SUPER) e a tela de edição.
        pendente, _ = Solicitacao.objects.update_or_create(
            external_hash="sem-rolagem-horizontal:pendente",
            defaults={**comum, "usuario": coord_vidas, "status": "pendente", "inicio": _em(10, 9), "fim": _em(10, 17)},
        )
        # Aprovada futura criada pela pessoa de nome longo: Publicação, Pré-agenda, Meus eventos
        # (coord_vidas participa), Grade Mensal e os dashboards (visão geral, equipe, GCal).
        aprovada, _ = Solicitacao.objects.update_or_create(
            external_hash="sem-rolagem-horizontal:aprovada",
            defaults={**comum, "usuario": pessoa_longa, "status": "aprovado", "inicio": _em(5, 9), "fim": _em(5, 17)},
        )
        for solicitacao in (pendente, aprovada):
            Participation.objects.get_or_create(solicitacao=solicitacao, usuario=coord_vidas, role="COORDENADOR")
            Participation.objects.get_or_create(solicitacao=solicitacao, usuario=pessoa_longa, role="FORMADOR")

        AvailabilityBlock.objects.get_or_create(
            usuario=coord_vidas,
            motivo=MOTIVO_BLOQUEIO_LONGO,
            defaults={"inicio": _em(20, 8), "fim": _em(20, 18), "created_by": coord_vidas},
        )
        Deslocamento.objects.update_or_create(
            external_hash="sem-rolagem-horizontal:deslocamento",
            defaults={
                "usuario": pessoa_longa,
                "origem": ORIGEM_LONGA,
                "destino": DESTINO_LONGO,
                "start_date": hoje + timedelta(days=3),
                "end_date": hoje + timedelta(days=4),
                "observacao": TEXTO_OBSERVACAO_LONGO,
            },
        )

        coordenador_dat, _ = DATCoordenador.objects.update_or_create(
            nome=COORDENADOR_DAT_LONGO,
            defaults={
                "area": AREA_DAT_LONGA,
                "cargo": CARGO_LONGO,
                "email": "aaa.coordenadora.regional.largura@test.com",
                "created_by": dat_e2e,
            },
        )
        DATAcao.objects.update_or_create(
            municipio=municipio,
            projeto=projeto,
            ano=ANO_TEXTOS_LONGOS,
            defaults={
                "coordenador": coordenador_dat,
                "observacao_carta": TEXTO_OBSERVACAO_LONGO,
                "created_by": dat_e2e,
            },
        )
        plano, _ = PlanoFormacoes.objects.update_or_create(
            municipio=municipio,
            projeto=projeto,
            ano=ANO_TEXTOS_LONGOS,
            defaults={"observacoes": TEXTO_OBSERVACAO_LONGO, "created_by": dat_e2e},
        )
        plano.coordenadores.set([pessoa_longa])
        DATCadastro.objects.update_or_create(
            municipio=municipio,
            projeto_geral=projeto_geral,
            plataforma=DATCadastro.Plataforma.FORMAR,
            ano=ANO_TEXTOS_LONGOS,
            defaults={"observacoes": TEXTO_OBSERVACAO_LONGO, "created_by": dat_e2e},
        )
        DATRegistro.objects.update_or_create(
            municipio=municipio,
            projeto_geral=projeto_geral,
            projeto=projeto,
            ano=ANO_TEXTOS_LONGOS,
            defaults={
                "obs_formar": TEXTO_OBSERVACAO_LONGO,
                "obs_avaliar": TEXTO_OBSERVACAO_LONGO,
                "created_by": dat_e2e,
            },
        )

        # Ações internas: só o superusuário abre. Template próprio (os 32 da migration têm nome curto).
        template, _ = AcaoTemplate.objects.update_or_create(
            ordem=ORDEM_ACAO_TEMPLATE_LONGA,
            defaults={
                "nome": ACAO_TEMPLATE_LONGA,
                "descricao_prazo": TEXTO_OBSERVACAO_LONGO,
                "tipo_ancora": "MARCO_CALENDARIO",
                "dias_prazo_uteis": 5,
            },
        )
        ciclo, _ = CicloAcoes.objects.get_or_create(
            projeto=projeto,
            municipio=municipio,
            semestre="2S",
            ano=ANO_TEXTOS_LONGOS,
            defaults={"created_by": dat_e2e},
        )
        AcaoInstancia.objects.get_or_create(ciclo=ciclo, template=template, defaults={"ordem": template.ordem})
        NotificacaoInterna.objects.get_or_create(
            destinatario=admin,
            titulo=NOTIFICACAO_LONGA,
            defaults={"mensagem": TEXTO_OBSERVACAO_LONGO, "tipo": "LEMBRETE", "nivel": "RESPONSAVEL"},
        )
