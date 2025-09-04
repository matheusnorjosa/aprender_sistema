from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import (
    Aprovacao,
    AprovacaoStatus,
    DisponibilidadeFormadores,
    Formador,
    Solicitacao,
    SolicitacaoStatus,
)


def run():
    User = get_user_model()

    # Buscar dados existentes
    formadores = list(Formador.objects.all()[:10])
    solicitacoes = list(Solicitacao.objects.all())

    if not formadores:
        print("⚠️ É necessário ter formadores cadastrados.")
        return

    agora = timezone.now()
    hoje = date.today()

    print("🔄 Criando bloqueios de disponibilidade...")

    # Criar alguns bloqueios de disponibilidade
    bloqueios_criados = 0
    for i, formador in enumerate(formadores[:5]):
        # Bloqueio total em uma data específica
        data_bloqueio = hoje + timedelta(days=i * 3 + 1)
        bloqueio, created = DisponibilidadeFormadores.objects.get_or_create(
            formador=formador,
            data_bloqueio=data_bloqueio,
            hora_inicio=time(0, 0),
            hora_fim=time(23, 59),
            defaults={
                "tipo_bloqueio": "Total",
                "motivo": f"Bloqueio total para {formador.nome}",
            },
        )
        if created:
            bloqueios_criados += 1
            print(f"✅ Bloqueio total criado para {formador.nome} em {data_bloqueio}")

        # Bloqueio parcial em outra data
        data_bloqueio_parcial = hoje + timedelta(days=i * 3 + 5)
        bloqueio_parcial, created = DisponibilidadeFormadores.objects.get_or_create(
            formador=formador,
            data_bloqueio=data_bloqueio_parcial,
            hora_inicio=time(14, 0),
            hora_fim=time(18, 0),
            defaults={
                "tipo_bloqueio": "Parcial",
                "motivo": f"Bloqueio parcial para {formador.nome}",
            },
        )
        if created:
            bloqueios_criados += 1
            print(
                f"✅ Bloqueio parcial criado para {formador.nome} em {data_bloqueio_parcial}"
            )

    print(f"\n🎯 Aprovando algumas solicitações...")

    # Aprovar algumas solicitações para ter eventos no calendário
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print("⚠️ Usuário admin não encontrado.")
        return

    aprovadas = 0
    for solicitacao in solicitacoes[:3]:  # Aprovar as primeiras 3
        if solicitacao.status == SolicitacaoStatus.PENDENTE:
            # Criar aprovação
            aprovacao = Aprovacao.objects.create(
                solicitacao=solicitacao,
                usuario_aprovador=admin,
                status_decisao=AprovacaoStatus.APROVADO,
                justificativa="Aprovado para teste do sistema de disponibilidade",
            )

            # Atualizar status da solicitação
            solicitacao.status = SolicitacaoStatus.APROVADO
            solicitacao.usuario_aprovador = admin
            solicitacao.data_aprovacao_rejeicao = timezone.now()
            solicitacao.save()

            aprovadas += 1
            print(f"✅ Solicitação aprovada: {solicitacao.titulo_evento}")

    print(f"\n📊 Resumo dos dados de teste criados:")
    print(f"   🔒 Bloqueios criados: {bloqueios_criados}")
    print(f"   ✅ Solicitações aprovadas: {aprovadas}")
    print(f"   👥 Formadores ativos: {Formador.objects.filter(ativo=True).count()}")
    print(f"   📅 Total de solicitações: {Solicitacao.objects.count()}")
    print(
        f"   🗓️ Solicitações aprovadas: {Solicitacao.objects.filter(status=SolicitacaoStatus.APROVADO).count()}"
    )

    print(
        f"\n🌐 Acesse a página de disponibilidade em: http://localhost:8000/disponibilidade/"
    )
