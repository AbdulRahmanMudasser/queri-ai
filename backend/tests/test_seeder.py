from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import BusinessRule, FewShotExample
from app.db.seeder import seed_database
from app.services.embeddings import EmbeddingsProvider


class DummyProvider(EmbeddingsProvider):
    async def get_embedding(self, _text: str) -> list[float]:
        return [0.1] * 384


@pytest.mark.asyncio
async def test_seed_skips_business_rules_when_non_empty() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    # db.scalar returns 5 for rules, 0 for examples
    db.scalar.side_effect = [5, 0]

    await seed_database(db, DummyProvider())

    # Verify db.add is called for FewShotExample but not BusinessRule
    added_instances = [call.args[0] for call in db.add.call_args_list]
    assert len(added_instances) > 0
    assert all(isinstance(inst, FewShotExample) for inst in added_instances)
    assert not any(isinstance(inst, BusinessRule) for inst in added_instances)


@pytest.mark.asyncio
async def test_seed_skips_examples_when_non_empty() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    # db.scalar returns 0 for rules, 3 for examples
    db.scalar.side_effect = [0, 3]

    await seed_database(db, DummyProvider())

    # Verify db.add is called for BusinessRule but not FewShotExample
    added_instances = [call.args[0] for call in db.add.call_args_list]
    assert len(added_instances) > 0
    assert all(isinstance(inst, BusinessRule) for inst in added_instances)
    assert not any(isinstance(inst, FewShotExample) for inst in added_instances)


@pytest.mark.asyncio
async def test_seed_populates_business_rules_when_empty() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    # db.scalar returns 0 for rules, 5 for examples
    db.scalar.side_effect = [0, 5]

    await seed_database(db, DummyProvider())

    added_instances = [call.args[0] for call in db.add.call_args_list]
    assert len(added_instances) == 2  # DEFAULT_BUSINESS_RULES has 2 items
    assert all(isinstance(inst, BusinessRule) for inst in added_instances)
    assert added_instances[0].rule_name == "booking_statuses"
    assert added_instances[1].rule_name == "active_record"


@pytest.mark.asyncio
async def test_seed_populates_examples_when_empty() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    # db.scalar returns 5 for rules, 0 for examples
    db.scalar.side_effect = [5, 0]

    await seed_database(db, DummyProvider())

    added_instances = [call.args[0] for call in db.add.call_args_list]
    assert len(added_instances) == 3  # DEFAULT_FEW_SHOT_QUESTIONS has 3 items
    assert all(isinstance(inst, FewShotExample) for inst in added_instances)
    assert added_instances[0].question == "Which hotel has the most bookings?"
    assert added_instances[0].question_vector == [0.1] * 384


@pytest.mark.asyncio
async def test_seed_handles_exception_gracefully() -> None:
    db = AsyncMock()
    db.scalar.side_effect = Exception("Database connection lost")

    # Should not raise exception
    await seed_database(db, DummyProvider())

    # Assert rollback was called
    db.rollback.assert_called_once()
