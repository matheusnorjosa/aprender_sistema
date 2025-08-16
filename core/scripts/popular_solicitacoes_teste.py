from django.utils import timezone
from core.models import Solicitacao, Formador, Municipio
from django.contrib.auth import get_user_model

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
            is_staff=True
        )

    # Busca alguns formadores e municípios existentes
    formadores = list(Formador.objects.all()[:3])
    municipios = list(Municipio.objects.all()[:2])

    if not formadores or not municipios:
        print("⚠️ É necessário ter pelo menos 1 Formador e 1 Município cadastrados.")
        return

    agora = timezone.now()

    for i in range(1, 4):
        solicitacao = Solicitacao.objects.create(
            titulo=f"Evento de Teste {i}",
            descricao=f"Descrição do evento de teste {i}",
            data_inicio=agora + timezone.timedelta(days=i),
            data_fim=agora + timezone.timedelta(days=i, hours=2),
            municipio=municipios[i % len(municipios)],
            solicitante=solicitante,
            status="pendente"
        )
        solicitacao.formadores.set([formadores[i % len(formadores)]])
        print(f"✅ Solicitação criada: {solicitacao.titulo}")
