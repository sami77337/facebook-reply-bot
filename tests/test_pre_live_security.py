from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
CORE_ROOTS = (
    APP_ROOT / "domain",
    APP_ROOT / "services",
    APP_ROOT / "persistence",
    APP_ROOT / "adapters" / "platforms",
)

FORBIDDEN_NETWORK_IMPORT_ROOTS = {
    "aiohttp",
    "aiogram",
    "facebook_business",
    "googleapiclient",
    "httpx",
    "requests",
    "telegram",
    "urllib3",
}
LEGACY_IMPORT_ROOTS = {
    "bot_manager",
    "database_config",
    "database_manager",
}


def _python_files() -> list[Path]:
    return sorted(path for root in CORE_ROOTS for path in root.rglob("*.py"))


def _case_id(value: Path) -> str:
    return str(value.relative_to(PROJECT_ROOT))


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


@pytest.mark.parametrize("path", _python_files(), ids=_case_id)
def test_new_core_has_no_direct_network_client_imports(path: Path) -> None:
    imported = _import_roots(path)
    assert imported.isdisjoint(FORBIDDEN_NETWORK_IMPORT_ROOTS), (
        f"{path.relative_to(PROJECT_ROOT)} imports a forbidden live-network dependency: "
        f"{sorted(imported & FORBIDDEN_NETWORK_IMPORT_ROOTS)}"
    )


@pytest.mark.parametrize("path", _python_files(), ids=_case_id)
def test_new_core_does_not_import_legacy_bot_modules(path: Path) -> None:
    imported = _import_roots(path)
    assert imported.isdisjoint(LEGACY_IMPORT_ROOTS), (
        f"{path.relative_to(PROJECT_ROOT)} imports legacy runtime code: "
        f"{sorted(imported & LEGACY_IMPORT_ROOTS)}"
    )


def test_new_application_contains_no_hardcoded_http_endpoints() -> None:
    offenders: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "http://" in text or "https://" in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == []


def test_ci_workflow_does_not_consume_production_secrets() -> None:
    ci = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "secrets." not in ci
    assert "contents: read" in ci


def test_secret_values_are_empty_in_env_example() -> None:
    env_lines = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    values = {
        key: value
        for line in env_lines
        if line and not line.startswith("#") and "=" in line
        for key, value in [line.split("=", 1)]
    }
    secret_keys = {
        "OPENAI_API_KEY",
        "META_ACCESS_TOKEN",
        "META_APP_SECRET",
        "META_VERIFY_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
        "FATWA_BRIDGE_SECRET",
    }
    assert secret_keys.issubset(values)
    assert all(values[key] == "" for key in secret_keys)


def test_shadow_service_has_no_external_action_contract_imports() -> None:
    path = APP_ROOT / "services" / "shadow.py"
    text = path.read_text(encoding="utf-8")
    forbidden_symbols = {
        "ReplyPublisher",
        "SupervisorTransportAdapter",
        "FatwaBridgeAdapter",
        "PublishingRepository",
    }
    assert all(symbol not in text for symbol in forbidden_symbols)
