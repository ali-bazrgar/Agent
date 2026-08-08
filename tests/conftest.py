from __future__ import annotations

from pathlib import Path

import pytest

from superagent.config.settings import Settings


@pytest.fixture
def temporary_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="testing",
        debug=True,
        app_host="127.0.0.1",
        app_port=9000,
        database_path=tmp_path / "superagent.sqlite3",
        storage_path=tmp_path / "storage",
        log_level="DEBUG",
    )
