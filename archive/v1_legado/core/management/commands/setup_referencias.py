# aprender_sistema/core/management/commands/setup_referencias.py
from django.core.management.base import BaseCommand

from core.models import Municipio, Projeto, TipoEvento

PROJETOS = ["Alfabetização", "Formação Continuada", "Projeto X"]
TIPOS = ["Presencial", "Online", "Híbrido"]
MUNICIPIOS = [("Fortaleza", "CE"), ("Caucaia", "CE"), ("Sobral", "CE")]


class Command(BaseCommand):
    help = "Cria dados mínimos de referência (Projetos, Tipos de Evento, Municípios)."

    def handle(self, *args, **options):
        for nome in PROJETOS:
            Projeto.objects.get_or_create(nome=nome)
        for nome in TIPOS:
            TipoEvento.objects.get_or_create(nome=nome)
        for nome, uf in MUNICIPIOS:
            Municipio.objects.get_or_create(nome=nome, uf=uf)
        self.stdout.write(self.style.SUCCESS("Referências criadas/verificadas."))
