"""
ETL Report JSON Schema - Estrutura padronizada para relatórios de ingestão

Localização: out/etl/last_run.json
Atualizado: A cada execução de comando de importação/sync

Exemplo de uso:
    from apps.core.schemas.etl_report import ETLReport, ETLMetrics

    report = ETLReport(
        command="preagenda_to_gcal",
        start_time=timezone.now(),
        end_time=timezone.now(),
        status="success",
        metrics=ETLMetrics(
            total_processed=100,
            created=10,
            updated=50,
            adopted=5,
            deleted=2,
            skipped=33,
            errors=0,
        ),
        filters={"since": "2025-01-01", "until": "2025-12-31"},
        errors=[],
    )

    report.save_to_file("out/etl/last_run.json")
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional, Literal
import json
import os


@dataclass
class ETLMetrics:
    """
    Métricas de processamento ETL.

    Atributos:
        total_processed: Total de registros processados
        created: Novos registros criados
        updated: Registros atualizados
        adopted: Registros adotados (já existiam mas não estavam vinculados)
        deleted: Registros deletados
        skipped: Registros ignorados (não processados)
        errors: Número de erros encontrados
    """

    total_processed: int
    created: int = 0
    updated: int = 0
    adopted: int = 0
    deleted: int = 0
    skipped: int = 0
    errors: int = 0


@dataclass
class ETLError:
    """
    Erro individual durante processamento ETL.

    Atributos:
        record_id: ID do registro que causou erro (se aplicável)
        error_type: Tipo de erro (ex: "ValidationError", "IntegrityError")
        message: Mensagem descritiva do erro
        timestamp: Quando o erro ocorreu
    """

    error_type: str
    message: str
    timestamp: str
    record_id: Optional[int] = None


@dataclass
class ETLReport:
    """
    Relatório completo de execução ETL.

    Atributos:
        command: Nome do comando executado
        start_time: Timestamp início da execução
        end_time: Timestamp fim da execução
        status: Status final (success, partial_success, failure)
        metrics: Métricas de processamento
        filters: Filtros aplicados (ex: data range, IDs específicos)
        errors: Lista de erros encontrados
        warnings: Lista de avisos (opcional)
    """

    command: str
    start_time: datetime
    end_time: datetime
    status: Literal["success", "partial_success", "failure"]
    metrics: ETLMetrics
    filters: Dict[str, str]
    errors: List[ETLError]
    warnings: List[str] = None

    def duration_seconds(self) -> float:
        """Calcula duração da execução em segundos"""
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """Converte para dicionário (JSON-serializable)"""
        data = {
            "command": self.command,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds(),
            "status": self.status,
            "metrics": asdict(self.metrics),
            "filters": self.filters,
            "errors": [asdict(e) for e in self.errors],
        }

        if self.warnings:
            data["warnings"] = self.warnings

        return data

    def save_to_file(self, filepath: str):
        """
        Salva relatório em arquivo JSON.

        Args:
            filepath: Caminho do arquivo (ex: "out/etl/last_run.json")
        """
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Escrever JSON formatado
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, filepath: str) -> "ETLReport":
        """
        Carrega relatório de arquivo JSON.

        Args:
            filepath: Caminho do arquivo

        Returns:
            ETLReport: Instância carregada do arquivo
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruir objetos
        metrics = ETLMetrics(**data["metrics"])
        errors = [ETLError(**e) for e in data["errors"]]

        return cls(
            command=data["command"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            status=data["status"],
            metrics=metrics,
            filters=data["filters"],
            errors=errors,
            warnings=data.get("warnings"),
        )


# ================================================================
# EXEMPLO DE SCHEMA JSON (para referência)
# ================================================================
ETL_REPORT_SCHEMA_EXAMPLE = {
    "command": "preagenda_to_gcal",
    "start_time": "2025-01-15T10:30:00+00:00",
    "end_time": "2025-01-15T10:32:15+00:00",
    "duration_seconds": 135.5,
    "status": "success",
    "metrics": {
        "total_processed": 1500,
        "created": 120,
        "updated": 800,
        "adopted": 50,
        "deleted": 30,
        "skipped": 500,
        "errors": 0,
    },
    "filters": {
        "since": "2025-01-01T00:00:00+00:00",
        "until": "2025-12-31T23:59:59+00:00",
        "calendar_id": "primary",
        "client": "fake",
    },
    "errors": [],
    "warnings": [
        "3 solicitações sem município definido (buffer RD-04 aplicado)",
        "15 eventos com summary > 1000 chars (truncados)",
    ],
}
