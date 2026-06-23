import pytest
from sqlalchemy import text

from backend.database.session import session_scope


@pytest.mark.integration
def test_database_select_one() -> None:
    with session_scope() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1
