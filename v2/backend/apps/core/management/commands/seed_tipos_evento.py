"""
Management command para popular TipoEvento com dados padrão (RF01)

Tipos de evento comuns em contexto educacional:
- Formação, Reunião, Workshop, Seminário, etc.

Idempotente: Usa get_or_create por nome
"""
from django.core.management.base import BaseCommand
from apps.core.models import TipoEvento


class Command(BaseCommand):
    help = "Seed TipoEvento com tipos padrão (idempotente)"

    TIPOS_PADRAO = [
        {"nome": "Formação", "descricao": "Formação pedagógica para professores e coordenadores"},
        {"nome": "Formação Inicial", "descricao": "Primeira formação de um projeto ou curso"},
        {"nome": "Formação Continuada", "descricao": "Formação de continuidade e aprofundamento"},
        {"nome": "Reunião", "descricao": "Reunião administrativa ou de planejamento"},
        {"nome": "Reunião Pedagógica", "descricao": "Reunião com foco pedagógico"},
        {"nome": "Workshop", "descricao": "Oficina prática hands-on"},
        {"nome": "Seminário", "descricao": "Evento de apresentação e discussão"},
        {"nome": "Palestra", "descricao": "Apresentação expositiva"},
        {"nome": "Encontro Pedagógico", "descricao": "Encontro entre educadores"},
        {"nome": "Acompanhamento", "descricao": "Visita de acompanhamento in loco"},
        {"nome": "Planejamento", "descricao": "Sessão de planejamento de atividades"},
        {"nome": "Avaliação", "descricao": "Sessão de avaliação de resultados"},
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🌱 Seed TipoEvento (RF01)"))

        created_count = 0
        existing_count = 0

        for tipo_data in self.TIPOS_PADRAO:
            tipo, created = TipoEvento.objects.get_or_create(
                nome=tipo_data["nome"],
                defaults={"descricao": tipo_data["descricao"]},
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Criado: {tipo.nome}")
                )
            else:
                existing_count += 1
                self.stdout.write(
                    self.style.WARNING(f"  ⊙ Já existe: {tipo.nome}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seed concluído: {created_count} criados, {existing_count} já existentes"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"Total no banco: {TipoEvento.objects.count()} tipos")
        )
