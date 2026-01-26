"""
ETL de Produtos: Import idempotente de Produto a partir de produtos.xlsx.

Mapeia produtos.xlsx → Produto:
- id_produto → Produto.codigo
- nome_produto → Produto.nome
- nome_colecao → Produto.descricao
- nome_projeto → Produto.projeto (FK)

Idempotência: get_or_create por codigo (unique)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import Produto, Projeto
from apps.core.services.resolvers import resolve_projeto


class Command(BaseCommand):
    help = "ETL de Produtos: import idempotente a partir de produtos.xlsx"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Caminho do arquivo XLSX (produtos.xlsx)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula execução sem writes no banco",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.dry_run = options["dry_run"]
        self.file_path = options["file"]

        self.stdout.write(f"🚀 ETL Produtos (dry_run={self.dry_run})")
        self.stdout.write(f"   File: {self.file_path}")

        # Stats
        self.stats = {
            "created": 0,
            "already_exists": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        # Pendências de projetos não encontrados
        self.pending_projetos: list[dict[str, Any]] = []

        # Carregar arquivo
        self.stdout.write("\n📂 Carregando arquivo...")
        produtos = self.extract_produtos()
        self.stdout.write(f"   {len(produtos)} produtos encontrados")

        # Processar
        self.stdout.write("\n⚙️  Processando produtos...")
        with transaction.atomic():
            for produto in produtos:
                self.process_produto(produto)

            if self.dry_run:
                self.stdout.write("   [DRY-RUN] Rollback transaction")
                transaction.set_rollback(True)

        # Relatório
        self.generate_report(produtos)

        self.stdout.write(self.style.SUCCESS("\n✅ ETL concluído!"))

    def extract_produtos(self) -> list[dict[str, Any]]:
        """Extrai produtos do arquivo XLSX."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas não instalado")

        file_path = Path(self.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        df = pd.read_excel(file_path)

        produtos: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            # Extrair campos
            codigo = str(row.get("id_produto") or row.get("codigo") or "").strip()
            nome = str(row.get("nome_produto") or row.get("nome") or "").strip()
            colecao = str(row.get("nome_colecao") or row.get("colecao") or "").strip()
            projeto_nome = str(row.get("nome_projeto") or row.get("projeto") or "").strip()
            tipo_produto = str(row.get("tipo_produto") or "").strip()

            if not codigo or codigo == "nan":
                continue

            # Compor descrição: coleção + tipo (se houver)
            descricao_parts = []
            if colecao and colecao != "nan":
                descricao_parts.append(colecao)
            if tipo_produto and tipo_produto != "nan":
                descricao_parts.append(f"Tipo: {tipo_produto}")
            descricao = " | ".join(descricao_parts) if descricao_parts else ""

            produtos.append({
                "codigo": codigo,
                "nome": nome if nome != "nan" else codigo,
                "descricao": descricao,
                "projeto_nome": projeto_nome if projeto_nome != "nan" else "",
            })

        return produtos

    def process_produto(self, produto: dict[str, Any]) -> None:
        """Processa um produto."""
        codigo = produto["codigo"]
        nome = produto["nome"]
        descricao = produto["descricao"]
        projeto_nome = produto["projeto_nome"]

        if not codigo:
            self.stats["skipped"] += 1
            return

        # Resolver projeto
        projeto: Projeto | None = None
        if projeto_nome:
            projeto = resolve_projeto(projeto_nome)
            if not projeto:
                # Tentar inferir pelo nome do produto
                projeto = self._infer_projeto_from_nome(nome)

            if not projeto:
                self.pending_projetos.append({
                    "codigo": codigo,
                    "nome": nome,
                    "projeto_nome": projeto_nome,
                })
                self.stats["skipped"] += 1
                return

        # Verificar se já existe
        existing = Produto.objects.filter(codigo=codigo).first()

        if existing:
            # Verificar se precisa atualizar
            needs_update = False
            if existing.nome != nome:
                needs_update = True
            if existing.descricao != descricao:
                needs_update = True
            if projeto and existing.projeto_id != projeto.id:
                needs_update = True

            if needs_update:
                if not self.dry_run:
                    existing.nome = nome
                    existing.descricao = descricao
                    if projeto:
                        existing.projeto = projeto
                    existing.save()
                self.stats["updated"] += 1
                self.stdout.write(f"   🔄 Atualizado: {codigo}")
            else:
                self.stats["already_exists"] += 1
            return

        # Criar novo
        if projeto:
            if not self.dry_run:
                Produto.objects.create(
                    codigo=codigo,
                    nome=nome,
                    descricao=descricao,
                    projeto=projeto,
                    ativo=True,
                )
                self.stdout.write(f"   ✅ Criado: {codigo} ({nome})")
            self.stats["created"] += 1
        else:
            self.stats["skipped"] += 1
            self.pending_projetos.append({
                "codigo": codigo,
                "nome": nome,
                "projeto_nome": projeto_nome or "(não informado)",
            })

    def _infer_projeto_from_nome(self, nome: str) -> Projeto | None:
        """Infere projeto a partir do nome do produto."""
        if not nome:
            return None

        key = nome.upper()

        mappings: list[tuple[list[str], str]] = [
            (["KIT COMBO NOVO LENDO E AMMA"], "Novo Lendo"),
            (["VIDA E CIENCIA", "VIDA E CIÊNCIA"], "Vida & Ciências"),
            (["VIDA E LINGUAGEM"], "Vida & Linguagem"),
            (["VIDA E MATEMATICA", "VIDA E MATEMÁTICA"], "Vida & Matemática"),
            (["LER OUVIR E CONTAR", "LER, OUVIR E CONTAR"], "LER OUVIR E CONTAR"),
            (["LENDO E ESCREVENDO"], "LER OUVIR E CONTAR"),
            (["ESCREVER COMUNICAR E SER"], "LER OUVIR E CONTAR"),
            (["A COR DA GENTE"], "A COR DA GENTE"),
            (["BRINCANDO E APRENDENDO"], "Brincando e Aprendendo"),
            (["SOU DA PAZ"], "SOU DA PAZ"),
            (["UNI DUNI T"], "UNI DUNI TÊ"),
            (["EDUCACAO FINANCEIRA", "EDUCAÇÃO FINANCEIRA"], "ED FINANCEIRA"),
            (["AVANCANDO JUNTOS", "AVANÇANDO JUNTOS"], "Avançando Juntos Matemática"),
            (["APRENDER MAIS"], "Projeto AMMA"),
            (["SUPER ATIVAR", "SUPERATIVAR"], "Superativar"),
            (["GESTAO ESCOLAR", "GESTÃO ESCOLAR", "FORTALECIMENTO DA GESTAO", "FORTALECIMENTO DA GESTÃO"], "GESTÃO ESCOLAR"),
            (["NOVO LENDO"], "Novo Lendo"),
            (["ACERTA"], "ACerta"),
            (["FLUIR"], "Fluir"),
            (["CATAVENTOS"], "Cataventos"),
            (["MIUDEZAS"], "Miudezas"),
            (["AVALIAR"], "ACerta"),
            (["TEMA"], "Superativar"),
        ]

        for patterns, projeto_nome in mappings:
            for pattern in patterns:
                if pattern in key:
                    return resolve_projeto(projeto_nome)

        return None

    def generate_report(self, produtos: list[dict[str, Any]]) -> None:
        """Gera relatório."""
        out_dir = Path(settings.BASE_DIR) / "out_etl"
        out_dir.mkdir(exist_ok=True)

        report_path = out_dir / "etl_produtos_report.json"

        report = {
            "stats": self.stats,
            "pending_projetos": self.pending_projetos,
            "total_produtos": len(produtos),
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"\n📄 Relatório salvo em: {report_path}")
        self.stdout.write("\n📊 Stats:")
        self.stdout.write(f"   Criados: {self.stats['created']}")
        self.stdout.write(f"   Atualizados: {self.stats['updated']}")
        self.stdout.write(f"   Já existentes: {self.stats['already_exists']}")
        self.stdout.write(f"   Skipped: {self.stats['skipped']}")

        if self.pending_projetos:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Projetos não encontrados: {len(self.pending_projetos)}"))
            for p in self.pending_projetos[:5]:
                self.stdout.write(f"   - {p['codigo']}: projeto '{p['projeto_nome']}'")
            if len(self.pending_projetos) > 5:
                self.stdout.write(f"   ... e mais {len(self.pending_projetos) - 5}")
