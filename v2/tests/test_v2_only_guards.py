from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_compose_project_name():
    env_path = ROOT / "infra" / ".env"
    assert env_path.exists()
    content = env_path.read_text()
    assert "COMPOSE_PROJECT_NAME=aprender_v2" in content


def test_compose_without_legacy_labels():
    compose = (ROOT / "infra" / "docker-compose.yml").read_text()
    assert "aprendersistema" not in compose
    assert "web-1" not in compose
    assert "db-1" not in compose
    assert "redis-1" not in compose


def test_makefile_exports_as_v2():
    text = (ROOT / "Makefile").read_text()
    assert "COMPOSE_PROJECT_NAME=aprender_v2" in text
