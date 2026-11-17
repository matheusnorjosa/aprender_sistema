"""
Preenche latitude/longitude de core_municipio pelo codigo IBGE (FER-66).

Fonte: `data/municipios_coordenadas_ibge.csv`, recorte (codigo_ibge, latitude,
longitude) da base publica kelvins/municipios-brasileiros, licenca MIT (ver
`data/README.md`). A tela Mapa do Brasil so mostra municipio com coordenada.

Regras:
- Casa SO pelo `ibge_code`; o nome nao entra (grafia varia, codigo nao).
- So preenche quem esta sem latitude ou longitude; quem ja tem fica como esta.
- Ensaio por padrao. `--apply` grava tudo numa transacao.
- O arquivo e validado inteiro antes de qualquer gravacao: codigo de 7 digitos sem
  repeticao, coordenada numerica dentro da faixa e um numero minimo de linhas (um
  arquivo cortado nao passa por base inteira).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.core.models import Municipio

if TYPE_CHECKING:
    from argparse import ArgumentParser

ARQUIVO_PADRAO = Path(settings.BASE_DIR) / "data" / "municipios_coordenadas_ibge.csv"
# O Brasil tem 5.570 municipios (+ Brasilia na base); bem abaixo disso, o arquivo veio cortado.
MINIMO_PADRAO = 5000
_CODIGO = re.compile(r"^\d{7}$")
_SEIS_CASAS = Decimal("0.000001")


def _coordenada(valor: str, limite: int, linha: int) -> Decimal:
    try:
        d = Decimal(valor.strip()).quantize(_SEIS_CASAS)
    except (InvalidOperation, ValueError) as e:
        raise CommandError(f"linha {linha}: coordenada {valor!r} nao e numero") from e
    if not d.is_finite() or not -limite <= d <= limite:
        raise CommandError(f"linha {linha}: coordenada {valor!r} fora de -{limite}..{limite}")
    return d


def ler_base(caminho: Path) -> dict[str, tuple[Decimal, Decimal]]:
    """Le e valida o arquivo inteiro: {codigo_ibge: (latitude, longitude)}."""
    base: dict[str, tuple[Decimal, Decimal]] = {}
    with open(caminho, encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        faltam = {"codigo_ibge", "latitude", "longitude"} - set(leitor.fieldnames or [])
        if faltam:
            raise CommandError(f"cabecalho sem as colunas {sorted(faltam)}")
        for n, row in enumerate(leitor, start=2):  # linha 1 e o cabecalho
            codigo = (row["codigo_ibge"] or "").strip()
            if not _CODIGO.match(codigo):
                raise CommandError(f"linha {n}: codigo IBGE {codigo!r} nao tem 7 digitos")
            if codigo in base:
                raise CommandError(f"linha {n}: codigo IBGE {codigo} repetido no arquivo")
            base[codigo] = (
                _coordenada(row["latitude"] or "", 90, n),
                _coordenada(row["longitude"] or "", 180, n),
            )
    return base


class Command(BaseCommand):
    help = "Preenche latitude/longitude dos municipios pelo codigo IBGE (ensaio por padrao)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--apply", action="store_true", help="Grava. Sem ele, so mostra o que faria.")
        parser.add_argument(
            "--csv", type=str, default=str(ARQUIVO_PADRAO), help="Arquivo codigo_ibge,latitude,longitude."
        )
        parser.add_argument(
            "--minimo",
            type=int,
            default=MINIMO_PADRAO,
            help=f"Minimo de linhas para aceitar o arquivo (padrao {MINIMO_PADRAO}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        aplicar = bool(options["apply"])
        base = ler_base(Path(options["csv"]))
        if len(base) < options["minimo"]:
            raise CommandError(f"o arquivo tem {len(base)} linhas, abaixo do minimo de {options['minimo']}")

        with transaction.atomic():
            sem_codigo = Municipio.objects.filter(Q(ibge_code__isnull=True) | Q(ibge_code="")).count()
            candidatos = Municipio.objects.exclude(ibge_code__isnull=True).exclude(ibge_code="").order_by("pk")
            if aplicar:
                # Trava as linhas lidas: ninguem preenche no meio e e sobrescrito aqui.
                candidatos = candidatos.select_for_update()
            preencher: list[Municipio] = []
            fora_da_base = igual = diferente = 0
            for m in candidatos:
                coord = base.get(m.ibge_code.strip())
                if coord is None:
                    fora_da_base += 1
                elif m.latitude is None or m.longitude is None:
                    m.latitude, m.longitude = coord
                    preencher.append(m)
                elif (m.latitude, m.longitude) == coord:
                    igual += 1
                else:
                    diferente += 1
            if aplicar:
                Municipio.objects.bulk_update(preencher, ["latitude", "longitude"], batch_size=500)

        verbo = "preenchidos" if aplicar else "preencheria"
        self.stdout.write("GRAVADO" if aplicar else "ENSAIO (nada gravado; use --apply)")
        self.stdout.write(f"linhas na base: {len(base)}")
        self.stdout.write(f"{verbo}: {len(preencher)}")
        self.stdout.write(f"ja tinha, igual a base: {igual}")
        self.stdout.write(f"ja tinha, diferente da base: {diferente}")
        self.stdout.write(f"sem codigo IBGE: {sem_codigo}")
        self.stdout.write(f"codigo fora da base: {fora_da_base}")
