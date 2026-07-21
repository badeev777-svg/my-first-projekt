# tests/test_risk.py
import pytest

from app.risk import is_risky


@pytest.mark.parametrize(
    ("tool_name", "tool_input", "expected"),
    [
        ("Bash", {"command": "git push origin main"}, True),
        ("Bash", {"command": "git commit --amend -m x"}, True),
        ("Bash", {"command": "rm -rf /var/www/app"}, True),
        ("Bash", {"command": "sudo systemctl restart nginx"}, True),
        ("Bash", {"command": "docker compose up -d"}, True),
        ("Bash", {"command": "bash deploy.sh"}, True),
        ("Bash", {"command": "git diff"}, False),
        ("Bash", {"command": "git commit -m 'wip'"}, False),
        ("Bash", {"command": "ls -la"}, False),
        ("Write", {"file_path": "/root/projects/Aleks/.env"}, True),
        ("Write", {"file_path": "/root/projects/Aleks/credentials.json"}, True),
        ("Edit", {"file_path": "/root/projects/Aleks/secrets/token.pem"}, True),
        ("Write", {"file_path": "/root/projects/Aleks/app/main.py"}, False),
        ("Read", {"file_path": "/root/projects/Aleks/.env"}, False),
        ("Glob", {"pattern": "**/*.py"}, False),
    ],
)
def test_is_risky(tool_name: str, tool_input: dict, expected: bool) -> None:
    assert is_risky(tool_name, tool_input) is expected
