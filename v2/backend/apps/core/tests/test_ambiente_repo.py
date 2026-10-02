"""
Self-verification do helper que pula (ou falha, na CI) os testes que dependem da
raiz do repositorio ou do git.

O QUE ESTA EM JOGO. Um skip mal feito esconde teste: se a CI um dia rodar sem a raiz
ou sem o git, 60 testes dos gates de documentacao sumiriam em silencio com a suite
verde. Por isso a trava tem teste proprio.

Verifica que:
1. Sem raiz e fora da CI -> skip, com o motivo combinado.
2. Sem raiz e na CI (`CI` ou `GITHUB_ACTIONS`) -> falha, com mensagem clara.
3. Com raiz -> devolve a raiz e nao pula, dentro ou fora da CI.
4. O mesmo para o git.
5. A deteccao da raiz nao estoura em caminho raso (o `IndexError` do container).
"""

from __future__ import annotations

import pathlib

import pytest

from apps.core.tests import ambiente_repo

VARIAVEIS_DE_CI = ("CI", "GITHUB_ACTIONS")


@pytest.fixture
def fora_da_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in VARIAVEIS_DE_CI:
        monkeypatch.delenv(nome, raising=False)


@pytest.fixture
def sem_raiz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ambiente_repo, "raiz_do_repo", lambda: None)


@pytest.fixture
def sem_git(monkeypatch: pytest.MonkeyPatch) -> None:
    def _nao_acha(_nome: str) -> None:
        return None

    monkeypatch.setattr(ambiente_repo.shutil, "which", _nao_acha)


@pytest.mark.usefixtures("fora_da_ci", "sem_raiz")
def test_sem_raiz_fora_da_ci_pula_com_motivo() -> None:
    with pytest.raises(pytest.skip.Exception) as erro:
        ambiente_repo.exige_raiz_do_repo()
    assert str(erro.value) == "precisa da raiz do repositório e do git (roda na CI)"


@pytest.mark.usefixtures("fora_da_ci", "sem_raiz")
@pytest.mark.parametrize("variavel", VARIAVEIS_DE_CI)
def test_sem_raiz_na_ci_falha_em_vez_de_pular(monkeypatch: pytest.MonkeyPatch, variavel: str) -> None:
    monkeypatch.setenv(variavel, "true")
    with pytest.raises(pytest.fail.Exception) as erro:
        ambiente_repo.exige_raiz_do_repo()
    assert "na CI estes testes têm de rodar" in str(erro.value)
    assert "raiz do repositório" in str(erro.value)


@pytest.mark.usefixtures("fora_da_ci", "sem_git")
def test_sem_git_fora_da_ci_pula_com_motivo() -> None:
    with pytest.raises(pytest.skip.Exception) as erro:
        ambiente_repo.exige_git()
    assert str(erro.value) == ambiente_repo.MOTIVO


@pytest.mark.usefixtures("fora_da_ci", "sem_git")
@pytest.mark.parametrize("variavel", VARIAVEIS_DE_CI)
def test_sem_git_na_ci_falha_em_vez_de_pular(monkeypatch: pytest.MonkeyPatch, variavel: str) -> None:
    monkeypatch.setenv(variavel, "true")
    with pytest.raises(pytest.fail.Exception) as erro:
        ambiente_repo.exige_git()
    assert "na CI estes testes têm de rodar" in str(erro.value)
    assert "git" in str(erro.value)


def _arvore_de_repo(base: pathlib.Path) -> pathlib.Path:
    """Arquivo de teste dentro de um checkout completo de mentira."""
    (base / "scripts").mkdir()
    (base / "v2" / "docs").mkdir(parents=True)
    testes = base / "v2" / "backend" / "apps" / "core" / "tests"
    testes.mkdir(parents=True)
    return testes / "ambiente_repo.py"


def test_raiz_presente_e_encontrada(tmp_path: pathlib.Path) -> None:
    arquivo = _arvore_de_repo(tmp_path)
    assert ambiente_repo.raiz_do_repo(arquivo) == tmp_path.resolve()


@pytest.mark.parametrize("ci", ["", "true"])
def test_com_raiz_roda_dentro_e_fora_da_ci(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, ci: str) -> None:
    monkeypatch.setenv("CI", ci)
    monkeypatch.setattr(ambiente_repo, "raiz_do_repo", lambda: tmp_path)
    assert ambiente_repo.exige_raiz_do_repo() == tmp_path


@pytest.mark.parametrize("ci", ["", "true"])
def test_com_git_roda_dentro_e_fora_da_ci(monkeypatch: pytest.MonkeyPatch, ci: str) -> None:
    def _acha(_nome: str) -> str:
        return "/usr/bin/git"

    monkeypatch.setenv("CI", ci)
    monkeypatch.setattr(ambiente_repo.shutil, "which", _acha)
    ambiente_repo.exige_git()


def test_caminho_raso_nao_estoura() -> None:
    """Caminho com so 4 niveis (o do container) nao tem `parents[5]`: era o IndexError da coleta."""
    assert ambiente_repo.raiz_do_repo(pathlib.Path("/raso/apps/core/tests/ambiente_repo.py")) is None


def test_so_o_backend_montado_nao_e_raiz(tmp_path: pathlib.Path) -> None:
    """Caminho fundo o bastante, mas sem `scripts/` e `v2/docs/` ao lado: nao e a raiz."""
    testes = tmp_path / "a" / "b" / "apps" / "core" / "tests"
    testes.mkdir(parents=True)
    assert ambiente_repo.raiz_do_repo(testes / "ambiente_repo.py") is None
