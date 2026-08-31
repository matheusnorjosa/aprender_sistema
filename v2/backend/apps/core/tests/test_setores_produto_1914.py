"""#1914 — SETORES_PRODUTO: vocabulário canônico de setor-de-produto (SSOT + exposto no meta).

`setor_canonico` (Gerencia) é vocabulário CONTROLADO (RELAY 28/#1906), distinto dos 13 grupos RBAC
(`SETOR_GROUPS`). A tela de conferência precisa de um Select FECHADO — texto-livre traria o drift que
o campo combate. Os valores canônicos já existem como range do `SETOR_MAPPING`; `SETORES_PRODUTO` os
fixa como SSOT em `constants` e o `RBACMetaView` os expõe pro FE montar o Select.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOperatorIssue=false, reportIndexIssue=false

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.constants import SETORES_PRODUTO
from apps.core.services.equipe_gerencia_import import SETOR_MAPPING
from apps.core.tests.factories import UsuarioFactory


def test_setor_mapping_so_mapeia_para_valores_canonicos() -> None:
    # Todo DESTINO do de-para (SETOR_MAPPING) tem de ser um setor-de-produto canônico:
    # senão um setor importado não teria opção na conferência (drift latente).
    assert set(SETOR_MAPPING.values()) <= set(SETORES_PRODUTO), set(SETOR_MAPPING.values()) - set(SETORES_PRODUTO)


def test_setores_produto_sem_duplicatas_e_nao_vazio() -> None:
    assert len(SETORES_PRODUTO) == len(set(SETORES_PRODUTO))
    assert len(SETORES_PRODUTO) >= 1


@pytest.mark.django_db
def test_rbac_meta_expoe_setores_produto() -> None:
    user = UsuarioFactory(groups=["DAT"])
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/rbac/meta/")
    assert resp.status_code == status.HTTP_200_OK
    assert "setores_produto" in resp.data
    assert set(resp.data["setores_produto"]) == set(SETORES_PRODUTO)
