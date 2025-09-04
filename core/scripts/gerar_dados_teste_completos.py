import random
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import (
    Aprovacao,
    AprovacaoStatus,
    Deslocamento,
    DisponibilidadeFormadores,
    Formador,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
)


def run():
    User = get_user_model()

    print(
        "🔄 Criando dados de teste completos para demonstrar todas as funcionalidades..."
    )

    # Limpar dados de teste anteriores
    DisponibilidadeFormadores.objects.all().delete()
    Deslocamento.objects.all().delete()
    Solicitacao.objects.all().delete()

    # Buscar dados necessários
    formadores = list(
        Formador.objects.all()[:20]
    )  # Usar 20 formadores para visualização mais clara
    municipios = list(Municipio.objects.all()[:10])
    projetos = list(Projeto.objects.all())
    tipos_evento = list(TipoEvento.objects.all())

    if not all([formadores, municipios, projetos, tipos_evento]):
        print("⚠️ É necessário ter dados mestres cadastrados.")
        return

    # Criar/buscar usuário admin
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.create_user(
            username="admin_teste",
            email="admin@teste.com",
            password="admin123",
            is_superuser=True,
            is_staff=True,
        )

    agora = timezone.now()
    hoje = date.today()

    # ===== CENÁRIO 1: EVENTOS ÚNICOS =====
    print("\n📅 Criando eventos únicos...")
    for i in range(5):
        formador = formadores[i]
        data_evento = hoje + timedelta(days=i * 2 + 1)

        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=admin,
            projeto=projetos[0],
            municipio=municipios[i % len(municipios)],
            tipo_evento=tipos_evento[i % len(tipos_evento)],
            titulo_evento=f"Evento Único {i+1}",
            data_inicio=timezone.make_aware(
                timezone.datetime.combine(data_evento, time(9, 0))
            ),
            data_fim=timezone.make_aware(
                timezone.datetime.combine(data_evento, time(11, 0))
            ),
            observacoes=f"Evento de teste único {i+1}",
            status=SolicitacaoStatus.APROVADO,
            usuario_aprovador=admin,
            data_aprovacao_rejeicao=agora,
        )
        solicitacao.formadores.set([formador])

    # ===== CENÁRIO 2: MÚLTIPLOS EVENTOS NO MESMO DIA =====
    print("📅 Criando múltiplos eventos no mesmo dia...")
    for i in range(3):
        formador = formadores[i + 5]
        data_evento = hoje + timedelta(days=15)  # Mesmo dia para todos

        # Criar 2-4 eventos para o mesmo formador no mesmo dia
        num_eventos = i + 2  # 2, 3, ou 4 eventos

        for j in range(num_eventos):
            hora_inicio = 8 + j * 2  # 8h, 10h, 12h, 14h
            solicitacao = Solicitacao.objects.create(
                usuario_solicitante=admin,
                projeto=projetos[0],
                municipio=municipios[j % len(municipios)],
                tipo_evento=tipos_evento[j % len(tipos_evento)],
                titulo_evento=f"Evento Múltiplo {i+1}-{j+1}",
                data_inicio=timezone.make_aware(
                    timezone.datetime.combine(data_evento, time(hora_inicio, 0))
                ),
                data_fim=timezone.make_aware(
                    timezone.datetime.combine(data_evento, time(hora_inicio + 1, 30))
                ),
                observacoes=f"Evento múltiplo {j+1} do formador {formador.nome}",
                status=SolicitacaoStatus.APROVADO,
                usuario_aprovador=admin,
                data_aprovacao_rejeicao=agora,
            )
            solicitacao.formadores.set([formador])

    # ===== CENÁRIO 3: DESLOCAMENTOS =====
    print("🚗 Criando deslocamentos...")
    for i in range(4):
        formador = formadores[i + 8]
        data_desloc = hoje + timedelta(days=i * 3 + 5)

        # Criar deslocamento
        deslocamento = Deslocamento.objects.create(
            data=data_desloc, origem=f"Origem {i+1}", destino=f"Destino {i+1}"
        )
        deslocamento.formadores.set([formador])

        # Para alguns deslocamentos, adicionar também eventos no mesmo dia
        if i < 2:  # Primeiros 2 terão eventos também (D1, D2)
            solicitacao = Solicitacao.objects.create(
                usuario_solicitante=admin,
                projeto=projetos[0],
                municipio=municipios[i],
                tipo_evento=tipos_evento[i],
                titulo_evento=f"Evento com Deslocamento {i+1}",
                data_inicio=timezone.make_aware(
                    timezone.datetime.combine(data_desloc, time(14, 0))
                ),
                data_fim=timezone.make_aware(
                    timezone.datetime.combine(data_desloc, time(16, 0))
                ),
                observacoes=f"Evento com deslocamento {i+1}",
                status=SolicitacaoStatus.APROVADO,
                usuario_aprovador=admin,
                data_aprovacao_rejeicao=agora,
            )
            solicitacao.formadores.set([formador])

    # ===== CENÁRIO 4: BLOQUEIOS TOTAIS =====
    print("🚫 Criando bloqueios totais...")
    bloqueios_totais = 0
    for i in range(5):
        formador = formadores[i + 12]
        data_bloqueio = hoje + timedelta(days=i * 2 + 8)

        bloqueio, created = DisponibilidadeFormadores.objects.get_or_create(
            formador=formador,
            data_bloqueio=data_bloqueio,
            hora_inicio=time(0, 0),
            hora_fim=time(23, 59),
            defaults={
                "tipo_bloqueio": "Total",
                "motivo": f"Bloqueio total - {formador.nome}",
            },
        )
        if created:
            bloqueios_totais += 1

    # ===== CENÁRIO 5: BLOQUEIOS PARCIAIS =====
    print("⚠️ Criando bloqueios parciais...")
    bloqueios_parciais = 0
    for i in range(5):
        formador = formadores[i + 15]
        data_bloqueio = hoje + timedelta(days=i * 2 + 10)

        bloqueio, created = DisponibilidadeFormadores.objects.get_or_create(
            formador=formador,
            data_bloqueio=data_bloqueio,
            hora_inicio=time(12, 0),
            hora_fim=time(18, 0),
            defaults={
                "tipo_bloqueio": "Parcial",
                "motivo": f"Bloqueio parcial - {formador.nome}",
            },
        )
        if created:
            bloqueios_parciais += 1

    # ===== CENÁRIO 6: CONFLITOS (Bloqueios + Eventos no mesmo período) =====
    print("❌ Criando conflitos (bloqueios + eventos)...")
    conflitos_criados = 0
    for i in range(3):
        formador = formadores[i + 17]
        data_conflito = hoje + timedelta(days=i * 3 + 20)

        # Criar bloqueio parcial
        bloqueio, created = DisponibilidadeFormadores.objects.get_or_create(
            formador=formador,
            data_bloqueio=data_conflito,
            hora_inicio=time(14, 0),
            hora_fim=time(18, 0),
            defaults={
                "tipo_bloqueio": "Parcial",
                "motivo": f"Bloqueio que gera conflito - {formador.nome}",
            },
        )

        # Criar evento que conflita com o bloqueio
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=admin,
            projeto=projetos[0],
            municipio=municipios[i],
            tipo_evento=tipos_evento[i],
            titulo_evento=f"Evento em Conflito {i+1}",
            data_inicio=timezone.make_aware(
                timezone.datetime.combine(data_conflito, time(15, 0))
            ),  # Sobrepõe com bloqueio
            data_fim=timezone.make_aware(
                timezone.datetime.combine(data_conflito, time(17, 0))
            ),
            observacoes=f"Evento que causa conflito {i+1}",
            status=SolicitacaoStatus.APROVADO,
            usuario_aprovador=admin,
            data_aprovacao_rejeicao=agora,
        )
        solicitacao.formadores.set([formador])
        conflitos_criados += 1

    # ===== CENÁRIO 7: CENÁRIOS MISTOS =====
    print("🎭 Criando cenários mistos...")

    # Formador com deslocamento E evento E bloqueio parcial em dias consecutivos
    if len(formadores) > 19:
        formador_misto = formadores[19]
        base_date = hoje + timedelta(days=25)

        # Dia 1: Deslocamento + Evento
        deslocamento = Deslocamento.objects.create(
            data=base_date, origem="Cidade A", destino="Cidade B"
        )
        deslocamento.formadores.set([formador_misto])

        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=admin,
            projeto=projetos[0],
            municipio=municipios[0],
            tipo_evento=tipos_evento[0],
            titulo_evento="Evento Misto com Deslocamento",
            data_inicio=timezone.make_aware(
                timezone.datetime.combine(base_date, time(9, 0))
            ),
            data_fim=timezone.make_aware(
                timezone.datetime.combine(base_date, time(11, 0))
            ),
            observacoes="Evento em dia de deslocamento",
            status=SolicitacaoStatus.APROVADO,
            usuario_aprovador=admin,
            data_aprovacao_rejeicao=agora,
        )
        solicitacao.formadores.set([formador_misto])

        # Dia 2: Bloqueio parcial
        DisponibilidadeFormadores.objects.get_or_create(
            formador=formador_misto,
            data_bloqueio=base_date + timedelta(days=1),
            hora_inicio=time(13, 0),
            hora_fim=time(17, 0),
            defaults={"tipo_bloqueio": "Parcial", "motivo": "Bloqueio misto"},
        )

        # Dia 3: Múltiplos eventos
        for j in range(3):
            hora = 8 + j * 3  # 8h, 11h, 14h
            solicitacao = Solicitacao.objects.create(
                usuario_solicitante=admin,
                projeto=projetos[0],
                municipio=municipios[j],
                tipo_evento=tipos_evento[j],
                titulo_evento=f"Evento Misto Múltiplo {j+1}",
                data_inicio=timezone.make_aware(
                    timezone.datetime.combine(
                        base_date + timedelta(days=2), time(hora, 0)
                    )
                ),
                data_fim=timezone.make_aware(
                    timezone.datetime.combine(
                        base_date + timedelta(days=2), time(hora + 2, 0)
                    )
                ),
                observacoes=f"Evento múltiplo misto {j+1}",
                status=SolicitacaoStatus.APROVADO,
                usuario_aprovador=admin,
                data_aprovacao_rejeicao=agora,
            )
            solicitacao.formadores.set([formador_misto])

    # ===== ESTATÍSTICAS FINAIS =====
    total_solicitacoes = Solicitacao.objects.count()
    total_aprovadas = Solicitacao.objects.filter(
        status=SolicitacaoStatus.APROVADO
    ).count()
    total_bloqueios = DisponibilidadeFormadores.objects.count()
    total_deslocamentos = Deslocamento.objects.count()

    print(f"\n📊 DADOS DE TESTE CRIADOS COM SUCESSO!")
    print(f"   📅 Total de solicitações: {total_solicitacoes}")
    print(f"   ✅ Solicitações aprovadas: {total_aprovadas}")
    print(f"   🔒 Bloqueios de disponibilidade: {total_bloqueios}")
    print(f"   🚗 Deslocamentos: {total_deslocamentos}")
    print(f"   👥 Formadores com dados: {len(formadores)}")

    print(f"\n🎯 CENÁRIOS DEMONSTRADOS:")
    print(f"   • Eventos únicos (1)")
    print(f"   • Múltiplos eventos (2, 3, 4+)")
    print(f"   • Deslocamentos simples (D)")
    print(f"   • Deslocamentos com eventos (D1, D2)")
    print(f"   • Bloqueios totais (T)")
    print(f"   • Bloqueios parciais (P)")
    print(f"   • Conflitos de agenda (X)")
    print(f"   • Combinações mistas complexas")

    print(f"\n🌐 Acesse para visualizar:")
    print(f"   📱 Página: http://localhost:8000/disponibilidade/")
    print(
        f"   📊 API: http://localhost:8000/mapa-mensal/?ano={hoje.year}&mes={hoje.month}"
    )
    print(f"\n✨ Agora você pode ver TODOS os cenários visuais funcionando!")
