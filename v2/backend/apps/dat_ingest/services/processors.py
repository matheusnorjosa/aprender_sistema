"""
ETL Processors - Classes para processar planilhas (Shim/Adapter para testes Issue #39)

Este módulo fornece wrappers/adapters mínimos para os testes sem reescrever toda a lógica.
As implementações delegam para as funções parse_* e loaders existentes.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false


from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook

from .loaders import parse_usuarios, parse_municipios, parse_projetos
from .parse_acompanhamento import parse_todas_abas_acompanhamento
from .parse_bloqueios import parse_bloqueios
from .parse_deslocamentos import parse_deslocamentos


class AgendaProcessor:
    """
    Processa planilhas de agenda (wrapper para parse_acompanhamento)

    Attributes:
        filepath: Path para arquivo Excel
        users_df: DataFrame com usuários para inferência de roles
        data: DataFrame com dados processados
    """

    def __init__(self, filepath: Path, users_df: pd.DataFrame):
        self.filepath = filepath
        self.users_df = users_df
        self.data = None

    def load(self) -> pd.DataFrame:
        """
        Carrega dados do arquivo

        Returns:
            DataFrame com dados processados
        """
        # Delega para parse_todas_abas_acompanhamento
        records = parse_todas_abas_acompanhamento(self.filepath)

        # Adicionar campo 'setor' extraído de 'src' (formato: "filename/abaname")
        for record in records:
            src = record.get('src', '')
            if '/' in src:
                record['setor'] = src.split('/')[-1]
            else:
                record['setor'] = ''

        self.data = pd.DataFrame(records)
        return self.data

    def process(self) -> dict[str, Any]:
        """
        Processa dados e retorna dict com events, missing, summary

        Returns:
            Dict com:
            - events: DataFrame com eventos processados
            - missing: Lista de nomes/emails não encontrados em users_df
            - summary: Dict com estatísticas do processamento
        """
        if self.data is None:
            self.load()

        # Inferir roles (coordenador, formadores_lista) e fluxo
        events_list = []
        missing_set = set()

        for idx, record in enumerate(self.data.to_dict("records")):
            # Extract base fields (mapear nomes do parse para nomes esperados pelo teste)
            projeto = record.get("projeto_nome", "")
            tipo_evento = record.get("encontro", "")  # 'encontro' do parse → 'tipo_evento' do teste
            municipio_raw = record.get("municipio_nome_uf", "")
            coordenador_raw = record.get("coordenador_nome", "")
            formadores_raw = record.get("formadores", [])
            setor = record.get("setor", "")  # Aba name

            # Separar município e UF (ex: "Fortaleza - CE" → "Fortaleza")
            municipio = municipio_raw.split(" - ")[0].strip() if " - " in municipio_raw else municipio_raw

            # Inferir role coordenador (email exact match ou name fuzzy)
            coordenador_encontrado = self._infer_user(coordenador_raw, missing_set)

            # Inferir roles formadores
            formadores_nomes = []
            formadores_encontrados = []
            if isinstance(formadores_raw, list):
                for f in formadores_raw:
                    if f:  # Skip vazios
                        formadores_nomes.append(f)
                        formadores_encontrados.append(self._infer_user(f, missing_set))
            elif formadores_raw:
                formadores_nomes.append(formadores_raw)
                formadores_encontrados.append(self._infer_user(formadores_raw, missing_set))

            # Determinar fluxo baseado no setor (aba)
            fluxo = "SUPER" if setor and setor.strip().upper() == "SUPER" else "NAO_SUPER"

            # Gerar event_uid único (hash baseado em projeto + tipo_evento + municipio + idx)
            event_uid = hashlib.sha256(
                f"{projeto}{tipo_evento}{municipio}{idx}".encode()
            ).hexdigest()[:16]

            events_list.append({
                "projeto": projeto,
                "tipo_evento": tipo_evento,
                "municipio": municipio,
                "coordenador": coordenador_raw,  # Nome original
                "coordenador_encontrado": coordenador_encontrado,  # Email resolvido
                "formadores_lista": formadores_nomes,  # Nomes originais
                "formadores_encontrados": formadores_encontrados,  # Emails resolvidos
                "fluxo": fluxo,
                "event_uid": event_uid,
            })

        events_df = pd.DataFrame(events_list)

        return {
            "events": events_df,
            "missing": list(missing_set),
            "summary": {
                "total_events": len(events_df),
                "missing_count": len(missing_set),
                "abas_processed": self.data["setor"].nunique() if "setor" in self.data.columns else 0,
            },
        }

    def _infer_user(self, raw_value: str, missing_set: set[str]) -> str:
        """
        Infere usuário por email (exact match) ou nome (fuzzy match)

        Args:
            raw_value: Email ou nome raw
            missing_set: Set para acumular valores não encontrados

        Returns:
            Email do usuário encontrado ou raw_value se não encontrar
        """
        if not raw_value:
            return ""

        raw_lower = raw_value.strip().lower()

        # Tentativa 1: Match exato por email
        if "@" in raw_lower:
            match = self.users_df[self.users_df["email"].str.lower() == raw_lower]
            if not match.empty:
                return match.iloc[0]["email"]

        # Tentativa 2: Match fuzzy por nome (case-insensitive, partial)
        for idx, row in self.users_df.iterrows():
            nome = str(row.get("nome", "")).lower()
            email = str(row.get("email", "")).lower()

            # Match partial name
            if nome and raw_lower in nome:
                return row["email"]
            if nome and nome in raw_lower:
                return row["email"]

        # Não encontrado
        missing_set.add(raw_value)
        return raw_value

    def get_formadores(self) -> list[str]:
        """
        Extrai lista única de formadores

        Returns:
            Lista de nomes de formadores
        """
        if self.data is None:
            self.load()

        formadores = set()
        for record in self.data.to_dict("records"):
            # parse_acompanhamento retorna 'formadores' como lista
            if "formadores" in record and record["formadores"]:
                formadores.update(record["formadores"])

        return sorted(formadores)


class DisponibilidadeProcessor:
    """
    Processa planilhas de disponibilidade/bloqueios (wrapper para parse_bloqueios)

    Attributes:
        filepath: Path para arquivo Excel
        data: DataFrame com dados processados
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = None

    def load(self) -> pd.DataFrame:
        """
        Carrega dados do arquivo

        Returns:
            DataFrame com dados processados
        """
        # Delega para parse_bloqueios
        records = parse_bloqueios(self.filepath)
        self.data = pd.DataFrame(records)
        return self.data

    def process(self) -> dict[str, Any]:
        """
        Processa dados e retorna dict com bloqueios

        Returns:
            Dict com:
            - bloqueios: DataFrame com bloqueios processados
            - summary: Dict com estatísticas do processamento
        """
        if self.data is None:
            self.load()

        return {
            "bloqueios": self.data,
            "summary": {
                "total_bloqueios": len(self.data),
                "tipos": self.data["tipo"].value_counts().to_dict() if "tipo" in self.data.columns else {},
            },
        }

    def get_bloqueios(self) -> list[dict[str, Any]]:
        """
        Retorna lista de bloqueios

        Returns:
            Lista de dicionários com bloqueios
        """
        if self.data is None:
            self.load()
        return self.data.to_dict("records")


class ControleProcessor:
    """
    Processa planilhas de controle/deslocamentos (wrapper para parse_deslocamentos)

    Attributes:
        filepath: Path para arquivo Excel
        data: DataFrame com dados processados
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = None

    def load(self) -> pd.DataFrame:
        """
        Carrega dados do arquivo

        Returns:
            DataFrame com dados processados
        """
        # Delega para parse_deslocamentos
        records = parse_deslocamentos(self.filepath)
        self.data = pd.DataFrame(records)
        return self.data

    def process(self) -> dict[str, Any]:
        """
        Processa dados e retorna dict com compras (deslocamentos)

        Returns:
            Dict com:
            - compras: DataFrame com deslocamentos/compras processados
            - summary: Dict com estatísticas do processamento
        """
        if self.data is None:
            self.load()

        return {
            "compras": self.data,
            "summary": {
                "total_compras": len(self.data),
                "municipios": self.data["municipio"].nunique() if "municipio" in self.data.columns else 0,
            },
        }

    def get_deslocamentos(self) -> list[dict[str, Any]]:
        """
        Retorna lista de deslocamentos

        Returns:
            Lista de dicionários com deslocamentos
        """
        if self.data is None:
            self.load()
        return self.data.to_dict("records")
