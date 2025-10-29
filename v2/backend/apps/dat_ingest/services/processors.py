"""
ETL Processors - Classes para processar planilhas (Shim/Adapter para testes Issue #39)

Este módulo fornece wrappers/adapters mínimos para os testes sem reescrever toda a lógica.
As implementações delegam para as funções parse_* e loaders existentes.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from .loaders import parse_usuarios, parse_municipios, parse_projetos
from .parse_acompanhamento import parse_todas_abas_acompanhamento
from .parse_bloqueios import parse_bloqueios
from .parse_deslocamentos import parse_deslocamentos


class AgendaProcessor:
    """
    Processa planilhas de agenda (wrapper para parse_acompanhamento)

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
        # Delega para parse_todas_abas_acompanhamento
        records = parse_todas_abas_acompanhamento(self.filepath)
        self.data = pd.DataFrame(records)
        return self.data

    def process(self) -> list[dict[str, Any]]:
        """
        Processa dados e retorna lista de registros

        Returns:
            Lista de dicionários com dados normalizados
        """
        if self.data is None:
            self.load()

        return self.data.to_dict("records")

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

    def process(self) -> list[dict[str, Any]]:
        """
        Processa dados e retorna lista de registros

        Returns:
            Lista de dicionários com dados normalizados
        """
        if self.data is None:
            self.load()

        return self.data.to_dict("records")

    def get_bloqueios(self) -> list[dict[str, Any]]:
        """
        Retorna lista de bloqueios

        Returns:
            Lista de dicionários com bloqueios
        """
        return self.process()


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

    def process(self) -> list[dict[str, Any]]:
        """
        Processa dados e retorna lista de registros

        Returns:
            Lista de dicionários com dados normalizados
        """
        if self.data is None:
            self.load()

        return self.data.to_dict("records")

    def get_deslocamentos(self) -> list[dict[str, Any]]:
        """
        Retorna lista de deslocamentos

        Returns:
            Lista de dicionários com deslocamentos
        """
        return self.process()
