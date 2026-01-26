"""
ETL de Equipe/Gerência: Import idempotente de EquipeGerencia.

Mapeia gerentes_coordenadores_apoio_formadores_setores.xlsx → EquipeGerencia:
- Cada aba representa um setor (Superintendência, Brincando e Aprendendo, ACerta, etc)
- Colunas: Gerentes, Coordenadores, Apoio de Coordenação, Formadores
- Cria Gerencia se não existir
- Associa Usuario com papel (GERENTE/COORDENADOR/APOIO/FORMADOR)

Idempotência: get_or_create por (gerencia, usuario, papel)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import EquipeGerencia, Gerencia, Usuario
from apps.core.services.resolvers import resolve_user_by_name


# Mapeamento de nomes de aba → nome_setor canônico
SETOR_MAPPING = {
    "Superintendência": "Superintendência",
    "Super": "Superintendência",
    "SUPER": "Superintendência",
    "Brincando e Aprendendo": "Brincando e Aprendendo",
    "Brincando": "Brincando e Aprendendo",
    "ACerta": "ACerta",
    "Acerta": "ACerta",
    "ACERTA": "ACerta",
    "Fluir das Emoções": "Fluir",
    "Fluir": "Fluir",
    "FLUIR": "Fluir",
    "Vidas": "Vidas",
    "VIDAS": "Vidas",
    "A Cor da Gente": "A Cor da Gente",
    "Sou da Paz": "Sou da Paz",
    "Educação Financeira": "Educação Financeira",
    "Ed Financeira": "Educação Financeira",
    "Ler, Ouvir e Contar": "Ler, Ouvir e Contar",
    "Ler Ouvir e Contar": "Ler, Ouvir e Contar",
    "Avançando Juntos": "Avançando Juntos",
    "IDEB10": "IDEB10",
    "My Companion": "My Companion",
}

# Mapeamento de nome de coluna → papel
PAPEL_MAPPING = {
    "Gerentes": "GERENTE",
    "Gerente": "GERENTE",
    "GERENTE": "GERENTE",
    "Coordenadores": "COORDENADOR",
    "Coordenador": "COORDENADOR",
    "COORDENADOR": "COORDENADOR",
    "Apoio de Coordenação": "APOIO",
    "Apoio": "APOIO",
    "APOIO": "APOIO",
    "Formadores": "FORMADOR",
    "Formador": "FORMADOR",
    "FORMADOR": "FORMADOR",
}


class Command(BaseCommand):
    help = "ETL de Equipe/Gerência: import idempotente a partir de gerentes_coordenadores...xlsx"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do arquivo XLSX (gerentes_coordenadores_apoio_formadores_setores.xlsx)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem writes no banco",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.dry_run = options["dry_run"]
        self.file_path = options["file"]

        self.stdout.write(f"🚀 ETL Equipe/Gerência (dry_run={self.dry_run})")
        self.stdout.write(f"   File: {self.file_path}")

        # Stats
        self.stats = {
            "gerencias_created": 0,
            "gerencias_existing": 0,
            "equipes_created": 0,
            "equipes_existing": 0,
            "skipped": 0,
        }

        # Pendências de usuários não encontrados
        self.pending_usuarios: list[dict[str, Any]] = []

        # Carregar arquivo
        self.stdout.write("\n📂 Carregando arquivo...")
        equipes = self.extract_equipes()
        self.stdout.write(f"   {len(equipes)} registros de equipe encontrados")

        # Processar
        self.stdout.write("\n⚙️  Processando equipes...")
        with transaction.atomic():
            for equipe in equipes:
                self.process_equipe(equipe)

            if self.dry_run:
                self.stdout.write("   [DRY-RUN] Rollback transaction")
                transaction.set_rollback(True)

        # Relatório
        self.generate_report(equipes)

        self.stdout.write(self.style.SUCCESS("\n✅ ETL concluído!"))

    def extract_equipes(self) -> list[dict[str, Any]]:
        """Extrai dados de equipes do arquivo XLSX."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas não instalado")

        file_path = Path(self.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        xl = pd.ExcelFile(file_path)

        equipes: list[dict[str, Any]] = []

        for sheet_name in xl.sheet_names:
            # Normalizar nome do setor
            nome_setor = SETOR_MAPPING.get(sheet_name, sheet_name)

            self.stdout.write(f"   Lendo aba: {sheet_name} → Setor: {nome_setor}")

            df = pd.read_excel(xl, sheet_name=sheet_name)

            # Processar cada coluna (Gerentes, Coordenadores, etc)
            for col in df.columns:
                papel = PAPEL_MAPPING.get(col)
                if not papel:
                    continue

                # Extrair nomes da coluna
                for valor in df[col].dropna():
                    nome = str(valor).strip()
                    if nome and nome != "nan":
                        equipes.append({
                            "setor": nome_setor,
                            "papel": papel,
                            "usuario_nome": nome,
                        })

        return equipes

    def process_equipe(self, equipe: dict[str, Any]) -> None:
        """Processa um registro de equipe."""
        setor = equipe["setor"]
        papel = equipe["papel"]
        usuario_nome = equipe["usuario_nome"]

        # 1. Resolver ou criar Gerencia
        gerencia = self._get_or_create_gerencia(setor)
        if not gerencia:
            self.stats["skipped"] += 1
            return

        # 2. Pular APOIO (requer coordenador_supervisor que não temos na planilha)
        if papel == "APOIO":
            self.stats["skipped"] += 1
            return

        # 3. Resolver usuário
        usuario = resolve_user_by_name(usuario_nome)
        if not usuario:
            self.pending_usuarios.append({
                "setor": setor,
                "papel": papel,
                "usuario_nome": usuario_nome,
            })
            self.stats["skipped"] += 1
            return

        # 4. Criar EquipeGerencia
        existing = EquipeGerencia.objects.filter(
            gerencia=gerencia,
            usuario=usuario,
            papel=papel,
        ).exists()

        if existing:
            self.stats["equipes_existing"] += 1
            return

        if not self.dry_run:
            EquipeGerencia.objects.create(
                gerencia=gerencia,
                usuario=usuario,
                papel=papel,
            )
            self.stdout.write(f"   ✅ {setor} | {papel} | {usuario_nome}")

        self.stats["equipes_created"] += 1

    def _get_or_create_gerencia(self, nome_setor: str) -> Gerencia | None:
        """Obtém ou cria uma Gerencia pelo nome do setor."""
        # Gerar nome de gerência baseado no setor
        nome_gerencia = self._generate_gerencia_nome(nome_setor)

        # Buscar por nome_setor
        gerencia = Gerencia.objects.filter(nome_setor__iexact=nome_setor).first()
        if gerencia:
            self.stats["gerencias_existing"] += 1
            return gerencia

        # Buscar por nome do setor como nome da gerência
        gerencia = Gerencia.objects.filter(nome__iexact=nome_setor).first()
        if gerencia:
            self.stats["gerencias_existing"] += 1
            return gerencia

        # Buscar pelo nome gerado da gerência
        gerencia = Gerencia.objects.filter(nome__iexact=nome_gerencia).first()
        if gerencia:
            self.stats["gerencias_existing"] += 1
            return gerencia

        # Criar nova gerência
        if not self.dry_run:
            gerencia, created = Gerencia.objects.get_or_create(
                nome=nome_gerencia,
                defaults={
                    "nome_setor": nome_setor,
                    "ativo": True,
                }
            )
            if created:
                self.stdout.write(f"   🆕 Gerência criada: {nome_gerencia} ({nome_setor})")
                self.stats["gerencias_created"] += 1
            else:
                self.stats["gerencias_existing"] += 1
            return gerencia
        else:
            self.stats["gerencias_created"] += 1
            # Retornar None em dry-run para não falhar depois
            # mas contar como "seria criada"
            return Gerencia.objects.filter(nome_setor__icontains=nome_setor[:5]).first()

    def _generate_gerencia_nome(self, nome_setor: str) -> str:
        """Gera nome de gerência baseado no setor."""
        # Mapeamento de setor → nome de gerência
        mapping = {
            "Superintendência": "SUPERINTENDENCIA",
            "Brincando e Aprendendo": "GERENCIA BRINCANDO",
            "ACerta": "GERENCIA ACERTA",
            "Fluir": "GERENCIA FLUIR",
            "Vidas": "GERENCIA VIDAS",
            "A Cor da Gente": "GERENCIA A COR DA GENTE",
            "Sou da Paz": "GERENCIA SOU DA PAZ",
            "Educação Financeira": "GERENCIA ED FINANCEIRA",
            "Ler, Ouvir e Contar": "GERENCIA LER OUVIR E CONTAR",
            "Avançando Juntos": "GERENCIA AVANCANDO JUNTOS",
            "IDEB10": "GERENCIA IDEB10",
            "My Companion": "GERENCIA MY COMPANION",
        }
        return mapping.get(nome_setor, f"GERENCIA {nome_setor.upper()}")

    def generate_report(self, equipes: list[dict[str, Any]]) -> None:
        """Gera relatório."""
        out_dir = Path(settings.BASE_DIR) / "out_etl"
        out_dir.mkdir(exist_ok=True)

        report_path = out_dir / "etl_equipe_gerencia_report.json"

        report = {
            "stats": self.stats,
            "pending_usuarios": self.pending_usuarios,
            "total_registros": len(equipes),
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"\n📄 Relatório salvo em: {report_path}")
        self.stdout.write("\n📊 Stats:")
        self.stdout.write(f"   Gerências criadas: {self.stats['gerencias_created']}")
        self.stdout.write(f"   Gerências existentes: {self.stats['gerencias_existing']}")
        self.stdout.write(f"   Equipes criadas: {self.stats['equipes_created']}")
        self.stdout.write(f"   Equipes existentes: {self.stats['equipes_existing']}")
        self.stdout.write(f"   Skipped: {self.stats['skipped']}")

        if self.pending_usuarios:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Usuários não encontrados: {len(self.pending_usuarios)}"))
            for p in self.pending_usuarios[:10]:
                self.stdout.write(f"   - {p['setor']} | {p['papel']} | {p['usuario_nome']}")
            if len(self.pending_usuarios) > 10:
                self.stdout.write(f"   ... e mais {len(self.pending_usuarios) - 10}")
