"""
ETL para popular EquipeGerencia a partir da planilha Usuários.xlsx.

Lê dados da planilha e vincula usuários às gerências usando CPF para match.

Usage:
    python manage.py etl_populate_equipe_from_xlsx --dry-run
    python manage.py etl_populate_equipe_from_xlsx --apply

Idempotence:
    - Usa get_or_create() para evitar duplicatas
    - Não remove registros existentes (apenas adiciona)

Mapeamento Planilha → Banco:
    - Superintendência → Super (ID=1)
    - Vidas / Vidas M / Vidas L / Vidas C → Vidas (ID=2)
    - Fluir → Fluir (ID=3)
    - ACerta → ACerta (ID=4)
    - Brincando → Brincando (ID=5)
    - Sou da Paz → Sou da Paz (ID=6)
    - IDEB 10 / Avançando Juntos → Individual (ID=7)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
from django.core.management.base import BaseCommand

from apps.core.models import EquipeGerencia, Gerencia, Usuario


# Mapeamento de gerência da planilha para nome_setor do banco
GERENCIA_MAP: dict[str, str] = {
    "Superintendência": "Super",
    "Vidas": "Vidas",
    "Vidas M": "Vidas",
    "Vidas L": "Vidas",
    "Vidas C": "Vidas",
    "Fluir": "Fluir",
    "ACerta": "ACerta",
    "Brincando": "Brincando",
    "Sou da Paz": "Sou da Paz",
    "IDEB 10": "Individual",
    "Avançando Juntos": "Individual",
    # "Outros" não tem correspondência direta
}

# Mapeamento de cargo da planilha para papel do EquipeGerencia
CARGO_MAP: dict[str, str] = {
    "Formadores": "FORMADOR",
    "Coordenadores": "COORDENADOR",
    "Gerente": "GERENTE",
}

# Mapeamento de papel para chave de estatística
PAPEL_TO_STATS_KEY: dict[str, str] = {
    "FORMADOR": "formadores_criados",
    "COORDENADOR": "coordenadores_criados",
    "GERENTE": "gerentes_criados",
}


def normalize_cpf(cpf: str | float | None) -> str | None:
    """Remove formatação do CPF, mantendo apenas dígitos."""
    if cpf is None or (isinstance(cpf, float) and pd.isna(cpf)):
        return None
    cpf_str = str(cpf).strip()
    # Remove tudo que não for dígito
    digits = re.sub(r"\D", "", cpf_str)
    if len(digits) < 9:
        return None
    # Preenche com zeros à esquerda para 11 dígitos
    return digits.zfill(11)


class Command(BaseCommand):
    """Popula EquipeGerencia a partir da planilha Usuários.xlsx."""

    help = "Popula EquipeGerencia a partir da planilha Usuários.xlsx"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula, não altera o banco",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica as alterações no banco",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostra detalhes de cada operação",
        )
        parser.add_argument(
            "--xlsx-path",
            type=str,
            default="/app/data/csv-import/todososusuarios.xlsx",
            help="Caminho para a planilha (default: todososusuarios.xlsx)",
        )

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        dry_run = options.get("dry_run", False)
        apply = options.get("apply", False)
        verbose = options.get("verbose", False)
        xlsx_path = options.get("xlsx_path", "/app/data/csv-import/todososusuarios.xlsx")

        if not dry_run and not apply:
            self.stderr.write(
                self.style.ERROR("Especifique --dry-run ou --apply")
            )
            return

        self.stdout.write("=" * 70)
        self.stdout.write("ETL: POPULAR EQUIPE GERENCIA (PLANILHA)")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Modo: {'DRY-RUN (simulação)' if dry_run else 'APPLY (produção)'}")
        self.stdout.write(f"Planilha: {xlsx_path}")
        self.stdout.write("")

        # Verificar se arquivo existe
        if not Path(xlsx_path).exists():
            self.stderr.write(
                self.style.ERROR(f"Arquivo não encontrado: {xlsx_path}")
            )
            return

        # Carregar planilha
        df = pd.read_excel(xlsx_path)
        self.stdout.write(f"Linhas na planilha: {len(df)}")
        self.stdout.write("")

        # Carregar gerências do banco
        gerencias_db: dict[str, Gerencia] = {}
        for g in Gerencia.objects.all():
            gerencias_db[g.nome_setor] = g
        self.stdout.write(f"Gerências no banco: {len(gerencias_db)}")
        for nome_setor, g in gerencias_db.items():
            self.stdout.write(f"  - {nome_setor} (ID={g.id})")
        self.stdout.write("")

        # Carregar usuários do banco indexados por CPF
        usuarios_db: dict[str, Usuario] = {}
        for u in Usuario.objects.all():
            if u.cpf:
                cpf_norm = normalize_cpf(u.cpf)
                if cpf_norm:
                    usuarios_db[cpf_norm] = u
        self.stdout.write(f"Usuários no banco com CPF: {len(usuarios_db)}")
        self.stdout.write("")

        # Estatísticas
        stats = {
            "linhas_processadas": 0,
            "gerencia_nao_mapeada": 0,
            "cargo_nao_mapeado": 0,
            "cpf_invalido": 0,
            "usuario_nao_encontrado": 0,
            "gerentes_criados": 0,
            "coordenadores_criados": 0,
            "formadores_criados": 0,
            "ja_existentes": 0,
            "erros": 0,
        }

        # Processar cada linha
        for idx, row in df.iterrows():
            stats["linhas_processadas"] += 1

            # Extrair dados
            nome = row.get("Nome", "")
            cpf_raw = row.get("CPF")
            cargo = row.get("Cargo", "")
            gerencia_planilha = row.get("Gerência", "")

            # Normalizar CPF
            cpf = normalize_cpf(cpf_raw)
            if not cpf:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(f"  [SKIP] Linha {idx+1}: CPF inválido ({cpf_raw})")
                    )
                stats["cpf_invalido"] += 1
                continue

            # Mapear gerência
            nome_setor = GERENCIA_MAP.get(gerencia_planilha)
            if not nome_setor:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [SKIP] Linha {idx+1} ({nome}): Gerência não mapeada ({gerencia_planilha})"
                        )
                    )
                stats["gerencia_nao_mapeada"] += 1
                continue

            gerencia = gerencias_db.get(nome_setor)
            if not gerencia:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [SKIP] Linha {idx+1} ({nome}): Gerência não encontrada no banco ({nome_setor})"
                        )
                    )
                stats["gerencia_nao_mapeada"] += 1
                continue

            # Mapear cargo
            papel = CARGO_MAP.get(cargo)
            if not papel:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [SKIP] Linha {idx+1} ({nome}): Cargo não mapeado ({cargo})"
                        )
                    )
                stats["cargo_nao_mapeado"] += 1
                continue

            # Buscar usuário por CPF
            usuario = usuarios_db.get(cpf)
            if not usuario:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [SKIP] Linha {idx+1} ({nome}): Usuário não encontrado no banco (CPF: {cpf})"
                        )
                    )
                stats["usuario_nao_encontrado"] += 1
                continue

            # Criar vínculo
            result = self._criar_equipe(gerencia, usuario, papel, dry_run, verbose, nome)
            self._update_stats(stats, result, PAPEL_TO_STATS_KEY[papel])

        # Também processar formadores_fluir.xlsx para o Fluir
        fluir_path = "/app/data/csv-import/formadores_fluir.xlsx"
        if Path(fluir_path).exists():
            self.stdout.write("")
            self.stdout.write("=" * 50)
            self.stdout.write("Processando formadores_fluir.xlsx...")
            self.stdout.write("=" * 50)

            df_fluir = pd.read_excel(fluir_path)
            gerencia_fluir = gerencias_db.get("Fluir")

            if gerencia_fluir:
                for idx, row in df_fluir.iterrows():
                    stats["linhas_processadas"] += 1

                    nome = row.get("Nome", "")
                    cpf_raw = row.get("CPF")
                    cpf = normalize_cpf(cpf_raw)

                    if not cpf:
                        stats["cpf_invalido"] += 1
                        continue

                    usuario = usuarios_db.get(cpf)
                    if not usuario:
                        if verbose:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  [SKIP] {nome}: Usuário não encontrado (CPF: {cpf})"
                                )
                            )
                        stats["usuario_nao_encontrado"] += 1
                        continue

                    result = self._criar_equipe(
                        gerencia_fluir, usuario, "FORMADOR", dry_run, verbose, nome
                    )
                    self._update_stats(stats, result, "formadores_criados")

        # Resumo
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("RESUMO")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Linhas processadas: {stats['linhas_processadas']}")
        self.stdout.write(f"Gerentes criados: {stats['gerentes_criados']}")
        self.stdout.write(f"Coordenadores criados: {stats['coordenadores_criados']}")
        self.stdout.write(f"Formadores criados: {stats['formadores_criados']}")
        self.stdout.write(f"Já existentes (skip): {stats['ja_existentes']}")
        self.stdout.write("")
        self.stdout.write(f"Gerência não mapeada: {stats['gerencia_nao_mapeada']}")
        self.stdout.write(f"Cargo não mapeado: {stats['cargo_nao_mapeado']}")
        self.stdout.write(f"CPF inválido: {stats['cpf_invalido']}")
        self.stdout.write(f"Usuário não encontrado: {stats['usuario_nao_encontrado']}")
        self.stdout.write(f"Erros: {stats['erros']}")

        total_criados = (
            stats["gerentes_criados"]
            + stats["coordenadores_criados"]
            + stats["formadores_criados"]
        )
        self.stdout.write("")
        self.stdout.write(f"TOTAL CRIADOS: {total_criados}")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("DRY-RUN: Nenhuma alteração foi feita no banco.")
            )
            self.stdout.write("Execute com --apply para aplicar as alterações.")

    def _criar_equipe(
        self,
        gerencia: Gerencia,
        usuario: Usuario,
        papel: str,
        dry_run: bool,
        verbose: bool,
        nome_planilha: str,
    ) -> str:
        """
        Cria registro em EquipeGerencia.

        Returns:
            "created", "exists", ou "error"
        """
        nome = usuario.get_full_name() or usuario.username

        if dry_run:
            exists = EquipeGerencia.objects.filter(
                gerencia=gerencia,
                usuario=usuario,
                papel=papel,
            ).exists()

            if exists:
                if verbose:
                    self.stdout.write(f"    [SKIP] {nome} já é {papel} em {gerencia.nome_setor}")
                return "exists"
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"    [+] {nome} → {papel} em {gerencia.nome_setor}"
                    )
                )
                return "created"

        # APPLY mode
        try:
            obj, created = EquipeGerencia.objects.get_or_create(
                gerencia=gerencia,
                usuario=usuario,
                papel=papel,
                defaults={"ativo": True},
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"    [+] {nome} → {papel} em {gerencia.nome_setor}"
                    )
                )
                return "created"
            else:
                if verbose:
                    self.stdout.write(f"    [SKIP] {nome} já é {papel} em {gerencia.nome_setor}")
                return "exists"

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"    [ERRO] {nome}: {e}")
            )
            return "error"

    def _update_stats(
        self,
        stats: dict[str, int],
        result: str,
        created_key: str,
    ) -> None:
        """Atualiza estatísticas baseado no resultado."""
        if result == "created":
            stats[created_key] += 1
        elif result == "exists":
            stats["ja_existentes"] += 1
        elif result == "error":
            stats["erros"] += 1
