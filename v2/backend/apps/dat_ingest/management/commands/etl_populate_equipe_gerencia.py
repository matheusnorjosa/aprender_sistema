"""
ETL para popular EquipeGerencia a partir de dados de Participation.

Infere a estrutura de equipe de cada gerência analisando:
1. Participations em Solicitações aprovadas
2. Projetos vinculados às gerências
3. Perfil do usuário (grupos RBAC)

Usage:
    python manage.py etl_populate_equipe_gerencia --dry-run
    python manage.py etl_populate_equipe_gerencia --apply

Idempotence:
    - Usa get_or_create() para evitar duplicatas
    - Não remove registros existentes (apenas adiciona)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from apps.core.models import (
    EquipeGerencia,
    Gerencia,
    Participation,
    Usuario,
)


class Command(BaseCommand):
    """Popula EquipeGerencia inferindo de Participations."""

    help = "Popula EquipeGerencia a partir de dados de Participation"

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

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        dry_run = options.get("dry_run", False)
        apply = options.get("apply", False)
        verbose = options.get("verbose", False)

        if not dry_run and not apply:
            self.stderr.write(
                self.style.ERROR("Especifique --dry-run ou --apply")
            )
            return

        self.stdout.write("=" * 70)
        self.stdout.write("ETL: POPULAR EQUIPE GERENCIA")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Modo: {'DRY-RUN (simulação)' if dry_run else 'APPLY (produção)'}")
        self.stdout.write("")

        # Estatísticas
        stats = {
            "gerencias_processadas": 0,
            "usuarios_vinculados": 0,
            "gerentes_criados": 0,
            "coordenadores_criados": 0,
            "formadores_criados": 0,
            "ja_existentes": 0,
            "erros": 0,
        }

        # 1. Buscar todas as gerências
        gerencias = Gerencia.objects.all().order_by("nome")
        self.stdout.write(f"Gerências encontradas: {gerencias.count()}")
        self.stdout.write("")

        # 2. Para cada gerência, inferir equipe
        for gerencia in gerencias:
            self.stdout.write(f"\n{'='*50}")
            self.stdout.write(f"GERÊNCIA: {gerencia.nome} ({gerencia.nome_setor})")
            self.stdout.write(f"{'='*50}")

            stats["gerencias_processadas"] += 1

            # 2.1. Buscar usuários que participaram de eventos dessa gerência
            usuarios_por_role = self._get_usuarios_por_gerencia(gerencia)

            if not usuarios_por_role["FORMADOR"] and not usuarios_por_role["COORDENADOR"]:
                self.stdout.write(self.style.WARNING("  Nenhum usuário encontrado via Participation"))
                continue

            # 2.2. Identificar gerente (usuário com grupo "Gerente" + mais participações)
            gerente = self._identificar_gerente(gerencia, usuarios_por_role)
            if gerente:
                result = self._criar_equipe(
                    gerencia, gerente, "GERENTE", dry_run, verbose
                )
                self._update_stats(stats, result, "gerentes_criados")

            # 2.3. Criar coordenadores
            for usuario in usuarios_por_role["COORDENADOR"]:
                if usuario == gerente:
                    continue  # Já é gerente
                result = self._criar_equipe(
                    gerencia, usuario, "COORDENADOR", dry_run, verbose
                )
                self._update_stats(stats, result, "coordenadores_criados")

            # 2.4. Criar formadores
            for usuario in usuarios_por_role["FORMADOR"]:
                if usuario == gerente:
                    continue  # Já é gerente
                if usuario in usuarios_por_role["COORDENADOR"]:
                    continue  # Já é coordenador
                result = self._criar_equipe(
                    gerencia, usuario, "FORMADOR", dry_run, verbose
                )
                self._update_stats(stats, result, "formadores_criados")

        # 3. Resumo
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("RESUMO")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Gerências processadas: {stats['gerencias_processadas']}")
        self.stdout.write(f"Gerentes criados: {stats['gerentes_criados']}")
        self.stdout.write(f"Coordenadores criados: {stats['coordenadores_criados']}")
        self.stdout.write(f"Formadores criados: {stats['formadores_criados']}")
        self.stdout.write(f"Já existentes (skip): {stats['ja_existentes']}")
        self.stdout.write(f"Erros: {stats['erros']}")
        total_criados = (
            stats["gerentes_criados"]
            + stats["coordenadores_criados"]
            + stats["formadores_criados"]
        )
        self.stdout.write(f"TOTAL CRIADOS: {total_criados}")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("⚠️  DRY-RUN: Nenhuma alteração foi feita no banco.")
            )
            self.stdout.write("    Execute com --apply para aplicar as alterações.")

    def _get_usuarios_por_gerencia(
        self, gerencia: Gerencia
    ) -> dict[str, list[Usuario]]:
        """
        Busca usuários que participaram de eventos da gerência.

        Returns:
            {"FORMADOR": [Usuario, ...], "COORDENADOR": [Usuario, ...]}
        """
        result: dict[str, list[Usuario]] = {"FORMADOR": [], "COORDENADOR": []}

        # Buscar participations de solicitações com projetos dessa gerência
        participations = (
            Participation.objects.filter(
                solicitacao__projeto__gerencia=gerencia,
                usuario__isnull=False,
            )
            .select_related("usuario")
            .values("usuario", "role")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Agrupar por role
        seen_formadores: set[int] = set()
        seen_coordenadores: set[int] = set()

        for p in participations:
            usuario_id = p["usuario"]
            role = p["role"]

            try:
                usuario = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                continue

            if role == "FORMADOR" and usuario_id not in seen_formadores:
                result["FORMADOR"].append(usuario)
                seen_formadores.add(usuario_id)
            elif role == "COORDENADOR" and usuario_id not in seen_coordenadores:
                result["COORDENADOR"].append(usuario)
                seen_coordenadores.add(usuario_id)

        self.stdout.write(f"  Formadores encontrados: {len(result['FORMADOR'])}")
        self.stdout.write(f"  Coordenadores encontrados: {len(result['COORDENADOR'])}")

        return result

    def _identificar_gerente(
        self,
        gerencia: Gerencia,
        usuarios_por_role: dict[str, list[Usuario]],
    ) -> Usuario | None:
        """
        Identifica o gerente da gerência.

        Prioridade:
        1. Usuario com grupo "Gerente" que participou de eventos
        2. Coordenador com mais participações
        """
        # Candidatos: coordenadores + formadores
        candidatos = (
            usuarios_por_role["COORDENADOR"] + usuarios_por_role["FORMADOR"]
        )

        # Filtrar por grupo "Gerente"
        gerentes_potenciais = [
            u for u in candidatos
            if u.groups.filter(name="Gerente").exists()
        ]

        if gerentes_potenciais:
            gerente = gerentes_potenciais[0]
            self.stdout.write(
                f"  Gerente identificado (grupo Gerente): {gerente.get_full_name() or gerente.username}"
            )
            return gerente

        # Fallback: coordenador com mais participações
        if usuarios_por_role["COORDENADOR"]:
            gerente = usuarios_por_role["COORDENADOR"][0]
            self.stdout.write(
                f"  Gerente identificado (coord principal): {gerente.get_full_name() or gerente.username}"
            )
            return gerente

        self.stdout.write(self.style.WARNING("  Nenhum gerente identificado"))
        return None

    def _criar_equipe(
        self,
        gerencia: Gerencia,
        usuario: Usuario,
        papel: str,
        dry_run: bool,
        verbose: bool,
    ) -> str:
        """
        Cria registro em EquipeGerencia.

        Returns:
            "created", "exists", ou "error"
        """
        nome = usuario.get_full_name() or usuario.username

        if dry_run:
            # Verificar se já existe
            exists = EquipeGerencia.objects.filter(
                gerencia=gerencia,
                usuario=usuario,
                papel=papel,
            ).exists()

            if exists:
                if verbose:
                    self.stdout.write(f"    [SKIP] {nome} já é {papel}")
                return "exists"
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"    [+] {nome} → {papel}")
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
                    self.style.SUCCESS(f"    [+] {nome} → {papel}")
                )
                return "created"
            else:
                if verbose:
                    self.stdout.write(f"    [SKIP] {nome} já é {papel}")
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
            stats["usuarios_vinculados"] += 1
        elif result == "exists":
            stats["ja_existentes"] += 1
        elif result == "error":
            stats["erros"] += 1
