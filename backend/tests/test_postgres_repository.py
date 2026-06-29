import os
import unittest

from app.core.domain import PLATFORM_GOOGLE, ReviewRecord


class PostgresReviewRepositoryTests(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("RUN_POSTGRES_TESTS") == "1",
        "set RUN_POSTGRES_TESTS=1 to run Docker PostgreSQL integration tests",
    )
    def test_ensure_schema_and_save_review_record(self):
        import asyncio

        from app.repositories.reviews import PostgresReviewRepository

        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5432/culture_media",
        )
        repository = PostgresReviewRepository(database_url=database_url)

        saved_id = asyncio.run(self._save_record(repository))

        try:
            self.assertIsInstance(saved_id, int)
            self.assertGreater(saved_id, 0)
        finally:
            asyncio.run(self._delete_record(database_url, saved_id))

    async def _save_record(self, repository):
        await repository.ensure_schema()
        return await repository.save(
            ReviewRecord(
                source="test",
                platform=PLATFORM_GOOGLE,
                review_text="Integration test review.",
                feelings=["服务好"],
                summary="测试摘要。",
                reply_draft="测试回复。",
                wecom_sent=True,
                external_review_id="integration-test",
                author="Codex",
                rating=5,
            )
        )

    async def _delete_record(self, database_url, saved_id):
        import asyncio

        await asyncio.to_thread(self._delete_record_sync, database_url, saved_id)

    def _delete_record_sync(self, database_url, saved_id):
        import psycopg

        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM reviews WHERE id = %s AND source = 'test'", (saved_id,))
            connection.commit()


if __name__ == "__main__":
    unittest.main()
