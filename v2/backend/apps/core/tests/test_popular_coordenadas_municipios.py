"""
Comando `popular_coordenadas_municipios` (FER-66).

Preenche latitude/longitude dos municipios a partir de uma base publica casada pelo
codigo IBGE. Em producao (17/11/2026) nenhum dos 5.581 municipios tinha coordenada, e
a tela Mapa do Brasil saia vazia. O comando antigo morava em dev_tools (nao existe em
producao) e casava por nome um CSV de 171 municipios.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.models import Municipio
from apps.core.tests.factories import MunicipioFactory

pytestmark = pytest.mark.django_db

FORTALEZA = "2304400"
SALVADOR = "2927408"


def _csv(tmp_path, linhas: list[str]) -> str:
    p = tmp_path / "coords.csv"
    p.write_text("codigo_ibge,latitude,longitude\n" + "".join(f"{x}\n" for x in linhas), encoding="utf-8")
    return str(p)


def _roda(csv: str, *args: str, minimo: str = "1") -> str:
    out = StringIO()
    call_command("popular_coordenadas_municipios", "--csv", csv, "--minimo", minimo, *args, stdout=out)
    return out.getvalue()


def test_ensaio_nao_grava(tmp_path):
    m = MunicipioFactory(ibge_code=FORTALEZA)
    saida = _roda(_csv(tmp_path, [f"{FORTALEZA},-3.7172,-38.5431"]))
    m.refresh_from_db()
    assert m.latitude is None and m.longitude is None
    assert "preencheria: 1 " in saida
    assert "ENSAIO" in saida


def test_apply_preenche_pelo_codigo_ibge(tmp_path):
    m = MunicipioFactory(ibge_code=FORTALEZA, nome="Nome Diferente Da Base")
    _roda(_csv(tmp_path, [f"{FORTALEZA},-3.7172,-38.5431", f"{SALVADOR},-12.9718,-38.5011"]), "--apply")
    m.refresh_from_db()
    assert m.latitude == Decimal("-3.717200")
    assert m.longitude == Decimal("-38.543100")


def test_nao_sobrescreve_coordenada_existente(tmp_path):
    m = MunicipioFactory(ibge_code=FORTALEZA, latitude=Decimal("-3.0"), longitude=Decimal("-38.0"))
    igual = MunicipioFactory(ibge_code=SALVADOR, latitude=Decimal("-12.9718"), longitude=Decimal("-38.5011"))
    saida = _roda(
        _csv(tmp_path, [f"{FORTALEZA},-3.7172,-38.5431", f"{SALVADOR},-12.9718,-38.5011"]),
        "--apply",
    )
    m.refresh_from_db()
    igual.refresh_from_db()
    assert m.latitude == Decimal("-3.000000"), "coordenada existente foi sobrescrita"
    assert "ja tinha, diferente da base: 1" in saida
    assert "ja tinha, igual a base: 1" in saida


def test_sem_codigo_e_codigo_fora_da_base_sao_contados(tmp_path):
    MunicipioFactory(ibge_code=None)
    MunicipioFactory(ibge_code="")
    MunicipioFactory(ibge_code="9999999")
    saida = _roda(_csv(tmp_path, [f"{FORTALEZA},-3.7172,-38.5431"]), "--apply")
    assert "sem codigo IBGE: 2" in saida
    assert "codigo fora da base: 1" in saida
    assert Municipio.objects.filter(latitude__isnull=False).count() == 0


def test_arquivo_curto_demais_recusa(tmp_path):
    """Um arquivo cortado (download pela metade) nao pode ser aplicado como se fosse a base inteira."""
    MunicipioFactory(ibge_code=FORTALEZA)
    with pytest.raises(CommandError, match="linhas"):
        _roda(_csv(tmp_path, [f"{FORTALEZA},-3.7172,-38.5431"]), "--apply", minimo="5000")
    assert Municipio.objects.filter(latitude__isnull=False).count() == 0


@pytest.mark.parametrize(
    "linha",
    [
        f"{FORTALEZA},95.0,-38.5",  # latitude fora de -90..90
        f"{FORTALEZA},-3.7,-181",  # longitude fora de -180..180
        f"{FORTALEZA},abc,-38.5",  # nao e numero
        "230440,-3.7,-38.5",  # codigo sem 7 digitos
    ],
)
def test_linha_invalida_recusa_o_arquivo_inteiro(tmp_path, linha):
    MunicipioFactory(ibge_code=SALVADOR)
    with pytest.raises(CommandError, match="linha 3"):
        _roda(_csv(tmp_path, [f"{SALVADOR},-12.9718,-38.5011", linha]), "--apply")
    assert Municipio.objects.filter(latitude__isnull=False).count() == 0, "gravou parte de um arquivo invalido"


def test_codigo_repetido_no_arquivo_recusa(tmp_path):
    with pytest.raises(CommandError, match="repetido"):
        _roda(_csv(tmp_path, [f"{FORTALEZA},-3.7,-38.5", f"{FORTALEZA},-3.8,-38.6"]))


def test_arquivo_real_da_base_e_valido():
    """O arquivo versionado (recorte de kelvins/municipios-brasileiros, MIT) passa na validacao inteira."""
    caminho = Path(settings.BASE_DIR) / "data" / "municipios_coordenadas_ibge.csv"
    assert caminho.exists(), "o arquivo da base nao esta onde o comando procura"
    saida = _roda(str(caminho), minimo="5000")
    assert "linhas na base: 5571" in saida


def test_meia_coordenada_recebe_o_par_da_base_e_e_contada(tmp_path):
    """So latitude, sem longitude, nao aparece no mapa; vira o par inteiro da base, contado a parte."""
    m = MunicipioFactory(ibge_code=FORTALEZA, latitude=Decimal("-3.0"), longitude=None)
    saida = _roda(_csv(tmp_path, [f"{FORTALEZA},-3.7172,-38.5431"]), "--apply")
    m.refresh_from_db()
    assert (m.latitude, m.longitude) == (Decimal("-3.717200"), Decimal("-38.543100"))
    assert "com meia coordenada trocada pelo par da base: 1" in saida
