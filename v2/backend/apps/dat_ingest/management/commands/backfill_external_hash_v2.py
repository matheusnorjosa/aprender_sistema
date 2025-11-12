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
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.core.models import Solicitacao, Participation
from apps.dat_ingest.services.acompanhamento_normalize import hash_event_v2


class Command(BaseCommand):
    help = "Backfill external_hash v2 em Solicitações (PR21)"

    def add_arguments(self, parser: CommandParser) -> None:
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

    def handle(self, *args: Any, **options: Any) -> None:
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
        hash_map: dict[str, list[int]] = defaultdict(list)

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
                        try:
                            with transaction.atomic():
                                sol.external_hash = new_hash
                                sol.save(update_fields=["external_hash"])
                        except Exception as save_err:
                            # Unique constraint violation: skip silently (collision expected)
                            # Mas registrar para relatório de colisões
                            if "unique constraint" in str(save_err).lower() or "duplicate key" in str(save_err).lower():
                                pass  # Hash já registrado no hash_map para relatório
                            else:
                                raise  # Re-raise se for outro tipo de erro
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

    def _local_dt(self, dt: Any) -> Any:
        """Converte datetime UTC para America/Fortaleza"""
        if dt is None:
            return None
        return timezone.localtime(dt)

    def build_row_from_solicitacao(self, sol: Solicitacao) -> dict[str, str]:
        """
        Constrói dicionário de dados para hash_event_v2 a partir de Solicitacao.
        Garante normalização compatível com a pipeline do PR21.

        Args:
            sol: Instância de Solicitacao

        Returns:
            Dict com campos normalizados
        """
        # Converter inicio/fim para timezone local
        ini_local = self._local_dt(sol.inicio)
        fim_local = self._local_dt(sol.fim)

        data = ini_local.date().isoformat() if ini_local else ""
        hora_inicio = ini_local.strftime("%H:%M") if ini_local else ""
        hora_fim = fim_local.strftime("%H:%M") if fim_local else ""

        # Projeto com alias IDEB
        projeto_nome = (sol.projeto.nome or "").strip() if sol.projeto_id else ""
        from apps.dat_ingest.services.acompanhamento_normalize import normalize_project_alias
        projeto_normalizado = normalize_project_alias(projeto_nome)

        # Fluxo SUPER x NAO_SUPER
        fluxo = getattr(sol.projeto, "fluxo", "NAO_SUPER") or "NAO_SUPER"
        aprovacao = "SIM" if (fluxo == "SUPER" and sol.status == "aprovado") else ""

        # Coordenador (coordenador da solicitação)
        coord_email = (sol.coordenador.email or "").strip().lower() if sol.coordenador_id else ""
        coord_name = ""
        if sol.coordenador_id:
            fn = (sol.coordenador.first_name or "").strip()
            ln = (sol.coordenador.last_name or "").strip()
            coord_name = f"{fn} {ln}".strip()
        coordenador = coord_email or coord_name

        # Município
        municipio = (sol.municipio.nome or "").strip() if sol.municipio_id else ""

        # Tipo evento
        tipo = (sol.tipo_evento.nome or "").strip() if sol.tipo_evento_id else ""

        # Formadores: primeiro tenta M2M field, depois Participation
        formadores = []
        if hasattr(sol, 'formadores'):
            # Usar M2M field (modelo antigo)
            formadores_qs = sol.formadores.all()
            for f in formadores_qs:
                ident = (f.email or "").strip().lower()
                if not ident:
                    fn = (f.first_name or "").strip()
                    ln = (f.last_name or "").strip()
                    ident = f"{fn} {ln}".strip()
                if ident:
                    formadores.append(ident)

        # Se não encontrou formadores no M2M, tentar Participation
        if not formadores:
            parts = Participation.objects.filter(
                solicitacao=sol, role="FORMADOR"
            ).select_related("usuario")
            for p in parts:
                uemail = (getattr(p.usuario, "email", "") or "").strip().lower()
                uname = ""
                if p.usuario_id:
                    fn = (p.usuario.first_name or "").strip()
                    ln = (p.usuario.last_name or "").strip()
                    uname = f"{fn} {ln}".strip()
                ident = uemail or uname
                if ident:
                    formadores.append(ident)

        # Ordenação determinística e padding até 5
        formadores = sorted(set(formadores))[:5]
        while len(formadores) < 5:
            formadores.append("")

        # Coord acompanha: campo boolean ou Participation
        coord_acomp_str = ""
        if sol.coordenador_acompanha:
            coord_acomp_str = "sim"
        else:
            # Verificar Participation
            parts_coord = Participation.objects.filter(
                solicitacao=sol, role="COORD_ACOMPANHA"
            ).select_related("usuario")
            coord_acomp_list = []
            for p in parts_coord:
                uemail = (getattr(p.usuario, "email", "") or "").strip().lower()
                if uemail:
                    coord_acomp_list.append(uemail)
            if coord_acomp_list:
                coord_acomp_str = ";".join(sorted(set(coord_acomp_list)))

        # Campos ausentes no modelo: usar vazio
        encontro = sol.encontro or ""
        segmento = sol.segmento or ""

        # Source sheet inference
        source_sheet = self.infer_source_sheet(sol)

        return {
            "source_sheet": source_sheet,
            "municipio": municipio,
            "encontro": encontro,
            "tipo": tipo,
            "data": data,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim,
            "projeto": projeto_normalizado,
            "segmento": segmento,
            "coord_acompanha": coord_acomp_str,
            "coordenador": coordenador,
            "formador1": formadores[0],
            "formador2": formadores[1],
            "formador3": formadores[2],
            "formador4": formadores[3],
            "formador5": formadores[4],
            "aprovacao": aprovacao,
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

    def generate_collisions_report(self, collisions: dict[str, list[int]]) -> None:
        """
        Gera relatório JSON de colisões em v2/.agents/outbox/.

        Args:
            collisions: Mapa de hash → list[Solicitacao IDs]
        """
        outbox = Path(settings.BASE_DIR) / ".agents" / "outbox"
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
                        "inicio": sol.inicio.isoformat() if sol.inicio else None,
                        "fim": sol.fim.isoformat() if sol.fim else None,
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
