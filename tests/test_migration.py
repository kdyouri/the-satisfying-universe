import pytest
from sqlalchemy import inspect, select, text

from tsu.db import Base
from tsu.models import BudgetGuard


@pytest.mark.postgres
def test_initial_migration_creates_all_tables_and_budget_guard(postgres_engine):
    assert set(Base.metadata.tables) <= set(inspect(postgres_engine).get_table_names())
    with postgres_engine.connect() as connection:
        assert connection.execute(select(BudgetGuard.id)).first() is not None
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
