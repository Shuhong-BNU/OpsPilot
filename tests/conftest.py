from pathlib import Path

import pytest

from app.config import config
from app.services.auth_service import auth_service
from app.services.database_service import database_service


@pytest.fixture(autouse=True)
def isolated_database(tmp_path: Path):
    original_db_path = config.database_path
    original_service_path = database_service.db_path
    original_initialized = database_service._initialized
    original_seeded = auth_service._seeded

    test_db_path = tmp_path / "opspilot-test.db"
    config.database_path = str(test_db_path)
    database_service.db_path = test_db_path
    database_service._initialized = False
    auth_service._seeded = False

    yield

    config.database_path = original_db_path
    database_service.db_path = original_service_path
    database_service._initialized = original_initialized
    auth_service._seeded = original_seeded
