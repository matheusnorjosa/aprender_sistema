"""
Views para Ingestão de CSVs ETL via REST API

App: dat_ingest
Stack: Python 3.13 | Django 5.2 | DRF
Timezone: America/Fortaleza

Endpoints:
    POST /api/ingest/agenda/ - Upload events.csv + event_people.csv
    POST /api/ingest/disponibilidade/ - Upload disp_blocks.csv + disp_travels.csv
    POST /api/ingest/controle/ - Upload controle_unificado.csv
    GET /api/ingest/health/ - Health check com contagens
"""

import csv
import logging
from io import StringIO
from typing import Any, Dict, List

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from core.rbac import IsDatOrControleOrAdminOps

from .models import (
    StgControleUnificado,
    StgDispBloqueio,
    StgDispDeslocamento,
    StgEvento,
    StgEventoPessoa,
)
from .serializers import (
    AgendaUploadSerializer,
    ControleUploadSerializer,
    DisponibilidadeUploadSerializer,
)
from .utils import parse_date, parse_time, safe_bool, safe_int, sha1_join

logger = logging.getLogger(__name__)


# =============================================================================
# UTILITÁRIOS DE LEITURA DE CSV
# =============================================================================


def read_csv_from_file(uploaded_file) -> List[Dict[str, str]]:
    """
    Lê arquivo CSV uploaded e retorna lista de dicts.

    Args:
        uploaded_file: InMemoryUploadedFile ou TemporaryUploadedFile

    Returns:
        Lista de dicionários (cada linha do CSV)
    """
    # Decodifica para string
    content = uploaded_file.read().decode("utf-8")
    csv_file = StringIO(content)

    # Lê com DictReader
    reader = csv.DictReader(csv_file)
    rows = list(reader)

    return rows


def validate_csv_headers(rows: List[Dict], required_fields: List[str], csv_name: str):
    """
    Valida que o CSV tem os campos obrigatórios.

    Args:
        rows: Lista de dicts do CSV
        required_fields: Lista de campos obrigatórios
        csv_name: Nome do CSV para mensagens de erro

    Raises:
        ValueError: Se campos obrigatórios faltam
    """
    if not rows:
        raise ValueError(f"{csv_name}: CSV vazio")

    first_row = rows[0]
    missing_fields = [f for f in required_fields if f not in first_row]

    if missing_fields:
        raise ValueError(
            f"{csv_name}: Campos obrigatórios faltando: {', '.join(missing_fields)}"
        )


# =============================================================================
# POST /api/ingest/agenda/
# =============================================================================


@api_view(["POST"])
@permission_classes([IsAdminUser])
def ingest_agenda(request):
    """
    Ingere arquivos events.csv e event_people.csv (DAT-P01).

    Payload:
        multipart/form-data com:
            - events (arquivo events.csv)
            - people (arquivo event_people.csv)

    Response:
        JSON: {"events_upserted": N, "people_upserted": M}
    """
    serializer = AgendaUploadSerializer(data=request.FILES)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Lê arquivos
        events_file = serializer.validated_data["events"]
        people_file = serializer.validated_data["people"]

        events_rows = read_csv_from_file(events_file)
        people_rows = read_csv_from_file(people_file)

        # Valida headers mínimos
        validate_csv_headers(
            events_rows, ["external_hash", "municipio", "data", "projeto"], "events.csv"
        )
        validate_csv_headers(
            people_rows,
            ["row_hash", "event_external_hash", "role", "name"],
            "event_people.csv",
        )

        # Upsert events
        events_upserted = 0
        for row in events_rows:
            external_hash = row.get("external_hash", "").strip()
            if not external_hash:
                logger.warning("Linha sem external_hash, pulando")
                continue

            _, created = StgEvento.objects.update_or_create(
                external_hash=external_hash,
                defaults={
                    "planilha": row.get("planilha", ""),
                    "aba": row.get("aba", ""),
                    "fluxo": row.get("fluxo", ""),
                    "aprovacao": row.get("aprovacao", ""),
                    "aprovado_futuro": row.get("aprovado_futuro", ""),
                    "criado_na_agenda": row.get("criado_na_agenda", ""),
                    "municipio": row.get("municipio", ""),
                    "encontro": row.get("encontro", ""),
                    "tipo": row.get("tipo", ""),
                    "data": parse_date(row.get("data", "")),
                    "hora_inicio": parse_time(row.get("hora_inicio", "")),
                    "hora_fim": parse_time(row.get("hora_fim", "")),
                    "projeto": row.get("projeto", ""),
                    "segmento": row.get("segmento", ""),
                    "coord_acompanha": row.get("coord_acompanha", ""),
                    "coordenador": row.get("coordenador", ""),
                    "formadores": row.get("formadores", ""),
                    "convidados": row.get("convidados", ""),
                    "cancelado_info": row.get("cancelado_info", ""),
                    "solicitante": row.get("solicitante", ""),
                    "status_temporal": row.get("status_temporal", ""),
                    "tempo_alerta": row.get("tempo_alerta", ""),
                },
            )
            events_upserted += 1

        # Upsert people
        people_upserted = 0
        for row in people_rows:
            row_hash = row.get("row_hash", "").strip()
            event_external_hash = row.get("event_external_hash", "").strip()

            if not row_hash or not event_external_hash:
                logger.warning("Linha sem row_hash ou event_external_hash, pulando")
                continue

            # Verifica se evento existe
            try:
                evento = StgEvento.objects.get(external_hash=event_external_hash)
            except StgEvento.DoesNotExist:
                logger.warning(
                    f"Evento {event_external_hash} não encontrado, pulando pessoa"
                )
                continue

            _, created = StgEventoPessoa.objects.update_or_create(
                row_hash=row_hash,
                defaults={
                    "event_external_hash": evento,
                    "role": row.get("role", "FORMADOR"),
                    "name": row.get("name", ""),
                    "matched": safe_bool(row.get("matched", "")),
                    "email": row.get("email", ""),
                    "cargo": row.get("cargo", ""),
                    "gerencia": row.get("gerencia", ""),
                },
            )
            people_upserted += 1

        return Response(
            {
                "events_upserted": events_upserted,
                "people_upserted": people_upserted,
            },
            status=status.HTTP_200_OK,
        )

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Erro ao ingerir agenda")
        return Response(
            {"error": f"Erro ao processar arquivos: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# POST /api/ingest/disponibilidade/
# =============================================================================


@api_view(["POST"])
@permission_classes([IsAdminUser])
def ingest_disponibilidade(request):
    """
    Ingere arquivos disp_blocks.csv e disp_travels.csv (DAT-P02).

    Payload:
        multipart/form-data com:
            - blocks (arquivo disp_blocks.csv)
            - travels (arquivo disp_travels.csv)

    Response:
        JSON: {"blocks_upserted": N, "travels_upserted": M}
    """
    serializer = DisponibilidadeUploadSerializer(data=request.FILES)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Lê arquivos
        blocks_file = serializer.validated_data["blocks"]
        travels_file = serializer.validated_data["travels"]

        blocks_rows = read_csv_from_file(blocks_file)
        travels_rows = read_csv_from_file(travels_file)

        # Valida headers mínimos
        validate_csv_headers(
            blocks_rows,
            ["row_hash", "data_inicial", "data_final", "tipo", "responsavel"],
            "disp_blocks.csv",
        )
        validate_csv_headers(
            travels_rows,
            ["row_hash", "origem", "data", "destino", "responsavel"],
            "disp_travels.csv",
        )

        # Upsert blocks
        blocks_upserted = 0
        for row in blocks_rows:
            row_hash = row.get("row_hash", "").strip()
            if not row_hash:
                logger.warning("Linha sem row_hash, pulando")
                continue

            _, created = StgDispBloqueio.objects.update_or_create(
                row_hash=row_hash,
                defaults={
                    "data_inicial": parse_date(row.get("data_inicial", "")),
                    "data_final": parse_date(row.get("data_final", "")),
                    "tipo": row.get("tipo", ""),
                    "responsavel": row.get("responsavel", ""),
                },
            )
            blocks_upserted += 1

        # Upsert travels
        travels_upserted = 0
        for row in travels_rows:
            row_hash = row.get("row_hash", "").strip()
            if not row_hash:
                logger.warning("Linha sem row_hash, pulando")
                continue

            _, created = StgDispDeslocamento.objects.update_or_create(
                row_hash=row_hash,
                defaults={
                    "origem": row.get("origem", ""),
                    "data": parse_date(row.get("data", "")),
                    "destino": row.get("destino", ""),
                    "responsavel": row.get("responsavel", ""),
                },
            )
            travels_upserted += 1

        return Response(
            {
                "blocks_upserted": blocks_upserted,
                "travels_upserted": travels_upserted,
            },
            status=status.HTTP_200_OK,
        )

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Erro ao ingerir disponibilidade")
        return Response(
            {"error": f"Erro ao processar arquivos: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# POST /api/ingest/controle/
# =============================================================================


@api_view(["POST"])
@permission_classes([IsAdminUser])
def ingest_controle(request):
    """
    Ingere arquivo controle_unificado.csv (DAT-P03).

    Payload:
        multipart/form-data com:
            - unificado (arquivo controle_unificado.csv)

    Response:
        JSON: {"unificado_upserted": N}
    """
    serializer = ControleUploadSerializer(data=request.FILES)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Lê arquivo
        unificado_file = serializer.validated_data["unificado"]
        unificado_rows = read_csv_from_file(unificado_file)

        # Valida headers mínimos
        validate_csv_headers(
            unificado_rows,
            ["row_hash", "municipio", "projeto", "uf", "gerencia"],
            "controle_unificado.csv",
        )

        # Upsert unificado
        unificado_upserted = 0
        for row in unificado_rows:
            row_hash = row.get("row_hash", "").strip()
            if not row_hash:
                logger.warning("Linha sem row_hash, pulando")
                continue

            _, created = StgControleUnificado.objects.update_or_create(
                row_hash=row_hash,
                defaults={
                    "municipio": row.get("municipio", ""),
                    "projeto": row.get("projeto", ""),
                    "uf": row.get("uf", ""),
                    "gerencia": row.get("gerencia", ""),
                    "qtd_compras": safe_int(row.get("qtd_compras", "0")),
                    "soma_quant": safe_int(row.get("soma_quant", "0")),
                    "primeira_data_compra": parse_date(
                        row.get("primeira_data_compra", "")
                    ),
                    "data_entrega": parse_date(row.get("data_entrega", "")),
                    "data_carta": parse_date(row.get("data_carta", "")),
                    "data_reuniao_alinhamento": parse_date(
                        row.get("data_reuniao_alinhamento", "")
                    ),
                    "contato_inicial": row.get("contato_inicial", ""),
                    "observacao_concat": row.get("observacao_concat", ""),
                },
            )
            unificado_upserted += 1

        return Response(
            {
                "unificado_upserted": unificado_upserted,
            },
            status=status.HTTP_200_OK,
        )

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Erro ao ingerir controle")
        return Response(
            {"error": f"Erro ao processar arquivo: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# GET /api/ingest/health/
# =============================================================================


@api_view(["GET"])
@permission_classes([IsDatOrControleOrAdminOps])
def health_check(request):
    """
    Health check endpoint.

    Retorna contagens por tabela e timestamp do último updated_at.
    Requer: DAT, Controle ou Admin Ops.

    Response:
        JSON: {
            "eventos": {"count": N, "last_updated": "2025-..."},
            "pessoas": {"count": M, "last_updated": "2025-..."},
            ...
        }
    """
    try:
        # Contagens
        eventos_count = StgEvento.objects.count()
        pessoas_count = StgEventoPessoa.objects.count()
        bloqueios_count = StgDispBloqueio.objects.count()
        deslocamentos_count = StgDispDeslocamento.objects.count()
        controle_count = StgControleUnificado.objects.count()

        # Timestamps do último updated_at
        eventos_last = (
            StgEvento.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        pessoas_last = (
            StgEventoPessoa.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        bloqueios_last = (
            StgDispBloqueio.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        deslocamentos_last = (
            StgDispDeslocamento.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        controle_last = (
            StgControleUnificado.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )

        return Response(
            {
                "eventos": {
                    "count": eventos_count,
                    "last_updated": eventos_last.isoformat() if eventos_last else None,
                },
                "pessoas": {
                    "count": pessoas_count,
                    "last_updated": pessoas_last.isoformat() if pessoas_last else None,
                },
                "bloqueios": {
                    "count": bloqueios_count,
                    "last_updated": (
                        bloqueios_last.isoformat() if bloqueios_last else None
                    ),
                },
                "deslocamentos": {
                    "count": deslocamentos_count,
                    "last_updated": (
                        deslocamentos_last.isoformat() if deslocamentos_last else None
                    ),
                },
                "controle_unificado": {
                    "count": controle_count,
                    "last_updated": (
                        controle_last.isoformat() if controle_last else None
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.exception("Erro no health check")
        return Response(
            {"error": f"Erro ao obter status: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
