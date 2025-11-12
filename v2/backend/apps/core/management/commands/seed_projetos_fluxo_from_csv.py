"""
Management command para classificar Projetos por fluxo a partir de CSV.

PR 13/N - Classificação de Projetos por Planilhas Oficiais

Lê arquivo CSV e atualiza campo 'fluxo' dos projetos existentes.
Matching:
- Prioridade 1: código (case-insensitive)
- Prioridade 2: nome normalizado (NFKD, casefold, sem pontuação)

Mapping de fluxos:
- SUPER → SUPER
- OUTROS → NAO_SUPER
- NAO_SUPER → NAO_SUPER
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false
Idempotente: Só atualiza se fluxo mudou.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q

from apps.core.models import Projeto


class Command(BaseCommand):
    help = "Seed Projeto.fluxo a partir de CSV (idempotente)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--csv',
            type=str,
            default='apps/core/data/projetos_fluxo.csv',
            help='Caminho do arquivo CSV (default: apps/core/data/projetos_fluxo.csv)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula execução sem persistir mudanças'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Log detalhado de cada operação'
        )

    def _normalize_string(self, s: str | None) -> str:
        """
        Normaliza string para matching robusto.

        Aplica:
        - NFKD (decomposição Unicode)
        - Remove acentos
        - Lowercase (casefold)
        - Remove caracteres não-alfanuméricos (exceto espaços)
        - Colapsa espaços múltiplos
        """
        if not s:
            return ''
        # NFKD + remove acentos
        s = unicodedata.normalize('NFKD', s)
        s = s.encode('ascii', 'ignore').decode('ascii')
        # casefold (mais robusto que lower)
        s = s.casefold()
        # Remove pontuação, mantém espaços
        s = re.sub(r'[^\w\s]', '', s)
        # Colapsa espaços
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def _map_fluxo(self, fluxo_csv: str) -> str | None:
        """
        Mapeia fluxo do CSV para choices do model.

        SUPER → SUPER
        OUTROS → NAO_SUPER
        NAO_SUPER → NAO_SUPER
        """
        fluxo_upper = fluxo_csv.upper().strip()
        if fluxo_upper == 'SUPER':
            return 'SUPER'
        elif fluxo_upper in ('OUTROS', 'NAO_SUPER'):
            return 'NAO_SUPER'
        else:
            return None  # Inválido

    def handle(self, *args: Any, **options: Any) -> None:
        csv_path = Path(options['csv'])
        dry_run = options['dry_run']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY-RUN MODE (não persiste mudanças)"))

        self.stdout.write(self.style.WARNING(f"📊 Lendo CSV: {csv_path}"))

        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f"❌ Arquivo não encontrado: {csv_path}"))
            return

        updated_count = 0
        ignored_count = 0
        not_found_count = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                codigo_csv = row.get('codigo', '').strip()
                nome_csv = row.get('nome', '').strip()
                fluxo_csv = row.get('fluxo', '').strip()

                if not nome_csv:
                    continue  # Linha vazia

                fluxo_target = self._map_fluxo(fluxo_csv)
                if fluxo_target is None:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠️ Fluxo inválido '{fluxo_csv}' para {nome_csv} (ignorado)")
                        )
                    ignored_count += 1
                    continue

                # Matching: Prioridade 1 - codigo (case-insensitive)
                projeto = None
                if codigo_csv:
                    projeto = Projeto.objects.filter(
                        Q(codigo__iexact=codigo_csv)
                    ).first()

                # Fallback: Prioridade 2 - nome normalizado
                if not projeto:
                    nome_norm = self._normalize_string(nome_csv)
                    for p in Projeto.objects.all():
                        if self._normalize_string(p.nome) == nome_norm:
                            projeto = p
                            break

                if not projeto:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"  ⊘ Projeto não encontrado: {nome_csv} (código: {codigo_csv or 'N/A'})")
                        )
                    not_found_count += 1
                    continue

                # Idempotência: só atualiza se fluxo mudou
                if projeto.fluxo == fluxo_target:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"  ⊙ Já atualizado: {projeto.nome} ({fluxo_target})")
                        )
                    ignored_count += 1
                    continue

                # Atualizar
                prev_fluxo = projeto.fluxo
                projeto.fluxo = fluxo_target

                if not dry_run:
                    projeto.save()

                if verbose or not dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ {'[DRY] ' if dry_run else ''}Atualizado: {projeto.nome} ({prev_fluxo} → {fluxo_target})"
                        )
                    )
                updated_count += 1

        # Sumário final
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {'[DRY-RUN] ' if dry_run else ''}Seed concluído:"
            )
        )
        self.stdout.write(f"   • Atualizados: {updated_count}")
        self.stdout.write(f"   • Ignorados (já OK): {ignored_count}")
        self.stdout.write(f"   • Não encontrados: {not_found_count}")
