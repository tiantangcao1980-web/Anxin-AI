import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_github_actions_deploy_runs_backend_migrations() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")

    assert re.search(
        r'if \[ "\$BACKEND_CHANGED" = "true" \]; then[\s\S]*?docker compose exec -T backend alembic upgrade head[\s\S]*?fi',
        workflow,
    )


def test_manual_deploy_script_runs_backend_migrations() -> None:
    deploy_script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert re.search(
        r"if printf .*backend[\s\S]*?docker compose exec -T backend alembic upgrade head[\s\S]*?fi",
        deploy_script,
    )
