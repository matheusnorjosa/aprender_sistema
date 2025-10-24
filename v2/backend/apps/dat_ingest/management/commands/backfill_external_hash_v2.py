"""
Backfill external_hash v2 em Solicitacoes existentes (PR21).

Este comando atualiza o campo external_hash de todas as Solicitações
usando a nova função hash_event_v2() com 17 campos normalizados.

SEGURANÇA:
- --dry-run (default): apenas mostra o que seria feito
- --apply: executa as atualizações

OUTPUTS:
- external_hash_v2_collisions.json: relatório de colisões detectadas
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Solicitacao
from apps.dat_ingest.services.acompanhamento_normalize import hash_event_v2


class Command(BaseCommand):
    help = "Backfill external_hash v2 em Solicitações (PR21)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplicar atualizações (sem este flag, apenas dry-run)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limitar processamento a N solicitações (para testes)",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        limit = options["limit"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("BACKFILL EXTERNAL_HASH V2 (PR21)")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Modo: {'APLICAR' if apply else 'DRY-RUN'}")
        if limit:
            self.stdout.write(f"Limit: {limit} solicitações\n")
        else:
            self.stdout.write("Limit: Todas as solicitações\n")

        # Carregar solicitações
        queryset = Solicitacao.objects.select_related(
            "municipio", "tipo_evento", "projeto", "coordenador"
        ).prefetch_related("formadores")

        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        self.stdout.write(f"📊 Total de solicitações: {total}\n")

        if total == 0:
            self.stdout.write(self.style.WARNING("⚠️  Nenhuma solicitação encontrada"))
            return

        # Estatísticas
        stats = {
            "total": total,
            "would_update": 0,
            "unchanged": 0,
            "errors": 0,
        }

        # Mapeamento hash → list[Solicitacao IDs] para detectar colisões
        hash_map: Dict[str, List[int]] = defaultdict(list)

        # Processar cada solicitação
        for sol in queryset:
            try:
                # Construir dicionário de dados para hash_event_v2
                row = self.build_row_from_solicitacao(sol)

                # Calcular hash v2
                new_hash = hash_event_v2(row)

                # Registrar no mapa de colisões
                hash_map[new_hash].append(sol.id)

                # Comparar com hash atual
                if sol.external_hash != new_hash:
                    stats["would_update"] += 1

                    if apply:
                        with transaction.atomic():
                            sol.external_hash = new_hash
                            sol.save(update_fields=["external_hash"])
                else:
                    stats["unchanged"] += 1

            except Exception as e:
                stats["errors"] += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Erro na solicitação {sol.id}: {e}")
                )

        # Detectar colisões (hash mapeado a 2+ solicitações)
        collisions = {
            hash_val: ids for hash_val, ids in hash_map.items() if len(ids) > 1
        }

        # Relatório de sumário
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("📊 SUMÁRIO:")
        self.stdout.write(f"   Total processadas: {stats['total']}")
        self.stdout.write(f"   Would update: {stats['would_update']}")
        self.stdout.write(f"   Unchanged: {stats['unchanged']}")
        self.stdout.write(f"   Errors: {stats['errors']}")
        self.stdout.write(f"   Colisões detectadas: {len(collisions)}")
        self.stdout.write("-" * 80)

        # Gerar relatório de colisões (se houver)
        if collisions:
            self.generate_collisions_report(collisions)
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  {len(collisions)} colisões detectadas!"
                )
            )
            self.stdout.write(
                "   Veja: v2/.agents/outbox/external_hash_v2_collisions.json"
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✅ Nenhuma colisão detectada!")
            )

        if not apply:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN: Use --apply para atualizar")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ {stats['would_update']} solicitações atualizadas!"
                )
            )

        self.stdout.write("\n✅ Backfill concluído!\n")

    def build_row_from_solicitacao(self, sol: Solicitacao) -> Dict[str, str]:
        """
        Constrói dicionário de dados para hash_event_v2 a partir de Solicitacao.

        Args:
            sol: Instância de Solicitacao

        Returns:
            Dict com campos normalizados
        """
        # Formadores (até 5)
        formadores = list(sol.formadores.all())
        formadores_emails = [f.email for f in formadores]
        while len(formadores_emails) < 5:
            formadores_emails.append("")

        # source_sheet: inferir a partir do projeto ou tipo
        # (simplificação: usar projeto.nome como proxy)
        source_sheet = self.infer_source_sheet(sol)

        return {
            "source_sheet": source_sheet,
            "municipio": sol.municipio.nome if sol.municipio else "",
            "encontro": sol.encontro or "",
            "tipo": sol.tipo_evento.nome if sol.tipo_evento else "",
            "data": sol.data.strftime("%Y-%m-%d") if sol.data else "",
            "hora_inicio": sol.hora_inicio.strftime("%H:%M") if sol.hora_inicio else "",
            "hora_fim": sol.hora_fim.strftime("%H:%M") if sol.hora_fim else "",
            "projeto": sol.projeto.nome if sol.projeto else "",
            "segmento": sol.segmento or "",
            "coord_acompanha": "sim" if sol.coord_acompanha else "",
            "coordenador": sol.coordenador.email if sol.coordenador else "",
            "formador1": formadores_emails[0],
            "formador2": formadores_emails[1],
            "formador3": formadores_emails[2],
            "formador4": formadores_emails[3],
            "formador5": formadores_emails[4],
            "aprovacao": sol.aprovacao if hasattr(sol, "aprovacao") else "",
        }

    def infer_source_sheet(self, sol: Solicitacao) -> str:
        """
        Infere a aba original (ACerta, Brincando, Vidas, Outros, Super) a partir do projeto.

        Args:
            sol: Instância de Solicitacao

        Returns:
            Nome da aba inferida
        """
        if not sol.projeto:
            return "Outros"

        projeto_nome = sol.projeto.nome.lower()

        if "acerta" in projeto_nome:
            return "ACerta"
        elif "brincando" in projeto_nome:
            return "Brincando"
        elif "vidas" in projeto_nome or "vida" in projeto_nome:
            return "Vidas"
        elif "super" in projeto_nome:
            return "Super"
        else:
            return "Outros"

    def generate_collisions_report(self, collisions: Dict[str, List[int]]):
        """
        Gera relatório JSON de colisões em v2/.agents/outbox/.

        Args:
            collisions: Mapa de hash → list[Solicitacao IDs]
        """
        outbox = Path("/app/.agents/outbox")
        outbox.mkdir(parents=True, exist_ok=True)

        output_file = outbox / "external_hash_v2_collisions.json"

        # Enriquecer com dados das solicitações
        report = []
        for hash_val, sol_ids in collisions.items():
            solicitacoes = Solicitacao.objects.filter(id__in=sol_ids).select_related(
                "municipio", "tipo_evento", "projeto", "coordenador"
            )

            collision_entry = {
                "hash": hash_val,
                "count": len(sol_ids),
                "solicitacoes": [
                    {
                        "id": sol.id,
                        "municipio": sol.municipio.nome if sol.municipio else None,
                        "tipo_evento": sol.tipo_evento.nome if sol.tipo_evento else None,
                        "data": sol.data.strftime("%Y-%m-%d") if sol.data else None,
                        "hora_inicio": sol.hora_inicio.strftime("%H:%M") if sol.hora_inicio else None,
                        "projeto": sol.projeto.nome if sol.projeto else None,
                        "coordenador": sol.coordenador.email if sol.coordenador else None,
                    }
                    for sol in solicitacoes
                ],
            }
            report.append(collision_entry)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"   📄 Colisões salvas em: {output_file}")
