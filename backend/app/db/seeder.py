import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BusinessRule, FewShotExample
from app.services.embeddings import EmbeddingsProvider

logger = logging.getLogger(__name__)

DEFAULT_BUSINESS_RULES = [
    {
        "rule_name": "booking_statuses",
        "rule_description": "Booking status code to label mapping",
        "rule_value": "1=confirmed, 2=pending, 3=cancelled, 4=completed",
    },
    {
        "rule_name": "active_record",
        "rule_description": "Filter for active/live records",
        "rule_value": (
            "Use status NOT IN (3) for active bookings, or is_active = TRUE for active hotels"
        ),
    },
]

DEFAULT_FEW_SHOT_QUESTIONS = [
    {
        "question": "Which hotel has the most bookings?",
        "sql_query": (
            "SELECT hotel_id, COUNT(*) AS total FROM bookings "
            "GROUP BY hotel_id ORDER BY total DESC LIMIT 1"
        ),
    },
    {
        "question": "Show all confirmed bookings",
        "sql_query": "SELECT * FROM bookings WHERE status = 1",
    },
    {
        "question": "List hotels in Lahore",
        "sql_query": "SELECT id, name, city FROM hotels WHERE city = 'Lahore'",
    },
]


async def seed_database(db: AsyncSession, provider: EmbeddingsProvider) -> None:
    """Idempotently seeds default business rules and few-shot examples into the database.

    Each table is checked independently. If empty, the default rows are inserted.
    On failure, the transaction is rolled back and the exception is logged, but not propagated.
    """
    try:
        # 1. Seed Business Rules
        rules_count = await db.scalar(select(func.count()).select_from(BusinessRule))
        if rules_count is None or rules_count == 0:
            logger.info("Seeding Default Business Rules...")
            for rule_data in DEFAULT_BUSINESS_RULES:
                db.add(BusinessRule(**rule_data))
            await db.commit()
            logger.info("Successfully Seeded %d Business Rules.", len(DEFAULT_BUSINESS_RULES))
        else:
            logger.info(
                "Business Rules Table Already Contains %d Rows, Skipping Seeding.", rules_count
            )

        # 2. Seed Few-Shot Examples
        examples_count = await db.scalar(select(func.count()).select_from(FewShotExample))
        if examples_count is None or examples_count == 0:
            logger.info("Seeding Default Few-Shot Examples...")
            for ex in DEFAULT_FEW_SHOT_QUESTIONS:
                # Generate embeddings using the provided embeddings provider
                vector = await provider.get_embedding(ex["question"])
                db.add(
                    FewShotExample(
                        question=ex["question"],
                        sql_query=ex["sql_query"],
                        question_vector=vector,
                    )
                )
            await db.commit()
            logger.info(
                "Successfully Seeded %d Few-Shot Examples.", len(DEFAULT_FEW_SHOT_QUESTIONS)
            )
        else:
            logger.info(
                "Few-Shot Examples Table Already Contains %d Rows, Skipping Seeding.",
                examples_count,
            )

    except Exception as exc:
        logger.warning("Database Seeding Failed: %s. Rolling Back Transaction.", exc, exc_info=True)
        await db.rollback()
