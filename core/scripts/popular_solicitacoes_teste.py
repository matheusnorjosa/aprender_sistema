from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Formador, Municipio, Projeto, Solicitacao, TipoEvento


def run():
    User = get_user_model()

    # Pega um usuário existente (admin) para associar como solicitante
    solicitante = User.objects.filter(is_superuser=True).first()
    if not solicitante:
        solicitante = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            is_superuser=True,
            is_staff=True,
        )

    # Busca dados existentes
    formadores = list(FormadorService.get_formadores_queryset()[:5])
    municipios = list(MunicipioService.todos()[:5])
    projetos = list(ProjetoService.todos())
    tipos_evento = list(TipoEvento.objects.all())

    if not formadores or not municipios or not projetos or not tipos_evento:
        print(
            "⚠️ É necessário ter pelo menos 1 Formador, 1 Município, 1 Projeto e 1 Tipo de Evento cadastrados."
        )
        return

    agora = timezone.now()

    for i in range(1, 6):
        # Criar a solicitação
        solicitacao = Solicitacao.objects.create(
            usuario_solicitante=solicitante,
            projeto=projetos[0],  # Usar primeiro projeto
            municipio=municipios[i % len(municipios)],
            tipo_evento=tipos_evento[i % len(tipos_evento)],
            titulo_evento=f"Evento de Teste {i}",
            data_inicio=agora
            + timezone.timedelta(days=i * 7),  # Uma semana de intervalo
            data_fim=agora + timezone.timedelta(days=i * 7, hours=2),
            observacoes=f"Observações do evento de teste {i}",
            numero_encontro_formativo=f"Encontro {i}",
        )

        # Associar formadores
        solicitacao.formadores.set([formadores[i % len(formadores)]])
        print(f"✅ Solicitação criada: {solicitacao.titulo_evento}")

    print(f"\n📊 Total de {Solicitacao.objects.count()} solicitações no sistema.")
